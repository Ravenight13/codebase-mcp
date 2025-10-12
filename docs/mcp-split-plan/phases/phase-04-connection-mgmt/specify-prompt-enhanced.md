# Feature: Production-Grade Connection Management

Branch: 004-connection-mgmt | Date: 2025-10-12 | Status: Draft

## Original User Description

Implement production-grade connection pooling and management for the Codebase MCP Server to ensure reliability, performance, and graceful degradation under various operational conditions. This feature establishes the foundational connection infrastructure that all database operations depend on.

The connection management system must handle:
- Connection pool lifecycle (initialization, health checks, graceful shutdown)
- Automatic reconnection with exponential backoff
- Connection validation and health monitoring
- Pool statistics and metrics for observability
- Resource cleanup and leak prevention
- Configuration validation and defaults

This is a foundational infrastructure component that Phase-05 (Repository Indexing) and Phase-06 (Semantic Search) will directly depend on.

---

## User Scenarios & Testing

### Scenario 1: Server Startup with Valid Configuration

**User Story**: As a developer, when I start the MCP server with a valid database configuration, I expect the connection pool to initialize successfully and be ready to handle requests within 2 seconds.

**Testing Workflow**:
1. Set `DATABASE_URL=postgresql+asyncpg://localhost/codebase_mcp`
2. Start MCP server: `python -m codebase_mcp.server`
3. Server logs show: `Connection pool initialized: min_size=2, max_size=10`
4. Health check returns: `{"status": "healthy", "connections": {"total": 2, "idle": 2, "active": 0}}`
5. First query executes in <100ms (no cold start delay)

**Expected Behavior**:
- Pool initializes with `min_size=2` connections immediately
- No connection errors or timeouts
- Server becomes ready for MCP requests within 2 seconds
- All connections pass validation queries

**Edge Cases**:
- Database server is temporarily slow to respond → Initialization retries up to 3 times with exponential backoff
- `min_size` exceeds available database connections → Log warning, reduce pool size, continue with lower capacity

---

### Scenario 2: Graceful Handling of Database Outage

**User Story**: As a system administrator, when the database server becomes unavailable during operation, I expect the MCP server to attempt automatic reconnection without crashing, and resume operations when the database recovers.

**Testing Workflow**:
1. MCP server is running with active connection pool
2. Execute query successfully: `search_code(query="authentication", limit=5)`
3. Stop PostgreSQL server: `docker stop postgres-container`
4. Attempt query → Returns error: `{"error": "DATABASE_ERROR", "message": "Connection pool unavailable"}`
5. Server logs show: `Connection pool unhealthy: 0/10 connections available. Attempting reconnection...`
6. Reconnection attempts logged: `Retry 1/5 in 1s... Retry 2/5 in 2s... Retry 3/5 in 4s...`
7. Restart PostgreSQL server: `docker start postgres-container`
8. Server logs show: `Connection pool recovered: 2/10 connections available`
9. Retry query → Success: Returns 5 search results

**Expected Behavior**:
- No server crash or process termination
- MCP protocol errors returned gracefully (not protocol violations)
- Automatic reconnection with exponential backoff (1s, 2s, 4s, 8s, 16s)
- Health check status updates: `healthy → degraded → unhealthy → recovering → healthy`
- Operations resume automatically after database recovery

**Edge Cases**:
- Database recovers during backoff wait → Immediately retry connection
- Database never recovers → Server stays in `unhealthy` state but continues accepting MCP requests (fails gracefully)
- Partial database recovery (some connections succeed) → Pool operates in degraded mode with reduced capacity

---

### Scenario 3: Connection Leak Detection and Prevention

**User Story**: As a developer, if my code accidentally holds database connections without releasing them, I expect the connection pool to detect this and log warnings to help me identify the leak.

**Testing Workflow**:
1. Configure pool with `max_size=5` and `leak_detection_timeout=30s`
2. Execute 3 queries that complete normally → Pool shows: `{"idle": 5, "active": 0}`
3. Execute query with simulated leak (connection not returned to pool):
   ```python
   async with pool.acquire() as conn:
       await asyncio.sleep(40)  # Hold connection for 40 seconds
   ```
4. After 30 seconds, server logs: `WARNING: Potential connection leak detected. Connection held for 30s. Stack trace: [...]`
5. After 40 seconds, connection returns to pool → Pool shows: `{"idle": 5, "active": 0}`

**Expected Behavior**:
- Leak detection triggers after configurable timeout (default 30s)
- Log message includes:
  - Duration connection was held
  - Stack trace showing where connection was acquired
  - Timestamp and connection ID
- Connection eventually returns to pool (no permanent leak)
- No false positives for long-running legitimate queries

**Edge Cases**:
- Long-running indexing operation (legitimate) → Leak detection timeout should be configurable per operation
- Orphaned connection (never returned) → Pool eventually recycles connection after `max_connection_lifetime` (e.g., 1 hour)

---

### Scenario 4: Pool Statistics and Observability

**User Story**: As a system administrator monitoring production systems, I need to query connection pool statistics to understand database load and identify performance bottlenecks.

**Testing Workflow**:
1. Start MCP server with pool configured: `min_size=2, max_size=10`
2. Query initial statistics:
   ```json
   {
     "total_connections": 2,
     "idle_connections": 2,
     "active_connections": 0,
     "waiting_requests": 0,
     "total_acquisitions": 0,
     "total_releases": 0,
     "avg_acquisition_time_ms": 0,
     "peak_active_connections": 0
   }
   ```
3. Execute 5 concurrent search queries
4. During execution, query statistics:
   ```json
   {
     "total_connections": 5,
     "idle_connections": 0,
     "active_connections": 5,
     "waiting_requests": 0,
     "total_acquisitions": 5,
     "avg_acquisition_time_ms": 2.3,
     "peak_active_connections": 5
   }
   ```
5. Queries complete, query statistics again:
   ```json
   {
     "total_connections": 5,
     "idle_connections": 5,
     "active_connections": 0,
     "waiting_requests": 0,
     "total_acquisitions": 5,
     "total_releases": 5,
     "avg_acquisition_time_ms": 2.3,
     "peak_active_connections": 5
   }
   ```
6. After 60 seconds of idle time, pool shrinks to `min_size=2`:
   ```json
   {
     "total_connections": 2,
     "idle_connections": 2,
     "active_connections": 0
   }
   ```

**Expected Behavior**:
- Statistics update in real-time (no stale data)
- Metrics exposed via health check endpoint
- Pool automatically scales between `min_size` and `max_size` based on load
- Idle connections reclaimed after configurable timeout (default 60s)
- Historical peak metrics retained for capacity planning

**Edge Cases**:
- Pool hits `max_size` limit → New requests wait, `waiting_requests` increments
- Pool size exceeds `max_size` temporarily → Log error, close excess connections immediately
- Statistics queries don't consume database connections

---

## Functional Requirements

### FR-001: Connection Pool Initialization

**Requirement**: The system must initialize a connection pool on server startup with configurable minimum and maximum connection limits.

**Acceptance Criteria**:
- Pool creates `min_size` connections immediately on startup
- Configuration validated before pool creation (fail fast on invalid config)
- Pool initialization completes within 2 seconds or logs detailed error
- Initialization failures prevent server startup (don't enter degraded state at launch)

**Configuration Parameters**:
```python
@dataclass
class PoolConfig:
    min_size: int = 2              # Minimum connections to maintain
    max_size: int = 10             # Maximum connections allowed
    max_queries: int = 50000       # Queries per connection before recycling
    max_idle_time: float = 60.0    # Seconds before idle connections are closed
    timeout: float = 30.0          # Seconds to wait for connection acquisition
    command_timeout: float = 60.0  # Seconds for query execution timeout
    max_connection_lifetime: float = 3600.0  # Max age of connection in seconds
```

**Error Handling**:
- Invalid `min_size` or `max_size` (<=0, min>max) → Raise `ValueError` with detailed message
- Database unreachable → Retry 3 times with exponential backoff, then fail startup
- Insufficient database connection limit → Log warning, reduce `min_size` to database limit

---

### FR-002: Connection Health Validation

**Requirement**: All connections must be validated before use to detect stale or broken connections.

**Acceptance Criteria**:
- Execute lightweight validation query before returning connection from pool
- Validation query: `SELECT 1` (completes in <5ms)
- Failed validation → Close connection, create new connection, retry once
- Validation timeout (>5s) → Treat as failure, close connection

**Health Check Query**:
```sql
-- Lightweight query to validate connection
SELECT 1 AS health_check;
```

**Performance Target**:
- Validation adds <10ms overhead to connection acquisition (p95)
- No validation overhead for connections acquired <5 seconds ago (caching)

**Error Handling**:
- Validation fails after retry → Log error with connection details, raise `ConnectionValidationError`
- Connection closed during validation → Treat as stale, create new connection
- Database in read-only mode → Validation succeeds, but log warning about database state

---

### FR-003: Automatic Reconnection with Exponential Backoff

**Requirement**: When database connectivity is lost, the system must attempt automatic reconnection with exponential backoff to avoid overwhelming the database.

**Acceptance Criteria**:
- Detect connection loss via failed queries or connection validation
- Retry connection with backoff intervals: 1s, 2s, 4s, 8s, 16s (max 5 attempts)
- Max backoff capped at 16 seconds (don't wait indefinitely)
- All reconnection attempts logged with timestamp and attempt number

**Backoff Algorithm**:
```python
def calculate_backoff(attempt: int, base_delay: float = 1.0, max_delay: float = 16.0) -> float:
    """Calculate exponential backoff delay."""
    delay = min(base_delay * (2 ** attempt), max_delay)
    return delay
```

**Behavior During Reconnection**:
- Server continues accepting MCP requests (don't block protocol)
- Database operations return `DATABASE_ERROR` with retry-after hint
- Health check status: `unhealthy` → `recovering` → `healthy`
- After 5 failed attempts, remain in `unhealthy` state but continue retrying every 16s

**Error Handling**:
- Connection succeeds during backoff wait → Cancel remaining backoff, reconnect immediately
- Connection fails permanently → Log critical error, remain in `unhealthy` state
- Partial reconnection (some connections succeed) → Enter `degraded` mode with reduced capacity

---

### FR-004: Connection Pool Statistics

**Requirement**: The system must expose real-time connection pool statistics for monitoring and debugging.

**Acceptance Criteria**:
- Statistics queryable via internal API (no database query required)
- Statistics include: total connections, idle, active, waiting requests, acquisition time
- Statistics updated atomically (no race conditions or stale data)
- Historical peak metrics retained (peak active connections, max wait time)

**Statistics Schema**:
```python
@dataclass
class PoolStatistics:
    total_connections: int        # Current total connections in pool
    idle_connections: int         # Connections available for use
    active_connections: int       # Connections currently in use
    waiting_requests: int         # Requests waiting for connection
    total_acquisitions: int       # Lifetime connection acquisitions
    total_releases: int           # Lifetime connection releases
    avg_acquisition_time_ms: float  # Average time to acquire connection
    peak_active_connections: int  # Max active connections since server start
    peak_wait_time_ms: float      # Max time request waited for connection
    pool_created_at: datetime     # When pool was initialized
    last_health_check: datetime   # Last successful health check
```

**Exposure Methods**:
- Internal API: `pool.get_statistics() -> PoolStatistics`
- Health check endpoint: `{"connections": {...statistics...}}`
- Prometheus metrics (future): `codebase_mcp_pool_connections{state="idle"}`

---

### FR-005: Graceful Connection Pool Shutdown

**Requirement**: On server shutdown, the system must gracefully close all connections and wait for active operations to complete.

**Acceptance Criteria**:
- Wait up to 30 seconds for active connections to finish queries
- After timeout, force-close remaining connections with warning log
- Release all pool resources (memory, file descriptors)
- Shutdown completes without exceptions or warnings

**Shutdown Sequence**:
1. Set pool status to `shutting_down` (reject new connection requests)
2. Wait for `active_connections` to reach 0 (max 30s timeout)
3. Close all idle connections
4. Force-close remaining active connections (log warning for each)
5. Close pool manager and release resources

**Error Handling**:
- Active query exceeds shutdown timeout → Force-close connection, log query details
- Connection close fails → Log error, continue shutdown (don't block)
- Exception during shutdown → Log critical error, ensure resources released

---

### FR-006: Connection Leak Detection

**Requirement**: The system must detect when connections are held longer than expected and log warnings to help identify leaks.

**Acceptance Criteria**:
- Track acquisition timestamp for each connection
- If connection held longer than `leak_detection_timeout` (default 30s), log warning
- Warning includes: duration held, stack trace of acquisition, connection ID
- No false positives for legitimate long-running operations

**Leak Detection Configuration**:
```python
@dataclass
class PoolConfig:
    leak_detection_timeout: float = 30.0  # Seconds before warning logged
    enable_leak_detection: bool = True    # Toggle for production/development
```

**Warning Log Format**:
```
WARNING: Potential connection leak detected
  Connection ID: conn_12345
  Held for: 35.2 seconds
  Acquired at: 2025-10-12T14:23:45.123Z
  Acquisition stack trace:
    File "server.py", line 45, in handle_request
    File "search.py", line 78, in search_code
```

**Edge Cases**:
- Indexing large repository (legitimately holds connection for >30s) → Allow per-operation timeout override
- Connection never returned (orphaned) → Recycle after `max_connection_lifetime` (e.g., 1 hour)

---

### FR-007: Configuration Validation

**Requirement**: The system must validate all connection pool configuration parameters and fail fast on invalid input.

**Acceptance Criteria**:
- Validate configuration before pool initialization
- Invalid values raise `ValueError` with detailed error message
- Provide sensible defaults for optional parameters
- Support environment variable overrides for all config values

**Validation Rules**:
- `min_size > 0` and `min_size <= max_size`
- `max_size > 0` and `max_size <= 100` (reasonable upper bound)
- `timeout > 0` and `timeout < 300` (max 5 minutes)
- `max_idle_time >= 10.0` (minimum 10 seconds to avoid thrashing)
- `DATABASE_URL` is valid PostgreSQL connection string

**Environment Variables**:
```bash
DATABASE_URL=postgresql+asyncpg://localhost/codebase_mcp  # Required
POOL_MIN_SIZE=2                                           # Optional (default: 2)
POOL_MAX_SIZE=10                                          # Optional (default: 10)
POOL_TIMEOUT=30.0                                         # Optional (default: 30.0)
POOL_MAX_IDLE_TIME=60.0                                   # Optional (default: 60.0)
```

**Error Messages**:
```python
# Example validation error
ValueError: Invalid pool configuration: min_size (15) exceeds max_size (10)
Suggestion: Reduce POOL_MIN_SIZE or increase POOL_MAX_SIZE
```

---

### FR-008: Health Check Integration

**Requirement**: The connection pool must integrate with the server's health check endpoint to report database connectivity status.

**Acceptance Criteria**:
- Health check queries pool statistics (no database query)
- Response includes: status (healthy/degraded/unhealthy), connection counts, last check time
- Health check completes in <10ms (no blocking operations)
- Status transitions logged with reason and timestamp

**Health Status States**:
- `healthy`: All connections valid, no errors in last 60 seconds
- `degraded`: Some connections failed, but >=50% capacity available
- `unhealthy`: <50% capacity or all connections failed

**Health Check Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-12T14:30:00.000Z",
  "database": {
    "status": "connected",
    "pool": {
      "total": 5,
      "idle": 3,
      "active": 2,
      "waiting": 0
    },
    "latency_ms": 2.3,
    "last_error": null
  }
}
```

---

### FR-009: Connection Recycling

**Requirement**: Connections must be periodically recycled to prevent resource leaks and refresh stale connections.

**Acceptance Criteria**:
- Close connections after `max_queries` executions (default 50,000)
- Close connections after `max_connection_lifetime` seconds (default 1 hour)
- Close idle connections after `max_idle_time` seconds (default 60s)
- Recycling logged with connection ID and reason

**Recycling Triggers**:
1. **Query count**: Connection executed 50,000 queries → Close and replace
2. **Lifetime**: Connection open for 1 hour → Close and replace
3. **Idle time**: Connection idle for 60 seconds and pool > `min_size` → Close (don't replace)

**Recycling Behavior**:
- Only recycle idle connections (never force-close active connections)
- Maintain `min_size` connections at all times (recycle = close + replace)
- Recycling rate-limited to avoid thrashing (max 1 connection per second)

**Log Format**:
```
INFO: Connection recycled
  Connection ID: conn_12345
  Reason: max_queries_reached
  Lifetime: 3245 seconds
  Total queries: 50,001
```

---

### FR-010: Concurrency and Thread Safety

**Requirement**: The connection pool must be safe for concurrent access from multiple async tasks without race conditions or deadlocks.

**Acceptance Criteria**:
- All pool operations use async locks or atomic operations
- No race conditions in statistics tracking
- Connection acquisition queuing (FIFO) when pool is full
- Deadlock detection (connection request timeout)

**Concurrency Guarantees**:
- Multiple tasks can call `pool.acquire()` concurrently → Queued in FIFO order
- Statistics updates are atomic (no partial reads)
- Connection validation doesn't block other acquisitions
- Pool shutdown waits for all active connections (no orphaned connections)

**Deadlock Prevention**:
- Connection acquisition times out after `timeout` seconds (default 30s)
- Timeout raises `PoolTimeoutError` with details:
  ```python
  PoolTimeoutError: Failed to acquire connection within 30.0 seconds
    Pool state: total=10, idle=0, active=10, waiting=5
    Suggestion: Increase POOL_MAX_SIZE or investigate slow queries
  ```

---

## Success Criteria

### Quantitative Metrics

1. **Pool Initialization**: Completes in <2 seconds (p95)
2. **Connection Acquisition**: <10ms overhead for validation (p95)
3. **Health Check**: <10ms response time (p99)
4. **Reconnection**: Succeeds within 30 seconds of database recovery (p95)
5. **Shutdown**: Completes gracefully within 30 seconds (p99)
6. **Memory**: No connection leaks over 24-hour operation
7. **Statistics**: Real-time updates with <1ms staleness

### Qualitative Metrics

1. **Reliability**: No crashes or protocol violations during database outages
2. **Observability**: All connection lifecycle events logged clearly
3. **Configurability**: All timeouts and limits configurable via environment variables
4. **Documentation**: Configuration parameters documented with examples
5. **Error Messages**: Actionable suggestions included in all error messages

---

## Key Entities

### ConnectionPoolManager

**Description**: Top-level manager responsible for connection pool lifecycle and health monitoring.

**Responsibilities**:
- Initialize connection pool with validated configuration
- Monitor pool health and trigger reconnection attempts
- Expose pool statistics for observability
- Coordinate graceful shutdown

**Key Methods**:
```python
class ConnectionPoolManager:
    async def initialize(self, config: PoolConfig) -> None:
        """Initialize connection pool with config validation."""

    async def shutdown(self, timeout: float = 30.0) -> None:
        """Gracefully shutdown pool, waiting for active connections."""

    async def health_check(self) -> HealthStatus:
        """Query pool health without database query."""

    def get_statistics(self) -> PoolStatistics:
        """Get real-time pool statistics."""
```

**Lifecycle States**:
- `initializing`: Pool is being created
- `healthy`: All systems operational
- `degraded`: Some connections failed, reduced capacity
- `unhealthy`: Critical failure, attempting recovery
- `recovering`: Reconnection in progress
- `shutting_down`: Graceful shutdown initiated
- `terminated`: Pool closed and resources released

---

### ConnectionPool

**Description**: Low-level asyncpg connection pool wrapper with validation and recycling.

**Responsibilities**:
- Acquire and release database connections
- Validate connections before use
- Track connection metrics (queries executed, lifetime)
- Implement connection recycling policies

**Key Methods**:
```python
class ConnectionPool:
    async def acquire(self, timeout: float | None = None) -> Connection:
        """Acquire connection with validation and timeout."""

    async def release(self, connection: Connection) -> None:
        """Return connection to pool."""

    async def close(self) -> None:
        """Close all connections in pool."""

    def get_size(self) -> int:
        """Get current pool size."""

    def get_idle_size(self) -> int:
        """Get number of idle connections."""
```

**Connection Context Manager**:
```python
async with pool.acquire() as conn:
    result = await conn.fetchrow("SELECT * FROM repositories WHERE id = $1", repo_id)
```

---

### PoolStatistics

**Description**: Immutable snapshot of connection pool state for monitoring.

**Responsibilities**:
- Provide real-time pool metrics
- Track historical peaks for capacity planning
- Support serialization for health check API

**Schema**:
```python
@dataclass(frozen=True)
class PoolStatistics:
    total_connections: int
    idle_connections: int
    active_connections: int
    waiting_requests: int
    total_acquisitions: int
    total_releases: int
    avg_acquisition_time_ms: float
    peak_active_connections: int
    peak_wait_time_ms: float
    pool_created_at: datetime
    last_health_check: datetime

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSON responses."""
        return asdict(self)
```

---

## Edge Cases & Error Handling

### Database Server Restarts

**Scenario**: PostgreSQL server restarts while MCP server is running with active connections.

**Expected Behavior**:
1. Active queries fail with `ConnectionResetError`
2. Pool detects failure via health check
3. All connections marked invalid and closed
4. Automatic reconnection triggered with exponential backoff
5. Pool returns to `healthy` state after successful reconnection
6. Subsequent queries succeed automatically

**Error Handling**:
- Log all connection failures with timestamp
- Health check status: `healthy` → `unhealthy` → `recovering` → `healthy`
- No manual intervention required

---

### Connection Exhaustion Under High Load

**Scenario**: MCP server receives more concurrent requests than `max_size` allows.

**Expected Behavior**:
1. First `max_size` requests acquire connections immediately
2. Additional requests queue in FIFO order
3. `waiting_requests` counter increments
4. When connection released, first queued request acquires it
5. If request waits longer than `timeout` (30s), raise `PoolTimeoutError`

**Error Handling**:
- Log warning when `waiting_requests > 0` for >10 seconds
- Include pool statistics in timeout error message
- Suggest increasing `POOL_MAX_SIZE` in error message

---

### Partial Database Connectivity

**Scenario**: Some connections succeed, but others fail (e.g., database connection limit reached).

**Expected Behavior**:
1. Pool operates with reduced capacity (e.g., 3/10 connections)
2. Health check status: `degraded`
3. Requests queue if all available connections active
4. Log warning with current capacity: "Pool degraded: 3/10 connections available"

**Error Handling**:
- Don't fail server startup if `min_size` cannot be achieved
- Log detailed error with suggested actions (increase database connection limit)
- Continue attempting to create additional connections in background

---

### Configuration Conflicts

**Scenario**: User provides conflicting configuration (e.g., `min_size=15`, `max_size=10`).

**Expected Behavior**:
1. Configuration validation fails before pool creation
2. Raise `ValueError` with clear error message:
   ```
   ValueError: Invalid pool configuration: min_size (15) exceeds max_size (10)
   Suggestion: Reduce POOL_MIN_SIZE to 10 or increase POOL_MAX_SIZE to 15
   ```
3. Server fails to start (don't enter degraded state with invalid config)

**Error Handling**:
- Validate all configuration parameters before any initialization
- Provide actionable suggestions in error messages
- Document valid ranges for all parameters

---

### Long-Running Queries

**Scenario**: Query takes >30 seconds to execute (e.g., large repository indexing).

**Expected Behavior**:
1. Connection remains active (not recycled during query)
2. Leak detection warning logged after 30 seconds (if enabled)
3. Query completes successfully
4. Connection returned to pool after completion
5. Connection recycled if `max_connection_lifetime` exceeded

**Error Handling**:
- Allow per-operation `leak_detection_timeout` override:
   ```python
   async with pool.acquire(leak_detection_timeout=300.0) as conn:
       await long_running_indexing_operation(conn)
   ```
- Log warning, but don't terminate connection (false positive)

---

### Graceful Shutdown with Active Queries

**Scenario**: Server shutdown initiated while queries are still executing.

**Expected Behavior**:
1. Pool status: `healthy` → `shutting_down`
2. New connection requests rejected with `PoolClosedError`
3. Wait up to 30 seconds for active connections to finish
4. If active queries exceed timeout, log warning and force-close connections
5. All resources released, shutdown completes

**Error Handling**:
- Log warning for each force-closed connection with query details
- Ensure database transactions rolled back (no orphaned transactions)
- Release all file descriptors and memory

---

## Review & Acceptance Checklist

### Functional Completeness

- [ ] **FR-001**: Connection pool initializes with configurable min/max size
- [ ] **FR-002**: All connections validated before use with `SELECT 1` query
- [ ] **FR-003**: Automatic reconnection with exponential backoff (1s, 2s, 4s, 8s, 16s)
- [ ] **FR-004**: Pool statistics exposed via internal API and health check
- [ ] **FR-005**: Graceful shutdown waits for active connections (30s timeout)
- [ ] **FR-006**: Connection leak detection logs warnings after configurable timeout
- [ ] **FR-007**: Configuration validation fails fast on invalid input
- [ ] **FR-008**: Health check reports status (healthy/degraded/unhealthy) in <10ms
- [ ] **FR-009**: Connections recycled based on query count, lifetime, and idle time
- [ ] **FR-010**: All pool operations safe for concurrent async access

### Test Coverage

- [ ] **Unit Tests**: Connection pool lifecycle (init, acquire, release, shutdown)
- [ ] **Unit Tests**: Configuration validation (valid and invalid inputs)
- [ ] **Unit Tests**: Statistics tracking (atomic updates, peak metrics)
- [ ] **Integration Tests**: Database outage and automatic reconnection
- [ ] **Integration Tests**: Connection exhaustion and request queuing
- [ ] **Integration Tests**: Graceful shutdown with active queries
- [ ] **Integration Tests**: Connection recycling triggers
- [ ] **Load Tests**: Pool handles 100 concurrent requests without deadlock
- [ ] **Load Tests**: No memory leaks over 1 hour of continuous operation

### Documentation

- [ ] **Configuration Guide**: All parameters documented with defaults and ranges
- [ ] **Troubleshooting Guide**: Common issues and resolutions (outages, exhaustion, leaks)
- [ ] **Observability Guide**: How to interpret pool statistics and health check
- [ ] **API Documentation**: All public methods documented with examples

### Operational Readiness

- [ ] **Logging**: All connection lifecycle events logged (acquire, release, recycle, error)
- [ ] **Metrics**: Pool statistics exposed for monitoring tools (Prometheus integration planned)
- [ ] **Error Messages**: All errors include actionable suggestions
- [ ] **Resource Cleanup**: No leaks detected after shutdown (validated with memory profiler)

---

## Clarifications

This section tracks resolved ambiguities from the specification process.

### Q1: Should the pool support multiple database connections (multi-tenant)?

**Status**: ❌ Out of scope for Phase-04

**Reasoning**: This feature is designed for single-database deployments. Multi-tenancy would require significant architectural changes (connection pool per tenant, tenant-aware routing, etc.). The current scope assumes one MCP server instance = one PostgreSQL database.

**Future Consideration**: If multi-tenancy is required in the future, implement a `ConnectionPoolRegistry` that manages multiple `ConnectionPoolManager` instances keyed by tenant ID.

---

### Q2: What happens if `min_size` cannot be achieved during initialization?

**Status**: ✅ Clarified in FR-001

**Decision**: Server startup fails if `min_size` connections cannot be established within 3 retry attempts. This is a fail-fast approach to avoid starting in a degraded state.

**Rationale**: Starting with degraded capacity can lead to cascading failures. Better to fail startup and alert operators to fix the database configuration before retrying.

---

### Q3: Should connection validation use a custom query or rely on asyncpg's built-in checks?

**Status**: ✅ Clarified in FR-002

**Decision**: Use explicit `SELECT 1` validation query before returning connections from pool.

**Rationale**:
- asyncpg's built-in checks may not detect all stale connection scenarios
- Explicit validation provides consistent behavior across PostgreSQL versions
- Lightweight query adds minimal overhead (<5ms)

---

### Q4: How should the pool handle transient network issues (e.g., brief DNS failures)?

**Status**: ✅ Clarified in FR-003

**Decision**: Treat transient network issues the same as database outages: automatic reconnection with exponential backoff.

**Behavior**:
- DNS resolution failures → Retry connection with backoff
- SSL handshake failures → Retry connection with backoff
- Connection timeout → Retry connection with backoff

**Rationale**: All connection failures are indistinguishable from the pool's perspective. Unified handling simplifies error recovery logic.

---

### Q5: Should leak detection be configurable per environment (e.g., disabled in production)?

**Status**: ✅ Clarified in FR-006

**Decision**: Leak detection enabled by default with configurable timeout. Can be disabled via `POOL_ENABLE_LEAK_DETECTION=false`.

**Recommendation**:
- **Development**: Enable with short timeout (30s) to catch leaks early
- **Production**: Enable with longer timeout (300s) to avoid false positives from long-running operations

---

### Q6: What is the recommended `max_size` for typical deployments?

**Status**: ✅ Clarified in FR-001

**Guidance**:
- **Development**: `max_size=5` (sufficient for local testing)
- **Small Production**: `max_size=10` (1-10 concurrent users)
- **Medium Production**: `max_size=25` (10-50 concurrent users)
- **Large Production**: `max_size=50` (50+ concurrent users)

**Formula**: `max_size ≈ 2 × expected_concurrent_users`

**Important**: Ensure PostgreSQL `max_connections` is at least 2× your pool's `max_size` to account for admin connections and other clients.

---

## Non-Goals

This section explicitly documents what is **NOT** included in this feature to prevent scope creep.

### ❌ Read Replicas and Connection Routing

**Excluded**: Automatic routing of read queries to read replicas and write queries to primary.

**Reasoning**: This feature assumes a single-database deployment. Read replica support requires:
- Connection pool per database (primary + replicas)
- Query analysis to determine read vs. write
- Replica lag monitoring and failover logic

**Future Work**: Could be added in Phase-08 (High Availability) if needed.

---

### ❌ Connection Pool Sharing Across Multiple Servers

**Excluded**: Shared connection pool for multiple MCP server instances.

**Reasoning**: Each MCP server instance manages its own connection pool. Shared pools require:
- External connection broker (e.g., PgBouncer)
- Inter-process communication for pool coordination
- Complex failure domains

**Recommendation**: Use PgBouncer as a separate layer if connection pooling across servers is needed.

---

### ❌ Advanced Health Checks (Query Performance Monitoring)

**Excluded**: Health checks that execute complex queries to validate database performance.

**Reasoning**: Health checks must complete in <10ms. Complex queries (e.g., analyzing slow query logs) would violate this requirement.

**Future Work**: Query performance monitoring belongs in a separate observability feature (Phase-07+).

---

### ❌ Connection Pool Warmup Strategies

**Excluded**: Advanced warmup logic (e.g., pre-warming connections with schema caches).

**Reasoning**: Adds complexity with minimal benefit for this use case. The database is already initialized with schema before the server starts.

**Future Work**: If cold-start latency becomes an issue, consider warmup logic in Phase-07+.

---

### ❌ Dynamic Pool Resizing Based on Load

**Excluded**: Automatically adjusting `max_size` based on observed load patterns.

**Reasoning**: Requires machine learning or heuristics to predict load. Adds significant complexity and unpredictability.

**Recommendation**: Use static configuration with monitoring. Operators can adjust `POOL_MAX_SIZE` based on observed metrics.

---

### ❌ Connection-Level Tracing and Profiling

**Excluded**: Detailed per-connection tracing (e.g., query execution time, lock contention).

**Reasoning**: This is a deep observability feature that belongs in a separate profiling tool, not in the core connection pool.

**Future Work**: Integration with OpenTelemetry or Jaeger could provide this in Phase-07+.

---

## Additional Context

### Dependency Chain

Phase-04 (Connection Management) is a **foundational dependency** for:

- **Phase-05 (Repository Indexing)**: Requires connection pool for database operations
- **Phase-06 (Semantic Search)**: Requires connection pool for vector search queries
- **Phase-07+ (Future Phases)**: All database-dependent features rely on this infrastructure

**Critical Path**: Phase-04 must be completed and validated before Phase-05 can begin implementation.

---

### Related Documentation

- **Database Schema**: See `docs/mcp-split-plan/phases/phase-05-indexing/schema.sql` for table definitions
- **MCP Protocol**: Connection pool must not block MCP SSE responses (non-blocking async operations)
- **asyncpg Documentation**: https://magicstack.github.io/asyncpg/current/

---

### Performance Baselines

**Target Metrics** (to be validated in Phase-04 testing):

| Metric | Target | Rationale |
|--------|--------|-----------|
| Pool Initialization | <2s (p95) | Fast server startup |
| Connection Acquisition | <10ms (p95) | Minimal overhead |
| Health Check Response | <10ms (p99) | Real-time monitoring |
| Reconnection (post-outage) | <30s (p95) | Acceptable recovery time |
| Graceful Shutdown | <30s (p99) | No forced connection kills |

---

### Security Considerations

1. **Connection String Exposure**: `DATABASE_URL` contains credentials
   - **Mitigation**: Load from environment variables, never log connection strings
   - **Future**: Support PostgreSQL password file (~/.pgpass)

2. **Connection Hijacking**: Malicious code could hold connections indefinitely
   - **Mitigation**: Leak detection and forced recycling after `max_connection_lifetime`

3. **SQL Injection**: Not applicable to connection pool (query execution is handled by repository/search layers)

---

### Known Limitations

1. **Single Database**: No support for multiple databases or multi-tenancy
2. **No Failover**: If primary database fails, server becomes unavailable (no automatic replica promotion)
3. **No Load Balancing**: All connections go to single database endpoint (no read replica routing)

These limitations are acceptable for Phase-04's scope and can be addressed in future phases if needed.

---

## Appendix: Example Usage

### Basic Connection Pool Usage

```python
from codebase_mcp.connection import ConnectionPoolManager, PoolConfig

# Initialize pool
config = PoolConfig(min_size=2, max_size=10, timeout=30.0)
pool_manager = ConnectionPoolManager(config)
await pool_manager.initialize()

# Acquire connection and execute query
async with pool_manager.pool.acquire() as conn:
    result = await conn.fetchrow("SELECT * FROM repositories WHERE id = $1", repo_id)

# Check pool health
health = await pool_manager.health_check()
print(f"Pool status: {health.status}")

# Get statistics
stats = pool_manager.get_statistics()
print(f"Active connections: {stats.active_connections}/{stats.total_connections}")

# Graceful shutdown
await pool_manager.shutdown(timeout=30.0)
```

### Configuration via Environment Variables

```bash
# Required
export DATABASE_URL="postgresql+asyncpg://localhost/codebase_mcp"

# Optional (defaults shown)
export POOL_MIN_SIZE=2
export POOL_MAX_SIZE=10
export POOL_TIMEOUT=30.0
export POOL_MAX_IDLE_TIME=60.0
export POOL_MAX_QUERIES=50000
export POOL_MAX_CONNECTION_LIFETIME=3600.0
export POOL_LEAK_DETECTION_TIMEOUT=30.0
export POOL_ENABLE_LEAK_DETECTION=true

# Start server
python -m codebase_mcp.server
```

### Health Check Response Example

```json
{
  "status": "healthy",
  "timestamp": "2025-10-12T14:30:00.000Z",
  "database": {
    "status": "connected",
    "pool": {
      "total": 5,
      "idle": 3,
      "active": 2,
      "waiting": 0,
      "total_acquisitions": 1523,
      "avg_acquisition_time_ms": 2.8,
      "peak_active_connections": 8
    },
    "last_error": null,
    "last_health_check": "2025-10-12T14:29:55.000Z"
  }
}
```

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-12 | Claude (AI Assistant) | Initial enhanced specification draft |

---

**END OF SPECIFICATION**
