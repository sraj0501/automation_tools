# DevTrack - Developer Automation Tools

> An intelligent system that automates developer timesheet tracking, task management, and progress reporting through Git monitoring and AI-powered natural language processing.

## �� Documentation

**All comprehensive documentation has been moved to the Wiki:**

- **[📖 Complete Wiki](wiki/index.html)** - Full documentation with all features, architecture, commands, and guides
- **[🔒 Privacy Policy](wiki/privacy.html)** - Detailed privacy and security information

## Quick Overview

DevTrack combines background process automation with AI intelligence to:
- Monitor your Git activity and trigger smart prompts at key moments
- Parse natural language updates into structured task data
- Learn your communication style from Teams, Azure DevOps, and Outlook
- Generate responses in YOUR voice using privacy-first local AI
- Integrate with Azure DevOps, GitHub, Jira, and Microsoft Lists
- Update tasks automatically in project tracking systems
- Generate professional reports for managers and stakeholders
- Track time and productivity without manual timesheet entry

## Installation Options

> **📘 New to local setup?** See the complete [Local Setup Guide](LOCAL_SETUP.md) for step-by-step instructions from scratch.

### Option 1: Local/Manual Installation (Recommended for Development)

Run DevTrack natively on your system without Docker for faster iteration and easier debugging.

#### Prerequisites
- **Go** 1.20+ ([Download](https://go.dev/dl/))
- **Python** 3.12+ with **uv** package manager ([Install uv](https://github.com/astral-sh/uv))
- **Git** (for repository monitoring)
- **Ollama** (optional, for AI features) ([Download](https://ollama.com/download))

#### Setup Steps

1. **Clone and configure**:
   ```bash
   git clone https://github.com/yourusername/automation_tools.git
   cd automation_tools
   
   # Copy and configure environment
   cp .env_sample .env
   # Edit .env - set PROJECT_ROOT to your repo path
   ```

2. **Install Python dependencies**:
   ```bash
   # uv automatically creates and manages virtual environment
   uv sync
   ```

3. **Build the Go binary**:
   ```bash
   cd devtrack-bin
   go build -o devtrack .
   
   # Optional: Install globally
   mv devtrack ~/.local/bin/
   # Add to PATH if not already: export PATH="$HOME/.local/bin:$PATH"
   ```

4. **Set up environment** (add to `~/.bashrc` or `~/.zshrc`):
   ```bash
   export PROJECT_ROOT="/path/to/automation_tools"
   ```

5. **Start the daemon**:
   ```bash
   # Navigate to the repository you want to monitor
   cd ~/path/to/your/project
   
   # Start daemon (runs in background)
   devtrack start &
   disown
   
   # Check status
   devtrack status
   ```


#### Key Configuration (.env file)

All configuration is centralized in `.env` with **no hardcoded defaults or fallback locations**.

**How DevTrack finds your .env file:**

- If the `DEVTRACK_ENV_FILE` environment variable is set, DevTrack will load the .env file from that path.
- If not set, DevTrack will only look for `.env` in the current working directory.
- If neither is found, DevTrack will exit with an error.

**Example:**
```sh
export DEVTRACK_ENV_FILE=/absolute/path/to/your/.env
~/.local/bin/devtrack
```

See `.env_sample` for a template of all required variables.

Validate `.env_sample` matches required runtime env keys:
```sh
python validate_env_sample.py
```

#### Local Installation Benefits
- ✅ Faster startup and iteration
- ✅ Native filesystem access (no Docker overhead)
- ✅ Easier debugging with direct log access
- ✅ Uses uv for fast dependency management
- ✅ Full Python 3.12 compatibility with spaCy NLP

---

### Option 2: Containerized Setup (Cross-Platform)

This workflow runs the full stack on macOS, Windows (PowerShell, WSL, or Git Bash), and Linux with the same commands.

1. Copy `.env_sample` to `.env` and set `DEVTRACK_WORKSPACE` to the host path you want mounted at `/workspace`. Relative paths (default `.`) resolve to the repository root and work on every OS. Use Windows-style paths (e.g., `C:\Users\you\Projects\automation_tools`) when running from PowerShell.
2. Enable BuildKit for faster incremental builds:

     ```bash
     DOCKER_BUILDKIT=1 docker buildx build --load .
     ```

3. Install and run [Ollama](https://ollama.com/download) locally on your host machine. Keep it listening on `11434` (or set `OLLAMA_HOST` in `.env` to match your custom port/URL). The container reaches the host via `host.docker.internal`, which is mapped automatically for Linux, macOS, and Windows.

     ```bash
     # host shell
     ollama serve
     ```

4. Launch the DevTrack container (it will call the host's Ollama endpoint):

     ```bash
     docker compose up devtrack
     ```

Bind mounts now rely on the portable `DEVTRACK_WORKSPACE` variable, so no OS-specific path rewriting or WSL hacks are required.

## System Architecture

\`\`\`
Git Activity/Timer → Go Daemon → Python AI Layer → Project Management APIs
                         ↓              ↓
                    SQLite Cache    NLP Processing
                         ↓              ↓
                    Local Storage   Task Matching → Email Reports
\`\`\`

### Core Components
- **Go Background Engine**: Lightweight daemon for Git monitoring and scheduling
- **Python Intelligence Layer**: NLP processing, API integrations, and user interactions
- **Local Storage**: SQLite for offline support and caching
- **Multiple Integrations**: Azure DevOps, GitHub, Microsoft Graph, Jira

## Quick Start

Choose your installation method above, then use these commands:

### Using Local Installation

```bash
# Navigate to a Git repository you want to monitor
cd ~/path/to/your/project

# Start daemon in background
devtrack start &
disown

# Check status and view configuration
devtrack status

# View recent logs
devtrack logs

# Make a commit with task info for NLP parsing
git commit -m "Working on #PROJ-123 - Fixed authentication bug (2h)"

# Check logs to see NLP parsing results
tail -f ~/.devtrack/daemon.log

# Stop daemon
devtrack stop
```

### Using Docker

```bash
# Start containerized daemon
docker compose up devtrack -d

# Check logs
docker compose logs devtrack -f

# Stop container
docker compose down
```

### Common Commands

```bash
# Daemon Control
devtrack start              # Start monitoring
devtrack stop               # Stop daemon
devtrack restart            # Restart with new config
devtrack status             # Show running status

# Scheduler Control
devtrack pause              # Pause scheduled triggers
devtrack resume             # Resume scheduler
devtrack force-trigger      # Trigger immediately
devtrack skip-next          # Skip next scheduled trigger

# Information
devtrack logs               # View recent logs
devtrack db-stats           # Database statistics
devtrack version            # Version information
devtrack help               # Full command list
```

## Technology Stack

### Backend (Go)
- Go 1.20+ daemon for monitoring and triggers
- fsnotify for real-time Git repository monitoring
- Cron-based scheduling with configurable intervals
- SQLite for local caching and trigger history
- TCP-based IPC for Go ↔ Python communication

### Intelligence (Python 3.12+)
- **uv** for fast dependency management
- **spaCy** (en_core_web_sm) for NLP and entity recognition
- **OLLAMA** for local LLM processing (privacy-first)
- **sentence-transformers** for semantic task matching
- **python-dotenv** for environment configuration
- Microsoft Graph SDK for Teams/Outlook integrations

### Integrations
- Azure DevOps REST API
- Microsoft Graph API (Teams, Email, Lists)
- GitHub API
- Jira API (planned)

### Configuration
- **.env file**: Zero-fallback configuration (16 required variables)
- All paths, ports, and file names customizable
- No hardcoded values - explicit configuration enforced

## Privacy & Security

DevTrack is built with privacy as a core principle:
- All data stored locally on your machine
- No cloud AI services (uses local Ollama)
- Explicit consent required for AI learning features
- Complete transparency about data collection
- Full data deletion option available anytime

For complete details, see the **[Privacy Policy](wiki/privacy.html)**.

## Troubleshooting

### Local Installation Issues

**Python version compatibility:**
```bash
# DevTrack requires Python 3.12 or 3.13 (not 3.14+)
python3 --version

# If using Python 3.14, uv will automatically downgrade
# based on pyproject.toml settings
```

**spaCy NLP model not found:**
```bash
# Install spaCy language model
uv run python -m spacy download en_core_web_sm
```

**Daemon won't start:**
```bash
# Check logs for errors
tail -50 ~/.devtrack/daemon.log

# Verify .env file exists and PROJECT_ROOT is set
cat .env | grep PROJECT_ROOT

# Ensure binary is in PATH
which devtrack

# Check if port is already in use
lsof -i :35893
```

**Git commits not detected:**
```bash
# Verify daemon is running in correct repository
devtrack status

# Check git monitor is active
tail ~/.devtrack/daemon.log | grep "Git monitor"

# Ensure you're making commits in the monitored repo
```

**IPC connection errors:**
```bash
# Check IPC configuration in .env
grep IPC .env

# Verify no firewall blocking localhost:35893
# Restart daemon after .env changes
devtrack restart
```

## Project Status

**Current Phase**: Phase 5 (Daily Reports) - Completed  
**Overall Progress**: ~80-85% Complete

**Phase 5 Achievements:**
- ✅ AI-enhanced daily report generation
- ✅ Ollama-powered productivity insights and recommendations
- ✅ Multiple output formats (Terminal, Text, HTML, Markdown, JSON)
- ✅ Automatic end-of-day detection and prompting
- ✅ Report saving and email integration

**Phase 3 Achievements:**
- ✅ TUI user prompts for work updates
- ✅ spaCy NLP parsing for task extraction
- ✅ Ollama description enhancement and categorization
- ✅ Full timer trigger workflow integration

**Next Phase (Phase 4):**
- 🔄 Azure DevOps task integration
- 🔄 GitHub Issues integration
- 🔄 JIRA integration

See the [Roadmap section in the Wiki](wiki/index.html#roadmap) for detailed status.

## Contributing

1. Fork the repository
2. Create a feature branch (\`git checkout -b feature/amazing-feature\`)
3. Commit your changes (\`git commit -m 'Add amazing feature'\`)
4. Push to the branch (\`git push origin feature/amazing-feature\`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

- **Documentation**: [Complete Wiki](wiki/index.html)
- **Issues**: [GitHub Issues](https://github.com/sraj0501/automation_tools/issues)
- **Discussions**: [GitHub Discussions](https://github.com/sraj0501/automation_tools/discussions)

---

**Note**: This tool is designed for individual and team productivity enhancement. Ensure you have appropriate licenses and permissions for all integrated services.
# Test interactive feedback
# Testing descriptive commit messages with reasoning
