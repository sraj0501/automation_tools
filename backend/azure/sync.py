"""
Azure DevOps sync utilities.

Provides a simple sync layer that fetches work items from Azure DevOps
and reports status. State is stored in Data/azure/sync_state.json for
offline reference and audit trail.

No dependency on ProjectManager — designed to work standalone.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from backend.azure.client import AzureDevOpsClient, AzureWorkItem

logger = logging.getLogger(__name__)


def _state_file() -> Path:
    """Return path to local sync state file."""
    data_dir = os.getenv("DATA_DIR", "Data")
    path = Path(data_dir) / "azure" / "sync_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _load_state() -> Dict:
    f = _state_file()
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return {"last_sync": None, "work_items": {}}


def _save_state(state: Dict) -> None:
    _state_file().write_text(json.dumps(state, indent=2, default=str))


# ---------------------------------------------------------------------------
# AzureSync — simple fetch + report, no ProjectManager dependency
# ---------------------------------------------------------------------------

class AzureSync:
    """Fetch Azure DevOps work items and maintain a local sync state."""

    def __init__(self, client: Optional[AzureDevOpsClient] = None) -> None:
        self.client = client or AzureDevOpsClient()

    # -- public API ---------------------------------------------------------

    async def sync(self) -> Dict:
        """Fetch all work items, persist state, return summary dict."""
        items = await self.client.get_my_work_items(max_results=200)

        by_state: Dict[str, List[AzureWorkItem]] = {}
        for wi in items:
            by_state.setdefault(wi.state, []).append(wi)

        state = {
            "last_sync": datetime.now(timezone.utc).isoformat(),
            "org": self.client._org,
            "project": self.client._project,
            "work_items": {
                str(wi.id): {
                    "id": wi.id,
                    "title": wi.title,
                    "state": wi.state,
                    "type": wi.work_item_type,
                    "assigned_to": wi.assigned_to,
                    "area_path": wi.area_path,
                    "iteration_path": wi.iteration_path,
                    "tags": wi.tags,
                    "url": wi.url,
                    "synced_at": datetime.now(timezone.utc).isoformat(),
                }
                for wi in items
            },
        }
        _save_state(state)
        logger.info(f"Azure sync complete: {len(items)} work items saved to {_state_file()}")

        return {
            "total": len(items),
            "by_state": {s: len(v) for s, v in by_state.items()},
            "items": items,
            "last_sync": state["last_sync"],
            "state_file": str(_state_file()),
        }

    async def get_work_item(self, item_id: int) -> Optional[AzureWorkItem]:
        """Fetch a single work item by ID."""
        return await self.client.get_work_item(item_id)

    async def add_comment(self, item_id: int, comment: str) -> bool:
        return await self.client.add_comment(item_id, comment)

    async def update_state(self, item_id: int, new_state: str) -> bool:
        return await self.client.update_work_item_state(item_id, new_state)

    def get_cached(self) -> Dict:
        """Return locally cached state without hitting the API."""
        return _load_state()
