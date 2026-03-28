#!/usr/bin/env python3
"""
Pre-populate MongoDB with demo notifications for the DevTrack demo.
Run this from the automation_tools root:
    uv run python demo/inject_alerts.py
"""

import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

_env = Path(__file__).parent.parent / ".env"
if _env.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env)
    except ImportError:
        pass

GITHUB_OWNER = os.getenv("GITHUB_OWNER", "sraj0501")
AZURE_ORG    = os.getenv("AZURE_ORGANIZATION", "MyOrg")

NOW = datetime.now(tz=timezone.utc)

DEMO_ALERTS = [
    # ── GitHub ────────────────────────────────────────────────────────────
    {
        "source": "github",
        "event_type": "assigned",
        "ticket_id": f"{GITHUB_OWNER}/devtrack-demo#3",
        "title": "Improve API error handling and response format",
        "summary": f"You were assigned to Issue #3",
        "url": f"https://github.com/{GITHUB_OWNER}/devtrack-demo/issues/3",
        "timestamp": NOW - timedelta(minutes=45),
        "read": False,
        "dismissed": False,
        "raw": {"number": 3, "state": "open"},
    },
    {
        "source": "github",
        "event_type": "comment",
        "ticket_id": f"{GITHUB_OWNER}/devtrack-demo#1",
        "title": "Add user authentication to the API",
        "summary": "alice: Can we use JWT tokens? The current session approach won't scale horizontally.",
        "url": f"https://github.com/{GITHUB_OWNER}/devtrack-demo/issues/1",
        "timestamp": NOW - timedelta(minutes=12),
        "read": False,
        "dismissed": False,
        "raw": {"comment_id": 10001, "commenter": "alice", "number": 1},
    },
    {
        "source": "github",
        "event_type": "review_requested",
        "ticket_id": f"{GITHUB_OWNER}/devtrack-demo#7",
        "title": "feat: add rate limiting to task endpoints",
        "summary": "Review requested by bob",
        "url": f"https://github.com/{GITHUB_OWNER}/devtrack-demo/pulls/7",
        "timestamp": NOW - timedelta(minutes=8),
        "read": False,
        "dismissed": False,
        "raw": {"number": 7, "author": "bob"},
    },
    # ── Azure DevOps ──────────────────────────────────────────────────────
    {
        "source": "azure",
        "event_type": "assigned",
        "ticket_id": f"{AZURE_ORG}#2401",
        "title": "Implement OAuth2 integration for Task API",
        "summary": "Assigned to you",
        "url": f"https://dev.azure.com/{AZURE_ORG}/_workitems/edit/2401",
        "timestamp": NOW - timedelta(hours=2),
        "read": False,
        "dismissed": False,
        "raw": {"work_item_id": 2401, "state": "Active"},
    },
    {
        "source": "azure",
        "event_type": "comment",
        "ticket_id": f"{AZURE_ORG}#2398",
        "title": "Fix task deletion not cascading to subtasks",
        "summary": "charlie: Reproduced on staging — happens when parent has >5 children.",
        "url": f"https://dev.azure.com/{AZURE_ORG}/_workitems/edit/2398",
        "timestamp": NOW - timedelta(minutes=30),
        "read": False,
        "dismissed": False,
        "raw": {"work_item_id": 2398, "comment_id": 88, "author": "charlie"},
    },
    {
        "source": "azure",
        "event_type": "status_change",
        "ticket_id": f"{AZURE_ORG}#2395",
        "title": "Add pagination to task list endpoint",
        "summary": "State: Active → Resolved (by david)",
        "url": f"https://dev.azure.com/{AZURE_ORG}/_workitems/edit/2395",
        "timestamp": NOW - timedelta(minutes=55),
        "read": False,
        "dismissed": False,
        "raw": {
            "work_item_id": 2395,
            "old_state": "Active",
            "new_state": "Resolved",
            "changed_by": "david",
        },
    },
]


async def main() -> None:
    from backend.db.mongo_alerts import get_store

    store = get_store()
    if not store.is_available():
        print("⚠  MongoDB not available — skipping alert injection.")
        print("   Alerts section of the demo won't show pre-seeded data.")
        print("   Start MongoDB with: docker compose up -d")
        return

    await store.ensure_indexes()
    count = 0
    for alert in DEMO_ALERTS:
        inserted = await store.insert_notification(alert)
        if inserted:
            count += 1

    print(f"✓  Injected {count}/{len(DEMO_ALERTS)} demo notifications into MongoDB.")


if __name__ == "__main__":
    asyncio.run(main())
