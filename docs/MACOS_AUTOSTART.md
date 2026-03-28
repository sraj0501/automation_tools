# macOS Auto-Start with launchd

> **Note:** This page covers macOS-specific launchd details. For the cross-platform guide (macOS / Linux / WSL) see [AUTOSTART.md](AUTOSTART.md).

Automatically start the DevTrack daemon when you log in to macOS, using the native launchd service manager.

---

## What Is launchd?

launchd is macOS's built-in service manager — the same mechanism used by system daemons and login items. DevTrack registers itself as a **user-level LaunchAgent**, which means:

- It starts when **you** log in (not at system boot)
- It runs as your user account (same permissions as your terminal)
- It is managed per-user — it will not affect other users on the same machine
- Launch agents live in `~/Library/LaunchAgents/`

---

## Prerequisites

- The `devtrack` binary must be built and installed:
  ```bash
  cd devtrack-bin
  go build -o devtrack .
  cp devtrack ~/.local/bin/   # or wherever you keep binaries
  ```
- Your `.env` file must be fully configured (all required variables set)
- `DEVTRACK_ENV_FILE` must point to your `.env` file (the plist sets this automatically)

---

## Installation

```bash
devtrack launchd-install
```

This command:

1. Reads the plist template from `Data/configs/dev.devtrack.plist`
2. Substitutes the binary path and project root into the template
3. Copies the result to `~/Library/LaunchAgents/dev.devtrack.plist`
4. Runs `launchctl load ~/Library/LaunchAgents/dev.devtrack.plist` to register it immediately

After installation, DevTrack will start automatically the next time you log in, and it is also loaded immediately in the current session.

---

## Verification

Check that launchd registered the service:

```bash
launchctl list | grep devtrack
```

Expected output:
```
<PID>   0   dev.devtrack
```

If the PID column shows a number, the daemon is running. If it shows a dash, it is registered but not currently running.

Check that the DevTrack daemon itself is healthy:

```bash
devtrack status
```

---

## Plist Template Details

The template at `Data/configs/dev.devtrack.plist` configures the service with:

| Key | Value |
|-----|-------|
| `Label` | `dev.devtrack` |
| `RunAtLoad` | `true` — starts immediately when loaded |
| `KeepAlive` | `false` — does not auto-restart on exit |
| `EnvironmentVariables` | Sets `DEVTRACK_ENV_FILE` to your `.env` path |
| `WorkingDirectory` | Your `PROJECT_ROOT` |
| `StandardOutPath` | `Data/logs/launchd.log` |
| `StandardErrorPath` | `Data/logs/launchd.log` |

---

## Manual launchctl Commands

Useful commands for inspecting and controlling the service directly:

```bash
# Check if service is registered and running
launchctl list | grep devtrack

# Start the service manually (without waiting for next login)
launchctl start dev.devtrack

# Stop the service (does not remove it — it will restart on next login)
launchctl stop dev.devtrack

# Check the plist that was installed
cat ~/Library/LaunchAgents/dev.devtrack.plist
```

---

## Troubleshooting

### Daemon did not start after login

1. Check the launch log:
   ```bash
   tail -50 Data/logs/launchd.log
   ```

2. Verify the plist is present and well-formed:
   ```bash
   ls ~/Library/LaunchAgents/dev.devtrack.plist
   plutil ~/Library/LaunchAgents/dev.devtrack.plist
   ```

3. Verify `DEVTRACK_ENV_FILE` points to a readable `.env`:
   ```bash
   grep DEVTRACK_ENV_FILE ~/Library/LaunchAgents/dev.devtrack.plist
   ```

4. Try loading manually:
   ```bash
   launchctl load ~/Library/LaunchAgents/dev.devtrack.plist
   devtrack status
   ```

### "Service not found" from launchctl start

The service has not been loaded yet. Run:

```bash
launchctl load ~/Library/LaunchAgents/dev.devtrack.plist
```

### devtrack status shows "not running" after login

The daemon may have exited due to a config error. Check the log:

```bash
tail -100 Data/logs/launchd.log
```

Common causes: missing `.env` variable, wrong `PROJECT_ROOT`, or binary not found at the path embedded in the plist. Rebuild with `devtrack launchd-install` after fixing the issue.

---

## Uninstall

```bash
devtrack launchd-uninstall
```

This unloads the service from the current session and removes the plist from `~/Library/LaunchAgents/`. DevTrack will no longer start automatically on login. The binary and your data are not affected.

---

**Next steps:** See [Quick Start](QUICK_START.md) or [Configuration Reference](CONFIGURATION.md).
