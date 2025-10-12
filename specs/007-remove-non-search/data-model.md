# Data Model: Feature 007 Deletion Inventory

## Overview

This document provides the complete inventory of files to DELETE and PRESERVE during the removal of 14 non-search MCP tools from the codebase-mcp server. The goal is to retain only `index_repository` and `search_code` tools while eliminating all project management, vendor tracking, and task management functionality.

**Deletion Scope**: 35 files total
**Preservation Scope**: 19 files total

---

## Section 1: Files to DELETE

### 1.1 Tool Files (4 files)

**DELETE: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/mcp/tools/tasks.py`**
- **Rationale**: Implements 4 task management tools (get_task, list_tasks, create_task, update_task)
- **Dependencies**: Uses Task model, TaskService, task validation schemas
- **Impact**: Removes all task CRUD functionality from MCP interface

**DELETE: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/mcp/tools/work_items.py`**
- **Rationale**: Implements 4 work item tools (create_work_item, update_work_item, query_work_item, list_work_items)
- **Dependencies**: Uses WorkItem model, WorkItemService, hierarchy logic
- **Impact**: Removes hierarchical project management functionality

**DELETE: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/mcp/tools/tracking.py`**
- **Rationale**: Implements 3 vendor tracking tools (query_vendor_status, update_vendor_status, create_vendor)
- **Dependencies**: Uses Vendor model, VendorService, deployment relationships
- **Impact**: Removes vendor extractor tracking functionality

**DELETE: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/mcp/tools/configuration.py`**
- **Rationale**: Implements 3 project configuration tools (get_project_configuration, update_project_configuration, record_deployment)
- **Dependencies**: Uses ProjectConfig model, DeploymentEvent model, configuration service
- **Impact**: Removes project-level configuration and deployment tracking

### 1.2 Model Files (4 files)

**DELETE: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/models/task.py`**
- **Rationale**: Defines Task SQLAlchemy model and Pydantic schemas (TaskCreate, TaskUpdate, TaskResponse, TaskSummary)
- **Dependencies**: Used by TaskService, tasks.py tool
- **Impact**: Removes task entity from data model

**DELETE: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/models/task_schemas.py`**
- **Rationale**: Defines auxiliary task schemas (TaskBranch, TaskCommit, TaskWithDetails)
- **Dependencies**: Used by task service for git integration
- **Impact**: Removes task-git relationship schemas

**DELETE: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/models/task_relations.py`**
- **Rationale**: Defines task relationship models (TaskPlanningReference junction table)
- **Dependencies**: Used by TaskService for many-to-many relationships
- **Impact**: Removes task relationship tracking

**DELETE: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/models/tracking.py`**
- **Rationale**: Defines Vendor, DeploymentEvent, ProjectConfig models and schemas
- **Dependencies**: Used by VendorService, DeploymentService, ConfigurationService
- **Impact**: Removes vendor tracking, deployment events, project configuration entities

### 1.3 Service Files (5 files)

**DELETE: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/services/tasks.py`**
- **Rationale**: Implements TaskService with CRUD operations, git integration, planning references
- **Dependencies**: Uses Task model, task schemas, database session
- **Impact**: Removes all task business logic

**DELETE: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/services/work_items.py`**
- **Rationale**: Implements WorkItemService with hierarchy management, materialized paths, dependency tracking
- **Dependencies**: Uses WorkItem model, hierarchy service, validation logic
- **Impact**: Removes work item business logic and hierarchy operations

**DELETE: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/services/vendor.py`**
- **Rationale**: Implements VendorService with vendor CRUD, status updates, optimistic locking
- **Dependencies**: Uses Vendor model, tracking schemas, locking service
- **Impact**: Removes vendor tracking business logic

**DELETE: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/services/deployment.py`**
- **Rationale**: Implements DeploymentService for deployment event recording and querying
- **Dependencies**: Uses DeploymentEvent model, vendor/work item relationships
- **Impact**: Removes deployment tracking business logic

**DELETE: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/services/hierarchy.py`**
- **Rationale**: Implements HierarchyService for materialized path operations, ancestor/descendant queries
- **Dependencies**: Used by WorkItemService for hierarchical operations
- **Impact**: Removes hierarchy management utilities

### 1.4 ANALYZE Files (7 files) - Import Analysis Complete

**Import Analysis Findings**: None of the 7 ANALYZE files are imported by search code (indexing.py, search.py, or their dependencies: indexer.py, embedder.py, chunker.py, scanner.py, searcher.py).

**DELETE: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/utils/types.py`**
- **Rationale**: Defines custom type aliases (PathStr, JSONDict, UUIDStr) used across the codebase
- **Import Analysis**: NOT imported by search code
- **Decision**: DELETE - No search dependencies found

**DELETE: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/utils/cache.py`**
- **Rationale**: Implements caching utilities for work item and vendor queries
- **Import Analysis**: NOT imported by search code
- **Decision**: DELETE - No search dependencies found

**DELETE: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/utils/validation.py`**
- **Rationale**: Provides validation helpers for UUIDs, work item types, status values
- **Import Analysis**: NOT imported by search code
- **Decision**: DELETE - No search dependencies found

**DELETE: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/utils/locking.py`**
- **Rationale**: Implements optimistic locking utilities for vendor and work item updates
- **Import Analysis**: NOT imported by search code
- **Decision**: DELETE - No search dependencies found

**DELETE: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/utils/git_history.py`**
- **Rationale**: Provides git integration utilities for task branching and commit tracking
- **Import Analysis**: NOT imported by search code
- **Decision**: DELETE - No search dependencies found

**DELETE: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/utils/markdown.py`**
- **Rationale**: Implements markdown parsing utilities for task descriptions and notes
- **Import Analysis**: NOT imported by search code
- **Decision**: DELETE - No search dependencies found

**DELETE: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/utils/fallback.py`**
- **Rationale**: Provides fallback logic for missing vendor extractors or failed operations
- **Import Analysis**: NOT imported by search code
- **Decision**: DELETE - No search dependencies found

### 1.5 Test Files (15 files estimated)

**DELETE: `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/unit/test_tasks.py`**
- **Rationale**: Unit tests for TaskService

**DELETE: `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/unit/test_work_items.py`**
- **Rationale**: Unit tests for WorkItemService

**DELETE: `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/unit/test_vendor.py`**
- **Rationale**: Unit tests for VendorService

**DELETE: `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/unit/test_deployment.py`**
- **Rationale**: Unit tests for DeploymentService

**DELETE: `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/unit/test_hierarchy.py`**
- **Rationale**: Unit tests for HierarchyService

**DELETE: `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/unit/test_utils_types.py`**
- **Rationale**: Unit tests for types.py utilities

**DELETE: `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/unit/test_utils_cache.py`**
- **Rationale**: Unit tests for cache.py utilities

**DELETE: `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/unit/test_utils_validation.py`**
- **Rationale**: Unit tests for validation.py utilities

**DELETE: `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/unit/test_utils_locking.py`**
- **Rationale**: Unit tests for locking.py utilities

**DELETE: `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/integration/test_tasks_integration.py`**
- **Rationale**: Integration tests for task CRUD operations

**DELETE: `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/integration/test_work_items_integration.py`**
- **Rationale**: Integration tests for work item hierarchy operations

**DELETE: `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/integration/test_vendor_integration.py`**
- **Rationale**: Integration tests for vendor tracking

**DELETE: `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/integration/test_deployment_integration.py`**
- **Rationale**: Integration tests for deployment event recording

**DELETE: `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/integration/test_configuration_integration.py`**
- **Rationale**: Integration tests for project configuration

**DELETE: `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/e2e/test_tracking_workflow.py`**
- **Rationale**: End-to-end tests for vendor tracking and deployment workflows

---

## Section 2: Files to PRESERVE

### 2.1 Tool Files (2 files)

**PRESERVE: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/mcp/tools/indexing.py`**
- **Rationale**: Implements `index_repository` tool (core functionality)
- **Dependencies**: Uses IndexerService, Repository model, embedder
- **Justification**: Required for semantic code indexing

**PRESERVE: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/mcp/tools/search.py`**
- **Rationale**: Implements `search_code` tool (core functionality)
- **Dependencies**: Uses SearcherService, CodeChunk model, embedder
- **Justification**: Required for semantic code search

### 2.2 Model Files (3 files)

**PRESERVE: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/models/repository.py`**
- **Rationale**: Defines Repository SQLAlchemy model and Pydantic schemas
- **Dependencies**: Used by indexing service and search service
- **Justification**: Core data model for indexed repositories

**PRESERVE: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/models/code_chunk.py`**
- **Rationale**: Defines CodeChunk SQLAlchemy model with pgvector embedding column
- **Dependencies**: Used by chunker, embedder, searcher services
- **Justification**: Core data model for searchable code chunks

**PRESERVE: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/models/database.py`**
- **Rationale**: Defines database connection, session management, Base declarative base
- **Dependencies**: Used by all services and models
- **Justification**: Core database infrastructure

### 2.3 Service Files (5 files)

**PRESERVE: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/services/indexer.py`**
- **Rationale**: Orchestrates repository indexing workflow (scan, chunk, embed, store)
- **Dependencies**: Uses scanner, chunker, embedder services
- **Justification**: Core indexing orchestration logic

**PRESERVE: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/services/embedder.py`**
- **Rationale**: Generates embeddings using Ollama nomic-embed-text model
- **Dependencies**: Uses httpx for Ollama API calls, pgvector for storage
- **Justification**: Core embedding generation for semantic search

**PRESERVE: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/services/chunker.py`**
- **Rationale**: Splits code files into semantic chunks (functions, classes, blocks)
- **Dependencies**: Uses tree-sitter parsers for AST-based chunking
- **Justification**: Core chunking logic for indexing

**PRESERVE: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/services/scanner.py`**
- **Rationale**: Scans repository directories, filters ignored files (.gitignore support)
- **Dependencies**: Uses pathlib, gitignore parsing
- **Justification**: Core file discovery for indexing

**PRESERVE: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/services/searcher.py`**
- **Rationale**: Performs semantic similarity search using pgvector cosine distance
- **Dependencies**: Uses embedder for query embeddings, CodeChunk model
- **Justification**: Core search logic with ranking and filtering

### 2.4 Shared Infrastructure Files (4 files)

**PRESERVE: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/config.py`**
- **Rationale**: Defines application configuration (database URL, Ollama endpoint, logging)
- **Dependencies**: Used by all services and tools
- **Justification**: Core configuration management

**PRESERVE: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/logging_config.py`**
- **Rationale**: Configures structured logging with JSON format
- **Dependencies**: Used across all modules
- **Justification**: Core observability infrastructure

**PRESERVE: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/main.py`**
- **Rationale**: FastMCP server entry point, tool registration
- **Dependencies**: Imports indexing.py and search.py tools
- **Justification**: Core MCP server initialization

**PRESERVE: `/Users/cliffclarke/Claude_Code/codebase-mcp/pyproject.toml`**
- **Rationale**: Project metadata, dependencies, tool configuration
- **Justification**: Core project definition

### 2.5 Test Files (9 files estimated)

**PRESERVE: `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/unit/test_indexer.py`**
- **Rationale**: Unit tests for IndexerService

**PRESERVE: `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/unit/test_embedder.py`**
- **Rationale**: Unit tests for EmbedderService

**PRESERVE: `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/unit/test_chunker.py`**
- **Rationale**: Unit tests for ChunkerService

**PRESERVE: `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/unit/test_scanner.py`**
- **Rationale**: Unit tests for ScannerService

**PRESERVE: `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/unit/test_searcher.py`**
- **Rationale**: Unit tests for SearcherService

**PRESERVE: `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/integration/test_indexing_integration.py`**
- **Rationale**: Integration tests for repository indexing workflow

**PRESERVE: `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/integration/test_search_integration.py`**
- **Rationale**: Integration tests for semantic search workflow

**PRESERVE: `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/e2e/test_index_search_workflow.py`**
- **Rationale**: End-to-end tests for index → search workflow

**PRESERVE: `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/conftest.py`**
- **Rationale**: Shared pytest fixtures for database setup, test repositories

---

## Section 3: Import Analysis Results

### 3.1 Analysis Methodology

Performed comprehensive import analysis using grep and manual code review to determine if any of the 7 ANALYZE files (`types.py`, `cache.py`, `validation.py`, `locking.py`, `git_history.py`, `markdown.py`, `fallback.py`) are imported by search code paths.

**Search Code Paths Analyzed**:
1. Direct tool files: `indexing.py`, `search.py`
2. Service dependencies: `indexer.py`, `embedder.py`, `chunker.py`, `scanner.py`, `searcher.py`
3. Model dependencies: `repository.py`, `code_chunk.py`, `database.py`
4. Infrastructure: `config.py`, `logging_config.py`, `main.py`

### 3.2 Import Analysis Findings

**Result**: ZERO imports found in search code for all 7 ANALYZE files.

**Details**:
- `types.py`: NOT imported by any search code (custom type aliases unused by indexing/search)
- `cache.py`: NOT imported by any search code (caching only used by work items/vendors)
- `validation.py`: NOT imported by any search code (validation only for tasks/work items)
- `locking.py`: NOT imported by any search code (optimistic locking only for vendors/work items)
- `git_history.py`: NOT imported by any search code (git integration only for tasks)
- `markdown.py`: NOT imported by any search code (markdown parsing only for task descriptions)
- `fallback.py`: NOT imported by any search code (fallback logic only for vendor operations)

### 3.3 Import Decision

**DECISION**: DELETE all 7 ANALYZE files

**Rationale**:
1. No search code dependencies detected in any of the 7 files
2. All utilities are scoped to task management, work items, or vendor tracking
3. No shared infrastructure used by both search and non-search functionality
4. Clean separation of concerns allows safe deletion without impact to search features

---

## Section 4: Import Cleanup

After deleting the 35 files, the following imports must be removed from preserved files to avoid import errors.

### 4.1 Main Server File

**File**: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/main.py`

**Imports to REMOVE**:
```python
from mcp.tools.tasks import get_task, list_tasks, create_task, update_task
from mcp.tools.work_items import create_work_item, update_work_item, query_work_item, list_work_items
from mcp.tools.tracking import query_vendor_status, update_vendor_status, create_vendor
from mcp.tools.configuration import get_project_configuration, update_project_configuration, record_deployment
```

**Imports to PRESERVE**:
```python
from mcp.tools.indexing import index_repository
from mcp.tools.search import search_code
```

**Tool Registrations to REMOVE**:
Remove 14 tool registrations from FastMCP app, keeping only:
- `app.tool()(index_repository)`
- `app.tool()(search_code)`

### 4.2 Model Initialization

**File**: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/models/__init__.py`

**Imports to REMOVE**:
```python
from models.task import Task, TaskCreate, TaskUpdate, TaskResponse, TaskSummary
from models.task_schemas import TaskBranch, TaskCommit, TaskWithDetails
from models.task_relations import TaskPlanningReference
from models.tracking import Vendor, DeploymentEvent, ProjectConfig
```

**Imports to PRESERVE**:
```python
from models.repository import Repository
from models.code_chunk import CodeChunk
from models.database import Base, get_session
```

### 4.3 Service Initialization

**File**: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/services/__init__.py`

**Imports to REMOVE**:
```python
from services.tasks import TaskService
from services.work_items import WorkItemService
from services.vendor import VendorService
from services.deployment import DeploymentService
from services.hierarchy import HierarchyService
```

**Imports to PRESERVE**:
```python
from services.indexer import IndexerService
from services.embedder import EmbedderService
from services.chunker import ChunkerService
from services.scanner import ScannerService
from services.searcher import SearcherService
```

### 4.4 Test Configuration

**File**: `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/conftest.py`

**Fixtures to REMOVE** (if present):
- Task model fixtures
- WorkItem model fixtures
- Vendor model fixtures
- DeploymentEvent model fixtures
- ProjectConfig model fixtures

**Fixtures to PRESERVE**:
- Database session fixtures
- Repository model fixtures
- CodeChunk model fixtures
- Test repository directory fixtures

### 4.5 Utility Module References

**Check for References in**:
- `config.py`: Remove any imports of deleted utils modules
- `logging_config.py`: Remove any imports of deleted utils modules
- Service files: Verify no imports of deleted utils (types, cache, validation, locking, git_history, markdown, fallback)

---

## Section 5: Registration Verification

### 5.1 FastMCP Tool Registration

**File**: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/main.py`

**Current State** (before deletion):
- 16 tools registered (14 non-search + 2 search)

**Target State** (after deletion):
- 2 tools registered (index_repository, search_code only)

**Verification Steps**:
1. Remove all non-search tool imports from main.py
2. Remove 14 tool registrations (keep only index_repository and search_code)
3. Verify FastMCP server starts without import errors
4. Test MCP protocol: `tools/list` should return exactly 2 tools

**Expected `tools/list` Response**:
```json
{
  "tools": [
    {
      "name": "index_repository",
      "description": "Index a code repository for semantic search",
      "inputSchema": {...}
    },
    {
      "name": "search_code",
      "description": "Search codebase using semantic similarity",
      "inputSchema": {...}
    }
  ]
}
```

### 5.2 Database Model Registration

**File**: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/models/database.py`

**Verification**:
1. Ensure only Repository and CodeChunk models are imported
2. Verify SQLAlchemy Base.metadata contains only 2 tables: `repositories`, `code_chunks`
3. Remove any foreign key constraints referencing deleted tables (tasks, work_items, vendors, deployments, project_config)

**SQL Verification Query**:
```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
-- Expected: repositories, code_chunks only
```

### 5.3 Alembic Migration Requirements

**Status**: Database schema contains 7+ tables from non-search features

**Migration Tasks**:
1. Create new Alembic migration (e.g., `003_remove_non_search_tables.py`)
2. Drop tables: tasks, task_branches, task_commits, task_planning_references, work_items, vendors, deployments, project_config
3. Drop foreign key constraints and indexes related to deleted tables
4. Preserve tables: repositories, code_chunks (and pgvector extension)

**Migration Template**:
```python
def upgrade():
    op.drop_table('task_planning_references')
    op.drop_table('task_commits')
    op.drop_table('task_branches')
    op.drop_table('tasks')
    op.drop_table('work_items')
    op.drop_table('deployment_vendors')
    op.drop_table('deployment_work_items')
    op.drop_table('deployments')
    op.drop_table('vendors')
    op.drop_table('project_config')

def downgrade():
    # Re-create tables (reverse order due to foreign keys)
    pass
```

### 5.4 Test Suite Verification

**Pre-Deletion Test Count**: ~24 test files (unit + integration + e2e)
**Post-Deletion Test Count**: ~9 test files (search-related only)

**Verification Steps**:
1. Delete 15 non-search test files
2. Run remaining test suite: `pytest tests/ -v`
3. Ensure all tests pass (no import errors from deleted modules)
4. Verify test coverage remains >80% for search code paths

**Expected Test Results**:
- Unit tests: 5 files passing (indexer, embedder, chunker, scanner, searcher)
- Integration tests: 2 files passing (indexing, search)
- E2E tests: 1 file passing (index_search_workflow)
- Conftest: 1 file (shared fixtures)

---

## Section 6: Complexity Metrics

### 6.1 Codebase Size Reduction

**Lines of Code (estimated)**:
- Tool files: ~1,200 lines deleted (4 files @ 300 lines each)
- Model files: ~800 lines deleted (4 files @ 200 lines each)
- Service files: ~2,500 lines deleted (5 files @ 500 lines each)
- Utils files: ~1,400 lines deleted (7 files @ 200 lines each)
- Test files: ~3,000 lines deleted (15 files @ 200 lines each)

**Total Reduction**: ~8,900 lines of code (approximately 60% reduction)

### 6.2 Dependency Reduction

**Database Tables**: 10 → 2 (80% reduction)
**SQLAlchemy Models**: 10 → 2 (80% reduction)
**MCP Tools**: 16 → 2 (87.5% reduction)
**Service Classes**: 10 → 5 (50% reduction)
**Test Files**: 24 → 9 (62.5% reduction)

### 6.3 Maintenance Burden Reduction

**Removed Responsibilities**:
- Task management (CRUD, git integration, planning references)
- Work item hierarchy (5-level tree, materialized paths, dependencies)
- Vendor tracking (status, versions, optimistic locking)
- Deployment events (PR tracking, test results, relationships)
- Project configuration (context type, token budgets, health checks)

**Retained Responsibilities**:
- Repository indexing (scan, chunk, embed, store)
- Semantic code search (query embedding, similarity search, ranking)

**Result**: Single-purpose server focused exclusively on semantic code search

---

## Section 7: Risk Assessment

### 7.1 Deletion Risks

**LOW RISK**: Import analysis confirms no search code dependencies on deleted files

**Potential Issues**:
1. **Shared utility imports**: If any search code imports deleted utils (not detected in analysis), will cause import errors
2. **Database constraints**: Foreign key constraints may prevent table drops if not properly ordered in migration
3. **Test fixtures**: Shared fixtures in conftest.py may reference deleted models

**Mitigation**:
1. Run comprehensive test suite after deletion to detect import errors
2. Use Alembic migration with proper table drop ordering (junction tables first)
3. Review conftest.py for deleted model references before running tests

### 7.2 Rollback Plan

**If deletion causes critical failures**:

1. **Git Rollback**:
   ```bash
   git revert <commit-hash>
   git push origin 007-remove-non-search
   ```

2. **Database Rollback**:
   ```bash
   alembic downgrade -1  # Revert migration 003
   ```

3. **Restore Deleted Files**:
   ```bash
   git checkout HEAD~1 -- src/mcp/tools/tasks.py
   git checkout HEAD~1 -- src/models/task.py
   # ... restore all 35 files
   ```

### 7.3 Testing Strategy

**Phase 1: Static Analysis**
- Run `mypy src/` to detect import errors
- Run `ruff check src/` to detect unused imports
- Verify no references to deleted modules in preserved files

**Phase 2: Unit Tests**
- Run `pytest tests/unit/ -v`
- Verify all search-related unit tests pass
- Confirm no import errors from deleted modules

**Phase 3: Integration Tests**
- Run `pytest tests/integration/ -v`
- Verify indexing and search workflows complete successfully
- Confirm database operations work with reduced schema

**Phase 4: End-to-End Tests**
- Run `pytest tests/e2e/ -v`
- Verify full index → search workflow
- Confirm MCP protocol compliance (tools/list returns 2 tools)

---

## Summary

This data model provides the complete deletion inventory for feature 007-remove-non-search. The analysis confirms that all 35 files marked for deletion (including 7 ANALYZE utils files) have no dependencies on search code paths. The deletion will reduce the codebase by ~8,900 lines of code (60% reduction) and eliminate 14 MCP tools, transforming the server into a focused semantic code search tool.

**Next Steps**:
1. Review this data model in Phase 1 planning review
2. Generate tasks.md with ordered deletion steps
3. Create Alembic migration 003 for database schema cleanup
4. Execute deletion with comprehensive test validation
