# Connection Pool Manager API Contract

**Purpose**: Internal API for connection pool lifecycle management

**Scope**: Internal infrastructure - not exposed via MCP protocol

## Initialization

### `initialize(config: PoolConfig) -> None`

**Purpose**: Initialize connection pool with validated configuration

**Parameters**:
- `config`: PoolConfig - Validated configuration object

**Behavior**:
1. Validate configuration (fail-fast on invalid input)
2. Create asyncpg pool with min_size connections
3. Validate all connections via SELECT 1
4. Transition to HEALTHY state
5. Start background tasks (health checks, recycling)

**Errors**:
- `PoolConfigurationError`: Invalid configuration
- `PoolInitializationError`: Cannot create min_size connections

**Performance**: <2s (p95) per SC-001

**Example**:
```python
config = PoolConfig(
    min_size=2,
    max_size=10,
    database_url="postgresql+asyncpg://localhost/codebase_mcp"
)
pool_manager = ConnectionPoolManager()
await pool_manager.initialize(config)
```

---

## Connection Acquisition

### `acquire(timeout: float | None = None) -> Connection`

**Purpose**: Acquire validated connection from pool

**Parameters**:
- `timeout`: Optional timeout override (default: config.timeout)

**Behavior**:
1. Acquire connection from asyncpg pool
2. Validate connection via SELECT 1 (<5ms)
3. Track acquisition timestamp and stack trace
4. Return connection or timeout

**Errors**:
- `PoolTimeoutError`: Acquisition exceeded timeout
- `ConnectionValidationError`: Connection validation failed
- `PoolClosedError`: Pool is shutting down

**Performance**: <10ms (p95) per SC-002

**Example**:
```python
async with pool_manager.pool.acquire() as conn:
    result = await conn.fetchrow("SELECT * FROM repositories WHERE id = $1", repo_id)
```

---

## Health Monitoring

### `health_check() -> HealthStatus`

**Purpose**: Get current pool health status without database query

**Returns**: HealthStatus - Current health with statistics

**Behavior**:
1. Read in-memory statistics (no locks)
2. Calculate health status based on capacity
3. Return HealthStatus model

**Performance**: <10ms (p99) per SC-003

**Example**:
```python
health = await pool_manager.health_check()
print(f"Status: {health.status}, Idle: {health.database.pool['idle']}")
```

---

## Statistics

### `get_statistics() -> PoolStatistics`

**Purpose**: Get detailed pool statistics for monitoring

**Returns**: PoolStatistics - Immutable statistics snapshot

**Behavior**:
1. Read current pool state atomically
2. Return PoolStatistics model

**Performance**: <1ms per SC-007

**Example**:
```python
stats = pool_manager.get_statistics()
print(f"Acquisitions: {stats.total_acquisitions}, Avg: {stats.avg_acquisition_time_ms}ms")
```

---

## Graceful Shutdown

### `shutdown(timeout: float = 30.0) -> None`

**Purpose**: Gracefully shutdown pool, waiting for active connections

**Parameters**:
- `timeout`: Max wait time for active connections (default: 30s)

**Behavior**:
1. Set pool status to SHUTTING_DOWN
2. Reject new acquisition requests
3. Wait for active_connections to reach 0 (max timeout seconds)
4. Close all idle connections
5. Force-close remaining active connections with warnings
6. Release all resources

**Performance**: <30s (p99) per SC-005

**Example**:
```python
# On server shutdown
await pool_manager.shutdown(timeout=30.0)
logger.info("Connection pool terminated")
```

---

## Error Handling

All methods raise specific exceptions:

- `PoolConfigurationError`: Configuration validation failed
- `PoolInitializationError`: Pool creation failed
- `PoolTimeoutError`: Connection acquisition timeout
- `ConnectionValidationError`: Connection validation failed
- `PoolClosedError`: Pool is shut down

All exceptions include:
- Error message with context
- Suggested action
- Current pool state (if applicable)

---

## Concurrency Guarantees

- All methods are async and thread-safe
- Connection acquisition queued in FIFO order
- Statistics updates are atomic
- No deadlocks (acquisition timeouts prevent)
- Multiple concurrent health_check() calls supported

---

## Lifecycle States

```
INITIALIZING → HEALTHY → DEGRADED → UNHEALTHY → RECOVERING → HEALTHY
                ↓                       ↓
            SHUTTING_DOWN → TERMINATED
```

**State Transitions**:
- `initialize()`: INITIALIZING → HEALTHY
- Database failure: HEALTHY → DEGRADED/UNHEALTHY
- Reconnection: UNHEALTHY → RECOVERING → HEALTHY
- `shutdown()`: * → SHUTTING_DOWN → TERMINATED
