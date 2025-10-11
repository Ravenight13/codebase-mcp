# Refactoring Plan for Codebase MCP Server

## Overview

This document details the file-by-file refactoring plan to transform the current monolithic codebase-mcp into a pure semantic code search MCP server with multi-project support.

---

## Current State Analysis

### Existing Tool Surface (13 tools)

**Search Tools (KEEP)**:
1. `index_repository` - Index code repository
2. `search_code` - Semantic code search

**Work Item Tools (REMOVE)**:
3. `create_work_item` - Create hierarchical work items
4. `list_work_items` - List work items with filters
5. `query_work_item` - Get work item with hierarchy
6. `update_work_item` - Update work item with optimistic locking

**Task Tools (REMOVE)**:
7. `create_task` - Create development task
8. `get_task` - Retrieve task by ID
9. `list_tasks` - List tasks with filters
10. `update_task` - Update task status

**Deployment Tools (REMOVE)**:
11. `record_deployment` - Record deployment event

**Vendor Tools (REMOVE)**:
12. `create_vendor` - Create vendor extractor
13. `query_vendor_status` - Query vendor status
14. `update_vendor_status` - Update vendor status

**Project Configuration Tools (REMOVE)**:
15. `get_project_configuration` - Get singleton configuration
16. `update_project_configuration` - Update configuration

### Database Schema

**Current Tables**:
```sql
-- KEEP (modify for multi-project)
repositories (id, name, path, indexed_at, ...)
code_chunks (id, repository_id, file_path, content, embedding, ...)

-- REMOVE
work_items (id, item_type, title, metadata, parent_id, ...)
work_item_dependencies (id, source_id, target_id, ...)
tasks (id, title, description, status, ...)
task_planning_references (id, task_id, file_path, ...)
deployments (id, deployed_at, metadata, ...)
deployment_vendors (id, deployment_id, vendor_id, ...)
deployment_work_items (id, deployment_id, work_item_id, ...)
vendors (id, name, status, version, metadata, ...)
project_configuration (id, active_context_type, ...)
```

---

## Refactoring Phases

### Phase 1: Branch and Baseline

**Objective**: Create feature branch and establish baseline tests

**Steps**:

1. **Create Feature Branch**
   ```bash
   git checkout -b 002-refactor-pure-search
   ```

2. **Run Baseline Tests**
   ```bash
   pytest tests/ --cov=src/codebase_mcp --cov-report=term
   # Capture baseline: test count, coverage %, passing tests
   ```

3. **Document Current State**
   - Count lines of code: `cloc src/ tests/`
   - List all MCP tools: `grep "@mcp.tool" src/ -r`
   - Export database schema: `pg_dump --schema-only`

**Acceptance Criteria**:
- Branch created: `002-refactor-pure-search`
- Baseline tests pass: 100%
- Baseline coverage documented: ~X%
- Current state documented in `docs/baseline-state.md`

**Commit**: `chore(refactor): create refactor branch and baseline`

---

### Phase 2: Remove Non-Search Database Tables

**Objective**: Remove all database tables except repositories and code_chunks

**Files to Modify**:

1. **`src/codebase_mcp/database/schema.sql`**
   - Remove: `work_items`, `work_item_dependencies`, `tasks`, `task_planning_references`, `deployments`, `deployment_vendors`, `deployment_work_items`, `vendors`, `project_configuration`
   - Keep: `repositories`, `code_chunks`
   - Add: `project_id` column to `repositories` and `code_chunks`

   **Before**:
   ```sql
   CREATE TABLE repositories (...);
   CREATE TABLE code_chunks (...);
   CREATE TABLE work_items (...);
   CREATE TABLE tasks (...);
   CREATE TABLE vendors (...);
   CREATE TABLE deployments (...);
   CREATE TABLE project_configuration (...);
   ```

   **After**:
   ```sql
   CREATE TABLE repositories (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       project_id TEXT NOT NULL,  -- NEW: project isolation
       name TEXT NOT NULL,
       path TEXT NOT NULL,
       indexed_at TIMESTAMP WITH TIME ZONE,
       created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
       UNIQUE(project_id, path)  -- NEW: unique per project
   );

   CREATE TABLE code_chunks (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       repository_id UUID REFERENCES repositories(id) ON DELETE CASCADE,
       project_id TEXT NOT NULL,  -- NEW: project isolation
       file_path TEXT NOT NULL,
       content TEXT NOT NULL,
       start_line INT NOT NULL,
       end_line INT NOT NULL,
       embedding vector(768) NOT NULL,  -- nomic-embed-text
       metadata JSONB,
       created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
   );

   -- Indexes for performance
   CREATE INDEX idx_repositories_project_id ON repositories(project_id);
   CREATE INDEX idx_code_chunks_project_id ON code_chunks(project_id);
   CREATE INDEX idx_code_chunks_repository_id ON code_chunks(repository_id);

   -- HNSW index for vector similarity (per project)
   CREATE INDEX idx_code_chunks_embedding
   ON code_chunks
   USING hnsw (embedding vector_cosine_ops)
   WITH (m = 16, ef_construction = 64);
   ```

2. **Create Migration Script** (`migrations/002_remove_non_search_tables.sql`)
   ```sql
   -- Drop tables in dependency order
   DROP TABLE IF EXISTS deployment_work_items;
   DROP TABLE IF EXISTS deployment_vendors;
   DROP TABLE IF EXISTS deployments;
   DROP TABLE IF EXISTS work_item_dependencies;
   DROP TABLE IF EXISTS work_items;
   DROP TABLE IF EXISTS task_planning_references;
   DROP TABLE IF EXISTS tasks;
   DROP TABLE IF EXISTS vendors;
   DROP TABLE IF EXISTS project_configuration;

   -- Add project_id to remaining tables
   ALTER TABLE repositories ADD COLUMN project_id TEXT;
   ALTER TABLE code_chunks ADD COLUMN project_id TEXT;

   -- Backfill project_id for existing data (default project)
   UPDATE repositories SET project_id = 'default' WHERE project_id IS NULL;
   UPDATE code_chunks SET project_id = 'default' WHERE project_id IS NULL;

   -- Make project_id NOT NULL
   ALTER TABLE repositories ALTER COLUMN project_id SET NOT NULL;
   ALTER TABLE code_chunks ALTER COLUMN project_id SET NOT NULL;

   -- Update unique constraint
   ALTER TABLE repositories DROP CONSTRAINT IF EXISTS repositories_path_key;
   ALTER TABLE repositories ADD CONSTRAINT repositories_project_path_key UNIQUE(project_id, path);

   -- Create indexes
   CREATE INDEX idx_repositories_project_id ON repositories(project_id);
   CREATE INDEX idx_code_chunks_project_id ON code_chunks(project_id);
   ```

**Acceptance Criteria**:
- Migration script created
- Schema file updated (only 2 tables remain)
- Migration tested on test database
- Documentation updated (schema diagram)

**Commit**: `refactor(db): remove non-search tables, add project_id`

---

### Phase 3: Remove Non-Search Tool Implementations

**Objective**: Remove all tool implementations except search

**Files to Delete**:

1. **`src/codebase_mcp/tools/work_items.py`**
   - Contains: `create_work_item`, `list_work_items`, `query_work_item`, `update_work_item`
   - Action: Delete entire file

2. **`src/codebase_mcp/tools/tasks.py`**
   - Contains: `create_task`, `get_task`, `list_tasks`, `update_task`
   - Action: Delete entire file

3. **`src/codebase_mcp/tools/deployments.py`**
   - Contains: `record_deployment`
   - Action: Delete entire file

4. **`src/codebase_mcp/tools/vendors.py`**
   - Contains: `create_vendor`, `query_vendor_status`, `update_vendor_status`
   - Action: Delete entire file

5. **`src/codebase_mcp/tools/project_config.py`**
   - Contains: `get_project_configuration`, `update_project_configuration`
   - Action: Delete entire file

**Files to Keep**:

1. **`src/codebase_mcp/tools/search.py`**
   - Contains: `index_repository`, `search_code`
   - Action: Modify to add `project_id` parameter

2. **`src/codebase_mcp/tools/__init__.py`**
   - Action: Update imports (remove deleted modules)

**Example Changes**:

**Before** (`src/codebase_mcp/tools/__init__.py`):
```python
from .search import index_repository, search_code
from .work_items import create_work_item, list_work_items, query_work_item, update_work_item
from .tasks import create_task, get_task, list_tasks, update_task
from .deployments import record_deployment
from .vendors import create_vendor, query_vendor_status, update_vendor_status
from .project_config import get_project_configuration, update_project_configuration

__all__ = [
    # Search
    "index_repository", "search_code",
    # Work Items
    "create_work_item", "list_work_items", "query_work_item", "update_work_item",
    # Tasks
    "create_task", "get_task", "list_tasks", "update_task",
    # Deployments
    "record_deployment",
    # Vendors
    "create_vendor", "query_vendor_status", "update_vendor_status",
    # Configuration
    "get_project_configuration", "update_project_configuration",
]
```

**After** (`src/codebase_mcp/tools/__init__.py`):
```python
from .search import index_repository, search_code

__all__ = [
    "index_repository",
    "search_code",
]
```

**Acceptance Criteria**:
- All non-search tool files deleted
- `__init__.py` updated (only search tools exported)
- Import errors fixed across codebase

**Commit**: `refactor(tools): remove non-search tool implementations`

---

### Phase 4: Remove Non-Search Database Operations

**Objective**: Remove database CRUD functions for non-search tables

**Files to Modify**:

1. **`src/codebase_mcp/database/operations.py`**
   - Remove functions: `create_work_item_db`, `list_work_items_db`, `query_work_item_db`, `update_work_item_db`, `create_task_db`, `get_task_db`, `list_tasks_db`, `update_task_db`, `record_deployment_db`, `create_vendor_db`, `query_vendor_status_db`, `update_vendor_status_db`, `get_project_configuration_db`, `update_project_configuration_db`
   - Keep functions: `index_repository_db`, `search_code_db`, database connection utilities

**Before** (partial):
```python
# Search operations
async def index_repository_db(pool, repo_path, force_reindex):
    ...

async def search_code_db(pool, query_embedding, filters, limit):
    ...

# Work item operations (REMOVE)
async def create_work_item_db(pool, item_type, title, metadata, parent_id):
    ...

async def list_work_items_db(pool, filters, limit, offset):
    ...

# Task operations (REMOVE)
async def create_task_db(pool, title, description, notes):
    ...

# ... etc
```

**After**:
```python
# Search operations only
async def index_repository_db(pool, repo_path, project_id, force_reindex):
    """Index repository with project isolation"""
    # Add project_id to INSERT statements
    ...

async def search_code_db(pool, query_embedding, project_id, filters, limit):
    """Search code within project"""
    # Add WHERE project_id = $1 to SELECT statements
    ...

# Connection utilities
async def get_db_pool(project_id: str) -> asyncpg.Pool:
    """Get connection pool for project database"""
    database_name = f"codebase_{project_id}"
    return await asyncpg.create_pool(
        host="localhost",
        port=5432,
        database=database_name,
        min_size=5,
        max_size=20
    )
```

**Acceptance Criteria**:
- All non-search database functions removed
- Search functions updated to include `project_id` parameter
- Database queries updated with `WHERE project_id = $1` filters

**Commit**: `refactor(db): remove non-search database operations`

---

### Phase 5: Update Server Tool Registration

**Objective**: Remove non-search tool registrations from MCP server

**Files to Modify**:

1. **`src/codebase_mcp/server.py`**
   - Remove tool registrations for non-search tools
   - Keep only: `index_repository`, `search_code`

**Before**:
```python
from fastmcp import FastMCP
from .tools import (
    index_repository, search_code,
    create_work_item, list_work_items, query_work_item, update_work_item,
    create_task, get_task, list_tasks, update_task,
    record_deployment,
    create_vendor, query_vendor_status, update_vendor_status,
    get_project_configuration, update_project_configuration,
)

mcp = FastMCP("codebase-mcp")

# Register all tools
mcp.tool()(index_repository)
mcp.tool()(search_code)
mcp.tool()(create_work_item)
mcp.tool()(list_work_items)
mcp.tool()(query_work_item)
mcp.tool()(update_work_item)
mcp.tool()(create_task)
mcp.tool()(get_task)
mcp.tool()(list_tasks)
mcp.tool()(update_task)
mcp.tool()(record_deployment)
mcp.tool()(create_vendor)
mcp.tool()(query_vendor_status)
mcp.tool()(update_vendor_status)
mcp.tool()(get_project_configuration)
mcp.tool()(update_project_configuration)
```

**After**:
```python
from fastmcp import FastMCP
from .tools import index_repository, search_code

mcp = FastMCP("codebase-mcp")

# Register search tools only
mcp.tool()(index_repository)
mcp.tool()(search_code)
```

**Acceptance Criteria**:
- Only 2 tools registered with MCP server
- Server starts successfully
- `mcp-inspector` validation passes

**Commit**: `refactor(server): register only search tools`

---

### Phase 6: Remove Non-Search Tests

**Objective**: Remove all test files for non-search functionality

**Files to Delete**:

1. **`tests/test_work_items.py`**
2. **`tests/test_tasks.py`**
3. **`tests/test_deployments.py`**
4. **`tests/test_vendors.py`**
5. **`tests/test_project_config.py`**

**Files to Keep**:

1. **`tests/test_search.py`** - Search tool tests
2. **`tests/test_indexing.py`** - Indexing pipeline tests
3. **`tests/test_embeddings.py`** - Ollama integration tests
4. **`tests/test_database.py`** - Database operations tests
5. **`tests/conftest.py`** - Shared fixtures

**Acceptance Criteria**:
- All non-search test files deleted
- Remaining tests pass: 100%
- Coverage remains >80%

**Commit**: `test(refactor): remove non-search tests`

---

### Phase 7: Add Multi-Project Support to Search Tools

**Objective**: Enhance search tools with multi-project capabilities

**Files to Modify**:

1. **`src/codebase_mcp/tools/search.py`**

**Changes**:

```python
from pydantic import BaseModel, Field

class IndexRepositoryParams(BaseModel):
    repo_path: str = Field(description="Absolute path to repository")
    project_id: str = Field(description="Project ID for isolation")
    force_reindex: bool = Field(default=False, description="Force re-indexing")

class SearchCodeParams(BaseModel):
    query: str = Field(description="Natural language search query")
    project_id: str | None = Field(default=None, description="Project ID (uses active project if None)")
    file_type: str | None = Field(default=None, description="File type filter (e.g., 'py', 'js')")
    directory: str | None = Field(default=None, description="Directory filter")
    limit: int = Field(default=10, ge=1, le=50, description="Max results")

@mcp.tool()
async def index_repository(params: IndexRepositoryParams) -> dict:
    """Index a code repository for semantic search"""
    # Get project-specific database pool
    pool = await get_db_pool(params.project_id)

    try:
        result = await index_repository_db(
            pool=pool,
            repo_path=params.repo_path,
            project_id=params.project_id,
            force_reindex=params.force_reindex
        )
        return result
    finally:
        await pool.close()

@mcp.tool()
async def search_code(params: SearchCodeParams) -> dict:
    """Search code using semantic similarity"""
    # Resolve project_id (active project or explicit)
    project_id = params.project_id or await get_active_project_id()

    # Get project-specific database pool
    pool = await get_db_pool(project_id)

    try:
        # Generate query embedding
        query_embedding = await generate_embedding(params.query)

        # Search database
        results = await search_code_db(
            pool=pool,
            query_embedding=query_embedding,
            project_id=project_id,
            filters={
                "file_type": params.file_type,
                "directory": params.directory,
            },
            limit=params.limit
        )

        return {
            "results": results,
            "project_id": project_id,
            "total_count": len(results),
            "latency_ms": ...  # measure actual latency
        }
    finally:
        await pool.close()
```

2. **`src/codebase_mcp/utils/project_context.py`** (NEW)

```python
import aiohttp
from typing import Optional

async def get_active_project_id() -> Optional[str]:
    """
    Query workflow-mcp for active project ID.
    Returns None if workflow-mcp unavailable.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://localhost:3000/mcp/workflow-mcp/get_active_project"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("project_id")
                return None
    except Exception:
        # workflow-mcp not available, explicit project_id required
        return None
```

**Acceptance Criteria**:
- `project_id` parameter added to both tools
- `get_active_project_id()` helper implemented
- Search falls back to explicit `project_id` if workflow-mcp unavailable
- Tests validate multi-project isolation (no cross-contamination)

**Commit**: `feat(search): add multi-project support with project_id parameter`

---

### Phase 8: Update Database Connection Management

**Objective**: One database per project, dynamic connection pooling

**Files to Modify**:

1. **`src/codebase_mcp/database/connection.py`**

**Before**:
```python
# Single global pool
_pool: Optional[asyncpg.Pool] = None

async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            host="localhost",
            database="codebase_mcp",  # Single database
            ...
        )
    return _pool
```

**After**:
```python
# Per-project pools
_pools: dict[str, asyncpg.Pool] = {}

async def get_db_pool(project_id: str) -> asyncpg.Pool:
    """Get or create connection pool for project database"""
    if project_id not in _pools:
        database_name = f"codebase_{project_id}"
        _pools[project_id] = await asyncpg.create_pool(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=database_name,
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", ""),
            min_size=5,
            max_size=20,
        )
    return _pools[project_id]

async def close_all_pools():
    """Close all database connection pools"""
    for pool in _pools.values():
        await pool.close()
    _pools.clear()
```

**Acceptance Criteria**:
- One connection pool per project
- Pools created lazily on first access
- Cleanup function closes all pools
- Environment variables for database configuration

**Commit**: `feat(db): implement per-project database connection pools`

---

### Phase 9: Remove Non-Search Documentation

**Objective**: Update documentation to reflect search-only scope

**Files to Modify**:

1. **`README.md`**
   - Remove sections: Work Items, Tasks, Vendors, Deployments
   - Keep sections: Semantic Search, Indexing, Multi-Project Support
   - Update tool list: Only 2 tools

2. **`docs/api.md`**
   - Remove tool documentation for non-search tools
   - Update: Only document `index_repository` and `search_code`

3. **`docs/architecture.md`**
   - Update architecture diagram (remove non-search components)
   - Update database schema diagram (only 2 tables)

4. **`CHANGELOG.md`**
   - Add entry for v2.0.0: "BREAKING CHANGE: Removed work items, tasks, vendors, deployments. Now pure semantic search MCP."

**Acceptance Criteria**:
- All documentation references to removed features deleted
- README accurately describes search-only functionality
- API docs list only 2 tools
- Changelog documents breaking change

**Commit**: `docs(refactor): update documentation for search-only scope`

---

### Phase 10: Create Migration Guide

**Objective**: Help users migrate from monolithic to search-only codebase-mcp

**Files to Create**:

1. **`docs/migration-guide.md`**

```markdown
# Migration Guide: Monolithic → Search-Only Codebase MCP

## Overview

Codebase MCP v2.0.0 is a pure semantic code search server. Work item tracking, task management, vendor tracking, and deployment recording have been moved to **workflow-mcp**.

## Breaking Changes

### Removed Tools
- `create_work_item`, `list_work_items`, `query_work_item`, `update_work_item` → Use `workflow-mcp`
- `create_task`, `get_task`, `list_tasks`, `update_task` → Use `workflow-mcp`
- `record_deployment` → Use `workflow-mcp`
- `create_vendor`, `query_vendor_status`, `update_vendor_status` → Use `workflow-mcp`
- `get_project_configuration`, `update_project_configuration` → Use `workflow-mcp`

### Retained Tools (with changes)
- `index_repository(repo_path, project_id, force_reindex)` - Added `project_id` parameter
- `search_code(query, project_id, file_type, directory, limit)` - Added `project_id` parameter

## Migration Steps

### 1. Install workflow-mcp
```bash
pip install workflow-mcp
# Configure in MCP client settings
```

### 2. Update Tool Calls
```python
# OLD (codebase-mcp v1.x)
result = await create_work_item(title="Feature X", item_type="task", ...)

# NEW (workflow-mcp v1.x)
result = await workflow_mcp.create_work_item(title="Feature X", item_type="task", ...)
```

### 3. Add project_id to Search Calls
```python
# OLD
result = await search_code(query="authentication")

# NEW (explicit project_id)
result = await search_code(query="authentication", project_id="my-project")

# NEW (uses active project from workflow-mcp)
result = await search_code(query="authentication", project_id=None)
```

### 4. Migrate Database
```bash
# Backup existing database
pg_dump codebase_mcp > backup.sql

# Run migration script
psql codebase_mcp < migrations/002_remove_non_search_tables.sql

# Verify migration
psql codebase_mcp -c "\dt"  # Should show only repositories, code_chunks
```

## Configuration Changes

### Before (v1.x)
```yaml
mcp_servers:
  codebase-mcp:
    command: codebase-mcp
    args: []
    env:
      DATABASE_URL: postgresql://localhost/codebase_mcp
```

### After (v2.x)
```yaml
mcp_servers:
  codebase-mcp:
    command: codebase-mcp
    args: []
    env:
      POSTGRES_HOST: localhost
      POSTGRES_PORT: 5432
      # No DATABASE_URL (per-project databases)

  workflow-mcp:  # NEW
    command: workflow-mcp
    args: []
    env:
      DATABASE_URL: postgresql://localhost/workflow_mcp
```

## FAQ

**Q: Can I still use codebase-mcp standalone?**
A: Yes, but you must provide `project_id` explicitly. Workflow-mcp integration is optional.

**Q: Do I need to re-index my code?**
A: Yes, if migrating from v1.x. Re-index with `project_id` parameter.

**Q: What happens to my existing work items/tasks data?**
A: It's preserved in the database backup. Restore to workflow-mcp's database schema (see workflow-mcp migration docs).
```

**Acceptance Criteria**:
- Migration guide created
- Clear step-by-step instructions
- Tool mapping table (old → new)
- Database migration script provided

**Commit**: `docs(migration): add migration guide for v2.0.0`

---

## Summary of Changes

### Removed Files (11)
1. `src/codebase_mcp/tools/work_items.py`
2. `src/codebase_mcp/tools/tasks.py`
3. `src/codebase_mcp/tools/deployments.py`
4. `src/codebase_mcp/tools/vendors.py`
5. `src/codebase_mcp/tools/project_config.py`
6. `tests/test_work_items.py`
7. `tests/test_tasks.py`
8. `tests/test_deployments.py`
9. `tests/test_vendors.py`
10. `tests/test_project_config.py`
11. (Database tables removed via migration)

### Modified Files (8)
1. `src/codebase_mcp/server.py` - Remove tool registrations
2. `src/codebase_mcp/tools/__init__.py` - Remove imports
3. `src/codebase_mcp/tools/search.py` - Add `project_id` parameter
4. `src/codebase_mcp/database/schema.sql` - Remove tables, add `project_id`
5. `src/codebase_mcp/database/operations.py` - Remove functions, add project filters
6. `src/codebase_mcp/database/connection.py` - Per-project pools
7. `README.md` - Update documentation
8. `docs/api.md` - Update tool documentation

### Created Files (3)
1. `src/codebase_mcp/utils/project_context.py` - workflow-mcp integration
2. `migrations/002_remove_non_search_tables.sql` - Database migration
3. `docs/migration-guide.md` - User migration guide

### Lines of Code Reduction (Estimated)
- **Before**: ~4,500 lines (all features)
- **After**: ~1,800 lines (search only)
- **Reduction**: 60% code reduction

### Tool Surface Reduction
- **Before**: 16 tools
- **After**: 2 tools
- **Reduction**: 87.5% tool reduction

---

## Risk Mitigation

### Risk 1: Breaking Changes for Existing Users
**Mitigation**:
- Semantic versioning: v2.0.0 (major version bump)
- Migration guide with clear instructions
- Database backup instructions before migration

### Risk 2: Data Loss During Migration
**Mitigation**:
- Migration script tested on test database first
- Backup instructions in migration guide
- Non-destructive migration (adds columns before dropping tables)

### Risk 3: workflow-mcp Integration Failures
**Mitigation**:
- Fallback to explicit `project_id` if workflow-mcp unavailable
- Integration tests with mock workflow-mcp
- Clear error messages when integration fails

### Risk 4: Performance Regression with Multi-Project
**Mitigation**:
- Per-project indexes (no cross-project query overhead)
- Connection pooling per project (isolated resources)
- Performance benchmarks before/after refactor

---

## Post-Refactor Validation Checklist

- [ ] All tests pass (100%)
- [ ] Coverage >80%
- [ ] mypy --strict passes (0 errors)
- [ ] mcp-inspector validation passes
- [ ] Performance benchmarks meet targets (<500ms search)
- [ ] Migration script tested on test database
- [ ] Documentation updated (README, API docs, architecture)
- [ ] Migration guide reviewed and tested
- [ ] CHANGELOG updated with breaking changes
- [ ] Version bumped to 2.0.0

---

## Timeline Estimate

- **Phase 1**: 1 hour (branch, baseline)
- **Phase 2**: 2 hours (database schema)
- **Phase 3**: 1 hour (delete tool files)
- **Phase 4**: 2 hours (database operations)
- **Phase 5**: 1 hour (server registration)
- **Phase 6**: 1 hour (delete test files)
- **Phase 7**: 3 hours (multi-project support)
- **Phase 8**: 2 hours (connection pooling)
- **Phase 9**: 2 hours (documentation)
- **Phase 10**: 2 hours (migration guide)

**Total**: ~17 hours (2-3 days with testing and validation)
