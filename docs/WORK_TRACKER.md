# Work Session Tracking & EOD Report

Automatic session-based time tracking — start a session, code as normal, and DevTrack logs every commit against the session. At end of day, generate a detailed AI report of what was achieved, what's still in progress, and what's pending tomorrow.

---

## Quick Start

### 1. Start a session

```bash
devtrack work start AUTH-42      # tied to a ticket/PR ref (optional)
devtrack work start              # no ticket ref — general session
```

### 2. Code as normal

Every `git commit` while the session is active is automatically attached to the session — no extra commands needed.

### 3. Stop the session

```bash
devtrack work stop
```

Duration is measured automatically from `started_at` to `ended_at`.

### 4. (Optional) Override the recorded time

```bash
devtrack work adjust 90          # "I was actually on this for 90 minutes"
```

The developer's override is stored in `adjusted_minutes`. The auto-measured `duration_minutes` is preserved for audit — both values are always in the database.

### 5. View today's sessions

```bash
devtrack work status
```

Shows the active session (if any) and all completed sessions for today with total time.

### 6. Generate the EOD report

```bash
devtrack work report             # terminal output
devtrack work report --email me@org.com   # terminal + email via MS Graph
```

---

## EOD Report

The report covers all sessions for the current day:

- **Session table** — ticket, effective time (adjusted or auto), number of commits
- **AI narrative** — 2-3 sentence summary of the day
- **Achievements** — what was completed
- **In progress** — items still open
- **Pending tomorrow** — inferred from open sessions and tickets

### Example output

```
EOD Report — 2026-03-28
========================================

Sessions:
  • 2h 15m  AUTH-42, 4 commit(s)
  • 45m [adjusted]  PROJ-88, 2 commit(s)
  • 30m  (general work)

Total time: 3h 30m

Summary:
Spent the morning completing the OAuth2 integration for AUTH-42 and
fixing a long-standing edge case in the token refresh flow. Afternoon
was split between a quick PROJ-88 bugfix and reviewing open PRs.

Achievements:
  ✅ OAuth2 flow fully working with Google (AUTH-42)
  ✅ Token refresh race condition fixed (PROJ-88)

In Progress:
  🔄 Unit tests for AUTH-42 provider setup

Pending Tomorrow:
  ⏳ Code review on PR #142 — approve or request changes
```

---

## Auto EOD Trigger

Set `EOD_REPORT_HOUR` to auto-generate and email the report daily:

```bash
EOD_REPORT_HOUR=18          # generate at 6 PM
EOD_REPORT_EMAIL=you@org.com
```

The scheduler auto-stops any active session before generating the report.

---

## Telegram Commands

| Command | Description |
|---------|-------------|
| `/workstart [ticket-ref]` | Start a session, optionally tied to a ticket |
| `/workstop` | Stop the active session |
| `/workadjust <minutes>` | Override time on the active or last session |
| `/workstatus` | Show active session + today's log |
| `/workreport [--email addr]` | Generate EOD report; optionally email it |

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `EOD_REPORT_HOUR` | `18` | Hour (24h) to auto-generate EOD report (0 = disabled) |
| `EOD_REPORT_EMAIL` | _(optional)_ | Default recipient for auto EOD emails |
| `WORK_SESSION_AUTO_STOP_MINUTES` | `0` | Auto-stop after N idle minutes (0 = disabled) |

Email delivery requires `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, and `AZURE_CLIENT_SECRET` for MS Graph auth (same credentials as other email features).

---

## Architecture

```
devtrack work start/stop/adjust/status/report
  │
  └── devtrack-bin/cli_work.go   (Go CLI handler)
         │
         ├── work_sessions table (SQLite, managed by database.go)
         │     started_at, ended_at, ticket_ref, commits (JSON),
         │     duration_minutes (auto), adjusted_minutes (override)
         │
         └── devtrack work report
               │
               └── python -m backend.work_tracker.eod_report_generator
                     │
                     ├── WorkSessionStore        (session_store.py)
                     ├── EODReportGenerator      (eod_report_generator.py)
                     └── EODEmailer              (eod_emailer.py)

python_bridge.py (auto-linking)
  handle_commit_trigger()
    → WorkSessionStore.append_commit(active_session_id, commit_hash)

  handle_timer_trigger()
    → pre-fills ticket_id from active session
    → passes active_session context to TUI prompt
```

---

## Implementation Files

```
devtrack-bin/
  ├── cli_work.go           — Go CLI: work start/stop/adjust/status/report
  └── database.go           — work_sessions table + 6 CRUD methods

backend/work_tracker/
  ├── __init__.py           — public exports
  ├── session_store.py      — WorkSessionStore (SQLite read/write)
  ├── eod_report_generator.py — EODReportGenerator, EODReport dataclass
  └── eod_emailer.py        — EODEmailer (MS Graph HTML email)

python_bridge.py            — auto-links commits; pre-fills ticket on timer trigger
```

---

## Time Adjustment Design

The system stores **two** time values per session:

| Field | Meaning |
|-------|---------|
| `duration_minutes` | Auto-measured: `ended_at − started_at` |
| `adjusted_minutes` | Developer override (NULL = use auto) |

`effective_duration()` returns `adjusted_minutes` if set, else `duration_minutes`. Reports always use the effective value, but both are accessible for audit/analytics.

---

## Troubleshooting

**Session not found after daemon restart**

Work sessions are stored in SQLite — they persist across restarts. Run `devtrack work status` to verify.

**Commits not attaching to session**

- Verify a session is active: `devtrack work status`
- Commits attach in `python_bridge.py`'s `handle_commit_trigger` — check daemon logs: `devtrack logs | grep "linked to work session"`

**EOD report shows no sessions**

- Confirm sessions were started today: `devtrack work status`
- Check the date: report uses today's date by default; pass `--date YYYY-MM-DD` to the Python module for another day

**Email not sending**

- Verify `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_SECRET` are set in `.env`
- Check daemon logs: `devtrack logs | grep EODEmailer`
