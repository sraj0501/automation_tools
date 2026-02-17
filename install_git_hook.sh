#!/bin/bash
# Install prepare-commit-msg hook for AI-enhanced commit messages

set -e

REPO_PATH="${1:-$(pwd)}"
HOOK_DIR="$REPO_PATH/.git/hooks"
HOOK_FILE="$HOOK_DIR/commit-msg"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENHANCER_SCRIPT="$SCRIPT_DIR/backend/commit_message_enhancer.py"

echo "🔧 Installing DevTrack AI Commit Enhancer..."
echo "   Repository: $REPO_PATH"

# Check if this is a git repository
if [ ! -d "$REPO_PATH/.git" ]; then
    echo "❌ Error: Not a git repository: $REPO_PATH"
    exit 1
fi

# Check if enhancer script exists
if [ ! -f "$ENHANCER_SCRIPT" ]; then
    echo "❌ Error: Enhancer script not found: $ENHANCER_SCRIPT"
    exit 1
fi

# Create hooks directory if it doesn't exist
mkdir -p "$HOOK_DIR"

# Create the hook (using commit-msg hook - runs after message is set, can modify it)
cat > "$HOOK_FILE" << 'HOOK_EOF'
#!/bin/bash
# DevTrack AI Commit Message Enhancer
# This hook enhances commit messages using AI analysis of staged changes

# Find the project root (where .env file is)
PROJECT_ROOT="${PROJECT_ROOT:-$HOME/Documents/GitHub/automation_tools}"

# Run the enhancer
if [ -f "$PROJECT_ROOT/backend/commit_message_enhancer.py" ]; then
    # Set GIT_DIR so the script knows where the repo is  
    REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
    export GIT_DIR="$REPO_ROOT/.git"
    cd "$REPO_ROOT" || exit 0
    uv run --directory "$PROJECT_ROOT" python "$PROJECT_ROOT/backend/commit_message_enhancer.py" "$1" commit-msg 2>&1 >> "$REPO_ROOT/.git/devtrack-enhancer.log"
fi

exit 0
HOOK_EOF

# Make hook executable
chmod +x "$HOOK_FILE"

echo "✓ Hook installed: $HOOK_FILE"
echo ""
echo "🎯 How it works:"
echo "   1. Stage your changes: git add <files>"
echo "   2. Commit with ANY message: git commit -m 'temp' or 'update'"
echo "   3. AI analyzes the diff and REPLACES your message with an enhanced one"
echo "   4. Enhanced message is committed to git history"
echo ""
echo "💡 Tip: Use generic messages and let AI write the real commit message!"
echo "   Examples: git commit -m 'wip', git commit -m 'fix', git commit -m '.'"
echo ""
