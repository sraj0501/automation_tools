"""
Task Manager API — Demo Project for DevTrack
A simple in-memory REST-style task manager.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from database import TaskDatabase
from models import Task
from utils import ValidationError, validate_task_input

db = TaskDatabase()


# ---------------------------------------------------------------------------
# API handlers (framework-agnostic — call these from your HTTP layer)
# ---------------------------------------------------------------------------

def create_task(body: Dict[str, Any]) -> Dict[str, Any]:
    """POST /tasks — create a new task."""
    try:
        cleaned = validate_task_input(
            title=body.get("title", ""),
            priority=body.get("priority", "medium"),
            due_date=body.get("due_date"),
        )
    except ValidationError as e:
        return {"error": str(e)}, 400

    task = Task(
        id=str(uuid.uuid4()),
        title=cleaned["title"],
        priority=cleaned["priority"],
        due_date=cleaned.get("due_date"),
        created_at=datetime.utcnow().isoformat(),
    )
    db.save(task)
    return task.to_dict(), 201


def get_task(task_id: str) -> Dict[str, Any]:
    """GET /tasks/{id} — fetch a single task."""
    task = db.find(task_id)
    if not task:
        return {"error": "Task not found"}, 404
    return task.to_dict(), 200


def list_tasks(priority: Optional[str] = None, completed: Optional[bool] = None) -> Dict[str, Any]:
    """GET /tasks — list tasks with optional filters."""
    tasks = db.all()
    if priority:
        tasks = [t for t in tasks if t.priority == priority]
    if completed is not None:
        tasks = [t for t in tasks if t.completed == completed]
    return {"tasks": [t.to_dict() for t in tasks], "count": len(tasks)}, 200


def complete_task(task_id: str) -> Dict[str, Any]:
    """PATCH /tasks/{id}/complete — mark a task as done."""
    task = db.find(task_id)
    if not task:
        return {"error": "Task not found"}, 404
    task.completed = True
    task.completed_at = datetime.utcnow().isoformat()
    db.save(task)
    return task.to_dict(), 200


def delete_task(task_id: str) -> Dict[str, Any]:
    """DELETE /tasks/{id} — remove a task."""
    if not db.delete(task_id):
        return {"error": "Task not found"}, 404
    return {}, 204
