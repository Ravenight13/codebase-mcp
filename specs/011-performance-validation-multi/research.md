# Research: Performance Validation & Multi-Tenant Testing

**Feature**: 011-performance-validation-multi
**Date**: 2025-10-13
**Phase**: 0 (Research & Technical Discovery)

## Overview

This document captures technical research decisions for validating the split MCP architecture's performance, resilience, and observability. Research focuses on testing frameworks, baseline collection strategies, load testing approaches, and observability patterns that align with constitutional principles.

## Research Areas

### 1. Performance Baseline & Regression Testing

**Decision**: Use pytest-benchmark with JSON baseline storage for performance regression detection.

**Rationale**:
- pytest-benchmark integrates seamlessly with existing pytest infrastructure
- JSON baseline storage (`performance_baselines/`) enables version-controlled baseline tracking
- Supports percentile calculations (p50, p95, p99) out-of-the-box
- `--benchmark-compare` flag enables automatic regression detection
- Warm-up iterations and statistical analysis built-in

**Alternatives Considered**:
- **locust**: Python-based load testing framework. Rejected - overkill for baseline validation, better suited for distributed load testing which is out of scope.
- **Custom timing harness**: Manual timing with statistics. Rejected - reinvents wheel, lacks percentile support, no regression detection.
- **pytest-benchmark with histogram storage**: Store full histograms. Rejected - unnecessary complexity, JSON baselines sufficient for p95 validation.

**Implementation Approach**:
```python
# tests/benchmarks/test_indexing_perf.py
@pytest.mark.benchmark(group="indexing")
def test_indexing_10k_files(benchmark, test_repository_10k):
    """Validate indexing performance meets <60s (p95) target."""
    result = benchmark.pedantic(
        index_repository,
        args=(test_repository_10k,),
        iterations=5,
        warmup_rounds=1
    )
    assert result.stats.mean < 60.0  # Constitutional target
```

**Baseline Storage**:
- Pre-split baseline: `docs/performance/baseline-pre-split.json`
- Post-split baseline: `docs/performance/baseline-post-split.json`
- Comparison script: `scripts/compare_baselines.py`

---

### 2. Load Testing Framework

**Decision**: Use k6 for concurrent client load testing with JavaScript scenario definitions.

**Rationale**:
- k6 is purpose-built for load testing with excellent performance (written in Go)
- JavaScript DSL is intuitive for defining scenarios (ramp-up, sustained load)
- Built-in metrics (latency percentiles, throughput, error rates) align with requirements
- Can test HTTP/SSE endpoints directly (MCP over SSE transport)
- Supports virtual user scenarios (concurrent clients)
- Lightweight installation (single binary), no JVM overhead

**Alternatives Considered**:
- **Apache JMeter**: GUI-based load testing. Rejected - heavyweight JVM dependency, poor scripting support, harder to version control test scenarios.
- **Artillery.io**: Node.js load testing. Rejected - Node.js runtime adds complexity, k6 has better performance and metrics.
- **Python asyncio-based custom harness**: Roll our own concurrent client simulation. Rejected - reinvents wheel, lacks percentile calculation, no rate limiting or scenario support.

**Implementation Approach**:
```javascript
// tests/load/k6_codebase_load.js
import http from 'k6/http';
import { check } from 'k6';

export let options = {
  stages: [
    { duration: '2m', target: 10 },   // Ramp-up to 10 concurrent users
    { duration: '5m', target: 50 },   // Ramp-up to 50 concurrent users
    { duration: '10m', target: 50 },  // Sustained load at 50 users
    { duration: '2m', target: 0 },    // Ramp-down
  ],
  thresholds: {
    'http_req_duration': ['p(95)<500'], // 95th percentile < 500ms
    'http_req_failed': ['rate<0.01'],   // Error rate < 1%
  },
};

export default function () {
  let res = http.post('http://localhost:8020/mcp/search', JSON.stringify({
    query: 'function authentication',
    limit: 10
  }));
  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });
}
```

**Scenario Coverage**:
- Normal load: 10 concurrent clients (baseline validation)
- Stress load: 50 concurrent clients (resilience validation)
- Sustained load: 1 hour continuous (uptime validation per SC-007)

---

### 3. Cross-Server Integration Testing

**Decision**: Use pytest with httpx async client for cross-server workflow validation.

**Rationale**:
- httpx is already a project dependency (for Ollama communication)
- Async support aligns with constitutional principle (async everything)
- Allows testing both servers simultaneously with asyncio.gather()
- Built-in timeout support for resilience testing
- Can mock server failures for error recovery scenarios

**Alternatives Considered**:
- **requests library**: Synchronous HTTP client. Rejected - blocks on I/O, violates async-first principle, slower for multi-server testing.
- **aiohttp**: Alternative async HTTP client. Rejected - httpx already in project, no compelling reason to add dependency.
- **Direct MCP SDK client**: Use official MCP client. Rejected - adds complexity, httpx sufficient for HTTP/SSE endpoint testing.

**Implementation Approach**:
```python
# tests/integration/test_cross_server_workflow.py
@pytest.mark.asyncio
async def test_search_to_work_item_workflow():
    """Validate cross-server workflow: search code -> create work item with entity reference."""
    async with httpx.AsyncClient() as client:
        # Step 1: Search code via codebase-mcp
        search_response = await client.post(
            "http://localhost:8020/mcp/search",
            json={"query": "authentication logic", "limit": 5}
        )
        assert search_response.status_code == 200
        entities = search_response.json()["results"]

        # Step 2: Create work item via workflow-mcp with entity reference
        work_item_response = await client.post(
            "http://localhost:8010/mcp/work_items",
            json={
                "title": "Fix authentication bug",
                "entity_references": [entities[0]["chunk_id"]]
            }
        )
        assert work_item_response.status_code == 201

        # Step 3: Verify entity reference stored correctly
        work_item_id = work_item_response.json()["id"]
        get_response = await client.get(
            f"http://localhost:8010/mcp/work_items/{work_item_id}"
        )
        assert entities[0]["chunk_id"] in get_response.json()["entity_references"]
```

---

### 4. Health Check & Metrics Endpoints

**Decision**: Implement `/health` and `/metrics` endpoints with Pydantic response models, exposed via FastMCP resource registration.

**Rationale**:
- FastMCP supports resource registration via `@mcp.resource()` decorator (aligns with Principle XI)
- Pydantic models ensure type safety for health/metrics responses (Principle VIII)
- Health checks validate database connectivity, connection pool status, uptime
- Metrics expose Prometheus-compatible format for future observability integration
- <50ms response time requirement ensures lightweight implementation (in-memory metrics)

**Alternatives Considered**:
- **Separate monitoring service**: Dedicated service for metrics. Rejected - violates simplicity principle, adds operational complexity.
- **Database-backed metrics**: Store metrics in PostgreSQL. Rejected - adds latency, violates <50ms response time requirement.
- **Custom metric format**: Roll our own metric format. Rejected - Prometheus format is industry standard, enables future integration.

**Implementation Approach**:
```python
# src/models/health.py
from pydantic import BaseModel
from typing import Literal

class ConnectionPoolStats(BaseModel):
    size: int
    min_size: int
    max_size: int
    free: int
    utilization_percent: float

class HealthCheckResponse(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    timestamp: str  # ISO 8601
    database_status: Literal["connected", "disconnected", "degraded"]
    connection_pool: ConnectionPoolStats
    uptime_seconds: float

# src/mcp/server_fastmcp.py
@mcp.resource("health://status")
async def health_check() -> HealthCheckResponse:
    """Health check endpoint - returns status within 50ms."""
    pool_stats = await connection_manager.get_pool_stats()
    db_status = await check_database_connectivity()

    return HealthCheckResponse(
        status="healthy" if db_status == "connected" else "degraded",
        timestamp=datetime.utcnow().isoformat(),
        database_status=db_status,
        connection_pool=pool_stats,
        uptime_seconds=time.time() - server_start_time
    )
```

**Prometheus Metrics Format**:
```
# HELP codebase_mcp_search_latency_seconds Search query latency
# TYPE codebase_mcp_search_latency_seconds histogram
codebase_mcp_search_latency_seconds_bucket{le="0.1"} 450
codebase_mcp_search_latency_seconds_bucket{le="0.5"} 480
codebase_mcp_search_latency_seconds_bucket{le="1.0"} 495
codebase_mcp_search_latency_seconds_count 500
codebase_mcp_search_latency_seconds_sum 125.3
```

---

### 5. Error Recovery & Resilience Testing

**Decision**: Use pytest with database connection mocking and timeout simulation for resilience validation.

**Rationale**:
- pytest-mock enables database connection failure simulation without touching production DB
- asyncio timeout utilities simulate transient failures
- Structured logging can be validated via log file inspection (JSON format per Principle V)
- Aligns with existing test infrastructure (no new framework required)

**Alternatives Considered**:
- **Chaos Monkey / chaos engineering framework**: Random failure injection. Rejected - out of scope for Phase 06, deferred to future enhancements.
- **Manual server shutdown testing**: Kill servers manually. Rejected - not repeatable, hard to automate in CI/CD.
- **Docker network partitions**: Simulate network failures via Docker. Rejected - adds Docker complexity, not aligned with local-first testing approach.

**Implementation Approach**:
```python
# tests/integration/test_resilience.py
@pytest.mark.asyncio
async def test_database_reconnection_after_failure(mocker):
    """Validate server detects DB failure within 5s and reconnects automatically."""
    # Simulate database connection failure
    mock_pool = mocker.patch('src.connection_pool.manager.ConnectionPoolManager.acquire')
    mock_pool.side_effect = asyncpg.exceptions.ConnectionDoesNotExistError()

    # Trigger database operation
    start_time = time.time()
    with pytest.raises(DatabaseConnectionError):
        await indexer_service.index_repository("/test/repo")

    # Verify failure detected within 5 seconds (FR-008)
    assert time.time() - start_time < 5.0

    # Simulate connection restoration
    mock_pool.side_effect = None

    # Verify automatic reconnection
    await asyncio.sleep(1.0)  # Wait for retry with exponential backoff
    result = await indexer_service.index_repository("/test/repo")
    assert result.status == "success"
```

---

### 6. Performance Variance & Regression Detection

**Decision**: Implement hybrid approach - flag violations if metrics exceed BOTH 10% degradation from baseline AND constitutional targets.

**Rationale**:
- FR-018 specifies hybrid approach to handle minor variance within acceptable range
- Prevents false positives from minor fluctuations (e.g., 8% degradation within targets)
- Ensures constitutional targets remain hard floor (cannot regress below targets even if baseline allows)
- Simple boolean logic: `regression = (degradation > 10%) AND (metric > target)`

**Alternatives Considered**:
- **Strict baseline enforcement**: Flag any degradation. Rejected - too sensitive, minor variance expected across runs.
- **Strict target enforcement only**: Ignore baseline comparison. Rejected - misses regression trends that stay within targets but degrade significantly.
- **Statistical significance testing**: Use t-tests for variance. Rejected - overkill for straightforward performance validation.

**Implementation Approach**:
```python
# scripts/validate_performance.sh
def check_regression(current: float, baseline: float, target: float) -> bool:
    """
    Flag regression if BOTH conditions met:
    1. Current exceeds baseline by >10%
    2. Current exceeds constitutional target
    """
    degradation_percent = ((current - baseline) / baseline) * 100
    exceeds_baseline = degradation_percent > 10.0
    exceeds_target = current > target

    return exceeds_baseline and exceeds_target

# Example: Indexing validation
current_indexing = 55.0  # seconds
baseline_indexing = 48.0  # seconds (pre-split)
target_indexing = 60.0    # seconds (constitutional)

regression = check_regression(current_indexing, baseline_indexing, target_indexing)
# regression = (55-48)/48*100 > 10% AND 55 > 60
# regression = 14.6% > 10% AND False
# regression = False (within target, acceptable degradation)
```

---

### 7. Test Data Generation

**Decision**: Use fixture-based test repository generation with tree-sitter for realistic code structure.

**Rationale**:
- Realistic code structure ensures performance tests reflect production conditions
- tree-sitter can generate syntactically valid code snippets (Python, JavaScript)
- Fixture scope controls repository lifecycle (function, session)
- Aligns with existing tree-sitter dependency (no new dependencies)

**Alternatives Considered**:
- **Static test repositories**: Pre-generated test repos checked into git. Rejected - large binary blobs, hard to version control, inflexible.
- **Random file generation**: Generate random text files. Rejected - unrealistic, doesn't test tree-sitter parsing overhead.
- **Cloning real repositories**: Use actual open-source repos. Rejected - network dependency, licensing concerns, inconsistent results.

**Implementation Approach**:
```python
# tests/fixtures/test_repository.py
@pytest.fixture(scope="session")
def test_repository_10k(tmp_path_factory) -> Path:
    """Generate 10,000-file test repository with realistic code structure."""
    repo_path = tmp_path_factory.mktemp("test_repo_10k")

    # Generate Python files with realistic structure
    for i in range(10000):
        file_path = repo_path / f"module_{i // 100}" / f"file_{i}.py"
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate syntactically valid Python code
        code = generate_python_module(
            num_functions=random.randint(3, 10),
            num_classes=random.randint(1, 3),
            avg_lines_per_function=random.randint(10, 50)
        )
        file_path.write_text(code)

    return repo_path
```

---

## Summary of Key Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| Performance Baseline | pytest-benchmark with JSON storage | Version-controlled baselines, percentile support, regression detection |
| Load Testing | k6 with JavaScript scenarios | Purpose-built, excellent performance, built-in metrics |
| Integration Testing | pytest + httpx async client | Existing dependency, async support, multi-server testing |
| Health/Metrics | FastMCP resources + Pydantic models | Type safety, constitutional compliance, Prometheus format |
| Resilience Testing | pytest-mock + timeout simulation | Repeatable, automatable, aligns with existing infrastructure |
| Regression Detection | Hybrid approach (10% + targets) | Balances variance tolerance with constitutional compliance |
| Test Data | Fixture-based generation with tree-sitter | Realistic structure, version-controllable, flexible |

## Open Questions (Resolved)

1. **Q**: Where are pre-split baseline metrics stored?
   **A**: Assumed location is `docs/performance/baseline-pre-split.json`. If missing, generate from current monolithic server before split deployment.

2. **Q**: How to handle workflow-mcp testing if server doesn't exist yet?
   **A**: Create mock workflow-mcp endpoints for cross-server integration tests. Full workflow-mcp implementation is hypothetical for Phase 06 scope.

3. **Q**: Should load testing cover multi-instance deployment?
   **A**: No, explicitly out of scope per spec.md line 191. Focus on single-instance capacity.

4. **Q**: What error rate threshold constitutes "graceful degradation"?
   **A**: k6 threshold: `http_req_failed: rate<0.01` (1% error rate). Aligns with 99.9% uptime requirement (SC-007).

5. **Q**: Should metrics endpoint impact main operations under load?
   **A**: Edge case in spec.md line 122. Implementation uses in-memory metrics with O(1) access to ensure <50ms response time without impacting indexing/search operations.

## Next Steps (Phase 1)

1. Generate `data-model.md` - Define Pydantic models for performance metrics, health checks, load test results
2. Generate `contracts/` - OpenAPI schemas for health/metrics endpoints
3. Generate `quickstart.md` - Integration test scenarios covering all user stories
4. Update agent context - Add k6, pytest-benchmark to technology stack in CLAUDE.md
