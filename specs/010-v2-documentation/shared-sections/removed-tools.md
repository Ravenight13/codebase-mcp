# Removed Tools Reference

This section documents all 14 MCP tools that were removed in v2.0 as part of the workflow-mcp server extraction. These tools provided project management, entity management, and work item tracking capabilities that are no longer part of the core Codebase MCP Server.

## Removed Project Management Tools (4 tools)

### `create_project`
**Status**: Removed in v2.0
**Category**: Project Management
**Description**: Created a new project workspace with an isolated PostgreSQL database. Projects served as containers for organizing entities and work items in v1.x.

### `switch_project`
**Status**: Removed in v2.0
**Category**: Project Management
**Description**: Switched the active project context for all subsequent operations. All entity and work item operations were scoped to the active project.

### `get_active_project`
**Status**: Removed in v2.0
**Category**: Project Management
**Description**: Retrieved the currently active project workspace metadata or returned null if no project was active.

### `list_projects`
**Status**: Removed in v2.0
**Category**: Project Management
**Description**: Listed all project workspaces with pagination support, ordered by creation date (newest first).

## Removed Entity Management Tools (6 tools)

### `register_entity_type`
**Status**: Removed in v2.0
**Category**: Entity Management
**Description**: Registered a new entity type with JSON Schema validation. Entity types defined the structure and validation rules for storing arbitrary JSONB data.

### `create_entity`
**Status**: Removed in v2.0
**Category**: Entity Management
**Description**: Created a new entity instance with data validated against the registered entity type's JSON Schema. Entities were scoped to the active project.

### `query_entities`
**Status**: Removed in v2.0
**Category**: Entity Management
**Description**: Queried entities with JSONB containment filters and tag matching. Supported complex filtering with GIN-indexed JSONB queries for sub-100ms performance.

### `update_entity`
**Status**: Removed in v2.0
**Category**: Entity Management
**Description**: Updated entity data with optimistic locking via version numbers to prevent concurrent update conflicts. Changes were validated against the entity type's JSON Schema.

### `delete_entity`
**Status**: Removed in v2.0
**Category**: Entity Management
**Description**: Soft-deleted an entity by setting the `deleted_at` timestamp. Required explicit confirmation to prevent accidental deletions.

### `update_entity_type_schema`
**Status**: Removed in v2.0
**Category**: Entity Management
**Description**: Updated an entity type's JSON Schema with backward compatibility validation. Automatically incremented schema versions and optionally validated existing entities against the new schema.

## Removed Work Item Management Tools (4 tools)

### `create_work_item`
**Status**: Removed in v2.0
**Category**: Work Item Management
**Description**: Created a new work item in a 5-level hierarchy (project → session → task → research → subtask) with automatic materialized path generation for fast ancestor queries.

### `update_work_item`
**Status**: Removed in v2.0
**Category**: Work Item Management
**Description**: Updated work item fields including title, description, and status. Automatically set `completed_at` timestamp when status changed to 'completed'.

### `query_work_items`
**Status**: Removed in v2.0
**Category**: Work Item Management
**Description**: Queried work items with filtering by type, status, and parent. Supported recursive descendant queries using materialized paths.

### `get_work_item_hierarchy`
**Status**: Removed in v2.0
**Category**: Work Item Management
**Description**: Retrieved complete hierarchy information for a work item including ancestors (parents to root), direct children, and all descendants using materialized path queries.

## Summary

**Total Removed Tools**: 14

- **Project Management**: 4 tools
- **Entity Management**: 6 tools
- **Work Item Management**: 4 tools

All removed functionality has been extracted to the separate **workflow-mcp** server, which is maintained as an independent MCP server focused on development workflow tracking. The Codebase MCP Server v2.0 focuses exclusively on semantic code search capabilities.
