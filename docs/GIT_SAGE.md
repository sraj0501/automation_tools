# git-sage — Local LLM Git Agent

`git-sage` is a local LLM-powered git agent built into DevTrack. It doesn't just suggest commands — it **plans, executes, verifies, and recovers from failure** autonomously.

---

## Modes

| Mode | Command | What it does |
|------|---------|-------------|
| **ask** | `git-sage ask "..."` | Explains the situation and suggests commands; you decide whether to run them |
| **do** | `git-sage do "..."` | Agent plans and executes step-by-step, detects failures, resolves conflicts, rolls back if needed |
| **interactive** | `git-sage interactive` | Persistent session — mix `ask` and `do` with shared context |

---

## Running git-sage

git-sage ships as a Python module inside DevTrack:

```bash
# Ask mode — get explanation and suggestions
uv run python -m backend.git_sage ask "how do I undo my last commit but keep the changes staged?"

# Do mode — agent executes the task
uv run python -m backend.git_sage do "squash my last 3 commits into one with a clean message"
uv run python -m backend.git_sage do "merge feature-auth into main and resolve any conflicts"
uv run python -m backend.git_sage do "delete all local branches that have been merged into main"

# Interactive session
uv run python -m backend.git_sage interactive
# sage> ask how does cherry-pick work
# sage> do rebase my branch onto main
# sage> undo       (undo the last step)
# sage> quit
```

---

## Session Approval Modes (`do` mode)

When you run `git-sage do`, it first shows an approval dialog before executing anything:

| Mode | Behaviour |
|------|-----------|
| **auto** | Executes all planned steps without pausing |
| **review** | Pauses before each step — you approve or skip |
| **suggest-only** | Shows the plan but never executes — you copy-paste commands manually |

Select your preference in the dialog. The choice is remembered for the session.

---

## What the Agent Can Do

- **Run** git and shell commands and read their output
- **Read files** to inspect conflict markers, configs, etc.
- **Write files** to resolve conflicts intelligently
- **Checkpoint** before any destructive operation (saves HEAD + stashes dirty state)
- **Rollback** to a checkpoint if something goes wrong
- **Ask you** when intent is genuinely ambiguous
- **Abort cleanly** when a conflict needs human judgment

### Example Session

```
🌿 git-sage agent
  Task: merge feature-auth into main and resolve any conflicts

  📌 CHECKPOINT [before-merge]   ← saves HEAD before risky operation

  ⚡ RUN  git checkout main
  ⚡ RUN  git merge feature-auth --no-ff
     Conflict in src/auth/middleware.py

  📄 READ_FILE  src/auth/middleware.py   ← reads conflict markers

  ✏️  WRITE_FILE  src/auth/middleware.py  ← resolves: keeps token validation + error handling

  ⚡ RUN  git add src/auth/middleware.py
  ⚡ RUN  git commit -m "Merge feature-auth: add token validation"

  ✅ Done: Merged feature-auth. Resolved 1 conflict by combining both sides.
```

---

## Follow-up Questions

After a `do` task completes, git-sage offers up to 5 follow-up questions in the **same conversation context**:

```
Task complete. Follow-up? (or Enter to exit)
> did the merge include all commits from feature-auth?
```

The agent already has full context of what it just did, so follow-up answers are precise.

---

## Undo

Every destructive step records a HEAD snapshot. You can undo:

```bash
# In interactive mode:
sage> undo        # undo the last step
sage> undo 3      # undo the last 3 steps
```

Or at any `do` session prompt.

---

## Configuration

git-sage reads config from `.env` (same file as DevTrack):

| Variable | Default | Description |
|---|---|---|
| `GIT_SAGE_PROVIDER` | `ollama` | LLM provider: `ollama`, `openai`, `groq`, `lmstudio` |
| `GIT_SAGE_DEFAULT_MODEL` | (required) | Model name, e.g. `llama3.2`, `gpt-4o-mini` |
| `GIT_SAGE_BASE_URL` | — | Override base URL for the provider |
| `GIT_SAGE_API_KEY` | — | Override API key for the provider |

### Provider Examples

```env
# Ollama (local, free)
GIT_SAGE_PROVIDER=ollama
GIT_SAGE_DEFAULT_MODEL=llama3.2

# OpenAI
GIT_SAGE_PROVIDER=openai
GIT_SAGE_DEFAULT_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...

# Groq (fast cloud inference, free tier)
GIT_SAGE_PROVIDER=groq
GIT_SAGE_DEFAULT_MODEL=llama-3.3-70b-versatile
GROQ_API_KEY=gsk_...

# LM Studio (local OpenAI-compatible)
GIT_SAGE_PROVIDER=lmstudio
GIT_SAGE_DEFAULT_MODEL=your-model-name
GIT_SAGE_BASE_URL=http://localhost:1234/v1
```

### Model Recommendations

| Task | Minimum | Better |
|------|---------|--------|
| `ask` / suggestions | 3B (llama3.2:3b) | 8B (llama3.1:8b) |
| Conflict resolution | 8B (mistral, llama3) | 13B+ |
| Complex rebases / squash | 13B+ | GPT-4o-mini or higher |

---

## Advanced Features

### Intelligent Conflict Resolution

git-sage reads conflict markers and understands **both sides**:

- **Auto-resolves** when safe: addition-only changes, adjacent (non-overlapping) changes, identical changes
- **Merges intelligently** for changes that can be combined
- **Reports unresolvable** conflicts with context and leaves them for you to handle

### Squash Flow

git-sage uses `git reset --soft HEAD~N && git commit -m "..."` — never `git rebase -i` (interactive rebase blocks the agent loop).

### PR Utilities

- Extract metadata from branch names (`feature/PROJ-123-fix-login`)
- Suggest PR titles and descriptions
- Analyze diff statistics (files changed, additions, deletions)
- Find related commits and issues

---

## Capabilities Summary

| Capability | Module |
|---|---|
| Agentic loop (plan → execute → verify → recover) | `agent.py` |
| LLM backends (Ollama, OpenAI-compatible, Groq) | `llm.py` |
| Git context collection | `context.py` |
| Branch, commit, stash, merge operations | `git_operations.py` |
| Conflict analysis and resolution | `conflict_resolver.py` |
| PR/MR metadata extraction | `pr_finder.py` |
| CLI (ask/do/interactive) + session dialog | `cli.py` |

---

## Troubleshooting

**Agent does nothing then says Done:**
- The LLM returned prose instead of JSON. Check the `[parse error]` log line.
- Groq's `compound-beta` model is unreliable for JSON — use `llama-3.3-70b-versatile` instead.

**Agent loops without finishing:**
- Interrupt with Ctrl+C and check `git status`.
- Set a lower `max_steps` or switch to a smarter model.
- Use `--verbose` to see each LLM response.

**Groq 403 Cloudflare block:**
- Ensure the `openai` Python package is installed: `uv add openai`. The `openai` SDK sets a proper User-Agent (unlike `urllib` which gets blocked).

**Conflicts not auto-resolved:**
- Some conflicts genuinely require human judgment — the agent reports these clearly.
- Try running with a larger model (13B+) for better conflict understanding.

**JSON mode errors / BadRequestError:**
- Some models don't support `response_format: json_object`. git-sage falls back to text-only mode with text-level JSON instructions.
- If this causes persistent failures, switch to a model with native JSON mode support (most llama3/mistral variants do).
