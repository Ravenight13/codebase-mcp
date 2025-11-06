# Troubleshooting Guide

## Common Issues

### Port Conflicts

**Problem**: "Port 5432 already in use" or similar

**Solution**:
1. Check what's using the port: `lsof -i :5432`
2. Either:
   - Stop local service: `sudo systemctl stop postgresql`
   - Change docker-compose port: Change `"5432:5432"` to `"5433:5432"`

### Services Not Starting

**Problem**: Some services unhealthy after 2+ minutes

**Check**:
```bash
docker-compose ps  # See which services are unhealthy
docker-compose logs <service>  # View service logs
```

**PostgreSQL issues**:
- Wait longer (health check: 10s initial wait)
- Check disk space: `docker exec <postgres_container> df -h`

**Ollama issues**:
- First run downloads 100+ MB model (slow)
- Check: `docker logs <ollama_container> | grep download`

**MCP Server issues**:
- Check logs: `docker-compose logs codebase-mcp`
- Verify DB ready: `docker-compose exec postgresql psql -U postgres -c "SELECT 1"`

### Database Migration Failures

**Problem**: "ERROR: Database migrations failed"

**Solution**:
```bash
# Check migration status
docker-compose exec codebase-mcp alembic current

# View available migrations
docker-compose exec codebase-mcp alembic history

# Manually run migrations
docker-compose exec codebase-mcp alembic upgrade head

# Downgrade if needed
docker-compose exec codebase-mcp alembic downgrade -1
```

### Connection Refused Errors

**Problem**: "connection refused" when accessing services

**Check**:
```bash
# Verify service is running
docker-compose ps

# Check network connectivity
docker-compose exec codebase-mcp ping postgresql  # Should work
docker-compose exec codebase-mcp curl http://ollama:11434/api/tags  # Should work
```

### Out of Memory

**Problem**: OOMKilled container or slow performance

**Solution**:
```bash
# Check resource limits
docker stats

# Adjust compose resource limits:
services:
  codebase-mcp:
    deploy:
      resources:
        limits:
          memory: 2G
```

### Volume Permission Issues (macOS)

**Problem**: Files in container are owned by root, can't edit from host

**Solution**:
- Ensure repository cloned in WSL2 filesystem (not Windows filesystem)
- Use `:cached` mode in volume mount (already configured)

### Ollama Model Download Stuck

**Problem**: Ollama downloading model for hours

**Check**:
```bash
# Monitor download
docker logs <ollama_container> | tail -f

# Check space
docker exec <ollama_container> df -h
```

**Workaround**: Pre-download model on host, mount volume

## Debug Procedures

### Enable Debug Logging

```bash
# Set DEBUG log level
docker-compose down
echo "LOG_LEVEL=DEBUG" >> .env
docker-compose up
```

### Shell Access to Container

```bash
# Enter container shell
docker-compose exec codebase-mcp /bin/bash

# Or specific service
docker-compose exec postgresql /bin/bash
```

### Database Inspection

```bash
# Connect to PostgreSQL
docker-compose exec postgresql psql -U postgres -d codebase_mcp

# Inside psql:
\dt                    # List tables
SELECT COUNT(*) FROM code_files;  # Count rows
\l                     # List databases
\q                     # Quit
```

### View Full Configuration

```bash
# Show running container config
docker-compose config

# Inspect specific service
docker inspect <container_name>
```

## Getting Help

1. Check logs: `docker-compose logs <service>`
2. Check status: `docker-compose ps`
3. Verify connectivity: `docker-compose exec <service> ping <other_service>`
4. Consult guides: DOCKER_SETUP.md, PRODUCTION_DEPLOYMENT.md
5. Review quickstart.md test scenarios

