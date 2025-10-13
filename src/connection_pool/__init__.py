"""
Connection Pool Management Module.

This module provides production-grade database connection pool management with:
- Automatic reconnection with exponential backoff
- Real-time pool statistics and health monitoring
- Graceful connection lifecycle management
- Structured JSON logging to /tmp/codebase-mcp.log

Constitutional Compliance:
- Principle III: Protocol Compliance - No stdout/stderr pollution
- Principle V: Production Quality - Comprehensive error handling and logging
- Principle VIII: Type Safety - Full mypy --strict compliance
- Principle XI: FastMCP Foundation - Designed for MCP server integration

Usage:
    from src.connection_pool import (
        ConnectionPoolManager,
        PoolConfig,
        PoolState,
        PoolHealthStatus,
        get_pool_logger,
    )

    # Configure pool
    config = PoolConfig(
        min_size=2,
        max_size=10,
        database_url="postgresql+asyncpg://localhost/db"
    )

    # Initialize pool with logging
    logger = get_pool_logger(__name__)
    async with ConnectionPoolManager(config) as pool:
        # Acquire connection
        async with pool.acquire() as conn:
            result = await conn.fetch("SELECT 1")

        # Check health
        health = await pool.health_check()
        logger.info("Pool health", extra={"context": health.dict()})
"""

from __future__ import annotations

# Export logging utilities for convenience
from src.connection_pool.pool_logging import (
    get_pool_logger,
    get_pool_structured_logger,
    log_pool_event,
    log_pool_initialization,
    log_connection_acquisition,
    log_reconnection_attempt,
    log_pool_statistics,
    LogLevel,
)

# Export models (when implemented)
# from src.connection_pool.config import PoolConfig
# from src.connection_pool.manager import ConnectionPoolManager, PoolState
# from src.connection_pool.health import PoolHealthStatus, HealthStatus
# from src.connection_pool.statistics import PoolStatistics
# from src.connection_pool.exceptions import (
#     ConnectionPoolError,
#     PoolConfigurationError,
#     PoolInitializationError,
#     PoolTimeoutError,
#     ConnectionValidationError,
#     PoolClosedError,
# )

__all__ = [
    # Logging utilities
    "get_pool_logger",
    "get_pool_structured_logger",
    "log_pool_event",
    "log_pool_initialization",
    "log_connection_acquisition",
    "log_reconnection_attempt",
    "log_pool_statistics",
    "LogLevel",
    # Models (uncomment when implemented)
    # "ConnectionPoolManager",
    # "PoolConfig",
    # "PoolState",
    # "PoolHealthStatus",
    # "HealthStatus",
    # "PoolStatistics",
    # "ConnectionPoolError",
    # "PoolConfigurationError",
    # "PoolInitializationError",
    # "PoolTimeoutError",
    # "ConnectionValidationError",
    # "PoolClosedError",
]
