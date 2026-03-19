# DevTrack Project Memory

**Last Updated**: March 13, 2026
**Project Status**: Production-Ready (Phases 1-4 + Personalization + git-sage Session UX + RAG)
**Current Branch**: sage-improvements (uncommitted changes: RAG personalization system)

## Project Overview

**DevTrack** - "OpenClaw-style Swiss Army knife for developers"
- Offline-first automation tool for developer workflows
- Monitors Git activity and scheduled timers
- Prompts for work updates, enriches with AI, routes to project management systems
- Focus: Workflows BEFORE and AFTER coding (not code generation)

## Architecture at a Glance

**Two-Layer System**:
- **Go Layer** (devtrack-bin/): Git monitoring, scheduling, IPC server, database
- **Python Layer** (backend/): NLP parsing, LLM enhancement, TUI prompts, integrations

Communication: TCP IPC (default 127.0.0.1:35893) with JSON-newline-delimited messages

**Binary**: Built with `cd devtrack-bin && go build -o devtrack . && cp devtrack ..`
The `devtrack` alias points to `/Users/sraj/git_apps/personal/automation_tools/devtrack`

## Project Phases Status

### ✅ **Phase 1-3: Git Workflow (COMPLETE)**
- Enhanced commit messages, conflict resolution, PR-aware parsing, event-driven integration

### ✅ **Phase 4: Project Management (COMPLETE)**
- ProjectManager, project data model, SQLAlchemy models, 40+ tests

### ✅ **Personalization: "Talk Like You" (COMPLETE & WORKING)**
- Teams chats collected → MongoDB `communication_samples`
- User profile built from communication style
- Daily cron delta sync (20:00) via `run_daily_learning.py`
- CLI: `enable-learning`, `show-profile`, `test-response`, `revoke-consent`, `learning-status`, `learning-sync [--full]`, `learning-setup-cron`, `learning-remove-cron`, `learning-cron-status`, `learning-reset`

### ✅ **RAG Personalization (COMPLETE — March 13, 2026)**

Two-signal personalization injected into EVERY LLM prompt in the system:

**Signal 1: Profile-based style instruction** (`PersonalizedAI.get_style_instruction()`)
- Fast, always available once a profile exists
- Constraints: formality, length, emoji preference, common phrases
- Output: `[STYLE: clear and direct, concise but complete, no emojis. ...]`

**Signal 2: RAG few-shot examples** (`backend/rag/`)
- ChromaDB vector store + `nomic-embed-text` via Ollama
- Retrieves semantically similar past responses the user wrote
- Shows actual examples of how the user writes in situations like the current one
- Output: `Here are real examples of how this user has written...`

**Global entry point**: `backend/personalization.py:inject_style(prompt, context_type, query_text)`

**RAG modules** (`backend/rag/`):
- `embedder.py` — Ollama `/api/embed`, returns None if model unavailable
- `vector_store.py` — ChromaDB PersistentClient, cosine similarity, context_type filter
- `sample_indexer.py` — `index_sample()`, `index_samples()`, `retrieve_examples()`

**Injection points** (all 6 output generators wired):
- commit_message_enhancer.py (context_type=commit, query=original message)
- description_enhancer.py (context_type=description, query=raw_input)
- git_sage/agent.py (appended to system prompt)
- daily_report_generator.py (daily + weekly)
- ai/create_tasks.py
- project_manager.py (_enhance_project_with_ai + _get_ai_suggestions)

**Auto-indexing**: New samples indexed immediately in `add_communication_sample()`. Profile load triggers incremental index. Revoke consent wipes ChromaDB.

**Setup**: `ollama pull nomic-embed-text` (one-time). ChromaDB installed via `uv sync`.

**Config vars** (all optional with defaults):
- `PERSONALIZATION_RAG_ENABLED=true`
- `PERSONALIZATION_EMBED_MODEL=nomic-embed-text`
- `PERSONALIZATION_RAG_K=3`
- `PERSONALIZATION_CHROMA_DIR=${DATA_DIR}/learning/chroma`

### ✅ **git-sage Session UX (COMPLETE — branch: sage-improvements)**

Key commits on `sage-improvements`:
- `bc19020` feat: session approval mode + step history + undo
- `505811e` fix: replace rebase with reset --soft for squash
- `7b07343` fix: enforce JSON mode + show raw LLM output on parse errors
- `2ae4af0` fix: strip groq/ prefix + harden JSON-only enforcement
- `9e13aa2` fix: surface full answer for informational tasks in done.summary
- `0373de3` feat: follow-up loop in do mode (5 questions, same context)

### 📋 **Planned: Multi-repo + launchd auto-start**
- launchd plist for macOS auto-start on login
- Multi-repo monitoring with per-repo project management config (workspaces.yaml)

### 📋 **Planned: Ticket Alerter**
- Poll Jira, Azure DevOps, GitHub for ticket events
- OS notification + MongoDB persistence
- See CLAUDE.md "Ticket Alerter" section for full design

## git-sage Session UX (current implementation)

### Session Approval Mode
At the start of every `devtrack sage do <task>` or entering interactive mode:
```
Session approval mode:
  [a]  Accept all    — run every command without asking
  [r]  Review each   — confirm every command before it runs
  [s]  Suggest only  — show commands, never execute them
```
- Mode persists for the session; `--yes` / `-y` flag skips dialog (auto)
- Interactive mode: approval asked once and applied to all `do` calls in that session

### Follow-up Loop (do mode)
- After each task completes, user can ask up to **5 follow-up questions**
- Same agent instance → same conversation history → full context retained
- Empty Enter exits; `history` / `undo [N]` work inline during follow-up
- Undo prompt shown once after all follow-ups finish

### Command History & Undo
- `GitAgent` captures `git HEAD` before every `run` action in `state.step_log`
- `get_step_history()` / `undo_step(idx)` → `git reset --hard <pre-step-HEAD>`
- `offer_undo()` prints numbered table, prompts for step to undo
- Interactive mode: `history` and `undo [N]` commands available
- Limitation: only git state undone; `write_file` edits are NOT reverted

### Squash Fix
- System prompt explicitly bans `git rebase -i` for squashing
- Agent always uses 3-step flow: `git --no-pager log -N`, `git reset --soft HEAD~N`, `git commit -m "..."`

### JSON Mode Enforcement
- `raw_chat(..., json_mode=True)` on every agent call
- Ollama: `"format": "json"` in payload
- OpenAI/Groq: `response_format={"type": "json_object"}` with `BadRequestError` fallback
- Model names strip `provider/` prefix (`groq/compound` → `compound-beta`) before API call

### Groq Support
- `GIT_SAGE_PROVIDER=groq` + `GROQ_API_KEY` in `.env`
- Uses openai SDK (not urllib) — avoids Cloudflare 403 block on `Python-urllib` UA
- Recommended model: `llama-3.3-70b-versatile` (better JSON compliance than `compound-beta`)

## Env-Driven Provider Config for git-sage

| `.env` variable | Purpose |
|---|---|
| `GIT_SAGE_PROVIDER` | Provider override (defaults to `LLM_PROVIDER`) |
| `GIT_SAGE_DEFAULT_MODEL` | Model for ollama/lmstudio |
| `GIT_SAGE_API_KEY` | API key override (falls back to provider-specific key) |
| `GIT_SAGE_BASE_URL` | Base URL override |
| `GROQ_API_KEY` | Groq API key |
| `GROQ_HOST` | Groq endpoint (default: https://api.groq.com/openai/v1) |
| `GROQ_MODEL` | Groq model name (native, no `groq/` prefix needed) |

## Key Files & Locations

```
backend/
  ├── personalization.py       - Global inject_style() — combines profile + RAG
  ├── personalized_ai.py       - Talk Like You AI engine + get_style_instruction()
  ├── learning_integration.py  - Teams collection, GraphClientAdapter, AsyncTeamsDataCollector
  ├── run_daily_learning.py    - Cron script for daily delta sync
  ├── rag/
  │   ├── __init__.py          - Package entry: get_indexer()
  │   ├── embedder.py          - Ollama /api/embed calls
  │   ├── vector_store.py      - ChromaDB PersistentClient wrapper
  │   └── sample_indexer.py    - index_sample/index_samples/retrieve_examples
  └── llm/
      ├── provider_factory.py  - Multi-provider fallback chain (includes Groq)
      └── groq_provider.py     - Groq via openai SDK

backend/git_sage/
  ├── cli.py       - Session approval, follow-up loop, history/undo, do_mode, interactive_mode
  ├── agent.py     - _run_loop(), run(), followup(), suggest_only, step_log, undo_step()
  ├── llm.py       - json_mode param, provider prefix stripping, BadRequestError fallback
  ├── config.py    - Env-driven: .env > ~/.config/git-sage/config.json > defaults
  └── __main__.py  - Entry point for `python -m backend.git_sage`

devtrack-bin/
  ├── main.go        - CLI entry; `sage` command delegates to runGitSage()
  ├── cli.go         - All CLI commands including 10 learning commands
  └── learning.go    - LearningCommands: SetupCron, RemoveCron, SyncNow, ResetLearning
```

## Configuration Architecture

**Single Source of Truth**: `.env` with NO hardcoded defaults
- Go: `config_env.go` | Python: `backend/config.py`
- 12 required vars (timeouts, hosts, models) — missing any → startup error with clear message

## Next Steps for Future Sessions

1. **Commit RAG work** — uncommitted changes on sage-improvements branch
2. **Push sage-improvements** — not yet pushed to origin
3. **launchd plist** — auto-start devtrack on macOS login
4. **Ticket Alerter** — poll Jira/Azure/GitHub, OS + terminal notifications, MongoDB persistence
5. **Multi-repo monitoring** — per-repo config via workspaces.yaml
6. **Phase 4B** — database integration for project management

## User Preferences & Notes

- Vision: "OpenClaw for developers" — comprehensive, offline-first, optional cloud
- Code style: follows existing patterns (check CLAUDE.md)
- No hardcoded values — all config via `.env`
- Testing required before commits
