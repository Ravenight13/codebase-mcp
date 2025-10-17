# Codebase-MCP Multi-Project Tracking System Analysis Report

## Executive Summary

The codebase-mcp implementation uses a **hybrid approach** combining:
- **Workspace-based isolation** (PostgreSQL schemas per project)
- **Explicit project_id parameters** (tool-level project specification)
- **Workflow-mcp integration** (automatic active project detection with fallback)
- **Global singleton connection pool** (single pool serves all projects)

This differs significantly from workflow-mcp's **session file-based approach** and requires careful migration strategy to avoid breaking existing functionality.

---

## 1. Current Project Tracking Mechanism

### 1.1 Resolution Strategy (Three-Tier Fallback)

**Location**: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/database/session.py` (lines 112-265)

The `resolve_project_id()` function implements multi-level project resolution:

```
1. Explicit ID (highest priority)
   └─> If provided via tool parameter, use immediately
   
2. Workflow-mcp Integration (if configured)
   └─> Query workflow-mcp server at WORKFLOW_MCP_URL
   └─> Endpoint: /api/v1/projects/active
   └─> Timeout: WORKFLOW_MCP_TIMEOUT (default: 1.0s)
   └─> Cache: TTL-based (WORKFLOW_MCP_CACHE_TTL, default: 60s)
   
3. Default Workspace (fallback)
   └─> None → uses "project_default" schema
   └─> All errors fall back gracefully
```

**Key Features**:
- No global state for "active project" in codebase-mcp
- Each tool call independently resolves project context
- Workflow-mcp integration is **optional** (graceful fallback if unavailable)
- Cache is **per-client instance** in `WorkflowIntegrationClient._cache`

### 1.2 Project Identifier Model

**Location**: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/models/project_identifier.py`

```python
# Format validation: lowercase alphanumeric with hyphens
# Examples: "client-a", "frontend-app", "my-project-123"

# Conversion: project_id → schema_name
project_id = "client-a"
schema_name = "project_client_a"  # prefix + underscore + project_id
```

**Validation Rules**:
- Must be lowercase alphanumeric + hyphens only
- Prevents SQL injection by validating before any DB operations
- Raises `ValueError` on invalid format

### 1.3 Session-Based Project Context

**Location**: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/database/session.py` (lines 273-399)

The `get_session()` async context manager is the primary interface:

```python
@asynccontextmanager
async def get_session(project_id: str | None = None) -> AsyncGenerator[AsyncSession, None]:
    """Yields database session with search_path set to project schema"""
    
    # Core flow:
    async with SessionLocal() as session:
        # 1. Resolve schema name
        if project_id is None:
            schema_name = "project_default"
        else:
            manager = ProjectWorkspaceManager(engine)
            schema_name = await manager.ensure_workspace_exists(project_id)
        
        # 2. Set PostgreSQL search_path to isolate schema
        await session.execute(text(f"SET search_path TO {schema_name}, public"))
        
        # 3. Yield session (auto-commit on success, rollback on error)
        yield session
```

**Key Properties**:
- **Per-request isolation**: Each tool invocation gets its own session
- **Auto-provisioning**: Workspace schema created on first use
- **Per-session search_path**: PostgreSQL isolates queries to project schema
- **Transaction management**: Auto-commit/rollback handled by context manager

---

## 2. MCP Tools Requiring Updates

### 2.1 Tools Currently Calling project Resolution

**File**: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/mcp/tools/indexing.py`

```python
@mcp.tool()
async def index_repository(
    repo_path: str,
    project_id: str | None = None,
    force_reindex: bool = False,
    ctx: Context | None = None,
) -> dict[str, Any]:
    # Line 100: Resolve project_id with workflow-mcp fallback
    resolved_id = await resolve_project_id(project_id)
    
    # Lines 104-141: Validate project_id format
    if resolved_id is not None:
        identifier = ProjectIdentifier(value=resolved_id)
        schema_name = identifier.to_schema_name()
    else:
        schema_name = "project_default"
    
    # Later: Pass to indexer service
    # result = await index_repository_service(db, repo_path, resolved_id, ...)
```

**File**: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/mcp/tools/search.py`

```python
@mcp.tool()
async def search_code(
    query: str,
    project_id: str | None = None,
    repository_id: str | None = None,
    file_type: str | None = None,
    directory: str | None = None,
    limit: int = 10,
    ctx: Context | None = None,
) -> dict[str, Any]:
    # Line 106: Resolve project_id with workflow-mcp fallback
    resolved_project_id = await resolve_project_id(project_id)
    
    # Lines 138-145: Validate and convert to schema_name
    if resolved_project_id is not None:
        identifier = ProjectIdentifier(value=resolved_project_id)
        schema_name = identifier.to_schema_name()
    else:
        schema_name = "project_default"
    
    # Later: Pass to search service with resolved schema
```

### 2.2 Tools Summary Table

| Tool | Location | Current Behavior | Project Integration |
|------|----------|------------------|---------------------|
| `index_repository` | `src/mcp/tools/indexing.py` | Indexes repository files | Yes - accepts `project_id` parameter |
| `search_code` | `src/mcp/tools/search.py` | Semantic search | Yes - accepts `project_id` parameter |

**Common Pattern**: Both tools follow identical resolution pattern
1. Accept optional `project_id` parameter
2. Call `resolve_project_id(project_id)` to get active project
3. Validate format with `ProjectIdentifier`
4. Convert to `schema_name`
5. Pass to service layer

---

## 3. Database Connection Management

### 3.1 Global Connection Pool Architecture

**Location**: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/connection_pool/manager.py`

The codebase-mcp uses a **single global connection pool** (AsyncPG-based):

```
┌─────────────────────────────────────────────┐
│  FastMCP Server (server_fastmcp.py)        │
├─────────────────────────────────────────────┤
│ Lifespan Startup:                          │
│  ├─ Create ConnectionPoolManager()         │
│  ├─ Initialize pool (min_size=2-10)        │
│  └─ Store in module-level _pool_manager    │
├─────────────────────────────────────────────┤
│ Tool Execution:                            │
│  ├─ get_pool_manager() returns global      │
│  ├─ Acquire connection from pool           │
│  ├─ Execute queries (via AsyncPG)          │
│  └─ Release connection back to pool        │
└─────────────────────────────────────────────┘
```

### 3.2 Pool Lifecycle Management

**Key Files**:
- `src/connection_pool/manager.py` - ConnectionPoolManager class
- `src/connection_pool/config.py` - PoolConfig settings
- `src/database/session.py` - SessionLocal factory using pool

**Pool Configuration** (from settings):
```python
pool_config = PoolConfig(
    min_size=2,                    # Min connections
    max_size=10,                   # Max connections
    timeout=30.0,                  # Connection acquisition timeout
    command_timeout=60.0,          # Query execution timeout
    max_queries=50000,             # Queries before recycling
    max_idle_time=300.0,           # Idle connection timeout (5 min)
    max_connection_lifetime=3600.0, # Connection lifetime (1 hour)
)
```

### 3.3 Session Creation Flow

**Location**: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/database/session.py` (lines 100-104)

```python
# Global session factory (created from pool)
SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# MCP tools get sessions:
async with SessionLocal() as session:
    # Session uses a connection from the pool
    # All queries routed through PostgreSQL search_path
    pass
```

### 3.4 Multi-Project Pool Strategy

**Current Approach**: Single pool serves all projects
- All projects share the same connection pool
- Schema isolation via PostgreSQL search_path (not separate pools)
- **Advantage**: Simplified connection management, shared resource efficiency
- **Risk**: No per-project connection limiting

**Comparison with Workflow-MCP**:
- workflow-mcp: Dedicated pool per project (separate AsyncPG connections)
- codebase-mcp: Shared pool, schema isolation via SET search_path

---

## 4. Service Constructor Patterns

### 4.1 Service Initialization in MCP Tools

**Pattern Used**: Services get session directly in tool

```python
# In index_repository tool:
async with get_session(project_id=resolved_id) as session:
    result = await index_repository_service(
        db=session,
        repo_path=Path(repo_path),
        project_id=resolved_id,
        force_reindex=force_reindex,
        progress=progress_tracker,
    )
```

### 4.2 Service Constructor Signatures

**Indexer Service** (`src/services/indexer.py`):
```python
async def index_repository(
    db: AsyncSession,
    repo_path: Path,
    name: str,
    project_id: str | None,
    force_reindex: bool = False,
    progress: ProgressCallback = NULL_PROGRESS,
) -> IndexResult:
    """Services receive:
    - db: Already-configured session with search_path set
    - project_id: For logging and workspace tracking
    - Other parameters: specific to operation
    """
```

**Searcher Service** (`src/services/searcher.py`):
```python
async def search_code(
    db: AsyncSession,
    query: str,
    project_id: str | None,
    repository_id: UUID | None = None,
    file_type: str | None = None,
    directory: str | None = None,
    limit: int = 10,
) -> list[SearchResult]:
    """Services don't manage project context:
    - search_path already set by get_session()
    - project_id passed for logging/metadata
    """
```

### 4.3 Pattern Summary

| Layer | Responsibility |
|-------|-----------------|
| MCP Tools | Resolve project_id, call get_session(), pass resolved ID |
| Database Layer | Set search_path based on project schema |
| Services | Execute queries (schema isolation is transparent) |

---

## 5. Existing Config Infrastructure

### 5.1 Settings Management

**Location**: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/config/settings.py`

```python
class Settings(BaseSettings):
    # Database
    database_url: PostgresDsn
    db_pool_size: int = 20
    db_max_overflow: int = 10
    
    # Workflow-MCP Integration
    workflow_mcp_url: HttpUrl | None = None
    workflow_mcp_timeout: float = 1.0
    workflow_mcp_cache_ttl: int = 60
    
    # Embedding
    ollama_base_url: HttpUrl
    ollama_embedding_model: str
    embedding_batch_size: int = 50
    
    # Pool Configuration
    pool_config: PoolConfig  # Auto-created from env vars
```

**No .codebase-mcp config directory exists** - all configuration via environment variables

### 5.2 Environment Variable Support

Supported config sources (in order):
1. `.env` file (if present)
2. Environment variables
3. Hardcoded defaults

```bash
# Example .env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/codebase_mcp
WORKFLOW_MCP_URL=http://localhost:8000
WORKFLOW_MCP_TIMEOUT=1.0
WORKFLOW_MCP_CACHE_TTL=60
EMBEDDING_BATCH_SIZE=50
```

### 5.3 No Session/State Files

Unlike workflow-mcp which maintains:
- `.workflow-mcp/session.json` - Current session state
- `.workflow-mcp/projects/` - Project configurations

codebase-mcp has **no persistent session storage**. Project context is:
- **Resolved on each tool call** (no session state)
- **Optional workflow-mcp integration** (if configured)
- **Stateless per-request model**

---

## 6. Key Differences from Workflow-MCP Approach

### 6.1 Comparison Matrix

| Aspect | Codebase-MCP | Workflow-MCP | Impact |
|--------|--------------|--------------|--------|
| **Active Project Tracking** | Query-time (no state) | Session file + state | Stateless vs stateful |
| **Connection Pool** | Single shared pool | Per-project pools | Shared resources vs isolation |
| **Schema Isolation** | PostgreSQL search_path | Separate databases | Row-level vs schema-level |
| **Configuration** | Environment variables only | Config files + env vars | No persistent config |
| **Session Management** | None (per-request) | Session files with TTL | Stateless vs session-based |
| **Project Resolution** | Three-tier: explicit → workflow-mcp → default | Session-based | Dynamic vs fixed |
| **Tool Parameters** | Explicit `project_id` optional | Session-based (auto) | Explicit vs implicit |

### 6.2 Fundamental Architecture Differences

**Codebase-MCP: Stateless Pull Model**
```
Tool Call
  ├─ Receive project_id (optional)
  ├─ Resolve: Explicit → workflow-mcp → default
  ├─ Get session with resolved project
  ├─ Execute within schema
  └─ Return results
```

**Workflow-MCP: Stateful Session Model**
```
Session Creation
  ├─ Write .workflow-mcp/session.json
  ├─ Set active_project
  └─ Store state with TTL

Tool Call
  ├─ Read session file
  ├─ Check if active project set
  ├─ Use from session (no parameter needed)
  └─ Return results
```

---

## 7. Potential Migration Challenges

### 7.1 Challenge #1: Removing Global State

**Current State in Codebase-MCP**:
- Module-level variables in `server_fastmcp.py`:
  ```python
  _pool_manager: ConnectionPoolManager | None = None
  _health_service: Any = None
  _metrics_service: Any = None
  ```

**Migration Risk**: Moving to session file model requires:
- Writing session state to disk
- Loading session state on tool calls
- Managing session TTL/expiration

### 7.2 Challenge #2: Tool Parameter Changes

**Current**:
```python
@mcp.tool()
async def index_repository(
    repo_path: str,
    project_id: str | None = None,  # Explicit optional parameter
    ...
)
```

**Workflow-MCP Equivalent** (hypothetical):
```python
@mcp.tool()
async def index_repository(
    repo_path: str,
    # project_id removed (comes from session)
    ...
)
```

**Migration Impact**:
- Tool signatures change (backward incompatible)
- Clients relying on explicit `project_id` break
- CLI/SDK tools need updates

### 7.3 Challenge #3: Connection Pool Architecture

**Current**: Single shared pool for all projects
- All connections to same PostgreSQL database
- Schema isolation via search_path

**Workflow-MCP Model**: Per-project connection pools
- Separate pool for each active project
- Connection pool sizes per project
- More resource-intensive

**Migration Path**: Need to decide:
1. Keep shared pool + search_path (compatible with current codebase-mcp)
2. Switch to per-project pools (matches workflow-mcp pattern, more complex)

### 7.4 Challenge #4: Configuration Format

**Current**: Environment variables only
```bash
DATABASE_URL=...
WORKFLOW_MCP_URL=...
```

**Workflow-MCP**: Config files + environment variables
```yaml
# ~/.workflow-mcp/config.yaml
projects:
  - name: client-a
    database_url: ...
```

**Migration**: Adding config file support requires:
- File I/O for session/project config
- Config parsing/validation
- Backward compatibility with env vars

### 7.5 Challenge #5: Session Persistence

**Current**: No session state, stateless per request
- Each tool invocation independent
- No session file to manage

**Workflow-MCP Pattern**: Session file-based
- Write `.workflow-mcp/session.json` on project switch
- Load on tool invocation
- TTL-based expiration cleanup

**Migration Risk**:
- File locking issues on concurrent tool calls
- Session synchronization across processes
- Cleanup of expired sessions

---

## 8. Critical Code Locations Reference

### 8.1 Project Resolution & Session Management

| File | Lines | Purpose |
|------|-------|---------|
| `src/database/session.py` | 112-265 | `resolve_project_id()` function |
| `src/database/session.py` | 273-399 | `get_session()` context manager |
| `src/services/workflow_client.py` | Full | Workflow-MCP HTTP integration |
| `src/models/workflow_context.py` | Full | Workflow context data model |

### 8.2 Tool Implementation

| File | Lines | Purpose |
|------|-------|---------|
| `src/mcp/tools/indexing.py` | 50-150 | index_repository tool |
| `src/mcp/tools/search.py` | 48-160 | search_code tool |

### 8.3 Infrastructure

| File | Lines | Purpose |
|------|-------|---------|
| `src/mcp/server_fastmcp.py` | 76-161 | Global module state (pool manager, services) |
| `src/mcp/server_fastmcp.py` | 169-270 | Lifespan and initialization |
| `src/connection_pool/manager.py` | 50-300+ | ConnectionPoolManager state management |
| `src/config/settings.py` | 48-300+ | Settings configuration |

### 8.4 Services

| File | Purpose |
|------|---------|
| `src/services/indexer.py` | Repository indexing (receives session + project_id) |
| `src/services/searcher.py` | Code search (receives session + project_id) |
| `src/services/workspace_manager.py` | Schema provisioning for projects |

---

## 9. Summary: Current Tracking Mechanism

### 9.1 How Projects Are Tracked Today

1. **No global active project state** - codebase-mcp is stateless
2. **Per-request resolution** - each tool call independently resolves project
3. **Three-tier fallback logic**:
   - Explicit parameter (highest priority)
   - Query workflow-mcp if configured
   - Default workspace (fallback)
4. **Schema-level isolation** - PostgreSQL search_path per session
5. **Shared connection pool** - single pool serves all projects/schemas

### 9.2 Key Invariants

- ✅ No .codebase-mcp config directory (environment-driven)
- ✅ No session files (stateless per-request)
- ✅ No global "active project" (resolved at tool invocation)
- ✅ Backward compatible with None project_id (default workspace)
- ✅ Optional workflow-mcp integration (graceful fallback)
- ✅ Per-session PostgreSQL search_path (schema isolation)

### 9.3 What Needs to Change for Integration

To integrate with workflow-mcp's session model:

1. **Add session file support** → Write `~/.codebase-mcp/session.json`
2. **Change tool signatures** → Remove or make implicit `project_id` parameter
3. **Add session initialization** → Read/validate session on startup
4. **Update resolution logic** → Check session file first before workflow-mcp
5. **Add session cleanup** → Implement TTL-based expiration handling
6. **Consider pool architecture** → Decide: shared pool vs per-project pools

---

## 10. Recommendations for Integration

### 10.1 Low-Risk Migration Path

**Phase 1: Keep current architecture, add session awareness**
- Keep shared connection pool ✅
- Keep tool `project_id` parameters ✅
- Add session file reading (read-only, non-persistent) ✅
- Preserve backward compatibility ✅

```python
# New resolution order:
1. Explicit project_id parameter
2. Read session file (if exists) 
3. Query workflow-mcp
4. Default workspace
```

### 10.2 High-Risk Changes to Avoid (Initially)

- ❌ Removing `project_id` from tool parameters (breaking change)
- ❌ Switching to per-project connection pools (architectural change)
- ❌ Implementing session persistence (adds state complexity)
- ❌ Requiring config files (breaks env-var-only deployment)

### 10.3 Suggested Implementation Approach

1. Create `SessionManager` class (reads `.codebase-mcp/session.json` if exists)
2. Update `resolve_project_id()` to check session file first
3. Keep all existing tool signatures unchanged
4. Add optional env var to enable session file support
5. Document that explicit `project_id` always overrides session

---

## Appendix A: File Locations

All paths are absolute from repository root:

```
/Users/cliffclarke/Claude_Code/codebase-mcp/

Core Session/Project Management:
├── src/database/session.py              # resolve_project_id(), get_session()
├── src/services/workflow_client.py      # WorkflowIntegrationClient
├── src/models/workflow_context.py       # WorkflowIntegrationContext
├── src/models/project_identifier.py     # ProjectIdentifier validation

MCP Tools:
├── src/mcp/tools/indexing.py           # index_repository tool
├── src/mcp/tools/search.py             # search_code tool

Infrastructure:
├── src/mcp/server_fastmcp.py           # Global pool/service management
├── src/connection_pool/manager.py      # ConnectionPoolManager
├── src/config/settings.py              # Settings (env vars only)

Services:
├── src/services/indexer.py             # Indexing logic
├── src/services/searcher.py            # Search logic
└── src/services/workspace_manager.py   # Schema provisioning
```

---

## Appendix B: Key Code Snippets

### B.1 Project Resolution (Current)

```python
# From src/database/session.py::resolve_project_id()
async def resolve_project_id(explicit_id: str | None) -> str | None:
    # 1. Explicit takes precedence
    if explicit_id is not None:
        return explicit_id
    
    # 2. Try workflow-mcp (if configured)
    if settings.workflow_mcp_url is not None:
        client = WorkflowIntegrationClient(...)
        try:
            active_project = await client.get_active_project()
            if active_project:
                return active_project
        except:
            pass
        finally:
            await client.close()
    
    # 3. Fallback to default
    return None
```

### B.2 Session Creation (Current)

```python
# From src/database/session.py::get_session()
@asynccontextmanager
async def get_session(project_id: str | None = None):
    async with SessionLocal() as session:
        try:
            # Determine schema
            if project_id is None:
                schema_name = "project_default"
            else:
                manager = ProjectWorkspaceManager(engine)
                schema_name = await manager.ensure_workspace_exists(project_id)
            
            # Isolate schema
            await session.execute(text(f"SET search_path TO {schema_name}, public"))
            
            yield session
            await session.commit()
        except:
            await session.rollback()
            raise
```

### B.3 Tool Usage (Current)

```python
# From src/mcp/tools/indexing.py::index_repository()
@mcp.tool()
async def index_repository(
    repo_path: str,
    project_id: str | None = None,  # Explicit optional
    ctx: Context | None = None,
):
    # Resolve project (may query workflow-mcp)
    resolved_id = await resolve_project_id(project_id)
    
    # Get isolated session
    async with get_session(resolved_id) as session:
        # Execute indexing with schema isolation
        result = await index_repository_service(
            db=session,
            project_id=resolved_id,
            ...
        )
    
    return result
```

