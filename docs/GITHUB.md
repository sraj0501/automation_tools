# GitHub Integration Guide

DevTrack integrates with GitHub to give you issue browsing, bidirectional sync, and creation — both from the CLI and from the Telegram bot.

---

## Quick Start

1. **Create a Personal Access Token (PAT)** in GitHub:
   - Go to **Settings → Developer settings → Personal access tokens → Tokens (classic)**
   - Select scopes: `repo`, `read:org`
   - Copy the token

2. **Add required variables to `.env`**:

```env
GITHUB_TOKEN=<your-github-token>
GITHUB_OWNER=<your-github-username-or-org>
GITHUB_REPO=<repository-name>
EMAIL=<your-github-email>
```

3. **Enable bidirectional sync** (optional):

```env
GITHUB_SYNC_ENABLED=true
```

---

## Configuration

All configuration is via `.env`. Copy from `.env_sample`.

### Core Authentication

| Variable | Required | Description |
|---|---|---|
| `GITHUB_TOKEN` | Yes | Personal Access Token with `repo` scope |
| `GITHUB_OWNER` | Yes | GitHub username or organization name |
| `GITHUB_REPO` | Yes | Repository name (without owner prefix) |
| `EMAIL` | Yes | Your GitHub email (used to filter assigned issues) |

### GitHub Enterprise

| Variable | Default | Description |
|---|---|---|
| `GITHUB_API_URL` | `https://api.github.com` | Set this to your GHE base API URL |
| `GITHUB_API_VERSION` | `2022-11-28` | GitHub REST API version header |

For GitHub Enterprise Server:

```env
GITHUB_API_URL=https://github.mycompany.com/api/v3
```

### Bidirectional Sync

When a commit or timer trigger fires, DevTrack matches the work description against your open issues and comments, closes, or creates them.

| Variable | Default | Description |
|---|---|---|
| `GITHUB_SYNC_ENABLED` | `false` | Enable automatic issue sync on commits and timer triggers |
| `GITHUB_AUTO_COMMENT` | `true` | Post a comment on matched issues |
| `GITHUB_AUTO_TRANSITION` | `false` | Close matched issues when status is `done`/`completed` |
| `GITHUB_CREATE_ON_NO_MATCH` | `false` | Open a new issue when no match is found |
| `GITHUB_MATCH_THRESHOLD` | `0.6` | Fuzzy-match confidence threshold (0.0–1.0) |
| `GITHUB_DONE_STATE` | `closed` | State to transition to when marking done |
| `GITHUB_SYNC_LABEL` | `devtrack` | Label added to issues created by DevTrack |

### Optional Enrichment Behaviors

| Variable | Default | Description |
|---|---|---|
| `GITHUB_AUTO_UPDATE_DESCRIPTION` | `false` | Append the latest commit hash and message to the body of a matched issue |
| `GITHUB_DEFAULT_MILESTONE` | _(unset)_ | Milestone title to assign when DevTrack creates a new issue |

---

## CLI Commands

### Check Connectivity

```bash
devtrack github-check
```

Verifies your token, email identity, and repository access. Outputs masked token for safety.

### List Issues

```bash
devtrack github-list                     # Open issues assigned to you
devtrack github-list --closed           # Include closed issues
devtrack github-list --state <state>    # Filter: open, closed, all
```

Issues are grouped by milestone for easy overview.

### View Issue Details

```bash
devtrack github-view <number>
# Example:
devtrack github-view 42
```

Shows full issue details: title, state, milestone, labels, description, and URL.

### Sync Issues

```bash
devtrack github-sync                    # Full sync (all open issues)
devtrack github-sync --full            # Explicit full sync
devtrack github-sync --hours 24       # Only issues updated in last 24 h
```

Sync stores issues locally at `Data/github/sync_state.json`. Subsequent `github-list` reads from this cache for speed — no API call needed.

---

## Telegram Commands

| Command | Description |
|---------|-------------|
| `/github` | List open issues assigned to you (live from API) |
| `/githubissue <number>` | View full details for an issue |
| `/githubcreate [bug\|feature\|task] <title>` | Create a new issue (type prefix optional) |

**Examples:**

```
/github
/githubissue 42
/githubcreate bug Login page crashes on Safari
/githubcreate feature Add dark mode support
/githubcreate Improve CI pipeline speed
```

The `/github` command goes live to the API on every call — no prior sync needed.

---

## How Bidirectional Sync Works

When `GITHUB_SYNC_ENABLED=true`, every commit trigger and work update is processed as follows:

1. **Fetch** open issues assigned to you via `GET /issues`
2. **Match** the commit message or work description against issue titles using fuzzy + semantic matching
3. If confidence ≥ `GITHUB_MATCH_THRESHOLD`:
   - **Comment** on the matched issue (if `GITHUB_AUTO_COMMENT=true`)
   - **Close** the issue (if `GITHUB_AUTO_TRANSITION=true` and status is `done`)
4. If no match found and `GITHUB_CREATE_ON_NO_MATCH=true`:
   - **Create** a new issue with the work description and `GITHUB_SYNC_LABEL` label

In multi-repo mode with `workspaces.yaml`, this sync is only called when the workspace has `pm_platform: github`. See [Multi-Repo Guide](MULTI_REPO.md).

---

## Inbound Webhooks

DevTrack can receive real-time events from GitHub via the built-in webhook server.

### Endpoint

```
POST /webhooks/github
```

Authenticated with HMAC-SHA256 signature: GitHub sends `X-Hub-Signature-256`, DevTrack validates against `WEBHOOK_GITHUB_SECRET`.

### Supported Events

| Event | Action | What DevTrack does |
|-------|--------|--------------------|
| `issues` | `assigned` | OS + terminal notification |
| `issues` | `opened` | OS + terminal notification |
| `issue_comment` | `created` | Notification if comment is on your issue |
| `pull_request` | `review_requested` | Notification |

### Setup

1. In your GitHub repository: **Settings → Webhooks → Add webhook**
2. Payload URL: `https://your-server/webhooks/github`
3. Content type: `application/json`
4. Secret: set to `WEBHOOK_GITHUB_SECRET` in `.env`
5. Select individual events: Issues, Issue comments, Pull requests

```env
WEBHOOK_ENABLED=true
WEBHOOK_GITHUB_SECRET=your_secret_here
```

---

## Issue Enrichment on Create

When DevTrack creates a new GitHub issue (via `GITHUB_CREATE_ON_NO_MATCH=true` or Telegram `/githubcreate`), it automatically:

- Appends the triggering commit hash and message to the issue description
- Assigns the issue to the authenticated user
- Applies `GITHUB_DEFAULT_MILESTONE` if configured

---

## Security Notes

- **Never commit your token** — it lives only in `.env`, which is in `.gitignore`
- Set token scopes to the minimum required: `repo` (full repo access) is sufficient; `read:org` is only needed for organization repositories
- For shared machines, use a fine-grained PAT scoped to specific repositories

---

## Troubleshooting

**`github-check` fails or `/github` replies "GitHub client not configured":**
- Verify `GITHUB_TOKEN`, `GITHUB_OWNER`, and `GITHUB_REPO` are all set in `.env`
- Restart DevTrack: `devtrack restart`

**Issues not showing up:**
- The API returns issues assigned to the authenticated user only
- Verify your token user matches `EMAIL` in `.env`
- PRs are filtered out automatically — only issues are shown

**Comments not appearing on matched issues:**
- Check `GITHUB_AUTO_COMMENT=true` in `.env`
- Check `GITHUB_SYNC_ENABLED=true` in `.env`
- Lower `GITHUB_MATCH_THRESHOLD` if matches are not being found (e.g., `0.4`)

**GitHub Enterprise:**
- Set `GITHUB_API_URL` to your GHE base API URL (no trailing slash)
- Tokens from github.com do not work on GHE — create a token on your GHE instance
