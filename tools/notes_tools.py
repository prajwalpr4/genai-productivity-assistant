"""
Notes Management Tools
======================
CRUD + search operations on the Notes table, exposed as LangChain
tools so that the Notes Agent can call them via function-calling.
"""

from langchain_core.tools import tool
from database.db import SessionLocal
from database.models import Note
from tools.mcp_registry import registry


@tool
def save_note(title: str, content: str, tags: str = "") -> str:
    """Save a new note. Tags is a comma-separated string of keywords for organization."""
    db = SessionLocal()
    try:
        note = Note(title=title, content=content, tags=tags)
        db.add(note)
        db.commit()
        db.refresh(note)
        return (
            f"📝 Note saved successfully!\n"
            f"  ID: {note.id}\n"
            f"  Title: {note.title}\n"
            f"  Tags: {note.tags or 'None'}"
        )
    except Exception as e:
        db.rollback()
        return f"❌ Failed to save note: {e}"
    finally:
        db.close()


@tool
def search_notes(query: str) -> str:
    """Search notes by keyword. Searches in title, content, and tags."""
    db = SessionLocal()
    try:
        results = (
            db.query(Note)
            .filter(
                (Note.title.ilike(f"%{query}%"))
                | (Note.content.ilike(f"%{query}%"))
                | (Note.tags.ilike(f"%{query}%"))
            )
            .order_by(Note.updated_at.desc())
            .all()
        )
        if not results:
            return f"🔍 No notes found matching '{query}'."
        lines = [f"🔍 Found {len(results)} note(s) matching '{query}':"]
        for n in results:
            preview = (n.content[:80] + "...") if len(n.content) > 80 else n.content
            lines.append(
                f"  📝 [{n.id}] {n.title}\n"
                f"      {preview}\n"
                f"      Tags: {n.tags or 'None'}"
            )
        return "\n".join(lines)
    finally:
        db.close()


@tool
def get_note(note_id: int) -> str:
    """Get the full content of a specific note by its ID."""
    db = SessionLocal()
    try:
        note = db.query(Note).filter(Note.id == note_id).first()
        if not note:
            return f"❌ Note with ID {note_id} not found."
        return (
            f"📝 Note Details:\n"
            f"  ID: {note.id}\n"
            f"  Title: {note.title}\n"
            f"  Content: {note.content}\n"
            f"  Tags: {note.tags or 'None'}\n"
            f"  Created: {note.created_at}\n"
            f"  Updated: {note.updated_at}"
        )
    finally:
        db.close()


@tool
def delete_note(note_id: int) -> str:
    """Delete a note by its ID."""
    db = SessionLocal()
    try:
        note = db.query(Note).filter(Note.id == note_id).first()
        if not note:
            return f"❌ Note with ID {note_id} not found."
        title = note.title
        db.delete(note)
        db.commit()
        return f"🗑️ Note '{title}' (ID {note_id}) deleted successfully."
    except Exception as e:
        db.rollback()
        return f"❌ Failed to delete note: {e}"
    finally:
        db.close()


@tool
def list_all_notes() -> str:
    """List all saved notes with their titles and tags."""
    db = SessionLocal()
    try:
        notes = db.query(Note).order_by(Note.updated_at.desc()).all()
        if not notes:
            return "📝 No notes saved yet."
        lines = [f"📝 All Notes ({len(notes)} total):"]
        for n in notes:
            preview = (n.content[:60] + "...") if len(n.content) > 60 else n.content
            lines.append(f"  📝 [{n.id}] {n.title} — {preview}  (Tags: {n.tags or 'None'})")
        return "\n".join(lines)
    finally:
        db.close()


# ── Exported list & MCP registration ───────────────────────────────

notes_tools = [save_note, search_notes, get_note, delete_note, list_all_notes]
registry.register_many(notes_tools, domain="notes")
