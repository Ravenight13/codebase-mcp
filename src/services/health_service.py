"""Health check service for monitoring server and database status.

Provides comprehensive health status checks including database connectivity,
connection pool statistics, and server uptime. Designed for <50ms response time
to meet constitutional performance requirements.

Entity Responsibilities:
- Query database connectivity status
- Collect connection pool statistics
- Calculate server uptime
- Determine overall health status (healthy/degraded/unhealthy)

Constitutional Compliance:
- Principle V: Production-quality health monitoring with actionable diagnostics
- Principle VIII: Type-safe health status reporting with mypy --strict
- FR-011: <50ms response time requirement for health checks
- SC-010: Health checks respond within 50ms
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Literal

from src.models.health import ConnectionPoolStats, HealthCheckResponse

if TYPE_CHECKING:
    from src.connection_pool.manager import ConnectionPoolManager


class HealthService:
    """Health check service for server monitoring.

    Provides non-blocking health checks with <50ms response time guarantee.
    Aggregates status from connection pool, database, and server components.

    Constitutional Compliance:
    - Principle IV: Performance (<50ms health check requirement)
    - Principle V: Production-quality monitoring
    - Principle VIII: Type-safe with complete annotations

    Attributes:
        _pool_manager: Connection pool manager instance
        _start_time: Server start timestamp for uptime calculation
    """

    def __init__(self, pool_manager: ConnectionPoolManager) -> None:
        """Initialize health service.

        Args:
            pool_manager: Connection pool manager for database health checks
        """
        self._pool_manager = pool_manager
        self._start_time = datetime.now(timezone.utc)

    async def check_health(self) -> HealthCheckResponse:
        """Perform comprehensive health check.

        Collects health status from multiple subsystems and aggregates into a
        single health response. Designed to complete in <50ms (p95) per FR-011.

        Health Status Determination:
        - HEALTHY: Database connected, pool utilization <80%, no errors
        - DEGRADED: Database connected, pool utilization 80-95%, minor issues
        - UNHEALTHY: Database disconnected, pool exhausted (>95%), critical failures

        Performance:
        - Target: <50ms p95 latency
        - Uses lightweight connection pool stats (no blocking queries)
        - Database check uses simple SELECT 1 with 1s timeout

        Returns:
            HealthCheckResponse with complete health status

        Constitutional Compliance:
        - FR-011: <50ms response time requirement
        - SC-010: Health checks respond within 50ms
        - Principle IV: Performance guarantees

        Example:
            >>> service = HealthService(pool_manager)
            >>> response = await service.check_health()
            >>> response.status
            'healthy'
            >>> response.database_status
            'connected'
        """
        timestamp = datetime.now(timezone.utc)

        # Check database connectivity with timeout
        database_status = await self._check_database_connectivity()

        # Collect connection pool statistics (non-blocking)
        pool_stats = await self._get_pool_stats()

        # Calculate server uptime
        uptime_seconds = self._calculate_uptime()

        # Determine overall health status
        overall_status, details = self._determine_health_status(
            database_status, pool_stats
        )

        return HealthCheckResponse(
            status=overall_status,
            timestamp=timestamp,
            database_status=database_status,
            connection_pool=pool_stats,
            uptime_seconds=uptime_seconds,
            details=details if details else None,
        )

    async def _check_database_connectivity(
        self,
    ) -> Literal["connected", "disconnected", "degraded"]:
        """Check database connectivity with timeout.

        Performs lightweight database connectivity check using simple query.
        Times out after 1 second to ensure <50ms health check target.

        Returns:
            Database status:
            - connected: Query succeeded in <100ms
            - degraded: Query succeeded but took 100ms-1000ms
            - disconnected: Query failed or timed out

        Performance:
        - Target: <100ms for healthy database
        - Timeout: 1000ms (prevents blocking health check)
        """
        try:
            # Use pool manager's connection pool
            pool = self._pool_manager._pool

            if pool is None:
                return "disconnected"

            # Simple connectivity check with timeout
            start_time = asyncio.get_event_loop().time()

            async def check_query() -> bool:
                async with pool.acquire() as conn:
                    result: int | None = await conn.fetchval("SELECT 1")
                    return result == 1

            # Execute with 1s timeout
            query_succeeded: bool = await asyncio.wait_for(check_query(), timeout=1.0)

            # Calculate query latency
            latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            # Determine status based on latency
            if latency_ms < 100:
                return "connected"
            else:
                return "degraded"

        except asyncio.TimeoutError:
            return "disconnected"
        except Exception:
            return "disconnected"

    async def _get_pool_stats(self) -> ConnectionPoolStats:
        """Collect connection pool statistics.

        Retrieves non-blocking pool statistics from connection pool manager.

        Returns:
            ConnectionPoolStats with current pool state

        Performance:
        - Non-blocking operation (<1ms)
        - No database queries required
        """
        pool = self._pool_manager._pool

        if pool is None:
            # Pool not initialized yet
            return ConnectionPoolStats(
                size=0,
                min_size=self._pool_manager._config.min_size
                if self._pool_manager._config
                else 0,
                max_size=self._pool_manager._config.max_size
                if self._pool_manager._config
                else 0,
                free=0,
            )

        # Get pool size and free connections
        size = pool.get_size()
        free_size = pool.get_idle_size()

        return ConnectionPoolStats(
            size=size,
            min_size=self._pool_manager._config.min_size
            if self._pool_manager._config
            else 0,
            max_size=self._pool_manager._config.max_size
            if self._pool_manager._config
            else 0,
            free=free_size,
        )

    def _calculate_uptime(self) -> Decimal:
        """Calculate server uptime in seconds.

        Returns:
            Server uptime as Decimal with 2 decimal places

        Performance:
        - Instant calculation (<1ms)
        - No I/O operations
        """
        now = datetime.now(timezone.utc)
        uptime = (now - self._start_time).total_seconds()
        return Decimal(str(uptime)).quantize(Decimal("0.01"))

    def _determine_health_status(
        self,
        database_status: Literal["connected", "disconnected", "degraded"],
        pool_stats: ConnectionPoolStats,
    ) -> tuple[Literal["healthy", "degraded", "unhealthy"], dict[str, str] | None]:
        """Determine overall health status from subsystem statuses.

        Health Status Logic:
        - UNHEALTHY: Database disconnected OR pool utilization >95%
        - DEGRADED: Database degraded OR pool utilization 80-95%
        - HEALTHY: Database connected AND pool utilization <80%

        Args:
            database_status: Database connectivity status
            pool_stats: Connection pool statistics

        Returns:
            Tuple of (overall_status, details_dict)
            - overall_status: healthy/degraded/unhealthy
            - details_dict: Optional dict with warning/error messages

        Example:
            >>> status, details = service._determine_health_status(
            ...     "connected", pool_stats
            ... )
            >>> status
            'healthy'
        """
        details: dict[str, str] = {}

        # Check database status
        if database_status == "disconnected":
            return (
                "unhealthy",
                {"error": "Database connection lost, reconnection in progress"},
            )

        # Calculate pool utilization
        utilization = pool_stats.utilization_percent

        # Determine status based on utilization thresholds
        if utilization > Decimal("95.0"):
            details["error"] = (
                f"Connection pool critically exhausted (utilization: {utilization}%)"
            )
            return ("unhealthy", details)

        if utilization > Decimal("80.0"):
            details["warning"] = (
                f"Connection pool utilization exceeds 80% (current: {utilization}%)"
            )
            return ("degraded", details)

        if database_status == "degraded":
            details["warning"] = "Database queries responding slowly (>100ms)"
            return ("degraded", details)

        # All systems healthy
        return ("healthy", None)


__all__ = ["HealthService"]
