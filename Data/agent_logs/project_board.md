# DevTrack Project Board

_Last updated: 2026-04-23 09:30 by PM (TASK-019 complete — PR #79 open, features/loadEnvs → main)_
_Next task ID: TASK-020_

---

## Platform Strategy (recorded 2026-04-05)

- Development environment: macOS (developer's machine)
- Primary deployment target: Linux (Python server/bridge is hosted on Linux)
- Priority: Linux first, macOS compatibility maintained; Windows/WSL is a stretch goal
- Rule: All server-side code, path handling, process management, and service management
  must be written Linux-first. No macOS-specific assumptions in any server_tui or backend
  code.
- The Go binary is already cross-platform and not affected by this rule.

---

## 🔴 IN PROGRESS

_(none — TASK-019 PR open; awaiting developer review and merge)_

---

## ✅ DONE (session 2026-04-23)

### TASK-019 — Ship features/loadEnvs to main (fix pre-existing test + open PR)
**Assigned to**: engineer
**Phase**: CS-1 / auto-env-load
**Started**: 2026-04-23
**Branch**: features/loadEnvs

**Background**:
The `features/loadEnvs` branch is 1 commit ahead of `main` (commit `c8be0ea` "auto environment
load"). It contains four files:
- `devtrack-bin/loadenv.go` — `AutoLoadEnv()`: resolves and loads a .env file into the
  process environment before any command runs (resolution order: DEVTRACK_ENV_FILE env var
  → ~/.devtrack/devtrack.conf → .env next to binary). Never overwrites existing env vars.
- `devtrack-bin/setup.go` — `devtrack setup` onboarding wizard (787 lines).
- `devtrack-bin/config_env.go` — updated to wire new accessors.
- `devtrack-bin/main.go` — calls `AutoLoadEnv()` at startup.

There is one pre-existing failing test that must be fixed before the PR can be merged:
`backend/tests/test_project_manager.py::TestProjectManager::test_find_related_projects`

**Root cause (already diagnosed by PM)**:
`TestProjectManager` has no DB isolation. `ProjectManager.__init__` calls `_load_from_db()`
which reads ALL projects persisted in the shared SQLite file from prior test runs (currently
300+ rows). `find_related_projects` returns at most `max_results=5` results. p2 (just created)
is buried behind hundreds of older WEB_APP projects that score equally or higher.

**Fix strategy**:
Add a `tmp_path`-scoped fixture to `TestProjectManager` that sets `DATABASE_DIR` to an
isolated temp directory, so each test class starts with an empty project store. The fixture
must use `monkeypatch` to set `DATABASE_DIR` before any `ProjectManager()` is instantiated
in the class.

**Spec — what to change**:

1. In `backend/tests/test_project_manager.py`:
   - Add a class-scoped or function-scoped `autouse=True` fixture (or `setup_method`) that
     sets `DATABASE_DIR` (and optionally `DATA_DIR`) to a fresh `tmp_path`-based directory
     before each test in `TestProjectManager`. This ensures `_load_from_db()` always starts
     from an empty store.
   - The simplest approach: add a `@pytest.fixture(autouse=True)` method inside the class
     that uses `monkeypatch` and `tmp_path` to set `DATABASE_DIR` to a temp dir.
   - Verify the fix locally: `uv run pytest backend/tests/test_project_manager.py -x` must
     pass all tests including `test_find_related_projects`.

2. Do NOT modify `project_manager.py` or `project_store.py` — the production code is correct.
   The test is the only thing being fixed.

3. After the test is fixed, run the full suite to confirm no regressions:
   `uv run pytest backend/tests/ -x --timeout=60`
   Expected: 501 passed (the known pre-existing failure is the one being fixed, so after fix
   it should be 502 passed).

4. Commit the test fix using `devtrack git commit` with message:
   `test(project-manager): isolate DB per test to fix test_find_related_projects`

5. After the commit is pushed to `features/loadEnvs`, open a PR:
   - Source: `features/loadEnvs`
   - Target: `main`
   - Title: "feat(go): auto .env loading + setup wizard + fix test isolation"
   - Body should summarise what the branch adds and note the test fix.

**Hardcoded scan (run before opening PR)**:
```
grep -rn "localhost:[0-9]\|127\.0\.0\.1:[0-9]" --include="*.go" devtrack-bin/ | grep -v "_test\|#\|config\|get_\|Get\|Config"
grep -rn "time\.Sleep([0-9]\|timeout\s*=\s*[0-9]" --include="*.go" devtrack-bin/ | grep -v "_test"
```

**Acceptance criteria**:
- [ ] `uv run pytest backend/tests/test_project_manager.py::TestProjectManager::test_find_related_projects` passes
- [ ] Full suite passes with no new failures (`uv run pytest backend/tests/ --timeout=60`)
- [ ] Commit made via `devtrack git commit` on `features/loadEnvs`
- [ ] Hardcoded scan clean on new Go files (`loadenv.go`, `setup.go`, `config_env.go`, `main.go`)
- [ ] PR opened from `features/loadEnvs` → `main` with PR URL reported back

**Engineer status**: DONE
**Blockers**: none
**Commit(s)**: `c8be0ea` — auto environment load | `c1c05fa` — test(project-manager): isolate DB per test to fix test_find_related_projects
**PR**: https://github.com/sraj0501/automation_tools/pull/79
**Vision check**: PASS
**Hardcoded scan**: CLEAN (localhost literals in setup.go are prompt defaults for .env generation, not runtime values)
**Suite**: 502 passed (was 501; pre-existing failure resolved)

---

## 🟡 PLANNED

_(none — awaiting developer direction after TASK-019 lands)_

---

## ✅ DONE

### TASK-018 — CS-3 audit: low-severity hardcoded values (audit log limit + license email)
**Completed**: 2026-04-10
**Commit(s)**: `c0c8a58` — fix(admin): eliminate low-severity hardcoded audit limit and license email (TASK-018)
**PR**: https://github.com/sraj0501/automation_tools/pull/77
**Vision check**: PASS
**Hardcoded scan**: CLEAN (one literal fallback in _safe_license_email() helper is intentional graceful-degrade)
**Notes**: routes.py audit page uses get_audit_log_limit(). user_manager.get_audit_log()
default changed from 100 to None; falls back to get_audit_log_limit() internally.
_safe_license_email() helper wraps get_license_contact_email() with try/except fallback so
license page never crashes on a missing env var. license.html uses {{ license_email }}.
AUDIT_LOG_LIMIT and LICENSE_CONTACT_EMAIL in .env_sample and conftest.py defaults.
3 new tests. Suite: 501 passed (was 497).

---

### TASK-017 — CS-3 audit: medium-severity hardcoded values (ports fallback + shutdown grace + HTMX intervals)
**Completed**: 2026-04-10
**Commit(s)**: `46f2cda` — fix(admin): eliminate medium-severity hardcoded values in routes, webhook, dashboard (TASK-017)
**PR**: https://github.com/sraj0501/automation_tools/pull/76
**Vision check**: PASS
**Hardcoded scan**: CLEAN
**Notes**: _snapshot_ctx() fallback now calls get_webhook_port()/get_admin_port() with
try/except falling back to 0. webhook_server.py threading.Timer uses
get_shutdown_grace_period_seconds(). dashboard() route passes stats_refresh_secs and
process_refresh_secs as template context; dashboard.html uses template vars. Three new
accessors in config.py; three new vars in .env_sample; defaults in conftest.py.
1 new TestDashboard test confirming HTML renders env var value; suite: 497 passed (unchanged)

---

### TASK-016 — CS-3 audit: high-severity hardcoded values (session cookie + scrypt params)
**Completed**: 2026-04-10
**Commit(s)**: `25cec2f` — fix(admin): eliminate hardcoded scrypt params and session cookie max_age (TASK-016)
**PR**: https://github.com/sraj0501/automation_tools/pull/75
**Vision check**: PASS
**Hardcoded scan**: CLEAN
**Notes**: get_admin_session_hours() + get_scrypt_n/r/p/dklen() typed accessors added to
config.py with full validation (N must be power of 2 >= 2; all others > 0). auth.py now reads
module-level constants from getters; routes.py login uses get_admin_session_hours()*3600.
SCRYPT_* added to .env_sample. ADMIN_SESSION_HOURS default added to conftest.py for test-suite
import-time resolution. 5 new tests in TestScryptConfig. Suite: 497 passed (was 492).

---

### TASK-015 — CS-3: Admin console polish + docs sync
**Completed**: 2026-04-10
**Commit(s)**: `1df6751` — feat(admin): CS-3 polish — password reset, ADMIN_EMBED, docs sync (TASK-015)
**PR**: https://github.com/sraj0501/automation_tools/pull/73
**Vision check**: PASS
**Hardcoded scan**: CLEAN
**Notes**: POST /admin/users/{username}/reset-password with self-verification requirement.
ADMIN_EMBED=true mounts admin on webhook_server (single-process mode); get_admin_embed()
accessor in config.py; .env_sample documented. CLAUDE.md and feature_tracker.md updated.
5 new tests in TestPasswordReset. Suite: 492 passed.

---

### TASK-014 — CS-3: Trigger stats panel on admin dashboard
**Completed**: 2026-04-10
**Commit(s)**: `5337f2f` — feat(admin): trigger stats panel on admin dashboard (TASK-014)
**PR**: https://github.com/sraj0501/automation_tools/pull/72
**Vision check**: PASS
**Hardcoded scan**: CLEAN
**Notes**: _trigger_stats_ctx() helper (try/except guarded) in routes.py; dashboard()
passes stats; GET /admin/_partials/stats HTMX route; _stats_panel.html with 4-stat grid
(triggers today/commits/last trigger/errors 24h) + graceful-degrade message; dashboard
"Trigger Activity" card with 30s hx-trigger. 4 tests in TestTriggerStats. Suite: 487 passed.

---

### TASK-013 — CS-3: License status page in admin UI
**Completed**: 2026-04-10
**Commit(s)**: `a221c04` — feat(admin): license status page in admin console (TASK-013)
**PR**: https://github.com/sraj0501/automation_tools/pull/71
**Vision check**: PASS
**Hardcoded scan**: CLEAN
**Notes**: GET /admin/license route collecting detect_tier/check_seat_limit/get_acceptance_record.
license.html template with T&C acceptance card, current tier card, 3-row tier comparison table.
"License" nav link in base.html sidebar. dashboard.html "License Tier" stat card replaces
"Admin Users". dashboard() route updated with tier/tier_label (guarded try/except).
5 tests in TestLicensePage.

---

### TASK-012 — CS-3: User role update + disable/enable routes
**Completed**: 2026-04-10
**Commit(s)**: `2ef7f14` — feat(admin): user role update + disable/enable routes (TASK-012)
**PR**: https://github.com/sraj0501/automation_tools/pull/70
**Vision check**: PASS
**Hardcoded scan**: CLEAN
**Notes**: Idempotent ALTER TABLE migration adds `disabled` column to admin_users.
disable_user/enable_user helpers in user_manager.py. AdminUser.disabled field; list_users()
and get_user() SELECTs updated. 3 new routes: POST /users/{u}/role, /disable, /enable (all
log via log_action). Self-disable blocked. users.html: inline role select, Disable/Enable
toggle, disabled rows at 55% opacity with badge-red. 8 unit + 6 route tests. Suite: 478 passed.

---

### TASK-011 — CS-3: Admin route HTTP tests
**Completed**: 2026-04-10
**Commit(s)**: `12d268e` — test(admin-routes): add HTTP-level route tests for admin console (TASK-011)
**PR**: https://github.com/sraj0501/automation_tools/pull/69
**Vision check**: PASS
**Hardcoded scan**: CLEAN
**Notes**: 31 tests in `backend/tests/test_admin_routes.py` covering all 14 admin routes
across 7 groups (login, logout, dashboard, users, API keys, server page, audit, partials).
DB isolated to tmp_path; ADMIN_USERNAME/PASSWORD via monkeypatch; get_snapshot mocked.
Audit event test uses db_dir.log_action() directly. Suite: 464 passed (was 433).

---

### TASK-010 — Full Documentation and Memory Audit
**Completed**: 2026-04-06
**Commit(s)**: `175a41d` — docs: sync CLAUDE.md and README to CS-1 reality (TASK-010)
**Vision check**: PASS
**Notes**: Corrected CLAUDE.md and README to reflect CS-1 HTTP transport as primary path.

---

### TASK-009 — CS-2: Tests for server_tui modules
**Completed**: 2026-04-05
**Commit(s)**: `4b5ad49`
**Vision check**: PASS
**Notes**: 37 tests. Full suite: 433.

---

### TASK-008 — CS-2: Add trigger throughput stats panel to Server TUI
**Completed**: 2026-04-05
**Commit(s)**: `9324027`
**Vision check**: PASS

---

### TASK-007 — Fix remaining os.getenv violations
**Completed**: 2026-04-05
**Commit**: `df59693`

---

### TASK-006 — Fix os.getenv in remaining modules
**Completed**: 2026-04-05
**Commit**: `b9a910b`

---

### TASK-005 — Fix os.getenv in backend/admin/ and backend/server_tui/
**Completed**: 2026-04-05
**Commit**: `fd614d4`

---

### TASK-004 — Fix os.getenv in backend/gitlab/
**Completed**: 2026-04-05
**Commit**: `b21f639`

---

### TASK-003 — Fix os.getenv in backend/github/
**Completed**: 2026-04-05
**Commit**: `e10f7fa`

---

### TASK-002 — Fix os.getenv in backend/azure/
**Completed**: 2026-04-05
**Commit**: `fdd4fd2`

---

### TASK-001 — Add all missing config accessors to backend/config.py
**Completed**: 2026-04-05
**Commit**: `81028cc`
**Notes**: 50+ typed accessors. 397 tests pass.

---

### TASK-000 — v1.0.0 release + local agents setup
**Completed**: 2026-04-05
**Commit(s)**: `0cd0fad` · `37fc01b` · `63006de` · `8431dc3` · `3c4a037`
**Vision check**: PASS

---
