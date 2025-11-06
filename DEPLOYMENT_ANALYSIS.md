# Codebase MCP Server - Deployment Architecture Analysis

## Executive Summary

**Codebase MCP Server** is a production-grade MCP (Model Context Protocol) server for semantic code search with PostgreSQL pgvector. It currently runs as a CLI application using Stdio transport (designed for Claude Desktop integration). There is **NO production containerization** - only a development devcontainer exists.

**Current Status**: Application runs directly on host OS or in development container with external PostgreSQL and Ollama dependencies.

---

## 1. Current Server Architecture

### 1.1 Entry Point & Execution Model

**Main Entry Point**: `src/mcp/server_fastmcp.py::main()`

```bash
# Package script (from pyproject.toml)
codebase-mcp = "src.mcp.server_fastmcp:main"

# Direct execution
python -m src.mcp.server_fastmcp

# From installed package
codebase-mcp
```

**Protocol & Transport**:
- **Framework**: FastMCP (`fastmcp>=0.1.0`)
- **Transport**: Stdio (NOT HTTP) - direct process communication via stdin/stdout
- **Design**: Single-process, blocking initialization pattern
- **Startup Time Target**: <2 seconds (measured)
- **Lifespan Pattern**: Async context manager with startup/shutdown hooks

### 1.2 Application Lifecycle

**Startup Sequence** (in `lifespan()` context manager):

```
1. Import tool modules (search, project, background_indexing)
2. Import resource modules (health, metrics_endpoint)
3. Initialize FastMCP server with lifespan
4. [STARTUP HOOK]:
   - Start session manager (async)
   - Initialize connection pool (blocking if DATABASE_URL set)
   - Initialize health service
   - Initialize metrics service
5. Tools registered and ready for MCP client calls
6. [SHUTDOWN HOOK]:
   - Close connection pool gracefully (30s timeout)
   - Stop session manager
```

**Execution Context**:
- Single process, single thread + async event loop
- Connection pool manages ~20-30 concurrent database connections
- Background worker thread pool for long-running indexing jobs
- File logging to `/tmp/codebase-mcp.log` (rotating, 10MB max, 5 backups)

### 1.3 Registered MCP Tools & Resources

**Tools** (3 total):
- `start_indexing_background`: Queue background indexing job
- `get_indexing_status`: Poll job progress
- `search_code`: Semantic code search

**Resources** (3 total):
- `health://status`: Service health check (<50ms response)
- `health://connection-pool`: Pool diagnostics
- `metrics://prometheus`: Prometheus metrics export

---

## 2. Dependencies & Requirements

### 2.1 Python & Runtime

**Required**:
- Python: 3.11+ (supports 3.11, 3.12, 3.13)
- `uv` package manager (recommended) or `pip`

**Installation Method**:
- Editable install: `uv pip install -e .` or `pip install -e .`
- Package install: `pip install codebase-mcp`

### 2.2 External Services (REQUIRED)

#### PostgreSQL 14+ (required)

```
Connection: postgresql+asyncpg://user:password@host:5432/database
Async Driver: asyncpg (required for FastMCP async)
Database: Two architectures supported:

1. Legacy (single database):
   - DATABASE_URL: Single shared database
   - Deprecated but supported for backward compatibility

2. Modern (recommended - database-per-project):
   - REGISTRY_DATABASE_URL: Central project registry/metadata
   - Automatic per-project databases: cb_proj_<uuid>
   - Auto-provisioned on first use
```

**Schema**:
- Managed by Alembic migrations (19 versions total)
- pgvector extension required (for semantic search)
- Tables: code_files, code_chunks, project_registry, indexing_jobs

#### Ollama (required for embeddings)

```
Service: Ollama embedding server
Default URL: http://localhost:11434
Default Model: nomic-embed-text (768-dimensional embeddings)
Must be pre-pulled: ollama pull nomic-embed-text
```

**Alternative Models**:
- `mxbai-embed-large` (1024-dimensional, slower)
- `all-minilm:latest` (384-dimensional, faster)

### 2.3 Python Dependencies Summary

**Core Production Dependencies** (from `pyproject.toml`):

```
# Web Framework & MCP Protocol
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
fastmcp>=0.1.0
mcp>=0.9.0

# Database & ORM
sqlalchemy[asyncpg]>=2.0.25
asyncpg>=0.30.0
alembic>=1.13.0
pgvector>=0.2.4

# Data Validation & Settings
pydantic>=2.5.0
pydantic-settings>=2.1.0

# Code Parsing (tree-sitter for AST extraction)
tree-sitter>=0.21.0
tree-sitter-python>=0.21.0
tree-sitter-javascript>=0.21.0
pathspec>=0.11.0

# HTTP Client (for Ollama API calls)
httpx>=0.26.0

# Utilities
python-dotenv>=1.0.0
greenlet>=3.2.4
jinja2>=3.1.0
```

**Total Dependencies**: ~30+ transitive dependencies

---

## 3. Configuration & Environment Variables

### 3.1 Required Environment Variables

```bash
# Registry Database (ALWAYS REQUIRED)
REGISTRY_DATABASE_URL=postgresql+asyncpg://user:password@host:5432/codebase_mcp_registry

# Ollama Service
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

### 3.2 Optional Environment Variables

```bash
# Legacy/Fallback Database (optional, for backward compatibility)
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/cb_proj_default_00000000

# Performance Tuning
EMBEDDING_BATCH_SIZE=50 (default, range: 1-1000)
MAX_CONCURRENT_REQUESTS=10 (default, range: 1-100)

# Connection Pool (if DATABASE_URL set)
DB_POOL_SIZE=20 (default)
DB_MAX_OVERFLOW=10 (default)

# Advanced Pool Configuration
POOL_MIN_SIZE=2
POOL_MAX_SIZE=10
POOL_TIMEOUT=30.0
POOL_COMMAND_TIMEOUT=60.0
POOL_MAX_IDLE_TIME=300.0
POOL_MAX_QUERIES=50000
POOL_MAX_CONNECTION_LIFETIME=3600.0
POOL_LEAK_DETECTION_TIMEOUT=30.0
POOL_ENABLE_LEAK_DETECTION=true

# Logging
LOG_LEVEL=INFO (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_FILE=/tmp/codebase-mcp.log

# Optional: Workflow MCP Integration
WORKFLOW_MCP_URL=http://localhost:8000 (optional, for multi-project auto-detection)
WORKFLOW_MCP_TIMEOUT=1.0 (seconds)
WORKFLOW_MCP_CACHE_TTL=60 (seconds)

# Background Indexing
MAX_CONCURRENT_INDEXING_JOBS=2 (default)
INDEXING_JOB_TIMEOUT_SECONDS=3600 (1 hour default)
```

### 3.3 Configuration Loading

- **Method**: Pydantic v2 `BaseSettings` with `.env` file support
- **Location**: `.env` file in working directory (auto-loaded)
- **Validation**: Fail-fast pattern - invalid config halts startup with actionable error messages
- **Type Safety**: Full Pydantic v2 validation (mypy --strict compliant)

---

## 4. Development vs Production Setup

### 4.1 Development Setup (Current)

**Location**: Devcontainer in `.devcontainer/`

**Services**:
- `claude`: Development container (based on `transformia/claude-code:2.0.28`)
  - Mounts source code from host: `/workspace`
  - Includes: git, docker-cli, task runner, hadolint
  - User: `code` (non-root, UID/GID configurable)
  - Entrypoint: bash with sleep loop for persistence

- `jsonlint`, `markdownlint`, `yamllint`: Linting containers (read-only)

**External Services** (required, on host):
- PostgreSQL 14+ (typically local)
- Ollama (typically local, port 11434)

**Server Startup**:
```bash
# Inside devcontainer
uv pip install -e .
python -m src.mcp.server_fastmcp
# OR
codebase-mcp
```

**Logs**:
- File: `/tmp/codebase-mcp.log`
- Stderr: Startup status messages
- MCP Client: Context-injected logging

### 4.2 Production Deployment (Current - NO CONTAINERIZATION)

**Current State**: Requires manual installation on host OS

**Installation Steps**:
```bash
# 1. Install Python 3.11+, PostgreSQL 14+, Ollama

# 2. Clone repository
git clone https://github.com/cliffclarke/codebase-mcp.git
cd codebase-mcp

# 3. Create .env file
cp .env.example .env
# Edit .env with production database URLs and Ollama endpoint

# 4. Install package (editable for development, or normal for production)
pip install -e .  # Development
# OR
pip install .  # Production

# 5. Run server
codebase-mcp

# 6. Restart service if needed
# systemd service file required (does not exist)
# OR run as background process: nohup codebase-mcp > /var/log/codebase-mcp.log 2>&1 &
```

**Missing Pieces for Production**:
- No Docker image
- No docker-compose for production stack
- No systemd service file
- No health check endpoint (exists but not exposed via HTTP)
- No metrics endpoint (exists but not exposed via HTTP - Prometheus format via MCP resource)
- No process manager (systemd, supervisor, etc.)
- No log rotation configuration (relies on Python rotating handler)

---

## 5. Database Setup & Migrations

### 5.1 Alembic Migrations

**Configuration**: `alembic.ini` (configured but DATABASE_URL not set in file)

**Versions**: 19 migration files

```
001_initial_schema.py
002_remove_non_search_tables.py
003_project_tracking.py
003a_add_missing_work_item_columns.py
003b_fix_version_column_for_optimistic_locking.py
005_case_insensitive_vendor_name.py
006_add_project_registry_schema.py
007_provision_default_workspace.py
008_add_indexing_jobs.py
... (recent versions with timestamps)
20251019_1348_add_status_message_to_indexing_jobs.py
20251019_1400_add_force_reindex_to_indexing_jobs.py
```

### 5.2 Schema Overview

**Tables**:
- `code_files`: Repository file metadata (with vector embeddings)
- `code_chunks`: Code segments with vector embeddings
- `project_registry`: Project/workspace tracking
- `indexing_jobs`: Background job tracking
- Supporting tables for migrations

**Indexes**:
- Vector similarity: pgvector `<=>` operator for cosine distance
- Full-text search: PostgreSQL tsvector for keyword search
- Standard indexes on `project_id`, `file_path`, `status`

### 5.3 Running Migrations

```bash
# Standard flow (uses DATABASE_URL env var)
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/db alembic upgrade head

# For registry database
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/codebase_mcp_registry alembic upgrade head

# Current status
alembic current

# History
alembic history

# Rollback (rarely needed)
alembic downgrade -1
```

---

## 6. Existing Containerization Efforts

### 6.1 Development Container (Exists)

**Files**:
- `/workspace/.devcontainer/Dockerfile`
- `/workspace/.devcontainer/docker-compose.yml`
- `/workspace/.devcontainer/devcontainer.json`
- `/workspace/.devcontainer/.dockerignore`

**Purpose**: VS Code / Claude Code development environment

**Limitations**:
- Single service container (development tools only)
- No PostgreSQL container
- No Ollama container
- Relies on host services
- Not suitable for production deployment

### 6.2 Missing Production Containers

**What Needs to be Created**:

1. **codebase-mcp service image**
   - Base: Python 3.11+ alpine or debian
   - Install: dependencies + codebase-mcp package
   - Entrypoint: codebase-mcp with proper signal handling
   - Health check: Health endpoint (would need HTTP wrapper or health check script)

2. **docker-compose.yml (production)**
   - codebase-mcp service
   - PostgreSQL 14 service (with pgvector extension)
   - Ollama service (CPU or GPU variants)
   - Networks: isolated app network
   - Volumes: persistent database storage
   - Environment variables: pre-configured

3. **Init scripts**
   - Database provisioning (create registry, run migrations)
   - Ollama model downloading (ollama pull nomic-embed-text)

---

## 7. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Claude Desktop Client                    │
└────────────────────────┬────────────────────────────────────┘
                         │ (Stdio Transport via MCP Protocol)
                         ▼
        ┌────────────────────────────────────┐
        │   FastMCP Server Process            │
        │   (src/mcp/server_fastmcp.py)      │
        │                                    │
        │  ┌──────────────────────────────┐ │
        │  │ Tools                        │ │
        │  │ - start_indexing_background │ │
        │  │ - get_indexing_status       │ │
        │  │ - search_code               │ │
        │  └──────────────────────────────┘ │
        │                                    │
        │  ┌──────────────────────────────┐ │
        │  │ Resources                    │ │
        │  │ - health://status            │ │
        │  │ - health://connection-pool   │ │
        │  │ - metrics://prometheus       │ │
        │  └──────────────────────────────┘ │
        │                                    │
        │  ┌──────────────────────────────┐ │
        │  │ Services                     │ │
        │  │ - Indexer (AST parsing)     │ │
        │  │ - Searcher (pgvector)       │ │
        │  │ - Embedder (Ollama API)     │ │
        │  │ - Background Worker          │ │
        │  │ - Health & Metrics           │ │
        │  └──────────────────────────────┘ │
        │                                    │
        │  ┌──────────────────────────────┐ │
        │  │ Connection Pool Manager      │ │
        │  │ (20-30 async connections)   │ │
        │  └──────────────────────────────┘ │
        └────────────────────────────────────┘
                    │                    │
                    ▼                    ▼
        ┌────────────────────┐  ┌────────────────────┐
        │    PostgreSQL 14   │  │     Ollama 0.x     │
        │   + pgvector ext   │  │   (Embedding API)  │
        │   (Code search DB) │  │   Port: 11434      │
        │   Port: 5432       │  │                    │
        └────────────────────┘  └────────────────────┘
```

---

## 8. Summary: What Needs Containerization

### For Production Docker Support, Need:

1. **Production Dockerfile**
   - Base: Python 3.11 slim (minimal) or alpine (tiny)
   - Dependencies: pip install -r requirements.txt
   - Entrypoint: codebase-mcp with proper signal handling
   - Non-root user: app (for security)
   - Health check: curl or script to verify startup

2. **Production docker-compose.yml**
   - Three services: codebase-mcp, postgres, ollama
   - Environment: Load from .env file
   - Volumes: persistent postgres data, logs
   - Networks: isolated docker network
   - Dependencies: service startup ordering

3. **Init Container / Scripts**
   - Database migration runner (alembic upgrade head)
   - Ollama model puller (ollama pull nomic-embed-text)
   - Registry database initialization

4. **Configuration**
   - Dockerfile ARG/ENV for build-time defaults
   - .env.docker template for runtime
   - Health check validation script

5. **Documentation**
   - Docker build instructions
   - docker-compose deployment guide
   - Environment variable reference
   - Health check & monitoring setup
   - Troubleshooting guide

### Key Non-Docker Changes Needed:

1. **Expose Health/Metrics via HTTP** (currently MCP resource only)
   - Add FastAPI app alongside FastMCP
   - OR add lightweight HTTP wrapper
   - Enables Docker HEALTHCHECK directive

2. **Graceful Shutdown**
   - Signal handlers for SIGTERM/SIGINT
   - Connection pool graceful close
   - Already implemented in lifespan context manager

3. **Log Forwarding**
   - Option to write JSON logs to stdout
   - Option to skip file logging in containers
   - Docker can capture stdout/stderr

---

## 9. Key Files & Locations

**Entry Point**:
- `/workspace/src/mcp/server_fastmcp.py` - Main FastMCP server

**Configuration**:
- `/workspace/src/config/settings.py` - Pydantic settings loader
- `/workspace/.env` - Environment variables (actual values)
- `/workspace/.env.example` - Template

**Database**:
- `/workspace/alembic.ini` - Alembic configuration
- `/workspace/migrations/` - Migration files

**Dependencies**:
- `/workspace/pyproject.toml` - Package metadata & dependencies
- `/workspace/requirements.txt` - Flattened dependency list

**Development**:
- `/workspace/.devcontainer/Dockerfile` - Dev container (existing)
- `/workspace/.devcontainer/docker-compose.yml` - Dev compose (existing)

**Services**:
- `/workspace/src/services/` - Business logic (indexer, searcher, embedder, background_worker)
- `/workspace/src/mcp/tools/` - MCP tool implementations
- `/workspace/src/mcp/resources/` - MCP resource implementations

---

## 10. Performance Characteristics (Current)

**Server Startup**: <2 seconds (connection pool ready)
**Search Latency**: 340ms p95 (500ms target)
**Indexing**: 50.4s p95 for 10K files (60s target)
**Connection Pool**: 20-30 concurrent connections (configurable)
**Background Jobs**: Configurable concurrency (default: 2)

---

## Summary

The Codebase MCP Server is **production-ready for deployment but currently lacks containerization**. The application:

- Runs as a single Python process with async FastMCP server
- Communicates via Stdio transport (not HTTP)
- Requires PostgreSQL 14+ and Ollama embedding service
- Uses environment-based configuration with fail-fast validation
- Has mature database schema with 19 Alembic migrations
- Includes health checks and metrics (currently MCP resource-only)
- Has existing development devcontainer but no production containers

**To containerize for production**, you need:
1. Production Dockerfile (Python 3.11+, minimal dependencies)
2. docker-compose.yml with PostgreSQL + Ollama services
3. HTTP wrapper or FastAPI for health checks and metrics
4. Init scripts for database migrations and model downloading
5. Environment variable templates and documentation

