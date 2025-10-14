# Health Monitoring Operations Guide

**Version**: 1.0.0
**Last Updated**: 2025-10-13
**Feature**: 011-performance-validation-multi
**Phase**: 7 - User Story 5
**Tasks**: T039, T041, T043-T044, T048
**Constitutional Compliance**: Principle V (Production Quality)
**Success Criteria**: SC-010

## Overview

This guide provides comprehensive instructions for monitoring the health of the dual-server MCP architecture using the built-in health check endpoints. The health monitoring system provides real-time visibility into server status, database connectivity, and resource utilization.

## Health Check Endpoint

### Endpoint Details

**URL**: `health://status`
**Protocol**: MCP Resource (via SSE)
**Response Time**: <50ms (p95)
**Format**: JSON (HealthCheckResponse model)

### FastMCP Resource Registration

```python
@mcp.resource("health://status")
async def health_check() -> HealthCheckResponse:
    """Health check endpoint with <50ms response time guarantee."""
    return await health_service.check_health()
```

## Response Structure

### HealthCheckResponse Model

```python
class HealthCheckResponse(BaseModel):
    """Health check response with comprehensive status.

    Constitutional Compliance:
    - Principle V: Production-quality health monitoring
    - SC-010: Health checks respond within 50ms
    """
    status: Literal["healthy", "degraded", "unhealthy"]
    timestamp: datetime
    database_status: Literal["connected", "disconnected", "degraded"]
    uptime_seconds: float
    connection_pool: ConnectionPoolStats
    checks: Dict[str, HealthCheckDetail]
    metadata: Dict[str, Any]

class ConnectionPoolStats(BaseModel):
    """Connection pool statistics for monitoring."""
    total_connections: int
    active_connections: int
    idle_connections: int
    waiting_requests: int
    pool_utilization: float  # 0.0 to 1.0
```

### Example Response

```json
{
  "status": "healthy",
  "timestamp": "2025-10-13T10:30:45.123Z",
  "database_status": "connected",
  "uptime_seconds": 3672.5,
  "connection_pool": {
    "total_connections": 10,
    "active_connections": 3,
    "idle_connections": 7,
    "waiting_requests": 0,
    "pool_utilization": 0.3
  },
  "checks": {
    "database": {
      "status": "pass",
      "latency_ms": 12.5,
      "message": "Database responding normally"
    },
    "memory": {
      "status": "pass",
      "usage_mb": 245,
      "limit_mb": 2048,
      "percentage": 11.9
    },
    "disk": {
      "status": "pass",
      "free_gb": 125.3,
      "percentage_used": 45.2
    }
  },
  "metadata": {
    "version": "2.0.0",
    "environment": "production",
    "region": "us-west-2"
  }
}
```

## Status Interpretation

### Health Status Levels

| Status | Description | Conditions | Action Required |
|--------|-------------|------------|-----------------|
| **healthy** | All systems operational | - Database connected<br>- Pool utilization <80%<br>- All checks passing | None |
| **degraded** | Performance impacted | - Pool utilization 80-95%<br>- High memory usage (>80%)<br>- Slow database response (>100ms) | Monitor closely |
| **unhealthy** | Critical issues | - Database disconnected<br>- Pool exhausted (>95%)<br>- Memory critical (>95%) | Immediate action |

### Database Status

| Status | Meaning | Typical Causes | Resolution |
|--------|---------|----------------|------------|
| **connected** | Normal operation | - | - |
| **degraded** | Slow responses | High load, network latency | Scale database, optimize queries |
| **disconnected** | No connection | Network failure, DB down | Check database server, network |

### Connection Pool Health

```python
def interpret_pool_utilization(utilization: float) -> str:
    if utilization < 0.5:
        return "healthy - low utilization"
    elif utilization < 0.8:
        return "normal - moderate utilization"
    elif utilization < 0.95:
        return "warning - high utilization"
    else:
        return "critical - pool exhausted"
```

## Monitoring Implementation

### 1. Basic Health Check Script

```python
#!/usr/bin/env python3
"""health_check.py - Monitor MCP server health"""

import asyncio
import json
from datetime import datetime
from mcp import Client

async def check_health(server_url: str):
    """Perform health check and return status."""
    client = Client(server_url)

    try:
        # Request health resource
        response = await client.get_resource("health://status")
        health_data = json.loads(response)

        # Parse status
        status = health_data["status"]
        db_status = health_data["database_status"]
        pool_util = health_data["connection_pool"]["pool_utilization"]

        # Format output
        print(f"[{datetime.now().isoformat()}] Health Check")
        print(f"  Status: {status.upper()}")
        print(f"  Database: {db_status}")
        print(f"  Pool Utilization: {pool_util:.1%}")

        # Return status code
        return 0 if status == "healthy" else 1

    except Exception as e:
        print(f"ERROR: Health check failed - {e}")
        return 2

if __name__ == "__main__":
    import sys
    server = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    exit_code = asyncio.run(check_health(server))
    sys.exit(exit_code)
```

### 2. Continuous Monitoring Loop

```bash
#!/bin/bash
# monitor_health.sh - Continuous health monitoring

INTERVAL=5  # Check every 5 seconds
ALERT_THRESHOLD=3  # Alert after 3 consecutive failures

failure_count=0

while true; do
    # Run health check
    python health_check.py http://localhost:8000
    status=$?

    if [ $status -eq 0 ]; then
        # Reset failure count on success
        failure_count=0
        echo "✅ Health check passed"
    else
        # Increment failure count
        ((failure_count++))
        echo "❌ Health check failed (count: $failure_count)"

        # Alert if threshold exceeded
        if [ $failure_count -ge $ALERT_THRESHOLD ]; then
            echo "🚨 ALERT: Health check failing continuously!"
            # Send alert (email, Slack, PagerDuty, etc.)
            ./send_alert.sh "MCP Server Health Critical"
        fi
    fi

    sleep $INTERVAL
done
```

### 3. Integration with Monitoring Systems

#### Datadog Integration
```python
from datadog import initialize, api
import asyncio

# Initialize Datadog
initialize(api_key="YOUR_API_KEY", app_key="YOUR_APP_KEY")

async def report_health_to_datadog():
    """Report health metrics to Datadog."""
    health = await check_health("http://localhost:8000")

    # Send metrics
    api.Metric.send([
        {
            "metric": "mcp.health.status",
            "points": [(time.time(), 1 if health["status"] == "healthy" else 0)],
            "tags": ["service:codebase-mcp"]
        },
        {
            "metric": "mcp.pool.utilization",
            "points": [(time.time(), health["connection_pool"]["pool_utilization"])],
            "tags": ["service:codebase-mcp"]
        }
    ])
```

#### Prometheus Exporter
```python
from prometheus_client import Gauge, start_http_server

# Define metrics
health_status = Gauge('mcp_health_status',
                     'Health status (1=healthy, 0.5=degraded, 0=unhealthy)')
pool_utilization = Gauge('mcp_pool_utilization',
                        'Connection pool utilization (0-1)')
database_latency = Gauge('mcp_database_latency_ms',
                        'Database response time in milliseconds')

async def update_metrics():
    """Update Prometheus metrics from health check."""
    health = await check_health("http://localhost:8000")

    # Map status to numeric value
    status_map = {"healthy": 1, "degraded": 0.5, "unhealthy": 0}
    health_status.set(status_map[health["status"]])

    # Update pool metrics
    pool_utilization.set(health["connection_pool"]["pool_utilization"])

    # Update database latency
    db_check = health["checks"].get("database", {})
    if "latency_ms" in db_check:
        database_latency.set(db_check["latency_ms"])

# Start Prometheus metrics server
start_http_server(9090)
```

## Alerting Thresholds

### Critical Alerts (Immediate Action)

| Metric | Threshold | Duration | Alert | Action |
|--------|-----------|----------|-------|--------|
| Health Status | unhealthy | 1 check | PagerDuty | Investigate immediately |
| Database Status | disconnected | 10s | PagerDuty | Check DB server |
| Pool Utilization | >95% | 30s | PagerDuty | Scale or optimize |
| Response Time | >500ms | 1 min | PagerDuty | Check server load |

### Warning Alerts (Monitor Closely)

| Metric | Threshold | Duration | Alert | Action |
|--------|-----------|----------|-------|--------|
| Health Status | degraded | 5 min | Slack | Monitor trend |
| Pool Utilization | >80% | 2 min | Slack | Consider scaling |
| Memory Usage | >80% | 5 min | Email | Check for leaks |
| Uptime | <1 hour | - | Log | Check for restarts |

### Example Alert Rules (Prometheus)

```yaml
groups:
  - name: mcp_health
    interval: 30s
    rules:
      - alert: MCPUnhealthy
        expr: mcp_health_status < 0.5
        for: 10s
        labels:
          severity: critical
          service: mcp
        annotations:
          summary: "MCP server is unhealthy"
          description: "Server {{ $labels.instance }} health status is {{ $value }}"
          runbook_url: "https://docs/runbooks/mcp-unhealthy"

      - alert: MCPPoolExhausted
        expr: mcp_pool_utilization > 0.95
        for: 30s
        labels:
          severity: critical
          service: mcp
        annotations:
          summary: "Connection pool is exhausted"
          description: "Pool utilization is {{ $value | humanizePercentage }}"
          runbook_url: "https://docs/runbooks/pool-exhausted"

      - alert: MCPHighLatency
        expr: mcp_database_latency_ms > 100
        for: 2m
        labels:
          severity: warning
          service: mcp
        annotations:
          summary: "Database latency is high"
          description: "Database latency is {{ $value }}ms"
```

## Production Monitoring Setup

### 1. Infrastructure Requirements

```yaml
monitoring:
  health_check:
    interval: 5s        # How often to check
    timeout: 1s         # Max time per check
    retries: 3          # Retries before marking unhealthy

  storage:
    retention: 30d      # Keep 30 days of metrics
    resolution: 10s     # Store data points every 10s

  alerting:
    channels:
      - type: pagerduty
        severity: critical
        api_key: ${PAGERDUTY_API_KEY}
      - type: slack
        severity: warning
        webhook: ${SLACK_WEBHOOK_URL}
      - type: email
        severity: info
        smtp_server: smtp.company.com
```

### 2. Dashboard Configuration

#### Grafana Dashboard JSON
```json
{
  "dashboard": {
    "title": "MCP Health Monitoring",
    "panels": [
      {
        "title": "Health Status",
        "type": "stat",
        "targets": [{
          "expr": "mcp_health_status"
        }],
        "thresholds": {
          "steps": [
            {"value": 0, "color": "red"},
            {"value": 0.5, "color": "yellow"},
            {"value": 1, "color": "green"}
          ]
        }
      },
      {
        "title": "Connection Pool Utilization",
        "type": "gauge",
        "targets": [{
          "expr": "mcp_pool_utilization * 100"
        }],
        "thresholds": {
          "steps": [
            {"value": 0, "color": "green"},
            {"value": 80, "color": "yellow"},
            {"value": 95, "color": "red"}
          ]
        }
      },
      {
        "title": "Database Latency",
        "type": "graph",
        "targets": [{
          "expr": "mcp_database_latency_ms"
        }]
      }
    ]
  }
}
```

### 3. Automation Scripts

#### Health Check Automation
```bash
#!/bin/bash
# automate_health_checks.sh

# Configuration
SERVERS=("codebase-mcp:8000" "workflow-mcp:8001")
LOG_DIR="/var/log/mcp/health"
ALERT_SCRIPT="./alert_manager.sh"

# Ensure log directory exists
mkdir -p $LOG_DIR

# Check each server
for server in "${SERVERS[@]}"; do
    log_file="$LOG_DIR/$(echo $server | tr ':' '_').log"

    # Run health check
    result=$(curl -s "http://$server/health/status")
    status=$(echo $result | jq -r '.status')
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    # Log result
    echo "$timestamp $status $result" >> $log_file

    # Alert if unhealthy
    if [ "$status" != "healthy" ]; then
        $ALERT_SCRIPT "$server is $status" "$result"
    fi
done
```

## Troubleshooting Guide

### Common Issues and Resolutions

| Symptom | Likely Cause | Diagnostic Steps | Resolution |
|---------|--------------|------------------|------------|
| Status: unhealthy | Database down | Check DB logs, network | Restart database, check credentials |
| Slow health checks | High server load | Check CPU, memory | Scale resources, optimize |
| Intermittent failures | Network issues | Check latency, packet loss | Stabilize network, add retries |
| Pool exhausted | Too many requests | Check active queries | Increase pool size, optimize queries |

### Debug Commands

```bash
# Check health endpoint directly
curl -s http://localhost:8000/health/status | jq '.'

# Monitor pool statistics
watch -n 1 'curl -s http://localhost:8000/health/status | jq .connection_pool'

# Check database connectivity
psql -h localhost -U user -d database -c "SELECT 1"

# View server logs
tail -f /var/log/mcp/server.log | grep -E "(health|pool|database)"

# Test response time
time curl -s http://localhost:8000/health/status > /dev/null
```

## Best Practices

### 1. Health Check Design
- Keep checks lightweight (<50ms)
- Avoid expensive operations
- Cache results when appropriate
- Use connection pooling

### 2. Monitoring Strategy
- Monitor from multiple locations
- Use both internal and external checks
- Set up redundant monitoring
- Test alert channels regularly

### 3. Alert Fatigue Prevention
- Set appropriate thresholds
- Use alert suppression for maintenance
- Group related alerts
- Provide clear runbooks

### 4. Capacity Planning
- Track utilization trends
- Set up predictive alerts
- Plan for growth
- Regular load testing

## References

- [Health Service Implementation](../../src/services/health_service.py)
- [HealthCheckResponse Model](../../src/models/health.py)
- [Feature Specification](../../specs/011-performance-validation-multi/spec.md)
- [Prometheus Integration Guide](prometheus-integration.md)
- [Incident Response Runbook](incident-response.md)