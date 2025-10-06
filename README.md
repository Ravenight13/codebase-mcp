# Codebase MCP Server

A production-grade MCP (Model Context Protocol) server that indexes code repositories into PostgreSQL with pgvector for semantic search, designed specifically for AI coding assistants.

## Overview

The Codebase MCP Server provides semantic code search capabilities through a focused, local-first architecture. It enables AI assistants to understand and navigate codebases efficiently by combining tree-sitter AST parsing with vector embeddings.

### Key Features

- **Semantic Code Search**: Natural language queries across indexed repositories
- **Repository Indexing**: Fast scanning and chunking with tree-sitter parsers
- **Task Management**: Development task tracking with git integration
- **MCP Protocol**: Six focused tools via Server-Sent Events (SSE)
- **Performance Guaranteed**: 60-second indexing for 10K files, 500ms p95 search latency
- **Production Ready**: Comprehensive error handling, structured logging, type safety

### MCP Tools

1. **search_code**: Semantic search across indexed code
2. **index_repository**: Index a repository for searching
3. **get_task**: Retrieve a specific development task
4. **list_tasks**: List tasks with filtering options
5. **create_task**: Create a new development task
6. **update_task**: Update task status with git integration

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
# Install production dependencies
pip install -r requirements.txt

# For development (includes testing and linting tools)
pip install -r requirements-dev.txt
```

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
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

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

## Running the Server

### Development Mode

```bash
# Start with auto-reload
uvicorn src.main:app --reload --host 127.0.0.1 --port 3000

# With custom log level
LOG_LEVEL=DEBUG uvicorn src.main:app --reload
```

### Production Mode

```bash
# Start production server
uvicorn src.main:app --host 0.0.0.0 --port 3000 --workers 4

# With gunicorn (recommended for production)
gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:3000
```

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

For detailed troubleshooting, see [docs/troubleshooting.md](docs/troubleshooting.md).

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

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/cliffclarke/codebase-mcp/issues)
- **Documentation**: [Full documentation](docs/)
- **Logs**: Check `/tmp/codebase-mcp.log` for detailed debugging

## Acknowledgments

- Built with FastAPI, SQLAlchemy, and Pydantic
- Vector search powered by pgvector
- Embeddings via Ollama and nomic-embed-text
- Code parsing with tree-sitter