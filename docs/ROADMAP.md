# DevTrack — Architecture & Distribution Roadmap

> **Last updated:** March 28, 2026
>
> This document captures the evolution from a single-machine tool to a distributed
> client-server product, including the planned server GUI, server TUI, and managed
> SaaS offering.  Feature-level planning lives in `docs/VISION.md`.

---

## Non-Negotiable Rules

### Rule 0 — Local-first, offline-capable, always

> **Everything must be possible to run locally, on a local model, completely
> offline. This is the core idea. It must never be broken by any change.**

Client-server is an **optional upgrade path** for developers who want it or need
it — not a replacement for local operation. Every feature that works on a managed
server must also work with `devtrack start` on a single laptop with no internet
connection.

```
Single laptop, no internet, local Ollama  →  100% of features work
                                              ALWAYS, in every release
```

Implications for every decision:
- `DEVTRACK_SERVER_MODE=managed` (local subprocess) is the **primary mode**, not a legacy fallback
- Ollama on localhost is a **first-class LLM backend**, not an afterthought
- SQLite is the **primary database** — no feature should require PostgreSQL or MongoDB to work
- No feature may add a hard dependency on a cloud service, an internet connection,
  or a remote server URL
- Degradation must always be graceful: if a cloud LLM is unreachable, fall back
  to local Ollama; if Ollama is down, fall back to raw text processing

### Rule 1 — devtrack CLI is always CLI/TUI — never a GUI

The Go binary (`devtrack`) is a **terminal-first tool**. Adding a GUI to it would
break the core premise: a developer's workflow lives in the terminal.

```
devtrack  →  CLI commands + optional TUI (Bubble Tea)
             NEVER a web UI, Electron app, or desktop GUI
```

The GUI lives on the **server side only** — it is an admin console for whoever
administers the server. Developers never interact with it in daily workflow.

---

## Current State (March 2026) — Everything Working Locally

The single-machine stack is feature-complete and production-ready:

```
Developer machine
  ├─ devtrack (Go binary, ~5 MB)
  │   ├─ Git monitoring (fsnotify, multi-repo)
  │   ├─ Scheduler (cron triggers)
  │   ├─ Work session tracking (SQLite)
  │   ├─ CLI: work, workspace, alerts, sage, …
  │   └─ IPC server (TCP 35893)
  │
  └─ Python backend (subprocess, same machine)
      ├─ python_bridge.py  ← IPC client, handles triggers
      ├─ NLP + LLM (Ollama / OpenAI / Anthropic / Groq)
      ├─ PM sync (Azure DevOps, GitHub, GitLab, Jira)
      ├─ Telegram bot
      ├─ Webhook server (FastAPI)
      ├─ Work session EOD reports + email
      ├─ Alert poller (GitHub + Azure + Jira)
      └─ AI project planning (/newproject)
```

**Distribution:** Go binary ships via GitHub Releases (GoReleaser, multi-platform).
Python backend is set up locally by the developer.

---

## The Problem This Roadmap Solves

Not every developer has:
- A powerful Mac capable of running Ollama + LLMs locally
- macOS at all (many teams use Linux/Windows)
- Time to manage a local Python server stack

**Goal:** The devtrack binary is a thin, fast client that any developer can download
and run. The AI/integration heavy-lifting runs on a shared server — either
self-hosted or as a managed SaaS offering.

---

## Phase CS-1 — IPC → HTTP (Core Infrastructure)

**Why it's needed first:** Everything else in this roadmap depends on this.
Currently Python connects *to* Go's TCP IPC server — that only works on the same
machine. For any remote deployment, Go must *send* to Python.

**The flip:**
```
TODAY (single machine only):
  Go TCP server ← Python connects in → push messages

AFTER CS-1 (distributed):
  Python HTTP server → Go POSTs trigger payloads to DEVTRACK_SERVER_URL
```

### What changes

**Python side** — new routes added to `backend/webhook_server.py` (FastAPI already running):
```
POST /trigger/commit      ← Go calls this on every commit
POST /trigger/timer       ← Go calls this on scheduler tick
GET  /health              ← Go polls this; marks server healthy/unhealthy
```

The existing `handle_commit_trigger()` / `handle_timer_trigger()` logic in
`python_bridge.py` moves into these route handlers verbatim — same logic,
different transport.

**Go side** — new HTTP sender in `devtrack-bin/`:
```go
// When DEVTRACK_SERVER_URL is set and non-local:
func (im *IntegratedMonitor) sendTriggerHTTP(payload TriggerPayload) error {
    resp, err := http.Post(GetServerURL()+"/trigger/commit", "application/json", body)
    // parse response, write outcomes to local SQLite
}
```

**Backward compatibility — Rule 0 is never broken:**

| Mode | Config | Behavior |
|---|---|---|
| **Local (default)** | `DEVTRACK_SERVER_MODE=managed` | Subprocess as today — zero change, works offline |
| Local external | `SERVER_MODE=external` + `SERVER_URL=http://localhost:8089` | HTTP to local Python process |
| Remote | `SERVER_MODE=external` + `SERVER_URL=https://aws-server` | HTTP to remote server |

`managed` mode **must always work** identically to how it works today. Any change
to CS-1 that degrades the single-machine experience is a regression, not a feature.

### User prompts in remote mode

When the server is remote, the Python TUI cannot open on the developer's terminal.
Two solutions (both implemented):

1. **Telegram** (primary for remote) — Python sends a Telegram message to the
   developer; they reply from their phone. Already works for all interactive flows.
2. **Go-side prompt** (fallback) — Go prompts the user in its own terminal before
   POSTing to Python. The HTTP payload includes the pre-filled response.

### Database boundary (no change needed for CS-1)

```
Go owns:    SQLite — work_sessions, trigger_history, commit_queue
Python owns: MongoDB — personalization, alerts, comms

Cross-boundary: Go includes active_session context IN the HTTP payload.
                Python returns results (actions taken, commit to link).
                Go writes outcomes to SQLite.
```

Python's `session_store.py` direct SQLite access is removed — it gets session
data from the request payload instead. This decouples the DB file path across machines.

**Files to create/modify:**
- `backend/webhook_server.py` — add `/trigger/commit`, `/trigger/timer`, `/health`
- `devtrack-bin/http_trigger.go` — Go HTTP client for sending triggers
- `devtrack-bin/daemon.go` — route to HTTP sender when `IsExternalServer()`
- `backend/work_tracker/session_store.py` — remove direct SQLite; accept session from payload
- `.env_sample` — no new vars needed (`DEVTRACK_SERVER_URL` already there)

---

## Phase CS-2 — Server TUI (Process Management)

**What:** A terminal UI for managing the Python backend server itself — aimed at
developers or ops who self-host the server.

**Not for end-users.** This is for whoever runs the server.

```
devtrack-server tui
  ┌─────────────────────────────────────────────────────┐
  │  DevTrack Server — Process Monitor                  │
  │─────────────────────────────────────────────────────│
  │  python_bridge     ● running  PID 12345  CPU 2%     │
  │  webhook_server    ● running  PID 12346  CPU 0%     │
  │  telegram_bot      ● running  PID 12347  CPU 0%     │
  │  alert_poller      ● running  PID 12348  CPU 0%     │
  │  ollama            ● running  :11434     GPU 45%    │
  │─────────────────────────────────────────────────────│
  │  Triggers today: 47  |  Commits processed: 23       │
  │  Last trigger: 14:32 |  Errors (24h): 0             │
  │─────────────────────────────────────────────────────│
  │  [r] restart process  [l] view logs  [q] quit       │
  └─────────────────────────────────────────────────────┘
```

**Tech:** Python + Textual (or Rich + curses). Reads from the server's own process
list, log files, and the `/health` endpoint added in CS-1.

**Key capabilities:**
- Live process status (running / crashed / restarting)
- CPU / memory per process
- Trigger throughput (commits/timers processed per hour)
- Error rate, last error
- Per-process log tail
- Restart individual processes
- Start / stop the full server stack

**Files to create:**
- `backend/server_tui/` — new module
  - `app.py` — Textual app entry point
  - `process_monitor.py` — reads `/proc` or `psutil` for process stats
  - `health_client.py` — polls `GET /health` endpoint
  - `log_viewer.py` — tails log files per process
- `pyproject.toml` — add `textual` or `rich` dependency

**Entry point:**
```bash
python -m backend.server_tui        # or: devtrack-server tui
```

---

## Phase CS-3 — Server GUI (Admin Console)

**What:** A web-based admin console for managing the server — users, permissions,
API keys, licenses. Runs as a separate FastAPI + lightweight frontend, served by
the Python backend.

**This is NOT for developers** using devtrack day-to-day. It is for whoever
administers the server (team lead, devops, SaaS admin).

### MVP scope

```
Admin Console  →  http://server-ip:8090/admin
  ├─ Users
  │   ├─ List / invite / remove users
  │   ├─ Per-user workspace permissions
  │   └─ API key management
  ├─ Server
  │   ├─ Process health (read-only, mirrors TUI)
  │   ├─ LLM provider config (which model, endpoint)
  │   └─ Integration credentials (Azure, GitHub, Jira tokens)
  ├─ Licenses
  │   ├─ License key entry
  │   ├─ Seat count / usage
  │   └─ Billing portal link (SaaS only)
  └─ Audit Log
      └─ Who did what, when
```

### Later scope (one-stop shop for server management)

Once the MVP is stable, the GUI expands to cover everything an admin needs:

- Full server configuration (all `.env` vars exposed as form fields)
- Workspace management across all users (read/write to workspaces.yaml per user)
- Trigger history and replay
- Alert rules management (which notifications go to whom)
- Webhook endpoint management
- Monitoring dashboards (charts from the analytics engine)
- Onboarding wizard for new self-hosted deployments

**What it will never do:**
- Replace the devtrack CLI for developers
- Show a Kanban board or task UI (that's a separate product decision)
- Require internet access (admin console works fully offline/self-hosted)

**Tech:**
- Backend: FastAPI routes under `/admin/` prefix in `backend/webhook_server.py`
- Auth: HTTP Basic Auth → JWT sessions (simple, no OAuth needed for self-hosted)
- Frontend: HTMX + minimal CSS (no React build step; renders server-side HTML)
  - OR: separate React SPA if complexity warrants it at that point
- Served on separate port (default `8090`) so the main trigger API (`8089`) is isolated

**Files to create:**
- `backend/admin/` — new module
  - `routes.py` — FastAPI router mounted at `/admin`
  - `auth.py` — session management
  - `user_manager.py` — CRUD for users + permissions
  - `license_manager.py` — license key validation + seat tracking
  - `templates/` — Jinja2 HTML templates (HTMX approach)
    - `dashboard.html`, `users.html`, `server.html`, `licenses.html`
  - `static/` — CSS + minimal JS
- `backend/db/admin_models.py` — SQLAlchemy models for users, sessions, licenses
- `docker-compose.yml` — expose port `8090` for admin console

---

## Phase CS-4 — Managed SaaS

**What:** DevTrack offers a hosted Python backend server. Developers pay for it
instead of running their own.

### User experience

```bash
# Developer downloads devtrack binary (free, always)
curl -L https://github.com/sraj0501/automation_tools/releases/latest/download/... | tar xz
sudo mv devtrack /usr/local/bin/

# Points to hosted server (paid plan)
echo "DEVTRACK_SERVER_URL=https://app.devtrack.io/api" >> .env
echo "DEVTRACK_API_KEY=dt_live_xxxx" >> .env
echo "DEVTRACK_SERVER_MODE=external" >> .env

# That's it — no Python, no Ollama, no local server
devtrack start
```

### Pricing model (proposed)

| Tier | Price | What's included |
|---|---|---|
| Solo | $0 | Self-hosted only; no support |
| Developer | $9/mo | 1 seat, hosted server, GPT-4o backend |
| Team | $29/mo per seat | Multi-seat, shared workspaces, admin console |
| Enterprise | Custom | SSO, on-prem option, SLA |

### Infrastructure

```
app.devtrack.io
  ├─ API Gateway (nginx)
  │   ├─ /api/trigger/commit   ← Go daemons POST here
  │   ├─ /api/trigger/timer
  │   ├─ /api/health
  │   └─ /admin/               ← Admin console (CS-3)
  │
  ├─ Python backend (containerized, per-tenant isolation)
  ├─ LLM router (OpenAI / Anthropic / Groq — no Ollama for SaaS)
  ├─ PostgreSQL (replaces per-tenant SQLite)
  └─ Redis (job queues, session cache)
```

### Go binary changes for SaaS

Minimal. The binary already supports `DEVTRACK_SERVER_URL`. One addition:
- `DEVTRACK_API_KEY` header added to all HTTP trigger requests for tenant auth
- `devtrack login` command — exchanges API key for session, verifies connectivity

---

## Phase CS-5 — GUI as Full Server Management Console

By this phase, the admin GUI (CS-3) has matured into the canonical interface for
everything server-side:

- Full workspace management across all registered developers on the server
- Project-level permissions (which users can see which repos/projects)
- Centralized LLM model routing (different tiers get different models)
- Usage analytics (how many triggers/day per user, LLM token consumption)
- Billing management integrated (for SaaS offering)
- White-label option for enterprise deployments

**The devtrack CLI remains unchanged** — it is the developer-facing tool and always
will be. The GUI is purely the admin/ops layer.

---

## Summary: What Lives Where

```
Developer machine (any OS, any spec):
  devtrack (Go binary) ─────────────────── always CLI/TUI, never GUI
    - Monitors git repos (local paths)
    - Runs scheduler
    - Holds local SQLite (work sessions, trigger history)
    - HTTP client → POSTs to DEVTRACK_SERVER_URL

DevTrack Server (self-hosted or SaaS):
  Python backend
    - HTTP API for triggers           (CS-1)
    - AI/NLP/LLM processing
    - PM integrations
    - Telegram bot (remote prompts)
    - Webhook receiver
    - TUI for server process mgmt     (CS-2)
    - Admin console GUI               (CS-3)
    - Multi-tenant, auth, licensing   (CS-4)

LLM layer (flexible):
    - Local Ollama (self-hosted, any machine Python can reach)
    - Managed Ollama server (team GPU box)
    - OpenAI / Anthropic / Groq (cloud, zero infra)
    - Configured via OLLAMA_HOST / LLM_PROVIDER — already works today
```

---

## Implementation Order

1. **CS-1** (IPC → HTTP) — unlock everything else; ~1 week of focused work
2. **CS-2** (Server TUI) — fast to build with Textual; useful for self-hosters
3. **CS-3 MVP** (Admin GUI — users + licenses) — needed before SaaS launch
4. **CS-4** (Managed SaaS) — infra + billing; can be built in parallel with CS-3
5. **CS-3 Full** (one-stop-shop) — ongoing expansion of admin console post-launch
