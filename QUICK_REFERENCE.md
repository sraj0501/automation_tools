# DevTrack Quick Reference Card

## Installation (One-Time Setup)

```bash
# 1. Install all dependencies
./install_phase3_deps.sh          # NLP parsing
./install_learning_deps.sh        # Personalized AI
./install_advanced_features.sh    # Reports & Matching

# 2. Build CLI
cd go-cli && go build -o devtrack

# 3. Configure MS Graph (optional, for email/Teams)
cd ../backend/msgraph_python
# Edit config.cfg with your Azure app credentials
python main.py  # Follow device code flow
```

## Daily Commands

### Daemon Control
```bash
devtrack start          # Start background daemon
devtrack stop           # Stop daemon
devtrack restart        # Restart daemon
devtrack status         # Show current status
devtrack logs           # View recent logs
```

### Reports
```bash
devtrack preview-report                    # Preview today's report
devtrack send-report manager@company.com   # Email report
devtrack save-report                       # Save to file
```

### AI Learning
```bash
devtrack enable-learning              # Enable & collect data (30 days)
devtrack learning-status              # Check status
devtrack show-profile                 # View learned patterns
devtrack test-response "some text"    # Test generation
```

### Database
```bash
devtrack db-stats       # Show database statistics
```

## Python Tools

### Test Task Matching
```bash
python3 backend/task_matcher.py test
```

### Generate HTML Report
```bash
python3 backend/email_reporter.py html > report.html
open report.html
```

### Test NLP Parser
```bash
python3 backend/nlp_parser.py test
```

## File Locations

```
~/.devtrack/
├── daemon.pid          # Daemon process ID
├── daemon.log          # Activity logs
├── daemon.db           # SQLite database
├── config.yaml         # Configuration
├── learning/           # AI learning data
│   ├── consent.json
│   ├── samples.json
│   └── profile.json
└── reports/            # Saved reports
    └── report-YYYY-MM-DD.txt
```

## Configuration (~/.devtrack/config.yaml)

```yaml
daemon:
  check_interval: 30s
  log_level: info

git:
  monitor_interval: 5s
  
scheduler:
  enabled: true
  interval: "3h"
  start_time: "09:00"
  end_time: "18:00"

reports:
  enabled: true
  schedule: "18:00"
  recipients:
    - manager@company.com
  format: html

task_matching:
  enabled: true
  auto_match_threshold: 0.8
  suggest_threshold: 0.6
  use_semantic: true

learning:
  enabled: true
  consent_given: true
```

## Typical Workflow

### Morning
```bash
devtrack start
# Daemon begins monitoring Git commits
```

### During Day
```bash
# Work normally, commit as usual
git commit -m "Fixed login bug PROJ-123 2h"
# Daemon automatically logs activity
```

### End of Day
```bash
devtrack preview-report
devtrack send-report manager@company.com
```

### Monthly
```bash
devtrack enable-learning 30  # Refresh AI profile
```

## Troubleshooting

### Daemon won't start
```bash
# Check if already running
devtrack status

# Check logs
devtrack logs

# Force kill and restart
devtrack stop
sleep 2
devtrack start
```

### No activities in report
```bash
# Check database
devtrack db-stats

# Verify Git monitoring
devtrack status

# Check logs
tail -50 ~/.devtrack/daemon.log
```

### AI learning not working
```bash
# Check consent
devtrack learning-status

# Enable if needed
devtrack enable-learning

# Check MS Graph auth
cd backend/msgraph_python && python main.py
```

### Import errors
```bash
# Reinstall dependencies
./install_advanced_features.sh

# Test imports
python3 -c "from fuzzywuzzy import fuzz; print('✓ fuzzywuzzy')"
python3 -c "from sentence_transformers import SentenceTransformer; print('✓ transformers')"
```

## Quick Tests

### Test Everything
```bash
# Build
cd go-cli && go build -o devtrack

# Test daemon
./devtrack start
sleep 2
./devtrack status
./devtrack stop

# Test report
./devtrack preview-report

# Test AI (if enabled)
./devtrack learning-status

# Test Python
python3 ../backend/task_matcher.py test
python3 ../backend/nlp_parser.py test
```

## Performance Tips

1. **Database cleanup:** Old records auto-cleaned after 30 days
2. **Learning updates:** Refresh monthly for best results
3. **Semantic matching:** First run downloads model (~100MB)
4. **Report caching:** Reports generated fresh each time

## Security Notes

- All data stored locally in `~/.devtrack/`
- No cloud AI (only local Ollama)
- Consent required for learning
- MS Graph uses OAuth2 device code flow
- No passwords stored

## Getting Help

```bash
devtrack help          # Show all commands
devtrack version       # Show version
```

**Documentation:**
- `README.md` - Project overview
- `IMPLEMENTATION_COMPLETE.md` - Complete feature list
- `PERSONALIZED_AI.md` - AI feature guide
- `PHASE3-5_COMPLETE.md` - Advanced features

**Support:**
- Check logs: `~/.devtrack/daemon.log`
- Database stats: `devtrack db-stats`
- Status check: `devtrack status`

---

**Quick Start:** `./install_learning_deps.sh && cd go-cli && go build -o devtrack && ./devtrack start`
