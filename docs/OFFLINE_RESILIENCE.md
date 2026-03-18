# Offline-First Resilience

DevTrack's Go daemon works as a resilient local agent that continues operating when services are unavailable and syncs when they recover. This is critical for the future client/server split where the Go binary runs on the work PC and Python runs remotely.

---

## Overview

Three core subsystems provide offline resilience:

| Subsystem | Purpose | Key File |
|-----------|---------|----------|
| **Store-and-Forward Queue** | Saves IPC messages when Python is offline, delivers on reconnect | `devtrack-bin/queue.go` |
| **Deferred Commits** | Queues commits for AI enhancement when Ollama is down | `devtrack-bin/deferred_commit.go` |
| **Health Monitoring** | Checks all services periodically, auto-restarts crashed processes | `devtrack-bin/health.go` |

---

## Store-and-Forward Message Queue

### Problem

Previously, when a commit or timer trigger fired while the Python bridge was disconnected, the IPC message was silently dropped. The trigger was logged to SQLite, but the actual processing (NLP parsing, task updates, user prompts) never happened.

### Solution

`MessageQueue` in `queue.go` intercepts all IPC sends. If the send fails (no clients connected), the message is stored in SQLite's `message_queue` table. A background goroutine periodically checks for reconnected clients and drains pending messages.

### Flow

```
Trigger fires
    |
    v
MessageQueue.SendOrQueue(msg)
    |
    +-- ipcServer.SendMessage(msg)
    |       +-- Success -> done
    |       +-- ErrNoClients -> fall through
    |
    +-- Enqueue in SQLite (message_queue table)
                |
        Drain goroutine (every QUEUE_DRAIN_INTERVAL_SECS)
            -> Check HasClients()
            -> Fetch pending messages
            -> Send each via IPC
            -> Mark sent or increment retry count
```

### Database Table

```sql
CREATE TABLE message_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_type TEXT NOT NULL,
    message_id TEXT NOT NULL,
    payload TEXT NOT NULL,        -- Full JSON IPCMessage
    status TEXT DEFAULT 'pending', -- pending, sent, failed
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 10,
    last_error TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `QUEUE_DRAIN_INTERVAL_SECS` | 10 | How often to check for clients and drain |
| `QUEUE_MAX_RETRIES` | 10 | Max retries before marking permanently failed |
| `QUEUE_RETENTION_DAYS` | 7 | Days to keep sent messages before cleanup |

### CLI

```bash
devtrack queue    # Show pending/failed/sent counts and pending message details
```

---

## Deferred Commits

### Problem

When running `devtrack git commit -m "message"`, if AI enhancement fails (Ollama down, network error), the user sees "AI enhancement unavailable" and can only accept the unenhanced message or cancel. There's no option to come back to it later.

### Solution

Two new options in the commit workflow:

1. **`--no-enhance` flag**: Skip AI entirely, commit with original message immediately
2. **`[Q]ueue` option**: When AI fails, queue the commit (message + diff + metadata) in SQLite for later enhancement and review

### Workflow

```
devtrack git commit -m "my change"
    |
    +-- AI available -> normal enhance/accept/regenerate loop
    |
    +-- AI unavailable ->
            [A]ccept unenhanced message
            [E]nhance (retry)
            [R]egenerate
            [Q]ueue for AI enhancement later   <-- NEW
            [C]ancel

If user picks [Q]:
    -> Captures: git diff --cached, branch, files, message
    -> Stores in deferred_commits SQLite table
    -> User continues working (no commit made)

Later, when AI is back:
    devtrack commits pending     # Check status
    devtrack commits review      # Interactive: Accept enhanced / Use original / Discard
```

### Skip AI Entirely

```bash
devtrack git commit -m "quick fix" --no-enhance
# Commits immediately with original message, no AI interaction
```

### Database Table

```sql
CREATE TABLE deferred_commits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_message TEXT NOT NULL,
    diff_patch TEXT,              -- git diff --cached output
    branch TEXT,
    repo_path TEXT,
    files_changed TEXT,           -- JSON array
    status TEXT DEFAULT 'pending', -- pending, enhanced, committed, expired
    enhanced_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `DEFERRED_COMMIT_EXPIRY_HOURS` | 72 | Hours before pending commits are auto-expired |

### CLI Commands

```bash
devtrack commits pending    # List all pending and enhanced deferred commits
devtrack commits review     # Interactive review of enhanced commits
                            # Options: [A]ccept enhanced, [O]riginal message, [S]kip, [D]iscard
```

### Internal Command

```bash
# Called by devtrack-git-wrapper.sh (not for direct use)
echo "$DIFF" | devtrack commit-queue --message "msg" --branch "main" --repo "/path" --files "a.go,b.go"
```

---

## Health Monitoring

### Problem

The daemon had no visibility into service health. Python bridge or webhook server could crash without detection. `devtrack status` only showed PID info.

### Solution

`HealthMonitor` in `health.go` runs a background goroutine that checks all services at a configurable interval and writes results to the `health_snapshots` SQLite table.

### Services Checked

| Service | How Checked | Auto-Restart |
|---------|-------------|--------------|
| **Python IPC** | `ipcServer.HasClients()` + client count | No (restarts bridge instead) |
| **Python Bridge** | `syscall.Kill(pid, 0)` process liveness | Yes |
| **Ollama** | `HTTP GET OLLAMA_HOST/api/tags` (2s timeout) | No |
| **Azure DevOps** | Config presence check (PAT + org + project set?) | No |
| **Webhook Server** | Process liveness check | Yes |
| **MongoDB** | `net.DialTimeout("tcp", host:port, 2s)` | No |

### Status Values

| Status | Meaning |
|--------|---------|
| `up` | Service is running and responsive |
| `down` | Service is not reachable or process is dead |
| `degraded` | Service responds but with errors |
| `unconfigured` | Required config variables not set |

### Auto-Restart

When Python bridge or webhook server process dies, the health monitor calls a restart callback. Restarts are rate-limited to prevent restart loops:

- Maximum `HEALTH_MAX_RESTARTS_PER_HOUR` restarts per service per hour
- Old restart timestamps are pruned each check cycle
- Restart runs in a goroutine to avoid blocking other checks

### Database Table

```sql
CREATE TABLE health_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service TEXT NOT NULL,
    status TEXT NOT NULL,
    latency_ms INTEGER DEFAULT 0,
    details TEXT,         -- JSON with service-specific info
    checked_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `HEALTH_CHECK_INTERVAL_SECS` | 30 | Seconds between health check cycles |
| `HEALTH_AUTO_RESTART_PYTHON` | true | Auto-restart Python bridge if it dies |
| `HEALTH_AUTO_RESTART_WEBHOOK` | true | Auto-restart webhook server if it dies |
| `HEALTH_MAX_RESTARTS_PER_HOUR` | 3 | Max auto-restarts per service per hour |

---

## Enhanced Status Dashboard

`devtrack status` now shows a comprehensive health dashboard:

```
DevTrack Daemon        * Running (PID 12345, uptime 4h 32m)

Services:
  Python IPC           * Connected (latency: 3ms)
  Python Bridge        * Connected
  Ollama               * Connected (latency: 45ms)
  Azure DevOps         * Connected
  Webhook Server       o Not configured
  MongoDB              * Connected (latency: 2ms)

Sync Queue:            0 pending, 0 failed
Deferred Commits:      1 enhanced (ready for review)

Scheduler:             every 30m, next in 12m
Work Hours:            9:00-18:00 (active)
```

Status icons:
- `*` (green) = up
- `*` (red) = down
- `*` (yellow) = degraded
- `o` (gray) = unconfigured

---

## New IPC Changes

### Sentinel Error

`ErrNoClients` is now returned by `IPCServer.SendMessage()` when no clients are connected (previously returned `nil` silently). This enables the queue to detect and handle offline scenarios.

### New Methods

| Method | Purpose |
|--------|---------|
| `HasClients() bool` | Check if any IPC clients are connected |
| `ClientCount() int` | Get number of connected clients |

### New Message Types

| Type | Direction | Purpose |
|------|-----------|---------|
| `ping` | Go -> Python | Health check latency measurement |
| `pong` | Python -> Go | Health check response |

---

## All Configuration Variables

```bash
# Add to .env (all have sensible defaults)
HEALTH_CHECK_INTERVAL_SECS=30
HEALTH_AUTO_RESTART_PYTHON=true
HEALTH_AUTO_RESTART_WEBHOOK=true
HEALTH_MAX_RESTARTS_PER_HOUR=3
QUEUE_DRAIN_INTERVAL_SECS=10
QUEUE_MAX_RETRIES=10
QUEUE_RETENTION_DAYS=7
DEFERRED_COMMIT_EXPIRY_HOURS=72
```

---

## File Reference

| File | Purpose |
|------|---------|
| `devtrack-bin/queue.go` | MessageQueue: store-and-forward with SQLite backing |
| `devtrack-bin/health.go` | HealthMonitor: periodic service checks + auto-restart |
| `devtrack-bin/deferred_commit.go` | DeferredCommitManager: queue/review/execute deferred commits |
| `devtrack-bin/database.go` | 3 new tables + 18 CRUD methods |
| `devtrack-bin/config_env.go` | 8 new config accessor functions |
| `devtrack-bin/ipc.go` | ErrNoClients, HasClients(), ClientCount(), ping/pong |
| `devtrack-bin/integrated.go` | Queue-aware trigger dispatch |
| `devtrack-bin/daemon.go` | Health monitor lifecycle, auto-restart callbacks |
| `devtrack-bin/cli.go` | Enhanced status, queue/commits/commit-queue commands |
| `devtrack-bin/main.go` | New command routing |
| `devtrack-git-wrapper.sh` | --no-enhance flag, [Q]ueue option |
| `.env_sample` | 8 new offline resilience variables |

---

## Troubleshooting

### Messages stuck in queue

```bash
devtrack queue                    # Check pending count
devtrack status                   # Check if Python IPC is connected
devtrack restart                  # Restart daemon to reconnect
```

The drain goroutine runs every `QUEUE_DRAIN_INTERVAL_SECS` seconds. Messages are retried up to `QUEUE_MAX_RETRIES` times. Permanently failed messages can be inspected in the SQLite database.

### Health monitor not showing services

The health monitor starts with the daemon. If `devtrack status` shows no services section, the daemon may be running old code. Restart it:

```bash
devtrack stop && devtrack start
```

### Deferred commits expired

Commits older than `DEFERRED_COMMIT_EXPIRY_HOURS` (default 72h) are auto-expired. To change:

```bash
# In .env
DEFERRED_COMMIT_EXPIRY_HOURS=168  # 7 days instead of 3
```

### Auto-restart not working

Check the daemon log for rate-limit messages:

```bash
devtrack logs | grep "restart skipped"
```

If you see "X restarts in last hour (max Y)", the rate limit is being hit. Investigate why the process keeps dying rather than increasing the limit.
