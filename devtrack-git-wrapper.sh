#!/bin/bash
# DevTrack Git Wrapper
# Enhances git commands with AI-powered features while maintaining git compatibility

set -e

PROJECT_ROOT="${PROJECT_ROOT:-$HOME/Documents/GitHub/automation_tools}"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if this is a git command
if [ "$1" != "git" ]; then
    echo "Usage: devtrack git <command> [args...]"
    echo ""
    echo "Examples:"
    echo "  devtrack git add file.js"
    echo "  devtrack git commit    (AI-enhanced commit message)"
    echo "  devtrack git push"
    echo "  devtrack git status"
    exit 1
fi

shift  # Remove 'git' from args

GIT_COMMAND="$1"
shift  # Remove the git subcommand

# Handle git commit with AI enhancement
if [ "$GIT_COMMAND" = "commit" ]; then
    # Check if there are staged changes
    if git diff --cached --quiet 2>/dev/null; then
        echo "No changes staged for commit."
        echo "Use 'devtrack git add <files>' to stage changes first."
        exit 1
    fi
    
    REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
    
    echo -e "${BLUE}🤖 DevTrack AI-Enhanced Commit${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    # Parse commit args to extract user message if provided
    USER_MESSAGE=""
    COMMIT_ARGS=()
    SKIP_NEXT=false
    
    for arg in "$@"; do
        if [ "$SKIP_NEXT" = true ]; then
            USER_MESSAGE="$arg"
            SKIP_NEXT=false
        elif [ "$arg" = "-m" ] || [ "$arg" = "--message" ]; then
            SKIP_NEXT=true
        else
            COMMIT_ARGS+=("$arg")
        fi
    done
    
    # Show what's being committed
    echo -e "${YELLOW}Staged changes:${NC}"
    git diff --cached --stat | head -10
    echo ""
    
    # Create temp file for message
    TEMP_MSG=$(mktemp)
    if [ -n "$USER_MESSAGE" ]; then
        echo "$USER_MESSAGE" > "$TEMP_MSG"
        echo -e "${BLUE}📝 Your message: ${YELLOW}$USER_MESSAGE${NC}"
    else
        echo "auto-generated" > "$TEMP_MSG"
    fi
    echo -e "${BLUE}🔍 Analyzing code changes with AI...${NC}"
    echo ""
    
    # Run enhancer
    cd "$REPO_ROOT"
    export GIT_DIR="$REPO_ROOT/.git"
    
    if uv run --directory "$PROJECT_ROOT" python "$PROJECT_ROOT/backend/commit_message_enhancer.py" "$TEMP_MSG" auto 2>&1 | grep -q "enhanced"; then
        # Read enhanced message (remove comment lines)
        ENHANCED_MESSAGE=$(grep -v "^#" "$TEMP_MSG" | sed '/^$/d')
        
        echo -e "${GREEN}✓ AI-enhanced commit message:${NC}"
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo "$ENHANCED_MESSAGE" | sed 's/^/  /'
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        
        # Commit with enhanced message
        git commit -F "$TEMP_MSG" "${COMMIT_ARGS[@]}"
        echo ""
        echo -e "${GREEN}✓ Committed successfully with AI-enhanced message!${NC}"
    else
        echo -e "${YELLOW}⚠️  AI enhancement failed, using original message${NC}"
        if [ -n "$USER_MESSAGE" ]; then
            git commit -m "$USER_MESSAGE" "${COMMIT_ARGS[@]}"
        else
            git commit "${COMMIT_ARGS[@]}"
        fi
    fi
    
    rm -f "$TEMP_MSG"

# Handle all other git commands - pass through to git
else
    exec git "$GIT_COMMAND" "$@"
fi
