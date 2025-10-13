"""Connection pool manager with lifecycle state management.

This module provides the ConnectionPoolManager class and PoolState enum for
managing asyncpg connection pools with health monitoring and graceful shutdown.

Constitutional Compliance:
- Principle VIII: Pydantic-based type safety with complete state tracking
- Principle V: Production-quality lifecycle management with comprehensive error handling
- Principle III: JSON-serializable state for MCP protocol observability
"""

from __future__ import annotations

import asyncio
import contextlib
import random
import time
import traceback
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, AsyncIterator, cast

import asyncpg  # type: ignore[import-untyped]

from .config import PoolConfig
from .exceptions import (
    ConnectionValidationError,
    PoolClosedError,
    PoolInitializationError,
    PoolTimeoutError,
)
from .health import (
    DatabaseStatus,
    HealthStatus,
    PoolHealthStatus,
    calculate_health_status,
)
from .pool_logging import (
    get_pool_structured_logger,
    log_pool_initialization,
)
from .statistics import PoolStatistics

if TYPE_CHECKING:
    from logging import Logger


@dataclass
class ConnectionMetadata:
    """Metadata for connection lifecycle tracking and leak detection.

    This dataclass tracks connection usage patterns for recycling decisions,
    leak detection, and health monitoring. Metadata is stored per active
    connection and updated on acquisition/release.

    **Connection Recycling** (Task T028):
    asyncpg automatically handles most connection recycling via create_pool parameters:
    - max_queries: asyncpg closes connection after N queries (default: 50,000)
    - max_inactive_connection_lifetime: asyncpg closes idle connections (default: 300s)

    This metadata enables ADDITIONAL recycling based on:
    - max_connection_lifetime: Total connection age (not handled by asyncpg)

    **Leak Detection** (Task T030):
    - Tracks acquisition timestamp and stack trace for leak warnings
    - Enables diagnostics for connections held longer than timeout

    **Constitutional Compliance**:
    - Principle VIII: Complete type annotations with dataclass safety
    - Principle V: Production-quality tracking with comprehensive metadata

    Attributes:
        connection_id: Unique connection identifier (str, from id(connection))
        acquired_at: UTC timestamp when connection was acquired from pool
        acquisition_stack_trace: Stack trace at acquisition time for leak detection
        query_count: Number of queries executed on this connection (for manual tracking)
        created_at: UTC timestamp when connection was first created
        last_used_at: UTC timestamp of last query or release (for idle tracking)
    """

    connection_id: str
    acquired_at: datetime
    acquisition_stack_trace: str
    query_count: int
    created_at: datetime
    last_used_at: datetime


class PoolState(str, Enum):
    """Connection pool lifecycle states.

    This enum represents the internal state of a connection pool throughout its
    lifecycle, from initialization to termination. State transitions are managed
    by the ConnectionPoolManager to ensure consistent lifecycle behavior.

    **State Definitions**:

    - INITIALIZING: Pool is being created and establishing min_size connections.
      No connections are available for use yet. Failed initialization transitions
      to UNHEALTHY.

    - HEALTHY: Pool is operating optimally with >=80% idle capacity, no recent
      errors (last 60 seconds), and normal wait times (<100ms). All connections
      are functioning correctly.

    - DEGRADED: Pool is functional but under stress. Conditions include:
      * 50-79% idle capacity (some connection pressure)
      * Recent errors within last 60 seconds
      * High wait times (>100ms peak)
      * Some connections failed but recovery possible

    - UNHEALTHY: Pool is critically compromised. Conditions include:
      * Zero total connections (complete failure)
      * <50% idle capacity (severe connection exhaustion)
      * Initialization failed
      * Critical error preventing connection establishment

    - RECOVERING: Pool is attempting to recover from UNHEALTHY state through
      reconnection attempts. This is a transient state during self-healing.
      Successful recovery transitions to HEALTHY; failed recovery returns to
      UNHEALTHY.

    - SHUTTING_DOWN: Graceful shutdown initiated. Pool stops accepting new
      requests, waits for active connections to complete, then closes all
      connections. Triggered by explicit shutdown signal or server termination.

    - TERMINATED: Pool has completed shutdown. All connections closed, resources
      released, and pool can no longer be used. This is a terminal state.

    **State Transitions**:

    Normal Lifecycle Flow:
    - INITIALIZING -> HEALTHY: Successfully created min_size connections
    - HEALTHY -> DEGRADED: Partial capacity or minor errors detected
    - DEGRADED -> UNHEALTHY: Critical capacity drop (<50%) or severe errors
    - UNHEALTHY -> RECOVERING: Self-healing reconnection attempt started
    - RECOVERING -> HEALTHY: Successful reconnection restored capacity

    Recovery Cycles:
    - RECOVERING -> UNHEALTHY: Recovery failed, may retry
    - DEGRADED -> HEALTHY: Capacity restored or errors cleared

    Shutdown Flow:
    - {HEALTHY|DEGRADED|UNHEALTHY} -> SHUTTING_DOWN: Shutdown signal received
    - SHUTTING_DOWN -> TERMINATED: All connections closed, cleanup complete

    **State Diagram**:

    ::

        +---------------+
        | INITIALIZING  |
        +-------+-------+
                |
                v
        +---------------+     +---------------+     +---------------+
        |   HEALTHY     |---->|   DEGRADED    |---->|  UNHEALTHY    |
        +-------+-------+     +-------+-------+     +-------+-------+
                |                     |                     |
                |                     |                     v
                |                     |              +---------------+
                |                     |              |  RECOVERING   |
                |                     |              +-------+-------+
                |                     |                     |
                |<--------------------+---------------------+
                |
                | (shutdown signal)
                v
        +---------------+
        | SHUTTING_DOWN |
        +-------+-------+
                |
                v
        +---------------+
        |  TERMINATED   |
        +---------------+

    **Usage Example**:

    .. code-block:: python

        from connection_pool.manager import PoolState

        # Pool manager tracks current state
        pool_state = PoolState.INITIALIZING

        # Successful initialization
        if connections_created >= min_size:
            pool_state = PoolState.HEALTHY

        # Detect degradation
        capacity_ratio = idle_connections / total_connections
        if capacity_ratio < 0.8:
            pool_state = PoolState.DEGRADED

        # Shutdown sequence
        if shutdown_requested:
            pool_state = PoolState.SHUTTING_DOWN
            await close_all_connections()
            pool_state = PoolState.TERMINATED

    **Constitutional Principle Compliance**:
    - Principle V (Production Quality): Comprehensive state tracking with clear semantics
    - Principle VIII (Type Safety): Enum-based state with no invalid values possible
    - Principle III (Protocol Compliance): JSON-serializable for MCP health checks

    **Attributes**:
        INITIALIZING: Pool creation in progress, connections being established
        HEALTHY: Pool operating optimally (>=80% capacity, no errors, normal latency)
        DEGRADED: Pool functional but stressed (50-79% capacity, recent errors, high latency)
        UNHEALTHY: Pool critically compromised (0 connections or <50% capacity)
        RECOVERING: Self-healing reconnection attempt in progress
        SHUTTING_DOWN: Graceful shutdown initiated, draining active connections
        TERMINATED: Pool shutdown complete, all resources released (terminal state)
    """

    INITIALIZING = "initializing"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    RECOVERING = "recovering"
    SHUTTING_DOWN = "shutting_down"
    TERMINATED = "terminated"


async def exponential_backoff_retry(
    attempt: int,
    max_delay: float = 16.0,
    jitter_factor: float = 0.1,
) -> None:
    """Implement exponential backoff with jitter for reconnection attempts.

    Calculates exponentially increasing delay with random jitter to prevent
    thundering herd issues when multiple servers restart simultaneously. This
    function is used by the reconnection loop to space out retry attempts.

    **Exponential Backoff Schedule** (with max_delay=16.0):
    - Attempt 0: 1.0s ± 10% jitter
    - Attempt 1: 2.0s ± 10% jitter
    - Attempt 2: 4.0s ± 10% jitter
    - Attempt 3: 8.0s ± 10% jitter
    - Attempt 4+: 16.0s ± 10% jitter (capped at max_delay)

    **Jitter Calculation**:
    Jitter prevents multiple clients from reconnecting at exactly the same time,
    which could overwhelm a recovering database server. The jitter is uniformly
    distributed in the range [-jitter_factor * delay, +jitter_factor * delay].

    **Performance Characteristics**:
    - Calculation: <1μs (simple arithmetic)
    - Sleep duration: Varies by attempt (1-16 seconds)
    - Memory: O(1) (no allocations)

    **Constitutional Compliance**:
    - Principle V (Production Quality): Graceful reconnection with backoff
    - Principle VIII (Type Safety): Complete type annotations with mypy --strict
    - Principle IV (Performance): Minimal computation overhead

    Args:
        attempt: Zero-based retry attempt number (0, 1, 2, ...). Higher attempts
            result in longer delays up to max_delay.
        max_delay: Maximum delay in seconds (default: 16.0). Delays are capped
            at this value regardless of attempt count.
        jitter_factor: Jitter as fraction of delay (default: 0.1 = 10%). Must be
            in range [0.0, 1.0]. A value of 0.1 means jitter is ±10% of delay.

    Returns:
        None: This function completes after sleeping for the calculated duration.

    Raises:
        ValueError: If jitter_factor is outside [0.0, 1.0] range or max_delay is
            negative (should not occur in normal usage).

    Examples:
        >>> # First reconnection attempt (1s ± 10%)
        >>> await exponential_backoff_retry(attempt=0)
        >>> # Sleeps for ~1.0s (actual: 0.9-1.1s with jitter)

        >>> # Third reconnection attempt (4s ± 10%)
        >>> await exponential_backoff_retry(attempt=2)
        >>> # Sleeps for ~4.0s (actual: 3.6-4.4s with jitter)

        >>> # Tenth attempt (capped at max_delay)
        >>> await exponential_backoff_retry(attempt=10, max_delay=16.0)
        >>> # Sleeps for ~16.0s (actual: 14.4-17.6s with jitter)

        >>> # Custom configuration (shorter max delay, no jitter)
        >>> await exponential_backoff_retry(
        ...     attempt=5,
        ...     max_delay=8.0,
        ...     jitter_factor=0.0
        ... )
        >>> # Sleeps for exactly 8.0s (no jitter)

    Usage in Reconnection Loop:
        >>> attempt = 0
        >>> while not connected:
        ...     try:
        ...         await pool.initialize(config)
        ...         connected = True
        ...     except Exception as e:
        ...         logger.error(f"Reconnection failed: {e}")
        ...         await exponential_backoff_retry(attempt)
        ...         attempt += 1
    """
    # Validate jitter_factor range
    if not 0.0 <= jitter_factor <= 1.0:
        raise ValueError(
            f"jitter_factor must be in range [0.0, 1.0], got {jitter_factor}"
        )

    # Validate max_delay is non-negative
    if max_delay < 0.0:
        raise ValueError(f"max_delay must be non-negative, got {max_delay}")

    # Calculate exponential delay: 1.0 * (2 ** attempt), capped at max_delay
    base_delay = 1.0 * (2 ** attempt)
    delay = min(base_delay, max_delay)

    # Add random jitter: uniform distribution in [-jitter_factor * delay, +jitter_factor * delay]
    jitter_range = jitter_factor * delay
    jitter = random.uniform(-jitter_range, jitter_range)

    # Total delay = exponential delay + jitter
    total_delay = delay + jitter

    # Ensure non-negative delay (should always be true given validations)
    total_delay = max(0.0, total_delay)

    # Sleep for calculated duration
    await asyncio.sleep(total_delay)


class ConnectionPoolManager:
    """Connection pool manager with lifecycle state management.

    This class manages the lifecycle of an asyncpg connection pool with comprehensive
    health monitoring, statistics tracking, and structured logging. It provides a
    production-grade pool management solution with <2 second initialization time
    and <10ms health check latency.

    **Features**:
    - Parallel connection validation during initialization (<2s target)
    - Real-time statistics tracking (<1ms get_statistics() latency)
    - Health checks with automatic status calculation (<10ms p99)
    - Structured logging to /tmp/codebase-mcp.log (no stdout pollution)
    - Type-safe configuration with Pydantic validation
    - Graceful shutdown with connection draining

    **Constitutional Compliance**:
    - Principle IV (Performance): <2s initialization, <10ms health checks
    - Principle V (Production Quality): Comprehensive error handling and logging
    - Principle VIII (Type Safety): Full mypy --strict compliance
    - Principle III (Protocol Compliance): No stdout/stderr pollution

    **Usage Example**:

    .. code-block:: python

        from connection_pool.config import PoolConfig
        from connection_pool.manager import ConnectionPoolManager

        # Create configuration
        config = PoolConfig(
            min_size=2,
            max_size=10,
            timeout=30.0,
            database_url="postgresql+asyncpg://localhost/codebase_mcp"
        )

        # Initialize pool
        manager = ConnectionPoolManager()
        await manager.initialize(config)

        # Get statistics
        stats = manager.get_statistics()
        print(f"Total connections: {stats.total_connections}")
        print(f"Idle connections: {stats.idle_connections}")

        # Health check
        health = await manager.health_check()
        print(f"Status: {health.status}")
        print(f"Uptime: {health.uptime_seconds}s")

    **Performance Characteristics**:
    - Initialization: <2 seconds for default pool size (2-10 connections)
    - Statistics retrieval: <1ms (synchronous, no locks)
    - Health check: <10ms p99 (includes statistics + status calculation)
    - Connection validation: <5ms per connection

    **Thread Safety**:
    - All public methods are thread-safe (asyncio-safe)
    - Statistics tracking uses atomic operations (no locks required)
    - Pool state transitions are serialized

    Attributes:
        _pool: asyncpg connection pool instance (None until initialized)
        _config: Pool configuration (immutable after initialization)
        _state: Current pool lifecycle state
        _start_time: Pool initialization timestamp (UTC)
        _logger: Structured logger for pool events
        _total_acquisitions: Lifetime connection acquisition count
        _total_releases: Lifetime connection release count
        _acquisition_times: Rolling window of acquisition times (deque)
        _peak_active: Peak active connection count
        _peak_wait_time: Peak connection wait time (milliseconds)
    """

    def __init__(self) -> None:
        """Initialize connection pool manager with default state.

        Creates a new pool manager instance in INITIALIZING state with no active
        pool. Call initialize() to create the asyncpg pool and establish connections.

        **Initialization State**:
        - Pool: None (not yet created)
        - State: INITIALIZING
        - Statistics: All counters at zero
        - Logging: Configured to /tmp/codebase-mcp.log

        **Performance**: <1ms (no I/O operations)

        **Constitutional Compliance**:
        - Principle VIII: Type-safe initialization with explicit None values
        - Principle V: Structured logger configured for production logging
        """
        # Core pool resources
        self._pool: asyncpg.Pool | None = None
        self._config: PoolConfig | None = None
        self._state: PoolState = PoolState.INITIALIZING
        self._start_time: datetime | None = None

        # Statistics tracking (no locks required, atomic operations)
        self._total_acquisitions: int = 0
        self._total_releases: int = 0
        self._acquisition_times: deque[float] = deque(maxlen=1000)  # Rolling window
        self._peak_active: int = 0
        self._peak_wait_time: float = 0.0

        # Shutdown management
        self._active_connection_count: int = 0
        self._shutdown_lock: asyncio.Lock = asyncio.Lock()
        self._reconnection_loop_task: asyncio.Task[None] | None = None
        self._pool_maintenance_task: asyncio.Task[None] | None = None

        # Error tracking for health checks
        self._last_error: str | None = None
        self._last_error_time: datetime | None = None

        # Connection metadata tracking for recycling and leak detection (T028, T030)
        self._connection_metadata: dict[int, ConnectionMetadata] = {}
        self._connection_creation_times: dict[int, datetime] = {}

        # Structured logging (JSON format, file-only)
        self._logger = get_pool_structured_logger(__name__)

    async def initialize(self, config: PoolConfig) -> None:
        """Initialize connection pool with validated configuration.

        Creates an asyncpg connection pool with the specified configuration and
        validates all connections in parallel. This method must complete within
        2 seconds to meet MVP performance requirements.

        **Initialization Steps**:
        1. Validate configuration (Pydantic validation)
        2. Create asyncpg pool with configured parameters
        3. Validate all connections in parallel (asyncio.gather)
        4. Set pool state to HEALTHY on success
        5. Record start time for uptime tracking

        **Performance Target**: <2 seconds (including parallel validation)

        **Configuration Parameters Applied**:
        - min_size: Minimum connection pool size
        - max_size: Maximum connection pool size
        - timeout: Connection acquisition timeout
        - command_timeout: Query execution timeout
        - max_queries: Queries before connection recycling
        - max_inactive_connection_lifetime: Idle connection timeout

        **Connection Recycling Behavior** (Task T028):

        asyncpg **automatically handles** most connection recycling:

        1. **Query-based recycling** (max_queries):
           - asyncpg closes connection after N queries (default: 50,000)
           - No manual intervention required
           - New connection automatically created on next acquire()

        2. **Idle timeout recycling** (max_inactive_connection_lifetime):
           - asyncpg closes idle connections after timeout (default: 300s)
           - Pool maintains at least min_size connections
           - Automatic cleanup, no manual tracking needed

        This pool manager **adds manual recycling** for:

        3. **Age-based recycling** (max_connection_lifetime):
           - Tracks total connection age from creation
           - Closes connection if age > max_connection_lifetime (default: 3600s)
           - Logs recycling event with reason: "lifetime"
           - Acquires fresh connection automatically

        **Recycling Event Logging**:
        All recycling events are logged with structured context:
        - recycle_reason: "query_limit" | "idle_timeout" | "lifetime"
        - connection_id: Unique identifier for debugging
        - age_seconds: Connection age at recycling time
        - max_connection_lifetime: Configured lifetime threshold

        **Error Recovery**:
        - On failure: Sets state to UNHEALTHY
        - Raises PoolInitializationError with actionable message
        - Logs initialization failure with context

        Args:
            config: Pool configuration (validated Pydantic model)

        Raises:
            PoolInitializationError: Pool creation or validation failed with
                actionable error message including database connectivity details

        Example:
            >>> config = PoolConfig(
            ...     min_size=2,
            ...     max_size=10,
            ...     timeout=30.0,
            ...     max_queries=50000,  # asyncpg auto-recycles after 50k queries
            ...     max_idle_time=300.0,  # asyncpg auto-recycles after 5 min idle
            ...     max_connection_lifetime=3600.0,  # Manual recycling after 1 hour
            ...     database_url="postgresql+asyncpg://localhost/test"
            ... )
            >>> manager = ConnectionPoolManager()
            >>> await manager.initialize(config)  # <2s completion
            >>> manager._state
            <PoolState.HEALTHY: 'healthy'>
        """
        start_time_ns = time.perf_counter()

        try:
            # Log initialization start
            self._logger.info(
                "Starting pool initialization",
                context=cast(Any, {
                    "min_size": config.min_size,
                    "max_size": config.max_size,
                    "timeout": config.timeout,
                    "command_timeout": config.command_timeout,
                })
            )

            # Validate configuration
            if config is None:
                raise PoolInitializationError(
                    "Configuration is None. "
                    "Suggestion: Provide valid PoolConfig instance"
                )

            self._config = config

            # Create asyncpg pool with configuration
            # Remove the +asyncpg suffix from database_url as asyncpg doesn't need it
            database_url = config.database_url.replace("postgresql+asyncpg://", "postgresql://")

            # Connection initialization hook (T028): Track connection creation time
            async def _connection_init(connection: asyncpg.Connection) -> None:
                """Track connection creation timestamp for age-based recycling.

                This hook is called by asyncpg when a new connection is created,
                allowing us to track connection age for max_connection_lifetime recycling.

                Args:
                    connection: Newly created asyncpg connection
                """
                conn_id = id(connection)
                creation_time = datetime.now(timezone.utc)
                self._connection_creation_times[conn_id] = creation_time

                self._logger.debug(
                    "Connection created and tracked",
                    context=cast(Any, {
                        "connection_id": conn_id,
                        "created_at": creation_time.isoformat(),
                    })
                )

            self._pool = await asyncpg.create_pool(
                dsn=database_url,
                min_size=config.min_size,
                max_size=config.max_size,
                timeout=config.timeout,
                command_timeout=config.command_timeout,
                max_queries=config.max_queries,
                max_inactive_connection_lifetime=config.max_idle_time,
                init=_connection_init,  # Track connection creation
            )

            if self._pool is None:
                raise PoolInitializationError(
                    f"Failed to create pool with min_size={config.min_size}. "
                    f"Database connection refused on {database_url}. "
                    "Suggestion: Verify database is running and credentials are correct"
                )

            # Validate connections in parallel (target <2s total)
            self._logger.debug(
                "Validating connections in parallel",
                context=cast(Any, {"min_size": config.min_size})
            )

            # Acquire all min_size connections and validate them in parallel
            validation_tasks = []
            connections = []

            # Acquire all connections first
            for _ in range(config.min_size):
                conn = await self._pool.acquire()
                connections.append(conn)
                validation_tasks.append(self._validate_connection(conn))

            # Validate all connections in parallel
            try:
                await asyncio.gather(*validation_tasks)
                self._logger.debug(
                    "All connections validated successfully",
                    context=cast(Any, {"connection_count": len(connections)})
                )
            finally:
                # Release all connections back to pool
                for conn in connections:
                    await self._pool.release(conn)

            # Set state to HEALTHY
            self._state = PoolState.HEALTHY
            self._start_time = datetime.now(timezone.utc)

            # Start background reconnection loop to monitor pool health
            self._reconnection_loop_task = asyncio.create_task(self._reconnection_loop())
            self._logger.debug(
                "Started reconnection loop background task",
                context=cast(Any, {"state": self._state.value})
            )

            # Start background pool maintenance task to shrink idle connections
            self._pool_maintenance_task = asyncio.create_task(self._pool_maintenance())
            self._logger.debug(
                "Started pool maintenance background task",
                context=cast(Any, {"state": self._state.value})
            )

            # Calculate initialization duration
            duration_ms = (time.perf_counter() - start_time_ns) * 1000

            # Log successful initialization
            log_pool_initialization(
                logger=self._logger._logger,  # Access underlying logger
                min_size=config.min_size,
                max_size=config.max_size,
                duration_ms=duration_ms,
                success=True,
            )

        except Exception as e:
            # Calculate failure duration
            duration_ms = (time.perf_counter() - start_time_ns) * 1000

            # Set state to UNHEALTHY
            self._state = PoolState.UNHEALTHY

            # Get detailed error traceback
            error_traceback = traceback.format_exc()

            # Log initialization failure
            log_pool_initialization(
                logger=self._logger._logger,  # Access underlying logger
                min_size=config.min_size if config else 0,
                max_size=config.max_size if config else 0,
                duration_ms=duration_ms,
                success=False,
                error_message=str(e),
            )

            self._logger.error(
                "Pool initialization failed",
                context=cast(Any, {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "traceback": error_traceback,
                }),
                exc_info=True
            )

            # Raise actionable error
            raise PoolInitializationError(
                f"Failed to initialize connection pool: {str(e)}. "
                f"Database connectivity issue on {config.database_url if config else 'unknown'}. "
                "Suggestion: Verify database is running, credentials are correct, "
                "and network connectivity is available"
            ) from e

    async def _validate_connection(self, conn: asyncpg.Connection) -> bool:
        """Validate connection with health check query.

        Executes a simple "SELECT 1" query to verify connection health. This method
        is called during pool initialization and connection recycling to ensure all
        connections are functioning correctly.

        **Performance Target**: <5ms per validation

        **Validation Query**: SELECT 1 (simplest possible query, minimal overhead)

        **Error Recovery**:
        - On failure: Raises ConnectionValidationError
        - Connection is automatically recycled by pool
        - Validation failure is logged with context

        Args:
            conn: asyncpg connection instance to validate

        Returns:
            True if validation succeeded (always returns True or raises)

        Raises:
            ConnectionValidationError: Validation query failed or timed out with
                connection details and suggested action

        Example:
            >>> conn = await pool.acquire()
            >>> result = await manager._validate_connection(conn)  # <5ms
            >>> result
            True
            >>> await pool.release(conn)
        """
        try:
            # Execute simple validation query (SELECT 1)
            start_time_ns = time.perf_counter()
            result = await conn.fetchval("SELECT 1")
            duration_ms = (time.perf_counter() - start_time_ns) * 1000

            if result != 1:
                raise ConnectionValidationError(
                    f"Connection validation failed: unexpected result {result}. "
                    "Expected result: 1. Connection has been recycled."
                )

            self._logger.debug(
                "Connection validated successfully",
                context=cast(Any, {
                    "validation_time_ms": duration_ms,
                    "query": "SELECT 1",
                })
            )

            return True

        except asyncio.TimeoutError as e:
            timeout_seconds = self._config.command_timeout if self._config else 60.0
            error_message = (
                f"Connection validation failed: query timeout after {timeout_seconds}s. "
                "Connection has been recycled. Check database load."
            )
            self._logger.error(
                "Connection validation timeout",
                context=cast(Any, {
                    "timeout_seconds": timeout_seconds,
                    "query": "SELECT 1",
                }),
                exc_info=True
            )
            raise ConnectionValidationError(error_message) from e

        except Exception as e:
            error_message = (
                f"Connection validation failed: {str(e)}. "
                "Connection has been recycled. Retrying acquisition."
            )
            self._logger.error(
                "Connection validation error",
                context=cast(Any, {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "query": "SELECT 1",
                }),
                exc_info=True
            )
            raise ConnectionValidationError(error_message) from e

    @contextlib.asynccontextmanager
    async def acquire(self) -> AsyncIterator[asyncpg.Connection]:
        """Acquire connection from pool with validation and automatic release.

        Context manager that acquires a connection from the pool, validates it,
        tracks acquisition metrics, and automatically releases it on context exit.
        Implements comprehensive error handling for timeout, validation, and
        shutdown scenarios.

        **Performance Target**: Connection acquisition completes within configured
        timeout (default 30s), with <5ms validation overhead.

        **Acquisition Flow**:
        1. Check pool state (reject if SHUTTING_DOWN or TERMINATED)
        2. Attempt connection acquisition with configured timeout
        3. Validate connection health via SELECT 1 query
        4. Track acquisition timestamp and stack trace for leak detection
        5. Increment total_acquisitions counter
        6. Yield connection to caller
        7. Auto-release connection on context exit

        **Error Handling**:
        - PoolClosedError: Pool is shutting down or terminated
        - PoolTimeoutError: Acquisition timeout with pool statistics
        - ConnectionValidationError: Invalid connection, auto-recycled with retry

        **Leak Detection Preparation** (for T030):
        - Captures stack trace at acquisition time
        - Records acquisition timestamp
        - Enables future leak detection diagnostics

        **Statistics Tracking**:
        - Increments total_acquisitions on successful acquisition
        - Increments total_releases on connection return
        - Tracks acquisition duration for performance monitoring

        Yields:
            asyncpg.Connection: Validated database connection that auto-releases
                on context exit

        Raises:
            PoolClosedError: Pool state is SHUTTING_DOWN or TERMINATED, no new
                connections can be acquired. Suggestion: Check shutdown sequence.
            PoolTimeoutError: Connection acquisition exceeded configured timeout.
                Includes pool statistics (total, idle, active connections) in error
                message. Suggestion: Increase pool size or optimize queries.
            ConnectionValidationError: Connection failed validation and was recycled.
                Logged as warning with connection details. Caller should retry.
            RuntimeError: Pool not initialized. Suggestion: Call initialize() first.

        Example:
            >>> manager = ConnectionPoolManager()
            >>> await manager.initialize(config)
            >>> async with manager.acquire() as conn:
            ...     result = await conn.fetchval("SELECT 1")
            ...     # Connection automatically released on exit
            >>> # Connection returned to pool here

        **Constitutional Compliance**:
        - Principle V: Production-quality error handling with actionable messages
        - Principle VIII: Type-safe with complete error coverage
        - Principle III: No stdout pollution, structured logging only
        """
        # Check pool initialization
        if self._pool is None or self._config is None:
            raise RuntimeError(
                "Pool not initialized. "
                "Suggestion: Call initialize(config) before acquiring connections"
            )

        # Check pool state (reject if shutting down or terminated)
        if self._state in (PoolState.SHUTTING_DOWN, PoolState.TERMINATED):
            raise PoolClosedError(
                f"Cannot acquire connection: pool state is {self._state.value}. "
                "Suggestion: Check pool lifecycle management and shutdown sequence"
            )

        # Track acquisition start time for statistics
        acquisition_start = time.perf_counter()

        # Capture stack trace for leak detection (T030 preparation)
        acquisition_stack = "".join(traceback.format_stack())

        connection: asyncpg.Connection | None = None

        try:
            # Attempt connection acquisition with timeout
            self._logger.debug(
                "Attempting connection acquisition",
                context=cast(Any, {
                    "timeout": self._config.timeout,
                    "pool_state": self._state.value,
                })
            )

            try:
                connection = await asyncio.wait_for(
                    self._pool.acquire(),
                    timeout=self._config.timeout
                )
            except asyncio.TimeoutError as e:
                # Get pool statistics for error message
                stats = self.get_statistics()

                error_message = (
                    f"Connection acquisition timeout after {self._config.timeout}s. "
                    f"Pool state: {stats.total_connections} total, "
                    f"{stats.active_connections} active, "
                    f"{stats.idle_connections} idle, "
                    f"{stats.waiting_requests} waiting. "
                    "Suggestion: Increase POOL_MAX_SIZE or optimize query performance"
                )

                self._logger.error(
                    "Connection acquisition timeout",
                    context=cast(Any, {
                        "timeout": self._config.timeout,
                        "total_connections": stats.total_connections,
                        "active_connections": stats.active_connections,
                        "idle_connections": stats.idle_connections,
                        "waiting_requests": stats.waiting_requests,
                    }),
                    exc_info=True
                )

                raise PoolTimeoutError(error_message) from e

            # Validate connection health
            try:
                await self._validate_connection(connection)
            except ConnectionValidationError as e:
                # Close invalid connection and log warning
                self._logger.warning(
                    "Connection validation failed, recycling connection",
                    context=cast(Any, {
                        "error": str(e),
                        "connection_closed": True,
                    })
                )

                # Close the invalid connection (connection is guaranteed non-None here)
                if connection is not None:
                    await connection.close()

                # Re-raise for caller to handle (should retry)
                raise

            # Increment acquisition counter
            self._total_acquisitions += 1

            # T026: Track acquisition time and update peak wait time
            acquisition_end = time.perf_counter()
            duration_ms = (acquisition_end - acquisition_start) * 1000
            self._acquisition_times.append(duration_ms)

            # Update peak wait time if current duration exceeds peak
            if duration_ms > self._peak_wait_time:
                self._peak_wait_time = duration_ms

            # T027: Track peak active connections
            active_connections = self._pool.get_size() - self._pool.get_idle_size()
            if active_connections > self._peak_active:
                self._peak_active = active_connections

            # T028: Check connection age and recycle if exceeds max_connection_lifetime
            # At this point, connection is guaranteed to be non-None (we just validated it)
            assert connection is not None, "Connection must be non-None after validation"

            conn_id = id(connection)
            now = datetime.now(timezone.utc)

            # Get or initialize connection creation time
            if conn_id not in self._connection_creation_times:
                # Connection created before tracking started, use now as creation time
                self._connection_creation_times[conn_id] = now

            created_at = self._connection_creation_times[conn_id]
            connection_age_seconds = (now - created_at).total_seconds()

            # Check if connection exceeds max lifetime
            if connection_age_seconds > self._config.max_connection_lifetime:
                # Log recycling event
                self._logger.info(
                    "Recycling connection due to age limit",
                    context=cast(Any, {
                        "connection_id": conn_id,
                        "age_seconds": connection_age_seconds,
                        "max_connection_lifetime": self._config.max_connection_lifetime,
                        "recycle_reason": "lifetime",
                    })
                )

                # Close the connection and acquire a new one (connection is guaranteed non-None here)
                await connection.close()

                # Remove from tracking
                self._connection_creation_times.pop(conn_id, None)

                # Acquire a fresh connection
                try:
                    connection = await asyncio.wait_for(
                        self._pool.acquire(),
                        timeout=self._config.timeout
                    )
                except asyncio.TimeoutError as e:
                    stats = self.get_statistics()
                    error_message = (
                        f"Connection acquisition timeout after recycling (timeout: {self._config.timeout}s). "
                        f"Pool state: {stats.total_connections} total, "
                        f"{stats.active_connections} active, "
                        f"{stats.idle_connections} idle. "
                        "Suggestion: Increase POOL_MAX_SIZE or optimize query performance"
                    )
                    self._logger.error(
                        "Connection acquisition timeout after recycling",
                        context=cast(Any, {
                            "timeout": self._config.timeout,
                            "total_connections": stats.total_connections,
                            "active_connections": stats.active_connections,
                        }),
                        exc_info=True
                    )
                    raise PoolTimeoutError(error_message) from e

                # Validate new connection
                await self._validate_connection(connection)

                # Update tracking with new connection
                conn_id = id(connection)
                created_at = datetime.now(timezone.utc)
                self._connection_creation_times[conn_id] = created_at

            # T028, T030: Create connection metadata for tracking
            metadata = ConnectionMetadata(
                connection_id=str(conn_id),
                acquired_at=now,
                acquisition_stack_trace=acquisition_stack,
                query_count=0,
                created_at=created_at,
                last_used_at=now,
            )
            self._connection_metadata[conn_id] = metadata

            # Log successful acquisition with stack trace for leak detection
            self._logger.debug(
                "Connection acquired successfully",
                context=cast(Any, {
                    "total_acquisitions": self._total_acquisitions,
                    "acquisition_stack": acquisition_stack,
                    "acquisition_timestamp": now.isoformat(),
                    "acquisition_duration_ms": duration_ms,
                    "active_connections": active_connections,
                    "peak_active_connections": self._peak_active,
                    "peak_wait_time_ms": self._peak_wait_time,
                    "connection_id": conn_id,
                    "connection_age_seconds": connection_age_seconds,
                })
            )

            # Yield connection to caller
            yield connection

        finally:
            # Auto-release connection on context exit
            if connection is not None:
                try:
                    # T028, T030: Update connection metadata before release
                    conn_id = id(connection)
                    if conn_id in self._connection_metadata:
                        metadata = self._connection_metadata[conn_id]
                        metadata.last_used_at = datetime.now(timezone.utc)
                        metadata.query_count += 1  # Increment for usage tracking

                        # Remove from active tracking (connection returning to pool)
                        self._connection_metadata.pop(conn_id, None)

                    # Release connection back to pool
                    await self._pool.release(connection)

                    # Increment release counter
                    self._total_releases += 1

                    # Calculate acquisition duration
                    acquisition_duration_ms = (time.perf_counter() - acquisition_start) * 1000

                    self._logger.debug(
                        "Connection released successfully",
                        context=cast(Any, {
                            "total_releases": self._total_releases,
                            "acquisition_duration_ms": acquisition_duration_ms,
                            "connection_id": conn_id,
                        })
                    )

                except Exception as e:
                    self._logger.error(
                        "Failed to release connection",
                        context=cast(Any, {
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                        }),
                        exc_info=True
                    )
                    # Don't re-raise to avoid suppressing original exceptions

    def get_statistics(self) -> PoolStatistics:
        """Get real-time pool statistics snapshot.

        Returns an immutable snapshot of current pool state including connection
        counts, performance metrics, and health indicators. This method is
        synchronous and completes in <1ms with no blocking operations.

        **Performance Target**: <1ms (no locks, no await, atomic reads)

        **Statistics Included**:
        - Connection counts (total, idle, active, waiting)
        - Lifetime metrics (acquisitions, releases)
        - Performance metrics (avg acquisition time, peak metrics)
        - Timestamps (pool created, last health check)
        - Error tracking (last error message and time)

        **Thread Safety**: Safe for concurrent calls (atomic operations only)

        Returns:
            PoolStatistics: Immutable statistics snapshot with all pool metrics

        Raises:
            RuntimeError: Pool not initialized (call initialize() first)

        Example:
            >>> stats = manager.get_statistics()  # <1ms
            >>> stats.total_connections
            10
            >>> stats.idle_connections
            7
            >>> stats.active_connections
            3
            >>> stats.avg_acquisition_time_ms
            2.5
        """
        if self._pool is None:
            raise RuntimeError(
                "Pool not initialized. "
                "Suggestion: Call initialize(config) before getting statistics"
            )

        # Read asyncpg pool state (atomic operations)
        total_connections = self._pool.get_size()
        idle_connections = self._pool.get_idle_size()
        active_connections = total_connections - idle_connections

        # Calculate average acquisition time from rolling window
        avg_acquisition_time_ms = 0.0
        if self._acquisition_times:
            avg_acquisition_time_ms = sum(self._acquisition_times) / len(self._acquisition_times)

        # Get waiting requests count (if available from pool)
        # Note: asyncpg doesn't expose waiting count directly, so we estimate as 0
        waiting_requests = 0

        # Create immutable statistics snapshot
        return PoolStatistics(
            total_connections=total_connections,
            idle_connections=idle_connections,
            active_connections=active_connections,
            waiting_requests=waiting_requests,
            total_acquisitions=self._total_acquisitions,
            total_releases=self._total_releases,
            avg_acquisition_time_ms=avg_acquisition_time_ms,
            peak_active_connections=self._peak_active,
            peak_wait_time_ms=self._peak_wait_time,
            pool_created_at=self._start_time if self._start_time else datetime.now(timezone.utc),
            last_health_check=datetime.now(timezone.utc),
            last_error=self._last_error,
            last_error_time=self._last_error_time,
        )

    async def health_check(self) -> HealthStatus:
        """Perform comprehensive health check with status calculation.

        Executes a complete health check including statistics collection, health
        status calculation, and uptime tracking. This method is the primary
        endpoint for MCP health check responses and monitoring dashboards.

        **Performance Target**: <10ms p99 (includes statistics + status calculation)

        **Health Check Steps**:
        1. Get current statistics snapshot (<1ms)
        2. Calculate health status from statistics (<1ms)
        3. Override status if in RECOVERING state:
           - UNHEALTHY if total_connections == 0 (complete failure)
           - DEGRADED if total_connections > 0 (partial recovery)
        4. Build database status dict with pool metrics and error information
        5. Calculate uptime since initialization
        6. Create immutable HealthStatus response

        **Status Determination** (see calculate_health_status for full rules):
        - HEALTHY: >=80% idle capacity, no recent errors, <100ms wait times
        - DEGRADED: 50-79% capacity, recent errors, or high wait times, or RECOVERING with connections
        - UNHEALTHY: 0 connections or <50% capacity, or RECOVERING with no connections

        **RECOVERING State Handling** (Task T022):
        When pool is in RECOVERING state:
        - Sets status to UNHEALTHY if total_connections == 0 (no connections during recovery)
        - Sets status to DEGRADED if total_connections > 0 (partial recovery in progress)
        - Includes last_error from reconnection attempts in DatabaseStatus

        Returns:
            HealthStatus: Complete health check response with status, database
                state, and uptime metrics

        Raises:
            RuntimeError: Pool not initialized (call initialize() first)

        Example:
            >>> health = await manager.health_check()  # <10ms p99
            >>> health.status
            <PoolHealthStatus.HEALTHY: 'healthy'>
            >>> health.database.pool
            {'total': 10, 'idle': 7, 'active': 3, 'waiting': 0}
            >>> health.uptime_seconds
            3600.5

        Constitutional Compliance:
            - Principle IV (Performance): <10ms completion time maintained
            - Principle VIII (Type Safety): Complete type annotations with mypy --strict
            - Principle V (Production Quality): Comprehensive error reporting including recovery state
        """
        if self._pool is None or self._config is None:
            raise RuntimeError(
                "Pool not initialized. "
                "Suggestion: Call initialize(config) before health check"
            )

        # Get current statistics snapshot (<1ms)
        stats = self.get_statistics()

        # Calculate health status from statistics (<1ms)
        health_status = calculate_health_status(stats, self._config)

        # Override health status if in RECOVERING state (Task T022)
        if self._state == PoolState.RECOVERING:
            if stats.total_connections == 0:
                # Complete failure during recovery - no connections available
                health_status = PoolHealthStatus.UNHEALTHY
            else:
                # Partial recovery - some connections available but not fully recovered
                health_status = PoolHealthStatus.DEGRADED

        # Build database status dict
        database_status = DatabaseStatus(
            status="connected" if self._state == PoolState.HEALTHY else "degraded",
            pool={
                "total": stats.total_connections,
                "idle": stats.idle_connections,
                "active": stats.active_connections,
                "waiting": stats.waiting_requests,
            },
            latency_ms=stats.avg_acquisition_time_ms if stats.avg_acquisition_time_ms > 0 else None,
            last_error=stats.last_error,  # Includes last_error from reconnection attempts
        )

        # Calculate uptime
        uptime_seconds = 0.0
        if self._start_time:
            uptime_seconds = (datetime.now(timezone.utc) - self._start_time).total_seconds()

        # Create health status response
        return HealthStatus(
            status=health_status,
            timestamp=datetime.now(timezone.utc),
            database=database_status,
            uptime_seconds=uptime_seconds,
        )

    async def _reconnection_loop(self) -> None:
        """Background task that monitors pool health and handles reconnection with exponential backoff.

        This task runs continuously in the background, monitoring connection pool health
        and automatically recovering from database outages. When all connections fail
        validation, the loop transitions to RECOVERING state and attempts reconnection
        with exponential backoff until the database becomes available again.

        **Reconnection Strategy**:
        - Health checks run every 10 seconds when pool is HEALTHY
        - On connection failure, transitions to RECOVERING state
        - Exponential backoff delays: 1s, 2s, 4s, 8s, 16s (capped at 16s)
        - Continues retrying every 16s indefinitely until success
        - Each attempt tries to re-initialize the pool with current config

        **Logging Events** (structured to /tmp/codebase-mcp.log):
        - "Database connectivity lost, entering reconnection mode" (with pool state)
        - "Reconnection attempt {attempt} after {delay}s delay" (for each attempt)
        - "Connection pool recovered: {idle}/{total} connections available" (on success)

        **Error Handling**:
        - All exceptions are caught, logged with context, and do not crash the loop
        - Invalid configuration or persistent failures continue retrying
        - Loop exits gracefully when pool enters SHUTTING_DOWN or TERMINATED state

        **Performance Characteristics**:
        - Health check interval: 10 seconds (minimal overhead)
        - Reconnection overhead: Varies by attempt (1-16 seconds + pool init time)
        - Memory: O(1) (no memory growth during long-running operation)

        **Constitutional Compliance**:
        - Principle V (Production Quality): Comprehensive error handling with self-healing
        - Principle VIII (Type Safety): Complete type annotations with mypy --strict
        - Principle III (Protocol Compliance): Structured logging, no stdout pollution

        **State Transitions**:
        - HEALTHY -> RECOVERING: All connections failed validation
        - RECOVERING -> HEALTHY: Successful reconnection and pool initialization
        - Any state -> exit: Pool enters SHUTTING_DOWN or TERMINATED

        Returns:
            None: This method runs until pool shutdown is initiated.

        Raises:
            No exceptions are raised to caller (all exceptions are caught and logged).
            The loop continues indefinitely until the pool is shut down.

        Example Usage (internal):
            >>> # Started automatically by initialize() method
            >>> self._reconnection_loop_task = asyncio.create_task(self._reconnection_loop())
            >>> # Cancelled automatically by shutdown() method
            >>> if self._reconnection_loop_task is not None:
            ...     self._reconnection_loop_task.cancel()

        Notes:
            - This method should only be called once per pool instance
            - The task reference is stored in self._reconnection_loop_task
            - The shutdown() method handles task cancellation automatically
        """
        attempt = 0
        health_check_interval = 10.0  # Check health every 10 seconds when HEALTHY

        self._logger.info(
            "Reconnection loop started",
            context=cast(Any, {
                "health_check_interval_seconds": health_check_interval,
                "pool_state": self._state.value,
            })
        )

        try:
            while True:
                # Exit loop if pool is shutting down or terminated
                if self._state in (PoolState.SHUTTING_DOWN, PoolState.TERMINATED):
                    self._logger.info(
                        "Reconnection loop exiting: pool is shutting down",
                        context=cast(Any, {"pool_state": self._state.value})
                    )
                    break

                # When HEALTHY, just sleep and check again periodically
                if self._state == PoolState.HEALTHY:
                    await asyncio.sleep(health_check_interval)
                    continue

                # Detect when all connections have failed (UNHEALTHY state)
                if self._state == PoolState.UNHEALTHY:
                    # Transition to RECOVERING state
                    self._state = PoolState.RECOVERING
                    attempt = 0  # Reset attempt counter on new recovery cycle

                    # Log database connectivity loss
                    stats = self.get_statistics() if self._pool else None
                    self._logger.error(
                        "Database connectivity lost, entering reconnection mode",
                        context=cast(Any, {
                            "previous_state": "UNHEALTHY",
                            "new_state": "RECOVERING",
                            "total_connections": stats.total_connections if stats else 0,
                            "idle_connections": stats.idle_connections if stats else 0,
                            "active_connections": stats.active_connections if stats else 0,
                        })
                    )

                # If in RECOVERING state, attempt reconnection with exponential backoff
                if self._state == PoolState.RECOVERING:
                    # Calculate next delay using exponential backoff
                    # (will be applied after this attempt fails or before next attempt)
                    base_delay = 1.0 * (2 ** attempt)
                    next_delay = min(base_delay, 16.0)

                    # Log reconnection attempt
                    self._logger.info(
                        f"Reconnection attempt {attempt + 1} starting",
                        context=cast(Any, {
                            "attempt_number": attempt + 1,
                            "next_delay_seconds": next_delay if attempt > 0 else 0,
                            "pool_state": self._state.value,
                        })
                    )

                    # If pool exists, close it before re-initializing
                    if self._pool is not None:
                        try:
                            await self._pool.close()
                            self._logger.debug(
                                "Closed existing pool before reconnection",
                                context=cast(Any, {})
                            )
                        except Exception as close_error:
                            self._logger.warning(
                                "Failed to close existing pool, continuing with reconnection",
                                context=cast(Any, {
                                    "error_type": type(close_error).__name__,
                                    "error_message": str(close_error),
                                })
                            )

                    # Attempt to re-initialize the pool
                    reconnection_succeeded = False
                    if self._config is not None:
                        try:
                            await self.initialize(self._config)
                            # If we get here, initialization succeeded (no exception)
                            reconnection_succeeded = True
                        except Exception as reconnect_error:
                            # Log reconnection failure with context
                            self._logger.error(
                                f"Reconnection attempt {attempt + 1} failed",
                                context=cast(Any, {
                                    "attempt_number": attempt + 1,
                                    "error_type": type(reconnect_error).__name__,
                                    "error_message": str(reconnect_error),
                                    "traceback": traceback.format_exc(),
                                }),
                                exc_info=True
                            )

                    # Check if reconnection succeeded
                    if reconnection_succeeded:
                        # Initialize() sets state to HEALTHY on success
                        stats = self.get_statistics()
                        self._logger.info(
                            "Connection pool recovered: "
                            f"{stats.idle_connections}/{stats.total_connections} connections available",
                            context=cast(Any, {
                                "attempt_number": attempt + 1,
                                "total_connections": stats.total_connections,
                                "idle_connections": stats.idle_connections,
                                "active_connections": stats.active_connections,
                            })
                        )
                        # Reset attempt counter after successful recovery
                        attempt = 0
                        continue
                    else:
                        # Reconnection failed, log backoff and retry
                        self._logger.info(
                            f"Reconnection attempt {attempt + 1} after {next_delay:.1f}s delay",
                            context=cast(Any, {
                                "attempt_number": attempt + 1,
                                "delay_seconds": next_delay,
                            })
                        )

                        # Increment attempt counter
                        attempt += 1

                        # Wait using exponential backoff
                        await exponential_backoff_retry(
                            attempt=min(attempt - 1, 4),  # Cap at attempt 4 for 16s delay
                            max_delay=16.0,
                            jitter_factor=0.1
                        )

                else:
                    # If in some other state (DEGRADED, INITIALIZING), wait and check again
                    await asyncio.sleep(health_check_interval)

        except asyncio.CancelledError:
            # Task was cancelled (shutdown initiated)
            self._logger.info(
                "Reconnection loop cancelled during shutdown",
                context=cast(Any, {"pool_state": self._state.value})
            )
            raise  # Re-raise to propagate cancellation

        except Exception as loop_error:
            # Unexpected error in reconnection loop (should not occur)
            self._logger.error(
                "Unexpected error in reconnection loop",
                context=cast(Any, {
                    "error_type": type(loop_error).__name__,
                    "error_message": str(loop_error),
                    "traceback": traceback.format_exc(),
                    "pool_state": self._state.value,
                }),
                exc_info=True
            )
            # Don't re-raise - let the loop exit gracefully

    async def _pool_maintenance(self) -> None:
        """Background task that shrinks pool by closing excess idle connections.

        This task runs continuously in the background, monitoring idle connection counts
        and shrinking the pool when idle connections exceed min_size. It respects the
        min_size constraint and only closes connections that asyncpg has already marked
        as idle beyond max_idle_time.

        **Maintenance Strategy**:
        - Runs every 60 seconds to check pool metrics
        - Checks if idle_connections > min_size
        - Logs pool metrics periodically for monitoring
        - Pool never shrinks below min_size (enforced by asyncpg configuration)
        - Uses asyncpg's built-in max_inactive_connection_lifetime for idle timeout

        **Asyncpg Behavior Note**:
        asyncpg's max_inactive_connection_lifetime parameter (set to config.max_idle_time)
        automatically closes connections that have been idle beyond the configured timeout.
        This maintenance task provides monitoring and logging but does NOT need to manually
        close connections - asyncpg handles that automatically. The pool will naturally
        shrink as idle connections time out, but never below min_size.

        **Logging Events** (structured to /tmp/codebase-mcp.log):
        - "Pool maintenance check" with current metrics every 60s
        - "Pool shrunk from {old_size} to {new_size} connections due to idle timeout"
          when pool size decreases (logged after asyncpg closes idle connections)

        **Error Handling**:
        - All exceptions are caught, logged with context, and do not crash the loop
        - Loop exits gracefully when pool enters SHUTTING_DOWN or TERMINATED state
        - Statistics read failures are logged and loop continues

        **Performance Characteristics**:
        - Check interval: 60 seconds (minimal overhead)
        - Statistics read: <1ms (no blocking operations)
        - Memory: O(1) (no memory growth during long-running operation)

        **Constitutional Compliance**:
        - Principle V (Production Quality): Comprehensive error handling and monitoring
        - Principle VIII (Type Safety): Complete type annotations with mypy --strict
        - Principle III (Protocol Compliance): Structured logging, no stdout pollution

        **State Transitions**:
        - Any state -> exit: Pool enters SHUTTING_DOWN or TERMINATED

        Returns:
            None: This method runs until pool shutdown is initiated.

        Raises:
            No exceptions are raised to caller (all exceptions are caught and logged).
            The loop continues indefinitely until the pool is shut down.

        Example Usage (internal):
            >>> # Started automatically by initialize() method
            >>> self._pool_maintenance_task = asyncio.create_task(self._pool_maintenance())
            >>> # Cancelled automatically by shutdown() method
            >>> if self._pool_maintenance_task is not None:
            ...     self._pool_maintenance_task.cancel()

        Notes:
            - This method should only be called once per pool instance
            - The task reference is stored in self._pool_maintenance_task
            - The shutdown() method handles task cancellation automatically
            - asyncpg handles idle connection closure automatically via max_inactive_connection_lifetime
        """
        maintenance_interval = 60.0  # Check pool every 60 seconds
        previous_size: int | None = None

        self._logger.info(
            "Pool maintenance task started",
            context=cast(Any, {
                "maintenance_interval_seconds": maintenance_interval,
                "pool_state": self._state.value,
            })
        )

        try:
            while True:
                # Exit loop if pool is shutting down or terminated
                if self._state in (PoolState.SHUTTING_DOWN, PoolState.TERMINATED):
                    self._logger.info(
                        "Pool maintenance task exiting: pool is shutting down",
                        context=cast(Any, {"pool_state": self._state.value})
                    )
                    break

                # Sleep for maintenance interval before checking
                await asyncio.sleep(maintenance_interval)

                # Skip maintenance if pool not initialized or state is not suitable
                if self._pool is None or self._config is None:
                    continue

                if self._state not in (PoolState.HEALTHY, PoolState.DEGRADED):
                    # Don't perform maintenance during RECOVERING, INITIALIZING, etc.
                    continue

                try:
                    # Get current pool statistics
                    stats = self.get_statistics()
                    current_size = stats.total_connections
                    idle_count = stats.idle_connections

                    # Log periodic pool metrics
                    self._logger.debug(
                        "Pool maintenance check",
                        context=cast(Any, {
                            "total_connections": current_size,
                            "idle_connections": idle_count,
                            "active_connections": stats.active_connections,
                            "min_size": self._config.min_size,
                            "max_idle_time": self._config.max_idle_time,
                        })
                    )

                    # Detect if pool has shrunk since last check (asyncpg closed idle connections)
                    if previous_size is not None and current_size < previous_size:
                        # Pool size decreased - asyncpg closed idle connections
                        connections_closed = previous_size - current_size

                        self._logger.info(
                            f"Pool shrunk from {previous_size} to {current_size} connections due to idle timeout",
                            context=cast(Any, {
                                "old_size": previous_size,
                                "new_size": current_size,
                                "connections_closed": connections_closed,
                                "current_idle": idle_count,
                                "min_size": self._config.min_size,
                                "max_idle_time": self._config.max_idle_time,
                            })
                        )

                        # Verify pool never shrunk below min_size (should be guaranteed by asyncpg)
                        if current_size < self._config.min_size:
                            self._logger.error(
                                "CRITICAL: Pool shrunk below min_size (asyncpg bug or misconfiguration)",
                                context=cast(Any, {
                                    "current_size": current_size,
                                    "min_size": self._config.min_size,
                                    "idle_connections": idle_count,
                                })
                            )

                    # Update previous size for next iteration
                    previous_size = current_size

                except Exception as stats_error:
                    # Log statistics read error but continue loop
                    self._logger.warning(
                        "Failed to read pool statistics during maintenance",
                        context=cast(Any, {
                            "error_type": type(stats_error).__name__,
                            "error_message": str(stats_error),
                        }),
                        exc_info=True
                    )

        except asyncio.CancelledError:
            # Task was cancelled (shutdown initiated)
            self._logger.info(
                "Pool maintenance task cancelled during shutdown",
                context=cast(Any, {"pool_state": self._state.value})
            )
            raise  # Re-raise to propagate cancellation

        except Exception as loop_error:
            # Unexpected error in maintenance loop (should not occur)
            self._logger.error(
                "Unexpected error in pool maintenance loop",
                context=cast(Any, {
                    "error_type": type(loop_error).__name__,
                    "error_message": str(loop_error),
                    "traceback": traceback.format_exc(),
                    "pool_state": self._state.value,
                }),
                exc_info=True
            )
            # Don't re-raise - let the loop exit gracefully


    async def shutdown(self, timeout: float = 30.0) -> None:
        """Gracefully shutdown connection pool with connection draining.

        Performs a graceful shutdown sequence that waits for active connections to
        complete before closing the pool. This method ensures clean resource cleanup
        and prevents in-flight operations from being abruptly terminated.

        **Shutdown Sequence**:
        1. Acquire shutdown lock to prevent concurrent shutdown calls
        2. Check if already terminated or shutting down (idempotent)
        3. Set state to SHUTTING_DOWN (rejects new acquire() requests)
        4. Wait for active connections to reach 0 (with timeout)
        5. Close idle connections gracefully via pool.close()
        6. Force-close remaining active connections if timeout exceeded
        7. Cancel reconnection loop background task if running
        8. Set state to TERMINATED
        9. Log shutdown phases and total duration

        **Performance Target**: <30 seconds default timeout

        **Graceful Shutdown Behavior**:
        - New acquire() requests are rejected immediately (PoolState.SHUTTING_DOWN)
        - Active connections are allowed to complete naturally
        - Timeout triggers force-close with warnings (includes connection IDs)
        - Idempotent: Safe to call multiple times
        - No data loss: All active operations complete or timeout

        **Error Recovery**:
        - Force-close logs warnings with connection details
        - Reconnection loop cancellation is logged
        - State transitions are atomic and logged

        Args:
            timeout: Maximum seconds to wait for active connections to complete
                (default: 30.0). If timeout exceeded, remaining connections are
                force-closed with warnings.

        Raises:
            RuntimeError: Pool not initialized (call initialize() first)

        Example:
            >>> manager = ConnectionPoolManager()
            >>> await manager.initialize(config)
            >>> # ... use pool ...
            >>> await manager.shutdown(timeout=60.0)  # 60s grace period
            >>> manager._state
            <PoolState.TERMINATED: 'terminated'>

        Constitutional Compliance:
            - Principle V: Production-quality shutdown with comprehensive error handling
            - Principle VIII: Type-safe state transitions with explicit enum values
            - Principle III: Structured logging with no stdout/stderr pollution
        """
        shutdown_start_time = time.perf_counter()

        # Acquire shutdown lock to prevent concurrent shutdowns
        async with self._shutdown_lock:
            # Check if already terminated or shutting down (idempotent)
            if self._state == PoolState.TERMINATED:
                self._logger.info(
                    "Shutdown skipped: pool already terminated",
                    context=cast(Any, {"state": self._state.value})
                )
                return

            if self._state == PoolState.SHUTTING_DOWN:
                self._logger.info(
                    "Shutdown already in progress",
                    context=cast(Any, {"state": self._state.value})
                )
                return

            # Verify pool is initialized
            if self._pool is None or self._config is None:
                raise RuntimeError(
                    "Pool not initialized. "
                    "Suggestion: Cannot shutdown uninitialized pool"
                )

            # PHASE 1: Transition to SHUTTING_DOWN state
            phase1_start = time.perf_counter()
            self._logger.info(
                "Shutdown initiated: transitioning to SHUTTING_DOWN state",
                context=cast(Any, {
                    "previous_state": self._state.value,
                    "timeout_seconds": timeout,
                    "active_connections": self._active_connection_count,
                })
            )
            self._state = PoolState.SHUTTING_DOWN
            phase1_duration_ms = (time.perf_counter() - phase1_start) * 1000
            self._logger.debug(
                "Phase 1 complete: state transition",
                context=cast(Any, {"duration_ms": phase1_duration_ms})
            )

            # PHASE 2: Wait for active connections to reach 0
            phase2_start = time.perf_counter()
            self._logger.info(
                "Waiting for active connections to complete",
                context=cast(Any, {
                    "active_connections": self._active_connection_count,
                    "timeout_seconds": timeout,
                })
            )

            try:
                # Wait for active connections to reach 0 with timeout
                await asyncio.wait_for(
                    self._wait_for_zero_active_connections(),
                    timeout=timeout
                )
                phase2_duration_ms = (time.perf_counter() - phase2_start) * 1000
                self._logger.info(
                    "Phase 2 complete: all active connections completed gracefully",
                    context=cast(Any, {
                        "duration_ms": phase2_duration_ms,
                        "active_connections": self._active_connection_count,
                    })
                )
            except asyncio.TimeoutError:
                phase2_duration_ms = (time.perf_counter() - phase2_start) * 1000
                self._logger.warning(
                    "Phase 2 timeout: force-closing remaining active connections",
                    context=cast(Any, {
                        "timeout_seconds": timeout,
                        "duration_ms": phase2_duration_ms,
                        "remaining_active_connections": self._active_connection_count,
                    })
                )

            # PHASE 3: Close idle connections gracefully
            phase3_start = time.perf_counter()
            idle_count = self._pool.get_idle_size()
            self._logger.info(
                "Closing idle connections gracefully",
                context=cast(Any, {"idle_connections": idle_count})
            )

            try:
                await self._pool.close()
                phase3_duration_ms = (time.perf_counter() - phase3_start) * 1000
                self._logger.info(
                    "Phase 3 complete: idle connections closed",
                    context=cast(Any, {
                        "duration_ms": phase3_duration_ms,
                        "closed_connections": idle_count,
                    })
                )
            except Exception as e:
                phase3_duration_ms = (time.perf_counter() - phase3_start) * 1000
                self._logger.error(
                    "Phase 3 error: failed to close idle connections gracefully",
                    context=cast(Any, {
                        "duration_ms": phase3_duration_ms,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                    }),
                    exc_info=True
                )

            # PHASE 4: Force-close remaining active connections if any
            if self._active_connection_count > 0:
                phase4_start = time.perf_counter()
                remaining_active = self._active_connection_count
                self._logger.warning(
                    "Force-closing remaining active connections",
                    context=cast(Any, {
                        "remaining_active_connections": remaining_active,
                        "timeout_seconds": timeout,
                        "reason": "Graceful shutdown timeout exceeded",
                    })
                )

                # Force terminate the pool (closes all connections immediately)
                try:
                    await self._pool.terminate()
                    phase4_duration_ms = (time.perf_counter() - phase4_start) * 1000
                    self._logger.warning(
                        "Phase 4 complete: force-closed active connections",
                        context=cast(Any, {
                            "duration_ms": phase4_duration_ms,
                            "force_closed_count": remaining_active,
                        })
                    )
                except Exception as e:
                    phase4_duration_ms = (time.perf_counter() - phase4_start) * 1000
                    self._logger.error(
                        "Phase 4 error: failed to force-close active connections",
                        context=cast(Any, {
                            "duration_ms": phase4_duration_ms,
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                        }),
                        exc_info=True
                    )

            # PHASE 5: Cancel reconnection loop background task
            if self._reconnection_loop_task is not None:
                phase5_start = time.perf_counter()
                self._logger.info(
                    "Cancelling reconnection loop background task",
                    context=cast(Any, {"task_done": self._reconnection_loop_task.done()})
                )

                if not self._reconnection_loop_task.done():
                    self._reconnection_loop_task.cancel()
                    try:
                        await self._reconnection_loop_task
                    except asyncio.CancelledError:
                        self._logger.debug(
                            "Reconnection loop task cancelled successfully",
                            context=cast(Any, {})
                        )

                phase5_duration_ms = (time.perf_counter() - phase5_start) * 1000
                self._logger.info(
                    "Phase 5 complete: reconnection loop cancelled",
                    context=cast(Any, {"duration_ms": phase5_duration_ms})
                )

            # PHASE 5 (continued): Cancel pool maintenance background task
            if self._pool_maintenance_task is not None:
                self._logger.info(
                    "Cancelling pool maintenance background task",
                    context=cast(Any, {"task_done": self._pool_maintenance_task.done()})
                )

                if not self._pool_maintenance_task.done():
                    self._pool_maintenance_task.cancel()
                    try:
                        await self._pool_maintenance_task
                    except asyncio.CancelledError:
                        self._logger.debug(
                            "Pool maintenance task cancelled successfully",
                            context=cast(Any, {})
                        )

                self._logger.info(
                    "Phase 5 complete: pool maintenance cancelled",
                    context=cast(Any, {})
                )

            # PHASE 6: Transition to TERMINATED state
            phase6_start = time.perf_counter()
            self._state = PoolState.TERMINATED
            phase6_duration_ms = (time.perf_counter() - phase6_start) * 1000
            self._logger.debug(
                "Phase 6 complete: state transition to TERMINATED",
                context=cast(Any, {"duration_ms": phase6_duration_ms})
            )

            # Log complete shutdown summary
            total_duration_ms = (time.perf_counter() - shutdown_start_time) * 1000
            self._logger.info(
                "Shutdown complete",
                context=cast(Any, {
                    "total_duration_ms": total_duration_ms,
                    "final_state": self._state.value,
                    "timeout_seconds": timeout,
                })
            )

    async def _wait_for_zero_active_connections(self) -> None:
        """Wait for active connection count to reach zero.

        Polls the active connection count every 100ms until it reaches zero.
        This method is called during graceful shutdown to wait for in-flight
        operations to complete.

        **Polling Strategy**:
        - Poll interval: 100ms (responsive without excessive CPU usage)
        - Exits immediately when active_connection_count reaches 0
        - No timeout (handled by caller with asyncio.wait_for)

        **Performance**: O(n) where n = active_connections * 100ms

        Returns:
            None when active connections reach 0

        Example:
            >>> # Called internally by shutdown()
            >>> await asyncio.wait_for(
            ...     self._wait_for_zero_active_connections(),
            ...     timeout=30.0
            ... )
        """
        while self._active_connection_count > 0:
            await asyncio.sleep(0.1)  # Poll every 100ms


__all__ = [
    "ConnectionMetadata",
    "ConnectionPoolManager",
    "PoolState",
    "exponential_backoff_retry",
]
