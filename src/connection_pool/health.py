"""
Health check models for connection pool monitoring and observability.

This module provides Pydantic models for connection pool health status reporting,
including pool statistics, database connectivity status, and overall health metrics.
Also provides health status calculation function for determining pool health from
statistics.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from .config import PoolConfig
from .statistics import PoolStatistics


class PoolHealthStatus(str, Enum):
    """
    Connection pool health status enumeration.

    Status Determination Logic:
    - HEALTHY: total_connections > 0, idle >= 80% capacity, no errors in last 60s
    - DEGRADED: total_connections > 0, idle 50-79% capacity, some recent errors
    - UNHEALTHY: total_connections == 0 OR idle < 50% capacity OR initialization failed

    Attributes:
        HEALTHY: Pool is operating optimally with sufficient capacity
        DEGRADED: Pool is functional but under stress or experiencing issues
        UNHEALTHY: Pool is unavailable or critically compromised
    """

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class DatabaseStatus(BaseModel):
    """
    Database connectivity status with pool statistics.

    Provides detailed information about the database connection state,
    including pool metrics, query latency, error tracking, and leak detection.

    Attributes:
        status: Connection status indicator (connected/disconnected/connecting)
        pool: Pool statistics dictionary containing:
            - total: Total number of connections in pool
            - idle: Number of idle connections available
            - active: Number of connections currently in use
            - waiting: Number of clients waiting for connections
        latency_ms: Last query latency in milliseconds (None if no recent queries)
        last_error: Last error message encountered (None if no recent errors)
        leak_count: Number of potential connection leaks detected in last 60 seconds

    Example:
        >>> db_status = DatabaseStatus(
        ...     status="connected",
        ...     pool={"total": 5, "idle": 3, "active": 2, "waiting": 0},
        ...     latency_ms=2.3,
        ...     last_error=None,
        ...     leak_count=0
        ... )
    """

    status: str = Field(
        description="Connection status (connected/disconnected/connecting)"
    )

    pool: dict[str, int] = Field(
        description="Pool statistics (total, idle, active, waiting)"
    )

    latency_ms: float | None = Field(
        default=None,
        description="Last query latency in milliseconds"
    )

    last_error: str | None = Field(
        default=None,
        description="Last error message"
    )

    leak_count: int = Field(
        default=0,
        description="Number of potential connection leaks detected in last 60 seconds"
    )


class HealthStatus(BaseModel):
    """
    Complete health check response for connection pool monitoring.

    Aggregates pool health status, database connectivity, and operational
    metrics into a comprehensive health report suitable for monitoring
    systems and observability dashboards.

    Attributes:
        status: Overall health status (HEALTHY/DEGRADED/UNHEALTHY)
        timestamp: Health check execution timestamp (UTC)
        database: Detailed database connectivity and pool state
        uptime_seconds: Server uptime in seconds (non-negative)

    Example:
        >>> health = HealthStatus(
        ...     status=PoolHealthStatus.HEALTHY,
        ...     timestamp=datetime.utcnow(),
        ...     database=DatabaseStatus(
        ...         status="connected",
        ...         pool={"total": 5, "idle": 3, "active": 2, "waiting": 0},
        ...         latency_ms=2.3
        ...     ),
        ...     uptime_seconds=3600.5
        ... )
    """

    status: PoolHealthStatus = Field(
        description="Overall health status"
    )

    timestamp: datetime = Field(
        description="Health check execution time"
    )

    database: DatabaseStatus = Field(
        description="Database connectivity and pool state"
    )

    uptime_seconds: float = Field(
        ge=0.0,
        description="Server uptime in seconds"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "timestamp": "2025-10-13T14:30:00.000Z",
                "database": {
                    "status": "connected",
                    "pool": {
                        "total": 5,
                        "idle": 3,
                        "active": 2,
                        "waiting": 0
                    },
                    "latency_ms": 2.3,
                    "last_error": None
                },
                "uptime_seconds": 3600.5
            }
        }
    }


def calculate_health_status(
    stats: PoolStatistics,
    config: PoolConfig
) -> PoolHealthStatus:
    """Calculate health status from pool statistics.

    This function implements the health status determination algorithm based on
    connection pool capacity, error history, and performance metrics. It provides
    a systematic approach to classifying pool health into three states: HEALTHY,
    DEGRADED, or UNHEALTHY.

    **Health Status Rules**:

    UNHEALTHY (Critical):
    - Total connections == 0 (complete failure, no connections available)
    - Idle capacity < 50% (severe connection exhaustion, <50% available)

    DEGRADED (Warning):
    - Idle capacity 50-79% (moderate connection pressure)
    - Recent errors within last 60 seconds (error recovery window)
    - Peak wait time > 100ms (performance degradation indicator)

    HEALTHY (Normal):
    - Idle capacity ≥ 80% (sufficient connection availability)
    - No recent errors (last 60 seconds clean)
    - Peak wait time ≤ 100ms (normal latency)

    **Algorithm**:
    1. Check for critical conditions (zero connections or <50% capacity) → UNHEALTHY
    2. Check for degraded conditions (50-79% capacity, recent errors, high latency) → DEGRADED
    3. If all checks pass → HEALTHY

    **Performance Characteristics**:
    - Time Complexity: O(1) - constant time calculations
    - Space Complexity: O(1) - no allocations
    - Latency: <1ms typical execution time

    **Constitutional Compliance**:
    - Principle VIII (Type Safety): Full type annotations, mypy --strict compliant
    - Principle V (Production Quality): Comprehensive error detection and classification
    - Principle IV (Performance): <1ms calculation time, no blocking operations

    Args:
        stats: Immutable snapshot of pool statistics containing connection counts,
               error history, and performance metrics. Must satisfy invariant:
               total_connections = idle_connections + active_connections.
        config: Pool configuration for context (currently unused but reserved for
                future threshold customization, e.g., configurable capacity ratios
                or error window durations).

    Returns:
        PoolHealthStatus enum value (HEALTHY, DEGRADED, or UNHEALTHY) representing
        the current pool health classification.

    Raises:
        ZeroDivisionError: Should not occur due to zero-check before division, but
                          if stats.total_connections is somehow corrupted, this
                          would indicate a critical bug in statistics tracking.

    Example:
        >>> from datetime import datetime, timezone, timedelta
        >>> from connection_pool.statistics import PoolStatistics
        >>> from connection_pool.config import PoolConfig
        >>>
        >>> # Healthy pool (80%+ idle capacity, no errors)
        >>> stats = PoolStatistics(
        ...     total_connections=10,
        ...     idle_connections=8,  # 80% idle
        ...     active_connections=2,
        ...     waiting_requests=0,
        ...     total_acquisitions=100,
        ...     total_releases=98,
        ...     avg_acquisition_time_ms=2.5,
        ...     peak_active_connections=5,
        ...     peak_wait_time_ms=15.0,  # <100ms
        ...     pool_created_at=datetime.now(timezone.utc),
        ...     last_health_check=datetime.now(timezone.utc),
        ...     last_error=None,
        ...     last_error_time=None
        ... )
        >>> config = PoolConfig(
        ...     min_size=2,
        ...     max_size=10,
        ...     database_url="postgresql+asyncpg://localhost/test"
        ... )
        >>> calculate_health_status(stats, config)
        <PoolHealthStatus.HEALTHY: 'healthy'>
        >>>
        >>> # Degraded pool (recent error)
        >>> stats_degraded = PoolStatistics(
        ...     total_connections=10,
        ...     idle_connections=8,
        ...     active_connections=2,
        ...     waiting_requests=0,
        ...     total_acquisitions=100,
        ...     total_releases=98,
        ...     avg_acquisition_time_ms=2.5,
        ...     peak_active_connections=5,
        ...     peak_wait_time_ms=15.0,
        ...     pool_created_at=datetime.now(timezone.utc),
        ...     last_health_check=datetime.now(timezone.utc),
        ...     last_error="Connection timeout",
        ...     last_error_time=datetime.now(timezone.utc) - timedelta(seconds=30)  # 30s ago
        ... )
        >>> calculate_health_status(stats_degraded, config)
        <PoolHealthStatus.DEGRADED: 'degraded'>
        >>>
        >>> # Unhealthy pool (<50% capacity)
        >>> stats_unhealthy = PoolStatistics(
        ...     total_connections=10,
        ...     idle_connections=4,  # 40% idle (<50%)
        ...     active_connections=6,
        ...     waiting_requests=0,
        ...     total_acquisitions=100,
        ...     total_releases=94,
        ...     avg_acquisition_time_ms=2.5,
        ...     peak_active_connections=8,
        ...     peak_wait_time_ms=15.0,
        ...     pool_created_at=datetime.now(timezone.utc),
        ...     last_health_check=datetime.now(timezone.utc)
        ... )
        >>> calculate_health_status(stats_unhealthy, config)
        <PoolHealthStatus.UNHEALTHY: 'unhealthy'>
        >>>
        >>> # Critical failure (zero connections)
        >>> stats_critical = PoolStatistics(
        ...     total_connections=0,
        ...     idle_connections=0,
        ...     active_connections=0,
        ...     waiting_requests=5,  # Requests queued but no connections
        ...     total_acquisitions=0,
        ...     total_releases=0,
        ...     avg_acquisition_time_ms=0.0,
        ...     peak_active_connections=0,
        ...     peak_wait_time_ms=0.0,
        ...     pool_created_at=datetime.now(timezone.utc),
        ...     last_health_check=datetime.now(timezone.utc)
        ... )
        >>> calculate_health_status(stats_critical, config)
        <PoolHealthStatus.UNHEALTHY: 'unhealthy'>

    **Implementation Notes**:
    - The function does not modify stats or config (pure function)
    - Capacity ratio calculation is safe due to zero-check guard
    - Error time comparison uses UTC timestamps for consistency
    - Peak wait time threshold (100ms) is a performance heuristic based on
      typical database query latencies (<50ms p95)
    - Future versions may expose thresholds in PoolConfig for customization

    **Related Functions**:
    - PoolStatistics: Immutable snapshot model for pool state
    - PoolConfig: Configuration model for pool tuning
    - HealthStatus: Complete health check response model

    **Version History**:
    - v2.0.0: Initial implementation with fixed thresholds
    - Future: Configurable thresholds via PoolConfig extension
    """
    # Critical condition: No connections available (complete pool failure)
    if stats.total_connections == 0:
        return PoolHealthStatus.UNHEALTHY

    # Calculate capacity ratio (safe division due to zero-check above)
    capacity_ratio: float = stats.idle_connections / stats.total_connections

    # Critical condition: Severe connection exhaustion (<50% capacity)
    if capacity_ratio < 0.5:
        return PoolHealthStatus.UNHEALTHY

    # Degraded condition: Moderate connection pressure (50-79% capacity)
    if capacity_ratio < 0.8:
        return PoolHealthStatus.DEGRADED

    # Degraded condition: Recent errors within last 60 seconds
    if stats.last_error_time is not None:
        # Calculate time since last error (use UTC for consistency)
        time_since_error: float = (
            datetime.now(timezone.utc) - stats.last_error_time
        ).total_seconds()

        # Error recovery window: 60 seconds
        if time_since_error < 60:
            return PoolHealthStatus.DEGRADED

    # Degraded condition: High wait times indicating performance degradation
    # Threshold: 100ms peak wait time (typical DB query p95 is <50ms)
    if stats.peak_wait_time_ms > 100:
        return PoolHealthStatus.DEGRADED

    # All checks passed: Pool is healthy
    return PoolHealthStatus.HEALTHY
