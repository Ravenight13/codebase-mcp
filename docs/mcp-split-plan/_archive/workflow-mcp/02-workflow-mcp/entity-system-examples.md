# Generic Entity System Examples

## Overview

The generic entity system enables workflow-mcp to support ANY domain (commission work, game development, research, etc.) without code changes or schema migrations. This document provides detailed, concrete examples of how the system works.

---

## Architecture Overview

### Key Concepts

1. **Entity Type Registration**: Define JSON Schema for a domain-specific entity type
2. **Entity Creation**: Create entity instances validated against their type's schema
3. **JSONB Storage**: All entity data stored in a single `data JSONB` column
4. **Runtime Validation**: Pydantic + JSON Schema validate data at creation/update
5. **Flexible Queries**: PostgreSQL JSONB operators enable domain-specific queries

### Database Schema

**entity_types table** (per project):
```sql
CREATE TABLE entity_types (
    entity_type_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type_name VARCHAR(100) UNIQUE NOT NULL,  -- e.g., "vendor", "game_mechanic"
    description TEXT,
    schema JSONB NOT NULL,                   -- JSON Schema Draft 7
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(100) DEFAULT 'claude-code'
);
```

**entities table** (per project):
```sql
CREATE TABLE entities (
    entity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(100) NOT NULL REFERENCES entity_types(type_name),
    name VARCHAR(200) NOT NULL,              -- Human-readable name (e.g., "EPSON")
    data JSONB NOT NULL,                     -- Domain-specific data (validated against schema)
    metadata JSONB DEFAULT '{}'::jsonb,      -- Optional metadata (not validated)
    version INT DEFAULT 1,                   -- Optimistic locking
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(100) DEFAULT 'claude-code',
    updated_by VARCHAR(100) DEFAULT 'claude-code',
    UNIQUE (entity_type, name)               -- Unique names per type
);

-- GIN index for fast JSONB queries
CREATE INDEX idx_entities_data ON entities USING GIN (data);
CREATE INDEX idx_entities_type_name ON entities (entity_type, name);
```

---

## Example 1: Commission Work (Vendor Tracking)

### Use Case

Track vendor invoice extractors with operational status, version, format support, and test results. Vendors can be "operational" or "broken" and must support at least one format (HTML or PDF).

### Step 1: Register Vendor Entity Type

**MCP Tool Invocation**:
```python
register_entity_type(
    project_id="commission-work-uuid",
    type_name="vendor",
    description="Invoice extraction vendor status tracking",
    schema={
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["operational", "broken"],
                "description": "Current operational status of the vendor extractor"
            },
            "extractor_version": {
                "type": "string",
                "pattern": "^\\d+\\.\\d+\\.\\d+$",
                "description": "Semantic version of the extractor (e.g., 1.2.0)"
            },
            "supports_html": {
                "type": "boolean",
                "description": "Whether the extractor can parse HTML invoices"
            },
            "supports_pdf": {
                "type": "boolean",
                "description": "Whether the extractor can parse PDF invoices"
            },
            "last_test_at": {
                "type": "string",
                "format": "date-time",
                "description": "ISO 8601 timestamp of last test execution"
            },
            "test_results": {
                "type": "object",
                "properties": {
                    "tests_passed": {"type": "integer", "minimum": 0},
                    "tests_failed": {"type": "integer", "minimum": 0},
                    "coverage_percent": {"type": "number", "minimum": 0, "maximum": 100}
                }
            },
            "notes": {
                "type": "string",
                "maxLength": 1000,
                "description": "Optional notes about the vendor"
            }
        },
        "required": ["status", "extractor_version"],
        "additionalProperties": false  # Strict schema (no extra fields)
    }
)
```

**Response**:
```json
{
    "entity_type_id": "550e8400-e29b-41d4-a716-446655440000",
    "type_name": "vendor",
    "description": "Invoice extraction vendor status tracking",
    "schema": { /* full schema */ },
    "created_at": "2025-10-11T10:00:00Z"
}
```

### Step 2: Create EPSON Vendor Entity

**MCP Tool Invocation**:
```python
create_entity(
    project_id="commission-work-uuid",
    entity_type="vendor",
    name="EPSON",
    data={
        "status": "operational",
        "extractor_version": "1.2.0",
        "supports_html": True,
        "supports_pdf": False,
        "last_test_at": "2025-10-11T09:30:00Z",
        "test_results": {
            "tests_passed": 24,
            "tests_failed": 0,
            "coverage_percent": 87.5
        }
    }
)
```

**Validation Flow**:
1. Check entity type "vendor" exists in project
2. Validate data against vendor JSON Schema using `jsonschema` library
3. Ensure required fields present: `status`, `extractor_version`
4. Validate enum: `status` must be "operational" or "broken"
5. Validate pattern: `extractor_version` must match `^\d+\.\d+\.\d+$`
6. Validate format: `last_test_at` must be ISO 8601 date-time
7. Store in entities table with version=1

**Response**:
```json
{
    "entity_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
    "entity_type": "vendor",
    "name": "EPSON",
    "data": { /* full data object */ },
    "version": 1,
    "created_at": "2025-10-11T10:05:00Z"
}
```

### Step 3: Create Canon Vendor Entity (Broken)

**MCP Tool Invocation**:
```python
create_entity(
    project_id="commission-work-uuid",
    entity_type="vendor",
    name="Canon",
    data={
        "status": "broken",
        "extractor_version": "0.9.0",
        "supports_html": True,
        "supports_pdf": True,
        "last_test_at": "2025-10-10T14:00:00Z",
        "test_results": {
            "tests_passed": 18,
            "tests_failed": 6,
            "coverage_percent": 75.0
        },
        "notes": "Failing on multi-page PDFs - investigate pagination logic"
    }
)
```

**Response**:
```json
{
    "entity_id": "b2c3d4e5-f678-9012-3456-7890abcdef12",
    "entity_type": "vendor",
    "name": "Canon",
    "data": { /* full data object */ },
    "version": 1,
    "created_at": "2025-10-11T10:10:00Z"
}
```

### Step 4: Query All Broken Vendors

**MCP Tool Invocation**:
```python
query_entities(
    project_id="commission-work-uuid",
    entity_type="vendor",
    filters={"data": {"status": "broken"}},
    limit=10
)
```

**SQL Query Generated** (AsyncPG):
```sql
SELECT
    entity_id,
    entity_type,
    name,
    data,
    version,
    created_at,
    updated_at
FROM entities
WHERE
    entity_type = 'vendor'
    AND data @> '{"status": "broken"}'::jsonb  -- JSONB containment operator
ORDER BY updated_at DESC
LIMIT 10;
```

**Response**:
```json
{
    "entities": [
        {
            "entity_id": "b2c3d4e5-f678-9012-3456-7890abcdef12",
            "entity_type": "vendor",
            "name": "Canon",
            "data": {
                "status": "broken",
                "extractor_version": "0.9.0",
                "supports_html": true,
                "supports_pdf": true,
                "test_results": {
                    "tests_passed": 18,
                    "tests_failed": 6,
                    "coverage_percent": 75.0
                },
                "notes": "Failing on multi-page PDFs - investigate pagination logic"
            },
            "version": 1
        }
    ],
    "total_count": 1
}
```

### Step 5: Update Canon Vendor to Operational

**MCP Tool Invocation**:
```python
update_entity(
    entity_id="b2c3d4e5-f678-9012-3456-7890abcdef12",
    version=1,  # Must match current version (optimistic locking)
    data_updates={
        "status": "operational",
        "extractor_version": "1.0.0",
        "test_results": {
            "tests_passed": 24,
            "tests_failed": 0,
            "coverage_percent": 85.0
        },
        "notes": "Fixed pagination logic - all tests passing"
    }
)
```

**Validation Flow**:
1. Check version=1 matches current version in database
2. Merge data_updates with existing data
3. Validate merged data against vendor JSON Schema
4. Increment version to 2
5. Update updated_at timestamp

**SQL Query Generated**:
```sql
UPDATE entities
SET
    data = $1,  -- Merged data (existing + updates)
    version = version + 1,
    updated_at = NOW(),
    updated_by = 'claude-code'
WHERE
    entity_id = $2
    AND version = $3  -- Optimistic locking check
RETURNING *;
```

**Response**:
```json
{
    "entity_id": "b2c3d4e5-f678-9012-3456-7890abcdef12",
    "entity_type": "vendor",
    "name": "Canon",
    "data": {
        "status": "operational",
        "extractor_version": "1.0.0",
        "supports_html": true,
        "supports_pdf": true,
        "test_results": {
            "tests_passed": 24,
            "tests_failed": 0,
            "coverage_percent": 85.0
        },
        "notes": "Fixed pagination logic - all tests passing"
    },
    "version": 2,
    "updated_at": "2025-10-11T15:30:00Z"
}
```

### Step 6: Query Vendors Supporting PDF

**MCP Tool Invocation**:
```python
query_entities(
    project_id="commission-work-uuid",
    entity_type="vendor",
    filters={"data": {"supports_pdf": True}},
    limit=10
)
```

**SQL Query Generated**:
```sql
SELECT * FROM entities
WHERE
    entity_type = 'vendor'
    AND data @> '{"supports_pdf": true}'::jsonb
ORDER BY updated_at DESC
LIMIT 10;
```

**Response**: Returns Canon (supports_pdf: true), excludes EPSON (supports_pdf: false).

---

## Example 2: Game Development (Mechanic Tracking)

### Use Case

Track TTRPG game mechanics with type classification (combat, skill, magic), implementation status, complexity ratings, dependencies, and playtesting results. Mechanics progress through design → prototype → playtesting → complete stages.

### Step 1: Register Game Mechanic Entity Type

**MCP Tool Invocation**:
```python
register_entity_type(
    project_id="ttrpg-core-uuid",
    type_name="game_mechanic",
    description="Core game system mechanics tracking",
    schema={
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "mechanic_type": {
                "type": "string",
                "enum": ["combat", "skill", "magic", "social", "crafting"],
                "description": "Category of game mechanic"
            },
            "implementation_status": {
                "type": "string",
                "enum": ["design", "prototype", "playtesting", "complete"],
                "description": "Current development stage"
            },
            "complexity": {
                "type": "integer",
                "minimum": 1,
                "maximum": 5,
                "description": "Complexity rating (1=simple, 5=very complex)"
            },
            "dependencies": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Names of other mechanics this depends on"
            },
            "playtests_completed": {
                "type": "integer",
                "minimum": 0,
                "description": "Number of completed playtests"
            },
            "playtests_required": {
                "type": "integer",
                "minimum": 0,
                "description": "Number of playtests needed before complete"
            },
            "feedback_summary": {
                "type": "string",
                "maxLength": 2000,
                "description": "Summary of playtest feedback"
            },
            "design_document": {
                "type": "string",
                "description": "Path to design document"
            }
        },
        "required": ["mechanic_type", "implementation_status", "complexity"],
        "additionalProperties": false
    }
)
```

### Step 2: Create Skill Check Mechanic

**MCP Tool Invocation**:
```python
create_entity(
    project_id="ttrpg-core-uuid",
    entity_type="game_mechanic",
    name="Skill Check System",
    data={
        "mechanic_type": "skill",
        "implementation_status": "prototype",
        "complexity": 3,
        "dependencies": ["Attribute System", "Dice Rolling"],
        "playtests_completed": 2,
        "playtests_required": 5,
        "feedback_summary": "Players like difficulty tiers but confused by modifiers",
        "design_document": "docs/mechanics/skill-checks.md"
    }
)
```

**Response**:
```json
{
    "entity_id": "c3d4e5f6-7890-1234-5678-90abcdef1234",
    "entity_type": "game_mechanic",
    "name": "Skill Check System",
    "data": { /* full data */ },
    "version": 1,
    "created_at": "2025-10-11T11:00:00Z"
}
```

### Step 3: Create Combat Initiative Mechanic

**MCP Tool Invocation**:
```python
create_entity(
    project_id="ttrpg-core-uuid",
    entity_type="game_mechanic",
    name="Combat Initiative",
    data={
        "mechanic_type": "combat",
        "implementation_status": "complete",
        "complexity": 2,
        "dependencies": ["Attribute System"],
        "playtests_completed": 8,
        "playtests_required": 5,
        "feedback_summary": "Very positive - simple and fast",
        "design_document": "docs/mechanics/initiative.md"
    }
)
```

### Step 4: Query All Prototype Mechanics

**MCP Tool Invocation**:
```python
query_entities(
    project_id="ttrpg-core-uuid",
    entity_type="game_mechanic",
    filters={"data": {"implementation_status": "prototype"}},
    limit=10
)
```

**SQL Query Generated**:
```sql
SELECT * FROM entities
WHERE
    entity_type = 'game_mechanic'
    AND data @> '{"implementation_status": "prototype"}'::jsonb
ORDER BY updated_at DESC
LIMIT 10;
```

**Response**: Returns "Skill Check System" (prototype), excludes "Combat Initiative" (complete).

### Step 5: Query Combat Mechanics Only

**MCP Tool Invocation**:
```python
query_entities(
    project_id="ttrpg-core-uuid",
    entity_type="game_mechanic",
    filters={"data": {"mechanic_type": "combat"}},
    limit=10
)
```

**SQL Query Generated**:
```sql
SELECT * FROM entities
WHERE
    entity_type = 'game_mechanic'
    AND data @> '{"mechanic_type": "combat"}'::jsonb
ORDER BY updated_at DESC
LIMIT 10;
```

**Response**: Returns "Combat Initiative", excludes "Skill Check System".

### Step 6: Update Skill Check to Playtesting

**MCP Tool Invocation**:
```python
update_entity(
    entity_id="c3d4e5f6-7890-1234-5678-90abcdef1234",
    version=1,
    data_updates={
        "implementation_status": "playtesting",
        "playtests_completed": 3,
        "feedback_summary": "Updated modifier rules based on feedback - testing new version"
    }
)
```

**Response**:
```json
{
    "entity_id": "c3d4e5f6-7890-1234-5678-90abcdef1234",
    "entity_type": "game_mechanic",
    "name": "Skill Check System",
    "data": {
        "mechanic_type": "skill",
        "implementation_status": "playtesting",  // Changed
        "complexity": 3,
        "dependencies": ["Attribute System", "Dice Rolling"],
        "playtests_completed": 3,  // Incremented
        "playtests_required": 5,
        "feedback_summary": "Updated modifier rules based on feedback - testing new version",
        "design_document": "docs/mechanics/skill-checks.md"
    },
    "version": 2,
    "updated_at": "2025-10-11T16:00:00Z"
}
```

---

## Advanced Query Patterns

### Pattern 1: Nested Property Queries

**Use Case**: Find vendors with >80% test coverage

**SQL Query**:
```sql
SELECT * FROM entities
WHERE
    entity_type = 'vendor'
    AND (data->'test_results'->>'coverage_percent')::float > 80
ORDER BY updated_at DESC;
```

**Python Code**:
```python
async with pool.acquire() as conn:
    query = """
        SELECT * FROM entities
        WHERE entity_type = $1
        AND (data->'test_results'->>'coverage_percent')::float > $2
        ORDER BY updated_at DESC
    """
    entities = await conn.fetch(query, 'vendor', 80.0)
```

### Pattern 2: Array Contains

**Use Case**: Find mechanics that depend on "Attribute System"

**SQL Query**:
```sql
SELECT * FROM entities
WHERE
    entity_type = 'game_mechanic'
    AND data->'dependencies' @> '["Attribute System"]'::jsonb
ORDER BY updated_at DESC;
```

### Pattern 3: Multiple Filters

**Use Case**: Find operational vendors supporting both HTML and PDF

**SQL Query**:
```sql
SELECT * FROM entities
WHERE
    entity_type = 'vendor'
    AND data @> '{"status": "operational", "supports_html": true, "supports_pdf": true}'::jsonb
ORDER BY updated_at DESC;
```

### Pattern 4: Field Existence Check

**Use Case**: Find vendors with test results

**SQL Query**:
```sql
SELECT * FROM entities
WHERE
    entity_type = 'vendor'
    AND data ? 'test_results'  -- ? operator checks for key existence
ORDER BY updated_at DESC;
```

### Pattern 5: Negation (NOT)

**Use Case**: Find mechanics NOT in complete status

**SQL Query**:
```sql
SELECT * FROM entities
WHERE
    entity_type = 'game_mechanic'
    AND NOT (data @> '{"implementation_status": "complete"}'::jsonb)
ORDER BY updated_at DESC;
```

---

## Optimistic Locking Example

### Scenario: Concurrent Updates

**Initial State**:
```json
{
    "entity_id": "...",
    "name": "Canon",
    "data": {"status": "broken", "extractor_version": "0.9.0"},
    "version": 1
}
```

**User A** (at 10:00:00):
```python
# Read entity
entity = query_entity("canon-uuid")  # version=1

# Modify locally
entity["data"]["status"] = "operational"
entity["data"]["extractor_version"] = "1.0.0"
```

**User B** (at 10:00:05, before A commits):
```python
# Read entity
entity = query_entity("canon-uuid")  # version=1

# Modify locally
entity["data"]["notes"] = "Fixed pagination bug"
```

**User A commits** (at 10:00:10):
```python
update_entity(
    entity_id="canon-uuid",
    version=1,  # Matches current version
    data_updates={"status": "operational", "extractor_version": "1.0.0"}
)
# SUCCESS: version incremented to 2
```

**User B commits** (at 10:00:15):
```python
update_entity(
    entity_id="canon-uuid",
    version=1,  # DOES NOT match current version (now 2)
    data_updates={"notes": "Fixed pagination bug"}
)
# ERROR: VersionMismatchError
# Message: "Entity was modified by another user. Please re-fetch and try again."
```

**User B retries** (at 10:00:20):
```python
# Re-fetch entity
entity = query_entity("canon-uuid")  # version=2, includes A's changes

# Merge B's changes with A's changes
update_entity(
    entity_id="canon-uuid",
    version=2,  # Now matches
    data_updates={"notes": "Fixed pagination bug"}
)
# SUCCESS: version incremented to 3
```

---

## Multi-Project Isolation Example

### Scenario: Commission and Game Dev Projects

**Commission Project**:
```python
# Create commission project
commission = create_project(name="invoice-extraction", description="Commission work")

# Register vendor entity type
register_entity_type(project_id=commission["project_id"], type_name="vendor", schema={...})

# Create EPSON vendor
create_entity(project_id=commission["project_id"], entity_type="vendor", name="EPSON", data={...})
```

**Game Dev Project**:
```python
# Create game dev project
game = create_project(name="ttrpg-core", description="Game development")

# Register game_mechanic entity type
register_entity_type(project_id=game["project_id"], type_name="game_mechanic", schema={...})

# Create skill check mechanic
create_entity(project_id=game["project_id"], entity_type="game_mechanic", name="Skill Check System", data={...})
```

**Isolation Validation**:
```python
# Query vendors in commission project
vendors = query_entities(project_id=commission["project_id"], entity_type="vendor")
# Returns: [{"name": "EPSON", ...}]

# Query vendors in game dev project
vendors_game = query_entities(project_id=game["project_id"], entity_type="vendor")
# Returns: [] (no vendors in game dev project)

# Query mechanics in game dev project
mechanics = query_entities(project_id=game["project_id"], entity_type="game_mechanic")
# Returns: [{"name": "Skill Check System", ...}]

# Query mechanics in commission project
mechanics_commission = query_entities(project_id=commission["project_id"], entity_type="game_mechanic")
# Returns: [] (no mechanics in commission project)
```

**Key Point**: Each project has its own database (`workflow_project_<uuid>`), so entities never leak across projects.

---

## Performance Characteristics

### GIN Index Benefits

**Without GIN Index**:
```sql
-- Sequential scan on 10,000 entities: ~100-200ms
SELECT * FROM entities WHERE data @> '{"status": "broken"}'::jsonb;
```

**With GIN Index**:
```sql
-- Index scan: ~5-10ms
CREATE INDEX idx_entities_data ON entities USING GIN (data);
SELECT * FROM entities WHERE data @> '{"status": "broken"}'::jsonb;
```

### Query Complexity

| Query Type | Example | Latency (10K entities) |
|------------|---------|------------------------|
| Simple containment | `data @> '{"status": "broken"}'` | 5-10ms |
| Nested property | `data->'test_results'->>'coverage'` | 10-20ms |
| Array contains | `data->'dependencies' @> '["X"]'` | 10-20ms |
| Multiple filters | `data @> '{"status": "operational", "supports_pdf": true}'` | 10-20ms |
| Full scan (no index) | `data->>'notes' LIKE '%bug%'` | 100-200ms |

---

## Summary

The generic entity system demonstrates:

1. **Domain Agnosticism**: Same code handles vendors, mechanics, papers, etc.
2. **Type Safety**: JSON Schema validation at creation/update
3. **Flexibility**: New entity types without code changes
4. **Performance**: GIN indexes enable fast JSONB queries
5. **Isolation**: Entities never leak across projects
6. **Concurrency**: Optimistic locking prevents lost updates

This architecture enables workflow-mcp to support unlimited domain types while maintaining performance, type safety, and data integrity.
