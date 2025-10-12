# Database Architecture Design

## Overview

The MCP split uses a **database-per-project** pattern with a central registry database for project discovery. Each project database contains both `codebase` and `workflow` schemas for complete data isolation.

## PostgreSQL Instance Layout

```
PostgreSQL Instance (localhost:5432)
├── mcp_registry (database)
│   └── public schema
│       └── projects table
├── project_myapp (database)
│   ├── codebase schema
│   │   ├── repositories
│   │   ├── code_chunks
│   │   └── embeddings
│   └── workflow schema
│       ├── entity_schemas
│       └── entities
├── project_website (database)
│   ├── codebase schema
│   └── workflow schema
└── project_gameengine (database)
    ├── codebase schema
    └── workflow schema
```

## Registry Database Schema

### Database: `mcp_registry`

The registry is the single source of truth for all projects.

#### Table: `projects`

```sql
CREATE DATABASE mcp_registry;

\c mcp_registry

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS projects (
    -- Identity
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    database_name TEXT NOT NULL UNIQUE,

    -- Metadata
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by TEXT NOT NULL DEFAULT 'claude-code',

    -- Validation constraints
    CONSTRAINT valid_name CHECK (name ~ '^[a-z0-9_]+$'),
    CONSTRAINT valid_db_name CHECK (database_name ~ '^project_[a-z0-9_]+$')
);

-- Indexes for fast lookup
CREATE INDEX idx_projects_name ON projects(name);
CREATE INDEX idx_projects_database_name ON projects(database_name);

-- Updated timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

**Performance Targets:**
- Lookup by name: < 1ms (indexed)
- Project list: < 10ms (< 20 projects)
- Insert new project: < 50ms

**Example Data:**
```sql
INSERT INTO projects (name, database_name, description) VALUES
    ('myapp', 'project_myapp', 'Main application codebase'),
    ('website', 'project_website', 'Marketing website'),
    ('gameengine', 'project_gameengine', 'Unity game project');
```

## Project Database Schema

Each project gets its own database with two schemas: `codebase` and `workflow`.

### Schema: `codebase`

Used by **codebase-mcp** for semantic code search.

```sql
-- Create project database
CREATE DATABASE project_myapp;

\c project_myapp

-- Create schemas
CREATE SCHEMA IF NOT EXISTS codebase;
CREATE SCHEMA IF NOT EXISTS workflow;

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;  -- pgvector for embeddings

-- Set search path
SET search_path TO codebase, public;
```

#### Table: `codebase.repositories`

Tracks indexed code repositories.

```sql
CREATE TABLE IF NOT EXISTS codebase.repositories (
    -- Identity
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    repo_path TEXT NOT NULL UNIQUE,

    -- Metadata
    name TEXT NOT NULL,
    last_indexed_at TIMESTAMPTZ,
    total_files INTEGER DEFAULT 0,
    total_chunks INTEGER DEFAULT 0,
    indexing_duration_seconds NUMERIC(10, 2),
    indexing_status TEXT NOT NULL DEFAULT 'pending',

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Validation
    CONSTRAINT valid_status CHECK (indexing_status IN ('pending', 'in_progress', 'completed', 'failed'))
);

CREATE INDEX idx_repositories_repo_path ON codebase.repositories(repo_path);
CREATE INDEX idx_repositories_status ON codebase.repositories(indexing_status);
```

#### Table: `codebase.code_chunks`

Stores code chunks with embeddings for semantic search.

```sql
CREATE TABLE IF NOT EXISTS codebase.code_chunks (
    -- Identity
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    repository_id UUID NOT NULL REFERENCES codebase.repositories(id) ON DELETE CASCADE,

    -- Code content
    file_path TEXT NOT NULL,
    file_type TEXT,
    content TEXT NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,

    -- Embedding (1536 dimensions for OpenAI ada-002, or 768 for sentence-transformers)
    embedding vector(768) NOT NULL,

    -- Context (optional)
    context_before TEXT,
    context_after TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Validation
    CONSTRAINT valid_line_numbers CHECK (start_line > 0 AND end_line >= start_line)
);

-- Indexes for performance
CREATE INDEX idx_code_chunks_repository ON codebase.code_chunks(repository_id);
CREATE INDEX idx_code_chunks_file_path ON codebase.code_chunks(file_path);
CREATE INDEX idx_code_chunks_file_type ON codebase.code_chunks(file_type);

-- CRITICAL: Vector similarity index for fast semantic search
CREATE INDEX idx_code_chunks_embedding ON codebase.code_chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
```

**Vector Index Notes:**
- `ivfflat` index type for approximate nearest neighbor (ANN) search
- `vector_cosine_ops` uses cosine similarity (most common for embeddings)
- `lists = 100` appropriate for 10k-100k chunks (adjust based on data size)
- Build index AFTER bulk insert for better performance

**Performance Targets:**
- Semantic search (10 results): < 500ms p95
- Embedding storage overhead: ~3KB per chunk (768 dimensions × 4 bytes)
- Index build time: ~30s for 100k chunks

### Schema: `workflow`

Used by **workflow-mcp** for AI project management.

#### Table: `workflow.entity_schemas`

Stores JSON Schema definitions for entity types.

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

-- Example schemas
INSERT INTO workflow.entity_schemas (schema_name, schema_definition, description) VALUES
(
    'task',
    '{
        "type": "object",
        "required": ["title", "status"],
        "properties": {
            "title": {"type": "string", "minLength": 1, "maxLength": 200},
            "status": {"type": "string", "enum": ["pending", "in_progress", "completed", "blocked"]},
            "description": {"type": "string"},
            "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
            "assignee": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}},
            "due_date": {"type": "string", "format": "date-time"}
        }
    }'::jsonb,
    'Development task entity'
),
(
    'vendor',
    '{
        "type": "object",
        "required": ["name", "status"],
        "properties": {
            "name": {"type": "string", "minLength": 1, "maxLength": 100},
            "status": {"type": "string", "enum": ["operational", "broken"]},
            "extractor_version": {"type": "string", "pattern": "^[0-9]+\\\\.[0-9]+\\\\.[0-9]+$"},
            "last_test_date": {"type": "string", "format": "date-time"},
            "test_results": {"type": "object"},
            "format_support": {
                "type": "object",
                "properties": {
                    "pdf": {"type": "boolean"},
                    "xml": {"type": "boolean"},
                    "csv": {"type": "boolean"}
                }
            }
        }
    }'::jsonb,
    'Invoice vendor/supplier entity'
);
```

#### Table: `workflow.entities`

Generic JSONB storage for all entity types.

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

**JSONB Index Notes:**
- `GIN (data)`: Supports all JSONB operators (@>, ?, etc.)
- `GIN (data jsonb_path_ops)`: Faster for containment (@>) but fewer operators
- Expression indexes: Extract specific fields for faster equality queries
- Build indexes based on actual query patterns

**Performance Targets:**
- Entity creation: < 100ms p95
- Entity update (optimistic lock): < 100ms p95
- Query by schema + filter: < 200ms p95 (< 10k entities)
- JSONB query overhead: ~2-5x slower than column query, still fast

## Connection Pooling Strategy

### Registry Pool (Singleton)

Both MCPs maintain a persistent connection pool to the registry database:

```python
from asyncpg import create_pool

# Shared registry pool configuration
REGISTRY_POOL_CONFIG = {
    'min_size': 2,       # Always maintain 2 connections
    'max_size': 10,      # Scale up to 10 for bursts
    'max_queries': 50000,  # Recycle after 50k queries
    'max_inactive_connection_lifetime': 300.0,  # 5 minutes
    'command_timeout': 60.0,  # 60 seconds
}

registry_pool = await create_pool(
    dsn="postgresql://user:pass@localhost/mcp_registry",
    **REGISTRY_POOL_CONFIG
)
```

### Per-Project Pools (Lazy + Cached)

Each project database gets its own pool, created on first access:

```python
# Per-project pool configuration (more conservative)
PROJECT_POOL_CONFIG = {
    'min_size': 1,       # Keep 1 connection warm
    'max_size': 5,       # Max 5 concurrent queries per project
    'max_queries': 50000,
    'max_inactive_connection_lifetime': 600.0,  # 10 minutes
    'command_timeout': 120.0,  # 2 minutes (indexing can be slow)
}

# Cache: project_name -> asyncpg.Pool
project_pools: Dict[str, asyncpg.Pool] = {}

async def get_project_pool(project_name: str) -> asyncpg.Pool:
    if project_name not in project_pools:
        # Lookup database name from registry
        async with registry_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT database_name FROM projects WHERE name = $1",
                project_name
            )
        if not row:
            raise ValueError(f"Project '{project_name}' not found")

        # Create new pool
        dsn = f"postgresql://user:pass@localhost/{row['database_name']}"
        pool = await create_pool(dsn, **PROJECT_POOL_CONFIG)
        project_pools[project_name] = pool

    return project_pools[project_name]
```

### Connection Pool Sizing

**Assumptions:**
- 2 concurrent MCP operations max (Claude Code typical usage)
- 20 projects in workspace
- Most projects idle at any given time

**Memory Calculation:**
- Registry pool: 2-10 connections = ~5MB
- Active project pool: 1-5 connections = ~2.5MB
- 2 active projects: 2 × 2.5MB = 5MB
- Total: ~10MB for connection pools (negligible)

**PostgreSQL Side:**
- Default `max_connections`: 200
- Registry: 10 × 2 MCPs = 20 connections
- Projects: 5 × 2 active × 2 MCPs = 20 connections
- Total: 40 connections (20% of limit)

**Scaling to 20 Projects (all active):**
- Projects: 5 × 20 × 2 MCPs = 200 connections
- Approaches PostgreSQL limit
- Solution: Reduce per-project max_size to 3 (120 connections total)

## Performance Considerations

### < 20 Projects: No Issues

- Registry queries: < 1ms (indexed by name)
- Project pool creation: < 50ms (lazy, cached)
- Query performance: Same as single-project
- Memory overhead: 10-50MB total

### Index Strategy for Performance

#### Registry Database

```sql
-- Already have these from schema above
CREATE INDEX idx_projects_name ON projects(name);  -- Exact match lookups
CREATE INDEX idx_projects_database_name ON projects(database_name);  -- Reverse lookups
```

#### Codebase Schema

```sql
-- Code chunk retrieval by repository
CREATE INDEX idx_code_chunks_repository ON codebase.code_chunks(repository_id);

-- File path filtering
CREATE INDEX idx_code_chunks_file_path ON codebase.code_chunks(file_path);

-- File type filtering (e.g., only search .py files)
CREATE INDEX idx_code_chunks_file_type ON codebase.code_chunks(file_type);

-- CRITICAL: Vector similarity search
CREATE INDEX idx_code_chunks_embedding ON codebase.code_chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);  -- Tune based on data size

-- Composite index for common filters
CREATE INDEX idx_code_chunks_repo_file_type
    ON codebase.code_chunks(repository_id, file_type);
```

#### Workflow Schema

```sql
-- Entity filtering by type
CREATE INDEX idx_entities_schema_name ON workflow.entities(schema_name);

-- Temporal queries
CREATE INDEX idx_entities_created_at ON workflow.entities(created_at DESC);
CREATE INDEX idx_entities_updated_at ON workflow.entities(updated_at DESC);

-- Soft delete filtering
CREATE INDEX idx_entities_deleted_at ON workflow.entities(deleted_at)
    WHERE deleted_at IS NULL;

-- CRITICAL: JSONB queries
CREATE INDEX idx_entities_data ON workflow.entities USING GIN (data);

-- Specific field extractions (create based on query patterns)
CREATE INDEX idx_entities_task_status ON workflow.entities
    ((data->>'status'))
    WHERE schema_name = 'task';

CREATE INDEX idx_entities_task_priority ON workflow.entities
    ((data->>'priority'))
    WHERE schema_name = 'task';

CREATE INDEX idx_entities_vendor_name ON workflow.entities
    ((data->>'name'))
    WHERE schema_name = 'vendor';
```

### Query Performance Targets

| Operation | Target Latency | Notes |
|-----------|---------------|-------|
| Registry lookup | < 1ms p95 | Indexed name lookup |
| Project pool creation | < 50ms | First access only |
| Code semantic search | < 500ms p95 | 10-100 results, ivfflat index |
| Entity create | < 100ms p95 | JSONB insert + validation |
| Entity update | < 100ms p95 | Optimistic lock check |
| Entity query | < 200ms p95 | < 10k entities, GIN indexed |
| Repository indexing | < 60s | 10k files, batch inserts |

### Scaling Limits

| Metric | Comfortable | Warning | Action Required |
|--------|-------------|---------|-----------------|
| Projects | < 20 | 20-50 | 50+ (reduce pool sizes) |
| Code chunks/project | < 100k | 100k-500k | 500k+ (tune ivfflat lists) |
| Entities/project | < 50k | 50k-200k | 200k+ (partition table) |
| Total DB size | < 10GB | 10-50GB | 50GB+ (vacuum, archive) |
| Concurrent queries | < 10 | 10-50 | 50+ (add PgBouncer) |

## Database Initialization Scripts

### Registry Setup

```sql
-- Create registry database and tables
CREATE DATABASE mcp_registry;

\c mcp_registry

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Run projects table DDL from above
\i create_registry_schema.sql

-- Verify
SELECT * FROM projects;
```

### Project Database Setup

```sql
-- Function to initialize a new project database
CREATE OR REPLACE FUNCTION initialize_project_database(p_database_name TEXT)
RETURNS VOID AS $$
BEGIN
    -- Create database (requires superuser or CREATEDB privilege)
    EXECUTE format('CREATE DATABASE %I', p_database_name);

    -- Connect and initialize schemas (in separate transaction)
    EXECUTE format('
        \c %I;
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
        CREATE EXTENSION IF NOT EXISTS vector;
        CREATE SCHEMA IF NOT EXISTS codebase;
        CREATE SCHEMA IF NOT EXISTS workflow;
    ', p_database_name);
END;
$$ LANGUAGE plpgsql;

-- Usage
SELECT initialize_project_database('project_myapp');
```

**Note:** In practice, database creation should be done via `asyncpg` from the MCP tool:

```python
@mcp.tool()
async def create_project(name: str, description: str = "") -> dict:
    """Create a new project with isolated database."""
    database_name = f"project_{name}"

    # Insert into registry
    async with conn_mgr.registry_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO projects (name, database_name, description)
            VALUES ($1, $2, $3)
        """, name, database_name, description)

    # Create project database
    system_conn = await asyncpg.connect(
        host=host, port=port, user=user, password=password, database='postgres'
    )
    await system_conn.execute(f'CREATE DATABASE {database_name}')
    await system_conn.close()

    # Initialize schemas
    project_conn = await asyncpg.connect(
        host=host, port=port, user=user, password=password, database=database_name
    )
    await project_conn.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    await project_conn.execute('CREATE EXTENSION IF NOT EXISTS vector')
    await project_conn.execute('CREATE SCHEMA IF NOT EXISTS codebase')
    await project_conn.execute('CREATE SCHEMA IF NOT EXISTS workflow')
    await project_conn.close()

    return {"name": name, "database_name": database_name}
```

## Backup and Recovery

### Registry Database Backup

Critical for disaster recovery - contains project catalog:

```bash
pg_dump -h localhost -U mcp_user -d mcp_registry > mcp_registry_backup.sql
```

### Project Database Backup

Each project database should be backed up independently:

```bash
# Backup all project databases
for db in $(psql -h localhost -U mcp_user -d mcp_registry -t -c "SELECT database_name FROM projects"); do
    pg_dump -h localhost -U mcp_user -d "$db" > "${db}_backup.sql"
done
```

### Restore Strategy

1. Restore registry database first
2. Restore project databases based on registry
3. Verify schema integrity
4. Rebuild vector indexes if needed

## Summary

The database architecture provides:

- **Isolation**: Database-per-project prevents cross-contamination
- **Performance**: Indexed queries meet < 500ms targets for < 20 projects
- **Scalability**: Connection pooling supports 20-50 projects comfortably
- **Flexibility**: JSONB entities allow schema evolution without migrations
- **Reliability**: Optimistic locking, soft deletes, and comprehensive indexes
