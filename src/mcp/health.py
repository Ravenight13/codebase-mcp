"""MCP resource handler for connection pool health monitoring.

Provides health check MCP resource exposing connection pool status and metrics
for observability and debugging.

Constitutional Compliance:
- Principle III: Protocol Compliance (MCP resource protocol)
- Principle IV: Performance (<10ms response time target)
- Principle V: Production Quality (comprehensive error handling)
- Principle VIII: Type Safety (mypy --strict compliance)
- Principle XI: FastMCP Foundation (FastMCP decorator-based resource)
"""

from __future__ import annotations

from typing import Any

from src.mcp.mcp_logging import get_logger
from src.mcp.server_fastmcp import get_pool_manager, mcp

# ==============================================================================
# Constants
# ==============================================================================

logger = get_logger(__name__)

# ==============================================================================
# Resource Implementation
# ==============================================================================


@mcp.resource("health://connection-pool")
async def get_pool_health() -> str:
    """Get connection pool health status.

    MCP resource that exposes connection pool health metrics including pool
    statistics, database connectivity, and operational status. Response time
    must be <10ms to meet performance requirements.

    **Resource URI**: health://connection-pool

    **Response Format**:
    Returns JSON string with complete health status:
    {
        "status": "healthy" | "degraded" | "unhealthy",
        "timestamp": "2025-10-13T14:30:00.000Z",
        "database": {
            "status": "connected" | "disconnected" | "connecting",
            "pool": {
                "total": 10,
                "idle": 7,
                "active": 3,
                "waiting": 0
            },
            "latency_ms": 2.3,
            "last_error": null,
            "leak_count": 0
        },
        "uptime_seconds": 3600.5
    }

    **Health Status Values**:
    - HEALTHY: Pool is operating optimally (>=80% idle capacity, no recent errors)
    - DEGRADED: Pool is functional but under stress (50-79% capacity, recent errors)
    - UNHEALTHY: Pool is critically compromised (0 connections or <50% capacity)

    **Error Handling**:
    - If pool_manager not initialized: Returns error status with actionable message
    - If health_check() fails: Logs error and returns error status
    - If pool not available: Returns status indicating pool initialization pending

    **Performance Target**: <10ms p99 (no blocking operations)

    **Constitutional Compliance**:
    - Principle IV (Performance): <10ms response time, no await on I/O
    - Principle VIII (Type Safety): Complete type annotations with mypy --strict
    - Principle V (Production Quality): Comprehensive error handling with context

    Returns:
        JSON string with health status (serialized dict from HealthStatus.model_dump())

    Example:
        >>> # Resource is accessed via MCP protocol
        >>> # URI: health://connection-pool
        >>> # Response: {"status": "healthy", "timestamp": "...", ...}
    """
    try:
        # Access pool_manager via module-level getter function
        # Pool manager is initialized during server lifespan startup
        try:
            pool_manager = get_pool_manager()
        except RuntimeError as e:
            # Pool manager not initialized yet
            error_response = {
                "status": "unhealthy",
                "error": "Connection pool not initialized",
                "message": str(e),
            }

            # Log to server file (not MCP client)
            logger.warning(
                "Health check called but pool_manager not initialized",
                extra={"context": {"error": error_response}},
            )

            # Import json for serialization
            import json

            return json.dumps(error_response)

        # Call health_check() on pool manager
        # This should be fast (<10ms) with no blocking operations
        health_status = await pool_manager.health_check()

        # Log health check execution (file only, not MCP client)
        logger.debug(
            "Health check executed successfully",
            extra={
                "context": {
                    "status": health_status.status.value,
                    "total_connections": health_status.database.pool["total"],
                    "idle_connections": health_status.database.pool["idle"],
                    "active_connections": health_status.database.pool["active"],
                    "uptime_seconds": health_status.uptime_seconds,
                }
            },
        )

        # Serialize health status to JSON string
        # HealthStatus is a Pydantic model, so model_dump() returns dict
        health_dict: dict[str, Any] = health_status.model_dump(mode="json")

        # Import json for serialization
        import json

        return json.dumps(health_dict)

    except Exception as e:
        # Comprehensive error handling for unexpected failures
        error_response = {
            "status": "unhealthy",
            "error": f"Health check failed: {type(e).__name__}",
            "message": str(e),
        }

        # Log error with full context
        logger.error(
            "Health check failed with exception",
            extra={
                "context": {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }
            },
            exc_info=True,
        )

        # Return error status as JSON
        import json

        return json.dumps(error_response)


__all__ = ["get_pool_health"]
