# Bug 2: Background Indexing Doesn't Trigger Auto-Creation

## Symptoms
- **Tool**: `start_indexing_background`
- **Error**: `database "cb_proj_codebase_mcp_455c8532" does not exist`
- **Auto-creation**: NOT triggered for background jobs
- **Foreground behavior**: Works correctly (auto-creates database)
- **Background behavior**: Fails with database doesn't exist error

## Root Cause Analysis

### Context Flow Comparison

**Foreground Indexing (`index_repository` tool):**
```python
# src/mcp/tools/indexing.py:172
async with get_session(project_id=resolved_id, ctx=ctx) as db:
    # ctx is available from MCP tool parameter
    # ✅ Auto-creation triggered via resolve_project_id() → _resolve_project_context()
```

**Background Indexing Worker:**
```python
# src/services/background_worker.py:127
async with get_session(project_id=project_id, ctx=ctx) as session:
    # ctx is passed to worker, but may be invalid/stale
    # ❌ Auto-creation fails or skips
```

### The Critical Difference

The background worker receives `ctx` from the MCP tool call context, but **FastMCP Context objects are request-scoped** and may not be valid when the background task executes. The worker runs asynchronously after the MCP tool returns, potentially after the context has been cleaned up.

**Evidence from code:**

1. **MCP tool creates task** (`src/mcp/tools/background_indexing.py:111-118`):
   ```python
   asyncio.create_task(
       _background_indexing_worker(
           job_id=job_id,
           repo_path=job_input.repo_path,
           project_id=resolved_id,
           ctx=ctx,  # ⚠️ Context may be stale when worker runs
       )
   )
   ```

2. **Worker uses context** (`src/services/background_worker.py:127`):
   ```python
   async with get_session(project_id=project_id, ctx=ctx) as session:
       # If ctx is invalid/cleaned up, session resolution may fail
   ```

3. **Session resolution** (`src/database/session.py:745-748`):
   ```python
   async def get_session(project_id: str | None = None, ctx: Context | None = None):
       resolved_project_id, database_name = await resolve_project_id(
           explicit_id=project_id,
           ctx=ctx,  # ⚠️ May be None or invalid
       )
   ```

4. **Auto-creation trigger** (`src/database/session.py:394-399`):
   ```python
   # In _resolve_project_context(), only called if ctx is valid
   if ctx is None:
       logger.debug("No FastMCP Context provided, cannot resolve from session")
       return None  # ❌ Auto-creation skipped!
   ```

### Resolution Chain Behavior

When `ctx` is None or invalid, the resolution chain falls back:
1. ❌ **Tier 1 (Explicit ID)**: `project_id` is provided but doesn't trigger auto-create
2. ❌ **Tier 2 (Session config)**: Skipped because `ctx` is invalid
3. ❓ **Tier 3 (workflow-mcp)**: May not have active project
4. ✅ **Tier 4 (Default)**: Falls back to default database

**But:** If the explicit `project_id` points to a non-existent database, the code tries to create a pool for it (`src/database/session.py:762-777`) and fails with "database doesn't exist" error from `create_pool()` → `asyncpg.create_pool()`.

## Code Locations

### Critical Path Files

1. **MCP Tool** - `/Users/cliffclarke/Claude_Code/codebase-mcp/src/mcp/tools/background_indexing.py`
   - Line 111-118: Task creation with `ctx` parameter

2. **Background Worker** - `/Users/cliffclarke/Claude_Code/codebase-mcp/src/services/background_worker.py`
   - Line 127: `get_session(project_id=project_id, ctx=ctx)`

3. **Session Manager** - `/Users/cliffclarke/Claude_Code/codebase-mcp/src/database/session.py`
   - Line 745-748: `resolve_project_id()` call
   - Line 320-322: Context validation (returns None if ctx is None)
   - Line 762-777: Pool creation (fails if database doesn't exist)

4. **Auto-Create Module** - `/Users/cliffclarke/Claude_Code/codebase-mcp/src/database/auto_create.py`
   - Line 227-559: `get_or_create_project_from_config()` (only called with valid ctx)

### Specific Line Numbers

- **Bug location**: `background_indexing.py:111-118` (stale context passed to background task)
- **Failure point**: `session.py:762-777` (pool creation for non-existent database)
- **Missing auto-create**: `session.py:320-322` (skips Tier 2 without valid ctx)

## Proposed Fix

### Option A: Capture Config Path Before Background Task (Recommended)

**Strategy**: Resolve config path in the foreground (while ctx is valid), then pass config path to background worker instead of ctx.

**Changes**:

1. **Modify `start_indexing_background` tool** (`background_indexing.py:84-140`):
   ```python
   @mcp.tool()
   async def start_indexing_background(
       repo_path: str,
       project_id: str | None = None,
       ctx: Context | None = None,
   ) -> dict[str, Any]:
       # NEW: Resolve project context while ctx is still valid
       config_path: Path | None = None
       if ctx:
           try:
               from src.auto_switch.config import find_config_file
               session_ctx_mgr = get_session_context_manager()
               working_dir = await session_ctx_mgr.get_working_directory(ctx.session_id)
               if working_dir:
                   config_path = find_config_file(Path(working_dir))
           except Exception as e:
               logger.debug(f"Failed to resolve config path: {e}")

       # Resolve project_id via 4-tier chain (captures database_name)
       resolved_id, database_name = await resolve_project_id(
           explicit_id=project_id,
           ctx=ctx,
       )

       # ... (existing job creation code) ...

       # Start background worker with config_path instead of ctx
       asyncio.create_task(
           _background_indexing_worker(
               job_id=job_id,
               repo_path=job_input.repo_path,
               project_id=resolved_id,
               config_path=config_path,  # NEW: Pass config path, not ctx
           )
       )
   ```

2. **Modify `_background_indexing_worker` signature** (`background_worker.py:83-112`):
   ```python
   async def _background_indexing_worker(
       job_id: UUID,
       repo_path: str,
       project_id: str,
       config_path: Path | None = None,  # NEW: Accept config path
   ) -> None:
       """Background worker that executes indexing and updates PostgreSQL.

       Args:
           job_id: UUID of indexing_jobs row
           repo_path: Absolute path to repository
           project_id: Resolved project identifier
           config_path: Optional path to .codebase-mcp/config.json for auto-creation
       """
       try:
           # Update status to running
           await update_job(...)

           # NEW: Auto-create project database if config provided
           if config_path:
               try:
                   from src.database.auto_create import get_or_create_project_from_config
                   await get_or_create_project_from_config(config_path)
                   logger.info(f"Auto-created/verified project database for {project_id}")
               except Exception as e:
                   logger.warning(f"Failed to auto-create project database: {e}")
                   # Continue anyway - might exist already

           # Run existing indexer (without ctx)
           async with get_session(project_id=project_id, ctx=None) as session:
               result = await index_repository(...)
   ```

### Option B: Make Pool Creation Trigger Auto-Create (Alternative)

**Strategy**: Modify `get_or_create_project_pool()` to auto-create database if it doesn't exist.

**Changes**:

1. **Modify `get_or_create_project_pool`** (`session.py:203-287`):
   ```python
   async def get_or_create_project_pool(database_name: str) -> asyncpg.Pool:
       # ... existing pool cache check ...

       try:
           # Try to create pool
           pool = await create_pool(
               database_name=database_name,
               min_size=POOL_MIN_SIZE,
               max_size=POOL_MAX_SIZE,
           )
       except asyncpg.InvalidCatalogNameError as e:
           # Database doesn't exist - try to create it
           logger.info(f"Database {database_name} doesn't exist, attempting auto-creation")

           # Extract project info from database name
           # cb_proj_<project_name>_<hash>
           try:
               from src.database.provisioning import create_project_database
               # Parse database_name to get project_name and project_id
               # This requires reverse-engineering the database name format
               # ... (parsing logic) ...

               await create_project_database(project_name, project_id)

               # Retry pool creation
               pool = await create_pool(
                   database_name=database_name,
                   min_size=POOL_MIN_SIZE,
                   max_size=POOL_MAX_SIZE,
               )
           except Exception as create_error:
               logger.error(f"Failed to auto-create database {database_name}: {create_error}")
               raise  # Re-raise original error
   ```

**Problem with Option B**:
- Requires parsing database_name to extract project_name/project_id
- Database name format is hash-based and not easily reversible
- Violates separation of concerns (pool manager shouldn't create databases)

## Recommended Solution: Option A

**Why Option A is better:**

1. **Preserves context while available**: Captures config path before ctx becomes invalid
2. **Explicit and clear**: Auto-creation happens at the start of worker, not hidden in pool logic
3. **No reverse-engineering**: Uses config file directly, no need to parse database names
4. **Separation of concerns**: Worker handles provisioning, pool manager handles connections
5. **Minimal code changes**: Small modifications to two functions

**Implementation steps:**

1. Add config path resolution to `start_indexing_background` (10 lines)
2. Modify worker signature to accept `config_path` instead of `ctx` (1 line)
3. Add auto-creation block at start of worker (8 lines)
4. Remove `ctx` from `get_session()` call in worker (1 line)

**Total changes**: ~20 lines of code

## Testing Plan

### Unit Tests

1. **Test config path capture**:
   ```python
   async def test_background_indexing_captures_config_path(tmp_path):
       """Verify config path is resolved before background task starts."""
       config_path = tmp_path / ".codebase-mcp" / "config.json"
       # Create config file
       # Call start_indexing_background with ctx
       # Mock _background_indexing_worker to capture config_path
       # Assert config_path is not None
   ```

2. **Test auto-creation in worker**:
   ```python
   async def test_worker_auto_creates_database(tmp_path):
       """Verify worker triggers auto-creation when config_path provided."""
       config_path = tmp_path / ".codebase-mcp" / "config.json"
       # Create config file
       # Call worker with config_path
       # Assert database was created
       # Assert indexing succeeded
   ```

3. **Test worker without config**:
   ```python
   async def test_worker_without_config_uses_existing_db():
       """Verify worker works with None config_path if DB exists."""
       # Create database manually
       # Call worker with config_path=None
       # Assert indexing succeeded
   ```

### Integration Tests

1. **Test background indexing with new project**:
   ```python
   async def test_background_indexing_auto_creates_project(tmp_path):
       """End-to-end test: background indexing creates database."""
       # Create config file
       # Set working directory via MCP
       # Call start_indexing_background
       # Poll job status until complete
       # Assert status == "completed"
       # Assert database exists
       # Assert files indexed > 0
   ```

2. **Test background indexing without config**:
   ```python
   async def test_background_indexing_default_project():
       """Verify fallback to default project works."""
       # Don't set working directory
       # Call start_indexing_background
       # Poll job status
       # Assert uses default database
   ```

### Manual Testing

1. **Test with Claude Code**:
   ```bash
   # 1. Create new project with config
   mkdir -p /tmp/test-bg-indexing/.codebase-mcp
   echo '{"project": {"name": "test-bg"}}' > /tmp/test-bg-indexing/.codebase-mcp/config.json

   # 2. Add test files
   echo "def hello(): pass" > /tmp/test-bg-indexing/test.py

   # 3. Call MCP tools
   # - set_working_directory("/tmp/test-bg-indexing")
   # - start_indexing_background(repo_path="/tmp/test-bg-indexing")
   # - get_indexing_status(job_id=<returned_id>)

   # 4. Verify database created
   psql -l | grep cb_proj_test_bg
   ```

2. **Test error handling**:
   - Invalid config file → job should fail gracefully
   - Database creation failure → job should capture error
   - Non-existent repo_path → job should fail with clear message

## Risk Assessment

### Low Risk

- **Scope**: Changes isolated to background indexing path
- **Fallback**: Foreground indexing remains unchanged
- **Validation**: Config path resolution already tested in foreground path
- **Auto-creation**: Uses existing `get_or_create_project_from_config()` (proven code)

### Potential Issues

1. **Config file race condition**:
   - **Risk**: Config file deleted between capture and worker execution
   - **Mitigation**: Worker should handle missing config gracefully (log warning, continue)

2. **Database already exists**:
   - **Risk**: Auto-creation called for existing database
   - **Mitigation**: `get_or_create_project_from_config()` is idempotent (returns existing)

3. **Registry sync failure**:
   - **Risk**: Database created but registry sync fails
   - **Mitigation**: Already handled by auto_create.py (lines 513-529, logs warning but continues)

4. **Performance impact**:
   - **Risk**: Auto-creation adds latency to worker startup
   - **Mitigation**: Only runs if config_path provided, database check is fast (<100ms)

### Rollback Plan

If issues occur:
1. Revert worker signature change (restore `ctx` parameter)
2. Revert tool changes (remove config path capture)
3. Background indexing will fail with original error (database doesn't exist)
4. Users can work around by creating project manually before indexing

## Success Criteria

1. ✅ Background indexing auto-creates database from config file
2. ✅ Background indexing works without config (uses default)
3. ✅ Foreground indexing remains unaffected
4. ✅ All tests pass
5. ✅ No performance regression (worker startup <200ms)
6. ✅ Error handling graceful (logs warnings, continues or fails cleanly)

## Related Issues

- **Bug 1**: Background indexing failure with explicit project_id (separate issue)
- **FR-012**: Multi-project workspace isolation (constitutional requirement)
- **Performance Principle IV**: 60s indexing target (must not be compromised)
