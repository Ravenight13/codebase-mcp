# Database-Per-Project Architecture

## Overview

Codebase MCP now uses a **database-per-project architecture** for complete multi-project isolation. This replaces the previous schema-based approach with true database-level separation.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     MCP Client (Claude)                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ MCP Protocol
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  Codebase MCP Server                         │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │     FastMCP Context (session_id)                     │  │
│  └──────────────────┬───────────────────────────────────┘  │
│                     │                                        │
│                     ▼                                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Session Context Manager                             │  │
│  │  - .codebase-mcp/config.json discovery               │  │
│  │  - Config caching with mtime invalidation            │  │
│  │  - Per-session working directory tracking            │  │
│  └──────────────────┬───────────────────────────────────┘  │
│                     │                                        │
│                     ▼                                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Project Resolution (4-tier chain)                   │  │
│  │  1. Explicit project_id parameter                    │  │
│  │  2. Session config (.codebase-mcp/config.json)       │  │
│  │  3. workflow-mcp integration (optional)              │  │
│  │  4. Default project fallback                         │  │
│  └──────────────────┬───────────────────────────────────┘  │
│                     │                                        │
│                     ▼                                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  ProjectRegistry Service                             │  │
│  │  - Lookup project by ID or name                      │  │
│  │  - Returns (project_id, database_name)               │  │
│  └──────────────────┬───────────────────────────────────┘  │
│                     │                                        │
│                     ▼                                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Connection Pool Manager                             │  │
│  │  - Per-project AsyncPG pools                         │  │
│  │  - Lazy initialization + caching                     │  │
│  └──────────────────┬───────────────────────────────────┘  │
└────────────────────┬┴───────────────────────────────────────┘
                     │
          ┌──────────┴────────────┬─────────────┐
          │                       │             │
          ▼                       ▼             ▼
┌───────────────────┐  ┌────────────────────┐  ┌──────────────────┐
│  Registry DB      │  │  Project DB 1      │  │  Project DB 2    │
│  ─────────────    │  │  ─────────────     │  │  ─────────────   │
│  codebase_mcp_    │  │  cb_proj_          │  │  cb_proj_        │
│  registry         │  │  my_project_abc    │  │  other_proj_def  │
│                   │  │                    │  │                  │
│  projects table:  │  │  repositories      │  │  repositories    │
│  - id             │  │  code_files        │  │  code_files      │
│  - name           │  │  code_chunks       │  │  code_chunks     │
│  - database_name  │  │  (pgvector)        │  │  (pgvector)      │
│  - metadata       │  │                    │  │                  │
└───────────────────┘  └────────────────────┘  └──────────────────┘
```

## Key Components

### 1. Registry Database

**Database**: `codebase_mcp_registry`

**Tables**:
- `projects`: Tracks all project workspaces

**Schema**:
```sql
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    database_name VARCHAR(255) UNIQUE NOT NULL,  -- cb_proj_{name}_{hash}
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);
```

### 2. Project Databases

**Naming Convention**: `cb_proj_{sanitized_name}_{uuid8}`

**Example**: `cb_proj_my_project_abc123de`

**Tables** (in each project database):
- `repositories`: Indexed code repositories
- `code_files`: Individual code files with metadata
- `code_chunks`: Semantic code chunks with embeddings (pgvector)

**Schema**: See `scripts/init_project_schema.sql`

### 3. Connection Pool Management

**Registry Pool**:
- Single AsyncPG pool for registry database
- Used for project lookups and metadata
- Min size: 2, Max size: 10 connections

**Project Pools**:
- Separate AsyncPG pool per project database
- Lazy initialization on first access
- Cached in module-level dict: `_project_pools`
- Min size: 2, Max size: 10 connections

### 4. Project Resolution

**4-Tier Resolution Chain**:

1. **Explicit ID** (highest priority):
   ```python
   await index_repository(repo_path="/path", project_id="my-project")
   ```

2. **Session Config** (recommended):
   ```python
   await set_working_directory("/path/to/project")  # Discovers .codebase-mcp/config.json
   await index_repository(repo_path="/path")        # Auto-resolves project
   ```

3. **workflow-mcp Integration** (optional):
   - Queries external workflow-mcp server
   - Timeout protection (1s default)
   - Graceful fallback on failure

4. **Default Fallback**:
   - Returns `("default", "cb_proj_default_00000000")`
   - Used when all resolution methods fail

## Configuration

### Environment Variables

```bash
# Registry database (required)
REGISTRY_DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/codebase_mcp_registry

# Default database (optional, for backward compatibility)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/codebase_mcp

# Connection pool settings
POOL_MIN_SIZE=2
POOL_MAX_SIZE=10

# Ollama for embeddings
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text:latest
```

### Project Config File

**Location**: `.codebase-mcp/config.json` (in project root)

**Format**:
```json
{
  "version": "1.0",
  "project": {
    "name": "my-project",
    "id": "550e8400-e29b-41d4-a716-446655440000"
  },
  "auto_switch": true,
  "strict_mode": false,
  "description": "My project description"
}
```

**Discovery**:
- Searches up to 20 parent directories
- Cached with mtime-based invalidation (<1ms cache hits)
- Falls back to workflow-mcp or default if not found

## Setup Guide

### 1. Initialize Registry Database

```bash
# Create registry database
createdb codebase_mcp_registry

# Initialize schema
psql -d codebase_mcp_registry -f scripts/init_registry_schema.sql
```

### 2. Create Default Project

```bash
# Create default fallback database
createdb cb_proj_default_00000000

# Initialize schema
psql -d cb_proj_default_00000000 -f scripts/init_project_schema.sql

# Register in registry
psql -d codebase_mcp_registry -c "
INSERT INTO projects (id, name, description, database_name)
VALUES (
    '00000000-0000-0000-0000-000000000000',
    'default',
    'Default fallback project',
    'cb_proj_default_00000000'
);
"
```

### 3. Create Project for Your Codebase

**Option A: Automated Script**:
```bash
python scripts/setup_codebase_mcp_project.py
```

**Option B: Manual Setup**:
```python
from src.database.registry import ProjectRegistry
from src.database.provisioning import create_pool

# Initialize registry
registry_pool = await create_pool("codebase_mcp_registry")
registry = ProjectRegistry(registry_pool)

# Create project (provisions database automatically)
project = await registry.create_project(
    name="my-project",
    description="My project description",
    metadata={"owner": "alice@example.com"}
)

print(f"Created: {project.database_name}")
```

### 4. Configure Project

Create `.codebase-mcp/config.json` in your project root:
```bash
mkdir -p .codebase-mcp
cat > .codebase-mcp/config.json << EOF
{
  "version": "1.0",
  "project": {
    "name": "my-project"
  }
}
EOF
```

## Usage Examples

### Basic Workflow

```python
from src.mcp.tools.project import set_working_directory
from src.mcp.tools.indexing import index_repository
from src.mcp.tools.search import search_code

# 1. Set working directory (discovers config)
await set_working_directory("/Users/alice/my-project")

# 2. Index repository (uses project from config)
result = await index_repository(
    repo_path="/Users/alice/my-project"
)
# Indexes to: cb_proj_my_project_abc123de

# 3. Search code (uses same project)
results = await search_code(
    query="authentication logic"
)
# Searches in: cb_proj_my_project_abc123de
```

### Multi-Project Workflow

```python
# Project A
await set_working_directory("/Users/alice/project-a")
await index_repository(repo_path="/Users/alice/project-a")
# Uses: cb_proj_project_a_xxx

# Project B
await set_working_directory("/Users/alice/project-b")
await index_repository(repo_path="/Users/alice/project-b")
# Uses: cb_proj_project_b_yyy

# Data is completely isolated (different databases)
```

### Explicit Project Override

```python
# Override project resolution with explicit ID
await index_repository(
    repo_path="/path/to/repo",
    project_id="my-specific-project"
)
# Forces: cb_proj_my_specific_project_*
```

## Benefits vs. Schema-Based

### Complete Isolation
- **Database-per-project**: Separate physical databases, impossible to cross-contaminate
- **Schema-based**: Shared database, risk of schema leakage via SQL errors

### Independent Scaling
- **Database-per-project**: Scale each project database independently
- **Schema-based**: All projects share same database resources

### Backup Flexibility
- **Database-per-project**: Backup/restore individual projects
- **Schema-based**: Must backup entire shared database

### Security
- **Database-per-project**: Database-level access control per project
- **Schema-based**: Schema-level access control (less granular)

### Monitoring
- **Database-per-project**: Per-project database metrics (CPU, I/O, queries)
- **Schema-based**: Aggregated metrics only

## Migration from Schema-Based

**No migration needed!** The old `codebase_mcp` database is unused in the new architecture. Data is not migrated - you start fresh with new project databases.

**Why no migration?**:
1. Schema-based data had no project tracking (no way to map schemas to projects)
2. Fresh start ensures clean database-per-project boundaries
3. Semantic search benefits from re-indexing with latest embeddings

**If you want to keep old data**:
1. Archive `codebase_mcp` database: `pg_dump codebase_mcp > backup.sql`
2. Create new project databases
3. Re-index repositories (recommended for best embeddings)

## Performance Characteristics

| Operation | Target | Typical | Notes |
|-----------|--------|---------|-------|
| Config discovery (cached) | <1ms | 0.8ms | LRU cache with mtime validation |
| Config discovery (uncached) | <60ms | 38ms | 20-level directory traversal |
| Registry lookup | <10ms | 5ms | PostgreSQL btree index |
| Project pool creation | <100ms | 45ms | One-time per project |
| Session creation | <5ms | 2ms | From existing pool |

## Troubleshooting

### "Project not found in registry"

**Cause**: Config references a project that doesn't exist in registry

**Solution**:
```python
from src.database.auto_create import get_or_create_project_from_config

# Automatically creates project if missing
project = await get_or_create_project_from_config(config_path)
```

### "Database already exists"

**Cause**: Trying to create a project database that exists

**Solution**:
- Check if project already registered: `psql -d codebase_mcp_registry -c "SELECT * FROM projects WHERE name = 'my-project'"`
- Either use existing project or choose different name

### "Connection pool timeout"

**Cause**: Too many concurrent connections

**Solution**:
- Increase pool size: `POOL_MAX_SIZE=20`
- Check for connection leaks (unclosed sessions)
- Monitor with: `SELECT count(*) FROM pg_stat_activity WHERE datname LIKE 'cb_proj_%';`

## API Reference

See the following modules for detailed API documentation:

- `src/database/registry.py` - ProjectRegistry service
- `src/database/provisioning.py` - Database provisioning utilities
- `src/database/session.py` - Session management and project resolution
- `src/database/auto_create.py` - Auto-provisioning from config

## See Also

- [Registry Schema](../scripts/init_registry_schema.sql) - SQL schema definition
- [Project Schema](../scripts/init_project_schema.sql) - Project database tables
- [Setup Script](../scripts/setup_codebase_mcp_project.py) - Automated project creation
