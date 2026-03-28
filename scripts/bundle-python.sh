#!/usr/bin/env bash
# bundle-python.sh — copies the Python backend into devtrack-bin/assets/
# so that go:embed can include it in the compiled binary.
#
# Called by:
#   • make bundle        (local dev)
#   • .goreleaser.yaml before.hooks  (CI release builds)
#
# Usage: scripts/bundle-python.sh [project-root]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${1:-$(cd "$SCRIPT_DIR/.." && pwd)}"
ASSETS_DIR="$PROJECT_ROOT/devtrack-bin/assets"

echo "📦 Bundling Python backend from $PROJECT_ROOT → $ASSETS_DIR"

# Clean and recreate
rm -rf "$ASSETS_DIR"
mkdir -p "$ASSETS_DIR"

# Copy Python backend source
cp -r "$PROJECT_ROOT/backend"         "$ASSETS_DIR/backend"
cp    "$PROJECT_ROOT/python_bridge.py" "$ASSETS_DIR/python_bridge.py"
cp    "$PROJECT_ROOT/pyproject.toml"   "$ASSETS_DIR/pyproject.toml"

# Copy uv.lock if present (for reproducible installs)
if [ -f "$PROJECT_ROOT/uv.lock" ]; then
    cp "$PROJECT_ROOT/uv.lock" "$ASSETS_DIR/uv.lock"
fi

# Copy .env_sample so devtrack install can print next steps
if [ -f "$PROJECT_ROOT/.env_sample" ]; then
    cp "$PROJECT_ROOT/.env_sample" "$ASSETS_DIR/.env_sample"
fi

# Remove __pycache__, .pyc, test files — no need to ship these
find "$ASSETS_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$ASSETS_DIR" -name "*.pyc" -delete 2>/dev/null || true
find "$ASSETS_DIR" -name "*.pyo" -delete 2>/dev/null || true
find "$ASSETS_DIR" -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find "$ASSETS_DIR" -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true

SIZE=$(du -sh "$ASSETS_DIR" 2>/dev/null | cut -f1)
echo "✅ Bundle complete. Size: $SIZE"
echo "   Files: $(find "$ASSETS_DIR" -type f | wc -l | tr -d ' ')"
