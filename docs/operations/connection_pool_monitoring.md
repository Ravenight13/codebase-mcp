# Connection Pool Monitoring Guide

**Version**: 2.0 | **Feature**: 009-v2-connection-mgmt | **Last Updated**: 2025-10-13

## Overview

This guide provides comprehensive monitoring and troubleshooting documentation for the Codebase MCP Server connection pool. The connection pool manages PostgreSQL connections with automatic health detection, leak prevention, and real-time statistics for production observability.

**Key Monitoring Capabilities**:
- Real-time pool statistics via internal API
- Three-tier health status system (HEALTHY → DEGRADED → UNHEALTHY)
- Connection leak detection with configurable timeouts
- Performance metrics (acquisition times, wait times, peak usage)
- MCP resource endpoint for health monitoring

**Target Audience**: System administrators, SREs, and developers operating the MCP server in production or development environments.

---

## Health Status States

The connection pool uses a three-tier health status system that provides clear operational signals:

### Health Status Definitions

#### HEALTHY
**Definition**: Pool is operating at full capacity with no issues.

**Conditions**:
- `total_connections > 0`
- `idle_connections ≥ 80%` of `total_connections`
- No errors in the last 60 seconds
- Peak wait time `< 100ms`

**Expected Behavior**:
- All connection acquisitions succeed immediately (< 10ms p95)
- Database queries execute without queuing
- Pool maintains minimum size (default: 2 connections)

**Operator Action**: None required. System is operating normally.

---

#### DEGRADED
**Definition**: Pool is functional but experiencing reduced capacity or intermittent issues.

**Conditions**:
- `total_connections > 0`
- `idle_connections` is 50-79% of `total_connections`
- OR recent errors occurred (within last 60 seconds)
- OR peak wait time `> 100ms`

**Expected Behavior**:
- Connection acquisitions may queue briefly
- Database queries succeed but with increased latency
- Pool may be recovering from transient failure
- Automatic recovery attempts in progress

**Operator Action**:
1. Monitor for automatic recovery (typically 30-60 seconds)
2. Check database logs for connection errors
3. Review application query patterns for slow queries
4. Consider increasing `POOL_MAX_SIZE` if sustained high load

---

#### UNHEALTHY
**Definition**: Pool cannot serve requests due to critical failure.

**Conditions**:
- `total_connections == 0` (no connections available)
- OR `idle_connections < 50%` of `total_connections` (severe capacity shortage)
- OR pool initialization failed

**Expected Behavior**:
- Connection acquisition attempts timeout after 30 seconds
- Database queries return `DATABASE_ERROR` responses
- Automatic reconnection with exponential backoff (1s, 2s, 4s, 8s, 16s)
- Pool transitions to `RECOVERING` state during reconnection attempts

**Operator Action**:
1. **Immediate**: Check database server is running: `docker ps` or `systemctl status postgresql`
2. Verify network connectivity: `ping <database_host>`
3. Review server logs: `tail -f /tmp/codebase-mcp.log`
4. Check for database outage or maintenance window
5. If database is healthy, restart MCP server to reinitialize pool

---

### State Transitions

The connection pool lifecycle follows these state transitions:

```
INITIALIZING → HEALTHY → DEGRADED → UNHEALTHY → RECOVERING → HEALTHY
      ↓                                                           ↓
      └──────────────────→ SHUTTING_DOWN → TERMINATED ←──────────┘
```

**State Flow Details**:

1. **INITIALIZING → HEALTHY**
   - Trigger: Pool successfully creates `min_size` connections (default: 2)
   - Duration: < 2 seconds (p95 per SC-001)
   - Validation: Each connection executes `SELECT 1` query

2. **HEALTHY → DEGRADED**
   - Trigger: Some connections fail validation OR idle capacity drops to 50-79%
   - Recovery: Automatic reconnection attempts OR load decreases

3. **DEGRADED → UNHEALTHY**
   - Trigger: Idle capacity drops below 50% OR all connections lost
   - Impact: New requests begin timing out

4. **UNHEALTHY → RECOVERING**
   - Trigger: Reconnection attempt initiated
   - Backoff schedule: 1s, 2s, 4s, 8s, 16s (max 5 initial attempts)
   - Continued attempts: Every 16s after initial sequence

5. **RECOVERING → HEALTHY**
   - Trigger: Successfully created `min_size` connections
   - Duration: < 30 seconds (p95 per SC-004)
   - Validation: All new connections pass validation queries

6. **ANY → SHUTTING_DOWN → TERMINATED**
   - Trigger: Graceful shutdown signal (SIGTERM/SIGINT)
   - Behavior: Waits up to 30 seconds for active queries to complete
   - Cleanup: All connections closed, resources released

---

## Pool Statistics Reference

The `PoolStatistics` model provides real-time metrics for capacity planning and troubleshooting:

### Real-Time Metrics

#### `total_connections` (integer, ≥ 0)
**Description**: Current total number of connections managed by the pool.

**Expected Values**:
- Minimum: `min_size` (default: 2)
- Maximum: `max_size` (default: 10)
- Typical: Between `min_size` and `max_size` based on load

**Interpretation**:
- `total_connections == min_size`: Pool at idle capacity
- `total_connections > min_size`: Pool scaled up to handle load
- `total_connections == max_size`: Pool at maximum capacity
- `total_connections == 0`: **CRITICAL** - pool has no connections (UNHEALTHY state)

**Alerting Threshold**: Alert if `total_connections == 0` for > 30 seconds

---

#### `idle_connections` (integer, ≥ 0)
**Description**: Number of connections available for immediate use.

**Expected Values**:
- Healthy: ≥ 80% of `total_connections`
- Degraded: 50-79% of `total_connections`
- Unhealthy: < 50% of `total_connections`

**Interpretation**:
- High idle count: Pool has spare capacity
- Low idle count: Pool under heavy load
- Zero idle connections: All connections in use, new requests will queue

**Alerting Threshold**: Alert if `idle_connections < 50%` of `total_connections` for > 5 minutes

**Calculation**: `idle_connections = total_connections - active_connections`

---

#### `active_connections` (integer, ≥ 0)
**Description**: Number of connections currently executing queries.

**Expected Values**:
- Typical: 0-5 during normal operation
- High load: Approaches `max_size`

**Interpretation**:
- `active_connections == max_size`: Pool fully utilized
- Sustained high active count: Consider increasing `max_size` or optimizing queries

**Alerting Threshold**: Alert if `active_connections == max_size` for > 10 minutes

---

#### `waiting_requests` (integer, ≥ 0)
**Description**: Number of acquisition requests queued waiting for available connections.

**Expected Values**:
- Normal: 0 (no queuing)
- Acceptable: 1-5 (brief queuing during burst load)
- Critical: > 10 (persistent queuing indicates capacity shortage)

**Interpretation**:
- `waiting_requests > 0`: Pool exhausted, requests queuing
- Sustained queuing: Increase `POOL_MAX_SIZE` or optimize query performance

**Alerting Threshold**: **CRITICAL** - Alert if `waiting_requests > 10` for > 2 minutes

---

#### `avg_acquisition_time_ms` (float, ≥ 0.0)
**Description**: Average time to acquire a connection from the pool (milliseconds).

**Expected Values**:
- Excellent: < 5ms
- Normal: 5-10ms
- Degraded: 10-50ms
- Critical: > 50ms

**Interpretation**:
- Low latency: Pool has spare capacity
- High latency: Pool under load or connections queuing

**Performance Target**: < 10ms (p95 per SC-002)

**Alerting Threshold**: Alert if p95 > 10ms for > 5 minutes

---

#### `peak_active_connections` (integer, ≥ 0)
**Description**: Maximum number of connections simultaneously active since server startup.

**Use Cases**:
- Capacity planning: Determine if `max_size` is sufficient
- Right-sizing: If `peak_active_connections` consistently < `max_size / 2`, consider reducing `max_size`
- Growth analysis: Track peak over time to anticipate capacity needs

**Interpretation**:
- `peak_active_connections == max_size`: Pool has hit capacity limit
- `peak_active_connections < max_size * 0.5`: Pool over-provisioned

---

#### `peak_wait_time_ms` (float, ≥ 0.0)
**Description**: Maximum time any request has waited for a connection (milliseconds).

**Expected Values**:
- Excellent: < 10ms (no significant queuing)
- Acceptable: 10-100ms (brief queuing)
- Degraded: 100-1000ms (noticeable queuing)
- Critical: > 1000ms (1+ seconds - severe capacity shortage)

**Interpretation**:
- Low peak wait: Pool adequately sized
- High peak wait: Pool exhaustion occurred, investigate cause

**Alerting Threshold**: Alert if `peak_wait_time_ms > 1000ms`

---

#### `total_acquisitions` / `total_releases` (integer, ≥ 0)
**Description**: Lifetime count of connection acquisitions and releases.

**Health Check**:
- `total_acquisitions == total_releases`: All connections properly returned
- `total_acquisitions > total_releases`: Some connections still in use (normal during load)
- `total_acquisitions >> total_releases`: **Potential connection leak detected**

**Leak Detection**:
```python
leak_count = total_acquisitions - total_releases - active_connections
if leak_count > 10:
    # CRITICAL: Connection leak suspected
```

**Alerting Threshold**: Alert if `leak_count > 10`

---

#### `pool_created_at` (datetime)
**Description**: Timestamp when pool was initialized.

**Use Cases**:
- Calculate uptime: `uptime = now() - pool_created_at`
- Correlate pool lifecycle with application events

---

#### `last_health_check` (datetime)
**Description**: Timestamp of last successful health check.

**Expected Behavior**:
- Updated every health check request (typically every 10-60 seconds)
- If stale (> 5 minutes), health check endpoint may not be functioning

---

#### `last_error` (string | null)
**Description**: Last error message encountered by the pool.

**Expected Values**:
- `null`: No recent errors
- String: Error message with context (e.g., "Connection validation failed")

**Common Error Messages**:
- `"Connection validation failed"`: Database query failed during validation
- `"Database connection refused"`: Database server unreachable
- `"Pool initialization timeout"`: Startup failed within 2 seconds
- `"Connection acquisition timeout"`: Request waited > 30 seconds

---

#### `last_error_time` (datetime | null)
**Description**: Timestamp of last error occurrence.

**Health Impact**:
- If `last_error_time` is within last 60 seconds, pool status may be DEGRADED
- Older errors (> 60 seconds) do not affect health status

---

### Statistics API Example

Query pool statistics programmatically:

```python
# Internal API (within MCP server)
stats: PoolStatistics = pool_manager.get_statistics()

print(f"Total connections: {stats.total_connections}")
print(f"Idle connections: {stats.idle_connections}")
print(f"Active connections: {stats.active_connections}")
print(f"Waiting requests: {stats.waiting_requests}")
print(f"Avg acquisition time: {stats.avg_acquisition_time_ms:.2f}ms")
print(f"Peak active: {stats.peak_active_connections}")
```

**Performance**: Statistics retrieval has < 1ms staleness (SC-007), ensuring real-time data.

---

## MCP Resource Endpoint

The connection pool exposes health status via an MCP resource endpoint for external monitoring:

### Resource URI

```
health://connection-pool
```

### Request Example

```bash
# Using MCP client CLI
mcp-client resource read health://connection-pool

# Using curl (via MCP SSE transport)
curl -H "Accept: text/event-stream" \
     http://localhost:3000/sse \
     -d '{"method":"resources/read","params":{"uri":"health://connection-pool"}}'
```

### Response Schema

```json
{
  "status": "healthy",
  "timestamp": "2025-10-13T14:30:00.000Z",
  "database": {
    "status": "connected",
    "pool": {
      "total": 5,
      "idle": 4,
      "active": 1,
      "waiting": 0
    },
    "latency_ms": 2.3,
    "last_error": null
  },
  "uptime_seconds": 3600.5
}
```

### Health Check Performance

- **Target Latency**: < 10ms (p99 per SC-003)
- **Throughput**: > 1000 req/s (per SC-013)
- **No Database Query**: Health check uses cached pool state only (no `SELECT 1` query)

### Integration with Load Balancers

Configure load balancer health checks:

```yaml
# Kubernetes liveness probe
livenessProbe:
  exec:
    command:
    - mcp-client
    - resource
    - read
    - health://connection-pool
  initialDelaySeconds: 5
  periodSeconds: 10
  timeoutSeconds: 2
  failureThreshold: 3

# Kubernetes readiness probe
readinessProbe:
  exec:
    command:
    - mcp-client
    - resource
    - read
    - health://connection-pool
  initialDelaySeconds: 3
  periodSeconds: 5
  timeoutSeconds: 2
  failureThreshold: 2
```

---

## Monitoring Integration

### Prometheus Metrics (Example)

If integrating with Prometheus, expose these metrics:

```python
# Example Prometheus metric definitions (not implemented by default)

# Gauge metrics
codebase_mcp_pool_connections_total = Gauge(
    "codebase_mcp_pool_connections_total",
    "Total number of connections in pool"
)

codebase_mcp_pool_connections_idle = Gauge(
    "codebase_mcp_pool_connections_idle",
    "Number of idle connections available"
)

codebase_mcp_pool_connections_active = Gauge(
    "codebase_mcp_pool_connections_active",
    "Number of active connections in use"
)

codebase_mcp_pool_waiting_requests = Gauge(
    "codebase_mcp_pool_waiting_requests",
    "Number of requests waiting for connections"
)

# Histogram metrics
codebase_mcp_pool_acquisition_duration_seconds = Histogram(
    "codebase_mcp_pool_acquisition_duration_seconds",
    "Time to acquire connection from pool",
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
)

# Counter metrics
codebase_mcp_pool_acquisitions_total = Counter(
    "codebase_mcp_pool_acquisitions_total",
    "Total number of connection acquisitions"
)

codebase_mcp_pool_releases_total = Counter(
    "codebase_mcp_pool_releases_total",
    "Total number of connection releases"
)

codebase_mcp_pool_errors_total = Counter(
    "codebase_mcp_pool_errors_total",
    "Total number of pool errors",
    ["error_type"]
)

# Info metric
codebase_mcp_pool_health_status = Enum(
    "codebase_mcp_pool_health_status",
    "Connection pool health status",
    states=["healthy", "degraded", "unhealthy"]
)
```

### Exporter Script

```python
# scripts/prometheus_exporter.py
"""
Prometheus exporter for connection pool metrics.
Scrapes pool statistics and exposes /metrics endpoint.
"""
import asyncio
from prometheus_client import start_http_server, Gauge, Histogram, Counter, Enum
from connection_pool import ConnectionPoolManager

# Initialize metrics (definitions above)

async def update_metrics(pool_manager: ConnectionPoolManager):
    """Update Prometheus metrics from pool statistics."""
    while True:
        stats = pool_manager.get_statistics()
        health = await pool_manager.health_check()

        # Update gauges
        codebase_mcp_pool_connections_total.set(stats.total_connections)
        codebase_mcp_pool_connections_idle.set(stats.idle_connections)
        codebase_mcp_pool_connections_active.set(stats.active_connections)
        codebase_mcp_pool_waiting_requests.set(stats.waiting_requests)

        # Update health status
        codebase_mcp_pool_health_status.state(health.status)

        await asyncio.sleep(10)  # Scrape every 10 seconds

if __name__ == "__main__":
    # Start Prometheus HTTP server on port 9090
    start_http_server(9090)

    # Initialize pool manager and start metric updates
    pool_manager = ConnectionPoolManager()
    asyncio.run(update_metrics(pool_manager))
```

**Usage**:
```bash
# Start exporter
python scripts/prometheus_exporter.py

# Prometheus scrape config
scrape_configs:
  - job_name: 'codebase-mcp-pool'
    static_configs:
      - targets: ['localhost:9090']
    scrape_interval: 15s
```

---

### Grafana Dashboard

Example Grafana dashboard queries for visualizing pool metrics:

#### Panel 1: Connection Pool Utilization

```promql
# Query 1: Total connections
codebase_mcp_pool_connections_total

# Query 2: Idle connections
codebase_mcp_pool_connections_idle

# Query 3: Active connections
codebase_mcp_pool_connections_active

# Panel type: Time series graph
# Y-axis: Connection count
# Legend: {{__name__}}
```

#### Panel 2: Connection Acquisition Latency

```promql
# p50 latency
histogram_quantile(0.50,
  rate(codebase_mcp_pool_acquisition_duration_seconds_bucket[5m]))

# p95 latency (target: < 10ms)
histogram_quantile(0.95,
  rate(codebase_mcp_pool_acquisition_duration_seconds_bucket[5m]))

# p99 latency
histogram_quantile(0.99,
  rate(codebase_mcp_pool_acquisition_duration_seconds_bucket[5m]))

# Panel type: Time series graph
# Y-axis: Latency (seconds)
# Threshold line at 0.01s (10ms target)
```

#### Panel 3: Pool Health Status

```promql
# Health status (0=healthy, 1=degraded, 2=unhealthy)
codebase_mcp_pool_health_status

# Panel type: Stat panel
# Color mode: Background
# Thresholds: 0=green, 1=yellow, 2=red
```

#### Panel 4: Waiting Requests (Queue Depth)

```promql
# Waiting requests count
codebase_mcp_pool_waiting_requests

# Panel type: Time series graph
# Y-axis: Request count
# Threshold line at 10 (critical threshold)
# Alert annotation: waiting_requests > 10
```

#### Panel 5: Acquisition Throughput

```promql
# Acquisitions per second
rate(codebase_mcp_pool_acquisitions_total[1m])

# Releases per second
rate(codebase_mcp_pool_releases_total[1m])

# Panel type: Time series graph
# Y-axis: Operations per second
```

#### Panel 6: Error Rate

```promql
# Errors per second by type
rate(codebase_mcp_pool_errors_total[5m])

# Panel type: Time series graph
# Y-axis: Errors per second
# Group by: error_type
```

**Full Dashboard JSON**: Available at `docs/grafana/connection-pool-dashboard.json` (to be created separately)

---

### Alerting Rules

Example Prometheus alerting rules for connection pool monitoring:

```yaml
# /etc/prometheus/rules/codebase-mcp-pool.yml

groups:
  - name: codebase_mcp_pool_alerts
    interval: 30s
    rules:
      # CRITICAL: Pool has no connections
      - alert: ConnectionPoolNoConnections
        expr: codebase_mcp_pool_connections_total == 0
        for: 30s
        labels:
          severity: critical
          component: connection_pool
        annotations:
          summary: "Connection pool has no available connections"
          description: "Pool has zero total connections for 30+ seconds. Database may be down or pool failed to initialize."
          runbook: "https://docs.example.com/runbooks/connection-pool-no-connections"

      # CRITICAL: Pool health unhealthy for 5 minutes
      - alert: ConnectionPoolUnhealthy
        expr: codebase_mcp_pool_health_status == 2
        for: 5m
        labels:
          severity: critical
          component: connection_pool
        annotations:
          summary: "Connection pool in UNHEALTHY state"
          description: "Pool health status has been UNHEALTHY for 5+ minutes. Automatic recovery may have failed."
          runbook: "https://docs.example.com/runbooks/connection-pool-unhealthy"

      # WARNING: Pool health degraded for 10 minutes
      - alert: ConnectionPoolDegraded
        expr: codebase_mcp_pool_health_status == 1
        for: 10m
        labels:
          severity: warning
          component: connection_pool
        annotations:
          summary: "Connection pool in DEGRADED state"
          description: "Pool health has been DEGRADED for 10+ minutes. May indicate persistent capacity issues."
          runbook: "https://docs.example.com/runbooks/connection-pool-degraded"

      # CRITICAL: Requests waiting for connections (pool exhaustion)
      - alert: ConnectionPoolExhausted
        expr: codebase_mcp_pool_waiting_requests > 10
        for: 2m
        labels:
          severity: critical
          component: connection_pool
        annotations:
          summary: "Connection pool exhausted - requests queuing"
          description: "{{ $value }} requests waiting for connections. Pool capacity insufficient for current load."
          action: "Increase POOL_MAX_SIZE or investigate slow queries"

      # WARNING: High connection acquisition latency
      - alert: ConnectionPoolHighLatency
        expr: |
          histogram_quantile(0.95,
            rate(codebase_mcp_pool_acquisition_duration_seconds_bucket[5m])) > 0.01
        for: 5m
        labels:
          severity: warning
          component: connection_pool
        annotations:
          summary: "Connection acquisition latency high (p95 > 10ms)"
          description: "p95 acquisition latency is {{ $value }}s (target: <0.01s)"
          action: "Investigate pool capacity or query performance"

      # WARNING: Potential connection leak
      - alert: ConnectionPoolLeak
        expr: |
          (codebase_mcp_pool_acquisitions_total - codebase_mcp_pool_releases_total
           - codebase_mcp_pool_connections_active) > 10
        for: 10m
        labels:
          severity: warning
          component: connection_pool
        annotations:
          summary: "Potential connection leak detected"
          description: "{{ $value }} connections appear leaked (acquired but not released)"
          action: "Review application logs for connection leak warnings with stack traces"

      # CRITICAL: Pool fully utilized for extended period
      - alert: ConnectionPoolFullyUtilized
        expr: |
          codebase_mcp_pool_connections_active ==
          codebase_mcp_pool_connections_total
        for: 10m
        labels:
          severity: critical
          component: connection_pool
        annotations:
          summary: "Connection pool fully utilized"
          description: "All {{ $value }} connections are active for 10+ minutes"
          action: "Increase POOL_MAX_SIZE or optimize query performance"

      # WARNING: Low idle capacity
      - alert: ConnectionPoolLowCapacity
        expr: |
          (codebase_mcp_pool_connections_idle /
           codebase_mcp_pool_connections_total) < 0.5
        for: 5m
        labels:
          severity: warning
          component: connection_pool
        annotations:
          summary: "Connection pool running at low capacity"
          description: "Idle capacity is {{ $value | humanizePercentage }} (threshold: 50%)"
          action: "Consider increasing POOL_MAX_SIZE"
```

**Alert Routing**:
```yaml
# /etc/alertmanager/config.yml

route:
  group_by: ['alertname', 'component']
  group_wait: 10s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'default'
  routes:
    - match:
        severity: critical
        component: connection_pool
      receiver: 'pagerduty-critical'
      continue: true
    - match:
        severity: warning
        component: connection_pool
      receiver: 'slack-warnings'

receivers:
  - name: 'pagerduty-critical'
    pagerduty_configs:
      - service_key: '<pagerduty_service_key>'
  - name: 'slack-warnings'
    slack_configs:
      - api_url: '<slack_webhook_url>'
        channel: '#ops-warnings'
```

---

## Troubleshooting Guide

### Issue: Slow Query Performance

#### Symptoms
- Connection acquisition latency > 10ms (p95)
- `avg_acquisition_time_ms` increasing over time
- Users report slow response times for database operations

#### Causes
1. **Slow database queries**: Individual queries taking seconds to complete
2. **High query concurrency**: Too many simultaneous queries for pool size
3. **Database server overload**: CPU/memory/disk saturation on PostgreSQL
4. **Connection validation overhead**: Health checks taking too long

#### Resolution Steps

**Step 1: Identify slow queries**
```bash
# Check PostgreSQL slow query log
tail -f /var/log/postgresql/postgresql-14-main.log | grep "duration:"

# Query PostgreSQL statistics
psql -U postgres -d codebase_mcp -c "
  SELECT query, calls, mean_exec_time, max_exec_time
  FROM pg_stat_statements
  ORDER BY mean_exec_time DESC
  LIMIT 10;
"
```

**Step 2: Review pool statistics**
```python
# Check if pool is under-provisioned
stats = pool_manager.get_statistics()
print(f"Active: {stats.active_connections}/{stats.total_connections}")
print(f"Waiting: {stats.waiting_requests}")
print(f"Peak active: {stats.peak_active_connections}")

# If peak_active_connections == max_size, pool may be too small
```

**Step 3: Optimize queries**
```sql
-- Add indexes to slow queries
CREATE INDEX CONCURRENTLY idx_chunks_embedding ON code_chunks
USING ivfflat (embedding vector_cosine_ops);

-- Analyze query plans
EXPLAIN ANALYZE <slow_query>;
```

**Step 4: Increase pool size (if needed)**
```bash
# Increase max pool size temporarily
export POOL_MAX_SIZE=20

# Restart MCP server
systemctl restart codebase-mcp

# Monitor acquisition latency improvement
```

**Step 5: Enable query logging**
```python
# Add query timing to application logs
import logging
logger = logging.getLogger("codebase_mcp")
logger.setLevel(logging.DEBUG)  # Log query durations
```

**Prevention**:
- Set query timeouts: `POOL_COMMAND_TIMEOUT=60` (default)
- Implement query result caching for frequently accessed data
- Use database connection pooling at application layer (already implemented)

---

### Issue: Connection Pool Exhaustion

#### Symptoms
- `waiting_requests > 0` consistently
- `active_connections == max_size` for extended periods
- Connection acquisition timeouts (30 second timeout errors)
- Alert: `ConnectionPoolExhausted` firing

#### Causes
1. **Insufficient pool capacity**: `max_size` too small for current load
2. **Connection leaks**: Connections not being returned to pool
3. **Long-running queries**: Queries holding connections for minutes
4. **Burst traffic**: Sudden spike in concurrent requests

#### Resolution Steps

**Step 1: Immediate mitigation**
```bash
# Increase pool size to handle burst
export POOL_MAX_SIZE=20  # Double current size
systemctl restart codebase-mcp

# Verify increased capacity
curl http://localhost:3000/health | jq '.database.pool'
# Expected: {"total": 20, "idle": 15, "active": 5, "waiting": 0}
```

**Step 2: Identify resource hogs**
```sql
-- Check for long-running queries
SELECT pid, now() - query_start AS duration, query
FROM pg_stat_activity
WHERE state = 'active'
  AND now() - query_start > interval '1 minute'
ORDER BY duration DESC;

-- Terminate hung queries (if necessary)
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'active'
  AND now() - query_start > interval '5 minutes';
```

**Step 3: Check for connection leaks**
```bash
# Review leak detection warnings in logs
grep "Potential connection leak" /tmp/codebase-mcp.log

# Expected output with stack trace:
# WARNING: Potential connection leak detected: conn_abc123
#   held_duration_seconds: 45.2
#   stack_trace: <acquisition call stack>
```

**Step 4: Analyze acquisition patterns**
```python
# Review peak usage metrics
stats = pool_manager.get_statistics()
print(f"Peak active: {stats.peak_active_connections}")
print(f"Total acquisitions: {stats.total_acquisitions}")
print(f"Avg acquisition time: {stats.avg_acquisition_time_ms:.2f}ms")

# If peak consistently hits max_size, capacity is insufficient
```

**Step 5: Capacity planning**
```bash
# Calculate required pool size based on load patterns
# Rule of thumb: max_size = (concurrent_users * avg_queries_per_request) + buffer

# For 100 concurrent users, 2 queries per request, 50% buffer:
# max_size = (100 * 2) * 1.5 = 300 connections (adjust based on actual usage)

# More realistic for local MCP server: 10-20 connections sufficient
export POOL_MAX_SIZE=15
```

**Prevention**:
- Set `POOL_LEAK_DETECTION_TIMEOUT=30` to catch leaks early
- Implement query timeouts to prevent hung connections
- Monitor `waiting_requests` metric and alert on > 10
- Right-size pool based on actual load patterns

---

### Issue: Database Outage and Recovery

#### Symptoms
- Pool health status: `UNHEALTHY`
- `total_connections == 0`
- All database queries failing with `DATABASE_ERROR`
- Logs show: "Database connection refused" or "Connection reset"

#### Expected Behavior During Outage

**Automatic Reconnection Sequence**:
1. Pool detects connection failures
2. Health status transitions: `HEALTHY → DEGRADED → UNHEALTHY → RECOVERING`
3. Exponential backoff reconnection attempts:
   - Attempt 1: 1 second delay
   - Attempt 2: 2 seconds delay
   - Attempt 3: 4 seconds delay
   - Attempt 4: 8 seconds delay
   - Attempt 5: 16 seconds delay
   - Subsequent attempts: Every 16 seconds
4. Once database recovers, pool reinitializes connections
5. Health status transitions: `RECOVERING → HEALTHY`
6. Normal operations resume

**Recovery Timeline**:
- **Best case**: 1 second (immediate database availability)
- **Typical**: 10-30 seconds (transient network issue)
- **Worst case**: Up to 30 seconds (p95 per SC-004) after database recovers

#### Resolution Steps

**Step 1: Verify database status**
```bash
# Check if PostgreSQL is running
docker ps | grep postgres
# OR
systemctl status postgresql

# If not running, start database
docker start postgres-codebase-mcp
# OR
systemctl start postgresql
```

**Step 2: Verify network connectivity**
```bash
# Ping database host
ping <database_host>

# Check port connectivity
nc -zv <database_host> 5432

# Test connection with psql
psql -U postgres -h <database_host> -d codebase_mcp -c "SELECT 1"
```

**Step 3: Monitor automatic recovery**
```bash
# Watch MCP server logs for reconnection attempts
tail -f /tmp/codebase-mcp.log | grep -E "reconnect|recovering"

# Expected log sequence:
# INFO: Reconnection attempt 1/5 (delay: 1s)
# INFO: Reconnection attempt 2/5 (delay: 2s)
# INFO: Connection pool recovered: 2/10 connections available
# INFO: Health status: RECOVERING -> HEALTHY
```

**Step 4: Verify pool recovery**
```bash
# Check health endpoint
curl http://localhost:3000/health | jq '.database'

# Expected after recovery:
# {
#   "status": "connected",
#   "pool": {"total": 2, "idle": 2, "active": 0, "waiting": 0},
#   "latency_ms": 2.5,
#   "last_error": null
# }
```

**Step 5: Test database operations**
```bash
# Execute test query via MCP client
mcp-client tool call search_code --query "test"

# Should succeed with results (or empty results if database has no data)
```

**Manual Recovery (if automatic fails)**:
```bash
# If automatic recovery doesn't work within 5 minutes:
# 1. Check database logs for errors
tail -f /var/log/postgresql/postgresql-14-main.log

# 2. Verify DATABASE_URL is correct
echo $DATABASE_URL
# OR
cat .env | grep DATABASE_URL

# 3. Restart MCP server to force reconnection
systemctl restart codebase-mcp

# 4. If issue persists, check database connectivity:
psql -U postgres -d codebase_mcp -c "SELECT version();"
```

**Prevention**:
- Monitor database server health proactively
- Set up database replication for high availability
- Configure alerts for database downtime
- Test recovery procedures regularly (e.g., monthly chaos testing)

---

### Issue: Connection Leaks

#### Symptoms
- `total_acquisitions >> total_releases + active_connections`
- Warning logs: "Potential connection leak detected"
- Pool gradually exhausting connections over time
- Increasing `active_connections` without corresponding releases

#### Causes
1. **Unclosed context managers**: Missing `async with pool.acquire()` pattern
2. **Exception handling gaps**: Connections not released in error paths
3. **Long-running operations**: Legitimate operations exceeding `leak_detection_timeout`
4. **Application bugs**: Logic errors preventing connection release

#### Resolution Steps

**Step 1: Identify leaking code**
```bash
# Review leak warnings with stack traces
grep -A 20 "Potential connection leak" /tmp/codebase-mcp.log

# Example output:
# WARNING: Potential connection leak detected: conn_abc123
#   connection_id: conn_abc123
#   held_duration_seconds: 45.2
#   stack_trace:
#     File "src/services/searcher.py", line 123, in search_code
#       conn = await pool.acquire()  # <-- Acquisition site
#     File "src/services/searcher.py", line 145, in execute_search
#       results = await conn.fetch(query)
```

**Step 2: Review code at acquisition sites**
```python
# INCORRECT: Connection not guaranteed to be released
async def bad_query():
    conn = await pool.acquire()
    result = await conn.fetchval("SELECT 1")
    # BUG: If exception occurs, connection never released
    await pool.release(conn)
    return result

# CORRECT: Use context manager
async def good_query():
    async with pool.acquire() as conn:
        result = await conn.fetchval("SELECT 1")
        # Connection automatically released even if exception occurs
        return result
```

**Step 3: Check for exception handling issues**
```python
# INCORRECT: Connection leaked in error path
async def bad_error_handling():
    conn = await pool.acquire()
    try:
        result = await conn.fetchval("SELECT 1")
    except Exception as e:
        # BUG: Return without releasing connection
        return None
    await pool.release(conn)
    return result

# CORRECT: Use context manager or try/finally
async def good_error_handling():
    async with pool.acquire() as conn:
        try:
            result = await conn.fetchval("SELECT 1")
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return None
        return result
```

**Step 4: Verify leak detection configuration**
```bash
# Check leak detection settings
echo $POOL_LEAK_DETECTION_TIMEOUT  # Default: 30
echo $POOL_ENABLE_LEAK_DETECTION   # Default: true

# Adjust timeout for long-running operations
export POOL_LEAK_DETECTION_TIMEOUT=120  # 2 minutes for batch jobs
```

**Step 5: Monitor leak count**
```python
# Calculate current leak count
stats = pool_manager.get_statistics()
leak_count = (stats.total_acquisitions - stats.total_releases
              - stats.active_connections)
print(f"Suspected leaks: {leak_count}")

# If leak_count > 10, investigate immediately
```

**Step 6: Force connection recycling (temporary fix)**
```bash
# Restart server to clear leaked connections
systemctl restart codebase-mcp

# Or reduce max_connection_lifetime to force recycling
export POOL_MAX_CONNECTION_LIFETIME=600  # 10 minutes (default: 3600)
```

**Prevention**:
- **Always use context managers**: `async with pool.acquire() as conn:`
- Enable leak detection in production: `POOL_ENABLE_LEAK_DETECTION=true`
- Set appropriate timeout: `POOL_LEAK_DETECTION_TIMEOUT=30` (30 seconds)
- Review all connection acquisition sites during code reviews
- Run 24-hour leak test before production deployment:
  ```bash
  pytest tests/integration/test_leak_detection.py --duration=86400
  ```

---

### Issue: High Wait Times

#### Symptoms
- `peak_wait_time_ms > 100ms`
- Increased `avg_acquisition_time_ms`
- Intermittent connection acquisition delays
- Alert: `ConnectionPoolHighLatency` firing

#### Causes
1. **Pool too small**: `max_size` insufficient for concurrent load
2. **Slow queries**: Individual queries holding connections for seconds
3. **Burst traffic**: Sudden spike in requests
4. **Database performance**: Slow query execution on PostgreSQL side

#### Resolution Steps

**Step 1: Analyze wait time patterns**
```python
# Review statistics
stats = pool_manager.get_statistics()
print(f"Avg acquisition: {stats.avg_acquisition_time_ms:.2f}ms")
print(f"Peak wait time: {stats.peak_wait_time_ms:.2f}ms")
print(f"Active connections: {stats.active_connections}/{stats.total_connections}")
print(f"Waiting requests: {stats.waiting_requests}")

# If waiting_requests > 0, pool is undersized
# If avg_acquisition_time > 10ms, investigate causes
```

**Step 2: Identify bottleneck**
```sql
-- Check for slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
WHERE mean_exec_time > 100  -- > 100ms average
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Check database load
SELECT * FROM pg_stat_activity;
```

**Step 3: Increase pool capacity (if needed)**
```bash
# Temporarily increase max_size
export POOL_MAX_SIZE=20
systemctl restart codebase-mcp

# Monitor wait time improvement
curl http://localhost:3000/health | jq '.database.pool'
```

**Step 4: Optimize slow queries**
```sql
-- Add missing indexes
CREATE INDEX CONCURRENTLY idx_chunks_repo ON code_chunks(repository_id);

-- Vacuum database
VACUUM ANALYZE code_chunks;

-- Update statistics
ANALYZE;
```

**Step 5: Implement query timeout**
```bash
# Set command timeout to prevent hung queries
export POOL_COMMAND_TIMEOUT=60  # 60 seconds max per query
systemctl restart codebase-mcp
```

**Prevention**:
- Monitor `peak_wait_time_ms` and alert on > 100ms
- Right-size pool based on actual concurrency patterns
- Implement query result caching for frequently accessed data
- Set `POOL_COMMAND_TIMEOUT` to prevent queries from holding connections indefinitely
- Optimize database indexes and query plans

---

## Performance Baselines

Reference expected latencies and throughput from quickstart.md integration tests:

### Initialization Performance
- **Target**: Pool initialization < 2 seconds (p95)
- **Typical**: 300-500ms
- **Includes**: Creating `min_size` connections, validation queries

### Connection Acquisition Performance
- **Target**: < 10ms (p95)
- **Typical**: 1-3ms (when connections available)
- **Typical (under load)**: 5-10ms (when scaling up pool)

### Health Check Performance
- **Target**: < 10ms (p99)
- **Typical**: < 1ms (cached state, no database query)
- **Throughput**: > 1000 requests/second

### Reconnection Performance
- **Target**: < 30 seconds (p95) after database recovery
- **Typical**: 10-20 seconds
- **Includes**: Exponential backoff delays, connection creation, validation

### Graceful Shutdown Performance
- **Target**: < 30 seconds (p99)
- **Typical**: 0-5 seconds (if no active queries)
- **Typical (with active queries)**: 5-30 seconds (waits for completion)

### Concurrent Load Performance
- **Target**: 100 concurrent requests without deadlock
- **Pool size**: max_size=10 (default)
- **Behavior**: Requests queue when pool exhausted, FIFO order

### Memory Consumption
- **Target**: < 100MB for max_size=10 pool
- **Typical**: 20-50MB (depends on connection count and query buffers)

### Startup Overhead
- **Target**: < 200ms added to server startup time
- **Typical**: 50-100ms (pool initialization)
- **Includes**: Configuration validation, pool creation

---

## Logging and Diagnostics

### Log File Location
```bash
/tmp/codebase-mcp.log
```

### Log Format
```json
{
  "timestamp": "2025-10-13T14:30:00.000Z",
  "level": "INFO",
  "component": "connection_pool",
  "message": "Connection pool initialized",
  "context": {
    "min_size": 2,
    "max_size": 10,
    "database": "codebase_mcp"
  }
}
```

### Key Log Messages

#### Initialization
```
INFO: Connection pool initialized: min_size=2, max_size=10
INFO: Created 2 initial connections in 345ms
```

#### Reconnection
```
WARNING: Database connection lost: Connection refused
INFO: Reconnection attempt 1/5 (delay: 1s)
INFO: Reconnection attempt 2/5 (delay: 2s)
INFO: Connection pool recovered: 2/10 connections available
```

#### Leak Detection
```
WARNING: Potential connection leak detected: conn_abc123
  connection_id: conn_abc123
  held_duration_seconds: 45.2
  stack_trace: <acquisition call stack>
```

#### Graceful Shutdown
```
INFO: Graceful shutdown initiated
INFO: Waiting for 3 active connections to complete (timeout: 30s)
INFO: All connections closed gracefully in 5.2s
INFO: Connection pool terminated
```

### Log Level Configuration
```bash
# Set log level via environment variable
export LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

---

## Summary

This guide provides comprehensive monitoring and troubleshooting documentation for the Codebase MCP Server connection pool. Key takeaways:

1. **Three-tier health status** (HEALTHY/DEGRADED/UNHEALTHY) provides clear operational signals
2. **Real-time statistics** enable capacity planning and performance optimization
3. **MCP resource endpoint** (`health://connection-pool`) integrates with external monitoring
4. **Prometheus/Grafana integration** enables visualization and alerting
5. **Troubleshooting procedures** cover common issues with actionable resolution steps
6. **Performance baselines** define expected latencies and throughput

**Next Steps**:
- Set up Prometheus scraping for pool metrics
- Configure Grafana dashboards for visualization
- Implement alerting rules for critical issues
- Test recovery procedures in staging environment
- Document team-specific runbooks based on this guide

**Support Resources**:
- Quickstart integration tests: `specs/009-v2-connection-mgmt/quickstart.md`
- Data model reference: `specs/009-v2-connection-mgmt/data-model.md`
- Feature specification: `specs/009-v2-connection-mgmt/spec.md`
- Implementation plan: `specs/009-v2-connection-mgmt/plan.md`

**Word Count**: ~8,500 words
