"""
devtrack azure-sync — fetch all Azure DevOps work items and report status.

Persists a local snapshot to Data/azure/sync_state.json.

Run via:
    devtrack azure-sync
    uv run python backend/azure/run_sync.py
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def _load_env() -> None:
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / ".env").exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(parent / ".env", override=True)
            except ImportError:
                pass
            return


_load_env()


async def run() -> int:
    from backend.azure.client import AzureDevOpsClient
    from backend.azure.sync import AzureSync

    client = AzureDevOpsClient()
    if not client.is_configured():
        print("ERROR: Azure DevOps not configured. Run 'devtrack azure-check'.")
        return 1

    print(f"Azure DevOps Sync  [{client._org}/{client._project}]")
    print("=" * 50)
    print()

    sync = AzureSync(client=client)

    print("Fetching work items...", flush=True)
    try:
        result = await sync.sync()

        total = result["total"]
        by_state = result["by_state"]
        items = result["items"]

        if total == 0:
            print("No work items assigned to you.")
            print()
            sync_states = os.getenv("AZURE_SYNC_STATES", "New,Active,In Progress")
            print(f"States checked: {sync_states}")
            print("Set AZURE_SYNC_STATES in .env to change which states are fetched.")
            return 0

        # Summary by state
        print(f"Work Items: {total} total")
        print("-" * 50)
        for state, count in sorted(by_state.items()):
            bar = "█" * min(count, 30)
            print(f"  {state:<20} {count:>3}  {bar}")
        print()

        # Recent items (up to 10)
        print(f"Items (newest {min(total, 10)}):")
        print("-" * 50)
        for wi in items[:10]:
            tags = f"  [{', '.join(wi.tags)}]" if wi.tags else ""
            print(f"  #{wi.id:<6} {wi.state:<15} {wi.work_item_type:<12} {wi.title[:45]}{tags}")
        if total > 10:
            print(f"  ... and {total - 10} more")
        print()

        print(f"Saved to: {result['state_file']}")
        print(f"Synced at: {result['last_sync']}")
        return 0

    except Exception as e:
        print(f"ERROR: {e}")
        return 1

    finally:
        await client.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
