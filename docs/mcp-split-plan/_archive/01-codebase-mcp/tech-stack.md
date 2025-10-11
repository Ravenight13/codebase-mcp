# Technical Stack for Codebase MCP Server

## Overview

The Codebase MCP Server uses a carefully selected technology stack optimized for semantic code search with local-first architecture, high performance, and production-grade quality. This stack is **NON-NEGOTIABLE** and enforced by Constitutional Principle XI.

---

## Core Technologies

### Python 3.11+

**Purpose**: Primary programming language for all server logic

**Justification**:
- **Async/Await**: Native support for asynchronous I/O (critical for performance)
- **Type Hints**: Full PEP 484 support with generics, protocols, and type guards
- **Match Statements**: Cleaner pattern matching for error handling
- **Performance**: 3.11+ has significant speed improvements over 3.10
- **Ecosystem**: Rich ML/AI libraries (tree-sitter, numpy, etc.)

**Key Features Used**:
- `async def` functions throughout (no blocking I/O)
- Type hints on all functions, classes, and module-level variables
- `match` statements for protocol message handling
- Structural pattern matching for error categorization

**Version Constraint**: `>=3.11,<4.0` (Python 3.11 or 3.12, not 3.13 until stable)

---

### PostgreSQL 14+ with pgvector

**Purpose**: Primary database for code chunks, embeddings, and metadata

**Justification**:
- **pgvector Extension**: Native vector similarity search with cosine distance
- **HNSW Indexes**: Approximate nearest neighbor search (scales to millions of vectors)
- **ACID Compliance**: Transactional safety for indexing operations
- **JSON Support**: JSONB columns for flexible metadata storage
- **Mature Ecosystem**: Battle-tested, well-documented, strong community

**Key Features Used**:
- `vector(768)` columns for nomic-embed-text embeddings
- HNSW indexes: `CREATE INDEX ON code_chunks USING hnsw (embedding vector_cosine_ops)`
- JSONB columns for chunk metadata (language, symbols, etc.)
- Transactional indexing (BEGIN/COMMIT for batch inserts)
- Connection pooling via AsyncPG

**Version Constraint**: `>=14.0` (pgvector requires PostgreSQL 11+, recommend 14+ for performance)

**Extensions Required**:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- For text search fallback
```

---

### pgvector Extension

**Purpose**: Vector similarity search within PostgreSQL

**Justification**:
- **In-Database Search**: No external vector store (Pinecone, Weaviate, etc.)
- **Cosine Similarity**: `<=>` operator for efficient similarity queries
- **Index Support**: HNSW and IVFFlat indexes for fast approximate search
- **SQL Integration**: Standard SQL queries, no custom query language

**Key Operations**:
```sql
-- Similarity search (cosine distance)
SELECT file_path, content, 1 - (embedding <=> query_embedding) AS similarity
FROM code_chunks
WHERE project_id = $1
ORDER BY embedding <=> query_embedding
LIMIT 10;

-- HNSW index for scaling (approximate nearest neighbor)
CREATE INDEX code_chunks_embedding_idx
ON code_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

**Version Constraint**: `>=0.5.0` (latest stable version)

---

### Ollama with nomic-embed-text

**Purpose**: Local embedding generation for code and queries

**Justification**:
- **Local-First**: Runs on localhost, no API keys, no cloud dependencies
- **Offline Capable**: Works without internet after initial model download
- **Free**: No per-token costs, unlimited usage
- **Privacy**: Code never leaves local machine
- **Fast**: Sub-200ms for single query embedding (GPU optional)

**Model: nomic-embed-text**
- **Dimensions**: 768 (balanced size/performance)
- **Context Length**: 8192 tokens (handles large code chunks)
- **Performance**: Competitive with OpenAI ada-002 on code search tasks
- **License**: Open source (Apache 2.0)

**API Interaction**:
```python
# Generate embedding via Ollama HTTP API
import aiohttp

async def generate_embedding(text: str) -> list[float]:
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:11434/api/embeddings",
            json={"model": "nomic-embed-text", "prompt": text}
        ) as response:
            data = await response.json()
            return data["embedding"]  # 768-dimensional vector
```

**Version Constraint**: Ollama `>=0.1.0`, nomic-embed-text model (pulled via `ollama pull nomic-embed-text`)

---

### FastMCP Framework

**Purpose**: MCP server implementation with ergonomic abstractions

**Justification**:
- **Official Support**: Built by Anthropic team, guaranteed protocol compliance
- **Ergonomic API**: Decorator-based tool registration (`@mcp.tool()`)
- **Type Safety**: Pydantic integration for parameter schemas
- **SSE Transport**: Built-in Server-Sent Events support (no stdout pollution)
- **Error Handling**: Structured MCP error responses

**Key Features Used**:
```python
from fastmcp import FastMCP
from pydantic import BaseModel, Field

mcp = FastMCP("codebase-mcp")

class SearchParams(BaseModel):
    query: str = Field(description="Natural language search query")
    project_id: str | None = Field(default=None, description="Project ID")
    limit: int = Field(default=10, ge=1, le=50)

@mcp.tool()
async def search_code(params: SearchParams) -> dict:
    """Search code using semantic similarity"""
    # Implementation
    return {"results": [...], "latency_ms": 250}
```

**Version Constraint**: `>=0.1.0` (track official releases)

---

### MCP Python SDK

**Purpose**: Model Context Protocol types and utilities

**Justification**:
- **Protocol Types**: Official type definitions for MCP messages
- **Validation**: Message validation utilities
- **Compatibility**: Ensures compatibility with all MCP clients

**Key Types Used**:
- `Tool`: Tool definition with schema
- `TextContent`: Text response content
- `ImageContent`: Image response content (not used in codebase-mcp)
- `ErrorCode`: Standard error codes (InvalidParams, InternalError, etc.)

**Version Constraint**: `>=0.1.0` (track official releases)

---

### AsyncPG

**Purpose**: Asynchronous PostgreSQL driver

**Justification**:
- **Native Async**: Built from ground up for asyncio (not sync wrapper)
- **Performance**: Fastest Python PostgreSQL driver (C-based protocol implementation)
- **Type Safety**: Strong typing with stubs for mypy
- **Connection Pooling**: Built-in pool with efficient resource management
- **Transaction Support**: Async context managers for transactions

**Key Features Used**:
```python
import asyncpg

# Connection pool
pool = await asyncpg.create_pool(
    host="localhost",
    port=5432,
    database=f"project_{project_id}",
    min_size=5,
    max_size=20
)

# Query with parameters (SQL injection safe)
async with pool.acquire() as conn:
    results = await conn.fetch(
        "SELECT * FROM code_chunks WHERE project_id = $1 ORDER BY embedding <=> $2 LIMIT $3",
        project_id, query_embedding, limit
    )
```

**Version Constraint**: `>=0.29.0` (latest stable version)

---

### Tree-sitter

**Purpose**: AST-aware code chunking for indexing

**Justification**:
- **Syntax-Aware**: Chunks respect code structure (functions, classes, not arbitrary lines)
- **Multi-Language**: 50+ language parsers available
- **Fast**: Incremental parsing, optimized for performance
- **Accurate**: Parses real-world code (tolerates syntax errors)

**Languages Supported**:
- Python, JavaScript, TypeScript, Rust, Go, Java, C, C++, C#, Ruby, PHP, etc.

**Key Operations**:
```python
from tree_sitter import Parser, Language

# Load language grammar
PY_LANGUAGE = Language("build/languages.so", "python")
parser = Parser()
parser.set_language(PY_LANGUAGE)

# Parse code
tree = parser.parse(bytes(source_code, "utf8"))

# Extract function definitions
for node in tree.root_node.children:
    if node.type == "function_definition":
        chunk = source_code[node.start_byte:node.end_byte]
        # Index this chunk
```

**Version Constraint**: `>=0.20.0` (stable API)

---

### Pydantic 2.x

**Purpose**: Data validation and type-safe models

**Justification**:
- **Runtime Validation**: Catch invalid data at API boundaries
- **Type Safety**: Full mypy integration with type hints
- **Performance**: 2.x is 5-20x faster than 1.x (Rust core)
- **JSON Schema**: Automatic schema generation for MCP tools
- **Coercion**: Automatic type coercion (str → int, etc.)

**Key Features Used**:
```python
from pydantic import BaseModel, Field, validator

class CodeChunk(BaseModel):
    file_path: str
    content: str = Field(min_length=1, max_length=10000)
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    embedding: list[float] = Field(min_length=768, max_length=768)

    @validator("end_line")
    def validate_line_order(cls, v, values):
        if "start_line" in values and v < values["start_line"]:
            raise ValueError("end_line must be >= start_line")
        return v
```

**Version Constraint**: `>=2.0,<3.0` (Pydantic 2.x only, breaking changes from 1.x)

---

### mypy

**Purpose**: Static type checking

**Justification**:
- **Catch Bugs Early**: Type errors found before runtime
- **Self-Documenting**: Type hints serve as inline documentation
- **Refactoring Safety**: Type checker validates refactorings
- **IDE Support**: Better autocomplete and inline errors

**Configuration** (`mypy.ini`):
```ini
[mypy]
python_version = 3.11
strict = True
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
disallow_any_generics = True
disallow_subclassing_any = True
disallow_untyped_calls = True
disallow_incomplete_defs = True
check_untyped_defs = True
disallow_untyped_decorators = True
no_implicit_optional = True
warn_redundant_casts = True
warn_unused_ignores = True
warn_no_return = True
warn_unreachable = True
strict_equality = True
```

**Version Constraint**: `>=1.7.0` (latest stable with 3.11 support)

---

### pytest with pytest-asyncio

**Purpose**: Testing framework

**Justification**:
- **Async Support**: pytest-asyncio for testing async functions
- **Fixtures**: Dependency injection for database, Ollama mocks
- **Parametrization**: Test same logic with multiple inputs
- **Coverage**: Integration with pytest-cov for coverage reports
- **Plugins**: Rich ecosystem (pytest-timeout, pytest-xdist, etc.)

**Key Features Used**:
```python
import pytest
import pytest_asyncio

@pytest_asyncio.fixture
async def db_pool():
    pool = await asyncpg.create_pool(...)
    yield pool
    await pool.close()

@pytest.mark.asyncio
async def test_search_code(db_pool):
    result = await search_code(query="authentication", project_id="test")
    assert len(result["results"]) > 0
    assert result["latency_ms"] < 500
```

**Version Constraint**: `pytest>=7.4.0`, `pytest-asyncio>=0.21.0`

---

## Supporting Libraries

### aiohttp

**Purpose**: Async HTTP client for Ollama API

**Justification**:
- **Async Native**: Built for asyncio, no thread pools
- **Client Sessions**: Efficient connection reuse
- **Streaming**: Supports streaming responses (not needed for embeddings)

**Version Constraint**: `>=3.9.0`

---

### numpy

**Purpose**: Array operations for embeddings (optional, for future optimizations)

**Justification**:
- **Vectorized Operations**: Fast cosine similarity in Python (before database)
- **Memory Efficiency**: Efficient storage for large embedding batches

**Version Constraint**: `>=1.24.0` (optional dependency)

---

## Development Tools

### black

**Purpose**: Code formatter

**Justification**: Consistent formatting, no bikeshedding

**Version Constraint**: `>=23.0.0`

---

### ruff

**Purpose**: Linter (replaces flake8, isort, pylint)

**Justification**: Fast (100x faster than flake8), comprehensive

**Version Constraint**: `>=0.1.0`

---

### pre-commit

**Purpose**: Git hooks for quality checks

**Justification**: Enforce quality before commits (black, ruff, mypy, tests)

**Version Constraint**: `>=3.5.0`

---

## Infrastructure

### Docker (Optional)

**Purpose**: Containerized PostgreSQL for local development

**Justification**: Consistent development environment, easy setup

**Example** (`docker-compose.yml`):
```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_PASSWORD: dev
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

---

## Dependency Management

### requirements.txt

**Production Dependencies**:
```
# Core
fastmcp>=0.1.0
mcp>=0.1.0
asyncpg>=0.29.0
pydantic>=2.0,<3.0
aiohttp>=3.9.0

# Code Processing
tree-sitter>=0.20.0

# Vector Search (via PostgreSQL)
# pgvector extension installed separately

# Utilities
python-dotenv>=1.0.0  # Config management
structlog>=23.2.0     # Structured logging
```

**Development Dependencies**:
```
# Type Checking
mypy>=1.7.0

# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
pytest-timeout>=2.2.0

# Code Quality
black>=23.0.0
ruff>=0.1.0
pre-commit>=3.5.0

# Database
alembic>=1.13.0  # Schema migrations
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│  Python 3.11+ (async/await, type hints)             │
│  ┌───────────────────────────────────────────────┐  │
│  │  FastMCP + MCP Python SDK (SSE transport)     │  │
│  │  ┌─────────────────────────────────────────┐  │  │
│  │  │  Pydantic Models (validation)           │  │  │
│  │  │  ┌───────────────────────────────────┐  │  │  │
│  │  │  │  AsyncPG (database I/O)           │  │  │  │
│  │  │  │  aiohttp (Ollama API)             │  │  │  │
│  │  │  │  tree-sitter (code parsing)       │  │  │  │
│  │  │  └───────────────────────────────────┘  │  │  │
│  │  └─────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                    │           │
        ┌───────────┘           └───────────┐
        ▼                                   ▼
┌──────────────────┐              ┌──────────────────┐
│  PostgreSQL 14+  │              │  Ollama          │
│  + pgvector      │              │  (nomic-embed)   │
│  (vector search) │              │  (embeddings)    │
└──────────────────┘              └──────────────────┘
```

---

## Why This Stack?

### Local-First Architecture
- **Ollama**: No cloud APIs, works offline
- **PostgreSQL**: Local or local network, no managed services
- **No External Dependencies**: All code runs on developer machine

### Performance
- **AsyncPG**: Fastest Python PostgreSQL driver
- **HNSW Indexes**: Sub-500ms search on 250k chunks
- **Async I/O**: Non-blocking, efficient concurrency

### Type Safety
- **Pydantic**: Runtime validation
- **mypy --strict**: Static type checking
- **Full Type Hints**: Self-documenting code

### Production Quality
- **PostgreSQL ACID**: Transactional safety
- **Error Handling**: Structured logging, graceful degradation
- **Testing**: pytest + pytest-asyncio, >80% coverage

### Developer Experience
- **FastMCP**: Ergonomic API, minimal boilerplate
- **Tree-sitter**: Language-aware chunking
- **Docker**: Easy local setup (optional)

---

## Non-Negotiable Constraints

This stack is enforced by Constitutional Principle XI. Deviations require:

1. Constitutional amendment (version bump)
2. Documented rationale (why deviation needed)
3. Migration plan (how to transition)
4. Approval from project maintainers

**Examples of Forbidden Alternatives**:
- ❌ OpenAI embeddings (violates Local-First)
- ❌ SQLite (no pgvector support)
- ❌ psycopg2 (blocking I/O, not async)
- ❌ Raw JSON-RPC (bypasses FastMCP framework)
- ❌ Python 3.10 or earlier (missing language features)
