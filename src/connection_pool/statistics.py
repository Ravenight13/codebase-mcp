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
    """Real-time connection pool statistics snapshot.

    Immutable snapshot of pool state including connection counts, performance
    metrics, and health status. Used for MCP health_check responses and
    monitoring dashboards with <1ms read latency.

    **Invariants**:
    - total_connections = idle_connections + active_connections
    - total_acquisitions >= total_releases
    - peak_active_connections >= active_connections
    - All counts >= 0

    **Serialization**:
    - JSON serializable for health check API responses
    - datetime fields use ISO 8601 format

    **Constitutional Compliance**:
    - Principle VIII (Type Safety): Pydantic model with complete Field() constraints
    - Principle V (Production Quality): Comprehensive validation with invariant enforcement
    - Principle III (Protocol Compliance): JSON-serializable for MCP transport

    Attributes:
        total_connections: Current total connections in pool (idle + active).
        idle_connections: Connections available for immediate use (not in active query).
        active_connections: Connections currently executing queries.
        waiting_requests: Number of acquire() calls waiting for available connection.
        total_acquisitions: Lifetime count of successful connection acquisitions.
        total_releases: Lifetime count of connection releases back to pool.
        avg_acquisition_time_ms: Rolling average connection acquisition time (milliseconds).
        peak_active_connections: Maximum active connections since pool initialization.
        peak_wait_time_ms: Maximum time any acquire() call waited (milliseconds).
        pool_created_at: Pool initialization timestamp (UTC).
        last_health_check: Last successful health check timestamp (UTC).
        last_error: Last error message encountered (None if no errors).
        last_error_time: Timestamp of last error (UTC, None if no errors).

    Example:
        >>> from datetime import datetime, timezone
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
        ...     pool_created_at=datetime.now(timezone.utc),
        ...     last_health_check=datetime.now(timezone.utc)
        ... )
        >>> stats.total_connections == stats.idle_connections + stats.active_connections
        True
        >>> stats.model_dump()  # JSON-serializable dict
        {'total_connections': 10, 'idle_connections': 7, ...}
    """

    total_connections: int = Field(
        ge=0,
        description="Current total connections in pool (idle + active). "
        "Ranges from min_size to max_size during normal operation."
    )

    idle_connections: int = Field(
        ge=0,
        description="Connections available for immediate use. "
        "High idle count (>80%) indicates healthy capacity."
    )

    active_connections: int = Field(
        ge=0,
        description="Connections currently executing queries. "
        "Sustained high active count may indicate pool exhaustion."
    )

    waiting_requests: int = Field(
        ge=0,
        description="Requests waiting for available connection. "
        "Non-zero indicates pool exhaustion requiring timeout or scaling."
    )

    total_acquisitions: int = Field(
        ge=0,
        description="Lifetime count of successful connection acquisitions. "
        "Monotonically increasing, never resets."
    )

    total_releases: int = Field(
        ge=0,
        description="Lifetime count of connection releases back to pool. "
        "Should closely match total_acquisitions (difference = active_connections)."
    )

    avg_acquisition_time_ms: float = Field(
        ge=0.0,
        description="Rolling average connection acquisition time in milliseconds. "
        "Calculated from last 1000 acquisitions. Target: <5ms."
    )

    peak_active_connections: int = Field(
        ge=0,
        description="Maximum active connections since pool initialization. "
        "Used for capacity planning and max_size tuning."
    )

    peak_wait_time_ms: float = Field(
        ge=0.0,
        description="Maximum time any acquire() call waited in milliseconds. "
        "Values >100ms indicate pool capacity issues."
    )

    pool_created_at: datetime = Field(
        description="Pool initialization timestamp (UTC). "
        "Used for uptime calculation in health checks."
    )

    last_health_check: datetime = Field(
        description="Last successful health check timestamp (UTC). "
        "Updated on every health_check() call."
    )

    last_error: str | None = Field(
        default=None,
        description="Last error message encountered (None if no errors). "
        "Used for health status degradation within 60-second window."
    )

    last_error_time: datetime | None = Field(
        default=None,
        description="Timestamp of last error (UTC, None if no errors). "
        "Errors within 60 seconds degrade health status to DEGRADED."
    )

    class Config:
        """Pydantic configuration for immutable statistics snapshot.

        Attributes:
            frozen: True - Makes statistics immutable after creation, preventing
                accidental modification. Each get_statistics() call returns a new
                immutable snapshot.
        """
        frozen = True  # Immutable snapshot
