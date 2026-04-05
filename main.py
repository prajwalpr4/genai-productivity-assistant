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

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer
from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy.orm import Session
import jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta

from agents.supervisor import build_multi_agent_graph, API_KEYS
from database.db import init_db, get_db
from database.models import User
from models.schemas import ChatRequest, ChatResponse, HealthResponse, ToolInfo, UserCreate, UserLogin, UserProfileUpdate, UserProfileResponse, Token
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


# ── Auth Configuration ─────────────────────────────────────────────
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-hackathon-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 1 week

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = str(payload.get("sub"))
        if user_id is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    return user


# ── Auth Routes ────────────────────────────────────────────────────

@app.post("/api/v1/auth/register", response_model=Token)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = User(
        email=user_in.email,
        password_hash=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        age=user_in.age,
        gender=user_in.gender,
        phone_number=user_in.phone_number
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    access_token = create_access_token(
        data={"sub": str(new_user.id)}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/v1/auth/login", response_model=Token)
def login(user_in: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_in.email).first()
    if not user or not verify_password(user_in.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
        
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/v1/profile", response_model=UserProfileResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user

@app.put("/api/v1/profile", response_model=UserProfileResponse)
def update_profile(profile_in: UserProfileUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    update_data = profile_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(current_user, key, value)
        
    db.commit()
    db.refresh(current_user)
    return current_user


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
