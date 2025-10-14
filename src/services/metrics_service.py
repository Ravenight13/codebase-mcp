"""Metrics collection service for Prometheus-compatible observability.

Provides in-memory metrics storage and Prometheus format export for monitoring
server performance, request rates, and latency distributions.

Entity Responsibilities:
- Store counter metrics (monotonically increasing values)
- Record histogram observations (latency distributions)
- Export metrics in Prometheus text exposition format
- Provide thread-safe metric updates

Constitutional Compliance:
- Principle V: Production-quality observability with comprehensive metrics
- Principle VIII: Type-safe metrics collection with mypy --strict
- FR-012: Prometheus-compatible format (request counts, latency histograms)
"""

from __future__ import annotations

import threading
from collections import defaultdict
from decimal import Decimal
from typing import TYPE_CHECKING

from src.models.metrics import (
    LatencyHistogram,
    MetricCounter,
    MetricHistogram,
    MetricsResponse,
)

if TYPE_CHECKING:
    pass


class MetricsService:
    """In-memory metrics collection service.

    Thread-safe metrics storage with support for counters and histograms.
    Designed for high-throughput metric recording with minimal overhead.

    Constitutional Compliance:
    - Principle V: Production-quality observability
    - Principle VIII: Type-safe with complete annotations
    - FR-012: Prometheus-compatible format

    Attributes:
        _lock: Thread lock for concurrent metric updates
        _counters: Counter storage (name -> value)
        _counter_help: Counter descriptions (name -> help_text)
        _histograms: Histogram storage (name -> observations)
        _histogram_help: Histogram descriptions (name -> help_text)
        _histogram_buckets: Bucket definitions (name -> bucket_boundaries)
    """

    def __init__(self) -> None:
        """Initialize metrics service with empty storage."""
        self._lock = threading.Lock()

        # Counter storage
        self._counters: dict[str, int] = defaultdict(int)
        self._counter_help: dict[str, str] = {}

        # Histogram storage (name -> list of observed values)
        self._histograms: dict[str, list[float]] = defaultdict(list)
        self._histogram_help: dict[str, str] = {}
        self._histogram_buckets: dict[str, list[float]] = {}

    def increment_counter(
        self, name: str, help_text: str, value: int = 1
    ) -> None:
        """Increment a counter metric.

        Thread-safe counter increment with automatic registration.

        Args:
            name: Counter name (Prometheus naming convention: lowercase_with_underscores)
            help_text: Human-readable description of counter
            value: Amount to increment (default: 1)

        Example:
            >>> service = MetricsService()
            >>> service.increment_counter(
            ...     "codebase_mcp_requests_total",
            ...     "Total number of requests",
            ...     1
            ... )
        """
        with self._lock:
            self._counters[name] += value
            if name not in self._counter_help:
                self._counter_help[name] = help_text

    def observe_histogram(
        self,
        name: str,
        help_text: str,
        value: float,
        buckets: list[float] | None = None,
    ) -> None:
        """Record histogram observation.

        Thread-safe histogram observation recording with automatic bucket registration.

        Args:
            name: Histogram name (Prometheus naming convention)
            help_text: Human-readable description of histogram
            value: Observed value (e.g., latency in seconds)
            buckets: Optional bucket boundaries (default: [0.1, 0.5, 1.0, 2.0, 5.0, 10.0])

        Example:
            >>> service = MetricsService()
            >>> service.observe_histogram(
            ...     "codebase_mcp_search_latency_seconds",
            ...     "Search query latency",
            ...     0.234,  # 234ms
            ...     buckets=[0.1, 0.5, 1.0, 2.0]
            ... )
        """
        # Default buckets for latency histograms (in seconds)
        default_buckets = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0]

        with self._lock:
            self._histograms[name].append(value)

            # Register help text on first observation
            if name not in self._histogram_help:
                self._histogram_help[name] = help_text

            # Register buckets on first observation
            if name not in self._histogram_buckets:
                self._histogram_buckets[name] = sorted(
                    buckets if buckets else default_buckets
                )

    def get_metrics(self) -> MetricsResponse:
        """Export all metrics in Prometheus-compatible format.

        Thread-safe metrics export. Returns snapshot of current metrics state
        formatted as MetricsResponse for JSON or Prometheus text export.

        Returns:
            MetricsResponse with all counters and histograms

        Example:
            >>> service = MetricsService()
            >>> service.increment_counter("requests_total", "Total requests", 100)
            >>> metrics = service.get_metrics()
            >>> metrics.counters[0].name
            'requests_total'
            >>> metrics.counters[0].value
            100
        """
        with self._lock:
            # Build counter metrics
            counters = [
                MetricCounter(
                    name=name,
                    help_text=self._counter_help.get(name, ""),
                    value=value,
                )
                for name, value in self._counters.items()
            ]

            # Build histogram metrics
            histograms = [
                self._build_histogram(name, observations)
                for name, observations in self._histograms.items()
            ]

            return MetricsResponse(counters=counters, histograms=histograms)

    def _build_histogram(
        self, name: str, observations: list[float]
    ) -> MetricHistogram:
        """Build histogram metric from observations.

        Calculates cumulative bucket counts, total count, and sum for Prometheus
        histogram format.

        Args:
            name: Histogram name
            observations: List of observed values

        Returns:
            MetricHistogram with buckets and aggregates

        Algorithm:
        - Sort bucket boundaries (le = less than or equal)
        - For each bucket, count observations <= bucket_le (cumulative)
        - Calculate total count and sum of all observations
        """
        bucket_boundaries = self._histogram_buckets.get(name, [0.1, 0.5, 1.0, 2.0])
        help_text = self._histogram_help.get(name, "")

        # Calculate cumulative bucket counts
        buckets: list[LatencyHistogram] = []
        for bucket_le in sorted(bucket_boundaries):
            count = sum(1 for obs in observations if obs <= bucket_le)
            buckets.append(
                LatencyHistogram(
                    bucket_le=Decimal(str(bucket_le)),
                    count=count,
                )
            )

        # Calculate total count and sum
        total_count = len(observations)
        total_sum = Decimal(str(sum(observations)))

        return MetricHistogram(
            name=name,
            help_text=help_text,
            buckets=buckets,
            count=total_count,
            sum=total_sum,
        )

    def reset_metrics(self) -> None:
        """Reset all metrics to initial state.

        Clears all counters and histograms. Useful for testing or
        periodic metric windows.

        Warning:
            This operation loses all accumulated metrics. Use with caution
            in production environments.

        Example:
            >>> service = MetricsService()
            >>> service.increment_counter("requests_total", "Total requests", 100)
            >>> service.reset_metrics()
            >>> metrics = service.get_metrics()
            >>> len(metrics.counters)
            0
        """
        with self._lock:
            self._counters.clear()
            self._counter_help.clear()
            self._histograms.clear()
            self._histogram_help.clear()
            self._histogram_buckets.clear()


# Global metrics service instance
_metrics_service: MetricsService | None = None


def get_metrics_service() -> MetricsService:
    """Get global metrics service instance.

    Singleton pattern for application-wide metrics collection.

    Returns:
        MetricsService instance

    Example:
        >>> from src.services.metrics_service import get_metrics_service
        >>> metrics = get_metrics_service()
        >>> metrics.increment_counter("requests_total", "Total requests")
    """
    global _metrics_service
    if _metrics_service is None:
        _metrics_service = MetricsService()
    return _metrics_service


__all__ = ["MetricsService", "get_metrics_service"]
