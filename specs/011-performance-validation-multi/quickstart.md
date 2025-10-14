# Quickstart: Performance Validation & Multi-Tenant Testing

**Feature**: 011-performance-validation-multi
**Date**: 2025-10-13
**Phase**: 1 (Design & Contracts)

## Overview

This document provides integration test scenarios for validating the split MCP architecture's performance, resilience, and observability. Each scenario maps to acceptance criteria from the feature specification.

## Prerequisites

### Environment Setup

1. **Both servers running**:
   ```bash
   # Terminal 1: Start codebase-mcp
   python run_server.py --port 8020

   # Terminal 2: Start workflow-mcp (hypothetical for Phase 06)
   python run_workflow_server.py --port 8010
   ```

2. **Test database populated**:
   ```bash
   # Index test repository (10k files)
   pytest tests/fixtures/test_repository.py::setup_test_repo_10k

   # Populate workflow-mcp with test data
   pytest tests/fixtures/workflow_fixtures.py::setup_test_projects
   ```

3. **Dependencies installed**:
   ```bash
   pip install pytest pytest-asyncio pytest-benchmark httpx k6
   ```

---

## Scenario 1: Performance Baseline Validation (User Story 1 - P1)

**Purpose**: Verify both servers meet constitutional performance targets.

**Acceptance Criteria**: spec.md lines 31-35

### Test Execution

```bash
# Run performance benchmarks
pytest tests/benchmarks/ -v --benchmark-only

# Compare against baseline
scripts/compare_baselines.py \
  --current performance_baselines/current.json \
  --baseline docs/performance/baseline-pre-split.json
```

### Expected Results

| Operation | Target (p95) | Baseline | Pass Criteria |
|-----------|--------------|----------|---------------|
| Indexing (10k files) | <60s | 48s | ≤60s AND within 10% of 48s (≤52.8s) |
| Search query | <500ms | 320ms | ≤500ms AND within 10% of 320ms (≤352ms) |
| Project switch | <50ms | 35ms | ≤50ms AND within 10% of 35ms (≤38.5ms) |
| Entity query | <100ms | 75ms | ≤100ms AND within 10% of 75ms (≤82.5ms) |

### Validation Commands

```python
# tests/benchmarks/test_indexing_perf.py
@pytest.mark.benchmark(group="indexing")
def test_indexing_10k_files_performance(benchmark, test_repository_10k):
    """Validate indexing meets <60s (p95) target."""
    result = benchmark.pedantic(
        index_repository,
        args=(test_repository_10k,),
        iterations=5,
        warmup_rounds=1
    )

    # Constitutional target
    assert result.stats.percentiles[95] < 60.0, \
        f"Indexing p95 {result.stats.percentiles[95]}s exceeds 60s target"

    # Baseline comparison (10% threshold)
    baseline_p95 = 48.0  # From docs/performance/baseline-pre-split.json
    max_acceptable = baseline_p95 * 1.1
    assert result.stats.percentiles[95] < max_acceptable, \
        f"Indexing p95 {result.stats.percentiles[95]}s exceeds baseline+10% ({max_acceptable}s)"
```

---

## Scenario 2: Cross-Server Integration Validation (User Story 2 - P1)

**Purpose**: Validate seamless workflows spanning both servers.

**Acceptance Criteria**: spec.md lines 49-54

### Test Execution

```bash
# Run cross-server integration tests
pytest tests/integration/test_cross_server_workflow.py -v
```

### Workflow Steps

1. **Search for code** (codebase-mcp):
   ```bash
   curl -X POST http://localhost:8020/mcp/search \
     -H "Content-Type: application/json" \
     -d '{"query": "authentication logic", "limit": 5}'
   ```

2. **Create work item with entity reference** (workflow-mcp):
   ```bash
   curl -X POST http://localhost:8010/mcp/work_items \
     -H "Content-Type: application/json" \
     -d '{
       "title": "Fix authentication bug",
       "entity_references": ["<chunk_id_from_search>"]
     }'
   ```

3. **Verify entity reference persisted**:
   ```bash
   curl -X GET http://localhost:8010/mcp/work_items/<work_item_id>
   ```

### Expected Results

- Search returns results with `chunk_id` field
- Work item created with status 201
- Work item retrieval shows `entity_references` array containing `chunk_id`
- Response times: search <500ms, work item creation <200ms

### Validation Code

```python
# tests/integration/test_cross_server_workflow.py
@pytest.mark.asyncio
async def test_search_to_work_item_workflow():
    """Validate cross-server workflow from search to work item creation."""
    async with httpx.AsyncClient() as client:
        # Step 1: Search code
        search_response = await client.post(
            "http://localhost:8020/mcp/search",
            json={"query": "authentication logic", "limit": 5},
            timeout=5.0
        )
        assert search_response.status_code == 200
        entities = search_response.json()["results"]
        assert len(entities) > 0, "Search returned no results"

        # Step 2: Create work item with entity reference
        work_item_response = await client.post(
            "http://localhost:8010/mcp/work_items",
            json={
                "title": "Fix authentication bug",
                "entity_references": [entities[0]["chunk_id"]]
            },
            timeout=5.0
        )
        assert work_item_response.status_code == 201
        work_item_id = work_item_response.json()["id"]

        # Step 3: Verify entity reference stored
        get_response = await client.get(
            f"http://localhost:8010/mcp/work_items/{work_item_id}",
            timeout=5.0
        )
        assert get_response.status_code == 200
        work_item = get_response.json()
        assert entities[0]["chunk_id"] in work_item["entity_references"]
```

---

## Scenario 3: Resilience and Failure Isolation (User Story 2 - P1)

**Purpose**: Validate servers operate independently when one fails.

**Acceptance Criteria**: spec.md lines 51-54

### Test Execution

```bash
# Run resilience tests
pytest tests/integration/test_resilience.py::test_server_failure_isolation -v
```

### Failure Scenarios

1. **Codebase-mcp unavailable**:
   ```python
   # Stop codebase-mcp
   # Workflow-mcp should continue operating normally
   async def test_workflow_continues_when_codebase_down():
       # Simulate codebase-mcp down
       with mock_server_unavailable("http://localhost:8020"):
           # Workflow operations should succeed
           response = await client.post(
               "http://localhost:8010/mcp/work_items",
               json={"title": "New task"}
           )
           assert response.status_code == 201

           # Messaging indicates code search unavailable
           assert "code_search_unavailable" in response.json().get("warnings", [])
   ```

2. **Workflow-mcp unavailable**:
   ```python
   # Stop workflow-mcp
   # Codebase-mcp should continue operating normally
   async def test_codebase_continues_when_workflow_down():
       # Simulate workflow-mcp down
       with mock_server_unavailable("http://localhost:8010"):
           # Code search should succeed
           response = await client.post(
               "http://localhost:8020/mcp/search",
               json={"query": "authentication"}
           )
           assert response.status_code == 200
           assert len(response.json()["results"]) > 0
   ```

3. **Stale entity reference handling**:
   ```python
   async def test_stale_entity_reference_handled_gracefully():
       # Create work item with entity reference
       work_item = await create_work_item_with_entity_ref(chunk_id="deleted-chunk")

       # Delete/re-index entity in codebase-mcp
       await delete_chunk("deleted-chunk")

       # Retrieve work item - should handle stale reference
       response = await client.get(f"/mcp/work_items/{work_item['id']}")
       assert response.status_code == 200

       # Entity reference marked as stale with clear messaging
       assert "stale_references" in response.json()
       assert "deleted-chunk" in response.json()["stale_references"]
   ```

### Expected Results

- Workflow operations succeed when codebase-mcp is down (with appropriate warnings)
- Code search succeeds when workflow-mcp is down
- Stale entity references handled gracefully with clear user messaging
- No cascading failures between servers

---

## Scenario 4: Load and Stress Testing (User Story 3 - P2)

**Purpose**: Verify servers handle high concurrent load without failure.

**Acceptance Criteria**: spec.md lines 67-72

### Test Execution

```bash
# Run k6 load tests
cd tests/load
k6 run k6_codebase_load.js --out json=codebase_load_results.json
k6 run k6_workflow_load.js --out json=workflow_load_results.json
```

### Load Test Configuration

```javascript
// tests/load/k6_codebase_load.js
export let options = {
  stages: [
    { duration: '2m', target: 10 },   // Ramp-up to 10 users
    { duration: '5m', target: 50 },   // Ramp-up to 50 users
    { duration: '10m', target: 50 },  // Sustained load
    { duration: '2m', target: 0 },    // Ramp-down
  ],
  thresholds: {
    'http_req_duration': ['p(95)<2000'],  // Graceful degradation: p95 <2s under extreme load
    'http_req_failed': ['rate<0.01'],     // Error rate <1%
  },
};

export default function () {
  let res = http.post('http://localhost:8020/mcp/search', JSON.stringify({
    query: 'function authentication',
    limit: 10
  }), {
    headers: { 'Content-Type': 'application/json' },
  });

  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time acceptable': (r) => r.timings.duration < 2000,
  });

  sleep(1);  // Pace requests
}
```

### Expected Results

| Metric | Target | Pass Criteria |
|--------|--------|---------------|
| Concurrent clients | 50 | Servers remain operational |
| p95 latency under load | <2000ms | Graceful degradation accepted |
| Error rate | <1% | 99% success rate maintained |
| Uptime during test | 99.9% | No crashes or unresponsiveness |
| Connection pool warnings | Logged when >80% | Warnings appear in structured logs |

### Validation Commands

```bash
# Check server uptime during load test
curl http://localhost:8020/health | jq '.uptime_seconds'

# Monitor connection pool utilization
curl http://localhost:8020/health | jq '.connection_pool.utilization_percent'

# Check error rates
curl http://localhost:8020/metrics | jq '.counters[] | select(.name=="codebase_mcp_errors_total")'
```

---

## Scenario 5: Database Resilience and Reconnection (User Story 4 - P2)

**Purpose**: Validate automatic recovery from database failures.

**Acceptance Criteria**: spec.md lines 85-89

### Test Execution

```bash
# Run database resilience tests
pytest tests/integration/test_resilience.py::test_database_reconnection -v
```

### Failure Simulation

```python
# tests/integration/test_resilience.py
@pytest.mark.asyncio
async def test_database_reconnection_after_failure(mocker):
    """Validate server detects DB failure within 5s and reconnects automatically."""

    # Step 1: Simulate database connection failure
    mock_pool = mocker.patch('src.connection_pool.manager.ConnectionPoolManager.acquire')
    mock_pool.side_effect = asyncpg.exceptions.ConnectionDoesNotExistError()

    # Step 2: Trigger database operation
    start_time = time.time()
    with pytest.raises(DatabaseConnectionError) as exc_info:
        await indexer_service.index_repository("/test/repo")

    # Validate failure detected within 5 seconds (FR-008)
    detection_time = time.time() - start_time
    assert detection_time < 5.0, f"Failure detection took {detection_time}s, exceeds 5s limit"

    # Validate error logged with context
    log_file = Path("/tmp/codebase-mcp.log")
    logs = json.loads(log_file.read_text())
    assert any(
        log["error"] == "database_connection_lost" and
        log["context"]["detection_time_seconds"] < 5.0
        for log in logs
    )

    # Step 3: Simulate connection restoration
    mock_pool.side_effect = None

    # Step 4: Verify automatic reconnection with exponential backoff
    await asyncio.sleep(2.0)  # Wait for retry with backoff (max 3 retries)

    result = await indexer_service.index_repository("/test/repo")
    assert result.status == "success", "Reconnection failed after DB restored"

    # Validate reconnection logged
    reconnection_logs = [log for log in logs if log.get("event") == "database_reconnected"]
    assert len(reconnection_logs) > 0, "Reconnection event not logged"
```

### Expected Results

- Database failure detected within 5 seconds (FR-008)
- Automatic reconnection with exponential backoff (max 3 retries)
- Operations resume from checkpoints after reconnection (no data loss)
- Structured logs include failure detection time and retry attempts
- Health check returns "unhealthy" status during disconnection

---

## Scenario 6: Observability and Health Monitoring (User Story 5 - P3)

**Purpose**: Validate health check and metrics endpoints provide comprehensive observability.

**Acceptance Criteria**: spec.md lines 103-107

### Test Execution

```bash
# Run observability tests
pytest tests/integration/test_observability.py -v
```

### Health Check Validation

```python
@pytest.mark.asyncio
async def test_health_check_response_time():
    """Validate health check responds within 50ms."""
    async with httpx.AsyncClient() as client:
        start_time = time.time()
        response = await client.get("http://localhost:8020/health")
        elapsed_ms = (time.time() - start_time) * 1000

        assert response.status_code == 200
        assert elapsed_ms < 50.0, f"Health check took {elapsed_ms}ms, exceeds 50ms limit"

        # Validate response structure
        data = response.json()
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
        assert "database_status" in data
        assert "connection_pool" in data
        assert "uptime_seconds" in data
```

### Metrics Validation

```python
@pytest.mark.asyncio
async def test_metrics_prometheus_format():
    """Validate metrics endpoint returns Prometheus-compatible format."""
    async with httpx.AsyncClient() as client:
        # Test JSON format
        json_response = await client.get(
            "http://localhost:8020/metrics",
            headers={"Accept": "application/json"}
        )
        assert json_response.status_code == 200
        metrics = json_response.json()

        # Validate counters
        assert "counters" in metrics
        assert any(c["name"] == "codebase_mcp_requests_total" for c in metrics["counters"])

        # Validate histograms
        assert "histograms" in metrics
        search_histogram = next(
            h for h in metrics["histograms"]
            if h["name"] == "codebase_mcp_search_latency_seconds"
        )
        assert len(search_histogram["buckets"]) > 0
        assert search_histogram["count"] > 0

        # Test Prometheus text format
        text_response = await client.get(
            "http://localhost:8020/metrics",
            headers={"Accept": "text/plain"}
        )
        assert text_response.status_code == 200
        assert "# HELP codebase_mcp_requests_total" in text_response.text
        assert "# TYPE codebase_mcp_requests_total counter" in text_response.text
```

### Structured Logging Validation

```python
def test_structured_logging_format():
    """Validate logs are structured JSON with required fields."""
    log_file = Path("/tmp/codebase-mcp.log")
    logs = [json.loads(line) for line in log_file.read_text().splitlines()]

    for log_entry in logs:
        # Validate required fields
        assert "timestamp" in log_entry
        assert "level" in log_entry
        assert "event" in log_entry

        # Validate timestamp format (ISO 8601)
        datetime.fromisoformat(log_entry["timestamp"])

        # Validate level is valid
        assert log_entry["level"] in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
```

### Expected Results

- Health check responds within 50ms
- Metrics endpoint responds within 100ms
- Prometheus text format is valid and parseable
- Structured logs contain all required fields (timestamp, level, event, context)
- Performance warnings logged when queries exceed 1s
- Connection pool warnings logged when utilization exceeds 80%

---

## Running All Scenarios

### Complete Test Suite

```bash
# Run all integration tests
pytest tests/ -v -m "integration or performance or contract"

# Generate coverage report
pytest tests/ --cov=src --cov-report=html

# Generate performance comparison report
scripts/validate_performance.sh \
  --baseline docs/performance/baseline-pre-split.json \
  --output docs/performance/validation-report.md
```

### Success Criteria Checklist

- [ ] All performance benchmarks pass (p95 within targets and baseline+10%)
- [ ] Cross-server workflows succeed with entity references
- [ ] Server failures remain isolated (no cascading failures)
- [ ] Load testing succeeds with 50 concurrent clients
- [ ] Database reconnection occurs within 10 seconds
- [ ] Health check responds within 50ms
- [ ] Metrics endpoint provides complete observability
- [ ] Structured logs contain all required fields
- [ ] Test coverage exceeds 95% for new code

---

## Troubleshooting

### Servers Won't Start

```bash
# Check if ports are in use
lsof -i :8020
lsof -i :8010

# Check database connectivity
psql -h localhost -d codebase_mcp -c "SELECT 1"
psql -h localhost -d workflow_mcp -c "SELECT 1"

# Check logs
tail -f /tmp/codebase-mcp.log
```

### Performance Tests Failing

```bash
# Verify test repository size
du -sh test_repos/test_repo_10k
find test_repos/test_repo_10k -type f | wc -l  # Should be 10000

# Check database is clean
psql -h localhost -d codebase_mcp -c "DELETE FROM chunks; DELETE FROM repositories;"

# Run benchmarks with verbose output
pytest tests/benchmarks/test_indexing_perf.py -v -s --benchmark-verbose
```

### Load Tests Failing

```bash
# Check k6 installation
k6 version

# Run load test with reduced concurrency for debugging
k6 run k6_codebase_load.js --vus 10 --duration 30s

# Monitor connection pool during load test
watch -n 1 'curl -s http://localhost:8020/health | jq .connection_pool'
```

---

## Next Steps

After completing these scenarios:

1. Review `docs/performance/validation-report.md` for performance comparison
2. Analyze load test results for capacity planning
3. Address any performance regressions exceeding 10% degradation
4. Document operational runbooks in `docs/operations/`
5. Prepare Phase 06 completion summary

---

## References

- **Feature Specification**: `specs/011-performance-validation-multi/spec.md`
- **Data Models**: `specs/011-performance-validation-multi/data-model.md`
- **API Contracts**: `specs/011-performance-validation-multi/contracts/`
- **Constitutional Targets**: `.specify/memory/constitution.md` (Principle IV)
