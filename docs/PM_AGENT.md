# PM Agent — AI Work Item Decomposition

The PM Agent uses an LLM to break down a problem statement into a structured work item hierarchy (Epic → Story/Feature → Task/Bug) and creates those items directly in your project management platform.

---

## Overview

Given a natural-language problem description, the PM Agent:

1. **Decomposes** the problem into a 3-level hierarchy using your configured LLM
2. **Shows a preview** of the hierarchy (indented tree + item count)
3. **Creates all items** in the target platform, respecting parent-child ordering
4. **Reports progress** item by item as creation happens

Supported platforms: **Azure DevOps**, **GitLab**, **GitHub**

---

## How to Use (Telegram `/plan` Command)

The PM Agent is accessed via the Telegram bot:

```
/plan Build a user authentication system with OAuth2 support
```

### Step 1 — Platform Picker

The bot presents an inline keyboard:

```
Select platform:
[Azure DevOps]  [GitLab]  [GitHub]
```

### Step 2 — LLM Decomposition + Preview

The LLM decomposes your problem and the bot shows:

```
Epic: Authentication System
  User Story: User Login
    Task: Build login form
    Bug: Fix session timeout
  User Story: OAuth2 Integration
    Task: Implement OAuth2 provider
    Task: Add token refresh logic

4 items total: 1 epic(s), 2 story/feature(s), 3 task(s)/bug(s)

[✅ Create All]  [❌ Cancel]
```

### Step 3 — Confirm

Tap **Create All** and the bot creates each item, sending live progress updates:

```
✅ Epic: Authentication System (ID: 1042)
✅ Story: User Login (ID: 1043, parent: 1042)
✅ Task: Build login form (ID: 1044)
...
Done. 4 created, 0 failed.
```

---

## Platform Hierarchy Mapping

| Level | Azure DevOps | GitLab | GitHub |
|-------|-------------|--------|--------|
| 0 (top) | Epic | Milestone | Milestone |
| 1 | Feature / User Story | Issue (label: story) | Issue |
| 2 | Task / Bug | Issue (label: task/bug) | Issue |

- **GitLab/GitHub milestones** are used at level 0 because they are universally available (GitLab Epics require Premium tier)
- Parent–child relationships: Azure uses native parent links; GitLab/GitHub set the `milestone_id` on child issues

---

## Configuration

```env
# PM Agent defaults
PM_AGENT_DEFAULT_PLATFORM=azure   # Default platform if not using Telegram picker
PM_AGENT_MAX_ITEMS_PER_LEVEL=10  # Hard cap per level to prevent runaway decomposition
```

The PM Agent uses your existing LLM configuration (`LLM_PROVIDER`, `OLLAMA_HOST`, etc.) and the platform credentials already configured for Azure/GitLab/GitHub.

---

## Programmatic API

`PMAgent` (`backend/pm_agent.py`) can be used directly in Python:

```python
from backend.pm_agent import PMAgent

# Create agent for a platform
agent = PMAgent(platform="azure")

# Decompose a problem
plan = agent.decompose("Build a user authentication system")

# Preview the plan
print(agent.format_preview(plan))
# Epic: Authentication System
#   Feature: User Login
#     Task: Build login form
#     Bug: Fix session timeout
# ...
# 4 items total: 1 epic(s), 1 story/feature(s), 2 task(s)/bug(s)

# Create all items (async)
import asyncio
created, failed = asyncio.run(agent.create_all(plan))
print(f"Created: {len(created)}, Failed: {len(failed)}")
```

### With Progress Callback

```python
async def show_progress(node, status):
    print(f"  {node.item_type}: {node.title} — {status}")

created, failed = await agent.create_all(plan, on_progress=show_progress)
```

### Constructor Options

```python
agent = PMAgent(
    platform="azure",           # "azure" | "gitlab" | "github"
    provider=my_llm_provider,   # Optional: inject a custom LLM provider (useful for testing)
    project_context="...",      # Optional: extra context injected into the LLM prompt
    area_path="MyOrg\\Sprint",  # Azure only: area path for created items
    iteration_path="Sprint 5",  # Azure only: iteration path
    max_items_per_level=10,     # Hard cap per level
)
```

---

## How Decomposition Works

The LLM receives a structured prompt with:
- The problem statement
- Platform-specific level descriptions (e.g., "level 0 must be type 'Epic'" for Azure)
- The max items per level cap
- Your personalization style (if learning is enabled)

The LLM returns JSON:

```json
{
  "items": [
    {"level": 0, "type": "Epic", "title": "...", "description": "...", "labels": [], "parent_index": null},
    {"level": 1, "type": "User Story", "title": "...", "description": "...", "labels": ["story"], "parent_index": 0},
    {"level": 2, "type": "Task", "title": "...", "description": "...", "labels": ["task"], "parent_index": 1}
  ]
}
```

DevTrack parses this with two fallback strategies (direct JSON parse, then regex extraction) to handle LLMs that wrap JSON in prose.

---

## Failure Handling

- If a parent item fails to create (API error or no result), all its children are automatically skipped and reported in the `failed` list
- The `create_all` call always returns `(created, failed)` — partial success is fine
- Failed items show the error reason in progress updates and the final summary

---

## Troubleshooting

**LLM returns no response / invalid JSON:**
- Verify your LLM provider is running (`ollama serve` or check API key)
- Try a more capable model — decomposition requires structured JSON output
- Models known to work well: `llama3.2`, `mistral`, `gpt-4o-mini`, `claude-haiku`

**Items created but with wrong hierarchy:**
- The LLM sometimes ignores the parent_index constraints — this improves with better models
- Use `PM_AGENT_MAX_ITEMS_PER_LEVEL` to limit sprawl

**Azure items not getting parent links:**
- Confirm `AZURE_DEVOPS_PAT` has **Work Items (Read & Write)** scope
- Check that the work item type supports parent links in your process template (Agile/Scrum/CMMI)

**GitLab milestone not created:**
- Confirm `GITLAB_PROJECT_ID` is set and your PAT has `api` scope (not just `read_user`)

**GitHub rate limits:**
- GitHub allows 5000 API requests/hour with a PAT
- For large decompositions (many items), space out creation or use a token with higher limits
