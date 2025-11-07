#!/bin/bash

# Installation script for Personalized AI Learning dependencies

set -e

echo "╔══════════════════════════════════════════════════════════╗"
echo "║   DevTrack Personalized AI - Dependency Installer       ║"
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

# Install ollama Python package
echo ""
echo "📦 Installing ollama Python package..."
pip3 install ollama || {
    echo "⚠️  Failed to install ollama. Trying with --user flag..."
    pip3 install --user ollama
}
echo "   ✓ ollama installed"

# Install spacy
echo ""
echo "📦 Installing spacy..."
pip3 install spacy || {
    echo "⚠️  Failed to install spacy. Trying with --user flag..."
    pip3 install --user spacy
}
echo "   ✓ spacy installed"

# Download spacy model
echo ""
echo "📦 Downloading spacy English model..."
python3 -m spacy download en_core_web_sm || {
    echo "⚠️  Failed to download spacy model. You may need to run:"
    echo "   python3 -m spacy download en_core_web_sm"
}
echo "   ✓ spacy model downloaded"

# Check if Ollama is installed
echo ""
echo "🔍 Checking Ollama installation..."
if ! command -v ollama &> /dev/null; then
    echo "⚠️  Ollama is not installed."
    echo ""
    echo "   Ollama is required for local AI processing."
    echo "   Would you like to install it now? (yes/no)"
    read -r INSTALL_OLLAMA
    
    if [[ "$INSTALL_OLLAMA" =~ ^[Yy]([Ee][Ss])?$ ]]; then
        echo ""
        echo "📥 Installing Ollama..."
        curl -fsSL https://ollama.ai/install.sh | sh
        echo "   ✓ Ollama installed"
    else
        echo ""
        echo "   ⏭️  Skipping Ollama installation."
        echo "   You can install it later with:"
        echo "   curl -fsSL https://ollama.ai/install.sh | sh"
    fi
else
    echo "   ✓ Ollama is installed"
fi

# Check if llama2 model is available
echo ""
echo "🔍 Checking for llama2 model..."
if command -v ollama &> /dev/null; then
    if ollama list | grep -q "llama2"; then
        echo "   ✓ llama2 model is available"
    else
        echo "⚠️  llama2 model not found."
        echo ""
        echo "   Would you like to download it now? (yes/no)"
        echo "   (This will download ~4GB of data)"
        read -r DOWNLOAD_MODEL
        
        if [[ "$DOWNLOAD_MODEL" =~ ^[Yy]([Ee][Ss])?$ ]]; then
            echo ""
            echo "📥 Downloading llama2 model..."
            ollama pull llama2
            echo "   ✓ llama2 model downloaded"
        else
            echo ""
            echo "   ⏭️  Skipping model download."
            echo "   You can download it later with:"
            echo "   ollama pull llama2"
        fi
    fi
else
    echo "   ⏭️  Skipping (Ollama not installed)"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║              INSTALLATION COMPLETE!                      ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "🎉 All dependencies for Personalized AI Learning are ready!"
echo ""
echo "Next steps:"
echo "  1. Ensure MS Graph authentication is configured"
echo "  2. Enable learning: devtrack enable-learning"
echo "  3. Check status: devtrack learning-status"
echo ""
echo "For more information, see: go-cli/PERSONALIZED_AI.md"
echo ""
