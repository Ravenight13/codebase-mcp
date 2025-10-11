# Implementation Phases for Codebase MCP Refactor

## Overview

This document provides a phase-by-phase breakdown of the refactoring effort to transform codebase-mcp into a pure semantic code search MCP with multi-project support. Each phase has clear objectives, acceptance criteria, git strategy, and testing requirements.

---

## Development Approach

**Strategy**: Option B Sequential
- workflow-mcp core exists first (prerequisite)
- Refactor codebase-mcp to integrate with workflow-mcp
- Independent deployment and testing

**Git Strategy**:
- **Branch**: `002-refactor-pure-search`
- **Commit Approach**: Micro-commits after each phase
- **Commit Format**: Conventional Commits (`type(scope): description`)
- **Working State**: All tests pass at every commit

**Testing Strategy**:
- **Unit Tests**: Test individual functions in isolation
- **Integration Tests**: Test database operations, Ollama interactions
- **Protocol Tests**: Validate MCP compliance via mcp-inspector
- **Performance Tests**: Benchmark search latency, indexing throughput
- **Multi-Project Tests**: Validate isolation (no cross-contamination)

---

## Phase 0: Prerequisites and Planning

### Objective
Ensure workflow-mcp is deployed and validate planning artifacts

### Tasks

1. **Verify workflow-mcp Deployment**
   ```bash
   # Test workflow-mcp is running
   curl http://localhost:3000/mcp/workflow-mcp/health
   # Expected: {"status": "ok", "version": "1.0.0"}
   ```

2. **Validate Planning Artifacts**
   - ✅ README.md (this document's parent)
   - ✅ constitution.md
   - ✅ user-stories.md
   - ✅ specify-prompt.txt
   - ✅ tech-stack.md
   - ✅ refactoring-plan.md
   - ✅ implementation-phases.md (this document)

3. **Review Current Codebase State**
   ```bash
   # Count lines of code
   cloc src/ tests/

   # List all MCP tools
   grep "@mcp.tool" src/ -r

   # Run baseline tests
   pytest tests/ -v --cov=src/codebase_mcp
   ```

### Acceptance Criteria
- [ ] workflow-mcp is deployed and responding
- [ ] All planning documents reviewed and approved
- [ ] Baseline metrics captured (LOC, test count, coverage)
- [ ] Feature branch ready: `002-refactor-pure-search`

### Git Strategy
- No commits in this phase (preparation only)

### Time Estimate
- **Duration**: 1 hour
- **Dependencies**: workflow-mcp deployment complete

---

## Phase 1: Create Feature Branch and Baseline

### Objective
Establish refactor branch and document current state

### Tasks

1. **Create Feature Branch**
   ```bash
   git checkout main
   git pull origin main
   git checkout -b 002-refactor-pure-search
   ```

2. **Capture Baseline Metrics**
   ```bash
   # Lines of code
   cloc src/ tests/ > docs/baseline/loc-before.txt

   # Test results
   pytest tests/ -v --cov=src/codebase_mcp --cov-report=html > docs/baseline/tests-before.txt

   # Database schema
   pg_dump --schema-only codebase_mcp > docs/baseline/schema-before.sql

   # Tool list
   grep "@mcp.tool" src/ -r > docs/baseline/tools-before.txt
   ```

3. **Document Baseline State**
   Create `docs/baseline/baseline-state.md`:
   ```markdown
   # Baseline State (Before Refactor)

   **Date**: 2025-10-11
   **Branch**: 002-refactor-pure-search
   **Commit**: [current commit hash]

   ## Metrics
   - Lines of Code: X
   - Test Count: Y
   - Test Coverage: Z%
   - MCP Tools: 16

   ## Tool Surface
   - Search: index_repository, search_code
   - Work Items: create_work_item, list_work_items, query_work_item, update_work_item
   - Tasks: create_task, get_task, list_tasks, update_task
   - Deployments: record_deployment
   - Vendors: create_vendor, query_vendor_status, update_vendor_status
   - Configuration: get_project_configuration, update_project_configuration

   ## Database Schema
   - Tables: repositories, code_chunks, work_items, tasks, vendors, deployments, project_configuration
   ```

### Acceptance Criteria
- [ ] Branch created: `002-refactor-pure-search`
- [ ] Baseline metrics captured in `docs/baseline/`
- [ ] Baseline state documented in `baseline-state.md`
- [ ] All baseline tests pass (100%)

### Git Strategy
```bash
# After documenting baseline
git add docs/baseline/
git commit -m "chore(refactor): establish baseline for pure-search refactor"
```

### Testing
- Run existing test suite to ensure clean starting state
- Expected: 100% tests passing

### Time Estimate
- **Duration**: 1 hour
- **Dependencies**: None

---

## Phase 2: Database Schema Refactoring

### Objective
Remove non-search database tables and add multi-project support

### Tasks

1. **Create Migration Script**
   Create `migrations/002_remove_non_search_tables.sql`:
   ```sql
   -- Backup warning
   -- Run: pg_dump codebase_mcp > backup-before-002.sql

   -- Drop non-search tables
   DROP TABLE IF EXISTS deployment_work_items CASCADE;
   DROP TABLE IF EXISTS deployment_vendors CASCADE;
   DROP TABLE IF EXISTS deployments CASCADE;
   DROP TABLE IF EXISTS work_item_dependencies CASCADE;
   DROP TABLE IF EXISTS work_items CASCADE;
   DROP TABLE IF EXISTS task_planning_references CASCADE;
   DROP TABLE IF EXISTS tasks CASCADE;
   DROP TABLE IF EXISTS vendors CASCADE;
   DROP TABLE IF EXISTS project_configuration CASCADE;

   -- Add project_id to remaining tables
   ALTER TABLE repositories ADD COLUMN project_id TEXT;
   ALTER TABLE code_chunks ADD COLUMN project_id TEXT;

   -- Backfill project_id (default project for existing data)
   UPDATE repositories SET project_id = 'default' WHERE project_id IS NULL;
   UPDATE code_chunks SET project_id = 'default' WHERE project_id IS NULL;

   -- Make project_id NOT NULL
   ALTER TABLE repositories ALTER COLUMN project_id SET NOT NULL;
   ALTER TABLE code_chunks ALTER COLUMN project_id SET NOT NULL;

   -- Update unique constraints
   ALTER TABLE repositories DROP CONSTRAINT IF EXISTS repositories_path_key;
   ALTER TABLE repositories ADD CONSTRAINT repositories_project_path_key UNIQUE(project_id, path);

   -- Create indexes for performance
   CREATE INDEX IF NOT EXISTS idx_repositories_project_id ON repositories(project_id);
   CREATE INDEX IF NOT EXISTS idx_code_chunks_project_id ON code_chunks(project_id);

   -- Verify migration
   SELECT 'Migration 002 complete' AS status;
   ```

2. **Update Schema File**
   Update `src/codebase_mcp/database/schema.sql`:
   - Remove all non-search table definitions
   - Add `project_id` to repositories and code_chunks
   - Update indexes and constraints

3. **Test Migration on Test Database**
   ```bash
   # Create test database
   createdb codebase_mcp_test
   psql codebase_mcp_test < src/codebase_mcp/database/schema.sql

   # Populate with test data
   psql codebase_mcp_test < tests/fixtures/test_data.sql

   # Run migration
   psql codebase_mcp_test < migrations/002_remove_non_search_tables.sql

   # Verify result
   psql codebase_mcp_test -c "\dt"
   # Expected: Only repositories and code_chunks
   ```

### Acceptance Criteria
- [ ] Migration script created and tested
- [ ] Schema file updated (only 2 tables: repositories, code_chunks)
- [ ] Migration tested on test database
- [ ] No data loss (test data preserved in remaining tables)
- [ ] Indexes created for performance

### Git Strategy
```bash
git add migrations/002_remove_non_search_tables.sql
git add src/codebase_mcp/database/schema.sql
git commit -m "refactor(db): remove non-search tables, add project_id for multi-project support"
```

### Testing
```bash
# Test migration on fresh database
pytest tests/test_migrations.py::test_migration_002

# Test schema integrity
pytest tests/test_database.py::test_schema_integrity
```

### Time Estimate
- **Duration**: 2-3 hours
- **Dependencies**: Phase 1 complete

---

## Phase 3: Remove Non-Search Tool Implementations

### Objective
Delete all tool implementations except search

### Tasks

1. **Delete Tool Files**
   ```bash
   # Remove work item tools
   git rm src/codebase_mcp/tools/work_items.py

   # Remove task tools
   git rm src/codebase_mcp/tools/tasks.py

   # Remove deployment tools
   git rm src/codebase_mcp/tools/deployments.py

   # Remove vendor tools
   git rm src/codebase_mcp/tools/vendors.py

   # Remove project configuration tools
   git rm src/codebase_mcp/tools/project_config.py
   ```

2. **Update Tool Module Initialization**
   Edit `src/codebase_mcp/tools/__init__.py`:
   ```python
   # Remove all imports except search
   from .search import index_repository, search_code

   __all__ = [
       "index_repository",
       "search_code",
   ]
   ```

3. **Fix Import Errors Across Codebase**
   ```bash
   # Find all import references to removed tools
   grep -r "from .tools import" src/

   # Update imports in server.py and other files
   ```

### Acceptance Criteria
- [ ] 5 tool files deleted
- [ ] `tools/__init__.py` updated (only search tools exported)
- [ ] No import errors in codebase
- [ ] Server starts successfully (even if tools not registered yet)

### Git Strategy
```bash
git add src/codebase_mcp/tools/
git commit -m "refactor(tools): remove non-search tool implementations"
```

### Testing
```bash
# Test imports
python -c "from src.codebase_mcp.tools import index_repository, search_code"

# Expected: No ImportError
```

### Time Estimate
- **Duration**: 1 hour
- **Dependencies**: Phase 2 complete

---

## Phase 4: Remove Non-Search Database Operations

### Objective
Remove CRUD functions for non-search tables

### Tasks

1. **Edit Database Operations File**
   Edit `src/codebase_mcp/database/operations.py`:
   - Delete: `create_work_item_db`, `list_work_items_db`, `query_work_item_db`, `update_work_item_db`
   - Delete: `create_task_db`, `get_task_db`, `list_tasks_db`, `update_task_db`
   - Delete: `record_deployment_db`
   - Delete: `create_vendor_db`, `query_vendor_status_db`, `update_vendor_status_db`
   - Delete: `get_project_configuration_db`, `update_project_configuration_db`
   - Keep: `index_repository_db`, `search_code_db`, connection utilities

2. **Update Search Functions for Multi-Project**
   ```python
   async def index_repository_db(
       pool: asyncpg.Pool,
       repo_path: str,
       project_id: str,  # NEW
       force_reindex: bool
   ) -> dict:
       """Index repository with project isolation"""
       # Add project_id to INSERT statements
       async with pool.acquire() as conn:
           # Check if already indexed
           existing = await conn.fetchrow(
               "SELECT id FROM repositories WHERE project_id = $1 AND path = $2",
               project_id, repo_path
           )
           if existing and not force_reindex:
               return {"status": "skipped", "message": "Already indexed"}

           # Index repository...
           # INSERT INTO repositories (project_id, path, ...) VALUES ($1, $2, ...)
           # INSERT INTO code_chunks (project_id, repository_id, ...) VALUES (...)

   async def search_code_db(
       pool: asyncpg.Pool,
       query_embedding: list[float],
       project_id: str,  # NEW
       filters: dict,
       limit: int
   ) -> list[dict]:
       """Search code within project"""
       async with pool.acquire() as conn:
           # Add WHERE project_id = $1 to SELECT
           results = await conn.fetch(
               """
               SELECT
                   file_path,
                   content,
                   start_line,
                   end_line,
                   1 - (embedding <=> $2) AS similarity
               FROM code_chunks
               WHERE project_id = $1
               ORDER BY embedding <=> $2
               LIMIT $3
               """,
               project_id, query_embedding, limit
           )
           return [dict(row) for row in results]
   ```

### Acceptance Criteria
- [ ] All non-search database functions removed
- [ ] Search functions updated with `project_id` parameter
- [ ] Database queries include `WHERE project_id = $X` filters
- [ ] No unused imports or dead code

### Git Strategy
```bash
git add src/codebase_mcp/database/operations.py
git commit -m "refactor(db): remove non-search operations, add project_id filters"
```

### Testing
```bash
# Test search database operations
pytest tests/test_database.py::test_index_repository_with_project_id
pytest tests/test_database.py::test_search_code_with_project_id
pytest tests/test_database.py::test_multi_project_isolation
```

### Time Estimate
- **Duration**: 2 hours
- **Dependencies**: Phase 3 complete

---

## Phase 5: Update MCP Server Tool Registration

### Objective
Register only search tools with MCP server

### Tasks

1. **Update Server File**
   Edit `src/codebase_mcp/server.py`:
   ```python
   from fastmcp import FastMCP
   from .tools import index_repository, search_code

   mcp = FastMCP("codebase-mcp")

   # Register search tools only
   mcp.tool()(index_repository)
   mcp.tool()(search_code)

   if __name__ == "__main__":
       mcp.run()
   ```

2. **Test Server Startup**
   ```bash
   # Start server
   python -m codebase_mcp.server

   # In another terminal, test with mcp-inspector
   mcp-inspector http://localhost:8000
   ```

3. **Validate MCP Protocol Compliance**
   ```bash
   # List available tools
   mcp-inspector http://localhost:8000 --list-tools

   # Expected output:
   # Tools:
   #   - index_repository
   #   - search_code
   ```

### Acceptance Criteria
- [ ] Only 2 tools registered with MCP server
- [ ] Server starts without errors
- [ ] mcp-inspector validation passes
- [ ] Tool schemas are valid (Pydantic → JSON Schema)

### Git Strategy
```bash
git add src/codebase_mcp/server.py
git commit -m "refactor(server): register only search tools (index_repository, search_code)"
```

### Testing
```bash
# Test server startup
pytest tests/test_server.py::test_server_startup

# Test tool registration
pytest tests/test_server.py::test_tool_list

# Test MCP protocol compliance
pytest tests/test_protocol.py::test_mcp_compliance
```

### Time Estimate
- **Duration**: 1 hour
- **Dependencies**: Phase 4 complete

---

## Phase 6: Remove Non-Search Tests

### Objective
Delete test files for removed functionality

### Tasks

1. **Delete Test Files**
   ```bash
   git rm tests/test_work_items.py
   git rm tests/test_tasks.py
   git rm tests/test_deployments.py
   git rm tests/test_vendors.py
   git rm tests/test_project_config.py
   ```

2. **Update Test Fixtures**
   Edit `tests/conftest.py`:
   - Remove fixtures for non-search features
   - Keep: `db_pool`, `test_repo_path`, `ollama_mock`

3. **Run Remaining Tests**
   ```bash
   pytest tests/ -v --cov=src/codebase_mcp
   ```

### Acceptance Criteria
- [ ] 5 test files deleted
- [ ] Remaining tests pass (100%)
- [ ] Coverage remains >80%
- [ ] No unused fixtures in `conftest.py`

### Git Strategy
```bash
git add tests/
git commit -m "test(refactor): remove tests for non-search functionality"
```

### Testing
```bash
# Run all remaining tests
pytest tests/ -v

# Check coverage
pytest tests/ --cov=src/codebase_mcp --cov-report=term
# Expected: >80% coverage
```

### Time Estimate
- **Duration**: 1 hour
- **Dependencies**: Phase 5 complete

---

## Phase 7: Add Multi-Project Support to Search Tools

### Objective
Implement project_id parameter and workflow-mcp integration

### Tasks

1. **Create Project Context Module**
   Create `src/codebase_mcp/utils/project_context.py`:
   ```python
   import aiohttp
   import os
   from typing import Optional

   async def get_active_project_id() -> Optional[str]:
       """
       Query workflow-mcp for active project ID.
       Returns None if workflow-mcp unavailable.
       """
       workflow_mcp_url = os.getenv(
           "WORKFLOW_MCP_URL",
           "http://localhost:3000/mcp/workflow-mcp"
       )

       try:
           async with aiohttp.ClientSession() as session:
               async with session.get(
                   f"{workflow_mcp_url}/get_active_project",
                   timeout=aiohttp.ClientTimeout(total=2.0)
               ) as response:
                   if response.status == 200:
                       data = await response.json()
                       return data.get("project_id")
                   return None
       except Exception as e:
           # workflow-mcp not available, log warning
           import logging
           logging.warning(f"Failed to get active project from workflow-mcp: {e}")
           return None
   ```

2. **Update Search Tool Parameters**
   Edit `src/codebase_mcp/tools/search.py`:
   ```python
   from pydantic import BaseModel, Field
   from ..utils.project_context import get_active_project_id

   class IndexRepositoryParams(BaseModel):
       repo_path: str = Field(description="Absolute path to repository")
       project_id: str = Field(description="Project ID for isolation")
       force_reindex: bool = Field(default=False)

   class SearchCodeParams(BaseModel):
       query: str = Field(description="Natural language search query")
       project_id: str | None = Field(
           default=None,
           description="Project ID (uses active project if None)"
       )
       file_type: str | None = Field(default=None, description="File type filter")
       directory: str | None = Field(default=None, description="Directory filter")
       limit: int = Field(default=10, ge=1, le=50)

   @mcp.tool()
   async def index_repository(params: IndexRepositoryParams) -> dict:
       """Index a code repository for semantic search"""
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
       # Resolve project_id
       project_id = params.project_id or await get_active_project_id()
       if not project_id:
           raise ValueError(
               "project_id required when workflow-mcp is unavailable"
           )

       # Get project database pool
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
           }
       finally:
           await pool.close()
   ```

3. **Write Multi-Project Tests**
   Create `tests/test_multi_project.py`:
   ```python
   import pytest
   import pytest_asyncio

   @pytest.mark.asyncio
   async def test_multi_project_isolation(db_pool_project_a, db_pool_project_b):
       """Test that projects are isolated (no cross-contamination)"""
       # Index same file in two projects
       await index_repository_db(db_pool_project_a, "/repo", "project-a", False)
       await index_repository_db(db_pool_project_b, "/repo", "project-b", False)

       # Search in project-a
       results_a = await search_code_db(
           db_pool_project_a, [0.1]*768, "project-a", {}, 10
       )

       # Search in project-b
       results_b = await search_code_db(
           db_pool_project_b, [0.1]*768, "project-b", {}, 10
       )

       # Verify no overlap
       assert len(results_a) > 0
       assert len(results_b) > 0
       assert all(r["project_id"] == "project-a" for r in results_a)
       assert all(r["project_id"] == "project-b" for r in results_b)

   @pytest.mark.asyncio
   async def test_search_with_workflow_mcp_integration(mock_workflow_mcp):
       """Test search uses active project from workflow-mcp"""
       # Mock workflow-mcp to return "project-alpha"
       mock_workflow_mcp.set_active_project("project-alpha")

       # Search without explicit project_id
       params = SearchCodeParams(query="authentication", project_id=None)
       result = await search_code(params)

       # Verify used project-alpha
       assert result["project_id"] == "project-alpha"
   ```

### Acceptance Criteria
- [ ] `project_id` parameter added to both tools
- [ ] `get_active_project_id()` helper implemented
- [ ] Search falls back to explicit `project_id` if workflow-mcp unavailable
- [ ] Multi-project isolation tests pass (no cross-contamination)
- [ ] Integration tests with workflow-mcp pass

### Git Strategy
```bash
git add src/codebase_mcp/utils/project_context.py
git add src/codebase_mcp/tools/search.py
git add tests/test_multi_project.py
git commit -m "feat(search): add multi-project support with workflow-mcp integration"
```

### Testing
```bash
# Test multi-project isolation
pytest tests/test_multi_project.py -v

# Test workflow-mcp integration
pytest tests/test_workflow_integration.py -v
```

### Time Estimate
- **Duration**: 3 hours
- **Dependencies**: Phase 6 complete

---

## Phase 8: Update Database Connection Management

### Objective
Implement per-project database connection pools

### Tasks

1. **Refactor Connection Module**
   Edit `src/codebase_mcp/database/connection.py`:
   ```python
   import asyncpg
   import os
   from typing import Dict, Optional

   # Per-project connection pools
   _pools: Dict[str, asyncpg.Pool] = {}

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
       """Close all database connection pools (for shutdown)"""
       for pool in _pools.values():
           await pool.close()
       _pools.clear()

   async def ensure_database_exists(project_id: str):
       """Create project database if it doesn't exist"""
       database_name = f"codebase_{project_id}"

       # Connect to default postgres database
       conn = await asyncpg.connect(
           host=os.getenv("POSTGRES_HOST", "localhost"),
           port=int(os.getenv("POSTGRES_PORT", "5432")),
           database="postgres",
           user=os.getenv("POSTGRES_USER", "postgres"),
           password=os.getenv("POSTGRES_PASSWORD", ""),
       )

       try:
           # Check if database exists
           exists = await conn.fetchval(
               "SELECT 1 FROM pg_database WHERE datname = $1",
               database_name
           )

           if not exists:
               # Create database
               await conn.execute(f"CREATE DATABASE {database_name}")

               # Connect to new database and create schema
               project_conn = await asyncpg.connect(
                   host=os.getenv("POSTGRES_HOST", "localhost"),
                   port=int(os.getenv("POSTGRES_PORT", "5432")),
                   database=database_name,
                   user=os.getenv("POSTGRES_USER", "postgres"),
                   password=os.getenv("POSTGRES_PASSWORD", ""),
               )

               try:
                   # Load schema from schema.sql
                   with open("src/codebase_mcp/database/schema.sql") as f:
                       schema_sql = f.read()
                   await project_conn.execute(schema_sql)
               finally:
                   await project_conn.close()
       finally:
           await conn.close()
   ```

2. **Update Tool Implementations**
   - Ensure all tools call `ensure_database_exists(project_id)` before operations
   - Update `index_repository` and `search_code` to use `get_db_pool(project_id)`

3. **Write Connection Pool Tests**
   ```python
   @pytest.mark.asyncio
   async def test_per_project_pools():
       """Test that each project has its own connection pool"""
       pool_a = await get_db_pool("project-a")
       pool_b = await get_db_pool("project-b")

       assert pool_a is not pool_b
       assert pool_a is await get_db_pool("project-a")  # Same pool on second call

   @pytest.mark.asyncio
   async def test_database_auto_creation():
       """Test that databases are created automatically"""
       project_id = "test-auto-create"
       await ensure_database_exists(project_id)

       # Verify database exists
       pool = await get_db_pool(project_id)
       async with pool.acquire() as conn:
           result = await conn.fetchval("SELECT 1")
           assert result == 1
   ```

### Acceptance Criteria
- [ ] One connection pool per project
- [ ] Pools created lazily on first access
- [ ] Databases auto-created if missing
- [ ] Cleanup function closes all pools
- [ ] Tests validate pool isolation

### Git Strategy
```bash
git add src/codebase_mcp/database/connection.py
git add tests/test_connection_pooling.py
git commit -m "feat(db): implement per-project connection pools with auto-creation"
```

### Testing
```bash
# Test connection pooling
pytest tests/test_connection_pooling.py -v

# Test multi-project with real databases
pytest tests/test_multi_project.py --integration -v
```

### Time Estimate
- **Duration**: 2 hours
- **Dependencies**: Phase 7 complete

---

## Phase 9: Update Documentation

### Objective
Update all documentation to reflect search-only scope

### Tasks

1. **Update README.md**
   - Remove: Work Items, Tasks, Vendors, Deployments sections
   - Add: Multi-Project Support section
   - Update: Tool list (only 2 tools)
   - Update: Architecture diagram (simplified)

2. **Update API Documentation**
   Edit `docs/api.md`:
   - Remove: All non-search tool documentation
   - Update: `index_repository` with `project_id` parameter
   - Update: `search_code` with `project_id` parameter
   - Add: Examples with multi-project usage

3. **Update Architecture Documentation**
   Edit `docs/architecture.md`:
   - Update: Database schema diagram (only 2 tables)
   - Add: Multi-project architecture diagram
   - Add: workflow-mcp integration diagram

4. **Update CHANGELOG.md**
   ```markdown
   # Changelog

   ## [2.0.0] - 2025-10-XX

   ### BREAKING CHANGES
   - Removed all non-search functionality (work items, tasks, vendors, deployments)
   - Moved removed functionality to `workflow-mcp` (install separately)
   - Added `project_id` parameter to `index_repository` and `search_code`
   - Database schema simplified (only `repositories` and `code_chunks` tables)

   ### Added
   - Multi-project support (one database per project)
   - Integration with workflow-mcp for active project context
   - Automatic database creation for new projects
   - Per-project connection pooling

   ### Removed
   - `create_work_item`, `list_work_items`, `query_work_item`, `update_work_item`
   - `create_task`, `get_task`, `list_tasks`, `update_task`
   - `record_deployment`
   - `create_vendor`, `query_vendor_status`, `update_vendor_status`
   - `get_project_configuration`, `update_project_configuration`

   ### Migration
   - See `docs/migration-guide.md` for migration instructions
   - Database migration script: `migrations/002_remove_non_search_tables.sql`
   ```

### Acceptance Criteria
- [ ] README.md updated (search-only scope)
- [ ] API docs updated (only 2 tools)
- [ ] Architecture docs updated (simplified diagrams)
- [ ] CHANGELOG.md documents breaking changes
- [ ] All documentation reviewed for accuracy

### Git Strategy
```bash
git add README.md docs/ CHANGELOG.md
git commit -m "docs(refactor): update documentation for search-only scope and multi-project support"
```

### Testing
- Manual review of all documentation
- Verify links work (no broken references)

### Time Estimate
- **Duration**: 2 hours
- **Dependencies**: Phase 8 complete

---

## Phase 10: Create Migration Guide

### Objective
Provide clear migration path for existing users

### Tasks

1. **Create Migration Guide**
   Create `docs/migration-guide.md` (see refactoring-plan.md for full content)

2. **Test Migration Instructions**
   - Follow migration guide step-by-step on test database
   - Verify all steps work as documented
   - Update guide based on testing results

3. **Create Migration Checklist**
   ```markdown
   # Migration Checklist

   - [ ] Backup existing database: `pg_dump codebase_mcp > backup.sql`
   - [ ] Install workflow-mcp: `pip install workflow-mcp`
   - [ ] Update MCP client config (add workflow-mcp server)
   - [ ] Run migration script: `psql codebase_mcp < migrations/002_remove_non_search_tables.sql`
   - [ ] Verify migration: `psql codebase_mcp -c "\dt"`
   - [ ] Update tool calls (add `project_id` parameter)
   - [ ] Test search functionality
   - [ ] Migrate work items/tasks data to workflow-mcp (see workflow-mcp docs)
   ```

### Acceptance Criteria
- [ ] Migration guide created and comprehensive
- [ ] Migration tested on real database
- [ ] Checklist provided for users
- [ ] Common issues documented with solutions

### Git Strategy
```bash
git add docs/migration-guide.md
git commit -m "docs(migration): add comprehensive migration guide for v2.0.0"
```

### Testing
- Manual testing of migration steps
- Validate backup/restore process

### Time Estimate
- **Duration**: 2 hours
- **Dependencies**: Phase 9 complete

---

## Phase 11: Performance Testing and Optimization

### Objective
Validate performance meets constitutional requirements

### Tasks

1. **Create Performance Test Suite**
   Create `tests/test_performance.py`:
   ```python
   import pytest
   import time

   @pytest.mark.performance
   @pytest.mark.asyncio
   async def test_search_latency_p95(large_indexed_repo):
       """Test search latency meets <500ms p95 target"""
       latencies = []

       # Run 100 searches
       for i in range(100):
           start = time.time()
           result = await search_code(
               SearchCodeParams(
                   query=f"test query {i}",
                   project_id="large-repo",
                   limit=10
               )
           )
           latency = (time.time() - start) * 1000  # Convert to ms
           latencies.append(latency)

       # Calculate p95
       latencies.sort()
       p95 = latencies[int(0.95 * len(latencies))]
       p50 = latencies[int(0.50 * len(latencies))]

       print(f"Search latency - p50: {p50:.2f}ms, p95: {p95:.2f}ms")

       assert p95 < 500, f"p95 latency {p95:.2f}ms exceeds 500ms target"
       assert p50 < 300, f"p50 latency {p50:.2f}ms exceeds 300ms target"

   @pytest.mark.performance
   @pytest.mark.asyncio
   async def test_indexing_throughput(temp_repo_10k_files):
       """Test indexing meets <60s for 10k files target"""
       start = time.time()

       result = await index_repository(
           IndexRepositoryParams(
               repo_path=temp_repo_10k_files,
               project_id="perf-test",
               force_reindex=True
           )
       )

       duration = time.time() - start

       print(f"Indexed {result['files_indexed']} files in {duration:.2f}s")

       assert duration < 60, f"Indexing took {duration:.2f}s, exceeds 60s target"
       assert result["status"] == "success"
   ```

2. **Run Performance Benchmarks**
   ```bash
   # Run performance tests
   pytest tests/test_performance.py -v -m performance

   # Generate performance report
   pytest tests/test_performance.py --benchmark-only --benchmark-json=perf-results.json
   ```

3. **Optimize if Needed**
   - If performance targets not met, profile and optimize:
     - HNSW index parameters (m, ef_construction)
     - Connection pool size
     - Batch sizes for indexing
     - Ollama embedding generation (concurrent requests)

### Acceptance Criteria
- [ ] Search latency <500ms (p95)
- [ ] Indexing throughput <60s for 10k files
- [ ] Performance tests pass consistently (3+ runs)
- [ ] Performance results documented

### Git Strategy
```bash
git add tests/test_performance.py
git commit -m "test(performance): add performance benchmarks for search and indexing"
```

### Testing
```bash
# Run performance suite multiple times
for i in {1..3}; do
  pytest tests/test_performance.py -v -m performance
done
```

### Time Estimate
- **Duration**: 3 hours (includes optimization if needed)
- **Dependencies**: Phase 10 complete

---

## Phase 12: Final Validation and Release Preparation

### Objective
Validate all requirements met and prepare for release

### Tasks

1. **Run Full Test Suite**
   ```bash
   # All tests
   pytest tests/ -v --cov=src/codebase_mcp --cov-report=html

   # Verify coverage >80%
   open htmlcov/index.html
   ```

2. **Run mypy Type Checking**
   ```bash
   mypy --strict src/codebase_mcp/
   # Expected: Success: no issues found
   ```

3. **Run MCP Protocol Compliance Tests**
   ```bash
   # Start server
   python -m codebase_mcp.server &

   # Run mcp-inspector
   mcp-inspector http://localhost:8000 --full-validation

   # Expected: 100% protocol compliance
   ```

4. **Validate Against Constitution**
   - [ ] Principle I: Simplicity Over Features (only search tools)
   - [ ] Principle II: Local-First Architecture (Ollama, PostgreSQL local)
   - [ ] Principle III: Protocol Compliance (mcp-inspector passes)
   - [ ] Principle IV: Performance Guarantees (benchmarks pass)
   - [ ] Principle V: Production Quality (mypy passes, coverage >80%)
   - [ ] Principle VI: Specification-First (spec.md exists, approved)
   - [ ] Principle VII: TDD (all tests pass)
   - [ ] Principle VIII: Pydantic Type Safety (all models use Pydantic)
   - [ ] Principle IX: Orchestrated Subagents (N/A for refactor)
   - [ ] Principle X: Git Micro-Commits (verified in commit history)
   - [ ] Principle XI: FastMCP Foundation (FastMCP used)

5. **Compare Baseline vs Final State**
   ```bash
   # Final metrics
   cloc src/ tests/ > docs/baseline/loc-after.txt
   pytest tests/ --cov=src/codebase_mcp > docs/baseline/tests-after.txt

   # Generate comparison report
   echo "## Refactor Results" > docs/baseline/comparison.md
   echo "" >> docs/baseline/comparison.md
   echo "### Before:" >> docs/baseline/comparison.md
   cat docs/baseline/loc-before.txt >> docs/baseline/comparison.md
   echo "" >> docs/baseline/comparison.md
   echo "### After:" >> docs/baseline/comparison.md
   cat docs/baseline/loc-after.txt >> docs/baseline/comparison.md
   ```

6. **Update Version Number**
   ```bash
   # Update version in pyproject.toml
   sed -i 's/version = "1.0.0"/version = "2.0.0"/' pyproject.toml

   # Update version in __init__.py
   sed -i 's/__version__ = "1.0.0"/__version__ = "2.0.0"/' src/codebase_mcp/__init__.py
   ```

7. **Create Release Tag**
   ```bash
   git tag -a v2.0.0 -m "Release v2.0.0: Pure semantic search MCP with multi-project support"
   ```

### Acceptance Criteria
- [ ] All tests pass (100%)
- [ ] Coverage >80%
- [ ] mypy --strict passes (0 errors)
- [ ] mcp-inspector validation passes (100%)
- [ ] All constitutional principles satisfied
- [ ] Version bumped to 2.0.0
- [ ] Release tag created

### Git Strategy
```bash
git add pyproject.toml src/codebase_mcp/__init__.py docs/baseline/
git commit -m "chore(release): prepare v2.0.0 release"
git tag -a v2.0.0 -m "Release v2.0.0: Pure semantic search MCP"
```

### Testing
- Full regression testing (all tests)
- Manual smoke testing (index + search)

### Time Estimate
- **Duration**: 2 hours
- **Dependencies**: Phase 11 complete

---

## Post-Implementation: Merge and Deploy

### Tasks

1. **Create Pull Request**
   ```bash
   git push origin 002-refactor-pure-search
   git push origin v2.0.0

   # Create PR via GitHub CLI
   gh pr create \
     --title "Refactor: Pure semantic search MCP with multi-project support" \
     --body "$(cat docs/mcp-split-plan/01-codebase-mcp/refactoring-plan.md)"
   ```

2. **Code Review**
   - Review all changes systematically
   - Verify constitutional compliance
   - Check documentation completeness
   - Validate test coverage

3. **Merge to Main**
   ```bash
   # After approval
   gh pr merge 002-refactor-pure-search --squash
   ```

4. **Deploy Documentation**
   - Update README on repository homepage
   - Publish migration guide
   - Announce breaking changes (v2.0.0)

### Time Estimate
- **Duration**: 1-2 hours (review time varies)
- **Dependencies**: Phase 12 complete

---

## Timeline Summary

| Phase | Description | Duration | Dependencies |
|-------|-------------|----------|--------------|
| 0 | Prerequisites | 1h | None |
| 1 | Branch & Baseline | 1h | Phase 0 |
| 2 | Database Schema | 2-3h | Phase 1 |
| 3 | Remove Tool Files | 1h | Phase 2 |
| 4 | Remove DB Operations | 2h | Phase 3 |
| 5 | Update Server | 1h | Phase 4 |
| 6 | Remove Tests | 1h | Phase 5 |
| 7 | Multi-Project Support | 3h | Phase 6 |
| 8 | Connection Pooling | 2h | Phase 7 |
| 9 | Documentation | 2h | Phase 8 |
| 10 | Migration Guide | 2h | Phase 9 |
| 11 | Performance Testing | 3h | Phase 10 |
| 12 | Final Validation | 2h | Phase 11 |
| Post | PR & Merge | 1-2h | Phase 12 |

**Total Estimated Time**: 23-25 hours (3-4 days with testing and validation)

---

## Success Criteria (Overall)

### Functional
- [ ] Only 2 MCP tools: `index_repository`, `search_code`
- [ ] Multi-project support works (isolation validated)
- [ ] workflow-mcp integration works (active project detection)
- [ ] Falls back to explicit project_id when workflow-mcp unavailable

### Non-Functional
- [ ] Search latency <500ms (p95)
- [ ] Indexing throughput <60s for 10k files
- [ ] 100% MCP protocol compliance
- [ ] Type-safe: mypy --strict passes
- [ ] Test coverage >80%

### Process
- [ ] All phases completed in order
- [ ] Micro-commits after each phase (working state)
- [ ] Documentation updated and comprehensive
- [ ] Migration guide tested and accurate

### Constitutional Compliance
- [ ] All 11 principles satisfied
- [ ] No scope creep (only search)
- [ ] Local-first (no cloud dependencies)
- [ ] Production quality (error handling, logging, types)

---

## Risk Management

### Risk: Performance Regression
**Mitigation**: Performance tests in Phase 11, optimize before release

### Risk: Data Loss During Migration
**Mitigation**: Migration guide emphasizes backup, migration tested on test DB first

### Risk: Breaking Changes Impact Users
**Mitigation**: Clear migration guide, semantic versioning (v2.0.0), deprecation notices

### Risk: workflow-mcp Integration Failures
**Mitigation**: Fallback to explicit project_id, clear error messages, integration tests

---

## Next Steps After Completion

1. **Monitor Production Usage**
   - Track error rates, latency percentiles
   - Collect user feedback on migration experience

2. **Future Enhancements** (v2.1.0+)
   - Add incremental indexing (only changed files)
   - Support for additional languages (via tree-sitter)
   - Query suggestions (based on indexed code)
   - Search analytics (popular queries, result relevance)

3. **Integration with Other MCPs**
   - Collaborate with workflow-mcp for deeper integration
   - Support project templates (auto-index on project creation)
