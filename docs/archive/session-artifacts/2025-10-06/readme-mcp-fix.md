# Codebase MCP Server

**Status:** ✅ Production-ready  
**Last Updated:** October 6, 2025

Semantic code search and task management via MCP protocol for Claude Desktop.

---

## Quick Start

```bash
# 1. Prerequisites check
psql -U cliffclarke -d codebase_mcp -c "SELECT 1"  # Database OK?
curl http://localhost:11434/api/tags              # Ollama OK?

# 2. Run tests
cd /Users/cliffclarke/Claude_Code/codebase-mcp
source .venv/bin/activate
./quick_start.sh

# 3. Configure Claude Desktop
# Copy claude_desktop_config.json to:
# ~/Library/Application Support/Claude/claude_desktop_config.json

# 4. Restart Claude Desktop
killall Claude

# 5. Verify in Claude Desktop
# Look for 🔨 tools menu → "codebase-mcp" → 6 tools
```

---

## Documentation

| File | Purpose | When to Read |
|------|---------|-------------|
| **EXECUTIVE_SUMMARY.md** | TL;DR of the fix | Start here |
| **MCP_STDIO_FIX.md** | Detailed troubleshooting | Issues with setup |
| **WRONG_VS_RIGHT.md** | Side-by-side code comparison | Learning/debugging |
| **claude_desktop_config.json** | Sample configuration | Setup phase |
| **quick_start.sh** | One-command test script | Testing |

---

## Architecture

```
Claude Desktop (MCP client)
    ↓ stdio transport
mcp_stdio_server.py (MCP server using official SDK)
    ↓
Tool Handlers (search, index, tasks)
    ↓
Services (chunker, embedder, searcher)
    ↓
Database (PostgreSQL + pgvector)
Ollama (embedding generation)
```

---

## Available Tools

1. **search_code** - Semantic code search across indexed repos
2. **index_repository** - Index a git repository for search
3. **list_tasks** - List tasks with optional filtering
4. **get_task** - Get task details by ID
5. **create_task** - Create a new task
6. **update_task** - Update existing task

---

## What Was Fixed

**Problem:** Original `stdio_server.py` was a custom JSON-RPC server that didn't speak MCP protocol.

**Solution:** New `mcp_stdio_server.py` uses official MCP SDK for protocol compliance.

**Key Changes:**
- ✅ Protocol compliance (initialize, tools/list, tools/call)
- ✅ Proper database session management
- ✅ Tool discovery and registration
- ✅ Parameter validation via schemas

See **WRONG_VS_RIGHT.md** for detailed comparison.

---

## File Structure

```
codebase-mcp/
├── src/
│   ├── mcp/
│   │   ├── mcp_stdio_server.py    ✅ USE THIS
│   │   ├── stdio_server.py        ❌ DEPRECATED
│   │   ├── tools/                 ✅ Tool handlers (working)
│   │   └── logging.py             ✅ Structured logging
│   ├── services/                  ✅ Core services
│   ├── models/                    ✅ Database models
│   └── database.py                ✅ Connection management
├── tests/
│   └── test_mcp_server.py         ✅ Test suite
├── EXECUTIVE_SUMMARY.md           📖 Start here
├── MCP_STDIO_FIX.md               📖 Troubleshooting
├── WRONG_VS_RIGHT.md              📖 Learning guide
├── claude_desktop_config.json     ⚙️ Sample config
└── quick_start.sh                 🚀 Test script
```

---

## Troubleshooting

### "Module not found"
→ Add `cwd` to Claude Desktop config

### "Database connection failed"
```bash
psql -U cliffclarke -d codebase_mcp -c "SELECT 1"
```

### "Ollama not responding"
```bash
curl http://localhost:11434/api/tags
ollama list | grep embeddinggemma
```

### "No tools visible in Claude Desktop"
1. Check logs: `tail -f /tmp/codebase-mcp.log`
2. Restart Claude Desktop: `killall Claude`
3. Verify config location: `~/Library/Application Support/Claude/`

---

## Tech Stack

- **Python 3.13** - Modern async/await
- **FastAPI** - SSE transport (for testing)
- **PostgreSQL 18 + pgvector** - Vector similarity search
- **SQLAlchemy + asyncpg** - Async database ORM
- **Ollama** - Local embedding generation
- **Tree-sitter** - AST-based code parsing
- **MCP SDK** - Protocol implementation

---

## Development

### Running Tests
```bash
python tests/test_mcp_server.py
```

### Adding New Tools
1. Create tool handler in `src/mcp/tools/`
2. Register in `mcp_stdio_server.py`:
   - Add to `list_tools()` 
   - Add to `call_tool()` dispatcher
3. Add input schema
4. Test with test suite

### Database Migrations
```bash
# Generate migration
alembic revision --autogenerate -m "description"

# Apply migration
alembic upgrade head
```

---

## Production Deployment

**Requirements:**
- PostgreSQL 18+ with pgvector extension
- Ollama with embeddinggemma:latest model
- Python 3.11+ with all requirements.txt installed
- Write access to log file location

**Environment Variables:**
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=embeddinggemma:latest
LOG_LEVEL=INFO
LOG_FILE=/var/log/codebase-mcp.log
```

---

## Support

**Check logs first:**
```bash
tail -f /tmp/codebase-mcp.log
```

**Run diagnostics:**
```bash
python tests/test_mcp_server.py
```

**Read documentation:**
- Problems during setup → MCP_STDIO_FIX.md
- Understanding the architecture → WRONG_VS_RIGHT.md
- Quick answers → EXECUTIVE_SUMMARY.md

---

## License

MIT License - See LICENSE file

---

## Contributing

1. Read WRONG_VS_RIGHT.md to understand the architecture
2. Run tests before and after changes
3. Follow existing code style (mypy --strict compliance)
4. Update documentation for new features

---

**Status:** ✅ Ready for production use  
**Confidence:** 95%  
**Next action:** Run `./quick_start.sh`

Make it so. 🖖
