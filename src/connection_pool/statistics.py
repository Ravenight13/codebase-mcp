"""Connection pool statistics model for monitoring and observability.

This module provides the PoolStatistics model, which represents an immutable
snapshot of connection pool state for health checks and monitoring dashboards.

Constitutional Compliance:
- Principle 8 (Type Safety): Uses Pydantic BaseModel with Field() constraints
- Principle 5 (Production Quality): Comprehensive validation and documentation
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PoolStatistics(BaseModel):
    """Real-time connection pool statistics.

    Immutable snapshot of pool state including connection counts, performance
    metrics, and health status. Used for MCP health_check responses and
    monitoring dashboards.

    **Invariants**:
    - total_connections = idle_connections + active_connections
    - total_acquisitions >= total_releases
    - peak_active_connections >= active_connections
    - All counts >= 0

    **Serialization**:
    - JSON serializable for health check API responses
    - datetime fields use ISO 8601 format

    Example:
        >>> stats = PoolStatistics(
        ...     total_connections=10,
        ...     idle_connections=7,
        ...     active_connections=3,
        ...     waiting_requests=0,
        ...     total_acquisitions=150,
        ...     total_releases=147,
        ...     avg_acquisition_time_ms=2.5,
        ...     peak_active_connections=8,
        ...     peak_wait_time_ms=15.3,
        ...     pool_created_at=datetime.now(),
        ...     last_health_check=datetime.now()
        ... )
        >>> stats.total_connections == stats.idle_connections + stats.active_connections
        True
    """

    total_connections: int = Field(
        ge=0,
        description="Current total connections in pool"
    )

    idle_connections: int = Field(
        ge=0,
        description="Connections available for use"
    )

    active_connections: int = Field(
        ge=0,
        description="Connections currently in use"
    )

    waiting_requests: int = Field(
        ge=0,
        description="Requests waiting for connection"
    )

    total_acquisitions: int = Field(
        ge=0,
        description="Lifetime connection acquisitions"
    )

    total_releases: int = Field(
        ge=0,
        description="Lifetime connection releases"
    )

    avg_acquisition_time_ms: float = Field(
        ge=0.0,
        description="Average time to acquire connection (milliseconds)"
    )

    peak_active_connections: int = Field(
        ge=0,
        description="Max active connections since server start"
    )

    peak_wait_time_ms: float = Field(
        ge=0.0,
        description="Max time request waited for connection (milliseconds)"
    )

    pool_created_at: datetime = Field(
        description="When pool was initialized"
    )

    last_health_check: datetime = Field(
        description="Last successful health check"
    )

    last_error: str | None = Field(
        default=None,
        description="Last error message if any"
    )

    last_error_time: datetime | None = Field(
        default=None,
        description="Timestamp of last error"
    )

    class Config:
        """Pydantic configuration for immutable statistics."""
        frozen = True  # Immutable snapshot
