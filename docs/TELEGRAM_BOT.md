# Telegram Bot Setup Guide

Remote control DevTrack from your phone. Receive live notifications for commits, timer triggers, report generation, and webhook events.

## Phone Setup (Telegram Side)

### Step 1: Install Telegram

Download Telegram from the [iOS App Store](https://apps.apple.com/app/telegram-messenger/id686449807), [Google Play](https://play.google.com/store/apps/details?id=org.telegram.messenger), or [desktop](https://desktop.telegram.org/).

### Step 2: Create a Bot with @BotFather

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Choose a display name (e.g., "DevTrack Bot")
4. Choose a username -- must end in `bot` (e.g., `my_devtrack_bot`)
5. BotFather gives you a bot token — copy it for the next step

### Step 3: Get Your Chat ID

1. Open a conversation with your new bot and tap **Start**
2. Send `/start`
3. The bot replies with your chat ID — copy it

**Group chats:** If you want the bot in a group, add it to the group first, then send `/start` in the group. The group chat ID will be a negative number. Use that value in the config.

## Server Setup (DevTrack Side)

### Step 1: Install the Dependency

```bash
cd /path/to/automation_tools
uv add python-telegram-bot
```

### Step 2: Configure `.env`

Add these variables to your `.env` file:

```bash
# ── TELEGRAM BOT ──────────────────────────────────────────────

# Master switch -- set to true to enable the bot
TELEGRAM_ENABLED=true

# Bot token from @BotFather (required)
TELEGRAM_BOT_TOKEN=<your-bot-token>

# Comma-separated chat IDs authorized to run commands
# Leave empty to allow anyone (dev mode only -- not recommended)
TELEGRAM_ALLOWED_CHAT_IDS=<your-chat-id>

# Notification toggles
TELEGRAM_NOTIFY_COMMITS=true
TELEGRAM_NOTIFY_TRIGGERS=true
TELEGRAM_NOTIFY_HEALTH=true

# Auto-restart the bot process if it crashes
HEALTH_AUTO_RESTART_TELEGRAM=true
```

You can list multiple chat IDs separated by commas.

### Step 3: Restart DevTrack

```bash
devtrack restart
```

The daemon starts the Telegram bot as a child process automatically when `TELEGRAM_ENABLED=true`.

### Step 4: Verify

```bash
devtrack telegram-status
```

Then send `/status` to your bot on Telegram -- you should get a response with daemon status.

## Available Commands

| Command | Auth Required | Description |
|---------|:---:|-------------|
| `/start` | No | Show your chat ID (for initial setup) |
| `/help` | No | List all available commands |
| `/status` | Yes | Daemon status and service health |
| `/logs` | Yes | Last 20 log lines (use `/logs 30` for 30, max 50) |
| `/trigger` | Yes | Force an immediate work update trigger |
| `/pause` | Yes | Pause the scheduler |
| `/resume` | Yes | Resume the scheduler |
| `/queue` | Yes | Message queue statistics (pending/processed counts) |
| `/commits` | Yes | Deferred commit status by category |
| `/health` | Yes | Per-service health: IPC, Ollama, Azure DevOps, MongoDB, etc. |

## Live Notifications

The bot pushes events to all authorized chat IDs automatically. No polling required -- the bot receives events from the Go daemon over IPC in real time.

**Events pushed:**

| Event | Example Message | Config Variable |
|-------|-----------------|-----------------|
| Commit detected | `*Commit detected*` + branch + message (truncated to 200 chars) | `TELEGRAM_NOTIFY_COMMITS` |
| Timer trigger | `*Timer trigger fired* -- work update prompt sent` | `TELEGRAM_NOTIFY_TRIGGERS` |
| Report generated | `*Report generation triggered*` | `TELEGRAM_NOTIFY_TRIGGERS` |
| Webhook event | `*Webhook: azure_devops* -- work_item.updated` + title | `TELEGRAM_NOTIFY_HEALTH` |

Set any of these to `false` in `.env` to silence that category.

## Security

- **Bot token**: Treat it like a password. Never commit it to git. It is already in `.gitignore` via `.env`.
- **Chat ID whitelist**: Only chat IDs listed in `TELEGRAM_ALLOWED_CHAT_IDS` can execute commands. Unauthorized users see "Unauthorized. Your chat ID is not in the allowed list."
- **Open commands**: `/start` and `/help` work without authorization so you can discover your chat ID during setup.
- **Local execution**: The bot runs on your machine, not a cloud server. Telegram uses long-polling (the bot calls Telegram's API to check for updates) -- no inbound ports need to be opened.
- **Recommendation**: Enable 2FA on your Telegram account for an extra layer of protection.

## Architecture

```
┌──────────────────────┐
│  Telegram API        │
│  (cloud, polls only) │
└──────────┬───────────┘
           │ long-poll
┌──────────▼───────────┐
│  Telegram Bot        │  python -m backend.telegram
│  (child process)     │  Started by Go daemon alongside python_bridge
│                      │
│  Commands:           │  /status, /logs, /trigger, /pause, /resume
│    → subprocess      │    calls `devtrack` CLI
│  Commands:           │  /queue, /commits, /health
│    → SQLite direct   │    reads Data/db/ directly
│                      │
│  IPC Client          │  Connects to Go daemon TCP server
│    → receives events │  commit_trigger, timer_trigger, webhook_event
│    → broadcasts to   │  all authorized chat IDs
│      Telegram chats  │
└──────────────────────┘
```

- The Go daemon launches `python -m backend.telegram` as a managed child process (same pattern as the webhook server).
- The bot connects to the Go IPC server as a second client alongside `python_bridge.py`.
- Go broadcasts IPC events to ALL connected clients -- the bot receives commits, triggers, and webhooks natively.
- Commands like `/status` and `/logs` shell out to the `devtrack` CLI binary.
- Commands like `/queue`, `/commits`, and `/health` read the SQLite database directly for speed.
- The daemon health monitor checks the bot process liveness and auto-restarts it if `HEALTH_AUTO_RESTART_TELEGRAM=true`.

## Troubleshooting

**Bot not responding:**
- Run `devtrack telegram-status` to check if the process is alive.
- Check logs: `devtrack logs` -- look for lines containing "telegram".
- Verify `TELEGRAM_ENABLED=true` in `.env`.
- Make sure `python-telegram-bot` is installed: `uv run python -c "import telegram; print(telegram.__version__)"`.

**"Unauthorized" reply:**
- Your chat ID is not in `TELEGRAM_ALLOWED_CHAT_IDS`.
- Send `/start` to the bot to see your current chat ID, then add it to `.env` and restart.

**No notifications arriving:**
- Check that `TELEGRAM_NOTIFY_COMMITS`, `TELEGRAM_NOTIFY_TRIGGERS`, or `TELEGRAM_NOTIFY_HEALTH` are set to `true`.
- Verify the IPC connection succeeded -- look for "Connected to DevTrack IPC server" in logs.
- If IPC failed, the bot still handles commands but cannot push live events.

**Bot keeps restarting:**
- Check `HEALTH_AUTO_RESTART_TELEGRAM` -- if true, the daemon restarts the bot on crash.
- Look at the logs for the crash reason (Python traceback, import error, token error).

**Telegram API errors:**
- "Unauthorized": the bot token is wrong. Get a fresh token from @BotFather.
- Network errors: check internet connectivity from the machine running DevTrack.

**"python-telegram-bot not found":**
```bash
uv add python-telegram-bot
devtrack restart
```

**Running the bot standalone (for debugging):**
```bash
uv run python -m backend.telegram
```
This starts the bot outside the daemon, with logs printed to stdout.
