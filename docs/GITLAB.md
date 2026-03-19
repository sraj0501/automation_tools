# GitLab Integration Guide

DevTrack integrates with GitLab to give you offline-capable issue browsing, syncing, and creation — both from the CLI and from the Telegram bot.

---

## Quick Start

1. **Create a Personal Access Token (PAT)** in GitLab:
   - Go to **Settings → Access Tokens**
   - Select scopes: `api`, `read_user`
   - Copy the token

2. **Add required variables to `.env`**:

```env
GITLAB_URL=https://gitlab.com
GITLAB_PAT=your_token_here
GITLAB_PROJECT_ID=12345678    # numeric project ID from Settings → General
EMAIL=you@example.com
```

3. **Test connectivity**:

```bash
devtrack gitlab-check
```

---

## Configuration

All configuration is via `.env`. Copy from `.env_sample`.

### Core Authentication

| Variable | Required | Description |
|---|---|---|
| `GITLAB_URL` | Yes | Your GitLab instance URL (default: `https://gitlab.com`) |
| `GITLAB_PAT` | Yes | Personal Access Token with `api` scope |
| `GITLAB_PROJECT_ID` | Yes | Numeric project ID (found in Settings → General) |
| `EMAIL` | Yes | Your GitLab email (used to filter assigned issues) |

### Sync Behavior

| Variable | Default | Description |
|---|---|---|
| `GITLAB_SYNC_ENABLED` | `false` | Enable background sync on daemon start |
| `GITLAB_SYNC_WINDOW_HOURS` | `0` | Hours to look back (`0` = full sync, `N` = last N hours) |

### Assignment Poller

| Variable | Default | Description |
|---|---|---|
| `GITLAB_POLL_ENABLED` | `false` | Enable polling for new issue assignments |
| `GITLAB_POLL_INTERVAL_MINS` | `5` | How often to check for new assignments |

---

## CLI Commands

### Check Connectivity

```bash
devtrack gitlab-check
```

Verifies your PAT, email identity, and (if `GITLAB_PROJECT_ID` is set) project access.
Outputs masked token for safety.

### List Issues

```bash
devtrack gitlab-list                     # Open issues assigned to you
devtrack gitlab-list --closed           # Include closed issues
devtrack gitlab-list --state <state>    # Filter: opened, closed, all
```

Issues are grouped by milestone for easy overview.

### View Issue Details

```bash
devtrack gitlab-view <project_id> <iid>
# Example:
devtrack gitlab-view 12345678 42
```

Shows full issue details: title, state, milestone, labels, description (HTML stripped), and URL.

### Sync Issues

```bash
devtrack gitlab-sync                    # Full sync (all open issues)
devtrack gitlab-sync --full            # Explicit full sync
devtrack gitlab-sync --hours 24       # Only issues updated in last 24 h
```

Sync stores issues locally at `Data/gitlab/sync_state.json`. Subsequent `gitlab-list` reads from this cache for speed — no API call needed.

---

## Sync Architecture

The local sync cache (`Data/gitlab/sync_state.json`) stores each issue keyed by its global GitLab ID:

```json
{
  "global_id": 123456789,
  "iid": 42,
  "project_id": 12345678,
  "title": "Fix login redirect",
  "state": "opened",
  "milestone_title": "Sprint 5",
  "labels": ["bug", "backend"],
  "due_date": null,
  "url": "https://gitlab.com/org/repo/-/issues/42",
  "synced_at": "2026-03-19T10:00:00Z"
}
```

- **Full sync** (`--full` or `GITLAB_SYNC_WINDOW_HOURS=0`): clears cache, fetches all open issues
- **Delta sync** (`--hours N`): merges only recently-updated issues into existing cache

---

## Assignment Poller

When `GITLAB_POLL_ENABLED=true`, the daemon starts a background poller that:

1. Checks for issues newly assigned to you every `GITLAB_POLL_INTERVAL_MINS` minutes
2. Skips issues already seen (tracked in `Data/gitlab/seen_assignments.json`)
3. Sends a Telegram notification for each new assignment (requires Telegram bot configured)

The notification includes a **View Details** button that opens the issue in the Telegram bot.

**Enable:**

```env
GITLAB_POLL_ENABLED=true
GITLAB_POLL_INTERVAL_MINS=5
TELEGRAM_ENABLED=true
```

---

## Telegram Bot Commands

When the Telegram bot is running, you can interact with GitLab issues from your phone:

| Command | Description |
|---------|-------------|
| `/gitlab` | List issues from the local sync cache |
| `/gitlabissue <project_id> <iid>` | View full details for an issue (live fetch) |
| `/gitlabcreate` | Create a new issue interactively (milestone picker shown) |

### Creating an Issue via Telegram

1. Send `/gitlabcreate`
2. Bot shows a milestone picker (inline keyboard)
3. Select a milestone (or "No Milestone")
4. Bot prompts: `Send the issue title:`
5. Reply with the title
6. Issue is created and the URL is returned

---

## API Reference

`GitLabClient` (`backend/gitlab/client.py`) provides async methods used internally by all GitLab scripts:

```python
from backend.gitlab.client import GitLabClient

client = GitLabClient()

# Read
issues = await client.get_my_issues(state="opened")
issue  = await client.get_issue(project_id=12345678, iid=42)
milestones = await client.get_milestones(project_id=12345678)

# Write
new_issue = await client.create_issue(
    title="Fix login redirect",
    description="Users are redirected to /home instead of /dashboard",
    labels=["bug"],
    milestone_id=5,
)
await client.add_comment(project_id=12345678, iid=42, comment="Fixed in abc123")
await client.close_issue(project_id=12345678, iid=42)

await client.close()
```

---

## Troubleshooting

**`gitlab-check` fails with 401:**
- Verify your PAT has `api` scope
- Confirm `GITLAB_PAT` is set correctly in `.env` (no trailing whitespace)
- Check `GITLAB_URL` matches your GitLab instance (self-hosted users: include the full URL)

**`gitlab-list` shows no issues:**
- Run `devtrack gitlab-sync` first to populate the local cache
- Check `EMAIL` in `.env` matches the email in your GitLab account (used to filter assignments)

**No assignment notifications:**
- Verify `GITLAB_POLL_ENABLED=true` and `TELEGRAM_ENABLED=true`
- Check `GITLAB_POLL_INTERVAL_MINS` (minimum 1)
- Look at logs: `devtrack logs | grep -i gitlab`

**Project ID not found:**
- The numeric project ID is in GitLab under **Settings → General** at the top of the page
- Alternatively: `GET /api/v4/projects?search=<repo-name>` returns the `id` field

**Self-hosted GitLab:**
- Set `GITLAB_URL=https://your-gitlab.company.com` (no trailing slash)
- All API calls go to `GITLAB_URL/api/v4/...`
