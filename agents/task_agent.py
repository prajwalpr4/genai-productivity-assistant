"""
Task Agent
==========
A specialised sub-agent responsible for all task-management operations.
It is given the task-related tools and a focused system prompt.
"""

from langgraph.prebuilt import create_react_agent
from tools.task_tools import task_tools

TASK_AGENT_PROMPT = (
    "You are the **Task Management Agent**, a specialist in to-do and task tracking.\n"
    "Your capabilities:\n"
    "  • Create new tasks with title, description, priority (low/medium/high), and due date.\n"
    "  • List tasks — optionally filtered by status (todo, in_progress, done).\n"
    "  • Update a task's status.\n"
    "  • Retrieve full details of a task.\n"
    "  • Delete tasks.\n\n"
    "Always confirm the action you took with a brief, friendly summary.\n"
    "If the user's request is ambiguous, ask for clarification before acting.\n"
    "Use the tools available to you — never make up data."
)


def create_task_agent(llm):
    """Return a compiled ReAct agent graph wired to task tools."""
    return create_react_agent(llm, task_tools, prompt=TASK_AGENT_PROMPT)
