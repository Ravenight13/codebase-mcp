# Workflow MCP Technical Stack

## Overview

This document details the technical stack for workflow-mcp, emphasizing the rationale for each technology choice and how they work together to deliver multi-project management with a generic entity system.

---

## Core Technologies

### Python 3.11+

**Why Python 3.11+**:
- **Async/await**: Native async support for high-concurrency database operations
- **Type hints**: Full static type checking with mypy --strict
- **Dataclasses**: Clean data structures with minimal boilerplate
- **Performance**: 10-60% faster than Python 3.10 (PEP 659 specializing adaptive interpreter)
- **Error messages**: Enhanced tracebacks for debugging

**Key Features Used**:
- `async/await` for all database operations (AsyncPG)
- Type hints for all function signatures and return types
- `dataclasses` for internal data structures
- `typing` module for generics and protocols

**Version Constraint**: ≥3.11 (exact version 3.11 or 3.12 recommended)

---

### PostgreSQL 14+

**Why PostgreSQL 14+**:
- **JSONB**: Native JSON storage with indexing for entity system
- **GIN indexes**: Fast queries on JSONB columns (containment, path operators)
- **Recursive CTEs**: Efficient work item hierarchy traversal
- **Materialized paths**: Fast ancestor queries without recursion
- **ACID transactions**: Guarantees for multi-table operations
- **Connection pooling**: Built-in support via pgBouncer or application-level (AsyncPG)

**PostgreSQL 14+ Features**:
- JSONB subscripting (`data['key']` syntax)
- Performance improvements for JSONB operations
- Multirange types (future: for date ranges in deployments)

**Database Architecture**:
```
workflow_registry/              # Registry database (always exists)
├── projects                    # All project metadata
├── active_project_config       # Singleton: current active project
└── connection_pool_stats       # Monitoring table (optional)

workflow_project_<uuid>/        # Project-specific database (per project)
├── work_items                  # Hierarchical work tracking
├── work_item_dependencies      # Dependency graph (blocked-by, depends-on)
├── tasks                       # Task management (may merge with work_items)
├── task_branches               # Git branch associations
├── task_commits                # Git commit associations
├── entities                    # Generic entity storage (JSONB)
├── entity_types                # Registered entity schemas (JSON Schema)
├── deployments                 # Deployment events
├── deployment_entities         # Many-to-many: deployments ↔ entities
└── deployment_work_items       # Many-to-many: deployments ↔ work_items
```

**JSONB Design Patterns**:
- **Entities table**: Single `data JSONB` column for all entity types
- **GIN index**: `CREATE INDEX idx_entities_data ON entities USING GIN (data);`
- **Containment queries**: `WHERE data @> '{"status": "operational"}'`
- **Path queries**: `WHERE data->>'status' = 'operational'`
- **Existence checks**: `WHERE data ? 'extractor_version'`

**Version Constraint**: ≥14.0 (PostgreSQL 15 or 16 recommended for performance)

---

### FastMCP Framework

**Why FastMCP**:
- **Official framework**: Built by Anthropic for MCP server development
- **Decorator-based**: Clean, Pythonic API for tool registration
- **Automatic schema generation**: No manual JSON-RPC boilerplate
- **Built-in validation**: Pydantic integration for inputs/outputs
- **SSE transport**: Server-Sent Events for MCP protocol
- **Progress reporting**: Native support for long-running operations
- **Resource API**: Expose project metadata as MCP resources

**Usage Pattern**:
```python
from fastmcp import FastMCP

mcp = FastMCP("workflow-mcp")

@mcp.tool()
async def create_project(
    name: str,
    description: str,
    metadata: dict | None = None
) -> dict:
    """Create a new project workspace with isolated database."""
    # Implementation validates inputs via Pydantic
    # Returns structured response
    return {"project_id": "...", "database": "workflow_project_..."}
```

**Key Features**:
- `@mcp.tool()`: Register async functions as MCP tools
- `@mcp.resource()`: Expose project metadata as resources
- `mcp.progress()`: Report progress for long operations (e.g., database creation)
- `mcp.error()`: Structured error responses matching MCP spec

**Non-Negotiable**: All MCP tools MUST use FastMCP decorators (no custom JSON-RPC)

---

### MCP Python SDK

**Why MCP Python SDK**:
- **Official protocol implementation**: Maintained by Anthropic
- **Type definitions**: Full TypeScript-like types for MCP messages
- **SSE transport**: Server-Sent Events implementation
- **Client utilities**: For testing and cross-MCP integration

**Integration with FastMCP**:
- FastMCP uses MCP Python SDK internally
- SDK provides transport layer (SSE)
- SDK validates message formats against spec

**Usage for Testing**:
```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async with stdio_client(StdioServerParameters(...)) as (read, write):
    async with ClientSession(read, write) as session:
        result = await session.call_tool("create_project", {"name": "test"})
```

---

### AsyncPG Driver

**Why AsyncPG**:
- **Performance**: 3-5x faster than psycopg2 for async operations
- **Native async**: Built for asyncio, no thread pool overhead
- **Connection pooling**: Built-in pool management with health checks
- **Prepared statements**: Automatic query plan caching
- **Type safety**: Direct mapping to Python types (no ORMs)

**Connection Pooling Architecture**:
```python
# Registry database pool (singleton)
registry_pool = await asyncpg.create_pool(
    dsn="postgresql://localhost/workflow_registry",
    min_size=2,
    max_size=10
)

# Project-specific pools (cached by project_id)
project_pools: dict[str, asyncpg.Pool] = {}

async def get_project_pool(project_id: str) -> asyncpg.Pool:
    if project_id not in project_pools:
        project_pools[project_id] = await asyncpg.create_pool(
            dsn=f"postgresql://localhost/workflow_project_{project_id}",
            min_size=1,
            max_size=5
        )
    return project_pools[project_id]
```

**Query Pattern** (No ORM):
```python
async with pool.acquire() as conn:
    # Prepared statement (automatic caching)
    entity = await conn.fetchrow(
        "SELECT * FROM entities WHERE entity_id = $1",
        entity_id
    )

    # Transaction for multi-table operations
    async with conn.transaction():
        await conn.execute("INSERT INTO entities (...) VALUES (...)")
        await conn.execute("INSERT INTO entity_types (...) VALUES (...)")
```

**Performance Benefits**:
- Connection reuse: <1ms overhead vs 10-50ms for new connection
- Prepared statements: Query planning amortized across calls
- Binary protocol: More efficient than text protocol (psycopg2)

**Version Constraint**: ≥0.29.0 (latest stable)

---

### Pydantic (v2)

**Why Pydantic v2**:
- **Data validation**: Runtime validation of all inputs/outputs
- **Type coercion**: Automatic type conversion (str → int, etc.)
- **JSON Schema generation**: For entity type schemas
- **Serialization**: Fast JSON serialization with `model_dump_json()`
- **Settings management**: Environment variable validation

**Usage Patterns**:

**1. Tool Input/Output Validation**:
```python
from pydantic import BaseModel, Field

class CreateProjectInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=1000)
    metadata: dict | None = None

class ProjectResponse(BaseModel):
    project_id: str
    name: str
    database: str
    created_at: str  # ISO 8601 format

@mcp.tool()
async def create_project(input: CreateProjectInput) -> ProjectResponse:
    # Pydantic validates input automatically
    project = await _create_project_in_db(input)
    return ProjectResponse(**project)
```

**2. Entity Data Validation**:
```python
from pydantic import ValidationError
import jsonschema

# Validate entity data against registered JSON Schema
def validate_entity_data(data: dict, schema: dict) -> None:
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as e:
        raise ValueError(f"Entity data validation failed: {e.message}")
```

**3. Work Item Metadata Validation**:
```python
from pydantic import BaseModel
from typing import Literal

class ProjectWorkItemMetadata(BaseModel):
    token_budget: int = Field(..., ge=1000, le=1_000_000)
    specification_file: str

class SessionWorkItemMetadata(BaseModel):
    token_usage: int = Field(0, ge=0)
    started_at: str  # ISO 8601
    completed_at: str | None = None

# Type-safe metadata per work item type
WorkItemMetadata = ProjectWorkItemMetadata | SessionWorkItemMetadata | ...
```

**mypy Integration**:
- Pydantic models fully typed
- mypy --strict passes with no `type: ignore`
- FastMCP uses Pydantic for tool parameter validation

**Version Constraint**: ≥2.0 (Pydantic v2 required for performance)

---

### JSON Schema (Draft 7)

**Why JSON Schema**:
- **Runtime validation**: Validate entity data against user-defined schemas
- **Language-agnostic**: Schemas portable across systems
- **Rich validation**: Types, enums, patterns, ranges, required fields
- **Documentation**: Self-documenting entity types

**Entity Type Registration**:
```python
# User registers vendor entity type with schema
register_entity_type(
    project_id="commission-uuid",
    type_name="vendor",
    schema={
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["operational", "broken"]
            },
            "extractor_version": {
                "type": "string",
                "pattern": "^\\d+\\.\\d+\\.\\d+$"  # Semantic versioning
            },
            "supports_html": {"type": "boolean"},
            "supports_pdf": {"type": "boolean"},
            "last_test_at": {
                "type": "string",
                "format": "date-time"
            }
        },
        "required": ["status", "extractor_version"],
        "additionalProperties": False  # Strict schema
    }
)

# Entity creation validates against schema
create_entity(
    project_id="commission-uuid",
    entity_type="vendor",
    name="EPSON",
    data={
        "status": "operational",
        "extractor_version": "1.2.0",
        "supports_html": True
        # Missing "supports_pdf" is OK (not required)
    }
)
# Validation passes

create_entity(..., data={"status": "unknown"})
# ValidationError: "unknown" not in enum ["operational", "broken"]
```

**Validation Library**: `jsonschema` Python package (reference implementation)

**Version Constraint**: JSON Schema Draft 7 (most widely supported)

---

## Development Tools

### mypy (Type Checker)

**Configuration** (`.mypy.ini` or `pyproject.toml`):
```ini
[mypy]
python_version = 3.11
strict = True
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
disallow_any_generics = True
no_implicit_optional = True
```

**Goal**: Zero type errors, no `type: ignore` comments

---

### ruff (Linter and Formatter)

**Why ruff**:
- **Fast**: 10-100x faster than flake8 + black
- **All-in-one**: Linting + formatting in one tool
- **Compatible**: Replaces flake8, isort, black, pyupgrade

**Configuration** (`pyproject.toml`):
```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "RUF"]
ignore = ["E501"]  # Line length handled by formatter
```

**Usage**:
```bash
ruff check .          # Lint
ruff format .         # Format
ruff check --fix .    # Auto-fix
```

---

### pytest (Testing Framework)

**Why pytest**:
- **Async support**: pytest-asyncio for async test functions
- **Fixtures**: Database setup/teardown, connection pools
- **Parametrization**: Test same function with multiple inputs
- **Coverage**: pytest-cov for coverage reporting

**Test Structure**:
```
tests/
├── unit/                      # Unit tests (no database)
│   ├── test_validation.py     # Pydantic model validation
│   └── test_schemas.py        # JSON Schema validation
├── integration/               # Integration tests (database)
│   ├── test_projects.py       # Project CRUD operations
│   ├── test_entities.py       # Entity system
│   └── test_isolation.py      # Multi-project isolation
└── protocol/                  # MCP protocol compliance
    └── test_mcp_tools.py      # Tool invocation contracts
```

**Fixture Example**:
```python
import pytest
import asyncpg

@pytest.fixture
async def registry_pool():
    """Fixture: Registry database connection pool."""
    pool = await asyncpg.create_pool("postgresql://localhost/workflow_registry_test")
    yield pool
    await pool.close()

@pytest.fixture
async def test_project(registry_pool):
    """Fixture: Create test project and clean up after."""
    project = await create_project_in_db(registry_pool, "test-project")
    yield project
    await delete_project_in_db(registry_pool, project["project_id"])
```

**Dependencies**:
- `pytest` ≥7.0
- `pytest-asyncio` ≥0.21 (async test support)
- `pytest-postgresql` ≥5.0 (database fixtures)
- `pytest-cov` ≥4.0 (coverage reporting)

---

### pytest-postgresql (Database Fixtures)

**Why pytest-postgresql**:
- **Isolated databases**: Each test gets fresh database
- **Fast setup**: Template database cloned per test
- **Cleanup**: Automatic teardown after tests

**Configuration** (`pyproject.toml`):
```toml
[tool.pytest.ini_options]
postgresql_exec = "/usr/local/bin/postgres"
postgresql_dbname = "workflow_test"
```

**Usage**:
```python
from pytest_postgresql import factories

# Create database factory
postgresql_proc = factories.postgresql_proc(port=5433)
postgresql = factories.postgresql("postgresql_proc")

def test_entity_creation(postgresql):
    # postgresql fixture provides connection to isolated database
    conn = postgresql
    # Run test...
```

---

## Infrastructure

### PostgreSQL Configuration

**Recommended Settings** (`postgresql.conf`):
```ini
# Connection pooling
max_connections = 200              # Support 100+ projects with pools

# Memory
shared_buffers = 256MB             # 25% of RAM for small systems
effective_cache_size = 1GB         # 50-75% of RAM

# JSONB Performance
# (GIN indexes automatically used for @> and ? operators)

# Logging (for development)
log_statement = 'all'              # Log all queries
log_duration = on                  # Log query duration
log_min_duration_statement = 100   # Log slow queries (>100ms)
```

**Connection Pooling Strategy**:
- **Registry pool**: Persistent, always connected (2-10 connections)
- **Project pools**: Lazy-loaded, cached per project (1-5 connections each)
- **Pool limits**: Max 200 total connections (PostgreSQL limit)

**Database Initialization**:
```bash
# Create registry database
createdb workflow_registry

# Run migrations (registry schema)
psql workflow_registry < migrations/001_registry_schema.sql

# Project databases created programmatically via create_project()
```

---

### Structured Logging

**Why Structured Logging**:
- **Parseable**: JSON logs for monitoring tools (Loki, Splunk)
- **Correlation IDs**: Track requests across tool invocations
- **No stdout pollution**: MCP protocol requires clean stdout

**Library Options**:
- **loguru**: Simple, powerful, no configuration
- **structlog**: More control, JSON output

**Configuration** (loguru):
```python
from loguru import logger

logger.remove()  # Remove default handler (stdout)
logger.add(
    "logs/workflow-mcp.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    rotation="100 MB",
    retention="30 days",
    level="INFO"
)

# Usage
logger.info("Project created", project_id="...", database="workflow_project_...")
logger.error("Entity validation failed", entity_type="vendor", error="...")
```

**Log Levels**:
- **DEBUG**: Database queries, connection pool stats
- **INFO**: Tool invocations, project switches, entity creation
- **WARNING**: Validation errors, optimistic locking conflicts
- **ERROR**: Database failures, unexpected errors
- **CRITICAL**: Server startup failures, protocol violations

---

## Performance Optimization

### Indexing Strategy

**Registry Database**:
```sql
-- Fast project lookup by name
CREATE INDEX idx_projects_name ON projects (name);

-- Active project queries
CREATE INDEX idx_active_project ON active_project_config (project_id);
```

**Project Databases**:
```sql
-- Work item hierarchy (materialized path)
CREATE INDEX idx_work_items_path ON work_items USING GIST (path);
CREATE INDEX idx_work_items_parent ON work_items (parent_id);

-- Entity queries (JSONB)
CREATE INDEX idx_entities_data ON entities USING GIN (data);
CREATE INDEX idx_entities_type_name ON entities (entity_type, name);

-- Task queries
CREATE INDEX idx_tasks_status ON tasks (status);
CREATE INDEX idx_tasks_branch ON tasks (branch);

-- Deployment queries
CREATE INDEX idx_deployments_deployed_at ON deployments (deployed_at DESC);
```

### Query Optimization

**JSONB Containment** (fast with GIN):
```sql
-- Find entities with status="broken"
SELECT * FROM entities
WHERE data @> '{"status": "broken"}'::jsonb;
-- Uses idx_entities_data GIN index
```

**Materialized Path** (fast ancestor queries):
```sql
-- Find all ancestors of work item
SELECT * FROM work_items
WHERE '/parent_id/child_id/' LIKE path || '%';
-- Uses idx_work_items_path GIST index
```

**Recursive CTE** (descendants query):
```sql
-- Find all descendants up to 5 levels
WITH RECURSIVE descendants AS (
  SELECT * FROM work_items WHERE work_item_id = $1
  UNION ALL
  SELECT wi.* FROM work_items wi
  JOIN descendants d ON wi.parent_id = d.work_item_id
  WHERE d.depth < 5
)
SELECT * FROM descendants;
```

---

## Deployment

### Local Development

**Prerequisites**:
- Python 3.11+ (`python --version`)
- PostgreSQL 14+ (`psql --version`)
- Git (`git --version`)

**Setup**:
```bash
# Clone repository
git clone https://github.com/user/workflow-mcp.git
cd workflow-mcp

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Initialize registry database
createdb workflow_registry
psql workflow_registry < migrations/001_registry_schema.sql

# Run tests
pytest

# Start MCP server
python -m workflow_mcp
```

---

### MCP Server Configuration

**Claude Desktop Configuration** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "workflow-mcp": {
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "workflow_mcp"],
      "env": {
        "DATABASE_URL": "postgresql://localhost/workflow_registry",
        "LOG_LEVEL": "INFO"
      }
    },
    "codebase-mcp": {
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "codebase_mcp"],
      "env": {...}
    }
  }
}
```

---

## Summary

**Technology Choices Rationale**:

| Technology | Reason | Alternative Rejected |
|------------|--------|----------------------|
| Python 3.11+ | Async, type hints, performance | Node.js (less type safety) |
| PostgreSQL 14+ | JSONB, GIN indexes, recursive CTEs | MongoDB (no ACID), SQLite (no JSONB GIN) |
| FastMCP | Official framework, decorator API | Custom JSON-RPC (protocol drift) |
| AsyncPG | 3-5x faster, native async | psycopg2 (sync, slower) |
| Pydantic v2 | Runtime validation, JSON Schema | dataclasses (no validation) |
| mypy | Static type checking | pyright (less mature) |
| ruff | Fast linting + formatting | flake8 + black (slower) |
| pytest | Async support, fixtures | unittest (less features) |

**Key Architectural Decisions**:
1. **Database-per-project**: Complete isolation, no cross-project queries
2. **JSONB for entities**: Generic storage, no schema migrations
3. **AsyncPG pools**: High performance, connection reuse
4. **Materialized paths**: Fast hierarchy queries without recursion
5. **Optimistic locking**: Version-based concurrency control

**Performance Targets Enabled By Stack**:
- AsyncPG: <1ms connection reuse, <10ms queries
- GIN indexes: <100ms JSONB queries on 10K+ entities
- Materialized paths: <10ms ancestor queries
- Connection pooling: <50ms project switching

This stack delivers production-ready performance, type safety, and flexibility for multi-project AI workflow management.
