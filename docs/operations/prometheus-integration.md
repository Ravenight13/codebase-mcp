# Prometheus Integration Guide

**Version**: 1.0.0
**Last Updated**: 2025-10-13
**Feature**: 011-performance-validation-multi
**Phase**: 7 - User Story 5
**Tasks**: T040, T042, T045, T049
**Constitutional Compliance**: Principle V (Production Quality)
**Success Criteria**: SC-010

## Overview

This guide provides comprehensive instructions for integrating the MCP servers with Prometheus for metrics collection, monitoring, and alerting. The system exposes metrics in both JSON and Prometheus text exposition format through dedicated endpoints.

## Metrics Endpoint

### Endpoint Details

**URL**: `metrics://prometheus`
**Protocol**: MCP Resource (via SSE)
**Formats**: JSON and Prometheus text exposition
**Update Frequency**: Real-time (counters and histograms)

### FastMCP Resource Registration

```python
@mcp.resource("metrics://prometheus")
async def metrics_endpoint(format: str = "prometheus") -> str | MetricsResponse:
    """Metrics endpoint supporting both JSON and Prometheus formats."""
    if format == "json":
        return await metrics_service.get_metrics_json()
    else:
        return await metrics_service.get_metrics_prometheus()
```

## Metrics Types and Structure

### Available Metrics

#### Counters (Monotonically Increasing)
```prometheus
# TYPE codebase_mcp_requests_total counter
# HELP codebase_mcp_requests_total Total number of requests processed
codebase_mcp_requests_total{method="search",status="success"} 12543
codebase_mcp_requests_total{method="search",status="error"} 23
codebase_mcp_requests_total{method="index",status="success"} 89

# TYPE codebase_mcp_errors_total counter
# HELP codebase_mcp_errors_total Total number of errors by type
codebase_mcp_errors_total{type="database",severity="error"} 5
codebase_mcp_errors_total{type="timeout",severity="warning"} 12

# TYPE codebase_mcp_connections_total counter
# HELP codebase_mcp_connections_total Total database connections created
codebase_mcp_connections_total 156
```

#### Histograms (Latency Distributions)
```prometheus
# TYPE codebase_mcp_request_duration_seconds histogram
# HELP codebase_mcp_request_duration_seconds Request duration in seconds
codebase_mcp_request_duration_seconds_bucket{le="0.005"} 1203
codebase_mcp_request_duration_seconds_bucket{le="0.01"} 2456
codebase_mcp_request_duration_seconds_bucket{le="0.025"} 5678
codebase_mcp_request_duration_seconds_bucket{le="0.05"} 8901
codebase_mcp_request_duration_seconds_bucket{le="0.1"} 10234
codebase_mcp_request_duration_seconds_bucket{le="0.25"} 11456
codebase_mcp_request_duration_seconds_bucket{le="0.5"} 12123
codebase_mcp_request_duration_seconds_bucket{le="1.0"} 12456
codebase_mcp_request_duration_seconds_bucket{le="+Inf"} 12543
codebase_mcp_request_duration_seconds_sum 234.567
codebase_mcp_request_duration_seconds_count 12543

# TYPE codebase_mcp_embedding_generation_seconds histogram
# HELP codebase_mcp_embedding_generation_seconds Embedding generation time
codebase_mcp_embedding_generation_seconds_bucket{le="0.1"} 45
codebase_mcp_embedding_generation_seconds_bucket{le="0.5"} 234
codebase_mcp_embedding_generation_seconds_bucket{le="1.0"} 456
codebase_mcp_embedding_generation_seconds_bucket{le="2.0"} 567
codebase_mcp_embedding_generation_seconds_bucket{le="5.0"} 589
codebase_mcp_embedding_generation_seconds_bucket{le="+Inf"} 590
codebase_mcp_embedding_generation_seconds_sum 456.789
codebase_mcp_embedding_generation_seconds_count 590
```

#### Gauges (Current Values)
```prometheus
# TYPE codebase_mcp_pool_connections gauge
# HELP codebase_mcp_pool_connections Current connection pool state
codebase_mcp_pool_connections{state="active"} 12
codebase_mcp_pool_connections{state="idle"} 38
codebase_mcp_pool_connections{state="total"} 50

# TYPE codebase_mcp_memory_usage_bytes gauge
# HELP codebase_mcp_memory_usage_bytes Current memory usage in bytes
codebase_mcp_memory_usage_bytes 523456789

# TYPE codebase_mcp_uptime_seconds gauge
# HELP codebase_mcp_uptime_seconds Server uptime in seconds
codebase_mcp_uptime_seconds 86432.5
```

### JSON Format Response

```json
{
  "timestamp": "2025-10-13T10:30:45.123Z",
  "counters": [
    {
      "name": "codebase_mcp_requests_total",
      "help_text": "Total number of requests processed",
      "value": 12543,
      "labels": {"method": "search", "status": "success"}
    }
  ],
  "histograms": [
    {
      "name": "codebase_mcp_request_duration_seconds",
      "help_text": "Request duration in seconds",
      "buckets": [
        {"le": 0.005, "count": 1203},
        {"le": 0.01, "count": 2456},
        {"le": 0.025, "count": 5678}
      ],
      "sum": 234.567,
      "count": 12543
    }
  ],
  "gauges": [
    {
      "name": "codebase_mcp_pool_connections",
      "help_text": "Current connection pool state",
      "value": 12,
      "labels": {"state": "active"}
    }
  ]
}
```

## Prometheus Configuration

### 1. Scraping Configuration

Add to `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'codebase-mcp'
    static_configs:
      - targets: ['codebase-mcp:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s
    scrape_timeout: 5s
    params:
      format: ['prometheus']

  - job_name: 'workflow-mcp'
    static_configs:
      - targets: ['workflow-mcp:8001']
    metrics_path: '/metrics'
    scrape_interval: 10s
    scrape_timeout: 5s
    params:
      format: ['prometheus']

  # High-frequency metrics for critical paths
  - job_name: 'codebase-mcp-critical'
    static_configs:
      - targets: ['codebase-mcp:8000']
    metrics_path: '/metrics'
    scrape_interval: 5s
    metric_relabel_configs:
      - source_labels: [__name__]
        regex: '(.*request_duration.*|.*pool_connections.*)'
        action: keep
```

### 2. Service Discovery Configuration

For Kubernetes environments:

```yaml
scrape_configs:
  - job_name: 'mcp-servers-k8s'
    kubernetes_sd_configs:
      - role: pod
        namespaces:
          names: ['mcp-namespace']
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
      - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
        action: replace
        regex: ([^:]+)(?::\d+)?;(\d+)
        replacement: $1:$2
        target_label: __address__
      - action: labelmap
        regex: __meta_kubernetes_pod_label_(.+)
      - source_labels: [__meta_kubernetes_namespace]
        action: replace
        target_label: kubernetes_namespace
      - source_labels: [__meta_kubernetes_pod_name]
        action: replace
        target_label: kubernetes_pod_name
```

## Alert Rules

### 1. Critical Alerts

```yaml
groups:
  - name: mcp_critical
    interval: 30s
    rules:
      - alert: MCPServerDown
        expr: up{job=~".*mcp.*"} == 0
        for: 1m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "MCP server {{ $labels.instance }} is down"
          description: "Server has been unreachable for >1 minute"
          runbook: "https://docs/runbooks/mcp-server-down"

      - alert: MCPHighErrorRate
        expr: |
          rate(codebase_mcp_errors_total[5m]) > 0.05
        for: 2m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }}"
          runbook: "https://docs/runbooks/high-error-rate"

      - alert: MCPPoolExhausted
        expr: |
          codebase_mcp_pool_connections{state="active"} /
          codebase_mcp_pool_connections{state="total"} > 0.95
        for: 30s
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "Connection pool nearly exhausted"
          description: "Pool utilization is {{ $value | humanizePercentage }}"
          runbook: "https://docs/runbooks/pool-exhausted"
```

### 2. Warning Alerts

```yaml
  - name: mcp_warnings
    interval: 60s
    rules:
      - alert: MCPHighLatency
        expr: |
          histogram_quantile(0.95,
            rate(codebase_mcp_request_duration_seconds_bucket[5m])
          ) > 0.5
        for: 5m
        labels:
          severity: warning
          team: platform
        annotations:
          summary: "High p95 latency"
          description: "P95 latency is {{ $value }}s (threshold: 0.5s)"
          runbook: "https://docs/runbooks/high-latency"

      - alert: MCPMemoryHigh
        expr: |
          codebase_mcp_memory_usage_bytes / (2 * 1024 * 1024 * 1024) > 0.8
        for: 10m
        labels:
          severity: warning
          team: platform
        annotations:
          summary: "High memory usage"
          description: "Memory usage is {{ $value | humanizePercentage }} of limit"

      - alert: MCPSlowEmbedding
        expr: |
          histogram_quantile(0.95,
            rate(codebase_mcp_embedding_generation_seconds_bucket[5m])
          ) > 2.0
        for: 5m
        labels:
          severity: warning
          team: platform
        annotations:
          summary: "Slow embedding generation"
          description: "P95 embedding time is {{ $value }}s"
```

### 3. SLA Alerts

```yaml
  - name: mcp_sla
    interval: 60s
    rules:
      - alert: MCPIndexingSLAViolation
        expr: |
          histogram_quantile(0.95,
            rate(codebase_mcp_indexing_duration_seconds_bucket[10m])
          ) > 60
        for: 10m
        labels:
          severity: warning
          sla: true
          team: platform
        annotations:
          summary: "Indexing SLA violation"
          description: "P95 indexing time {{ $value }}s exceeds 60s SLA"
          impact: "Repository indexing may timeout"

      - alert: MCPSearchSLAViolation
        expr: |
          histogram_quantile(0.95,
            rate(codebase_mcp_search_duration_seconds_bucket[10m])
          ) > 0.5
        for: 10m
        labels:
          severity: warning
          sla: true
          team: platform
        annotations:
          summary: "Search SLA violation"
          description: "P95 search time {{ $value }}s exceeds 500ms SLA"
          impact: "User search experience degraded"
```

## Dashboard Recommendations

### 1. Grafana Dashboard Configuration

```json
{
  "dashboard": {
    "title": "MCP Metrics Overview",
    "uid": "mcp-overview",
    "tags": ["mcp", "performance"],
    "panels": [
      {
        "id": 1,
        "title": "Request Rate",
        "type": "graph",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
        "targets": [{
          "expr": "rate(codebase_mcp_requests_total[5m])",
          "legendFormat": "{{method}} - {{status}}"
        }]
      },
      {
        "id": 2,
        "title": "P95 Latency",
        "type": "graph",
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
        "targets": [{
          "expr": "histogram_quantile(0.95, rate(codebase_mcp_request_duration_seconds_bucket[5m]))",
          "legendFormat": "P95 Latency"
        }],
        "yaxes": [{"format": "s"}]
      },
      {
        "id": 3,
        "title": "Connection Pool Usage",
        "type": "graph",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
        "targets": [
          {
            "expr": "codebase_mcp_pool_connections{state='active'}",
            "legendFormat": "Active"
          },
          {
            "expr": "codebase_mcp_pool_connections{state='idle'}",
            "legendFormat": "Idle"
          }
        ],
        "stack": true
      },
      {
        "id": 4,
        "title": "Error Rate",
        "type": "graph",
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
        "targets": [{
          "expr": "rate(codebase_mcp_errors_total[5m])",
          "legendFormat": "{{type}} - {{severity}}"
        }]
      },
      {
        "id": 5,
        "title": "Memory Usage",
        "type": "stat",
        "gridPos": {"h": 4, "w": 6, "x": 0, "y": 16},
        "targets": [{
          "expr": "codebase_mcp_memory_usage_bytes / (1024 * 1024)",
          "legendFormat": "Memory (MB)"
        }],
        "unit": "MB"
      },
      {
        "id": 6,
        "title": "Uptime",
        "type": "stat",
        "gridPos": {"h": 4, "w": 6, "x": 6, "y": 16},
        "targets": [{
          "expr": "codebase_mcp_uptime_seconds / 3600",
          "legendFormat": "Uptime (hours)"
        }],
        "unit": "hours"
      }
    ]
  }
}
```

### 2. Key Metrics to Monitor

#### Performance Metrics
- **Request rate**: `rate(codebase_mcp_requests_total[5m])`
- **P50/P95/P99 latencies**: `histogram_quantile(0.X, rate(request_duration_seconds_bucket[5m]))`
- **Error rate**: `rate(codebase_mcp_errors_total[5m])`
- **Success rate**: `rate(requests_total{status="success"}[5m]) / rate(requests_total[5m])`

#### Resource Metrics
- **Pool utilization**: `pool_connections{state="active"} / pool_connections{state="total"}`
- **Memory usage**: `memory_usage_bytes / (2 * 1024 * 1024 * 1024)`
- **CPU usage**: `rate(process_cpu_seconds_total[5m])`
- **Open file descriptors**: `process_open_fds`

#### Business Metrics
- **Indexing throughput**: `rate(files_indexed_total[5m])`
- **Search volume**: `rate(searches_performed_total[5m])`
- **Embedding generation rate**: `rate(embeddings_generated_total[5m])`

## Production Setup

### 1. High Availability Configuration

```yaml
# prometheus-ha.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    replica: '$(REPLICA)'  # A or B for HA pair

alerting:
  alert_relabel_configs:
    - source_labels: [replica]
      regex: 'B'
      action: drop  # Only one replica sends alerts

remote_write:
  - url: "http://thanos-receiver:10908/api/v1/receive"
    queue_config:
      capacity: 10000
      max_shards: 100
      max_samples_per_send: 5000

remote_read:
  - url: "http://thanos-querier:10901/api/v1/query"
    read_recent: true
```

### 2. Storage and Retention

```yaml
# Storage configuration
storage:
  tsdb:
    path: /prometheus/data
    retention.time: 30d
    retention.size: 50GB
    wal_compression: true

  # Chunk settings for better performance
  chunks:
    min_block_duration: 2h
    max_block_duration: 2h
    target_heap_size: 1GB
```

### 3. Recording Rules for Performance

```yaml
groups:
  - name: mcp_aggregations
    interval: 30s
    rules:
      # Pre-calculate p95 latencies
      - record: mcp:request_duration:p95:5m
        expr: |
          histogram_quantile(0.95,
            sum(rate(codebase_mcp_request_duration_seconds_bucket[5m])) by (le, job)
          )

      # Pre-calculate request rates
      - record: mcp:request_rate:5m
        expr: |
          sum(rate(codebase_mcp_requests_total[5m])) by (job, method, status)

      # Pre-calculate error rates
      - record: mcp:error_rate:5m
        expr: |
          sum(rate(codebase_mcp_errors_total[5m])) by (job, type, severity)

      # Pool utilization
      - record: mcp:pool_utilization:instant
        expr: |
          codebase_mcp_pool_connections{state="active"} /
          codebase_mcp_pool_connections{state="total"}
```

## Integration Testing

### 1. Verify Metrics Endpoint

```bash
# Test Prometheus format
curl -s http://localhost:8000/metrics?format=prometheus | head -20

# Test JSON format
curl -s http://localhost:8000/metrics?format=json | jq '.counters[0]'

# Verify specific metrics exist
curl -s http://localhost:8000/metrics | grep -E "codebase_mcp_requests_total"
```

### 2. Prometheus Validation

```bash
# Check Prometheus targets
curl -s http://prometheus:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job | contains("mcp"))'

# Query metrics
curl -G http://prometheus:9090/api/v1/query \
  --data-urlencode 'query=codebase_mcp_requests_total' | jq '.'

# Check metric ingestion rate
curl -G http://prometheus:9090/api/v1/query \
  --data-urlencode 'query=prometheus_tsdb_samples_appended_total' | jq '.'
```

### 3. Alert Testing

```bash
# Trigger test alert
curl -X POST http://prometheus:9090/-/reload

# Check pending alerts
curl -s http://prometheus:9090/api/v1/alerts | jq '.data.alerts[] | select(.state=="pending")'

# Verify alertmanager received alert
curl -s http://alertmanager:9093/api/v1/alerts | jq '.[].labels'
```

## Troubleshooting

### Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| No metrics appearing | Scrape config error | Check prometheus.yml, verify targets |
| High cardinality warnings | Too many label combinations | Reduce label dimensions |
| Slow queries | Missing recording rules | Add pre-aggregation rules |
| Storage full | Retention too long | Reduce retention or add storage |
| Missing metrics | Server not exposing | Check /metrics endpoint |

### Debug Commands

```bash
# Check Prometheus configuration
promtool check config prometheus.yml

# Validate rules
promtool check rules rules.yml

# Test metric query
promtool query instant http://localhost:9090 'up{job="codebase-mcp"}'

# Check TSDB stats
curl -s http://prometheus:9090/api/v1/status/tsdb | jq '.'

# View metric metadata
curl -s http://localhost:8000/metrics | grep "^# HELP"
```

## Best Practices

### 1. Metric Naming
- Use standard Prometheus conventions
- Include unit in name (_seconds, _bytes, _total)
- Use consistent prefixes (codebase_mcp_)
- Keep cardinality under control

### 2. Label Usage
- Use static labels for dimensions
- Avoid high-cardinality labels (IDs, timestamps)
- Be consistent across metrics
- Document label meanings

### 3. Performance Optimization
- Use recording rules for complex queries
- Implement histogram buckets appropriately
- Batch metric updates
- Use metric caching where appropriate

### 4. Monitoring the Monitor
- Monitor Prometheus health
- Track ingestion rate
- Watch storage usage
- Alert on scrape failures

## References

- [Metrics Service Implementation](../../src/services/metrics_service.py)
- [MetricsResponse Model](../../src/models/metrics.py)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Dashboard Examples](https://grafana.com/grafana/dashboards/)
- [Health Monitoring Guide](health-monitoring.md)
- [Incident Response Runbook](incident-response.md)