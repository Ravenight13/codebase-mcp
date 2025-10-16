# Quick Reference: Codebase-MCP Project Tracking System

## Current Architecture Summary

### 1. Project Tracking: Stateless Per-Request Model

| Component | Details |
|-----------|---------|
| **State Type** | Stateless (no global active project) |
| **Resolution** | Per-request via `resolve_project_id()` |
| **Priority Order** | Explicit param → workflow-mcp query → default workspace |
| **Storage** | None (in-memory client cache only) |
| **Config Format** | Environment variables only |

### 2. Key Files and Responsibilities

| File | Responsibility | Key Functions |
|------|-----------------|----------------|
| `src/database/session.py` | Project resolution and session management | `resolve_project_id()`, `get_session()` |
| `src/services/workflow_client.py` | HTTP client for workflow-mcp integration | `get_active_project()`, caching |
| `src/mcp/tools/indexing.py` | Index repository tool | Uses `resolve_project_id()` + `get_session()` |
| `src/mcp/tools/search.py` | Search tool | Uses `resolve_project_id()` + `get_session()` |
| `src/mcp/server_fastmcp.py` | Server initialization and lifecycle | Global pool/service management |
| `src/connection_pool/manager.py` | Connection pool lifecycle | ConnectionPoolManager state |
| `src/config/settings.py` | Configuration from environment | Settings model with validation |

### 3. MCP Tools Summary

| Tool | Location | Parameters | Project Support |
|------|----------|------------|-----------------|
| `index_repository` | `src/mcp/tools/indexing.py` | `repo_path`, `project_id` (optional), `force_reindex` | YES - explicit `project_id` parameter |
| `search_code` | `src/mcp/tools/search.py` | `query`, `project_id` (optional), `repository_id`, filters | YES - explicit `project_id` parameter |

### 4. Resolution Flow (Three-Tier)

```
resolve_project_id(explicit_id) called
    ├─ [1] If explicit_id provided
    │   └─ Return immediately (highest priority)
    │
    ├─ [2] If workflow_mcp_url configured
    │   ├─ Create WorkflowIntegrationClient
    │   ├─ Query /api/v1/projects/active
    │   ├─ Timeout: 1.0s (default)
    │   ├─ Cache: 60s (default)
    │   ├─ Return active_project if found
    │   └─ Close client
    │
    └─ [3] Fallback (default)
        └─ Return None (uses project_default schema)
```

### 5. Session & Schema Isolation

```
get_session(project_id) called
    ├─ Create new AsyncSession from pool
    ├─ If project_id is None:
    │   └─ schema_name = "project_default"
    │
    ├─ If project_id provided:
    │   ├─ manager = ProjectWorkspaceManager(engine)
    │   ├─ schema_name = await manager.ensure_workspace_exists(project_id)
    │   └─ (Creates schema + tables on first use)
    │
    ├─ SET search_path TO {schema_name}, public
    ├─ Yield session to caller
    ├─ On success: COMMIT
    └─ On error: ROLLBACK
```

### 6. Connection Pool Architecture

| Aspect | Details |
|--------|---------|
| **Type** | Single global AsyncPG pool |
| **Location** | Module-level in `server_fastmcp.py` |
| **Lifecycle** | Created in lifespan startup, closed on shutdown |
| **Access** | Via `get_pool_manager()` (global singleton) |
| **All Projects** | Share same pool, isolated via PostgreSQL search_path |
| **Pool Size** | min=2, max=10 (configurable via settings) |

### 7. Project Resolution Hierarchy

```
┌─────────────────────────────────────────────┐
│ Tool Receives Request                       │
│ (e.g., index_repository tool)               │
└────────────────┬────────────────────────────┘
                 │
                 v
        ┌─────────────────────┐
        │ Explicit project_id?│─────YES────> Return it
        │ (from parameter)    │              (Priority 1)
        └────────┬────────────┘
                 │ NO
                 v
    ┌──────────────────────────────┐
    │ workflow_mcp_url configured? │
    └────────┬─────────────────────┘
             │ YES
             v
    ┌────────────────────────────┐
    │ Query workflow-mcp server  │──────> Found? Return
    │ /api/v1/projects/active    │        (Priority 2)
    │ (Timeout: 1s, Cached: 60s) │
    └────────┬───────────────────┘
             │ Timeout/Error/Not Found
             v
    ┌──────────────────────────┐
    │ Return None              │
    │ (uses default workspace) │
    │ (Priority 3 - Fallback)  │
    └──────────────────────────┘
```

### 8. Key Differences from Workflow-MCP

| Aspect | Codebase-MCP | Workflow-MCP |
|--------|--------------|--------------|
| **State Model** | Stateless per-request | Stateful session-based |
| **Session File** | None | `.workflow-mcp/session.json` |
| **Active Project** | No global state | Session file-based |
| **Pool Model** | Shared pool + search_path | Per-project pools |
| **Tool Parameters** | Explicit `project_id` | Implicit (from session) |
| **Config Format** | Environment variables | Config files + env vars |
| **Resolution** | Three-tier fallback | Session file first |

### 9. Migration Considerations

#### Low-Risk Changes
- Add session file reading (read-only, non-persistent)
- Update resolution order to check session file
- Keep tool `project_id` parameters
- Keep shared connection pool
- Preserve backward compatibility

#### High-Risk Changes (Avoid Initially)
- Remove `project_id` from tool parameters
- Switch to per-project connection pools
- Implement session persistence (writes)
- Require config files
- Break environment-variable-only deployments

### 10. Critical Constants

| Setting | Default | Location | Notes |
|---------|---------|----------|-------|
| `WORKFLOW_MCP_TIMEOUT` | 1.0s | settings | HTTP timeout for workflow-mcp queries |
| `WORKFLOW_MCP_CACHE_TTL` | 60s | settings | How long to cache active project |
| `DB_POOL_SIZE` | 20 | settings | Min connections in pool |
| `DB_MAX_OVERFLOW` | 10 | settings | Additional connections beyond min |
| `POOL_MAX_IDLE_TIME` | 300s | config | Idle connection timeout (5 min) |
| `POOL_MAX_CONNECTION_LIFETIME` | 3600s | config | Connection lifetime (1 hour) |

### 11. File Locations (Absolute Paths)

```
/Users/cliffclarke/Claude_Code/codebase-mcp/

Project Resolution & Session Management:
├── src/database/session.py                  # Core logic
├── src/services/workflow_client.py          # Workflow-MCP HTTP integration
├── src/models/workflow_context.py           # Data model
├── src/models/project_identifier.py         # Validation

MCP Tools:
├── src/mcp/tools/indexing.py               # index_repository tool
├── src/mcp/tools/search.py                 # search_code tool

Infrastructure:
├── src/mcp/server_fastmcp.py               # Startup/shutdown
├── src/connection_pool/manager.py          # Pool lifecycle
├── src/config/settings.py                  # Configuration

Services (Receive Resolved Project Context):
├── src/services/indexer.py                 # Repository indexing
├── src/services/searcher.py                # Code search
└── src/services/workspace_manager.py       # Schema provisioning
```

---

## What Needs to Change for Workflow-MCP Integration

### Current State
- ✅ Stateless per-request model
- ✅ No persistent session files
- ✅ Optional workflow-mcp integration
- ✅ Three-tier fallback logic
- ✅ Explicit tool `project_id` parameters

### Required Changes for Integration
1. Add `SessionManager` class to read `.codebase-mcp/session.json`
2. Update `resolve_project_id()` to check session file first
3. Maintain backward compatibility with current tool signatures
4. Implement session file format compatibility
5. Add cleanup for expired session files

### Non-Breaking Migration Path
```python
# New resolution order:
1. Explicit project_id parameter (highest priority)
2. Session file (if exists)
3. Query workflow-mcp (if configured)
4. Default workspace (fallback)
```

