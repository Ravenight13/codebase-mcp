# Bug Report: Missing Database Existence Check in Registry Lookup

**Date**: 2025-10-19
**Severity**: HIGH
**Status**: IDENTIFIED
**Reporter**: System Testing
**Branch**: `fix/project-resolution-auto-create`

---

## Summary

When `get_or_create_project()` finds a project in the PostgreSQL registry, it returns the project immediately without validating that the referenced database actually exists. This causes indexing operations to fail with "database does not exist" errors when the registry entry is stale or corrupted.

---

## Impact

**User-Facing Symptoms**:
- Indexing jobs start but immediately fail with database errors
- Error message: `relation "code_chunks" does not exist` or `database "cb_proj_*" does not exist`
- Users cannot index repositories even though project appears to be configured correctly

**System Impact**:
- Registry entries can become orphaned (project exists but database doesn't)
- No automatic recovery mechanism
- Cross-contamination between workflow-mcp and codebase-mcp projects possible

**Affected Operations**:
- `start_indexing_background()` - Fails when database missing
- `search_code()` - Fails when database missing
- All database-dependent MCP tools

---

## Root Cause Analysis

### Code Location
**File**: `src/database/auto_create.py`
**Function**: `get_or_create_project()`
**Lines**: 348-384

### The Bug

```python
# Step 3.5: Check PostgreSQL registry (for server restart scenarios)
async with registry_pool.acquire() as conn:
    if project_id:
        row = await conn.fetchrow(
            "SELECT id, name, database_name, description FROM projects WHERE id = $1",
            project_id
        )
    else:
        row = await conn.fetchrow(
            "SELECT id, name, database_name, description FROM projects WHERE name = $1",
            project_name
        )

    if row:
        # Found in PostgreSQL - add to in-memory registry and return
        existing_project = Project(
            project_id=row['id'],
            name=row['name'],
            database_name=row['database_name'],  # ⚠️ NEVER VALIDATES DATABASE EXISTS
            description=row['description'] or ""
        )
        registry.add(existing_project)
        return existing_project  # ⚠️ RETURNS WITHOUT CHECKING
```

**The Problem**:
1. Queries registry for project metadata ✅
2. Finds project with `database_name` field ✅
3. **NEVER checks if that database actually exists** ❌
4. Returns project to caller ❌
5. Caller attempts to connect to non-existent database ❌
6. Operation fails with cryptic error ❌

### Why This Happens

**Scenario 1: Manual Registry Corruption**
- Admin manually deletes project database
- Registry entry remains
- Code trusts registry blindly

**Scenario 2: Cross-Server Contamination**
- Project created in workflow-mcp with ID `04f99cfe...`
- Config file copied to codebase-mcp directory with same ID
- Codebase-mcp creates registry entry pointing to `cb_proj_*` database
- Actual database is `wf_proj_*` (different server, different schema)
- Registry points to non-existent database

**Scenario 3: Failed Database Provisioning**
- Project creation starts
- Registry entry inserted successfully
- Database provisioning fails (disk full, permissions, etc.)
- Registry entry remains but database doesn't exist
- Next restart finds registry entry and trusts it

---

## Reproduction Steps

### Setup
```bash
# 1. Create registry entry with non-existent database
psql -h localhost -U postgres -d codebase_mcp <<SQL
INSERT INTO projects (id, name, database_name, description, created_at, updated_at, metadata)
VALUES (
    '12345678-1234-1234-1234-123456789012',
    'test-project',
    'cb_proj_test_project_12345678',  -- Database doesn't exist
    'Test project',
    NOW(),
    NOW(),
    '{}'::jsonb
);
SQL

# 2. Verify database doesn't exist
psql -h localhost -U postgres -c "\l" | grep cb_proj_test_project
# (should show nothing)

# 3. Create config pointing to this project
mkdir -p /tmp/test-repo/.codebase-mcp
cat > /tmp/test-repo/.codebase-mcp/config.json <<JSON
{
  "version": "1.0",
  "project": {
    "name": "test-project",
    "id": "12345678-1234-1234-1234-123456789012"
  }
}
JSON
```

### Trigger Bug
```python
# Via MCP tools
result = await set_working_directory("/tmp/test-repo")
# Returns success - config found

job = await start_indexing_background("/tmp/test-repo")
# Job starts

status = await get_indexing_status(job["job_id"])
# Status: "failed"
# Error: 'relation "code_chunks" does not exist'
```

### Expected Behavior
- System detects database doesn't exist
- Automatically provisions database
- Indexing proceeds successfully

### Actual Behavior
- System trusts registry entry
- Attempts to connect to non-existent database
- Indexing fails immediately

---

## Evidence

### Test Case Failure (workflow-mcp)

```
⏺ codebase-mcp - start_indexing_background
  ⎿  {
       "job_id": "8e67f1e3-dbd7-42da-a536-aa31c7956f83",
       "status": "pending",
       "project_id": "04f99cfe-6c6e-49a8-a895-bda0c2016248",
       "database_name": "cb_proj_workflow_mcp_dev_04f99cfe"
     }

⏺ codebase-mcp - get_indexing_status
  ⎿  {
       "status": "failed",
       "error_message": "relation \"code_chunks\" does not exist"
     }
```

### Registry vs Database Mismatch

```sql
-- Registry entry
SELECT name, database_name FROM projects WHERE name = 'workflow-mcp-dev';
name             | database_name
-----------------+-----------------------------------
workflow-mcp-dev | cb_proj_workflow_mcp_dev_04f99cfe

-- Actual database
\l | grep workflow_mcp
wf_proj_workflow_mcp_dev_cc59e45a  -- Different prefix, different hash!
```

---

## Fix Strategy

### Solution: Add Database Existence Validation

**Location**: `src/database/auto_create.py:348-384`

**Implementation**:
```python
if row:
    # Found in PostgreSQL registry
    database_name = row['database_name']

    # ✅ ADD: Verify database actually exists
    db_exists = await conn.fetchval(
        "SELECT 1 FROM pg_database WHERE datname = $1",
        database_name
    )

    if not db_exists:
        # Database missing - provision it now
        logger.warning(
            f"Database {database_name} missing for project {row['name']}, provisioning...",
            extra={
                "context": {
                    "operation": "get_or_create_project",
                    "project_id": row['id'],
                    "database_name": database_name,
                    "recovery": "auto_provision"
                }
            }
        )

        # Extract project name and ID from row
        await create_project_database(row['name'], row['id'])

        logger.info(
            f"✓ Database provisioned: {database_name}",
            extra={
                "context": {
                    "operation": "get_or_create_project",
                    "database_name": database_name,
                    "recovery": "completed"
                }
            }
        )

    # Now safe to return the project
    existing_project = Project(
        project_id=row['id'],
        name=row['name'],
        database_name=database_name,
        description=row['description'] or ""
    )
    registry.add(existing_project)

    # Update config if needed...
    return existing_project
```

### Benefits
1. **Self-Healing**: Automatically recovers from orphaned registry entries
2. **User-Friendly**: Users never see "database does not exist" errors
3. **Idempotent**: Safe to call multiple times
4. **Auditable**: Logs all recovery actions

---

## Test Cases Required

### 1. Registry Entry Exists, Database Missing
```python
async def test_auto_provision_missing_database():
    """Test automatic database provisioning when registry entry orphaned."""
    # Create registry entry
    await insert_registry_entry(project_id, "test-project", "cb_proj_test_12345678")

    # Ensure database doesn't exist
    await drop_database_if_exists("cb_proj_test_12345678")

    # Call get_or_create_project
    project = await get_or_create_project(config_path)

    # Verify database was auto-provisioned
    db_exists = await check_database_exists("cb_proj_test_12345678")
    assert db_exists, "Database should be auto-provisioned"

    # Verify schema initialized
    async with pool.acquire() as conn:
        tables = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        assert len(tables) >= 3, "Should have repositories, code_files, code_chunks tables"
```

### 2. Registry Entry Correct, Database Exists
```python
async def test_no_provision_when_database_exists():
    """Test no unnecessary provisioning when database already exists."""
    # Create registry entry AND database
    project_id = await create_full_project("test-project")

    # Call get_or_create_project (should not re-provision)
    with assert_no_database_creation():
        project = await get_or_create_project(config_path)

    assert project.project_id == project_id
```

### 3. Cross-Server ID Contamination
```python
async def test_reject_wrong_database_prefix():
    """Test detection of cross-server database contamination."""
    # Create registry entry with wrong prefix
    await insert_registry_entry(
        "04f99cfe-6c6e-49a8-a895-bda0c2016248",
        "workflow-mcp",
        "wf_proj_workflow_mcp_04f99cfe"  # workflow-mcp prefix, not codebase-mcp
    )

    # Should detect mismatch and re-provision with correct prefix
    project = await get_or_create_project(config_path)

    assert project.database_name.startswith("cb_proj_")
    assert not project.database_name.startswith("wf_proj_")
```

---

## Acceptance Criteria

- [ ] Database existence check added after registry lookup
- [ ] Automatic database provisioning when missing
- [ ] Comprehensive logging of recovery actions
- [ ] Test coverage for orphaned registry scenarios
- [ ] Test coverage for cross-server contamination
- [ ] Integration test: workflow-mcp indexing works
- [ ] No performance regression (<50ms overhead for existence check)

---

## Related Issues

- **Fixed**: Registry Sync Bug (commit `5a0c6462`) - Projects persist to PostgreSQL
- **Fixed**: Event Loop Test Bug (commit `16117eca`) - Cleanup in test fixtures
- **Related**: Cross-server project isolation (workflow-mcp vs codebase-mcp)

---

## Timeline

- **2025-10-19 11:30 AM**: Bug discovered during workflow-mcp indexing test
- **2025-10-19 11:45 AM**: Root cause identified (missing database validation)
- **2025-10-19 12:00 PM**: Bug report created
- **2025-10-19 12:15 PM**: Fix implementation started

---

## References

- **Code**: `src/database/auto_create.py:348-384`
- **Test Session**: `SESSION_HANDOFF_MCP_TESTING.md`
- **Related Bug**: `docs/bugs/project-resolution-secondary-call/`
- **PostgreSQL Docs**: [pg_database catalog](https://www.postgresql.org/docs/current/catalog-pg-database.html)
