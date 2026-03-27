#!/usr/bin/env bash
# =============================================================================
# DevTrack Demo Reset
# Tears down demo state so the demo can be run again from a clean slate.
#
# Usage:
#   cd /Users/sraj/git_apps/personal/automation_tools
#   bash demo/reset.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DEMO_PROJECT="$HOME/git_apps/personal/devtrack-demo"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RESET='\033[0m'; BOLD='\033[1m'
ok()   { echo -e "${GREEN}✓${RESET}  $*"; }
info() { echo -e "${YELLOW}▶${RESET}  $*"; }

# ── Load .env via Python dotenv ───────────────────────────────────────────────
if [[ -f "$ROOT_DIR/.env" ]]; then
  eval "$(cd "$ROOT_DIR" && uv run python3 -c "
import os; from dotenv import load_dotenv; load_dotenv('.env')
for k in ['GITHUB_TOKEN','GITHUB_OWNER']:
    v = os.getenv(k,'')
    if v:
        safe = v.replace(\"'\",\"'\\\\''\" )
        print(f\"export {k}='{safe}'\")
  ")"
fi

echo ""
echo -e "${BOLD}DevTrack Demo Reset${RESET}"
echo "─────────────────────────────────────────────"

# ── 1. Reset utils.py to 'before' state ──────────────────────────────────────
info "Resetting utils.py to stub state..."
if [[ -d "$DEMO_PROJECT" ]]; then
  cp "$SCRIPT_DIR/project/utils.py" "$DEMO_PROJECT/utils.py"
  cd "$DEMO_PROJECT"
  git checkout -- utils.py 2>/dev/null || true
  ok "utils.py reset"
else
  echo "   (demo project not found — skipping)"
fi

# ── 2. Clear MongoDB demo alerts ─────────────────────────────────────────────
info "Clearing demo alerts from MongoDB..."
cd "$ROOT_DIR"
uv run python3 - << 'PYEOF'
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

async def clear():
    try:
        from backend.db.mongo_alerts import get_store
        store = get_store()
        if not store.is_available():
            print("   MongoDB not available — skipping")
            return
        coll = store._collection
        if coll is None:
            print("   No collection — skipping")
            return
        result = await coll.delete_many({"source": {"$in": ["github", "azure"]}})
        print(f"   Deleted {result.deleted_count} notifications")
        # Also clear last_checked state
        state_coll = store._state_collection
        if state_coll is not None:
            await state_coll.delete_many({})
            print("   Cleared last_checked state")
    except Exception as e:
        print(f"   Error: {e}")

asyncio.run(clear())
PYEOF
ok "MongoDB cleared"

# ── 3. Re-inject fresh demo alerts ───────────────────────────────────────────
info "Re-injecting fresh demo alerts..."
uv run python demo/inject_alerts.py

# ── 4. Close any test PRs/issues created during demo (optional) ─────────────
# Only if GITHUB_TOKEN is available
if [[ -n "${GITHUB_TOKEN:-}" && -n "${GITHUB_OWNER:-}" ]]; then
  info "Checking for demo commits to revert in GitHub..."
  # Nothing to do — we don't revert the pushed commit, demo runs are additive
  ok "GitHub state preserved (commits stay, issues stay)"
fi

echo ""
echo -e "${BOLD}${GREEN}Reset complete — ready for another run.${RESET}"
echo ""
echo "  Run the demo:  bash demo/run_demo.sh"
echo ""
