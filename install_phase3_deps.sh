#!/bin/bash

# Phase 3 Dependency Installation Script
# Installs NLP and AI dependencies for DevTrack

echo "🚀 Installing Phase 3 Dependencies for DevTrack"
echo "================================================"
echo ""

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"
echo ""

# Install spaCy
echo "📦 Installing spaCy..."
pip install spacy

# Download spaCy language model
echo "📥 Downloading spaCy English model (en_core_web_sm)..."
python3 -m spacy download en_core_web_sm

# Install sentence-transformers for semantic matching
echo "📦 Installing sentence-transformers..."
pip install sentence-transformers

# Install fuzzywuzzy for fuzzy string matching
echo "📦 Installing fuzzywuzzy and python-Levenshtein..."
pip install fuzzywuzzy python-Levenshtein

# Install dateparser for natural language date parsing
echo "📦 Installing dateparser..."
pip install dateparser

# Verify Ollama installation
echo ""
echo "🤖 Checking Ollama installation..."
if command -v ollama &> /dev/null; then
    echo "✓ Ollama is installed"
    ollama list
    echo ""
    echo "If you don't see a model, install one with:"
    echo "  ollama pull llama3.1"
else
    echo "❌ Ollama is NOT installed"
    echo ""
    echo "Install Ollama from: https://ollama.ai"
    echo "Then pull a model: ollama pull llama3.1"
fi

echo ""
echo "✅ Phase 3 dependencies installation complete!"
echo ""
echo "Next steps:"
echo "1. Ensure Ollama is running: ollama serve"
echo "2. Test NLP parser: python3 backend/nlp_parser.py"
echo "3. Start the Python bridge: python3 python_bridge.py"
