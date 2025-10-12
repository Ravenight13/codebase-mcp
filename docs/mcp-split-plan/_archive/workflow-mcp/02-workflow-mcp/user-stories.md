# Workflow MCP User Stories

## Overview

These user stories capture the needs of developers using AI coding assistants (Claude Code, Cursor, etc.) to manage multiple projects with domain-specific entities and work items.

Stories are organized by feature area with acceptance criteria and priority (P0 = MVP, P1 = Core, P2 = Complete).

---

## Project Workspace Management

### US-001: Create New Project Workspace (P0)
**As a** developer starting a new commission project
**I need** to create an isolated project workspace with its own database
**So that** my commission work data never mixes with my game development data

**Acceptance Criteria**:
- Command: `create_project(name, description, metadata)`
- Creates new PostgreSQL database: `workflow_project_<uuid>`
- Initializes schema (work_items, entities, entity_types, deployments, tasks)
- Registers project in workflow_registry.projects table
- Returns project_id for subsequent operations
- Performance: <1 second for complete project setup

**Example**:
```python
project = create_project(
    name="invoice-extractor-commission",
    description="Commission work for PDF invoice extraction",
    metadata={"client": "Acme Corp", "contract_id": "C-2025-001"}
)
# Returns: {"project_id": "uuid", "database": "workflow_project_<uuid>", ...}
```

---

### US-002: Switch Active Project Context (P0)
**As a** developer working on multiple projects
**I need** to quickly switch between commission and game dev contexts
**So that** AI assistants operate on the correct project's data

**Acceptance Criteria**:
- Command: `switch_active_project(project_id)`
- Updates workflow_registry.active_project_config (singleton table)
- Selects connection pool for target project database
- Performance: <50ms latency for context switch
- Validates project exists before switching
- Returns confirmation with project name

**Example**:
```python
# Switch from commission work to game dev
switch_active_project("ttrpg-core-uuid")
# AI assistant now queries/creates entities in game dev database
```

---

### US-003: Query Active Project Context (P0)
**As a** codebase-mcp server
**I need** to query which project is currently active
**So that** I can tag indexed code chunks with the correct project context

**Acceptance Criteria**:
- Command: `get_active_project()`
- Returns project metadata (id, name, description, metadata)
- Performance: <10ms latency (registry database query)
- Works even if no project is active (returns null)
- Cached in-memory with invalidation on switch

**Example**:
```python
active = get_active_project()
# Returns: {"project_id": "uuid", "name": "invoice-extractor-commission", ...}
```

---

### US-004: List All Projects (P0)
**As a** developer
**I need** to see all my project workspaces
**So that** I can choose which one to activate

**Acceptance Criteria**:
- Command: `list_projects(include_inactive=False)`
- Returns projects sorted by last_activated_at descending
- Includes metadata (name, description, created_at, entity_type_count, work_item_count)
- Performance: <100ms for 100+ projects
- Optionally filters active vs inactive projects

**Example**:
```python
projects = list_projects()
# Returns: [
#   {"project_id": "...", "name": "invoice-extractor-commission", "last_activated_at": "2025-10-10T14:00:00Z"},
#   {"project_id": "...", "name": "ttrpg-core-system", "last_activated_at": "2025-10-08T09:30:00Z"}
# ]
```

---

## Generic Entity System

### US-005: Register Domain-Specific Entity Type (P1)
**As a** developer starting commission work
**I need** to register a "vendor" entity type with its validation schema
**So that** I can track vendor extractor status without hardcoded tables

**Acceptance Criteria**:
- Command: `register_entity_type(project_id, type_name, schema, description)`
- Stores JSON Schema in project's entity_types table
- Validates schema is valid JSON Schema Draft 7
- Enforces unique type names per project (case-insensitive)
- Returns entity_type_id and parsed schema
- Performance: <100ms

**Example**:
```python
register_entity_type(
    project_id="commission-uuid",
    type_name="vendor",
    description="Invoice extraction vendor status tracking",
    schema={
        "type": "object",
        "properties": {
            "status": {"enum": ["operational", "broken"]},
            "extractor_version": {"type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$"},
            "supports_html": {"type": "boolean"},
            "supports_pdf": {"type": "boolean"},
            "last_test_at": {"type": "string", "format": "date-time"}
        },
        "required": ["status", "extractor_version"]
    }
)
```

---

### US-006: Create Entity Instance (P1)
**As a** developer implementing a vendor extractor
**I need** to create an EPSON vendor entity with operational status
**So that** my AI assistant can track which vendors are working

**Acceptance Criteria**:
- Command: `create_entity(project_id, entity_type, name, data, metadata)`
- Validates data against registered entity type's JSON Schema
- Stores in project's entities table (JSONB column)
- Enforces unique names per (project_id, entity_type)
- Returns entity_id and version=1 (for optimistic locking)
- Performance: <100ms including validation

**Example**:
```python
entity = create_entity(
    project_id="commission-uuid",
    entity_type="vendor",
    name="EPSON",
    data={
        "status": "operational",
        "extractor_version": "1.2.0",
        "supports_html": True,
        "supports_pdf": False
    }
)
# Returns: {"entity_id": "uuid", "version": 1, ...}
```

---

### US-007: Query Entities by Type and Filters (P1)
**As a** developer debugging broken extractors
**I need** to query all vendors with status="broken"
**So that** I know which extractors need fixing

**Acceptance Criteria**:
- Command: `query_entities(project_id, entity_type, filters, limit, offset)`
- Uses JSONB containment operator (@>) for filtering
- Supports nested property queries (e.g., data->>'status' = 'broken')
- Returns entities sorted by updated_at descending
- Performance: <100ms for 10,000+ entities (GIN index)
- Token-efficient: returns only requested fields

**Example**:
```python
broken_vendors = query_entities(
    project_id="commission-uuid",
    entity_type="vendor",
    filters={"data": {"status": "broken"}},
    limit=10
)
# Returns: [{"entity_id": "...", "name": "EPSON", "data": {"status": "broken", ...}}, ...]
```

---

### US-008: Update Entity with Optimistic Locking (P1)
**As a** developer fixing a vendor extractor
**I need** to update vendor status from "broken" to "operational" with version check
**So that** concurrent updates don't create race conditions

**Acceptance Criteria**:
- Command: `update_entity(entity_id, version, data_updates, metadata_updates)`
- Validates data_updates against entity type's JSON Schema
- Checks version matches current version (optimistic locking)
- Returns error if version mismatch (concurrent update detected)
- Increments version on successful update
- Performance: <100ms

**Example**:
```python
update_entity(
    entity_id="epson-uuid",
    version=3,  # Must match current version
    data_updates={"status": "operational", "extractor_version": "1.2.1"}
)
# Returns: {"entity_id": "...", "version": 4, ...}
# OR raises: VersionMismatchError if version != 3
```

---

### US-009: Register Game Mechanic Entity Type (P1)
**As a** game developer working on a TTRPG system
**I need** to register a "game_mechanic" entity type
**So that** I can track combat, skill check, and magic system designs

**Acceptance Criteria**:
- Same as US-005 but for different domain (game_mechanic vs vendor)
- Demonstrates generic entity system works for any domain
- Game dev project completely isolated from commission project
- No code changes required to support new domain

**Example**:
```python
register_entity_type(
    project_id="ttrpg-uuid",
    type_name="game_mechanic",
    description="Core game system mechanics tracking",
    schema={
        "type": "object",
        "properties": {
            "mechanic_type": {"enum": ["combat", "skill", "magic", "social"]},
            "implementation_status": {"enum": ["design", "prototype", "playtesting", "complete"]},
            "complexity": {"type": "integer", "minimum": 1, "maximum": 5},
            "dependencies": {"type": "array", "items": {"type": "string"}},
            "playtests_passed": {"type": "integer", "minimum": 0}
        },
        "required": ["mechanic_type", "implementation_status", "complexity"]
    }
)
```

---

### US-010: Create Game Mechanic Entity (P1)
**As a** game developer
**I need** to create a "Skill Check System" mechanic entity
**So that** I can track its implementation status and playtesting progress

**Acceptance Criteria**:
- Same as US-006 but for game_mechanic entity type
- Validates against game_mechanic JSON Schema
- Demonstrates multi-domain support with same codebase

**Example**:
```python
mechanic = create_entity(
    project_id="ttrpg-uuid",
    entity_type="game_mechanic",
    name="Skill Check System",
    data={
        "mechanic_type": "skill",
        "implementation_status": "prototype",
        "complexity": 3,
        "dependencies": ["Attribute System", "Dice Rolling"],
        "playtests_passed": 2
    }
)
```

---

## Hierarchical Work Items

### US-011: Create Root-Level Work Item (P2)
**As a** developer starting a feature
**I need** to create a project-level work item
**So that** I can organize sessions and tasks under it

**Acceptance Criteria**:
- Command: `create_work_item(project_id, item_type, title, metadata, parent_id=None)`
- Supports types: project, session, task, research
- Type-specific metadata validated via Pydantic
- parent_id=None creates root-level item
- Returns work_item_id and materialized path
- Performance: <150ms

**Example**:
```python
work_item = create_work_item(
    project_id="commission-uuid",
    item_type="project",
    title="Invoice Extraction Feature",
    metadata={
        "token_budget": 200000,
        "specification_file": "specs/001-invoice-extraction/spec.md"
    }
)
# Returns: {"work_item_id": "uuid", "path": "/uuid/", ...}
```

---

### US-012: Create Child Work Item (P2)
**As a** developer breaking down a project
**I need** to create session and task work items under the project
**So that** I can track implementation in a hierarchy

**Acceptance Criteria**:
- Same as US-011 but with parent_id specified
- Validates parent exists and is not deleted
- Validates hierarchy depth ≤ 5 levels
- Builds materialized path (/parent_path/child_id/)
- Updates parent's children list

**Example**:
```python
session = create_work_item(
    project_id="commission-uuid",
    item_type="session",
    title="Implement EPSON Extractor",
    parent_id="project-work-item-uuid",
    metadata={
        "token_usage": 45000,
        "started_at": "2025-10-10T09:00:00Z"
    }
)
# Returns: {"work_item_id": "uuid", "path": "/project-uuid/session-uuid/", ...}
```

---

### US-013: Query Work Item with Full Hierarchy (P2)
**As a** developer reviewing progress
**I need** to query a work item with all its children up to 5 levels
**So that** I can see the complete feature breakdown

**Acceptance Criteria**:
- Command: `query_work_item(work_item_id, include_children=True, include_dependencies=True)`
- Returns work item with parent chain (ancestors via materialized path)
- Returns children recursively up to 5 levels (CTE)
- Includes dependency relationships (blocked-by, depends-on)
- Performance: <10ms for 5 levels
- Token-efficient: only includes requested fields

**Example**:
```python
hierarchy = query_work_item("project-work-item-uuid", include_children=True)
# Returns: {
#   "work_item_id": "...",
#   "title": "Invoice Extraction Feature",
#   "children": [
#     {"work_item_id": "...", "title": "Implement EPSON Extractor", "children": [...]},
#     {"work_item_id": "...", "title": "Implement Canon Extractor", "children": [...]}
#   ]
# }
```

---

### US-014: Update Work Item Status (P2)
**As a** developer completing a task
**I need** to mark a work item as "completed"
**So that** AI assistants know which tasks are done

**Acceptance Criteria**:
- Command: `update_work_item(work_item_id, version, status, title, metadata)`
- Supports partial updates (only provided fields updated)
- Status enum: active, completed, blocked
- Optimistic locking via version parameter
- Performance: <150ms

**Example**:
```python
update_work_item(
    work_item_id="session-uuid",
    version=2,
    status="completed",
    metadata={"completed_at": "2025-10-10T17:00:00Z", "token_usage": 48500}
)
```

---

### US-015: Soft Delete Work Item (P2)
**As a** developer cleaning up abandoned work
**I need** to soft delete a work item and its children
**So that** they don't appear in queries but remain in audit trail

**Acceptance Criteria**:
- Command: `update_work_item(work_item_id, version, deleted_at=NOW())`
- Sets deleted_at timestamp (soft delete)
- Recursively marks children as deleted (CTE)
- Excluded from list_work_items by default
- Can be included with include_deleted=True
- Performance: <200ms for 100 descendants

**Example**:
```python
update_work_item(
    work_item_id="abandoned-session-uuid",
    version=1,
    deleted_at="2025-10-11T12:00:00Z"
)
```

---

## Task Management

### US-016: Create Task with Planning References (P2)
**As a** developer implementing a feature
**I need** to create a task linked to spec.md and plan.md
**So that** AI assistants have context for implementation

**Acceptance Criteria**:
- Command: `create_task(project_id, title, description, planning_references)`
- Creates task with "need to be done" status
- planning_references: array of relative file paths
- Returns task_id
- Performance: <150ms

**Example**:
```python
task = create_task(
    project_id="commission-uuid",
    title="Implement EPSON HTML parser",
    description="Parse EPSON invoice HTML and extract line items",
    planning_references=[
        "specs/001-invoice-extraction/spec.md",
        "specs/001-invoice-extraction/plan.md"
    ]
)
```

---

### US-017: Associate Task with Git Branch and Commit (P2)
**As a** developer implementing a task
**I need** to associate the task with my feature branch and commit
**So that** deployment history links to implementation details

**Acceptance Criteria**:
- Command: `update_task(task_id, status, branch, commit)`
- Creates task_branches and task_commits records
- Validates commit is 40-character hex string
- Many-to-many: tasks can have multiple branches/commits
- Performance: <150ms

**Example**:
```python
update_task(
    task_id="task-uuid",
    status="in-progress",
    branch="001-invoice-extraction",
    commit="a1b2c3d4e5f6789012345678901234567890abcd"
)
```

---

### US-018: List Tasks with Filters (P2)
**As a** developer planning my day
**I need** to see all "need to be done" tasks in the active project
**So that** I know what to work on next

**Acceptance Criteria**:
- Command: `list_tasks(project_id, status, branch, limit, full_details=False)`
- Filters: status (need to be done, in-progress, complete), branch
- Default: Returns TaskSummary (5 fields, ~120 tokens/task)
- full_details=True: Returns full TaskResponse (10 fields, ~800 tokens/task)
- Performance: <200ms for 100+ tasks

**Example**:
```python
tasks = list_tasks(project_id="commission-uuid", status="need to be done", limit=10)
# Returns: [
#   {"task_id": "...", "title": "Implement EPSON parser", "status": "need to be done", ...},
#   {"task_id": "...", "title": "Add Canon support", "status": "need to be done", ...}
# ]
```

---

## Deployment Tracking

### US-019: Record Deployment Event (P2)
**As a** developer deploying to production
**I need** to record deployment details with PR and test results
**So that** I have an audit trail of what was deployed when

**Acceptance Criteria**:
- Command: `record_deployment(project_id, deployed_at, metadata, vendor_ids, work_item_ids)`
- metadata: PR URL, commit hash, test results, constitutional compliance
- Creates deployment_vendors and deployment_work_items junction records
- Returns deployment_id
- Performance: <200ms

**Example**:
```python
deployment = record_deployment(
    project_id="commission-uuid",
    deployed_at="2025-10-11T16:00:00Z",
    metadata={
        "pr_url": "https://github.com/user/repo/pull/42",
        "commit_hash": "a1b2c3d4...",
        "tests_passed": True,
        "constitutional_compliance": True,
        "test_summary": "All 127 tests passed"
    },
    vendor_ids=["epson-entity-uuid", "canon-entity-uuid"],
    work_item_ids=["session-uuid"]
)
```

---

### US-020: Query Deployments with Relationships (P2)
**As a** developer investigating a production issue
**I need** to see which vendors and work items were in the last deployment
**So that** I can identify what changed

**Acceptance Criteria**:
- Command: `list_deployments(project_id, limit, include_relationships=True)`
- Returns deployments sorted by deployed_at descending
- Includes affected vendors and work items (via junction tables)
- Performance: <200ms for 100+ deployments

**Example**:
```python
deployments = list_deployments(project_id="commission-uuid", limit=5, include_relationships=True)
# Returns: [
#   {
#     "deployment_id": "...",
#     "deployed_at": "2025-10-11T16:00:00Z",
#     "metadata": {"pr_url": "...", ...},
#     "vendors": [{"entity_id": "...", "name": "EPSON"}],
#     "work_items": [{"work_item_id": "...", "title": "Implement EPSON Extractor"}]
#   }
# ]
```

---

## Cross-MCP Integration

### US-021: codebase-mcp Queries Active Project (P0)
**As a** codebase-mcp server indexing code
**I need** to query workflow-mcp for the active project
**So that** I can tag code chunks with project context

**Acceptance Criteria**:
- codebase-mcp calls workflow-mcp's `get_active_project()` tool
- Returns project metadata or null if no active project
- Performance: <10ms (in-memory cache)
- No authentication required (local IPC)

**Example**:
```python
# In codebase-mcp during indexing
active_project = await workflow_mcp_client.get_active_project()
if active_project:
    chunk.project_id = active_project["project_id"]
```

---

### US-022: workflow-mcp Queries Code References (P2)
**As a** developer creating a task
**I need** workflow-mcp to find related code via codebase-mcp
**So that** task descriptions include relevant file references

**Acceptance Criteria**:
- workflow-mcp calls codebase-mcp's `search_code()` tool
- Filters results by active project_id (if codebase-mcp supports)
- Includes code references in task metadata
- Performance: <500ms (depends on codebase-mcp)

**Example**:
```python
# In workflow-mcp when creating task
code_refs = await codebase_mcp_client.search_code(
    query="EPSON invoice parser",
    project_id=active_project_id
)
task_metadata["code_references"] = code_refs
```

---

## Priority Summary

**P0 (MVP)**: Project workspace management (US-001 to US-004)
- Must have for multi-project isolation
- Foundation for all other features

**P1 (Core)**: Generic entity system (US-005 to US-010)
- Critical for commission work and game dev support
- Validates generic entity architecture

**P2 (Complete)**: Work items, tasks, deployments (US-011 to US-022)
- Full project management capabilities
- Cross-MCP integration

---

*These user stories define the complete scope of workflow-mcp's functionality across MVP, Core, and Complete phases.*
