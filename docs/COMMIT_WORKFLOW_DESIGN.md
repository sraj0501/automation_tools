# Commit Workflow Design

> **Architecture decision document.** This file defines the intended design for DevTrack's commit workflow. Engineering work on this subsystem should follow this design. Changes to the design should be recorded here with rationale before implementation begins.

**Status**: Planned — not yet implemented
**Supersedes**: The existing `backend/commit_message_enhancer.py` hook approach
**Last reviewed**: April 1, 2026

---

## Vision

When a developer commits, DevTrack should:

1. Silently capture a shadow commit on a local audit branch
2. Reason across the developer's full ticket context to rank relevant issues
3. Surface a single approval screen: commit message + top ticket match + PM update draft
4. After approval, commit lands on the real branch; PM tool is updated asynchronously

The developer never leaves the terminal. The AI does the context work; the human makes the final call.

---

## Design Principles

- **AI ranks, human picks.** The AI provides a ranked, reasoned shortlist. The developer confirms. No silent auto-assignment.
- **Context match over fuzzy match.** The AI reasons across all assigned tickets + the diff — not just text similarity. "Given what you're supposed to be working on, what does this change relate to?"
- **Fresh data where it matters.** Full ticket list is cached locally. At commit time, the top 5 candidates are live-fetched for guaranteed freshness. The bulk cache is eventually consistent.
- **PM sync is mandatory at setup.** DevTrack cannot operate in commit-workflow mode without tickets loaded. Onboarding enforces this.
- **Never block the commit.** If any step fails (network down, AI timeout), the commit still goes through. PM updates are queued for later.
- **Never leave the terminal.** Creating tickets, updating status, commenting — all from the TUI.

---

## Data Flow

### Onboarding (one-time, mandatory)

```
devtrack init
  1. Connect PM tool  →  auth flow (token / OAuth)
  2. Full ticket sync →  all open tickets assigned to user
                         embed each (title + description + comments)
                         store in local SQLite + vector index
  3. Watch repo       →  git hook installed
                         shadow branch naming confirmed
  4. Ready            →  "Make a commit to see DevTrack in action."
```

The ticket sync is not skippable. If it fails, `devtrack init` reports a clear error and does not complete. This guarantees DevTrack always has context before it intercepts a commit.

### Background refresh (periodic, silent)

- Delta sync every 6 hours (or on `devtrack start`)
- Fetches only tickets updated since `last_sync`
- Re-embeds changed tickets
- Never blocks the developer

### At commit time (two-stage)

**Stage 1 — local, instant (target: < 500ms)**
- Embed the diff summary
- Score against full local ticket cache (cosine similarity over embeddings)
- Rerank with branch name, session history, recent commits on this branch
- Produce top 5 candidates with relevance scores + AI reasoning

**Stage 2 — live fetch, targeted (target: < 2 sec)**
- Fetch fresh state of top 5 tickets from PM API
- Update local cache for those 5 tickets
- Surface to TUI with guaranteed-fresh data

This two-tier approach keeps the ranking fast (local) while ensuring the developer never approves an update against stale ticket data.

---

## Commit Flow (step by step)

```
Developer: git commit -m "fix token refresh"
                │
                ▼
     DevTrack intercepts (prepare-commit-msg hook)
                │
     ┌──────────┴────────────┐
     │ async, non-blocking   │  sync
     ▼                       ▼
Shadow commit            Stage 1: local ranking
devtrack/<branch>        Stage 2: live fetch top 5
(raw progress,                    │
 no approval)                     ▼
                         Approval TUI
                                  │
                    ┌─────────────┴─────────────┐
                    │ sync                       │ async
                    ▼                            ▼
           Commit → real branch         PM tool updated
           with AI-refined message      (comment + status transition)
```

---

## Approval TUI

Single screen, keyboard-driven, target time-on-screen: 3–5 seconds.

```
┌─ DevTrack ──────────────────────────────────────────────────┐
│                                                              │
│  COMMIT MESSAGE                                    [e]dit   │
│  ───────────────────────────────────────────────────────    │
│  Fix token refresh retry logic in session handler           │
│                                                             │
│  TICKET                              ████████░░  82% match  │
│  ───────────────────────────────────────────────────────    │
│  ▶ AUTH-156  Token refresh not retrying           [↑↓ pick] │
│    AUTH-142  Login fails after session expiry               │
│    AUTH-138  Session invalidated on mobile                  │
│    + Create new ticket                                      │
│    + Skip PM update                                         │
│                                                             │
│  PM UPDATE  (AUTH-156)                             [e]dit   │
│  ───────────────────────────────────────────────────────    │
│  Implemented retry logic with exponential backoff.          │
│  3 retries before hard logout. PR #67 linked.               │
│                                                             │
│  STATUS  In Progress → In Review  (auto-transition)         │
│                                                             │
│  [Enter] Approve   [e] Edit   [↑↓] Change ticket   [s] Skip │
└─────────────────────────────────────────────────────────────┘
```

### Status auto-transition rules

Transitions only fire when:
- Match confidence > 85%, AND
- Developer approves (Enter)

Below 85%: a comment is posted, but status is not changed. Developer can override via `[e]dit`.

---

## Create New Ticket (in-flow)

When the developer selects "+ Create new ticket":

```
┌─ New Ticket ────────────────────────────────────────────────┐
│                                                              │
│  AI draft (from diff + commit message + branch context):     │
│                                                              │
│  Title:    Add retry logic for token refresh failures        │
│  Type:     Bug                                               │
│  Priority: Medium                                            │
│  Assigned: you                                               │
│  Epic:     AUTH-100  Authentication Rework  (inferred)       │
│                                                              │
│  Description:                                                │
│  Token refresh silently fails when auth service is          │
│  temporarily unavailable. Session invalidated instead of    │
│  retrying. Needs exponential backoff, 3 retries max.         │
│                                                              │
│  [Enter] Create & link   [e] Edit   [Esc] Back               │
└─────────────────────────────────────────────────────────────┘
```

On creation:
- Ticket created in PM tool, assigned to user
- Immediately linked to the commit
- PM update posted as first comment
- Added to local cache with embedding
- Commit proceeds

Epic inference: the AI looks at which epic nearby tickets belong to and places the new ticket there. Developer edits if wrong.

---

## Shadow Branch

`devtrack/<branch-name>` — a local-only audit trail.

| Behaviour | Detail |
|---|---|
| Created automatically | On first intercepted commit on a branch, if it doesn't exist |
| Receives every commit | Including abandoned or rewritten ones — unfiltered progress log |
| Never pushed automatically | Stays local unless explicitly pushed by developer |
| Pruned automatically | After N days (default: 30) or via `devtrack prune-shadows` |
| Never blocks the commit | Shadow branch failures are logged and ignored; real commit proceeds |

---

## Offline & Failure Behaviour

| Scenario | Behaviour |
|---|---|
| PM API unreachable at commit time | Stage 2 (live fetch) skipped; TUI shows cached data with `[stale]` indicator; PM update queued |
| AI ranking times out (> 3 sec) | TUI opens with "still ranking..." then populates; developer can proceed with message only |
| Developer uses `git commit --no-verify` | Shadow commit still captured; PM update queued via next `devtrack sync` |
| Ticket cache empty (first install, sync not done) | Commit proceeds; TUI shows "Run devtrack sync-tickets to enable ticket matching" |

---

## Terminal PM Commands

Beyond commits, the same ticket cache and AI layer powers standalone terminal PM access:

```bash
devtrack tickets              # List assigned open tickets (from cache)
devtrack tickets --all        # Include closed/resolved
devtrack ticket AUTH-156      # Full detail + comments
devtrack new-ticket           # Create from scratch interactively
devtrack update AUTH-156      # Update status or add comment
devtrack sync-tickets         # Force full refresh of ticket cache
```

---

## Local Cache Schema

```sql
-- Full ticket cache (bulk sync + background refresh)
tickets (
  id              TEXT PRIMARY KEY,   -- "github:owner/repo:123"
  source          TEXT,               -- github | jira | azure
  external_id     TEXT,
  title           TEXT,
  description     TEXT,
  status          TEXT,
  priority        TEXT,
  epic_id         TEXT,
  linked_branches TEXT,               -- JSON array
  last_synced_at  DATETIME,
  embedding       BLOB                -- float32 array, stored as bytes
)

-- Live fetch log
ticket_live_fetches (
  ticket_id       TEXT,
  fetched_at      DATETIME,
  commit_sha      TEXT
)

-- PM update queue (for offline / skipped commits)
pm_update_queue (
  id              INTEGER PRIMARY KEY,
  ticket_id       TEXT,
  update_text     TEXT,
  transition_to   TEXT,
  commit_sha      TEXT,
  created_at      DATETIME,
  status          TEXT                -- pending | sent | failed
)
```

No separate vector database needed. Cosine similarity over 50–200 embeddings (one developer's assigned tickets) runs in microseconds in Python with numpy.

---

## Build Order

| Step | Component | Depends on |
|---|---|---|
| 1 | **Ticket cache** — SQLite schema + sync from GitHub | PM client (exists) |
| 2 | **Ticket embedder** — embed on sync, store in cache | Ticket cache |
| 3 | **Context ranker** — diff embed + score + rerank | Ticket embedder |
| 4 | **Live fetcher** — top-5 fresh fetch at commit time | Context ranker |
| 5 | **Shadow branch manager** — create/manage devtrack/* branches | git_operations.py (exists) |
| 6 | **Approval TUI** — ranked ticket list + commit msg + PM update | Context ranker + shadow branch |
| 7 | **New ticket creator** — in-TUI creation with AI draft | Approval TUI + PM client |
| 8 | **Async PM updater** — post-approval fire-and-forget + queue | Approval TUI |
| 9 | **Commit orchestrator** — replaces prepare-commit-msg hook | All of the above |

Start with GitHub as the PM source. The cache schema and ranker are PM-agnostic — Jira and Azure slot in later by implementing the same sync interface.

---

## What This Replaces

The existing `backend/commit_message_enhancer.py` (`prepare-commit-msg` hook) handles only message enhancement. It will be superseded by the commit orchestrator (Step 9 above). The existing file can be used as reference for the hook invocation pattern but the logic will not be carried forward.

`backend/task_matcher.py` (fuzzy + semantic matching) is the foundation for the context ranker (Step 3) and should be extended rather than replaced.
