# DevTrack Configuration Reference

Complete reference for all `.env` variables and configuration options.

---

## Overview

DevTrack is configured via a single `.env` file with **no hardcoded defaults for critical values**.

- Copy `.env_sample` to `.env`, then fill in your paths and credentials
- All path variables must be absolute paths (not relative)
- **The daemon does not load `.env` itself.** You must load it into the shell before running `devtrack`:

  ```bash
  set -a && source .env && set +a
  devtrack start
  ```

  Or use `direnv` (add `dotenv` to `.envrc`) or use any password manager to load the environments at runtime like one password etc.
- For production (Linux): `devtrack autostart-install` bakes all vars into the systemd unit — no manual sourcing needed
- After changing `.env`, reload with: `devtrack stop && source .env && devtrack start`

---

## Quick Setup Checklist

At minimum you need:

```bash
PROJECT_ROOT=/path/to/automation_tools
DEVTRACK_WORKSPACE=${PROJECT_ROOT}       # or multi-repo via workspaces.yaml
DATA_DIR=${PROJECT_ROOT}/Data
LLM_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2
GIT_SAGE_DEFAULT_MODEL=llama3.2
IPC_CONNECT_TIMEOUT_SECS=5
IPC_RETRY_DELAY_MS=2000
HTTP_TIMEOUT_SHORT=10
HTTP_TIMEOUT=30
HTTP_TIMEOUT_LONG=60
LLM_REQUEST_TIMEOUT_SECS=120
PROMPT_TIMEOUT_SIMPLE_SECS=30
PROMPT_TIMEOUT_WORK_SECS=60
PROMPT_TIMEOUT_TASK_SECS=120
SENTIMENT_ANALYSIS_WINDOW_MINUTES=120
WEBHOOK_PORT=8089
```

---

## System Paths

### PROJECT_ROOT *(required)*

Root directory of the `automation_tools` repository.

```bash
PROJECT_ROOT=/home/user/automation_tools
```

### DEVTRACK_HOME *(required)*

Directory containing the `devtrack` binary.

```bash
DEVTRACK_HOME=${PROJECT_ROOT}/devtrack-bin
```

### DEVTRACK_WORKSPACE

Single Git repository to monitor. Ignored when `workspaces.yaml` is present.

```bash
DEVTRACK_WORKSPACE=${PROJECT_ROOT}
# Or a different project:
# DEVTRACK_WORKSPACE=/home/user/my-project
```

### WORKSPACES_FILE *(optional)*

Override the location of `workspaces.yaml` for multi-repo mode.

```bash
WORKSPACES_FILE=/custom/path/workspaces.yaml
```

See [Multi-Repo Guide](MULTI_REPO.md) for details.

### Data Directories

```bash
DATA_DIR=${PROJECT_ROOT}/Data
DATABASE_DIR=${DATA_DIR}/db
LOG_DIR=${DATA_DIR}/logs
PID_DIR=${DATA_DIR}/pids
REPORT_DIR=${DATA_DIR}/reports
CONFIG_DIR_PATH=${DATA_DIR}/configs
LEARNING_DIR_PATH=${DATA_DIR}/learning
```

---

## Server Architecture

### DEVTRACK_SERVER_MODE

Controls how the Python backend is managed.

| Value | Behavior |
|-------|----------|
| `managed` (default) | `devtrack start` spawns the Python webhook server as a subprocess |
| `external` | Python backend runs separately; daemon connects to `DEVTRACK_SERVER_URL` |
| `cloud` | Set automatically by `devtrack cloud login`; uses `~/.devtrack/cloud.json` |

```bash
DEVTRACK_SERVER_MODE=managed
```

### DEVTRACK_SERVER_URL *(external/cloud mode)*

URL of the Python backend server.

```bash
# Managed mode: leave blank (auto-set to https://127.0.0.1:<WEBHOOK_PORT>)
DEVTRACK_SERVER_URL=

# External local:
# DEVTRACK_SERVER_URL=https://localhost:8089

# External cloud:
# DEVTRACK_SERVER_URL=https://your-devtrack-server.com
```

### DEVTRACK_TLS

Enable TLS encryption for Go ↔ Python channel. Go generates a self-signed ECDSA cert at startup; the Python server uses it.

```bash
DEVTRACK_TLS=true     # default — required for production
# DEVTRACK_TLS=false  # only for Docker internal networks or trusted dev
```

### DEVTRACK_TLS_CERT / DEVTRACK_TLS_KEY *(optional)*

Override cert/key paths. Useful when supplying a CA-signed cert for cloud deployments.

```bash
DEVTRACK_TLS_CERT=Data/tls/server.crt
DEVTRACK_TLS_KEY=Data/tls/server.key
```

### DEVTRACK_API_KEY *(optional)*

API key sent as `X-DevTrack-API-Key` header on all `/trigger/*` requests. Required for public/cloud deployments. Auto-populated by `devtrack cloud login`.

```bash
DEVTRACK_API_KEY=
```

> The Python server's port and bind address are configured by `WEBHOOK_PORT` / `WEBHOOK_HOST` — see [Webhook Server](#webhook-server) below.

---

## IPC Configuration

Internal TCP socket used for Python → Go response/ack messages (not the primary trigger channel — that is HTTPS POST).

```bash
IPC_HOST=127.0.0.1
IPC_PORT=35893
IPC_CONNECT_TIMEOUT_SECS=5    # required — no default
IPC_RETRY_DELAY_MS=2000       # required — no default
```

---

## Timeout Configuration *(all required — no defaults)*

Missing any of these causes the daemon to fail at startup with a clear error message.

| Variable | Unit | Typical value | Used by |
|----------|------|---------------|---------|
| `HTTP_TIMEOUT_SHORT` | seconds | `10` | Quick API calls, health checks |
| `HTTP_TIMEOUT` | seconds | `30` | Most API calls |
| `HTTP_TIMEOUT_LONG` | seconds | `60` | Large uploads, complex operations |
| `LLM_REQUEST_TIMEOUT_SECS` | seconds | `120` | AI model inference calls |
| `PROMPT_TIMEOUT_SIMPLE_SECS` | seconds | `30` | Quick yes/no TUI prompts |
| `PROMPT_TIMEOUT_WORK_SECS` | seconds | `60` | Work update text input |
| `PROMPT_TIMEOUT_TASK_SECS` | seconds | `120` | Detailed task descriptions |
| `SENTIMENT_ANALYSIS_WINDOW_MINUTES` | minutes | `120` | Teams sentiment analysis window |

```bash
HTTP_TIMEOUT_SHORT=10
HTTP_TIMEOUT=30
HTTP_TIMEOUT_LONG=60
LLM_REQUEST_TIMEOUT_SECS=120
PROMPT_TIMEOUT_SIMPLE_SECS=30
PROMPT_TIMEOUT_WORK_SECS=60
PROMPT_TIMEOUT_TASK_SECS=120
SENTIMENT_ANALYSIS_WINDOW_MINUTES=120
```

---

## LLM / AI Configuration

### LLM_PROVIDER

Primary LLM provider for DevTrack (commit messages, reports, descriptions).

```bash
LLM_PROVIDER=ollama       # local, free (default)
# LLM_PROVIDER=openai     # cloud, paid — better quality
# LLM_PROVIDER=anthropic  # cloud, paid — reasoning focused
# LLM_PROVIDER=groq       # cloud, fast free tier
# LLM_PROVIDER=lmstudio   # local, OpenAI-compatible
```

If the primary provider is unavailable, the system falls back to any provider with valid credentials in this order: OpenAI → Anthropic → Groq → Ollama.

### Ollama *(local, free)*

```bash
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

Pull models with `ollama pull llama3.2`.

### LM Studio *(local, OpenAI-compatible)*

```bash
LMSTUDIO_HOST=http://localhost:1234/v1
```

### OpenAI *(optional — auto-fallback when key is set)*

```bash
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
```

### Anthropic *(optional — auto-fallback when key is set)*

```bash
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-haiku-4-5
```

### Groq *(optional — auto-fallback when key is set)*

```bash
GROQ_API_KEY=
GROQ_HOST=https://api.groq.com/openai/v1
GROQ_MODEL=llama-3.3-70b-versatile
```

### git-sage LLM

git-sage can use a different provider from the main LLM pipeline.

```bash
GIT_SAGE_PROVIDER=ollama           # defaults to LLM_PROVIDER if unset
GIT_SAGE_DEFAULT_MODEL=llama3.2    # required — no default
GIT_SAGE_BASE_URL=                 # optional: override base URL
GIT_SAGE_API_KEY=                  # optional: override API key
```

### LLM Generation Parameters

Fine-tune temperature and token limits per use case.

```bash
COMMIT_LLM_TEMPERATURE=0.1
COMMIT_LLM_MAX_TOKENS=1000

REPORT_LLM_TEMPERATURE=0.3
REPORT_LLM_MAX_TOKENS=600

PERSONALIZATION_LLM_TEMPERATURE=0.7
PERSONALIZATION_LLM_MAX_TOKENS=300

DESCRIPTION_LLM_TEMPERATURE=0.3
DESCRIPTION_LLM_MAX_TOKENS=300
```

---

## Application Settings

```bash
PROMPT_INTERVAL=30        # minutes between work-update prompts
WORK_HOURS_ONLY=true      # only prompt during work hours
WORK_START_HOUR=9         # work day start (24h)
WORK_END_HOUR=18          # work day end (24h)
TIMEZONE=UTC
LOG_LEVEL=info            # debug | info | warn | error
AUTO_SYNC=true
OUTPUT_TYPE=both          # terminal | file | both
DAILY_REPORT_TIME=18:00
WEEKLY_REPORT_DAY=Friday
SEND_ON_TRIGGER=false
SEND_DAILY_SUMMARY=true
DEVTRACK_COMMIT_ONLY=false  # skip push prompt after commit
```

---

## External Integrations

### Azure DevOps

```bash
AZURE_DEVOPS_PAT=your_personal_access_token
AZURE_ORGANIZATION=your_org_name
AZURE_PROJECT=your_project_name
AZURE_API_KEY=your_azure_devops_api_key    # alternative to PAT for some endpoints
AZURE_API_VERSION=7.1
EMAIL=your_email@example.com

# Excel task import (optional)
AZURE_EXCEL_FILE=${PROJECT_ROOT}/backend/data/tasks.xlsx
AZURE_EXCEL_SHEET=my_tasks

# Work item creation defaults (optional)
AZURE_PARENT_WORK_ITEM_ID=              # parent ID for newly created work items
AZURE_STARTING_WORK_ITEM_ID=0           # offset for work item ID lookups
```

**Bidirectional sync:**

```bash
AZURE_SYNC_ENABLED=false
AZURE_SYNC_AUTO_COMMENT=true       # post comment on matched work item
AZURE_SYNC_AUTO_TRANSITION=false   # change state when work is "done"
AZURE_SYNC_CREATE_ON_NO_MATCH=false
AZURE_SYNC_MATCH_THRESHOLD=0.7     # 0.0–1.0 fuzzy-match confidence
AZURE_SYNC_WINDOW_HOURS=0          # 0 = full resync; N = last N hours

AZURE_POLL_ENABLED=false           # poll for new assignments
AZURE_POLL_INTERVAL_MINS=5
```

See [Azure DevOps Guide](AZURE_DEVOPS.md).

### GitHub

```bash
GITHUB_TOKEN=your_github_token
GITHUB_OWNER=your_username_or_org
GITHUB_REPO=your_repo_name
GITHUB_API_URL=                    # blank for github.com; set for GHE
GITHUB_API_VERSION=2022-11-28
```

**Bidirectional sync:**

```bash
GITHUB_SYNC_ENABLED=false
GITHUB_AUTO_COMMENT=true
GITHUB_AUTO_TRANSITION=false
GITHUB_CREATE_ON_NO_MATCH=false
GITHUB_MATCH_THRESHOLD=0.6
GITHUB_DONE_STATE=closed
GITHUB_SYNC_LABEL=devtrack
GITHUB_AUTO_UPDATE_DESCRIPTION=false
GITHUB_SYNC_WINDOW_HOURS=0              # 0 = full resync; N = last N hours only
GITHUB_LOG_PATH=                        # optional: override branch-analysis log path
```

See [GitHub Guide](GITHUB.md).

### GitLab

```bash
GITLAB_URL=https://gitlab.com      # or self-hosted URL
GITLAB_PAT=your_personal_access_token
GITLAB_PROJECT_ID=                 # numeric project ID
```

**Bidirectional sync:**

```bash
GITLAB_SYNC_ENABLED=false
GITLAB_SYNC_WINDOW_HOURS=0
GITLAB_AUTO_COMMENT=true
GITLAB_AUTO_TRANSITION=false
GITLAB_CREATE_ON_NO_MATCH=false
GITLAB_MATCH_THRESHOLD=0.6
GITLAB_DONE_STATE=closed
GITLAB_SYNC_LABEL=devtrack
GITLAB_AUTO_UPDATE_DESCRIPTION=false
GITLAB_POLL_ENABLED=false
GITLAB_POLL_INTERVAL_MINS=5
```

**Webhook auto-registration** (requires public URL):

`GITLAB_PROJECT_IDS`, `DEVTRACK_WEBHOOK_PUBLIC_URL`, and `WEBHOOK_GITLAB_SECRET` are configured in the [Webhook Server](#webhook-server) section.

See [GitLab Guide](GITLAB.md).

### Jira

```bash
JIRA_URL=https://yourorg.atlassian.net
JIRA_EMAIL=your_email@example.com
JIRA_API_TOKEN=your_jira_api_token
JIRA_PROJECT_KEY=PROJ
```

### Email / Microsoft Teams

```bash
EMAIL_TO_ADDRESSES=dev@example.com
EMAIL_CC_ADDRESSES=manager@example.com
EMAIL_MANAGER=manager@example.com
EMAIL_SUBJECT="DevTrack Daily Report"

TEAMS_CHANNEL_ID=your_teams_channel_id
TEAMS_CHANNEL_NAME="DevTrack Updates"
TEAMS_CHAT_ID=your_teams_chat_id
TEAMS_CHAT_TYPE=channel
TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/your-webhook-url
TEAMS_MENTION_USER=false
SENTIMENT_TARGET_SENDER=          # display name for responsiveness tracking
```

### Azure AD / Microsoft Graph *(optional)*

Required for Teams chat collection (personalization learning) and spec emailer via MS Graph.

```bash
AZURE_CLIENT_ID=
AZURE_TENANT_ID=
AZURE_CLIENT_SECRET=
```

---

## Webhook Server

Receives inbound events from Azure DevOps, GitHub, and GitLab. Also serves as the HTTP endpoint the Go daemon POSTs triggers to.

```bash
WEBHOOK_ENABLED=false
WEBHOOK_PORT=8089
WEBHOOK_HOST=0.0.0.0

# Authentication for each inbound source
WEBHOOK_AZURE_USERNAME=devtrack
WEBHOOK_AZURE_PASSWORD=           # Basic Auth password for Azure webhooks
WEBHOOK_GITHUB_SECRET=            # HMAC secret for GitHub webhooks
WEBHOOK_GITLAB_SECRET=            # Token for GitLab webhooks (X-Gitlab-Token header)

# Notification delivery
WEBHOOK_NOTIFY_OS=true
WEBHOOK_NOTIFY_TERMINAL=true

# GitLab webhook auto-registration (optional)
GITLAB_PROJECT_IDS=               # comma-separated numeric project IDs
DEVTRACK_WEBHOOK_PUBLIC_URL=      # public URL of this server (e.g. https://myserver.com)
```

---

## Ticket Alerter

Polls GitHub, Azure DevOps, and Jira for events relevant to you (assignments, comments, state changes). Delivers macOS OS notifications and terminal output.

```bash
ALERT_ENABLED=true
ALERT_POLL_INTERVAL_SECS=300      # poll every 5 minutes

ALERT_GITHUB_ENABLED=true         # requires GITHUB_TOKEN
ALERT_AZURE_ENABLED=true          # requires AZURE_DEVOPS_PAT + AZURE_ORGANIZATION
ALERT_JIRA_ENABLED=true           # requires JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN

ALERT_NOTIFY_ASSIGNED=true
ALERT_NOTIFY_COMMENTS=true
ALERT_NOTIFY_STATUS_CHANGES=true
ALERT_NOTIFY_REVIEW_REQUESTED=true  # GitHub only

AZURE_EMAIL=you@yourorg.com       # filter out your own Azure comments
```

---

## Telegram Bot

```bash
TELEGRAM_ENABLED=false
TELEGRAM_BOT_TOKEN=
TELEGRAM_ALLOWED_CHAT_IDS=        # comma-separated chat IDs
TELEGRAM_NOTIFY_COMMITS=false
TELEGRAM_NOTIFY_TRIGGERS=true
TELEGRAM_NOTIFY_HEALTH=true
HEALTH_AUTO_RESTART_TELEGRAM=true
```

See [Telegram Bot Guide](TELEGRAM_BOT.md).

## Slack Bot

```bash
SLACK_ENABLED=false
SLACK_BOT_TOKEN=                  # xoxb-... Bot User OAuth Token
SLACK_APP_TOKEN=                  # xapp-... App-Level Token (Socket Mode)
SLACK_ALLOWED_CHANNEL_IDS=        # comma-separated channel IDs; blank = all
```

Setup: Create a Slack App → enable Socket Mode → add `/devtrack` slash command → add scopes `chat:write`, `commands`, `channels:read`.

---

## Admin Console (CS-3)

Web UI at `http://localhost:8090/admin/`.

```bash
ADMIN_PORT=8090
ADMIN_HOST=0.0.0.0
ADMIN_USERNAME=admin
ADMIN_PASSWORD=changeme           # change before exposing to a network
ADMIN_SECRET_KEY=                 # JWT signing secret (generate: python3 -c "import secrets; print(secrets.token_hex(32))")
ADMIN_SESSION_HOURS=8
```

`ADMIN_PASSWORD` may be a bcrypt hash (`$2b$...`) or plain text (local dev only).

---

## Vacation Mode

```bash
VACATION_CONFIDENCE_THRESHOLD=0.7   # minimum LLM confidence to auto-submit (0–1)
VACATION_AUTO_SUBMIT=true           # false = log only, don't post to PM
```

---

## Work Session Tracking

```bash
EOD_REPORT_HOUR=18                  # auto-generate EOD report at this hour (0 = disabled)
EOD_REPORT_EMAIL=you@org.com        # default recipient for auto EOD reports
WORK_SESSION_AUTO_STOP_MINUTES=0    # auto-stop idle session after N minutes (0 = disabled)
```

---

## AI Project Planning

```bash
NEWPROJECT_ENABLED=true
SPEC_REVIEW_BASE_URL=http://localhost:8089   # URL where PMs review/approve specs
```

---

## Infrastructure (docker-compose)

### MongoDB

MongoDB is used for personalization (communication samples, user profiles) and alert deduplication. Leave `MONGODB_URI` blank to use file-based fallback storage.

```bash
MONGO_USER=devtrack
MONGO_PASSWORD=devtrack
MONGO_PORT=27017
MONGODB_DB_NAME=devtrack
MONGODB_URI=mongodb://${MONGO_USER}:${MONGO_PASSWORD}@localhost:${MONGO_PORT}/${MONGODB_DB_NAME}?authSource=admin
```

### Redis

```bash
REDIS_PASSWORD=devtrack
REDIS_PORT=6379
REDIS_MAX_MEMORY=256mb
REDIS_URL=redis://:${REDIS_PASSWORD}@localhost:${REDIS_PORT}/0
```

### PostgreSQL

```bash
POSTGRES_USER=devtrack
POSTGRES_PASSWORD=devtrack
POSTGRES_DB=devtrack
POSTGRES_PORT=5432
POSTGRES_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT}/${POSTGRES_DB}
```

Start all services: `docker compose up -d`

---

## Offline Resilience & Health Checks

```bash
HEALTH_CHECK_INTERVAL_SECS=30
HEALTH_AUTO_RESTART_PYTHON=true
HEALTH_AUTO_RESTART_WEBHOOK=true
HEALTH_MAX_RESTARTS_PER_HOUR=3
QUEUE_DRAIN_INTERVAL_SECS=10
QUEUE_MAX_RETRIES=10
QUEUE_RETENTION_DAYS=7
DEFERRED_COMMIT_EXPIRY_HOURS=72
```

---

## Personalization & Learning

```bash
LEARNING_PYTHON_PATH=python3
LEARNING_SCRIPT_PATH=${PROJECT_ROOT}/backend/learning_integration.py
LEARNING_DAILY_SCRIPT_PATH=${PROJECT_ROOT}/backend/run_daily_learning.py
LEARNING_DEFAULT_DAYS=30
LEARNING_CRON_ENABLED=false
LEARNING_CRON_SCHEDULE="0 20 * * *"   # daily at 8 PM
LEARNING_HISTORY_DAYS=30

# RAG personalization (ChromaDB + Ollama)
# Requires: ollama pull nomic-embed-text
PERSONALIZATION_RAG_ENABLED=true
PERSONALIZATION_EMBED_MODEL=nomic-embed-text
PERSONALIZATION_RAG_K=3
PERSONALIZATION_CHROMA_DIR=${DATA_DIR}/learning/chroma
```

---

## Semantic Model

```bash
SEMANTIC_MODEL_NAME=all-MiniLM-L6-v2
```

---

## Project Sync

```bash
PROJECT_SYNC_ENABLED=false
PROJECT_SYNC_INTERVAL_SECS=300
PM_AGENT_MAX_ITEMS_PER_LEVEL=10
PM_AGENT_DEFAULT_PLATFORM=azure
```

---

## Commit Enhancement

AI-powered commit message enhancement via `devtrack git commit`.

```bash
COMMIT_ENHANCE_MODE=false    # set true to enable AI enhancement on every commit
```

---

## Telemetry & Cloud

```bash
# Anonymous install/active ping (disable with: devtrack telemetry off)
DEVTRACK_PING_URL=https://ping.devtrack.dev   # set empty to disable without CLI

# DevTrack cloud API (empty for self-hosted / local-only use)
DEVTRACK_API_URL=

# Auto-accept terms of service (for CI/headless installs)
DEVTRACK_AUTO_ACCEPT_TERMS=false
```

---

## Build Metadata

```bash
DEVTRACK_VERSION=0.1.0-alpha
DEVTRACK_BUILD_DATE=2026-03-02
```

---

## Changing Configuration

Edit `.env`, then reload — the daemon does not watch the file for changes:

```bash
devtrack stop
nano .env
set -a && source .env && set +a
devtrack start
devtrack status
```

If using `autostart-install` (launchd/systemd), re-run it after `.env` changes so the new values are baked into the service unit:

```bash
devtrack autostart-uninstall
devtrack autostart-install
```

---

## Validation

```bash
# Check all required vars are set
grep -E "IPC_CONNECT_TIMEOUT_SECS|HTTP_TIMEOUT_SHORT|HTTP_TIMEOUT=|HTTP_TIMEOUT_LONG|IPC_RETRY_DELAY_MS|OLLAMA_HOST|LMSTUDIO_HOST|GIT_SAGE_DEFAULT_MODEL|PROMPT_TIMEOUT_SIMPLE_SECS|PROMPT_TIMEOUT_WORK_SECS|PROMPT_TIMEOUT_TASK_SECS|LLM_REQUEST_TIMEOUT_SECS|SENTIMENT_ANALYSIS_WINDOW_MINUTES" .env

# Test daemon can start
devtrack start
devtrack status
```

---

**Related:** [Architecture Overview](ARCHITECTURE.md) · [Multi-Repo Guide](MULTI_REPO.md) · [LLM Setup](LLM_GUIDE.md) · [Troubleshooting](TROUBLESHOOTING.md)
