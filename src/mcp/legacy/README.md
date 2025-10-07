# Legacy MCP Server Files

**STATUS**: DEPRECATED - Do not use for new deployments

## Purpose

This directory contains legacy MCP server implementations that have been superseded by `server_fastmcp.py`. These files are preserved for:

1. **Git History Rollback**: Version control reversion capability if migration issues arise
2. **Reference Documentation**: Historical implementation patterns during troubleshooting
3. **Backward Compatibility Validation**: Comparing behavior with new FastMCP implementation

## Migration Information

- **Migration Date**: 2025-10-06
- **Feature Branch**: `002-refactor-mcp-server`
- **New Server**: `src/mcp/server_fastmcp.py`
- **Specification**: `specs/002-refactor-mcp-server/`
- **Rollback Documentation**: `docs/ROLLBACK.md`

## Legacy Files

### Core Server Implementations
- **`server.py`** - Original FastAPI-based MCP server (SSE transport)
- **`stdio_server.py`** - Original stdio transport implementation
- **`mcp_stdio_server.py`** - First stdio server iteration
- **`mcp_stdio_server_v2.py`** - Second stdio server iteration
- **`mcp_stdio_server_v3.py`** - Third stdio server iteration (final legacy version)

### Evolution Timeline
1. `server.py` - Initial SSE implementation
2. `stdio_server.py` - Added stdio transport
3. `mcp_stdio_server.py` - Refactored stdio approach
4. `mcp_stdio_server_v2.py` - Improved stdio handling
5. `mcp_stdio_server_v3.py` - Final legacy version
6. `server_fastmcp.py` - **Current FastMCP implementation** ✅

## Why FastMCP?

The migration to FastMCP addresses:

- **Protocol Compliance**: Native MCP decorators (`@mcp.tool()`)
- **Type Safety**: Built-in Pydantic model validation
- **Developer Experience**: Simplified handler registration
- **Maintainability**: Reduced boilerplate code
- **Testing**: Better testability with FastMCP utilities

## Rollback Procedure

If rollback is needed:

```bash
# Restore from git history (example for server.py)
git checkout HEAD~N -- src/mcp/legacy/server.py
git mv src/mcp/legacy/server.py src/mcp/server.py

# Or restore entire legacy directory
git checkout 002-refactor-mcp-server~1 -- src/mcp/legacy/
```

See `docs/ROLLBACK.md` for complete rollback instructions.

## DO NOT USE

**These files are not maintained and may contain bugs or security issues.**

For all new development, use:
- **`src/mcp/server_fastmcp.py`** - Current production server

## Questions?

See migration documentation:
- Feature specification: `specs/002-refactor-mcp-server/spec.md`
- Implementation plan: `specs/002-refactor-mcp-server/plan.md`
- Task breakdown: `specs/002-refactor-mcp-server/tasks.md`
