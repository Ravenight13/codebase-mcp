# MCP Split Architecture Overview

## Executive Summary

The monolithic `codebase-mcp` is being split into two focused Model Context Protocol (MCP) servers:

1. **codebase-mcp**: Semantic code search with pgvector embeddings
2. **workflow-mcp**: AI project management with generic JSONB entities

Both MCPs share a single PostgreSQL instance but implement database-per-project isolation for multi-project workspace support.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Claude Code CLI                         │
│                    (MCP Client/Host)                         │
└────────────┬────────────────────────────┬───────────────────┘
             │                            │
             │ SSE/stdio                  │ SSE/stdio
             │ Port 8001                  │ Port 8002
             │                            │
    ┌────────▼────────┐         ┌────────▼────────┐
    │  codebase-mcp   │         │  workflow-mcp   │
    │   (FastMCP)     │         │   (FastMCP)     │
    │                 │         │                 │
    │ - index_repo    │         │ - create_entity │
    │ - search_code   │         │ - update_entity │
    │ - get_chunks    │         │ - query_entity  │
    └────────┬────────┘         └────────┬────────┘
             │                            │
             │ asyncpg                    │ asyncpg
             │                            │
    ┌────────▼────────────────────────────▼────────┐
    │          PostgreSQL 14+ Instance             │
    │                                               │
    │  ┌─────────────────────────────────────┐    │
    │  │     mcp_registry (database)         │    │
    │  │  ┌─────────────────────────────┐   │    │
    │  │  │  projects (table)           │   │    │
    │  │  │  - id (uuid, pk)            │   │    │
    │  │  │  - name (text, unique)      │   │    │
    │  │  │  - database_name (text)     │   │    │
    │  │  │  - created_at (timestamptz) │   │    │
    │  │  └─────────────────────────────┘   │    │
    │  └─────────────────────────────────────┘    │
    │                                               │
    │  ┌─────────────────────────────────────┐    │
    │  │  project_abc (database)             │    │
    │  │  ┌──────────────────────────────┐   │    │
    │  │  │  codebase schema             │   │    │
    │  │  │  - repositories              │   │    │
    │  │  │  - code_chunks               │   │    │
    │  │  │  - embeddings (vector)       │   │    │
    │  │  └──────────────────────────────┘   │    │
    │  │  ┌──────────────────────────────┐   │    │
    │  │  │  workflow schema             │   │    │
    │  │  │  - entity_schemas            │   │    │
    │  │  │  - entities (JSONB)          │   │    │
    │  │  └──────────────────────────────┘   │    │
    │  └─────────────────────────────────────┘    │
    │                                               │
    │  ┌─────────────────────────────────────┐    │
    │  │  project_xyz (database)             │    │
    │  │  ... (same schema structure)        │    │
    │  └─────────────────────────────────────┘    │
    └───────────────────────────────────────────────┘
```

## How Both MCPs Work Together

### Independent Tool Namespaces

Each MCP exposes tools to Claude Code via the MCP protocol:

**codebase-mcp tools:**
- `index_repository(repo_path, project_name)` - Index code into project DB
- `search_code(query, project_name, filters)` - Semantic search
- `get_code_chunks(chunk_ids, project_name)` - Retrieve code context

**workflow-mcp tools:**
- `create_entity(project_name, schema_name, data)` - Create work item
- `update_entity(project_name, entity_id, data)` - Update work item
- `query_entities(project_name, schema_name, filters)` - Query work items
- `record_deployment(project_name, data)` - Log deployments

Claude Code aggregates tools from both MCPs in a single namespace, allowing the AI to use both simultaneously:

```python
# Example Claude Code usage (conceptual)
await codebase_mcp.search_code(
    query="authentication logic",
    project_name="my_project"
)

await workflow_mcp.create_entity(
    project_name="my_project",
    schema_name="task",
    data={"title": "Fix auth bug", "status": "in_progress"}
)
```

### Database-Per-Project Pattern

Each project gets its own PostgreSQL database with both schemas:

1. **Registry Database** (`mcp_registry`)
   - Single source of truth for all projects
   - Stores project metadata and database mappings
   - Used by both MCPs to discover project databases

2. **Project Databases** (`project_<name>`)
   - One database per project (e.g., `project_myapp`, `project_website`)
   - Contains both `codebase` and `workflow` schemas
   - Complete data isolation between projects
   - No cross-project queries possible

### Connection Flow Between MCPs

Both MCPs use the shared `ProjectConnectionManager` pattern:

```python
# In both codebase-mcp and workflow-mcp
from shared.connection_manager import ProjectConnectionManager

# Initialization (at MCP server startup)
conn_mgr = ProjectConnectionManager(
    registry_dsn="postgresql://user:pass@localhost/mcp_registry"
)
await conn_mgr.initialize()

# Tool execution (lazy project pool creation)
@mcp.tool()
async def search_code(query: str, project_name: str):
    # Get project-specific pool (creates if first time)
    async with conn_mgr.get_project_connection(project_name) as conn:
        # Execute query on project database
        results = await conn.fetch("""
            SELECT content, similarity
            FROM codebase.code_chunks
            WHERE embedding <-> $1 < 0.5
        """, query_embedding)
    return results
```

**Key Flow:**
1. Claude Code invokes tool on either MCP
2. MCP looks up project in registry (via `conn_mgr.registry_pool`)
3. MCP gets/creates connection pool for project database
4. Query executes on project-specific database
5. Results returned to Claude Code

### Project Isolation Guarantees

**Database-Level Isolation:**
- Each project has a separate PostgreSQL database
- No shared tables between projects
- Database permissions enforce boundaries
- Connection pools are project-scoped

**Schema-Level Organization:**
- `codebase` schema: repositories, code_chunks, embeddings
- `workflow` schema: entity_schemas, entities
- Schemas prevent naming conflicts within project DB

**Query-Level Safety:**
- All tools require `project_name` parameter
- No cross-database queries supported
- Connection manager validates project existence
- Invalid project names raise ValueError

**Performance Isolation:**
- Each project has independent connection pool
- Heavy indexing on project A doesn't block project B
- Per-project query performance metrics
- No resource contention between projects

## Deployment Architecture

### Single PostgreSQL Instance

Both MCPs connect to the same PostgreSQL instance:

```bash
# Environment variables for both MCPs
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_USER=mcp_user
export POSTGRES_PASSWORD=secure_password
export POSTGRES_DB=mcp_registry  # Registry database
```

### Dual MCP Servers

```bash
# Terminal 1: Start codebase-mcp
cd codebase-mcp
python -m codebase_mcp.server --port 8001

# Terminal 2: Start workflow-mcp
cd workflow-mcp
python -m workflow_mcp.server --port 8002
```

### Claude Code Configuration

```json
{
  "mcpServers": {
    "codebase-mcp": {
      "url": "http://localhost:8001",
      "transport": "sse"
    },
    "workflow-mcp": {
      "url": "http://localhost:8002",
      "transport": "sse"
    }
  }
}
```

## Performance Characteristics

### Target: < 20 Projects

The architecture is optimized for small-to-medium AI coding workspaces:

- **Registry queries**: < 1ms (indexed by project name)
- **Connection pool creation**: < 50ms (lazy, cached)
- **Per-project operations**: Same as single-project performance
- **Memory overhead**: 2-10 connections × 20 projects = 40-200 connections total
- **PostgreSQL max_connections**: 200 (default) sufficient

### Scaling Considerations

**Up to 20 projects:**
- No performance degradation
- Linear memory scaling
- Excellent query isolation

**20-100 projects:**
- May need connection pool tuning
- Consider connection pooler (PgBouncer)
- Monitor PostgreSQL connection limits

**100+ projects:**
- Requires architectural changes
- Consider schema-per-project instead of database-per-project
- Implement connection pool eviction/LRU cache

## Migration Path

### Phase 1: Split MCPs (Current)
- Extract workflow tools to separate MCP
- Keep shared PostgreSQL connection
- Both MCPs read from same project databases

### Phase 2: Database-Per-Project (Future)
- Registry database with project catalog
- Dynamic database creation
- Connection manager with lazy pooling

### Phase 3: Production Hardening (Future)
- Connection pool monitoring
- Automatic pool cleanup for inactive projects
- Health checks and reconnection logic

## Error Handling Strategy

### Project Not Found
```python
# Raises ValueError from ProjectConnectionManager
await conn_mgr.get_project_connection("nonexistent_project")
# → ValueError: Project 'nonexistent_project' not found in registry
```

### Database Connection Failure
```python
# Logs error, raises ConnectionError
await conn_mgr.initialize()
# → ConnectionError: Failed to connect to registry database
```

### Schema Missing
```python
# Raises RuntimeError if schema not initialized
async with conn_mgr.get_project_connection(project_name) as conn:
    await conn.fetch("SELECT * FROM codebase.repositories")
# → RuntimeError: Schema 'codebase' not found in project database
```

## Security Considerations

### Database Credentials
- Both MCPs use same PostgreSQL credentials
- Credentials stored in environment variables
- No credentials in code or version control
- Consider using PostgreSQL roles for MCP-specific permissions

### Project Isolation
- Database-level isolation prevents cross-project data leaks
- No SQL injection risk (all queries use parameterized statements)
- Project names validated (alphanumeric + underscores only)

### Network Security
- MCPs listen on localhost by default
- Use TLS for remote Claude Code connections
- Consider firewall rules for PostgreSQL port

## Observability

### Logging Strategy
- Both MCPs log to stdout (FastMCP default)
- Connection manager logs pool creation/destruction
- Query performance logged at DEBUG level
- Error stack traces logged at ERROR level

### Metrics
- Connection pool size per project
- Query latency (p50, p95, p99)
- Tool invocation counts
- Project database sizes

### Health Checks
- Registry database connectivity
- Project database connectivity
- Connection pool health
- Schema integrity validation

## Next Steps

See detailed documentation:
- [database-design.md](./database-design.md) - Complete schema definitions
- [connection-management.md](./connection-management.md) - ProjectConnectionManager implementation
- [entity-system.md](./entity-system.md) - Generic JSONB entity design
- [deployment-config.md](./deployment-config.md) - Running both MCPs
