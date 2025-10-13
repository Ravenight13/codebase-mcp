"""
Connection Pool Structured Logging Configuration.

This module configures structured logging for the connection pool subsystem,
ensuring all logs are written to /tmp/codebase-mcp.log in JSON format with
proper log levels and context.

Constitutional Compliance:
- Principle III: Protocol Compliance - No stdout/stderr pollution (MCP SSE requirement)
- Principle V: Production Quality - Structured, rotatable, comprehensive logging
- Principle VIII: Type Safety - Full mypy --strict compliance

Integration:
- Uses the existing mcp_logging infrastructure for consistent JSON formatting
- All connection pool logs go to /tmp/codebase-mcp.log
- Provides convenience methods for common logging patterns

Usage:
    from src.connection_pool.logging import get_pool_logger, log_pool_event

    logger = get_pool_logger(__name__)
    logger.info("Pool initialized", extra={"context": {"min_size": 2, "max_size": 10}})

    # Or use convenience function
    log_pool_event(
        logger=logger,
        level="info",
        event="pool_initialized",
        context={"min_size": 2, "max_size": 10}
    )
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from src.mcp.mcp_logging import get_logger, get_structured_logger, StructuredLogger

# ==============================================================================
# Type Definitions
# ==============================================================================

LogLevel = Literal["debug", "info", "warning", "error", "critical"]

# ==============================================================================
# Connection Pool Logger Factory
# ==============================================================================


def get_pool_logger(name: str) -> logging.Logger:
    """Get configured logger for connection pool modules with JSON structured output.

    Creates a logger instance using the existing mcp_logging infrastructure,
    ensuring constitutional compliance with MCP protocol requirements and
    production-quality logging standards.

    **Logger Configuration**:
    - JSON structured logging with automatic field serialization
    - File-only output to /tmp/codebase-mcp.log (no stdout/stderr)
    - Automatic log rotation (100MB per file, 5 backup files)
    - Thread-safe for concurrent logging from multiple pool operations
    - Log level: INFO (configurable via environment variables)

    **Constitutional Compliance**:
    - Principle III (Protocol Compliance): No stdout/stderr pollution
    - Principle V (Production Quality): Structured, rotatable logging
    - Principle VIII (Type Safety): Complete type annotations

    Args:
        name: Logger name, typically __name__ from calling module.
            Used for hierarchical log filtering (e.g., "connection_pool.manager").

    Returns:
        logging.Logger: Configured logger instance with JSON structured output
            to /tmp/codebase-mcp.log. Use standard logging methods: debug(),
            info(), warning(), error(), critical().

    Example:
        >>> from src.connection_pool.pool_logging import get_pool_logger
        >>> logger = get_pool_logger(__name__)
        >>> logger.info(
        ...     "Pool initialized",
        ...     extra={"context": {"min_size": 2, "max_size": 10}}
        ... )
        >>> # Logs to /tmp/codebase-mcp.log:
        >>> # {"timestamp":"2025-10-13T14:30:00Z","level":"INFO",
        >>> #  "message":"Pool initialized","context":{"min_size":2,"max_size":10}}
    """
    return get_logger(name)


def get_pool_structured_logger(name: str) -> StructuredLogger:
    """Get structured logger with type-safe convenience methods for pool modules.

    Creates a StructuredLogger instance with type-safe logging methods that
    automatically handle context serialization and exception tracking. Preferred
    over get_pool_logger() for new code due to better type safety.

    **Convenience Methods**:
    - debug(message, context, exc_info): Debug-level logging with optional context
    - info(message, context, exc_info): Info-level logging with optional context
    - warning(message, context, exc_info): Warning-level logging with optional context
    - error(message, context, exc_info): Error-level logging with optional context
    - critical(message, context, exc_info): Critical-level logging with optional context

    **Context Serialization**:
    - Automatically serializes dict[str, Any] to JSON
    - Handles datetime objects with ISO 8601 format
    - Safely handles exceptions and stack traces

    **Constitutional Compliance**:
    - Principle VIII (Type Safety): Complete type annotations with mypy --strict
    - Principle III (Protocol Compliance): JSON structured output, no stdout/stderr
    - Principle V (Production Quality): Comprehensive error context capture

    Args:
        name: Logger name, typically __name__ from calling module.
            Used for hierarchical log filtering (e.g., "connection_pool.manager").

    Returns:
        StructuredLogger: Logger instance with type-safe convenience methods.
            All methods accept optional context dict and exc_info bool.

    Example:
        >>> from src.connection_pool.pool_logging import get_pool_structured_logger
        >>> logger = get_pool_structured_logger(__name__)
        >>> logger.info(
        ...     "Connection acquired",
        ...     context={
        ...         "pool_size": 10,
        ...         "active_connections": 5,
        ...         "acquisition_time_ms": 2.3
        ...     }
        ... )
        >>> # Error logging with exception context
        >>> try:
        ...     await pool.acquire()
        ... except Exception as e:
        ...     logger.error(
        ...         "Connection acquisition failed",
        ...         context={"timeout": 30.0},
        ...         exc_info=True
        ...     )
    """
    return get_structured_logger(name)


# ==============================================================================
# Convenience Logging Functions
# ==============================================================================


def log_pool_event(
    logger: logging.Logger,
    level: LogLevel,
    event: str,
    context: dict[str, Any] | None = None,
    exc_info: bool = False,
) -> None:
    """Log connection pool event with structured context and consistent formatting.

    Convenience function for logging common pool events with standardized
    structure, automatic context enrichment, and event name injection. Used
    throughout connection pool modules for consistent log formatting.

    **Event Structure**:
    All logged events include:
    - event: Event name for filtering and aggregation
    - timestamp: Automatic UTC timestamp from logger
    - level: Log level (DEBUG/INFO/WARNING/ERROR/CRITICAL)
    - context: User-provided structured data (optional)
    - exc_info: Exception traceback if exc_info=True

    **Performance**: <1ms overhead per log call (negligible)

    **Constitutional Compliance**:
    - Principle III (Protocol Compliance): Structured JSON output only
    - Principle VIII (Type Safety): Complete type annotations
    - Principle V (Production Quality): Comprehensive context capture

    Args:
        logger: Logger instance from get_pool_logger(__name__).
            Must be configured for JSON structured output.
        level: Log level as string literal. Valid values:
            "debug", "info", "warning", "error", "critical".
        event: Event name/description for log aggregation and filtering.
            Examples: "pool_initialized", "connection_acquired",
            "reconnection_attempt", "leak_detected".
        context: Structured context data as dict[str, Any]. Automatically
            serialized to JSON. Common fields: pool_size, active_connections,
            error_type, duration_ms. Optional, defaults to None.
        exc_info: Whether to include exception traceback in log. Set True
            when logging from exception handler. Defaults to False.

    Raises:
        KeyError: If level is not a valid LogLevel literal (should not occur
            with type checking enabled).

    Example:
        >>> logger = get_pool_logger(__name__)
        >>> # Info-level event logging
        >>> log_pool_event(
        ...     logger=logger,
        ...     level="info",
        ...     event="pool_initialized",
        ...     context={
        ...         "min_size": 2,
        ...         "max_size": 10,
        ...         "initialization_time_ms": 125.5
        ...     }
        ... )
        >>> # Logs: {"timestamp":"...","level":"INFO","event":"pool_initialized",
        >>> #        "context":{"event":"pool_initialized","min_size":2,...}}

        >>> # Error-level event with exception
        >>> log_pool_event(
        ...     logger=logger,
        ...     level="error",
        ...     event="connection_validation_failed",
        ...     context={
        ...         "connection_id": "conn-123",
        ...         "error_type": "ConnectionError"
        ...     },
        ...     exc_info=True
        ... )
        >>> # Logs: {"timestamp":"...","level":"ERROR",...,"traceback":"..."}
    """
    log_level = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }[level]

    extra: dict[str, Any] = {}
    if context:
        # Add event name to context for easier filtering in log analysis
        enhanced_context = {"event": event, **context}
        extra["context"] = enhanced_context
    else:
        extra["context"] = {"event": event}

    logger.log(log_level, event, extra=extra, exc_info=exc_info)


def log_pool_initialization(
    logger: logging.Logger,
    min_size: int,
    max_size: int,
    duration_ms: float,
    success: bool = True,
    error_message: str | None = None,
) -> None:
    """Log pool initialization event with standardized context.

    Specialized logging function for pool initialization events, used by
    ConnectionPoolManager.initialize() to log startup success or failure
    with comprehensive context.

    **Logged Context**:
    - min_size: Configured minimum pool size
    - max_size: Configured maximum pool size
    - duration_ms: Initialization duration (target: <2000ms)
    - error_message: Error details if initialization failed

    **Performance Target**: <2000ms initialization time logged in context

    Args:
        logger: Logger instance from get_pool_logger(__name__).
        min_size: Minimum pool size from PoolConfig (1-100).
        max_size: Maximum pool size from PoolConfig (1-100, >= min_size).
        duration_ms: Initialization duration in milliseconds from
            time.perf_counter(). Should be <2000ms per performance target.
        success: Whether initialization succeeded. True logs INFO level,
            False logs ERROR level with exc_info=True. Defaults to True.
        error_message: Error message if initialization failed. Included in
            context when success=False. Optional, defaults to None.

    Example:
        >>> logger = get_pool_logger(__name__)
        >>> # Successful initialization
        >>> log_pool_initialization(
        ...     logger=logger,
        ...     min_size=2,
        ...     max_size=10,
        ...     duration_ms=125.5,
        ...     success=True
        ... )
        >>> # Logs: {"level":"INFO","event":"Pool initialized successfully",
        >>> #        "context":{"min_size":2,"max_size":10,"duration_ms":125.5}}

        >>> # Failed initialization
        >>> log_pool_initialization(
        ...     logger=logger,
        ...     min_size=2,
        ...     max_size=10,
        ...     duration_ms=1850.3,
        ...     success=False,
        ...     error_message="Connection refused on localhost:5432"
        ... )
        >>> # Logs: {"level":"ERROR","event":"Pool initialization failed",
        >>> #        "context":{...,"error_message":"Connection refused..."}}
    """
    context: dict[str, Any] = {
        "min_size": min_size,
        "max_size": max_size,
        "duration_ms": duration_ms,
    }

    if success:
        log_pool_event(
            logger=logger,
            level="info",
            event="Pool initialized successfully",
            context=context,
        )
    else:
        if error_message:
            context["error_message"] = error_message
        log_pool_event(
            logger=logger,
            level="error",
            event="Pool initialization failed",
            context=context,
            exc_info=True,
        )


def log_connection_acquisition(
    logger: logging.Logger,
    acquisition_time_ms: float,
    pool_size: int,
    active_connections: int,
    idle_connections: int,
) -> None:
    """Log connection acquisition with current pool state context.

    Specialized logging function for connection acquisition events, used by
    ConnectionPoolManager.acquire() to log successful connection checkout
    with performance metrics and pool capacity snapshot.

    **Logged Context**:
    - acquisition_time_ms: Time to acquire connection (target: <5ms)
    - pool_size: Total connections in pool at acquisition time
    - active_connections: Connections in use after this acquisition
    - idle_connections: Connections remaining available

    **Performance Target**: acquisition_time_ms <5ms typical, <30ms worst-case

    Args:
        logger: Logger instance from get_pool_logger(__name__).
        acquisition_time_ms: Time taken to acquire connection in milliseconds,
            measured via time.perf_counter(). Typical: <5ms, target: <30ms.
        pool_size: Total connections in pool at acquisition time (min_size
            to max_size). Used for capacity tracking.
        active_connections: Connections currently in use after this acquisition.
            Includes this newly acquired connection. Used for utilization metrics.
        idle_connections: Connections remaining available for checkout.
            Should be >0 for healthy pool (0 indicates exhaustion).

    Example:
        >>> logger = get_pool_logger(__name__)
        >>> log_connection_acquisition(
        ...     logger=logger,
        ...     acquisition_time_ms=2.3,
        ...     pool_size=10,
        ...     active_connections=5,
        ...     idle_connections=5
        ... )
        >>> # Logs: {"level":"DEBUG","event":"Connection acquired",
        >>> #        "context":{"acquisition_time_ms":2.3,"pool_size":10,
        >>> #                  "active_connections":5,"idle_connections":5}}
    """
    log_pool_event(
        logger=logger,
        level="debug",
        event="Connection acquired",
        context={
            "acquisition_time_ms": acquisition_time_ms,
            "pool_size": pool_size,
            "active_connections": active_connections,
            "idle_connections": idle_connections,
        },
    )


def log_reconnection_attempt(
    logger: logging.Logger,
    attempt: int,
    delay_seconds: float,
    success: bool = False,
) -> None:
    """Log database reconnection attempt with exponential backoff context.

    Specialized logging function for reconnection events, used by the
    _reconnection_loop() background task to log database recovery attempts
    with exponential backoff timing.

    **Logged Context**:
    - attempt: Reconnection attempt number (1-indexed)
    - delay_seconds: Exponential backoff delay before this attempt
    - success: Whether reconnection succeeded

    **Backoff Schedule**: 1s, 2s, 4s, 8s, 16s (capped at 16s)

    **Log Levels**:
    - success=True: INFO level ("Reconnection succeeded")
    - success=False: WARNING level ("Reconnection attempt")

    Args:
        logger: Logger instance from get_pool_logger(__name__).
        attempt: Reconnection attempt number (1-indexed, 1 = first attempt).
            Used to calculate exponential backoff delay.
        delay_seconds: Delay before this attempt in seconds, calculated via
            exponential_backoff_retry(). Values: 1, 2, 4, 8, 16 (capped).
        success: Whether reconnection succeeded. True logs INFO level,
            False logs WARNING level. Defaults to False.

    Example:
        >>> logger = get_pool_logger(__name__)
        >>> # Failed reconnection attempt (WARNING level)
        >>> log_reconnection_attempt(
        ...     logger=logger,
        ...     attempt=3,
        ...     delay_seconds=4.0,
        ...     success=False
        ... )
        >>> # Logs: {"level":"WARNING","event":"Reconnection attempt",
        >>> #        "context":{"attempt":3,"delay_seconds":4.0}}

        >>> # Successful reconnection (INFO level)
        >>> log_reconnection_attempt(
        ...     logger=logger,
        ...     attempt=4,
        ...     delay_seconds=8.0,
        ...     success=True
        ... )
        >>> # Logs: {"level":"INFO","event":"Reconnection succeeded",
        >>> #        "context":{"attempt":4,"delay_seconds":8.0}}
    """
    level: LogLevel = "info" if success else "warning"
    event = "Reconnection succeeded" if success else "Reconnection attempt"

    log_pool_event(
        logger=logger,
        level=level,
        event=event,
        context={
            "attempt": attempt,
            "delay_seconds": delay_seconds,
        },
    )


def log_pool_statistics(
    logger: logging.Logger,
    total_connections: int,
    idle_connections: int,
    active_connections: int,
    waiting_requests: int,
    total_acquisitions: int,
    total_releases: int,
    avg_acquisition_time_ms: float,
) -> None:
    """Log pool statistics snapshot for observability and monitoring.

    Specialized logging function for periodic pool statistics dumps, used by
    monitoring and observability systems to track pool health trends over time.
    Logs comprehensive metrics including connection counts, lifetime statistics,
    and performance metrics.

    **Logged Context** (all fields):
    - total_connections: Total pool size at snapshot time
    - idle_connections: Available connections (capacity)
    - active_connections: Connections in use (load)
    - waiting_requests: Queued acquire() calls (contention)
    - total_acquisitions: Lifetime acquisition count (usage)
    - total_releases: Lifetime release count (balance)
    - avg_acquisition_time_ms: Rolling average latency (performance)

    **Invariant**: total_connections = idle_connections + active_connections

    **Log Level**: INFO (periodic observability logging)

    Args:
        logger: Logger instance from get_pool_logger(__name__).
        total_connections: Total connections in pool (min_size to max_size).
        idle_connections: Connections available for immediate use (>= 0).
        active_connections: Connections currently executing queries (>= 0).
        waiting_requests: Requests waiting for available connection (>= 0).
            Non-zero indicates pool exhaustion.
        total_acquisitions: Lifetime connection acquisition count (>= 0).
            Monotonically increasing, never resets.
        total_releases: Lifetime connection release count (>= 0).
            Should approximately equal total_acquisitions.
        avg_acquisition_time_ms: Rolling average acquisition time (>= 0.0).
            Target: <5ms typical, <30ms worst-case.

    Example:
        >>> logger = get_pool_logger(__name__)
        >>> log_pool_statistics(
        ...     logger=logger,
        ...     total_connections=10,
        ...     idle_connections=7,
        ...     active_connections=3,
        ...     waiting_requests=0,
        ...     total_acquisitions=150,
        ...     total_releases=147,
        ...     avg_acquisition_time_ms=2.5
        ... )
        >>> # Logs: {"level":"INFO","event":"Pool statistics",
        >>> #        "context":{"total_connections":10,"idle_connections":7,
        >>> #                  "active_connections":3,"waiting_requests":0,
        >>> #                  "total_acquisitions":150,"total_releases":147,
        >>> #                  "avg_acquisition_time_ms":2.5}}
    """
    log_pool_event(
        logger=logger,
        level="info",
        event="Pool statistics",
        context={
            "total_connections": total_connections,
            "idle_connections": idle_connections,
            "active_connections": active_connections,
            "waiting_requests": waiting_requests,
            "total_acquisitions": total_acquisitions,
            "total_releases": total_releases,
            "avg_acquisition_time_ms": avg_acquisition_time_ms,
        },
    )


# ==============================================================================
# Public API
# ==============================================================================

__all__ = [
    "LogLevel",
    "get_pool_logger",
    "get_pool_structured_logger",
    "log_pool_event",
    "log_pool_initialization",
    "log_connection_acquisition",
    "log_reconnection_attempt",
    "log_pool_statistics",
]
