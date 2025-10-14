# src/models/performance.py
from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from pydantic_core.core_schema import ValidationInfo
from typing import Literal
from datetime import datetime
from decimal import Decimal

class PerformanceBenchmarkResult(BaseModel):
    """
    Performance benchmark result for regression detection.

    Constitutional Compliance:
    - Principle VIII: Pydantic-based type safety with validators
    - Principle IV: Validates performance against constitutional targets
    """

    # Identification
    benchmark_id: str = Field(
        description="Unique identifier for this benchmark run (UUID)"
    )
    server_id: Literal["codebase-mcp", "workflow-mcp"] = Field(
        description="Server identifier"
    )
    operation_type: Literal["index", "search", "project_switch", "entity_query"] = Field(
        description="Operation being benchmarked"
    )

    # Timing
    timestamp: datetime = Field(
        description="Benchmark execution timestamp (ISO 8601)"
    )

    # Latency Metrics (in milliseconds)
    latency_p50_ms: Decimal = Field(
        ge=0,
        decimal_places=2,
        description="50th percentile latency in milliseconds"
    )
    latency_p95_ms: Decimal = Field(
        ge=0,
        decimal_places=2,
        description="95th percentile latency in milliseconds"
    )
    latency_p99_ms: Decimal = Field(
        ge=0,
        decimal_places=2,
        description="99th percentile latency in milliseconds"
    )
    latency_mean_ms: Decimal = Field(
        ge=0,
        decimal_places=2,
        description="Mean latency in milliseconds"
    )
    latency_min_ms: Decimal = Field(
        ge=0,
        decimal_places=2,
        description="Minimum latency in milliseconds"
    )
    latency_max_ms: Decimal = Field(
        ge=0,
        decimal_places=2,
        description="Maximum latency in milliseconds"
    )

    # Test Parameters
    sample_size: int = Field(
        ge=1,
        description="Number of iterations in the benchmark"
    )
    test_parameters: dict[str, str | int | float] = Field(
        default_factory=dict,
        description="Test-specific parameters (e.g., file_count, query_text)"
    )

    # Validation
    pass_status: Literal["pass", "fail", "warning"] = Field(
        description="Pass/fail status against target thresholds"
    )
    target_threshold_ms: Decimal | None = Field(
        default=None,
        description="Target threshold for this operation (from constitution)"
    )

    @field_validator("latency_p95_ms")
    @classmethod
    def validate_p95_ordering(cls, v: Decimal, info: ValidationInfo) -> Decimal:
        """Validate p95 >= p50."""
        if "latency_p50_ms" in info.data and v < info.data["latency_p50_ms"]:
            raise ValueError("latency_p95_ms must be >= latency_p50_ms")
        return v

    @field_validator("latency_p99_ms")
    @classmethod
    def validate_p99_ordering(cls, v: Decimal, info: ValidationInfo) -> Decimal:
        """Validate p99 >= p95."""
        if "latency_p95_ms" in info.data and v < info.data["latency_p95_ms"]:
            raise ValueError("latency_p99_ms must be >= latency_p95_ms")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "benchmark_id": "550e8400-e29b-41d4-a716-446655440000",
                "server_id": "codebase-mcp",
                "operation_type": "search",
                "timestamp": "2025-10-13T10:30:00Z",
                "latency_p50_ms": 245.32,
                "latency_p95_ms": 478.91,
                "latency_p99_ms": 512.45,
                "latency_mean_ms": 268.77,
                "latency_min_ms": 198.12,
                "latency_max_ms": 543.88,
                "sample_size": 100,
                "test_parameters": {
                    "query_text": "authentication logic",
                    "concurrent_clients": 10
                },
                "pass_status": "pass",
                "target_threshold_ms": 500.0
            }
        }
