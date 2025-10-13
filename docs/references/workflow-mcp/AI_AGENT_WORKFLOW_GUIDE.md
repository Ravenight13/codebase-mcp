# AI Agent Workflow Integration Guide

**Audience**: Claude Code instances and AI agents using Spec-Kit framework  
**Purpose**: Leverage workflow-mcp MCP tools for enhanced project management  
**Status**: Optional enhancement - use when project complexity warrants  
**Framework**: [Spec-Kit](https://github.com/github/spec-kit)

---

## Quick Start (5 Commands)

```python
# 1. List available tools (verify connection)
# Ask: "List all workflow-mcp tools"

# 2. Create project for current work
create_project(
    name="my-feature-name",
    description="Brief description from spec.md"
)

# 3. Switch to project
switch_project(project_id="<id-from-step-2>")

# 4. Create root work item
create_work_item(
    item_type="project",
    title="Feature Name",
    description="From spec.md summary"
)

# 5. Query to verify
query_work_items(status="active")
```

**Expected Time**: 2-3 minutes to set up project tracking

---

## When to Use Workflow-MCP

### ✅ **Use When:**
- Multi-session feature development (3+ sessions)
- Complex task hierarchies (parent/child relationships)
- Tracking deployments across environments
- Custom domain entities need management
- Work blocked by dependencies
- Multiple projects active (context switching)

### ❌ **Skip When:**
- Simple single-session tasks
- One-off bug fixes
- Read-only exploration
- tasks.md already provides sufficient tracking

**Rule of Thumb**: If the spec has >5 tasks in tasks.md, consider using workflow-mcp

---

## Spec-Kit Integration Patterns

### Pattern 1: After `/speckit.specify` - Create Project

**When**: Immediately after specification is written  
**Purpose**: Establish project tracking for the feature

```python
# Read spec.md to get feature name and description
spec_content = read_file(".specify/specs/NNN/spec.md")

# Extract name from spec (usually first heading)
project = create_project(
    name="NNN-feature-name",  # Use spec number + name
    description="One-line summary from spec.md"
)

# Switch to it
switch_project(project_id=project["id"])

# Create root work item
root_work_item = create_work_item(
    item_type="project",
    title="Spec NNN: Feature Name",
    description="Extracted from spec.md Goals section",
    status="active"
)
```

**Result**: Project context established, ready for task tracking

---

### Pattern 2: During `/speckit.implement` - Track Work Items

**When**: Implementing complex tasks from tasks.md  
**Purpose**: Track progress, manage dependencies

**Option A: Create Session for Each Implementation Phase**
```python
# For each major phase (e.g., "Backend API", "Frontend UI")
session = create_work_item(
    item_type="session",
    title="Backend API Implementation",
    parent_id=root_work_item["id"],
    status="active"
)
```

**Option B: Create Tasks for Multi-Step Work**
```python
# For complex tasks that span multiple commits/sessions
task = create_work_item(
    item_type="task",
    title="Implement user authentication flow",
    description="From tasks.md line 15",
    parent_id=session["id"],
    status="active"
)

# Update as you progress
update_work_item(
    work_item_id=task["id"],
    status="completed"
)
```

**When NOT to Create Work Items**:
- Simple tasks (<30min)
- Tasks already tracked well in tasks.md
- One-off exploratory work

**Key Insight**: tasks.md is the source of truth. Work items supplement for complexity, not replace.

---

### Pattern 3: Track Dependencies Between Tasks

**When**: Task blocked by another task  
**Purpose**: Make blockers visible, query blocked items

```python
# Task A depends on Task B (Task A is blocked until B completes)
add_work_item_dependency(
    work_item_id=task_a["id"],
    depends_on_id=task_b["id"],
    dependency_type="blocks"  # blocks, relates_to, or duplicates
)

# Query blocked items
blocked = list_blocked_work_items()
# Returns: Tasks waiting on dependencies
```

**Circular Detection**: System prevents circular dependencies automatically

---

### Pattern 4: Record Deployments

**When**: Merging to main, releasing, deploying to staging/prod  
**Purpose**: Track what's deployed where, link code to work

```python
# After git commit, before/after deployment
record_deployment(
    commit_sha="abc123def456",  # From git log
    branch="main",
    environment="production",  # production, staging, dev
    status="deployed",  # pending, deployed, failed, rolled_back
    commit_message="Implement feature X",
    author_name="Your Name",
    author_email="your@email.com",
    deployed_at="2025-01-15T10:30:00Z",  # ISO 8601
    metadata={"release_notes": "..."},
    work_item_ids=[task["id"]]  # Link to work items
)

# Query deployments
prod_deployments = list_deployments(environment="production")
```

**Use Cases**:
- Release tracking
- Deployment history
- Rollback reference
- What's in prod vs staging

---

## Available Tools (21 Total)

### 1. Project Management (4 tools)

**create_project**(name, description)
- Creates new project with isolated database
- Returns: project metadata with `id` and `database_name`

**switch_project**(project_id)
- Switches active project context (all tools use active project)
- Returns: success message

**get_active_project**()
- Returns: Currently active project or null

**list_projects**(limit=20, offset=0)
- Returns: Paginated project list

**Example Use**:
```python
# Multi-project scenario
project_a = create_project("feature-a", "User authentication")
project_b = create_project("feature-b", "Payment processing")

switch_project(project_a["id"])  # Work on feature A
# ... create work items, entities ...

switch_project(project_b["id"])  # Switch to feature B
# ... different work items, entities (isolated) ...
```

---

### 2. Work Item Management (7 tools)

**5-Level Hierarchy**:
1. **project** - Top level (feature/epic)
2. **session** - Development session/phase
3. **task** - Specific work item
4. **research** - Investigation/exploration
5. **subtask** - Task breakdown

**create_work_item**(item_type, title, description, status, parent_id)
- item_type: "project", "session", "task", "research", "subtask"
- status: "planned", "active", "completed", "blocked"
- parent_id: Optional, creates hierarchy
- Returns: work item with `id`, `hierarchy_level`, `materialized_path`

**update_work_item**(work_item_id, title, description, status)
- Updates fields (only provide fields to change)
- Auto-sets `completed_at` when status="completed"
- Returns: updated work item

**query_work_items**(status, item_type, parent_id, include_descendants)
- Filter by any combination
- include_descendants: Get full subtree (recursive)
- Returns: {work_items: [...], count: N}

**get_work_item_hierarchy**(work_item_id)
- Returns: {work_item, ancestors, children, descendants}
- Full context for a work item

**delete_work_item**(work_item_id, confirmed)
- Soft delete (confirmed must be True)
- Returns: success message

**add_work_item_dependency**(work_item_id, depends_on_id, dependency_type)
- dependency_type: "blocks", "relates_to", "duplicates"
- Circular dependency detection
- Returns: dependency metadata

**list_blocked_work_items**()
- Returns: All work items blocked by dependencies
- Useful for unblocking workflow

**Example: Complete Hierarchy**:
```python
# Create full hierarchy for complex feature
root = create_work_item(
    item_type="project",
    title="User Authentication System",
    status="active"
)

session = create_work_item(
    item_type="session",
    title="Backend API Development",
    parent_id=root["id"],
    status="active"
)

task = create_work_item(
    item_type="task",
    title="Implement JWT token generation",
    parent_id=session["id"],
    status="active"
)

subtask = create_work_item(
    item_type="subtask",
    title="Add token expiration logic",
    parent_id=task["id"],
    status="completed"
)

# Query full tree
hierarchy = get_work_item_hierarchy(task["id"])
# Returns: ancestors=[root, session], children=[subtask], descendants=[subtask]
```

---

### 3. Entity Management (6 tools)

**Purpose**: Track custom domain entities (not work items)

**register_entity_type**(type_name, schema, description)
- schema: JSON Schema for validation
- Returns: entity type metadata

**create_entity**(entity_type, name, data, tags)
- data: JSONB object (validated against schema)
- tags: Array of strings for filtering
- Returns: entity with `id`, `version`

**query_entities**(entity_type, filter, tags, include_deleted)
- filter: JSONB containment query (e.g., {"status": "active"})
- tags: Array filter (AND logic)
- Returns: Array of entities

**update_entity**(entity_id, data, current_version)
- current_version: For optimistic locking
- Returns: entity with incremented version

**delete_entity**(entity_id, confirmed)
- Soft delete (confirmed must be True)
- Returns: success message

**update_entity_type_schema**(type_name, new_schema, validate_existing)
- Schema evolution (backward compatible)
- validate_existing: Check all entities pass new schema
- Returns: updated entity type

**Example Use Case: Track Vendor Extractors**:
```python
# Register vendor entity type
register_entity_type(
    type_name="vendor_extractor",
    schema={
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["operational", "broken"]},
            "version": {"type": "string"},
            "last_tested": {"type": "string", "format": "date-time"}
        },
        "required": ["status", "version"]
    },
    description="PDF vendor extractors"
)

# Create vendor entities
epson = create_entity(
    entity_type="vendor_extractor",
    name="EPSON",
    data={"status": "broken", "version": "2.3.0"},
    tags=["pdf", "high-priority"]
)

# Query broken vendors
broken = query_entities(
    entity_type="vendor_extractor",
    filter={"status": "broken"},
    tags=["high-priority"]
)
```

---

### 4. Deployment Tracking (3 tools)

**record_deployment**(commit_sha, branch, environment, status, ...)
- See Pattern 4 above for full signature
- Returns: deployment metadata with relationships

**list_deployments**(environment, limit, offset)
- environment: Optional filter ("production", "staging", "dev")
- Returns: {deployments: [...], total, limit, offset}

**get_deployment**(deployment_id)
- Returns: Single deployment with all relationships

**Example: Release Workflow**:
```python
# Before deployment
deployment = record_deployment(
    commit_sha="abc123",
    branch="main",
    environment="staging",
    status="pending"
)

# After successful deployment
update_deployment = record_deployment(
    commit_sha="abc123",
    branch="main",
    environment="staging",
    status="deployed",
    deployed_at=datetime.now().isoformat()
)

# Promote to production
prod_deployment = record_deployment(
    commit_sha="abc123",
    branch="main",
    environment="production",
    status="deployed"
)

# Query production history
prod_history = list_deployments(environment="production")
```

---

## Response Formats

**Success Response** (most tools):
```json
{
  "id": "uuid",
  "field1": "value1",
  "created_at": "2025-01-15T10:30:00Z",
  ...
}
```

**List Response**:
```json
{
  "items_key": [...],  // work_items, deployments, projects, etc.
  "count": 10,
  "total": 100,
  "limit": 20,
  "offset": 0
}
```

**Error Response**:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error",
    "data": {"additional": "context"}
  }
}
```

**Common Error Codes**:
- `NO_ACTIVE_PROJECT`: Call `switch_project()` first
- `VALIDATION_ERROR`: Invalid parameters
- `DATABASE_ERROR`: Database operation failed
- `NOT_FOUND`: Resource doesn't exist

---

## Common Patterns

### Pattern: Multi-Session Context Preservation

**Scenario**: Feature spans multiple sessions, need context continuity

**Session 1: Setup**
```python
project = create_project("auth-system", "User authentication")
switch_project(project["id"])
root = create_work_item(item_type="project", title="Auth System", status="active")
```

**Session 2: Continue**
```python
# Reconnect to project
projects = list_projects()
auth_project = [p for p in projects if "auth" in p["name"]][0]
switch_project(auth_project["id"])

# Query existing work
work_items = query_work_items(status="active")
# Continue from where you left off
```

---

### Pattern: Dogfooding (Using workflow-mcp to Build workflow-mcp)

**Scenario**: Use the system to track its own development

```python
# Create project for workflow-mcp itself
wf_project = create_project(
    "workflow-mcp",
    "MCP-based project management system"
)
switch_project(wf_project["id"])

# Track phase 11 work
phase11 = create_work_item(
    item_type="project",
    title="Phase 11: Production Deployment",
    status="active"
)

option1 = create_work_item(
    item_type="session",
    title="Option 1: 90% Coverage",
    parent_id=phase11["id"],
    status="completed"
)

# Track deployment
record_deployment(
    commit_sha=git_sha,
    branch="master",
    environment="production",
    work_item_ids=[phase11["id"], option1["id"]]
)
```

---

### Pattern: Entity-Driven Development

**Scenario**: Domain entities drive implementation

```python
# 1. Define domain entities from spec
register_entity_type("api_endpoint", schema={...})
register_entity_type("database_table", schema={...})

# 2. Create entities during design
login_endpoint = create_entity(
    entity_type="api_endpoint",
    name="POST /api/auth/login",
    data={"status": "planned", "priority": "high"}
)

# 3. Create work items linked to entities
implement_login = create_work_item(
    item_type="task",
    title=f"Implement {login_endpoint['name']}",
    description=f"Entity ID: {login_endpoint['id']}"
)

# 4. Update entity status as work progresses
update_entity(
    login_endpoint["id"],
    data={"status": "implemented"},
    current_version=login_endpoint["version"]
)
```

---

## Performance Characteristics

**Targets** (CI-enforced):
- Project switching: <50ms (p95 <60ms)
- Entity queries: <100ms (p95 <120ms)
- Work item queries: <200ms (p95 <240ms)

**Database Isolation**:
- Each project has dedicated PostgreSQL database
- Complete data isolation between projects
- Connection pooling (2-10 connections per DB)

**Scalability**:
- Tested with 50+ concurrent projects
- JSONB GIN indexes for fast entity queries
- Materialized path indexes for work item hierarchy

---

## Troubleshooting

### Issue: "NO_ACTIVE_PROJECT" Error

**Cause**: No project is active (required for most tools)

**Solution**:
```python
# List projects to find the one you want
projects = list_projects()

# Switch to it
switch_project(projects[0]["id"])

# Now other tools will work
```

---

### Issue: Work Items Don't Appear

**Cause**: Querying wrong project or items in different status

**Solution**:
```python
# Check active project
active = get_active_project()
print(f"Active: {active['name'] if active else 'None'}")

# Query with broader filter
all_items = query_work_items()  # No filters = all items

# Or query specific status
completed = query_work_items(status="completed")
```

---

### Issue: Schema Validation Failed

**Cause**: Entity data doesn't match registered schema

**Solution**:
```python
# Query entity type to see schema
# (Currently no direct tool - use query_entities to infer)

# Ensure data matches schema exactly
create_entity(
    entity_type="vendor",
    name="EPSON",
    data={
        "status": "operational",  # Required field
        "version": "2.0.0"        # Required field
    }
)
```

---

### Issue: Circular Dependency Detected

**Cause**: Attempting to create dependency cycle (A→B→A)

**Solution**: This is correct behavior! Circular dependencies are prevented.
```python
# Identify the cycle
hierarchy = get_work_item_hierarchy(task_id)
# Check ancestors and dependencies
# Remove conflicting dependency
```

---

## Best Practices

### 1. Project Naming Convention
```
{spec-number}-{feature-name}
Examples:
  - 042-user-authentication
  - 101-payment-processing
```

### 2. Work Item Descriptions
- Reference spec.md line numbers
- Include acceptance criteria
- Link to related work items

### 3. Status Progression
```
planned → active → completed (happy path)
planned → active → blocked → active → completed (with blockers)
```

### 4. Entity Type Design
- Keep schemas simple initially
- Use optional fields for new properties
- Backfill before making required

### 5. Deployment Metadata
```python
{
    "release_notes": "User-facing changes",
    "breaking_changes": ["API changes"],
    "rollback_instructions": "...",
    "performance_impact": "..."
}
```

---

## Integration with Spec-Kit Slash Commands

| Spec-Kit Command | Workflow-MCP Action | When |
|------------------|---------------------|------|
| `/speckit.specify` | Create project + root work item | After spec written |
| `/speckit.tasks` | Optional: Create session/tasks | For complex features |
| `/speckit.implement` | Update work item status | During implementation |
| Git commit | Record deployment | On merge/release |

**Automation Level**: Manual with suggested patterns (not forced)

---

## Example: Complete Feature Development Flow

```python
# 1. After /speckit.specify
project = create_project(
    "042-user-auth",
    "Implement JWT-based authentication"
)
switch_project(project["id"])

root = create_work_item(
    item_type="project",
    title="Spec 042: User Authentication",
    description="JWT tokens, refresh flow, role-based access",
    status="active"
)

# 2. During /speckit.plan
backend = create_work_item(
    item_type="session",
    title="Backend API Development",
    parent_id=root["id"],
    status="active"
)

frontend = create_work_item(
    item_type="session",
    title="Frontend Integration",
    parent_id=root["id"],
    status="planned"
)

# 3. During /speckit.implement
# Backend task
jwt_task = create_work_item(
    item_type="task",
    title="Implement JWT token generation",
    parent_id=backend["id"],
    status="active"
)

# Mark completed when done
update_work_item(jwt_task["id"], status="completed")

# Frontend task (depends on backend)
add_work_item_dependency(
    work_item_id=frontend["id"],
    depends_on_id=backend["id"],
    dependency_type="blocks"
)

# 4. After merging to main
record_deployment(
    commit_sha="abc123",
    branch="main",
    environment="production",
    status="deployed",
    work_item_ids=[root["id"], jwt_task["id"]]
)

# 5. Mark project complete
update_work_item(root["id"], status="completed")
```

---

## Quick Reference Card

| Task | Tool | Required Params |
|------|------|-----------------|
| Start new feature | `create_project` | name, description |
| Switch context | `switch_project` | project_id |
| Create work | `create_work_item` | item_type, title |
| Update status | `update_work_item` | work_item_id, status |
| Query work | `query_work_items` | (optional filters) |
| Track deployment | `record_deployment` | commit_sha, branch, environment |
| Define entity | `register_entity_type` | type_name, schema |
| Create entity | `create_entity` | entity_type, name, data |

---

## Document Version

**Version**: 1.0  
**Created**: 2025-10-12  
**For**: AI agents using Spec-Kit framework  
**System**: workflow-mcp v0.4.0-alpha  
**Tools**: 21 MCP tools available  
**Status**: Production-ready (81% test coverage)

---

**Questions?** See:
- `docs/guides/architecture-guide.md` - System internals
- `docs/guides/development-guide.md` - Developer commands
- `CLAUDE.md` - Quick reference
- Session logs in `/tmp/workflow-mcp.log`

**Ready to start?** Test with the prompt at the top of this document!
