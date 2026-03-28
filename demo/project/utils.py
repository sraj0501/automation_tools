"""Input validation utilities for the Task Manager API."""

from datetime import date
from typing import Optional


class ValidationError(Exception):
    pass


def validate_task_input(title: str, priority: str, due_date: Optional[str] = None) -> dict:
    """
    Validate and normalise task input fields.

    TODO: implement validation logic
      - title must be non-empty and <= 200 chars
      - priority must be one of: low, medium, high
      - due_date, if provided, must be ISO 8601 (YYYY-MM-DD) and not in the past
    """
    pass  # TODO: implement


def format_task_for_display(task: dict) -> str:
    """Format a task dict into a human-readable string."""
    status = "✓" if task.get("completed") else "○"
    priority_icons = {"low": "▽", "medium": "△", "high": "▲"}
    icon = priority_icons.get(task.get("priority", "medium"), "△")
    return f"[{status}] {icon} {task['title']}"
