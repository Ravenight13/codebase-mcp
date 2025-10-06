#!/usr/bin/env bash
# Quick setup and test script for MCP stdio server
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 MCP Server Quick Start"
echo "=" | head -c 60
echo ""

# Check prerequisites
echo "1. Checking prerequisites..."

if ! command -v python &> /dev/null; then
    echo "❌ Python not found"
    exit 1
fi

if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL not found"
    exit 1
fi

if ! pgrep -x ollama &> /dev/null; then
    echo "⚠️  Ollama not running - starting it..."
    ollama serve &> /dev/null &
    sleep 2
fi

echo "✅ Prerequisites OK"
echo ""

# Activate virtual environment
echo "2. Activating virtual environment..."
source .venv/bin/activate
echo "✅ Virtual environment activated"
echo ""

# Check database connection
echo "3. Checking database connection..."
if psql -U cliffclarke -d codebase_mcp -c "SELECT 1" &> /dev/null; then
    echo "✅ Database connection OK"
else
    echo "❌ Database connection failed"
    echo "   Run: psql -U cliffclarke -d codebase_mcp -c \"SELECT 1\""
    exit 1
fi
echo ""

# Run tests
echo "4. Running MCP server tests..."
python tests/test_mcp_server.py

# Show next steps
echo ""
echo "📋 Next steps:"
echo ""
echo "1. Copy this config to Claude Desktop:"
echo "   ~/Library/Application Support/Claude/claude_desktop_config.json"
echo ""
cat claude_desktop_config.json
echo ""
echo "2. Restart Claude Desktop:"
echo "   killall Claude"
echo ""
echo "3. Check logs:"
echo "   tail -f /tmp/codebase-mcp.log"
echo ""
echo "4. In Claude, look for 🔨 tools menu"
echo "   Should see 'codebase-mcp' with 6 tools"
echo ""
