"""MCP resource handler for Prometheus metrics endpoint.

Provides standardized metrics endpoint returning MetricsResponse with both
JSON and Prometheus text exposition format per contracts/metrics-endpoint.yaml.

Constitutional Compliance:
- Principle III: Protocol Compliance (MCP resource protocol)
- Principle V: Production Quality (comprehensive observability)
- Principle VIII: Type Safety (mypy --strict compliance)
- Principle XI: FastMCP Foundation (FastMCP decorator-based resource)
- FR-012: Prometheus-compatible format (request counts, latency histograms)
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.mcp.server_fastmcp import get_metrics_service, mcp

# ==============================================================================
# Constants
# ==============================================================================

logger = logging.getLogger(__name__)

# ==============================================================================
# Resource Implementation
# ==============================================================================


@mcp.resource("metrics://prometheus")
async def get_prometheus_metrics() -> str:
    """Get Prometheus-compatible metrics.

    MCP resource that exposes server metrics in Prometheus exposition format.
    Returns MetricsResponse conforming to contracts/metrics-endpoint.yaml.

    **Resource URI**: metrics://prometheus

    **Response Format**:
    Returns JSON string with MetricsResponse schema:
    {
        "counters": [
            {
                "name": "codebase_mcp_requests_total",
                "help_text": "Total number of requests",
                "value": 10000
            }
        ],
        "histograms": [
            {
                "name": "codebase_mcp_search_latency_seconds",
                "help_text": "Search query latency",
                "buckets": [
                    {"bucket_le": 0.1, "count": 450},
                    {"bucket_le": 0.5, "count": 9500}
                ],
                "count": 10000,
                "sum": 2345.67
            }
        ]
    }

    **Supported Formats**:
    - JSON: Default format (returned from this resource)
    - Prometheus text: Use MetricsResponse.to_prometheus() for text format

    **Metrics Categories**:
    - Request counters: Total requests, successful requests, failed requests
    - Latency histograms: Search latency, indexing duration, query latency
    - Error counters: Errors by type (timeout, connection_pool_exhausted)
    - Resource utilization: Connection pool usage, memory usage

    **Constitutional Compliance**:
    - FR-012: Prometheus-compatible format
    - Principle V (Production Quality): Comprehensive observability
    - Principle VIII (Type Safety): Complete type annotations with mypy --strict

    Returns:
        JSON string with MetricsResponse (serialized from Pydantic model)

    Example:
        >>> # Resource is accessed via MCP protocol
        >>> # URI: metrics://prometheus
        >>> # Response: {"counters": [...], "histograms": [...]}
    """
    try:
        # Access metrics service via module-level getter function
        # Metrics service is initialized during server lifespan startup
        try:
            metrics_service = get_metrics_service()
        except RuntimeError as e:
            # Metrics service not initialized yet
            error_response = {
                "error": "Metrics service not initialized",
                "message": str(e),
                "counters": [],
                "histograms": [],
            }

            # Log to server file (not MCP client)
            logger.warning(
                "Metrics request called but metrics_service not initialized",
                extra={"context": {"error": error_response}},
            )

            return json.dumps(error_response)

        # Get metrics snapshot (non-blocking, <10ms)
        metrics_response = metrics_service.get_metrics()

        # Log metrics collection (file only, not MCP client)
        logger.debug(
            "Metrics collected successfully",
            extra={
                "context": {
                    "counter_count": len(metrics_response.counters),
                    "histogram_count": len(metrics_response.histograms),
                }
            },
        )

        # Serialize metrics response to JSON string
        # MetricsResponse is a Pydantic model, so model_dump() returns dict
        metrics_dict: dict[str, Any] = metrics_response.model_dump(mode="json")

        return json.dumps(metrics_dict)

    except Exception as e:
        # Comprehensive error handling for unexpected failures
        error_response = {
            "error": f"Metrics collection failed: {type(e).__name__}",
            "message": str(e),
            "counters": [],
            "histograms": [],
        }

        # Log error with full context
        logger.error(
            "Metrics collection failed with exception",
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


__all__ = ["get_prometheus_metrics"]
