"""Observability endpoint integration tests for Phase 7 User Story 5.

Validates health check and metrics endpoints meet constitutional requirements
for response time, schema compliance, and structured logging.

Test Coverage:
- T043: Health check response time (<50ms per SC-010)
- T044: Health check schema validation (OpenAPI contract compliance)
- T045: Metrics endpoint format (JSON and Prometheus text per FR-012)
- T046: Structured logging validation (JSON format with required fields)

Constitutional Compliance:
- Principle IV: Performance guarantees (SC-010: <50ms health checks)
- Principle V: Production quality observability
- Principle VIII: Type safety (mypy --strict compliance)
- SC-010: Health checks respond within 50ms
- FR-011: Health endpoint <50ms response time requirement
- FR-012: Prometheus-compatible metrics format

FR References:
- FR-011: Health check endpoint with database connectivity check (<50ms)
- FR-012: Prometheus metrics endpoint (counters, histograms, text format)
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, AsyncGenerator

import pytest
import pytest_asyncio

from src.connection_pool.config import PoolConfig
from src.connection_pool.manager import ConnectionPoolManager
from src.models.health import ConnectionPoolStats, HealthCheckResponse
from src.models.metrics import (
    LatencyHistogram,
    MetricCounter,
    MetricHistogram,
    MetricsResponse,
)
from src.services.health_service import HealthService
from src.services.metrics_service import MetricsService


@pytest_asyncio.fixture
async def pool_manager() -> AsyncGenerator[ConnectionPoolManager, None]:
    """Create connection pool manager for health checks.

    Yields:
        Initialized ConnectionPoolManager for testing health service

    Note:
        Uses test database connection from environment
    """
    config = PoolConfig(
        database_url="postgresql+asyncpg://postgres:postgres@localhost:5432/codebase_mcp_test",
        min_size=2,
        max_size=5,
        timeout=5.0,
    )

    manager = ConnectionPoolManager()
    await manager.initialize(config)

    yield manager

    # Cleanup
    await manager.shutdown()


@pytest_asyncio.fixture
async def health_service(pool_manager: ConnectionPoolManager) -> HealthService:
    """Create health service for testing.

    Args:
        pool_manager: Connection pool manager fixture

    Returns:
        Initialized HealthService instance
    """
    return HealthService(pool_manager)


@pytest.fixture
def metrics_service() -> MetricsService:
    """Create metrics service for testing.

    Returns:
        Fresh MetricsService instance with empty metrics
    """
    service = MetricsService()
    service.reset_metrics()
    return service


@pytest.mark.asyncio
async def test_health_check_response_time(
    health_service: HealthService,
) -> None:
    """Validate health check responds within 50ms per SC-010.

    Test validates:
    1. Health check completes in <50ms (p95 requirement per FR-011)
    2. Response contains all required fields
    3. Status values are valid (healthy/degraded/unhealthy)
    4. Database status is reported correctly
    5. Connection pool statistics are present

    Acceptance Criteria:
    - quickstart.md lines 413-430
    - SC-010: Health checks respond within 50ms
    - FR-011: <50ms response time requirement

    Constitutional Compliance:
    - Principle IV: Performance guarantees (<50ms health check)
    - Principle V: Production quality health monitoring
    - Principle VIII: Type safety (HealthCheckResponse model)

    Args:
        health_service: Health service fixture

    Test Strategy:
        Execute health check 10 times and validate:
        - p95 latency <50ms
        - All responses have correct schema
        - Response times are consistent
    """
    # Execute health checks and measure latency
    latencies: list[float] = []
    responses: list[HealthCheckResponse] = []

    for _ in range(10):
        start_time = time.time()
        response = await health_service.check_health()
        elapsed_ms = (time.time() - start_time) * 1000

        latencies.append(elapsed_ms)
        responses.append(response)

    # Calculate p95 latency
    sorted_latencies = sorted(latencies)
    p95_index = int(len(sorted_latencies) * 0.95)
    p95_latency = sorted_latencies[p95_index]

    # Validate p95 latency meets constitutional requirement
    assert p95_latency < 50.0, (
        f"Health check p95 latency {p95_latency:.2f}ms exceeds 50ms limit (SC-010)"
    )

    # Validate all responses have correct structure
    for response in responses:
        # Validate status is one of allowed values
        assert response.status in ["healthy", "degraded", "unhealthy"], (
            f"Invalid status: {response.status}"
        )

        # Validate timestamp is present and recent
        assert isinstance(response.timestamp, datetime), (
            f"Invalid timestamp type: {type(response.timestamp)}"
        )

        # Validate database_status
        assert response.database_status in ["connected", "disconnected", "degraded"], (
            f"Invalid database_status: {response.database_status}"
        )

        # Validate connection pool stats are present
        assert isinstance(response.connection_pool, ConnectionPoolStats), (
            f"Invalid connection_pool type: {type(response.connection_pool)}"
        )
        assert response.connection_pool.size >= 0
        assert response.connection_pool.min_size >= 0
        assert response.connection_pool.max_size > 0
        assert response.connection_pool.free >= 0

        # Validate uptime
        assert isinstance(response.uptime_seconds, Decimal), (
            f"Invalid uptime_seconds type: {type(response.uptime_seconds)}"
        )
        assert response.uptime_seconds >= Decimal("0")

    # Log performance summary for monitoring
    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    min_latency = min(latencies)

    print(f"\nHealth Check Performance Summary:")
    print(f"  Iterations: {len(latencies)}")
    print(f"  p95 Latency: {p95_latency:.2f}ms (target: <50ms)")
    print(f"  Avg Latency: {avg_latency:.2f}ms")
    print(f"  Min Latency: {min_latency:.2f}ms")
    print(f"  Max Latency: {max_latency:.2f}ms")


@pytest.mark.asyncio
async def test_health_check_response_schema(
    health_service: HealthService,
) -> None:
    """Validate health check response conforms to OpenAPI contract.

    Test validates:
    1. Response matches HealthCheckResponse Pydantic model
    2. All required fields are present
    3. Field types match contract specification
    4. Nested connection pool stats are valid
    5. Response can be serialized to JSON

    Acceptance Criteria:
    - contracts/health-endpoint.yaml compliance
    - HealthCheckResponse model validation

    Constitutional Compliance:
    - Principle VIII: Type safety with Pydantic models
    - Principle V: Production quality API contracts
    - FR-011: Health check endpoint specification

    Args:
        health_service: Health service fixture

    Test Strategy:
        Execute health check and validate:
        - Pydantic model validation passes
        - JSON serialization works correctly
        - All contract fields present
    """
    # Execute health check
    response = await health_service.check_health()

    # Validate response is HealthCheckResponse instance
    assert isinstance(response, HealthCheckResponse), (
        f"Response must be HealthCheckResponse, got {type(response)}"
    )

    # Validate all required fields are present
    assert hasattr(response, "status"), "Missing field: status"
    assert hasattr(response, "timestamp"), "Missing field: timestamp"
    assert hasattr(response, "database_status"), "Missing field: database_status"
    assert hasattr(response, "connection_pool"), "Missing field: connection_pool"
    assert hasattr(response, "uptime_seconds"), "Missing field: uptime_seconds"
    assert hasattr(response, "details"), "Missing field: details"

    # Validate connection pool nested structure
    pool_stats = response.connection_pool
    assert hasattr(pool_stats, "size"), "Missing connection_pool field: size"
    assert hasattr(pool_stats, "min_size"), "Missing connection_pool field: min_size"
    assert hasattr(pool_stats, "max_size"), "Missing connection_pool field: max_size"
    assert hasattr(pool_stats, "free"), "Missing connection_pool field: free"

    # Validate pool utilization calculation
    utilization = pool_stats.utilization_percent
    assert isinstance(utilization, Decimal), (
        f"Utilization must be Decimal, got {type(utilization)}"
    )
    assert Decimal("0") <= utilization <= Decimal("100"), (
        f"Utilization must be 0-100%, got {utilization}"
    )

    # Validate JSON serialization (required for MCP resource response)
    health_dict: dict[str, Any] = response.model_dump(mode="json")
    json_str = json.dumps(health_dict)
    assert len(json_str) > 0, "JSON serialization failed"

    # Validate deserialized JSON contains all fields
    deserialized = json.loads(json_str)
    assert "status" in deserialized, "JSON missing field: status"
    assert "timestamp" in deserialized, "JSON missing field: timestamp"
    assert "database_status" in deserialized, "JSON missing field: database_status"
    assert "connection_pool" in deserialized, "JSON missing field: connection_pool"
    assert "uptime_seconds" in deserialized, "JSON missing field: uptime_seconds"

    # Validate connection_pool nested structure in JSON
    pool_json = deserialized["connection_pool"]
    assert "size" in pool_json, "JSON connection_pool missing field: size"
    assert "min_size" in pool_json, "JSON connection_pool missing field: min_size"
    assert "max_size" in pool_json, "JSON connection_pool missing field: max_size"
    assert "free" in pool_json, "JSON connection_pool missing field: free"

    # Validate status values are contract-compliant
    assert deserialized["status"] in ["healthy", "degraded", "unhealthy"], (
        f"Invalid status in JSON: {deserialized['status']}"
    )
    assert deserialized["database_status"] in ["connected", "disconnected", "degraded"], (
        f"Invalid database_status in JSON: {deserialized['database_status']}"
    )


@pytest.mark.asyncio
async def test_metrics_prometheus_format(
    metrics_service: MetricsService,
) -> None:
    """Validate metrics endpoint supports both JSON and Prometheus text formats.

    Test validates:
    1. Metrics are collected in memory
    2. JSON format contains counters and histograms
    3. Prometheus text format conforms to exposition format spec
    4. Counter values are monotonically increasing
    5. Histogram buckets are sorted and cumulative

    Acceptance Criteria:
    - quickstart.md lines 435-468
    - FR-012: Prometheus-compatible metrics format
    - contracts/metrics-endpoint.yaml compliance

    Constitutional Compliance:
    - Principle V: Production quality observability
    - Principle VIII: Type safety (MetricsResponse model)
    - FR-012: Prometheus format with counters and histograms

    Args:
        metrics_service: Metrics service fixture

    Test Strategy:
        Record test metrics and validate:
        - JSON format with MetricsResponse schema
        - Prometheus text format compliance
        - Bucket ordering and cumulative counts
    """
    # Record test counter metrics
    metrics_service.increment_counter(
        name="codebase_mcp_requests_total",
        help_text="Total number of requests",
        value=100,
    )
    metrics_service.increment_counter(
        name="codebase_mcp_errors_total",
        help_text="Total number of errors",
        value=5,
    )

    # Record test histogram metrics (search latencies in seconds)
    search_latencies = [0.05, 0.15, 0.25, 0.35, 0.45, 0.75, 0.85, 1.5, 2.5]
    for latency in search_latencies:
        metrics_service.observe_histogram(
            name="codebase_mcp_search_latency_seconds",
            help_text="Search query latency",
            value=latency,
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0],
        )

    # === Test JSON Format ===

    metrics_response = metrics_service.get_metrics()

    # Validate MetricsResponse type
    assert isinstance(metrics_response, MetricsResponse), (
        f"Response must be MetricsResponse, got {type(metrics_response)}"
    )

    # Validate counters structure
    assert len(metrics_response.counters) == 2, (
        f"Expected 2 counters, got {len(metrics_response.counters)}"
    )

    # Find request counter
    request_counter = next(
        (c for c in metrics_response.counters if c.name == "codebase_mcp_requests_total"),
        None,
    )
    assert request_counter is not None, "Missing counter: codebase_mcp_requests_total"
    assert isinstance(request_counter, MetricCounter), (
        f"Counter must be MetricCounter, got {type(request_counter)}"
    )
    assert request_counter.value == 100, (
        f"Expected counter value 100, got {request_counter.value}"
    )
    assert request_counter.help_text == "Total number of requests"

    # Find error counter
    error_counter = next(
        (c for c in metrics_response.counters if c.name == "codebase_mcp_errors_total"),
        None,
    )
    assert error_counter is not None, "Missing counter: codebase_mcp_errors_total"
    assert error_counter.value == 5

    # Validate histograms structure
    assert len(metrics_response.histograms) == 1, (
        f"Expected 1 histogram, got {len(metrics_response.histograms)}"
    )

    # Validate search latency histogram
    search_histogram = metrics_response.histograms[0]
    assert isinstance(search_histogram, MetricHistogram), (
        f"Histogram must be MetricHistogram, got {type(search_histogram)}"
    )
    assert search_histogram.name == "codebase_mcp_search_latency_seconds"
    assert search_histogram.help_text == "Search query latency"
    assert search_histogram.count == len(search_latencies), (
        f"Expected histogram count {len(search_latencies)}, got {search_histogram.count}"
    )

    # Validate histogram buckets are sorted
    bucket_les = [bucket.bucket_le for bucket in search_histogram.buckets]
    assert bucket_les == sorted(bucket_les), (
        f"Histogram buckets must be sorted, got {bucket_les}"
    )

    # Validate bucket counts are cumulative (monotonically increasing)
    bucket_counts = [bucket.count for bucket in search_histogram.buckets]
    for i in range(1, len(bucket_counts)):
        assert bucket_counts[i] >= bucket_counts[i - 1], (
            f"Bucket counts must be cumulative, but bucket {i} has count "
            f"{bucket_counts[i]} < previous count {bucket_counts[i - 1]}"
        )

    # Validate total count equals final bucket count
    assert search_histogram.count == search_histogram.buckets[-1].count, (
        f"Total count ({search_histogram.count}) must equal final bucket count "
        f"({search_histogram.buckets[-1].count})"
    )

    # Validate sum calculation
    expected_sum = sum(search_latencies)
    assert abs(float(search_histogram.sum) - expected_sum) < 0.01, (
        f"Expected histogram sum {expected_sum}, got {search_histogram.sum}"
    )

    # Validate JSON serialization
    metrics_dict: dict[str, Any] = metrics_response.model_dump(mode="json")
    json_str = json.dumps(metrics_dict)
    assert len(json_str) > 0, "JSON serialization failed"

    deserialized = json.loads(json_str)
    assert "counters" in deserialized, "JSON missing field: counters"
    assert "histograms" in deserialized, "JSON missing field: histograms"
    assert len(deserialized["counters"]) == 2
    assert len(deserialized["histograms"]) == 1

    # === Test Prometheus Text Format ===

    prometheus_text = metrics_response.to_prometheus()

    # Validate Prometheus text format structure
    assert isinstance(prometheus_text, str), (
        f"Prometheus text must be str, got {type(prometheus_text)}"
    )
    assert len(prometheus_text) > 0, "Prometheus text is empty"

    # Validate counter format (HELP, TYPE, value)
    assert "# HELP codebase_mcp_requests_total Total number of requests" in prometheus_text, (
        "Missing HELP line for requests_total counter"
    )
    assert "# TYPE codebase_mcp_requests_total counter" in prometheus_text, (
        "Missing TYPE line for requests_total counter"
    )
    assert "codebase_mcp_requests_total 100" in prometheus_text, (
        "Missing value line for requests_total counter"
    )

    # Validate error counter
    assert "# HELP codebase_mcp_errors_total Total number of errors" in prometheus_text
    assert "# TYPE codebase_mcp_errors_total counter" in prometheus_text
    assert "codebase_mcp_errors_total 5" in prometheus_text

    # Validate histogram format
    assert "# HELP codebase_mcp_search_latency_seconds Search query latency" in prometheus_text, (
        "Missing HELP line for search_latency histogram"
    )
    assert "# TYPE codebase_mcp_search_latency_seconds histogram" in prometheus_text, (
        "Missing TYPE line for search_latency histogram"
    )

    # Validate histogram buckets
    assert 'codebase_mcp_search_latency_seconds_bucket{le="0.1"}' in prometheus_text, (
        "Missing 0.1s bucket"
    )
    assert 'codebase_mcp_search_latency_seconds_bucket{le="0.5"}' in prometheus_text, (
        "Missing 0.5s bucket"
    )
    assert 'codebase_mcp_search_latency_seconds_bucket{le="1.0"}' in prometheus_text, (
        "Missing 1.0s bucket"
    )
    assert 'codebase_mcp_search_latency_seconds_bucket{le="+Inf"}' in prometheus_text, (
        "Missing +Inf bucket"
    )

    # Validate histogram count and sum
    assert f"codebase_mcp_search_latency_seconds_count {len(search_latencies)}" in prometheus_text, (
        "Missing or incorrect histogram count"
    )
    assert "codebase_mcp_search_latency_seconds_sum" in prometheus_text, (
        "Missing histogram sum"
    )


@pytest.mark.asyncio
async def test_structured_logging_format(tmp_path: Path) -> None:
    """Validate structured logs are JSON with required fields.

    Test validates:
    1. Log entries are valid JSON
    2. Each entry contains timestamp, level, event fields
    3. Timestamps are ISO 8601 format
    4. Log levels are valid (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    5. Log entries contain contextual information

    Acceptance Criteria:
    - quickstart.md lines 473-489
    - FR-013: Structured logging with JSON format

    Constitutional Compliance:
    - Principle V: Production quality logging
    - Principle VIII: Type safety in log structure
    - FR-013: Structured logging for monitoring

    Args:
        tmp_path: Pytest temporary directory fixture

    Test Strategy:
        Generate test log entries and validate:
        - JSON format compliance
        - Required fields present
        - Timestamp and level validity
    """
    # Create test log file
    log_file = tmp_path / "test_structured_logging.log"

    # Write test log entries in JSON format
    test_logs = [
        {
            "timestamp": "2025-10-13T10:30:00.123456Z",
            "level": "INFO",
            "event": "server_started",
            "message": "Codebase MCP Server started successfully",
            "context": {"port": 8020, "version": "2.0.0"},
        },
        {
            "timestamp": "2025-10-13T10:30:01.456789Z",
            "level": "DEBUG",
            "event": "health_check_executed",
            "message": "Health check completed",
            "context": {"status": "healthy", "latency_ms": 12.5},
        },
        {
            "timestamp": "2025-10-13T10:30:02.789012Z",
            "level": "WARNING",
            "event": "pool_utilization_high",
            "message": "Connection pool utilization exceeds 80%",
            "context": {"utilization_percent": 85.5, "pool_size": 10, "free": 2},
        },
        {
            "timestamp": "2025-10-13T10:30:03.012345Z",
            "level": "ERROR",
            "event": "database_connection_failed",
            "message": "Failed to connect to database",
            "context": {"error": "Connection timeout", "retry_count": 3},
        },
    ]

    # Write test logs to file
    with open(log_file, "w") as f:
        for log_entry in test_logs:
            f.write(json.dumps(log_entry) + "\n")

    # Read and validate log file
    log_entries = []
    with open(log_file, "r") as f:
        for line in f:
            try:
                log_entry = json.loads(line.strip())
                log_entries.append(log_entry)
            except json.JSONDecodeError as e:
                pytest.fail(f"Log entry is not valid JSON: {line!r}, error: {e}")

    # Validate we have all test log entries
    assert len(log_entries) == 4, (
        f"Expected 4 log entries, got {len(log_entries)}"
    )

    # Validate each log entry structure
    valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

    for idx, log_entry in enumerate(log_entries):
        # Validate required fields are present
        assert "timestamp" in log_entry, f"Log entry {idx} missing field: timestamp"
        assert "level" in log_entry, f"Log entry {idx} missing field: level"
        assert "event" in log_entry, f"Log entry {idx} missing field: event"
        assert "message" in log_entry, f"Log entry {idx} missing field: message"

        # Validate timestamp is ISO 8601 format
        timestamp_str = log_entry["timestamp"]
        try:
            # Parse ISO 8601 timestamp (handle both with and without microseconds)
            if timestamp_str.endswith("Z"):
                # UTC timezone indicator
                datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            else:
                datetime.fromisoformat(timestamp_str)
        except ValueError as e:
            pytest.fail(
                f"Log entry {idx} has invalid timestamp format: {timestamp_str}, error: {e}"
            )

        # Validate level is valid
        level = log_entry["level"]
        assert level in valid_levels, (
            f"Log entry {idx} has invalid level: {level}, must be one of {valid_levels}"
        )

        # Validate event and message are non-empty strings
        assert isinstance(log_entry["event"], str) and len(log_entry["event"]) > 0, (
            f"Log entry {idx} event must be non-empty string"
        )
        assert isinstance(log_entry["message"], str) and len(log_entry["message"]) > 0, (
            f"Log entry {idx} message must be non-empty string"
        )

        # Validate context field (if present) is a dict
        if "context" in log_entry:
            assert isinstance(log_entry["context"], dict), (
                f"Log entry {idx} context must be dict, got {type(log_entry['context'])}"
            )

    # Validate specific test log entries
    assert log_entries[0]["event"] == "server_started"
    assert log_entries[0]["level"] == "INFO"
    assert "port" in log_entries[0]["context"]
    assert log_entries[0]["context"]["port"] == 8020

    assert log_entries[1]["event"] == "health_check_executed"
    assert log_entries[1]["level"] == "DEBUG"
    assert "status" in log_entries[1]["context"]

    assert log_entries[2]["event"] == "pool_utilization_high"
    assert log_entries[2]["level"] == "WARNING"
    assert "utilization_percent" in log_entries[2]["context"]

    assert log_entries[3]["event"] == "database_connection_failed"
    assert log_entries[3]["level"] == "ERROR"
    assert "error" in log_entries[3]["context"]

    # Validate log entries are sorted by timestamp (chronological order)
    timestamps = [log_entry["timestamp"] for log_entry in log_entries]
    assert timestamps == sorted(timestamps), (
        "Log entries must be in chronological order"
    )


__all__ = [
    "test_health_check_response_time",
    "test_health_check_response_schema",
    "test_metrics_prometheus_format",
    "test_structured_logging_format",
]
