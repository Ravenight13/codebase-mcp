# codebase-mcp

> **⚠️ REFACTORING IN PROGRESS**
> This MCP is being refactored to focus exclusively on semantic code search
> with multi-project support. See [`docs/REFACTORING-JOURNAL.md`](docs/REFACTORING-JOURNAL.md) for status.

## Current Refactoring Status

**Phase 0: Preparation** 🚧 (In Progress)
- [x] Refactor branch created
- [x] Rollback procedures established
- [ ] Performance baseline collected
- [ ] Database permissions validated

**Phases 1-12: Implementation** ⏳ (Pending)
- Database refactor (per-project databases)
- Remove non-search features (14 tools → 0)
- Keep core search tools (2 tools)
- Add multi-project support
- Target: 16 → 2 tools, 4500 → 1800 LOC

## Emergency Rollback

If issues occur during refactoring:

```bash
./scripts/emergency_rollback.sh
```

This restores the codebase to tag: `backup-before-refactor`

---

## Overview

A production-grade MCP (Model Context Protocol) server that indexes code repositories into PostgreSQL with pgvector for semantic search, designed specifically for AI coding assistants.

The Codebase MCP Server provides semantic code search capabilities through a focused, local-first architecture. It enables AI assistants to understand and navigate codebases efficiently by combining tree-sitter AST parsing with vector embeddings.

### Key Features

- **Semantic Code Search**: Natural language queries across indexed repositories
- **Repository Indexing**: Fast scanning and chunking with tree-sitter parsers
- **Task Management**: Development task tracking with git integration
- **MCP Protocol**: Six focused tools via Server-Sent Events (SSE) and stdio (JSON-RPC)
- **Performance Guaranteed**: 60-second indexing for 10K files, 500ms p95 search latency
- **Production Ready**: Comprehensive error handling, structured logging, type safety

### MCP Tools

1. **search_code**: Semantic search across indexed code
2. **index_repository**: Index a repository for searching
3. **get_task**: Retrieve a specific development task
4. **list_tasks**: List tasks with filtering options
5. **create_task**: Create a new development task
6. **update_task**: Update task status with git integration

## Quick Start

### 1. Database Setup
```bash
# Create database
createdb codebase_mcp

# Initialize schema
psql -d codebase_mcp -f db/init_tables.sql
```

### 2. Install Dependencies
```bash
# Install dependencies including FastMCP framework
uv sync

# Or with pip
pip install -r requirements.txt
```

**Key Dependencies:**
- `fastmcp>=0.1.0` - Modern MCP framework with decorator-based tools
- `anthropic-mcp` - MCP protocol implementation
- `sqlalchemy>=2.0` - Async ORM
- `pgvector` - PostgreSQL vector extension
- `ollama` - Embedding generation

### 3. Configure Claude Desktop
Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "codebase-mcp": {
      "command": "uv",
      "args": [
        "run",
        "--with",
        "fastmcp",
        "python",
        "/absolute/path/to/codebase-mcp/server_fastmcp.py"
      ]
    }
  }
}
```

**Important:**
- Use absolute paths!
- Server uses FastMCP framework with decorator-based tool definitions
- All logs go to `/tmp/codebase-mcp.log` (no stdout/stderr pollution)

### 4. Start Ollama
```bash
ollama serve
ollama pull nomic-embed-text
```

### 5. Test
```bash
# Test database and tools
uv run python tests/test_tool_handlers.py

# Test repository indexing
uv run python tests/test_embeddings.py
```

## Current Status

### Working Tools (6/6) ✅

| Tool | Status | Description |
|------|--------|-------------|
| `create_task` | ✅ Working | Create development tasks with planning references |
| `get_task` | ✅ Working | Retrieve task by ID |
| `list_tasks` | ✅ Working | List tasks with filters (status, branch) |
| `update_task` | ✅ Working | Update tasks with git tracking (branch, commit) |
| `index_repository` | ✅ Working | Index code repositories with semantic chunking |
| `search_code` | ✅ Working | Semantic code search with pgvector similarity |

### Recent Fixes (Oct 6, 2025)
- ✅ Parameter passing architecture (Pydantic models)
- ✅ MCP schema mismatches (status enums, missing parameters)
- ✅ Timezone/datetime compatibility (PostgreSQL)
- ✅ Binary file filtering (images, cache dirs)

### Test Results
```
✅ Task Management: 7/7 tests passed
✅ Repository Indexing: 2 files indexed, 6 chunks created
✅ Embeddings: 100% coverage (768-dim vectors)
✅ Database: Connection pooling, async operations working
```

## Tool Usage Examples

### Create a Task
In Claude Desktop:
```
Create a task called "Implement user authentication" with description "Add JWT-based authentication to the API"
```

Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Implement user authentication",
  "description": "Add JWT-based authentication to the API",
  "status": "need to be done",
  "created_at": "2025-10-06T21:30:00",
  "planning_references": []
}
```

### Index a Repository
```
Index the repository at /Users/username/projects/myapp
```

Response:
```json
{
  "repository_id": "abc123...",
  "files_indexed": 234,
  "chunks_created": 1456,
  "duration_seconds": 12.5,
  "status": "success"
}
```

### Search Code
```
Search for "authentication middleware" in Python files
```

Response:
```json
{
  "results": [
    {
      "file_path": "src/middleware/auth.py",
      "content": "def authenticate_request(request):\n    ...",
      "start_line": 45,
      "similarity_score": 0.92
    }
  ],
  "total_count": 5,
  "latency_ms": 250
}
```

### Track Task with Git
```
Update task abc123 to status "in-progress" and link it to branch "feature/auth"
```

Response:
```json
{
  "id": "abc123...",
  "status": "in-progress",
  "branches": ["feature/auth"],
  "commits": []
}
```

## Architecture

```
Claude Desktop ↔ FastMCP Server ↔ Tool Handlers ↔ Services ↔ PostgreSQL
                                                        ↓
                                                     Ollama (embeddings)
```

**MCP Framework**: Built with [FastMCP](https://github.com/jlowin/fastmcp) - a modern, decorator-based framework for building MCP servers with:
- Type-safe tool definitions via `@mcp.tool()` decorators
- Automatic JSON Schema generation from Pydantic models
- Dual logging (file + MCP protocol) without stdout pollution
- Async/await support throughout

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed component diagrams.

## Documentation

- **[docs/status/MCP_SERVER_STATUS.md](docs/status/MCP_SERVER_STATUS.md)** - Current status, test results, configuration
- **[docs/status/SESSION_HANDOFF.md](docs/status/SESSION_HANDOFF.md)** - Recent problems solved, current working state
- **[docs/guides/SETUP_GUIDE.md](docs/guides/SETUP_GUIDE.md)** - Complete setup instructions with troubleshooting
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System architecture and data flow
- **[CLAUDE.md](CLAUDE.md)** - Specify workflow for AI-assisted development

## Database Schema

11 tables with pgvector for semantic search:

**Core Tables:**
- `repositories` - Indexed repositories
- `code_files` - Source files with metadata
- `code_chunks` - Semantic chunks with embeddings (vector(768))
- `tasks` - Development tasks with git tracking
- `task_status_history` - Audit trail

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for complete schema documentation.

## Technology Stack

- **MCP Framework:** FastMCP 0.1+ (decorator-based tool definitions)
- **Server:** Python 3.13+, FastAPI patterns, async/await
- **Database:** PostgreSQL 14+ with pgvector extension
- **Embeddings:** Ollama (nomic-embed-text, 768 dimensions)
- **ORM:** SQLAlchemy 2.0 (async), Pydantic V2 for validation
- **Type Safety:** Full mypy --strict compliance

## Development

### Running Tests
```bash
# Tool handlers
uv run python tests/test_tool_handlers.py

# Repository indexing
uv run python tests/test_embeddings.py

# Unit tests
uv run pytest tests/ -v
```

### Code Structure
```
codebase-mcp/
├── server_fastmcp.py              # FastMCP server entry point (NEW)
├── src/
│   ├── mcp/
│   │   └── tools/                 # Tool handlers with service integration
│   │       ├── tasks.py           # Task management
│   │       ├── indexing.py        # Repository indexing
│   │       └── search.py          # Semantic search
│   ├── services/                  # Business logic layer
│   │   ├── tasks.py               # Task CRUD + git tracking
│   │   ├── indexer.py             # Indexing orchestration
│   │   ├── scanner.py             # File discovery
│   │   ├── chunker.py             # AST-based chunking
│   │   ├── embedder.py            # Ollama integration
│   │   └── searcher.py            # pgvector similarity search
│   └── models/                    # Database models + Pydantic schemas
│       ├── task.py                # Task, TaskCreate, TaskUpdate
│       ├── code_chunk.py          # CodeChunk
│       └── ...
└── tests/
    ├── test_tool_handlers.py      # Integration tests
    └── test_embeddings.py         # Embedding validation
```

**FastMCP Server Architecture:**
- `server_fastmcp.py` - Main entry point using `@mcp.tool()` decorators
- Tool handlers in `src/mcp/tools/` provide service integration
- Services in `src/services/` contain all business logic
- Dual logging: file (`/tmp/codebase-mcp.log`) + MCP protocol

## Prerequisites

### System Requirements

- **Python 3.11+** (3.13 compatible)
- **PostgreSQL 14+** with pgvector extension
- **Ollama** for embedding generation
- **4GB+ RAM** recommended
- **SSD storage** for optimal performance

### PostgreSQL with pgvector

```bash
# Install PostgreSQL 14+
# macOS
brew install postgresql@14
brew services start postgresql@14

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install postgresql-14 postgresql-contrib-14

# Install pgvector extension
# macOS
brew install pgvector

# Ubuntu/Debian
sudo apt install postgresql-14-pgvector

# Enable pgvector in your database
psql -U postgres -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Ollama Setup

```bash
# Install Ollama
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama service
ollama serve

# Pull required embedding model
ollama pull nomic-embed-text
```

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/cliffclarke/codebase-mcp.git
cd codebase-mcp
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python3.11 -m venv .venv

# Activate virtual environment
# macOS/Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Install production dependencies (includes FastMCP)
pip install -r requirements.txt

# For development (includes testing and linting tools)
pip install -r requirements-dev.txt

# Or with uv (recommended)
uv sync
```

**Key Dependencies Installed:**
- `fastmcp>=0.1.0` - Modern MCP framework
- `sqlalchemy>=2.0` - Async database ORM
- `pgvector` - PostgreSQL vector extension Python bindings
- `ollama` - Embedding generation client
- `pydantic>=2.0` - Data validation and settings

### 4. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your configuration
nano .env
```

**Environment Variables:**

```bash
# Database Configuration
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/codebase_mcp

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=embeddinggemma

# Performance Tuning
EMBEDDING_BATCH_SIZE=50        # Batch size for embedding generation
MAX_CONCURRENT_REQUESTS=10     # Max parallel Ollama requests

# Logging
LOG_LEVEL=INFO                  # DEBUG, INFO, WARNING, ERROR
LOG_FILE=/tmp/codebase-mcp.log  # Log file location
```

## Database Setup

### 1. Create Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE codebase_mcp;

# Enable pgvector extension
\c codebase_mcp
CREATE EXTENSION IF NOT EXISTS vector;
\q
```

### 2. Initialize Schema

```bash
# Run database initialization script
python scripts/init_db.py

# Verify schema creation
alembic current
```

The initialization script will:
- Create all required tables (repositories, files, chunks, tasks)
- Set up vector indexes for similarity search
- Configure connection pooling
- Apply all database migrations

### 3. Verify Setup

```bash
# Check database connectivity
python -c "from src.database import Database; import asyncio; asyncio.run(Database.create_pool())"

# Run migration status check
alembic current
```

### 4. Database Reset & Cleanup

During development, you may need to reset your database. See [DATABASE_RESET.md](DATABASE_RESET.md) for three reset options:

- **scripts/clear_data.sh** - Clear all data, keep schema (fastest, no restart needed)
- **scripts/reset_database.sh** - Drop and recreate all tables (recommended for schema changes)
- **scripts/nuclear_reset.sh** - Drop entire database (requires Claude Desktop restart)

```bash
# Quick data wipe (keeps schema)
./scripts/clear_data.sh

# Full table reset (recommended)
./scripts/reset_database.sh

# Nuclear option (drops database)
./scripts/nuclear_reset.sh
```

## Running the Server

### FastMCP Server (Recommended)

The primary way to run the server is via Claude Desktop or other MCP clients:

```bash
# Via Claude Desktop (configured in claude_desktop_config.json)
# Server starts automatically when Claude Desktop launches

# Manual testing with FastMCP CLI
uv run --with fastmcp python server_fastmcp.py

# With custom log level
LOG_LEVEL=DEBUG uv run --with fastmcp python server_fastmcp.py
```

**Server Entry Point**: `server_fastmcp.py` in repository root

**Logging**: All output goes to `/tmp/codebase-mcp.log` (configurable via `LOG_FILE` env var)

### Development Mode (Legacy FastAPI)

```bash
# Start with auto-reload (if FastAPI server exists)
uvicorn src.main:app --reload --host 127.0.0.1 --port 3000

# With custom log level
LOG_LEVEL=DEBUG uvicorn src.main:app --reload
```

### Production Mode (Legacy)

```bash
# Start production server
uvicorn src.main:app --host 0.0.0.0 --port 3000 --workers 4

# With gunicorn (recommended for production)
gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:3000
```

### stdio Transport (Legacy CLI Mode)

The legacy MCP server supports stdio transport for CLI clients via JSON-RPC 2.0 over stdin/stdout.

```bash
# Start stdio server (reads JSON-RPC from stdin)
python -m src.mcp.stdio_server

# Echo a single request
echo '{"jsonrpc":"2.0","id":1,"method":"list_tasks","params":{"limit":5}}' | python -m src.mcp.stdio_server

# Pipe requests from a file (one JSON-RPC request per line)
cat requests.jsonl | python -m src.mcp.stdio_server

# Interactive mode (type JSON-RPC requests manually)
python -m src.mcp.stdio_server
{"jsonrpc":"2.0","id":1,"method":"get_task","params":{"task_id":"..."}}
```

**JSON-RPC 2.0 Request Format:**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "search_code",
  "params": {
    "query": "async def",
    "limit": 10
  }
}
```

**JSON-RPC 2.0 Response Format:**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "results": [...],
    "total_count": 42,
    "latency_ms": 250
  }
}
```

**Available Methods:**
- `search_code` - Semantic code search
- `index_repository` - Index a repository
- `get_task` - Get task by ID
- `list_tasks` - List tasks with filters
- `create_task` - Create new task
- `update_task` - Update task status

**Logging:**
All logs go to `/tmp/codebase-mcp.log` (configurable via `LOG_FILE` env var). No stdout/stderr pollution - only JSON-RPC protocol messages on stdout.

### Health Check

```bash
# Check server health
curl http://localhost:3000/health

# Expected response:
{
  "status": "healthy",
  "database": "connected",
  "ollama": "connected",
  "version": "0.1.0"
}
```

## Usage Examples

### 1. Index a Repository

```python
# Via MCP protocol
{
  "tool": "index_repository",
  "arguments": {
    "path": "/path/to/your/repo",
    "name": "My Project",
    "force_reindex": false
  }
}

# Response
{
  "repository_id": "uuid-here",
  "files_indexed": 150,
  "chunks_created": 1200,
  "duration_seconds": 45.3,
  "status": "success"
}
```

### 2. Search Code

```python
# Search for authentication logic
{
  "tool": "search_code",
  "arguments": {
    "query": "user authentication password validation",
    "limit": 10,
    "file_type": "py"
  }
}

# Response includes ranked code chunks with context
{
  "results": [...],
  "total_count": 25,
  "latency_ms": 230
}
```

### 3. Task Management

```python
# Create a task
{
  "tool": "create_task",
  "arguments": {
    "title": "Implement rate limiting",
    "description": "Add rate limiting to API endpoints",
    "planning_references": ["specs/rate-limiting.md"]
  }
}

# Update task with git integration
{
  "tool": "update_task",
  "arguments": {
    "task_id": "task-uuid",
    "status": "complete",
    "branch": "feature/rate-limiting",
    "commit": "abc123..."
  }
}
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│                 MCP Client (AI)                 │
└─────────────────┬───────────────────────────────┘
                  │ SSE Protocol
┌─────────────────▼───────────────────────────────┐
│              MCP Server Layer                   │
│  ┌──────────────────────────────────────────┐  │
│  │         Tool Registration & Routing       │  │
│  └──────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────┐  │
│  │          Request/Response Handling        │  │
│  └──────────────────────────────────────────┘  │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│              Service Layer                      │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐  │
│  │  Indexer   │ │  Searcher  │ │Task Manager│  │
│  └──────┬─────┘ └──────┬─────┘ └──────┬─────┘  │
│         │              │              │         │
│  ┌──────▼──────────────▼──────────────▼──────┐ │
│  │          Repository Service                │ │
│  └──────┬─────────────────────────────────────┘ │
│         │                                       │
│  ┌──────▼─────────────────────────────────────┐ │
│  │          Embedding Service (Ollama)        │ │
│  └─────────────────────────────────────────────┘│
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│              Data Layer                         │
│  ┌──────────────────────────────────────────┐  │
│  │     PostgreSQL with pgvector              │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐  │  │
│  │  │Repository│ │   Files  │ │  Chunks  │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘  │  │
│  │  ┌──────────┐ ┌──────────────────────┐   │  │
│  │  │  Tasks   │ │  Vector Embeddings   │   │  │
│  │  └──────────┘ └──────────────────────┘   │  │
│  └──────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘
```

### Component Overview

- **MCP Layer**: Handles protocol compliance, tool registration, SSE transport
- **Service Layer**: Business logic for indexing, searching, task management
- **Repository Service**: File system operations, git integration, .gitignore handling
- **Embedding Service**: Ollama integration for generating text embeddings
- **Data Layer**: PostgreSQL with pgvector for storage and similarity search

### Data Flow

1. **Indexing**: Repository → Parse → Chunk → Embed → Store
2. **Searching**: Query → Embed → Vector Search → Rank → Return
3. **Task Tracking**: Create → Update → Git Integration → Query

## Testing

### Run All Tests

```bash
# Run all tests with coverage
pytest tests/ -v --cov=src --cov-report=term-missing

# Run specific test categories
pytest tests/unit/ -v          # Unit tests only
pytest tests/integration/ -v   # Integration tests
pytest tests/contract/ -v      # Contract tests
```

### Test Categories

- **Unit Tests**: Fast, isolated component tests
- **Integration Tests**: Database and service integration
- **Contract Tests**: MCP protocol compliance validation
- **Performance Tests**: Latency and throughput benchmarks

### Coverage Requirements

- Minimum coverage: 95%
- Critical paths: 100%
- View HTML report: `open htmlcov/index.html`

## Performance Tuning

### Database Optimization

```sql
-- Optimize vector searches
CREATE INDEX ON chunks USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Adjust work_mem for large result sets
ALTER SYSTEM SET work_mem = '256MB';
SELECT pg_reload_conf();
```

### Connection Pool Settings

```python
# In .env
DATABASE_POOL_SIZE=20        # Connection pool size
DATABASE_MAX_OVERFLOW=10     # Max overflow connections
DATABASE_POOL_TIMEOUT=30     # Connection timeout in seconds
```

### Embedding Batch Size

```python
# Adjust based on available memory
EMBEDDING_BATCH_SIZE=100     # For systems with 8GB+ RAM
EMBEDDING_BATCH_SIZE=50      # Default for 4GB RAM
EMBEDDING_BATCH_SIZE=25      # For constrained environments
```

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check PostgreSQL is running: `pg_ctl status`
   - Verify DATABASE_URL in .env
   - Ensure database exists: `psql -U postgres -l`

2. **Ollama Connection Error**
   - Check Ollama is running: `curl http://localhost:11434/api/tags`
   - Verify model is installed: `ollama list`
   - Check OLLAMA_BASE_URL in .env

3. **Slow Performance**
   - Check database indexes: `\di` in psql
   - Monitor query performance: See logs at LOG_FILE path
   - Adjust batch sizes and connection pool

For detailed troubleshooting, see [docs/troubleshooting.md](docs/troubleshooting.md) and [docs/guides/SETUP_GUIDE.md](docs/guides/SETUP_GUIDE.md).

## Contributing

We follow a specification-driven development workflow using the Specify framework.

### Development Workflow

1. **Feature Specification**: Use `/specify` command to create feature specs
2. **Planning**: Generate implementation plan with `/plan`
3. **Task Breakdown**: Create tasks with `/tasks`
4. **Implementation**: Execute tasks with `/implement`

### Git Workflow

```bash
# Create feature branch
git checkout -b 001-feature-name

# Make atomic commits
git add .
git commit -m "feat(component): add specific feature"

# Push and create PR
git push origin 001-feature-name
```

### Code Quality Standards

- **Type Safety**: `mypy --strict` must pass
- **Linting**: `ruff check` with no errors
- **Testing**: All tests must pass with 95%+ coverage
- **Documentation**: Update relevant docs with changes

### Constitutional Principles

1. **Simplicity Over Features**: Focus on core semantic search
2. **Local-First Architecture**: No cloud dependencies
3. **Protocol Compliance**: Strict MCP adherence
4. **Performance Guarantees**: Meet stated benchmarks
5. **Production Quality**: Comprehensive error handling

See [.specify/memory/constitution.md](.specify/memory/constitution.md) for full principles.

## FastMCP Migration (Oct 2025)

**Migration Complete**: The server has been successfully migrated from the legacy MCP SDK to the modern FastMCP framework.

### What Changed

**Before (MCP SDK):**
```python
# Old: Manual tool registration with JSON schemas
class MCPServer:
    def __init__(self):
        self.tools = {
            "search_code": {
                "name": "search_code",
                "description": "...",
                "inputSchema": {...}
            }
        }
```

**After (FastMCP):**
```python
# New: Decorator-based tool definitions
@mcp.tool()
async def search_code(query: str, limit: int = 10) -> dict[str, Any]:
    """Semantic code search with natural language queries."""
    # Implementation
```

### Key Benefits

1. **Simpler Tool Definitions**: Decorators replace manual JSON schema creation
2. **Type Safety**: Automatic schema generation from Pydantic models
3. **Dual Logging**: File logging + MCP protocol without stdout pollution
4. **Better Error Handling**: Structured error responses with context
5. **Cleaner Architecture**: Separation of tool interface from business logic

### Server Files

- **New Entry Point**: `server_fastmcp.py` (root directory)
- **Legacy Server**: `src/mcp/mcp_stdio_server_v3.py` (deprecated, will be removed)
- **Tool Handlers**: `src/mcp/tools/*.py` (unchanged, reused by FastMCP)
- **Services**: `src/services/*.py` (unchanged, business logic intact)

### Configuration Update Required

**Update your Claude Desktop config** to use the new server:

```json
{
  "mcpServers": {
    "codebase-mcp": {
      "command": "uv",
      "args": ["run", "--with", "fastmcp", "python", "/path/to/server_fastmcp.py"]
    }
  }
}
```

### Migration Notes

- All 6 MCP tools remain functional (100% backward compatible)
- No database schema changes required
- Tool signatures and responses unchanged
- Logging now goes exclusively to `/tmp/codebase-mcp.log`
- All tests pass with FastMCP implementation

### Performance

FastMCP maintains performance targets:
- Repository indexing: <60 seconds for 10K files
- Code search: <500ms p95 latency
- Async/await throughout for optimal concurrency

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/cliffclarke/codebase-mcp/issues)
- **Documentation**: [Full documentation](docs/)
- **Logs**: Check `/tmp/codebase-mcp.log` for detailed debugging

## Acknowledgments

- MCP framework powered by [FastMCP](https://github.com/jlowin/fastmcp)
- Built with FastAPI, SQLAlchemy, and Pydantic
- Vector search powered by [pgvector](https://github.com/pgvector/pgvector)
- Embeddings via [Ollama](https://ollama.com/) and nomic-embed-text
- Code parsing with tree-sitter
- MCP protocol by [Anthropic](https://modelcontextprotocol.io/)