#!/usr/bin/env bash
# Convenience script to run MCP tools integration tests
# Activates virtual environment and executes test_mcp_tools.py

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "ERROR: Virtual environment not found at .venv"
    echo "Please create it with: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment and run tests
echo "Activating virtual environment..."
source .venv/bin/activate

echo "Running MCP tools integration tests..."
python test_mcp_tools.py
EXIT_CODE=$?

# Deactivate virtual environment
deactivate

exit $EXIT_CODE
