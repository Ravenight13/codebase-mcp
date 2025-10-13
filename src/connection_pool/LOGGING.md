# Connection Pool Logging Configuration

## Overview

The connection pool module uses structured JSON logging that writes to `/tmp/codebase-mcp.log`. This ensures MCP protocol compliance (no stdout/stderr pollution) and provides rich observability for production environments.

## Architecture

```
Connection Pool Modules
    ↓
src/connection_pool/pool_logging.py
    ↓
src/mcp/mcp_logging.py (shared infrastructure)
    ↓
/tmp/codebase-mcp.log (JSON formatted, rotated)
```

## Key Features

1. **JSON Structured Logging**: All logs are JSON formatted for easy parsing
2. **File-Only Output**: No stdout/stderr pollution (MCP protocol compliance)
3. **Automatic Rotation**: 100MB per file, 5 backup files retained
4. **Rich Context**: Pool metrics, connection details, performance data
5. **Type-Safe**: Full mypy --strict compliance with Pydantic models

## Usage

### Basic Logging

```python
from src.connection_pool.pool_logging import get_pool_logger

logger = get_pool_logger(__name__)
logger.info("Pool initialized")
logger.warning("Pool capacity at 75%")
logger.error("Connection validation failed")
```

### Structured Logging with Context

```python
from src.connection_pool.pool_logging import get_pool_structured_logger

logger = get_pool_structured_logger(__name__)
logger.info(
    "Pool initialized successfully",
    context={
        "min_size": 2,
        "max_size": 10,
        "initialization_time_ms": 125.5,
    }
)
```

### Convenience Functions

```python
from src.connection_pool.pool_logging import (
    log_pool_initialization,
    log_connection_acquisition,
    log_reconnection_attempt,
    log_pool_statistics,
)

# Pool initialization
log_pool_initialization(
    logger=logger,
    min_size=2,
    max_size=10,
    duration_ms=125.5,
    success=True
)

# Connection acquisition
log_connection_acquisition(
    logger=logger,
    acquisition_time_ms=2.3,
    pool_size=10,
    active_connections=5,
    idle_connections=5
)
```

## Log Levels

- **DEBUG**: Connection acquisitions, releases, detailed pool state
- **INFO**: Pool initialization, statistics, normal operations
- **WARNING**: Capacity warnings, reconnection attempts, degraded state
- **ERROR**: Connection validation failures, initialization errors
- **CRITICAL**: Pool failures, unrecoverable errors

## JSON Log Format

```json
{
    "timestamp": "2025-10-13T12:25:47.991298+00:00",
    "level": "INFO",
    "logger": "connection_pool.manager",
    "module": "manager",
    "function": "initialize",
    "line": 125,
    "message": "Pool initialized successfully",
    "context": {
        "event": "pool_initialized",
        "min_size": 2,
        "max_size": 10,
        "duration_ms": 125.5
    },
    "format_version": "1.0"
}
```

## Context Fields

Common context fields used in connection pool logs:

- **Pool State**: `min_size`, `max_size`, `total_connections`, `idle_connections`, `active_connections`
- **Performance**: `acquisition_time_ms`, `avg_acquisition_time_ms`, `duration_ms`
- **Events**: `event` (event name for filtering), `connection_id`, `reason`
- **Errors**: `error_type`, `error_message`, `traceback`
- **Reconnection**: `attempt`, `delay_seconds`, `success`

## Viewing Logs

```bash
# Tail logs in real-time
tail -f /tmp/codebase-mcp.log

# View last 10 entries with pretty-printing
tail -10 /tmp/codebase-mcp.log | while read line; do echo "$line" | python3 -m json.tool; done

# Filter by event type
grep "pool_initialized" /tmp/codebase-mcp.log | python3 -m json.tool

# Filter by log level
grep '"level":"ERROR"' /tmp/codebase-mcp.log | python3 -m json.tool
```

## Constitutional Compliance

- **Principle III**: Protocol Compliance - No stdout/stderr pollution
- **Principle V**: Production Quality - Structured, rotatable, comprehensive logging
- **Principle VIII**: Type Safety - Full mypy --strict compliance

## Log Rotation

- **Max File Size**: 100MB per log file
- **Backup Count**: 5 backup files retained
- **Naming**: `/tmp/codebase-mcp.log`, `/tmp/codebase-mcp.log.1`, etc.
- **Compression**: Not enabled (can be added if needed)

## Examples

See `src/connection_pool/pool_logging_example.py` for comprehensive usage examples including:
- Basic logging
- Structured logging with context
- Convenience functions
- Error logging with exception context
- Custom event logging
- Lifecycle event logging

Run examples:
```bash
python3 src/connection_pool/pool_logging_example.py
```

## Integration with Connection Pool Manager

The ConnectionPoolManager will use this logging infrastructure for:

1. **Initialization**: Log pool startup, configuration validation, connection establishment
2. **Acquisition/Release**: Log connection acquisitions and releases (DEBUG level)
3. **Health Checks**: Log health status transitions (HEALTHY → DEGRADED → UNHEALTHY)
4. **Reconnection**: Log exponential backoff attempts and recovery
5. **Statistics**: Log pool metrics periodically or on-demand
6. **Shutdown**: Log graceful shutdown phases and connection cleanup

## Performance Considerations

- **Async-Safe**: All logging operations are thread-safe and async-safe
- **Minimal Overhead**: Structured logging adds <1ms overhead per log entry
- **No Blocking**: File I/O is buffered and non-blocking
- **Rotation**: Log rotation is handled by Python's RotatingFileHandler

## Troubleshooting

### Logs Not Appearing

```python
from src.mcp.mcp_logging import LoggerManager

manager = LoggerManager()
print(f"Logging configured: {manager.is_configured()}")
```

### Permission Issues

Ensure `/tmp/codebase-mcp.log` is writable:
```bash
touch /tmp/codebase-mcp.log
chmod 644 /tmp/codebase-mcp.log
```

### Log File Full

Check disk space:
```bash
df -h /tmp
```

Rotation should handle this automatically, but manual cleanup:
```bash
rm /tmp/codebase-mcp.log.*
```

## Future Enhancements

- Add log streaming to monitoring systems (Datadog, CloudWatch)
- Implement log aggregation for distributed deployments
- Add structured log querying utilities
- Support custom log destinations via configuration
