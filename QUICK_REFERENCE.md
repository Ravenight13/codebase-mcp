# MCP Server Quick Reference

## 🚀 Starting the Server

```bash
# 1. Verify Prerequisites
pg_isready                           # PostgreSQL running?
curl http://localhost:11434/api/tags # Ollama running?

# 2. Start services if needed
open /Applications/Postgres.app      # Start Postgres
ollama serve &                       # Start Ollama

# 3. Launch Claude Desktop (MCP loads automatically)
open -a Claude
```

**Config Location:** `~/Library/Application Support/Claude/claude_desktop_config.json`

## ✅ Quick Health Check

```bash
# All-in-one test
psql -d codebase_mcp -c "SELECT COUNT(*) FROM tasks;" && \
curl -s http://localhost:11434/api/tags | grep -q "nomic-embed-text" && \
echo "✓ All systems operational"
```

## 📁 Log Locations

```bash
# Real-time monitoring
tail -f ~/Library/Logs/Claude/mcp*.log     # Claude Desktop logs
tail -f /tmp/codebase-mcp.log              # MCP server logs

# Check Claude loaded MCP
# In Claude Desktop: View → Developer Tools → Console → Search "MCP"
```

## 🔄 Restart Procedures

```bash
# Quick restart
killall Claude && open -a Claude           # Restart Claude Desktop

# Full restart
killall -9 Claude && killall ollama && \
ollama serve & && sleep 2 && open -a Claude
```

## 🧪 Test Commands

```bash
# Database connection
psql -d codebase_mcp -c "\dt"

# Test task creation (if test files exist)
uv run python test_tool_handlers.py

# Test MCP tools (if test files exist)
uv run python test_mcp_tools.py

# Manual tool test
echo '{"method":"tools/list"}' | uv run python -m src.mcp.mcp_stdio_server_v3
```

## 🔧 Common Issues & Instant Fixes

| Issue | Command Fix |
|-------|------------|
| **"Database connection failed"** | `createdb codebase_mcp && psql -d codebase_mcp -f init_tables.sql` |
| **"MCP server not showing"** | `killall Claude && open -a Claude` |
| **"Ollama connection refused"** | `ollama serve &` |
| **"No such model: nomic-embed-text"** | `ollama pull nomic-embed-text` |
| **"Permission denied"** | `chmod +x quick_start.sh && ./quick_start.sh` |
| **"Binary file skipped"** | Fixed in code - pull latest |

## 🚨 Emergency Reset

```bash
# Nuclear option - fixes everything
dropdb codebase_mcp 2>/dev/null; \
createdb codebase_mcp && \
psql -d codebase_mcp -f init_tables.sql && \
killall -9 Claude ollama 2>/dev/null; \
ollama serve & && sleep 2 && \
open -a Claude && \
echo "✓ Full reset complete"
```

## ⚡ Performance Benchmarks
- **Task ops:** <200ms
- **Search:** <500ms
- **Small index (10 files):** ~2s
- **Large index (1000 files):** ~60s

## 📍 Key Files
```
src/mcp/mcp_stdio_server_v3.py    # MCP server implementation
claude_desktop_config.json        # Claude MCP configuration
init_tables.sql                   # Database schema
.env                              # Environment variables
```

## 💡 Pro Tips
- Check Developer Tools Console in Claude Desktop for MCP errors
- Server auto-starts with Claude Desktop - no manual launch needed
- Logs are your friend - always check `/tmp/codebase-mcp.log` first
- If search is slow, check `ollama list` - model should be loaded

**Still stuck?** See `SETUP_GUIDE.md` for detailed setup or `DEBUG_LOG.md` for troubleshooting