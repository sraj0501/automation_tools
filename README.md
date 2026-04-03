<div align="center">

# DevTrack

**The developer automation layer that lives between your terminal and your project management tools.**

*Watches your Git activity. Prompts at the right moments. Routes work updates through AI. Keeps Azure DevOps, GitHub, and GitLab in sync — all on your machine.*

[![GitHub Release](https://img.shields.io/github/v/release/sraj0501/automation_tools?label=release)](https://github.com/sraj0501/automation_tools/releases/latest)
[![Platforms](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-blue)](https://github.com/sraj0501/automation_tools/releases/latest)
[![License](https://img.shields.io/badge/license-Community-green)](TERMS.md)

![DevTrack demo](wiki/assets/demo.gif)

</div>

---

## The 30-second pitch

You finish a feature. You type `git commit`. That's where DevTrack wakes up.

It refines your commit message with AI, asks how long the work took, opens a split-pane picker so you can link to an open issue in one keypress, posts a comment on that issue, and offers to push — all before you've left the terminal. When the session ends, it generates an EOD report in your own writing style, learned from your Teams messages.

The Go daemon is a 5 MB binary. The Python backend runs as a subprocess. Nothing leaves your machine unless you want it to.

---

## Install

```bash
# macOS / Linux
curl -L https://github.com/sraj0501/automation_tools/releases/latest/download/devtrack_$(uname -s)_$(uname -m).tar.gz | tar xz
sudo mv devtrack /usr/local/bin/

# Clone the Python backend (required for AI and integrations)
git clone https://github.com/sraj0501/automation_tools.git
cd automation_tools
uv sync
cp .env_sample .env
nano .env          # set your API keys and PROJECT_ROOT

devtrack start
devtrack status
```

> Full walkthrough: [Installation Guide](docs/INSTALLATION.md) · [Quick Start](docs/QUICK_START.md)

---

## The core loop

```
You type: git commit -m "fix auth redirect"
                │
                ▼
        DevTrack intercepts
                │
          ┌─────┴─────┐
          │  AI refines │  → Accept / Enhance / Regenerate
          └─────┬─────┘
                │
        "Log this work? (y/n)"
                │
        "How long? (e.g. 2h, 30m)"
                │
        ┌────────────────┐
        │  Ticket picker  │  ↑/↓ to browse · / to filter · Enter to link
        │  (split pane)   │
        └────────┬───────┘
                 │
        Comment posted on issue
        Commit hash attached
                 │
        "Push to origin/branch? (y/n)"
```

Shell setup is one line, done once:

```bash
eval "$(devtrack shell-init)"    # add to ~/.zshrc or ~/.bashrc
devtrack enable-git              # opt this repo in
```

After that, `git commit` routes through DevTrack automatically for monitored repos. Everything else (`git push`, `git pull`, `git status`) goes straight to real git, unmodified. Escape hatch: `GIT_NO_DEVTRACK=1 git commit -m "skip"`.

> AI commit enhancement is only active when the daemon is running. If you stop it, `git commit` passes through with zero delay and no errors.

---

## What it connects to

| Integration | What DevTrack does |
|-------------|-------------------|
| **Azure DevOps** | Post commit comments, transition work item states, create missing items |
| **GitHub** | Comment on issues/PRs, sync recent activity, alert on review requests |
| **GitLab** | Comment on issues, list and view issues assigned to you |
| **Jira** | Alert on assignments, comments, and status changes *(alerter)* |
| **Microsoft Teams** | Learn your communication style for personalized AI output |
| **Outlook / MS Graph** | Send EOD reports by email |
| **Telegram** | Remote control from your phone — `/workstart`, `/workreport`, `/plan` |
| **Slack** | `/devtrack status`, `/devtrack trigger`, and more via Socket Mode |
| **Ollama / OpenAI / Anthropic / Groq** | AI commit messages, reports, conflict resolution, git-sage agent |

---

## Key features

### Multi-repo monitoring

```yaml
# workspaces.yaml
workspaces:
  - name: work-api
    path: ~/work/api
    pm_platform: azure
    pm_assignee: jane@example.com
    pm_iteration_path: "MyProject\\Sprint 5"
  - name: oss-lib
    path: ~/oss/my-lib
    pm_platform: github
    pm_milestone: 3
```

```bash
devtrack workspace list
devtrack workspace add my-project ~/code/project --pm github
```

### Work session tracking

```bash
devtrack work start AUTH-42    # start timing a ticket
devtrack work stop             # auto-measures duration
devtrack work report           # EOD narrative in terminal
devtrack work report --email me@org.com
```

Every `git commit` while a session is active automatically attaches its hash — no manual logging.

### git-sage — local LLM git agent

![git-sage standup demo](wiki/assets/standup-demo.gif)

```bash
uv run python -m backend.git_sage do "squash my last 5 commits"
uv run python -m backend.git_sage ask "how do I rebase onto main?"
```

Runs an agentic loop: plans operations, executes them, reads output, handles failures with rollback, only asks when genuinely ambiguous. Session approval dialog (auto / review / suggest-only), step history, and interactive undo built in.

### Personalized AI ("Talk Like You")

```bash
devtrack enable-learning        # opt in — learns from Teams messages
devtrack show-profile           # view your inferred writing style
devtrack test-response "Completed auth module"
```

Combines a style profile with ChromaDB RAG (actual examples of how you write) to personalize every commit message, work update, and report the system generates.

### Ticket alerter

```bash
devtrack alerts                 # unread notifications (last 24 h)
devtrack alerts --all
devtrack alerts --clear
```

Background poller watches GitHub, Azure DevOps, and Jira for assigned issues, new comments, review requests, and state changes. Delivers macOS OS notifications and terminal output.

### AI project planning (via Telegram)

```
/plan Build a payment processing system
→ Decomposes into Epic + Stories + Tasks
→ Creates everything in Azure / GitLab / GitHub

/newproject
→ Pick platform · Enter requirements + deadline
→ AI fetches team workload · Generates sprint YAML
→ PM approves via email link · Sprints created with dependencies
```

### Server management

```bash
devtrack server-tui    # live process monitor (CPU%, memory, health)
devtrack admin-start   # web admin console at localhost:8090/admin/
devtrack tui           # full-screen dashboard: overview, activity, workspaces, alerts
```

---

## Deployment modes

| Mode | How | Use case |
|------|-----|----------|
| **Managed** (default) | Daemon spawns Python automatically | Local dev |
| **External** | `DEVTRACK_SERVER_URL=http://host:port` | Docker / self-hosted backend |
| **Cloud** | `devtrack cloud login --url URL --key KEY` | Remote managed backend |

```bash
docker compose up -d   # starts Python backend + MongoDB, Redis, PostgreSQL
```

---

## Technology

| Layer | Stack |
|-------|-------|
| Daemon / CLI | Go 1.24+, fsnotify, robfig/cron, modernc/sqlite |
| AI backend | Python 3.12+, uv, spaCy, aiohttp |
| Local LLM | Ollama (default) · OpenAI · Anthropic · Groq · LM Studio |
| Storage | SQLite (app state), ChromaDB (RAG), optional MongoDB |
| Remote control | Telegram (python-telegram-bot) · Slack (slack-bolt Socket Mode) |
| PM integrations | Azure DevOps · GitLab · GitHub · Jira REST APIs |
| Admin console | FastAPI + HTMX, JWT auth |
| Observability | runtime-narrative — structured story/stage traces on every webhook request |

---

## Documentation

| I want to… | Go to |
|-----------|-------|
| Install DevTrack | [Installation Guide](docs/INSTALLATION.md) |
| Run it for the first time | [Quick Start](docs/QUICK_START.md) |
| See all CLI commands | [CLI Reference](docs/CLI_REFERENCE.md) |
| Configure `.env` | [Configuration Reference](docs/CONFIGURATION.md) |
| Set up AI commits / git-sage | [Git Features](docs/GIT_FEATURES.md) · [git-sage](docs/GIT_SAGE.md) |
| Connect Azure DevOps | [Azure DevOps Guide](docs/AZURE_DEVOPS.md) |
| Connect GitLab / GitHub | [GitLab](docs/GITLAB.md) · [GitHub](docs/GITHUB.md) |
| Monitor multiple repos | [Multi-Repo Guide](docs/MULTI_REPO.md) |
| Set up Telegram / Slack | [Telegram](docs/TELEGRAM_BOT.md) · [Slack](docs/SLACK_BOT.md) |
| Set up AI providers | [LLM Guide](docs/LLM_GUIDE.md) |
| Enable "Talk Like You" | [Personalization](docs/PERSONALIZATION.md) |
| Auto-start at login | [Auto-Start Guide](docs/AUTOSTART.md) |
| Track time / EOD report | [Work Tracker](docs/WORK_TRACKER.md) |
| Get ticket alerts | [Ticket Alerter](docs/TICKET_ALERTER.md) |
| Plan a project with AI | [AI Project Planning](docs/PROJECT_PLANNING.md) |
| Fix a problem | [Troubleshooting](docs/TROUBLESHOOTING.md) |
| Understand the architecture | [Architecture](docs/ARCHITECTURE.md) |
| Full documentation index | [docs/INDEX.md](docs/INDEX.md) |

---

## Testing

```bash
cd devtrack-bin && go test ./...          # Go layer
uv run pytest backend/tests/             # Python backend (133 tests)
uv run pytest backend/tests/ -k cs1     # CS-1 HTTP trigger suite
```

---

## Privacy

All data stays on your machine. Ollama runs locally. External AI services (OpenAI, Anthropic, Groq) are optional — only prompt text is sent, never commit history or personal context. Learning from Teams requires explicit opt-in and can be deleted at any time with `devtrack learning-reset`.

---

## License

DevTrack Community License — free for personal use and teams up to 10 users. Enterprise (11+ users) requires a paid license.

```bash
devtrack terms          # read the terms
devtrack terms --accept # accept non-interactively (e.g. in CI)
```

Full text: [TERMS.md](TERMS.md)
