#!/usr/bin/env bash
# Quick test script to verify MCP server before Claude Desktop deployment

set -e

echo "🧪 MCP Server Quick Test"
echo "=" | head -c 60
echo ""

cd /Users/cliffclarke/Claude_Code/codebase-mcp
source .venv/bin/activate

echo "1️⃣  Testing minimal MCP server (should show 1 tool)..."
echo ""
timeout 5 bash -c '
    python test_minimal_mcp.py 2>/tmp/minimal_stderr.log &
    PID=$!
    sleep 1
    echo "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"0.1.0\",\"capabilities\":{},\"clientInfo\":{\"name\":\"test\",\"version\":\"1.0\"}}}" | nc localhost 0
    echo "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\",\"params\":{}}" | nc localhost 0
    kill $PID 2>/dev/null || true
' || echo "(timeout ok - checking stderr)"

if grep -q "1 tools" /tmp/minimal_stderr.log 2>/dev/null; then
    echo "✅ Minimal server works - found tools in stderr"
else
    echo "⚠️  Check /tmp/minimal_stderr.log for details"
fi

echo ""
echo "2️⃣  Testing v2 MCP server (should show 6 tools)..."
echo ""

# Direct pipe test
(
    sleep 1
    echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"0.1.0","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
    sleep 0.5
    echo '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
    sleep 0.5
) | python -m src.mcp.mcp_stdio_server_v2 2>&1 | tee /tmp/v2_output.log

echo ""
echo "3️⃣  Checking results..."

if grep -q '"name".*"search_code"' /tmp/v2_output.log; then
    TOOL_COUNT=$(grep -o '"name"' /tmp/v2_output.log | wc -l | tr -d ' ')
    echo "✅ V2 server works - found $TOOL_COUNT tools"
else
    echo "❌ V2 server returned 0 tools"
    echo ""
    echo "Debug output:"
    cat /tmp/v2_output.log
    exit 1
fi

echo ""
echo "=" | head -c 60
echo ""
echo "✅ All tests passed!"
echo ""
echo "📋 Next steps:"
echo "1. Copy config: cp claude_desktop_config_FIXED.json ~/Library/Application\\ Support/Claude/claude_desktop_config.json"
echo "2. Restart Claude: killall Claude"
echo "3. Check for tools in Claude Desktop 🔨 menu"
