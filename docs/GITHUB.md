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

## Checking Connectivity

There is no dedicated CLI command yet — verify connectivity via the Telegram bot:

```
/github
```

If GitHub is configured correctly, you will see your open issues. If credentials are missing or invalid, the bot will reply with a clear error message.

---

## Security Notes

- **Never commit your token** — it lives only in `.env`, which is in `.gitignore`
- Set token scopes to the minimum required: `repo` (full repo access) is sufficient; `read:org` is only needed for organization repositories
- For shared machines, use a fine-grained PAT scoped to specific repositories

---

## Troubleshooting

**`/github` replies "GitHub client not configured":**
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
