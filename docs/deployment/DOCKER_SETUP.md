# Docker Setup Guide - Local Development

**Purpose**: Get the entire Codebase MCP Server stack running locally with `docker-compose up`

## Quick Start (3 steps)

### 1. Copy environment template
```bash
cp .env.example .env
```

### 2. Start the stack
```bash
docker-compose up
```

**Expected output**:
```
postgresql   | ... database system is ready to accept connections
ollama       | ... Listening on 127.0.0.1:11434
codebase-mcp | Running database migrations...
codebase-mcp | Server ready to accept connections
```

**Wait time**: All services should be healthy within 120 seconds

### 3. Verify and use
```bash
# Check all services are healthy
docker-compose ps
# Output should show all services as "Up (healthy)"

# Run tests
docker-compose exec codebase-mcp pytest tests/integration/ -v
```

## What Gets Started?

| Service | Image | Port | Purpose | Health Check |
|---------|-------|------|---------|---|
| **postgresql** | postgres:14 | 5432 | Code repository database | `pg_isready` |
| **ollama** | ollama/ollama:latest | 11434 | Embedding service | HTTP GET /api/tags |
| **codebase-mcp** | built from Dockerfile | (stdio) | MCP server | pgrep process check |

## Services Start in Order

```
1. PostgreSQL (required by everything)
   ↓
2. Ollama (depends on PostgreSQL)
   ↓
3. MCP Server (depends on both, runs migrations)
```

The `depends_on` and `healthcheck` directives in docker-compose.yml ensure proper startup order.

## File Structure

```
workspace/
├── .env                 # Configuration (created from .env.example)
├── .env.example         # Template - DO NOT EDIT, copy to .env
├── Dockerfile           # Production image definition
├── docker-compose.yml   # Dev stack orchestration
├── scripts/docker/
│   └── entrypoint.sh    # Container startup script
└── docs/deployment/
    └── DOCKER_SETUP.md  # This file
```

## Development Workflow

### Hot Reload (Change Code Without Restart)

The source code directory is mounted as a volume with hot reload enabled:

```yaml
volumes:
  - .:/workspace:cached  # Source code volume mount
```

**Try it**:
```bash
# Terminal 1: Watch logs
docker-compose logs -f codebase-mcp

# Terminal 2: Modify source file
echo "# New comment" >> src/mcp/server_fastmcp.py

# Terminal 1: Should see no container restart (file synced immediately)
```

### Running Commands Inside Container

```bash
# Run tests
docker-compose exec codebase-mcp pytest tests/ -v

# View logs
docker-compose logs codebase-mcp

# Open shell
docker-compose exec codebase-mcp /bin/bash

# Run Python interactively
docker-compose exec codebase-mcp python
```

## Common Tasks

### Restart Services (Keep Data)

```bash
# Restart only the MCP server (keep PostgreSQL and Ollama running)
docker-compose restart codebase-mcp

# Restart all services
docker-compose restart

# Graceful stop and restart
docker-compose stop
docker-compose start
```

### Full Reset (Delete All Data)

```bash
# Stop and remove containers, delete volumes
docker-compose down -v

# Start fresh
docker-compose up
```

### View Database

```bash
# Connect to PostgreSQL
docker-compose exec postgresql psql -U postgres -d codebase_mcp

# List tables
\dt

# Count indexed files
SELECT COUNT(*) FROM code_files;

# Exit
\q
```

### Check Service Health

```bash
# Status of all services
docker-compose ps

# View specific service logs
docker-compose logs postgresql
docker-compose logs ollama
docker-compose logs codebase-mcp

# Follow logs in real-time
docker-compose logs -f codebase-mcp

# Inspect service details
docker inspect codebase-mcp
```

## Environment Variables

See `.env.example` for all available options.

**Key variables**:
- `REGISTRY_DATABASE_URL`: PostgreSQL connection string
- `OLLAMA_BASE_URL`: Ollama service URL
- `POSTGRES_PASSWORD`: Database admin password
- `LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR

## Troubleshooting

### "Port 5432 already in use"

**Problem**: PostgreSQL container can't bind to port 5432 (likely local PostgreSQL running)

**Solution**: Change port in docker-compose.yml:
```yaml
postgresql:
  ports:
    - "5433:5432"  # Use 5433 instead of 5432
```

Then update `.env`:
```bash
REGISTRY_DATABASE_URL=postgresql+asyncpg://postgres:dev-password@postgresql:5432/codebase_mcp
# ^ Keep as 5432 (internal container port), or use postgresql hostname
```

### "All services starting but codebase-mcp unhealthy"

**Possible causes**:
1. PostgreSQL not ready: Wait 30+ seconds for PostgreSQL health check to pass
2. Migrations failed: Check logs with `docker-compose logs codebase-mcp`
3. Ollama model not downloaded: First run downloads ~100MB model, wait for completion

**Debug**:
```bash
# Check PostgreSQL is actually healthy
docker-compose ps

# See detailed logs
docker-compose logs codebase-mcp

# Check migrations ran
docker-compose exec codebase-mcp ls -la alembic/
```

### "docker-compose: command not found"

**Solution**: Install Docker Compose:
- **Linux**: `sudo apt-get install docker-compose` or `pip install docker-compose`
- **macOS/Windows**: Included with Docker Desktop

### "Cannot connect to Docker daemon"

**Solution**: Start Docker:
- **Linux**: `sudo systemctl start docker`
- **macOS**: Open Docker Desktop application
- **Windows**: Start Docker Desktop

### Volume mount permissions (Windows/WSL2)

**Problem**: Files inside container are root-owned, hard to edit from Windows

**Solution**: 
- Ensure repository is cloned in WSL2 filesystem (`/home/user/...`), not Windows filesystem (`/mnt/c/...`)
- Files are synced correctly with proper permissions

### Ollama model download slow

**Problem**: First run of `docker-compose up` takes 5+ minutes (downloading embedding model)

**Expected**: Ollama downloads `nomic-embed-text` (~100 MB) on first run

**Check progress**:
```bash
docker-compose logs ollama | grep -i download
```

**Subsequent runs**: Use cached model from `ollama_data` volume (instant)

## Performance Tuning

### macOS Docker Desktop Volume Mount Performance

Default volume mounts on macOS can be slow. Options to speed up:

**1. Use `:cached` mode (recommended, already in docker-compose.yml)**
```yaml
volumes:
  - .:/workspace:cached
```

**2. Use delegated mode (faster writes, slower reads)**
```yaml
volumes:
  - .:/workspace:delegated
```

**3. Use Docker Sync (separate tool)**
```bash
# Install
gem install docker-sync

# Start sync
docker-sync-stack start
```

## Next Steps

- ✅ **Now**: `docker-compose up` to start stack
- ✅ **Then**: Run `docker-compose exec codebase-mcp pytest` to verify tests pass
- ✅ **Continue**: Modify code and test changes (hot reload works)
- ✅ **When done**: `docker-compose down -v` to clean up

## Documentation

- **Production Deployment**: See [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md)
- **CI/CD Integration**: See [DOCKER_SETUP.md](DOCKER_SETUP.md) CI/CD section
- **Troubleshooting**: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Health Checks**: See [HEALTH_CHECKS.md](HEALTH_CHECKS.md)

