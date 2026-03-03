# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**DevTrack** is a developer automation tool that monitors Git activity and scheduled timers, prompting developers for work updates and routing them through an AI pipeline to update project management systems and generate reports.

## Build & Run Commands

### Go daemon (devtrack-bin/)
```bash
cd devtrack-bin
go build -o devtrack .          # Build binary
go test ./...                   # Run all Go tests
go vet ./...                    # Run Go linter
```

### Python backend
```bash
uv sync                         # Install/sync dependencies (uv manages the venv)
uv run pytest backend/tests/    # Run all Python tests
uv run pytest backend/tests/test_nlp_parser.py  # Run a single test file
uv run python validate_env_sample.py            # Validate .env keys match .env_sample
```

### Running the daemon locally
```bash
export PROJECT_ROOT="/path/to/automation_tools"
export DEVTRACK_ENV_FILE="$PROJECT_ROOT/.env"
devtrack start &                # Start background daemon
devtrack status                 # Verify it's running
devtrack logs                   # View recent log output
```

## Architecture

The system has two main runtime components communicating over a TCP socket (default `127.0.0.1:35893`, configurable via `IPC_HOST`/`IPC_PORT` in `.env`):

```
Git commits / cron timer
        │
        ▼
┌──────────────────┐     TCP IPC (JSON)     ┌──────────────────────────┐
│  Go Daemon       │ ──────────────────────▶ │  Python Bridge           │
│  devtrack-bin/   │                         │  python_bridge.py        │
│  - git_monitor   │                         │  - NLP parsing (spaCy)   │
│  - scheduler     │                         │  - LLM enhancement       │
│  - ipc (server)  │ ◀────────────────────── │  - TUI user prompts      │
│  - database      │    task_update / ack    │  - Report generation     │
│  - cli           │                         │  - Project mgmt APIs     │
└──────────────────┘                         └──────────────────────────┘
        │                                              │
        ▼                                              ▼
  SQLite (Data/db/)                        Azure DevOps / GitHub / Jira
  PID/logs (Data/)                         Microsoft Graph (Teams/Email)
```

### Go layer (`devtrack-bin/`)
| File | Purpose |
|---|---|
| `main.go` | Entry point; routes CLI args or delegates `git` subcommand to shell wrapper |
| `cli.go` | All CLI command implementations (`start`, `stop`, `status`, `logs`, etc.) |
| `daemon.go` | Lifecycle management (PID file, signals, Python bridge process) |
| `integrated.go` | `IntegratedMonitor` — wires together git monitor, scheduler, and IPC server |
| `git_monitor.go` | fsnotify-based Git repository watcher; fires `commit_trigger` on new commits |
| `scheduler.go` | Cron-based periodic trigger using robfig/cron; fires `timer_trigger` |
| `ipc.go` | TCP IPC server (Go side); JSON-delimited messages, one handler per `MessageType` |
| `database.go` | SQLite via modernc.org/sqlite; stores trigger history and task updates |
| `config.go` | YAML config struct (`Data/configs/config.yaml`); all runtime values via `config_env.go` |
| `config_env.go` | All `.env` key accessors for Go — the single source of truth for env var names |
| `learning.go` | Personalized AI learning consent and profile management |

### Python layer (`backend/` + `python_bridge.py`)
| Module | Purpose |
|---|---|
| `python_bridge.py` | Entry point started by Go daemon; connects to IPC server and dispatches triggers |
| `backend/config.py` | Centralized config — all modules use `backend.config.get()`, not `os.getenv()` directly |
| `backend/ipc_client.py` | TCP IPC client (Python side); mirrors message types from Go's `ipc.go` |
| `backend/nlp_parser.py` | spaCy-based parser for commit/user text → structured task data |
| `backend/description_enhancer.py` | Ollama-based description enhancement and categorization |
| `backend/user_prompt.py` | Terminal TUI for interactive work-update prompts |
| `backend/daily_report_generator.py` | AI-enhanced daily/weekly report generation with multiple output formats |
| `backend/task_matcher.py` | Fuzzy + semantic matching of natural language to tracked tasks |
| `backend/llm/` | Multi-provider LLM abstraction: `provider_factory.py` builds a fallback chain (primary → OpenAI/Anthropic → Ollama) |
| `backend/jira/client.py` | Jira REST API client |
| `backend/github/pr_analyzer.py` | GitHub PR analysis |
| `backend/azure/` | Azure DevOps work item fetching and updating |
| `backend/msgraph_python/` | Microsoft Graph integration (Teams chat, Outlook, sentiment) |

## Configuration

All configuration flows from a single `.env` file. There are **no hardcoded fallback values** for paths or credentials.

- Go reads env vars via `config_env.go` (loaded with `joho/godotenv`)
- Python reads via `backend/config.py` functions (`get()`, `get_int()`, `get_bool()`, `get_path()`)
- `DEVTRACK_ENV_FILE` overrides `.env` location; if unset, Go requires `.env` in the working directory
- Runtime data lives under `Data/` (db, logs, reports, pids) — paths configurable via `DATA_DIR`, `DATABASE_DIR`, etc.

The LLM provider is selected by `LLM_PROVIDER` (`ollama` | `openai` | `anthropic`). Providers with available credentials are added as automatic fallbacks in `backend/llm/provider_factory.py`.

## Key Patterns

- **IPC message protocol**: JSON-newline-delimited over TCP. Message types are defined in both `devtrack-bin/ipc.go` (`MessageType` constants) and `backend/ipc_client.py` (`MessageType` enum) — keep them in sync when adding new trigger types.
- **Python optional imports**: All Python subsystems (NLP, TUI, LLM, report generator) are imported with `try/except` and individually gated; the bridge degrades gracefully if a dependency is missing.
- **Tests**: Python tests use `uv run pytest`. The `conftest.py` adds the repo root to `sys.path`. Tests that change the LLM provider must call `reset_provider_cache()` before/after to avoid cross-test contamination.
- **`devtrack git commit` workflow**: Uses `devtrack-git-wrapper.sh` with AI-enhanced iterative refinement. Supports up to 5 attempts with options to Accept, Enhance, Regenerate, or Cancel. Explicit `--dry-run` flag for preview-only mode. See `GIT_COMMIT_WORKFLOW.md` for detailed user guide.
