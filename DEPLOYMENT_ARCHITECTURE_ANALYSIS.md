# Codebase MCP Server - Deployment Architecture Analysis

## Executive Summary

**Codebase MCP Server** is a production-grade MCP (Model Context Protocol) server for semantic code search with PostgreSQL pgvector. It currently runs as a CLI application with Stdio transport, designed for Claude Desktop integration.

### Current Deployment Status
- **No production containerization**: Exists only as a devcontainer for development
- **Entry Point**: `src/mcp/server_fastmcp.py::main()` (FastMCP server)
- **Transport**: Stdio (not HTTP) - designed for direct process communication
- **Dependencies**: PostgreSQL 14+, Ollama (embedding model)
- **Python**: 3.11+ required

---

## 1. Current Server Architecture

### 1.1 Entry Point & Startup

**Main Entry Point**: `/workspace/src/mcp/server_fastmcp.py`

```python
# Project script entry point (pyproject.toml)
[project.scripts]
codebase-mcp = "src.mcp.server_fastmcp:main"
```

**Startup Sequence**:
1. Import tool modules (`search`, `project`, `background_indexing`)
2. Import resource modules (`health`, `metrics_endpoint`)
3. Initialize FastMCP server with lifespan context manager
4. Start connection pool and session manager
5. Begin serving with Stdio transport

**Lifespan Pattern** (FastMCP async context manager):
- **Startup**: Initialize session manager → initialize connection pool → services ready
- **Shutdown**: Close pool gracefully → stop session manager

### 1.2 MCP Protocol Implementation

- **Framework**: FastMCP (`fastmcp>=0.1.0`)
- **Transport**: Stdio (no HTTP server)
- **Tools**: 3 MCP tools registered via decorators
  - `start_indexing_background`: Queue background indexing job
  - `get_indexing_status`: Poll job progress
  - `search_code`: Semantic search
- **Resources**: 3 health/metrics endpoints
  - `health://status`: Service health check
  - `health://connection-pool`: Pool diagnostics
  - `metrics://prometheus`: Prometheus metrics export

### 1.3 Application Structure

```
src/
├── mcp/
│   ├── server_fastmcp.py      # Main server (FastMCP with lifespan)
│   ├── tools/                 # MCP tool implementations
│   │   ├── search.py
│   │   ├── project.py
│   │   └── background_indexing.py
│   ├── resources/             # MCP resources (health, metrics)
│   │   ├── health_endpoint.py
│   │   └── metrics_endpoint.py
│   ├── health.py
│   ├── errors.py
│   ├── mcp_logging.py
│   └── middleware.py
├── services/                  # Business logic
│   ├── indexer.py            # Repository indexing orchestration
│   ├── searcher.py           # Semantic search
│   ├── embedder.py           # Vector embeddings via Ollama
│   ├── chunker.py            # Code chunking (tree-sitter)
│   ├── scanner.py            # File discovery and detection
│   ├── background_worker.py  # Background job executor
│   ├── health_service.py     # Health checks
│   └── metrics_service.py    # Metrics collection
├── database/                  # Database layer
│   ├── session.py            # Async session management
│   ├── registry.py           # Project registry
│   ├── provisioning.py       # Database provisioning
│   └── auto_create.py        # Auto-create databases
├── connection_pool/           # Connection pooling
│   ├── manager.py            # Pool lifecycle management
│   ├── config.py             # Pool configuration
│   ├── health.py
│   ├── statistics.py
│   └── exceptions.py
├── config/
│   └── settings.py           # Environment-based config
├── models/                    # Pydantic data models
│   ├── code_file.py
│   ├── code_chunk.py
│   ├── indexing_job.py
│   ├── repository.py
│   ├── project_identifier.py
│   ├── health.py
│   ├── metrics.py
│   └── ...
└── auto_switch/              # Project auto-detection
    ├── session_context.py    # Session isolation
    ├── discovery.py          # Project discovery
    ├── cache.py
    └── validation.py
```

---

## 2. Dependencies & Requirements

### 2.1 Python Version
- **Required**: Python 3.11+
- **Tested**: Python 3.11, 3.12, 3.13 (classifiers in pyproject.toml)

### 2.2 Production Dependencies (`requirements.txt`)

| Category | Package | Version | Purpose |
|----------|---------|---------|---------|
| **Web Framework** | FastAPI | >=0.109.0 | API routing (used for tools/resources in FastMCP) |
| | uvicorn[standard] | >=0.27.0 | ASGI server (if HTTP endpoint needed) |
| **Database** | SQLAlchemy[asyncpg] | >=2.0.25 | Async ORM for PostgreSQL |
| | asyncpg | >=0.30.0 | Async PostgreSQL driver |
| | alembic | >=1.13.0 | Database migrations |
| | pgvector | >=0.2.4 | Vector similarity search |
| | aiosqlite | >=0.19.0 | Async SQLite fallback |
| **Data Validation** | pydantic | >=2.5.0 | Data validation/serialization |
| | pydantic-settings | >=2.1.0 | Environment-based config |
| **MCP Protocol** | mcp | >=0.9.0 | MCP protocol SDK |
| | fastmcp | >=0.1.0 | FastMCP framework (NEW) |
| **Code Parsing** | tree-sitter | >=0.21.0 | AST parsing |
| | tree-sitter-python | >=0.21.0 | Python grammar |
| | tree-sitter-javascript | >=0.21.0 | JavaScript grammar |
| | pathspec | >=0.11.0 | .gitignore pattern matching |
| **HTTP Client** | httpx | >=0.26.0 | Async HTTP client (Ollama) |
| **Utilities** | python-dotenv | >=1.0.0 | .env file loading |
| | greenlet | >=3.2.4 | Async compatibility |
| | jinja2 | >=3.1.0 | Template rendering |

### 2.3 External Service Dependencies

| Service | Purpose | Requirement |
|---------|---------|-------------|
| **PostgreSQL** | Code repository database | 14+ (pgvector extension) |
| **Ollama** | Embedding model service | Running at `OLLAMA_BASE_URL` |
| **tree-sitter** | Code parsing | Local (installed via pip) |

**Ollama Models**: 
- Default: `nomic-embed-text` (384-dim embeddings)
- Must be pre-pulled: `ollama pull nomic-embed-text`

### 2.4 Development Dependencies

Significant tools for quality (mypy, ruff, pytest, benchmarking):
- pytest, pytest-asyncio, pytest-cov, pytest-mock, pytest-timeout
- mypy with strict mode
- ruff (linting & formatting)
- py-spy (profiling)

---

## 3. Configuration Management

### 3.1 Environment Variables

**Required Variables**:
```bash
# Registry database (required for database-per-project architecture)
REGISTRY_DATABASE_URL=postgresql+asyncpg://user:password@host:5432/codebase_mcp_registry

# Ollama configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

**Optional Variables**:
```bash
# Legacy database (optional - for backward compatibility)
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/cb_proj_default_00000000

# Performance tuning
EMBEDDING_BATCH_SIZE=50          # Texts per Ollama request
MAX_CONCURRENT_REQUESTS=10       # Concurrent AI assistants

# Connection pool (advanced)
POOL_MIN_SIZE=2                  # Min connections
POOL_MAX_SIZE=10                 # Max connections
POOL_TIMEOUT=30.0                # Acquisition timeout
POOL_COMMAND_TIMEOUT=60.0        # Query timeout
POOL_MAX_IDLE_TIME=60.0          # Idle timeout
POOL_MAX_QUERIES=50000           # Queries before recycling
POOL_MAX_CONNECTION_LIFETIME=3600.0
POOL_LEAK_DETECTION_TIMEOUT=30.0
POOL_ENABLE_LEAK_DETECTION=true

# Logging
LOG_LEVEL=INFO
LOG_FILE=/tmp/codebase-mcp.log

# Workflow MCP integration (optional)
WORKFLOW_MCP_URL=http://localhost:8001
WORKFLOW_MCP_TIMEOUT=1.0
WORKFLOW_MCP_CACHE_TTL=60

# Background indexing (optional)
MAX_CONCURRENT_INDEXING_JOBS=2
INDEXING_JOB_TIMEOUT_SECONDS=3600
```

### 3.2 Settings Implementation

**File**: `/workspace/src/config/settings.py`
- Uses Pydantic 2.0+ BaseSettings
- Loads from `.env` file (auto-discovery)
- Fail-fast validation with actionable error messages
- Singleton pattern via `get_settings()` function
- Type-safe (mypy --strict compliance)

---

## 4. Database Architecture

### 4.1 Current Schema

**Database-Per-Project Architecture**:
- **Registry Database** (`codebase_mcp_registry`): Tracks all projects and their isolated databases
- **Project Databases** (`cb_proj_*`): Isolated per-project code repositories and embeddings

**Core Tables** (per project database):
```
repositories           # Git repositories being indexed
code_files            # Source files within repositories
code_chunks           # Semantic code chunks (AST-based)
indexing_jobs         # Background indexing job tracking
```

**Vector Similarity**: pgvector extension for semantic search
- Embeddings stored as `vector(384)` type (nomic-embed-text dimensions)
- HNSW index for fast similarity queries

### 4.2 Migrations

**Tool**: Alembic (database migration framework)
- **Config**: `/workspace/alembic.ini`
- **Versions**: `/workspace/migrations/versions/`
- **Current Migrations**: 7 versions (database refactoring, project registry, force reindex)

**Running Migrations**:
```bash
# Apply all pending migrations
DATABASE_URL=postgresql+asyncpg://... alembic upgrade head

# Rollback one step
DATABASE_URL=postgresql+asyncpg://... alembic downgrade -1

# Check current version
alembic current
```

---

## 5. Development vs Production Setup Differences

### 5.1 Development Setup

**Current**: Devcontainer-based development environment

```
.devcontainer/
├── Dockerfile              # Based on transformia/claude-code:2.0.28
├── docker-compose.yml      # Development services (jsonlint, markdownlint, yamllint)
├── devcontainer.json       # VS Code devcontainer config
└── .dockerignore
```

**Development Approach**:
- Editable install: `pip install -e .` (symlink to source)
- Server starts via: `codebase-mcp` (console script)
- Logs to: `/tmp/codebase-mcp.log`
- Database: Local PostgreSQL + Ollama
- Testing: pytest with markers (unit, integration, contract, performance)

### 5.2 Production Setup (Not Yet Containerized)

**Current Gaps**:
1. No production Dockerfile for application
2. No Docker Compose for multi-container deployment (app + PostgreSQL + Ollama)
3. No init scripts for database setup
4. No health check configuration
5. No signal handling for graceful shutdown
6. Logs written to `/tmp/` (should be persistent)
7. No process manager (systemd, supervisord)
8. No reverse proxy configuration (nginx)

**What Exists**:
- Executable entry point: `codebase-mcp` (can be wrapped)
- Comprehensive settings validation
- Health service (`HealthService`) with health checks
- Metrics service (`MetricsService`) for monitoring
- Graceful shutdown in lifespan context manager

---

## 6. Existing Containerization Efforts

### 6.1 Devcontainer (Development Only)

**Purpose**: VS Code devcontainer for development
- **Base Image**: `transformia/claude-code:2.0.28` (custom Claude Code image)
- **Tools**: hadolint, task, git, sudo, docker-cli
- **User**: `code` (non-root)
- **No database services**: Assumes local PostgreSQL + Ollama

**Limitations for Production**:
- Based on custom transformia images (not publicly available)
- Development tools not needed in production
- No application server included
- No database or Ollama containerization

### 6.2 Docker Compose (Development Only)

**Purpose**: Development environment orchestration
- **Services**: jsonlint, markdownlint, yamllint (linting tools)
- **Not for app/database**: App runs on host machine

---

## 7. Deployment Model Assessment

### 7.1 Current State

```
┌─────────────────────────────────────────────────────────┐
│ Claude Desktop                                          │
│ (MCP Client - Stdio transport)                         │
└──────────────────┬──────────────────────────────────────┘
                   │ Stdio (stdin/stdout/stderr)
                   │
┌──────────────────▼──────────────────────────────────────┐
│ codebase-mcp (Python FastMCP server)                    │
│ - Entry: src/mcp/server_fastmcp.py::main()            │
│ - Transport: Stdio (not HTTP)                          │
│ - Logging: /tmp/codebase-mcp.log                       │
└──────────────────┬──────────────────────────────────────┘
                   │ asyncpg driver (async)
                   │
        ┌──────────┴──────────┬────────────────────┐
        │                     │                    │
┌───────▼────────┐  ┌────────▼──────┐  ┌──────────▼──────┐
│ PostgreSQL 14+ │  │ PostgreSQL 14+ │  │ Ollama         │
│ (Registry DB)  │  │ (Project DBs)  │  │ (Embeddings)   │
└────────────────┘  └────────────────┘  └────────────────┘
```

### 7.2 What Needs Containerization

| Component | Current | Needed |
|-----------|---------|--------|
| **Python App** | Local binary | Docker image + container |
| **PostgreSQL** | Host machine | Docker container |
| **Ollama** | Host machine | Docker container |
| **Compose** | Dev only (lint tools) | Production (app + DB + Ollama) |
| **Health Checks** | Service exists | Docker health checks |
| **Logging** | /tmp/ file | Volume-mounted logs |
| **Signals** | Lifespan handles | Proper shutdown signals |

---

## 8. Key Implementation Details

### 8.1 Async Architecture

**Pattern**: Async-first design using asyncio + asyncpg
- All database operations are async (`AsyncSession`, `asyncpg`)
- Connection pooling via asyncpg: min=2, max=10 (configurable)
- Session-per-request pattern (auto-created by dependency injection)

### 8.2 Error Handling

**Production-Ready Patterns**:
- Fail-fast configuration validation (pydantic-settings)
- Proper exception hierarchy (`MCPError`, `ConnectionPoolError`)
- Graceful shutdown in lifespan (no abrupt termination)
- Retry logic for transient failures
- Comprehensive logging with context

### 8.3 Background Jobs

**Pattern**: Long-running indexing jobs without blocking MCP client
- `start_indexing_background`: Returns job_id immediately
- `get_indexing_status`: Poll for completion
- Worker pool: `background_worker.py` with configurable max concurrent jobs
- Job states: pending → running → completed/failed

### 8.4 Multi-Project Support

**Architecture**: Database-per-project isolation
- Project ID parameter in search/indexing tools (optional)
- Session auto-detection via `.codebase-mcp/config.json`
- Registry database tracks all project configurations
- Auto-provisioning of new project databases on first use

---

## 9. Running the Server

### 9.1 Manual Startup

```bash
# Install dependencies
pip install -r requirements.txt

# Set up .env file
cp .env.example .env
# Edit .env with database URLs and Ollama config

# Run migrations
DATABASE_URL=postgresql+asyncpg://... alembic upgrade head

# Start server (Stdio transport - output to stdout)
codebase-mcp
```

### 9.2 Claude Desktop Configuration

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

## 10. Summary: What Needs to Be Containerized

### High Priority (Core Deployment)

1. **Python Application Dockerfile**
   - Base: `python:3.11-slim` (minimal, production)
   - Install dependencies from requirements.txt
   - Run as non-root user
   - Entry point: `codebase-mcp` (FastMCP server)
   - Expose Stdio (no port needed)
   - Volume mounts: logs, config, database data

2. **Docker Compose (Production)**
   - Service: codebase-mcp (application)
   - Service: PostgreSQL 14+ (registry + project databases)
   - Service: Ollama (embedding model)
   - Networks: internal networking
   - Volumes: persistent data, logs, models
   - Health checks: each service

3. **Database Setup**
   - Init script for pgvector extension
   - Alembic migration on startup
   - Registry database provisioning

4. **Logging & Persistence**
   - Volume for `/tmp/codebase-mcp.log`
   - Log rotation configuration
   - Structured log output (JSON)

### Medium Priority (Operations)

5. **Health Checks**
   - Docker HEALTHCHECK directives
   - Readiness probe (database + Ollama connection)
   - Liveness probe (process running)

6. **Graceful Shutdown**
   - SIGTERM handling (already in lifespan)
   - Shutdown timeout (30s)
   - Connection drain before exit

7. **Monitoring & Observability**
   - Prometheus metrics endpoint
   - Health endpoint
   - Structured logging

### Low Priority (Enhancements)

8. **Reverse Proxy** (if HTTP needed)
   - Nginx configuration (if moving beyond Stdio)
   - TLS/HTTPS support

9. **Process Management** (if not Docker)
   - Systemd service file
   - Supervisord configuration
   - Init script for traditional deployment

---

## 11. Constraints & Considerations

### 11.1 Stdio Transport Constraint

**Key Limitation**: This is an MCP Stdio server, NOT an HTTP service
- Output is the MCP protocol (binary/JSON)
- Cannot expose via reverse proxy
- Cannot be accessed via HTTP
- Must run as subprocess of Claude Desktop (or similar MCP client)

**Implications for Containerization**:
- Cannot expose a port (Stdio is process-local)
- Health checks must be internal (not HTTP probes)
- Monitoring must be via logs/metrics
- Container primarily for isolation and reproducibility

### 11.2 Multi-Container Coordination

**Services Must Communicate**:
- App → PostgreSQL (REGISTRY_DATABASE_URL)
- App → Ollama (OLLAMA_BASE_URL)
- Both must be reachable from app container

**Network Considerations**:
- Internal Docker network (no external exposure needed)
- Service discovery via container names
- Environment variable injection for connection strings

### 11.3 Database Initialization

**Challenge**: Two-phase database setup
1. Create databases (registry + project databases)
2. Run migrations (Alembic upgrade head)
3. Insert seed data (optional)

**Solution**: Init container or entrypoint script

---

## 12. Recommended Containerization Approach

### Phase 1: Application Container

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install -e .

USER nobody
ENTRYPOINT ["codebase-mcp"]
```

### Phase 2: Docker Compose Stack

```yaml
services:
  postgres:
    image: postgres:14-alpine
    environment:
      POSTGRES_PASSWORD: ...
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./scripts/init_db.sql:/docker-entrypoint-initdb.d/

  ollama:
    image: ollama/ollama
    volumes:
      - ollama-models:/root/.ollama
    command: serve
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]

  codebase-mcp:
    build: .
    depends_on:
      postgres:
        condition: service_healthy
      ollama:
        condition: service_healthy
    environment:
      REGISTRY_DATABASE_URL: postgresql+asyncpg://...
      OLLAMA_BASE_URL: http://ollama:11434
    volumes:
      - ./logs:/tmp
```

### Phase 3: Production Hardening

- Image scanning and security
- Multi-stage builds (reduce image size)
- Non-root user enforcement
- Resource limits
- Graceful shutdown configuration

---

## Conclusion

The Codebase MCP Server is a well-architected, production-ready application that currently runs as a local CLI tool. Its containerization should focus on:

1. **Reproducibility**: Docker image ensures consistent environment
2. **Isolation**: Containerized PostgreSQL, Ollama, and app
3. **Operations**: Compose file for easy deployment
4. **Observability**: Health checks, logging, metrics

The application's architecture (async, connection pooling, graceful shutdown) is already production-ready for containerization.
