#!/usr/bin/env bash
# Diagnostic script to check Claude Desktop MCP integration

echo "🔍 MCP Server Diagnostics"
echo "=" | head -c 60
echo ""

# Check if Claude Desktop config exists
CLAUDE_CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
if [ -f "$CLAUDE_CONFIG" ]; then
    echo "✅ Claude Desktop config found"
    echo "📄 Config contents:"
    cat "$CLAUDE_CONFIG"
    echo ""
else
    echo "❌ Claude Desktop config not found at:"
    echo "   $CLAUDE_CONFIG"
    echo ""
fi

# Check Claude Desktop logs
CLAUDE_LOGS="$HOME/Library/Logs/Claude"
if [ -d "$CLAUDE_LOGS" ]; then
    echo "📋 Recent Claude Desktop logs:"
    echo ""
    
    # Find most recent MCP-related logs
    echo "MCP server logs:"
    find "$CLAUDE_LOGS" -name "mcp*.log" -type f -mtime -1 | head -5 | while read log; do
        echo ""
        echo "--- $log ---"
        tail -50 "$log"
    done
    
    echo ""
    echo "Main app logs (last 30 lines):"
    if [ -f "$CLAUDE_LOGS/app.log" ]; then
        tail -30 "$CLAUDE_LOGS/app.log"
    fi
else
    echo "❌ Claude Desktop logs not found"
fi

echo ""
echo "📝 Server logs:"
if [ -f "/tmp/codebase-mcp.log" ]; then
    echo "--- /tmp/codebase-mcp.log (last 50 lines) ---"
    tail -50 /tmp/codebase-mcp.log
else
    echo "❌ No server logs at /tmp/codebase-mcp.log"
fi

echo ""
echo "🔧 Environment check:"
echo "Python: $(which python)"
echo "Python version: $(python --version)"
echo "Working directory exists: $([ -d /Users/cliffclarke/Claude_Code/codebase-mcp ] && echo YES || echo NO)"
echo "Server file exists: $([ -f /Users/cliffclarke/Claude_Code/codebase-mcp/src/mcp/mcp_stdio_server.py ] && echo YES || echo NO)"

echo ""
echo "🗄️  Database check:"
psql -U cliffclarke -d codebase_mcp -c "SELECT 1" &>/dev/null && echo "✅ Database accessible" || echo "❌ Database not accessible"

echo ""
echo "🤖 Ollama check:"
curl -s http://localhost:11434/api/tags &>/dev/null && echo "✅ Ollama accessible" || echo "❌ Ollama not accessible"
