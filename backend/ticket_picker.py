#!/usr/bin/env python3
"""
ticket_picker.py — Interactive TUI for linking a commit to a PM ticket.

Called as a subprocess by devtrack-git-wrapper.sh after the user accepts an
AI-enhanced commit message.  All interactive output goes to stderr; the selected
ticket ID (or empty string) is written to the file given by --output.

Usage:
    python backend/ticket_picker.py \
        --repo-path /path/to/repo \
        --workspaces-file /path/to/workspaces.yaml \
        --commit-message "the current commit message" \
        --output /tmp/ticket_id.txt
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Any, List, NamedTuple, Optional

# ---------------------------------------------------------------------------
# Bootstrap: make sure project root is on sys.path
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load env before any backend imports
from backend.config import _load_env  # noqa: E402
_load_env()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TITLE_MAX = 44   # max chars before truncation with …
MAX_DISPLAY = 20 # max tickets to show without search


def _trunc(text: str, max_len: int = TITLE_MAX) -> str:
    return text if len(text) <= max_len else text[: max_len - 1] + "\u2026"


def _print(msg: str = "") -> None:
    """Print to stderr (all TUI output must go here)."""
    print(msg, file=sys.stderr)


def _input(prompt: str) -> str:
    """Read a line from stdin, printing the prompt to stderr."""
    sys.stderr.write(prompt)
    sys.stderr.flush()
    return sys.stdin.readline().rstrip("\n")


# ---------------------------------------------------------------------------
# Workspace lookup
# ---------------------------------------------------------------------------

class WorkspaceConfig(NamedTuple):
    pm_platform: str   # "azure" | "github" | "gitlab" | "jira" | "none"
    pm_project: str    # project identifier (may be empty)


def _find_workspace(repo_path: str, workspaces_file: str) -> Optional[WorkspaceConfig]:
    """Return WorkspaceConfig for *repo_path* or None if not found."""
    ws_path = Path(workspaces_file)
    if not ws_path.exists():
        return None

    try:
        import yaml  # type: ignore
    except ImportError:
        _print("  [ticket_picker] PyYAML not installed — skipping ticket link")
        return None

    with ws_path.open() as fh:
        data = yaml.safe_load(fh) or {}

    canonical_repo = os.path.realpath(repo_path)
    for ws in data.get("workspaces", []):
        ws_path_val = ws.get("path", "")
        if os.path.realpath(ws_path_val) == canonical_repo:
            return WorkspaceConfig(
                pm_platform=(ws.get("pm_platform") or "").lower(),
                pm_project=ws.get("pm_project") or "",
            )
    return None


# ---------------------------------------------------------------------------
# Unified ticket model
# ---------------------------------------------------------------------------

class Ticket(NamedTuple):
    display_id: str   # "#123" — what we write to the output file
    title: str
    status: str


# ---------------------------------------------------------------------------
# Platform adapters
# ---------------------------------------------------------------------------

async def _fetch_azure(search: Optional[str] = None) -> List[Ticket]:
    from backend.azure.client import AzureDevOpsClient  # type: ignore
    client = AzureDevOpsClient()
    if not client.is_configured():
        _print("  [azure] Client not configured — check AZURE_ORGANIZATION / AZURE_DEVOPS_PAT")
        return []
    try:
        if search:
            items = await client.search_work_items(search, max_results=MAX_DISPLAY)
        else:
            items = await client.get_my_work_items(
                states=["New", "Active", "In Progress", "Committed", "Doing"],
                max_results=MAX_DISPLAY,
            )
        return [Ticket(f"#{i.id}", i.title, i.state) for i in items]
    finally:
        await client.close()


async def _create_azure(title: str) -> Optional[Ticket]:
    from backend.azure.client import AzureDevOpsClient  # type: ignore
    client = AzureDevOpsClient()
    if not client.is_configured():
        return None
    try:
        item = await client.create_work_item(title=title)
        if item:
            return Ticket(f"#{item.id}", item.title, item.state)
        return None
    finally:
        await client.close()


async def _fetch_github(search: Optional[str] = None) -> List[Ticket]:
    from backend.github.client import GitHubClient  # type: ignore
    client = GitHubClient()
    if not client.is_configured():
        _print("  [github] Client not configured — check GITHUB_TOKEN / GITHUB_OWNER / GITHUB_REPO")
        return []
    try:
        if search:
            items = await client.search_issues(search, max_results=MAX_DISPLAY)
        else:
            items = await client.get_my_issues(state="open")
        return [Ticket(f"#{i.number}", i.title, i.state) for i in items]
    finally:
        await client.close()


async def _create_github(title: str, commit_message: str = "") -> Optional[Ticket]:
    from backend.github.client import GitHubClient  # type: ignore
    client = GitHubClient()
    if not client.is_configured():
        return None
    try:
        issue = await client.create_issue(title=title, body=commit_message)
        if issue:
            return Ticket(f"#{issue.number}", issue.title, issue.state)
        return None
    finally:
        await client.close()


async def _fetch_gitlab(search: Optional[str] = None) -> List[Ticket]:
    from backend.gitlab.client import GitLabClient  # type: ignore
    client = GitLabClient()
    if not client.is_configured():
        _print("  [gitlab] Client not configured — check GITLAB_PAT")
        return []
    try:
        if search:
            items = await client.search_issues(search, max_results=MAX_DISPLAY)
        else:
            items = await client.get_my_issues(state="opened")
        return [Ticket(f"#{i.iid}", i.title, i.state) for i in items]
    finally:
        await client.close()


async def _create_gitlab(title: str) -> Optional[Ticket]:
    from backend.gitlab.client import GitLabClient  # type: ignore
    client = GitLabClient()
    if not client.is_configured():
        return None
    try:
        issue = await client.create_issue(title=title)
        if issue:
            return Ticket(f"#{issue.iid}", issue.title, issue.state)
        return None
    finally:
        await client.close()


# ---------------------------------------------------------------------------
# Dispatch helpers
# ---------------------------------------------------------------------------

async def _fetch(platform: str, search: Optional[str] = None) -> List[Ticket]:
    if platform == "azure":
        return await _fetch_azure(search)
    elif platform == "github":
        return await _fetch_github(search)
    elif platform == "gitlab":
        return await _fetch_gitlab(search)
    return []


async def _create(platform: str, title: str, commit_message: str = "") -> Optional[Ticket]:
    if platform == "azure":
        return await _create_azure(title)
    elif platform == "github":
        return await _create_github(title, commit_message)
    elif platform == "gitlab":
        return await _create_gitlab(title)
    return None


# ---------------------------------------------------------------------------
# TUI rendering
# ---------------------------------------------------------------------------

SEP = "\u2500" * 62   # ──────────

def _render_list(tickets: List[Ticket], platform: str, search: Optional[str] = None) -> None:
    _print(f"\n  {'#':<3}  {'ID':<8}  {'Title':<{TITLE_MAX}}  Status")
    _print(f"  {'\u2500'*3}  {'\u2500'*8}  {'\u2500'*TITLE_MAX}  {'\u2500'*10}")
    for idx, t in enumerate(tickets[:MAX_DISPLAY], start=1):
        _print(f"  {idx:<3}  {t.display_id:<8}  {_trunc(t.title):<{TITLE_MAX}}  {t.status}")
    overflow = len(tickets) - MAX_DISPLAY
    if overflow > 0:
        _print(f"\n  \u2026 and {overflow} more. Use /search to filter.")
    _print()


def _render_header(platform: str, pm_project: str) -> None:
    _print(SEP)
    _print(f"\U0001f3ab  Link commit to a ticket  ({platform} \u00b7 {pm_project or 'default'})")
    _print(SEP)


def _render_prompt(search: Optional[str] = None) -> str:
    if search:
        return "[number] select  [/] clear search  [n] new issue  Enter skip\n> "
    return "[number] select  [/text] search  [n] new issue  Enter skip\n> "


# ---------------------------------------------------------------------------
# Main interactive loop
# ---------------------------------------------------------------------------

def _run_tui(platform: str, pm_project: str, commit_message: str) -> str:
    """
    Runs the interactive ticket picker TUI.
    Returns the selected ticket ID string (e.g. "#123") or "" for skip.
    """
    _render_header(platform, pm_project)

    _SENTINEL = object()
    search: Optional[str] = None
    prev_search: Any = _SENTINEL   # tracks last fetched search to avoid redundant API calls
    tickets: List[Ticket] = []

    while True:
        # ---- (re)fetch tickets when search term changes ----
        # prev_search starts as a sentinel object so the first iteration always fetches
        if prev_search is _SENTINEL or search != prev_search:
            prev_search = search
            _print("Fetching tickets\u2026")
            try:
                tickets = asyncio.run(_fetch(platform, search))
            except Exception as exc:
                _print(f"  [error] Could not fetch tickets: {exc}")
                tickets = []

        # ---- render list ----
        if search:
            _print(f'\n  Search: "{search}"')

        if not tickets:
            if search:
                _print("  No tickets matched your search.")
            else:
                _print("  No assigned tickets found.")

        if tickets:
            _render_list(tickets, platform, search)

        # ---- read input ----
        raw = _input(_render_prompt(search))

        # Enter = skip
        if raw == "":
            return ""

        # /text = search (or / alone = clear)
        if raw.startswith("/"):
            term = raw[1:].strip()
            search = term if term else None
            continue

        # n = new issue
        if raw.strip().lower() == "n":
            default_title = commit_message.splitlines()[0] if commit_message else ""
            new_title_prompt = f"  New issue title (Enter to use commit message):\n  > "
            raw_title = _input(new_title_prompt)
            title = raw_title.strip() or default_title or "Untitled"
            _print("  Creating issue\u2026")
            try:
                created = asyncio.run(_create(platform, title, commit_message))
            except Exception as exc:
                _print(f"  [error] Could not create issue: {exc}")
                return ""
            if created:
                _print(f"  \u2713 Created {created.display_id}: {_trunc(created.title)}")
                return created.display_id
            else:
                _print("  [error] Issue creation failed — skipping ticket link")
                return ""

        # numeric = select from list
        try:
            idx = int(raw.strip())
        except ValueError:
            _print("  Invalid input. Enter a number, /search, n, or press Enter to skip.")
            continue

        if 1 <= idx <= len(tickets[:MAX_DISPLAY]):
            selected = tickets[idx - 1]
            _print(f"  \u2713 Selected {selected.display_id}: {_trunc(selected.title)}")
            return selected.display_id
        else:
            _print(f"  Number out of range (1\u2013{min(len(tickets), MAX_DISPLAY)}).")
            continue


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive ticket picker for devtrack git commit")
    parser.add_argument("--repo-path", required=True)
    parser.add_argument("--workspaces-file", required=True)
    parser.add_argument("--commit-message", default="")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    output_path = Path(args.output)

    def _write(ticket_id: str) -> None:
        output_path.write_text(ticket_id)

    # ---- workspace lookup ----
    ws = _find_workspace(args.repo_path, args.workspaces_file)
    if ws is None:
        _print(f"\u2139\ufe0f  Repo not tracked in workspaces.yaml \u2014 skipping ticket link")
        _write("")
        return

    platform = ws.pm_platform
    if not platform or platform == "none":
        _write("")
        return

    if platform == "jira":
        _print("\u2139\ufe0f  Jira ticket linking not yet supported")
        _write("")
        return

    if platform not in ("azure", "github", "gitlab"):
        _print(f"\u2139\ufe0f  Unknown PM platform '{platform}' \u2014 skipping ticket link")
        _write("")
        return

    # ---- run TUI ----
    try:
        ticket_id = _run_tui(platform, ws.pm_project, args.commit_message)
        _write(ticket_id)
    except KeyboardInterrupt:
        _print("\n  Skipping ticket link.")
        _write("")
    except Exception as exc:
        _print(f"\n  [ticket_picker] Unexpected error: {exc} \u2014 skipping ticket link")
        _write("")


if __name__ == "__main__":
    main()
