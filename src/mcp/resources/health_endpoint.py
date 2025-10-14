"""MCP resource handler for health check endpoint.

Provides standardized health check endpoint returning HealthCheckResponse
per contracts/health-endpoint.yaml specification.

Constitutional Compliance:
- Principle III: Protocol Compliance (MCP resource protocol)
- Principle IV: Performance (<50ms response time requirement per FR-011)
- Principle V: Production Quality (comprehensive error handling)
- Principle VIII: Type Safety (mypy --strict compliance)
- Principle XI: FastMCP Foundation (FastMCP decorator-based resource)
- SC-010: Health checks respond within 50ms
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.mcp.server_fastmcp import get_health_service, mcp

# ==============================================================================
# Constants
# ==============================================================================

logger = logging.getLogger(__name__)

# ==============================================================================
# Resource Implementation
# ==============================================================================


@mcp.resource("health://status")
async def get_health_status() -> str:
    """Get comprehensive health status.

    MCP resource that exposes server health status including database connectivity,
    connection pool statistics, and uptime. Returns HealthCheckResponse conforming
    to contracts/health-endpoint.yaml.

    **Resource URI**: health://status

    **Response Format**:
    Returns JSON string with HealthCheckResponse schema:
    {
        "status": "healthy" | "degraded" | "unhealthy",
        "timestamp": "2025-10-13T10:30:00Z",
        "database_status": "connected" | "disconnected" | "degraded",
        "connection_pool": {
            "size": 8,
            "min_size": 5,
            "max_size": 20,
            "free": 6
        },
        "uptime_seconds": 3600.50,
        "details": {"warning": "..."}  # Optional
    }

    **Health Status Values**:
    - HEALTHY: Database connected, pool utilization <80%, no errors
    - DEGRADED: Database connected, pool utilization 80-95%, minor issues
    - UNHEALTHY: Database disconnected, pool exhausted (>95%), critical failures

    **Performance Target**: <50ms p95 (FR-011, SC-010)

    **Constitutional Compliance**:
    - FR-011: <50ms response time requirement
    - SC-010: Health checks respond within 50ms
    - Principle IV (Performance): <50ms response time guarantee
    - Principle VIII (Type Safety): Complete type annotations with mypy --strict
    - Principle V (Production Quality): Comprehensive error handling

    Returns:
        JSON string with HealthCheckResponse (serialized from Pydantic model)

    Example:
        >>> # Resource is accessed via MCP protocol
        >>> # URI: health://status
        >>> # Response: {"status": "healthy", "timestamp": "...", ...}
    """
    try:
        # Access health service via module-level getter function
        # Health service is initialized during server lifespan startup
        try:
            health_service = get_health_service()
        except RuntimeError as e:
            # Health service not initialized yet
            error_response = {
                "status": "unhealthy",
                "error": "Health service not initialized",
                "message": str(e),
            }

            # Log to server file (not MCP client)
            logger.warning(
                "Health check called but health_service not initialized",
                extra={"context": {"error": error_response}},
            )

            return json.dumps(error_response)

        # Perform health check (should complete in <50ms)
        health_response = await health_service.check_health()

        # Log health check execution (file only, not MCP client)
        logger.debug(
            "Health check executed successfully",
            extra={
                "context": {
                    "status": health_response.status,
                    "database_status": health_response.database_status,
                    "pool_size": health_response.connection_pool.size,
                    "pool_free": health_response.connection_pool.free,
                    "uptime_seconds": str(health_response.uptime_seconds),
                }
            },
        )

        # Serialize health response to JSON string
        # HealthCheckResponse is a Pydantic model, so model_dump() returns dict
        health_dict: dict[str, Any] = health_response.model_dump(mode="json")

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
        return json.dumps(error_response)


__all__ = ["get_health_status"]
