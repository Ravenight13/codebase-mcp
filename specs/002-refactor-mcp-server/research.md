# FastMCP Framework Integration Research

This document consolidates technical research findings for migrating the Codebase MCP Server from the official MCP Python SDK to the FastMCP framework.

## 1. FastMCP Async Support

**Decision**: FastMCP fully supports async def functions with @mcp.tool() decorators for database operations

**Rationale**:
- FastMCP is built with async-first design, supporting async tool handlers natively
- Context injection works seamlessly with async functions
- Compatible with AsyncPG and SQLAlchemy async sessions

**Alternatives Considered**:
- Synchronous-only decorators (rejected: would block event loop during DB operations)
- Manual async wrapper functions (rejected: unnecessary complexity)

**Implementation Notes**:
```python
from fastmcp import FastMCP
from fastmcp.context import Context

mcp = FastMCP("codebase-mcp")

@mcp.tool
async def search_code(query: str, ctx: Context) -> dict:
    """Async tool with database operations."""
    await ctx.info(f"Searching for: {query}")

    # AsyncPG/SQLAlchemy async session operations
    async with get_db_session() as session:
        result = await session.execute(select(CodeChunk)...)
        chunks = result.scalars().all()

    return {"results": chunks}
```

**Key Points**:
- Use `async def` for all tool handlers that perform I/O
- Context methods like `ctx.info()` are async and require `await`
- Database session management integrates naturally with async context managers
- No special configuration needed for async support

## 2. FastMCP Context Logging Integration

**Decision**: FastMCP's context.log() sends logs to MCP client, NOT files. File logging requires separate Python logging configuration.

**Rationale**:
- FastMCP Context logging (`ctx.info()`, `ctx.error()`) is MCP protocol-compliant and sends messages to the CLIENT (e.g., Claude Desktop)
- This is DIFFERENT from traditional file logging
- For `/tmp/codebase-mcp.log`, must use Python's standard logging module alongside Context logging

**Alternatives Considered**:
- Relying solely on Context logging (rejected: logs only go to client, not persisted)
- Custom Context wrapper to redirect to files (rejected: violates MCP protocol)
- Dual logging approach (selected: Context for client, Python logging for files)

**Implementation Notes**:
```python
import logging
from fastmcp import FastMCP
from fastmcp.context import Context

# Configure file logging separately
logging.basicConfig(
    filename='/tmp/codebase-mcp.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

mcp = FastMCP("codebase-mcp")

@mcp.tool
async def search_code(query: str, ctx: Context) -> dict:
    # Client-side logging (MCP protocol)
    await ctx.info(f"Searching for: {query}")

    # File logging (persistence)
    logger.info(f"Search request: query={query}")

    # Both log methods can coexist
    return {"results": []}
```

**Key Points**:
- Context logging methods: `ctx.debug()`, `ctx.info()`, `ctx.warning()`, `ctx.error()`
- Context logs are sent via MCP protocol to client (not to stdout/stderr/files)
- Use Python's `logging` module for file-based logs at `/tmp/codebase-mcp.log`
- Dual logging pattern: Context for client visibility, logging for server persistence
- FastMCP settings provide `log_level` and `log_enabled` for internal framework logging

## 3. FastMCP Schema Override Mechanisms

**Decision**: FastMCP uses automatic schema generation from type hints. Manual override via OpenAPI import is experimental.

**Rationale**:
- FastMCP emphasizes convention-over-configuration with automatic type inference
- Pydantic models in function signatures generate schemas automatically
- Manual schema definition is supported via OpenAPI specification import (experimental feature)
- For most cases, Pydantic models provide sufficient schema control

**Alternatives Considered**:
- Manual JSON Schema definition (not directly supported in stable API)
- Custom schema decorators (rejected: not part of FastMCP API)
- OpenAPI import (available but experimental)
- Pydantic models with Field() constraints (selected: stable, well-supported)

**Implementation Notes**:
```python
from pydantic import BaseModel, Field
from fastmcp import FastMCP

mcp = FastMCP("codebase-mcp")

# Automatic schema generation from Pydantic models
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    limit: int = Field(10, ge=1, le=100, description="Max results")

class SearchResult(BaseModel):
    id: str
    content: str
    similarity_score: float = Field(..., ge=0.0, le=1.0)

@mcp.tool
async def search_code(request: SearchRequest) -> list[SearchResult]:
    """Schema is automatically generated from Pydantic models."""
    return [SearchResult(id="...", content="...", similarity_score=0.95)]

# Experimental: Import from OpenAPI spec
mcp.import_openapi(
    openapi_spec=openapi_dict,
    route_map={"/search": search_code}
)
```

**Key Points**:
- Default approach: Let FastMCP infer schemas from type hints and Pydantic models
- Use Pydantic `Field()` for constraints, descriptions, defaults
- Manual schema override via `import_openapi()` is experimental
- Docstrings are parsed for tool descriptions (no manual description needed)
- Schema conflicts should be resolved by adjusting Pydantic model definitions

## 4. FastMCP Stdio Transport Configuration

**Decision**: FastMCP defaults to stdio transport with simple `mcp.run()` call

**Rationale**:
- Stdio is the default transport for Claude Desktop compatibility
- No explicit configuration needed for stdio
- Alternative transports (HTTP, SSE) require explicit parameters

**Alternatives Considered**:
- SSE transport (current implementation: rejected for complexity)
- HTTP transport (rejected: not compatible with Claude Desktop)
- Stdio transport (selected: Claude Desktop standard)

**Implementation Notes**:
```python
from fastmcp import FastMCP

mcp = FastMCP("codebase-mcp")

# Register tools
@mcp.tool
async def search_code(query: str) -> dict:
    return {"results": []}

# Stdio transport (default)
if __name__ == "__main__":
    mcp.run()  # Uses stdio by default

# Alternative: Explicit stdio
if __name__ == "__main__":
    mcp.run(transport="stdio")

# Alternative transports (not for Claude Desktop)
# mcp.run(transport="http", host="127.0.0.1", port=8000)
# mcp.run(transport="sse", host="127.0.0.1", port=8000)
```

**Key Points**:
- Default `mcp.run()` uses stdio transport automatically
- Compatible with Claude Desktop out-of-the-box
- No FastAPI/HTTP server needed for stdio mode
- Installation: `uv run mcp install server.py` (for Claude Desktop)
- Development mode: `uv run mcp dev server.py` (for testing)

**Migration Impact**:
- Current SSE implementation can be removed entirely
- No need for separate HTTP server or FastAPI endpoints
- Simplified deployment (single Python file)
- Stdout/stderr are used for MCP protocol communication (must not log to stdout/stderr)

## 5. FastMCP Decorator Failure Modes

**Decision**: FastMCP provides limited fail-fast validation for decorator registration. Custom validation needed for production use.

**Rationale**:
- FastMCP exceptions include `ValidationError`, `ToolError`, `InvalidSignature`
- Decorator registration errors are raised at registration time (not runtime)
- No built-in comprehensive startup validation
- Custom validation layer needed to meet constitutional principle V (production quality)

**Alternatives Considered**:
- Rely on FastMCP's built-in validation (rejected: insufficient for production)
- Runtime error detection only (rejected: fails after deployment)
- Custom fail-fast validation at startup (selected: catches issues before serving)

**Implementation Notes**:
```python
from fastmcp import FastMCP
from fastmcp.exceptions import FastMCPError, ValidationError, ToolError, InvalidSignature

mcp = FastMCP("codebase-mcp")

# Decorator registration errors
@mcp.tool
async def invalid_tool(param_without_type) -> dict:  # Raises InvalidSignature
    """Missing type hints cause registration failure."""
    return {}

# Custom fail-fast validation
def validate_server_startup(mcp_server: FastMCP) -> None:
    """Validate all registered components before starting server.

    Raises:
        ValidationError: If any tools/resources fail validation
    """
    # Check all tools are registered
    if not mcp_server.list_tools():
        raise ValidationError("No tools registered")

    # Validate tool schemas
    for tool in mcp_server.list_tools():
        if not tool.input_schema:
            raise ValidationError(f"Tool {tool.name} missing input schema")

    # Test database connectivity
    try:
        test_db_connection()
    except Exception as e:
        raise ValidationError(f"Database connection failed: {e}")

    logger.info("Server startup validation passed")

# Apply validation before starting
if __name__ == "__main__":
    try:
        validate_server_startup(mcp)
        mcp.run()
    except FastMCPError as e:
        logger.critical(f"Server startup failed: {e}")
        sys.exit(1)
```

**Error Messages**:
- `InvalidSignature`: Raised when function signature is incompatible (missing type hints, invalid parameters)
- `ValidationError`: Parameter or return value validation failures
- `ToolError`: General tool operation errors
- `FastMCPError`: Base exception for all FastMCP errors

**Key Points**:
- Decorators validate at registration time (during module import)
- Type hints are REQUIRED for all parameters and return values
- Missing type hints raise `InvalidSignature` immediately
- Custom validation should run before `mcp.run()` to catch configuration issues
- Implement health checks for external dependencies (database, Ollama)

## 6. Pydantic Model Compatibility

**Decision**: Standard Pydantic models (BaseModel) are fully compatible with FastMCP's automatic schema generation

**Rationale**:
- FastMCP uses Pydantic internally for schema generation
- Existing Task, CodeChunk, Repository models will work without modification
- Automatic conversion from SQLAlchemy models to Pydantic schemas via `model_config`
- No conflicts between standard Pydantic and FastMCP

**Alternatives Considered**:
- Custom schema classes (rejected: unnecessary complexity)
- Manual JSON schema definitions (rejected: loses Pydantic validation benefits)
- Standard Pydantic BaseModel (selected: full compatibility, zero changes needed)

**Implementation Notes**:
```python
from pydantic import BaseModel, Field
from fastmcp import FastMCP
import uuid
from datetime import datetime

mcp = FastMCP("codebase-mcp")

# Existing Pydantic models work as-is
class TaskResponse(BaseModel):
    """Existing model from src/models/task.py - no changes needed."""
    id: uuid.UUID
    title: str
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    planning_references: list[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}

class CodeChunkResponse(BaseModel):
    """Existing model from src/models/code_chunk.py - no changes needed."""
    id: uuid.UUID
    code_file_id: uuid.UUID
    content: str
    start_line: int
    end_line: int
    chunk_type: str
    has_embedding: bool = Field(default=False)
    similarity_score: float | None = Field(None)

    model_config = {"from_attributes": True}

# Use existing models directly in tools
@mcp.tool
async def search_code(query: str, limit: int = 10) -> list[CodeChunkResponse]:
    """Search code using existing Pydantic models."""
    async with get_db_session() as session:
        chunks = await search_chunks(session, query, limit)
        return [CodeChunkResponse.model_validate(c) for c in chunks]

@mcp.tool
async def list_tasks(status: str | None = None) -> list[TaskResponse]:
    """List tasks using existing Pydantic models."""
    async with get_db_session() as session:
        tasks = await get_tasks(session, status)
        return [TaskResponse.model_validate(t) for t in tasks]
```

**Compatibility Matrix**:
| Feature | Pydantic v2 | FastMCP Support | Notes |
|---------|-------------|-----------------|-------|
| BaseModel | ✓ | ✓ | Full support |
| Field() constraints | ✓ | ✓ | Reflected in MCP schema |
| model_config | ✓ | ✓ | from_attributes works |
| field_validator | ✓ | ✓ | Validation runs automatically |
| Nested models | ✓ | ✓ | Schema generated recursively |
| Optional types | ✓ | ✓ | Union types supported |
| UUID types | ✓ | ✓ | Serialized as strings |
| datetime | ✓ | ✓ | ISO 8601 format |

**Key Points**:
- Zero code changes needed for existing Pydantic models
- FastMCP automatically generates MCP schemas from Pydantic models
- Field descriptions, constraints, defaults are preserved
- SQLAlchemy → Pydantic conversion via `model_validate()` works seamlessly
- No schema conflicts or compatibility issues identified
- Type safety maintained end-to-end (mypy --strict compliance)

## Migration Path Summary

Based on this research, the migration from MCP SDK to FastMCP involves:

1. **Server Initialization**: Replace SSE transport with simple `mcp.run()` stdio
2. **Tool Registration**: Replace `@server.tool()` with `@mcp.tool` (nearly identical)
3. **Logging**: Add dual logging (Context for client, Python logging for files)
4. **Models**: Keep existing Pydantic models unchanged (full compatibility)
5. **Validation**: Add custom fail-fast validation before server startup
6. **Async**: Continue using async def handlers (full support confirmed)

**Risk Assessment**:
- Low risk: Pydantic model compatibility, async support, stdio transport
- Medium risk: Logging configuration (requires dual approach)
- Low risk: Schema generation (automatic from Pydantic)
- Medium risk: Startup validation (requires custom implementation)

**Constitutional Compliance**:
- Principle III (Protocol Compliance): Stdio transport ensures no stdout/stderr pollution
- Principle V (Production Quality): Custom validation needed for fail-fast behavior
- Principle VIII (Type Safety): Full Pydantic support maintains mypy --strict compliance
- Principle IV (Performance): Migration should not impact indexing or search performance

## References

- FastMCP Repository: https://github.com/jlowin/fastmcp
- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
- Current Implementation: /Users/cliffclarke/Claude_Code/codebase-mcp/src/mcp/server.py
- Existing Models: /Users/cliffclarke/Claude_Code/codebase-mcp/src/models/
