#!/bin/bash
# RAVL Framework Installation Script
# Installs RAVL as a git submodule in your project
# Usage: curl -sSL https://raw.githubusercontent.com/KevinT/RavlGPT/main/install.sh | bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "🚀 Installing RAVL Framework..."
echo ""

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: Not in a git repository${NC}"
    echo "   Please run this command from your project root"
    echo "   Initialize git first: git init"
    exit 1
fi

echo -e "${GREEN}✅ Git repository detected${NC}"

# Check if .ravl already exists
if [ -d ".ravl" ]; then
    echo -e "${YELLOW}⚠️  .ravl directory already exists${NC}"
    echo "   RAVL may already be installed"
    echo ""
    read -p "   Reinstall? This will remove and re-add the submodule (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}Installation cancelled${NC}"
        exit 0
    fi

    # Remove existing submodule
    echo "   Removing existing .ravl..."
    git submodule deinit -f .ravl 2>/dev/null || true
    git rm -f .ravl 2>/dev/null || true
    rm -rf .ravl .git/modules/.ravl
fi

# Add RAVL as submodule
echo "Adding RAVL submodule..."
if git submodule add https://github.com/KevinT/RavlGPT .ravl 2>&1; then
    echo -e "${GREEN}✅ Added .ravl submodule${NC}"
else
    echo -e "${RED}❌ Failed to add submodule${NC}"
    echo "   Check your internet connection and try again"
    exit 1
fi

# Make CLI tools executable
echo "Making CLI tools executable..."
if chmod +x .ravl/ravl/bin/* 2>&1; then
    echo -e "${GREEN}✅ Made CLI tools executable${NC}"
else
    echo -e "${YELLOW}⚠️  Could not make tools executable (may need manual chmod)${NC}"
fi

# Create wrapper symlink
echo "Creating ./ravl wrapper..."
if [ -L "./ravl" ]; then
    rm -f ./ravl
fi
if ln -s .ravl/ravl/bin/ravl-wrapper ./ravl 2>&1; then
    echo -e "${GREEN}✅ Created ./ravl wrapper${NC}"
else
    echo -e "${YELLOW}⚠️  Could not create symlink (may need to create manually)${NC}"
fi

# Check Python version
echo "Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
    MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

    if [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 9 ] && [ "$MINOR" -le 13 ]; then
        echo -e "${GREEN}✅ Python $PYTHON_VERSION found${NC}"
    else
        echo -e "${YELLOW}⚠️  Python $PYTHON_VERSION found (3.9-3.13 recommended)${NC}"
        echo "   Install Python 3.12: brew install python@3.12"
    fi
else
    echo -e "${RED}❌ Python 3 not found${NC}"
    echo "   Install Python: brew install python@3.12"
fi

# Check for API keys
echo "Checking for LLM API keys..."
HAS_KEY=false

if [ ! -z "$ANTHROPIC_API_KEY" ]; then
    echo -e "${GREEN}✅ ANTHROPIC_API_KEY found${NC}"
    HAS_KEY=true
fi

if [ ! -z "$OPENAI_API_KEY" ]; then
    echo -e "${GREEN}✅ OPENAI_API_KEY found${NC}"
    HAS_KEY=true
fi

if [ ! -z "$GOOGLE_API_KEY" ]; then
    echo -e "${GREEN}✅ GOOGLE_API_KEY found${NC}"
    HAS_KEY=true
fi

if [ "$HAS_KEY" = false ]; then
    echo -e "${YELLOW}⚠️  No LLM API keys found${NC}"
    echo "   Markdown loops require an API key"
    echo ""
    echo "   ${BLUE}To get started:${NC}"
    echo "   1. Get an API key from: https://console.anthropic.com/"
    echo "   2. Set it in your shell:"
    echo "      ${BLUE}export ANTHROPIC_API_KEY=\"sk-ant-...\"${NC}"
    echo ""
fi

# Test venv creation (lightweight check - don't actually create it)
echo "Checking virtual environment support..."
if command -v python3 &> /dev/null; then
    if python3 -c "import venv" 2>/dev/null; then
        echo -e "${GREEN}✅ Virtual environment support available${NC}"
    else
        echo -e "${YELLOW}⚠️  Python venv module not found${NC}"
        echo "   Install: sudo apt install python3-venv"
    fi
fi

# Success message
echo ""
echo -e "${GREEN}Installation complete! 🎉${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"

if [ "$HAS_KEY" = true ]; then
    echo "  ./ravl example_1_single_loop    # Run rugby tips example"
else
    echo "  ${YELLOW}# First, set your API key:${NC}"
    echo "  export ANTHROPIC_API_KEY=\"sk-ant-...\""
    echo ""
    echo "  ${BLUE}# Then run an example:${NC}"
    echo "  ./ravl example_1_single_loop"
fi

echo "  ./ravl --list                   # List all available loops"
echo "  ./ravl-clone example_1_single_loop my_tips  # Clone and customize"
echo ""
echo -e "${BLUE}Documentation:${NC}"
echo "  cat .ravl/INSTALL.md            # Installation guide"
echo "  cat .ravl/docs/README.md        # Framework overview"
echo ""
