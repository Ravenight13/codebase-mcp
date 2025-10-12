# Structured Logging Module

## Overview

The `src/mcp/logging.py` module provides production-grade structured logging for the Codebase MCP Server with full constitutional compliance.

## Constitutional Compliance

### ✅ Principle III: Protocol Compliance
- **No stdout/stderr pollution**: All logs written to file only
- **Clean MCP protocol**: Ensures SSE communication works correctly
- **Console handlers removed**: Automatically removes any console handlers

### ✅ Principle V: Production Quality
- **Structured JSON format**: Machine-parseable log entries
- **Automatic log rotation**: 100MB per file, 5 backup files
- **Comprehensive error handling**: Full exception tracebacks
- **Performance metrics**: Duration, latency, throughput tracking

### ✅ Principle VIII: Type Safety
- **mypy --strict compliance**: 100% type coverage
- **Pydantic validation**: Type-safe log record models
- **TypedDict contexts**: Structured context metadata

## Features

1. **JSON Structured Logging**: Every log entry is valid JSON
2. **File-Only Output**: Logs to `/tmp/codebase-mcp.log` (configurable)
3. **Automatic Rotation**: 100MB per file, keeps 5 backup files
4. **Contextual Logging**: Type-safe context with request IDs, metrics, etc.
5. **Full Type Safety**: Complete mypy --strict compliance
6. **Performance Tracking**: Built-in support for timing and metrics
7. **Exception Logging**: Full tracebacks with context
8. **Singleton Management**: Auto-configured on import

## Quick Start

### Basic Usage

```python
from src.mcp.logging import get_logger

logger = get_logger(__name__)
logger.info("Service started")
logger.error("Operation failed", exc_info=True)
```

### Structured Logging with Context

```python
from src.mcp.logging import get_structured_logger

logger = get_structured_logger(__name__)

logger.info(
    "Repository indexed",
    context={
        "repository_id": "repo-123",
        "files_processed": 1000,
        "duration_ms": 1234.56
    }
)
```

## API Reference

### `get_logger(name: str) -> logging.Logger`

Get a standard Python logger with JSON structured output.

**Parameters:**
- `name`: Logger name (typically `__name__`)

**Returns:** Configured `logging.Logger` instance

**Example:**
```python
logger = get_logger(__name__)
logger.info("Service started")
```

### `get_structured_logger(name: str) -> StructuredLogger`

Get a structured logger with convenience methods and context support.

**Parameters:**
- `name`: Logger name (typically `__name__`)

**Returns:** `StructuredLogger` instance with context support

**Example:**
```python
logger = get_structured_logger(__name__)
logger.info("Operation completed", context={"duration_ms": 123.45})
```

### `configure_logging(...)`

Manually configure logging with custom settings.

**Parameters:**
- `log_file`: Path to log file (default: `/tmp/codebase-mcp.log`)
- `max_bytes`: Maximum size per file before rotation (default: 100MB)
- `backup_count`: Number of backup files to keep (default: 5)
- `level`: Minimum log level (default: `logging.INFO`)

**Example:**
```python
from pathlib import Path
import logging

configure_logging(
    log_file=Path("/var/log/mcp.log"),
    max_bytes=50 * 1024 * 1024,  # 50MB
    backup_count=10,
    level=logging.DEBUG
)
```

## Log Format

Each log entry is a single JSON line with the following structure:

```json
{
  "timestamp": "2025-10-06T12:34:56.789Z",
  "level": "INFO",
  "logger": "src.services.indexer",
  "module": "indexer",
  "function": "index_repository",
  "line": 42,
  "message": "Repository indexed successfully",
  "context": {
    "repository_id": "repo-123",
    "files_processed": 1000,
    "duration_ms": 1234.56
  },
  "format_version": "1.0"
}
```

### Log Entry Fields

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | string | ISO 8601 timestamp with timezone |
| `level` | string | Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `logger` | string | Logger name (typically module name) |
| `module` | string | Python module where log was generated |
| `function` | string | Function name where log was generated |
| `line` | integer | Line number where log was generated |
| `message` | string | Human-readable log message |
| `context` | object | Additional structured context data |
| `format_version` | string | Log format version (for backward compatibility) |

## Context Types

The module provides a `LogContext` TypedDict for type-safe context metadata:

```python
from src.mcp.logging import LogContext

context: LogContext = {
    # Request/Operation Context
    "request_id": "req-123",
    "operation": "index_repository",
    "repository_id": "repo-456",
    "repository_path": "/path/to/repo",

    # Performance Metrics
    "duration_ms": 1234.56,
    "latency_ms": 500.0,

    # Error Context
    "error": "Connection timeout",
    "error_type": "TimeoutError",
    "traceback": "...",

    # Additional Context
    "files_processed": 1000,
    "embeddings_count": 5000,
    "custom": {"key": "value"}
}
```

## Usage Patterns

### Pattern 1: Service Initialization

```python
from src.mcp.logging import get_structured_logger

logger = get_structured_logger(__name__)

def initialize_service() -> None:
    logger.info("Service initializing", context={"version": "1.0.0"})
    # ... initialization code ...
    logger.info("Service ready", context={"port": 8000})
```

### Pattern 2: Repository Indexing

```python
from src.mcp.logging import get_structured_logger
import time

logger = get_structured_logger(__name__)

def index_repository(repo_path: str) -> None:
    start_time = time.perf_counter()

    logger.info(
        "Repository indexing started",
        context={
            "repository_path": repo_path,
            "operation": "index_repository"
        }
    )

    try:
        # ... indexing logic ...
        files_processed = 1000
        duration_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "Repository indexed successfully",
            context={
                "repository_path": repo_path,
                "files_processed": files_processed,
                "duration_ms": duration_ms
            }
        )
    except Exception as e:
        logger.error(
            "Repository indexing failed",
            context={
                "repository_path": repo_path,
                "error": str(e)
            }
        )
        raise
```

### Pattern 3: Error Handling with Context

```python
from src.mcp.logging import get_structured_logger

logger = get_structured_logger(__name__)

def process_file(file_path: str) -> None:
    try:
        # ... processing logic ...
        pass
    except FileNotFoundError:
        logger.error(
            "File not found",
            context={
                "file_path": file_path,
                "operation": "process_file"
            }
        )
        raise
    except Exception:
        logger.critical(
            "Unexpected error processing file",
            context={
                "file_path": file_path,
                "operation": "process_file"
            }
        )
        raise
```

### Pattern 4: Performance Monitoring

```python
from src.mcp.logging import get_structured_logger
import time

logger = get_structured_logger(__name__)

def search_embeddings(query: str) -> list[str]:
    start_time = time.perf_counter()

    # ... search logic ...
    results = ["result1", "result2"]

    duration_ms = (time.perf_counter() - start_time) * 1000

    logger.info(
        "Search completed",
        context={
            "query": query,
            "results_count": len(results),
            "duration_ms": duration_ms,
            "operation": "search_embeddings"
        }
    )

    if duration_ms > 500:
        logger.warning(
            "Slow search detected",
            context={
                "query": query,
                "duration_ms": duration_ms,
                "threshold_ms": 500
            }
        )

    return results
```

## Log Rotation

Logs automatically rotate when they reach the configured size limit:

- **Default max size**: 100MB per file
- **Default backup count**: 5 files
- **Rotation naming**: `codebase-mcp.log.1`, `codebase-mcp.log.2`, etc.
- **Automatic cleanup**: Old backups are automatically deleted

### Rotation Behavior

1. When `codebase-mcp.log` reaches 100MB, it's renamed to `codebase-mcp.log.1`
2. Existing backups are incremented: `.1` → `.2`, `.2` → `.3`, etc.
3. The oldest backup (`.5`) is deleted
4. A new `codebase-mcp.log` is created

## Configuration

### Default Configuration

```python
LOG_FILE_PATH = Path("/tmp/codebase-mcp.log")
LOG_MAX_BYTES = 100 * 1024 * 1024  # 100MB
LOG_BACKUP_COUNT = 5
LOG_FORMAT_VERSION = "1.0"
```

### Custom Configuration

```python
from pathlib import Path
from src.mcp.logging import configure_logging
import logging

configure_logging(
    log_file=Path("/var/log/mcp-server.log"),
    max_bytes=50 * 1024 * 1024,  # 50MB
    backup_count=10,
    level=logging.DEBUG
)
```

## Testing

The module includes comprehensive tests in `tests/unit/test_logging.py`:

- **19 tests**: All passing with 96% coverage
- **mypy --strict**: 100% type safety compliance
- **Constitutional compliance**: Tests verify Principles III, V, VIII

### Running Tests

```bash
# Run all logging tests
pytest tests/unit/test_logging.py -v

# Run with coverage
pytest tests/unit/test_logging.py --cov=src/mcp/logging --cov-report=term-missing

# Type check
mypy src/mcp/logging.py --strict
```

## Best Practices

### ✅ DO

1. **Use structured context for important data**
   ```python
   logger.info("Repository indexed", context={"repo_id": "123", "files": 1000})
   ```

2. **Log at appropriate levels**
   - `DEBUG`: Detailed diagnostic information
   - `INFO`: General informational messages
   - `WARNING`: Warning messages for potentially harmful situations
   - `ERROR`: Error messages for failures
   - `CRITICAL`: Critical messages for severe failures

3. **Include context for debugging**
   ```python
   logger.error("Database query failed", context={"query": sql, "params": params})
   ```

4. **Use exception logging**
   ```python
   try:
       dangerous_operation()
   except Exception:
       logger.error("Operation failed", exc_info=True)
   ```

### ❌ DON'T

1. **Don't log sensitive data**
   ```python
   # BAD: Logs passwords
   logger.info("User login", context={"password": "secret123"})

   # GOOD: Logs username only
   logger.info("User login", context={"username": "user123"})
   ```

2. **Don't log to stdout/stderr**
   ```python
   # BAD: Violates Principle III
   print("Debug message")

   # GOOD: Use structured logging
   logger.debug("Debug message")
   ```

3. **Don't use string formatting in messages**
   ```python
   # BAD: Inefficient, poor structure
   logger.info(f"Processed {count} files in {duration}ms")

   # GOOD: Use context
   logger.info("Files processed", context={"count": count, "duration_ms": duration})
   ```

4. **Don't log inside tight loops**
   ```python
   # BAD: Performance impact
   for item in large_list:
       logger.debug(f"Processing {item}")

   # GOOD: Log batch operations
   logger.info("Batch processing started", context={"items": len(large_list)})
   for item in large_list:
       # ... process item ...
   logger.info("Batch processing completed")
   ```

## Troubleshooting

### Issue: No logs appearing

**Cause**: Logging level too high

**Solution**: Configure with appropriate level
```python
configure_logging(level=logging.DEBUG)
```

### Issue: Logs not rotating

**Cause**: File size limit not reached

**Solution**: Check file size and rotation settings
```python
configure_logging(
    max_bytes=10 * 1024 * 1024,  # 10MB for testing
    backup_count=3
)
```

### Issue: Type errors in tests

**Cause**: LogContext type mismatch

**Solution**: Use type annotations
```python
from typing import Any

context: dict[str, Any] = {"key": "value"}
logger.info("Message", context=context)  # type: ignore[arg-type]
```

## Implementation Details

### Architecture

1. **JSONFormatter**: Converts log records to JSON format
2. **LoggerManager**: Singleton manager for configuration
3. **StructuredLogger**: Convenience wrapper with context support
4. **LogContext**: TypedDict for type-safe context metadata
5. **StructuredLogRecord**: Pydantic model for validation

### Performance

- **JSON serialization**: Fast using Pydantic's JSON encoder
- **File I/O**: Buffered writes with automatic flushing
- **Rotation**: Efficient file operations with minimal overhead
- **Type checking**: Zero runtime overhead with mypy

### Dependencies

- **Python 3.11+**: Required for modern type hints
- **Pydantic 2.5+**: Used for data validation and JSON serialization
- **Standard library**: `logging`, `logging.handlers`, `json`, `datetime`, `pathlib`

## Integration Examples

### FastAPI Integration

```python
from fastapi import FastAPI, Request
from src.mcp.logging import get_structured_logger

app = FastAPI()
logger = get_structured_logger(__name__)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start_time) * 1000

    logger.info(
        "Request processed",
        context={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms
        }
    )

    return response
```

### Database Operations

```python
from src.mcp.logging import get_structured_logger
import time

logger = get_structured_logger(__name__)

async def execute_query(query: str, params: dict) -> list:
    start_time = time.perf_counter()

    try:
        result = await db.execute(query, params)
        duration_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "Query executed",
            context={
                "duration_ms": duration_ms,
                "rows_affected": len(result)
            }
        )

        return result
    except Exception:
        logger.error(
            "Query execution failed",
            context={"query": query[:100]}  # Log first 100 chars
        )
        raise
```

## Summary

The structured logging module provides:

- ✅ **Constitutional compliance**: Principles III, V, VIII
- ✅ **Production quality**: Rotation, error handling, performance
- ✅ **Type safety**: 100% mypy --strict compliance
- ✅ **Comprehensive testing**: 19 tests, 96% coverage
- ✅ **Easy integration**: Simple API, auto-configuration
- ✅ **Performance**: Efficient JSON serialization, minimal overhead

Use this module for all logging in the Codebase MCP Server to ensure consistency, compliance, and production quality.
