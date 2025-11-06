# Codebase MCP Server - Deployment Quick Reference

## One-Page Summary

### What is Codebase MCP Server?
- Production-grade MCP (Model Context Protocol) server for semantic code search
- Indexes code repositories into PostgreSQL with pgvector embeddings
- Designed for Claude Desktop integration via Stdio transport
- Provides 3 core tools: `start_indexing_background`, `get_indexing_status`, `search_code`

### Current Architecture
```
Claude Desktop → codebase-mcp (Python FastMCP) → PostgreSQL + Ollama
```

### Key Facts

| Aspect | Detail |
|--------|--------|
| **Entry Point** | `src/mcp/server_fastmcp.py::main()` |
| **Framework** | FastMCP (Stdio transport, no HTTP) |
| **Language** | Python 3.11+ |
| **Database** | PostgreSQL 14+ with pgvector extension |
| **Embedding Model** | Ollama (default: nomic-embed-text) |
| **Async Runtime** | asyncio + asyncpg |
| **Config** | Environment variables + .env file |
| **Logging** | File-based to `/tmp/codebase-mcp.log` |
| **Package Entry** | `codebase-mcp` (console script) |

### Deployment Status

**Development**: 
- Devcontainer (VS Code) ✓
- Local PostgreSQL + Ollama ✓
- Editable install (`pip install -e .`) ✓

**Production**:
- ✗ No production Dockerfile
- ✗ No production Docker Compose
- ✗ No containerized database setup
- ✗ No container health checks

---

## Critical Dependencies

### Python Packages (from requirements.txt)

**Database**:
- SQLAlchemy[asyncpg] >=2.0.25
- asyncpg >=0.30.0
- alembic >=1.13.0
- pgvector >=0.2.4

**MCP Protocol**:
- fastmcp >=0.1.0
- mcp >=0.9.0

**Code Processing**:
- tree-sitter >=0.21.0
- tree-sitter-python >=0.21.0
- tree-sitter-javascript >=0.21.0

**Configuration**:
- pydantic >=2.5.0
- pydantic-settings >=2.1.0
- python-dotenv >=1.0.0

**Other**:
- fastapi >=0.109.0
- httpx >=0.26.0
- jinja2 >=3.1.0

### External Services

| Service | Port | Purpose |
|---------|------|---------|
| PostgreSQL | 5432 | Code repository & registry databases |
| Ollama | 11434 | Text embedding generation |

---

## Environment Variables

### Required
```bash
REGISTRY_DATABASE_URL=postgresql+asyncpg://user:pass@localhost/registry
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

### Optional
```bash
DATABASE_URL=postgresql+asyncpg://...              # Legacy, optional
EMBEDDING_BATCH_SIZE=50                            # Tuning
MAX_CONCURRENT_REQUESTS=10                         # Tuning
POOL_MIN_SIZE=2                                    # Advanced
POOL_MAX_SIZE=10                                   # Advanced
LOG_LEVEL=INFO
LOG_FILE=/tmp/codebase-mcp.log
MAX_CONCURRENT_INDEXING_JOBS=2
INDEXING_JOB_TIMEOUT_SECONDS=3600
```

---

## Key Components

### Server (MCP Interface)
- **File**: `src/mcp/server_fastmcp.py`
- **Pattern**: FastMCP with async lifespan
- **Tools**: Registered via @mcp.tool() decorators
- **Resources**: Health/metrics endpoints
- **Transport**: Stdio (process-local, not HTTP)

### Database Layer
- **Session Management**: `src/database/session.py`
- **Connection Pooling**: `src/connection_pool/manager.py`
- **Registry**: `src/database/registry.py` (tracks projects)
- **Auto-Create**: `src/database/auto_create.py` (per-project databases)
- **Migrations**: Alembic (`alembic/versions/`)

### Core Services
- **Indexer**: `src/services/indexer.py` (orchestration)
- **Searcher**: `src/services/searcher.py` (semantic search)
- **Embedder**: `src/services/embedder.py` (Ollama integration)
- **Chunker**: `src/services/chunker.py` (code chunking)
- **Scanner**: `src/services/scanner.py` (file discovery)
- **Background Worker**: `src/services/background_worker.py` (job processing)

### Configuration
- **Settings**: `src/config/settings.py` (Pydantic-based, fail-fast validation)
- **Pool Config**: `src/connection_pool/config.py`

---

## Database Schema

### Database-Per-Project Architecture
- **Registry Database**: `codebase_mcp_registry` (tracks projects)
- **Project Databases**: `cb_proj_*` (isolated per project)

### Core Tables (per project DB)
```
repositories       # Git repos being indexed
code_files        # Source files
code_chunks       # Semantic chunks (with embeddings)
indexing_jobs     # Background job tracking
```

### Migrations
```bash
# List migrations
ls alembic/versions/

# Current: 7 migrations
# - Database refactoring
# - Project registry schema
# - Force reindex support

# Run migrations
DATABASE_URL=postgresql+asyncpg://... alembic upgrade head
```

---

## Running the Server

### Manual (Development)
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create .env file
cp .env.example .env
# Edit with your PostgreSQL and Ollama URLs

# 3. Run migrations
DATABASE_URL=postgresql+asyncpg://... alembic upgrade head

# 4. Start server (outputs MCP protocol to stdout)
codebase-mcp
```

### In Claude Desktop
```json
{
  "mcpServers": {
    "codebase-mcp": {
      "command": "python",
      "args": ["-m", "src.mcp.server_fastmcp"],
      "env": {
        "REGISTRY_DATABASE_URL": "postgresql+asyncpg://...",
        "OLLAMA_BASE_URL": "http://localhost:11434"
      }
    }
  }
}
```

---

## What Needs Containerization

### Phase 1: Application Container
- **Base**: `python:3.11-slim`
- **Install**: Requirements + application code
- **Entry**: `codebase-mcp` command
- **User**: Non-root (for security)
- **Volumes**: Logs, config, database data

### Phase 2: Docker Compose
- **postgres service**: PostgreSQL 14+ with pgvector
- **ollama service**: Ollama with embedding model
- **codebase-mcp service**: Application container
- **Networking**: Internal (no exposed ports)
- **Volumes**: Persistent data directories
- **Health checks**: Each service

### Phase 3: Production Hardening
- Multi-stage builds
- Image scanning
- Resource limits
- Graceful shutdown handlers
- Structured logging

---

## Important Constraints

### Stdio Transport (Not HTTP)
- **Key Point**: This is NOT an HTTP service
- **Output**: MCP protocol messages only (binary/JSON)
- **No ports exposed**: Stdio is process-local
- **Health checks**: Must be internal, not HTTP probes
- **Use case**: Claude Desktop subprocess, not web service

### Multi-Container Requirements
- PostgreSQL must be reachable from app container
- Ollama must be reachable from app container
- Internal Docker network sufficient (no external exposure)

---

## Configuration Validation

The application performs **fail-fast validation** on startup:

```bash
# Invalid DATABASE_URL scheme → Server won't start
# Missing REGISTRY_DATABASE_URL → Server won't start
# Invalid POOL_* values → Server won't start
# Unreachable PostgreSQL → Server won't start
# Unreachable Ollama → First indexing fails (caught gracefully)
```

All validation errors include actionable error messages.

---

## Performance Targets (Constitutional)

- **Indexing**: <60s p95 for 10,000 files
- **Search**: <500ms p95 latency
- **Health Check**: <50ms
- **Connection Pool**: min=2, max=10 (configurable)
- **Background Jobs**: Configurable max concurrent (default=2)

---

## Key Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Project metadata, dependencies, tool configs |
| `requirements.txt` | Production dependencies (generated from pyproject.toml) |
| `.env.example` | Environment variable template |
| `alembic.ini` | Alembic migration configuration |
| `Makefile` | Common development tasks |
| `.devcontainer/` | VS Code devcontainer setup (development only) |
| `src/mcp/server_fastmcp.py` | Main server entry point |
| `src/config/settings.py` | Configuration management |
| `migrations/versions/` | Database migration scripts |

---

## Common Tasks

### Run Tests
```bash
pytest                    # All tests
pytest -m unit           # Unit tests only
pytest -m integration    # Integration tests only
```

### Type Check
```bash
mypy src                  # Full type checking (strict mode)
```

### Lint & Format
```bash
ruff check src            # Lint
ruff format src           # Auto-format
```

### Database Operations
```bash
alembic current           # Show current migration
alembic history           # Show all migrations
alembic upgrade head      # Apply pending migrations
alembic downgrade -1      # Rollback one migration
```

---

## For Full Details

See `/workspace/DEPLOYMENT_ARCHITECTURE_ANALYSIS.md` (612 lines) for:
- Complete architecture documentation
- Detailed dependency analysis
- Database design explanation
- Development vs production differences
- Recommended containerization approach
- Implementation patterns and constraints

---

## Contact Points for Containerization

1. **Entry Point**: `src/mcp/server_fastmcp.py::main()`
2. **Settings**: `src/config/settings.py` (reads .env)
3. **Database**: `src/database/` (async session management)
4. **Connection Pool**: `src/connection_pool/manager.py` (lifespan)
5. **Health Service**: `src/services/health_service.py` (readiness probes)
6. **Metrics**: `src/services/metrics_service.py` (observability)
7. **Logging**: File handler in `src/mcp/server_fastmcp.py`

All are production-ready for containerization.
