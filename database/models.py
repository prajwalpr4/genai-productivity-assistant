"""
SQLAlchemy ORM models for Tasks, Calendar Events, and Notes.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from database.db import Base


class Task(Base):
    """A productivity task with status tracking and priority levels."""
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    status = Column(String(20), default="todo")          # todo | in_progress | done
    priority = Column(String(20), default="medium")      # low | medium | high
    due_date = Column(String(50), default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Task(id={self.id}, title='{self.title}', status='{self.status}')>"


class CalendarEvent(Base):
    """A calendar event with start/end times and optional location."""
    __tablename__ = "calendar_events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    start_time = Column(String(50), nullable=False)
    end_time = Column(String(50), nullable=False)
    location = Column(String(255), default="")
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<CalendarEvent(id={self.id}, title='{self.title}')>"


class Note(Base):
    """A free-form note with optional tags for organization."""
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, default="")
    tags = Column(String(500), default="")               # Comma-separated tags
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Note(id={self.id}, title='{self.title}')>"


class User(Base):
    """User profile for authentication and personal info."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), default="")
    age = Column(Integer, nullable=True)
    gender = Column(String(50), default="")
    phone_number = Column(String(50), default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"
