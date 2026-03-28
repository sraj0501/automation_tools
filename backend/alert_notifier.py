"""
Alert notifier for DevTrack.

Delivers notifications via:
  - macOS OS notification: osascript
  - Terminal: formatted print to stdout

Respects ALERT_NOTIFY_* env vars from backend.config.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys
from datetime import datetime
from typing import Any, Dict, Optional

import backend.config as cfg

logger = logging.getLogger(__name__)


def _should_notify(event_type: str) -> bool:
    """Return True if this event_type is enabled via config."""
    event_type = event_type.lower()
    if event_type == "assigned":
        return cfg.get_bool("ALERT_NOTIFY_ASSIGNED", True)
    if event_type == "comment":
        return cfg.get_bool("ALERT_NOTIFY_COMMENTS", True)
    if event_type in ("status_change", "status-change"):
        return cfg.get_bool("ALERT_NOTIFY_STATUS_CHANGES", True)
    if event_type in ("review_requested", "review-requested"):
        return cfg.get_bool("ALERT_NOTIFY_REVIEW_REQUESTED", True)
    # Default: allow unknown types through
    return True


def _os_notify(title: str, subtitle: str, message: str) -> bool:
    """
    Send a macOS notification via osascript.

    Returns True on success, False if osascript not available or failed.
    """
    if not shutil.which("osascript"):
        return False
    script = (
        f'display notification {_osa_quote(message)} '
        f'with title {_osa_quote(title)} '
        f'subtitle {_osa_quote(subtitle)}'
    )
    try:
        subprocess.run(
            ["osascript", "-e", script],
            check=True,
            capture_output=True,
            timeout=5,
        )
        return True
    except Exception as e:
        logger.debug(f"osascript notification failed: {e}")
        return False


def _osa_quote(text: str) -> str:
    """Wrap a string in AppleScript double-quotes, escaping backslash and quote."""
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _terminal_notify(notification: Dict[str, Any]) -> None:
    """Print a formatted notification to stdout."""
    source = notification.get("source", "").upper()
    event_type = notification.get("event_type", "")
    title = notification.get("title", "")
    summary = notification.get("summary", "")
    url = notification.get("url", "")
    ts = notification.get("timestamp")

    ts_str = ""
    if isinstance(ts, datetime):
        ts_str = ts.strftime("%H:%M")
    elif isinstance(ts, str):
        ts_str = ts[:16]

    icon = _event_icon(event_type)
    print(f"\n{icon} [{source}] {event_type.upper()}")
    print(f"  {title}")
    if summary:
        print(f"  {summary}")
    if url:
        print(f"  {url}")
    if ts_str:
        print(f"  {ts_str}")


def _event_icon(event_type: str) -> str:
    icons = {
        "assigned": "-->",
        "comment": "  [C]",
        "review_requested": " [R]",
        "status_change": " [S]",
    }
    return icons.get(event_type.lower(), " [!]")


def notify(notification: Dict[str, Any]) -> None:
    """
    Deliver a single notification via all enabled channels.

    ``notification`` should be a dict matching the notifications collection schema:
    {
        source, event_type, ticket_id, title, summary, url,
        timestamp, read, dismissed, raw
    }
    """
    event_type = notification.get("event_type", "")
    if not _should_notify(event_type):
        logger.debug(f"Notification suppressed by config: {event_type}")
        return

    title = notification.get("title", "DevTrack Alert")
    summary = notification.get("summary", "")
    source = notification.get("source", "").upper()

    if cfg.get_bool("ALERT_NOTIFY_TERMINAL", True):
        _terminal_notify(notification)

    if cfg.get_bool("ALERT_NOTIFY_OS", True):
        subtitle = f"[{source}] {event_type.replace('_', ' ').title()}"
        _os_notify("DevTrack", subtitle, f"{title}: {summary}" if summary else title)


def notify_many(notifications: list) -> None:
    """Deliver multiple notifications."""
    for n in notifications:
        try:
            notify(n)
        except Exception as e:
            logger.warning(f"Failed to deliver notification: {e}")
