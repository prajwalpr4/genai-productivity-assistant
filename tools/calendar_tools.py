"""
Calendar Management Tools
=========================
CRUD operations on the CalendarEvents table, exposed as LangChain
tools so that the Calendar Agent can invoke them via function-calling.
"""

from langchain_core.tools import tool
from database.db import SessionLocal
from database.models import CalendarEvent
from tools.mcp_registry import registry


@tool
def add_event(title: str, start_time: str, end_time: str, description: str = "", location: str = "") -> str:
    """Add a new calendar event. Times should be in 'YYYY-MM-DD HH:MM' format."""
    db = SessionLocal()
    try:
        event = CalendarEvent(
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            location=location,
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return (
            f"📅 Event created successfully!\n"
            f"  ID: {event.id}\n"
            f"  Title: {event.title}\n"
            f"  Start: {event.start_time}\n"
            f"  End: {event.end_time}\n"
            f"  Location: {event.location or 'Not specified'}"
        )
    except Exception as e:
        db.rollback()
        return f"❌ Failed to create event: {e}"
    finally:
        db.close()


@tool
def list_events(date_filter: str = "") -> str:
    """List calendar events. Optionally filter by date (YYYY-MM-DD). Pass empty string for all events."""
    db = SessionLocal()
    try:
        query = db.query(CalendarEvent)
        if date_filter and date_filter.strip():
            query = query.filter(CalendarEvent.start_time.like(f"{date_filter.strip()}%"))
        events = query.order_by(CalendarEvent.start_time).all()
        if not events:
            return "📅 No events found."
        lines = [f"📅 Events ({len(events)} total):"]
        for e in events:
            lines.append(
                f"  🔹 [{e.id}] {e.title}\n"
                f"      {e.start_time} → {e.end_time}"
                f"{f'  📍 {e.location}' if e.location else ''}"
            )
        return "\n".join(lines)
    finally:
        db.close()


@tool
def get_event(event_id: int) -> str:
    """Get full details of a specific calendar event by its ID."""
    db = SessionLocal()
    try:
        event = db.query(CalendarEvent).filter(CalendarEvent.id == event_id).first()
        if not event:
            return f"❌ Event with ID {event_id} not found."
        return (
            f"📅 Event Details:\n"
            f"  ID: {event.id}\n"
            f"  Title: {event.title}\n"
            f"  Description: {event.description or 'No description'}\n"
            f"  Start: {event.start_time}\n"
            f"  End: {event.end_time}\n"
            f"  Location: {event.location or 'Not specified'}\n"
            f"  Created: {event.created_at}"
        )
    finally:
        db.close()


@tool
def delete_event(event_id: int) -> str:
    """Delete a calendar event by its ID."""
    db = SessionLocal()
    try:
        event = db.query(CalendarEvent).filter(CalendarEvent.id == event_id).first()
        if not event:
            return f"❌ Event with ID {event_id} not found."
        title = event.title
        db.delete(event)
        db.commit()
        return f"🗑️ Event '{title}' (ID {event_id}) deleted successfully."
    except Exception as e:
        db.rollback()
        return f"❌ Failed to delete event: {e}"
    finally:
        db.close()


@tool
def check_availability(date: str) -> str:
    """Check calendar availability for a given date (YYYY-MM-DD). Shows free and busy slots."""
    db = SessionLocal()
    try:
        events = (
            db.query(CalendarEvent)
            .filter(CalendarEvent.start_time.like(f"{date}%"))
            .order_by(CalendarEvent.start_time)
            .all()
        )
        if not events:
            return f"✅ You are completely free on {date}. No events scheduled."

        lines = [f"📅 Schedule for {date}:"]
        for e in events:
            lines.append(f"  🔴 BUSY: {e.start_time} → {e.end_time} — {e.title}")
        lines.append(f"\n  You have {len(events)} event(s) on this date. Other slots are free.")
        return "\n".join(lines)
    finally:
        db.close()


# ── Exported list & MCP registration ───────────────────────────────

calendar_tools = [add_event, list_events, get_event, delete_event, check_availability]
registry.register_many(calendar_tools, domain="calendar")
