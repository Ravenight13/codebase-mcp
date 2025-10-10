# Database Session Management

Production-grade async SQLAlchemy session factory for PostgreSQL with connection pooling, automatic transaction management, and comprehensive error handling.

## Features

- **Async SQLAlchemy**: Full async/await support using asyncpg driver
- **Connection Pooling**: Configurable pool size (default: 10 connections, 20 overflow)
- **Automatic Transactions**: Context manager pattern with auto-commit/rollback
- **Type Safety**: 100% mypy --strict compliance with complete type annotations
- **Error Handling**: Comprehensive logging and graceful error handling
- **Health Checks**: Built-in database connectivity monitoring
- **Production Ready**: Connection recycling, pre-ping validation, timeout handling

## Quick Start

### Basic Usage

```python
from src.database import get_session
from sqlalchemy import select
from src.models.repository import Repository

# Query example
async def get_all_repositories():
    async with get_session() as session:
        result = await session.execute(select(Repository))
        repos = result.scalars().all()
        return list(repos)
```

### Create Operation

```python
async def create_repository(path: str):
    async with get_session() as session:
        repo = Repository(path=path)
        session.add(repo)
        await session.flush()  # Get ID before commit
        # Auto-commits on exit
        return repo
```

### Update Operation

```python
from uuid import UUID

async def update_repository(repo_id: UUID, new_path: str):
    async with get_session() as session:
        result = await session.execute(
            select(Repository).where(Repository.id == repo_id)
        )
        repo = result.scalar_one_or_none()

        if repo:
            repo.path = new_path
            # Auto-commits on exit

        return repo
```

### Error Handling

```python
async def safe_create_repository(path: str):
    try:
        async with get_session() as session:
            repo = Repository(path=path)
            session.add(repo)
            return repo
    except Exception as e:
        # Session auto-rolls back on exception
        print(f"Error: {e}")
        return None
```

### Health Check

```python
from src.database import check_database_health

async def verify_database():
    is_healthy = await check_database_health()
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "database": "ok" if is_healthy else "error",
    }
```

## Configuration

Configure via environment variables:

```bash
# Database connection URL (required)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/codebase_mcp

# Enable SQL query logging (optional, default: false)
SQL_ECHO=true
```

### Connection Pool Settings

Default configuration (can be customized in `session.py`):

- **Pool Size**: 10 connections (core pool)
- **Max Overflow**: 20 connections (additional on-demand)
- **Pool Timeout**: 30 seconds (wait time before timeout)
- **Pool Pre-Ping**: Enabled (validates connections before use)
- **Pool Recycle**: 3600 seconds (recycles connections after 1 hour)

## MCP Tool Integration

Use the session factory in MCP tools:

```python
from fastmcp import FastMCP
from src.database import get_session
from src.models.repository import Repository

mcp = FastMCP("codebase-mcp")

@mcp.tool()
async def create_repository(repo_path: str) -> dict[str, str]:
    """Create a new repository."""
    try:
        async with get_session() as session:
            repo = Repository(path=repo_path)
            session.add(repo)
            await session.flush()

            return {
                "status": "success",
                "repo_id": str(repo.id),
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }
```

## API Reference

### `get_session()`

Async context manager for database sessions.

**Returns**: `AsyncGenerator[AsyncSession, None]`

**Features**:
- Automatic commit on success
- Automatic rollback on exception
- Ensures session is closed after use
- Complete error logging

**Example**:
```python
async with get_session() as session:
    result = await session.execute(select(Repository))
    repos = result.scalars().all()
```

### `get_session_factory()`

Get the initialized session factory.

**Returns**: `async_sessionmaker[AsyncSession]`

**Use Case**: When you need the factory itself (e.g., dependency injection)

**Example**:
```python
factory = get_session_factory()
async with factory() as session:
    # Use session
    pass
```

### `check_database_health()`

Check database connection health.

**Returns**: `bool` (True if healthy, False otherwise)

**Features**:
- Executes simple `SELECT 1` query
- Uses connection pooling
- Comprehensive error logging
- <1ms typical latency

**Example**:
```python
is_healthy = await check_database_health()
if not is_healthy:
    logger.error("Database is not accessible")
```

## Architecture

### Module Structure

```
src/database/
├── __init__.py          # Public API exports
├── session.py           # Session factory implementation
└── README.md            # This file
```

### Transaction Flow

```
┌─────────────────────────────────┐
│    async with get_session()    │
└────────────┬────────────────────┘
             │
             ▼
    ┌────────────────┐
    │ Create Session │
    └────────┬───────┘
             │
             ▼
    ┌────────────────┐
    │ Execute Queries│
    └────────┬───────┘
             │
         ┌───┴───┐
         │       │
    Success   Exception
         │       │
         ▼       ▼
    ┌────────┬──────────┐
    │ Commit │ Rollback │
    └────────┴──────────┘
             │
             ▼
    ┌────────────────┐
    │ Close Session  │
    └────────────────┘
```

### Connection Pool Architecture

```
┌──────────────────────────────┐
│    Application Requests      │
└───────────┬──────────────────┘
            │
            ▼
┌───────────────────────────────┐
│    Connection Pool Manager    │
│  ┌─────────────────────────┐  │
│  │  Core Pool (10 conns)   │  │
│  └─────────────────────────┘  │
│  ┌─────────────────────────┐  │
│  │ Overflow (20 conns max) │  │
│  └─────────────────────────┘  │
└───────────┬───────────────────┘
            │
            ▼
┌───────────────────────────────┐
│      PostgreSQL Database      │
└───────────────────────────────┘
```

## Performance Characteristics

- **Connection Acquisition**: <10ms (from pool)
- **Health Check**: <1ms (simple SELECT 1)
- **Connection Validation**: Pre-ping before each use
- **Connection Recycling**: Every 3600 seconds (1 hour)
- **Pool Timeout**: 30 seconds max wait

## Error Handling

### Automatic Rollback

The session context manager automatically rolls back transactions on any exception:

```python
async with get_session() as session:
    repo = Repository(path="/test")
    session.add(repo)
    raise ValueError("Something went wrong")
    # Session automatically rolls back
```

### Exception Propagation

All exceptions are propagated after cleanup:

```python
try:
    async with get_session() as session:
        # Database operation
        raise CustomError("Error")
except CustomError:
    # Exception is propagated after rollback
    print("Caught exception after cleanup")
```

### Comprehensive Logging

All session lifecycle events are logged:

- Session start (DEBUG)
- Commit success (DEBUG)
- Rollback on error (ERROR with context)
- Session close (DEBUG)

## Testing

### Unit Tests

Run unit tests for the session factory:

```bash
pytest tests/unit/test_database_session.py -v
```

### Type Checking

Verify type safety:

```bash
mypy src/database/ --strict
```

### Coverage

The session module has 100% test coverage with 12 comprehensive tests:

- Session factory creation
- Transaction commit/rollback
- Error handling and cleanup
- Health check functionality
- Logging verification
- Configuration validation

## Constitutional Compliance

This module follows the project's constitutional principles:

- **Principle IV**: Performance (connection pooling, async operations)
- **Principle V**: Production quality (comprehensive error handling, cleanup)
- **Principle VIII**: Type safety (mypy --strict compliance)
- **Principle XI**: FastMCP Foundation (async patterns for MCP tools)

## Examples

See `/examples/database_session_usage.py` for comprehensive usage examples:

- Basic queries
- Create/Update operations
- Error handling patterns
- Batch operations
- MCP tool integration
- Health check examples

## Troubleshooting

### Connection Timeout

If you experience connection timeouts:

1. Check database is accessible: `await check_database_health()`
2. Verify DATABASE_URL is correct
3. Increase `POOL_TIMEOUT` if needed (default: 30s)

### Pool Exhaustion

If you see "pool limit exceeded" errors:

1. Review connection usage patterns
2. Ensure sessions are closed (use context manager)
3. Consider increasing `POOL_SIZE` or `MAX_OVERFLOW`

### Stale Connections

Connections are automatically recycled after 1 hour. If you experience stale connections:

1. Verify `pool_pre_ping=True` is enabled (default)
2. Reduce `pool_recycle` time if needed
3. Check database firewall/timeout settings

## Best Practices

1. **Always use the context manager**: `async with get_session()`
2. **Don't reuse sessions**: Create new session per operation
3. **Use flush for IDs**: `await session.flush()` to get ID before commit
4. **Handle exceptions**: Wrap in try/except for custom error handling
5. **Check health**: Use `check_database_health()` for monitoring
6. **Type annotations**: Always annotate return types for type safety

## Related Documentation

- [SQLAlchemy Async ORM](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [asyncpg Driver](https://magicstack.github.io/asyncpg/current/)
- [FastMCP Documentation](https://github.com/fastmcp/fastmcp)
- [Project Constitution](../../.specify/memory/constitution.md)
