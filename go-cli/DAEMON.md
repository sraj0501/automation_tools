# Background Daemon

Process management system for running DevTrack in the background with start/stop/restart/status commands.

## Features

### ✅ Implemented

- **Process Management**: Start, stop, restart daemon
- **PID File Management**: Track running daemon process
- **Graceful Shutdown**: Clean shutdown on SIGTERM/SIGINT
- **Signal Handling**: Reload config on SIGHUP
- **Status Reporting**: Detailed daemon status information
- **Log Management**: File-based logging with rotation support
- **Pause/Resume**: Control scheduler without stopping daemon
- **CLI Interface**: User-friendly command-line interface

### 🎯 Core Components

1. **`daemon.go`**: Daemon process management
   - `Daemon`: Main daemon struct
   - Process lifecycle (start/stop/restart)
   - PID file management
   - Signal handlers
   - Graceful shutdown
   - Log management

2. **`cli.go`**: Command-line interface
   - User-friendly commands
   - Status formatting
   - Error handling
   - Help system

## Usage

### Build the Binary

```bash
cd go-cli
go build -o devtrack
```

### Daemon Commands

```bash
# Start the daemon
./devtrack start

# Check status
./devtrack status

# Pause scheduler (keeps git monitoring active)
./devtrack pause

# Resume scheduler
./devtrack resume

# View logs
./devtrack logs

# Stop the daemon
./devtrack stop

# Restart the daemon
./devtrack restart
```

### Status Output

```
📊 DevTrack Daemon Status
═════════════════════════

Status:     ✅ RUNNING
PID:        12345
Uptime:     2h 15m
Started:    Fri, 01 Nov 2025 10:30:00 IST
Triggers:   8
Last:       Fri, 01 Nov 2025 12:45:00 IST

Configuration:
  Config:   ~/.devtrack/config.yaml
  Logs:     ~/.devtrack/daemon.log
  PID file: ~/.devtrack/daemon.pid

Scheduler:
  Paused:       false
  Interval:     180 minutes
  Next trigger: 45 minutes

Work Hours:
  Enabled:      true
  Hours:        9:00 - 18:00
  In hours:     true
```

## Architecture

### Daemon Lifecycle

```
┌─────────────┐
│   Start     │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│ 1. Load Config      │
│ 2. Setup Logging    │
│ 3. Write PID File   │
│ 4. Start Monitoring │
│ 5. Setup Signals    │
└──────┬──────────────┘
       │
       ▼
┌─────────────────┐
│  Running Loop   │◄────┐
│                 │     │
│ • Git Monitor   │     │
│ • Scheduler     │     │
│ • Signal Handler│     │
└──────┬──────────┘     │
       │                │
       │  ┌────────────┴────────┐
       │  │ Signals:            │
       │  │ • SIGHUP → Reload   │──┘
       │  │ • SIGTERM → Shutdown│
       │  │ • SIGINT → Shutdown │
       │  └─────────────────────┘
       │
       ▼
┌─────────────────┐
│   Shutdown      │
│                 │
│ 1. Stop Monitor │
│ 2. Cancel Ctx   │
│ 3. Remove PID   │
│ 4. Close Logs   │
└─────────────────┘
```

### File Structure

```
~/.devtrack/
├── config.yaml      # Configuration
├── daemon.pid       # Process ID
├── daemon.log       # Application logs
└── commit.log       # Git commit log (from hooks)
```

## Configuration

The daemon uses `~/.devtrack/config.yaml`:

```yaml
version: 1.0.0

repositories:
  - name: myproject
    path: /path/to/repo
    enabled: true
    project: MyProject

settings:
  prompt_interval: 180  # 3 hours
  work_hours_only: false
  work_start_hour: 9
  work_end_hour: 18
  timezone: Asia/Kolkata
  log_level: info
  auto_sync: true

integrations:
  azure_devops:
    enabled: true
  github:
    enabled: true
  jira:
    enabled: false
```

## Signal Handling

### SIGTERM / SIGINT
- Triggers graceful shutdown
- Stops monitoring
- Cleans up resources
- Removes PID file

### SIGHUP
- Reloads configuration
- Applies new settings
- Continues running

Example:
```bash
# Reload config without restart
kill -HUP $(cat ~/.devtrack/daemon.pid)
```

## Process Management

### PID File

The daemon writes its process ID to `~/.devtrack/daemon.pid`:
```
12345
```

This allows:
- Checking if daemon is running
- Sending signals to daemon
- Preventing multiple instances

### Graceful Shutdown

On shutdown signal:
1. Log shutdown message
2. Stop Git monitoring
3. Stop scheduler
4. Cancel context
5. Remove PID file
6. Close log file
7. Exit cleanly

### Auto-restart

For production, use a process manager:

**systemd (Linux):**
```ini
[Unit]
Description=DevTrack Developer Automation Daemon
After=network.target

[Service]
Type=simple
User=%i
ExecStart=/usr/local/bin/devtrack start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**launchd (macOS):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.devtrack.daemon</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/devtrack</string>
        <string>start</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

## Logging

### Log Format

```
2025/11/01 10:30:00 daemon.go:78: Starting DevTrack daemon...
2025/11/01 10:30:01 git_monitor.go:45: Started monitoring Git repository: /path/to/repo
2025/11/01 10:30:01 scheduler.go:92: ✓ Scheduler started. Next trigger at: Fri, 01 Nov 2025 13:30:00 IST
2025/11/01 13:30:00 scheduler.go:245: 🔔 Timer trigger #1 at Fri, 01 Nov 2025 13:30:00 IST
```

### View Logs

```bash
# Last 50 lines (default)
./devtrack logs

# Tail logs in real-time
tail -f ~/.devtrack/daemon.log

# Filter for errors
grep ERROR ~/.devtrack/daemon.log

# Search for triggers
grep "trigger" ~/.devtrack/daemon.log
```

## CLI Commands Reference

### start
Starts the daemon in the background.

```bash
./devtrack start
```

**Output:**
```
🚀 Starting DevTrack daemon...
✓ Daemon started successfully
```

### stop
Stops a running daemon gracefully.

```bash
./devtrack stop
```

**Output:**
```
⏹️  Stopping DevTrack daemon...
✓ Daemon stopped successfully
```

### restart
Restarts the daemon (stop + start).

```bash
./devtrack restart
```

**Output:**
```
🔄 Restarting DevTrack daemon...
Stopping current instance...
⏹️  Stopping DevTrack daemon...
✓ Daemon stopped successfully
🚀 Starting DevTrack daemon...
✓ Daemon started successfully
```

### status
Shows detailed daemon status.

```bash
./devtrack status
```

See status output example above.

### pause
Pauses the scheduler (Git monitoring continues).

```bash
./devtrack pause
```

**Output:**
```
✓ Scheduler paused

Git monitoring is still active
Use 'devtrack resume' to resume scheduler
```

### resume
Resumes the scheduler.

```bash
./devtrack resume
```

**Output:**
```
✓ Scheduler resumed
```

### logs
Shows recent log entries.

```bash
./devtrack logs
```

**Output:**
```
📄 Last 50 log entries:
════════════════════════
2025/11/01 10:30:00 Starting DevTrack daemon...
2025/11/01 10:30:01 Git monitor started
...
```

### version
Shows version information.

```bash
./devtrack version
```

### help
Shows help message.

```bash
./devtrack help
```

## Testing

### Test Individual Components

```bash
# Test Git monitoring
go run . test-git

# Test scheduler
go run . test-scheduler

# Test configuration
go run . test-config

# Test integrated system
go run . test-integrated
```

### Manual Testing

```bash
# Build
go build -o devtrack

# Start daemon
./devtrack start &

# Check status
./devtrack status

# Pause scheduler
./devtrack pause

# Resume scheduler
./devtrack resume

# Stop daemon
./devtrack stop
```

## Integration Points

### Current Status
- ✅ Daemon implemented
- ✅ PID management
- ✅ Graceful shutdown
- ✅ Signal handling
- ✅ CLI interface
- ✅ Status reporting
- ✅ Log management
- ⏳ IPC communication (next)
- ⏳ Database logging (next)
- ⏳ System service integration

### Next Steps
1. Implement IPC for Go ↔ Python communication
2. Add SQLite database for trigger logging
3. Create systemd/launchd service files
4. Add daemon auto-start on boot
5. Implement log rotation
6. Add metrics collection

## Troubleshooting

### Daemon won't start
```bash
# Check if already running
./devtrack status

# Check logs
./devtrack logs

# Force stop if stuck
kill $(cat ~/.devtrack/daemon.pid)
rm ~/.devtrack/daemon.pid
```

### Can't find repository
```bash
# Run from repository directory
cd /path/to/your/repo
./devtrack start

# Or configure in ~/.devtrack/config.yaml
```

### Logs not showing
```bash
# Check log file exists
ls -la ~/.devtrack/daemon.log

# Check permissions
chmod 644 ~/.devtrack/daemon.log
```

## Future Enhancements

- [ ] Daemon auto-restart on crash
- [ ] Log rotation and compression
- [ ] Metrics and health checks
- [ ] Remote status API (HTTP endpoint)
- [ ] Multi-repository daemon instances
- [ ] Resource usage monitoring
- [ ] Integration with system notifications
- [ ] Web dashboard for status
