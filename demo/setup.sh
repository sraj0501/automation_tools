#!/usr/bin/env bash
# =============================================================================
# DevTrack Demo Setup
# Creates the demo GitHub repo, seeds issues, initialises the local project,
# adds the demo workspace, and pre-populates MongoDB with demo alerts.
#
# Run once before the demo:
#   cd /Users/sraj/git_apps/personal/automation_tools
#   bash demo/setup.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DEMO_PROJECT="$HOME/git_apps/personal/devtrack-demo"

# ── Colors ────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; RESET='\033[0m'; BOLD='\033[1m'
ok()   { echo -e "${GREEN}✓${RESET}  $*"; }
info() { echo -e "${YELLOW}▶${RESET}  $*"; }
fail() { echo -e "${RED}✗${RESET}  $*"; exit 1; }

# ── Load .env via Python dotenv (handles quotes, special chars correctly) ─────
if [[ ! -f "$ROOT_DIR/.env" ]]; then
  fail ".env not found in $ROOT_DIR"
fi

eval "$(cd "$ROOT_DIR" && uv run python3 -c "
import os; from dotenv import load_dotenv; load_dotenv('.env')
for k in ['GITHUB_TOKEN','GITHUB_OWNER','AZURE_ORGANIZATION','AZURE_PROJECT','EMAIL']:
    v = os.getenv(k,'')
    if v:
        safe = v.replace(\"'\",\"'\\\\''\" )
        print(f\"export {k}='{safe}'\")
")"

GITHUB_TOKEN="${GITHUB_TOKEN:-}"
GITHUB_OWNER="${GITHUB_OWNER:-}"
DEMO_REPO="devtrack-demo"

[[ -z "$GITHUB_TOKEN" ]] && fail "GITHUB_TOKEN not set in .env"
[[ -z "$GITHUB_OWNER" ]] && fail "GITHUB_OWNER not set in .env"

echo ""
echo -e "${BOLD}DevTrack Demo Setup${RESET}"
echo "─────────────────────────────────────────────"

# ── 1. Create GitHub repo ─────────────────────────────────────────────────────
info "Creating GitHub repo ${GITHUB_OWNER}/${DEMO_REPO}..."

REPO_CHECK=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/repos/${GITHUB_OWNER}/${DEMO_REPO}")

if [[ "$REPO_CHECK" == "200" ]]; then
  ok "Repo already exists — skipping creation"
else
  CREATE_RESP=$(curl -s -X POST \
    -H "Authorization: Bearer $GITHUB_TOKEN" \
    -H "Content-Type: application/json" \
    https://api.github.com/user/repos \
    -d "{
      \"name\": \"${DEMO_REPO}\",
      \"description\": \"DevTrack demo project — Task Manager API\",
      \"private\": false,
      \"auto_init\": false
    }")
  REPO_URL=$(echo "$CREATE_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('html_url',''))")
  [[ -z "$REPO_URL" ]] && fail "Failed to create repo. Response: $CREATE_RESP"
  ok "Created repo: $REPO_URL"
fi

# ── 2. Initialise local demo project ─────────────────────────────────────────
info "Setting up local project at $DEMO_PROJECT..."

if [[ -d "$DEMO_PROJECT/.git" ]]; then
  ok "Local repo already exists — skipping init"
else
  mkdir -p "$DEMO_PROJECT"
  cp -r "$SCRIPT_DIR/project/." "$DEMO_PROJECT/"

  cd "$DEMO_PROJECT"
  git init -b main
  git add .
  git commit -m "Initial commit: Task Manager API skeleton"
  git remote add origin "https://${GITHUB_TOKEN}@github.com/${GITHUB_OWNER}/${DEMO_REPO}.git"
  git push -u origin main
  ok "Pushed initial commit to GitHub"
fi

# ── 3. Seed GitHub issues ─────────────────────────────────────────────────────
info "Seeding GitHub issues..."

seed_issue() {
  local title="$1" body="$2" labels="$3"
  # Check if issue with same title already exists
  EXISTS=$(curl -s \
    -H "Authorization: Bearer $GITHUB_TOKEN" \
    "https://api.github.com/repos/${GITHUB_OWNER}/${DEMO_REPO}/issues?state=open&per_page=20" \
    | python3 -c "
import sys, json
issues = json.load(sys.stdin)
title = '''${title}'''
print('yes' if any(i['title'] == title for i in issues) else 'no')
" 2>/dev/null)

  if [[ "$EXISTS" == "yes" ]]; then
    echo "   (skipped: '$title' already exists)"
    return
  fi

  PAYLOAD=$(python3 -c "
import json
print(json.dumps({'title': '''${title}''', 'body': '''${body}''', 'labels': ${labels}}))
")
  RESULT=$(curl -s -X POST \
    -H "Authorization: Bearer $GITHUB_TOKEN" \
    -H "Content-Type: application/json" \
    "https://api.github.com/repos/${GITHUB_OWNER}/${DEMO_REPO}/issues" \
    -d "$PAYLOAD")
  NUM=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('number','?'))")
  echo "   #${NUM}: ${title}"
}

seed_issue \
  "Add user authentication to the API" \
  "Implement JWT-based authentication.\n\n- [ ] Token generation on login\n- [ ] Middleware for protected routes\n- [ ] Refresh token support" \
  '["feature","priority:high"]'

seed_issue \
  "Add input validation to task creation endpoint" \
  "Currently the API accepts any input without validation, leading to corrupt data.\n\n- [ ] Validate title (non-empty, max 200 chars)\n- [ ] Validate priority (low/medium/high)\n- [ ] Validate due_date format and range" \
  '["bug","priority:high"]'

seed_issue \
  "Improve API error handling and response format" \
  "Standardise error responses across all endpoints.\n\nCurrently errors return inconsistent shapes. Define a standard error envelope." \
  '["enhancement"]'

seed_issue \
  "Add pagination to task list endpoint" \
  "GET /tasks can return unbounded results. Add page/limit query params with sensible defaults." \
  '["enhancement","good first issue"]'

seed_issue \
  "Write integration tests for create and delete flows" \
  "Unit tests cover validation but we need integration tests that exercise the full create → read → delete lifecycle." \
  '["testing"]'

seed_issue \
  "Add task tagging and filtering by tag" \
  "Users want to tag tasks (e.g. work, personal, urgent) and filter by tag. Requires model changes and new query params." \
  '["feature"]'

ok "Issues seeded"

# ── 4. Add demo workspace to workspaces.yaml ──────────────────────────────────
info "Registering demo workspace..."

if grep -q "devtrack-demo" "$ROOT_DIR/workspaces.yaml"; then
  ok "Demo workspace already registered"
else
  cat >> "$ROOT_DIR/workspaces.yaml" << EOF

  # Demo project (created by demo/setup.sh)
  - name: "devtrack-demo"
    path: "${DEMO_PROJECT}"
    pm_platform: "github"
    pm_project: "projects/1"
    enabled: true
    ignore_branches: []
    tags: ["demo"]
EOF
  ok "Added devtrack-demo workspace"
fi

# Enable git integration for the demo workspace
cd "$DEMO_PROJECT"
git config devtrack.enabled true
ok "Enabled devtrack git integration for demo repo"

# ── 5. Inject demo alerts into MongoDB ────────────────────────────────────────
info "Injecting demo alerts into MongoDB..."
cd "$ROOT_DIR"
uv run python demo/inject_alerts.py

# ── 6. Reset utils.py to the 'before' state ───────────────────────────────────
info "Ensuring utils.py is in 'before' state for the commit demo..."
cd "$DEMO_PROJECT"
cp "$SCRIPT_DIR/project/utils.py" utils.py
git checkout -- utils.py 2>/dev/null || true
ok "utils.py reset to skeleton state"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}Setup complete!${RESET}"
echo ""
echo "  Demo project:  $DEMO_PROJECT"
echo "  GitHub repo:   https://github.com/${GITHUB_OWNER}/${DEMO_REPO}"
echo ""
echo "  Run the demo:  bash demo/run_demo.sh"
echo "  Reset after:   bash demo/reset.sh"
echo ""
