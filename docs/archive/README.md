# Archive Directory

This directory contains historical files from the Codebase MCP Server project that are no longer actively used but preserved for historical reference.

## Archive Structure

```
archive/
├── legacy-servers/          # Deprecated MCP server implementations
├── experimental-servers/    # Experimental/unused server implementations
├── session-artifacts/       # Development session notes and debugging logs
│   ├── 2025-10-06/         # Session artifacts from Oct 6, 2025
│   └── tasks/              # Task-specific implementation summaries
├── specs/                   # Abandoned or completed feature specifications
├── scripts/                 # Deprecated scripts and utilities
├── configs/                 # Old configuration files
└── code/                    # Experimental or unused code

```

## Archive Organization

### legacy-servers/

Contains legacy MCP server implementations that were deprecated during the FastMCP migration (Feature 002):

- **001-mcp_stdio_server.py** - First stdio server iteration
- **002-mcp_stdio_server_v2.py** - Second stdio server iteration
- **003-mcp_stdio_server_v3.py** - Third stdio server iteration (final legacy version)
- **004-stdio_server.py** - Original stdio transport implementation
- **005-server.py** - MCP Server initialization with SSE transport (still imported by main.py)

**Context**: These files were replaced by `src/mcp/server_fastmcp.py` using the FastMCP framework. See `specs/002-refactor-mcp-server/` for migration details.

**Git History**: All files moved with `git mv` to preserve commit history.

### experimental-servers/

Contains experimental or unused server implementations:

- **main-sse-server.py** - FastAPI application with SSE transport, appears to be an alternative/experimental implementation that was not used in production

**Context**: The production server uses `run_server.py` → `src/mcp/server_fastmcp.py` with stdio transport, not SSE.

### session-artifacts/

Contains development session notes, debugging logs, and status reports organized by date:

#### 2025-10-06/

Session artifacts from FastMCP migration and stdio troubleshooting:

- **executive-summary.md** - MCP stdio fix summary
- **mcp-stdio-fix.md** - Detailed MCP stdio troubleshooting
- **critical-fix.md** - Path and tool registration issues
- **debug-log.md** - Debugging session log
- **readme-mcp-fix.md** - MCP fix readme
- **wrong-vs-right.md** - Side-by-side comparison of wrong vs right implementation
- **phase-3.4-validation.md** - Phase 3.4 validation report
- **session-handoff-fastmcp.md** - FastMCP session handoff notes
- **test-fixes-recommended.md** - Test fixes recommendations
- **session-handoff.md** - General session handoff document
- **implementation-summary.md** - General implementation summary

#### tasks/

Task-specific implementation and validation summaries:

- **t005-validation.md** - Task 005 validation summary
- **t031-implementation.md** - Task 031 implementation summary

## What Was Archived

**Archived on**: 2025-10-08

**Files archived**:
- 5 legacy server implementations (~1,500 lines of code)
- 1 experimental server implementation (main.py, 517 lines)
- 11 session/debug documents (~136KB)
- 4 status summaries

**Files removed** (generated artifacts):
- htmlcov/ directory (2.8MB HTML coverage reports)
- All __pycache__/ directories
- All *.pyc files
- .DS_Store

## Accessing Archived Files

All archived source code files were moved using `git mv`, so their full commit history is preserved. To view the history:

```bash
# View history of a specific archived file
git log --follow docs/archive/legacy-servers/001-mcp_stdio_server.py

# View the file at a specific point in time
git show <commit-hash>:src/mcp/legacy/mcp_stdio_server.py
```

## Related Documentation

- **specs/001-build-a-production/** - Initial production server implementation
- **specs/002-refactor-mcp-server/** - FastMCP migration documentation
- **docs/ROLLBACK.md** - FastMCP rollback procedures
- **docs/ARCHITECTURE.md** - Current architecture documentation

## Why These Files Were Archived

### Legacy Servers

The legacy server implementations were replaced during the FastMCP migration (Feature 002) to:
- Simplify the codebase
- Use the official FastMCP framework for better MCP protocol compliance
- Reduce maintenance burden
- Follow Constitutional Principle XI (FastMCP Foundation)

### Session Artifacts

Session notes and debugging logs were archived because:
- They represent point-in-time debugging and are no longer current
- The issues they document have been resolved
- They are valuable historical reference but not active documentation

### Experimental Code

The experimental SSE server (main.py) was archived because:
- The production implementation uses stdio transport via server_fastmcp.py
- No references to running main.py in production configuration
- SSE transport was not adopted for Claude Desktop integration

## Restoration

If you need to restore any archived file:

```bash
# Restore a specific file to its original location
git mv docs/archive/path/to/file.py src/original/path/file.py

# Or create a new branch with the old implementation
git checkout -b restore-legacy-server <commit-hash>
```

---

**Archive Curator**: Automated via FastMCP audit task (Task ID: 81fd2694-0564-4436-9cec-03d4da0661ca)
**Last Updated**: 2025-10-08
