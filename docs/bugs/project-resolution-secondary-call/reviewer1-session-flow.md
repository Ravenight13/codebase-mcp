# Code Review: Session Management and Context Passing Issue

## Reviewer Focus
Session management and context propagation in project resolution flow.

## Root Cause Analysis

### Primary Issue: Missing Context in get_session()
**Location:** `/src/mcp/tools/indexing.py`, line 172
**Confidence:** HIGH

The `ctx` (FastMCP Context) is NOT being passed to `get_session()` when it's called from `index_repository`:

```python
# Current code (INCORRECT):
async with get_session(project_id=resolved_id) as db:  # Line 172
```

**Should be:**
```python
async with get_session(project_id=resolved_id, ctx=ctx) as db:
```

### Secondary Issue: Missing PostgreSQL Registry Persistence
**Location:** `/src/database/auto_create.py`, line 361
**Confidence:** HIGH

When auto-creating a project from config, the system:
1. Creates the project database via `create_project_database()`
2. Adds the project to the **in-memory registry** (line 385)
3. **FAILS to persist** the project to the PostgreSQL `projects` table

This causes a critical desync between in-memory and persistent state.

## Detailed Flow Analysis

### First Resolution (SUCCESS)
1. `index_repository()` calls `resolve_project_id(explicit_id=None, ctx=ctx)`
2. Since no explicit_id, tries session-based resolution
3. Calls `_resolve_project_context(ctx)` which:
   - Gets session_id from `ctx.session_id`
   - Retrieves working directory for session
   - Finds `.codebase-mcp/config.json`
   - Calls `get_or_create_project_from_config()`
   - **Auto-creates project** (database + in-memory registry entry)
   - Returns `(project_id, database_name)`
4. Returns auto-created project successfully

### Second Resolution (FAILURE)
1. `index_repository()` calls `get_session(project_id=resolved_id)`
   - **BUG #1:** `ctx` is NOT passed to `get_session()`
2. `get_session()` calls `resolve_project_id(explicit_id=resolved_id, ctx=ctx)`
   - Since `ctx` wasn't passed to `get_session()`, `ctx` is `None` here
3. With explicit_id set, tries PostgreSQL registry lookup:
   ```sql
   SELECT id, database_name FROM projects WHERE id = $1 OR name = $1
   ```
   - **BUG #2:** Project doesn't exist in PostgreSQL (only in-memory)
   - Returns `None`, logs "not found in registry"
4. Since `ctx` is `None`, cannot try session-based resolution
5. workflow-mcp integration likely not configured or doesn't help
6. Falls back to default workspace

## Evidence from Code

### Missing Context Pass (indexing.py:172)
```python
# Line 116: First resolution WITH context
resolved_id, database_name = await resolve_project_id(explicit_id=project_id, ctx=ctx)

# Line 172: Second resolution WITHOUT context
async with get_session(project_id=resolved_id) as db:  # ctx missing!
```

### In-Memory Only Registration (auto_create.py:385)
```python
# Line 385: Adds to in-memory registry
registry.add(project)  # Only updates Python dictionaries

# Missing: INSERT INTO projects table in PostgreSQL
```

### Registry Lookups Use PostgreSQL (session.py:513-521)
```python
# Explicit ID resolution queries PostgreSQL, not in-memory registry
registry_pool = await _initialize_registry_pool()
async with registry_pool.acquire() as conn:
    row = await conn.fetchrow("""
        SELECT id, database_name
        FROM projects
        WHERE id = $1 OR name = $1
        LIMIT 1
    """, explicit_id)
```

## Proposed Fix

### Fix 1: Pass Context to get_session()
```python
# src/mcp/tools/indexing.py, line 172
async with get_session(project_id=resolved_id, ctx=ctx) as db:
```

### Fix 2: Persist Project to PostgreSQL Registry
```python
# src/database/auto_create.py, after line 385
# Add PostgreSQL persistence
from src.database.session import _initialize_registry_pool

registry_pool = await _initialize_registry_pool()
async with registry_pool.acquire() as conn:
    await conn.execute("""
        INSERT INTO projects (id, name, database_name, description, created_at, updated_at)
        VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT (id) DO NOTHING
    """, project.project_id, project.name, project.database_name, project.description)
```

## Impact Assessment

### Current Behavior
- First call auto-creates project successfully
- Second call fails to find the project, falls back to default
- Data isolation is broken - queries run against wrong database

### After Fix
- Context properly propagated through all calls
- Projects persisted to PostgreSQL on creation
- Consistent resolution regardless of call path

## Confidence Level
**HIGH** - The missing `ctx` parameter and lack of PostgreSQL persistence clearly explain the observed behavior.

## Testing Recommendations

1. **Unit Test:** Verify `get_session()` receives and uses `ctx` parameter
2. **Integration Test:** Verify auto-created projects appear in PostgreSQL `projects` table
3. **End-to-End Test:** Verify second resolution finds auto-created project
4. **Regression Test:** Ensure explicit project_id still works when provided

## Additional Notes

The dual-registry pattern (in-memory + PostgreSQL) creates a synchronization hazard. Consider:
- Using PostgreSQL as the single source of truth
- Or ensuring all write operations update both registries atomically
- Adding periodic sync checks to detect desync conditions