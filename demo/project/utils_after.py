"""Input validation utilities for the Task Manager API."""

from datetime import date
from typing import Optional


class ValidationError(Exception):
    pass


def validate_task_input(title: str, priority: str, due_date: Optional[str] = None) -> dict:
    """
    Validate and normalise task input fields.

    Returns a dict of cleaned values ready for the Task model.
    Raises ValidationError with a descriptive message on failure.
    """
    if not title or not title.strip():
        raise ValidationError("Title cannot be empty")
    if len(title) > 200:
        raise ValidationError("Title must be 200 characters or fewer")

    priority = priority.lower().strip()
    if priority not in ("low", "medium", "high"):
        raise ValidationError(f"Priority must be low, medium, or high — got '{priority}'")

    cleaned: dict = {"title": title.strip(), "priority": priority}

    if due_date:
        try:
            parsed = date.fromisoformat(due_date)
        except ValueError:
            raise ValidationError(f"due_date must be ISO 8601 (YYYY-MM-DD) — got '{due_date}'")
        if parsed < date.today():
            raise ValidationError(f"due_date cannot be in the past — got '{due_date}'")
        cleaned["due_date"] = due_date

    return cleaned


def format_task_for_display(task: dict) -> str:
    """Format a task dict into a human-readable string."""
    status = "✓" if task.get("completed") else "○"
    priority_icons = {"low": "▽", "medium": "△", "high": "▲"}
    icon = priority_icons.get(task.get("priority", "medium"), "△")
    return f"[{status}] {icon} {task['title']}"
