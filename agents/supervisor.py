"""
Supervisor Agent — Multi-Agent Orchestrator
============================================
Uses LangGraph to build a Supervisor → Worker pattern:

  1. User message enters at the **supervisor** node.
  2. Supervisor uses Gemini + structured output to decide which
     sub-agent should handle the request (or FINISH).
  3. The chosen sub-agent executes its tools against the database.
  4. Control returns to the supervisor, which can route to another
     agent or finish the workflow.

This design satisfies the hackathon requirement of a *primary agent
coordinating one or more sub-agents* with multi-step workflows.
"""

from __future__ import annotations

import json
import logging
from typing import Annotated, Literal, Sequence, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent

from agents.task_agent import create_task_agent, TASK_AGENT_PROMPT, task_tools
from agents.calendar_agent import create_calendar_agent, CALENDAR_AGENT_PROMPT, calendar_tools
from agents.notes_agent import create_notes_agent, NOTES_AGENT_PROMPT, notes_tools

logger = logging.getLogger(__name__)

# ── Shared state across all nodes ──────────────────────────────────

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    next: str                # routing target set by the supervisor
    agents_used: list[str]   # tracks which agents participated


# ── Supervisor prompt ──────────────────────────────────────────────

SUPERVISOR_SYSTEM = """\
You are the **Supervisor Agent** of a multi-agent productivity assistant.

You coordinate three specialised sub-agents:
  • task_agent   – creates, lists, updates, and deletes tasks.
  • calendar_agent – manages calendar events and checks availability.
  • notes_agent  – saves, searches, and manages notes.

### Routing rules
1. Read the user's latest request carefully.
2. Decide which ONE sub-agent should act next.
3. If the request spans multiple domains (e.g. "create a task AND schedule a meeting"),
   route to one agent at a time — you will get a chance to route again after each completes.
4. If ALL required work has been completed, or the user is just chatting, choose FINISH.

### Response format
Respond with ONLY a JSON object (no markdown, no extra text):
{"next": "<task_agent|calendar_agent|notes_agent|FINISH>", "reasoning": "<one sentence>"}
"""

# ── Build the multi-agent graph ────────────────────────────────────

def build_multi_agent_graph():
    """Construct and compile the LangGraph supervisor workflow."""

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0,
        convert_system_message_to_human=True,
        max_retries=3,
        timeout=60,
    )

    # ---- Sub-agents (ReAct agents compiled by LangGraph) -----------
    _task_agent = create_react_agent(llm, task_tools, prompt=TASK_AGENT_PROMPT)
    _calendar_agent = create_react_agent(llm, calendar_tools, prompt=CALENDAR_AGENT_PROMPT)
    _notes_agent = create_react_agent(llm, notes_tools, prompt=NOTES_AGENT_PROMPT)

    # ---- Node functions -------------------------------------------

    def supervisor_node(state: AgentState) -> dict:
        """Use Gemini to decide which agent handles the next step."""
        messages = list(state["messages"])
        response = llm.invoke([SystemMessage(content=SUPERVISOR_SYSTEM)] + messages)
        content = response.content.strip()

        # Parse the JSON routing decision
        try:
            # Handle cases where model wraps JSON in markdown code fences
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            decision = json.loads(content)
            next_agent = decision.get("next", "FINISH")
            reasoning = decision.get("reasoning", "")
        except (json.JSONDecodeError, AttributeError):
            # Fallback: try to find agent name in raw text
            content_lower = content.lower()
            if "task" in content_lower:
                next_agent = "task_agent"
                reasoning = "Detected task-related request."
            elif "calendar" in content_lower or "schedule" in content_lower or "event" in content_lower or "meeting" in content_lower:
                next_agent = "calendar_agent"
                reasoning = "Detected calendar-related request."
            elif "note" in content_lower:
                next_agent = "notes_agent"
                reasoning = "Detected notes-related request."
            else:
                next_agent = "FINISH"
                reasoning = "No specific agent needed."

        logger.info(f"Supervisor → {next_agent} ({reasoning})")
        agents_used = list(state.get("agents_used", []))
        return {"next": next_agent, "agents_used": agents_used}

    def _make_agent_node(agent_graph, agent_name: str):
        """Wrap a sub-agent so it appends a tagged summary to shared state."""

        def node(state: AgentState) -> dict:
            # Invoke the sub-agent's own react graph
            result = agent_graph.invoke({"messages": list(state["messages"])})

            # Extract the last non-tool AI message as the summary
            ai_msgs = [
                m for m in result["messages"]
                if isinstance(m, AIMessage) and not getattr(m, "tool_calls", None)
            ]
            summary = ai_msgs[-1].content if ai_msgs else "Done."
            agents_used = list(state.get("agents_used", []))
            if agent_name not in agents_used:
                agents_used.append(agent_name)

            return {
                "messages": [AIMessage(content=summary, name=agent_name)],
                "agents_used": agents_used,
            }

        return node

    # ---- Assemble the graph ----------------------------------------
    workflow = StateGraph(AgentState)

    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("task_agent", _make_agent_node(_task_agent, "task_agent"))
    workflow.add_node("calendar_agent", _make_agent_node(_calendar_agent, "calendar_agent"))
    workflow.add_node("notes_agent", _make_agent_node(_notes_agent, "notes_agent"))

    # Entry point
    workflow.add_edge(START, "supervisor")

    # Supervisor routes conditionally
    workflow.add_conditional_edges(
        "supervisor",
        lambda state: state.get("next", "FINISH"),
        {
            "task_agent": "task_agent",
            "calendar_agent": "calendar_agent",
            "notes_agent": "notes_agent",
            "FINISH": END,
        },
    )

    # After each sub-agent, return to supervisor for potential follow-up
    workflow.add_edge("task_agent", "supervisor")
    workflow.add_edge("calendar_agent", "supervisor")
    workflow.add_edge("notes_agent", "supervisor")

    return workflow.compile()
