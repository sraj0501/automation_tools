"""Data models for the Task Manager API."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional


@dataclass
class Task:
    id: str
    title: str
    priority: str = "medium"       # low | medium | high
    completed: bool = False
    due_date: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    tags: list = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
