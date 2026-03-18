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
                "No Azure sync data found\\. Run `devtrack azure-sync` first\\.",
                parse_mode="MarkdownV2"
            )
            return

        with open(state_file) as f:
            data = json.load(f)

        # work_items is a dict keyed by ID
        work_items = data.get("work_items", {})
        last_sync = data.get("last_sync", "unknown")
        if last_sync and "T" in last_sync:
            last_sync = last_sync.split("T")[0]

        if not work_items:
            await update.message.reply_text(
                f"No work items found\\.\n_Last synced: {last_sync}_\n\nRun `devtrack azure\\-sync` to refresh\\.",
                parse_mode="MarkdownV2"
            )
            return

        # Group by state
        by_state: dict = {}
        for item in work_items.values():
            state = item.get("state", "Unknown")
            by_state.setdefault(state, []).append(item)

        messages = []
        for state in sorted(by_state.keys()):
            state_items = by_state[state]
            block = [f"*{state}* ({len(state_items)})"]
            for item in state_items:
                item_id = item.get("id", "?")
                title = item.get("title", "(no title)")
                wtype = item.get("type", "")
                sprint = item.get("iteration_path", "")
                due = item.get("due_date", "")
                desc_raw = item.get("description", "") or ""
                desc = _strip_html(desc_raw)
                if len(desc) > 120:
                    desc = desc[:120] + "..."

                block.append(f"\n`#{item_id}` — *{title}*")
                block.append(f"  Type: {wtype}  |  State: {state}")
                if sprint:
                    block.append(f"  Sprint: {sprint.split('\\\\')[-1]}")
                if due:
                    block.append(f"  Due: {due}")
                if desc:
                    block.append(f"  _{desc}_")

            messages.append("\n".join(block))

        header = f"*Azure DevOps — My Issues* ({len(work_items)} total)\n"
        footer = f"\n_Synced: {last_sync}_ | /issue <id> for full details"

        # Send in chunks so we don't exceed Telegram's limit
        current = header
        for block in messages:
            if len(current) + len(block) + len(footer) + 5 > MAX_MSG_LEN:
                await update.message.reply_text(current, parse_mode="Markdown")
                current = block
            else:
                current = current + "\n\n" + block

        current += footer
        await update.message.reply_text(current, parse_mode="Markdown")

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

        lines = [
            f"*#{wi.id} — {_escape_md(wi.title)}*",
            "",
            f"*Type:* {wi.work_item_type}",
            f"*State:* {wi.state}",
            f"*Assigned:* {wi.assigned_to or '(unassigned)'}",
            f"*Area:* {wi.area_path}",
        ]
        if wi.iteration_path:
            sprint_name = wi.iteration_path.split("\\")[-1]
            lines.append(f"*Sprint:* {sprint_name}")
        if wi.due_date:
            lines.append(f"*Due:* {wi.due_date}")
        if wi.tags:
            lines.append(f"*Tags:* {', '.join(wi.tags)}")
        if wi.parent_id:
            lines.append(f"*Parent:* #{wi.parent_id}")
        if wi.url:
            lines.append(f"*URL:* {wi.url}")

        if wi.description:
            clean = _strip_html(wi.description)
            if clean:
                lines.append("")
                lines.append("*Description:*")
                # Trim long descriptions
                if len(clean) > 800:
                    clean = clean[:800] + "..."
                lines.append(clean)

        text = "\n".join(lines)
        if len(text) > MAX_MSG_LEN - 20:
            text = text[:MAX_MSG_LEN - 20] + "\n... (truncated)"
        await update.message.reply_text(text, parse_mode="Markdown")

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


def _strip_html(text: str) -> str:
    """Remove HTML tags for terminal/Telegram display."""
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def _escape_md(text: str) -> str:
    """Escape Markdown special characters in user content."""
    for ch in r"\_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, f"\\{ch}")
    return text


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
