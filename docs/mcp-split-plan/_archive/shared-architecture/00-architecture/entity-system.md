# Generic JSONB Entity System Architecture

## Overview

The workflow-mcp uses a **generic entity system** with JSONB storage for flexible, schema-less project management. Instead of hardcoded tables for tasks, vendors, deployments, etc., we use two tables:

1. **entity_schemas**: JSON Schema definitions for entity types
2. **entities**: JSONB storage for all entity instances

This design allows:
- **Schema evolution** without database migrations
- **Project-specific entity types** (e.g., game mechanics, invoice vendors)
- **Runtime validation** via Pydantic models
- **PostgreSQL JSONB query power** (GIN indexes, operators)

## Why Generic vs Hardcoded Tables

### Hardcoded Approach (Traditional)

```sql
-- Separate table for each entity type
CREATE TABLE tasks (
    id UUID PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    priority TEXT,
    description TEXT,
    ...
);

CREATE TABLE vendors (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    extractor_version TEXT,
    ...
);

CREATE TABLE deployments (
    id UUID PRIMARY KEY,
    deployed_at TIMESTAMPTZ NOT NULL,
    commit_hash TEXT,
    ...
);
```

**Problems:**
- Schema changes require migrations (ALTER TABLE)
- Adding new entity types requires DDL changes
- Project-specific entities need custom tables
- AI cannot easily extend schema at runtime

### Generic Approach (This Design)

```sql
-- Single table for entity schemas
CREATE TABLE entity_schemas (
    schema_name TEXT PRIMARY KEY,
    schema_definition JSONB NOT NULL,  -- JSON Schema
    ...
);

-- Single table for all entities
CREATE TABLE entities (
    id UUID PRIMARY KEY,
    schema_name TEXT REFERENCES entity_schemas(schema_name),
    data JSONB NOT NULL,  -- Flexible storage
    ...
);
```

**Benefits:**
- No migrations for schema changes (update schema_definition)
- New entity types = insert into entity_schemas
- Project-specific entities supported out-of-the-box
- AI can define new entity types dynamically
- PostgreSQL JSONB provides excellent query performance

**Trade-offs:**
- Slightly slower queries (JSONB vs columns) - 2-5x overhead, still fast
- No database-level foreign keys between entities
- Schema validation happens at runtime (application layer)
- Less database-enforced type safety

**Verdict:** For AI-assisted project management, flexibility > rigid schema.

## Schema Architecture

### entity_schemas Table

Stores JSON Schema definitions for validation.

```sql
CREATE TABLE IF NOT EXISTS workflow.entity_schemas (
    -- Identity
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    schema_name TEXT NOT NULL UNIQUE,

    -- Schema definition (JSON Schema format)
    schema_definition JSONB NOT NULL,

    -- Metadata
    version INTEGER NOT NULL DEFAULT 1,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by TEXT NOT NULL DEFAULT 'claude-code',

    -- Validation
    CONSTRAINT valid_schema_name CHECK (schema_name ~ '^[a-z_][a-z0-9_]*$')
);

CREATE INDEX idx_entity_schemas_name ON workflow.entity_schemas(schema_name);
```

**Schema Definition Format:**

JSON Schema (draft-07) for validation:

```json
{
    "type": "object",
    "required": ["title", "status"],
    "properties": {
        "title": {
            "type": "string",
            "minLength": 1,
            "maxLength": 200
        },
        "status": {
            "type": "string",
            "enum": ["pending", "in_progress", "completed", "blocked"]
        },
        "priority": {
            "type": "string",
            "enum": ["low", "medium", "high", "critical"]
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"}
        }
    }
}
```

### entities Table

Generic JSONB storage for all entity instances.

```sql
CREATE TABLE IF NOT EXISTS workflow.entities (
    -- Identity
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    schema_name TEXT NOT NULL REFERENCES workflow.entity_schemas(schema_name) ON DELETE RESTRICT,

    -- Entity data (validated against schema)
    data JSONB NOT NULL,

    -- Versioning (optimistic locking)
    version INTEGER NOT NULL DEFAULT 1,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by TEXT NOT NULL DEFAULT 'claude-code',
    updated_by TEXT NOT NULL DEFAULT 'claude-code',

    -- Soft delete
    deleted_at TIMESTAMPTZ,

    -- Validation
    CONSTRAINT valid_version CHECK (version > 0)
);

-- Indexes for query performance
CREATE INDEX idx_entities_schema_name ON workflow.entities(schema_name);
CREATE INDEX idx_entities_created_at ON workflow.entities(created_at DESC);
CREATE INDEX idx_entities_updated_at ON workflow.entities(updated_at DESC);
CREATE INDEX idx_entities_deleted_at ON workflow.entities(deleted_at) WHERE deleted_at IS NULL;

-- CRITICAL: GIN indexes for JSONB queries
CREATE INDEX idx_entities_data ON workflow.entities USING GIN (data);
CREATE INDEX idx_entities_data_jsonb_path ON workflow.entities USING GIN (data jsonb_path_ops);

-- Example: Index specific JSONB fields for common queries
CREATE INDEX idx_entities_status ON workflow.entities
    ((data->>'status'))
    WHERE schema_name = 'task';

CREATE INDEX idx_entities_vendor_name ON workflow.entities
    ((data->>'name'))
    WHERE schema_name = 'vendor';
```

## Pydantic Validation at Runtime

### Schema Validation Flow

```
┌─────────────────────────────────────────────────┐
│  MCP Tool: create_entity(schema_name, data)     │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│  1. Lookup schema from entity_schemas table     │
│     SELECT schema_definition FROM ...           │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│  2. Validate data against JSON Schema           │
│     jsonschema.validate(data, schema)           │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│  3. Validate with Pydantic model (if exists)    │
│     TaskEntity(**data)  # Type safety           │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│  4. Insert into entities table                  │
│     INSERT INTO entities (schema_name, data)... │
└─────────────────────────────────────────────────┘
```

### Python Implementation

```python
"""
entity_manager.py - Generic entity system with Pydantic validation
"""
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel, Field, ValidationError
import jsonschema
from uuid import UUID
import asyncpg


class EntityBase(BaseModel):
    """Base model for all entities."""
    pass


class TaskEntity(EntityBase):
    """Task entity model."""
    title: str = Field(..., min_length=1, max_length=200)
    status: str = Field(..., pattern="^(pending|in_progress|completed|blocked)$")
    priority: Optional[str] = Field(None, pattern="^(low|medium|high|critical)$")
    description: Optional[str] = None
    tags: Optional[list[str]] = None
    assignee: Optional[str] = None
    due_date: Optional[str] = None


class VendorEntity(EntityBase):
    """Vendor entity model."""
    name: str = Field(..., min_length=1, max_length=100)
    status: str = Field(..., pattern="^(operational|broken)$")
    extractor_version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    last_test_date: Optional[str] = None
    test_results: Optional[Dict[str, Any]] = None
    format_support: Optional[Dict[str, bool]] = None


class GameMechanicEntity(EntityBase):
    """Game mechanic entity (project-specific)."""
    name: str = Field(..., min_length=1, max_length=100)
    mechanic_type: str = Field(..., pattern="^(movement|combat|puzzle|dialogue)$")
    complexity: str = Field(..., pattern="^(simple|medium|complex)$")
    implementation_status: str = Field(..., pattern="^(design|prototype|implemented|tested)$")
    dependencies: Optional[list[str]] = None
    parameters: Optional[Dict[str, Any]] = None


class EntityManager:
    """Manages generic entities with validation."""

    # Registry of Pydantic models by schema name
    _model_registry: Dict[str, Type[EntityBase]] = {
        "task": TaskEntity,
        "vendor": VendorEntity,
        "game_mechanic": GameMechanicEntity,
    }

    def __init__(self, conn_mgr):
        """Initialize with connection manager."""
        self.conn_mgr = conn_mgr

    async def get_schema(self, project_name: str, schema_name: str) -> dict:
        """Get entity schema definition."""
        async with self.conn_mgr.get_project_connection(project_name) as conn:
            row = await conn.fetchrow("""
                SELECT schema_definition, version
                FROM workflow.entity_schemas
                WHERE schema_name = $1
            """, schema_name)

        if not row:
            raise ValueError(f"Schema '{schema_name}' not found")

        return {
            "schema_name": schema_name,
            "schema_definition": row["schema_definition"],
            "version": row["version"],
        }

    def _validate_json_schema(self, data: dict, schema_definition: dict) -> None:
        """Validate data against JSON Schema."""
        try:
            jsonschema.validate(instance=data, schema=schema_definition)
        except jsonschema.ValidationError as e:
            raise ValueError(f"JSON Schema validation failed: {e.message}")

    def _validate_pydantic(self, schema_name: str, data: dict) -> EntityBase:
        """Validate data with Pydantic model if registered."""
        model_class = self._model_registry.get(schema_name)
        if not model_class:
            # No Pydantic model registered, skip validation
            return None

        try:
            return model_class(**data)
        except ValidationError as e:
            raise ValueError(f"Pydantic validation failed: {e}")

    async def create_entity(
        self,
        project_name: str,
        schema_name: str,
        data: dict,
        created_by: str = "claude-code"
    ) -> UUID:
        """
        Create a new entity with validation.

        Args:
            project_name: Project name
            schema_name: Entity schema name
            data: Entity data (will be validated)
            created_by: Creator identifier

        Returns:
            Entity ID (UUID)

        Raises:
            ValueError: If validation fails or schema not found
        """
        # Get schema definition
        schema_info = await self.get_schema(project_name, schema_name)
        schema_definition = schema_info["schema_definition"]

        # Validate against JSON Schema
        self._validate_json_schema(data, schema_definition)

        # Validate with Pydantic (if model exists)
        self._validate_pydantic(schema_name, data)

        # Insert entity
        async with self.conn_mgr.get_project_connection(project_name) as conn:
            entity_id = await conn.fetchval("""
                INSERT INTO workflow.entities
                    (schema_name, data, created_by, updated_by)
                VALUES ($1, $2, $3, $3)
                RETURNING id
            """, schema_name, data, created_by)

        return entity_id

    async def update_entity(
        self,
        project_name: str,
        entity_id: UUID,
        data: dict,
        expected_version: int,
        updated_by: str = "claude-code"
    ) -> None:
        """
        Update entity with optimistic locking.

        Args:
            project_name: Project name
            entity_id: Entity ID
            data: Updated entity data
            expected_version: Expected version (for optimistic locking)
            updated_by: Updater identifier

        Raises:
            ValueError: If validation fails, entity not found, or version mismatch
        """
        async with self.conn_mgr.get_project_connection(project_name) as conn:
            # Get current entity
            row = await conn.fetchrow("""
                SELECT schema_name, version
                FROM workflow.entities
                WHERE id = $1 AND deleted_at IS NULL
            """, entity_id)

            if not row:
                raise ValueError(f"Entity {entity_id} not found")

            if row["version"] != expected_version:
                raise ValueError(
                    f"Version mismatch: expected {expected_version}, "
                    f"current {row['version']}"
                )

            schema_name = row["schema_name"]

            # Get schema and validate
            schema_info = await self.get_schema(project_name, schema_name)
            self._validate_json_schema(data, schema_info["schema_definition"])
            self._validate_pydantic(schema_name, data)

            # Update entity
            result = await conn.execute("""
                UPDATE workflow.entities
                SET
                    data = $1,
                    version = version + 1,
                    updated_at = NOW(),
                    updated_by = $2
                WHERE id = $3 AND version = $4 AND deleted_at IS NULL
            """, data, updated_by, entity_id, expected_version)

            if result == "UPDATE 0":
                raise ValueError("Update failed due to concurrent modification")

    async def query_entities(
        self,
        project_name: str,
        schema_name: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 50,
        offset: int = 0
    ) -> list[dict]:
        """
        Query entities with JSONB filters.

        Args:
            project_name: Project name
            schema_name: Entity schema name
            filters: JSONB filters (key-value pairs)
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of entities

        Example:
            # Find all in-progress tasks
            await query_entities("myapp", "task", {"status": "in_progress"})

            # Find high priority tasks
            await query_entities("myapp", "task", {"priority": "high"})
        """
        async with self.conn_mgr.get_project_connection(project_name) as conn:
            # Build WHERE clause from filters
            where_clauses = ["schema_name = $1", "deleted_at IS NULL"]
            params = [schema_name]

            if filters:
                for idx, (key, value) in enumerate(filters.items(), start=2):
                    where_clauses.append(f"data->>'{key}' = ${idx}")
                    params.append(str(value))

            where_clause = " AND ".join(where_clauses)
            params.extend([limit, offset])

            # Execute query
            rows = await conn.fetch(f"""
                SELECT id, schema_name, data, version, created_at, updated_at
                FROM workflow.entities
                WHERE {where_clause}
                ORDER BY updated_at DESC
                LIMIT ${len(params)-1} OFFSET ${len(params)}
            """, *params)

        return [
            {
                "id": str(row["id"]),
                "schema_name": row["schema_name"],
                "data": row["data"],
                "version": row["version"],
                "created_at": row["created_at"].isoformat(),
                "updated_at": row["updated_at"].isoformat(),
            }
            for row in rows
        ]
```

## Example: Vendor Entity vs Game Mechanic Entity

### Vendor Entity (Invoice Extraction)

**Schema Definition:**

```json
{
    "type": "object",
    "required": ["name", "status"],
    "properties": {
        "name": {
            "type": "string",
            "minLength": 1,
            "maxLength": 100
        },
        "status": {
            "type": "string",
            "enum": ["operational", "broken"]
        },
        "extractor_version": {
            "type": "string",
            "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$"
        },
        "last_test_date": {
            "type": "string",
            "format": "date-time"
        },
        "test_results": {
            "type": "object",
            "properties": {
                "pdf_extraction": {"type": "boolean"},
                "line_items_accuracy": {"type": "number", "minimum": 0, "maximum": 1}
            }
        },
        "format_support": {
            "type": "object",
            "properties": {
                "pdf": {"type": "boolean"},
                "xml": {"type": "boolean"},
                "csv": {"type": "boolean"}
            }
        }
    }
}
```

**Example Instance:**

```python
await entity_mgr.create_entity(
    project_name="invoice_app",
    schema_name="vendor",
    data={
        "name": "Acme Corp",
        "status": "operational",
        "extractor_version": "2.1.0",
        "last_test_date": "2025-10-10T14:00:00Z",
        "test_results": {
            "pdf_extraction": True,
            "line_items_accuracy": 0.98
        },
        "format_support": {
            "pdf": True,
            "xml": True,
            "csv": False
        }
    }
)
```

**Query Example:**

```python
# Find all broken vendors
broken_vendors = await entity_mgr.query_entities(
    project_name="invoice_app",
    schema_name="vendor",
    filters={"status": "broken"}
)

# Find vendors with PDF support (requires complex JSONB query)
async with conn_mgr.get_project_connection("invoice_app") as conn:
    vendors = await conn.fetch("""
        SELECT id, data
        FROM workflow.entities
        WHERE schema_name = 'vendor'
          AND (data->'format_support'->>'pdf')::boolean = true
    """)
```

### Game Mechanic Entity (Game Development)

**Schema Definition:**

```json
{
    "type": "object",
    "required": ["name", "mechanic_type", "implementation_status"],
    "properties": {
        "name": {
            "type": "string",
            "minLength": 1,
            "maxLength": 100
        },
        "mechanic_type": {
            "type": "string",
            "enum": ["movement", "combat", "puzzle", "dialogue"]
        },
        "complexity": {
            "type": "string",
            "enum": ["simple", "medium", "complex"]
        },
        "implementation_status": {
            "type": "string",
            "enum": ["design", "prototype", "implemented", "tested"]
        },
        "dependencies": {
            "type": "array",
            "items": {"type": "string"}
        },
        "parameters": {
            "type": "object",
            "additionalProperties": true
        }
    }
}
```

**Example Instance:**

```python
await entity_mgr.create_entity(
    project_name="my_game",
    schema_name="game_mechanic",
    data={
        "name": "Double Jump",
        "mechanic_type": "movement",
        "complexity": "medium",
        "implementation_status": "prototype",
        "dependencies": ["basic_jump", "air_control"],
        "parameters": {
            "second_jump_height": 0.8,
            "cooldown_ms": 500,
            "animation": "double_jump_anim"
        }
    }
)
```

**Query Example:**

```python
# Find all combat mechanics in design phase
combat_mechanics = await entity_mgr.query_entities(
    project_name="my_game",
    schema_name="game_mechanic",
    filters={
        "mechanic_type": "combat",
        "implementation_status": "design"
    }
)

# Find complex mechanics (requires JSONB query)
async with conn_mgr.get_project_connection("my_game") as conn:
    complex_mechanics = await conn.fetch("""
        SELECT id, data->>'name' as name, data->>'mechanic_type' as type
        FROM workflow.entities
        WHERE schema_name = 'game_mechanic'
          AND data->>'complexity' = 'complex'
    """)
```

## Query Patterns with JSONB Operators

PostgreSQL provides powerful JSONB operators for flexible queries:

### Containment Operator (@>)

```sql
-- Find entities with specific nested values
SELECT * FROM workflow.entities
WHERE data @> '{"status": "in_progress", "priority": "high"}'::jsonb;

-- Find vendors with PDF support
SELECT * FROM workflow.entities
WHERE schema_name = 'vendor'
  AND data @> '{"format_support": {"pdf": true}}'::jsonb;
```

### Field Extraction (->>, ->)

```sql
-- Extract text field (->>)
SELECT id, data->>'name' as name, data->>'status' as status
FROM workflow.entities
WHERE schema_name = 'vendor';

-- Extract JSON object (->)
SELECT id, data->'test_results' as test_results
FROM workflow.entities
WHERE schema_name = 'vendor';
```

### Array Contains (?|)

```sql
-- Find tasks with specific tags
SELECT * FROM workflow.entities
WHERE schema_name = 'task'
  AND data->'tags' ?| array['urgent', 'bug'];
```

### JSONB Path Queries (jsonb_path_query)

```sql
-- Complex nested queries
SELECT id, jsonb_path_query(data, '$.parameters.second_jump_height') as jump_height
FROM workflow.entities
WHERE schema_name = 'game_mechanic'
  AND jsonb_path_exists(data, '$.parameters.second_jump_height');
```

### Performance Considerations

**GIN Index Usage:**

```sql
-- This query uses GIN index
EXPLAIN ANALYZE
SELECT * FROM workflow.entities
WHERE data @> '{"status": "operational"}'::jsonb;

-- This query uses expression index (if created)
EXPLAIN ANALYZE
SELECT * FROM workflow.entities
WHERE data->>'status' = 'operational';
```

**Index Strategy:**

```sql
-- General GIN index (supports all JSONB operators)
CREATE INDEX idx_entities_data ON workflow.entities USING GIN (data);

-- Specific field index (faster for equality queries)
CREATE INDEX idx_entities_task_status ON workflow.entities
    ((data->>'status'))
    WHERE schema_name = 'task';

-- Composite index for common filter combinations
CREATE INDEX idx_entities_task_status_priority ON workflow.entities
    ((data->>'status'), (data->>'priority'))
    WHERE schema_name = 'task';
```

**Query Performance:**

| Query Pattern | Without Index | With GIN Index | With Expression Index |
|---------------|---------------|----------------|----------------------|
| `data @> '{}'` | 500ms | 50ms (10x) | N/A |
| `data->>'field' = ''` | 500ms | 100ms (5x) | 10ms (50x) |
| Full table scan | 500ms | 500ms | 500ms |

**Recommendations:**

1. Use GIN indexes for containment queries (@>)
2. Create expression indexes for frequently filtered fields
3. Limit result sets with WHERE and LIMIT
4. Monitor query performance with EXPLAIN ANALYZE
5. For < 10k entities, indexes matter less (all fast)

## Dynamic Schema Registration

AI assistants can register new entity schemas at runtime:

```python
@mcp.tool()
async def register_entity_schema(
    project_name: str,
    schema_name: str,
    schema_definition: dict,
    description: str = ""
) -> dict:
    """
    Register a new entity schema.

    Args:
        project_name: Project name
        schema_name: Unique schema name (snake_case)
        schema_definition: JSON Schema definition
        description: Human-readable description

    Returns:
        Schema info with ID

    Example:
        await register_entity_schema(
            project_name="my_game",
            schema_name="boss_encounter",
            schema_definition={
                "type": "object",
                "required": ["name", "difficulty"],
                "properties": {
                    "name": {"type": "string"},
                    "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
                    "phases": {"type": "integer", "minimum": 1}
                }
            },
            description="Boss encounter configuration"
        )
    """
    # Validate schema name
    if not re.match(r'^[a-z_][a-z0-9_]*$', schema_name):
        raise ValueError("Invalid schema name (must be snake_case)")

    # Validate JSON Schema
    try:
        jsonschema.Draft7Validator.check_schema(schema_definition)
    except jsonschema.SchemaError as e:
        raise ValueError(f"Invalid JSON Schema: {e}")

    # Insert schema
    async with conn_mgr.get_project_connection(project_name) as conn:
        schema_id = await conn.fetchval("""
            INSERT INTO workflow.entity_schemas
                (schema_name, schema_definition, description)
            VALUES ($1, $2, $3)
            RETURNING id
        """, schema_name, schema_definition, description)

    return {
        "schema_id": str(schema_id),
        "schema_name": schema_name,
        "description": description
    }
```

## Summary

The generic JSONB entity system provides:

- **Flexibility**: Schema evolution without migrations
- **Type Safety**: Pydantic validation at runtime
- **Performance**: GIN indexes for fast JSONB queries (< 200ms p95)
- **Extensibility**: AI can register new entity types dynamically
- **Project-Specific**: Each project defines its own entity types
- **PostgreSQL Power**: Full JSONB query capabilities

**Trade-off**: Slightly slower than column-based queries, but still fast enough for < 10k entities per schema type.
