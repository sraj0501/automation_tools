# DevTrack

> Developer automation that handles the overhead so you can focus on coding.
> Monitors your Git activity, prompts for work updates, routes them through AI, and keeps your project management systems in sync — all running locally on your machine.

DevTrack is a **client-server tool**. The Go binary (`devtrack`) is a lean daemon/client (~5 MB, no Python required to install) that monitors git activity and handles scheduling. The Python backend is a separate deployable server that provides AI processing, integrations, and reporting. In the default "managed" mode the daemon spawns the Python process automatically; in "external" mode you run Python in Docker or in the cloud and point the daemon at it.

[![GitHub Release](https://img.shields.io/github/v/release/sraj0501/automation_tools?label=release)](https://github.com/sraj0501/automation_tools/releases/latest)

---

## What DevTrack Does

- **Watches your Git commits** and fires AI-enhanced work update prompts at the right moments
- **Zero-friction git workflow** — type `git commit` as normal; DevTrack intercepts it for monitored repos. No extra commands to remember. `git add` with no arguments automatically stages all changes (`git add .`).
- **Understands natural language** — "Working on PR #42 auth bug (2 hours)" extracts the ticket, time, and status automatically
- **Interactive ticket linking** — after logging work, a split-pane picker lists your open issues (arrow keys or j/k to navigate, full issue body visible on the right, `/` to filter, Enter to link)
- **Syncs to Azure DevOps, GitLab, and GitHub** — comments on matched work items, transitions states, creates missing items
- **Monitors multiple repos** — each repo routes to its own PM platform via `workspaces.yaml`
- **Learns your communication style** from Teams messages and writes updates in your voice
- **Runs 100% locally** — Ollama for AI, SQLite for storage, no cloud required
- **Works offline** — queues everything and syncs when connectivity returns
- **Remote-controllable** via a Telegram bot on your phone
- **OS-aware auto-start** — one command installs the right mechanism for your OS: launchd on macOS, systemd user service on Linux/WSL with systemd, or a shell profile block on WSL without systemd
- **Ticket Alerter** — polls GitHub, Azure DevOps, and Jira for assigned issues, new comments, review requests, and status changes; delivers macOS OS notifications and terminal output

---

## Documentation

**Start here:** [docs/INDEX.md](docs/INDEX.md)

| I want to… | Go to |
|-----------|-------|
| Understand what DevTrack is | [Getting Started](docs/GETTING_STARTED.md) |
| Install DevTrack | [Installation Guide](docs/INSTALLATION.md) |
| Run it for the first time | [Quick Start](docs/QUICK_START.md) |
| See all CLI commands | [CLI Reference](docs/CLI_REFERENCE.md) |
| Configure `.env` | [Configuration Reference](docs/CONFIGURATION.md) |
| Set up AI commits / git-sage | [Git Features](docs/GIT_FEATURES.md) · [git-sage](docs/GIT_SAGE.md) |
| Set up shell integration | [Git Features](docs/GIT_FEATURES.md) |
| Connect Azure DevOps | [Azure DevOps Guide](docs/AZURE_DEVOPS.md) |
| Connect GitLab | [GitLab Guide](docs/GITLAB.md) |
| Connect GitHub | [GitHub Guide](docs/GITHUB.md) |
| Monitor multiple repos | [Multi-Repo Guide](docs/MULTI_REPO.md) |
| Use the Telegram bot | [Telegram Bot Setup](docs/TELEGRAM_BOT.md) |
| Use the PM Agent (`/plan`) | [PM Agent Guide](docs/PM_AGENT.md) |
| Set up AI providers | [LLM Guide](docs/LLM_GUIDE.md) |
| Enable "Talk Like You" | [Personalization](docs/PERSONALIZATION.md) |
| Fix a problem | [Troubleshooting](docs/TROUBLESHOOTING.md) |
| Understand the architecture | [Architecture](docs/ARCHITECTURE.md) |
| Auto-start at login (all OS) | [Auto-Start Guide](docs/AUTOSTART.md) |
| Track time automatically (EOD report) | [Work Tracker](docs/WORK_TRACKER.md) |
| Get ticket alerts (GitHub / Azure / Jira) | [Ticket Alerter](docs/TICKET_ALERTER.md) |
| Plan a project with AI | [AI Project Planning](docs/PROJECT_PLANNING.md) |
| Contribute or modify DevTrack | [CLAUDE.md](CLAUDE.md) |

---

## Setup

### Option 1 — Download binary (recommended)

Pre-built binaries are published automatically on every release for macOS (Apple Silicon + Intel), Linux (amd64 + arm64), and Windows (amd64).

```bash
# macOS / Linux — download the Go daemon
curl -L https://github.com/sraj0501/automation_tools/releases/latest/download/devtrack_$(uname -s)_$(uname -m).tar.gz | tar xz
sudo mv devtrack /usr/local/bin/

# Print client-server setup instructions
devtrack install
```

All releases are listed at: https://github.com/sraj0501/automation_tools/releases

#### Local / managed mode (default)

The daemon spawns the Python backend as a subprocess automatically. No separate server needed.

```bash
git clone https://github.com/sraj0501/automation_tools.git   # Python source
cd automation_tools
uv sync                  # install Python dependencies
cp .env_sample .env
nano .env                # set PROJECT_ROOT, DEVTRACK_WORKSPACE, DATA_DIR, and required vars
# DEVTRACK_SERVER_MODE=managed  (default — no need to set explicitly)

devtrack start           # starts the Go daemon + Python backend together
devtrack status
```

#### Docker / external mode

Run the Python backend in a container; the Go daemon connects to it over HTTP.

```bash
docker compose up -d     # start Python backend + infrastructure (MongoDB, etc.)

# In .env on the host machine:
# DEVTRACK_SERVER_MODE=external
# DEVTRACK_SERVER_URL=http://localhost:8089

devtrack start           # Go daemon only — connects to the running Python server
devtrack status
```

### Option 2 — Build from source (developers / contributors)

```bash
git clone https://github.com/sraj0501/automation_tools.git
cd automation_tools
chmod +x setup_local.sh
./setup_local.sh
```

The script handles everything: dependency checks, Python env, spaCy model, Go binary build (`go build` — no bundle step), `~/.local/bin` install, and `.env` bootstrap.

See [Installation Guide](docs/INSTALLATION.md) for a manual walkthrough or Windows instructions.

To uninstall: `./uninstall.sh`

---

## Core Features

### AI-Enhanced Git Workflow

```bash
# After one-time shell setup: eval "$(devtrack shell-init)"
git add          # no args → stages everything (git add .)
git commit -m "fix auth redirect"
# → DevTrack intercepts for monitored repos → AI refines → Accept / Enhance / Regenerate
#   (pressing E gives the AI double the token budget for a more detailed message)
# → "Log this work? (y/n): y"
# → "How long did this take? (e.g. 2h, 30m) [Enter to skip]:"
# → Split-pane ticket picker opens: open issues on the left, full issue body on the
#   right. ↑/↓ or j/k to navigate, / to filter, Enter to link, n to create new, Esc to skip.
# → Commit synced as a comment on the selected issue.
# → "🚀 Push to origin/<branch>? (y/n)" — y pushes immediately, n prints the command.

# Or use devtrack directly (always works, no setup needed):
devtrack git commit -m "fix auth redirect"
```

### Shell Integration — Type `git commit` Natively

Add to `~/.zshrc` or `~/.bashrc` (one time):
```bash
eval "$(devtrack shell-init)"
```

Then opt repos in:
```bash
devtrack enable-git    # opt this repo in via git config (instant, no yaml edit)
# or add the repo to workspaces.yaml — interception is automatic
```

After that, `git commit`, `git history`, and `git messages` route through DevTrack transparently for monitored repos. `git add` with no arguments is also intercepted and defaults to `git add .` — supply paths explicitly to stage individual files as normal. Everything else (`git push`, `git pull`, `git status`, …) goes straight to real git — unaffected.

The setup is **self-maintaining**: `eval "$(devtrack shell-init)"` installs both a `git()` shell function (for commit interception) and a `devtrack()` wrapper that auto-reloads the shell functions whenever you run `devtrack start`, `devtrack restart`, or `devtrack enable-git`. No need to re-run `eval` or open a new terminal after updates.

Escape hatch for a single command: `GIT_NO_DEVTRACK=1 git commit -m "skip"`

### git-sage — Local LLM Git Agent

```bash
uv run python -m backend.git_sage do "squash my last 5 commits"
uv run python -m backend.git_sage ask "how do I rebase onto main?"
```

### Project Management — Azure DevOps, GitLab, GitHub

```bash
devtrack azure-list          # work items assigned to you
devtrack azure-sync          # pull everything from Azure
devtrack gitlab-list         # GitLab issues assigned to you
devtrack gitlab-view 12345 42
devtrack github-check        # connection status
devtrack github-list         # open issues/PRs assigned to you
devtrack github-list --closed
devtrack github-list --state all
devtrack github-view 99      # view issue or PR #99
devtrack github-sync         # pull recent activity (last 24h)
devtrack github-sync --full  # full sync
devtrack github-sync --hours 48
```

On any platform, when a commit creates a new issue it automatically includes the commit hash and message in the description and is auto-assigned to the authenticated user (overridable per workspace via `pm_assignee` in `workspaces.yaml`). Set `GITHUB_AUTO_UPDATE_DESCRIPTION=true` or `GITLAB_AUTO_UPDATE_DESCRIPTION=true` to also append commit info to existing matched issues. Milestone assignment is configured per workspace via `pm_milestone` in `workspaces.yaml` (not a global `.env` var).

### Multi-Repo Monitoring

```yaml
# workspaces.yaml — each repo routes to its own PM platform
workspaces:
  - name: work-api
    path: ~/work/api
    pm_platform: azure
    pm_assignee: "jane@example.com"    # override default assignee
    pm_iteration_path: "MyProject\\Sprint 5"  # Azure sprint
    pm_area_path: "MyProject\\Backend"         # Azure area
  - name: oss-lib
    path: ~/oss/my-lib
    pm_platform: github
    pm_milestone: 3                            # GitHub milestone number
```

```bash
devtrack workspace list                                           # all monitored repos + status
devtrack workspace add <name> <path> --pm azure|gitlab|github|jira|none  # add a repo; --pm sets PM platform
devtrack workspace remove <name>                                  # remove a repo
devtrack workspace enable <name>                                  # enable monitoring
devtrack workspace disable <name>                                 # disable monitoring
# add/remove/enable/disable automatically reload the running daemon — no manual reload needed
```

### PM Agent (via Telegram)

```
/plan Build a payment processing system
→ LLM decomposes → Epic + Stories + Tasks → Creates in Azure / GitLab / GitHub
```

### AI Project Planning (via Telegram)

```
/newproject
→ Pick platform (Azure / GitHub / GitLab)
→ Type requirements + deadline + your email in plain text
→ Select team members from live roster (multi-select keyboard)
→ AI fetches each developer's current workload automatically
→ Generates full YAML spec: features, stories, sprints, capacity analysis, risks
→ Spec emailed to PM with an Approve / Review link
→ PM approves (or requests changes iteratively) via web form or Telegram
→ On approval: sprints, milestones, epics, stories created with dependencies
```

Set `SPEC_REVIEW_BASE_URL=http://your-server:8089` in `.env` so the review link in emails points to the right host. The review form lives at `GET /spec/{id}/review` on the webhook server.

### Ticket Alerter

```bash
devtrack alerts            # show unread notifications (last 24 h)
devtrack alerts --all      # show all notifications
devtrack alerts --clear    # mark all as read
```

Background poller watches GitHub, Azure DevOps, and Jira for events relevant to you:

| Source | Events |
|--------|--------|
| GitHub | Assigned, review requested, comment on your issues |
| Azure DevOps | Assigned, comment added, state changed |
| Jira | Assigned to me, comment added, status changed |

Delivers macOS OS notifications (`osascript`) and terminal output. Configure via `.env`:
```
ALERT_ENABLED=true
ALERT_POLL_INTERVAL_SECS=300
ALERT_GITHUB_ENABLED=true
ALERT_AZURE_ENABLED=true
ALERT_JIRA_ENABLED=true
```

### Work Session Tracking

```bash
devtrack work start AUTH-42           # start tracking time on a ticket or PR
devtrack work stop                    # stop session — duration auto-measured
devtrack work adjust 90               # override recorded time to 90 minutes
devtrack work status                  # active session + today's completed sessions
devtrack work report                  # EOD report in terminal
devtrack work report --email me@org.com  # EOD report + email via MS Graph
```

While a session is active, every `git commit` automatically attaches its hash to the session — no manual time entry needed. At end of day an AI narrative summarises what was achieved, what's in progress, and what's pending tomorrow.

`adjusted_minutes` stores the developer's override; `duration_minutes` keeps the auto-measured value for audit. The EOD report uses the adjusted value when set.

Telegram: `/workstart [ticket]` · `/workstop` · `/workadjust <mins>` · `/workstatus` · `/workreport [--email addr]`

Configure via `.env`:
```
EOD_REPORT_HOUR=18                 # auto-generate report at 6 PM (0 = disabled)
EOD_REPORT_EMAIL=you@org.com       # recipient for auto EOD reports
WORK_SESSION_AUTO_STOP_MINUTES=0   # auto-stop after N idle minutes (0 = disabled)
```

### Personalized AI

```bash
devtrack enable-learning      # opt in to style learning from Teams
devtrack show-profile         # view your inferred writing style
devtrack test-response "Completed auth module"  # see it in action
```

---

## Architecture

DevTrack is split into two independently deployable components:

| Component | What it is | Language | Size |
|-----------|-----------|----------|------|
| `devtrack` binary | Daemon + CLI client | Go 1.20+ | ~5 MB — no Python required to install |
| Python backend | AI server | Python 3.12+ | Runs as subprocess (managed) or container (external) |

The Go daemon handles git monitoring, cron scheduling, the SQLite database, and the IPC server. The Python backend handles NLP, LLM calls, TUI prompts, project management integrations, Telegram, and report generation. They communicate over a TCP socket (default `127.0.0.1:35893`).

**Server modes** — set in `.env`:

| Mode | Config | Use case |
|------|--------|----------|
| `managed` (default) | `DEVTRACK_SERVER_MODE=managed` | Local dev — daemon spawns Python subprocess automatically |
| `external` | `DEVTRACK_SERVER_MODE=external` + `DEVTRACK_SERVER_URL=http://host:port` | Docker or cloud-hosted Python backend |

A `Dockerfile.server` is provided for containerising the Python backend.

## Technology

| Layer | Stack |
|-------|-------|
| Daemon / CLI | Go 1.20+, fsnotify, robfig/cron, modernc/sqlite |
| AI backend server | Python 3.12+, uv, spaCy, aiohttp |
| Local LLM | Ollama (default) — also OpenAI, Anthropic, Groq, LM Studio |
| Storage | SQLite (triggers/history), ChromaDB (RAG), optional MongoDB |
| Remote control | Telegram bot via python-telegram-bot |
| PM integrations | Azure DevOps REST API, GitLab REST API, GitHub REST API, Jira REST API |
| Observability | runtime-narrative — structured story/stage traces; auto-wraps webhook requests and produces failure reports |

---

## Privacy

All data stays on your machine. Ollama runs locally. External AI services (OpenAI, Anthropic, Groq) are optional — only the prompt text is sent, never full commit history or personal context. Learning from Teams requires explicit opt-in and can be deleted anytime.

---

## License

MIT License — see [LICENSE](LICENSE).
