# Auto-Start (OS-aware)

Automatically start the DevTrack daemon when you log in, using the right mechanism for your operating system.

---

## Quick Start

```bash
devtrack autostart-install    # Install and enable auto-start
devtrack autostart-status     # Verify it is registered
devtrack autostart-uninstall  # Remove auto-start at any time
```

DevTrack detects your OS and picks the appropriate mechanism automatically:

| OS | Mechanism | Location |
|----|-----------|----------|
| macOS | launchd LaunchAgent | `~/Library/LaunchAgents/dev.devtrack.plist` |
| Linux with systemd | systemd user service | `~/.config/systemd/user/devtrack.service` |
| WSL with systemd | systemd user service | `~/.config/systemd/user/devtrack.service` |
| WSL without systemd | Shell profile block | `~/.zshrc` or `~/.bashrc` |

---

## Prerequisites

- The `devtrack` binary must be built and on your `PATH` (or referenced by its full path)
- Your `.env` file must be fully configured (all required variables set)
- `PROJECT_ROOT` must be set in `.env`, or `devtrack` must be run from the project directory

---

## macOS — launchd

launchd is macOS's built-in service manager. DevTrack registers as a **user-level LaunchAgent**, which means it starts when _you_ log in and runs with your permissions.

### Install

```bash
devtrack autostart-install
# equivalent: devtrack launchd-install
```

This command:
1. Reads the plist template from `Data/configs/dev.devtrack.plist`
2. Substitutes the binary path and project root
3. Copies the result to `~/Library/LaunchAgents/dev.devtrack.plist`
4. Runs `launchctl load` to register and start the service immediately

### Status

```bash
devtrack autostart-status
# or directly:
launchctl list | grep devtrack
```

Expected output: `<PID>   0   dev.devtrack` — a number in the PID column means the daemon is running.

### Manual launchctl commands

```bash
launchctl start dev.devtrack   # Start without waiting for next login
launchctl stop  dev.devtrack   # Stop (will restart on next login)
cat ~/Library/LaunchAgents/dev.devtrack.plist
```

### Uninstall

```bash
devtrack autostart-uninstall
# equivalent: devtrack launchd-uninstall
```

---

## Linux — systemd user service

On a Linux system where systemd is the init process, DevTrack installs a **systemd user service** (`--user` scope), which starts at login and runs as your user account.

### Systemd detection

DevTrack checks for systemd by looking for:
- `/run/systemd/private` (most reliable)
- `/proc/1/comm` containing `systemd`
- A successful `pidof systemd`

### Install

```bash
devtrack autostart-install
```

This command:
1. Reads the service template from `Data/configs/dev.devtrack.service`
2. Substitutes the binary path, project root, and env file path
3. Writes the unit to `~/.config/systemd/user/devtrack.service`
4. Runs `systemctl --user daemon-reload`, `enable`, and `start`

### Status

```bash
devtrack autostart-status
# or directly:
systemctl --user status devtrack
```

### Manual systemctl commands

```bash
systemctl --user start devtrack
systemctl --user stop  devtrack
systemctl --user restart devtrack
journalctl --user -u devtrack -f   # Follow logs
```

### Uninstall

```bash
devtrack autostart-uninstall
```

This stops the service, disables it, removes the unit file, and reloads the systemd daemon.

---

## WSL (Windows Subsystem for Linux)

DevTrack detects WSL by reading `/proc/version` and checking for `microsoft` (case-insensitive).

### WSL with systemd

If your WSL distribution has systemd enabled (WSL 0.67.6+ with `systemd=true` in `/etc/wsl.conf`), DevTrack installs a systemd user service — the same as the Linux path above.

### WSL without systemd

When systemd is not available, DevTrack appends a startup block to your shell profile (`~/.zshrc` if it exists, otherwise `~/.bashrc`):

```bash
# DevTrack auto-start
DEVTRACK_ENV_FILE=/path/to/.env /path/to/devtrack start 2>/dev/null || true
# End DevTrack auto-start
```

The block is idempotent — running `autostart-install` again when the block is already present prints a warning and exits.

#### Install

```bash
devtrack autostart-install
```

After installation, re-source your profile to start DevTrack in the current session:

```bash
source ~/.zshrc   # or ~/.bashrc
```

#### Status

```bash
devtrack autostart-status
```

Shows whether the block is present in the profile file and runs `devtrack status` to show the daemon state.

#### Uninstall

```bash
devtrack autostart-uninstall
```

Removes the marker block from the profile file.

---

## Service Template Details

### `Data/configs/dev.devtrack.plist` (macOS)

| Key | Value |
|-----|-------|
| `Label` | `dev.devtrack` |
| `RunAtLoad` | `true` — starts immediately when loaded |
| `KeepAlive` | `false` — does not auto-restart on exit |
| `EnvironmentVariables` | Sets `DEVTRACK_ENV_FILE` to your `.env` path |
| `WorkingDirectory` | Your `PROJECT_ROOT` |
| `StandardOutPath` / `StandardErrorPath` | `Data/logs/launchd.log` |

### `Data/configs/dev.devtrack.service` (Linux / WSL with systemd)

| Setting | Value |
|---------|-------|
| `Type` | `oneshot` with `RemainAfterExit=yes` |
| `ExecStart` | `<binary> start` |
| `Environment` | `DEVTRACK_ENV_FILE=<path>` |
| `WorkingDirectory` | Your `PROJECT_ROOT` |
| `StandardOutput` / `StandardError` | `Data/logs/systemd.log` |
| `WantedBy` | `default.target` |

---

## Troubleshooting

### Daemon did not start after login (macOS)

```bash
tail -50 Data/logs/launchd.log
ls ~/Library/LaunchAgents/dev.devtrack.plist
plutil ~/Library/LaunchAgents/dev.devtrack.plist
```

Common causes: missing `.env` variable, wrong `PROJECT_ROOT`, or binary not found at the embedded path. Re-run `devtrack autostart-install` after fixing the issue.

### Daemon did not start after login (Linux/WSL systemd)

```bash
tail -50 Data/logs/systemd.log
systemctl --user status devtrack
journalctl --user -u devtrack --no-pager | tail -50
```

Check that `DEVTRACK_ENV_FILE` points to a valid, fully-configured `.env`.

### devtrack status shows "not running" (WSL no-systemd)

The profile block runs `devtrack start` in new interactive shell sessions only. Ensure you have re-sourced your profile or opened a new terminal window.

### "autostart-install already present" warning (WSL no-systemd)

The block was already appended on a previous install. Run `devtrack autostart-uninstall` first, then reinstall.

---

**Next steps:** See [Quick Start](QUICK_START.md) or [Configuration Reference](CONFIGURATION.md).
