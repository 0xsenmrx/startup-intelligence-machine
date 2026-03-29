#!/bin/bash

# Startup Intelligence Machine v4.1 Launcher (Unix)
# Supports: Linux, macOS, WSL

set -e

echo "============================================"
echo " Startup Intelligence Machine v0.1 Launcher"
echo "============================================"
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python
if ! command -v python3 &>/dev/null; then
  echo -e "${RED}[ERROR] Python 3 not found${NC}"
  echo "Install from: https://python.org"
  exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}[✓] Python found: $PYTHON_VERSION${NC}"

# Virtual environment setup
VENV_DIR="venv"

if [ ! -d "$VENV_DIR" ]; then
  echo "[1/4] Creating virtual environment..."
  python3 -m venv "$VENV_DIR"
else
  echo "[1/4] Virtual environment found"
fi

# Activate
echo "[2/4] Activating environment..."
source "$VENV_DIR/bin/activate"

# Install dependencies
echo "[3/4] Installing dependencies..."
pip install -q pydantic google-genai tenacity ddgs rich || {
  echo -e "${YELLOW}[WARNING] Some packages may have failed, continuing...${NC}"
}

# Check for .env file
echo "[4/4] Checking API credentials..."
if [ ! -f ".env" ]; then
  if [ -z "$GEMINI_API_KEY" ]; then
    echo
    echo -e "${RED}[!] WARNING: No API key found!${NC}"
    echo "Create a .env file with: GEMINI_API_KEY=your_key_here"
    echo "Or set environment variable: export GEMINI_API_KEY=your_key"
    echo "Get key at: https://aistudio.google.com/app/apikey"
    exit 1
  else
    echo -e "${GREEN}[✓] API key found in environment${NC}"
  fi
else
  export $(grep -v '^#' .env | xargs)
  echo -e "${GREEN}[✓] API key loaded from .env${NC}"
fi

echo
echo "============================================"
echo " All systems ready. Starting..."
echo "============================================"
echo

# Run (default to explore mode if no queries.txt exists)
if [ -f "queries.txt" ]; then
  python runner.py --mode=batch "$@"
else
  echo -e "${YELLOW}No queries.txt found. Starting in EXPLORE mode...${NC}"
  python runner.py --mode=explore "$@"
fi

echo
echo "============================================"
echo " Session Complete"
echo "============================================"
