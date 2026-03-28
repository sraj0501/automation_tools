# DevTrack Advanced Features

## AI-Enhanced Daily Reports

**Basic reports** (via `devtrack preview-report`, `save-report`, `send-report`):
- Use `backend/email_reporter.py` – reads from SQLite `task_updates`, formats as text/HTML.

**AI-enhanced reports** (via Python bridge):
- Use `backend/daily_report_generator.py` – Ollama-powered insights (executive summary, accomplishments, recommendations, productivity score).
- Triggered when:
  - End-of-day window (default 6:00 PM ± 15 min) via timer trigger
  - `REPORT_TRIGGER` IPC message (e.g. from future CLI)

To run AI-enhanced report directly:
```bash
uv run python -c "
from backend.daily_report_generator import DailyReportGenerator
gen = DailyReportGenerator()
report = gen.generate_report(include_ai=True)
print(gen.format_report(report, 'terminal'))
"
```

## Analytics (devtrack stats / db-stats)

`devtrack stats` (alias for `db-stats`) shows:
- Total triggers, responses, task updates
- Triggers today and this week
- Top projects by update count (last 30 days)
- Unsynced updates, log entries

## Structured Observability (runtime-narrative)

DevTrack integrates the [`runtime-narrative`](https://pypi.org/project/runtime-narrative/) package for structured, story-scoped observability. When installed (included in `uv sync`), it wraps key pipeline steps in named stories and stages so that failures produce rich, structured diagnostics rather than raw tracebacks.

### Where it is used

| Component | Story name | What it wraps |
|-----------|-----------|---------------|
| FastAPI webhook server | `webhook.<source>` | Every inbound webhook request (Azure DevOps, GitHub, Jira, GitLab) |
| `python_bridge.py` handlers | `commit_trigger`, `timer_trigger` | Commit and timer event processing pipelines |

### Graceful degradation

Both integration points import `_story` and `_stage` context managers with a `try/except` fallback:

```python
try:
    from runtime_narrative import story as _story, stage as _stage
except ImportError:
    from contextlib import asynccontextmanager, contextmanager
    @asynccontextmanager
    async def _story(name, **kw): yield
    @contextmanager
    def _stage(name, **kw): yield
```

If `runtime-narrative` is not installed, all behaviour is identical — no errors, no missing logs, just no structured stories.

### Configuration

DevTrack uses `failure_diagnostics="lean"` throughout, which produces concise failure reports without including sensitive values (tokens, passwords, URLs with credentials) in the structured output.

### Installation

`runtime-narrative` is listed in `pyproject.toml` dependencies and installed automatically by `uv sync`. No additional steps are required.

---

## Future Work

- **Dashboard**: Web UI for analytics (planned)
- **Mobile notifications**: Push on triggers (planned)
- **Plugin system**: Extensible integrations (planned)
