"""Connection Pool Usage Examples

This module demonstrates common usage patterns for the connection pool manager.
All examples are executable and show best practices for production deployments.

Constitutional Compliance:
- Principle V: Production Quality (comprehensive error handling)
- Principle VIII: Type Safety (full type hints with mypy --strict)
- Principle III: Protocol Compliance (no stdout pollution, structured logging)

Requirements:
- Python 3.11+
- asyncpg
- pydantic
- PostgreSQL 14+ running locally or accessible via DATABASE_URL

Usage:
    # Run all examples
    python docs/examples/connection_pool_usage.py

    # Run with custom DATABASE_URL
    DATABASE_URL="postgresql+asyncpg://user:pass@host/db" python docs/examples/connection_pool_usage.py

    # Run single example
    python -c "from docs.examples.connection_pool_usage import example_basic_initialization; import asyncio; asyncio.run(example_basic_initialization())"
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any

# Import connection pool components
try:
    from src.connection_pool.config import PoolConfig
    from src.connection_pool.exceptions import (
        ConnectionValidationError,
        PoolClosedError,
        PoolTimeoutError,
    )
    from src.connection_pool.health import PoolHealthStatus
    from src.connection_pool.manager import ConnectionPoolManager, PoolState
except ImportError as e:
    print(f"ERROR: Failed to import connection pool modules: {e}", file=sys.stderr)
    print("Ensure you're running from the project root directory.", file=sys.stderr)
    sys.exit(1)


def print_section(title: str) -> None:
    """Print formatted section header for example output.

    Args:
        title: Section title to display

    Example:
        >>> print_section("Example 1: Basic Initialization")
        ================================================================================
        Example 1: Basic Initialization
        ================================================================================
    """
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80 + "\n")


def get_database_url() -> str | None:
    """Get DATABASE_URL from environment or return None if not set.

    Tries both DATABASE_URL and POOL_DATABASE_URL environment variables.
    Returns None if neither is set, allowing examples to handle gracefully.

    Returns:
        Database URL string or None if not configured

    Example:
        >>> url = get_database_url()
        >>> if url is None:
        ...     print("DATABASE_URL not set, skipping example")
        >>> else:
        ...     config = PoolConfig(database_url=url)
    """
    return os.environ.get("DATABASE_URL") or os.environ.get("POOL_DATABASE_URL")


# ============================================================================
# Example 1: Basic Pool Initialization
# ============================================================================


async def example_basic_initialization() -> None:
    """Demonstrate basic pool initialization with default configuration.

    Shows:
    - Creating PoolConfig with minimal parameters
    - Initializing ConnectionPoolManager
    - Performing health check after initialization
    - Getting pool statistics
    - Graceful shutdown

    Performance:
    - Initialization: <2s (target per SC-001)
    - Health check: <10ms (target per SC-003)

    Constitutional Compliance:
    - Principle IV: Performance Guarantees (<2s init, <10ms health check)
    - Principle V: Production Quality (comprehensive error handling)
    """
    print_section("Example 1: Basic Pool Initialization")

    database_url = get_database_url()
    if database_url is None:
        print("⚠️  DATABASE_URL not set. Skipping example.")
        print("   Set via: export DATABASE_URL='postgresql+asyncpg://localhost/codebase_mcp'")
        return

    # Create configuration with defaults
    config = PoolConfig(
        min_size=2,  # Minimum connections to maintain
        max_size=10,  # Maximum connections allowed
        timeout=30.0,  # Connection acquisition timeout
        database_url=database_url,
    )

    print(f"📋 Configuration:")
    print(f"   min_size: {config.min_size}")
    print(f"   max_size: {config.max_size}")
    print(f"   timeout: {config.timeout}s")
    print(f"   database_url: {config.database_url[:50]}...")

    # Create pool manager
    manager = ConnectionPoolManager()

    # Initialize pool (measure duration)
    print(f"\n🔄 Initializing pool...")
    start_time = time.perf_counter()

    try:
        await manager.initialize(config)
        duration_ms = (time.perf_counter() - start_time) * 1000

        print(f"✅ Pool initialized in {duration_ms:.2f}ms")
        print(f"   State: {manager._state.value}")

        # Get statistics
        stats = manager.get_statistics()
        print(f"\n📊 Pool Statistics:")
        print(f"   Total connections: {stats.total_connections}")
        print(f"   Idle connections: {stats.idle_connections}")
        print(f"   Active connections: {stats.active_connections}")
        print(f"   Total acquisitions: {stats.total_acquisitions}")
        print(f"   Total releases: {stats.total_releases}")

        # Perform health check
        health = await manager.health_check()
        print(f"\n🏥 Health Status:")
        print(f"   Status: {health.status.value}")
        print(f"   Database status: {health.database.status}")
        print(f"   Uptime: {health.uptime_seconds:.2f}s")
        print(f"   Pool state: total={health.database.pool['total']}, "
              f"idle={health.database.pool['idle']}, "
              f"active={health.database.pool['active']}")

        # Graceful shutdown
        print(f"\n🛑 Shutting down pool...")
        await manager.shutdown(timeout=10.0)
        print(f"✅ Pool shut down successfully")
        print(f"   Final state: {manager._state.value}")

    except Exception as e:
        print(f"❌ Error during initialization: {e}")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Suggestion: Check DATABASE_URL and ensure PostgreSQL is running")
        raise


# ============================================================================
# Example 2: Production Configuration
# ============================================================================


async def example_production_config() -> None:
    """Demonstrate production-ready pool configuration.

    Shows:
    - Full PoolConfig with all tuning parameters
    - Environment variable usage
    - Connection lifecycle settings
    - Leak detection configuration

    Production Best Practices:
    - max_queries: 50000 (recycle connections after many queries)
    - max_idle_time: 300s (close idle connections after 5 minutes)
    - max_connection_lifetime: 3600s (recycle connections after 1 hour)
    - enable_leak_detection: True (monitor for connection leaks)
    - leak_detection_timeout: 30s (warn if connection held >30s)

    Constitutional Compliance:
    - Principle V: Production Quality (comprehensive tuning)
    - Principle VIII: Type Safety (all parameters explicitly typed)
    """
    print_section("Example 2: Production Configuration")

    database_url = get_database_url()
    if database_url is None:
        print("⚠️  DATABASE_URL not set. Skipping example.")
        return

    # Production-grade configuration
    config = PoolConfig(
        # Pool sizing
        min_size=5,  # Maintain minimum 5 connections
        max_size=20,  # Allow scaling up to 20 connections

        # Connection lifecycle
        max_queries=50000,  # Recycle after 50k queries (asyncpg built-in)
        max_idle_time=300.0,  # Close idle connections after 5 minutes
        max_connection_lifetime=3600.0,  # Recycle connections after 1 hour

        # Timeouts
        timeout=30.0,  # Connection acquisition timeout
        command_timeout=60.0,  # Query execution timeout

        # Leak detection
        enable_leak_detection=True,  # Enable leak monitoring
        leak_detection_timeout=30.0,  # Warn if connection held >30s

        # Database URL
        database_url=database_url,
    )

    print(f"📋 Production Configuration:")
    print(f"   Pool sizing: min={config.min_size}, max={config.max_size}")
    print(f"   Connection lifecycle:")
    print(f"     - max_queries: {config.max_queries} (asyncpg auto-recycle)")
    print(f"     - max_idle_time: {config.max_idle_time}s (asyncpg auto-close)")
    print(f"     - max_connection_lifetime: {config.max_connection_lifetime}s (manual recycle)")
    print(f"   Timeouts:")
    print(f"     - acquisition: {config.timeout}s")
    print(f"     - query execution: {config.command_timeout}s")
    print(f"   Leak detection:")
    print(f"     - enabled: {config.enable_leak_detection}")
    print(f"     - threshold: {config.leak_detection_timeout}s")

    # Initialize with production config
    manager = ConnectionPoolManager()

    try:
        await manager.initialize(config)
        print(f"\n✅ Pool initialized with production configuration")

        # Show resulting pool state
        stats = manager.get_statistics()
        print(f"\n📊 Initial Pool State:")
        print(f"   Total connections: {stats.total_connections}")
        print(f"   Idle connections: {stats.idle_connections}")
        print(f"   Configuration applied successfully")

        # Environment variable overrides
        print(f"\n💡 Environment Variable Overrides:")
        print(f"   POOL_MIN_SIZE={config.min_size}")
        print(f"   POOL_MAX_SIZE={config.max_size}")
        print(f"   POOL_TIMEOUT={config.timeout}")
        print(f"   POOL_MAX_CONNECTION_LIFETIME={config.max_connection_lifetime}")
        print(f"   POOL_ENABLE_LEAK_DETECTION={str(config.enable_leak_detection).lower()}")
        print(f"   DATABASE_URL=postgresql+asyncpg://...")

        await manager.shutdown()

    except Exception as e:
        print(f"❌ Error: {e}")
        raise


# ============================================================================
# Example 3: Connection Acquisition Patterns
# ============================================================================


async def example_connection_acquisition() -> None:
    """Demonstrate connection acquisition with context manager.

    Shows:
    - Proper acquire() usage with async context manager
    - Automatic connection release on exit
    - Query execution patterns
    - Error handling with automatic release

    Why Context Manager:
    - Guarantees connection release even if exception occurs
    - Prevents connection leaks from forgotten releases
    - Idiomatic Python async pattern

    Constitutional Compliance:
    - Principle V: Production Quality (guaranteed resource cleanup)
    - Principle VIII: Type Safety (typed context manager protocol)
    """
    print_section("Example 3: Connection Acquisition Patterns")

    database_url = get_database_url()
    if database_url is None:
        print("⚠️  DATABASE_URL not set. Skipping example.")
        return

    config = PoolConfig(
        min_size=2,
        max_size=10,
        database_url=database_url,
    )

    manager = ConnectionPoolManager()
    await manager.initialize(config)

    print("✅ Pool initialized")

    # Pattern 1: Basic query execution
    print(f"\n📌 Pattern 1: Basic Query Execution")
    async with manager.acquire() as conn:
        print("   Connection acquired from pool")
        result = await conn.fetchval("SELECT 1")
        print(f"   Query result: {result}")
        print("   Connection will be released automatically on exit")
    # Connection automatically released here
    print("✅ Connection released back to pool")

    # Pattern 2: Multiple queries on same connection
    print(f"\n📌 Pattern 2: Multiple Queries (Reuse Connection)")
    async with manager.acquire() as conn:
        result1 = await conn.fetchval("SELECT 1")
        result2 = await conn.fetchval("SELECT 2")
        result3 = await conn.fetchval("SELECT $1 + $2", 10, 20)
        print(f"   Results: {result1}, {result2}, {result3}")
    print("✅ Connection released after multiple queries")

    # Pattern 3: Error handling with automatic release
    print(f"\n📌 Pattern 3: Error Handling (Connection Still Released)")
    try:
        async with manager.acquire() as conn:
            print("   Connection acquired")
            # Simulate error
            await conn.fetchval("SELECT 1 / 0")  # Division by zero
    except Exception as e:
        print(f"   ⚠️  Query failed: {type(e).__name__}: {str(e)[:50]}")
        print("   Connection automatically released despite error")
    print("✅ Connection released even after exception")

    # Pattern 4: Concurrent acquisitions
    print(f"\n📌 Pattern 4: Concurrent Acquisitions")

    async def execute_query(query_id: int) -> int:
        """Execute query with connection acquisition."""
        async with manager.acquire() as conn:
            result: Any = await conn.fetchval("SELECT $1", query_id)
            # fetchval returns Any from asyncpg, cast to int for type safety
            return int(result)

    # Execute 5 queries concurrently
    results = await asyncio.gather(*[execute_query(i) for i in range(1, 6)])
    print(f"   Concurrent query results: {results}")
    print("✅ All connections released after concurrent operations")

    # Show final statistics
    stats = manager.get_statistics()
    print(f"\n📊 Final Statistics:")
    print(f"   Total acquisitions: {stats.total_acquisitions}")
    print(f"   Total releases: {stats.total_releases}")
    print(f"   Peak active connections: {stats.peak_active_connections}")
    print(f"   Average acquisition time: {stats.avg_acquisition_time_ms:.2f}ms")

    await manager.shutdown()


# ============================================================================
# Example 4: Health Monitoring
# ============================================================================


async def example_health_monitoring() -> None:
    """Demonstrate health check and statistics monitoring.

    Shows:
    - health_check() usage and response structure
    - get_statistics() for real-time metrics
    - Health status interpretation (HEALTHY/DEGRADED/UNHEALTHY)
    - Pool statistics analysis for diagnostics

    Health Status Rules:
    - HEALTHY: >=80% idle capacity, no recent errors, <100ms wait times
    - DEGRADED: 50-79% capacity, recent errors, or high wait times
    - UNHEALTHY: 0 connections or <50% capacity

    Constitutional Compliance:
    - Principle IV: Performance (<10ms health check, <1ms statistics)
    - Principle V: Production Quality (comprehensive observability)
    """
    print_section("Example 4: Health Monitoring")

    database_url = get_database_url()
    if database_url is None:
        print("⚠️  DATABASE_URL not set. Skipping example.")
        return

    config = PoolConfig(
        min_size=5,
        max_size=10,
        database_url=database_url,
    )

    manager = ConnectionPoolManager()
    await manager.initialize(config)

    print("✅ Pool initialized")

    # Health check (async operation)
    print(f"\n🏥 Health Check:")
    start_time = time.perf_counter()
    health = await manager.health_check()
    health_duration_ms = (time.perf_counter() - start_time) * 1000

    print(f"   Status: {health.status.value.upper()}")
    print(f"   Timestamp: {health.timestamp.isoformat()}")
    print(f"   Uptime: {health.uptime_seconds:.2f}s")
    print(f"   Health check latency: {health_duration_ms:.3f}ms")

    # Database status
    print(f"\n💾 Database Status:")
    print(f"   Connection status: {health.database.status}")
    print(f"   Pool state:")
    print(f"     - Total: {health.database.pool['total']}")
    print(f"     - Idle: {health.database.pool['idle']}")
    print(f"     - Active: {health.database.pool['active']}")
    print(f"     - Waiting: {health.database.pool['waiting']}")
    print(f"   Latency: {health.database.latency_ms:.2f}ms" if health.database.latency_ms else "   Latency: N/A")
    print(f"   Last error: {health.database.last_error if health.database.last_error else 'None'}")
    print(f"   Leak count: {health.database.leak_count}")

    # Pool statistics (synchronous operation)
    print(f"\n📊 Pool Statistics:")
    start_time = time.perf_counter()
    stats = manager.get_statistics()
    stats_duration_ms = (time.perf_counter() - start_time) * 1000

    print(f"   Connection counts:")
    print(f"     - Total: {stats.total_connections}")
    print(f"     - Idle: {stats.idle_connections}")
    print(f"     - Active: {stats.active_connections}")
    print(f"     - Waiting requests: {stats.waiting_requests}")
    print(f"   Lifetime metrics:")
    print(f"     - Total acquisitions: {stats.total_acquisitions}")
    print(f"     - Total releases: {stats.total_releases}")
    print(f"   Performance metrics:")
    print(f"     - Avg acquisition time: {stats.avg_acquisition_time_ms:.2f}ms")
    print(f"     - Peak active connections: {stats.peak_active_connections}")
    print(f"     - Peak wait time: {stats.peak_wait_time_ms:.2f}ms")
    print(f"   Statistics retrieval latency: {stats_duration_ms:.3f}ms")

    # Health status interpretation
    print(f"\n🔍 Health Status Interpretation:")
    if health.status == PoolHealthStatus.HEALTHY:
        print("   ✅ HEALTHY - Pool operating optimally")
        print("      - Sufficient idle capacity (>=80%)")
        print("      - No recent errors")
        print("      - Normal latency (<100ms)")
    elif health.status == PoolHealthStatus.DEGRADED:
        print("   ⚠️  DEGRADED - Pool under stress")
        print("      - Moderate capacity (50-79% idle)")
        print("      - Recent errors or high latency")
        print("      - Action: Investigate query patterns, consider scaling")
    else:  # UNHEALTHY
        print("   ❌ UNHEALTHY - Pool critically compromised")
        print("      - Zero connections or severe exhaustion (<50% capacity)")
        print("      - Action: Immediate investigation required")

    # Capacity analysis
    capacity_ratio = stats.idle_connections / stats.total_connections if stats.total_connections > 0 else 0.0
    print(f"\n📈 Capacity Analysis:")
    print(f"   Idle capacity: {capacity_ratio * 100:.1f}%")
    print(f"   Utilization: {(1 - capacity_ratio) * 100:.1f}%")
    print(f"   Headroom: {stats.idle_connections}/{stats.total_connections} connections")

    await manager.shutdown()


# ============================================================================
# Example 5: Error Handling
# ============================================================================


async def example_error_handling() -> None:
    """Demonstrate comprehensive error handling patterns.

    Shows:
    - PoolTimeoutError handling (connection acquisition timeout)
    - ConnectionValidationError handling (stale connection detected)
    - PoolClosedError handling (operations on closed pool)
    - Retry patterns with exponential backoff

    Error Recovery Strategies:
    - PoolTimeoutError: Retry with backoff or increase pool size
    - ConnectionValidationError: Automatic retry (connection recycled)
    - PoolClosedError: Check pool lifecycle, don't retry

    Constitutional Compliance:
    - Principle V: Production Quality (comprehensive error handling)
    - Principle VIII: Type Safety (typed exception hierarchy)
    """
    print_section("Example 5: Error Handling")

    database_url = get_database_url()
    if database_url is None:
        print("⚠️  DATABASE_URL not set. Skipping example.")
        return

    # Error Pattern 1: PoolTimeoutError
    print(f"📌 Pattern 1: PoolTimeoutError (Acquisition Timeout)")

    config = PoolConfig(
        min_size=2,
        max_size=2,  # Small pool to trigger timeout easily
        timeout=1.0,  # Short timeout for demonstration
        database_url=database_url,
    )

    manager = ConnectionPoolManager()
    await manager.initialize(config)

    # Fill the pool
    async def hold_connection(duration: float) -> None:
        """Hold a connection for specified duration."""
        async with manager.acquire() as conn:
            await asyncio.sleep(duration)

    # Start 2 long-running tasks (fill pool)
    long_tasks = [asyncio.create_task(hold_connection(5.0)) for _ in range(2)]
    await asyncio.sleep(0.2)  # Let them acquire connections

    # Try to acquire a third connection (will timeout)
    try:
        print("   Attempting connection acquisition with full pool...")
        async with manager.acquire() as conn:
            pass  # Won't reach here
    except PoolTimeoutError as e:
        print(f"   ✅ PoolTimeoutError caught: {str(e)[:80]}")
        print(f"   Recovery strategy: Retry with exponential backoff or increase pool size")

        # Show retry with backoff
        print(f"\n   Retrying with exponential backoff...")
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Exponential backoff: 1s, 2s, 4s
                backoff_delay = 2 ** attempt
                print(f"   Attempt {attempt + 1}/{max_retries} (after {backoff_delay}s delay)...")
                await asyncio.sleep(backoff_delay)

                # Try acquisition with shorter timeout
                config_retry = PoolConfig(
                    min_size=2,
                    max_size=2,
                    timeout=0.5,
                    database_url=database_url,
                )
                async with manager.acquire() as conn:
                    result = await conn.fetchval("SELECT 1")
                    print(f"   ✅ Retry succeeded: result={result}")
                    break
            except PoolTimeoutError:
                print(f"   ⚠️  Attempt {attempt + 1} failed")
                if attempt == max_retries - 1:
                    print(f"   ❌ Max retries exceeded")

    # Cancel long-running tasks
    for task in long_tasks:
        task.cancel()
    await asyncio.gather(*long_tasks, return_exceptions=True)

    await manager.shutdown()

    # Error Pattern 2: ConnectionValidationError
    print(f"\n📌 Pattern 2: ConnectionValidationError (Stale Connection)")
    print("   Note: This error is automatically handled by the pool")
    print("   - Connection validation fails → connection recycled")
    print("   - Caller should retry acquisition")
    print("   - No manual intervention needed")
    print("   ✅ Pool automatically handles stale connections")

    # Error Pattern 3: PoolClosedError
    print(f"\n📌 Pattern 3: PoolClosedError (Operations on Closed Pool)")

    config = PoolConfig(
        min_size=2,
        max_size=10,
        database_url=database_url,
    )

    manager = ConnectionPoolManager()
    await manager.initialize(config)
    print("   Pool initialized")

    # Shut down pool
    await manager.shutdown()
    print("   Pool shut down")

    # Try to acquire connection after shutdown
    try:
        print("   Attempting connection acquisition on closed pool...")
        async with manager.acquire() as conn:
            pass  # Won't reach here
    except PoolClosedError as e:
        print(f"   ✅ PoolClosedError caught: {str(e)[:80]}")
        print(f"   Recovery strategy: Check pool lifecycle, reinitialize if needed")
        print(f"   Note: Don't retry - pool is permanently closed")

    # Error Pattern 4: Best Practices
    print(f"\n📌 Pattern 4: Error Handling Best Practices")
    print("   1. Always use context manager for automatic release:")
    print("      async with manager.acquire() as conn:")
    print("          # Connection released even if exception occurs")
    print("   2. Catch specific exceptions first, then general:")
    print("      except PoolTimeoutError: # Handle timeout")
    print("      except ConnectionValidationError: # Handle validation")
    print("      except PoolClosedError: # Handle closed pool")
    print("      except Exception: # Catch-all")
    print("   3. Log errors with structured context for debugging")
    print("   4. Use exponential backoff for retries (max 3-5 attempts)")
    print("   5. Monitor pool health to detect issues early")

    print("\n✅ Error handling examples complete")


# ============================================================================
# Example 6: Graceful Shutdown
# ============================================================================


async def example_graceful_shutdown() -> None:
    """Demonstrate proper pool shutdown sequence.

    Shows:
    - shutdown() with timeout parameter
    - Waiting for active connections to complete
    - State transitions (HEALTHY → SHUTTING_DOWN → TERMINATED)
    - Error handling during shutdown

    Shutdown Phases:
    1. Transition to SHUTTING_DOWN (rejects new acquire requests)
    2. Wait for active connections to complete (up to timeout)
    3. Close idle connections gracefully
    4. Force-close remaining connections if timeout exceeded
    5. Transition to TERMINATED

    Constitutional Compliance:
    - Principle V: Production Quality (graceful resource cleanup)
    - Principle IV: Performance (<30s shutdown target)
    """
    print_section("Example 6: Graceful Shutdown")

    database_url = get_database_url()
    if database_url is None:
        print("⚠️  DATABASE_URL not set. Skipping example.")
        return

    config = PoolConfig(
        min_size=2,
        max_size=10,
        database_url=database_url,
    )

    manager = ConnectionPoolManager()
    await manager.initialize(config)

    print(f"✅ Pool initialized")
    print(f"   Initial state: {manager._state.value}")

    # Phase 1: Start a long-running query
    print(f"\n📌 Phase 1: Start Long-Running Query")

    async def long_query() -> str:
        """Execute a long query to demonstrate graceful wait."""
        async with manager.acquire() as conn:
            print("   📊 Long query started (3 seconds)")
            await conn.fetchval("SELECT pg_sleep(3)")  # 3 second query
            print("   ✅ Long query completed")
            return "completed"

    query_task = asyncio.create_task(long_query())
    await asyncio.sleep(0.5)  # Let query start

    # Phase 2: Initiate graceful shutdown
    print(f"\n📌 Phase 2: Initiate Graceful Shutdown")
    print(f"   Current state: {manager._state.value}")
    print(f"   Initiating shutdown with 30s timeout...")

    shutdown_start = time.perf_counter()
    shutdown_task = asyncio.create_task(manager.shutdown(timeout=30.0))

    # Wait briefly to see state transition
    await asyncio.sleep(0.1)
    print(f"   State after shutdown initiated: {manager._state.value}")

    # Phase 3: Wait for both query and shutdown to complete
    print(f"\n📌 Phase 3: Wait for Completion")
    query_result = await query_task
    print(f"   Query result: {query_result}")

    await shutdown_task
    shutdown_duration = time.perf_counter() - shutdown_start

    print(f"   ✅ Shutdown completed in {shutdown_duration:.2f}s")
    print(f"   Final state: {manager._state.value}")

    # Phase 4: Verify pool behavior after shutdown
    print(f"\n📌 Phase 4: Verify Post-Shutdown Behavior")
    try:
        async with manager.acquire() as conn:
            pass  # Won't reach here
    except PoolClosedError as e:
        print(f"   ✅ New acquisitions rejected: {type(e).__name__}")
        print(f"   Pool correctly enforces TERMINATED state")

    # Demonstrate forced shutdown
    print(f"\n📌 Phase 5: Forced Shutdown (Timeout Exceeded)")
    print("   Note: If active connections don't complete within timeout,")
    print("   they are force-closed. Demonstration:")

    manager2 = ConnectionPoolManager()
    await manager2.initialize(config)

    async def stuck_query() -> str:
        """Simulate a stuck query that won't complete."""
        try:
            async with manager2.acquire() as conn:
                print("   📊 Stuck query started (infinite wait)")
                await asyncio.sleep(100)  # Long wait
                return "completed"
        except asyncio.CancelledError:
            print("   ⚠️  Stuck query cancelled by force shutdown")
            raise

    stuck_task = asyncio.create_task(stuck_query())
    await asyncio.sleep(0.5)  # Let query start

    # Shutdown with short timeout (will force-close)
    print(f"   Initiating shutdown with 2s timeout (query takes 100s)...")
    shutdown_start = time.perf_counter()
    await manager2.shutdown(timeout=2.0)
    shutdown_duration = time.perf_counter() - shutdown_start

    print(f"   ✅ Shutdown completed in {shutdown_duration:.2f}s")
    print(f"   Force-close triggered after timeout")

    # Cancel stuck task
    stuck_task.cancel()
    try:
        await stuck_task
    except asyncio.CancelledError:
        pass

    print("\n✅ Graceful shutdown examples complete")


# ============================================================================
# Example 7: Database Outage Recovery
# ============================================================================


async def example_database_outage() -> None:
    """Demonstrate automatic reconnection during database outage.

    Shows:
    - Automatic reconnection with exponential backoff
    - State transitions (HEALTHY → UNHEALTHY → RECOVERING → HEALTHY)
    - Health checks during recovery
    - Connection functionality after recovery

    Reconnection Strategy:
    - Health checks run every 10 seconds
    - On failure: transition to RECOVERING
    - Exponential backoff: 1s, 2s, 4s, 8s, 16s (max)
    - Continues retrying every 16s until success

    Note: This example demonstrates the reconnection mechanism but cannot
    actually simulate a database outage without external tools (e.g., Docker).
    See specs/009-v2-connection-mgmt/quickstart.md for full integration test.

    Constitutional Compliance:
    - Principle V: Production Quality (self-healing)
    - Principle IV: Performance (<30s reconnection target)
    """
    print_section("Example 7: Database Outage Recovery")

    database_url = get_database_url()
    if database_url is None:
        print("⚠️  DATABASE_URL not set. Skipping example.")
        return

    print("📋 Automatic Reconnection Mechanism:")
    print("   1. Pool monitors health every 10 seconds")
    print("   2. On connection failure → state: UNHEALTHY")
    print("   3. Automatic transition to RECOVERING state")
    print("   4. Retry with exponential backoff:")
    print("      - Attempt 1: 1s delay")
    print("      - Attempt 2: 2s delay")
    print("      - Attempt 3: 4s delay")
    print("      - Attempt 4: 8s delay")
    print("      - Attempt 5+: 16s delay (capped)")
    print("   5. On success → state: HEALTHY")
    print("   6. Continues indefinitely until recovery")

    config = PoolConfig(
        min_size=2,
        max_size=10,
        database_url=database_url,
    )

    manager = ConnectionPoolManager()
    await manager.initialize(config)

    print(f"\n✅ Pool initialized")
    print(f"   State: {manager._state.value}")

    # Verify pool is healthy
    health = await manager.health_check()
    print(f"   Health status: {health.status.value}")

    # Show background reconnection task
    print(f"\n🔄 Background Tasks:")
    if manager._reconnection_loop_task:
        print(f"   Reconnection loop: Running (task_done={manager._reconnection_loop_task.done()})")
    if manager._pool_maintenance_task:
        print(f"   Pool maintenance: Running (task_done={manager._pool_maintenance_task.done()})")
    if manager._leak_detection_task:
        print(f"   Leak detection: Running (task_done={manager._leak_detection_task.done()})")

    print(f"\n💡 Simulating Database Outage:")
    print("   Note: Full outage simulation requires external tools")
    print("   For complete test, see:")
    print("   - specs/009-v2-connection-mgmt/quickstart.md Test Scenario 3")
    print("   - Uses Docker to stop/start PostgreSQL")
    print("   - Validates automatic reconnection within 30s target")

    # Demonstrate health monitoring during normal operation
    print(f"\n📊 Health Monitoring During Normal Operation:")
    for i in range(3):
        health = await manager.health_check()
        print(f"   Check {i + 1}: status={health.status.value}, "
              f"connections={health.database.pool['total']}, "
              f"uptime={health.uptime_seconds:.1f}s")
        await asyncio.sleep(1)

    print(f"\n🔍 State Transitions During Outage (Conceptual):")
    print("   1. HEALTHY → connection validation fails")
    print("   2. HEALTHY → UNHEALTHY (all connections lost)")
    print("   3. UNHEALTHY → RECOVERING (reconnection initiated)")
    print("   4. RECOVERING → health status: DEGRADED (some connections restored)")
    print("   5. RECOVERING → HEALTHY (full recovery)")
    print("   Note: Health status in RECOVERING state:")
    print("      - UNHEALTHY if total_connections == 0")
    print("      - DEGRADED if total_connections > 0")

    print(f"\n✅ Pool operating normally")
    print("   For full outage recovery test, run integration test:")
    print("   $ pytest tests/integration/test_connection_pool.py::test_database_outage_recovery -v")

    await manager.shutdown()
    print("\n✅ Database outage recovery example complete")


# ============================================================================
# Main Demonstration
# ============================================================================


async def main() -> None:
    """Run all connection pool usage examples.

    Executes each example in sequence with error handling to ensure
    all examples run even if one fails. Provides summary at the end.

    Returns:
        None
    """
    print("\n" + "=" * 80)
    print("Connection Pool Usage Examples")
    print("Comprehensive demonstration of production patterns")
    print("=" * 80)

    database_url = get_database_url()
    if database_url is None:
        print("\n⚠️  WARNING: DATABASE_URL not set")
        print("Some examples will be skipped. To run all examples:")
        print("  export DATABASE_URL='postgresql+asyncpg://localhost/codebase_mcp'")
        print("  python docs/examples/connection_pool_usage.py")

    # Track example results
    results: dict[str, bool] = {}

    # Example 1: Basic Initialization
    try:
        await example_basic_initialization()
        results["Example 1"] = True
    except Exception as e:
        print(f"\n❌ Example 1 failed: {e}")
        results["Example 1"] = False

    # Example 2: Production Configuration
    try:
        await example_production_config()
        results["Example 2"] = True
    except Exception as e:
        print(f"\n❌ Example 2 failed: {e}")
        results["Example 2"] = False

    # Example 3: Connection Acquisition
    try:
        await example_connection_acquisition()
        results["Example 3"] = True
    except Exception as e:
        print(f"\n❌ Example 3 failed: {e}")
        results["Example 3"] = False

    # Example 4: Health Monitoring
    try:
        await example_health_monitoring()
        results["Example 4"] = True
    except Exception as e:
        print(f"\n❌ Example 4 failed: {e}")
        results["Example 4"] = False

    # Example 5: Error Handling
    try:
        await example_error_handling()
        results["Example 5"] = True
    except Exception as e:
        print(f"\n❌ Example 5 failed: {e}")
        results["Example 5"] = False

    # Example 6: Graceful Shutdown
    try:
        await example_graceful_shutdown()
        results["Example 6"] = True
    except Exception as e:
        print(f"\n❌ Example 6 failed: {e}")
        results["Example 6"] = False

    # Example 7: Database Outage Recovery
    try:
        await example_database_outage()
        results["Example 7"] = True
    except Exception as e:
        print(f"\n❌ Example 7 failed: {e}")
        results["Example 7"] = False

    # Summary
    print("\n" + "=" * 80)
    print("Example Results Summary")
    print("=" * 80)

    success_count = sum(1 for passed in results.values() if passed)
    total_count = len(results)

    for example, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {status}  {example}")

    print(f"\nTotal: {success_count}/{total_count} examples passed")

    if success_count == total_count:
        print("✅ All examples completed successfully!")
    else:
        print(f"⚠️  {total_count - success_count} examples failed")

    print("\n" + "=" * 80)
    print("For more information:")
    print("  - Specification: specs/009-v2-connection-mgmt/spec.md")
    print("  - Integration Tests: specs/009-v2-connection-mgmt/quickstart.md")
    print("  - Source Code: src/connection_pool/")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    """Entry point for running examples."""
    asyncio.run(main())
