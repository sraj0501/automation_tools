# DevTrack Local Setup Guide

Complete step-by-step instructions for running DevTrack locally from scratch (without Docker).

## Prerequisites

Before you begin, ensure you have these installed:

### 1. **Go 1.20+**
```bash
# Check if Go is installed
go version

# If not installed, download from: https://go.dev/dl/
# Or on Linux:
# Edit .env file with your paths
sudo tar -C /usr/local -xzf go1.24.0.linux-amd64.tar.gz
echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc
source ~/.bashrc
```

### 2. **Python 3.12 or 3.13** (NOT 3.14+)
```bash
# Check Python version
python3 --version

# Should be 3.12.x or 3.13.x (3.14+ has spaCy compatibility issues)
```

### 3. **uv Package Manager**
```bash
# Install uv
CLI_BINARY_NAME=devtrack

# Verify installation
uv --version
```

### 4. **Git**
```bash
# Should already be installed
git --version
```

### 5. **Ollama** (Optional - for AI features)
```bash
# Download from: https://ollama.com/download
# Or on Linux:
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama server
ollama serve
```

---

## Setup Steps

### Step 1: Clone Repository
```bash
cd ~/Documents/GitHub  # or your preferred location
```

### Step 2: Configure Environment
~/.local/bin/devtrack
# Copy example configuration
cp .env_sample .env
nano .env  # or use your preferred editor
```

**Required .env Configuration:**
```bash
# Update these paths to match your system
go build -o devtrack .
DEVTRACK_HOME=/home/YOUR_USERNAME/.devtrack
DEVTRACK_WORKSPACE=/home/YOUR_USERNAME/Documents/GitHub

# IPC Configuration (can usually keep defaults)
IPC_HOST=127.0.0.1
IPC_PORT=35893

# File names (can usually keep defaults)
mv devtrack ~/.local/bin/
CLI_BINARY_NAME=devtrack
CONFIG_FILE_NAME=config.yaml
DATABASE_FILE_NAME=devtrack.db
PID_FILE_NAME=daemon.pid
LOG_FILE_NAME=daemon.log

which devtrack
devtrack version
CONFIG_DIR_NAME=.devtrack

# CLI identifiers (can usually keep defaults)
CLI_APP_NAME=DevTrack
CLI_DAEMON_NAME=devtrack

# Ollama endpoint (adjust if using custom port)
OLLAMA_HOST=http://localhost:11434
devtrack start &

### Step 2: Configure Environment
```bash
devtrack status
cp .env_sample .env

# Edit .env file with your paths
nano .env  # or use your preferred editor
```
devtrack stop
**.env File Location and Usage:**

- All configuration is loaded from the `.env` file. There are **no fallback locations or hardcoded defaults**.
- Set the `DEVTRACK_ENV_FILE` environment variable to the absolute path of your `.env` file before running DevTrack:

devtrack status
export DEVTRACK_ENV_FILE=/absolute/path/to/your/.env
~/.local/bin/devtrack
ps aux | grep devtrack

- If `DEVTRACK_ENV_FILE` is not set, DevTrack will only look for `.env` in the current working directory.
- If neither is found, DevTrack will exit with an error.

See `.env_sample` for a template of all required variables.

### Step 3: Install Python Dependencies
```bash
# uv automatically creates virtual environment and installs dependencies
uv sync

# Verify spaCy installation
uv run python -c "import spacy; print(spacy.__version__)"
```

### Step 4: Build Go Binary
```bash
cd devtrack-bin
go build -o devtrack .

# Verify build
./devtrack version
```

### Step 5: Install Binary Globally (Optional but Recommended)
```bash
# Create ~/.local/bin if it doesn't exist
mkdir -p ~/.local/bin

# Move binary to PATH
mv devtrack ~/.local/bin/

# Add to PATH if not already (add to ~/.bashrc or ~/.zshrc)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc

# Verify global installation
which devtrack
devtrack version
```

### Step 6: Set PROJECT_ROOT Environment Variable
```bash
# Add to ~/.bashrc or ~/.zshrc
echo 'export PROJECT_ROOT="/home/YOUR_USERNAME/Documents/GitHub/automation_tools"' >> ~/.bashrc
source ~/.bashrc

# Verify
echo $PROJECT_ROOT
```

### Step 7: Create DevTrack Home Directory
```bash
# Create configuration directory (will also be created automatically on first run)
mkdir -p ~/.devtrack
```

---

## Running DevTrack

### Method 1: Using run_devtrack_local.sh Script
```bash
# From the project root
cd ~/Documents/GitHub/automation_tools
# Make script executable (first time only)
chmod +x run_devtrack_local.sh

# Run the script
./run_devtrack_local.sh
```

This script will:
- ✅ Load configuration from `.env`
- ✅ Validate all required variables
- ✅ Stop any existing instances
- ✅ Start the daemon in background
- ✅ Show status and logs

### Method 2: Manual Daemon Control
```bash
# Navigate to the repository you want to monitor
cd ~/Documents/GitHub/your-project

# Start daemon (runs in background)
devtrack start &
disown

# Check status
devtrack status

# View logs
tail -f ~/.devtrack/daemon.log

# Stop daemon
```

---

## Verification

### Check All Components Are Running
```bash
# 1. Check daemon status
devtrack status

# 2. Check processes
ps aux | grep devtrack
ps aux | grep python_bridge.py

# 3. Check logs (should show NLP parser loaded)
tail -50 ~/.devtrack/daemon.log | grep -E "NLP|spaCy|IPC|Git monitor"

# Expected output:
# - ✓ IPC server started
# - ✓ Git monitor started
# - ✓ NLP parser initialized
# - ✅ Connected to IPC server
```

### Test Commit Detection
```bash
# In your monitored repository
cd ~/Documents/GitHub/your-project

# Make a test commit with NLP-rich message
echo "test" >> README.md
git add README.md
git commit -m "Working on #PROJ-123 - Fixed authentication bug (2h)"

# Check logs for NLP parsing
tail -30 ~/.devtrack/daemon.log

# You should see:
# - 🎯 COMMIT TRIGGER
# - 📝 Parsing commit message with NLP...
```

---
```bash
# Check Python version used by uv
uv run python --version

# Should be 3.12 or 3.13
# If 3.14, pyproject.toml already restricts to <3.14
# Re-run: uv sync
```

### Issue: "spaCy model not found"
```bash
# Download English model
uv run python -m spacy download en_core_web_sm

# Verify
uv run python -c "import spacy; spacy.load('en_core_web_sm')"
```

### Issue: "Binary not found in PATH"
```bash
# Check PATH
echo $PATH | grep -o ~/.local/bin

# If not there, add to PATH
export PATH="$HOME/.local/bin:$PATH"

# Make permanent
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
```

### Issue: ".env file not found"
```bash
# Verify .env exists
ls -la .env

# If missing, copy from example
cp .env_sample .env

# Edit with your paths
nano .env
```

### Issue: "IPC connection failed"
```bash
# Check if port is already in use
lsof -i :35893

# If occupied, change IPC_PORT in .env
# Then rebuild and restart
```

### Issue: "Git commits not detected"
```bash
# 1. Check daemon is running
devtrack status

# 2. Verify you're in the monitored repository
pwd
# Should match DEVTRACK_WORKSPACE or be a subdirectory

# 3. Check daemon was started from that directory
tail ~/.devtrack/daemon.log | grep "Git repository"

# 4. Restart daemon in correct directory
cd ~/path/to/your-project
devtrack restart
```

---

## Directory Structure After Setup

```
automation_tools/
├── .env                    # Your configuration (DO NOT commit)
├── .env_sample            # Template
├── devtrack-bin/
│   └── devtrack           # Built binary (before moving to ~/.local/bin)
├── python_bridge.py       # Python IPC bridge
├── backend/               # Python modules
├── run_devtrack_local.sh  # Quick start script
└── pyproject.toml        # Python dependencies

~/.devtrack/              # Runtime data
├── config.yaml          # User configuration
├── daemon.log          # Daemon logs
├── daemon.pid          # Process ID
└── devtrack.db         # SQLite database

~/.local/bin/           # Installed binary
└── devtrack           # Global command
```

---

## Next Steps

Once setup is complete and daemon is running:

1. **Configure work hours** (optional):
   ```bash
   devtrack config set work-hours "09:00-17:00"
   ```

2. **Adjust trigger interval** (optional):
   ```bash
   devtrack config set interval 120  # 120 minutes
   ```

3. **Enable learning mode** (optional):
   ```bash
   devtrack enable-learning
   ```

4. **Test manual triggers**:
   ```bash
   devtrack force-trigger
   ```

5. **View help for all commands**:
   ```bash
   devtrack help
   ```

---

## Regular Usage

### Daily Workflow
```bash
# Morning: Check status
devtrack status

# During work: Make commits as normal
git commit -m "Working on #TICKET-123 - Feature description (time estimate)"

# End of day: Generate report (if configured)
devtrack send-summary

# Evening: Stop daemon (optional)
devtrack stop
```

### View Activity
```bash
# Recent triggers
devtrack logs

# Database stats
devtrack db-stats

# Check parsed tasks
tail -100 ~/.devtrack/daemon.log | grep "Parsed result"
```

---

## Updating DevTrack

```bash
cd ~/Documents/GitHub/automation_tools

# Pull latest changes
git pull origin main

# Update Python dependencies
uv sync

# Rebuild Go binary
cd devtrack-bin
go build -o devtrack .
mv devtrack ~/.local/bin/

# Restart daemon
devtrack restart
```

---

## Uninstalling

```bash
# Stop daemon
devtrack stop

# Remove binary
rm ~/.local/bin/devtrack

# Remove runtime data (optional - deletes all logs and database)
rm -rf ~/.devtrack

# Remove project files
rm -rf ~/Documents/GitHub/automation_tools

# Remove environment variable from shell config
# Edit ~/.bashrc or ~/.zshrc and remove PROJECT_ROOT export
```

---

## Getting Help

- **Documentation**: See [README.md](README.md)
- **Wiki**: [Full documentation](wiki/index.html)
- **Issues**: [GitHub Issues](https://github.com/yourusername/automation_tools/issues)
- **Logs**: Check `~/.devtrack/daemon.log` for detailed error messages
