# Incident Response Runbook

**Version**: 1.0.0
**Last Updated**: 2025-10-13
**Feature**: 011-performance-validation-multi
**Phase**: 8
**Task**: T054
**Constitutional Compliance**: Principle V (Production Quality)

## Overview

This runbook provides step-by-step procedures for responding to production incidents in the dual-server MCP architecture. Each scenario includes detection methods, immediate actions, resolution steps, and post-incident procedures.

## Incident Severity Levels

| Level | Name | Response Time | Examples | Escalation |
|-------|------|---------------|----------|------------|
| **P1** | Critical | 15 min | Complete outage, data loss | Page on-call immediately |
| **P2** | High | 1 hour | Degraded performance, partial outage | Page on-call within 30 min |
| **P3** | Medium | 4 hours | Non-critical features down | Email team |
| **P4** | Low | 24 hours | Minor issues, cosmetic bugs | Next business day |

## Quick Reference

| Incident Type | Severity | First Action | Page |
|---------------|----------|--------------|------|
| Database connection failure | P1 | Check DB status | [Link](#database-connection-failures) |
| Pool exhaustion | P2 | Increase pool size | [Link](#connection-pool-exhaustion) |
| Server crash | P1 | Restart service | [Link](#server-failures) |
| High latency | P2 | Check metrics | [Link](#performance-degradation) |
| Memory leak | P2 | Restart with heap dump | [Link](#memory-issues) |

## Database Connection Failures

### Detection

**Automated Alerts**:
```yaml
- alert: DatabaseConnectionLost
  expr: up{job="postgresql"} == 0
  severity: critical
```

**Manual Detection**:
```bash
# Check database connectivity
psql -h localhost -U mcp_user -d codebase_mcp -c "SELECT 1"

# Check server health
curl http://localhost:8000/health/status | jq '.database_status'
```

### Immediate Actions

1. **Verify database is running**:
```bash
# Check PostgreSQL status
systemctl status postgresql

# Check if port is listening
netstat -an | grep 5432

# Check PostgreSQL logs
tail -f /var/log/postgresql/postgresql-*.log
```

2. **Check network connectivity**:
```bash
# Test connection from app server
nc -zv database-host 5432

# Check DNS resolution
nslookup database-host

# Trace network path
traceroute database-host
```

3. **Verify credentials**:
```bash
# Test with connection string
psql "postgresql://user:password@host:5432/database"

# Check environment variables
env | grep DATABASE_URL
```

### Resolution Steps

#### Scenario 1: Database is down

```bash
# 1. Start PostgreSQL if stopped
sudo systemctl start postgresql

# 2. If fails to start, check disk space
df -h /var/lib/postgresql

# 3. Check for corruption
sudo -u postgres pg_checksums --check -D /var/lib/postgresql/data

# 4. If corrupted, restore from backup
sudo systemctl stop postgresql
sudo -u postgres pg_basebackup -h backup-server -D /var/lib/postgresql/data
sudo systemctl start postgresql
```

#### Scenario 2: Connection pool exhausted

```bash
# 1. Identify blocking queries
psql -c "SELECT pid, now() - pg_stat_activity.query_start AS duration, query
         FROM pg_stat_activity
         WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes';"

# 2. Kill long-running queries
psql -c "SELECT pg_terminate_backend(pid)
         FROM pg_stat_activity
         WHERE pid <> pg_backend_pid()
         AND query_start < now() - interval '10 minutes';"

# 3. Increase connection limit temporarily
psql -c "ALTER SYSTEM SET max_connections = 500;"
psql -c "SELECT pg_reload_conf();"
```

#### Scenario 3: Network issues

```bash
# 1. Restart network service
sudo systemctl restart networking

# 2. Check firewall rules
iptables -L -n | grep 5432

# 3. Add firewall exception if needed
iptables -A INPUT -p tcp --dport 5432 -j ACCEPT

# 4. Check connection limits
sysctl net.core.somaxconn
sysctl -w net.core.somaxconn=1024
```

### Recovery Verification

```bash
# 1. Test database connection
psql -h localhost -U mcp_user -d codebase_mcp -c "SELECT COUNT(*) FROM code_chunks;"

# 2. Verify server health
curl http://localhost:8000/health/status | jq '.status'

# 3. Check metrics
curl http://localhost:8000/metrics | grep database_connections

# 4. Run test query
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test search"}'
```

### Post-Incident Actions

1. **Document timeline** in incident report
2. **Analyze root cause**:
   - Review logs from 1 hour before incident
   - Check for recent deployments
   - Review database metrics
3. **Implement preventive measures**:
   - Add connection pooling monitors
   - Implement circuit breakers
   - Schedule regular connection pool analysis

## Connection Pool Exhaustion

### Detection

**Automated Alerts**:
```yaml
- alert: ConnectionPoolExhausted
  expr: pool_utilization > 0.95
  severity: high
```

**Manual Detection**:
```bash
# Check pool statistics
curl http://localhost:8000/health/status | jq '.connection_pool'

# Monitor pool in real-time
watch -n 1 'curl -s http://localhost:8000/health/status | jq .connection_pool'
```

### Immediate Actions

1. **Increase pool size dynamically**:
```bash
# Set environment variable and restart
export POOL_MAX_SIZE=200
systemctl restart codebase-mcp

# Or use API if available
curl -X POST http://localhost:8000/admin/pool/resize \
  -H "Content-Type: application/json" \
  -d '{"max_size": 200}'
```

2. **Identify pool consumers**:
```sql
-- Find active connections
SELECT
    pid,
    usename,
    application_name,
    client_addr,
    state,
    query_start,
    NOW() - query_start AS duration,
    query
FROM pg_stat_activity
WHERE datname = 'codebase_mcp'
ORDER BY query_start;
```

3. **Kill idle connections**:
```sql
-- Terminate idle connections older than 5 minutes
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'codebase_mcp'
  AND state = 'idle'
  AND state_change < NOW() - INTERVAL '5 minutes';
```

### Resolution Steps

#### Short-term Fix

```bash
# 1. Restart with larger pool
docker-compose down
docker-compose up -d --env POOL_MAX_SIZE=200

# 2. Or modify systemd service
cat > /etc/systemd/system/codebase-mcp.service.d/override.conf << EOF
[Service]
Environment="POOL_MAX_SIZE=200"
EOF
systemctl daemon-reload
systemctl restart codebase-mcp
```

#### Long-term Solution

```python
# Implement adaptive pool sizing
class AdaptivePoolManager:
    def adjust_pool_size(self):
        utilization = self.get_utilization()

        if utilization > 0.9:
            new_size = min(self.max_size * 1.5, 500)
            self.resize_pool(new_size)
            logger.warning(f"Pool resized to {new_size} due to high utilization")

        elif utilization < 0.3 and self.max_size > self.initial_size:
            new_size = max(self.max_size * 0.7, self.initial_size)
            self.resize_pool(new_size)
            logger.info(f"Pool downsized to {new_size} due to low utilization")
```

### Recovery Verification

```bash
# Verify pool is healthy
curl http://localhost:8000/health/status | \
  jq '.connection_pool | select(.pool_utilization < 0.8)'

# Run load test to verify capacity
k6 run -u 20 -d 30s tests/load/quick_test.js
```

## Server Failures

### Detection

**Automated Alerts**:
```yaml
- alert: ServerDown
  expr: up{job="mcp-servers"} == 0
  severity: critical
```

### Immediate Actions

1. **Check server status**:
```bash
# Check if process is running
ps aux | grep -E "(codebase|workflow)-mcp"

# Check systemd status
systemctl status codebase-mcp
systemctl status workflow-mcp

# Check Docker status (if containerized)
docker ps | grep mcp
```

2. **Restart failed server**:
```bash
# Systemd restart
systemctl restart codebase-mcp

# Docker restart
docker restart codebase-mcp

# With health check wait
timeout 30 bash -c 'until curl -f http://localhost:8000/health/status; do sleep 1; done'
```

3. **Check for port conflicts**:
```bash
# Find process using port
lsof -i :8000
netstat -tlnp | grep 8000

# Kill conflicting process
kill -9 $(lsof -t -i:8000)
```

### Resolution Steps

#### Scenario 1: Out of Memory

```bash
# 1. Check memory usage
free -h
dmesg | grep -i "killed process"

# 2. Increase memory limit
# For systemd
cat > /etc/systemd/system/codebase-mcp.service.d/memory.conf << EOF
[Service]
MemoryLimit=4G
MemoryMax=4G
EOF

# For Docker
docker update --memory="4g" --memory-swap="4g" codebase-mcp

# 3. Restart with new limits
systemctl daemon-reload
systemctl restart codebase-mcp
```

#### Scenario 2: Corrupted State

```bash
# 1. Clear cache and temporary files
rm -rf /tmp/mcp-cache/*
rm -rf /var/lib/mcp/temp/*

# 2. Reset application state
redis-cli FLUSHDB

# 3. Restart clean
systemctl stop codebase-mcp
sleep 5
systemctl start codebase-mcp
```

#### Scenario 3: Dependency Issues

```bash
# 1. Check Ollama service (for embeddings)
systemctl status ollama
curl http://localhost:11434/api/tags

# 2. Restart dependencies
systemctl restart ollama
systemctl restart redis

# 3. Verify dependencies are accessible
nc -zv localhost 11434  # Ollama
nc -zv localhost 6379   # Redis
```

### Recovery Verification

```bash
# Full health check
for service in codebase-mcp workflow-mcp; do
  echo "Checking $service..."
  systemctl is-active $service
  curl -s http://localhost:$([ "$service" = "workflow-mcp" ] && echo 8001 || echo 8000)/health/status | jq '.status'
done
```

## Performance Degradation

### Detection

**Automated Alerts**:
```yaml
- alert: HighLatency
  expr: histogram_quantile(0.95, request_duration_seconds) > 0.5
  severity: high
```

### Immediate Actions

1. **Identify bottleneck**:
```bash
# Check CPU usage
top -n 1 | head -20

# Check disk I/O
iostat -x 1 5

# Check network
iftop -i eth0

# Database slow queries
psql -c "SELECT * FROM pg_stat_statements
         WHERE mean_exec_time > 100
         ORDER BY mean_exec_time DESC LIMIT 10;"
```

2. **Enable profiling**:
```python
# Add profiling endpoint
import cProfile
import pstats
import io

@app.route('/debug/profile')
async def profile():
    pr = cProfile.Profile()
    pr.enable()

    # Run sample workload
    await perform_search("test query")

    pr.disable()
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats(20)

    return s.getvalue()
```

### Resolution Steps

#### Quick Wins

```bash
# 1. Clear caches
redis-cli FLUSHALL

# 2. Restart to clear memory
systemctl restart codebase-mcp

# 3. Increase connection pool
export POOL_MAX_SIZE=200
systemctl restart codebase-mcp

# 4. Disable debug logging
export LOG_LEVEL=WARNING
systemctl restart codebase-mcp
```

#### Database Optimization

```sql
-- Update statistics
ANALYZE;

-- Rebuild indexes
REINDEX INDEX CONCURRENTLY idx_chunks_embedding;

-- Clear bloat
VACUUM FULL ANALYZE code_chunks;
```

## Memory Issues

### Detection

```bash
# Monitor memory usage
watch -n 1 'free -h; echo "---"; ps aux | grep mcp | grep -v grep'

# Check for memory leaks
pmap -x $(pgrep -f codebase-mcp) | tail -1
```

### Resolution Steps

1. **Capture heap dump**:
```python
# Add memory profiling
import tracemalloc
import gc

# Start tracing
tracemalloc.start()

# After some operations
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')

for stat in top_stats[:10]:
    print(stat)

# Force garbage collection
gc.collect()
```

2. **Restart with monitoring**:
```bash
# Enable memory profiling
export PYTHONTRACEMALLOC=10
systemctl restart codebase-mcp

# Monitor with lower memory limit
systemd-run --scope -p MemoryLimit=2G --uid=mcp /usr/bin/codebase-mcp
```

## Escalation Paths

### Escalation Matrix

| Time | Severity | Status | Action |
|------|----------|--------|--------|
| 0-15 min | P1 | Unresolved | Page secondary on-call |
| 15-30 min | P1 | Unresolved | Page team lead |
| 30-60 min | P1 | Unresolved | Page engineering manager |
| 60+ min | P1 | Unresolved | Activate incident command |

### Contact Information

```yaml
on_call_rotation:
  primary:
    - name: "Primary On-Call"
      phone: "+1-555-0100"
      slack: "@oncall-primary"

  secondary:
    - name: "Secondary On-Call"
      phone: "+1-555-0101"
      slack: "@oncall-secondary"

  escalation:
    - name: "Team Lead"
      phone: "+1-555-0102"
      slack: "@team-lead"

    - name: "Engineering Manager"
      phone: "+1-555-0103"
      slack: "@eng-manager"
```

## Recovery Procedures

### Full System Recovery

```bash
#!/bin/bash
# full_recovery.sh - Complete system recovery procedure

echo "Starting full system recovery..."

# 1. Stop all services
systemctl stop codebase-mcp workflow-mcp

# 2. Clear all caches
redis-cli FLUSHALL
rm -rf /tmp/mcp-cache/*

# 3. Verify database
psql -U postgres -c "SELECT 1;" || {
    echo "Database down, starting..."
    systemctl start postgresql
}

# 4. Reset connection pools
export POOL_MIN_SIZE=5
export POOL_MAX_SIZE=50

# 5. Start services in order
systemctl start workflow-mcp
sleep 5
systemctl start codebase-mcp

# 6. Wait for health
for i in {1..30}; do
    if curl -f http://localhost:8000/health/status; then
        echo "Codebase-MCP healthy"
        break
    fi
    sleep 2
done

for i in {1..30}; do
    if curl -f http://localhost:8001/health/status; then
        echo "Workflow-MCP healthy"
        break
    fi
    sleep 2
done

# 7. Run smoke tests
python tests/smoke/test_basic_operations.py

echo "Recovery complete!"
```

### Data Recovery

```bash
#!/bin/bash
# data_recovery.sh - Restore from backup

# 1. Stop services
systemctl stop codebase-mcp workflow-mcp

# 2. Backup current (possibly corrupted) data
pg_dump codebase_mcp > backup_corrupted_$(date +%Y%m%d_%H%M%S).sql

# 3. Restore from last known good backup
psql -U postgres -c "DROP DATABASE IF EXISTS codebase_mcp;"
psql -U postgres -c "CREATE DATABASE codebase_mcp;"
psql -U postgres codebase_mcp < /backups/last_known_good.sql

# 4. Verify restoration
psql -U postgres codebase_mcp -c "SELECT COUNT(*) FROM code_chunks;"

# 5. Restart services
systemctl start codebase-mcp workflow-mcp
```

## Post-Incident Procedures

### Incident Report Template

```markdown
# Incident Report - [DATE]

## Summary
- **Incident ID**: INC-2025-001
- **Severity**: P1/P2/P3/P4
- **Duration**: XX minutes
- **Impact**: [Users affected, features impacted]

## Timeline
- **HH:MM** - Alert triggered
- **HH:MM** - On-call engineer paged
- **HH:MM** - Initial investigation started
- **HH:MM** - Root cause identified
- **HH:MM** - Fix deployed
- **HH:MM** - Service restored
- **HH:MM** - Incident closed

## Root Cause
[Detailed explanation of what caused the incident]

## Resolution
[Steps taken to resolve the incident]

## Impact
- **Users Affected**: X
- **Requests Failed**: Y
- **Data Loss**: None/Describe

## Lessons Learned
1. What went well
2. What could be improved
3. Action items

## Action Items
- [ ] Update monitoring for earlier detection
- [ ] Add runbook for this scenario
- [ ] Implement preventive measures
```

### Post-Mortem Meeting

**Agenda**:
1. Timeline review (10 min)
2. Root cause analysis (20 min)
3. Impact assessment (10 min)
4. Improvement discussion (20 min)
5. Action items assignment (10 min)

**Participants**:
- On-call engineer
- Team lead
- Service owners
- SRE representative

## Automation Scripts

### Health Check Loop

```bash
#!/bin/bash
# health_monitor.sh - Continuous health monitoring

while true; do
    for service in codebase-mcp:8000 workflow-mcp:8001; do
        IFS=':' read -r name port <<< "$service"

        if ! curl -sf http://localhost:$port/health/status > /dev/null; then
            echo "ALERT: $name is unhealthy!"
            # Send alert
            curl -X POST https://hooks.slack.com/services/YOUR/WEBHOOK/URL \
                -H "Content-Type: application/json" \
                -d "{\"text\":\"🚨 $name health check failed!\"}"
        fi
    done
    sleep 30
done
```

### Automatic Recovery

```python
#!/usr/bin/env python3
"""auto_recovery.py - Automatic incident recovery"""

import subprocess
import time
import requests
from typing import Dict, Callable

class AutoRecovery:
    def __init__(self):
        self.recovery_strategies = {
            "database_connection": self.recover_database,
            "pool_exhausted": self.recover_pool,
            "high_memory": self.recover_memory,
            "server_down": self.recover_server
        }

    def detect_issue(self) -> str:
        """Detect what type of issue is occurring."""
        try:
            response = requests.get("http://localhost:8000/health/status")
            health = response.json()

            if health["database_status"] == "disconnected":
                return "database_connection"

            if health["connection_pool"]["pool_utilization"] > 0.95:
                return "pool_exhausted"

            # Check memory usage
            mem_check = subprocess.run(
                ["free", "-b"],
                capture_output=True,
                text=True
            )
            # Parse memory usage...

        except requests.exceptions.RequestException:
            return "server_down"

        return "unknown"

    def recover_database(self):
        """Recover database connection."""
        subprocess.run(["systemctl", "restart", "postgresql"])
        time.sleep(5)

    def recover_pool(self):
        """Recover from pool exhaustion."""
        # Increase pool size
        subprocess.run([
            "systemctl", "set-environment",
            "POOL_MAX_SIZE=200"
        ])
        subprocess.run(["systemctl", "restart", "codebase-mcp"])

    def recover_memory(self):
        """Recover from high memory usage."""
        subprocess.run(["systemctl", "restart", "codebase-mcp"])

    def recover_server(self):
        """Recover from server down."""
        subprocess.run(["systemctl", "start", "codebase-mcp"])

    def run(self):
        """Main recovery loop."""
        issue = self.detect_issue()

        if issue in self.recovery_strategies:
            print(f"Detected issue: {issue}")
            print(f"Attempting recovery...")

            self.recovery_strategies[issue]()

            # Verify recovery
            time.sleep(10)
            if self.verify_health():
                print("Recovery successful!")
            else:
                print("Recovery failed, escalating...")
                self.escalate()

    def verify_health(self) -> bool:
        """Verify system is healthy."""
        try:
            response = requests.get("http://localhost:8000/health/status")
            return response.json()["status"] == "healthy"
        except:
            return False

    def escalate(self):
        """Escalate to on-call."""
        # Send page to on-call
        subprocess.run([
            "curl", "-X", "POST",
            "https://api.pagerduty.com/incidents",
            "-H", "Authorization: Token token=YOUR_TOKEN",
            "-H", "Content-Type: application/json",
            "-d", '{"incident": {"type": "incident", "title": "Auto-recovery failed"}}'
        ])

if __name__ == "__main__":
    recovery = AutoRecovery()
    recovery.run()
```

## References

- [Health Monitoring Guide](health-monitoring.md)
- [Performance Tuning Guide](performance-tuning.md)
- [Resilience Validation Report](resilience-validation-report.md)
- [Database Operations](../database/operations.md)
- [Constitutional Principles](../../.specify/memory/constitution.md)