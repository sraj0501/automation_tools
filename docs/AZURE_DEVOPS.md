# Azure DevOps Integration Guide

DevTrack integrates with Azure DevOps for bidirectional work item synchronization. When you commit code or submit work updates, DevTrack can match them to Azure work items, add comments, transition states, and keep your local project state in sync with Azure.

## Table of Contents

- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Features](#features)
- [Bidirectional Sync](#bidirectional-sync)
- [Webhook Integration](#webhook-integration)
- [Notifications](#notifications)
- [Legacy Utilities](#legacy-utilities)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

1. **Create a Personal Access Token (PAT)** in Azure DevOps:
   - Go to `https://dev.azure.com/{organization}/_usersSettings/tokens`
   - Create token with scopes: **Work Items (Read & Write)**

2. **Add required variables to `.env`**:

```env
AZURE_DEVOPS_PAT=your_pat_here
AZURE_ORGANIZATION=your_org_name
AZURE_PROJECT=your_project_name
EMAIL=you@example.com

# Enable sync
AZURE_SYNC_ENABLED=true
```

3. **Start DevTrack** — the daemon will automatically initialize the Azure client on startup.

---

## Configuration

All configuration is via `.env`. Copy from `.env_sample` and fill in values.

### Core Authentication

| Variable | Required | Description |
|---|---|---|
| `AZURE_DEVOPS_PAT` | Yes | Personal Access Token (falls back to `AZURE_API_KEY`) |
| `AZURE_ORGANIZATION` | Yes | Organization name from `dev.azure.com/{org}` |
| `AZURE_PROJECT` | Yes | Project name within the organization |
| `EMAIL` | Yes | Your Azure DevOps email (used to filter assigned items) |
| `AZURE_API_VERSION` | No | API version (default: `7.1`) |

### Sync Behavior

| Variable | Default | Description |
|---|---|---|
| `AZURE_SYNC_ENABLED` | `false` | Enable bidirectional sync |
| `AZURE_SYNC_AUTO_COMMENT` | `true` | Add comment on matched work items when you commit |
| `AZURE_SYNC_AUTO_TRANSITION` | `false` | Auto-transition state when work is marked done |
| `AZURE_SYNC_CREATE_ON_NO_MATCH` | `false` | Create new work item if no match found |
| `AZURE_SYNC_MATCH_THRESHOLD` | `0.7` | Confidence threshold for task matching (0.0–1.0) |
| `AZURE_SYNC_STATES` | `New,Active,In Progress` | Work item states to fetch |
| `AZURE_SYNC_DONE_STATE` | `Done` | Target state when marking items complete |
| `AZURE_SYNC_WORK_ITEM_TYPE` | `Task` | Work item type for newly created items |
| `AZURE_SYNC_DEFAULT_AREA_PATH` | — | Default area path for new work items |
| `AZURE_SYNC_DEFAULT_ITERATION_PATH` | — | Default iteration path for queries |
| `AZURE_SYNC_TAG` | `devtrack-managed` | Tag applied to all DevTrack-managed items |

### State Mapping

Map local DevTrack project states to Azure DevOps work item states:

| Variable | Default | Maps To |
|---|---|---|
| `AZURE_SYNC_STATE_SETUP` | `New` | Local `SETUP` project status |
| `AZURE_SYNC_STATE_ACTIVE` | `Active` | Local `ACTIVE` project status |
| `AZURE_SYNC_STATE_CLOSED` | `Done` | Local `CLOSED` project status |
| `AZURE_SYNC_GOAL_STATE_PENDING` | `New` | Local goal `PENDING` status |
| `AZURE_SYNC_GOAL_STATE_IN_PROGRESS` | `Active` | Local goal `IN_PROGRESS` status |
| `AZURE_SYNC_GOAL_STATE_COMPLETED` | `Done` | Local goal `COMPLETED` status |

---

## Features

### Commit-Triggered Sync

When you run `devtrack git commit` (or when the git monitor detects a commit), DevTrack:

1. Extracts task context from the commit message using NLP
2. Searches Azure work items assigned to you for a match
3. If a match is found above `AZURE_SYNC_MATCH_THRESHOLD`:
   - Adds a comment with the commit hash, author, and message (if `AZURE_SYNC_AUTO_COMMENT=true`)
   - Transitions the work item state (if `AZURE_SYNC_AUTO_TRANSITION=true` and work is done)
4. If no match and `AZURE_SYNC_CREATE_ON_NO_MATCH=true`: creates a new work item

You can also reference a ticket explicitly in your commit message or work update:
```
Fix login redirect issue [PROJ-123]
```
DevTrack will match directly by ticket ID, skipping fuzzy search.

### Timer-Triggered Sync

When the scheduled timer fires and you submit a work update:

1. The work update text is matched against Azure work items
2. Same comment/transition/create logic as commit sync
3. Git context (branch, PR, recent changes) is injected before matching for better accuracy

### Task Matching

DevTrack uses a two-stage matching approach:

1. **Exact ticket ID** — regex-scans the text for patterns like `PROJ-123`, `AB#123`; bypasses fuzzy search
2. **Fuzzy + semantic match** — `task_matcher.py` scores candidate work items by title similarity; only picks matches above `AZURE_SYNC_MATCH_THRESHOLD`

---

## Bidirectional Sync

The `AzureProjectSync` class (`backend/azure/sync.py`) handles full bidirectional state between local DevTrack projects and Azure DevOps.

### Push Local → Azure

```python
# Sync a specific project's goals to Azure work items
sync.sync_project_to_azure(project_id)
```

- Creates an Azure work item for each project goal that doesn't have one
- Updates existing work items if state has changed
- Tags all managed items with `AZURE_SYNC_TAG`
- Stores goal→work_item ID mappings in `Project.metadata`

### Pull Azure → Local

```python
# Fetch Azure items and create/update local projects
sync.sync_azure_to_local(iteration_path="MyTeam\\Sprint 5")
```

- Fetches work items tagged `AZURE_SYNC_TAG` in the given iteration
- Groups by area path → creates matching local projects
- Updates goal states based on Azure work item states

### Full Two-Phase Sync

```python
sync.full_sync()
```

Phase 1: Push all locally tracked projects to Azure.
Phase 2: Pull any Azure items not yet tracked locally.

### Webhook-Driven Updates

When Azure fires a webhook (e.g., a teammate changes a work item state), `AzureProjectSync.handle_webhook_update()` processes the event and updates the local project/goal state automatically.

---

## Webhook Integration

DevTrack includes a FastAPI webhook server that receives events from Azure DevOps, GitHub, and Jira.

### Setup

1. Enable the webhook server in `.env`:

```env
WEBHOOK_ENABLED=true
WEBHOOK_HOST=0.0.0.0
WEBHOOK_PORT=8089
WEBHOOK_AZURE_USERNAME=devtrack
WEBHOOK_AZURE_PASSWORD=choose_a_strong_password
```

2. In Azure DevOps, create a **Service Hook**:
   - Go to **Project Settings → Service Hooks → Create subscription**
   - Select **Web Hooks**
   - Events: Work item updated, Work item commented, Work item created
   - URL: `http://your-host:8089/webhooks/azure-devops`
   - Authentication: Basic auth with the username/password from `.env`

3. Start DevTrack — the webhook server starts automatically with the daemon.

### Webhook Endpoints

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/webhooks/azure-devops` | POST | Basic Auth | Azure DevOps service hook events |
| `/webhooks/github` | POST | HMAC-SHA256 | GitHub webhook events |
| `/webhooks/jira` | POST | None | Jira webhook events |
| `/health` | GET | None | Server health check |
| `/status` | GET | None | Service status with IPC connection state |

### Handled Azure Events

| Event | Action |
|---|---|
| `workitem.updated` | Syncs state/field changes to local project |
| `workitem.commented` | Sends notification with comment text |
| `workitem.created` | Notifies, optionally tracks new item |
| `workitem.deleted` | Sends notification |

---

## Notifications

DevTrack delivers notifications for incoming webhook events through two channels.

### Terminal Notifications

Colored output with a terminal bell:
```
[DevTrack] Work item PROJ-123 updated: "Fix login redirect" → Active
```

Enable/disable: `WEBHOOK_NOTIFY_TERMINAL=true`

### macOS OS Notifications

Native macOS notification via `osascript`:

Enable/disable: `WEBHOOK_NOTIFY_OS=true`

---

## API Reference

The `AzureDevOpsClient` class (`backend/azure/client.py`) provides async methods for all Azure DevOps REST API operations.

```python
from backend.azure.client import AzureDevOpsClient

client = AzureDevOpsClient()

# Read
projects = await client.get_projects()
items = await client.get_my_work_items(states=["Active", "In Progress"])
item = await client.get_work_item(work_item_id=123)
results = await client.search_work_items(query="login bug")

# Write
new_item = await client.create_work_item(
    title="Fix login redirect",
    work_item_type="Task",
    area_path="MyOrg\\MyProject\\Backend",
    iteration_path="MyOrg\\MyProject\\Sprint 5",
)
await client.update_work_item_state(work_item_id=123, new_state="Active")
await client.add_comment(work_item_id=123, comment="Committed fix in abc123")
await client.update_work_item_fields(work_item_id=123, fields={
    "System.Title": "Updated title",
    "Microsoft.VSTS.Scheduling.StoryPoints": 3,
})
```

The client authenticates using HTTP Basic Auth with your PAT token. All methods are `async` and require an active event loop.

---

## Legacy Utilities

These standalone scripts exist for one-off operations and are not part of the core daemon flow:

| Script | Purpose |
|---|---|
| `backend/azure/azure_work_items.py` | Interactive CLI browser for projects and work items |
| `backend/azure/fetch_stories.py` | Fetch user stories assigned to `EMAIL` |
| `backend/azure/azure_updator.py` | Bulk create tasks from an Excel file with duplicate detection |

### Excel Bulk Import

```env
AZURE_EXCEL_FILE=/path/to/tasks.xlsx
AZURE_EXCEL_SHEET=my_tasks
AZURE_PARENT_WORK_ITEM_ID=100
AZURE_DEFAULT_ASSIGNEE=you@example.com
```

Run:
```bash
uv run python backend/azure/azure_updator.py
```

---

## Troubleshooting

**Azure client not initializing at daemon startup**
- Check `AZURE_DEVOPS_PAT`, `AZURE_ORGANIZATION`, and `AZURE_PROJECT` are set in `.env`
- Verify the PAT has **Work Items (Read & Write)** scope
- Check logs: `devtrack logs | grep -i azure`

**Work items not being matched**
- Lower `AZURE_SYNC_MATCH_THRESHOLD` (e.g., `0.5`) to allow weaker matches
- Reference the ticket ID explicitly in your commit/update: `[PROJ-123]`
- Check that `AZURE_SYNC_STATES` includes the state of items you want to match

**Commits not auto-commenting**
- Confirm `AZURE_SYNC_ENABLED=true` and `AZURE_SYNC_AUTO_COMMENT=true`
- Run `devtrack logs | grep -i "sync\|azure"` to see sync activity

**Webhook not receiving events**
- Verify `WEBHOOK_ENABLED=true` and the server is accessible from Azure (check firewall/port)
- Test with: `curl http://localhost:8089/health`
- Check Azure DevOps service hook delivery log for errors (Project Settings → Service Hooks → Recent deliveries)
- Ensure Basic Auth credentials in Azure match `WEBHOOK_AZURE_USERNAME`/`WEBHOOK_AZURE_PASSWORD`

**State transitions not happening**
- `AZURE_SYNC_AUTO_TRANSITION` must be `true`
- DevTrack only transitions when the local status is "done/closed" — check `AZURE_SYNC_DONE_STATE` matches your workflow

**Webhook server won't start**
- Confirm `WEBHOOK_HOST`, `WEBHOOK_PORT`, and `WEBHOOK_AZURE_PASSWORD` are set
- Check that port `8089` (or configured port) is not already in use: `lsof -i :8089`
- Verify `fastapi` and `uvicorn` are installed: `uv run python -c "import fastapi, uvicorn"`
