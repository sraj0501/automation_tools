# DevTrack CLI Reference

Complete reference for all `devtrack` commands.

---

## Daemon Control

```bash
devtrack start          # Start the background daemon
devtrack stop           # Stop the daemon gracefully
devtrack restart        # Stop and restart (kills all sub-services, respawns clean)
devtrack status         # Show daemon status, uptime, PID, and service health
devtrack logs           # Show last 50 log lines
devtrack logs -f        # Follow log output in real time (like tail -f)
```

**Tip:** `devtrack restart` fully tears down and respawns the Python bridge, webhook server, Telegram bot, Azure assignment poller, and GitLab assignment poller.

---

## Scheduler

```bash
devtrack pause           # Pause timed work-update triggers (git monitoring continues)
devtrack resume          # Resume the scheduler
devtrack force-trigger   # Fire a work-update prompt immediately (no waiting)
devtrack skip-next       # Skip the next scheduled trigger
devtrack send-summary    # Generate and send the daily summary now
```

---

## Git (AI-Enhanced Commits)

```bash
devtrack git commit -m "message"           # AI-enhanced commit (up to 5 refinement attempts)
devtrack git commit -m "message" --dry-run # Preview AI suggestion without committing
devtrack git history                       # Show recent commit history
devtrack git messages                      # Alias for git history
```

See [GIT_COMMIT_WORKFLOW.md](GIT_COMMIT_WORKFLOW.md) for the full interactive workflow.

---

## Shell Integration

Skip the `devtrack` prefix — type `git commit` directly for monitored repos.

### Setup (one time)

```bash
# Add to ~/.zshrc or ~/.bashrc, then reload your shell
eval "$(devtrack shell-init)"
source ~/.zshrc
```

### Per-Repo Opt-In

```bash
devtrack enable-git    # Opt this repo in  — sets git config devtrack.enabled=true
devtrack disable-git   # Opt this repo out — removes git config devtrack.enabled
```

### Workspace Detection

```bash
devtrack is-workspace  # Exit 0 if CWD is a DevTrack workspace (used internally)
```

This command is called automatically by the shell `git()` function to check `workspaces.yaml`. Repos already in `workspaces.yaml` are intercepted without `devtrack enable-git`.

### Bypass

```bash
GIT_NO_DEVTRACK=1 git commit -m "message"   # Skip DevTrack for this one command
command git commit -m "message"             # Always calls real git
```

### What gets intercepted

| Command | Intercepted? |
|---------|-------------|
| `git commit` | Yes — routed through DevTrack AI enhancement |
| `git history` | Yes — shows DevTrack commit history |
| `git messages` | Yes — alias for git history |
| `git push`, `git pull`, `git status`, `git log`, … | No — always real git |

---

## git-sage Agent

```bash
# These commands run the git-sage LLM agent directly
uv run python -m backend.git_sage ask "how do I undo my last commit?"
uv run python -m backend.git_sage do  "squash my last 3 commits"
uv run python -m backend.git_sage interactive   # Persistent session (ask + do loop)
```

See [GIT_SAGE.md](GIT_SAGE.md) for full documentation.

---

## Azure DevOps

```bash
devtrack azure-check                      # Test config and connectivity
devtrack azure-list                       # List open work items assigned to you
devtrack azure-list --all                 # All work items (no state filter)
devtrack azure-list --state "Active,New"  # Filter by comma-separated states
devtrack azure-view <id>                  # Show full details for a work item
devtrack azure-sync                       # Full resync (clears cache, fetches all)
devtrack azure-sync --full               # Explicit full resync
devtrack azure-sync --hours 24           # Only items changed in last 24 h
```

See [AZURE_DEVOPS.md](AZURE_DEVOPS.md) for setup and configuration.

---

## GitLab

```bash
devtrack gitlab-check                        # Test config and connectivity
devtrack gitlab-list                         # List open issues assigned to you
devtrack gitlab-list --closed               # Include closed issues
devtrack gitlab-list --state <state>        # Filter by state (opened, closed, all)
devtrack gitlab-view <project_id> <iid>     # Show full details for an issue
devtrack gitlab-sync                         # Full resync (fetches all open issues)
devtrack gitlab-sync --full                 # Explicit full resync
devtrack gitlab-sync --hours 24            # Only issues updated in last 24 h
```

See [GITLAB.md](GITLAB.md) for setup and configuration.

---

## GitHub

```bash
devtrack github-check                        # Test config and connectivity
devtrack github-list                         # List open issues assigned to you
devtrack github-list --closed               # Include closed issues
devtrack github-list --state <state>        # Filter by state (open, closed, all)
devtrack github-view <number>               # Show full details for an issue
devtrack github-sync                         # Full resync (fetches all open issues)
devtrack github-sync --full                 # Explicit full resync
devtrack github-sync --hours 24            # Only issues updated in last 24 h
```

See [GITHUB.md](GITHUB.md) for setup and configuration.

---

## PM Agent (via Telegram)

The PM Agent is Telegram-only. Use `/plan` in your Telegram bot:

```
/plan Build a user authentication system
```

This opens a platform picker → LLM decomposes into Epic/Story/Task → shows a preview → confirm to create all items.

See [PM_AGENT.md](PM_AGENT.md) for full documentation.

---

## Offline Resilience

```bash
devtrack queue             # Show message queue stats (pending, processed, failed)
devtrack commits pending   # List deferred commits waiting for AI enhancement
devtrack commits review    # Review AI-enhanced deferred commits interactively
```

---

## Reports

```bash
devtrack preview-report [date]   # Preview today's report (or YYYY-MM-DD)
devtrack send-report <email>     # Email the daily report to an address
devtrack save-report [date]      # Save report to a file
devtrack db-stats                # Database statistics and analytics
devtrack stats                   # Alias for db-stats
```

---

## Personalized AI Learning

```bash
devtrack enable-learning [days]   # Enable learning (default: last 30 days)
devtrack learning-sync            # Delta sync — only new messages since last run
devtrack learning-sync --full     # Force full re-collection (ignore delta state)
devtrack learning-status          # Show consent status and sample count
devtrack show-profile             # Display your learned communication profile
devtrack test-response <text>     # Generate a personalized response (no auth needed)
devtrack revoke-consent           # Delete all learning data and revoke consent
devtrack learning-reset           # Wipe everything and start fresh
```

### Learning Cron

```bash
devtrack learning-setup-cron      # Install daily cron from LEARNING_CRON_SCHEDULE in .env
devtrack learning-cron-status     # Show cron entry and schedule settings
devtrack learning-remove-cron     # Remove the cron entry
```

See [PERSONALIZATION.md](PERSONALIZATION.md) for full documentation.

---

## Telegram Bot

```bash
devtrack telegram-status   # Show whether the Telegram bot process is alive
```

**In Telegram** (all require your chat ID to be in `TELEGRAM_ALLOWED_CHAT_IDS`):

| Command | Description |
|---------|-------------|
| `/start` | Get your chat ID (for initial setup) |
| `/help` | List all bot commands |
| `/status` | Daemon status and service health |
| `/logs [N]` | Last N log lines (default 20, max 50) |
| `/trigger` | Force a work-update trigger |
| `/pause` | Pause the scheduler |
| `/resume` | Resume the scheduler |
| `/queue` | Message queue statistics |
| `/commits` | Deferred commit status |
| `/health` | Per-service health check |
| `/azure` | List Azure work items from cache |
| `/azureissue <id>` | View a specific Azure work item |
| `/azurecreate` | Create a new Azure work item interactively |
| `/gitlab` | List GitLab issues from cache |
| `/gitlabissue <project_id> <iid>` | View a specific GitLab issue |
| `/gitlabcreate` | Create a new GitLab issue interactively |
| `/github` | List open GitHub issues assigned to you |
| `/githubissue <number>` | View a specific GitHub issue |
| `/githubcreate [bug\|feature\|task] <title>` | Create a new GitHub issue |
| `/plan <problem>` | Decompose a problem → Epic/Story/Task → create items |

---

## Info & Settings

```bash
devtrack version    # Show version information
devtrack help       # Show all commands with brief descriptions
devtrack settings   # Show config paths and key environment settings
```

---

## Environment Variables Quick Reference

All configuration comes from `.env`. Copy `.env_sample` to `.env` and fill in your values. Key groups:

| Group | Variables |
|-------|-----------|
| Paths | `PROJECT_ROOT`, `DEVTRACK_WORKSPACE`, `DATA_DIR` |
| IPC | `IPC_HOST`, `IPC_PORT`, `IPC_CONNECT_TIMEOUT_SECS` |
| LLM | `LLM_PROVIDER`, `OLLAMA_HOST`, `OLLAMA_MODEL` |
| Azure | `AZURE_DEVOPS_PAT`, `AZURE_ORGANIZATION`, `AZURE_PROJECT`, `EMAIL` |
| GitLab | `GITLAB_URL`, `GITLAB_PAT`, `GITLAB_PROJECT_ID` |
| GitHub | `GITHUB_TOKEN`, `GITHUB_OWNER`, `GITHUB_REPO` |
| Telegram | `TELEGRAM_ENABLED`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_CHAT_IDS` |
| PM Agent | `PM_AGENT_DEFAULT_PLATFORM`, `PM_AGENT_MAX_ITEMS_PER_LEVEL` |

See [CONFIGURATION.md](CONFIGURATION.md) for the complete variable reference.
