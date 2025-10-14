"""Load testing models for performance validation.

This module defines Pydantic models for capturing load test results,
error breakdowns, and resource utilization statistics.

Constitutional Compliance:
- Principle IV: Validates performance under concurrent load
- Principle V: Tracks error rates and resource utilization
- Principle VIII: Type safety (all models fully typed with mypy --strict)
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator


class ErrorBreakdown(BaseModel):
    """Error breakdown by type during load test.

    Tracks the count and percentage of specific error types
    that occurred during load testing execution.

    Validation:
        - count: Must be non-negative
        - percentage: Must be between 0 and 100 with 2 decimal places
    """

    error_type: str = Field(
        description="Error type (e.g., 'timeout', 'connection_refused', '500_internal')"
    )
    count: int = Field(
        ge=0,
        description="Number of errors of this type"
    )
    percentage: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("100"),
        description="Percentage of total requests",
        decimal_places=2
    )

    model_config = {"frozen": False}

    @field_validator("percentage")
    @classmethod
    def validate_percentage_precision(cls, v: Decimal) -> Decimal:
        """Ensure percentage has exactly 2 decimal places."""
        return v.quantize(Decimal("0.01"))


class ResourceUsageStats(BaseModel):
    """Resource utilization statistics during load test.

    Captures CPU, memory, and connection pool utilization metrics
    during load test execution.

    Validation:
        - All CPU percentages: 0-100%
        - Memory values: Non-negative MB values
        - Connection pool utilization: 0-100%
        - Max values must be >= average values
    """

    cpu_percent_avg: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("100"),
        description="Average CPU utilization percentage",
        decimal_places=2
    )
    cpu_percent_max: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("100"),
        description="Maximum CPU utilization percentage",
        decimal_places=2
    )
    memory_mb_avg: Decimal = Field(
        ge=Decimal("0"),
        description="Average memory usage in MB",
        decimal_places=2
    )
    memory_mb_max: Decimal = Field(
        ge=Decimal("0"),
        description="Maximum memory usage in MB",
        decimal_places=2
    )
    connection_pool_utilization_avg: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("100"),
        description="Average connection pool utilization percentage",
        decimal_places=2
    )
    connection_pool_utilization_max: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("100"),
        description="Maximum connection pool utilization percentage",
        decimal_places=2
    )

    model_config = {"frozen": False}

    @field_validator(
        "cpu_percent_avg",
        "cpu_percent_max",
        "memory_mb_avg",
        "memory_mb_max",
        "connection_pool_utilization_avg",
        "connection_pool_utilization_max"
    )
    @classmethod
    def validate_decimal_precision(cls, v: Decimal) -> Decimal:
        """Ensure all metrics have exactly 2 decimal places."""
        return v.quantize(Decimal("0.01"))

    @model_validator(mode="after")
    def validate_max_greater_than_avg(self) -> ResourceUsageStats:
        """Validate that maximum values are >= average values."""
        if self.cpu_percent_max < self.cpu_percent_avg:
            raise ValueError(
                f"cpu_percent_max ({self.cpu_percent_max}) must be >= "
                f"cpu_percent_avg ({self.cpu_percent_avg})"
            )

        if self.memory_mb_max < self.memory_mb_avg:
            raise ValueError(
                f"memory_mb_max ({self.memory_mb_max}) must be >= "
                f"memory_mb_avg ({self.memory_mb_avg})"
            )

        if self.connection_pool_utilization_max < self.connection_pool_utilization_avg:
            raise ValueError(
                f"connection_pool_utilization_max ({self.connection_pool_utilization_max}) "
                f"must be >= connection_pool_utilization_avg "
                f"({self.connection_pool_utilization_avg})"
            )

        return self


class LoadTestResult(BaseModel):
    """
    Load/stress test execution result.

    Captures comprehensive metrics from load testing including request counts,
    latency distributions, error breakdowns, and resource utilization.

    Constitutional Compliance:
    - Principle IV: Validates performance under concurrent load
    - Principle V: Tracks error rates and resource utilization
    - Principle VIII: Type safety (mypy --strict compliant)

    Validation Rules:
    - successful_requests + failed_requests = total_requests
    - Latency ordering: avg <= p95 <= max
    - Error breakdown counts sum to failed_requests
    """

    # Identification
    test_id: str = Field(
        description="Unique test identifier (UUID)"
    )
    server_id: Literal["codebase-mcp", "workflow-mcp"] = Field(
        description="Server under test"
    )
    test_scenario: str = Field(
        description="Load test scenario name (e.g., 'Sustained 50 concurrent clients')"
    )

    # Test Configuration
    concurrent_clients: int = Field(
        ge=1,
        description="Number of concurrent clients"
    )
    test_duration_seconds: int = Field(
        ge=1,
        description="Total test duration in seconds"
    )
    timestamp: datetime = Field(
        description="Test execution timestamp"
    )

    # Request Metrics
    total_requests: int = Field(
        ge=0,
        description="Total requests sent"
    )
    successful_requests: int = Field(
        ge=0,
        description="Number of successful requests (2xx status)"
    )
    failed_requests: int = Field(
        ge=0,
        description="Number of failed requests (4xx/5xx/timeout)"
    )

    # Latency Metrics (in milliseconds)
    latency_avg_ms: Decimal = Field(
        ge=Decimal("0"),
        description="Average latency",
        decimal_places=2
    )
    latency_p95_ms: Decimal = Field(
        ge=Decimal("0"),
        description="95th percentile latency",
        decimal_places=2
    )
    latency_max_ms: Decimal = Field(
        ge=Decimal("0"),
        description="Maximum latency",
        decimal_places=2
    )

    # Error Analysis
    error_breakdown: list[ErrorBreakdown] = Field(
        default_factory=list,
        description="Error breakdown by type"
    )

    # Resource Usage
    resource_usage: ResourceUsageStats = Field(
        description="Resource utilization statistics"
    )

    model_config = {
        "frozen": False,
        "json_schema_extra": {
            "example": {
                "test_id": "load-test-001",
                "server_id": "codebase-mcp",
                "test_scenario": "Sustained 50 concurrent clients",
                "concurrent_clients": 50,
                "test_duration_seconds": 600,
                "timestamp": "2025-10-13T10:30:00Z",
                "total_requests": 30000,
                "successful_requests": 29850,
                "failed_requests": 150,
                "latency_avg_ms": "342.56",
                "latency_p95_ms": "1245.78",
                "latency_max_ms": "2987.23",
                "error_breakdown": [
                    {
                        "error_type": "timeout",
                        "count": 120,
                        "percentage": "0.40"
                    },
                    {
                        "error_type": "connection_pool_exhausted",
                        "count": 30,
                        "percentage": "0.10"
                    }
                ],
                "resource_usage": {
                    "cpu_percent_avg": "65.23",
                    "cpu_percent_max": "89.45",
                    "memory_mb_avg": "512.34",
                    "memory_mb_max": "678.90",
                    "connection_pool_utilization_avg": "75.50",
                    "connection_pool_utilization_max": "95.00"
                }
            }
        }
    }

    # Derived Metrics
    @computed_field  # type: ignore[prop-decorator]
    @property
    def success_rate_percent(self) -> Decimal:
        """Calculate success rate percentage.

        Returns:
            Success rate as percentage with 2 decimal places.
            Returns 0.00 if total_requests is 0.
        """
        if self.total_requests == 0:
            return Decimal("0.00")
        return Decimal(
            (self.successful_requests / self.total_requests) * 100
        ).quantize(Decimal("0.01"))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def requests_per_second(self) -> Decimal:
        """Calculate average requests per second.

        Returns:
            Requests per second with 2 decimal places.
            Returns 0.00 if test_duration_seconds is 0.
        """
        if self.test_duration_seconds == 0:
            return Decimal("0.00")
        return Decimal(
            self.total_requests / self.test_duration_seconds
        ).quantize(Decimal("0.01"))

    @field_validator("latency_avg_ms", "latency_p95_ms", "latency_max_ms")
    @classmethod
    def validate_latency_precision(cls, v: Decimal) -> Decimal:
        """Ensure latency values have exactly 2 decimal places."""
        return v.quantize(Decimal("0.01"))

    @model_validator(mode="after")
    def validate_request_counts(self) -> LoadTestResult:
        """Validate that successful + failed requests equals total requests."""
        calculated_total = self.successful_requests + self.failed_requests
        if calculated_total != self.total_requests:
            raise ValueError(
                f"Request count mismatch: successful ({self.successful_requests}) + "
                f"failed ({self.failed_requests}) = {calculated_total}, "
                f"but total_requests is {self.total_requests}"
            )
        return self

    @model_validator(mode="after")
    def validate_latency_ordering(self) -> LoadTestResult:
        """Validate that latency metrics follow logical ordering: avg <= p95 <= max."""
        if self.latency_avg_ms > self.latency_p95_ms:
            raise ValueError(
                f"latency_avg_ms ({self.latency_avg_ms}) must be <= "
                f"latency_p95_ms ({self.latency_p95_ms})"
            )

        if self.latency_p95_ms > self.latency_max_ms:
            raise ValueError(
                f"latency_p95_ms ({self.latency_p95_ms}) must be <= "
                f"latency_max_ms ({self.latency_max_ms})"
            )

        return self

    @model_validator(mode="after")
    def validate_error_breakdown_counts(self) -> LoadTestResult:
        """Validate that error breakdown counts sum to failed_requests."""
        if not self.error_breakdown:
            # Empty error breakdown is valid if failed_requests is 0
            if self.failed_requests != 0:
                raise ValueError(
                    f"error_breakdown is empty but failed_requests is {self.failed_requests}"
                )
            return self

        total_error_count = sum(err.count for err in self.error_breakdown)
        if total_error_count != self.failed_requests:
            raise ValueError(
                f"Error breakdown count mismatch: sum of error counts ({total_error_count}) "
                f"does not equal failed_requests ({self.failed_requests})"
            )

        return self
