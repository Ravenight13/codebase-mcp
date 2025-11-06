# Health Checks Configuration

## Overview

Health checks monitor service availability and trigger restarts/alerts automatically.

## Service Health Checks

### PostgreSQL

```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U postgres"]
  start_period: 10s   # Grace period after start
  interval: 10s       # Check every 10 seconds
  timeout: 5s         # Fail if check takes >5s
  retries: 5          # Mark unhealthy after 5 failures
```

**Status**: Healthy when database accepts connections
**Timeout**: Database unavailable >30 seconds

### Ollama

```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -f http://localhost:11434/api/tags || exit 1"]
  start_period: 20s   # Grace period (model download)
  interval: 30s       # Check every 30 seconds
  timeout: 5s         # Fail if check takes >5s
  retries: 3          # Mark unhealthy after 3 failures
```

**Status**: Healthy when API responds
**Timeout**: Ollama unavailable >90 seconds

### Codebase MCP Server

```yaml
healthcheck:
  test: ["CMD", "pgrep", "-f", "python.*server_fastmcp"]
  start_period: 20s   # Grace period for startup
  interval: 30s       # Check every 30 seconds
  timeout: 5s         # Fail if check takes >5s
  retries: 3          # Mark unhealthy after 3 failures
```

**Status**: Healthy when process is running
**Timeout**: Server crashed/stopped

## Monitoring Health

### Via Docker Compose

```bash
# Check all services
docker-compose ps
# STATUS column shows: Up (healthy), Up (unhealthy), Up (health: starting)

# Specific service health
docker-compose ps codebase-mcp

# Watch in real-time
watch -n 1 'docker-compose ps'
```

### Via Docker CLI

```bash
# Check container health
docker inspect <container_name> --format='{{.State.Health.Status}}'

# Get health details
docker inspect <container_name> --format='{{json .State.Health}}' | jq

# View health check history
docker inspect <container_name> | grep -A 50 "Health"
```

### Via Logs

```bash
# View health check failures
docker-compose logs <service> | grep -i health

# Monitor health checks
docker-compose logs -f <service> | grep -i "health\|failed"
```

## Configuring Health Checks

### Customize Timeout

If service is slow to respond, increase timeout:

```yaml
codebase-mcp:
  healthcheck:
    timeout: 10s    # Was 5s
```

### Customize Interval

For lighter load, increase check interval:

```yaml
ollama:
  healthcheck:
    interval: 60s   # Was 30s
```

### Customize Start Grace Period

For slow startup services:

```yaml
postgresql:
  healthcheck:
    start_period: 30s  # Was 10s
```

### Disable Health Check

```yaml
codebase-mcp:
  healthcheck:
    disable: true
```

## Health Check Failures

### PostgreSQL Unhealthy

**Causes**:
- Database initialization still running (wait longer)
- Disk full
- Resource exhaustion

**Fix**:
```bash
docker-compose restart postgresql
docker-compose logs postgresql

# Check disk
docker exec <postgres_container> df -h
```

### Ollama Unhealthy

**Causes**:
- Model downloading (first run, can take 5+ minutes)
- Network issues accessing external sources
- API timeout

**Fix**:
```bash
# View logs
docker logs <ollama_container>

# Check network
docker-compose exec ollama ping 8.8.8.8

# Increase timeout in compose file
```

### MCP Server Unhealthy

**Causes**:
- Startup time exceeds grace period
- Process crashes immediately
- Database/Ollama unavailable

**Fix**:
```bash
# Check logs
docker-compose logs codebase-mcp

# Increase grace period
# Or fix underlying issue (database, Ollama)
```

## Restart Policies

### Development

```yaml
# Restart on failure (for development)
restart_policy:
  condition: on-failure
  max_retries: 3
```

### Production

```yaml
# Restart unless explicitly stopped
restart_policy:
  condition: unless-stopped
```

## Docker Restart Behavior

```bash
# Stop a specific service (won't auto-restart)
docker-compose stop codebase-mcp

# Restart service
docker-compose start codebase-mcp

# Full restart (stop + start)
docker-compose restart codebase-mcp

# Kill unhealthy services (restart with compose)
docker-compose up --force-recreate
```

