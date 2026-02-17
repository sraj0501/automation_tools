#!/bin/bash
# Run DevTrack locally (outside Docker)

REPO_PATH="/home/sraj/Documents/GitHub/udemy_multi_api"
DEVTRACK_DIR="$HOME/.devtrack"
WORK_DIR="/home/sraj/Documents/GitHub/automation_tools"
DEVTRACK_CLI="devtrack-cli"

echo "🚀 Starting DevTrack Locally"
echo "======================================"
echo "Repository: $REPO_PATH"
echo "Config Dir: $DEVTRACK_DIR"
echo "======================================"

# Kill any existing processes
pkill -f "devtrack-cli" 2>/dev/null
pkill -f "python_bridge.py" 2>/dev/null
sleep 1

# Clear old logs
> "$DEVTRACK_DIR/daemon.log"

# Start the Go daemon in the background
echo "Starting Go daemon..."
cd "$WORK_DIR/devtrack"
./"$DEVTRACK_CLI" start --repo="$REPO_PATH" >> "$DEVTRACK_DIR/daemon.log" 2>&1 &
DAEMON_PID=$!
echo "Daemon started (PID: $DAEMON_PID)"

# Wait for daemon to initialize
sleep 3

# Check if daemon is running
if ps -p $DAEMON_PID > /dev/null; then
    echo "✅ Daemon is running"
else
    echo "❌ Daemon failed to start"
    tail -20 "$DEVTRACK_DIR/daemon.log"
    exit 1
fi

# Show recent logs
echo ""
echo "📋 Recent daemon logs:"
echo "--------------------------------------"
tail -15 "$DEVTRACK_DIR/daemon.log"

echo ""
echo "======================================"
echo "✅ DevTrack running locally!"
echo "====================================="
echo "Commands:"
echo "  tail -f ~/.devtrack/daemon.log    - Watch logs"
echo "  ps aux | grep devtrack             - Check processes"
echo "  pkill -f devtrack-cli              - Stop daemon"
echo ""