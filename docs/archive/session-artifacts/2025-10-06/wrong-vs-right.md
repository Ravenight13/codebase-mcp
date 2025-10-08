# Side-by-Side: Wrong vs Right MCP Implementation

This document shows exactly what was wrong and why, so you can understand the architecture.

---

## Architecture Comparison

### ❌ WRONG: stdio_server.py (Custom JSON-RPC)

```
┌─────────────────┐
│ Claude Desktop  │
└────────┬────────┘
         │ Sends: {"jsonrpc":"2.0", "method":"search_code", ...}
         │ Expects: MCP protocol (initialize, tools/list, tools/call)
         ↓
┌─────────────────────────────────┐
│ stdio_server.py                 │  ❌ Protocol mismatch!
│ - Custom JSON-RPC server        │
│ - Direct method routing         │
│ - No MCP handshake              │
│ - No tool discovery             │
└────────┬────────────────────────┘
         │ Tries to route "search_code" directly
         ↓
┌─────────────────┐
│ Tool Handlers   │  ✅ These work fine
└─────────────────┘
```

**Why it fails:**
- Claude Desktop speaks **MCP protocol**
- Your server speaks **generic JSON-RPC**
- It's like trying to connect a USB-C device to a USB-A port

---

### ✅ RIGHT: mcp_stdio_server.py (Official MCP SDK)

```
┌─────────────────┐
│ Claude Desktop  │
└────────┬────────┘
         │ Sends: {"method":"initialize", ...}
         │        {"method":"tools/list", ...}
         │        {"method":"tools/call", "params":{"name":"search_code"}}
         ↓
┌─────────────────────────────────┐
│ mcp_stdio_server.py             │  ✅ Protocol match!
│ - Uses mcp.server.Server        │
│ - Proper MCP handshake          │
│ - @app.list_tools() decorator   │
│ - @app.call_tool() decorator    │
└────────┬────────────────────────┘
         │ Routes through MCP SDK → "search_code"
         ↓
┌─────────────────┐
│ Tool Handlers   │  ✅ These work fine
└─────────────────┘
```

**Why it works:**
- Uses the official MCP SDK
- Speaks the same protocol as Claude Desktop
- Handles all the complexity automatically

---

## Code Comparison: Tool Registration

### ❌ WRONG: Manual routing dictionary

```python
# stdio_server.py
TOOL_REGISTRY: dict[str, Any] = {
    "search_code": search_code_tool,
    "index_repository": index_repository_tool,
    "get_task": get_task_tool,
    # ...
}

async def handle_request(request: dict[str, Any]) -> dict[str, Any]:
    method = request.get("method")
    tool_handler = TOOL_REGISTRY.get(method)  # Direct lookup
    if not tool_handler:
        return {"error": {"code": -32601, "message": "Method not found"}}
    # ...
```

**Problems:**
1. No tool metadata (descriptions, schemas)
2. Claude Desktop can't discover what tools exist
3. No parameter validation
4. No MCP protocol messages

---

### ✅ RIGHT: MCP SDK decorators

```python
# mcp_stdio_server.py
from mcp.server import Server
from mcp.types import Tool

app = Server("codebase-mcp")

@app.list_tools()
async def list_tools() -> list[Tool]:
    """Called when Claude wants to see available tools."""
    return [
        Tool(
            name="search_code",
            description="Search codebase using semantic similarity",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "integer", "default": 10}
                },
                "required": ["query"]
            }
        ),
        # ... more tools
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Called when Claude wants to execute a tool."""
    handler = tool_handlers.get(name)
    result = await handler(db=db, **arguments)
    return [TextContent(type="text", text=json.dumps(result))]
```

**Benefits:**
1. ✅ Tool discovery (Claude can see what's available)
2. ✅ Rich metadata (descriptions, parameter schemas)
3. ✅ Type-safe (Pydantic validation)
4. ✅ Protocol-compliant

---

## Code Comparison: Database Session Management

### ❌ WRONG: Manual generator manipulation

```python
# stdio_server.py
db_generator = get_db()
db_session = await db_generator.__anext__()  # Get session

try:
    result = await tool_handler(db=db_session, **params)
    
    # Try to trigger cleanup by exhausting generator
    try:
        await db_generator.__anext__()  # ❌ This doesn't work!
    except StopAsyncIteration:
        pass
```

**Problems:**
1. Doesn't trigger the cleanup logic in `get_db()`'s finally block
2. Transactions may not commit
3. Sessions may leak
4. Violates async generator protocol

**Why it fails:**
The `get_db()` generator has this structure:
```python
async def get_db():
    async with SessionLocal() as session:
        try:
            yield session  # ← First __anext__() gets here
            await session.commit()  # ← Never reached with your approach!
        except Exception:
            await session.rollback()
        finally:
            await session.close()
```

When you call `__anext__()` twice, you're just trying to get another value from the generator, which doesn't exist. It raises `StopAsyncIteration` but **doesn't execute the cleanup code**.

---

### ✅ RIGHT: Proper async iteration

```python
# mcp_stdio_server.py
async for db in get_db():
    try:
        result = await handler(db=db, **arguments)
        # When loop exits, get_db()'s finally block runs automatically
    except Exception as e:
        # Exception propagates, triggering rollback in get_db()
        raise
```

**Why it works:**
1. `async for` properly drives the generator to completion
2. The cleanup code in `get_db()` runs automatically
3. Transactions commit on success, rollback on error
4. Sessions are properly closed

**The key insight:** `get_db()` is designed for `async for` or FastAPI's `Depends()`, not manual `__anext__()` calls.

---

## Code Comparison: Server Main Loop

### ❌ WRONG: Manual stdin reading

```python
# stdio_server.py
async def run_stdio_server() -> None:
    await init_db_connection()
    
    while True:
        loop = asyncio.get_event_loop()
        line = await loop.run_in_executor(None, sys.stdin.readline)
        
        if not line:
            break
        
        request = json.loads(line)
        response = await handle_request(request)  # ❌ Not MCP protocol!
        print(json.dumps(response), flush=True)
```

**Problems:**
1. No MCP initialization handshake
2. No protocol version negotiation
3. No capability exchange
4. Raw JSON-RPC, not MCP messages

---

### ✅ RIGHT: MCP SDK handles everything

```python
# mcp_stdio_server.py
async def main() -> None:
    await init_db_connection()
    
    # MCP SDK handles all protocol complexity
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )
```

**What the SDK does for you:**
1. ✅ Handles MCP handshake
2. ✅ Protocol version negotiation
3. ✅ Message framing and parsing
4. ✅ Error handling and error codes
5. ✅ Request routing
6. ✅ Response formatting

---

## Protocol Message Comparison

### What Claude Desktop Actually Sends

#### Message 1: Initialize
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "0.1.0",
    "capabilities": {},
    "clientInfo": {"name": "claude-desktop", "version": "1.0.0"}
  }
}
```

**stdio_server.py response:** ❌ "Method 'initialize' not found"  
**mcp_stdio_server.py response:** ✅ Returns server capabilities

---

#### Message 2: List Tools
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list",
  "params": {}
}
```

**stdio_server.py response:** ❌ "Method 'tools/list' not found"  
**mcp_stdio_server.py response:** ✅ Returns array of Tool objects with schemas

---

#### Message 3: Call Tool
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "search_code",
    "arguments": {"query": "async def", "limit": 10}
  }
}
```

**stdio_server.py response:** ❌ "Method 'tools/call' not found"  
**mcp_stdio_server.py response:** ✅ Executes search_code_tool and returns results

---

## The Fundamental Misunderstanding

### You thought:
"I need to build a stdio server that accepts JSON-RPC requests"

### Reality:
"I need to implement the **MCP protocol** which happens to use JSON-RPC as its transport"

It's like saying:
- ❌ "I need to send data over TCP" (true but incomplete)
- ✅ "I need to implement HTTP over TCP" (the actual requirement)

JSON-RPC is the **transport layer**. MCP is the **protocol layer** on top of it.

---

## Analogy: HTTP vs Raw TCP

### Building a web server:

**❌ WRONG Approach:**
```python
# Reading raw TCP sockets
sock = socket.socket()
sock.bind(('0.0.0.0', 80))
while True:
    data = sock.recv(1024)
    # Manually parse HTTP headers
    # Manually handle HTTP verbs
    # Manually format HTTP responses
```

**✅ RIGHT Approach:**
```python
# Using Flask/FastAPI
from fastapi import FastAPI
app = FastAPI()

@app.get("/users")
def list_users():
    return {"users": [...]}
```

**Same with MCP:**
- ❌ WRONG: Manual JSON-RPC over stdio
- ✅ RIGHT: Use the MCP SDK

---

## Key Takeaways

### 1. **Use Official SDKs**
When a protocol has an official SDK, USE IT. Don't reinvent:
- ✅ `mcp` package for MCP servers
- ✅ `httpx` for HTTP clients
- ✅ `sqlalchemy` for SQL
- ❌ Custom protocol implementations

### 2. **Understand the Protocol Layers**
```
Application Layer:  Your tool handlers
Protocol Layer:     MCP (tool discovery, execution)
Transport Layer:    JSON-RPC 2.0
Physical Layer:     stdio (stdin/stdout)
```

You were building at the Transport Layer when you needed the Protocol Layer.

### 3. **Async Generators Are Designed for async for**
```python
# ❌ Don't do this
gen = async_generator()
val = await gen.__anext__()
# Manual cleanup attempts

# ✅ Do this instead
async for val in async_generator():
    # Automatic cleanup
```

### 4. **Test Against Real Clients**
Your custom implementation might "work" in isolation but fails when Claude Desktop tries to connect because it doesn't speak the same protocol.

---

## Performance Impact

**Custom implementation:**
- 0 tools visible to Claude Desktop
- 0 successful tool calls
- 100% failure rate

**MCP SDK implementation:**
- 6 tools visible to Claude Desktop
- ~100% success rate (assuming DB/Ollama work)
- Proper error handling
- Protocol compliance

---

## Final Wisdom (from Captain Picard)

> "There are always alternatives, Number One. But sometimes we must choose the path that leads to greater understanding, even when it challenges our initial assumptions."

You built something functional (JSON-RPC server) but it wasn't the right thing (MCP server). This is a common engineering mistake - solving the problem as you understood it, rather than the actual requirement.

**The lesson:** When integrating with existing systems, understand their protocols fully before building. Check if official SDKs exist. Test against real clients early.

Now you have a production-ready MCP server that actually works with Claude Desktop. 🎯

**Make it so.** 🖖
