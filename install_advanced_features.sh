#!/bin/bash

# Installation script for Phase 3-5 dependencies
# Installs all required packages for email reporting and task matching

set -e

echo "╔══════════════════════════════════════════════════════════╗"
echo "║   DevTrack Phase 3-5 - Dependency Installer             ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Check Python
echo "🔍 Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "   ✓ Found Python $PYTHON_VERSION"

# Check pip
echo ""
echo "🔍 Checking pip installation..."
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed. Please install pip."
    exit 1
fi
echo "   ✓ pip3 is available"

# Install fuzzywuzzy and python-Levenshtein
echo ""
echo "📦 Installing fuzzywuzzy for fuzzy string matching..."
pip3 install fuzzywuzzy python-Levenshtein || {
    echo "⚠️  Failed with pip3, trying with --user flag..."
    pip3 install --user fuzzywuzzy python-Levenshtein
}
echo "   ✓ fuzzywuzzy installed"

# Install sentence-transformers for semantic matching
echo ""
echo "📦 Installing sentence-transformers for semantic matching..."
echo "   (This may take a few minutes and download ~100MB)"
pip3 install sentence-transformers || {
    echo "⚠️  Failed with pip3, trying with --user flag..."
    pip3 install --user sentence-transformers
}
echo "   ✓ sentence-transformers installed"

# Install scikit-learn (required by sentence-transformers)
echo ""
echo "📦 Installing scikit-learn..."
pip3 install scikit-learn || {
    echo "⚠️  Failed with pip3, trying with --user flag..."
    pip3 install --user scikit-learn
}
echo "   ✓ scikit-learn installed"

# Test imports
echo ""
echo "🧪 Testing Python imports..."

python3 << 'EOF'
try:
    from fuzzywuzzy import fuzz
    print("   ✓ fuzzywuzzy works")
except ImportError as e:
    print(f"   ✗ fuzzywuzzy import failed: {e}")
    exit(1)

try:
    from sentence_transformers import SentenceTransformer
    print("   ✓ sentence-transformers works")
except ImportError as e:
    print(f"   ✗ sentence-transformers import failed: {e}")
    exit(1)

try:
    from sklearn.metrics.pairwise import cosine_similarity
    print("   ✓ scikit-learn works")
except ImportError as e:
    print(f"   ✗ scikit-learn import failed: {e}")
    exit(1)

print("\n   All imports successful!")
EOF

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Some imports failed. Please check the error messages above."
    exit 1
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║              INSTALLATION COMPLETE!                      ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "🎉 All dependencies installed successfully!"
echo ""
echo "New Features Available:"
echo "  ✅ Email Report Generation"
echo "     - devtrack preview-report"
echo "     - devtrack send-report <email>"
echo "     - devtrack save-report"
echo ""
echo "  ✅ Task Matching & Fuzzy Logic"
echo "     - Automatic matching of updates to existing tasks"
echo "     - Semantic similarity search"
echo "     - Confidence scoring"
echo ""
echo "Next steps:"
echo "  1. Build CLI: cd go-cli && go build -o devtrack"
echo "  2. Test report: ./devtrack preview-report"
echo "  3. Test matcher: python3 backend/task_matcher.py test"
echo ""
