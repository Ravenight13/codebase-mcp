# Technical Research: Production-Grade MCP Server

**Feature**: Production-Grade MCP Server for Semantic Code Search
**Date**: 2025-10-06
**Research Phase**: Phase 0 - Technology decisions and best practices

## 1. MCP SDK Python SSE Transport

### Decision
Use `mcp` Python SDK with SSE (Server-Sent Events) transport for protocol compliance.

### Rationale
- **Protocol Compliance**: MCP specification requires SSE transport for streaming responses
- **No stdout/stderr pollution**: SSE uses HTTP response stream, keeping stdout clean
- **Tool Registration**: SDK provides decorators for tool definition with automatic schema generation
- **Type Safety**: Integrates with Pydantic for request/response validation

### Implementation Approach
```python
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent

# Server setup with SSE transport
server = Server("codebase-mcp")
transport = SseServerTransport("/messages")

# Tool registration with schema
@server.tool()
async def search_code(query: str, filters: Optional[dict] = None) -> list[dict]:
    """Semantic code search with optional filters"""
    # Implementation
```

### Alternatives Considered
- **stdio transport**: Rejected - pollutes stdout/stderr, breaks protocol compliance
- **Custom SSE implementation**: Rejected - SDK provides battle-tested implementation
- **WebSocket transport**: Rejected - not in MCP specification

### Key Considerations
- Log to `/tmp/codebase-mcp.log` exclusively (file-based structured logging)
- Never use `print()` or write to stdout/stderr
- Use SDK's error handling for protocol-compliant error responses
- Tool schemas auto-generate from type hints

---

## 2. Tree-sitter for Multi-Language Parsing

### Decision
Use Tree-sitter with dynamic language grammar loading for AST-based code chunking.

### Rationale
- **Language-Agnostic**: Supports 40+ languages with consistent API
- **AST Accuracy**: Proper syntax tree vs regex heuristics
- **Chunk Boundaries**: Detect function/class boundaries for semantic chunking
- **Performance**: Incremental parsing for file updates

### Implementation Approach
```python
from tree_sitter import Language, Parser
import tree_sitter_python
import tree_sitter_javascript
# ... dynamic language loading

# Detect language, load grammar, parse
def chunk_code(file_path: str, content: str) -> list[CodeChunk]:
    lang = detect_language(file_path)  # by extension
    parser = get_parser(lang)
    tree = parser.parse(bytes(content, "utf8"))

    # Extract function/class nodes as chunks
    chunks = []
    for node in tree.root_node.children:
        if node.type in ['function_definition', 'class_definition']:
            chunks.append(CodeChunk(
                content=content[node.start_byte:node.end_byte],
                start_line=node.start_point[0],
                end_line=node.end_point[0],
                type=node.type
            ))
    return chunks
```

### Alternatives Considered
- **Regex-based chunking**: Rejected - fragile, language-specific patterns
- **Line-based splitting**: Rejected - breaks semantic boundaries
- **LibCST (Python only)**: Rejected - not language-agnostic

### Key Considerations
- Fallback to line-based chunking for unsupported languages
- Cache parsed ASTs for incremental updates
- Target chunk size: 100-500 lines for embedding quality
- Handle parse errors gracefully (malformed code)

---

## 3. PostgreSQL pgvector Extension

### Decision
Use pgvector with HNSW indexing and cosine distance for vector similarity search.

### Rationale
- **HNSW Performance**: Hierarchical NSW gives <500ms search on 10K vectors
- **Cosine Distance**: Better for normalized embeddings (nomic-embed-text outputs unit vectors)
- **PostgreSQL Integration**: Native SQL queries, ACID transactions
- **Scalability**: Handles 1M+ vectors with proper indexing

### Implementation Approach
```sql
-- Install pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Code chunks table with vector column
CREATE TABLE code_chunks (
    id UUID PRIMARY KEY,
    file_id UUID REFERENCES code_files(id),
    content TEXT NOT NULL,
    start_line INT,
    end_line INT,
    embedding vector(768),  -- nomic-embed-text dimension
    created_at TIMESTAMP DEFAULT NOW()
);

-- HNSW index for fast similarity search
CREATE INDEX ON code_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Similarity search query
SELECT content, 1 - (embedding <=> query_vector) AS similarity
FROM code_chunks
WHERE 1 - (embedding <=> query_vector) > 0.7  -- threshold
ORDER BY embedding <=> query_vector
LIMIT 10;
```

### Alternatives Considered
- **IVFFlat indexing**: Rejected - slower recall than HNSW for our scale
- **L2 distance**: Rejected - cosine better for unit-normalized embeddings
- **Separate vector DB (Qdrant, Weaviate)**: Rejected - adds complexity, violates local-first

### Key Considerations
- Index parameters: `m=16` (neighbors), `ef_construction=64` (build quality)
- Query parameters: `ef_search=40` for <500ms with good recall
- Batch inserts for initial indexing (60s target)
- Vacuum regularly to maintain index performance

---

## 4. Ollama HTTP API Integration

### Decision
Use Ollama HTTP API directly with `httpx` async client for embedding generation.

### Rationale
- **Simplicity**: Direct HTTP calls vs SDK abstraction
- **Batch Support**: Generate embeddings for multiple chunks in single request
- **Error Handling**: Explicit control over retry logic, timeouts
- **Local-First**: Ollama runs locally, no cloud dependencies

### Implementation Approach
```python
import httpx
from pydantic import BaseModel

class EmbeddingRequest(BaseModel):
    model: str = "nomic-embed-text"
    prompt: str

class EmbeddingResponse(BaseModel):
    embedding: list[float]

async def generate_embeddings(texts: list[str]) -> list[list[float]]:
    async with httpx.AsyncClient() as client:
        tasks = []
        for text in texts:
            req = EmbeddingRequest(prompt=text)
            tasks.append(
                client.post(
                    "http://localhost:11434/api/embeddings",
                    json=req.dict(),
                    timeout=30.0
                )
            )
        responses = await asyncio.gather(*tasks)
        return [EmbeddingResponse(**r.json()).embedding for r in responses]
```

### Alternatives Considered
- **Ollama Python SDK**: Rejected - adds dependency, less control
- **OpenAI embeddings**: Rejected - violates local-first, costs money
- **Sentence-transformers**: Rejected - Ollama already provides optimized inference

### Key Considerations
- Batch size: 50-100 texts per request for 60s indexing target
- Timeout: 30s per request (large batches)
- Retry logic: 3 attempts with exponential backoff
- Model validation: Check `nomic-embed-text` availability on startup

---

## 5. Async SQLAlchemy Patterns

### Decision
Use SQLAlchemy 2.0+ with AsyncPG driver and async sessionmaker.

### Rationale
- **Async Operations**: Non-blocking DB queries for <500ms search latency
- **Type Safety**: Full type hints with mypy support
- **ORM Benefits**: Relationship management, migration support
- **Connection Pooling**: Efficient concurrent query handling

### Implementation Approach
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator

# Engine setup
engine = create_async_engine(
    "postgresql+asyncpg://user:pass@localhost/codebase_mcp",
    echo=False,
    pool_size=20,
    max_overflow=10
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Dependency injection
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

# Usage in services
async def search_code(db: AsyncSession, query_vector: list[float]):
    result = await db.execute(
        select(CodeChunk)
        .order_by(CodeChunk.embedding.cosine_distance(query_vector))
        .limit(10)
    )
    return result.scalars().all()
```

### Alternatives Considered
- **Sync SQLAlchemy**: Rejected - blocks event loop, poor concurrency
- **asyncpg directly**: Rejected - lose ORM benefits, more boilerplate
- **Tortoise ORM**: Rejected - less mature, weaker type support

### Key Considerations
- Connection pool: 20 connections for 10 concurrent AI assistants
- Session management: FastAPI dependency injection
- Transaction isolation: SERIALIZABLE for task updates
- Migration tool: Alembic with async support

---

## 6. File Change Detection

### Decision
Use filesystem timestamp comparison (polling) over event-based watching for cross-platform reliability.

### Rationale
- **Simplicity**: Check `mtime` on scan, compare with DB state
- **Reliability**: No missed events, works on all platforms
- **Performance**: Acceptable for incremental updates (10K files in <5s)
- **No Dependencies**: Built-in `pathlib` and `os.stat`

### Implementation Approach
```python
from pathlib import Path
from datetime import datetime

async def detect_changes(repo_path: Path, db: AsyncSession) -> ChangeSet:
    changes = ChangeSet(added=[], modified=[], deleted=[])

    # Get current filesystem state
    current_files = {
        f: f.stat().st_mtime
        for f in repo_path.rglob("*")
        if f.is_file() and not is_ignored(f)
    }

    # Get DB state
    db_files = await db.execute(
        select(CodeFile.path, CodeFile.modified_at)
    )
    db_state = {Path(p): m.timestamp() for p, m in db_files}

    # Compare
    for file_path, mtime in current_files.items():
        if file_path not in db_state:
            changes.added.append(file_path)
        elif mtime > db_state[file_path]:
            changes.modified.append(file_path)

    changes.deleted = set(db_state.keys()) - set(current_files.keys())
    return changes
```

### Alternatives Considered
- **Watchdog (inotify/FSEvents)**: Rejected - complex, platform-specific bugs, can miss events during downtime
- **Git diff tracking**: Rejected - requires git repo, doesn't handle uncommitted changes

### Key Considerations
- Run change detection on: server startup, manual trigger, scheduled interval
- Ignore patterns: Load .gitignore and .mcpignore
- Deleted file retention: Mark deleted, cleanup after 90 days
- Performance: Parallel stat() calls for large repos

---

## 7. Pydantic Settings Management

### Decision
Use `pydantic-settings` BaseSettings with environment variable parsing and .env file support.

### Rationale
- **Validation**: Type-checked config with custom validators
- **Environment Variables**: Auto-parse from env with type coercion
- **.env Support**: Development-friendly local config
- **Fail-Fast**: Config errors on startup, not runtime

### Implementation Approach
```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, PostgresDsn

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    # Database
    database_url: PostgresDsn = Field(
        ...,
        description="PostgreSQL connection string with asyncpg driver"
    )

    # Ollama
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama API base URL"
    )
    ollama_embedding_model: str = Field(
        default="nomic-embed-text",
        description="Embedding model name"
    )

    # Performance
    embedding_batch_size: int = Field(
        default=50,
        ge=1,
        le=1000,
        description="Texts per embedding request"
    )

    max_concurrent_requests: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Concurrent AI assistant limit"
    )

    @field_validator("database_url")
    @classmethod
    def validate_asyncpg_driver(cls, v: PostgresDsn) -> PostgresDsn:
        if v.scheme != "postgresql+asyncpg":
            raise ValueError("Must use asyncpg driver")
        return v

# Singleton instance
settings = Settings()
```

### Alternatives Considered
- **python-decouple**: Rejected - less feature-rich than pydantic-settings
- **dynaconf**: Rejected - overkill for simple config
- **ConfigParser**: Rejected - no validation, manual type coercion

### Key Considerations
- Required vs optional: Use `Field(...)` for required, `Field(default=...)` for optional
- Validation: Custom validators for complex rules (URL formats, ranges)
- Documentation: Field descriptions auto-generate docs
- Testing: Override settings with environment variables in tests

---

## 8. Performance Profiling Strategy

### Decision
Use `asyncio` profiling, SQL query logging, and custom metrics to identify bottlenecks for 60s indexing and 500ms search targets.

### Rationale
- **Indexing Bottleneck**: Likely embedding generation (Ollama API calls)
- **Search Bottleneck**: Likely vector similarity computation (pgvector index quality)
- **Profiling Tools**: `cProfile` for CPU, `py-spy` for sampling, custom timing for async

### Implementation Approach
```python
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

@asynccontextmanager
async def timed_operation(operation: str) -> AsyncGenerator[None, None]:
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        logger.info(f"{operation} took {elapsed:.2f}s")

# Usage
async def index_repository(repo_path: Path):
    async with timed_operation("File scanning"):
        files = await scan_files(repo_path)

    async with timed_operation("Embedding generation"):
        embeddings = await generate_embeddings(files)

    async with timed_operation("Database insertion"):
        await bulk_insert_embeddings(db, embeddings)
```

### Optimization Targets
1. **Indexing (<60s for 10K files)**:
   - Parallelize file scanning (async I/O)
   - Batch embedding generation (50-100 per request)
   - Bulk database inserts (1000 rows per transaction)
   - Skip unchanged files (incremental updates)

2. **Search (<500ms p95)**:
   - HNSW index tuning (`m`, `ef_construction`)
   - Query-time `ef_search` parameter
   - Result limit (top 10 results)
   - Connection pooling (reduce handshake overhead)

### Alternatives Considered
- **Line profiler**: Rejected - overhead too high for async code
- **Memory profiler**: Rejected - not primary bottleneck

### Key Considerations
- Benchmark on realistic data (10K files, varied languages)
- Measure p50, p95, p99 latencies (not just average)
- Profile in production-like environment (not debug mode)
- Log slow operations for post-mortem analysis

---

## Summary

All research tasks complete. Key technical decisions:

1. ✅ **MCP SDK Python SSE** - Protocol compliance with file logging
2. ✅ **Tree-sitter** - AST-based chunking, language-agnostic
3. ✅ **pgvector HNSW** - Fast similarity search with cosine distance
4. ✅ **Ollama HTTP API** - Direct async calls, batch embeddings
5. ✅ **Async SQLAlchemy** - Non-blocking queries, type-safe ORM
6. ✅ **Timestamp-based change detection** - Simple, reliable, cross-platform
7. ✅ **Pydantic Settings** - Validated config, fail-fast startup
8. ✅ **Performance profiling** - Targeted optimization for 60s/500ms targets

No remaining NEEDS CLARIFICATION blockers. Ready for Phase 1: Design & Contracts.
