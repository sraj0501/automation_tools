"""Telegram bot command handlers for DevTrack."""
import json
import logging
import os
import re
import sqlite3
import subprocess
from typing import TYPE_CHECKING

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

if TYPE_CHECKING:
    from backend.telegram.bot import DevTrackBot

logger = logging.getLogger(__name__)

# Maximum Telegram message length
MAX_MSG_LEN = 4096

# Module-level pending stores for multi-step flows
_PENDING_GITLAB_CREATES: dict = {}  # chat_id -> title
_PENDING_PLANS: dict = {}           # chat_id -> {"problem": str, "plan": ..., "platform": str}


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
    app.add_handler(CallbackQueryHandler(_on_sprint_selected, pattern=r"^sprint:"))
    app.add_handler(CallbackQueryHandler(_on_view_issue, pattern=r"^view_issue:"))
    # GitLab commands
    app.add_handler(CommandHandler("gitlab", _make_handler(bot, _cmd_gitlab)))
    app.add_handler(CommandHandler("gitlabissue", _make_handler(bot, _cmd_gitlab_issue)))
    app.add_handler(CommandHandler("gitlabcreate", _make_handler(bot, _cmd_gitlab_create)))
    app.add_handler(CallbackQueryHandler(_on_view_gitlab_issue, pattern=r"^view_gitlab_issue:"))
    app.add_handler(CallbackQueryHandler(_on_gitlab_milestone_selected, pattern=r"^gitlab_milestone:"))
    # PM Agent commands
    app.add_handler(CommandHandler("plan", _make_handler(bot, _cmd_plan)))
    app.add_handler(CallbackQueryHandler(_on_plan_platform_selected, pattern=r"^plan_platform:"))
    app.add_handler(CallbackQueryHandler(_on_plan_confirmed, pattern=r"^plan_confirm:"))
    app.add_handler(CallbackQueryHandler(_on_plan_cancelled, pattern=r"^plan_cancel:"))


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
        "/gitlab -- GitLab issues assigned to me (from cache)\n"
        "/gitlabissue <project\\_id> <iid> -- Fetch a single issue live\n"
        "/gitlabcreate <title> -- Create a new GitLab issue\n"
        "/plan <problem statement> -- Decompose into work items and create in PM platform\n"
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


_TYPE_KEYWORDS = {
    "bug": "Bug",
    "task": "Task",
    "feature": "Feature",
    "epic": "Epic",
    "story": "Product Backlog Item",
    "pbi": "Product Backlog Item",
}


async def _cmd_create(update: Update, context: ContextTypes.DEFAULT_TYPE, bot: "DevTrackBot"):
    """Handle /create [type] <title> -- create a new Azure DevOps work item."""
    if not context.args:
        await update.message.reply_text(
            "Usage:\n"
            "<code>/create Fix the login bug</code>\n"
            "<code>/create bug Fix the login bug</code>\n"
            "<code>/create task Review sprint PR</code>\n\n"
            "Type keywords: bug, task, feature, epic, story, pbi",
            parse_mode="HTML"
        )
        return

    first = context.args[0].lower()
    if first in _TYPE_KEYWORDS and len(context.args) > 1:
        work_item_type = _TYPE_KEYWORDS[first]
        title = " ".join(context.args[1:])
    else:
        work_item_type = "Task"
        title = " ".join(context.args)

    try:
        from backend.azure.client import AzureDevOpsClient

        client = AzureDevOpsClient()
        if not client.is_configured():
            await update.message.reply_text(
                "Azure DevOps is not configured. Check your <code>.env</code>.",
                parse_mode="HTML"
            )
            return

        # Fetch sprints in parallel with showing progress
        await update.message.reply_text(
            f"Fetching sprints for <b>{_h(work_item_type)}</b>: <i>{_h(title)}</i>...",
            parse_mode="HTML"
        )
        iterations = await client.get_iterations()
        await client.close()

        # Build sprint picker keyboard
        # Each button encodes: sprint:<work_item_type>|<iteration_path>|<title>
        buttons = []
        for it in iterations:
            name = it.get("name", "")
            path = it.get("path", "") or name
            # Truncate label for button display
            label = name[:30]
            payload = f"sprint:{work_item_type}|{path}|{title}"
            if len(payload) <= 64:  # Telegram callback_data limit
                buttons.append([InlineKeyboardButton(label, callback_data=payload)])

        buttons.append([InlineKeyboardButton("No sprint (backlog)", callback_data=f"sprint:{work_item_type}||{title}")])

        if not buttons:
            # No sprints found — create without sprint
            await _do_create(update, work_item_type, title, iteration_path=None)
            return

        keyboard = InlineKeyboardMarkup(buttons)
        await update.message.reply_text(
            f"Which sprint for <b>{_h(work_item_type)}</b>: <i>{_h(title)}</i>?",
            reply_markup=keyboard,
            parse_mode="HTML"
        )

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def _on_sprint_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback when user picks a sprint from the inline keyboard."""
    query = update.callback_query
    await query.answer()

    try:
        # payload: sprint:<type>|<iteration_path>|<title>
        payload = query.data[len("sprint:"):]
        parts = payload.split("|", 2)
        if len(parts) != 3:
            await query.edit_message_text("Invalid selection.")
            return

        work_item_type, iteration_path, title = parts
        iteration_path = iteration_path or None

        await query.edit_message_text(
            f"Creating <b>{_h(work_item_type)}</b>: <i>{_h(title)}</i>"
            + (f"\nSprint: {_h(iteration_path.split(chr(92))[-1])}" if iteration_path else "\nBacklog (no sprint)")
            + "...",
            parse_mode="HTML"
        )
        await _do_create(query, work_item_type, title, iteration_path)

    except Exception as e:
        await query.edit_message_text(f"Error: {e}")


async def _do_create(ctx, work_item_type: str, title: str, iteration_path):
    """Create the work item and send confirmation."""
    from backend.azure.client import AzureDevOpsClient

    client = AzureDevOpsClient()
    try:
        wi = await client.create_work_item(
            title=title,
            work_item_type=work_item_type,
            iteration_path=iteration_path,
        )
    finally:
        await client.close()

    if not wi:
        text = f"Failed to create {work_item_type}. Check Azure DevOps permissions."
    else:
        sprint_label = ""
        if wi.iteration_path:
            sprint_label = f"\nSprint: {_h(wi.iteration_path.split(chr(92))[-1])}"
        url_label = f'\n<a href="{wi.url}">Open in Azure DevOps</a>' if wi.url else ""
        text = (
            f"✓ Created <b>{_h(wi.work_item_type)}</b> <code>#{wi.id}</code>\n"
            f"<b>{_h(wi.title)}</b>\n"
            f"State: {_h(wi.state)}"
            f"{sprint_label}{url_label}"
        )

    # ctx is either a Message (from direct create) or a CallbackQuery
    if hasattr(ctx, "edit_message_text"):
        await ctx.edit_message_text(text, parse_mode="HTML")
    else:
        await ctx.message.reply_text(text, parse_mode="HTML")


async def _on_view_issue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: View Full Details button on assignment notifications."""
    query = update.callback_query
    await query.answer()
    try:
        item_id = int(query.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await query.answer("Invalid work item ID", show_alert=True)
        return

    await query.message.reply_text(f"Fetching work item #{item_id}...")

    try:
        from backend.azure.client import AzureDevOpsClient
        client = AzureDevOpsClient()
        if not client.is_configured():
            await query.message.reply_text("Azure DevOps is not configured.")
            return

        wi = await client.get_work_item(item_id)
        await client.close()

        if not wi:
            await query.message.reply_text(f"Work item #{item_id} not found or not accessible.")
            return

        sprint_name = wi.iteration_path.split("\\")[-1] if wi.iteration_path else ""
        lines = [
            f"<code>#{wi.id}</code>  <b>{_h(wi.title)}</b>",
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
            lines.append(f'<a href="{wi.url}">Open in Azure DevOps</a>')
        if wi.description:
            clean = _strip_html_entities(wi.description)
            if clean:
                if len(clean) > 800:
                    clean = clean[:800] + "..."
                lines.append(f"\n<b>Description:</b>\n<i>{_h(clean)}</i>")

        text = "\n".join(lines)
        if len(text) > MAX_MSG_LEN - 20:
            text = text[:MAX_MSG_LEN - 20] + "\n... (truncated)"
        await query.message.reply_text(text, parse_mode="HTML")

    except Exception as e:
        await query.message.reply_text(f"Error: {e}")


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


# ---------------------------------------------------------------------------
# GitLab helpers
# ---------------------------------------------------------------------------

def _get_gitlab_state_file() -> str:
    """Resolve path to Data/gitlab/sync_state.json."""
    try:
        from backend.config import get_path
        data_dir = get_path("DATA_DIR")
        return os.path.join(data_dir, "gitlab", "sync_state.json")
    except Exception:
        pass
    project_root = os.environ.get("PROJECT_ROOT", "")
    if project_root:
        return os.path.join(project_root, "Data", "gitlab", "sync_state.json")
    return ""


# ---------------------------------------------------------------------------
# GitLab command handlers
# ---------------------------------------------------------------------------

async def _cmd_gitlab(update: Update, context: ContextTypes.DEFAULT_TYPE, bot: "DevTrackBot"):
    """Handle /gitlab -- list GitLab issues assigned to me (from cache)."""
    try:
        state_file = _get_gitlab_state_file()
        if not state_file or not os.path.exists(state_file):
            await update.message.reply_text(
                "No GitLab sync data found. Run <code>devtrack gitlab-sync</code> first.",
                parse_mode="HTML"
            )
            return

        with open(state_file) as f:
            data = json.load(f)

        issues = data.get("issues", {})
        last_sync = data.get("last_sync", "unknown")
        if last_sync and "T" in last_sync:
            last_sync = last_sync.split("T")[0]

        if not issues:
            await update.message.reply_text(
                f"No issues found.\n<i>Last synced: {last_sync}</i>\n\n"
                "Run <code>devtrack gitlab-sync</code> to refresh.",
                parse_mode="HTML"
            )
            return

        # Group by state
        by_state: dict = {}
        for item in issues.values():
            state = item.get("state", "opened")
            by_state.setdefault(state, []).append(item)

        blocks = []
        for state in sorted(by_state.keys()):
            state_items = by_state[state]
            lines = [f"<b>{_h(state)}</b> ({len(state_items)})"]
            for item in state_items:
                iid = item.get("iid", "?")
                project_id = item.get("project_id", "?")
                title = _h(item.get("title", "(no title)"))
                labels = _h(", ".join(item.get("labels", [])))
                milestone = _h(item.get("milestone_title", "") or "")
                due = _h(item.get("due_date", "") or "")

                lines.append(f"\n<code>!{iid}</code> <b>{title}</b>")
                lines.append(f"  Project: {project_id}  |  {_h(state)}")
                if milestone:
                    lines.append(f"  Milestone: {milestone}")
                if labels:
                    lines.append(f"  Labels: {labels}")
                if due:
                    lines.append(f"  Due: {due}")
            blocks.append("\n".join(lines))

        header = f"<b>GitLab — My Issues</b> ({len(issues)} total)\n\n"
        footer = f"\n\n<i>Synced: {last_sync}</i>  |  /gitlabissue &lt;project_id&gt; &lt;iid&gt;"

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


async def _cmd_gitlab_issue(update: Update, context: ContextTypes.DEFAULT_TYPE, bot: "DevTrackBot"):
    """Handle /gitlabissue <project_id> <iid> -- fetch single issue live."""
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Usage: /gitlabissue <project_id> <issue_iid>")
        return

    try:
        project_id = int(context.args[0])
        issue_iid = int(context.args[1])
    except ValueError:
        await update.message.reply_text("Both project_id and iid must be integers.")
        return

    await update.message.reply_text(f"Fetching GitLab issue !{issue_iid} in project {project_id}...")

    try:
        from backend.gitlab.client import GitLabClient
        client = GitLabClient()
        if not client.is_configured():
            await update.message.reply_text(
                "GitLab is not configured. Check your <code>.env</code>.", parse_mode="HTML"
            )
            return

        issue = await client.get_issue(project_id, issue_iid)
        await client.close()

        if not issue:
            await update.message.reply_text(f"Issue !{issue_iid} not found in project {project_id}.")
            return

        lines = [
            f"<code>!{issue.iid}</code> <b>{_h(issue.title)}</b>",
            "",
            f"<b>State:</b> {_h(issue.state)}",
            f"<b>Project:</b> {issue.project_id}",
            f"<b>Assigned:</b> {_h(issue.assignee or '(unassigned)')}",
        ]
        if issue.milestone_title:
            lines.append(f"<b>Milestone:</b> {_h(issue.milestone_title)}")
        if issue.labels:
            lines.append(f"<b>Labels:</b> {_h(', '.join(issue.labels))}")
        if issue.due_date:
            lines.append(f"<b>Due:</b> {_h(issue.due_date)}")
        if issue.url:
            lines.append(f"<b>URL:</b> {issue.url}")
        if issue.description:
            clean = _strip_html_entities(issue.description)
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


async def _cmd_gitlab_create(update: Update, context: ContextTypes.DEFAULT_TYPE, bot: "DevTrackBot"):
    """Handle /gitlabcreate <title> -- create a GitLab issue with optional milestone picker."""
    if not context.args:
        await update.message.reply_text(
            "Usage: <code>/gitlabcreate Fix the login bug</code>",
            parse_mode="HTML"
        )
        return

    title = " ".join(context.args)

    try:
        from backend.gitlab.client import GitLabClient
        client = GitLabClient()
        if not client.is_configured():
            await update.message.reply_text(
                "GitLab is not configured. Check your <code>.env</code>.",
                parse_mode="HTML"
            )
            return

        await update.message.reply_text(
            f"Fetching milestones for: <i>{_h(title)}</i>...",
            parse_mode="HTML"
        )

        milestones = await client.get_milestones()  # uses GITLAB_PROJECT_ID
        await client.close()

        chat_id = update.effective_chat.id
        _PENDING_GITLAB_CREATES[chat_id] = title

        buttons = []
        for m in milestones:
            mid = m.get("id", "")
            mname = m.get("title", "")
            label = mname[:30]
            payload = f"gitlab_milestone:{mid}|{chat_id}"
            buttons.append([InlineKeyboardButton(label, callback_data=payload)])

        buttons.append([InlineKeyboardButton(
            "No milestone", callback_data=f"gitlab_milestone:0|{chat_id}"
        )])

        if not milestones:
            # No milestones — create directly
            await _do_gitlab_create(update, title, milestone_id=None)
            return

        keyboard = InlineKeyboardMarkup(buttons)
        await update.message.reply_text(
            f"Choose milestone for: <b>{_h(title)}</b>",
            reply_markup=keyboard,
            parse_mode="HTML"
        )

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def _on_gitlab_milestone_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback when user picks a milestone from the GitLab create flow."""
    query = update.callback_query
    await query.answer()

    try:
        payload = query.data[len("gitlab_milestone:"):]
        parts = payload.split("|", 1)
        if len(parts) != 2:
            await query.edit_message_text("Invalid selection.")
            return

        milestone_id_str, chat_id_str = parts
        milestone_id = int(milestone_id_str) if milestone_id_str != "0" else None
        chat_id = int(chat_id_str)

        title = _PENDING_GITLAB_CREATES.pop(chat_id, None)
        if not title:
            await query.edit_message_text("Session expired. Please run /gitlabcreate again.")
            return

        milestone_label = f" (milestone #{milestone_id})" if milestone_id else " (no milestone)"
        await query.edit_message_text(
            f"Creating issue: <i>{_h(title)}</i>{_h(milestone_label)}...",
            parse_mode="HTML"
        )
        await _do_gitlab_create(query, title, milestone_id=milestone_id)

    except Exception as e:
        await query.edit_message_text(f"Error: {e}")


async def _do_gitlab_create(ctx, title: str, milestone_id):
    """Create the GitLab issue and send confirmation."""
    from backend.gitlab.client import GitLabClient
    client = GitLabClient()
    try:
        issue = await client.create_issue(
            title=title,
            milestone_id=milestone_id,
        )
    finally:
        await client.close()

    if not issue:
        text = "Failed to create issue. Check GitLab permissions and GITLAB_PROJECT_ID."
    else:
        url_label = f'\n<a href="{issue.url}">Open in GitLab</a>' if issue.url else ""
        milestone_label = f"\nMilestone: {_h(issue.milestone_title)}" if issue.milestone_title else ""
        text = (
            f"Created issue <code>!{issue.iid}</code>\n"
            f"<b>{_h(issue.title)}</b>\n"
            f"State: {_h(issue.state)}"
            f"{milestone_label}{url_label}"
        )

    if hasattr(ctx, "edit_message_text"):
        await ctx.edit_message_text(text, parse_mode="HTML")
    else:
        await ctx.message.reply_text(text, parse_mode="HTML")


async def _on_view_gitlab_issue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: View Details on GitLab assignment notifications."""
    query = update.callback_query
    await query.answer()
    try:
        global_id = int(query.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await query.answer("Invalid issue ID", show_alert=True)
        return

    await query.message.reply_text(f"Fetching GitLab issue #{global_id}...")

    try:
        from backend.gitlab.client import GitLabClient
        client = GitLabClient()
        if not client.is_configured():
            await query.message.reply_text("GitLab is not configured.")
            return

        issue = await client.get_issue_by_global_id(global_id)
        await client.close()

        if not issue:
            await query.message.reply_text(f"Issue #{global_id} not found.")
            return

        lines = [
            f"<code>!{issue.iid}</code> <b>{_h(issue.title)}</b>",
            f"<b>State:</b> {_h(issue.state)}",
            f"<b>Assigned:</b> {_h(issue.assignee or '(unassigned)')}",
        ]
        if issue.milestone_title:
            lines.append(f"<b>Milestone:</b> {_h(issue.milestone_title)}")
        if issue.labels:
            lines.append(f"<b>Labels:</b> {_h(', '.join(issue.labels))}")
        if issue.url:
            lines.append(f'<a href="{issue.url}">Open in GitLab</a>')
        if issue.description:
            clean = _strip_html_entities(issue.description)
            if clean and len(clean) > 800:
                clean = clean[:800] + "..."
            if clean:
                lines.append(f"\n<b>Description:</b>\n<i>{_h(clean)}</i>")

        text = "\n".join(lines)
        if len(text) > MAX_MSG_LEN - 20:
            text = text[:MAX_MSG_LEN - 20] + "\n... (truncated)"
        await query.message.reply_text(text, parse_mode="HTML")

    except Exception as e:
        await query.message.reply_text(f"Error: {e}")


# ---------------------------------------------------------------------------
# PM Agent command handlers
# ---------------------------------------------------------------------------

async def _cmd_plan(update: Update, context: ContextTypes.DEFAULT_TYPE, bot: "DevTrackBot"):
    """Handle /plan <problem> -- start the PM agent flow."""
    if not context.args:
        await update.message.reply_text(
            "Usage: <code>/plan &lt;problem statement&gt;</code>\n\n"
            "Example: <code>/plan Build a user authentication system with login, "
            "signup, password reset, and session management</code>",
            parse_mode="HTML"
        )
        return

    problem = " ".join(context.args)
    chat_id = update.effective_chat.id
    _PENDING_PLANS[chat_id] = {"problem": problem, "plan": None}

    buttons = [
        [InlineKeyboardButton("Azure DevOps", callback_data=f"plan_platform:azure|{chat_id}")],
        [InlineKeyboardButton("GitLab", callback_data=f"plan_platform:gitlab|{chat_id}")],
        [InlineKeyboardButton("GitHub", callback_data=f"plan_platform:github|{chat_id}")],
        [InlineKeyboardButton("Cancel", callback_data=f"plan_cancel:{chat_id}")],
    ]

    keyboard = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(
        f"<b>PM Agent</b>\n\nProblem: <i>{_h(problem[:200])}</i>\n\nChoose target platform:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


async def _on_plan_platform_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: platform chosen — run LLM decomposition and show preview."""
    query = update.callback_query
    await query.answer()

    try:
        payload = query.data[len("plan_platform:"):]
        platform, chat_id_str = payload.split("|", 1)
        chat_id = int(chat_id_str)

        pending = _PENDING_PLANS.get(chat_id)
        if not pending:
            await query.edit_message_text("Session expired. Run /plan again.")
            return

        problem = pending["problem"]

        await query.edit_message_text(
            f"Decomposing for <b>{_h(platform)}</b>...\n\n"
            f"<i>{_h(problem[:150])}</i>",
            parse_mode="HTML"
        )

        from backend.pm_agent import PMAgent
        agent = PMAgent(platform=platform)
        plan = agent.decompose(problem)

        _PENDING_PLANS[chat_id]["plan"] = plan
        _PENDING_PLANS[chat_id]["platform"] = platform

        preview = agent.format_preview(plan)
        if len(preview) > 3000:
            preview = preview[:3000] + "\n... (truncated)"

        confirm_buttons = [
            [InlineKeyboardButton(
                f"Create all {plan.total_count} items",
                callback_data=f"plan_confirm:{chat_id}"
            )],
            [InlineKeyboardButton("Cancel", callback_data=f"plan_cancel:{chat_id}")],
        ]
        keyboard = InlineKeyboardMarkup(confirm_buttons)

        await query.edit_message_text(
            f"<b>Plan Preview</b> ({_h(platform)})\n\n<pre>{_h(preview)}</pre>",
            reply_markup=keyboard,
            parse_mode="HTML"
        )

    except ValueError as e:
        await query.edit_message_text(f"Failed to decompose: {_h(str(e))}", parse_mode="HTML")
    except Exception as e:
        await query.edit_message_text(f"Error: {e}")


async def _on_plan_confirmed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: user confirmed — create all items, report results."""
    query = update.callback_query
    await query.answer()

    try:
        chat_id = int(query.data.split(":", 1)[1])
        pending = _PENDING_PLANS.pop(chat_id, None)
        if not pending or not pending.get("plan"):
            await query.edit_message_text("Session expired. Run /plan again.")
            return

        plan = pending["plan"]
        platform = pending["platform"]

        await query.edit_message_text(
            f"Creating {plan.total_count} items in <b>{_h(platform)}</b>...",
            parse_mode="HTML"
        )

        progress_msg = await query.message.reply_text("Starting...", parse_mode="HTML")
        progress_lines = []

        async def on_progress(node, status):
            progress_lines.append(f"{_h(node.title[:40])}: {_h(status)}")
            if len(progress_lines) % 3 == 0:
                text = "\n".join(progress_lines[-10:])
                try:
                    await progress_msg.edit_text(f"<pre>{text}</pre>", parse_mode="HTML")
                except Exception:
                    pass

        from backend.pm_agent import PMAgent
        agent = PMAgent(platform=platform)
        created, failed = await agent.create_all(plan, on_progress=on_progress)

        lines = [
            f"<b>Done</b> — {len(created)} created, {len(failed)} failed",
            "",
        ]
        for node in created[:20]:
            url_part = f' <a href="{node.platform_url}">#{node.platform_id}</a>' if node.platform_url else ""
            lines.append(f"{_h(node.title[:50])}{url_part}")
        if len(created) > 20:
            lines.append(f"... and {len(created) - 20} more")

        if failed:
            lines.append(f"\n<b>Failed ({len(failed)}):</b>")
            for node, err in failed[:5]:
                lines.append(f"  {_h(node.title[:40])}: {_h(err[:60])}")

        text = "\n".join(lines)
        if len(text) > MAX_MSG_LEN - 20:
            text = text[:MAX_MSG_LEN - 20] + "\n... (truncated)"

        await progress_msg.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)

    except Exception as e:
        await query.message.reply_text(f"Error during creation: {e}")


async def _on_plan_cancelled(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: user cancelled plan."""
    query = update.callback_query
    await query.answer()
    try:
        chat_id = int(query.data.split(":", 1)[1])
        _PENDING_PLANS.pop(chat_id, None)
    except Exception:
        pass
    await query.edit_message_text("Plan cancelled.")
