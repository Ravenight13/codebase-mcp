"""
Example usage of connection pool structured logging.

This file demonstrates proper usage patterns for the connection pool logging
module with constitutional compliance and best practices.

Run this file to see example log output in /tmp/codebase-mcp.log
"""

from __future__ import annotations

from typing import Any, cast

from src.connection_pool.pool_logging import (
    get_pool_logger,
    get_pool_structured_logger,
    log_pool_initialization,
    log_connection_acquisition,
    log_reconnection_attempt,
    log_pool_statistics,
    log_pool_event,
)


def example_basic_pool_logging() -> None:
    """Example: Basic pool logging with standard logger."""
    logger = get_pool_logger(__name__)

    # Simple log messages
    logger.info("Connection pool module initialized")
    logger.debug("Configuration validation passed")
    logger.warning("Pool capacity at 75%")


def example_structured_pool_logging() -> None:
    """Example: Structured pool logging with context."""
    logger = get_pool_structured_logger(__name__)

    # Log with rich context
    logger.info(
        "Pool initialized successfully",
        context=cast(Any, {
            "min_size": 2,
            "max_size": 10,
            "database_url": "postgresql+asyncpg://localhost:5432/codebase_mcp",
            "initialization_time_ms": 125.5,
        }),
    )

    # Log connection acquisition
    logger.debug(
        "Connection acquired from pool",
        context=cast(Any, {
            "pool_size": 10,
            "active_connections": 5,
            "idle_connections": 5,
            "acquisition_time_ms": 2.3,
        }),
    )


def example_convenience_functions() -> None:
    """Example: Using convenience logging functions."""
    logger = get_pool_logger(__name__)

    # Pool initialization
    log_pool_initialization(
        logger=logger,
        min_size=2,
        max_size=10,
        duration_ms=125.5,
        success=True,
    )

    # Connection acquisition
    log_connection_acquisition(
        logger=logger,
        acquisition_time_ms=2.3,
        pool_size=10,
        active_connections=5,
        idle_connections=5,
    )

    # Reconnection attempt
    log_reconnection_attempt(
        logger=logger,
        attempt=3,
        delay_seconds=4.0,
        success=False,
    )

    # Pool statistics
    log_pool_statistics(
        logger=logger,
        total_connections=10,
        idle_connections=7,
        active_connections=3,
        waiting_requests=0,
        total_acquisitions=150,
        total_releases=147,
        avg_acquisition_time_ms=2.5,
    )


def example_error_logging() -> None:
    """Example: Error logging with exception context."""
    logger = get_pool_structured_logger(__name__)

    try:
        # Simulate error
        msg = "Database connection validation failed"
        raise ConnectionError(msg)
    except ConnectionError:
        logger.error(
            "Connection validation failed",
            context=cast(Any, {
                "connection_id": "conn-12345",
                "pool_size": 10,
                "active_connections": 8,
                "error_type": "ConnectionError",
            }),
        )


def example_custom_events() -> None:
    """Example: Custom pool event logging."""
    logger = get_pool_logger(__name__)

    # Custom event with structured context
    log_pool_event(
        logger=logger,
        level="info",
        event="connection_recycled",
        context={
            "connection_id": "conn-67890",
            "reason": "query_limit_exceeded",
            "query_count": 1000,
            "max_queries": 1000,
        },
    )

    # Another custom event
    log_pool_event(
        logger=logger,
        level="warning",
        event="pool_capacity_warning",
        context={
            "idle_percentage": 45.0,
            "threshold": 50.0,
            "recommendation": "Increase POOL_MAX_SIZE",
        },
    )


def example_lifecycle_logging() -> None:
    """Example: Pool lifecycle event logging."""
    logger = get_pool_structured_logger(__name__)

    # Initialization phase
    logger.info(
        "Pool initialization started",
        context=cast(Any, {
            "min_size": 2,
            "max_size": 10,
            "state": "INITIALIZING",
        }),
    )

    # Healthy state
    logger.info(
        "Pool health check passed",
        context=cast(Any, {
            "state": "HEALTHY",
            "total_connections": 5,
            "idle_connections": 4,
            "active_connections": 1,
        }),
    )

    # Recovery phase
    logger.warning(
        "Pool entering recovery mode",
        context=cast(Any, {
            "state": "RECOVERING",
            "reason": "database_connectivity_lost",
            "reconnection_attempts": 0,
        }),
    )

    # Shutdown phase
    logger.info(
        "Pool shutdown initiated",
        context=cast(Any, {
            "state": "SHUTTING_DOWN",
            "active_connections": 2,
            "grace_period_seconds": 30.0,
        }),
    )


if __name__ == "__main__":
    # These examples demonstrate usage patterns
    # The actual log output goes to /tmp/codebase-mcp.log in JSON format
    print("Running connection pool logging examples...")
    print("Check /tmp/codebase-mcp.log for JSON structured log output")
    print()

    example_basic_pool_logging()
    example_structured_pool_logging()
    example_convenience_functions()
    example_error_logging()
    example_custom_events()
    example_lifecycle_logging()

    print("Examples complete. Review /tmp/codebase-mcp.log for output.")
