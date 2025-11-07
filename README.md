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

### Installation

\`\`\`bash
# 1. Install dependencies
./install_phase3_deps.sh          # NLP parsing
./install_learning_deps.sh        # Personalized AI
./install_advanced_features.sh    # Reports & Matching

# 2. Build CLI
cd go-cli && go build -o devtrack

# 3. Configure MS Graph (optional)
cd ../backend/msgraph_python
# Edit config.cfg with your Azure app credentials
python main.py  # Follow device code flow
\`\`\`

### Basic Usage

\`\`\`bash
# Start the daemon
./devtrack start

# Check status
./devtrack status

# View logs
./devtrack logs

# Stop the daemon
./devtrack stop
\`\`\`

### Key Commands

\`\`\`bash
# Daemon Control
devtrack start|stop|restart|status|logs

# AI Learning
devtrack enable-learning              # Enable & collect data
devtrack learning-status              # Check status
devtrack show-profile                 # View learned patterns

# Reports
devtrack preview-report               # Preview today's report
devtrack send-report <email>          # Email report

# Manual Triggers
devtrack force-trigger                # Trigger immediately
devtrack skip-next                    # Skip next trigger
\`\`\`

## Technology Stack

### Backend (Go)
- Go daemon for monitoring and triggers
- fsnotify for Git repository monitoring
- Cron-based scheduling
- SQLite for local caching

### Intelligence (Python)
- OLLAMA for local LLM processing
- spaCy for NLP and entity recognition
- sentence-transformers for semantic matching
- Microsoft Graph SDK for integrations

### Integrations
- Azure DevOps REST API
- Microsoft Graph API (Teams, Email, Lists)
- GitHub API
- Jira API (planned)

## Privacy & Security

DevTrack is built with privacy as a core principle:
- All data stored locally on your machine
- No cloud AI services (uses local Ollama)
- Explicit consent required for AI learning features
- Complete transparency about data collection
- Full data deletion option available anytime

For complete details, see the **[Privacy Policy](wiki/privacy.html)**.

## Project Status

**Current Phase**: Phase 2 (Go Background Engine)  
**Overall Progress**: ~50-55% Complete

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
