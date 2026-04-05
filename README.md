# 🤖 Multi-Agent Productivity Assistant

A multi-agent AI system built with **FastAPI**, **LangGraph**, and **Google Gemini** that helps users manage tasks, schedules, and information through natural language.

## 🏗️ Architecture

```
User ──▶ FastAPI ──▶ Supervisor Agent (Gemini 2.0 Flash)
                          │
                ┌─────────┼─────────┐
                ▼         ▼         ▼
          Task Agent  Calendar   Notes
                       Agent     Agent
                │         │         │
                ▼         ▼         ▼
              SQLite Database (Tasks / Events / Notes)
```

### Key Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **API Layer** | FastAPI | RESTful endpoints + Chat UI |
| **Agent Orchestration** | LangGraph | Supervisor → Worker multi-agent pattern |
| **LLM Engine** | Gemini 2.0 Flash | Natural language understanding & tool calling |
| **Tool Protocol** | MCP-style Registry | Standardised tool discovery & execution |
| **Database** | SQLAlchemy + SQLite | Structured data persistence |
| **Auth System** | JSON Storage + BCrypt | Local User Profiles management |

## 📁 Project Structure

```
genai-productivity-assistant/
├── main.py                 # FastAPI application entry point
├── agents/
│   ├── supervisor.py       # Primary supervisor agent (LangGraph)
│   ├── task_agent.py       # Task management sub-agent
│   ├── calendar_agent.py   # Calendar management sub-agent
│   └── notes_agent.py      # Notes management sub-agent
├── tools/
│   ├── task_tools.py       # Task CRUD tools
│   ├── calendar_tools.py   # Calendar CRUD tools
│   ├── notes_tools.py      # Notes CRUD + search tools
│   └── mcp_registry.py     # MCP tool registry
├── database/
│   ├── db.py               # SQLAlchemy engine & session
│   ├── models.py           # ORM models (Task, Event, Note)
│   └── users.json          # Local Auth storage
├── models/
│   └── schemas.py          # Pydantic request/response schemas
├── static/
│   └── index.html          # Chat UI
├── Dockerfile
├── requirements.txt
└── .env
```

## 🚀 Quick Start

### 1. Clone & install

```bash
git clone <your-repo-url>
cd genai-productivity-assistant
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY
```

### 3. Run locally

```bash
uvicorn main:app --reload --port 8000
```

Visit `http://localhost:8000` for the chat UI or `http://localhost:8000/docs` for Swagger.

## ☁️ Deploy to Cloud Run

```bash
# Build and deploy
gcloud run deploy productivity-assistant \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_API_KEY=<your-key>
```

## 🛠️ API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/auth/register` | Register a new user profile |
| `POST` | `/api/v1/auth/login` | Authenticate and receive JWT |
| `GET/PUT` | `/api/v1/profile` | Read or Update personal details |
| `GET` | `/api/v1/dashboard/*` | Fetch live data for widget rendering |
| `POST` | `/api/v1/chat` | Send a message to the multi-agent system |
| `GET` | `/api/v1/tools` | MCP-style tool discovery |
| `GET` | `/api/v1/health` | Health check |
| `GET` | `/` | Dashboard & Chat UI |

### Example Request

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Create a high-priority task to finish the report by Friday and schedule a team meeting tomorrow at 3 PM"}'
```

## 🤖 Multi-Agent Workflow

1. **User** sends a natural language request via the API.
2. **Supervisor Agent** analyses the request and routes to the appropriate sub-agent.
3. **Sub-Agent** (Task / Calendar / Notes) executes the relevant tools against the database.
4. Control returns to the **Supervisor**, which may route to another agent if the request spans multiple domains.
5. Final response is compiled and returned to the user.

## 📄 License

Built for the **GenAI Academy APAC Edition — Cohort 1 Hackathon** (2026).
#
