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
    """Connection pool health status enumeration for monitoring and alerting.

    Defines three health states with specific determination criteria used by
    calculate_health_status() for pool health classification. Status directly
    impacts monitoring dashboards and alerting thresholds.

    **Status Determination Logic**:

    - **HEALTHY**: total_connections > 0, idle >= 80% capacity, no errors in last 60s,
      peak wait time <= 100ms. Pool is operating optimally with sufficient headroom.

    - **DEGRADED**: total_connections > 0, idle 50-79% capacity, recent errors within
      60s window, or peak wait time > 100ms. Pool is functional but under stress.

    - **UNHEALTHY**: total_connections == 0 OR idle < 50% capacity OR initialization
      failed. Pool is critically compromised or unavailable.

    **Constitutional Compliance**:
    - Principle III (Protocol Compliance): JSON-serializable for MCP health responses
    - Principle VIII (Type Safety): Enum-based with no invalid states possible

    Attributes:
        HEALTHY: Pool operating optimally with sufficient capacity (>=80% idle).
            No action required, continue normal operation.
        DEGRADED: Pool functional but stressed (50-79% idle) or recent errors.
            Warning state - investigate query patterns and consider scaling.
        UNHEALTHY: Pool critically compromised (0 connections or <50% idle).
            Alert state - immediate action required, may impact availability.

    Example:
        >>> status = PoolHealthStatus.HEALTHY
        >>> status.value
        'healthy'
        >>> PoolHealthStatus(status.value)  # Round-trip serialization
        <PoolHealthStatus.HEALTHY: 'healthy'>
    """

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class DatabaseStatus(BaseModel):
    """Database connectivity status with detailed pool metrics.

    Provides comprehensive information about database connection state for
    health check responses and monitoring dashboards. Includes pool statistics,
    performance metrics, error tracking, and leak detection.

    **Constitutional Compliance**:
    - Principle III (Protocol Compliance): JSON-serializable for MCP transport
    - Principle VIII (Type Safety): Pydantic model with complete Field() validation
    - Principle V (Production Quality): Comprehensive metrics for observability

    Attributes:
        status: Connection status indicator. Valid values:
            - "connected": Database is reachable and pool is operational
            - "disconnected": Database is unreachable, pool unavailable
            - "connecting": Initial connection attempt in progress
            - "degraded": Connected but experiencing issues (errors, low capacity)
        pool: Pool statistics dictionary with required keys:
            - total: Total connections in pool (min_size to max_size)
            - idle: Idle connections available for immediate use
            - active: Connections currently executing queries
            - waiting: Requests waiting for available connection
        latency_ms: Average query latency in milliseconds from recent acquisitions.
            None if no queries executed yet. Target: <5ms for local PostgreSQL.
        last_error: Last error message encountered during pool operations.
            None if no errors in current session. Used for health degradation.
        leak_count: Number of potential connection leaks detected in last 60 seconds.
            Non-zero triggers health degradation to DEGRADED state.

    Example:
        >>> db_status = DatabaseStatus(
        ...     status="connected",
        ...     pool={"total": 5, "idle": 3, "active": 2, "waiting": 0},
        ...     latency_ms=2.3,
        ...     last_error=None,
        ...     leak_count=0
        ... )
        >>> db_status.pool["idle"]
        3
        >>> db_status.model_dump_json()  # JSON serialization
        '{"status":"connected","pool":{"total":5,...},...}'
    """

    status: str = Field(
        description="Connection status: connected/disconnected/connecting/degraded. "
        "Reflects current database reachability and pool operational state."
    )

    pool: dict[str, int] = Field(
        description="Pool statistics with keys: total, idle, active, waiting. "
        "All values are non-negative integers representing connection counts."
    )

    latency_ms: float | None = Field(
        default=None,
        description="Average query latency in milliseconds from recent acquisitions. "
        "None if no queries executed yet. Target: <5ms for local PostgreSQL."
    )

    last_error: str | None = Field(
        default=None,
        description="Last error message from pool operations (connection failures, "
        "validation errors, timeouts). None if no errors in current session."
    )

    leak_count: int = Field(
        default=0,
        ge=0,
        description="Number of potential connection leaks detected in last 60 seconds. "
        "Non-zero value triggers health status degradation to DEGRADED."
    )


class HealthStatus(BaseModel):
    """Complete health check response for MCP monitoring and observability.

    Aggregates pool health status, database connectivity, and operational
    metrics into a comprehensive health report suitable for MCP health_check
    tool responses, monitoring systems, and observability dashboards.

    **Performance Target**: <10ms p99 latency for health_check() call.

    **Constitutional Compliance**:
    - Principle III (Protocol Compliance): JSON-serializable for MCP transport
    - Principle IV (Performance): <10ms health check latency maintained
    - Principle VIII (Type Safety): Pydantic model with complete validation
    - Principle V (Production Quality): Comprehensive metrics for monitoring

    Attributes:
        status: Overall health status (HEALTHY/DEGRADED/UNHEALTHY) calculated
            from pool statistics using calculate_health_status() algorithm.
            Determines alerting thresholds in monitoring systems.
        timestamp: Health check execution timestamp (UTC) using datetime.now(timezone.utc).
            ISO 8601 format in JSON serialization for timezone-aware parsing.
        database: Detailed database connectivity and pool state including connection
            counts, latency metrics, error tracking, and leak detection.
        uptime_seconds: Pool uptime in seconds since initialization. Non-negative
            float calculated from (now - pool_created_at). Used for uptime SLO tracking.

    Example:
        >>> from datetime import datetime, timezone
        >>> health = HealthStatus(
        ...     status=PoolHealthStatus.HEALTHY,
        ...     timestamp=datetime.now(timezone.utc),
        ...     database=DatabaseStatus(
        ...         status="connected",
        ...         pool={"total": 5, "idle": 3, "active": 2, "waiting": 0},
        ...         latency_ms=2.3,
        ...         last_error=None,
        ...         leak_count=0
        ...     ),
        ...     uptime_seconds=3600.5
        ... )
        >>> health.status
        <PoolHealthStatus.HEALTHY: 'healthy'>
        >>> health.model_dump_json()  # MCP transport format
        '{"status":"healthy","timestamp":"2025-10-13T14:30:00.000Z",...}'
    """

    status: PoolHealthStatus = Field(
        description="Overall health status (HEALTHY/DEGRADED/UNHEALTHY) calculated "
        "from pool statistics. Determines monitoring alert thresholds."
    )

    timestamp: datetime = Field(
        description="Health check execution timestamp (UTC) in ISO 8601 format. "
        "Used for health check freshness validation and time-series metrics."
    )

    database: DatabaseStatus = Field(
        description="Detailed database connectivity and pool state including "
        "connection counts, latency, errors, and leak detection."
    )

    uptime_seconds: float = Field(
        ge=0.0,
        description="Pool uptime in seconds since initialization. Non-negative "
        "float used for uptime SLO tracking and stability metrics."
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
                    "last_error": None,
                    "leak_count": 0
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
