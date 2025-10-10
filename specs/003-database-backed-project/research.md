# Technical Research: Project Status Tracking System

**Feature**: 003-database-backed-project
**Date**: 2025-10-10
**Phase**: Phase 0 - Research & Technical Decisions

## Overview

This document captures technical research and decisions for implementing a database-backed project status and work item tracking system as MCP tools. The system replaces manual .project_status.md with queryable PostgreSQL storage supporting multiple AI clients, with performance targets of <1ms vendor queries, <10ms work item hierarchies, and <100ms full status generation.

## Research Areas

### 1. Optimistic Locking Patterns in SQLAlchemy

**Decision**: Use SQLAlchemy 2.0 ORM-level optimistic locking with `version_id_col` mapper argument

**Rationale**:
- SQLAlchemy's built-in versioning prevents boilerplate version checking code
- Automatic `StaleDataError` exception on version mismatch provides clear failure signal
- Column automatically incremented on UPDATE, preventing manual management bugs
- Integrates seamlessly with async SQLAlchemy sessions

**Implementation Approach**:
```python
from sqlalchemy.orm import Mapped, mapped_column

class WorkItem(Base):
    __tablename__ = "work_items"
    __mapper_args__ = {"version_id_col": "version"}

    version: Mapped[int] = mapped_column(default=1, nullable=False)
```

**Alternatives Considered**:
1. **Application-level timestamp comparison**: Requires manual `WHERE updated_at = :expected_timestamp` in UPDATE queries; error-prone, no automatic failure signal
2. **Database triggers**: PostgreSQL trigger on UPDATE to check version; adds database-specific logic, harder to test, breaks ORM abstraction
3. **SELECT FOR UPDATE with explicit locking**: Pessimistic locking reduces concurrency; contradicts spec requirement for optimistic approach

**References**:
- SQLAlchemy 2.0 docs: [Configuring a Version Counter](https://docs.sqlalchemy.org/en/20/orm/versioning.html)
- MCP best practices: Optimistic concurrency for multi-client scenarios

---

### 2. SQLite Cache for Offline Fallback

**Decision**: Use `aiosqlite` with async context managers and schema mirroring strategy

**Rationale**:
- `aiosqlite` provides async/await interface matching AsyncPG patterns
- Schema mirroring (same table definitions as PostgreSQL) enables transparent fallback queries
- In-process database requires no external dependencies (constitutional compliance: local-first)
- File-based persistence survives process restarts (vs in-memory cache)

**Implementation Approach**:
```python
import aiosqlite
from contextlib import asynccontextmanager

@asynccontextmanager
async def get_sqlite_session():
    async with aiosqlite.connect("cache/project_status.db") as conn:
        conn.row_factory = aiosqlite.Row
        yield conn

# Mirror PostgreSQL schema in SQLite
CREATE_TABLES_SQL = """
    CREATE TABLE IF NOT EXISTS work_items (
        id TEXT PRIMARY KEY,
        version INTEGER NOT NULL,
        -- ... same columns as PostgreSQL
    );
"""
```

**Schema Synchronization Strategy**:
- Use Alembic migration to generate matching CREATE TABLE statements for SQLite
- On PostgreSQL unavailable: writes go to both SQLite + markdown (parallel, per clarification #2)
- On PostgreSQL reconnect: sync SQLite changes using `INSERT ... ON CONFLICT DO UPDATE`

**Alternatives Considered**:
1. **In-memory dict cache**: Lost on process restart; no persistence for offline scenarios; requires manual TTL management
2. **Redis**: External dependency violates constitutional local-first principle; unnecessary complexity for single-process MCP server
3. **DuckDB**: More features than needed (OLAP focus); larger dependency; aiosqlite sufficient for key-value + simple queries

**References**:
- aiosqlite docs: https://aiosqlite.omnilib.dev/
- SQLite async patterns: Context managers for transaction safety

---

### 3. JSONB Pydantic Validation Integration

**Decision**: Store serialized Pydantic models in JSONB, validate on read/write boundaries

**Rationale**:
- Pydantic provides runtime validation matching MCP tool input schemas
- SQLAlchemy JSON column type with custom `TypeDecorator` enables automatic serialization
- Type-specific metadata schemas (ProjectMetadata, SessionMetadata, TaskMetadata, etc.) enforce structure
- Validation errors caught at MCP tool boundary with field-level error messages

**Implementation Approach**:
```python
from sqlalchemy import JSON, TypeDecorator
from pydantic import BaseModel, ValidationError
import json

class PydanticJSON(TypeDecorator):
    impl = JSON
    cache_ok = True

    def __init__(self, pydantic_model: type[BaseModel]):
        self.pydantic_model = pydantic_model
        super().__init__()

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        # Validate with Pydantic, store as JSON
        validated = self.pydantic_model.model_validate(value)
        return validated.model_dump(mode='json')

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        # Deserialize and validate on read
        return self.pydantic_model.model_validate(value)

class VendorExtractor(Base):
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        PydanticJSON(VendorMetadata),
        nullable=False
    )
```

**Error Handling**:
- `ValidationError` raised on invalid JSONB → return 400 error to MCP client with field details
- Store schema version in JSONB for forward compatibility (`{"_schema_version": "1.0", ...}`)

**Alternatives Considered**:
1. **Separate validation layer**: Manual `validate()` calls before database writes; error-prone, easy to forget
2. **JSON Schema validation**: Less expressive than Pydantic; no Python type hints; manual schema maintenance
3. **PostgreSQL CHECK constraints**: Database-level validation, but error messages unclear; can't reuse for MCP tool input validation

**References**:
- Pydantic docs: [Custom Types](https://docs.pydantic.dev/latest/usage/types/custom/)
- SQLAlchemy custom types: [TypeDecorator](https://docs.sqlalchemy.org/en/20/core/custom_types.html)

---

### 4. Automatic Archiving Strategy

**Decision**: Background task (FastMCP context) with configurable threshold (default 1 year), moving rows to separate `archived_work_items` table

**Rationale**:
- Separate archive table keeps active table small for <10ms query performance
- Archive table has identical schema (no data loss), allows separate indexing strategy
- Background task prevents blocking MCP tool operations
- Configurable threshold supports different archiving policies without code changes

**Implementation Approach**:
```python
from datetime import datetime, timedelta
from sqlalchemy import select, insert, delete

async def archive_old_work_items(threshold_days: int = 365):
    """Move work items older than threshold to archive table"""
    cutoff_date = datetime.utcnow() - timedelta(days=threshold_days)

    # Select candidates
    stmt = select(WorkItem).where(
        WorkItem.created_at < cutoff_date,
        WorkItem.deleted_at.is_(None)  # Don't archive already deleted
    )
    old_items = await session.execute(stmt)

    # Copy to archive, delete from active
    for item in old_items.scalars():
        await session.execute(
            insert(ArchivedWorkItem).values(**item.__dict__)
        )
        await session.delete(item)

    await session.commit()

# FastMCP background task registration
@mcp.background_task(interval_seconds=86400)  # Daily
async def daily_archiving():
    await archive_old_work_items(threshold_days=365)
```

**Migration Strategy**:
- Alembic migration creates `archived_work_items` with identical schema to `work_items`
- Add indexes optimized for archive queries (year-based, read-only access patterns)
- Archive queries use separate MCP tool: `query_archived_work_items`

**Alternatives Considered**:
1. **Soft-delete flag only**: Active table grows unbounded; query performance degrades over 5 years; violates <10ms requirement
2. **Manual archiving**: Requires operator intervention; doesn't scale for AI assistant workflows
3. **Time-based partitioning**: PostgreSQL native partitioning by year; complex to query across partitions; harder to test locally

**References**:
- PostgreSQL performance: Table size impact on index scans
- FastMCP background tasks: https://github.com/jlowin/fastmcp#background-tasks

---

### 5. Hierarchical Query Performance

**Decision**: Recursive CTEs (Common Table Expressions) with materialized path caching

**Rationale**:
- PostgreSQL recursive CTEs are optimized for tree traversal
- Materialized path (`path` column storing "/parent1/parent2/current"`) enables single-query ancestor retrieval
- Combination provides fast queries: CTE for children, materialized path for ancestors
- Meets <10ms requirement for 5-level depth queries

**Implementation Approach**:
```python
# Database schema
class WorkItem(Base):
    parent_id: Mapped[UUID | None] = mapped_column(ForeignKey("work_items.id"))
    path: Mapped[str] = mapped_column(String, index=True)  # Materialized path
    depth: Mapped[int] = mapped_column(default=0)

# Recursive CTE for descendants
GET_DESCENDANTS_CTE = """
    WITH RECURSIVE descendants AS (
        SELECT id, parent_id, path, depth, 0 as level
        FROM work_items
        WHERE id = :root_id

        UNION ALL

        SELECT w.id, w.parent_id, w.path, w.depth, d.level + 1
        FROM work_items w
        INNER JOIN descendants d ON w.parent_id = d.id
        WHERE d.level < 5  -- Max 5 levels
    )
    SELECT * FROM descendants ORDER BY level, path;
"""

# Ancestors via materialized path
async def get_ancestors(work_item_id: UUID) -> list[WorkItem]:
    item = await session.get(WorkItem, work_item_id)
    ancestor_ids = item.path.split('/')[:-1]  # "/p1/p2/current" -> ["p1", "p2"]
    return await session.execute(
        select(WorkItem).where(WorkItem.id.in_(ancestor_ids))
    )

# Update path on parent change
async def update_materialized_path(work_item: WorkItem):
    if work_item.parent_id:
        parent = await session.get(WorkItem, work_item.parent_id)
        work_item.path = f"{parent.path}/{work_item.id}"
        work_item.depth = parent.depth + 1
    else:
        work_item.path = f"/{work_item.id}"
        work_item.depth = 0
```

**Performance Optimization**:
- Index on `path` column for ancestor queries
- Index on `parent_id` for recursive CTE
- Limit recursion depth to 5 (per spec requirement)
- Cache full hierarchy in MCP tool response (reduce round trips)

**Alternatives Considered**:
1. **Adjacency list with application-level recursion**: N+1 query problem; multiple round trips to database; slower than CTE
2. **Nested sets (left/right values)**: Fast reads, but complex updates; parent changes require recomputing entire tree
3. **Closure table**: Separate junction table for all ancestor/descendant pairs; fast queries but expensive writes (O(depth²) inserts per node)

**References**:
- PostgreSQL CTE docs: [WITH Queries](https://www.postgresql.org/docs/current/queries-with.html)
- Materialized path pattern: https://en.wikipedia.org/wiki/Materialized_path

---

### 6. YAML Frontmatter Parsing

**Decision**: Use `python-frontmatter` library with schema versioning and graceful error handling

**Rationale**:
- `python-frontmatter` is battle-tested library for parsing YAML frontmatter
- Schema versioning (`schema_version: "1.0"` in frontmatter) enables forward compatibility
- Graceful error handling: malformed YAML skips entry with warning, doesn't fail entire migration

**Implementation Approach**:
```python
import frontmatter
from pathlib import Path

async def parse_session_prompt(prompt_file: Path) -> SessionMetadata | None:
    try:
        post = frontmatter.load(prompt_file)

        # Validate schema version
        schema_version = post.metadata.get('schema_version', '1.0')
        if schema_version not in SUPPORTED_VERSIONS:
            logger.warning(f"Unsupported schema {schema_version} in {prompt_file}")
            return None

        # Extract metadata
        return SessionMetadata(
            token_budget=post.metadata['token_budget'],
            prompts_count=post.metadata['prompts_count'],
            yaml_frontmatter=post.metadata
        )
    except (yaml.YAMLError, KeyError, ValidationError) as e:
        logger.error(f"Malformed YAML in {prompt_file}: {e}")
        return None  # Skip invalid entries, per clarification
```

**Error Scenarios** (from spec edge case):
- Missing required fields → log error, skip entry, continue parsing
- Invalid YAML syntax → log error with line number, skip entry
- Unknown schema version → log warning, attempt best-effort parse or skip

**Migration Strategy**:
- Parse all session prompts from git history
- Validate against Pydantic `SessionMetadata` schema
- Store in `work_items` table with `item_type='session'`

**Alternatives Considered**:
1. **Custom regex parsing**: Fragile; doesn't handle nested YAML structures; error-prone
2. **TOML frontmatter**: Requires migrating existing YAML files; incompatible with existing .project_status.md format
3. **JSON frontmatter**: Less human-readable; YAML is established convention for markdown frontmatter

**References**:
- python-frontmatter: https://pypi.org/project/python-frontmatter/
- YAML 1.2 spec: https://yaml.org/spec/1.2/spec.html

---

### 7. Markdown Status Report Generation

**Decision**: Template-based generation with Jinja2, matching legacy .project_status.md format

**Rationale**:
- Jinja2 provides powerful templating with filters, conditionals, loops
- Template inheritance enables consistent structure across report sections
- Legacy format compatibility ensures backward compatibility (constitutional requirement)
- Separation of data (database queries) and presentation (templates)

**Implementation Approach**:
```python
from jinja2 import Environment, FileSystemLoader

# Template: templates/project_status.md.j2
"""
# Project Status - {{ timestamp }}

## Operational Vendors ({{ vendors|selectattr('status', 'equalto', 'operational')|list|length }}/{{ vendors|length }})

{% for vendor in vendors|sort(attribute='name') %}
- **{{ vendor.name }}**: {{ vendor.status }}
  ({{ vendor.metadata.test_results.passing }}/{{ vendor.metadata.test_results.total }} tests)
  [{{ vendor.metadata.format_support|select|list|join(', ') }}]
{% endfor %}

## Active Work Items

{% for item in work_items|rejectattr('deleted_at') %}
### {{ item.title }} ({{ item.item_type }})
- **Status**: {{ item.status }}
- **Created**: {{ item.created_at|datetimeformat }}
{% if item.parent %}
- **Parent**: {{ item.parent.title }}
{% endif %}
{% endfor %}

## Recent Deployments

{% for deployment in deployments|sort(attribute='deployed_at', reverse=True)|list[:5] %}
- **{{ deployment.deployed_at|datetimeformat }}**: PR #{{ deployment.metadata.pr_number }} - {{ deployment.metadata.pr_title }}
  - Vendors: {{ deployment.vendors|map(attribute='name')|join(', ') }}
  - Tests: {{ deployment.metadata.test_summary|dictsort }}
  - Constitutional Compliance: {{ '✅' if deployment.metadata.constitutional_compliance else '❌' }}
{% endfor %}
"""

async def generate_project_status_md() -> str:
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('project_status.md.j2')

    # Query database
    vendors = await get_all_vendors()
    work_items = await get_active_work_items()
    deployments = await get_recent_deployments(limit=10)

    # Render template
    return template.render(
        timestamp=datetime.utcnow().isoformat(),
        vendors=vendors,
        work_items=work_items,
        deployments=deployments
    )
```

**Performance Target**: <100ms for full status generation (spec requirement FR-023)
- Pre-load all data in parallel queries
- Use database indexes for filtering (operational vendors, active items)
- Cache template compilation

**Alternatives Considered**:
1. **String formatting (f-strings)**: Fragile for complex structures; mixing logic with presentation; hard to maintain
2. **Custom template engine**: Reinventing the wheel; Jinja2 is production-ready
3. **Direct markdown assembly**: No reusability; hard to test formatting separately from data

**References**:
- Jinja2 docs: https://jinja.palletsprojects.com/
- Markdown best practices: Consistent heading levels, bullet formatting

---

## Summary

All technical decisions documented with rationale, implementation approach, and alternatives considered. Key technologies:

1. **SQLAlchemy 2.0 optimistic locking** for concurrent updates
2. **aiosqlite** for offline fallback cache
3. **Pydantic TypeDecorator** for JSONB validation
4. **Separate archive table** with background task (1-year threshold)
5. **Recursive CTEs + materialized paths** for hierarchical queries
6. **python-frontmatter** for YAML parsing with error handling
7. **Jinja2 templates** for markdown generation

All decisions align with constitutional principles:
- Local-first (no external services)
- Performance guarantees (<1ms, <10ms, <100ms)
- Production quality (error handling, validation)
- Type safety (Pydantic throughout)

**Next Phase**: Generate data-model.md, contracts/, quickstart.md, and update CLAUDE.md
