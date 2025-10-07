# Session Handoff: FastMCP Server Tool Registration Issue

**Date:** 2025-10-07  
**Status:** 🟡 Server connects, database works, but tools not appearing in Claude Desktop  
**Urgency:** High - Need proper fix, not workaround

---

## Quick Summary

**Problem:** After refactoring from custom MCP server to fastMCP, the server connects successfully and database initializes, but **Claude Desktop sees ZERO tools** in the 🔨 menu.

**Root Cause:** Timing issue - Claude Desktop requests tool list BEFORE fastMCP's lifespan handler completes tool registration.

**Proof Tools Work:** Direct Python test shows all 6 tools ARE registered:
```bash
cd /Users/cliffclarke/Claude_Code/codebase-mcp
.venv/bin/python -c "from src.mcp.server_fastmcp import mcp; import asyncio; print(asyncio.run(mcp.get_tools()).keys())"
# Output: dict_keys(['index_repository', 'search_code', 'get_task', 'list_tasks', 'create_task', 'update_task'])
```

---

## What Was Working (Previous Session)

✅ **Custom MCP Server v3** (`src/mcp/mcp_stdio_server_v3.py`)
- All 6 tools functional
- Database connection working
- Tools appeared in Claude Desktop immediately
- Successfully tested: create_task, get_task, list_tasks, update_task

✅ **Database**
- PostgreSQL with pgvector
- 11 tables created
- Clean reset scripts available (`./clear_data.sh`)

✅ **4/6 Tools Fully Tested**
- `create_task` ✅
- `get_task` ✅  
- `list_tasks` ✅
- `update_task` ✅
- `index_repository` ⚠️ (had timezone import bug, not tested after refactor)
- `search_code` 🔍 (not tested yet, needs indexed data)

---

## What's Broken Now

❌ **FastMCP Server** (`src/mcp/server_fastmcp.py`)
- Server starts successfully
- Database initializes: `"Database initialized successfully"`
- Lifespan handler works
- Tools register correctly (proven by direct Python test)
- **BUT:** Claude Desktop tool list shows empty `[]`

### Evidence from Logs

**Desktop Log** (`~/Library/Logs/Claude/mcp-server-codebase-mcp.log`):
```
2025-10-07T10:48:33.932Z - Processing request of type ListToolsRequest
2025-10-07T10:48:33.933Z - result: {"tools":[]}  ← EMPTY!
```

**Server Log** (`/tmp/codebase-mcp.log`):
```json
{"timestamp":"2025-10-07T10:48:33.929694","message":"Database initialized successfully"}
{"timestamp":"2025-10-07T10:48:33.932743","message":"Processing request of type ListToolsRequest"}
```

**Direct Python Test:**
```bash
.venv/bin/python -c "from src.mcp.server_fastmcp import mcp; import asyncio; print(len(asyncio.run(mcp.get_tools())))"
# Output: 6  ← All tools present!
```

---

## Root Cause Analysis

### The Timing Problem

1. **Claude Desktop connects** → Immediately sends `ListToolsRequest`
2. **fastMCP lifespan handler starts** → Initializing database (takes ~50ms)
3. **Tools list requested** → Returns `[]` because registration isn't complete yet
4. **Desktop caches empty list** → Never re-requests tools
5. **200ms later:** All tools are registered (but Desktop already gave up)

### Why This Happens

FastMCP's lifespan handler runs **asynchronously** during server startup:

```python
@asynccontextmanager
async def lifespan(app: FastMCP) -> AsyncGenerator[None, None]:
    # Startup: Initialize database
    await init_db_connection()  # Takes ~50ms
    
    yield  # Server starts accepting connections HERE
    
    # Shutdown
    await close_db_connection()
```

The problem: Desktop connects immediately after `yield`, but tool decorators might not have finished registering.

---

## Current Configuration

**Desktop Config:** `~/Library/Application Support/Claude/claude_desktop_config.json`
```json
"codebase-mcp": {
  "command": "/Users/cliffclarke/Claude_Code/codebase-mcp/.venv/bin/python",
  "args": ["-m", "src.mcp.server_fastmcp"],
  "env": {
    "PYTHONPATH": "/Users/cliffclarke/Claude_Code/codebase-mcp",
    "DATABASE_URL": "postgresql+asyncpg://cliffclarke@localhost:5432/codebase_mcp",
    "OLLAMA_BASE_URL": "http://localhost:11434",
    "OLLAMA_EMBEDDING_MODEL": "embeddinggemma:latest",
    "LOG_LEVEL": "DEBUG",
    "LOG_FILE": "/tmp/codebase-mcp.log"
  }
}
```

---

## Files to Review

### Core Server Files
- **`src/mcp/server_fastmcp.py`** - Main fastMCP server (228 lines)
  - Line 85: `lifespan` handler with database init
  - Line 127: `mcp = FastMCP("codebase-mcp", version="0.1.0", lifespan=lifespan)`
  - Line 223-228: Tool module imports

### Tool Handler Files (All using `@mcp.tool()` decorator)
- **`src/mcp/tools/tasks.py`** - 4 task management tools
- **`src/mcp/tools/search.py`** - 1 search tool
- **`src/mcp/tools/indexing.py`** - 1 indexing tool

### Working Previous Version (Backup)
- **`src/mcp/mcp_stdio_server_v3.py`** - Known working custom server (can revert to this)

---

## Potential Solutions

### Option 1: Fix Tool Registration Timing (Preferred)

**Problem:** Tool decorators run during module import, but might execute before fastMCP is fully ready.

**Solution:** Move tool registration to happen explicitly AFTER lifespan initialization:

```python
# In server_fastmcp.py
@asynccontextmanager
async def lifespan(app: FastMCP) -> AsyncGenerator[None, None]:
    # Startup
    await init_db_connection()
    
    # Explicitly register tools AFTER database init
    logger.info("Registering tools...")
    # Import tools here (instead of at module level)
    import src.mcp.tools.indexing  # noqa
    import src.mcp.tools.search  # noqa
    import src.mcp.tools.tasks  # noqa
    logger.info(f"Registered {len(await mcp.get_tools())} tools")
    
    yield
    
    # Shutdown
    await close_db_connection()
```

### Option 2: Add Validation Before Accepting Connections

```python
async def lifespan(app: FastMCP) -> AsyncGenerator[None, None]:
    # Startup
    await init_db_connection()
    
    # Wait for tool registration to complete
    max_retries = 10
    for i in range(max_retries):
        tools = await mcp.get_tools()
        if len(tools) == 6:  # All tools registered
            logger.info(f"All {len(tools)} tools registered")
            break
        await asyncio.sleep(0.1)  # 100ms delay
    else:
        raise RuntimeError("Tool registration timeout")
    
    yield
    await close_db_connection()
```

### Option 3: FastMCP Eager Tool Loading

Check if fastMCP has a flag to force eager tool registration:
```python
mcp = FastMCP(
    "codebase-mcp",
    version="0.1.0",
    lifespan=lifespan,
    # Look for flags like:
    # eager_tool_loading=True,
    # lazy_loading=False,
)
```

### Option 4: Revert to Working v3 Server

If fastMCP issues persist, revert to the known-working custom server:
```json
"args": ["-m", "src.mcp.mcp_stdio_server_v3"]
```

---

## Testing Protocol

### 1. Verify Tool Registration Directly
```bash
cd /Users/cliffclarke/Claude_Code/codebase-mcp
.venv/bin/python -c "from src.mcp.server_fastmcp import mcp; import asyncio; tools = asyncio.run(mcp.get_tools()); print(f'Tools: {len(tools)}'); print(list(tools.keys()))"
```
**Expected:** `Tools: 6` with all tool names listed

### 2. Check Server Logs
```bash
tail -50 /tmp/codebase-mcp.log | grep -E "Tool modules imported|Database initialized|tools registered"
```
**Expected:** See confirmation of tool import and database init

### 3. Check Desktop Logs
```bash
tail -50 ~/Library/Logs/Claude/mcp-server-codebase-mcp.log | grep -E "result.*tools|ListToolsRequest"
```
**Expected:** See `"tools":[]` (current bug) or `"tools":[...]` (fixed)

### 4. Restart Claude Desktop & Test
```bash
# Quit Desktop completely
osascript -e 'quit app "Claude"'
sleep 2
# Reopen
open -a Claude
```
Then check 🔨 Tools menu for 6 codebase-mcp tools

### 5. Test Tool Execution
Once tools appear in Desktop:
```
Create a task called "Verify fastMCP fix" with description "All tools working in Claude Desktop"
```
**Expected:** Task created successfully with UUID returned

---

## Database State

**Current Status:** Empty (reset with `./clear_data.sh` last session)

**Tables:** 11 tables, all empty
```sql
SELECT 'repositories', COUNT(*) FROM repositories UNION ALL
SELECT 'code_files', COUNT(*) FROM code_files UNION ALL
SELECT 'tasks', COUNT(*) FROM tasks;
-- All show 0 rows
```

**Reset if Needed:**
```bash
cd /Users/cliffclarke/Claude_Code/codebase-mcp
./clear_data.sh  # Fast (1s), keeps schema
# OR
./reset_database.sh  # Medium (2s), recreates schema
```

---

## Environment Info

**Python:** 3.13.7  
**PostgreSQL:** Postgres.app (14+)  
**fastMCP:** 2.12.4  
**MCP SDK:** 1.16.0  
**OS:** macOS  
**Location:** Aledo, Texas, US

**Key Paths:**
- Project: `/Users/cliffclarke/Claude_Code/codebase-mcp`
- Venv: `/Users/cliffclarke/Claude_Code/codebase-mcp/.venv`
- Server Log: `/tmp/codebase-mcp.log`
- Desktop Log: `~/Library/Logs/Claude/mcp-server-codebase-mcp.log`
- Desktop Config: `~/Library/Application Support/Claude/claude_desktop_config.json`

---

## Key Insights from Session

1. **Tools ARE registered** - Direct Python test proves this
2. **Database works perfectly** - Lifespan handler succeeds
3. **Timing is the culprit** - Desktop requests tools too early
4. **Not a circular import** - Imports work fine (tested directly)
5. **fastMCP lifespan yield** - Server accepts connections before tools are ready

---

## Recommended Approach for Next Session

1. **Try Option 1 first** (Move tool imports into lifespan)
   - Most proper fix
   - Ensures tools register BEFORE server accepts connections
   - Maintains fastMCP architecture

2. **If Option 1 fails, try Option 2** (Add validation loop)
   - Defensive approach
   - Guarantees tools are ready
   - Small delay acceptable for reliability

3. **Document fastMCP issue** 
   - May be a fastMCP bug worth reporting
   - Check fastMCP GitHub issues for similar problems
   - Version 2.12.4 might have known issues

4. **Last resort: Revert to v3**
   - v3 server worked perfectly
   - All 4 tools tested successfully
   - Only missing indexer fixes (timezone import, binary files)

---

## Commands for New Session

```bash
# Navigate to project
cd /Users/cliffclarke/Claude_Code/codebase-mcp

# Test tool registration directly
.venv/bin/python -c "from src.mcp.server_fastmcp import mcp; import asyncio; print('Tools:', len(asyncio.run(mcp.get_tools())))"

# Check server logs
tail -100 /tmp/codebase-mcp.log | grep -i "tool\|database\|error"

# Check Desktop logs
tail -100 ~/Library/Logs/Claude/mcp-server-codebase-mcp.log | grep -i "tool\|error\|result"

# Edit server file
code src/mcp/server_fastmcp.py

# Restart Claude Desktop (after changes)
osascript -e 'quit app "Claude"' && sleep 2 && open -a Claude
```

---

## Success Criteria

✅ All 6 tools appear in Claude Desktop 🔨 menu  
✅ `create_task` executes successfully  
✅ `list_tasks` returns created task  
✅ No timing-related errors in logs  
✅ Database connection stable  

---

## Notes

- User prefers direct feedback, no sugar-coating
- Experienced tech leader (5 years MD, 13+ years sales/ops/tech)
- Comfortable with command line and debugging
- Values proper fixes over quick hacks (but appreciates pragmatism)
- Previous working state: v3 server with 4/6 tools tested successfully

---

## If You Need to Revert

**Restore working v3 server:**
```bash
# Update Desktop config
cat > ~/Library/Application\ Support/Claude/claude_desktop_config.json << 'EOF'
{
  "mcpServers": {
    "codebase-mcp": {
      "command": "/Users/cliffclarke/Claude_Code/codebase-mcp/.venv/bin/python",
      "args": ["-m", "src.mcp.mcp_stdio_server_v3"],
      "env": {
        "PYTHONPATH": "/Users/cliffclarke/Claude_Code/codebase-mcp",
        "DATABASE_URL": "postgresql+asyncpg://cliffclarke@localhost:5432/codebase_mcp",
        "OLLAMA_BASE_URL": "http://localhost:11434",
        "OLLAMA_EMBEDDING_MODEL": "embeddinggemma:latest",
        "LOG_LEVEL": "DEBUG",
        "LOG_FILE": "/tmp/codebase-mcp.log"
      }
    }
  }
}
EOF

# Restart Claude Desktop
osascript -e 'quit app "Claude"' && sleep 2 && open -a Claude
```

Then verify tools appear and work.

---

**End of Handoff**
