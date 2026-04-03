"""
Task Management Tools
=====================
CRUD operations on the Tasks table, exposed as LangChain tools
so that the Task Agent can call them via function-calling.
"""

from langchain_core.tools import tool
from database.db import SessionLocal
from database.models import Task
from tools.mcp_registry import registry


# ── Tool definitions ────────────────────────────────────────────────

@tool
def create_task(title: str, description: str = "", priority: str = "medium", due_date: str = "") -> str:
    """Create a new task. Priority can be low, medium, or high. Due date is in YYYY-MM-DD format."""
    db = SessionLocal()
    try:
        task = Task(
            title=title,
            description=description,
            priority=priority.lower(),
            due_date=due_date,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return (
            f"✅ Task created successfully!\n"
            f"  ID: {task.id}\n"
            f"  Title: {task.title}\n"
            f"  Priority: {task.priority}\n"
            f"  Due: {task.due_date or 'Not set'}\n"
            f"  Status: {task.status}"
        )
    except Exception as e:
        db.rollback()
        return f"❌ Failed to create task: {e}"
    finally:
        db.close()


@tool
def list_tasks(status_filter: str = "") -> str:
    """List all tasks. Optionally filter by status: todo, in_progress, or done. Pass empty string for all tasks."""
    db = SessionLocal()
    try:
        query = db.query(Task)
        if status_filter and status_filter.strip():
            query = query.filter(Task.status == status_filter.strip().lower())
        tasks = query.order_by(Task.created_at.desc()).all()
        if not tasks:
            return "📋 No tasks found."
        lines = [f"📋 Tasks ({len(tasks)} total):"]
        for t in tasks:
            emoji = {"todo": "⬜", "in_progress": "🔶", "done": "✅"}.get(t.status, "⬜")
            lines.append(
                f"  {emoji} [{t.id}] {t.title} | Priority: {t.priority} | "
                f"Due: {t.due_date or 'N/A'} | Status: {t.status}"
            )
        return "\n".join(lines)
    finally:
        db.close()


@tool
def update_task_status(task_id: int, new_status: str) -> str:
    """Update a task's status. Valid statuses: todo, in_progress, done."""
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return f"❌ Task with ID {task_id} not found."
        old_status = task.status
        task.status = new_status.strip().lower()
        db.commit()
        return f"✅ Task '{task.title}' status changed: {old_status} → {task.status}"
    except Exception as e:
        db.rollback()
        return f"❌ Failed to update task: {e}"
    finally:
        db.close()


@tool
def get_task(task_id: int) -> str:
    """Get full details of a specific task by its ID."""
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return f"❌ Task with ID {task_id} not found."
        return (
            f"📌 Task Details:\n"
            f"  ID: {task.id}\n"
            f"  Title: {task.title}\n"
            f"  Description: {task.description or 'No description'}\n"
            f"  Status: {task.status}\n"
            f"  Priority: {task.priority}\n"
            f"  Due Date: {task.due_date or 'Not set'}\n"
            f"  Created: {task.created_at}"
        )
    finally:
        db.close()


@tool
def delete_task(task_id: int) -> str:
    """Delete a task by its ID."""
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return f"❌ Task with ID {task_id} not found."
        title = task.title
        db.delete(task)
        db.commit()
        return f"🗑️ Task '{title}' (ID {task_id}) deleted successfully."
    except Exception as e:
        db.rollback()
        return f"❌ Failed to delete task: {e}"
    finally:
        db.close()


# ── Exported list & MCP registration ───────────────────────────────

task_tools = [create_task, list_tasks, update_task_status, get_task, delete_task]
registry.register_many(task_tools, domain="tasks")
