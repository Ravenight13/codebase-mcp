# Bug Analysis: Project Resolution and Database Creation Issues

**Date**: 2025-10-19
**Severity**: CRITICAL
**Status**: Root causes identified, fixes pending

## Issue Summary

The codebase-mcp server has multiple critical bugs in its project resolution system that cause:
1. Wrong databases to be used for projects
2. Config changes to be ignored
3. Persistent stale project mappings
4. Cross-contamination between codebase-mcp and workflow-mcp projects

## User-Reported Symptoms

1. **No auto-creation of databases**: Config with project ID fails with "Database does not exist"
2. **Config changes ignored**: Changing project.id in config doesn't affect behavior
3. **Wrong database mapping**: Project "commission-vendor-extractors" mapped to "cb_proj_workflow_mcp_0d1eea82" (clearly a workflow-mcp database, not codebase-mcp)
4. **Persistent mappings**: Mapping persists across config changes and `set_working_directory()` calls

## Root Cause Analysis

### Bug 1: Incorrect Fallthrough in Tier 1 Resolution

**File**: `src/database/session.py:494-550`
**Function**: `resolve_project_id()` - Tier 1 (Explicit ID)

**Issue**:
When an explicit project_id is provided but NOT found in the registry, the function logs a message and **continues to Tier 2** instead of returning an error or creating the project.

```python
# Lines 520-531
if row is None:
    logger.info(
        f"Explicit project_id not found in registry: {explicit_id}, trying other methods",
        ...
    )
    # Don't return - continue to Tier 2, 3, 4  ❌ BUG!
else:
    return (row['id'], row['database_name'])
```

**Impact**:
- User specifies a project ID in config
- ID doesn't exist in PostgreSQL registry yet
- System falls through to workflow-mcp (Tier 3)
- Returns WRONG project from workflow-mcp
- User gets "cb_proj_workflow_mcp_*" database instead of codebase-mcp database

**Expected Behavior**:
When explicit ID provided, either:
1. Return the project if found in registry
2. Trigger auto-creation if not found
3. Return error if can't be created

### Bug 2: Uncontrolled Fallthrough to workflow-mcp

**File**: `src/database/session.py:552-663`
**Functions**: `resolve_project_id()` - Tiers 2 & 3

**Issue**:
When Tier 2 (session config) fails to resolve a project, the system automatically falls through to Tier 3 (workflow-mcp query), even when the user has explicitly configured a project in `.codebase-mcp/config.json`.

**Flow**:
1. User has `.codebase-mcp/config.json` with project ID "commission-vendor-extractors"
2. Tier 2 calls `_resolve_project_context(ctx)` → `get_or_create_project_from_config()`
3. If project not in PostgreSQL registry OR database doesn't exist → Tier 2 fails
4. System falls through to Tier 3 → queries workflow-mcp
5. workflow-mcp returns a different project (e.g., "cb_proj_workflow_mcp_0d1eea82")
6. User's indexing job uses WRONG database

**Impact**:
- Cross-contamination between projects
- User's code indexed into wrong database
- Config changes appear to be ignored
- No error message indicating what went wrong

**Expected Behavior**:
If session config specifies a project, Tier 3 (workflow-mcp) should be skipped entirely. The project should be auto-created if it doesn't exist.

### Bug 3: Database Existence Not Validated

**File**: `src/database/auto_create.py:341-440`
**Function**: `get_or_create_project_from_config()`

**Issue**:
When a project is found in the PostgreSQL registry (lines 346-357), the code checks if the database exists (lines 371-374). However, if the database is missing, it provisions it (lines 378-403) but then **returns the project immediately** (line 440).

The problem: If provisioning fails or is incomplete, the function still returns success.

**Code Flow**:
```python
# Lines 371-374: Check if database exists
db_exists = await conn.fetchval(
    "SELECT 1 FROM pg_database WHERE datname = $1",
    database_name
)

# Lines 376-403: If missing, provision
if not db_exists:
    await create_project_database(row['name'], row['id'])
    # ❌ No verification that creation succeeded!

# Lines 405-440: Return project (even if provisioning failed)
existing_project = Project(...)
return existing_project
```

**Impact**:
- If database creation fails silently, user gets error later
- Error message says "database doesn't exist" instead of showing root cause

### Bug 4: In-Memory Registry Not Cleared on Config Changes

**File**: `src/database/auto_create.py:89-167`
**Class**: `ProjectRegistry`

**Issue**:
The in-memory `ProjectRegistry` singleton (`_registry_instance`) caches projects by ID and name (lines 104-105). When a user changes the project ID in their config file:
1. Cache detects mtime change and invalidates (cache.py works correctly)
2. Config is re-parsed with new ID
3. But in-memory registry still has entry for **old project ID**
4. PostgreSQL registry also has entry for **old project ID**
5. System returns old project instead of creating new one

**Code**:
```python
# Lines 104-105
self._projects_by_id: dict[str, Project] = {}
self._projects_by_name: dict[str, Project] = {}

# Lines 107-118: Lookup by ID
def get_by_id(self, project_id: str) -> Project | None:
    normalized_id = project_id.replace("-", "").lower()
    return self._projects_by_id.get(normalized_id)  # ❌ Returns stale project
```

**Impact**:
- Config changes appear to be ignored
- User can't switch to a new project ID
- Must restart server to clear in-memory registry

**Expected Behavior**:
When config changes to a new project ID, the old project should be removed from in-memory registry, or the registry should be invalidated entirely.

### Bug 5: PostgreSQL Registry Not Updated on Config Changes

**File**: `src/database/auto_create.py:340-453`
**Function**: `get_or_create_project_from_config()`

**Issue**:
When user changes project ID in config, the code checks PostgreSQL registry by **old ID** (lines 347-351) and returns that project without checking if it matches the current config.

**Scenario**:
1. User has config with `project.id = "old-id"`
2. Server creates project "old-id" in PostgreSQL registry
3. User changes config to `project.id = "new-id"`
4. mtime cache invalidates (works correctly)
5. Code checks PostgreSQL registry for "new-id" → not found
6. Code checks PostgreSQL registry by **name** → finds "old-id"
7. Returns "old-id" project (lines 406-440)
8. User still sees old database

**Code**:
```python
# Lines 353-356: Check by name if ID lookup failed
else:
    row = await conn.fetchrow(
        "SELECT id, name, database_name, description FROM projects WHERE name = $1",
        project_name  # ❌ Returns project with old ID!
    )
```

**Impact**:
- Config changes ignored
- User can't migrate to new project ID
- Must manually delete PostgreSQL registry entry

## Database Name Evidence

The user reports database name: **`cb_proj_workflow_mcp_0d1eea82`**

Analysis of this name:
- Prefix: `cb_proj_` ✓ (correct for codebase-mcp)
- Sanitized name: `workflow_mcp` ❌ (should be "commission_processing_ve...")
- Hash: `0d1eea82` (8-char UUID prefix)

This proves the project was created by/for workflow-mcp, not codebase-mcp. The name "workflow_mcp" in the database name is the smoking gun that confirms Tier 3 (workflow-mcp fallthrough) is returning the wrong project.

## Resolution Chain (Current vs Expected)

### Current Behavior (BROKEN)
```
1. Tier 1: explicit_id="commission-vendor-extractors"
   → Not in registry
   → ❌ Falls through to Tier 2

2. Tier 2: session config with project.id
   → get_or_create_project_from_config()
   → ❌ Database doesn't exist, provisioning fails
   → ❌ Falls through to Tier 3

3. Tier 3: workflow-mcp query
   → ✓ Returns "workflow-mcp" project (WRONG!)
   → database_name = "cb_proj_workflow_mcp_0d1eea82"

4. Result: User indexes into WRONG database
```

### Expected Behavior (FIXED)
```
1. Tier 1: explicit_id="commission-vendor-extractors"
   → Not in registry
   → Create project with this ID
   → Return new project

2. If Tier 1 fails, Tier 2: session config
   → get_or_create_project_from_config()
   → Create database if doesn't exist
   → Return new project
   → ❌ NO FALLTHROUGH to Tier 3

3. Tier 3: workflow-mcp (ONLY if no config present)
   → Query workflow-mcp
   → Return project from workflow-mcp

4. Tier 4: default workspace (last resort)
```

## Affected Components

1. **src/database/session.py**
   - `resolve_project_id()` - Tier 1, 2, 3 fallthrough logic
   - `_resolve_project_context()` - session config resolution

2. **src/database/auto_create.py**
   - `get_or_create_project_from_config()` - project creation
   - `ProjectRegistry` - in-memory caching

3. **src/auto_switch/cache.py**
   - `ConfigCache` - mtime validation (working correctly)

4. **src/mcp/tools/background_indexing.py**
   - `start_indexing_background()` - uses resolve_project_id()

## Recommended Fixes

### Fix 1: Prevent Fallthrough in Tier 1
**File**: `src/database/session.py:520-531`

```python
# When explicit ID not found, create project instead of falling through
if row is None:
    logger.info(f"Explicit project_id not found, creating: {explicit_id}")

    # Attempt auto-creation via session config (if available)
    if ctx is not None:
        result = await _resolve_project_context(ctx)
        if result is not None:
            return result

    # If auto-creation fails, return error
    raise ValueError(
        f"Project '{explicit_id}' does not exist in registry. "
        f"Create it using workflow-mcp or set up .codebase-mcp/config.json"
    )
```

### Fix 2: Skip workflow-mcp When Config Present
**File**: `src/database/session.py:552-663`

```python
# Tier 2: Try session-based config resolution (if Context provided)
if ctx is not None:
    try:
        result = await _resolve_project_context(ctx)
        if result is not None:
            return result

        # If config exists but resolution failed, don't fallthrough to workflow-mcp
        from src.auto_switch.discovery import find_config_file
        from src.auto_switch.session_context import get_session_context_manager

        working_dir = await get_session_context_manager().get_working_directory(ctx.session_id)
        if working_dir:
            config_path = find_config_file(Path(working_dir))
            if config_path:
                # Config exists but resolution failed - this is an error
                raise ValueError(
                    f"Found config at {config_path} but failed to resolve project. "
                    f"Check config syntax and database availability."
                )
    except Exception as e:
        logger.warning(f"Session-based resolution failed: {e}")
        # If config exists, re-raise error instead of falling through
        raise

# Only reach Tier 3 if no config was found
```

### Fix 3: Validate Database After Provisioning
**File**: `src/database/auto_create.py:376-403`

```python
if not db_exists:
    logger.warning(f"Database {database_name} missing, provisioning...")
    await create_project_database(row['name'], row['id'])

    # Verify provisioning succeeded
    db_exists_after = await conn.fetchval(
        "SELECT 1 FROM pg_database WHERE datname = $1",
        database_name
    )
    if not db_exists_after:
        raise ValueError(
            f"Failed to provision database {database_name} for project {row['name']}"
        )

    logger.info(f"✓ Database provisioned and verified: {database_name}")
```

### Fix 4: Clear In-Memory Registry on Config Change
**File**: `src/database/auto_create.py:227-256`

Add registry invalidation when config changes are detected:

```python
async def get_or_create_project_from_config(
    config_path: Path,
    registry: ProjectRegistry | None = None,
) -> Project:
    if registry is None:
        registry = get_registry()

    config = read_config(config_path)
    project_name = config["project"]["name"]
    project_id = config["project"].get("id")

    # Check if project name exists with DIFFERENT ID
    existing = registry.get_by_name(project_name)
    if existing and project_id and existing.project_id != project_id:
        logger.warning(
            f"Config changed project ID: {existing.project_id} → {project_id}. "
            f"Removing old project from registry."
        )
        # Clear stale entry from in-memory registry
        # TODO: Implement removal methods in ProjectRegistry
        registry._projects_by_id.pop(existing.project_id.replace("-", "").lower(), None)
        registry._projects_by_name.pop(project_name, None)

    # Continue with normal resolution...
```

### Fix 5: Add Diagnostic Logging
**File**: `src/database/session.py:431-674`

Add logging at each tier to show resolution path:

```python
async def resolve_project_id(...) -> tuple[str, str]:
    logger.info(
        "=== Project Resolution Chain ===",
        extra={
            "context": {
                "explicit_id": explicit_id,
                "has_ctx": ctx is not None,
                "workflow_mcp_enabled": settings.workflow_mcp_url is not None if settings else False,
            }
        }
    )

    # Tier 1
    if explicit_id is not None:
        logger.info(f"Tier 1: Trying explicit ID: {explicit_id}")
        ...

    # Tier 2
    if ctx is not None:
        logger.info("Tier 2: Trying session config")
        ...

    # Tier 3
    if settings.workflow_mcp_url is not None:
        logger.info("Tier 3: Trying workflow-mcp")
        ...

    # Tier 4
    logger.info("Tier 4: Using default workspace")
    ...
```

## Testing Plan

### Test Case 1: Config with New Project ID
```bash
# Setup
echo '{"version":"1.0","project":{"name":"test-project","id":"new-id-123"},"auto_switch":true}' > .codebase-mcp/config.json

# Test
await set_working_directory("/path/to/project")
result = await start_indexing_background("/path/to/project")

# Verify
assert result["project_id"] == "new-id-123"
assert result["database_name"].startswith("cb_proj_test_project_")
assert "workflow_mcp" not in result["database_name"]  # ❌ CURRENTLY FAILS
```

### Test Case 2: Config ID Change
```bash
# Step 1: Create project with ID "old-id"
echo '{"version":"1.0","project":{"name":"test-project","id":"old-id"},"auto_switch":true}' > .codebase-mcp/config.json
await set_working_directory("/path/to/project")
result1 = await start_indexing_background("/path/to/project")

# Step 2: Change ID to "new-id"
echo '{"version":"1.0","project":{"name":"test-project","id":"new-id"},"auto_switch":true}' > .codebase-mcp/config.json
await set_working_directory("/path/to/project")  # Should invalidate cache
result2 = await start_indexing_background("/path/to/project")

# Verify
assert result2["project_id"] == "new-id"  # ❌ CURRENTLY FAILS (returns "old-id")
assert result2["database_name"] != result1["database_name"]
```

### Test Case 3: No workflow-mcp Fallthrough
```bash
# Setup: Config with project that doesn't exist
echo '{"version":"1.0","project":{"name":"missing-project","id":"missing-123"},"auto_switch":true}' > .codebase-mcp/config.json

# Disable workflow-mcp in environment
unset WORKFLOW_MCP_URL

# Test
await set_working_directory("/path/to/project")
result = await start_indexing_background("/path/to/project")

# Verify: Should create project, not fallback to default
assert result["project_id"] == "missing-123"
assert result["database_name"].startswith("cb_proj_missing_project_")
```

## Priority

**CRITICAL** - These bugs cause:
1. Data corruption (indexing into wrong database)
2. Silent failures (config changes ignored)
3. User confusion (error messages don't explain root cause)
4. Cross-project contamination (workflow-mcp projects mixed with codebase-mcp)

## Next Steps

1. **Implement Fix 1-5** as described above
2. **Add integration tests** for all test cases
3. **Update documentation** to clarify project resolution chain
4. **Add user-facing error messages** that explain which tier failed and why
5. **Consider deprecating Tier 3** (workflow-mcp) to simplify system

## Related Files

- `src/database/session.py` - Project resolution (resolve_project_id)
- `src/database/auto_create.py` - Auto-creation (get_or_create_project_from_config)
- `src/database/provisioning.py` - Database creation (create_project_database)
- `src/auto_switch/cache.py` - Config caching (mtime validation)
- `src/auto_switch/discovery.py` - Config discovery (find_config_file)
- `src/mcp/tools/background_indexing.py` - Indexing tool (uses resolve_project_id)
