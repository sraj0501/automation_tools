# DevTrack Documentation

> All documentation lives in `docs/`. Start here and follow the links.

---

## New User? Start Here

| Step | Guide |
|------|-------|
| 1. What is DevTrack? | [GETTING_STARTED.md](GETTING_STARTED.md) |
| 2. Install everything | [INSTALLATION.md](INSTALLATION.md) |
| 3. Run it for the first time | [QUICK_START.md](QUICK_START.md) |
| 4. All CLI commands | [CLI_REFERENCE.md](CLI_REFERENCE.md) |
| 5. All `.env` variables | [CONFIGURATION.md](CONFIGURATION.md) |

---

## Feature Guides

### Git & Commits
| Guide | What it covers |
|-------|---------------|
| [GIT_FEATURES.md](GIT_FEATURES.md) | Enhanced commits, conflict resolution, work update parsing |
| [GIT_COMMIT_WORKFLOW.md](GIT_COMMIT_WORKFLOW.md) | Detailed interactive AI commit workflow (Accept/Enhance/Regenerate) |
| [GIT_SAGE.md](GIT_SAGE.md) | Local LLM git agent — ask/do/interactive modes, undo, approval modes |
| [COMMIT_WORKFLOW_DESIGN.md](COMMIT_WORKFLOW_DESIGN.md) | **Planned redesign** — context-aware ticket ranking, shadow branches, approval TUI, in-terminal PM updates |

### Project Management Integrations
| Guide | What it covers |
|-------|---------------|
| [AZURE_DEVOPS.md](AZURE_DEVOPS.md) | Azure DevOps sync, webhooks, assignment poller, work item creation |
| [GITLAB.md](GITLAB.md) | GitLab sync, issue browsing, assignment poller, Telegram commands |
| [GITHUB.md](GITHUB.md) | GitHub sync, issue browsing, bidirectional sync, Telegram commands |
| [MULTI_REPO.md](MULTI_REPO.md) | Monitor multiple repos, each routed to its own PM platform via workspaces.yaml |
| [PM_AGENT.md](PM_AGENT.md) | AI decomposition of problems into Epic → Story → Task hierarchies |

### Productivity
| Guide | What it covers |
|-------|---------------|
| [TICKET_ALERTER.md](TICKET_ALERTER.md) | Background poller for GitHub, Azure DevOps, and Jira — OS + terminal notifications |
| [PROJECT_PLANNING.md](PROJECT_PLANNING.md) | AI project planning via `/newproject` — spec generation, team workloads, approval flow |
| [WORK_TRACKER.md](WORK_TRACKER.md) | Automatic session-based time tracking + AI EOD report with email delivery |

### Remote Control
| Guide | What it covers |
|-------|---------------|
| [TELEGRAM_BOT.md](TELEGRAM_BOT.md) | Full bot setup, all commands (Azure, GitLab, GitHub, PM Agent, scheduler) |

### System Integration
| Guide | What it covers |
|-------|---------------|
| [AUTOSTART.md](AUTOSTART.md) | Auto-start DevTrack at login — OS-aware (macOS launchd, Linux/WSL systemd, shell profile) |
| [MACOS_AUTOSTART.md](MACOS_AUTOSTART.md) | macOS launchd details (legacy reference) |

### AI & Personalization
| Guide | What it covers |
|-------|---------------|
| [LLM_GUIDE.md](LLM_GUIDE.md) | LLM provider setup (Ollama, OpenAI, Anthropic, Groq, LM Studio) |
| [PERSONALIZATION.md](PERSONALIZATION.md) | "Talk Like You" — learn your style from Teams, inject into all prompts |
| [LLM_STRATEGY.md](LLM_STRATEGY.md) | Multi-provider fallback architecture |

---

## Reference

| Guide | What it covers |
|-------|---------------|
| [CONFIGURATION.md](CONFIGURATION.md) | Every `.env` variable with type, default, and description |
| [CLI_REFERENCE.md](CLI_REFERENCE.md) | Every `devtrack` command with flags and examples |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Go daemon + Python bridge + IPC + SQLite architecture |
| [OFFLINE_RESILIENCE.md](OFFLINE_RESILIENCE.md) | Store-and-forward, health monitor, deferred commits |
| [ADVANCED_FEATURES.md](ADVANCED_FEATURES.md) | Reports, TUI, analytics, and other advanced features |
| [TUI_FLOWS.md](TUI_FLOWS.md) | Terminal user interface design and interaction flows |
| [VERIFICATION.md](VERIFICATION.md) | Manual step-by-step verification that everything is working |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Solutions to common problems, error messages, and edge cases |
| [VISION.md](VISION.md) | Project vision, roadmap, and planned features |
| [REFACTORING.md](REFACTORING.md) | Config philosophy — why there are no hardcoded defaults |

---

## Strategy

| Guide | What it covers |
|-------|---------------|
| [LAUNCH_STRATEGY.md](LAUNCH_STRATEGY.md) | **Governing doc** — wedge, positioning, first-run UX, channel sequence, risk register, decision framework |
| [TUI_NAVIGATION_DESIGN.md](TUI_NAVIGATION_DESIGN.md) | **Planned** — ESC=back, Ctrl+C=cancel, FlowController + RawInput architecture |

---

## For Developers

- **[CLAUDE.md](../CLAUDE.md)** — Architecture, build commands, key patterns, debugging guide. Start here if you want to contribute or modify DevTrack.

---

## docs/ File Index

```
docs/
├── INDEX.md                  ← you are here
│
├── Getting Started
│   ├── GETTING_STARTED.md    what is DevTrack, concepts, first-run checklist
│   ├── INSTALLATION.md       step-by-step install for macOS, Linux, Windows
│   ├── QUICK_START.md        get running in 15 minutes
│   ├── CLI_REFERENCE.md      all devtrack commands
│   └── CONFIGURATION.md      all .env variables
│
├── Git Features
│   ├── GIT_FEATURES.md       enhanced commits, conflict resolution, work parsing
│   ├── GIT_COMMIT_WORKFLOW.md interactive AI commit refinement workflow
│   └── GIT_SAGE.md           git-sage LLM agent
│
├── Integrations
│   ├── AZURE_DEVOPS.md       Azure DevOps sync, webhooks, API reference
│   ├── GITLAB.md             GitLab sync, issue management, poller
│   ├── GITHUB.md             GitHub sync, issue management, Telegram commands
│   ├── MULTI_REPO.md         Multi-repo monitoring via workspaces.yaml
│   ├── PM_AGENT.md           AI work item decomposition
│   ├── TELEGRAM_BOT.md       Telegram remote control
│   ├── AUTOSTART.md          Auto-start (OS-aware: launchd / systemd / shell profile)
│   └── MACOS_AUTOSTART.md    Auto-start on macOS login via launchd (legacy reference)
│
├── AI & Personalization
│   ├── LLM_GUIDE.md          provider setup and model config
│   ├── PERSONALIZATION.md    "Talk Like You" learning system
│   └── LLM_STRATEGY.md       multi-provider fallback architecture
│
└── Advanced & Reference
    ├── ARCHITECTURE.md       system design
    ├── OFFLINE_RESILIENCE.md store-and-forward, health monitoring
    ├── ADVANCED_FEATURES.md  reports, analytics, TUI
    ├── TUI_FLOWS.md          terminal UI design
    ├── REFACTORING.md        config philosophy
    ├── VISION.md             roadmap
    ├── VERIFICATION.md       manual verification steps
    └── TROUBLESHOOTING.md    debugging and common errors
```
