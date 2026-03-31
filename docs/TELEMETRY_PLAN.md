# DevTrack Telemetry Plan

**Status**: Planned — not yet implemented
**Last Updated**: March 29, 2026

---

## Goals

1. Understand how many people download and actively use DevTrack
2. Track registered user growth (CS-4 cloud signups)
3. Know which features are actually used
4. Show all metrics live in the admin console dashboard
5. Respect local-first philosophy — telemetry is always opt-in, never required

---

## What We Get for Free (Zero Code)

GitHub Releases already tracks download counts per binary asset per release.

```bash
# Query download counts at any time
curl -s https://api.github.com/repos/sraj0501/automation_tools/releases \
  | jq '[.[] | {tag: .tag_name, downloads: [.assets[].download_count] | add}]'
```

Also available for free: star count, fork count, clone traffic (requires GitHub token, 14-day window only).

These get polled every 15 minutes by a background task and surfaced in the admin dashboard — no binary changes needed.

---

## Telemetry Architecture

### Three Tiers

```
Tier 1: Anonymous opt-in (Go binary)
  → install_id UUID + command events + heartbeat
  → POST /telemetry/event on the cloud server
  → controlled by devtrack telemetry on/off

Tier 2: Registered users (CS-4 cloud server)
  → devtrack cloud login already hits the server
  → api_keys table extended with created_at + last_seen_at
  → no extra work from the binary side

Tier 3: Server-side aggregates + live dashboard
  → SSE stream pushes live counters to admin console
  → GitHub download counts polled every 15 min
```

### Data Flow

```
Developer machine                     DevTrack Cloud Server
     │                                        │
     │  POST /telemetry/event  (opt-in)       │
     │ ─────────────────────────────────────► │ INSERT INTO telemetry_events
     │  {install_id, event, props}            │
     │                                        │  asyncio.Queue notified
     │  POST /trigger/...  (normal use)       │
     │ ─────────────────────────────────────► │ UPDATE api_keys SET last_seen_at
     │  X-DevTrack-API-Key header             │
     │                                        │
     │                          Admin browser │
     │                                    GET /admin/telemetry/stream  (SSE)
     │                                    ◄──────────────────────────────────
     │                                        │  event: counters  (every 5s)
     │                                        │  event: live_event  (on INSERT)
```

---

## Privacy Design

- **Default OFF**: telemetry disabled until user runs `devtrack telemetry on`
- **Anonymous**: install_id is a random UUID with no link to user identity, email, or machine name
- **No PII ever**: no repo paths, commit messages, file names, usernames, or API keys
- **Local-first safe**: binary works identically with telemetry on or off; failures are silent
- **Transparent**: `devtrack telemetry status` shows exactly what would be sent

### What Is Sent

| Event | Trigger | Payload (no PII) |
|---|---|---|
| `install` | First `devtrack telemetry on` | version, os, arch |
| `command` | Each CLI invocation | command name only (e.g. `work`, `tui`, `cloud`) |
| `heartbeat` | Daemon startup | version, active_features bitmask |
| `signup` | `devtrack cloud login` succeeds | version, os only |

### What Is Never Sent

- Repo paths or names
- Commit messages or hashes
- File names or diffs
- Usernames or emails
- API keys or tokens
- Workspace names or ticket IDs

---

## Data Model

### `telemetry_events` table (server SQLite / Postgres)

```sql
CREATE TABLE telemetry_events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    install_id   TEXT    NOT NULL,       -- random UUID; stable per install
    event        TEXT    NOT NULL,       -- "install"|"command"|"heartbeat"|"signup"
    props        TEXT    DEFAULT '{}',   -- JSON: {command, version, os, arch, features}
    received_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_telemetry_install  ON telemetry_events(install_id);
CREATE INDEX idx_telemetry_event    ON telemetry_events(event);
CREATE INDEX idx_telemetry_received ON telemetry_events(received_at);
```

### `api_keys` table extensions (already exists in admin.db)

```sql
ALTER TABLE api_keys ADD COLUMN install_id   TEXT;   -- linked at cloud login
ALTER TABLE api_keys ADD COLUMN last_seen_at TEXT;   -- updated per authenticated request
-- created_at already exists
```

### Aggregate queries (no materialized tables needed)

```sql
-- Signups today
SELECT COUNT(*) FROM api_keys WHERE date(created_at) = date('now');

-- DAU (unique install_ids active today)
SELECT COUNT(DISTINCT install_id) FROM telemetry_events
WHERE date(received_at) = date('now');

-- MAU
SELECT COUNT(DISTINCT install_id) FROM telemetry_events
WHERE received_at > datetime('now', '-30 days');

-- Command histogram (last 30 days)
SELECT json_extract(props, '$.command') AS cmd, COUNT(*) AS n
FROM telemetry_events WHERE event = 'command'
  AND received_at > datetime('now', '-30 days')
GROUP BY cmd ORDER BY n DESC;

-- Active registered users (seen in last 7 days)
SELECT COUNT(*) FROM api_keys
WHERE last_seen_at > datetime('now', '-7 days');
```

---

## Real-Time Dashboard (SSE + HTMX)

The existing admin console (FastAPI + Jinja2 + HTMX) gets a live telemetry panel driven by Server-Sent Events.

### SSE Endpoint

```python
# backend/telemetry/stream.py

_event_queue: asyncio.Queue = asyncio.Queue()  # shared between writer and SSE generator

async def push_live_event(event: dict):
    """Called by /telemetry/event handler after each INSERT."""
    await _event_queue.put(event)

@router.get("/admin/telemetry/stream")
async def telemetry_stream(request: Request, _=Depends(require_admin)):
    async def generator():
        last_counter_push = 0.0
        while not await request.is_disconnected():
            now = asyncio.get_event_loop().time()

            # Push aggregate counters every 5 seconds
            if now - last_counter_push >= 5:
                stats = await _compute_live_stats()
                stats["github_downloads"] = _github_download_cache.total
                yield {"event": "counters", "data": json.dumps(stats)}
                last_counter_push = now

            # Drain live event queue (non-blocking)
            while not _event_queue.empty():
                ev = _event_queue.get_nowait()
                yield {"event": "live_event", "data": json.dumps(ev)}

            await asyncio.sleep(0.5)

    return EventSourceResponse(generator())
```

### Dashboard HTML (HTMX SSE extension)

```html
<!-- One persistent SSE connection; HTMX handles reconnect -->
<div hx-ext="sse" sse-connect="/admin/telemetry/stream">

  <!-- Counter panel: server returns rendered HTML fragment on each "counters" event -->
  <div id="stats-panel"
       sse-swap="counters"
       hx-swap="outerHTML">
    <!-- initial render from Jinja2 -->
  </div>

  <!-- Live event feed: new rows prepended as they arrive -->
  <table>
    <tbody id="live-feed"
           sse-swap="live_event"
           hx-swap="afterbegin">
    </tbody>
  </table>

</div>
```

The SSE endpoint returns **HTML fragments**, not raw JSON, so HTMX swaps them directly — no JavaScript needed on the frontend.

### GitHub Download Counts (15-min polling)

```python
# backend/telemetry/github_stats.py

_github_download_cache = {"total": 0, "by_release": {}, "updated_at": None}

async def _poll_github_downloads_loop():
    while True:
        try:
            counts = await _fetch_github_release_downloads()
            _github_download_cache.update(counts)
        except Exception:
            pass  # stale cache is fine
        await asyncio.sleep(900)  # 15 min (GitHub caches anyway)

# Mounted at app startup:
@app.on_event("startup")
async def start_github_poller():
    asyncio.create_task(_poll_github_downloads_loop())
```

---

## New CLI Commands (Go binary)

```
devtrack telemetry on      Enable telemetry; generate install_id if not present
devtrack telemetry off     Disable telemetry (install_id retained for re-enable)
devtrack telemetry status  Show: enabled/disabled, install_id preview, what would be sent
```

### `~/.devtrack/telemetry.json` (chmod 0600)

```json
{
  "enabled": true,
  "install_id": "a3f8c2d1-...",
  "opted_in_at": "2026-03-29T10:00:00Z"
}
```

---

## New Files to Create

### Go (`devtrack-bin/`)

| File | Purpose |
|---|---|
| `telemetry.go` | `TelemetryConfig`, `LoadTelemetryConfig()`, `SaveTelemetryConfig()`, `Track(event, props)` (non-blocking goroutine POST), `handleTelemetry()` CLI dispatcher |

### Python (`backend/telemetry/`)

| File | Purpose |
|---|---|
| `__init__.py` | Package init |
| `store.py` | `TelemetryStore`: INSERT event, aggregate queries (DAU, MAU, signups, command histogram) |
| `router.py` | FastAPI router: `POST /telemetry/event`, `GET /admin/telemetry/stream` (SSE) |
| `github_stats.py` | Background poller for GitHub Releases download counts |
| `stream.py` | `asyncio.Queue` shared state, `push_live_event()`, SSE generator |

### Modified files

| File | Change |
|---|---|
| `devtrack-bin/cli.go` | Add `"telemetry"` case + `Track("command", ...)` call in Execute() |
| `devtrack-bin/cloud.go` | Call `Track("signup", ...)` after successful cloud login |
| `devtrack-bin/daemon.go` | Call `Track("heartbeat", ...)` at daemon startup |
| `backend/webhook_server.py` | Mount telemetry router; start GitHub poller at startup |
| `backend/admin/routes.py` | Add telemetry stats to dashboard context; add SSE stream link |
| `backend/admin/templates/dashboard.html` | Add SSE-powered live telemetry panel |
| `backend/admin/user_manager.py` | Add `install_id`, `last_seen_at` to api_keys; update `last_seen_at` on auth |
| `.env_sample` | Add `TELEMETRY_ENABLED`, `GITHUB_REPO_SLUG` |

---

## New `.env_sample` Variables

```bash
# Telemetry
TELEMETRY_ENABLED=true              # Enable /telemetry/event endpoint on the server
GITHUB_REPO_SLUG=sraj0501/automation_tools  # For GitHub download count polling
```

---

## Implementation Phases

### Phase 1 — Server-side foundation (1 day)
1. `backend/telemetry/store.py` — `telemetry_events` table + CRUD
2. `backend/telemetry/router.py` — `POST /telemetry/event` endpoint
3. `backend/telemetry/github_stats.py` — GitHub download count poller
4. Mount router in `webhook_server.py`
5. Extend `api_keys` table with `last_seen_at`, `install_id`

### Phase 2 — Real-time admin dashboard (1 day)
1. `backend/telemetry/stream.py` — SSE generator + asyncio.Queue
2. `GET /admin/telemetry/stream` SSE endpoint
3. Admin dashboard template: SSE-powered stats panel + live event feed

### Phase 3 — Go binary instrumentation (1 day)
1. `devtrack-bin/telemetry.go` — config file, `Track()` helper
2. `devtrack telemetry on/off/status` commands
3. Wire `Track()` into cli.go, cloud.go, daemon.go

### Phase 4 — Polish (half day)
1. First-run opt-in prompt (non-blocking, can dismiss)
2. `devtrack telemetry status` output showing what would be sent
3. Retention metrics (D1/D7/D30 cohort analysis based on install events)

---

## Verification Checklist

```bash
# 1. Server receives events
curl -X POST https://myserver.com/telemetry/event \
  -H "Content-Type: application/json" \
  -d '{"install_id":"test-123","event":"command","props":{"command":"work"}}'
# → 200 OK

# 2. Admin dashboard shows live data
# Open /admin → telemetry panel updates every 5s

# 3. Live event feed
# Run devtrack work start in another terminal
# → new row appears in admin dashboard within 1s

# 4. GitHub download counts
# Check /admin → download count matches GitHub releases page

# 5. Opt-in flow
devtrack telemetry on
devtrack telemetry status   # shows: enabled, install_id: a3f8c2d1-…, events: command, heartbeat

# 6. Opt-out is clean
devtrack telemetry off
# → no more POSTs; binary works identically
```
