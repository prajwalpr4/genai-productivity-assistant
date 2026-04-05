"""
Database engine, session, and initialization utilities.
Uses SQLAlchemy with SQLite (easily swappable for Cloud SQL / Postgres).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./productivity.db")

# For SQLite we need check_same_thread=False so FastAPI threads can share the connection
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency – yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables defined by models that inherit from Base."""
    from database.models import Task, CalendarEvent, Note, User  # noqa: F401
    Base.metadata.create_all(bind=engine)
