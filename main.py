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

from agents.supervisor import build_multi_agent_graph, API_KEYS
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


# ── Startup / Shutdown ─────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    logger.info("Initialising database …")
    init_db()

    # Force-import tools so they register with the MCP registry
    import tools.task_tools      # noqa: F401
    import tools.calendar_tools  # noqa: F401
    import tools.notes_tools     # noqa: F401

    logger.info(f"Ready — {len(registry)} tools registered | {len(API_KEYS)} API key(s) loaded for rotation.")


# ── Chat endpoint ──────────────────────────────────────────────────

@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Accept a natural-language message, route it through the multi-agent
    supervisor, and return the final response.

    On rate-limit (429) errors, automatically retries with the next API
    key in the rotation pool.
    """
    logger.info(f"[session={req.session_id}] user: {req.message}")
    start = time.time()

    max_attempts = max(len(API_KEYS), 1)
    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            # Build a fresh graph with the next API key from the pool
            graph = build_multi_agent_graph()

            result = graph.invoke(
                {
                    "messages": [HumanMessage(content=req.message)],
                    "next": "",
                    "agents_used": [],
                }
            )

            elapsed = time.time() - start
            logger.info(f"Completed in {elapsed:.2f}s (attempt {attempt}/{max_attempts})")

            # Extract final AI message
            ai_msgs = [
                m for m in result["messages"]
                if isinstance(m, AIMessage)
            ]
            if ai_msgs:
                response_text = ai_msgs[-1].content
            else:
                # If no agents were used, provide a helpful conversational fallback
                response_text = (
                    "Hello! I am your productivity assistant. I can help you manage your tasks, "
                    "calendar events, and notes. Try asking me to 'Create a new task' or 'Schedule a meeting'!"
                )

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

        except Exception as exc:
            last_error = exc
            err_msg = str(exc).lower()
            is_rate_limit = "429" in str(exc) or "quota" in err_msg or "rate" in err_msg or "resource" in err_msg

            if is_rate_limit and attempt < max_attempts:
                logger.warning(
                    f"Rate-limited on attempt {attempt}/{max_attempts}. "
                    f"Rotating to next API key and retrying in 2s…"
                )
                time.sleep(2)
                continue
            else:
                logger.exception("Agent invocation failed")
                if is_rate_limit:
                    raise HTTPException(
                        status_code=429,
                        detail="All API keys are currently rate-limited. Please wait a minute and try again.",
                    )
                raise HTTPException(status_code=500, detail=f"Agent error: {str(exc)[:200]}")


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
