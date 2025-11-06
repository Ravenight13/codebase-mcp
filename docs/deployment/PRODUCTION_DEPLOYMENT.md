# Production Deployment Guide

## Overview

Run Codebase MCP Server in production using Docker containers with external PostgreSQL and Ollama services.

## Prerequisites

- Docker installed (Engine 20.10+)
- External PostgreSQL 14+ instance (or managed service)
- External Ollama service (or self-hosted)
- Network connectivity between containers and external services

## Build Production Image

```bash
# Build image for current version
docker build -t codebase-mcp:$(git rev-parse --short HEAD) .

# Verify image size (must be <500 MB)
docker images codebase-mcp
# Output should show: ~320-390 MB
```

## Run Production Container

### With External Services

```bash
docker run -d \
  --name codebase-mcp-prod \
  -e REGISTRY_DATABASE_URL="postgresql+asyncpg://user:PASSWORD@db.prod.com:5432/codebase_prod" \
  -e OLLAMA_BASE_URL="http://ollama.internal.prod.com:11434" \
  --restart unless-stopped \
  codebase-mcp:latest
```

### With Docker Compose (Multi-Instance)

```yaml
services:
  codebase-mcp-1:
    image: codebase-mcp:latest
    environment:
      REGISTRY_DATABASE_URL: postgresql+asyncpg://user:PASSWORD@db.prod.com/codebase_prod
      OLLAMA_BASE_URL: http://ollama.internal.com:11434
    restart: unless-stopped

  codebase-mcp-2:
    image: codebase-mcp:latest
    environment:
      REGISTRY_DATABASE_URL: postgresql+asyncpg://user:PASSWORD@db.prod.com/codebase_prod
      OLLAMA_BASE_URL: http://ollama.internal.com:11434
    restart: unless-stopped
```

## Configuration

### Required Environment Variables

| Variable | Example | Notes |
|----------|---------|-------|
| `REGISTRY_DATABASE_URL` | `postgresql+asyncpg://user:pass@db.prod.com:5432/codebase_prod` | Must be secure, use secrets management |
| `OLLAMA_BASE_URL` | `http://ollama.internal.com:11434` | Internal service URL |

### Optional Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `OLLAMA_EMBEDDING_MODEL` | `nomic-embed-text` | Embedding model name |
| `EMBEDDING_BATCH_SIZE` | `32` | Batch size for embeddings |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `DATABASE_POOL_MAX_SIZE` | `20` | Max database connections |

## Health Checks

```bash
# Check container health
docker inspect codebase-mcp-prod --format='{{.State.Health.Status}}'
# Output: healthy or unhealthy

# View logs
docker logs codebase-mcp-prod

# Execute command in container
docker exec codebase-mcp-prod pgrep -f "python.*server_fastmcp"
```

## Scaling

Multiple instances share PostgreSQL and Ollama:

```bash
# Start 3 instances
for i in 1 2 3; do
  docker run -d \
    --name codebase-mcp-$i \
    -e REGISTRY_DATABASE_URL="postgresql+asyncpg://user:pass@db.prod.com/codebase_prod" \
    -e OLLAMA_BASE_URL="http://ollama.internal.com:11434" \
    --restart unless-stopped \
    codebase-mcp:latest
done

# Load balance traffic across instances
# (Use nginx, HAProxy, or cloud load balancer)
```

## Monitoring

### Health Check Endpoint

```bash
# Check process is running (Docker HEALTHCHECK)
docker exec codebase-mcp-prod pgrep -f "python.*server_fastmcp"

# Check database connectivity
docker exec codebase-mcp-prod python -c \
  "from sqlalchemy import create_engine; \
   engine = create_engine('$REGISTRY_DATABASE_URL'); \
   print('Database OK' if engine.connect() else 'Database FAIL')"
```

### Logs

```bash
# Follow logs
docker logs -f codebase-mcp-prod

# Search logs
docker logs codebase-mcp-prod | grep ERROR

# Export logs
docker logs codebase-mcp-prod > codebase-mcp-prod.log
```

## Troubleshooting

**Container won't start**: Check logs for database/Ollama connectivity issues
**Health check failing**: Verify network access to external services
**High memory usage**: Adjust DATABASE_POOL_MAX_SIZE and EMBEDDING_BATCH_SIZE

## Upgrades

```bash
# Build new version
docker build -t codebase-mcp:v2.0.0 .

# Stop old container
docker stop codebase-mcp-prod

# Remove old container
docker rm codebase-mcp-prod

# Start new version
docker run -d --name codebase-mcp-prod ... codebase-mcp:v2.0.0
```

