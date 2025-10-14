# API Contracts: Performance Validation & Multi-Tenant Testing

**Feature**: 011-performance-validation-multi
**Phase**: 1 (Design & Contracts)

## Overview

This directory contains OpenAPI 3.1.0 specifications for health check and metrics endpoints required for Phase 06 performance validation and observability.

## Contract Files

### health-endpoint.yaml

**Purpose**: Health check endpoint specification for both codebase-mcp and workflow-mcp servers.

**Endpoint**: `GET /health`

**Response Time Target**: <50ms (p95) per FR-011

**Key Features**:
- Overall health status (healthy/degraded/unhealthy)
- Database connectivity status
- Connection pool statistics with utilization percentage
- Server uptime
- Optional details for degraded/unhealthy states

**Status Determination**:
- **Healthy**: Database connected, pool utilization <80%, no errors
- **Degraded**: Database connected but slow (queries >1s) OR pool utilization >80%
- **Unhealthy**: Database disconnected OR pool exhausted

**Constitutional Compliance**:
- Principle V: Production quality health monitoring
- FR-011: <50ms response time, detailed status information

---

### metrics-endpoint.yaml

**Purpose**: Prometheus-compatible metrics endpoint for observability and performance monitoring.

**Endpoint**: `GET /metrics`

**Response Time Target**: <100ms (does not impact main operations)

**Supported Formats**:
- `application/json` - Structured JSON response
- `text/plain` - Prometheus text exposition format

**Metric Types**:
1. **Counters**: Monotonically increasing values (requests, errors, operations)
2. **Histograms**: Latency distributions with percentile buckets

**Key Metrics**:
- `{server}_requests_total` - Total request count
- `{server}_errors_total` - Total error count
- `{server}_search_latency_seconds` - Search latency histogram (codebase-mcp)
- `{server}_indexing_duration_seconds` - Indexing duration histogram (codebase-mcp)
- `{server}_project_switch_latency_seconds` - Project switch latency (workflow-mcp)
- `{server}_entity_query_latency_seconds` - Entity query latency (workflow-mcp)

**Constitutional Performance Targets** (encoded in histogram buckets):
- Search latency: p95 < 500ms (0.5s)
- Indexing duration: p95 < 60s
- Project switching: p95 < 50ms (0.05s)
- Entity queries: p95 < 100ms (0.1s)

**Constitutional Compliance**:
- Principle V: Production quality observability
- FR-012: Prometheus-compatible format
- FR-014: Performance warnings logged when thresholds exceeded

---

## Usage Examples

### Health Check (cURL)

```bash
# Codebase-MCP health check
curl -X GET http://localhost:8020/health

# Workflow-MCP health check (hypothetical for Phase 06)
curl -X GET http://localhost:8010/health

# Example response
{
  "status": "healthy",
  "timestamp": "2025-10-13T10:30:00Z",
  "database_status": "connected",
  "connection_pool": {
    "size": 8,
    "min_size": 5,
    "max_size": 20,
    "free": 6,
    "utilization_percent": 25.00
  },
  "uptime_seconds": 3600.50,
  "details": null
}
```

### Metrics (cURL)

```bash
# Get metrics in JSON format
curl -X GET http://localhost:8020/metrics \
  -H "Accept: application/json"

# Get metrics in Prometheus text format
curl -X GET http://localhost:8020/metrics \
  -H "Accept: text/plain"

# Example JSON response (excerpt)
{
  "counters": [
    {
      "name": "codebase_mcp_requests_total",
      "help_text": "Total number of requests",
      "value": 10000
    }
  ],
  "histograms": [
    {
      "name": "codebase_mcp_search_latency_seconds",
      "help_text": "Search query latency",
      "buckets": [
        {"bucket_le": 0.1, "count": 450},
        {"bucket_le": 0.5, "count": 9500},
        {"bucket_le": 1.0, "count": 9950}
      ],
      "count": 10000,
      "sum": 2345.67
    }
  ]
}
```

### Prometheus Scraping Configuration

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'codebase-mcp'
    static_configs:
      - targets: ['localhost:8020']
    metrics_path: '/metrics'
    scrape_interval: 15s

  - job_name: 'workflow-mcp'
    static_configs:
      - targets: ['localhost:8010']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

---

## Integration Testing

These contracts are used by integration tests in `tests/integration/test_observability.py`:

```python
@pytest.mark.asyncio
async def test_health_check_response_schema():
    """Validate health check response matches OpenAPI schema."""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8020/health")

        assert response.status_code == 200
        data = response.json()

        # Validate required fields
        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
        assert "timestamp" in data
        assert "database_status" in data
        assert "connection_pool" in data
        assert "uptime_seconds" in data

        # Validate connection pool structure
        pool = data["connection_pool"]
        assert "size" in pool
        assert "min_size" in pool
        assert "max_size" in pool
        assert "free" in pool
        assert "utilization_percent" in pool

        # Validate response time
        assert response.elapsed.total_seconds() < 0.05  # <50ms
```

---

## Validation

OpenAPI schemas can be validated using:

```bash
# Install openapi-spec-validator
pip install openapi-spec-validator

# Validate schemas
openapi-spec-validator contracts/health-endpoint.yaml
openapi-spec-validator contracts/metrics-endpoint.yaml
```

---

## Implementation Checklist

- [ ] Implement health check endpoint in `src/mcp/server_fastmcp.py`
- [ ] Implement metrics endpoint in `src/mcp/server_fastmcp.py`
- [ ] Create Pydantic models in `src/models/health.py` and `src/models/metrics.py`
- [ ] Add health check to FastMCP resource registration (`@mcp.resource("health://status")`)
- [ ] Add metrics to FastMCP resource registration (`@mcp.resource("metrics://prometheus")`)
- [ ] Write integration tests validating contract compliance
- [ ] Validate <50ms response time for health checks
- [ ] Validate <100ms response time for metrics
- [ ] Test Prometheus scraping integration (manual validation)

---

## Future Enhancements (Out of Scope for Phase 06)

1. **Grafana Dashboards**: Pre-built dashboards for metrics visualization
2. **Alerting Rules**: Prometheus alerting for threshold violations
3. **Distributed Tracing**: OpenTelemetry integration for request tracing
4. **Custom Metrics**: User-defined metrics via configuration
5. **Metrics Persistence**: Historical metrics storage in TimeSeries DB

---

## References

- **OpenAPI 3.1.0 Specification**: https://spec.openapis.org/oas/v3.1.0
- **Prometheus Exposition Format**: https://prometheus.io/docs/instrumenting/exposition_formats/
- **Constitutional Principles**: `.specify/memory/constitution.md`
- **Feature Specification**: `specs/011-performance-validation-multi/spec.md`
- **Data Models**: `specs/011-performance-validation-multi/data-model.md`
