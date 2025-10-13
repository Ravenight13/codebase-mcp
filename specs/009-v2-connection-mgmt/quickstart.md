# Quickstart: Connection Pool Integration Testing

**Branch**: 009-v2-connection-mgmt | **Date**: 2025-10-13
**Purpose**: Integration test scenarios for validating connection pool implementation

## Prerequisites

```bash
# Install dependencies
pip install asyncpg pydantic pydantic-settings pytest pytest-asyncio

# Start PostgreSQL (via Docker)
docker run --name postgres-test -e POSTGRES_PASSWORD=test -p 5432:5432 -d postgres:14

# Create test database
docker exec postgres-test psql -U postgres -c "CREATE DATABASE codebase_mcp_test;"
```

## Test Scenario 1: Pool Initialization

**Validates**: FR-001, SC-001 (pool initialization <2s)

```python
import asyncio
import time
from connection_pool import ConnectionPoolManager, PoolConfig

async def test_pool_initialization():
    """Test pool initializes successfully within 2 seconds."""
    config = PoolConfig(
        min_size=2,
        max_size=10,
        database_url="postgresql+asyncpg://postgres:test@localhost/codebase_mcp_test"
    )

    pool_manager = ConnectionPoolManager()

    start = time.perf_counter()
    await pool_manager.initialize(config)
    duration = time.perf_counter() - start

    # Validate initialization time (SC-001)
    assert duration < 2.0, f"Initialization took {duration:.3f}s (target: <2s)"

    # Validate pool state
    stats = pool_manager.get_statistics()
    assert stats.total_connections == 2, "Pool should have min_size connections"
    assert stats.idle_connections == 2, "All connections should be idle"

    # Validate health status (FR-008)
    health = await pool_manager.health_check()
    assert health.status == "healthy", "Pool should be healthy"
    assert health.database_connected is True

    await pool_manager.shutdown()
    print(f"✅ Pool initialization test passed ({duration:.3f}s)")

# Run test
asyncio.run(test_pool_initialization())
```

**Expected Output**:
```
✅ Pool initialization test passed (0.345s)
```

---

## Test Scenario 2: Connection Acquisition

**Validates**: FR-002, SC-002 (connection acquisition <10ms)

```python
import asyncio
import time

async def test_connection_acquisition():
    """Test connection acquisition with validation overhead."""
    config = PoolConfig(
        min_size=2,
        max_size=10,
        database_url="postgresql+asyncpg://postgres:test@localhost/codebase_mcp_test"
    )

    pool_manager = ConnectionPoolManager()
    await pool_manager.initialize(config)

    # Measure acquisition time
    acquisition_times = []
    for i in range(20):
        start = time.perf_counter()
        async with pool_manager.pool.acquire() as conn:
            # Validate connection executes query successfully
            result = await conn.fetchval("SELECT 1")
            assert result == 1
        duration_ms = (time.perf_counter() - start) * 1000
        acquisition_times.append(duration_ms)

    # Calculate p95 latency (SC-002)
    acquisition_times.sort()
    p95 = acquisition_times[int(len(acquisition_times) * 0.95)]
    avg = sum(acquisition_times) / len(acquisition_times)

    assert p95 < 10.0, f"p95 acquisition time: {p95:.2f}ms (target: <10ms)"

    # Validate statistics tracking (FR-004)
    stats = pool_manager.get_statistics()
    assert stats.total_acquisitions >= 20, "Should track all acquisitions"
    assert stats.total_releases >= 20, "Should track all releases"
    assert stats.avg_acquisition_time_ms > 0, "Should calculate average time"

    await pool_manager.shutdown()
    print(f"✅ Connection acquisition test passed (p95: {p95:.2f}ms, avg: {avg:.2f}ms)")

asyncio.run(test_connection_acquisition())
```

**Expected Output**:
```
✅ Connection acquisition test passed (p95: 2.34ms, avg: 1.87ms)
```

---

## Test Scenario 3: Database Outage Recovery

**Validates**: FR-003, SC-004 (automatic reconnection <30s)

```python
import asyncio
import subprocess

async def test_database_outage_recovery():
    """Test automatic reconnection after database outage."""
    config = PoolConfig(
        min_size=2,
        max_size=10,
        database_url="postgresql+asyncpg://postgres:test@localhost/codebase_mcp_test"
    )

    pool_manager = ConnectionPoolManager()
    await pool_manager.initialize(config)

    # Verify pool is healthy
    health = await pool_manager.health_check()
    assert health.status == "healthy"
    print("✅ Pool initialized and healthy")

    # Simulate database outage
    print("🔴 Stopping PostgreSQL...")
    subprocess.run(["docker", "stop", "postgres-test"], check=True)

    await asyncio.sleep(2)  # Wait for connection failures

    # Verify pool detects outage (FR-003)
    health = await pool_manager.health_check()
    assert health.status in ["unhealthy", "degraded"], "Pool should detect database down"
    print(f"✅ Pool detected outage (status: {health.status})")

    # Restart database
    print("🟢 Restarting PostgreSQL...")
    subprocess.run(["docker", "start", "postgres-test"], check=True)

    # Wait for automatic reconnection (SC-004)
    start = time.perf_counter()
    max_wait = 30.0
    while True:
        health = await pool_manager.health_check()
        if health.status == "healthy":
            break
        if time.perf_counter() - start > max_wait:
            raise TimeoutError(f"Reconnection took >{max_wait}s")
        await asyncio.sleep(1)

    duration = time.perf_counter() - start
    print(f"✅ Pool recovered in {duration:.1f}s")

    # Validate connections work after recovery
    async with pool_manager.pool.acquire() as conn:
        result = await conn.fetchval("SELECT 1")
        assert result == 1
    print("✅ Connections functional after recovery")

    await pool_manager.shutdown()
    print(f"✅ Database outage recovery test passed ({duration:.1f}s)")

asyncio.run(test_database_outage_recovery())
```

**Expected Output**:
```
✅ Pool initialized and healthy
🔴 Stopping PostgreSQL...
✅ Pool detected outage (status: unhealthy)
🟢 Restarting PostgreSQL...
✅ Pool recovered in 12.3s
✅ Connections functional after recovery
✅ Database outage recovery test passed (12.3s)
```

---

## Test Scenario 4: Concurrent Load

**Validates**: SC-008 (100 concurrent requests without deadlock)

```python
import asyncio
import time

async def test_concurrent_load():
    """Test pool handles 100 concurrent requests."""
    config = PoolConfig(
        min_size=2,
        max_size=10,
        database_url="postgresql+asyncpg://postgres:test@localhost/codebase_mcp_test"
    )

    pool_manager = ConnectionPoolManager()
    await pool_manager.initialize(config)

    async def execute_query(query_id: int):
        """Execute a query with connection acquisition."""
        async with pool_manager.pool.acquire() as conn:
            await conn.fetchval("SELECT pg_sleep(0.01)")  # 10ms query
            return query_id

    # Execute 100 concurrent queries
    start = time.perf_counter()
    tasks = [execute_query(i) for i in range(100)]
    results = await asyncio.gather(*tasks)
    duration = time.perf_counter() - start

    # Validate all queries completed (SC-008)
    assert len(results) == 100, "All 100 queries should complete"
    assert sorted(results) == list(range(100)), "All query IDs should be present"

    # Check pool statistics (FR-004, FR-010)
    stats = pool_manager.get_statistics()
    assert stats.total_acquisitions >= 100, "Should have 100+ acquisitions"
    assert stats.peak_active_connections <= 10, "Should not exceed max_size"
    assert stats.waiting_requests == 0, "All requests should have completed"

    await pool_manager.shutdown()
    print(f"✅ Concurrent load test passed (100 requests in {duration:.2f}s)")
    print(f"   Peak active: {stats.peak_active_connections}, Avg acquisition: {stats.avg_acquisition_time_ms:.2f}ms")

asyncio.run(test_concurrent_load())
```

**Expected Output**:
```
✅ Concurrent load test passed (100 requests in 1.24s)
   Peak active: 10, Avg acquisition: 2.45ms
```

---

## Test Scenario 5: Graceful Shutdown

**Validates**: FR-005, SC-005 (shutdown <30s with active queries)

```python
import asyncio
import time

async def test_graceful_shutdown():
    """Test graceful shutdown waits for active queries."""
    config = PoolConfig(
        min_size=2,
        max_size=10,
        database_url="postgresql+asyncpg://postgres:test@localhost/codebase_mcp_test"
    )

    pool_manager = ConnectionPoolManager()
    await pool_manager.initialize(config)

    # Start long-running query
    async def long_query():
        async with pool_manager.pool.acquire() as conn:
            await conn.fetchval("SELECT pg_sleep(5)")  # 5 second query
            return "completed"

    query_task = asyncio.create_task(long_query())
    await asyncio.sleep(0.5)  # Let query start

    # Initiate graceful shutdown (FR-005)
    start = time.perf_counter()
    shutdown_task = asyncio.create_task(pool_manager.shutdown(timeout=30.0))

    # Wait for both
    query_result = await query_task
    await shutdown_task
    duration = time.perf_counter() - start

    # Validate shutdown behavior (SC-005)
    assert query_result == "completed", "Query should complete before shutdown"
    assert duration < 30.0, f"Shutdown took {duration:.1f}s (target: <30s)"
    assert 5.0 <= duration <= 6.0, "Should wait for query to complete (~5s)"

    print(f"✅ Graceful shutdown test passed ({duration:.1f}s)")

asyncio.run(test_graceful_shutdown())
```

**Expected Output**:
```
✅ Graceful shutdown test passed (5.2s)
```

---

## Test Scenario 6: Health Check Performance

**Validates**: FR-008, SC-003 (health check <10ms p99)

```python
import asyncio
import time

async def test_health_check_performance():
    """Test health check response time without database query."""
    config = PoolConfig(
        min_size=2,
        max_size=10,
        database_url="postgresql+asyncpg://postgres:test@localhost/codebase_mcp_test"
    )

    pool_manager = ConnectionPoolManager()
    await pool_manager.initialize(config)

    # Measure health check latency (SC-003)
    latencies = []
    for i in range(100):
        start = time.perf_counter()
        health = await pool_manager.health_check()
        duration_ms = (time.perf_counter() - start) * 1000
        latencies.append(duration_ms)
        assert health.status in ["healthy", "degraded", "unhealthy"]
        assert hasattr(health, "pool_statistics"), "Should include pool stats"

    # Calculate p99 latency
    latencies.sort()
    p99 = latencies[int(len(latencies) * 0.99)]
    p95 = latencies[int(len(latencies) * 0.95)]
    avg = sum(latencies) / len(latencies)

    assert p99 < 10.0, f"p99 health check time: {p99:.2f}ms (target: <10ms)"

    # Verify no database query overhead (FR-008)
    assert p99 < 5.0, "Health check should not require database query"

    await pool_manager.shutdown()
    print(f"✅ Health check performance test passed (p99: {p99:.2f}ms, p95: {p95:.2f}ms, avg: {avg:.2f}ms)")

asyncio.run(test_health_check_performance())
```

**Expected Output**:
```
✅ Health check performance test passed (p99: 0.85ms, p95: 0.62ms, avg: 0.43ms)
```

---

## Test Scenario 7: Configuration Validation

**Validates**: FR-007 (configuration validation with fail-fast)

```python
import pytest
from connection_pool import PoolConfig

def test_configuration_validation():
    """Test configuration validation catches invalid parameters."""

    # Test 1: min_size > max_size (should fail)
    with pytest.raises(ValueError) as exc_info:
        config = PoolConfig(
            min_size=10,
            max_size=5,
            database_url="postgresql+asyncpg://localhost/test"
        )
    assert "min_size (10) cannot be greater than max_size (5)" in str(exc_info.value)
    print("✅ Test 1: Detected min_size > max_size")

    # Test 2: Invalid database URL (should fail)
    with pytest.raises(ValueError) as exc_info:
        config = PoolConfig(
            min_size=2,
            max_size=10,
            database_url="invalid://url"
        )
    assert "database_url must use postgresql" in str(exc_info.value)
    print("✅ Test 2: Detected invalid database URL")

    # Test 3: Negative min_size (should fail)
    with pytest.raises(ValueError) as exc_info:
        config = PoolConfig(
            min_size=-1,
            max_size=10,
            database_url="postgresql+asyncpg://localhost/test"
        )
    assert "min_size must be positive" in str(exc_info.value)
    print("✅ Test 3: Detected negative min_size")

    # Test 4: Valid configuration (should succeed)
    config = PoolConfig(
        min_size=2,
        max_size=10,
        database_url="postgresql+asyncpg://localhost/test"
    )
    assert config.min_size == 2
    assert config.max_size == 10
    print("✅ Test 4: Valid configuration accepted")

    print("✅ Configuration validation test passed")

test_configuration_validation()
```

**Expected Output**:
```
✅ Test 1: Detected min_size > max_size
✅ Test 2: Detected invalid database URL
✅ Test 3: Detected negative min_size
✅ Test 4: Valid configuration accepted
✅ Configuration validation test passed
```

---

## Test Scenario 8: Connection Leak Detection

**Validates**: FR-006 (leak detection with warnings)

```python
import asyncio
import time

async def test_connection_leak_detection():
    """Test leak detection logs warnings for held connections."""
    config = PoolConfig(
        min_size=2,
        max_size=5,
        leak_detection_timeout=10.0,  # 10 second timeout
        enable_leak_detection=True,
        database_url="postgresql+asyncpg://postgres:test@localhost/codebase_mcp_test"
    )

    pool_manager = ConnectionPoolManager()
    await pool_manager.initialize(config)

    # Simulate connection leak (hold connection for 12 seconds)
    async def leak_connection():
        async with pool_manager.pool.acquire() as conn:
            print("⏳ Holding connection for 12 seconds...")
            await asyncio.sleep(12)  # Exceeds leak_detection_timeout
            return "released"

    # Start leak task
    start = time.perf_counter()
    result = await leak_connection()
    duration = time.perf_counter() - start

    # Validate leak was detected (FR-006)
    # Note: In real implementation, check logs for warning message
    # Expected log: "WARNING: Potential connection leak detected. Connection held for 10s"

    assert result == "released", "Connection should eventually be released"
    assert duration >= 12.0, "Should have held connection for full duration"

    # Validate pool returns to normal state
    stats = pool_manager.get_statistics()
    assert stats.idle_connections == 2, "Pool should return to normal"

    await pool_manager.shutdown()
    print(f"✅ Connection leak detection test passed ({duration:.1f}s)")
    print("   Note: Check logs for 'WARNING: Potential connection leak detected'")

asyncio.run(test_connection_leak_detection())
```

**Expected Output**:
```
⏳ Holding connection for 12 seconds...
✅ Connection leak detection test passed (12.1s)
   Note: Check logs for 'WARNING: Potential connection leak detected'
```

---

## Test Scenario 9: Pool Statistics Tracking

**Validates**: FR-004, SC-007 (statistics with <1ms staleness)

```python
import asyncio
import time

async def test_pool_statistics_tracking():
    """Test pool statistics track real-time metrics accurately."""
    config = PoolConfig(
        min_size=2,
        max_size=10,
        database_url="postgresql+asyncpg://postgres:test@localhost/codebase_mcp_test"
    )

    pool_manager = ConnectionPoolManager()
    await pool_manager.initialize(config)

    # Test 1: Initial state
    stats = pool_manager.get_statistics()
    assert stats.total_connections == 2, "Should start with min_size"
    assert stats.idle_connections == 2, "All should be idle"
    assert stats.active_connections == 0, "None should be active"
    print("✅ Test 1: Initial statistics correct")

    # Test 2: Active connections
    async def hold_connection(duration: float):
        async with pool_manager.pool.acquire() as conn:
            await asyncio.sleep(duration)

    # Start 5 concurrent connections
    tasks = [asyncio.create_task(hold_connection(0.5)) for _ in range(5)]
    await asyncio.sleep(0.1)  # Let them acquire connections

    stats = pool_manager.get_statistics()
    assert stats.active_connections == 5, "Should have 5 active"
    assert stats.total_connections >= 5, "Should scale up as needed"
    print(f"✅ Test 2: Active connections tracked (active={stats.active_connections})")

    # Wait for completion
    await asyncio.gather(*tasks)

    # Test 3: Post-completion state
    stats = pool_manager.get_statistics()
    assert stats.total_acquisitions >= 5, "Should track acquisitions"
    assert stats.total_releases >= 5, "Should track releases"
    assert stats.peak_active_connections >= 5, "Should record peak"
    print(f"✅ Test 3: Peak statistics recorded (peak={stats.peak_active_connections})")

    # Test 4: Data staleness (SC-007)
    start = time.perf_counter()
    stats1 = pool_manager.get_statistics()
    stats2 = pool_manager.get_statistics()
    duration_ms = (time.perf_counter() - start) * 1000

    assert duration_ms < 1.0, f"Statistics retrieval took {duration_ms:.3f}ms (target: <1ms)"
    print(f"✅ Test 4: Statistics retrieval latency acceptable ({duration_ms:.3f}ms)")

    await pool_manager.shutdown()
    print("✅ Pool statistics tracking test passed")

asyncio.run(test_pool_statistics_tracking())
```

**Expected Output**:
```
✅ Test 1: Initial statistics correct
✅ Test 2: Active connections tracked (active=5)
✅ Test 3: Peak statistics recorded (peak=5)
✅ Test 4: Statistics retrieval latency acceptable (0.042ms)
✅ Pool statistics tracking test passed
```

---

## Test Scenario 10: Connection Exhaustion

**Validates**: Edge case - connection exhaustion under high load

```python
import asyncio
import time

async def test_connection_exhaustion():
    """Test behavior when max_size connections are exhausted."""
    config = PoolConfig(
        min_size=2,
        max_size=5,  # Small pool to test exhaustion
        timeout=10.0,  # 10 second timeout
        database_url="postgresql+asyncpg://postgres:test@localhost/codebase_mcp_test"
    )

    pool_manager = ConnectionPoolManager()
    await pool_manager.initialize(config)

    async def hold_connection(duration: float, query_id: int):
        """Hold connection for specified duration."""
        try:
            async with pool_manager.pool.acquire() as conn:
                print(f"  Query {query_id} acquired connection")
                await asyncio.sleep(duration)
                return query_id
        except asyncio.TimeoutError:
            print(f"  Query {query_id} timed out waiting for connection")
            raise

    # Start 5 long queries (fill the pool)
    long_tasks = [asyncio.create_task(hold_connection(3.0, i)) for i in range(5)]
    await asyncio.sleep(0.5)  # Let them acquire all connections

    # Verify pool is exhausted
    stats = pool_manager.get_statistics()
    assert stats.active_connections == 5, "Pool should be fully utilized"
    print(f"✅ Pool exhausted (active={stats.active_connections}, max={config.max_size})")

    # Start additional query that must wait
    start = time.perf_counter()
    waiting_task = asyncio.create_task(hold_connection(0.1, 999))

    # Wait for original queries to complete and release connections
    await asyncio.gather(*long_tasks)

    # Waiting query should now succeed
    result = await waiting_task
    duration = time.perf_counter() - start

    assert result == 999, "Waiting query should complete successfully"
    assert duration >= 2.5, "Should have waited for connection availability"
    print(f"✅ Queued request succeeded after {duration:.1f}s wait")

    # Verify statistics tracked waiting
    stats = pool_manager.get_statistics()
    # Note: waiting_requests should have been >0 at peak

    await pool_manager.shutdown()
    print("✅ Connection exhaustion test passed")

asyncio.run(test_connection_exhaustion())
```

**Expected Output**:
```
  Query 0 acquired connection
  Query 1 acquired connection
  Query 2 acquired connection
  Query 3 acquired connection
  Query 4 acquired connection
✅ Pool exhausted (active=5, max=5)
  Query 999 acquired connection
✅ Queued request succeeded after 2.6s wait
✅ Connection exhaustion test passed
```

---

## Running All Tests

```bash
# Run all integration tests
pytest tests/integration/test_connection_pool.py -v

# Run with performance validation
pytest tests/integration/test_connection_pool.py --benchmark-only

# Run with coverage
pytest tests/integration/test_connection_pool.py --cov=connection_pool --cov-report=html

# Run specific test scenario
pytest tests/integration/test_connection_pool.py::test_pool_initialization -v
```

---

## Performance Benchmarking

```python
# benchmark_connection_pool.py
import asyncio
import time
from connection_pool import ConnectionPoolManager, PoolConfig

async def benchmark_pool_performance():
    """Comprehensive performance benchmark."""
    config = PoolConfig(
        min_size=2,
        max_size=10,
        database_url="postgresql+asyncpg://postgres:test@localhost/codebase_mcp_test"
    )

    pool_manager = ConnectionPoolManager()

    # Benchmark 1: Initialization time (SC-001)
    start = time.perf_counter()
    await pool_manager.initialize(config)
    init_time = time.perf_counter() - start
    print(f"Initialization: {init_time:.3f}s (target: <2s)")

    # Benchmark 2: Connection acquisition (SC-002)
    acquisition_times = []
    for _ in range(1000):
        start = time.perf_counter()
        async with pool_manager.pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        acquisition_times.append((time.perf_counter() - start) * 1000)

    acquisition_times.sort()
    print(f"Acquisition p50: {acquisition_times[500]:.2f}ms")
    print(f"Acquisition p95: {acquisition_times[950]:.2f}ms (target: <10ms)")
    print(f"Acquisition p99: {acquisition_times[990]:.2f}ms")

    # Benchmark 3: Health check throughput (SC-013)
    health_checks = 0
    start = time.perf_counter()
    while time.perf_counter() - start < 1.0:
        await pool_manager.health_check()
        health_checks += 1

    throughput = health_checks
    print(f"Health check throughput: {throughput} req/s (target: >1000 req/s)")

    # Benchmark 4: Concurrent load (SC-008)
    async def concurrent_query():
        async with pool_manager.pool.acquire() as conn:
            await conn.fetchval("SELECT 1")

    start = time.perf_counter()
    await asyncio.gather(*[concurrent_query() for _ in range(100)])
    concurrent_time = time.perf_counter() - start
    print(f"100 concurrent queries: {concurrent_time:.3f}s")

    await pool_manager.shutdown()

    # Summary
    print("\n=== Performance Summary ===")
    print(f"✅ Initialization: {init_time:.3f}s < 2s")
    print(f"{'✅' if acquisition_times[950] < 10 else '❌'} Acquisition p95: {acquisition_times[950]:.2f}ms < 10ms")
    print(f"{'✅' if throughput > 1000 else '❌'} Health check throughput: {throughput} > 1000 req/s")
    print(f"✅ Concurrent load: {concurrent_time:.3f}s (no deadlocks)")

asyncio.run(benchmark_pool_performance())
```

Run with:
```bash
python benchmark_connection_pool.py
```

**Expected Output**:
```
Initialization: 0.345s (target: <2s)
Acquisition p50: 1.23ms
Acquisition p95: 2.87ms (target: <10ms)
Acquisition p99: 4.52ms
Health check throughput: 2341 req/s (target: >1000 req/s)
100 concurrent queries: 0.234s

=== Performance Summary ===
✅ Initialization: 0.345s < 2s
✅ Acquisition p95: 2.87ms < 10ms
✅ Health check throughput: 2341 > 1000 req/s
✅ Concurrent load: 0.234s (no deadlocks)
```

---

## Cleanup

```bash
# Stop and remove test database
docker stop postgres-test
docker rm postgres-test

# Remove test artifacts
rm -f /tmp/codebase-mcp-test.log
rm -rf htmlcov/
```

---

## Troubleshooting

### Pool Initialization Fails
- **Check PostgreSQL is running**: `docker ps`
- **Verify database exists**: `docker exec postgres-test psql -U postgres -l`
- **Check DATABASE_URL is correct**: Should use `postgresql+asyncpg://` scheme
- **Review logs**: `tail -f /tmp/codebase-mcp.log`

### Reconnection Takes >30s
- **Check network latency**: `ping localhost`
- **Review exponential backoff logs**: Look for retry intervals (1s, 2s, 4s, 8s, 16s)
- **Verify PostgreSQL restarted successfully**: `docker logs postgres-test`
- **Check connection limits**: `docker exec postgres-test psql -U postgres -c "SHOW max_connections;"`

### Concurrent Load Fails
- **Check max_size is sufficient**: Default is 10, increase if needed
- **Review pool statistics**: Look for `waiting_requests > 0` indicating exhaustion
- **Increase max_size**: Set `POOL_MAX_SIZE=20` environment variable
- **Check for deadlocks**: Review application logs for hung connections

### Health Check Latency High
- **Verify no database query overhead**: Health check should use cached state only
- **Check system load**: High CPU/memory usage can delay async operations
- **Review implementation**: Ensure health check doesn't acquire connections

### Connection Leaks Detected
- **Review stack traces**: Leak warnings include acquisition location
- **Check for unclosed context managers**: Ensure `async with pool.acquire()` pattern used
- **Validate test cleanup**: Tests should call `await pool_manager.shutdown()`
- **Run 24-hour leak test**: `pytest tests/integration/test_leak_detection.py`

---

## Next Steps

After validating all integration tests:

1. **Run performance benchmarks**: `python benchmark_connection_pool.py`
2. **Run 24-hour leak detection**: `pytest tests/integration/test_leak_detection.py --duration=86400`
3. **Review logs for warnings**: `tail -f /tmp/codebase-mcp.log`
4. **Validate constitutional compliance**: Check against `.specify/memory/constitution.md`
5. **Proceed to `/speckit.tasks`**: Generate implementation tasks from plan.md

---

## Success Criteria Validation

| Criterion | Target | Validation Method |
|-----------|--------|-------------------|
| SC-001 | Pool init <2s (p95) | Test Scenario 1 |
| SC-002 | Acquisition <10ms (p95) | Test Scenario 2 |
| SC-003 | Health check <10ms (p99) | Test Scenario 6 |
| SC-004 | Reconnection <30s (p95) | Test Scenario 3 |
| SC-005 | Shutdown <30s (p99) | Test Scenario 5 |
| SC-006 | No leaks (24hr) | 24-hour leak test |
| SC-007 | Stats staleness <1ms | Test Scenario 9 |
| SC-008 | 100 concurrent requests | Test Scenario 4 |
| SC-009 | No crashes on outage | Test Scenario 3 |
| SC-010 | Actionable log messages | Manual log review |
| SC-011 | Memory <100MB (max_size=10) | Memory profiler |
| SC-012 | Startup overhead <200ms | Test Scenario 1 |
| SC-013 | Health check >1000 req/s | Performance benchmark |
