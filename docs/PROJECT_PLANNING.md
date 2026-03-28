# AI Project Planning

The `/newproject` Telegram command turns a plain-text requirements description into a fully-structured project plan — with sprints, stories, capacity analysis, and risk assessment — and creates everything in your PM tool (Azure DevOps, GitHub, or GitLab) on approval.

---

## How It Works

```
PM types /newproject in Telegram
        │
        ▼
Pick platform (Azure / GitHub / GitLab)
        │
        ▼
Describe the project in plain text
  (requirements, deadline, your email)
        │
        ▼
Select team members from live platform roster
  (multi-select toggle keyboard)
        │
        ▼
AI fetches each developer's current workload
  from Azure/GitHub/GitLab automatically
        │
        ▼
LLM generates full YAML spec:
  features → stories → sprints
  capacity analysis, skill gaps, risks
        │
        ├──► Email to PM with Approve/Edit link
        │
        ▼
PM reviews via Telegram preview OR web form
  • Approve → creates everything in PM tool
  • Request changes → iterative revision loop
        │
        ▼
Sprints, epics, stories created with
topological dependency ordering
```

---

## Quick Start

### 1. Configure `.env`

```bash
# Base URL for the spec review web form
SPEC_REVIEW_BASE_URL=http://your-server:8089

# Email delivery requires Azure Graph credentials
AZURE_CLIENT_ID=...
AZURE_TENANT_ID=...
AZURE_CLIENT_SECRET=...
```

### 2. Start `/newproject` in Telegram

```
/newproject
```

The bot will guide you through:

1. **Platform** — Azure DevOps, GitHub, or GitLab
2. **Requirements** — paste your requirements, deadline (`by July 31`), and your email address in one free-text message
3. **Team selection** — the bot fetches the team roster from your platform and shows an inline keyboard. Tap names to toggle selection (✅).
4. **Generation** — the AI fetches workloads, builds the spec, sends you a preview and an email

### 3. Review and Approve

After generation you'll see:
```
Customer Portal Redesign
Sprints: 4 | Stories: 18 | ✅ On track

Risks:
  • [MEDIUM] Alice has 3 active bugs that may spill into Sprint 1
  • [HIGH] No mobile developer — M1 story requires React Native

[Review & edit full spec] (link)
```

Tap **✅ Approve & Create** or **✏️ Request Changes**.

---

## Spec Format

The generated spec is YAML and follows this structure:

```yaml
spec_meta:
  version: 1
  spec_id: "uuid"
  status: draft          # draft | pending_review | approved | in_progress | completed
  pm_platform: azure
  pm_email: pm@org.com
  review_url: http://your-server:8089/spec/{id}/review

project:
  name: "Customer Portal Redesign"
  deadline: "2026-07-31"
  goals:
    - "Modernize the UI"
    - "Add SSO integration"

team:
  developers:
    - name: "Alice Chen"
      email: alice@org.com
      platform_user_id: alice@org.com
      skills:
        primary: [frontend, react]
        secondary: [testing]
      capacity_override: null   # set to {available_days: N, reason: "..."} to override

workload_snapshot:              # AI-computed from platform
  pulled_at: "2026-03-28T10:00:00Z"
  developers:
    - name: "Alice Chen"
      current_assignments:
        - {item_id: "PROJ-123", title: "Fix login bug", estimated_days_remaining: 2.0}
      committed_days: 2.0
      available_days: 78.0
      capacity_source: auto     # auto | override

features:
  - id: F1
    title: "User Authentication"
    skill_required: [backend, security]
    stories:
      - id: S1
        title: "OAuth2 provider setup"
        story_points: 8
        assigned_to: "Bob Patel"
        sprint: 1
        depends_on: []
        acceptance_criteria:
          - "OAuth2 flow works with Google"

sprints:
  - number: 1
    name: "Sprint 1 — Foundation"
    start: "2026-04-07"
    end: "2026-04-18"
    goal: "Auth + core data model"
    stories: [S1, S2]

capacity_analysis:
  estimated_effort_days: 120
  on_track: true
  buffer_days: 53
  risks:
    - type: skill_gap
      severity: high
      message: "No mobile developer assigned"
      recommendation: "Add a mobile specialist or descope"

approval:
  status: pending
  iterations: []
```

---

## Capacity Override

If a developer is unavailable (vacation, other project), the PM can override their capacity. Add to the spec before approving:

```yaml
capacity_override:
  available_days: 10
  reason: "On leave weeks 1-2"
```

---

## Web Review Form

The spec review form is served by the webhook server at:

```
GET  /spec/{spec_id}/review   — editable YAML form
POST /spec/{spec_id}/review   — submit approval or change request
```

The PM can edit the YAML directly in the browser before approving.

To use the web form, the webhook server must be reachable from the PM's browser. Set `SPEC_REVIEW_BASE_URL` in `.env` to the public or local URL.

---

## What Gets Created on Approval

| Platform | Sprint | Feature | Story |
|----------|--------|---------|-------|
| Azure DevOps | Iteration node | Feature work item | User Story (with story points, assignee, parent) |
| GitHub | Milestone | Label | Issue (with milestone, assignee, labels) |
| GitLab | Milestone | Label | Issue (with milestone, assignee, labels) |

Stories are created in topological order — a story that depends on another is always created after its dependency.

---

## Module Reference (`backend/project_spec/`)

| Module | Class | Key Methods |
|--------|-------|-------------|
| `developer_roster.py` | `DeveloperRoster` | `list_team_members(platform)` |
| `workload_analyzer.py` | `WorkloadAnalyzer` | `analyze(devs, platform, deadline)` |
| `spec_generator.py` | `SpecGenerator` | `generate(...)`, `revise(spec, feedback)` |
| `spec_store.py` | `SpecStore` | `save(spec)`, `load(spec_id)`, `update_status(...)` |
| `project_creator.py` | `ProjectCreator` | `create(spec, dry_run=False)` |
| `spec_emailer.py` | `SpecEmailer` | `send_draft(spec)` |

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `NEWPROJECT_ENABLED` | `true` | Enable the `/newproject` command |
| `SPEC_REVIEW_BASE_URL` | `http://localhost:8089` | Base URL for web review form links |
| `MONGODB_URI` | _(optional)_ | MongoDB for spec storage; falls back to files |
| `MONGODB_DB` | `devtrack` | MongoDB database name |

Spec files are stored under `DATA_DIR/project_specs/` when MongoDB is not configured.
