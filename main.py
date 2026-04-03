"""
Multi-Agent Productivity Assistant — FastAPI Application
=========================================================
Endpoints:
  POST /api/v1/chat        – Send a natural-language request to the supervisor
  GET  /api/v1/tools        – MCP-style tool discovery
  GET  /api/v1/health       – Health check
  GET  /                    – Serves the chat UI
"""

from __future__ import annotations

import logging
import os
import time

from dotenv import load_dotenv

load_dotenv()  # must happen before any Google SDK import

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import AIMessage, HumanMessage

from agents.supervisor import build_multi_agent_graph
from database.db import init_db
from models.schemas import ChatRequest, ChatResponse, HealthResponse, ToolInfo
from tools.mcp_registry import registry

# ── Logging ────────────────────────────────────────────────────────
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

# ── App setup ──────────────────────────────────────────────────────
app = FastAPI(
    title="Multi-Agent Productivity Assistant",
    description=(
        "An AI-powered assistant that coordinates Task, Calendar, and Notes "
        "agents to manage your productivity workflows."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global reference to the compiled multi-agent graph
graph = None


# ── Startup / Shutdown ─────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    global graph
    logger.info("Initialising database …")
    init_db()

    logger.info("Building multi-agent graph …")
    graph = build_multi_agent_graph()

    # Force-import tools so they register with the MCP registry
    import tools.task_tools      # noqa: F401
    import tools.calendar_tools  # noqa: F401
    import tools.notes_tools     # noqa: F401

    logger.info(f"Ready — {len(registry)} tools registered across MCP registry.")


# ── Chat endpoint ──────────────────────────────────────────────────

@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Accept a natural-language message, route it through the multi-agent
    supervisor, and return the final response.
    """
    if graph is None:
        raise HTTPException(status_code=503, detail="Agent system not ready.")

    logger.info(f"[session={req.session_id}] user: {req.message}")
    start = time.time()

    try:
        result = graph.invoke(
            {
                "messages": [HumanMessage(content=req.message)],
                "next": "",
                "agents_used": [],
            }
        )
    except Exception as exc:
        logger.exception("Agent invocation failed")
        err_msg = str(exc)
        if "quota" in err_msg.lower() or "rate" in err_msg.lower() or "429" in err_msg:
            raise HTTPException(
                status_code=429,
                detail="The AI service is temporarily rate-limited. Please wait a few seconds and try again.",
            )
        raise HTTPException(status_code=500, detail=f"Agent error: {err_msg[:200]}")

    elapsed = time.time() - start
    logger.info(f"Completed in {elapsed:.2f}s")

    # Extract final AI message
    ai_msgs = [
        m for m in result["messages"]
        if isinstance(m, AIMessage)
    ]
    response_text = ai_msgs[-1].content if ai_msgs else "I wasn't able to process that request."

    agents_used = result.get("agents_used", [])

    # Build step log from named messages
    steps = []
    for m in result["messages"]:
        if isinstance(m, AIMessage) and getattr(m, "name", None):
            steps.append(f"[{m.name}] {m.content[:120]}")

    return ChatResponse(
        response=response_text,
        agents_used=agents_used,
        steps=steps,
    )


# ── MCP tool discovery ─────────────────────────────────────────────

@app.get("/api/v1/tools", response_model=list[ToolInfo])
async def list_tools():
    """MCP-style tool discovery — lists every registered tool."""
    return registry.list_tools()


# ── Health check ───────────────────────────────────────────────────

@app.get("/api/v1/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        agents=["supervisor", "task_agent", "calendar_agent", "notes_agent"],
        tools_count=len(registry),
    )


# ── Serve the chat UI ─────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    ui_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    try:
        with open(ui_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Multi-Agent Productivity Assistant API</h1>"
            "<p>Visit <a href='/docs'>/docs</a> for the Swagger UI.</p>",
            status_code=200,
        )
