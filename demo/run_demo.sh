#!/usr/bin/env bash
# =============================================================================
# DevTrack Demo — 15-minute walkthrough
#
# Usage:
#   cd /Users/sraj/git_apps/personal/automation_tools
#   bash demo/run_demo.sh
#
# Prerequisites:
#   bash demo/setup.sh   (run once before the demo)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DEMO_PROJECT="$HOME/git_apps/personal/devtrack-demo"
DEVTRACK="$ROOT_DIR/devtrack"

# ── Colors & helpers ──────────────────────────────────────────────────────────
RESET='\033[0m'; BOLD='\033[1m'; DIM='\033[2m'
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'
BLUE='\033[0;34m'; MAGENTA='\033[0;35m'; WHITE='\033[1;37m'

section() {
  echo ""
  echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
  echo -e "${BOLD}${BLUE}  $1${RESET}"
  echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
  echo ""
}

narrate() { echo -e "${CYAN}  ${DIM}$*${RESET}"; echo ""; }
cmd()     { echo -e "${GREEN}  \$${RESET} ${WHITE}$*${RESET}"; }
pause()   { echo ""; echo -e "${YELLOW}  ↵  Press Enter to continue...${RESET}"; read -r; }
run()     { cmd "$*"; eval "$*"; }

# ── Sanity checks ─────────────────────────────────────────────────────────────
if [[ ! -d "$DEMO_PROJECT/.git" ]]; then
  echo -e "${YELLOW}⚠  Demo project not found. Run: bash demo/setup.sh${RESET}"
  exit 1
fi

# ── Reset utils.py to 'before' state so commit demo is repeatable ─────────────
cp "$SCRIPT_DIR/project/utils.py" "$DEMO_PROJECT/utils.py"
cd "$DEMO_PROJECT" && git checkout -- utils.py 2>/dev/null || true

clear

# =============================================================================
# SECTION 1 — Introduction
# =============================================================================
section "1 / 6  —  DevTrack: your AI developer assistant"

narrate "DevTrack runs in the background and handles the overhead around your coding:"
narrate "  → Monitors every git commit and scheduled timers"
narrate "  → Prompts you for work updates, enriches them with AI"
narrate "  → Syncs to GitHub and Azure DevOps automatically"
narrate "  → Alerts you when something important happens in your tickets"

echo -e "${GREEN}  \$${RESET} ${WHITE}devtrack status${RESET}"
"$DEVTRACK" status

pause

# =============================================================================
# SECTION 2 — The Commit Flow
# =============================================================================
section "2 / 6  —  The Commit Flow"

narrate "We have a Task Manager API. The validate_task_input() function is a stub —"
narrate "let's implement it and commit the change."

echo ""
cmd "cd $DEMO_PROJECT"
cd "$DEMO_PROJECT"
echo ""

narrate "Current state of utils.py (the TODO stub):"
echo ""
grep -A6 "def validate_task_input" utils.py | head -10 | sed 's/^/    /'
echo ""

pause

narrate "Applying the implementation..."
cp "$SCRIPT_DIR/project/utils_after.py" utils.py
echo ""

narrate "What changed:"
git diff utils.py | grep '^[+-]' | grep -v '^---\|^+++' | head -20 | sed 's/^/    /'
echo ""

pause

narrate "Now watch DevTrack intercept the commit..."
echo ""
cmd "git add utils.py"
git add utils.py
echo ""
echo -e "${CYAN}  ─── DevTrack git commit flow ────────────────────────────────────${RESET}"
echo -e "${CYAN}  The AI enhancer will suggest an improved message."
echo -e "  Press  A  to accept  |  E  for a richer version  |  R  to retry${RESET}"
echo ""

pause

# Hand off to the user — they drive from here
echo -e "${GREEN}  \$${RESET} ${WHITE}git commit -m \"add input validation to task creation\"${RESET}"
echo ""
echo -e "${YELLOW}  >>> Running live — interact with the prompts below <<<${RESET}"
echo ""
git commit -m "add input validation to task creation"

echo ""
pause

# =============================================================================
# SECTION 3 — Ticket Alerter
# =============================================================================
section "3 / 6  —  Ticket Alerter (GitHub + Azure DevOps)"

cd "$ROOT_DIR"

narrate "DevTrack polls GitHub and Azure DevOps every 5 minutes."
narrate "It uses delta sync (last_checked timestamp per source) so you never"
narrate "see the same notification twice."
echo ""

run "$DEVTRACK alerts --all"

echo ""
pause

# =============================================================================
# SECTION 4 — git-sage
# =============================================================================
section "4 / 6  —  git-sage: your AI git assistant"

cd "$DEMO_PROJECT"

narrate "git-sage is DevTrack's agentic git tool."
narrate "Ask it anything about your repo — it reads the code, git log, and context."
echo ""

run "$DEVTRACK sage ask \"Look at this project. What's been implemented, what's still stubbed out, and what should I tackle next based on the open GitHub issues?\""

echo ""
pause

# =============================================================================
# SECTION 5 — Personalization
# =============================================================================
section "5 / 6  —  Personalization: 'Talk Like You'"

cd "$ROOT_DIR"

narrate "DevTrack learns your communication style from your Teams messages."
narrate "Every AI-generated message — commit text, work updates, reports — is"
narrate "rewritten to sound like you, not like a bot."
echo ""

run "$DEVTRACK show-profile"

echo ""
narrate "Let's see it generate a personalised standup update:"
echo ""
run "$DEVTRACK test-response \"summarize today's work on the task validation feature for standup\""

echo ""
pause

# =============================================================================
# SECTION 6 — Daily Report + Wiki
# =============================================================================
section "6 / 6  —  Daily Reports + Documentation"

narrate "DevTrack generates AI-enhanced daily and weekly reports,"
narrate "delivered to your terminal, email, or Teams."
echo ""

run "$DEVTRACK report --format terminal 2>/dev/null || echo '  (report generation requires LLM — see devtrack report --help)'"

echo ""
narrate "Everything is documented in the self-hosted wiki:"
echo ""
cmd "open $ROOT_DIR/wiki/wiki.html"
open "$ROOT_DIR/wiki/wiki.html" 2>/dev/null || echo "  Wiki is at: $ROOT_DIR/wiki/wiki.html"

echo ""

# =============================================================================
# Done
# =============================================================================
echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}${GREEN}  Demo complete — thanks!${RESET}"
echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
echo -e "  ${CYAN}Reset for another run:${RESET}  bash demo/reset.sh"
echo ""
