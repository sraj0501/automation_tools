# DevTrack

> Developer automation that handles the overhead so you can focus on coding.
> Monitors your Git activity, prompts for work updates, routes them through AI, and keeps your project management systems in sync — all running locally on your machine.

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
