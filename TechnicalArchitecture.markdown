# Technical Architecture: DevTrack CLI

## Overview
**DevTrack CLI** is a non-intrusive, intelligent command-line tool that automates developer timesheet and progress reporting by prompting developers periodically (every 3 hours) or on Git commits, integrating with project management systems, and generating end-of-day summaries. The tool uses **Go** for the lightweight background process and system-level tasks, and **Python** for intelligent processing and integrations, with **SQLite** for local storage and **YAML** for configuration.

This document outlines the technical architecture, components, their interactions, and the project structure to guide development.

## Design Principles
- **Non-Intrusive**: Minimize workflow disruption with concise, skippable prompts.
- **Modular**: Separate concerns between Go (system tasks) and Python (logic and integrations) for maintainability.
- **Cross-Platform**: Support Windows, macOS, and Linux.
- **Secure**: Encrypt sensitive data and use secure API practices.
- **Lightweight**: Ensure low CPU/memory usage for the background process.
- **Extensible**: Allow easy addition of new project management integrations.

## Technical Components
The architecture is divided into two main layers—**Go Core** and **Python Intelligence Layer**—with supporting components for storage, configuration, and communication.

### 1. Go Core (Background Engine)
**Purpose**: Runs as a lightweight daemon to handle system monitoring, trigger detection, and scheduling.  
**Responsibilities**:
- Monitor Git repositories for commit events using Git hooks or polling.
- Schedule time-based prompts (every 3 hours, configurable).
- Trigger the Python layer to display prompts or process data.
- Log trigger events to SQLite for auditing and offline support.
- Handle cross-platform file system and process management.

**Key Features**:
- **Git Integration**: Detects `git commit` events by:
  - Using Git hooks (e.g., `post-commit`) to run a Go binary.
  - Polling the `.git` directory for changes (fallback for systems where hooks are impractical).
- **Time-Based Triggers**: Uses a scheduler to fire prompts at configurable intervals (default: 3 hours).
- **Daemon Process**: Runs continuously with minimal resource usage (<10 MB RAM, <1% CPU target).
- **Communication**: Sends trigger data (e.g., repo name, commit message) to the Python layer via IPC.

**Technical Considerations**:
- Use Go’s `fsnotify` package for file system monitoring (e.g., watching `.git` changes).
- Leverage Go’s goroutines for concurrent monitoring of multiple repositories and scheduling.
- Ensure cross-platform compatibility for Git hook setup and file system paths.

### 2. Python Intelligence Layer (Logic and Integrations)
**Purpose**: Handles user interactions, intelligent processing, and external integrations.  
**Responsibilities**:
- Display context-aware prompts for project/task details.
- Parse user responses using NLP to extract relevant data (e.g., project names, ticket numbers).
- Integrate with project management systems (e.g., Jira, GitHub Issues) via APIs.
- Compile and present end-of-day summaries for user review.
- Push updates to tickets and send optional email notifications.

**Key Features**:
- **Prompt System**: Uses a CLI interface or system notifications for non-intrusive prompts, with options to skip or defer.
- **NLP Processing**: Extracts structured data from free-text responses (e.g., “Fixed login bug for Project X” → project: “Project X”, ticket: “#123”).
- **API Integrations**: Connects to project management systems to fetch task details and post updates.
- **Summary Generation**: Aggregates daily activities into a report, editable via CLI or a temporary file.
- **Offline Support**: Caches responses and updates in SQLite for syncing when online.

**Technical Considerations**:
- Use `prompt_toolkit` for interactive CLI prompts or `plyer` for system notifications.
- Leverage `spaCy` for lightweight NLP or `transformers` for advanced parsing if needed.
- Use `requests` for API calls, with platform-specific libraries (e.g., `jira` for Jira).
- Implement a retry mechanism for failed API calls to ensure reliability.

### 3. Communication Layer
**Purpose**: Facilitates interaction between Go Core and Python Intelligence Layer.  
**Mechanism**: Inter-Process Communication (IPC) using Unix sockets (Linux/macOS) or named pipes (Windows).  
**Workflow**:
- Go Core detects a trigger (e.g., commit or 3-hour interval) and sends a JSON payload to Python with context (e.g., `{"event": "commit", "repo": "my-project", "commit_message": "Fixed bug"}`).
- Python processes the payload, displays a prompt, and sends results back to Go for logging.
- Alternatively, Python runs a lightweight HTTP server (e.g., `Flask`) that Go calls with HTTP requests (less preferred due to overhead).

**Technical Considerations**:
- Use Go’s `net` package and Python’s `socket` module for IPC.
- Keep payloads lightweight (JSON with minimal fields) to avoid latency.
- Handle connection failures gracefully, caching data in SQLite if Python is unresponsive.

### 4. Local Storage
**Purpose**: Stores trigger events, prompt responses, and cached API updates for auditing and offline support.  
**Implementation**: SQLite database (file-based, cross-platform).  
**Schema**:
- **Triggers**: Stores trigger events (e.g., `id`, `timestamp`, `type` [commit/time], `repo`, `commit_message`).
- **Responses**: Stores user prompt responses (e.g., `id`, `trigger_id`, `project`, `ticket`, `description`).
- **Updates**: Stores pending API updates (e.g., `id`, `ticket_id`, `update_text`, `status` [pending/sent]).
- **Logs**: Stores debug logs (e.g., `timestamp`, `component`, `message`).

**Technical Considerations**:
- Use Go’s `database/sql` with SQLite driver for trigger writes.
- Use Python’s `sqlite3` for reading and updating response data.
- Implement a cleanup mechanism to prevent database bloat (e.g., delete logs older than 30 days).

### 5. Configuration
**Purpose**: Allows users to define projects, API credentials, and prompt settings.  
**Implementation**: YAML file (e.g., `~/.devtrack/config.yaml`).  
**Structure**:
```yaml
projects:
  - name: ProjectX
    repo: /path/to/repo
    branch: main
    ticket_prefix: PRX
api_integrations:
  github:
    token: <encrypted_token>
    repo: user/repo
  jira:
    url: https://jira.example.com
    token: <encrypted_token>
settings:
  prompt_interval: 3h
  summary_time: 17:00
  timezone: UTC
```
**Technical Considerations**:
- Use `go-yaml` in Go and `PyYAML` in Python for parsing.
- Encrypt sensitive fields (e.g., API tokens) using a system keychain or Go’s `crypto` package.
- Validate config file on startup to catch errors (e.g., missing fields, invalid paths).

## System Workflow
1. **Startup**:
   - Go Core starts as a daemon, reads config file, and initializes repository monitoring and scheduler.
   - Python layer initializes, waiting for triggers from Go.
2. **Trigger Detection**:
   - Go detects a `git commit` (via hook or polling) or a 3-hour interval.
   - Go logs the trigger to SQLite and sends a JSON payload to Python via IPC.
3. **Prompt and Processing**:
   - Python receives the payload, infers context (e.g., project from repo), and displays a prompt.
   - User responds (e.g., “Fixed login for ProjectX #123”).
   - Python parses the response using NLP, maps it to a ticket, and stores it in SQLite.
4. **API Update**:
   - Python sends updates to the project management system via API (e.g., comment on GitHub Issue #123).
   - If offline, Python caches the update in SQLite.
5. **End-of-Day Summary**:
   - At the configured time, Python aggregates responses from SQLite into a summary.
   - User reviews/edits the summary via CLI or a temporary file.
   - Python pushes final updates to APIs and sends optional email notifications.
6. **Sync and Cleanup**:
   - Go and Python sync cached data when online.
   - Go cleans up old logs/triggers to maintain database size.

## Project Structure
The project is organized into Go and Python modules with clear separation of concerns.

```
devtrack-cli/
├── cmd/                    # Go entry points
│   ├── devtrack/           # Main Go binary
│   │   ├── main.go         # Entry point for daemon
│   │   └── daemon.go       # Daemon logic (monitoring, scheduling)
│   └── devtrackctl/        # CLI control binary
│       ├── main.go         # Entry point for control commands
│       └── commands.go     # Commands (e.g., pause, set-interval)
├── internal/               # Go internal packages
│   ├── git/                # Git integration (hooks, polling)
│   ├── scheduler/          # Time-based trigger logic
│   ├── ipc/                # IPC communication with Python
│   └── storage/            # SQLite interactions
├── python/                 # Python module
│   ├── prompts/            # Prompt generation and display
│   │   ├── __init__.py
│   │   └── prompt.py
│   ├── nlp/                # NLP parsing logic
│   │   ├── __init__.py
│   │   └── parser.py
│   ├── integrations/       # Project management API integrations
│   │   ├── __init__.py
│   │   ├── github.py
│   │   └── jira.py
│   ├── summary/            # End-of-day summary logic
│   │   ├── __init__.py
│   │   └── summary.py
│   └── storage/            # SQLite interactions
│       ├── __init__.py
│       └── db.py
├── config/                 # Configuration files
│   └── config.yaml         # Default user config template
├── scripts/                # Utility scripts
│   ├── install.sh          # Installation script (Linux/macOS)
│   └── install.ps1         # Installation script (Windows)
├── docs/                   # Documentation
│   └── user-guide.md       # User documentation
├── tests/                  # Tests for both Go and Python
│   ├── go/                 # Go unit tests
│   └── python/             # Python unit tests
├── Dockerfile              # For containerized deployment
├── README.md               # Project overview and setup instructions
└── go.mod                  # Go module dependencies
```

### Component Details
1. **Go Core**:
   - `cmd/devtrack`: Main binary for the daemon.
     - `main.go`: Initializes daemon, config, and monitoring.
     - `daemon.go`: Implements repository monitoring and scheduling.
   - `cmd/devtrackctl`: CLI for user control (e.g., `devtrackctl pause`).
   - `internal/git`: Handles Git hook setup and polling using `go-git`.
   - `internal/scheduler`: Manages time-based triggers using Go’s `time` package.
   - `internal/ipc`: Sends JSON payloads to Python via sockets/pipes.
   - `internal/storage`: Logs triggers to SQLite.

2. **Python Intelligence Layer**:
   - `python/prompts`: Manages CLI prompts (`prompt_toolkit`) or notifications (`plyer`).
   - `python/nlp`: Parses responses using `spaCy` for lightweight NLP or `transformers` for advanced parsing.
   - `python/integrations`: Modular API clients for GitHub, Jira, etc., using `requests`.
   - `python/summary`: Generates and presents end-of-day summaries, editable via CLI or file.
   - `python/storage`: Reads/writes responses and updates to SQLite.

3. **Shared Components**:
   - `config/config.yaml`: User configuration file, parsed by `go-yaml` and `PyYAML`.
   - SQLite database (e.g., `~/.devtrack/devtrack.db`): Shared storage for triggers, responses, and logs.

## Technical Considerations
### Cross-Platform Support
- **Git Hooks**: Use platform-specific scripts to install hooks (e.g., Bash for Linux/macOS, PowerShell for Windows).
- **File Paths**: Handle Windows vs. Unix path differences in Go (`filepath` package) and Python (`os.path`).
- **Notifications**: Use `plyer` in Python for cross-platform system notifications.

### Security
- Encrypt API tokens in `config.yaml` using Go’s `crypto` package or system keychain.
- Use HTTPS for all API calls and validate SSL certificates.
- Avoid logging sensitive data (e.g., commit messages) unless explicitly enabled.

### Performance
- **Go Core**: Optimize goroutines to minimize CPU usage; use `fsnotify` for efficient file monitoring.
- **Python Layer**: Lazy-load NLP models and cache API responses to reduce latency.
- **Database**: Index SQLite tables for fast queries; implement cleanup for old records.

### Error Handling
- **Git Failures**: Handle missing repositories or invalid Git hooks gracefully.
- **API Failures**: Cache updates in SQLite and retry with exponential backoff.
- **IPC Failures**: Log failed communications and fall back to SQLite for data persistence.

### Edge Cases
1. **No Git Repository**: Prompt for manual project input or skip.
2. **Multiple Repositories**: Track context per repo using SQLite.
3. **Offline Mode**: Cache all data in SQLite and sync when online.
4. **Skipped Prompts**: Store in SQLite and revisit at end-of-day.
5. **Ambiguous Context**: Offer dropdowns or manual input for project selection.
6. **Time Zone Handling**: Use system time zone with config override.

## Implementation Notes
### Go Core
- **Git Integration**:
  - Prefer Git hooks (`post-commit`) for real-time commit detection.
  - Fallback to polling (every 10 seconds) using `fsnotify` for repos without hooks.
  - Extract repo name, branch, and commit message for context.
- **Scheduler**:
  - Use Go’s `time.Ticker` for 3-hour prompts, adjustable via config.
  - Support pausing/resuming via `devtrackctl` commands.
- **IPC**:
  - Use Unix sockets (Linux/macOS) or named pipes (Windows) for Go-Python communication.
  - Send JSON payloads with fields: `event_type`, `repo`, `branch`, `commit_message`, `timestamp`.

### Python Intelligence Layer
- **Prompts**:
  - Use `prompt_toolkit` for CLI prompts with autocomplete for project names.
  - Support natural language input and predefined options (e.g., project list from config).
  - Allow deferring prompts with a timeout (e.g., revisit in 30 minutes).
- **NLP**:
  - Use `spaCy` for initial parsing (e.g., extract entities like “ProjectX”, “#123”).
  - Optionally integrate `transformers` for advanced parsing if accuracy is low.
  - Cache parsed results in SQLite to improve suggestions over time.
- **API Integrations**:
  - Start with GitHub Issues (using `requests` with OAuth).
  - Modularize for Jira, Trello, etc., with a plugin-like structure.
  - Cache API responses in SQLite to reduce calls and support offline mode.
- **Summary**:
  - Aggregate responses from SQLite into a Markdown-formatted report.
  - Allow editing via CLI or by opening a temporary file in the user’s editor (e.g., `vim`, `code`).
  - Send emails using `smtplib` with user-configured SMTP settings.

### Database
- **Schema**:
  - `triggers(id, timestamp, type, repo, branch, commit_message)`
  - `responses(id, trigger_id, project, ticket, description, timestamp)`
  - `updates(id, ticket_id, update_text, status, timestamp)`
  - `logs(id, timestamp, component, message)`
- **Access**: Go writes to `triggers` and `logs`; Python reads/writes `responses` and `updates`.

### Configuration
- Validate `config.yaml` on startup to ensure required fields (e.g., `projects`, `api_integrations`).
- Support defaults for `prompt_interval` (3h) and `summary_time` (17:00).
- Encrypt sensitive fields using a user-provided passphrase or system keychain.

## Development Setup
1. **Prerequisites**:
   - Go (1.20+): For the daemon and CLI control binary.
   - Python (3.8+): For the intelligence layer.
   - SQLite: For local storage.
   - Git: For repository monitoring.
2. **Dependencies**:
   - Go: `go-git`, `fsnotify`, `go-yaml`, `database/sql`.
   - Python: `GitPython`, `spaCy`, `requests`, `prompt_toolkit`, `PyYAML`, `sqlite3`.
3. **Build Process**:
   - Compile Go binaries (`devtrack`, `devtrackctl`) using `go build`.
   - Package Python dependencies using `PyInstaller` or a virtual environment.
   - Provide installation scripts (`install.sh`, `install.ps1`) to set up Git hooks and configs.
4. **Testing**:
   - Go: Unit tests for Git integration, scheduler, and IPC using `testing`.
   - Python: Unit tests for NLP, prompts, and API integrations using `pytest`.
   - End-to-end tests for Go-Python communication and cross-platform compatibility.

## Next Steps
1. **Initialize Project**:
   - Create the project structure as outlined.
   - Set up `go.mod` and Python `requirements.txt`.
2. **Prototype Go Core**:
   - Implement basic daemon with Git hook detection and time-based scheduler.
   - Test IPC with a dummy Python script.
3. **Prototype Python Layer**:
   - Build a CLI prompt system and integrate with GitHub Issues API.
   - Add basic NLP parsing for responses.
4. **Integrate Components**:
   - Connect Go and Python via IPC.
   - Test end-to-end workflow (commit → prompt → API update).
5. **Iterate**:
   - Add SQLite for storage and offline support.
   - Implement end-of-day summary and email notifications.
   - Test edge cases and optimize performance.

## Success Metrics
- **Functionality**: Triggers fire correctly, prompts are context-aware, and API updates succeed.
- **Performance**: Go daemon uses <10 MB RAM, Python prompts respond in <1 second.
- **Reliability**: Handles all edge cases without crashes or data loss.
- **Usability**: 90% of prompts completed or skipped within 10 seconds in user testing.

This technical architecture provides a robust foundation for building DevTrack CLI, leveraging Go’s performance and Python’s intelligence. Start with the Go Core for monitoring and Python for prompts, then iterate on integrations and advanced features.