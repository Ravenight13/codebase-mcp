# Reviewer 2: Registry Synchronization Analysis

## Executive Summary

**Finding**: There is a critical **registry synchronization gap** between the in-memory registry (`src/database/auto_create.py`) and the persistent registry database (`codebase_mcp_registry.projects` table). Auto-created projects are **NEVER written to the persistent database**, causing Tier 1 lookups to fail consistently.

**Confidence Level**: 95% - The code evidence is clear and unambiguous.

## Registry Architecture Analysis

### 1. Two Distinct Registry Systems

#### In-Memory Registry (`src/database/auto_create.py`)
- **Location**: Lines 89-168 define `ProjectRegistry` class
- **Scope**: Process-local, singleton pattern
- **Storage**: Python dicts `_projects_by_id` and `_projects_by_name`
- **Persistence**: **NONE** - Lost on server restart
- **Used By**: Tier 2 resolution (`get_or_create_project_from_config`)

#### Persistent Registry (`codebase_mcp_registry.projects` table)
- **Location**: PostgreSQL database table
- **Scope**: Cross-process, persistent
- **Storage**: Database records with proper ACID guarantees
- **Persistence**: Survives server restarts
- **Used By**: Tier 1 resolution (lines 510-537 in `session.py`)

### 2. The Synchronization Gap

#### Evidence from `auto_create.py`:

```python
# Line 385: Add to in-memory registry
registry.add(project)

# Lines 387-400: Update config file with project ID
if config["project"]["id"] != project_id:
    logger.info(f"Updating config with project ID: {project_id}", ...)
    config["project"]["id"] = project_id
    write_config(config_path, config)
```

**Critical Finding**: After creating a project database and adding to in-memory registry, the code **NEVER** inserts a record into the persistent `projects` table.

#### Evidence from `session.py` Tier 1 Resolution:

```python
# Lines 510-537: Tier 1 queries ONLY the persistent registry
registry_pool = await _initialize_registry_pool()
async with registry_pool.acquire() as conn:
    row = await conn.fetchrow("""
        SELECT id, database_name
        FROM projects
        WHERE id = $1 OR name = $1
        LIMIT 1
    """, explicit_id)
```

This query will **ALWAYS fail** for auto-created projects because they don't exist in the `projects` table.

### 3. Tier 2 Resolution Issue

When Tier 1 fails to find the project in the persistent registry, it falls through to Tier 2 (lines 554-574 in `session.py`):

```python
# Line 399: Import auto_create module
from src.database.auto_create import get_or_create_project_from_config

# Line 401-404: Call get_or_create_project_from_config
project = await get_or_create_project_from_config(
    config_path=config_path,
    registry=None  # Uses singleton registry
)
```

#### The Secondary Call Problem

On the **second call** with the same project:
1. Project already exists in in-memory registry (from first call)
2. `get_or_create_project_from_config` finds it in memory (line 311 in `auto_create.py`)
3. Returns the in-memory project successfully
4. BUT: Still not in persistent registry for future Tier 1 lookups

### 4. Singleton Pattern Analysis

The singleton pattern IS correctly implemented:

```python
# Lines 154-167 in auto_create.py
_registry_instance: ProjectRegistry | None = None

def get_registry() -> ProjectRegistry:
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ProjectRegistry()
    return _registry_instance
```

**Verification**: The singleton works correctly within the process. The issue is NOT with the singleton pattern but with the lack of persistence.

## Race Conditions

No race conditions detected. The issue is deterministic:
1. First call: Creates project in memory only
2. Second call: Finds project in memory
3. Both calls: Project never written to persistent registry

## Code Evidence

### Missing INSERT Statement

The `auto_create.py` module **lacks any SQL INSERT statement** to the `projects` table. Compare with `registry.py` which properly inserts:

```python
# registry.py lines 315-326
row = await conn.fetchrow("""
    INSERT INTO projects (id, name, description, database_name, metadata)
    VALUES ($1, $2, $3, $4, $5)
    RETURNING id, name, description, database_name, created_at, updated_at, metadata
""", project_id, name, description, database_name, metadata or {})
```

No equivalent code exists in `auto_create.py`.

### Database Creation Without Registry Record

`auto_create.py` line 361 creates the database:
```python
await create_project_database(project_name, project_id)
```

But this only creates the physical database, not the registry record.

## Recommendations

### Option 1: Write to Persistent Registry (RECOMMENDED)

Add code after line 385 in `auto_create.py`:

```python
# Add to in-memory registry
registry.add(project)

# NEW: Also write to persistent registry
try:
    from src.database.session import _initialize_registry_pool
    registry_pool = await _initialize_registry_pool()
    async with registry_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO projects (id, name, description, database_name, metadata)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (id) DO UPDATE SET
                updated_at = NOW()
        """, project.project_id, project.name, project.description,
            project.database_name, {})
    logger.info(f"✓ Project synced to persistent registry: {project.name}")
except Exception as e:
    logger.error(f"Failed to sync to persistent registry: {e}")
    # Continue anyway - in-memory registry still works
```

### Option 2: Use ProjectRegistry Service

Replace the entire in-memory registry with the proper `ProjectRegistry` service from `registry.py`:

```python
from src.database.registry import ProjectRegistry
from src.database.provisioning import create_pool

# In get_or_create_project_from_config
registry_pool = await create_pool("codebase_mcp_registry")
registry_service = ProjectRegistry(registry_pool)

# Use registry_service.get_project_by_name() instead of in-memory lookup
# Use registry_service.create_project() instead of manual creation
```

### Option 3: Enhanced In-Memory Lookup (NOT RECOMMENDED)

Make Tier 1 check both persistent AND in-memory registries. This is complex and doesn't solve the persistence problem.

## Impact Analysis

### Current Behavior
- Projects auto-created via config files work within the same server session
- Projects are lost on server restart
- Tier 1 resolution always fails for auto-created projects
- Creates "phantom" databases without registry records

### After Fix
- Projects persist across server restarts
- Tier 1 resolution succeeds on subsequent calls
- Registry remains the single source of truth
- No phantom databases

## Severity

**CRITICAL** - This bug creates data inconsistency between the registry and actual databases, leading to:
1. Orphaned databases without registry records
2. Failed project resolution after server restarts
3. Confusion when the same project behaves differently across sessions

## Testing Recommendations

1. **Unit Test**: Mock the registry pool and verify INSERT is called
2. **Integration Test**: Create project, restart server, verify project still resolves
3. **End-to-End Test**: Use MCP client to create project via config, verify it appears in `SELECT * FROM projects`

## Conclusion

The dual-registry problem is caused by a **missing synchronization step** where auto-created projects are added to the in-memory registry but never written to the persistent database. This is a straightforward bug with a clear fix: add an INSERT statement to sync the project to the persistent registry after successful creation.

**Recommended Fix**: Option 1 - Add INSERT to persistent registry in `auto_create.py` after line 385.