# DevTrack

> Developer automation that handles the overhead so you can focus on coding.
> Monitors your Git activity, prompts for work updates, routes them through AI, and keeps your project management systems in sync — all running locally on your machine.

---

## What DevTrack Does

- **Watches your Git commits** and fires AI-enhanced work update prompts at the right moments
- **Understands natural language** — "Working on PR #42 auth bug (2 hours)" extracts the ticket, time, and status automatically
- **Syncs to Azure DevOps, GitLab, and GitHub** — comments on matched work items, transitions states, creates missing items
- **Monitors multiple repos** — each repo routes to its own PM platform via `workspaces.yaml`
- **Learns your communication style** from Teams messages and writes updates in your voice
- **Runs 100% locally** — Ollama for AI, SQLite for storage, no cloud required
- **Works offline** — queues everything and syncs when connectivity returns
- **Remote-controllable** via a Telegram bot on your phone

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
| Contribute or modify DevTrack | [CLAUDE.md](CLAUDE.md) |

---

## Setup

```bash
git clone https://github.com/sraj0501/automation_tools.git
cd automation_tools
chmod +x setup_local.sh
./setup_local.sh
```

The script handles everything: dependency checks, Python env, spaCy model, Go binary build, `~/.local/bin` install, and `.env` bootstrap.

See [Installation Guide](docs/INSTALLATION.md) for a manual walkthrough or Windows instructions.

To uninstall: `./uninstall.sh`

---

## Core Features

### AI-Enhanced Git Workflow

```bash
devtrack git commit -m "fix auth redirect"
# → AI refines the message with branch/PR context → Accept / Enhance / Regenerate
```

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
# GitHub: managed via Telegram /github, /githubissue, /githubcreate
```

### Multi-Repo Monitoring

```yaml
# workspaces.yaml — each repo routes to its own PM platform
workspaces:
  - name: work-api
    path: ~/work/api
    pm_platform: azure
  - name: oss-lib
    path: ~/oss/my-lib
    pm_platform: github
```

```bash
devtrack workspace list       # all monitored repos + status
devtrack workspace add <path> --name my-repo --platform gitlab
```

### PM Agent (via Telegram)

```
/plan Build a payment processing system
→ LLM decomposes → Epic + Stories + Tasks → Creates in Azure / GitLab / GitHub
```

### Personalized AI

```bash
devtrack enable-learning      # opt in to style learning from Teams
devtrack show-profile         # view your inferred writing style
devtrack test-response "Completed auth module"  # see it in action
```

---

## Technology

| Layer | Stack |
|-------|-------|
| Daemon | Go 1.20+, fsnotify, robfig/cron, modernc/sqlite |
| AI bridge | Python 3.12+, uv, spaCy, aiohttp |
| Local LLM | Ollama (default) — also OpenAI, Anthropic, Groq, LM Studio |
| Storage | SQLite (triggers/history), ChromaDB (RAG), optional MongoDB |
| Remote control | Telegram bot via python-telegram-bot |
| PM integrations | Azure DevOps REST API, GitLab REST API, GitHub REST API |

---

## Privacy

All data stays on your machine. Ollama runs locally. External AI services (OpenAI, Anthropic, Groq) are optional — only the prompt text is sent, never full commit history or personal context. Learning from Teams requires explicit opt-in and can be deleted anytime.

---

## License

MIT License — see [LICENSE](LICENSE).
