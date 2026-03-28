"""In-memory task database with optional JSON persistence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from models import Task

_DATA_FILE = Path(__file__).parent / ".tasks.json"


class TaskDatabase:
    def __init__(self) -> None:
        self._store: Dict[str, Task] = {}
        self._load()

    def save(self, task: Task) -> None:
        self._store[task.id] = task
        self._persist()

    def find(self, task_id: str) -> Optional[Task]:
        return self._store.get(task_id)

    def all(self) -> List[Task]:
        return list(self._store.values())

    def delete(self, task_id: str) -> bool:
        if task_id not in self._store:
            return False
        del self._store[task_id]
        self._persist()
        return True

    def _persist(self) -> None:
        try:
            _DATA_FILE.write_text(
                json.dumps({k: v.to_dict() for k, v in self._store.items()}, indent=2)
            )
        except Exception:
            pass

    def _load(self) -> None:
        if _DATA_FILE.exists():
            try:
                data = json.loads(_DATA_FILE.read_text())
                self._store = {k: Task.from_dict(v) for k, v in data.items()}
            except Exception:
                self._store = {}
