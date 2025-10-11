# Workflow MCP Implementation Phases

## Overview

This document defines the phased implementation strategy for workflow-mcp, breaking development into two major phases:

- **Phase 1 (Weeks 1-3): Core** - Project management foundation with multi-project support
- **Phase 3 (Weeks 7-9): Complete** - Work items, tasks, generic entities, and deployment tracking

*Note: Phase 2 is reserved for codebase-mcp development in the overall project plan.*

Each phase includes specific deliverables, acceptance criteria, git strategy, and testing requirements.

---

## Phase 1: Core (Weeks 1-3)

### Goal

Build the multi-project workspace foundation that enables AI assistants to create, switch, and query isolated project contexts. This phase establishes the registry database, database-per-project architecture, and connection pooling system.

### Deliverables

#### 1. Project Structure and Configuration (Week 1, Days 1-2)

**Tasks**:
- Initialize Python 3.11+ project with Poetry or pip
- Create `pyproject.toml` with dependencies (FastMCP, AsyncPG, Pydantic)
- Configure mypy --strict, ruff, pytest
- Create directory structure:
  ```
  workflow_mcp/
  ├── __init__.py
  ├── server.py           # FastMCP server entry point
  ├── config.py           # Pydantic settings (DATABASE_URL, LOG_LEVEL)
  ├── database/
  │   ├── __init__.py
  │   ├── registry.py     # Registry database operations
  │   ├── projects.py     # Project database creation/management
  │   └── pools.py        # Connection pool management
  ├── models/
  │   ├── __init__.py
  │   └── project.py      # Pydantic models for projects
  └── tools/
      ├── __init__.py
      └── projects.py     # MCP tools for project management

  tests/
  ├── unit/
  │   └── test_models.py
  ├── integration/
  │   └── test_projects.py
  └── protocol/
      └── test_mcp_tools.py

  migrations/
  └── 001_registry_schema.sql
  ```

**Acceptance Criteria**:
- mypy --strict passes with zero errors
- ruff linting passes
- pytest discovers all test files

**Git Strategy**:
- Branch: `001-project-structure`
- Commits:
  - `chore(setup): initialize Python project with Poetry`
  - `chore(config): add mypy, ruff, pytest configuration`
  - `chore(structure): create directory structure and stub files`

---

#### 2. Registry Database Schema (Week 1, Days 2-3)

**Tasks**:
- Design registry database schema (`migrations/001_registry_schema.sql`)
- Implement registry connection pool (AsyncPG)
- Create health check function for registry database

**Schema**:
```sql
-- Registry database: workflow_registry

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Projects table
CREATE TABLE projects (
    project_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    database_name VARCHAR(100) UNIQUE NOT NULL,  -- workflow_project_<uuid>
    metadata JSONB DEFAULT '{}'::jsonb,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'archived', 'deleted')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(100) DEFAULT 'claude-code',
    updated_by VARCHAR(100) DEFAULT 'claude-code',
    last_activated_at TIMESTAMPTZ
);

-- Active project configuration (singleton table)
CREATE TABLE active_project_config (
    id INT PRIMARY KEY DEFAULT 1 CHECK (id = 1),  -- Singleton constraint
    project_id UUID REFERENCES projects(project_id) ON DELETE SET NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by VARCHAR(100) DEFAULT 'claude-code'
);

-- Insert singleton row
INSERT INTO active_project_config (id, project_id) VALUES (1, NULL);

-- Indexes
CREATE INDEX idx_projects_name ON projects (name);
CREATE INDEX idx_projects_status ON projects (status);
CREATE INDEX idx_projects_last_activated ON projects (last_activated_at DESC NULLS LAST);
```

**Acceptance Criteria**:
- Migration script runs successfully
- Registry connection pool initialized (<100ms)
- Health check returns True if registry database is up

**Git Strategy**:
- Branch: `001-project-structure`
- Commit: `feat(database): add registry database schema and connection pool`

---

#### 3. Project Database Template (Week 1, Days 3-5)

**Tasks**:
- Design project database schema template
- Create schema initialization script
- Implement database creation function (CREATE DATABASE + run schema)

**Schema** (`migrations/002_project_schema.sql`):
```sql
-- Project database template: workflow_project_<uuid>

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Work items table (hierarchical)
CREATE TABLE work_items (
    work_item_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    parent_id UUID REFERENCES work_items(work_item_id) ON DELETE CASCADE,
    item_type VARCHAR(20) NOT NULL CHECK (item_type IN ('project', 'session', 'task', 'research')),
    title VARCHAR(200) NOT NULL,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'completed', 'blocked')),
    metadata JSONB DEFAULT '{}'::jsonb,
    path TEXT,  -- Materialized path: /parent_id/child_id/
    depth INT DEFAULT 0,
    version INT DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    created_by VARCHAR(100) DEFAULT 'claude-code',
    updated_by VARCHAR(100) DEFAULT 'claude-code'
);

-- Work item dependencies
CREATE TABLE work_item_dependencies (
    dependency_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    work_item_id UUID NOT NULL REFERENCES work_items(work_item_id) ON DELETE CASCADE,
    depends_on_id UUID NOT NULL REFERENCES work_items(work_item_id) ON DELETE CASCADE,
    dependency_type VARCHAR(20) DEFAULT 'blocks' CHECK (dependency_type IN ('blocks', 'requires')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tasks table
CREATE TABLE tasks (
    task_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    notes TEXT,
    status VARCHAR(20) DEFAULT 'need to be done' CHECK (status IN ('need to be done', 'in-progress', 'complete')),
    planning_references TEXT[],  -- Array of file paths
    version INT DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(100) DEFAULT 'claude-code',
    updated_by VARCHAR(100) DEFAULT 'claude-code'
);

-- Task git associations
CREATE TABLE task_branches (
    task_id UUID REFERENCES tasks(task_id) ON DELETE CASCADE,
    branch_name VARCHAR(200) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (task_id, branch_name)
);

CREATE TABLE task_commits (
    task_id UUID REFERENCES tasks(task_id) ON DELETE CASCADE,
    commit_hash CHAR(40) NOT NULL,  -- Git SHA-1
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (task_id, commit_hash)
);

-- Entity types table
CREATE TABLE entity_types (
    entity_type_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    schema JSONB NOT NULL,  -- JSON Schema Draft 7
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(100) DEFAULT 'claude-code'
);

-- Entities table (generic JSONB storage)
CREATE TABLE entities (
    entity_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type VARCHAR(100) NOT NULL REFERENCES entity_types(type_name) ON DELETE RESTRICT,
    name VARCHAR(200) NOT NULL,
    data JSONB NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    version INT DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(100) DEFAULT 'claude-code',
    updated_by VARCHAR(100) DEFAULT 'claude-code',
    UNIQUE (entity_type, name)
);

-- Deployments table
CREATE TABLE deployments (
    deployment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    deployed_at TIMESTAMPTZ NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,  -- PR details, test results, etc.
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(100) DEFAULT 'claude-code'
);

-- Deployment relationships (many-to-many)
CREATE TABLE deployment_entities (
    deployment_id UUID REFERENCES deployments(deployment_id) ON DELETE CASCADE,
    entity_id UUID REFERENCES entities(entity_id) ON DELETE CASCADE,
    PRIMARY KEY (deployment_id, entity_id)
);

CREATE TABLE deployment_work_items (
    deployment_id UUID REFERENCES deployments(deployment_id) ON DELETE CASCADE,
    work_item_id UUID REFERENCES work_items(work_item_id) ON DELETE CASCADE,
    PRIMARY KEY (deployment_id, work_item_id)
);

-- Indexes
CREATE INDEX idx_work_items_parent ON work_items (parent_id);
CREATE INDEX idx_work_items_type_status ON work_items (item_type, status);
CREATE INDEX idx_work_items_path ON work_items USING GIST (path gist_trgm_ops);
CREATE INDEX idx_tasks_status ON tasks (status);
CREATE INDEX idx_entities_data ON entities USING GIN (data);
CREATE INDEX idx_entities_type_name ON entities (entity_type, name);
CREATE INDEX idx_deployments_deployed_at ON deployments (deployed_at DESC);
```

**Acceptance Criteria**:
- Schema initialization script runs successfully
- Database creation function works (create DB + apply schema)
- Function validates database_name format (`workflow_project_<uuid>`)

**Git Strategy**:
- Branch: `002-project-database-template`
- Commits:
  - `feat(database): add project database schema template`
  - `feat(database): implement database creation with schema initialization`

---

#### 4. MCP Tools: Project Management (Week 2, Days 1-3)

**Tasks**:
- Implement `create_project` tool
- Implement `switch_active_project` tool
- Implement `get_active_project` tool
- Implement `list_projects` tool

**Tool Specifications**:

**create_project**:
```python
@mcp.tool()
async def create_project(
    name: str,
    description: str,
    metadata: dict | None = None
) -> dict:
    """
    Create a new project workspace with isolated database.

    Args:
        name: Project name (1-100 chars, unique)
        description: Project description
        metadata: Optional metadata (JSONB)

    Returns:
        {
            "project_id": "uuid",
            "name": "project-name",
            "database_name": "workflow_project_<uuid>",
            "created_at": "ISO 8601"
        }
    """
    # 1. Validate name is unique
    # 2. Generate project_id and database_name
    # 3. Create database: CREATE DATABASE workflow_project_<uuid>
    # 4. Initialize schema (run 002_project_schema.sql)
    # 5. Insert into registry.projects
    # 6. Create connection pool for new project
    # 7. Return project metadata
```

**switch_active_project**:
```python
@mcp.tool()
async def switch_active_project(project_id: str) -> dict:
    """
    Switch active project context.

    Args:
        project_id: UUID of project to activate

    Returns:
        {
            "project_id": "uuid",
            "name": "project-name",
            "switched_at": "ISO 8601"
        }
    """
    # 1. Validate project exists and not deleted
    # 2. Update active_project_config (singleton)
    # 3. Update projects.last_activated_at
    # 4. Ensure connection pool exists for project
    # 5. Return confirmation
```

**get_active_project**:
```python
@mcp.tool()
async def get_active_project() -> dict | None:
    """
    Get currently active project.

    Returns:
        Project metadata or None if no active project
    """
    # 1. Query active_project_config
    # 2. If project_id is NULL, return None
    # 3. Join with projects table for full metadata
    # 4. Return project metadata
```

**list_projects**:
```python
@mcp.tool()
async def list_projects(
    include_archived: bool = False,
    limit: int = 50,
    offset: int = 0
) -> dict:
    """
    List all projects.

    Args:
        include_archived: Include archived/deleted projects
        limit: Max results (1-100)
        offset: Pagination offset

    Returns:
        {
            "projects": [{"project_id": "...", "name": "...", ...}],
            "total_count": 42
        }
    """
    # 1. Query projects with filters
    # 2. Order by last_activated_at DESC NULLS LAST
    # 3. Apply pagination
    # 4. Return projects and count
```

**Acceptance Criteria**:
- All tools registered with FastMCP
- All tools invocable via MCP protocol
- Pydantic validates inputs/outputs
- Tools log operations (structured logging)

**Git Strategy**:
- Branch: `003-project-management-tools`
- Commits:
  - `feat(tools): implement create_project MCP tool`
  - `feat(tools): implement switch_active_project MCP tool`
  - `feat(tools): implement get_active_project MCP tool`
  - `feat(tools): implement list_projects MCP tool`

---

#### 5. Connection Pool Management (Week 2, Days 4-5)

**Tasks**:
- Implement connection pool registry (dict[project_id, Pool])
- Add lazy pool creation (on first access)
- Add pool health checks
- Add pool cleanup on project deletion

**Architecture**:
```python
class ConnectionPoolManager:
    """Manages AsyncPG connection pools per project."""

    def __init__(self, registry_dsn: str):
        self.registry_pool: asyncpg.Pool = None
        self.project_pools: dict[str, asyncpg.Pool] = {}

    async def initialize_registry(self) -> None:
        """Initialize registry database connection pool."""
        self.registry_pool = await asyncpg.create_pool(
            dsn=self.registry_dsn,
            min_size=2,
            max_size=10
        )

    async def get_project_pool(self, project_id: str) -> asyncpg.Pool:
        """Get or create connection pool for project."""
        if project_id not in self.project_pools:
            # Query registry for database_name
            project = await self._get_project_metadata(project_id)
            # Create pool for project database
            self.project_pools[project_id] = await asyncpg.create_pool(
                dsn=f"postgresql://localhost/{project['database_name']}",
                min_size=1,
                max_size=5
            )
        return self.project_pools[project_id]

    async def close_project_pool(self, project_id: str) -> None:
        """Close and remove project pool."""
        if project_id in self.project_pools:
            await self.project_pools[project_id].close()
            del self.project_pools[project_id]

    async def close_all(self) -> None:
        """Close all connection pools."""
        for pool in self.project_pools.values():
            await pool.close()
        await self.registry_pool.close()
```

**Acceptance Criteria**:
- Registry pool initializes on server startup
- Project pools lazy-load on first access (<50ms)
- Pools reused across tool invocations
- Health checks detect failed connections

**Git Strategy**:
- Branch: `004-connection-pool-management`
- Commits:
  - `feat(database): implement connection pool manager`
  - `feat(database): add pool health checks and cleanup`

---

#### 6. Testing Suite (Week 3, Days 1-3)

**Tasks**:
- Write unit tests for Pydantic models
- Write integration tests for project CRUD operations
- Write isolation tests (multi-project data separation)
- Write MCP protocol compliance tests

**Test Cases**:

**Unit Tests** (`tests/unit/test_models.py`):
```python
def test_project_model_validation():
    """Test Pydantic validation for project model."""
    # Valid project
    project = ProjectResponse(
        project_id="550e8400-e29b-41d4-a716-446655440000",
        name="test-project",
        database_name="workflow_project_550e8400",
        created_at="2025-10-11T10:00:00Z"
    )
    assert project.name == "test-project"

    # Invalid: name too long
    with pytest.raises(ValidationError):
        ProjectResponse(name="x" * 101, ...)
```

**Integration Tests** (`tests/integration/test_projects.py`):
```python
@pytest.mark.asyncio
async def test_create_project(registry_pool):
    """Test project creation with database initialization."""
    project = await create_project_in_db(
        pool=registry_pool,
        name="test-project",
        description="Test project"
    )

    # Verify project in registry
    assert project["project_id"] is not None
    assert project["database_name"].startswith("workflow_project_")

    # Verify database exists
    conn = await asyncpg.connect(f"postgresql://localhost/{project['database_name']}")
    tables = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    assert len(tables) > 0  # Schema initialized
    await conn.close()

    # Cleanup
    await delete_project_in_db(registry_pool, project["project_id"])
```

**Isolation Tests** (`tests/integration/test_isolation.py`):
```python
@pytest.mark.asyncio
async def test_multi_project_isolation():
    """Test that projects never see each other's data."""
    # Create two projects
    project_a = await create_project("project-a", "Project A")
    project_b = await create_project("project-b", "Project B")

    # Add entity type to project A
    await register_entity_type(
        project_id=project_a["project_id"],
        type_name="vendor",
        schema={...}
    )

    # Create entity in project A
    await create_entity(
        project_id=project_a["project_id"],
        entity_type="vendor",
        name="EPSON",
        data={...}
    )

    # Query entities in project B (should be empty)
    entities_b = await query_entities(
        project_id=project_b["project_id"],
        entity_type="vendor"
    )
    assert len(entities_b) == 0  # Isolation confirmed

    # Cleanup
    await delete_project(project_a["project_id"])
    await delete_project(project_b["project_id"])
```

**Protocol Tests** (`tests/protocol/test_mcp_tools.py`):
```python
@pytest.mark.asyncio
async def test_create_project_tool():
    """Test create_project MCP tool invocation."""
    async with stdio_client(...) as (read, write):
        async with ClientSession(read, write) as session:
            result = await session.call_tool(
                "create_project",
                {"name": "test-project", "description": "Test"}
            )
            assert "project_id" in result
            assert result["name"] == "test-project"
```

**Acceptance Criteria**:
- >90% line coverage
- All tests pass in CI (<5 min total)
- Isolation tests confirm no cross-project leaks

**Git Strategy**:
- Branch: `005-testing-suite`
- Commits:
  - `test(unit): add Pydantic model validation tests`
  - `test(integration): add project CRUD tests`
  - `test(integration): add multi-project isolation tests`
  - `test(protocol): add MCP tool compliance tests`

---

#### 7. Documentation and Integration (Week 3, Days 4-5)

**Tasks**:
- Write README.md with setup instructions
- Document MCP tool contracts (inputs/outputs)
- Create example usage scripts
- Write integration guide for codebase-mcp

**Deliverables**:
- `README.md`: Project overview, installation, usage
- `docs/tools.md`: MCP tool reference (all tools documented)
- `docs/integration.md`: How codebase-mcp queries workflow-mcp
- `examples/`: Example scripts demonstrating tool usage

**Acceptance Criteria**:
- Documentation complete and accurate
- Examples run successfully
- codebase-mcp can query `get_active_project()`

**Git Strategy**:
- Branch: `006-documentation`
- Commits:
  - `docs(readme): add project overview and setup instructions`
  - `docs(tools): document MCP tool contracts`
  - `docs(integration): add codebase-mcp integration guide`

---

### Phase 1 Acceptance Criteria

**Functional**:
- [ ] Create project with isolated database
- [ ] Switch active project (<50ms latency)
- [ ] Query active project metadata
- [ ] List projects with pagination

**Performance**:
- [ ] Project creation: <1 second (database creation + schema)
- [ ] Project switching: <50ms p95 latency
- [ ] get_active_project: <10ms p95 latency
- [ ] list_projects: <100ms for 100+ projects

**Quality**:
- [ ] mypy --strict passes with zero errors
- [ ] >90% test coverage
- [ ] All MCP tools invocable from Claude Desktop/CLI
- [ ] Isolation tests confirm no cross-project data leaks

**Integration**:
- [ ] codebase-mcp can query workflow-mcp's `get_active_project()` tool
- [ ] Active project context persists across MCP sessions

---

## Phase 3: Complete (Weeks 7-9)

*Phase 2 is reserved for codebase-mcp development.*

### Goal

Build the complete project management system with hierarchical work items, task tracking, generic entity system, and deployment history recording. This phase delivers full functionality for AI-assisted workflow management.

### Deliverables

#### 1. Hierarchical Work Items (Week 7, Days 1-3)

**Tasks**:
- Implement `create_work_item` tool
- Implement `query_work_item` tool (with hierarchy traversal)
- Implement `update_work_item` tool
- Implement `list_work_items` tool
- Add materialized path updates on create/update

**Tool Specifications**:

**create_work_item**:
```python
@mcp.tool()
async def create_work_item(
    project_id: str,
    item_type: str,  # project, session, task, research
    title: str,
    metadata: dict,
    parent_id: str | None = None
) -> dict:
    """Create hierarchical work item."""
    # 1. Validate project exists
    # 2. Validate item_type enum
    # 3. Validate metadata against type-specific Pydantic model
    # 4. If parent_id: validate parent exists, depth < 5
    # 5. Build materialized path: /parent_path/work_item_id/
    # 6. Insert into work_items table
    # 7. Return work item metadata
```

**query_work_item**:
```python
@mcp.tool()
async def query_work_item(
    work_item_id: str,
    include_children: bool = True,
    include_dependencies: bool = True
) -> dict:
    """Query work item with hierarchy and dependencies."""
    # 1. Fetch work item by ID
    # 2. If include_children: Recursive CTE to get descendants (max 5 levels)
    # 3. If include_dependencies: Join work_item_dependencies
    # 4. Build nested hierarchy structure
    # 5. Return work item with children and dependencies
```

**Acceptance Criteria**:
- Hierarchy up to 5 levels deep
- Materialized path enables fast ancestor queries (<10ms)
- Recursive CTE returns descendants in <10ms
- Optimistic locking prevents concurrent update conflicts

**Git Strategy**:
- Branch: `007-work-items`
- Commits:
  - `feat(work-items): implement create_work_item tool`
  - `feat(work-items): implement query_work_item with hierarchy traversal`
  - `feat(work-items): implement update_work_item with optimistic locking`
  - `feat(work-items): implement list_work_items with filters`

---

#### 2. Task Management (Week 7, Days 4-5)

**Tasks**:
- Implement `create_task` tool
- Implement `update_task` tool (with git integration)
- Implement `list_tasks` tool (with token-efficient summary mode)

**Tool Specifications**:

**create_task**:
```python
@mcp.tool()
async def create_task(
    project_id: str,
    title: str,
    description: str,
    planning_references: list[str] | None = None
) -> dict:
    """Create task with planning document references."""
    # 1. Validate project exists
    # 2. Insert into tasks table (status='need to be done')
    # 3. Store planning_references (array of file paths)
    # 4. Return task metadata
```

**update_task**:
```python
@mcp.tool()
async def update_task(
    task_id: str,
    status: str | None = None,
    branch: str | None = None,
    commit: str | None = None
) -> dict:
    """Update task status and git associations."""
    # 1. Update tasks.status if provided
    # 2. If branch: Insert into task_branches (many-to-many)
    # 3. If commit: Validate 40-char hex, insert into task_commits
    # 4. Return updated task
```

**list_tasks**:
```python
@mcp.tool()
async def list_tasks(
    project_id: str,
    status: str | None = None,
    branch: str | None = None,
    full_details: bool = False,
    limit: int = 50
) -> dict:
    """List tasks with optional filters."""
    # 1. Query tasks with filters (status, branch)
    # 2. If full_details=False: Return TaskSummary (5 fields, ~120 tokens)
    # 3. If full_details=True: Return TaskResponse (10 fields, ~800 tokens)
    # 4. Order by updated_at DESC
    # 5. Return tasks and total_count
```

**Acceptance Criteria**:
- Tasks link to planning documents (spec.md, plan.md)
- Git branch/commit associations work
- Token-efficient summary mode reduces response size by 6x

**Git Strategy**:
- Branch: `008-task-management`
- Commits:
  - `feat(tasks): implement create_task tool`
  - `feat(tasks): implement update_task with git integration`
  - `feat(tasks): implement list_tasks with token-efficient mode`

---

#### 3. Generic Entity System (Week 8, Days 1-4)

**Tasks**:
- Implement `register_entity_type` tool
- Implement `create_entity` tool (with JSON Schema validation)
- Implement `query_entities` tool (with JSONB filtering)
- Implement `update_entity` tool (with optimistic locking)

**Tool Specifications**:

**register_entity_type**:
```python
@mcp.tool()
async def register_entity_type(
    project_id: str,
    type_name: str,
    schema: dict,
    description: str | None = None
) -> dict:
    """Register entity type with JSON Schema."""
    # 1. Validate schema is valid JSON Schema Draft 7
    # 2. Validate type_name is unique in project (case-insensitive)
    # 3. Insert into entity_types table
    # 4. Return entity_type_id and schema
```

**create_entity**:
```python
@mcp.tool()
async def create_entity(
    project_id: str,
    entity_type: str,
    name: str,
    data: dict,
    metadata: dict | None = None
) -> dict:
    """Create entity instance validated against type schema."""
    # 1. Fetch entity type schema from entity_types
    # 2. Validate data against schema using jsonschema library
    # 3. Validate name is unique for (entity_type, name)
    # 4. Insert into entities table (JSONB column)
    # 5. Return entity_id and version=1
```

**query_entities**:
```python
@mcp.tool()
async def query_entities(
    project_id: str,
    entity_type: str,
    filters: dict | None = None,
    limit: int = 10,
    offset: int = 0
) -> dict:
    """Query entities with JSONB filtering."""
    # 1. Build WHERE clause with JSONB @> operator
    # 2. Apply pagination (limit, offset)
    # 3. Order by updated_at DESC
    # 4. Return entities and total_count
```

**update_entity**:
```python
@mcp.tool()
async def update_entity(
    entity_id: str,
    version: int,
    data_updates: dict,
    metadata_updates: dict | None = None
) -> dict:
    """Update entity with optimistic locking."""
    # 1. Fetch current entity
    # 2. Check version matches (optimistic locking)
    # 3. Merge data_updates with existing data
    # 4. Validate merged data against entity type schema
    # 5. Update entities table, increment version
    # 6. Return updated entity
```

**Acceptance Criteria**:
- JSON Schema validation works for all data types
- JSONB queries with GIN index perform in <100ms
- Optimistic locking prevents concurrent update conflicts
- Commission and game dev projects work independently

**Git Strategy**:
- Branch: `009-entity-system`
- Commits:
  - `feat(entities): implement register_entity_type tool`
  - `feat(entities): implement create_entity with JSON Schema validation`
  - `feat(entities): implement query_entities with JSONB filtering`
  - `feat(entities): implement update_entity with optimistic locking`

---

#### 4. Deployment Tracking (Week 8, Day 5)

**Tasks**:
- Implement `record_deployment` tool
- Implement `list_deployments` tool (with relationships)

**Tool Specifications**:

**record_deployment**:
```python
@mcp.tool()
async def record_deployment(
    project_id: str,
    deployed_at: str,  # ISO 8601
    metadata: dict,
    entity_ids: list[str] | None = None,
    work_item_ids: list[str] | None = None
) -> dict:
    """Record deployment event with relationships."""
    # 1. Insert into deployments table
    # 2. If entity_ids: Insert into deployment_entities (many-to-many)
    # 3. If work_item_ids: Insert into deployment_work_items (many-to-many)
    # 4. Return deployment_id
```

**list_deployments**:
```python
@mcp.tool()
async def list_deployments(
    project_id: str,
    include_relationships: bool = True,
    limit: int = 10
) -> dict:
    """List deployments with entities and work items."""
    # 1. Query deployments ordered by deployed_at DESC
    # 2. If include_relationships: Join entities and work_items
    # 3. Return deployments with relationships
```

**Acceptance Criteria**:
- Deployments link to entities and work items
- Metadata stores PR URL, test results, constitutional compliance

**Git Strategy**:
- Branch: `010-deployment-tracking`
- Commits:
  - `feat(deployments): implement record_deployment tool`
  - `feat(deployments): implement list_deployments with relationships`

---

#### 5. Integration Testing (Week 9, Days 1-2)

**Tasks**:
- Write end-to-end tests for complete workflows
- Test commission work scenario (vendors)
- Test game dev scenario (mechanics)
- Performance testing (100+ projects, 10K+ entities)

**Test Scenarios**:

**Commission Work E2E**:
```python
@pytest.mark.asyncio
async def test_commission_workflow():
    """Test complete commission work workflow."""
    # 1. Create commission project
    project = await create_project("commission-work", "Invoice extraction")

    # 2. Switch to commission project
    await switch_active_project(project["project_id"])

    # 3. Register vendor entity type
    await register_entity_type(project["project_id"], "vendor", schema={...})

    # 4. Create vendor entities
    epson = await create_entity(project["project_id"], "vendor", "EPSON", data={...})
    canon = await create_entity(project["project_id"], "vendor", "Canon", data={...})

    # 5. Query broken vendors
    broken = await query_entities(project["project_id"], "vendor", filters={"data": {"status": "broken"}})
    assert len(broken) == 1  # Only Canon is broken

    # 6. Update Canon to operational
    await update_entity(canon["entity_id"], version=1, data_updates={"status": "operational"})

    # 7. Record deployment
    await record_deployment(
        project["project_id"],
        deployed_at="2025-10-11T16:00:00Z",
        metadata={"pr_url": "...", "tests_passed": True},
        entity_ids=[epson["entity_id"], canon["entity_id"]]
    )
```

**Game Dev E2E**:
```python
@pytest.mark.asyncio
async def test_game_dev_workflow():
    """Test complete game dev workflow."""
    # Similar to commission workflow but with game_mechanic entities
```

**Performance Test**:
```python
@pytest.mark.asyncio
async def test_100_projects_performance():
    """Test performance with 100+ projects."""
    # 1. Create 100 projects
    projects = [await create_project(f"project-{i}", "Test") for i in range(100)]

    # 2. Switch between projects (measure latency)
    start = time.time()
    for project in projects[:10]:
        await switch_active_project(project["project_id"])
    elapsed = time.time() - start
    assert elapsed / 10 < 0.05  # <50ms per switch
```

**Acceptance Criteria**:
- End-to-end tests pass for both domains
- Performance tests validate <50ms project switching
- Isolation tests confirm no cross-project leaks

**Git Strategy**:
- Branch: `011-integration-testing`
- Commits:
  - `test(e2e): add commission work end-to-end test`
  - `test(e2e): add game dev end-to-end test`
  - `test(perf): add 100+ project performance test`

---

#### 6. Documentation and Release (Week 9, Days 3-5)

**Tasks**:
- Update README with complete feature list
- Document all MCP tools (Phase 1 + Phase 3)
- Write entity system guide with examples
- Create deployment guide

**Deliverables**:
- `README.md`: Updated with complete feature list
- `docs/entity-system.md`: Entity system guide with examples
- `docs/deployment.md`: Production deployment guide
- `CHANGELOG.md`: Version history and breaking changes

**Acceptance Criteria**:
- Documentation covers all features
- Examples demonstrate commission + game dev workflows
- Deployment guide includes PostgreSQL setup

**Git Strategy**:
- Branch: `012-documentation-release`
- Commits:
  - `docs(readme): update with complete feature list`
  - `docs(entity-system): add entity system guide with examples`
  - `docs(deployment): add production deployment guide`
  - `chore(release): prepare v1.0.0 release`

---

### Phase 3 Acceptance Criteria

**Functional**:
- [ ] Hierarchical work items up to 5 levels
- [ ] Task management with git integration
- [ ] Generic entity system (commission + game dev domains)
- [ ] Deployment tracking with relationships

**Performance**:
- [ ] Work item hierarchy queries: <200ms p95 latency
- [ ] Entity queries (10K+ entities): <100ms p95 latency
- [ ] Task listing (summary mode): <150ms p95 latency

**Quality**:
- [ ] >90% test coverage across all features
- [ ] End-to-end tests pass for commission and game dev
- [ ] Performance tests validate latency targets
- [ ] mypy --strict passes with zero errors

**Integration**:
- [ ] codebase-mcp can query active project
- [ ] workflow-mcp can query codebase-mcp for code references
- [ ] Multi-MCP workflows work smoothly

---

## Git Strategy Summary

### Branch Naming

- Feature branches: `###-descriptive-name` (e.g., `001-project-structure`)
- Branch from `main` or `master`
- Merge via pull request after review

### Commit Strategy

- **Micro-commits**: Commit after each completed task
- **Conventional Commits**: `type(scope): description`
  - Types: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`
  - Scope: `database`, `tools`, `entities`, `tasks`, `work-items`
- **Atomic commits**: One logical change per commit
- **Working state**: All tests pass at every commit

### Example Workflow

```bash
# Phase 1: Project structure
git checkout -b 001-project-structure
git add .
git commit -m "chore(setup): initialize Python project with Poetry"
git commit -m "chore(config): add mypy, ruff, pytest configuration"
git commit -m "chore(structure): create directory structure and stub files"
git commit -m "feat(database): add registry database schema and connection pool"
git push origin 001-project-structure
# Create PR, review, merge

# Phase 1: Project database template
git checkout -b 002-project-database-template
git commit -m "feat(database): add project database schema template"
git commit -m "feat(database): implement database creation with schema initialization"
git push origin 002-project-database-template
# Create PR, review, merge

# Phase 3: Entity system
git checkout -b 009-entity-system
git commit -m "feat(entities): implement register_entity_type tool"
git commit -m "feat(entities): implement create_entity with JSON Schema validation"
git commit -m "feat(entities): implement query_entities with JSONB filtering"
git commit -m "feat(entities): implement update_entity with optimistic locking"
git push origin 009-entity-system
# Create PR, review, merge
```

---

## Testing Strategy

### Test Pyramid

```
       /\
      /  \     E2E Tests (5%)
     /----\    Integration Tests (25%)
    /------\   Unit Tests (70%)
   /--------\
```

### Test Categories

**Unit Tests** (70%):
- Pydantic model validation
- JSON Schema validation
- Query building logic
- Utility functions

**Integration Tests** (25%):
- Database CRUD operations
- Connection pool management
- Multi-project isolation
- MCP tool invocations

**End-to-End Tests** (5%):
- Complete workflows (commission, game dev)
- Cross-MCP integration
- Performance benchmarks

### CI Pipeline

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -e ".[dev]"
      - run: mypy --strict workflow_mcp
      - run: ruff check .
      - run: pytest --cov=workflow_mcp --cov-report=xml
      - run: pytest tests/protocol  # MCP compliance tests
```

**Success Criteria**:
- All tests pass (<5 min total)
- >90% line coverage
- mypy --strict passes
- ruff linting passes

---

## Summary

**Phase 1 (Weeks 1-3)**: Core project management foundation
- Registry database + connection pooling
- create_project, switch_active_project, get_active_project, list_projects
- <50ms project switching, <100ms project listing
- codebase-mcp can query active project

**Phase 3 (Weeks 7-9)**: Complete workflow management
- Hierarchical work items (5 levels deep, <200ms queries)
- Task management with git integration
- Generic entity system (commission + game dev domains)
- Deployment tracking with relationships
- <100ms entity queries, <150ms task listing

**Git Strategy**:
- Branch-per-feature with micro-commits
- Conventional Commits format
- Atomic commits with working state

**Testing Strategy**:
- 70% unit tests, 25% integration tests, 5% E2E tests
- >90% coverage, CI runs full suite in <5 min
- Isolation and performance tests validate quality

This phased approach delivers a production-ready, multi-project workflow management system with complete type safety, performance guarantees, and domain flexibility.
