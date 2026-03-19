# Multi-Repo Monitoring Guide

Monitor multiple Git repositories simultaneously, each routing to its own project management platform.

---

## Overview

By default, DevTrack monitors a single repository (`DEVTRACK_WORKSPACE` in `.env`) and uses a priority chain to decide which PM platform to sync to (Azure → GitLab → GitHub).

**Multi-repo mode** removes that ambiguity:
- Each repository gets its own entry in `workspaces.yaml`
- Each workspace declares exactly one `pm_platform`
- Commits in that repo route directly to the declared platform — no guessing

**Backward compatibility**: If `workspaces.yaml` does not exist, DevTrack continues to behave exactly as before.

---

## Setup

### Step 1: Create workspaces.yaml

Copy the sample and edit it:

```bash
cp workspaces.yaml.sample workspaces.yaml
```

```yaml
# workspaces.yaml
version: "1"
workspaces:
  - name: "work-api"
    path: ~/work/api
    pm_platform: azure        # azure | gitlab | github | jira | none
    pm_project: ""            # optional: platform-specific project override
    enabled: true
    ignore_branches: []
    tags: [work]

  - name: "oss-lib"
    path: ~/oss/my-lib
    pm_platform: github
    pm_project: ""
    enabled: true
    ignore_branches: [main]
    tags: [oss]

  - name: "internal-tools"
    path: ~/work/tools
    pm_platform: gitlab
    pm_project: "12345"       # GitLab numeric project ID (overrides GITLAB_PROJECT_ID)
    enabled: true
    ignore_branches: []
    tags: [work]
```

### Step 2: Restart the daemon

```bash
devtrack restart
```

The daemon reads `workspaces.yaml` at startup and starts one Git monitor per enabled workspace.

### Step 3: Verify

```bash
devtrack status
```

The status output shows `workspace_count: N` confirming multi-repo mode is active.

---

## workspaces.yaml Reference

### File Location

By default: `$PROJECT_ROOT/workspaces.yaml`

Override with the `WORKSPACES_FILE` env var:

```env
WORKSPACES_FILE=/path/to/my/workspaces.yaml
```

### Schema

```yaml
version: "1"              # schema version (required)
workspaces:
  - name: string          # display name (required)
    path: string          # absolute or ~/ path to the Git repo (required)
    pm_platform: string   # routing target (required; see values below)
    pm_project: string    # optional platform-specific override (see below)
    enabled: bool         # true = monitored, false = ignored (default: true)
    ignore_branches: list # branch names to ignore (optional)
    tags: list            # arbitrary labels for your own organization (optional)
```

### pm_platform Values

| Value | Routes to | Notes |
|-------|-----------|-------|
| `azure` | Azure DevOps | Uses `AZURE_DEVOPS_ORG`, `AZURE_DEVOPS_PROJECT` from `.env` |
| `gitlab` | GitLab | Uses `GITLAB_PROJECT_ID` from `.env` unless `pm_project` is set |
| `github` | GitHub | Uses `GITHUB_OWNER`/`GITHUB_REPO` from `.env` |
| `jira` | Jira | Not yet implemented |
| `none` | — | Monitoring active, PM sync disabled for this repo |
| `` (empty) | Priority chain | Falls back to Azure → GitLab → GitHub (single-repo behavior) |

### pm_project Field

Allows overriding the PM project per workspace without changing global `.env` vars:

| Platform | pm_project meaning |
|----------|-------------------|
| `azure` | Azure DevOps project name (overrides `AZURE_DEVOPS_PROJECT`) |
| `gitlab` | Numeric project ID (overrides `GITLAB_PROJECT_ID`) |
| `github` | Ignored — owner/repo comes from `.env` |

---

## How Routing Works

When a commit fires in workspace `work-api` with `pm_platform: azure`:

1. Go daemon detects the commit in `~/work/api`
2. The IPC trigger message includes `pm_platform: "azure"` and `workspace_name: "work-api"`
3. Python bridge reads `pm_platform` from the message
4. `_route_pm_sync("azure", ...)` is called — only Azure is contacted, GitLab and GitHub are skipped
5. Azure work item is matched, commented, and optionally transitioned

When `pm_platform` is empty (or workspaces.yaml is absent), the legacy priority chain runs: Azure → GitLab → GitHub, stopping at the first match.

---

## Per-Platform Configuration

Each platform must still be configured in `.env`. The workspace routing just determines *which* platform is called — not *how* it behaves.

### Azure DevOps

```env
AZURE_DEVOPS_ORG=my-org
AZURE_DEVOPS_PROJECT=MyProject
AZURE_DEVOPS_TOKEN=<pat>

AZURE_SYNC_ENABLED=true
AZURE_SYNC_AUTO_COMMENT=true
AZURE_SYNC_AUTO_TRANSITION=false
AZURE_SYNC_CREATE_ON_NO_MATCH=false
AZURE_SYNC_MATCH_THRESHOLD=0.7
```

See [Azure DevOps Guide](AZURE_DEVOPS.md).

### GitLab

```env
GITLAB_URL=https://gitlab.com
GITLAB_PAT=<pat>
GITLAB_PROJECT_ID=12345678

GITLAB_SYNC_ENABLED=true
GITLAB_AUTO_COMMENT=true
GITLAB_AUTO_TRANSITION=false
GITLAB_CREATE_ON_NO_MATCH=false
GITLAB_MATCH_THRESHOLD=0.6
```

See [GitLab Guide](GITLAB.md).

### GitHub

```env
GITHUB_TOKEN=<token>
GITHUB_OWNER=my-org
GITHUB_REPO=my-repo

GITHUB_SYNC_ENABLED=true
GITHUB_AUTO_COMMENT=true
GITHUB_AUTO_TRANSITION=false
GITHUB_CREATE_ON_NO_MATCH=false
GITHUB_MATCH_THRESHOLD=0.6
```

See [GitHub Guide](GITHUB.md).

---

## Disabling a Workspace

Set `enabled: false` to pause monitoring without removing the entry:

```yaml
  - name: "old-project"
    path: ~/old/project
    pm_platform: azure
    enabled: false       # monitored but inactive
```

Restart the daemon after changing `enabled`.

---

## Troubleshooting

**Daemon starts in single-repo mode despite workspaces.yaml:**
- Confirm the file is at `$PROJECT_ROOT/workspaces.yaml` (or `WORKSPACES_FILE` is set)
- Check for YAML parse errors: `uv run python -c "import yaml; yaml.safe_load(open('workspaces.yaml'))"`
- Check daemon logs: `devtrack logs | grep -i workspace`

**A workspace is not being monitored:**
- Confirm `enabled: true` for that entry
- Confirm the path exists and is a valid Git repo: `git -C ~/work/api status`
- Check logs for `skipping workspace` messages

**Commits routing to wrong platform:**
- Confirm `pm_platform` value matches one of: `azure`, `gitlab`, `github`, `none`, or empty
- An unknown value falls back to the priority chain; check logs for `Unknown pm_platform` warning
- Confirm `DEVTRACK_WORKSPACE` in `.env` is not overriding (it is ignored when workspaces.yaml is present)

**pm_project not being used:**
- For GitLab: `pm_project` must be a numeric string (e.g., `"12345"`)
- Strings that fail int conversion are silently ignored, falling back to `GITLAB_PROJECT_ID`
