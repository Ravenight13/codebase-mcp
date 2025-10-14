# Data Model: Performance Validation & Multi-Tenant Testing

**Feature**: 011-performance-validation-multi
**Date**: 2025-10-13
**Phase**: 1 (Design & Contracts)

## Overview

This document defines the Pydantic data models for performance validation, health monitoring, and observability. All models use Pydantic v2 with explicit validators and type annotations (Constitutional Principle VIII).

## Entity Definitions

### 1. Performance Benchmark Result

**Purpose**: Record of a single performance benchmark run for regression detection.

**Source**: Extracted from spec.md Key Entities (line 151-152)

**Pydantic Model**:
```python
# src/models/performance.py
from pydantic import BaseModel, Field, field_validator
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
    def validate_p95_ordering(cls, v: Decimal, info) -> Decimal:
        """Validate p95 >= p50."""
        if "latency_p50_ms" in info.data and v < info.data["latency_p50_ms"]:
            raise ValueError("latency_p95_ms must be >= latency_p50_ms")
        return v

    @field_validator("latency_p99_ms")
    @classmethod
    def validate_p99_ordering(cls, v: Decimal, info) -> Decimal:
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
```

**Validation Rules**:
- Latency percentiles must be ordered: p50 <= p95 <= p99
- All latency values must be non-negative
- Sample size must be >= 1
- pass_status derived from comparison with target_threshold_ms

**State Transitions**: None (immutable record)

---

### 2. Integration Test Case

**Purpose**: Definition of a cross-server workflow test scenario.

**Source**: Extracted from spec.md Key Entities (line 154-155)

**Pydantic Model**:
```python
# src/models/testing.py
from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime

class IntegrationTestStep(BaseModel):
    """Single step in an integration test workflow."""

    step_number: int = Field(
        ge=1,
        description="Step sequence number"
    )
    server: Literal["codebase-mcp", "workflow-mcp"] = Field(
        description="Target server for this step"
    )
    action: str = Field(
        description="Action description (e.g., 'Search for authentication code')"
    )
    api_call: dict[str, str | int | dict] = Field(
        description="API call details (method, endpoint, payload)"
    )
    expected_response: dict[str, str | int | list] = Field(
        description="Expected response structure"
    )
    assertions: list[str] = Field(
        description="List of assertions to validate (e.g., 'status_code == 200')"
    )

class IntegrationTestCase(BaseModel):
    """
    Cross-server workflow test scenario.

    Constitutional Compliance:
    - Principle III: Validates MCP protocol compliance across servers
    - Principle VIII: Type-safe test definitions
    """

    # Identification
    test_id: str = Field(
        description="Unique test identifier (UUID)"
    )
    test_name: str = Field(
        min_length=1,
        max_length=255,
        description="Human-readable test name"
    )
    test_description: str = Field(
        description="Detailed test scenario description"
    )

    # Configuration
    required_servers: list[Literal["codebase-mcp", "workflow-mcp"]] = Field(
        description="List of servers required for this test"
    )

    # Test Definition
    setup_steps: list[str] = Field(
        default_factory=list,
        description="Setup actions before test execution"
    )
    workflow_steps: list[IntegrationTestStep] = Field(
        min_length=1,
        description="Sequence of workflow steps to execute"
    )
    teardown_steps: list[str] = Field(
        default_factory=list,
        description="Cleanup actions after test execution"
    )

    # Execution Status
    last_run_status: Literal["pass", "fail", "skipped", "not_run"] = Field(
        default="not_run",
        description="Status from last test execution"
    )
    last_run_timestamp: datetime | None = Field(
        default=None,
        description="Timestamp of last test execution"
    )
    last_run_error: str | None = Field(
        default=None,
        description="Error message if last run failed"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "test_id": "int-test-001",
                "test_name": "Search to Work Item Workflow",
                "test_description": "Validate cross-server workflow from code search to work item creation",
                "required_servers": ["codebase-mcp", "workflow-mcp"],
                "setup_steps": [
                    "Index test repository in codebase-mcp",
                    "Create test project in workflow-mcp"
                ],
                "workflow_steps": [
                    {
                        "step_number": 1,
                        "server": "codebase-mcp",
                        "action": "Search for authentication code",
                        "api_call": {
                            "method": "POST",
                            "endpoint": "/mcp/search",
                            "payload": {"query": "authentication logic", "limit": 5}
                        },
                        "expected_response": {
                            "status_code": 200,
                            "results": "list[dict]"
                        },
                        "assertions": [
                            "status_code == 200",
                            "len(results) > 0"
                        ]
                    },
                    {
                        "step_number": 2,
                        "server": "workflow-mcp",
                        "action": "Create work item with entity reference",
                        "api_call": {
                            "method": "POST",
                            "endpoint": "/mcp/work_items",
                            "payload": {
                                "title": "Fix authentication bug",
                                "entity_references": ["{{results[0].chunk_id}}"]
                            }
                        },
                        "expected_response": {
                            "status_code": 201,
                            "id": "string"
                        },
                        "assertions": [
                            "status_code == 201",
                            "id is not None"
                        ]
                    }
                ],
                "teardown_steps": [
                    "Delete test work item",
                    "Clear indexed repository"
                ],
                "last_run_status": "pass",
                "last_run_timestamp": "2025-10-13T10:30:00Z",
                "last_run_error": None
            }
        }
```

**Validation Rules**:
- workflow_steps must have at least 1 step
- step_number must be sequential starting from 1
- required_servers must be non-empty

**State Transitions**:
- not_run -> pass/fail/skipped (after execution)
- pass/fail/skipped -> pass/fail/skipped (re-execution)

---

### 3. Load Test Result

**Purpose**: Record of load/stress test execution with performance and error metrics.

**Source**: Extracted from spec.md Key Entities (line 157-158)

**Pydantic Model**:
```python
# src/models/load_testing.py
from pydantic import BaseModel, Field, computed_field
from typing import Literal
from datetime import datetime, timedelta
from decimal import Decimal

class ErrorBreakdown(BaseModel):
    """Error breakdown by type during load test."""

    error_type: str = Field(
        description="Error type (e.g., 'timeout', 'connection_refused', '500_internal')"
    )
    count: int = Field(
        ge=0,
        description="Number of errors of this type"
    )
    percentage: Decimal = Field(
        ge=0,
        le=100,
        decimal_places=2,
        description="Percentage of total requests"
    )

class ResourceUsageStats(BaseModel):
    """Resource utilization statistics during load test."""

    cpu_percent_avg: Decimal = Field(
        ge=0,
        le=100,
        decimal_places=2,
        description="Average CPU utilization percentage"
    )
    cpu_percent_max: Decimal = Field(
        ge=0,
        le=100,
        decimal_places=2,
        description="Maximum CPU utilization percentage"
    )
    memory_mb_avg: Decimal = Field(
        ge=0,
        decimal_places=2,
        description="Average memory usage in MB"
    )
    memory_mb_max: Decimal = Field(
        ge=0,
        decimal_places=2,
        description="Maximum memory usage in MB"
    )
    connection_pool_utilization_avg: Decimal = Field(
        ge=0,
        le=100,
        decimal_places=2,
        description="Average connection pool utilization percentage"
    )
    connection_pool_utilization_max: Decimal = Field(
        ge=0,
        le=100,
        decimal_places=2,
        description="Maximum connection pool utilization percentage"
    )

class LoadTestResult(BaseModel):
    """
    Load/stress test execution result.

    Constitutional Compliance:
    - Principle IV: Validates performance under concurrent load
    - Principle V: Tracks error rates and resource utilization
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
        ge=0,
        decimal_places=2,
        description="Average latency"
    )
    latency_p95_ms: Decimal = Field(
        ge=0,
        decimal_places=2,
        description="95th percentile latency"
    )
    latency_max_ms: Decimal = Field(
        ge=0,
        decimal_places=2,
        description="Maximum latency"
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

    # Derived Metrics
    @computed_field
    @property
    def success_rate_percent(self) -> Decimal:
        """Calculate success rate percentage."""
        if self.total_requests == 0:
            return Decimal("0.00")
        return Decimal(
            (self.successful_requests / self.total_requests) * 100
        ).quantize(Decimal("0.01"))

    @computed_field
    @property
    def requests_per_second(self) -> Decimal:
        """Calculate average requests per second."""
        if self.test_duration_seconds == 0:
            return Decimal("0.00")
        return Decimal(
            self.total_requests / self.test_duration_seconds
        ).quantize(Decimal("0.01"))

    class Config:
        json_schema_extra = {
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
                "latency_avg_ms": 342.56,
                "latency_p95_ms": 1245.78,
                "latency_max_ms": 2987.23,
                "error_breakdown": [
                    {
                        "error_type": "timeout",
                        "count": 120,
                        "percentage": 0.40
                    },
                    {
                        "error_type": "connection_pool_exhausted",
                        "count": 30,
                        "percentage": 0.10
                    }
                ],
                "resource_usage": {
                    "cpu_percent_avg": 65.23,
                    "cpu_percent_max": 89.45,
                    "memory_mb_avg": 512.34,
                    "memory_mb_max": 678.90,
                    "connection_pool_utilization_avg": 75.50,
                    "connection_pool_utilization_max": 95.00
                }
            }
        }
```

**Validation Rules**:
- successful_requests + failed_requests = total_requests
- connection_pool_utilization must be 0-100%
- CPU/memory percentages must be non-negative

**State Transitions**: None (immutable record)

---

### 4. Health Check Response

**Purpose**: Server health status with database connectivity and connection pool metrics.

**Source**: Extracted from spec.md FR-011 (line 138) and research.md health check section

**Pydantic Model**:
```python
# src/models/health.py
from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime
from decimal import Decimal

class ConnectionPoolStats(BaseModel):
    """Connection pool statistics."""

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

    @property
    def utilization_percent(self) -> Decimal:
        """Calculate pool utilization percentage."""
        if self.size == 0:
            return Decimal("0.00")
        used = self.size - self.free
        return Decimal((used / self.size) * 100).quantize(Decimal("0.01"))

class HealthCheckResponse(BaseModel):
    """
    Health check response model.

    Constitutional Compliance:
    - Principle V: Production-quality health monitoring
    - Principle VIII: Type-safe health status reporting
    - FR-011: <50ms response time requirement
    """

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
        ge=0,
        decimal_places=2,
        description="Server uptime in seconds"
    )

    # Optional Details (for degraded/unhealthy states)
    details: dict[str, str] | None = Field(
        default=None,
        description="Additional details for degraded/unhealthy status"
    )

    class Config:
        json_schema_extra = {
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
```

**Validation Rules**:
- status derived from database_status and connection_pool utilization
- free connections must be <= size
- min_size <= size <= max_size

**State Transitions**:
- healthy <-> degraded (when connection pool > 80% or DB slow)
- degraded <-> unhealthy (when DB disconnected or pool exhausted)

---

### 5. Metrics Response

**Purpose**: Prometheus-compatible metrics for observability.

**Source**: Extracted from spec.md FR-012 (line 139) and research.md metrics section

**Pydantic Model**:
```python
# src/models/metrics.py
from pydantic import BaseModel, Field
from decimal import Decimal

class LatencyHistogram(BaseModel):
    """Latency histogram for Prometheus."""

    bucket_le: Decimal = Field(
        description="Bucket upper bound (le = less than or equal)"
    )
    count: int = Field(
        ge=0,
        description="Number of observations <= bucket_le"
    )

class MetricCounter(BaseModel):
    """Counter metric (monotonically increasing)."""

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

class MetricHistogram(BaseModel):
    """Histogram metric with buckets."""

    name: str = Field(
        description="Metric name"
    )
    help_text: str = Field(
        description="Metric description"
    )
    buckets: list[LatencyHistogram] = Field(
        description="Histogram buckets"
    )
    count: int = Field(
        ge=0,
        description="Total observation count"
    )
    sum: Decimal = Field(
        ge=0,
        decimal_places=2,
        description="Sum of all observations"
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

    class Config:
        json_schema_extra = {
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
```

**Validation Rules**:
- Histogram buckets must be sorted by bucket_le
- Bucket counts must be monotonically increasing
- Final bucket count must equal total count

**State Transitions**: None (immutable snapshot)

---

## Relationships

### Performance Benchmark Result
- **Related to**: Load Test Result (load tests generate benchmark results)
- **Cardinality**: 1 load test : N benchmark results

### Integration Test Case
- **Related to**: Integration Test Step (composition)
- **Cardinality**: 1 test case : N steps

### Health Check Response
- **Related to**: Connection Pool Stats (composition)
- **Cardinality**: 1 health check : 1 pool stats

### Metrics Response
- **Related to**: Metric Counter, Metric Histogram (composition)
- **Cardinality**: 1 metrics response : N counters + M histograms

## Storage Strategy

### Performance Benchmark Results
- **Storage**: JSON files in `performance_baselines/` directory (version-controlled)
- **Filename**: `{server_id}_{operation_type}_{timestamp}.json`
- **Retention**: Keep all baselines for historical comparison

### Integration Test Cases
- **Storage**: YAML files in `tests/integration/scenarios/` (version-controlled)
- **Filename**: `{test_id}.yaml`
- **Execution Results**: Stored in CI/CD artifacts, not committed

### Load Test Results
- **Storage**: JSON files in test output directory (CI/CD artifacts)
- **Filename**: `load_test_{server_id}_{timestamp}.json`
- **Retention**: Keep last 30 days in CI/CD

### Health Check / Metrics
- **Storage**: In-memory only (no persistence)
- **Rationale**: <50ms response time requirement, metrics scraped by Prometheus

## Implementation Files

| Model | File Path | Purpose |
|-------|-----------|---------|
| PerformanceBenchmarkResult | `src/models/performance.py` | Benchmark results |
| IntegrationTestCase | `src/models/testing.py` | Integration test definitions |
| LoadTestResult | `src/models/load_testing.py` | Load test results |
| HealthCheckResponse | `src/models/health.py` | Health check responses |
| MetricsResponse | `src/models/metrics.py` | Prometheus metrics |

## Next Steps

1. Generate OpenAPI schemas for health/metrics endpoints in `contracts/`
2. Generate integration test scenarios in `quickstart.md`
3. Implement Pydantic models in `src/models/` directory
4. Write validation tests for each model in `tests/unit/test_models.py`
