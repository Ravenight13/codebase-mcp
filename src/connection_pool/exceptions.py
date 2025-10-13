"""
Connection Pool Exception Hierarchy.

This module defines the exception hierarchy for the connection pool management system.
All exceptions inherit from the base ConnectionPoolError class, providing a consistent
error handling interface for pool operations.

Exception Hierarchy:
    ConnectionPoolError (Base)
    ├── PoolConfigurationError      - Configuration validation failures
    ├── PoolInitializationError     - Pool startup failures
    ├── PoolTimeoutError            - Connection acquisition timeouts
    ├── ConnectionValidationError   - Connection health check failures
    └── PoolClosedError             - Operations on closed pool

Usage:
    try:
        await pool.acquire()
    except PoolTimeoutError as e:
        logger.error(f"Connection acquisition failed: {e}")
    except ConnectionPoolError as e:
        logger.error(f"Pool error: {e}")

Constitutional Compliance:
    - Principle V: Production Quality - Comprehensive error handling
    - Principle VIII: Type Safety - All exceptions fully typed
"""

from __future__ import annotations


class ConnectionPoolError(Exception):
    """
    Base exception for all connection pool errors.

    All connection pool exceptions inherit from this base class, allowing
    callers to catch all pool-related errors with a single exception handler.

    Attributes:
        message: Human-readable error description with context
        suggestion: Optional recommended action for resolution

    Example:
        try:
            await pool.acquire()
        except ConnectionPoolError as e:
            logger.error(f"Pool operation failed: {e}")
            # Handle pool error with fallback behavior
    """

    pass


class PoolConfigurationError(ConnectionPoolError):
    """
    Configuration validation failed during pool initialization.

    Raised when pool configuration parameters are invalid or inconsistent,
    such as max_size < min_size or negative timeout values.

    Examples:
        >>> raise PoolConfigurationError(
        ...     "max_size (5) must be >= min_size (10). "
        ...     "Suggestion: Increase POOL_MAX_SIZE to 10 or reduce POOL_MIN_SIZE to 5"
        ... )

        >>> raise PoolConfigurationError(
        ...     "timeout (-1.0) must be positive. "
        ...     "Suggestion: Set POOL_TIMEOUT to a positive value (e.g., 5.0)"
        ... )

    When raised:
        - During PoolConfig.validate() method
        - When environment variables contain invalid values
        - When runtime configuration updates violate constraints
    """

    pass


class PoolInitializationError(ConnectionPoolError):
    """
    Pool initialization failed during startup.

    Raised when the pool cannot establish the minimum required connections
    during initialization, or when database connectivity is unavailable.

    Examples:
        >>> raise PoolInitializationError(
        ...     "Failed to create min_size (2) connections: "
        ...     "Database connection refused on localhost:5432. "
        ...     "Suggestion: Verify database is running and connection credentials are correct"
        ... )

        >>> raise PoolInitializationError(
        ...     "Database migration state invalid: pending migrations detected. "
        ...     "Suggestion: Run 'alembic upgrade head' before starting the pool"
        ... )

    When raised:
        - During ConnectionPoolManager.__aenter__() startup
        - When min_size connections cannot be established
        - When database schema validation fails
    """

    pass


class PoolTimeoutError(ConnectionPoolError):
    """
    Connection acquisition timeout exceeded.

    Raised when a connection cannot be acquired within the configured timeout
    period, indicating pool exhaustion or slow query performance.

    Examples:
        >>> raise PoolTimeoutError(
        ...     f"Connection acquisition timeout after 5.0s. "
        ...     f"Pool state: 10 total, 10 active, 5 waiting. "
        ...     "Suggestion: Increase POOL_MAX_SIZE or optimize query performance"
        ... )

        >>> raise PoolTimeoutError(
        ...     "Connection acquisition timeout after 5.0s. "
        ...     "All connections in use by long-running queries. "
        ...     "Suggestion: Review active queries and consider adding connection timeout"
        ... )

    When raised:
        - During ConnectionPoolManager.acquire() when timeout expires
        - When pool is at max_size and no connections become available
        - When all connections are held by long-running operations

    Pool Statistics:
        Exception message includes current pool state:
        - total_connections: Current pool size
        - active_connections: Connections in use
        - waiting_requests: Queued acquisition requests
    """

    pass


class ConnectionValidationError(ConnectionPoolError):
    """
    Connection validation failed during health check.

    Raised when a connection fails the validation query (SELECT 1) or is
    detected as stale/broken. The connection is automatically recycled.

    Examples:
        >>> raise ConnectionValidationError(
        ...     "Connection validation failed: server closed connection unexpectedly. "
        ...     "Connection has been recycled. Retrying acquisition."
        ... )

        >>> raise ConnectionValidationError(
        ...     "Connection validation failed: query timeout after 1.0s. "
        ...     "Connection has been recycled. Check database load."
        ... )

    When raised:
        - During ConnectionPoolManager._validate_connection()
        - When SELECT 1 query fails or times out
        - When connection is detected as broken during health check

    Recovery:
        - Connection is automatically recycled (closed and replaced)
        - Caller should retry acquisition
        - Pool statistics reflect connection recycling
    """

    pass


class PoolClosedError(ConnectionPoolError):
    """
    Pool is closed and cannot accept requests.

    Raised when operations are attempted on a closed pool, indicating
    improper lifecycle management or shutdown sequence.

    Examples:
        >>> raise PoolClosedError(
        ...     "Cannot acquire connection: pool is closed. "
        ...     "Suggestion: Check pool lifecycle management and shutdown sequence"
        ... )

        >>> raise PoolClosedError(
        ...     "Cannot release connection: pool is closed. "
        ...     "Connection will be discarded without recycling."
        ... )

    When raised:
        - During acquire() after __aexit__() has been called
        - During release() after pool shutdown
        - When operations are attempted outside context manager scope

    Prevention:
        - Always use pool within async context manager:
          async with ConnectionPoolManager(config) as pool:
              conn = await pool.acquire()
        - Ensure proper shutdown ordering in application lifecycle
    """

    pass
