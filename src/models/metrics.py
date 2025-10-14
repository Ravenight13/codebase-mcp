# src/models/metrics.py
"""
Metrics models for Prometheus-compatible observability.

Constitutional Compliance:
- Principle V: Production-quality observability
- Principle VIII: Pydantic-based type safety with validators
- FR-012: Prometheus-compatible format
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, ConfigDict
from pydantic_core.core_schema import ValidationInfo
from decimal import Decimal


class LatencyHistogram(BaseModel):
    """
    Latency histogram bucket for Prometheus.

    Represents a single bucket in a histogram with cumulative count.
    """

    bucket_le: Decimal = Field(
        description="Bucket upper bound (le = less than or equal)"
    )
    count: int = Field(
        ge=0,
        description="Number of observations <= bucket_le"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "bucket_le": 0.5,
                "count": 9500
            }
        }
    )


class MetricCounter(BaseModel):
    """
    Counter metric (monotonically increasing).

    Represents a Prometheus counter that only increases over time.
    """

    name: str = Field(
        description="Metric name"
    )
    help_text: str = Field(
        description="Metric description"
    )
    value: int = Field(
        ge=0,
        description="Counter value"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "codebase_mcp_requests_total",
                "help_text": "Total number of requests",
                "value": 10000
            }
        }
    )


class MetricHistogram(BaseModel):
    """
    Histogram metric with buckets.

    Represents a Prometheus histogram with cumulative bucket counts.
    """

    name: str = Field(
        description="Metric name"
    )
    help_text: str = Field(
        description="Metric description"
    )
    buckets: list[LatencyHistogram] = Field(
        description="Histogram buckets (must be sorted by bucket_le)"
    )
    count: int = Field(
        ge=0,
        description="Total observation count"
    )
    sum: Decimal = Field(
        ge=0,
        description="Sum of all observations"
    )

    @field_validator("buckets")
    @classmethod
    def validate_bucket_ordering(cls, v: list[LatencyHistogram]) -> list[LatencyHistogram]:
        """
        Validate histogram buckets are sorted and counts are monotonically increasing.

        Validation Rules:
        - Buckets must be sorted by bucket_le (ascending)
        - Bucket counts must be monotonically increasing (cumulative)
        """
        if len(v) < 1:
            raise ValueError("Histogram must have at least one bucket")

        # Check bucket_le is sorted
        bucket_les = [bucket.bucket_le for bucket in v]
        if bucket_les != sorted(bucket_les):
            raise ValueError("Buckets must be sorted by bucket_le (ascending)")

        # Check counts are monotonically increasing
        counts = [bucket.count for bucket in v]
        for i in range(1, len(counts)):
            if counts[i] < counts[i-1]:
                raise ValueError(
                    f"Bucket counts must be monotonically increasing "
                    f"(bucket {i} has count {counts[i]} < previous count {counts[i-1]})"
                )

        return v

    @field_validator("count")
    @classmethod
    def validate_count_matches_final_bucket(cls, v: int, info: ValidationInfo) -> int:
        """Validate total count equals the final bucket count."""
        if "buckets" in info.data and len(info.data["buckets"]) > 0:
            final_bucket_count = info.data["buckets"][-1].count
            if v != final_bucket_count:
                raise ValueError(
                    f"Total count ({v}) must equal final bucket count ({final_bucket_count})"
                )
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "codebase_mcp_search_latency_seconds",
                "help_text": "Search query latency",
                "buckets": [
                    {"bucket_le": 0.1, "count": 450},
                    {"bucket_le": 0.5, "count": 9500},
                    {"bucket_le": 1.0, "count": 9950},
                    {"bucket_le": 2.0, "count": 10000}
                ],
                "count": 10000,
                "sum": 2345.67
            }
        }
    )


class MetricsResponse(BaseModel):
    """
    Metrics response in Prometheus format.

    Constitutional Compliance:
    - Principle V: Production-quality observability
    - FR-012: Prometheus-compatible format
    """

    counters: list[MetricCounter] = Field(
        default_factory=list,
        description="Counter metrics (requests, errors)"
    )
    histograms: list[MetricHistogram] = Field(
        default_factory=list,
        description="Histogram metrics (latency)"
    )

    def to_prometheus(self) -> str:
        """
        Export metrics in Prometheus text exposition format.

        Format follows Prometheus exposition format specification:
        https://prometheus.io/docs/instrumenting/exposition_formats/

        Returns:
            Prometheus-formatted text with HELP, TYPE, and metric lines.
        """
        lines: list[str] = []

        # Export counters
        for counter in self.counters:
            lines.append(f"# HELP {counter.name} {counter.help_text}")
            lines.append(f"# TYPE {counter.name} counter")
            lines.append(f"{counter.name} {counter.value}")
            lines.append("")  # Blank line between metrics

        # Export histograms
        for histogram in self.histograms:
            lines.append(f"# HELP {histogram.name} {histogram.help_text}")
            lines.append(f"# TYPE {histogram.name} histogram")

            # Export buckets
            for bucket in histogram.buckets:
                lines.append(
                    f'{histogram.name}_bucket{{le="{bucket.bucket_le}"}} {bucket.count}'
                )

            # Export +Inf bucket (always equals total count)
            lines.append(f'{histogram.name}_bucket{{le="+Inf"}} {histogram.count}')

            # Export count and sum
            lines.append(f"{histogram.name}_count {histogram.count}")
            lines.append(f"{histogram.name}_sum {histogram.sum}")
            lines.append("")  # Blank line between metrics

        return "\n".join(lines)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "counters": [
                    {
                        "name": "codebase_mcp_requests_total",
                        "help_text": "Total number of requests",
                        "value": 10000
                    },
                    {
                        "name": "codebase_mcp_errors_total",
                        "help_text": "Total number of errors",
                        "value": 42
                    }
                ],
                "histograms": [
                    {
                        "name": "codebase_mcp_search_latency_seconds",
                        "help_text": "Search query latency",
                        "buckets": [
                            {"bucket_le": 0.1, "count": 450},
                            {"bucket_le": 0.5, "count": 9500},
                            {"bucket_le": 1.0, "count": 9950},
                            {"bucket_le": 2.0, "count": 10000}
                        ],
                        "count": 10000,
                        "sum": 2345.67
                    }
                ]
            }
        }
    )
