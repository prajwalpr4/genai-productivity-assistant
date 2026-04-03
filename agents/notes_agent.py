"""
Notes Agent
===========
A specialised sub-agent responsible for all note-taking operations.
"""

from langgraph.prebuilt import create_react_agent
from tools.notes_tools import notes_tools

NOTES_AGENT_PROMPT = (
    "You are the **Notes Management Agent**, a specialist in capturing information.\n"
    "Your capabilities:\n"
    "  • Save new notes with a title, content, and optional comma-separated tags.\n"
    "  • Search notes by keyword (searches title, content, and tags).\n"
    "  • List all saved notes.\n"
    "  • Retrieve the full content of a specific note.\n"
    "  • Delete notes.\n\n"
    "Always confirm the action you took with a brief, friendly summary.\n"
    "If the user's request is ambiguous, ask for clarification before acting.\n"
    "Use the tools available to you — never make up data."
)


def create_notes_agent(llm):
    """Return a compiled ReAct agent graph wired to notes tools."""
    return create_react_agent(llm, notes_tools, prompt=NOTES_AGENT_PROMPT)
