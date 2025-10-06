# CRITICAL FIX - Path and Tool Registration Issues

## Issue 1: Python Not Found (SOLVED)

**Error:** `spawn python ENOENT 2`

**Cause:** Claude Desktop can't find `python` command in its PATH

**Fix:** Use absolute path to Python executable

### ❌ OLD Config:
```json
{
  "command": "python",
  ...
}
```

### ✅ NEW Config:
```json
{
  "command": "/Users/cliffclarke/Claude_Code/codebase-mcp/.venv/bin/python",
  ...
}
```

---

## Issue 2: 0 Tools Returned (LIKELY FIXED)

**Symptom:** Server starts but `tools/list` returns empty array

**Possible causes:**
1. Async function not being called properly
2. Database session issues causing silent failures
3. Tool registration not working with MCP SDK version

**Fix:** Created `mcp_stdio_server_v2.py` with:
- Tools defined at module level (not in function)
- Simplified database session handling
- Better error logging
- Direct use of SessionLocal instead of get_db() generator

---

## Testing Instructions

### Step 1: Test minimal MCP server first

```bash
cd /Users/cliffclarke/Claude_Code/codebase-mcp
source .venv/bin/activate

# Test the minimal server (should show 1 tool)
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"0.1.0","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | python test_minimal_mcp.py 2>&1

# Then test tools/list
echo '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' | python test_minimal_mcp.py 2>&1
```

**Expected:** Should see "1 tools" in stderr debug output

### Step 2: Test v2 server

```bash
# Test the v2 server (should show 6 tools)
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"0.1.0","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | python -m src.mcp.mcp_stdio_server_v2 2>&1

echo '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' | python -m src.mcp.mcp_stdio_server_v2 2>&1
```

**Expected:** Should see 6 tools listed

### Step 3: Update Claude Desktop config

Use `claude_desktop_config_FIXED.json`:

```json
{
  "mcpServers": {
    "codebase-mcp": {
      "command": "/Users/cliffclarke/Claude_Code/codebase-mcp/.venv/bin/python",
      "args": ["-m", "src.mcp.mcp_stdio_server_v2"],
      "cwd": "/Users/cliffclarke/Claude_Code/codebase-mcp",
      "env": {
        "DATABASE_URL": "postgresql+asyncpg://cliffclarke@localhost:5432/codebase_mcp",
        "OLLAMA_BASE_URL": "http://localhost:11434",
        "OLLAMA_EMBEDDING_MODEL": "embeddinggemma:latest",
        "LOG_LEVEL": "INFO",
        "LOG_FILE": "/tmp/codebase-mcp.log"
      }
    }
  }
}
```

**Key changes:**
1. ✅ `"command"`: Full path to Python
2. ✅ `"args"`: Changed to `src.mcp.mcp_stdio_server_v2`

### Step 4: Deploy

```bash
# Copy fixed config
cp claude_desktop_config_FIXED.json ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Restart Claude Desktop
killall Claude

# Check logs
tail -f /tmp/codebase-mcp.log
```

---

## Debugging

### If still 0 tools:

```bash
# Check stderr output manually
python -m src.mcp.mcp_stdio_server_v2 2>&1 &
echo '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' | python -m src.mcp.mcp_stdio_server_v2

# Should see tool list in response
```

### Check Claude Desktop logs:

```bash
# Find MCP logs
ls -la ~/Library/Logs/Claude/mcp*.log

# View latest
tail -100 ~/Library/Logs/Claude/mcp-server-codebase-mcp.log
```

### Check server logs:

```bash
tail -100 /tmp/codebase-mcp.log
```

---

## What Changed in v2

| Aspect | v1 | v2 |
|--------|----|----|
| Tools definition | Inside async function | Module level list |
| DB session | `async for db in get_db()` | Direct `SessionLocal()` |
| Error handling | Basic | Comprehensive with traceback |
| Logging | Minimal | Debug output included |

**Why module-level tools?** Ensures the tools list is always available and not dependent on any runtime state.

**Why direct SessionLocal?** The `get_db()` generator is designed for FastAPI dependency injection, not direct async iteration. Using SessionLocal directly gives us full control.

---

## Success Criteria

✅ **Minimal test server shows 1 tool**  
✅ **V2 server shows 6 tools**  
✅ **No ENOENT errors in Claude Desktop**  
✅ **Server stays connected (no immediate disconnect)**  
✅ **Tools visible in Claude Desktop hammer menu**

---

## If STILL Having Issues

Run the diagnostic script:

```bash
chmod +x diagnose.sh
./diagnose.sh > diagnostic_output.txt
```

This will collect:
- Claude Desktop config
- Claude Desktop logs  
- Server logs
- Environment check
- Database/Ollama status

Share `diagnostic_output.txt` for further debugging.

---

**Confidence on path fix:** 100% - ENOENT is definitely a PATH issue  
**Confidence on tools fix:** 85% - architectural fix, but need to test

**Next action:** Test minimal server first, then v2, then deploy to Desktop
