"""
Pydantic schemas for API request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional


class ChatRequest(BaseModel):
    """Incoming chat message from the user."""
    message: str = Field(..., description="The user's natural language request")
    session_id: str = Field(default="default", description="Session identifier for conversation continuity")


class ChatResponse(BaseModel):
    """Response from the multi-agent system."""
    response: str = Field(..., description="The assistant's final answer")
    agents_used: list[str] = Field(default_factory=list, description="Sub-agents that participated")
    steps: list[str] = Field(default_factory=list, description="High-level steps taken by the system")


class ToolInfo(BaseModel):
    """MCP-style tool metadata exposed via the discovery endpoint."""
    name: str
    domain: str
    description: str


class HealthResponse(BaseModel):
    """Health-check response."""
    status: str = "healthy"
    version: str = "1.0.0"
    agents: list[str] = []
    tools_count: int = 0
