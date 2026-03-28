# Ticket Alerter

A background polling service that watches GitHub, Azure DevOps, and Jira for events relevant to you — delivering macOS OS notifications and terminal output so you never miss an assignment or comment.

---

## Quick Start

### 1. Configure `.env`

```bash
ALERT_ENABLED=true
ALERT_POLL_INTERVAL_SECS=300     # poll every 5 minutes

# Per-source toggles
ALERT_GITHUB_ENABLED=true
ALERT_AZURE_ENABLED=true
ALERT_JIRA_ENABLED=true

# Per-event toggles
ALERT_NOTIFY_ASSIGNED=true
ALERT_NOTIFY_COMMENTS=true
ALERT_NOTIFY_STATUS_CHANGES=true
ALERT_NOTIFY_REVIEW_REQUESTED=true   # GitHub only

# Optional: filter out your own Azure/Jira comments
# AZURE_EMAIL=you@yourorg.com
```

### 2. Start the daemon

```bash
devtrack start
```

The alerter poller starts automatically as a subprocess of the daemon when `ALERT_ENABLED=true`.

### 3. View notifications

```bash
devtrack alerts            # show unread notifications (last 24 h)
devtrack alerts --all      # show all notifications
devtrack alerts --clear    # mark all as read
```

---

## Events by Source

| Source | Events | Notes |
|--------|--------|-------|
| **GitHub** | Assigned to issue or PR | Checks `assignee` field |
| | Review requested on PR | `ALERT_NOTIFY_REVIEW_REQUESTED` |
| | Comment on issue/PR you're involved in | Filters own comments |
| **Azure DevOps** | Work item assigned to you | First-run guard (skips on cold start) |
| | Comment added to your work items | Filters `AZURE_EMAIL` author |
| | State changed on your work items | First-run guard |
| **Jira** | Issue assigned to you | JQL `assignee changed to currentUser()` |
| | Comment on your issues | Filters own email |
| | Status changed on your issues | JQL `status changed` |

---

## Notification Delivery

### macOS OS Notifications

Uses `osascript` to show a native notification:

```
DevTrack Alert — GitHub
"PR Review Requested: Fix login redirect (#142)"
```

Configure `ALERT_NOTIFY_OS=true` (default `true`).

### Terminal Output

When the daemon is running in a terminal session, alerts are also printed to stdout. Configure `ALERT_NOTIFY_TERMINAL=true` (default `true`).

---

## Architecture

```
alert_poller.py  (async, runs as daemon subprocess)
  ├── GitHubAlerter    — GitHub REST API
  ├── AzureAlerter     — Azure DevOps REST API
  └── JiraAlerter      — Jira REST API
          │
          ▼
  MongoAlertsStore     — MongoDB notifications + alert_state collections
  (file-based fallback if MongoDB unavailable)
          │
          ▼
  AlertNotifier
    ├── macOS: osascript
    └── Terminal: stdout (if TTY)
```

Each alerter tracks `last_checked` per user in the `alert_state` MongoDB collection so only new events are processed on each poll cycle.

---

## MongoDB Schema

```
notifications collection:
  _id:        ObjectId
  source:     "github" | "azure" | "jira"
  event_type: "assigned" | "comment" | "status_change" | "review_requested"
  ticket_id:  "owner/repo#123" | "PROJ-42"
  title:      "Fix login bug"
  summary:    "Alice commented: LGTM"
  url:        "https://..."
  timestamp:  datetime
  read:       false
  dismissed:  false
  raw:        { ...full API payload... }
```

---

## Implementation Files

```
backend/
  ├── alert_poller.py           — Main async poller; orchestrates all sources
  ├── alert_notifier.py         — macOS osascript + terminal output
  ├── alerters/
  │   ├── github_alerter.py     — GitHub assigned/comments/review-requests
  │   ├── azure_alerter.py      — Azure DevOps assigned/comments/state-changes
  │   └── jira_alerter.py       — Jira assigned/comments/status-changes
  └── db/mongo_alerts.py        — MongoAlertsStore: notifications + alert_state
```

---

## Troubleshooting

**No notifications appearing**

- Check `ALERT_ENABLED=true` and the per-source toggle (`ALERT_GITHUB_ENABLED`, etc.)
- Verify the daemon is running: `devtrack status`
- Check logs: `devtrack logs | grep alert`

**Getting your own comments as notifications**

- Set `AZURE_EMAIL=you@yourorg.com` (Azure/Jira filter)
- The alerters automatically skip comments where the author matches your configured email

**First poll shows no results (Azure/Jira)**

- Expected — first-run guard skips assigned and state-change events on the initial poll to avoid a flood of old notifications. Subsequent polls will catch new events.

**MongoDB not configured**

- The alerter works without MongoDB using an in-memory state store, but notifications will not persist across restarts. Set `MONGODB_URI` to enable persistence.
