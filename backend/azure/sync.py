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
from datetime import datetime, timedelta, timezone
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

    async def sync(self, full: bool = True, hours: Optional[int] = None) -> Dict:
        """Fetch work items and persist state.

        Args:
            full:  If True (default), clear existing cache and do a complete resync.
            hours: If set, only fetch items changed in the last N hours and merge
                   into the existing cache. Overrides `full`.
        """
        changed_after: Optional[datetime] = None
        existing: Dict = {}

        if hours is not None:
            # Windowed sync — merge into existing cache
            changed_after = datetime.now(timezone.utc) - timedelta(hours=hours)
            existing = _load_state().get("work_items", {})
            logger.info(f"Azure sync: windowed mode, last {hours}h (since {changed_after.isoformat()})")
        elif full:
            # Full sync — start fresh
            logger.info("Azure sync: full mode, clearing existing cache")
        else:
            # Incremental default: read window from env
            window_hours = int(os.getenv("AZURE_SYNC_WINDOW_HOURS", "0") or "0")
            if window_hours > 0:
                changed_after = datetime.now(timezone.utc) - timedelta(hours=window_hours)
                existing = _load_state().get("work_items", {})
                logger.info(f"Azure sync: env window {window_hours}h")
            else:
                logger.info("Azure sync: full mode (AZURE_SYNC_WINDOW_HOURS=0)")

        items = await self.client.get_my_work_items(
            max_results=200,
            changed_after=changed_after,
        )

        now = datetime.now(timezone.utc).isoformat()
        fetched_records = {
            str(wi.id): {
                "id": wi.id,
                "title": wi.title,
                "description": wi.description,
                "state": wi.state,
                "type": wi.work_item_type,
                "assigned_to": wi.assigned_to,
                "area_path": wi.area_path,
                "iteration_path": wi.iteration_path,
                "due_date": wi.due_date,
                "tags": wi.tags,
                "url": wi.url,
                "synced_at": now,
            }
            for wi in items
        }

        # Merge: fetched records overwrite existing ones
        merged = {**existing, **fetched_records}

        state = {
            "last_sync": now,
            "sync_mode": f"windowed:{hours}h" if hours else ("full" if not existing else f"windowed:{window_hours}h" if changed_after else "full"),
            "org": self.client._org,
            "project": self.client._project,
            "work_items": merged,
        }
        _save_state(state)
        logger.info(f"Azure sync complete: {len(items)} fetched, {len(merged)} total in cache")

        by_state: Dict[str, List[AzureWorkItem]] = {}
        for wi in items:
            by_state.setdefault(wi.state, []).append(wi)

        return {
            "total": len(merged),
            "fetched": len(items),
            "by_state": {s: len(v) for s, v in by_state.items()},
            "items": items,
            "last_sync": now,
            "state_file": str(_state_file()),
            "mode": state["sync_mode"],
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
