"""Telegram bot command handlers for DevTrack."""
import json
import logging
import os
import re
import sqlite3
import subprocess
from typing import TYPE_CHECKING

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

if TYPE_CHECKING:
    from backend.telegram.bot import DevTrackBot

logger = logging.getLogger(__name__)

# Maximum Telegram message length
MAX_MSG_LEN = 4096


def _devtrack_bin() -> str:
    """Resolve the devtrack binary path from PROJECT_ROOT."""
    project_root = os.environ.get("PROJECT_ROOT", "")
    if project_root:
        candidate = os.path.join(project_root, "devtrack")
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    # Fallback: assume it's in PATH
    return "devtrack"


def _devtrack_env() -> dict:
    """Build subprocess environment with DEVTRACK_ENV_FILE set."""
    env = os.environ.copy()
    if "DEVTRACK_ENV_FILE" not in env:
        project_root = env.get("PROJECT_ROOT", "")
        if project_root:
            env["DEVTRACK_ENV_FILE"] = os.path.join(project_root, ".env")
    return env


def register_handlers(app: Application, bot: "DevTrackBot"):
    """Register all command handlers."""
    app.add_handler(CommandHandler("start", _cmd_start))
    app.add_handler(CommandHandler("help", _cmd_help))
    app.add_handler(CommandHandler("status", _make_handler(bot, _cmd_status)))
    app.add_handler(CommandHandler("logs", _make_handler(bot, _cmd_logs)))
    app.add_handler(CommandHandler("trigger", _make_handler(bot, _cmd_trigger)))
    app.add_handler(CommandHandler("pause", _make_handler(bot, _cmd_pause)))
    app.add_handler(CommandHandler("resume", _make_handler(bot, _cmd_resume)))
    app.add_handler(CommandHandler("queue", _make_handler(bot, _cmd_queue)))
    app.add_handler(CommandHandler("commits", _make_handler(bot, _cmd_commits)))
    app.add_handler(CommandHandler("health", _make_handler(bot, _cmd_health)))
    app.add_handler(CommandHandler("issues", _make_handler(bot, _cmd_issues)))
    app.add_handler(CommandHandler("issue", _make_handler(bot, _cmd_issue)))
    app.add_handler(CommandHandler("create", _make_handler(bot, _cmd_create)))


def _make_handler(bot: "DevTrackBot", handler_fn):
    """Wrap a handler with auth check."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await bot._check_auth(update):
            return
        await handler_fn(update, context, bot)
    return wrapper


async def _cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command (no auth needed)."""
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"DevTrack Bot\n\n"
        f"Your chat ID: `{chat_id}`\n\n"
        f"Add this to `TELEGRAM_ALLOWED_CHAT_IDS` in your `.env` to authorize.\n\n"
        f"Use /help for available commands.",
        parse_mode="Markdown"
    )


async def _cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command (no auth needed)."""
    await update.message.reply_text(
        "*DevTrack Bot Commands*\n\n"
        "/status -- Daemon status and service health\n"
        "/logs -- Recent daemon log lines\n"
        "/trigger -- Force an immediate work update trigger\n"
        "/pause -- Pause the scheduler\n"
        "/resume -- Resume the scheduler\n"
        "/queue -- Message queue statistics\n"
        "/commits -- Deferred commit status\n"
        "/health -- Detailed service health\n"
        "/issues -- Azure DevOps work items assigned to you\n"
        "/issue <id> -- Full details of a specific work item\n"
        "/create <title> -- Create a Task (prefix with 'bug' or 'task' to set type)\n"
        "/help -- Show this message",
        parse_mode="Markdown"
    )


async def _cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE, bot: "DevTrackBot"):
    """Handle /status -- show daemon status."""
    try:
        result = subprocess.run(
            [_devtrack_bin(), "status"],
            capture_output=True, text=True, timeout=10, env=_devtrack_env()
        )
        output = result.stdout or result.stderr or "No output"
        # Truncate if too long
        if len(output) > MAX_MSG_LEN - 20:
            output = output[:MAX_MSG_LEN - 20] + "\n... (truncated)"
        await update.message.reply_text(f"```\n{output}\n```", parse_mode="Markdown")
    except subprocess.TimeoutExpired:
        await update.message.reply_text("Status command timed out")
    except FileNotFoundError:
        await update.message.reply_text("`devtrack` binary not found in PATH")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def _cmd_logs(update: Update, context: ContextTypes.DEFAULT_TYPE, bot: "DevTrackBot"):
    """Handle /logs -- show recent log lines."""
    try:
        # Get line count from args (default 20)
        lines = 20
        if context.args:
            try:
                lines = min(int(context.args[0]), 50)  # Cap at 50
            except ValueError:
                pass

        result = subprocess.run(
            [_devtrack_bin(), "logs", "-n", str(lines)],
            capture_output=True, text=True, timeout=10, env=_devtrack_env()
        )
        output = result.stdout or result.stderr or "No logs available"
        if len(output) > MAX_MSG_LEN - 20:
            output = output[-(MAX_MSG_LEN - 20):]  # Keep tail
        await update.message.reply_text(f"```\n{output}\n```", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def _cmd_trigger(update: Update, context: ContextTypes.DEFAULT_TYPE, bot: "DevTrackBot"):
    """Handle /trigger -- force immediate work update."""
    try:
        result = subprocess.run(
            [_devtrack_bin(), "force-trigger"],
            capture_output=True, text=True, timeout=10, env=_devtrack_env()
        )
        output = result.stdout or result.stderr or "Trigger sent"
        await update.message.reply_text(output.strip())
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def _cmd_pause(update: Update, context: ContextTypes.DEFAULT_TYPE, bot: "DevTrackBot"):
    """Handle /pause -- pause scheduler."""
    try:
        result = subprocess.run(
            [_devtrack_bin(), "pause"],
            capture_output=True, text=True, timeout=10, env=_devtrack_env()
        )
        output = result.stdout or result.stderr or "Paused"
        await update.message.reply_text(output.strip())
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def _cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE, bot: "DevTrackBot"):
    """Handle /resume -- resume scheduler."""
    try:
        result = subprocess.run(
            [_devtrack_bin(), "resume"],
            capture_output=True, text=True, timeout=10, env=_devtrack_env()
        )
        output = result.stdout or result.stderr or "Resumed"
        await update.message.reply_text(output.strip())
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def _cmd_queue(update: Update, context: ContextTypes.DEFAULT_TYPE, bot: "DevTrackBot"):
    """Handle /queue -- show message queue stats."""
    try:
        db_path = _get_db_path()
        if not db_path:
            await update.message.reply_text("Database not found")
            return

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT status, COUNT(*) FROM message_queue GROUP BY status")
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            await update.message.reply_text("Message queue is empty")
            return

        text = "*Message Queue*\n\n"
        for status, count in rows:
            text += f"- {status}: {count}\n"

        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def _cmd_commits(update: Update, context: ContextTypes.DEFAULT_TYPE, bot: "DevTrackBot"):
    """Handle /commits -- show deferred commit status."""
    try:
        db_path = _get_db_path()
        if not db_path:
            await update.message.reply_text("Database not found")
            return

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT status, COUNT(*) FROM deferred_commits GROUP BY status")
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            await update.message.reply_text("No deferred commits")
            return

        text = "*Deferred Commits*\n\n"
        for status, count in rows:
            text += f"- {status}: {count}\n"

        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def _cmd_health(update: Update, context: ContextTypes.DEFAULT_TYPE, bot: "DevTrackBot"):
    """Handle /health -- show detailed service health."""
    try:
        db_path = _get_db_path()
        if not db_path:
            await update.message.reply_text("Database not found")
            return

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get latest health snapshot per service
        cursor.execute("""
            SELECT service, status, latency_ms, details, checked_at
            FROM health_snapshots h1
            WHERE checked_at = (
                SELECT MAX(checked_at) FROM health_snapshots h2 WHERE h2.service = h1.service
            )
            ORDER BY service
        """)
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            await update.message.reply_text("No health data available yet")
            return

        text = "*Service Health*\n\n"
        status_map = {
            "up": "UP", "down": "DOWN", "degraded": "DEGRADED", "unconfigured": "N/A"
        }

        for service, status, latency_ms, details, checked_at in rows:
            name = _service_display_name(service)
            label = status_map.get(status, status)
            line = f"*{name}*: {label}"
            if latency_ms and latency_ms > 0:
                line += f" ({latency_ms}ms)"
            text += line + "\n"

        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def _cmd_issues(update: Update, context: ContextTypes.DEFAULT_TYPE, bot: "DevTrackBot"):
    """Handle /issues -- list Azure DevOps work items assigned to me (from cache)."""
    try:
        state_file = _get_azure_state_file()
        if not state_file or not os.path.exists(state_file):
            await update.message.reply_text(
                "No Azure sync data found. Run <code>devtrack azure-sync</code> first.",
                parse_mode="HTML"
            )
            return

        with open(state_file) as f:
            data = json.load(f)

        work_items = data.get("work_items", {})
        last_sync = data.get("last_sync", "unknown")
        if last_sync and "T" in last_sync:
            last_sync = last_sync.split("T")[0]

        if not work_items:
            await update.message.reply_text(
                f"No work items found.\n<i>Last synced: {last_sync}</i>\n\n"
                "Run <code>devtrack azure-sync</code> to refresh.",
                parse_mode="HTML"
            )
            return

        by_state: dict = {}
        for item in work_items.values():
            state = item.get("state", "Unknown")
            by_state.setdefault(state, []).append(item)

        blocks = []
        for state in sorted(by_state.keys()):
            state_items = by_state[state]
            lines = [f"<b>{_h(state)}</b> ({len(state_items)})"]
            for item in state_items:
                item_id = item.get("id", "?")
                title = _h(item.get("title", "(no title)"))
                wtype = _h(item.get("type", ""))
                sprint_raw = item.get("iteration_path", "") or ""
                sprint = _h(sprint_raw.split("\\")[-1]) if sprint_raw else ""
                due = _h(item.get("due_date", "") or "")
                desc = _strip_html_entities(item.get("description", "") or "")
                if len(desc) > 150:
                    desc = desc[:150] + "..."

                lines.append(f"\n<code>#{item_id}</code> <b>{title}</b>")
                lines.append(f"  {wtype}  |  {state}")
                if sprint:
                    lines.append(f"  Sprint: {sprint}")
                if due:
                    lines.append(f"  Due: {due}")
                if desc:
                    lines.append(f"  <i>{_h(desc)}</i>")
            blocks.append("\n".join(lines))

        header = f"<b>Azure DevOps — My Issues</b> ({len(work_items)} total)\n\n"
        footer = f"\n\n<i>Synced: {last_sync}</i>  |  /issue &lt;id&gt; for full details"

        current = header
        for block in blocks:
            if len(current) + len(block) + len(footer) + 5 > MAX_MSG_LEN:
                await update.message.reply_text(current, parse_mode="HTML")
                current = block
            else:
                current = current + block + "\n\n"

        await update.message.reply_text(current + footer, parse_mode="HTML")

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def _cmd_issue(update: Update, context: ContextTypes.DEFAULT_TYPE, bot: "DevTrackBot"):
    """Handle /issue <id> -- fetch full work item details live from Azure DevOps."""
    if not context.args:
        await update.message.reply_text("Usage: /issue <work-item-id>")
        return

    try:
        item_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(f"Invalid ID: `{context.args[0]}`", parse_mode="Markdown")
        return

    await update.message.reply_text(f"Fetching work item #{item_id}...")

    try:
        from backend.azure.client import AzureDevOpsClient

        client = AzureDevOpsClient()
        if not client.is_configured():
            await update.message.reply_text("Azure DevOps is not configured. Check your `.env`.")
            return

        wi = await client.get_work_item(item_id)
        await client.close()

        if not wi:
            await update.message.reply_text(f"Work item #{item_id} not found or not accessible.")
            return

        sprint_name = wi.iteration_path.split("\\")[-1] if wi.iteration_path else ""

        lines = [
            f"<code>#{wi.id}</code> <b>{_h(wi.title)}</b>",
            "",
            f"<b>Type:</b> {_h(wi.work_item_type)}",
            f"<b>State:</b> {_h(wi.state)}",
            f"<b>Assigned:</b> {_h(wi.assigned_to or '(unassigned)')}",
        ]
        if sprint_name:
            lines.append(f"<b>Sprint:</b> {_h(sprint_name)}")
        if wi.due_date:
            lines.append(f"<b>Due:</b> {_h(wi.due_date)}")
        if wi.area_path:
            lines.append(f"<b>Area:</b> {_h(wi.area_path)}")
        if wi.tags:
            lines.append(f"<b>Tags:</b> {_h(', '.join(wi.tags))}")
        if wi.parent_id:
            lines.append(f"<b>Parent:</b> #{wi.parent_id}")
        if wi.url:
            lines.append(f"<b>URL:</b> {wi.url}")

        if wi.description:
            clean = _strip_html_entities(wi.description)
            if clean:
                if len(clean) > 800:
                    clean = clean[:800] + "..."
                lines.append(f"\n<b>Description:</b>\n<i>{_h(clean)}</i>")

        text = "\n".join(lines)
        if len(text) > MAX_MSG_LEN - 20:
            text = text[:MAX_MSG_LEN - 20] + "\n... (truncated)"
        await update.message.reply_text(text, parse_mode="HTML")

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def _cmd_create(update: Update, context: ContextTypes.DEFAULT_TYPE, bot: "DevTrackBot"):
    """Handle /create [type] <title> -- create a new Azure DevOps work item."""
    if not context.args:
        await update.message.reply_text(
            "Usage:\n"
            "<code>/create Fix the login bug</code>\n"
            "<code>/create bug Fix the login bug</code>\n"
            "<code>/create task Review PR for sprint 2</code>",
            parse_mode="HTML"
        )
        return

    # Check if first word is a type keyword
    type_keywords = {
        "bug": "Bug",
        "task": "Task",
        "feature": "Feature",
        "epic": "Epic",
        "story": "Product Backlog Item",
        "pbi": "Product Backlog Item",
    }
    first = context.args[0].lower()
    if first in type_keywords and len(context.args) > 1:
        work_item_type = type_keywords[first]
        title = " ".join(context.args[1:])
    else:
        work_item_type = "Task"
        title = " ".join(context.args)

    await update.message.reply_text(f"Creating {work_item_type}: <i>{_h(title)}</i>...", parse_mode="HTML")

    try:
        from backend.azure.client import AzureDevOpsClient

        client = AzureDevOpsClient()
        if not client.is_configured():
            await update.message.reply_text("Azure DevOps is not configured. Check your <code>.env</code>.", parse_mode="HTML")
            return

        wi = await client.create_work_item(title=title, work_item_type=work_item_type)
        await client.close()

        if not wi:
            await update.message.reply_text(f"Failed to create {work_item_type}. Check Azure DevOps permissions.")
            return

        lines = [
            f"✓ Created <b>{_h(wi.work_item_type)}</b> <code>#{wi.id}</code>",
            f"<b>{_h(wi.title)}</b>",
            f"State: {_h(wi.state)}",
        ]
        if wi.url:
            lines.append(f"<a href=\"{wi.url}\">Open in Azure DevOps</a>")

        await update.message.reply_text("\n".join(lines), parse_mode="HTML")

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


def _get_azure_state_file() -> str:
    """Resolve path to Data/azure/sync_state.json."""
    try:
        from backend.config import get_path
        data_dir = get_path("DATA_DIR")
        return os.path.join(data_dir, "azure", "sync_state.json")
    except Exception:
        pass
    project_root = os.environ.get("PROJECT_ROOT", "")
    if project_root:
        return os.path.join(project_root, "Data", "azure", "sync_state.json")
    return ""


def _h(text: str) -> str:
    """Escape HTML special characters for Telegram HTML parse mode."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _strip_html_entities(text: str) -> str:
    """Strip HTML tags and decode common entities for display."""
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return " ".join(text.split()).strip()


def _strip_html(text: str) -> str:
    """Remove HTML tags for terminal display."""
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def _get_db_path() -> str:
    """Get the SQLite database path."""
    from backend.config import get_path
    try:
        db_dir = get_path("DATABASE_DIR")
        db_file = os.environ.get("DATABASE_FILE_NAME", "devtrack.db")
        path = os.path.join(db_dir, db_file)
        if os.path.exists(path):
            return path
    except Exception:
        pass
    return ""


def _service_display_name(service: str) -> str:
    """Human-readable service name."""
    names = {
        "ipc": "Python IPC",
        "python_bridge": "Python Bridge",
        "ollama": "Ollama",
        "azure_devops": "Azure DevOps",
        "webhook_server": "Webhook Server",
        "mongodb": "MongoDB",
        "telegram_bot": "Telegram Bot",
    }
    return names.get(service, service)
