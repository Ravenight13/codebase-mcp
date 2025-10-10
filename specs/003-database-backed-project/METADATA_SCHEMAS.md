# Work Item Metadata Schemas Documentation

**Feature**: 003-database-backed-project
**Date**: 2025-10-10
**Purpose**: Reference guide for required metadata fields per work item type

---

## Overview

Work items in the database-backed project tracking system use **type-specific JSONB metadata** validated by Pydantic schemas. Each work item type (`project`, `session`, `task`, `research`) requires a specific metadata structure.

**Key Principles:**
- All metadata is validated at creation time using Pydantic
- Metadata validation errors are returned immediately with field-level details
- JSONB storage allows flexible schema evolution
- Required fields MUST be provided; optional fields may be null

---

## Quick Reference

| Item Type   | Required Fields | Optional Fields | Validation Rules |
|-------------|----------------|-----------------|------------------|
| `project`   | `description` | `target_quarter`, `constitutional_principles` | description ≤ 1000 chars |
| `session`   | `token_budget`, `prompts_count`, `yaml_frontmatter` | - | token_budget: 1000-1000000, yaml_frontmatter must have `schema_version` |
| `task`      | - | `estimated_hours`, `actual_hours`, `blocked_reason` | hours: 0-1000, blocked_reason ≤ 500 chars |
| `research`  | - | `research_questions`, `findings_summary`, `references` | findings_summary ≤ 2000 chars |

---

## Project Metadata

**Type**: `ProjectMetadata`
**Use Case**: High-level project tracking with constitutional alignment

### Schema

```json
{
  "description": "Project description and purpose (REQUIRED)",
  "target_quarter": "2025-Q1 (OPTIONAL)",
  "constitutional_principles": [
    "Simplicity Over Features",
    "Local-First Architecture"
  ]
}
```

### Field Details

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `description` | string | ✅ Yes | max 1000 chars | Project description and purpose |
| `target_quarter` | string | ❌ No | format: `YYYY-Q[1-4]` | Target completion quarter |
| `constitutional_principles` | array[string] | ❌ No | - | List of relevant constitutional principles |

### Validation Rules

- **description**: Must be provided, max length 1000 characters
- **target_quarter**: If provided, must match pattern `^\d{4}-Q[1-4]$` (e.g., "2025-Q1", "2024-Q3")
- **constitutional_principles**: Defaults to empty list if not provided

### Example: Create Project

```json
{
  "item_type": "project",
  "title": "Implement semantic code search",
  "metadata": {
    "description": "Add semantic search capabilities to code indexer using pgvector and embedding models",
    "target_quarter": "2025-Q2",
    "constitutional_principles": [
      "Simplicity Over Features",
      "Performance Guarantees"
    ]
  },
  "created_by": "claude-code"
}
```

---

## Session Metadata

**Type**: `SessionMetadata`
**Use Case**: AI coding session tracking with token budget and YAML frontmatter

### Schema

```json
{
  "token_budget": 200000,
  "prompts_count": 15,
  "yaml_frontmatter": {
    "schema_version": "1.0",
    "mode": "implement",
    "custom_field": "value"
  }
}
```

### Field Details

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `token_budget` | integer | ✅ Yes | 1000 ≤ value ≤ 1000000 | Token budget allocated for this session |
| `prompts_count` | integer | ✅ Yes | ≥ 0 | Number of prompts executed in session |
| `yaml_frontmatter` | object | ✅ Yes | must include `schema_version` | Raw YAML frontmatter from session prompt file |

### Validation Rules

- **token_budget**: Must be between 1000 and 1000000 (inclusive)
- **prompts_count**: Must be non-negative (≥ 0)
- **yaml_frontmatter**:
  - Must be a valid object/dictionary
  - MUST include `schema_version` field
  - Can contain arbitrary additional fields

### Example: Create Session

```json
{
  "item_type": "session",
  "title": "2025-10-10 Implementation Session",
  "parent_id": "46379897-50ce-44ba-b766-96b27427818e",
  "metadata": {
    "token_budget": 200000,
    "prompts_count": 0,
    "yaml_frontmatter": {
      "schema_version": "1.0",
      "mode": "implement",
      "feature": "003-database-backed-project"
    }
  },
  "created_by": "claude-code"
}
```

---

## Task Metadata

**Type**: `TaskMetadata`
**Use Case**: Task execution tracking with time estimates and blocking reasons

### Schema

```json
{
  "estimated_hours": 2.5,
  "actual_hours": 3.0,
  "blocked_reason": "Waiting for database migration to complete"
}
```

### Field Details

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `estimated_hours` | float | ❌ No | 0 ≤ value ≤ 1000 | Estimated hours to complete task |
| `actual_hours` | float | ❌ No | 0 ≤ value ≤ 1000 | Actual hours spent on task |
| `blocked_reason` | string | ❌ No | max 500 chars | Reason why task is blocked (if status='blocked') |

### Validation Rules

- **estimated_hours**: If provided, must be between 0 and 1000
- **actual_hours**: If provided, must be between 0 and 1000
- **blocked_reason**: If provided, max length 500 characters
- **All fields optional**: Can provide empty object `{}` for minimal task

### Example: Create Task with No Metadata

```json
{
  "item_type": "task",
  "title": "Implement database migration script",
  "parent_id": "87a280bb-144c-4399-8080-e9eb9ebffb4c",
  "metadata": {},
  "created_by": "claude-code"
}
```

### Example: Create Task with Full Metadata

```json
{
  "item_type": "task",
  "title": "Implement optimistic locking",
  "parent_id": "87a280bb-144c-4399-8080-e9eb9ebffb4c",
  "metadata": {
    "estimated_hours": 4.0,
    "actual_hours": null,
    "blocked_reason": null
  },
  "status": "active",
  "created_by": "claude-code"
}
```

---

## Research Metadata

**Type**: `ResearchMetadata`
**Use Case**: Technical research documentation with questions, findings, and references

### Schema

```json
{
  "research_questions": [
    "What is the best caching strategy for offline fallback?",
    "How to handle concurrent updates without locking?"
  ],
  "findings_summary": "SQLite provides best offline fallback with minimal overhead. Optimistic locking prevents conflicts.",
  "references": [
    "https://docs.sqlalchemy.org/en/20/",
    "RFC 7234 - HTTP Caching"
  ]
}
```

### Field Details

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `research_questions` | array[string] | ❌ No | - | List of research questions addressed |
| `findings_summary` | string | ❌ No | max 2000 chars | Summary of research findings |
| `references` | array[string] | ❌ No | - | List of reference URLs or documents |

### Validation Rules

- **research_questions**: Defaults to empty list if not provided
- **findings_summary**: If provided, max length 2000 characters
- **references**: Defaults to empty list if not provided
- **All fields optional**: Can provide empty object `{}` for minimal research item

### Example: Create Research Item

```json
{
  "item_type": "research",
  "title": "Hierarchical query optimization research",
  "parent_id": "46379897-50ce-44ba-b766-96b27427818e",
  "metadata": {
    "research_questions": [
      "Should we use materialized paths or recursive CTEs?",
      "What is the performance impact of 5-level hierarchies?"
    ],
    "findings_summary": "Materialized paths provide <1ms ancestor queries. Recursive CTEs handle descendants in <10ms for 5 levels.",
    "references": [
      "https://www.postgresql.org/docs/current/queries-with.html",
      "https://explainextended.com/2009/09/24/adjacency-list-vs-nested-sets-postgresql/"
    ]
  },
  "created_by": "claude-code"
}
```

---

## Common Validation Errors

### Error 1: Missing Required Field

```json
{
  "error": "Metadata validation failed for session: 1 validation error for SessionMetadata\ntoken_budget\n  Field required [type=missing, input_value={'prompts_count': 0}, input_type=dict]"
}
```

**Solution**: Ensure all required fields are provided in metadata object.

### Error 2: Invalid Field Type

```json
{
  "error": "Metadata validation failed for session: 1 validation error for SessionMetadata\ntoken_budget\n  Input should be a valid integer [type=int_type, input_value='200000', input_type=str]"
}
```

**Solution**: Ensure field types match schema (e.g., `token_budget` must be integer, not string).

### Error 3: Constraint Violation

```json
{
  "error": "Metadata validation failed for session: 1 validation error for SessionMetadata\ntoken_budget\n  Input should be greater than or equal to 1000 [type=greater_than_equal, input_value=500, input_type=int]"
}
```

**Solution**: Check field constraints (e.g., `token_budget` must be ≥ 1000).

### Error 4: Missing schema_version in YAML Frontmatter

```json
{
  "error": "Metadata validation failed for session: YAML frontmatter must include schema_version"
}
```

**Solution**: Ensure `yaml_frontmatter` object includes required `schema_version` field.

---

## Testing Metadata

### Minimal Valid Metadata Examples

```python
# Project (minimal)
project_metadata = {
    "description": "Test project"
}

# Session (minimal)
session_metadata = {
    "token_budget": 10000,
    "prompts_count": 0,
    "yaml_frontmatter": {"schema_version": "1.0"}
}

# Task (minimal - empty object is valid)
task_metadata = {}

# Research (minimal - empty object is valid)
research_metadata = {}
```

### Comprehensive Valid Metadata Examples

```python
# Project (comprehensive)
project_metadata = {
    "description": "Comprehensive project tracking system with hierarchical work items",
    "target_quarter": "2025-Q2",
    "constitutional_principles": [
        "Simplicity Over Features",
        "Local-First Architecture",
        "Performance Guarantees"
    ]
}

# Session (comprehensive)
session_metadata = {
    "token_budget": 200000,
    "prompts_count": 15,
    "yaml_frontmatter": {
        "schema_version": "1.0",
        "mode": "implement",
        "feature": "003-database-backed-project",
        "phase": "phase-2"
    }
}

# Task (comprehensive)
task_metadata = {
    "estimated_hours": 4.5,
    "actual_hours": 5.2,
    "blocked_reason": "Waiting for upstream API changes"
}

# Research (comprehensive)
research_metadata = {
    "research_questions": [
        "What is the best approach for handling concurrent updates?",
        "How to optimize hierarchical queries for 5-level trees?",
        "Should we use materialized paths or closure tables?"
    ],
    "findings_summary": "Materialized paths with recursive CTEs provide optimal performance for 5-level hierarchies. Optimistic locking prevents concurrent update conflicts without database locks. PostgreSQL ltree extension not needed for our use case.",
    "references": [
        "https://docs.sqlalchemy.org/en/20/orm/session_transaction.html",
        "https://www.postgresql.org/docs/current/queries-with.html",
        "https://martinfowler.com/eaaCatalog/optimisticOfflineLock.html"
    ]
}
```

---

## Schema Evolution

### Adding New Fields

To add new optional fields to existing metadata types:

1. Update Pydantic schema in `contracts/pydantic-schemas.py`
2. Add field with default value or `Optional[]` type
3. Existing data remains valid (new field defaults to null)

### Changing Field Constraints

To modify field constraints (e.g., increase max length):

1. Update Pydantic schema constraints
2. Run database migration if database column constraints exist
3. Test with existing data to ensure backward compatibility

### Deprecating Fields

To deprecate fields:

1. Mark field as `Optional[]` in schema
2. Update documentation with deprecation notice
3. Remove field validation logic after grace period

---

## References

- **Pydantic Schema Definitions**: `specs/003-database-backed-project/contracts/pydantic-schemas.py`
- **MCP Tool Implementation**: `src/mcp/tools/work_items.py`
- **Database Models**: `src/models/task.py` (WorkItem model)
- **Feature Specification**: `specs/003-database-backed-project/spec.md`

---

## Support

If you encounter metadata validation errors:

1. Check this documentation for required fields
2. Verify field types match schema definitions
3. Review Pydantic schema source for detailed validation rules
4. Check MCP tool error messages for specific validation failures
