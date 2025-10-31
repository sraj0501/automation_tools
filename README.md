# Developer Automation Tools

> An intelligent system that automates developer timesheet tracking, task management, and progress reporting through Git monitoring and AI-powered natural language processing.

## 🎯 Project Overview

This system combines background process automation with AI intelligence to:
- **Monitor your Git activity** and trigger smart prompts at key moments
- **Parse natural language updates** into structured task data
- **Integrate with project management tools** (Azure DevOps, GitHub, Jira)
- **Update tasks automatically** in Microsoft Lists and project tracking systems
- **Generate professional reports** for managers and stakeholders
- **Create intelligent subtasks** for complex activities
- **Track time and productivity** without manual timesheet entry

## 🏗️ System Architecture

### Hybrid Go + Python Design
```
Git Activity/Timer → Go Daemon → Python AI Layer → Project Management APIs
                         ↓              ↓
                    SQLite Cache    NLP Processing
                         ↓              ↓
                    Local Storage   Task Matching → Email Reports
```

### Core Components
1. **Go Background Engine**: Lightweight daemon for Git monitoring and scheduling
2. **Python Intelligence Layer**: NLP processing, API integrations, and user interactions
3. **Local Storage**: SQLite for offline support and caching
4. **Multiple Integrations**: Azure DevOps, GitHub, Microsoft Graph, Jira

## 🚀 Core Workflow

### Automatic Trigger Flow
```
Git Commit / 3-Hour Timer → Context-Aware Prompt → AI Processing → 
Task Update → Manager Report → Subtask Generation (if needed)
```

### Example Daily Interaction
```
[Git Commit Detected]
Prompt: "What did you work on in this commit?"
You: "Fixed login bug for Project Alpha, ticket #123"

AI: "✓ Updated GitHub Issue #123 with your progress
     ✓ Logged time to Azure DevOps
     ✓ Status: In Progress → Review Ready
     
     Should I create subtasks for testing and documentation?"

[End of Day - 5:00 PM]
AI: "📊 Daily Summary Ready:
     - 3 tasks completed
     - 2 in progress
     - 6.5 hours logged
     
     Review and send to manager?"
```

## 🧠 Key Features

### 1. Non-Intrusive Monitoring
- **Go Daemon**: Lightweight background process (<10 MB RAM, <1% CPU)
- **Git Integration**: Detects commits via hooks or polling
- **Smart Scheduling**: Configurable prompts (default: every 3 hours)
- **Context Awareness**: Infers project details from repo, branch, and files

### 2. AI-Powered Intelligence
- **Natural Language Parsing**: Extract tasks, tickets, and time from free text
- **Entity Recognition**: Identify project names, ticket numbers, status changes
- **Semantic Matching**: Fuzzy match activities to existing tasks
- **Confidence Scoring**: Ask clarifying questions when uncertain
- **Learning System**: Improves suggestions based on your patterns

### 3. Multi-Platform Integration
- **Azure DevOps**: Work items, boards, and sprint tracking
- **GitHub**: Issues, pull requests, and project boards
- **Microsoft Lists**: SharePoint-based task management
- **Microsoft Graph**: Email, calendar, and Teams integration
- **Jira**: Issue tracking and project management (planned)

### 4. Intelligent Task Management
- **Subtask Generation**: Automatically break down complex tasks
- **Status Tracking**: Update task states across platforms
- **Time Logging**: Track time spent without manual entry
- **Dependency Detection**: Identify and track task relationships
- **Priority Management**: Adjust task priorities based on deadlines

### 5. Automated Reporting
- **Daily Summaries**: Compile activities into professional reports
- **Email Generation**: Create manager-ready status updates
- **Progress Analytics**: Track productivity patterns and trends
- **Bottleneck Detection**: Identify stuck tasks needing attention
- **Customizable Templates**: Adapt report style to manager preferences

### 6. Offline Support & Reliability
- **Local Caching**: SQLite storage for offline work
- **Automatic Sync**: Push updates when connectivity restored
- **Data Privacy**: All AI processing can be done locally (OLLAMA)
- **Audit Trail**: Complete history of all updates and triggers

## 📚 Technology Stack

### Backend Engine (Go)
- **Purpose**: Lightweight daemon for monitoring and triggers
- **go-git v5.16.3**: Repository access and commit detection
- **fsnotify v1.9.0**: File system monitoring for .git directories
- **gopkg.in/yaml.v3**: YAML-based configuration management
- **modernc.org/sqlite v1.39.1**: Embedded SQLite database
- **robfig/cron/v3**: Time-based scheduling and triggers
- **Goroutines**: Concurrent monitoring and scheduling
- **Bubble Tea, Bubbles, Lipgloss**: TUI framework and styling

### Intelligence Layer (Python)
- **OLLAMA 0.6.0**: Local LLM for text understanding and generation
- **spaCy 3.8.7**: Named Entity Recognition (NER) for task extraction (with en_core_web_sm model)
- **sentence-transformers 5.1.2**: Semantic similarity matching
- **transformers** (Hugging Face): Advanced NLP processing
- **dateparser**: Natural language date parsing
- **fuzzywuzzy**: Fuzzy string matching for task disambiguation
- **python-Levenshtein**: Fast string distance calculations

### Integration APIs
- **msgraph-sdk-python**: Microsoft Graph API (Lists, Email, Teams)
- **Azure DevOps REST API**: Work items and boards
- **GitHub API**: Issues and project management
- **requests**: HTTP client for API interactions
- **msal**: Microsoft Authentication Library

### Data & Storage
- **SQLite**: Local caching and offline support
- **pandas**: Data analysis and reporting
- **json/yaml**: Configuration and data serialization

### Communication
- **IPC**: Unix sockets/named pipes for Go-Python communication
- **JSON**: Structured data exchange between components
- **schedule** - Automated daily/weekly triggers

## 🔧 System Requirements & Setup

### Prerequisites
- **Go 1.20+**: For the background daemon
- **Python 3.8+**: For AI processing and integrations
- **Git**: Repository monitoring
- **OLLAMA** (optional): For local LLM processing
- **Microsoft 365** or **Azure DevOps**: For task management integration

### Required Permissions

#### Microsoft Graph API Scopes
```python
graphUserScopes = [
    "User.Read",           # Read user profile
    "Mail.Send",           # Send emails  
    "Sites.Read.All",      # Read SharePoint Lists
    "Sites.ReadWrite.All"  # Update SharePoint Lists
]
```

### Installation

```bash
# Clone repository
git clone https://github.com/sraj0501/automation_tools.git
cd automation_tools

# Install Go dependencies
cd go-cli
go mod download

# Install Python dependencies
cd ..
pip install -r requirements.txt

# Configure settings
cp config.example.cfg backend/msgraph_python/config.cfg
# Edit config.cfg with your credentials

# Install OLLAMA (optional, for local AI)
# Visit https://ollama.ai for installation
ollama pull llama3.1

# Build Go daemon
cd go-cli
go build -o devtrack

# Set up Git hooks (optional)
./scripts/install-hooks.sh
```

### Configuration

The system uses `~/.devtrack/config.yaml` for all settings. On first run, a default configuration is created:

```yaml
projects:
  - name: ProjectAlpha
    repo: /path/to/repo
    branch: main
    ticket_prefix: PA-

api_integrations:
  azure_devops:
    organization: your-org
    project: your-project
    pat: <encrypted_token>
  github:
    token: <encrypted_token>
    repo: owner/repo

settings:
  scheduler:
    interval_minutes: 180              # Prompt every 3 hours
    work_hours_only: true
    work_start: "09:00"
    work_end: "18:00"
    enabled: true
  
  git:
    enabled: true
    repos:
      - /path/to/repo
    use_hooks: true                    # Install post-commit hooks
  
  notifications:
    output_type: email                 # Options: "email", "teams", "both"
    send_on_trigger: false
    send_daily_summary: true
    daily_report_time: "18:00"
    
    email:
      enabled: true
      to_addresses:
        - your.email@example.com
      cc_addresses:
        - manager@example.com
      subject: "DevTrack Daily Report - {{.Date}}"
      manager_email: manager@example.com
    
    teams:
      enabled: false
      chat_type: channel               # Options: "channel" or "chat"
      channel_id: "19:abc123..."
      webhook_url: ""
      mention_user: false
  
  timezone: UTC
  offline_mode: true
```

For detailed notification configuration, see [go-cli/NOTIFICATIONS.md](go-cli/NOTIFICATIONS.md).

### Basic Usage

```bash
# Build the Go binary
cd go-cli
go build -o devtrack

# Start the daemon
./devtrack start

# Check daemon status
./devtrack status

# Pause/resume monitoring
./devtrack pause
./devtrack resume

# Stop the daemon
./devtrack stop

# Restart the daemon
./devtrack restart

# View daemon logs
./devtrack logs

# Test individual components
./devtrack test-git         # Test Git monitoring
./devtrack test-scheduler   # Test timer scheduling
./devtrack test-config      # Test configuration
./devtrack test-integrated  # Test combined system

# Check version
./devtrack version

# Get help
./devtrack help

# Manual Python interactions
python main.py --mode daily
python main.py --mode summary
```

## 🔐 Security & Privacy

### Data Protection
- **Local AI Processing**: Use OLLAMA for on-premise LLM processing
- **Encrypted Credentials**: API tokens stored in system keychain or encrypted config
- **Audit Trail**: Complete logging of all data access and updates
- **Minimal Data Collection**: Only essential information is captured
- **Offline First**: Work without internet, sync when available

### Best Practices
- Store sensitive configs outside version control
- Use environment variables for secrets
- Enable 2FA on all integrated services
- Regular security audits of API access
- Follow principle of least privilege for API scopes

## ⚡ Performance Considerations

### Resource Usage Targets
- **Go Daemon**: <10 MB RAM, <1% CPU
- **Python Layer**: Lazy-loaded, activated only on triggers
- **Database**: SQLite with automatic cleanup (30-day retention)
- **API Calls**: Cached responses, retry with exponential backoff

### Optimization Strategies
- Lightweight NLP models (spaCy small models)
- Efficient IPC using Unix sockets/named pipes
- Goroutines for concurrent monitoring
- Database indexing for fast queries
- Batch API updates to minimize calls

## 🛠️ Development & Contributing

### Setting Up Development Environment

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Go tests
cd go-cli && go test ./...

# Linting
pylint backend/
golangci-lint run ./go-cli
```

### Architecture Principles
- **Modularity**: Clear separation between Go and Python layers
- **Extensibility**: Plugin-based integration system
- **Cross-Platform**: Support Windows, macOS, Linux
- **Non-Intrusive**: Minimal workflow disruption
- **Reliability**: Graceful degradation on failures

### Contributing
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 🐛 Troubleshooting

### Common Issues

**Git hooks not triggering**
```bash
# Check hook installation
ls -la .git/hooks/post-commit
# Reinstall hooks
./scripts/install-hooks.sh
```

**Python dependencies issues**
```bash
# Create fresh virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

**API authentication failures**
```bash
# Verify credentials
python backend/msgraph_python/main.py --test-auth
# Regenerate tokens if expired
```

**Go daemon not starting**
```bash
# Check logs
cat ~/.devtrack/logs/daemon.log
# Rebuild daemon
cd go-cli && go build -o devtrack
```

## 📁 Project Structure

```
automation_tools/
├── main.py                          # FastAPI entry point
├── pyproject.toml                   # Python dependencies (with spaCy, sentence-transformers, ollama)
├── README.md                        # Project documentation
├── Roadmap.md                       # 📋 Complete implementation roadmap with status
│
├── backend/
│   ├── ai/
│   │   └── create_tasks.py         # OLLAMA task generation (260 lines)
│   ├── azure/
│   │   ├── AzureDevOps.py          # Azure DevOps base class
│   │   ├── azure_updator.py        # Work item CRUD operations (188 lines)
│   │   ├── azure_work_items.py     # Work item utilities
│   │   └── fetch_stories.py        # Story retrieval
│   ├── data/
│   │   ├── Daily Tracker.csv       # Activity logging
│   │   ├── tasks.csv               # Task database
│   │   └── tasks.xlsx              # Excel task management
│   ├── db/
│   │   └── models.py               # Pydantic data models
│   ├── github/
│   │   ├── get_github_data.py      # Commit fetching
│   │   ├── ghAnalysis.py           # Repository analytics
│   │   └── gh_analysis.ipynb       # Analysis notebook
│   └── msgraph_python/
│       ├── main.py                 # Graph API CLI (482 lines)
│       ├── graph.py                # Graph client (316 lines)
│       ├── chat_analyzer.py        # Teams chat export
│       ├── sentiment_analysis.py   # OLLAMA sentiment analysis (627 lines)
│       └── config.cfg              # Graph API configuration
│
├── go-cli/
│   ├── main.go                     # CLI entry point with command routing
│   ├── tui.go                      # Bubble Tea interface (195 lines)
│   ├── styles.go                   # UI styling (Lipgloss)
│   ├── git_monitor.go              # ✅ Git commit detection (230 lines)
│   ├── config.go                   # ✅ YAML configuration management (280 lines)
│   ├── scheduler.go                # ✅ Time-based triggers with cron (330 lines)
│   ├── integrated.go               # ✅ Combined Git+Timer monitoring (200 lines)
│   ├── daemon.go                   # ✅ Background daemon process (350 lines)
│   ├── cli.go                      # ✅ CLI commands interface (380 lines)
│   ├── demo.go                     # Test utilities for all components
│   ├── deps.go                     # Dependency retention helper
│   ├── go.mod                      # Go dependencies (go-git, fsnotify, sqlite, cron, etc.)
│   ├── GIT_INTEGRATION.md          # Git monitoring documentation
│   ├── SCHEDULER.md                # Scheduler system documentation
│   ├── DAEMON.md                   # Daemon process documentation
│   └── NOTIFICATIONS.md            # Notification configuration guide
│
└── utils/
    └── __init__.py                 # Shared utilities
```

## 🗺️ Project Roadmap & Implementation Status

**See [Roadmap.MD](Roadmap.MD)** for complete implementation tracking:
- ✅ **Checkbox-based feature list** - Every feature marked as ✅ implemented or ❌ pending
- 📊 **6 development phases** with detailed status breakdowns
- 🎯 **Priority matrix** (P0-P3) for feature planning
- ⏱️ **Timeline estimates** (Q4 2025 - Q4 2026)
- 📦 **Dependency audit** - Installed vs missing libraries
- 🚨 **Critical path to MVP** with effort estimates
- 📈 **Success metrics** for each milestone
- 🔍 **Technical recommendations** and next steps

**Current Status**: 
- **Phase 2** (Go Background Engine) - **60% complete** ✅
  - ✅ **Completed**: Git monitoring, scheduler system, daemon process, CLI interface, notification config
  - ⏳ **In Progress**: IPC communication layer, SQLite schema
- **Phase 1** (Python Prototype): 70% complete ✅
  - ✅ Working: Azure DevOps, Microsoft Graph, OLLAMA AI, CSV tracking, Teams analysis
  - ❌ Missing: NLP parsing, task matching, automated email reports
- **Overall Progress**: ~50-55% complete

### Recently Completed (November 2025)
- ✅ **Git Integration Module**: Real-time commit detection with fsnotify, post-commit hooks
- ✅ **Scheduler System**: Cron-based time triggers (default 3hr), pause/resume, work hours
- ✅ **Background Daemon**: Start/stop/restart/status, PID management, signal handling
- ✅ **CLI Interface**: Full command suite with help, version, logs, test commands
- ✅ **Notification System**: Email and Teams output configuration with daily reports

## 📚 Additional Resources
```

## � Project Structure

```
automation_tools/
├── main.py                          # FastAPI entry point
├── pyproject.toml                   # Python dependencies
├── README.md                        # Project documentation
├── Roadmap.MD                       # Implementation roadmap
├── IMPLEMENTATION_STATUS.md         # Status analysis
│
├── backend/
│   ├── ai/
│   │   └── create_tasks.py         # OLLAMA task generation (260 lines)
│   ├── azure/
│   │   ├── AzureDevOps.py          # Azure DevOps base class
│   │   ├── azure_updator.py        # Work item CRUD operations (188 lines)
│   │   ├── azure_work_items.py     # Work item utilities
│   │   └── fetch_stories.py        # Story retrieval
│   ├── data/
│   │   ├── Daily Tracker.csv       # Activity logging
│   │   ├── tasks.csv               # Task database
│   │   └── tasks.xlsx              # Excel task management
│   ├── db/
│   │   └── models.py               # Pydantic data models
│   ├── github/
│   │   ├── get_github_data.py      # Commit fetching
│   │   ├── ghAnalysis.py           # Repository analytics
│   │   └── gh_analysis.ipynb       # Analysis notebook
│   └── msgraph_python/
│       ├── main.py                 # Graph API CLI (482 lines)
│       ├── graph.py                # Graph client (316 lines)
│       ├── chat_analyzer.py        # Teams chat export
│       ├── sentiment_analysis.py   # OLLAMA sentiment analysis (627 lines)
│       └── config.cfg              # Graph API configuration
│
├── go-cli/
│   ├── main.go                     # TUI entry point
│   ├── tui.go                      # Bubble Tea interface (195 lines)
│   ├── styles.go                   # UI styling
│   └── go.mod                      # Go dependencies
│
└── utils/
    └── __init__.py                 # Shared utilities
```

##  Additional Resources

### Documentation
- **[Roadmap.MD](Roadmap.MD)** - Complete implementation roadmap with checkboxes for all features
- [Azure DevOps REST API](https://docs.microsoft.com/en-us/rest/api/azure/devops/)
- [Microsoft Graph API](https://docs.microsoft.com/en-us/graph/overview)
- [GitHub REST API](https://docs.github.com/en/rest)

### Related Projects
- [OLLAMA](https://ollama.ai/) - Local LLM runtime
- [spaCy](https://spacy.io/) - Industrial-strength NLP
- [sentence-transformers](https://www.sbert.net/) - Semantic text similarity
- [Microsoft Graph Python SDK](https://github.com/microsoftgraph/msgraph-sdk-python)

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- OLLAMA team for local LLM capabilities
- Microsoft Graph API team
- Go and Python communities
- All open-source contributors

## 📞 Support & Contact

- **Issues**: [GitHub Issues](https://github.com/sraj0501/automation_tools/issues)
- **Discussions**: [GitHub Discussions](https://github.com/sraj0501/automation_tools/discussions)
- **Owner**: [@sraj0501](https://github.com/sraj0501)

---

**Note**: This tool is designed for individual and team productivity enhancement. Ensure you have appropriate licenses and permissions for all integrated services (Microsoft 365, Azure DevOps, GitHub, etc.).

**Current Status**: Active Development - Phase 2 (Go Background Engine)  
**Overall Progress**: ~35-40% Complete  
**Detailed Status**: See [Roadmap.MD](Roadmap.MD) for complete checkbox-based feature tracking