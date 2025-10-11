# Workflow MCP - AI Project Management Server

## Overview

**workflow-mcp** is a focused, production-grade MCP server that provides AI-assisted project management with multi-project workspace support and a generic entity system. It enables AI coding assistants to track work items, manage tasks, record deployments, and handle domain-specific entities (vendors, game mechanics, etc.) across isolated project workspaces.

## Purpose

This MCP server addresses the need for AI assistants to:
- **Manage multiple projects** with complete data isolation (one database per project)
- **Track work hierarchies** (projects → sessions → tasks → research items)
- **Handle domain-specific entities** without hardcoded tables (commission vendors, game mechanics, etc.)
- **Record development history** (deployments, git commits, test results)
- **Switch contexts** rapidly between different project types

## Relationship to codebase-mcp

workflow-mcp is a **complementary** MCP server that works alongside codebase-mcp:

- **codebase-mcp**: Code intelligence (semantic search, indexing, code embeddings)
- **workflow-mcp**: Project management (work items, tasks, entities, deployments)

Both servers can query each other for context:
- codebase-mcp can query workflow-mcp for active project context
- workflow-mcp can query codebase-mcp for code references during task planning

## Key Features

### 1. Multi-Project Workspace Management
- **Registry database** tracks all projects with metadata
- **Database-per-project** ensures complete isolation
- **Active project switching** with <50ms latency
- **Connection pooling** per project database

### 2. Hierarchical Work Items
- **Project** → **Session** → **Task** → **Research** hierarchy
- Type-specific metadata (JSONB)
- Parent-child relationships with materialized paths
- Dependency tracking (blocked-by, depends-on)

### 3. Generic Entity System
- **No hardcoded domain tables** (no vendor, game_mechanic tables)
- **Runtime entity type registration** via JSON Schema
- **Flexible JSONB storage** with Pydantic validation
- **Domain-agnostic queries** using PostgreSQL JSONB operators

### 4. Task Management
- Status tracking (need to be done, in-progress, complete)
- Git integration (branch/commit associations)
- Planning references (links to spec.md, plan.md)
- Token-efficient list operations

### 5. Deployment History
- Event recording with PR details and test results
- Constitutional compliance tracking
- Relationships to work items and entities
- Audit trail for production changes

## Generic Entity System

The entity system supports **any domain** without schema changes:

### Commission Work Example
```python
# Register vendor entity type
register_entity_type(
    project_id="commission-001",
    type_name="vendor",
    schema={
        "type": "object",
        "properties": {
            "status": {"enum": ["operational", "broken"]},
            "extractor_version": {"type": "string"},
            "supports_html": {"type": "boolean"}
        },
        "required": ["status"]
    }
)

# Create vendor entity
create_entity(
    project_id="commission-001",
    entity_type="vendor",
    name="EPSON",
    data={"status": "operational", "supports_html": True}
)
```

### Game Development Example
```python
# Register game mechanic entity type
register_entity_type(
    project_id="ttrpg-core",
    type_name="game_mechanic",
    schema={
        "type": "object",
        "properties": {
            "mechanic_type": {"enum": ["combat", "skill", "magic"]},
            "implementation_status": {"enum": ["design", "prototype", "complete"]},
            "complexity": {"type": "integer", "minimum": 1, "maximum": 5}
        },
        "required": ["mechanic_type", "implementation_status"]
    }
)

# Create mechanic entity
create_entity(
    project_id="ttrpg-core",
    entity_type="game_mechanic",
    name="Skill Check System",
    data={"mechanic_type": "skill", "implementation_status": "prototype", "complexity": 3}
)
```

## Architecture Highlights

### Database Structure
```
workflow_registry/          # Registry database (always exists)
├── projects                # Project metadata table
└── active_project_config   # Current active project

workflow_project_<id>/      # Project-specific database (per project)
├── work_items              # Hierarchical work tracking
├── tasks                   # Task management (legacy, may merge with work_items)
├── entities                # Generic entity storage (JSONB)
├── entity_types            # Registered entity schemas (JSON Schema)
├── deployments             # Deployment history
└── work_item_dependencies  # Dependency relationships
```

### Performance Targets
- **Project switching**: <50ms (registry query + connection pool lookup)
- **Work item operations**: <200ms (hierarchy queries with materialized paths)
- **Entity queries**: <100ms (JSONB indexing with GIN)
- **Task list**: <200ms (with token-efficient summary mode)

## Success Criteria

1. **Isolation**: Commission project data never visible in game dev project
2. **Flexibility**: New entity types registered without code changes
3. **Performance**: <50ms project switching, <200ms work item operations
4. **Scalability**: Support 100+ projects with independent databases
5. **Type Safety**: All operations validated via Pydantic at runtime

## Development Approach

- **Specification-first**: Requirements before implementation
- **Test-driven**: Protocol compliance tests before features
- **Git micro-commits**: Atomic commits after each task
- **Branch-per-feature**: Isolated development with PR review
- **FastMCP foundation**: Built on FastMCP framework with MCP Python SDK
