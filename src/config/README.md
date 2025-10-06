# Configuration Module

Production-grade Pydantic settings configuration for the Codebase MCP Server.

## Overview

The `settings` module provides type-safe, validated configuration management using `pydantic-settings`. All configuration is loaded from environment variables with `.env` file support.

**Constitutional Compliance:**
- ✅ Principle V: Production quality with fail-fast validation
- ✅ Principle VIII: Type safety with Pydantic 2.0+, mypy --strict compliance

## Quick Start

### 1. Create `.env` file

```bash
cp .env.example .env
```

### 2. Edit configuration values

```bash
# .env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/codebase_mcp
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_BATCH_SIZE=50
MAX_CONCURRENT_REQUESTS=10
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
LOG_LEVEL=INFO
LOG_FILE=/tmp/codebase-mcp.log
```

### 3. Use in application code

```python
from src.config import settings

# Access configuration values
db_url = settings.database_url
batch_size = settings.embedding_batch_size
log_level = settings.log_level
```

## Configuration Fields

### Database Configuration

#### `DATABASE_URL` (required)
- **Type**: PostgreSQL DSN with asyncpg driver
- **Format**: `postgresql+asyncpg://user:password@host:port/database`
- **Validation**: Must use `asyncpg` driver for async SQLAlchemy
- **Example**: `postgresql+asyncpg://admin:secret@localhost:5432/codebase_mcp`

#### `DB_POOL_SIZE` (optional)
- **Type**: Integer
- **Default**: `20`
- **Range**: `5-50`
- **Description**: SQLAlchemy connection pool size
- **Recommendation**: Set to match `MAX_CONCURRENT_REQUESTS` for optimal resource usage

#### `DB_MAX_OVERFLOW` (optional)
- **Type**: Integer
- **Default**: `10`
- **Range**: `0-20`
- **Description**: Maximum overflow connections beyond pool size
- **Use Case**: Handle traffic spikes without exhausting connections

### Ollama Configuration

#### `OLLAMA_BASE_URL` (optional)
- **Type**: HTTP URL
- **Default**: `http://localhost:11434`
- **Validation**: Must be valid HTTP/HTTPS URL
- **Description**: Ollama API base URL for embedding generation
- **Example**: `http://ollama.example.com:11434`

#### `OLLAMA_EMBEDDING_MODEL` (optional)
- **Type**: String
- **Default**: `nomic-embed-text`
- **Description**: Ollama model name for embeddings
- **Recommendation**: Use `nomic-embed-text` (768 dimensions) for best results
- **Note**: Model must be pulled locally: `ollama pull nomic-embed-text`

### Performance Tuning

#### `EMBEDDING_BATCH_SIZE` (optional)
- **Type**: Integer
- **Default**: `50`
- **Range**: `1-1000`
- **Description**: Number of text chunks to embed per Ollama API request
- **Performance Impact**:
  - **Smaller batches** (10-30): Lower latency, more API calls
  - **Larger batches** (50-100): Higher throughput, better for bulk indexing
- **Recommendation**: `50-100` for optimal indexing performance

#### `MAX_CONCURRENT_REQUESTS` (optional)
- **Type**: Integer
- **Default**: `10`
- **Range**: `1-100`
- **Description**: Maximum concurrent AI assistant connections
- **Resource Impact**: Each connection consumes 1 database connection
- **Recommendation**: Match to expected concurrent users

### Logging Configuration

#### `LOG_LEVEL` (optional)
- **Type**: Enum
- **Default**: `INFO`
- **Valid Values**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Description**: Logging verbosity level
- **Development**: Use `DEBUG` for detailed tracing
- **Production**: Use `INFO` or `WARNING`

#### `LOG_FILE` (optional)
- **Type**: String (file path)
- **Default**: `/tmp/codebase-mcp.log`
- **Description**: File path for structured JSON logs
- **CRITICAL**: Never log to stdout/stderr (violates MCP protocol)
- **Production**: Use persistent path like `/var/log/codebase-mcp.log`

## Validation & Error Handling

### Automatic Validation

Settings are validated on server startup using Pydantic validators. Invalid configuration halts startup with actionable error messages.

```python
# Invalid database URL (wrong driver)
DATABASE_URL=postgresql://user:password@localhost:5432/db

# Error message:
# ValidationError: DATABASE_URL must use asyncpg driver for async operations.
# Found: postgresql
# Expected: postgresql+asyncpg
#
# Fix: Update .env file:
#   DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/codebase_mcp
```

### Validation Rules

1. **Database URL**:
   - Must use `postgresql+asyncpg://` scheme
   - Must be valid PostgreSQL connection string

2. **Numeric Ranges**:
   - `EMBEDDING_BATCH_SIZE`: 1-1000
   - `MAX_CONCURRENT_REQUESTS`: 1-100
   - `DB_POOL_SIZE`: 5-50
   - `DB_MAX_OVERFLOW`: 0-20

3. **URLs**:
   - `OLLAMA_BASE_URL`: Must be valid HTTP/HTTPS URL

4. **Enums**:
   - `LOG_LEVEL`: Must be valid log level name

### Performance Warnings

Small batch sizes trigger performance warnings:

```python
EMBEDDING_BATCH_SIZE=5

# Warning: EMBEDDING_BATCH_SIZE=5 is very small and may impact indexing performance.
# Recommended: 50-100 for optimal throughput.
```

## Usage Patterns

### Basic Usage

```python
from src.config import settings

# Database connection
engine = create_async_engine(
    str(settings.database_url),
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow
)

# Ollama client
ollama_client = httpx.AsyncClient(
    base_url=str(settings.ollama_base_url),
    timeout=30.0
)

# Logging
logging.basicConfig(
    filename=settings.log_file,
    level=settings.log_level.value
)
```

### Testing with Custom Settings

```python
import pytest
from src.config.settings import Settings

@pytest.fixture
def test_settings(monkeypatch):
    """Override settings for testing."""
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://test:test@localhost:5432/test_db"
    )
    monkeypatch.setenv("EMBEDDING_BATCH_SIZE", "10")

    return Settings()

def test_with_custom_config(test_settings):
    assert test_settings.embedding_batch_size == 10
```

### Environment-Specific Configuration

```bash
# Development (.env.development)
DATABASE_URL=postgresql+asyncpg://dev:dev@localhost:5432/codebase_mcp_dev
LOG_LEVEL=DEBUG

# Production (.env.production)
DATABASE_URL=postgresql+asyncpg://prod:secret@db.example.com:5432/codebase_mcp
LOG_LEVEL=WARNING
LOG_FILE=/var/log/codebase-mcp/app.log
DB_POOL_SIZE=30
MAX_CONCURRENT_REQUESTS=50
```

## Type Safety

All settings are fully typed with mypy --strict compliance:

```python
from src.config import settings

# Type-checked access
db_url: PostgresDsn = settings.database_url
batch_size: int = settings.embedding_batch_size
log_level: LogLevel = settings.log_level

# Autocomplete support in IDEs
settings.ollama_  # → ollama_base_url, ollama_embedding_model
```

## Singleton Pattern

Settings use lazy-loaded singleton pattern for consistency:

```python
from src.config import settings, get_settings

# Both return same instance
settings1 = settings
settings2 = get_settings()

assert settings1 is settings2  # True
```

## Best Practices

### 1. Required vs Optional Fields

- **Always set `DATABASE_URL`**: Required for server startup
- **Use defaults for local development**: Ollama at localhost:11434
- **Customize for production**: Set all performance parameters

### 2. Security

- **Never commit `.env` file**: Add to `.gitignore`
- **Use environment variables in production**: Cloud provider secrets management
- **Rotate database credentials**: Don't hardcode in config

### 3. Performance Tuning

- **Match pool size to concurrency**: `DB_POOL_SIZE` ≈ `MAX_CONCURRENT_REQUESTS`
- **Optimize batch size**: Larger for bulk indexing (100), smaller for real-time (30)
- **Monitor resource usage**: Adjust based on actual load

### 4. Logging

- **Development**: `LOG_LEVEL=DEBUG`, `LOG_FILE=/tmp/codebase-mcp.log`
- **Production**: `LOG_LEVEL=INFO`, persistent log path
- **NEVER use stdout/stderr**: MCP protocol violation

## Troubleshooting

### Common Errors

#### Missing DATABASE_URL

```
ValidationError: 1 validation error for Settings
database_url
  Field required
```

**Fix**: Set `DATABASE_URL` in `.env` or environment

#### Wrong Database Driver

```
ValidationError: DATABASE_URL must use asyncpg driver for async operations.
Found: postgresql
Expected: postgresql+asyncpg
```

**Fix**: Change `postgresql://` to `postgresql+asyncpg://`

#### Invalid Numeric Range

```
ValidationError: 1 validation error for Settings
embedding_batch_size
  Input should be greater than or equal to 1
```

**Fix**: Set value within valid range (1-1000)

### Debugging

```python
# Print all settings
from src.config import settings
import json

print(json.dumps(settings.model_dump(), indent=2, default=str))
```

## References

- **Pydantic Settings**: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- **PostgreSQL AsyncPG**: https://magicstack.github.io/asyncpg/
- **Ollama API**: https://github.com/ollama/ollama/blob/main/docs/api.md
- **MCP Protocol**: https://modelcontextprotocol.io/

## License

MIT License - See LICENSE file for details
