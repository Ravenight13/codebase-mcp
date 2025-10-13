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
    """
    Get a configured logger for connection pool modules.

    This logger uses the existing mcp_logging infrastructure, ensuring:
    - JSON structured logging
    - File-only output to /tmp/codebase-mcp.log
    - Automatic log rotation (100MB per file, 5 backup files)
    - No stdout/stderr pollution (MCP protocol compliance)

    Args:
        name: Logger name (typically __name__ from calling module)

    Returns:
        Configured logger instance with JSON structured output

    Example:
        >>> from src.connection_pool.logging import get_pool_logger
        >>> logger = get_pool_logger(__name__)
        >>> logger.info(
        ...     "Pool initialized",
        ...     extra={"context": {"min_size": 2, "max_size": 10}}
        ... )
    """
    return get_logger(name)


def get_pool_structured_logger(name: str) -> StructuredLogger:
    """
    Get a structured logger with convenience methods for connection pool modules.

    Provides type-safe logging methods with context support:
    - debug(message, context, exc_info)
    - info(message, context, exc_info)
    - warning(message, context, exc_info)
    - error(message, context, exc_info)
    - critical(message, context, exc_info)

    Args:
        name: Logger name (typically __name__ from calling module)

    Returns:
        StructuredLogger instance with convenience methods

    Example:
        >>> from src.connection_pool.logging import get_pool_structured_logger
        >>> logger = get_pool_structured_logger(__name__)
        >>> logger.info(
        ...     "Connection acquired",
        ...     context={
        ...         "pool_size": 10,
        ...         "active_connections": 5,
        ...         "acquisition_time_ms": 2.3
        ...     }
        ... )
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
    """
    Log a connection pool event with structured context.

    Convenience function for logging common pool events with consistent
    formatting and context structure.

    Args:
        logger: Logger instance (from get_pool_logger)
        level: Log level (debug/info/warning/error/critical)
        event: Event name/description (e.g., "pool_initialized", "connection_acquired")
        context: Structured context data (pool metrics, connection details, etc.)
        exc_info: Whether to include exception information

    Example:
        >>> logger = get_pool_logger(__name__)
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
    """
    Log pool initialization event with standardized context.

    Args:
        logger: Logger instance
        min_size: Minimum pool size
        max_size: Maximum pool size
        duration_ms: Initialization duration in milliseconds
        success: Whether initialization succeeded
        error_message: Error message if initialization failed

    Example:
        >>> logger = get_pool_logger(__name__)
        >>> log_pool_initialization(
        ...     logger=logger,
        ...     min_size=2,
        ...     max_size=10,
        ...     duration_ms=125.5,
        ...     success=True
        ... )
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
    """
    Log connection acquisition with pool state context.

    Args:
        logger: Logger instance
        acquisition_time_ms: Time taken to acquire connection
        pool_size: Total pool size
        active_connections: Active connections count
        idle_connections: Idle connections count

    Example:
        >>> logger = get_pool_logger(__name__)
        >>> log_connection_acquisition(
        ...     logger=logger,
        ...     acquisition_time_ms=2.3,
        ...     pool_size=10,
        ...     active_connections=5,
        ...     idle_connections=5
        ... )
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
    """
    Log database reconnection attempt with exponential backoff context.

    Args:
        logger: Logger instance
        attempt: Reconnection attempt number
        delay_seconds: Delay before this attempt (backoff duration)
        success: Whether reconnection succeeded

    Example:
        >>> logger = get_pool_logger(__name__)
        >>> log_reconnection_attempt(
        ...     logger=logger,
        ...     attempt=3,
        ...     delay_seconds=4.0,
        ...     success=False
        ... )
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
    """
    Log pool statistics snapshot for observability.

    Args:
        logger: Logger instance
        total_connections: Total connections in pool
        idle_connections: Idle connections available
        active_connections: Active connections in use
        waiting_requests: Requests waiting for connections
        total_acquisitions: Lifetime connection acquisitions
        total_releases: Lifetime connection releases
        avg_acquisition_time_ms: Average acquisition time

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
