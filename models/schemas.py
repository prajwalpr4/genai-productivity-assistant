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


class UserCreate(BaseModel):
    """Schema for user registration."""
    email: str
    password: str
    full_name: Optional[str] = ""
    age: Optional[int] = None
    gender: Optional[str] = ""
    phone_number: Optional[str] = ""


class UserLogin(BaseModel):
    """Schema for user login."""
    email: str
    password: str


class UserProfileUpdate(BaseModel):
    """Schema to update a user profile."""
    full_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    phone_number: Optional[str] = None


class UserProfileResponse(BaseModel):
    """Secure response schema for user info (no password)."""
    id: int
    email: str
    full_name: str
    age: Optional[int]
    gender: str
    phone_number: str

    class Config:
        from_attributes = True


class Token(BaseModel):
    """JWT Token response schema."""
    access_token: str
    token_type: str = "bearer"

class TaskResponse(BaseModel):
    id: int
    title: str
    status: str
    priority: str
    due_date: str

    class Config:
        from_attributes = True

class CalendarEventResponse(BaseModel):
    id: int
    title: str
    start_time: str
    end_time: str
    
    class Config:
        from_attributes = True

class NoteResponse(BaseModel):
    id: int
    title: str
    
    class Config:
        from_attributes = True
