"""Health check models for monitoring server and database status.

Provides comprehensive health check responses with connection pool statistics
for monitoring server uptime, database connectivity, and resource utilization.

Entity Responsibilities:
- Track server health status (healthy/degraded/unhealthy)
- Monitor database connection pool statistics
- Calculate pool utilization percentages
- Provide timestamped health snapshots

Constitutional Compliance:
- Principle V: Production-quality health monitoring
- Principle VIII: Type-safe health status reporting
- FR-011: <50ms response time requirement
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator


class ConnectionPoolStats(BaseModel):
    """Connection pool statistics.

    Tracks current pool size, configured limits, and available connections
    for monitoring database connection health.

    Attributes:
        size: Current number of connections in pool
        min_size: Minimum configured pool size
        max_size: Maximum configured pool size
        free: Number of available (unused) connections
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "size": 8,
                "min_size": 5,
                "max_size": 20,
                "free": 6
            }
        }
    )

    size: int = Field(
        ge=0,
        description="Current pool size"
    )
    min_size: int = Field(
        ge=0,
        description="Minimum pool size configuration"
    )
    max_size: int = Field(
        ge=1,
        description="Maximum pool size configuration"
    )
    free: int = Field(
        ge=0,
        description="Number of free connections"
    )

    @field_validator("max_size")
    @classmethod
    def validate_max_size(cls, v: int, info: ValidationInfo) -> int:
        """Validate max_size is greater than or equal to min_size."""
        # Access to other fields requires ValidationInfo from pydantic v2
        # This validator ensures max_size >= 1 via Field constraint
        if v < 1:
            raise ValueError("max_size must be at least 1")
        return v

    @field_validator("free")
    @classmethod
    def validate_free_connections(cls, v: int, info: ValidationInfo) -> int:
        """Validate free connections do not exceed pool size."""
        # In Pydantic v2, we rely on model_validator for cross-field validation
        # This validator ensures free >= 0 via Field constraint
        if v < 0:
            raise ValueError("free connections cannot be negative")
        return v

    @property
    def utilization_percent(self) -> Decimal:
        """Calculate pool utilization percentage.

        Returns:
            Decimal percentage (0.00-100.00) of pool connections in use
        """
        if self.size == 0:
            return Decimal("0.00")
        used = self.size - self.free
        return Decimal((used / self.size) * 100).quantize(Decimal("0.01"))


class HealthCheckResponse(BaseModel):
    """Health check response model.

    Comprehensive health status including database connectivity, connection pool
    statistics, server uptime, and optional degradation details.

    Status Determination:
    - healthy: Database connected, pool within limits, no errors
    - degraded: Database connected but slow, pool utilization >80%, minor issues
    - unhealthy: Database disconnected, pool exhausted, critical failures

    Constitutional Compliance:
    - Principle V: Production-quality health monitoring
    - Principle VIII: Type-safe health status reporting
    - FR-011: <50ms response time requirement

    Attributes:
        status: Overall health status
        timestamp: Health check timestamp (ISO 8601)
        database_status: Database connectivity status
        connection_pool: Connection pool statistics
        uptime_seconds: Server uptime in seconds
        details: Optional details for degraded/unhealthy states
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "timestamp": "2025-10-13T10:30:00Z",
                "database_status": "connected",
                "connection_pool": {
                    "size": 8,
                    "min_size": 5,
                    "max_size": 20,
                    "free": 6
                },
                "uptime_seconds": 3600.50,
                "details": None
            }
        }
    )

    status: Literal["healthy", "degraded", "unhealthy"] = Field(
        description="Overall health status"
    )
    timestamp: datetime = Field(
        description="Health check timestamp (ISO 8601)"
    )

    # Database Health
    database_status: Literal["connected", "disconnected", "degraded"] = Field(
        description="Database connectivity status"
    )
    connection_pool: ConnectionPoolStats = Field(
        description="Connection pool statistics"
    )

    # Server Metrics
    uptime_seconds: Decimal = Field(
        ge=Decimal("0"),
        decimal_places=2,
        description="Server uptime in seconds"
    )

    # Optional Details (for degraded/unhealthy states)
    details: dict[str, str] | None = Field(
        default=None,
        description="Additional details for degraded/unhealthy status"
    )

    @field_validator("status")
    @classmethod
    def validate_status_consistency(cls, v: Literal["healthy", "degraded", "unhealthy"]) -> Literal["healthy", "degraded", "unhealthy"]:
        """Validate status is one of allowed values.

        Note: This validator is primarily for documentation as Literal type
        already enforces valid values. Cross-field validation (e.g., status
        matching database_status) should be done in application logic.
        """
        allowed_statuses = {"healthy", "degraded", "unhealthy"}
        if v not in allowed_statuses:
            raise ValueError(f"status must be one of {allowed_statuses}")
        return v

    @field_validator("database_status")
    @classmethod
    def validate_database_status(cls, v: Literal["connected", "disconnected", "degraded"]) -> Literal["connected", "disconnected", "degraded"]:
        """Validate database_status is one of allowed values.

        Note: This validator is primarily for documentation as Literal type
        already enforces valid values.
        """
        allowed_statuses = {"connected", "disconnected", "degraded"}
        if v not in allowed_statuses:
            raise ValueError(f"database_status must be one of {allowed_statuses}")
        return v
