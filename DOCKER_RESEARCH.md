# Docker Best Practices Research: Codebase MCP Server Containerization

**Document**: Comprehensive research on Docker containerization strategies  
**Scope**: All 5 Docker-related areas  
**Context**: Codebase MCP Server - Python 3.11+ FastMCP framework, PostgreSQL 14+, Ollama  
**Date**: 2025-11-06

---

## 1. Multi-Stage Dockerfile Optimization

### 1.1 Base Image Selection

**Context**: Codebase MCP uses Python 3.11+ with compilation dependencies (tree-sitter, pgvector, asyncpg).

#### Option A: python:3.12-slim (RECOMMENDED)
```dockerfile
FROM python:3.12-slim as base
```

**Pros**:
- Base size: ~150MB (slim: 130MB vs standard: 910MB)
- Includes essential build tools for compilation (gcc, make)
- Well-supported upstream image
- Balances minimal footprint with practical dev tooling

**Cons**:
- Includes non-essential tools (curl, git, etc.) for production

**Best for**: MCP server - good balance of build capability and final size

#### Option B: python:3.12-alpine
```dockerfile
FROM python:3.12-alpine as base
```

**Pros**:
- Minimal base size: ~50MB
- Excellent final image size (<300MB target achievable)
- Reduced attack surface

**Cons**:
- Musl libc instead of glibc (binary compatibility issues)
- Missing system libraries for tree-sitter compilation
- Requires `apk add` for build dependencies (adds complexity)
- Known issues with pgvector on Alpine (requires special handling)
- Slower builds due to Alpine's package availability

**Best for**: Simple services without native compilation, microservices

#### Option C: python:3.12-distroless
```dockerfile
FROM python:3.12-distroless as base
```

**Pros**:
- Extremely minimal: ~20MB base
- No shell, no package manager = maximal security
- Excellent for hardened environments

**Cons**:
- Cannot run build steps (gcc, make required)
- No shell for debugging or health checks
- Cannot run migrations directly
- Requires separate build image
- Complex layering strategy

**Best for**: Hardened production deployments (not initial implementation)

### Recommendation for MCP Server

**Primary Choice**: `python:3.12-slim`

Rationale:
- Supports direct compilation of tree-sitter, pgvector, asyncpg without special handling
- Includes system packages needed for database drivers (libpq-dev dependencies)
- Reasonable final image size (350-450MB achievable)
- Simplest multi-stage pattern with reliable builds
- Future migration to distroless possible after build optimization

### 1.2 Multi-Stage Build Strategy

#### Recommended Pattern: Builder + Runtime Separation

```dockerfile
# Stage 1: Builder (compilation environment)
FROM python:3.12-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first (for layer caching)
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime (stripped dependencies only)
FROM python:3.12-slim as runtime

WORKDIR /app

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy compiled Python packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY src/ src/
COPY migrations/ migrations/
COPY alembic.ini .
COPY server_fastmcp.py .

# Non-root user
RUN useradd -m -u 1000 mcp
USER mcp

# Health check script
COPY docker/healthcheck.sh /
RUN chmod +x /healthcheck.sh

EXPOSE 9999
HEALTHCHECK CMD /healthcheck.sh || exit 1

ENTRYPOINT ["python", "server_fastmcp.py"]
```

**Key Principles**:

1. **Dependency Caching Layers**
   - Copy requirements first, install dependencies
   - Application code copied last (changes frequently)
   - Rebuild only necessary layers on code changes

2. **Clean Compilation**
   - Build dependencies (gcc, make) in builder stage
   - Runtime stage includes ONLY runtime dependencies (libpq5, not libpq-dev)
   - Reduces runtime image size by 30-50%

3. **Non-Root User**
   - Create `mcp` user (UID 1000, GID 1000)
   - Improves security posture
   - Prevents accidental file permission issues

4. **Minimal Layer Count**
   - Each RUN instruction creates a layer (use `&&` for chaining)
   - Combine apt-get update + install + cleanup in single layer
   - Don't create unnecessary layers

### 1.3 Layer Ordering for Cache Efficiency

**Optimal Order**:

```
1. Base image FROM
2. Metadata (WORKDIR, USER setup)
3. System dependencies (apt-get, never changes during development)
4. Build tools (gcc, make, only in builder)
5. Python requirements (changes per dependency update)
6. Application source code (changes frequently during development)
7. Entry point configuration (rarely changes)
```

**Impact on Build Times**:
- Same code change: 2-3 seconds (only code layer rebuilt)
- Dependency change: 30-45 seconds (includes pip install)
- System dependency change: 60+ seconds (rebuilds from base)

### 1.4 Target Image Size

**Goal**: <500MB per specification

**Breakdown for MCP Server**:
- python:3.12-slim base: 150MB
- Python dependencies (compiled): 150-200MB
- Application code: <10MB
- Runtime libraries (libpq, psql): 20-30MB
- Total: 320-390MB

**How to Achieve**:

```dockerfile
# 1. Avoid large unnecessary packages
RUN pip install --no-cache-dir --no-optional-deps ...

# 2. Remove test files from installed packages
RUN find /root/.local -type d -name tests -exec rm -rf {} + 2>/dev/null || true

# 3. Use wheels-only for faster installs
RUN pip install --user --only-binary=:all: -r requirements.txt

# 4. Verify final size
# docker build -t codebase-mcp . && docker image ls codebase-mcp
# Expected: <500MB
```

---

## 2. Health Check Implementation for Stdio MCP Servers

### 2.1 Challenge: Stdio Services Have No HTTP

MCP servers use stdin/stdout/stderr for protocol communication. Unlike HTTP servers (port-based health checks), stdio servers require a different approach.

### 2.2 Available Strategies

#### Strategy A: Custom Health Check Script (RECOMMENDED)

Docker's HEALTHCHECK instruction can run any executable:

```dockerfile
COPY docker/healthcheck.sh /healthcheck.sh
RUN chmod +x /healthcheck.sh

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD /healthcheck.sh
```

**Implementation: /docker/healthcheck.sh**

```bash
#!/bin/bash
set -e

# Method 1: Check process is running
if ! pgrep -f "python server_fastmcp.py" > /dev/null; then
    echo "ERROR: Server process not running"
    exit 1
fi

# Method 2: Test MCP via stdio (if possible)
# This requires spawning a test client that sends a JSON-RPC request
# and verifies response (more complex, requires test utilities in container)

# Method 3: Check database connectivity (indicative of health)
if ! timeout 2 python -c "
import asyncio
from src.database import Database
asyncio.run(Database.create_pool())
print('Database healthy')
" 2>/dev/null; then
    echo "ERROR: Database not responding"
    exit 1
fi

# Method 4: Check Ollama connectivity
if ! timeout 2 curl -s http://ollama:11434/api/tags > /dev/null; then
    echo "WARN: Ollama not responding (may recover)"
    # Don't exit here - server can still start without Ollama initially
fi

echo "OK"
exit 0
```

**Pros**:
- No HTTP server needed
- Uses existing Python code (can reuse database/service logic)
- Can test actual functionality (not just process existence)
- Docker understands the health state

**Cons**:
- Adds complexity (bash script, Python subprocess)
- Every health check spawns processes (resource cost)
- May slow startup if checks are blocking

#### Strategy B: MCP Tool-Based Health (FUTURE)

Once `/health` MCP tool exists, health checks could use it:

```bash
#!/bin/bash
# Future approach: call MCP tool via JSON-RPC stdio
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | \
    timeout 2 python -m src.mcp.stdio_server | grep -q "search_code" && exit 0 || exit 1
```

**Status**: Out of scope for initial Docker support (health endpoints exist in perf validation branch)

#### Strategy C: Sidekcar Health Checker (ADVANCED)

Separate health check container that polls the MCP server:

```yaml
services:
  mcp-server:
    # ...
  health-checker:
    image: health-checker:1.0
    environment:
      MCP_SERVER_HOST: mcp-server
      MCP_SERVER_PID: # requires pid mode
    depends_on:
      - mcp-server
```

**Status**: Overcomplicated for current use case

### 2.3 Recommended Health Check Configuration

```dockerfile
# Minimal process check (lightweight)
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD pgrep -f "python server_fastmcp.py" || exit 1
```

**Configuration Rationale**:
- `--start-period=15s`: Give container 15s to start (db migrations take ~5-10s)
- `--interval=30s`: Check every 30 seconds (reasonable for long-running process)
- `--timeout=5s`: Abort if check takes >5 seconds (prevent hanging)
- `--retries=3`: Allow 3 consecutive failures before marking unhealthy

**Better Option: Composite Check**

```dockerfile
# Verify process AND service readiness
COPY docker/healthcheck.sh /
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD /healthcheck.sh
```

**docker/healthcheck.sh**:
```bash
#!/bin/bash
set -e

# Lightweight checks that complete <5 seconds
pgrep -f "python server_fastmcp.py" > /dev/null || exit 1

# Optional: verify database is reachable (add if needed)
# timeout 2 psql -h ${REGISTRY_DATABASE_URL} -c "SELECT 1" > /dev/null || exit 1

exit 0
```

### 2.4 Health Check Exit Codes

| Code | Meaning | Docker Behavior |
|------|---------|-----------------|
| 0 | Healthy | Increments healthy counter |
| 1 | Unhealthy | Increments unhealthy counter |
| Other | Status unknown | Ignored by Docker |

---

## 3. Docker-Compose for Development

### 3.1 Service Dependency Management

**Order of Service Startup**:

```yaml
services:
  postgres:
    # Must start first - other services depend on it
    healthcheck: ...
    
  ollama:
    # Should wait for postgres, but can start in parallel
    depends_on:
      postgres:
        condition: service_healthy
    
  mcp-server:
    # Must wait for both postgres and ollama
    depends_on:
      postgres:
        condition: service_healthy
      ollama:
        condition: service_healthy
```

**Health Check Strategy**:

```yaml
postgres:
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U postgres"]
    interval: 10s
    timeout: 5s
    retries: 5
    start_period: 10s

ollama:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
    interval: 30s
    timeout: 5s
    retries: 3
    start_period: 30s  # Ollama takes time to start

mcp-server:
  depends_on:
    postgres:
      condition: service_healthy
    ollama:
      condition: service_healthy
  healthcheck:
    test: ["CMD", "pgrep", "-f", "python server_fastmcp.py"]
    interval: 30s
    timeout: 5s
    retries: 3
    start_period: 20s
```

### 3.2 Volume Mounting Strategy for Development

```yaml
mcp-server:
  volumes:
    # Application source (hot reload on changes)
    - ./src:/app/src:cached
    - ./migrations:/app/migrations:cached
    - ./server_fastmcp.py:/app/server_fastmcp.py:cached
    
    # Configuration
    - ./.env:/app/.env:ro
    - ./alembic.ini:/app/alembic.ini:ro
    
    # Persistent data (survives container restart)
    - db-data:/var/lib/postgresql/data
    - ollama-data:/root/.ollama
  
  # Mount options for performance (macOS/Docker Desktop)
  # Add to top-level compose file
```

**Volume Mount Modes**:

- `:cached` - Async data sync from host→container (good for source code)
- `:delegated` - Async sync from container→host (good for outputs)
- Default (sync) - Immediate bi-directional sync (good for config)
- `:ro` - Read-only (good for configs, prevents accidental modification)

### 3.3 Environment Variable Handling

```yaml
mcp-server:
  environment:
    # Database
    REGISTRY_DATABASE_URL: "postgresql+asyncpg://postgres:postgres@postgres:5432/codebase_mcp"
    
    # Ollama (docker-compose network)
    OLLAMA_BASE_URL: "http://ollama:11434"
    
    # Logging
    LOG_LEVEL: "DEBUG"
    LOG_FILE: "/tmp/codebase-mcp.log"
    
    # Development
    PYTHONUNBUFFERED: "1"
    PYTHONDONTWRITEBYTECODE: "1"
  
  env_file:
    - .env.example  # Provides defaults
    - .env          # Overrides (not in git)
```

**Pattern: .env.example (checked in)**
```bash
# Database
REGISTRY_DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/codebase_mcp
REGISTRY_DATABASE_POOL_SIZE=5

# Ollama
OLLAMA_BASE_URL=http://ollama:11434

# Logging
LOG_LEVEL=INFO
LOG_FILE=/tmp/codebase-mcp.log
```

### 3.4 Networking and Port Configuration

```yaml
services:
  postgres:
    ports:
      - "5432:5432"  # Expose for local psql clients
    networks:
      - backend

  ollama:
    ports:
      - "11434:11434"  # Expose for ollama CLI
    networks:
      - backend

  mcp-server:
    # MCP uses stdio, no port exposed
    networks:
      - backend

networks:
  backend:
    driver: bridge
    name: codebase-mcp-network
```

**Service Discovery in Docker Compose**:
- `postgres:5432` - Accessible as `postgres` hostname within network
- `ollama:11434` - Accessible as `ollama` hostname
- Use hostnames instead of localhost for inter-service communication

### 3.5 Production vs Development Compose Files

```bash
# Development: full stack with source mounts
docker-compose -f docker-compose.yml up

# Production: only runtime containers
docker-compose -f docker-compose.prod.yml up

# Testing: isolated database, optional services
docker-compose -f docker-compose.test.yml up
```

**docker-compose.yml (Development)**:
```yaml
services:
  postgres:
    build:
      context: .
      dockerfile: Dockerfile.postgres
    ports:
      - "5432:5432"
    volumes:
      - db-dev:/var/lib/postgresql/data
    environment:
      POSTGRES_PASSWORD: dev-password

  mcp-server:
    build:
      context: .
    volumes:
      - ./src:/app/src:cached  # Hot reload
      - ./migrations:/app/migrations:cached
    environment:
      LOG_LEVEL: DEBUG
```

**docker-compose.prod.yml (Production)**:
```yaml
services:
  postgres:
    image: postgres:14  # Pre-built production image
    ports: []  # No port exposure
    volumes:
      - db-prod:/var/lib/postgresql/data
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}  # From secrets
    deploy:
      resources:
        limits:
          memory: 2G

  mcp-server:
    image: codebase-mcp:${VERSION}  # Pre-built image
    volumes: []  # No source mounts
    environment:
      LOG_LEVEL: INFO
```

---

## 4. Graceful Shutdown Handling in Python Containers

### 4.1 SIGTERM Signal Handling Basics

When `docker stop` or `docker-compose down` is called:

1. Docker sends SIGTERM to PID 1 (entrypoint process)
2. Process has 10 seconds to shutdown (default timeout)
3. After timeout, Docker sends SIGKILL (forceful kill)

**Goal**: Complete in-flight operations and cleanup resources gracefully.

### 4.2 Implementation Pattern for FastMCP Server

**Recommended Approach: Context Manager + Signal Handler**

```python
# src/server/shutdown_handler.py

import asyncio
import signal
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

class GracefulShutdown:
    """Handle graceful shutdown on SIGTERM."""
    
    def __init__(self, timeout_seconds: float = 10.0):
        self.timeout_seconds = timeout_seconds
        self.shutdown_event: asyncio.Event = asyncio.Event()
        self.tasks_in_flight: set[asyncio.Task[None]] = set()
    
    def register_signal_handlers(self) -> None:
        """Register SIGTERM and SIGINT handlers."""
        
        def signal_handler(signum: int, frame: Any) -> None:
            logger.info(f"Received signal {signum}, initiating graceful shutdown")
            self.shutdown_event.set()
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    
    async def wait_for_shutdown(self) -> None:
        """Block until shutdown signal received."""
        await self.shutdown_event.wait()
    
    async def shutdown_with_timeout(self) -> None:
        """Wait for tasks to complete, with timeout."""
        try:
            await asyncio.wait_for(
                asyncio.gather(*self.tasks_in_flight, return_exceptions=True),
                timeout=self.timeout_seconds
            )
            logger.info("All tasks completed gracefully")
        except asyncio.TimeoutError:
            logger.warning(
                f"Shutdown timeout after {self.timeout_seconds}s, "
                f"cancelling {len(self.tasks_in_flight)} remaining tasks"
            )
            for task in self.tasks_in_flight:
                task.cancel()
            
            # Give tasks a chance to handle cancellation
            await asyncio.sleep(1.0)
```

**Integration in server_fastmcp.py**:

```python
# server_fastmcp.py

import asyncio
from src.server.shutdown_handler import GracefulShutdown

async def main() -> None:
    shutdown = GracefulShutdown(timeout_seconds=10.0)
    shutdown.register_signal_handlers()
    
    try:
        # Start server components
        db_pool = await init_database()
        
        # Wait for shutdown signal
        await shutdown.wait_for_shutdown()
        
        logger.info("Shutting down...")
        
        # Cleanup operations
        if db_pool:
            await db_pool.dispose()
        
        # Wait for in-flight operations (max 10 seconds)
        await shutdown.shutdown_with_timeout()
        
        logger.info("Shutdown complete")
        return 0
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
```

### 4.3 Container-Level Timeout Configuration

```dockerfile
# Set graceful shutdown timeout
# Default is 10 seconds, explicit configuration recommended
STOPSIGNAL SIGTERM

# Optional: environment-based timeout
ENV SHUTDOWN_TIMEOUT=10
```

**Docker Compose**:

```yaml
mcp-server:
  stop_grace_period: 15s  # Give container 15s to shutdown gracefully
  stop_signal: SIGTERM     # Signal to send (default)
```

### 4.4 Testing Graceful Shutdown

```bash
# Test graceful shutdown
docker-compose up -d

# Wait for startup
sleep 5

# Send SIGTERM and observe logs
docker-compose down

# Verify:
# - No error messages
# - Database connections closed cleanly
# - In-flight operations completed
# - All processes terminated within timeout
```

### 4.5 Timeout Strategies

| Scenario | Timeout | Rationale |
|----------|---------|-----------|
| Development | 10s | Quick iterations, minimal data |
| Staging | 30s | Realistic workloads, some in-flight ops |
| Production | 60s | Large indexing jobs may be running |

**Configuration per Environment**:

```yaml
# docker-compose.yml (dev)
stop_grace_period: 10s

# docker-compose.prod.yml (prod)
stop_grace_period: 60s
```

---

## 5. Database Migrations in Container Startup

### 5.1 Startup Script Pattern

**Recommended: entrypoint.sh wrapper**

```bash
#!/bin/bash
set -e

# entrypoint.sh - Container initialization

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" >&2
}

log "Starting Codebase MCP Server"

# 1. Wait for database availability
log "Waiting for PostgreSQL..."
until timeout 2 psql "$REGISTRY_DATABASE_URL" -c "SELECT 1" > /dev/null 2>&1; do
    log "PostgreSQL not ready, retrying..."
    sleep 2
done
log "PostgreSQL is ready"

# 2. Run database migrations
log "Running database migrations..."
if ! alembic upgrade head; then
    log "ERROR: Database migration failed"
    exit 1
fi
log "Migrations completed"

# 3. Start the application
log "Starting MCP server"
exec python server_fastmcp.py
```

**Dockerfile**:

```dockerfile
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
```

### 5.2 Error Handling Strategy

```bash
#!/bin/bash
set -e  # Exit on first error

# Retry logic for database availability
retry_count=0
max_retries=30
retry_delay=2

log_error() {
    echo "[ERROR] $(date +'%Y-%m-%d %H:%M:%S'): $*" >&2
}

log_info() {
    echo "[INFO] $(date +'%Y-%m-%d %H:%M:%S'): $*" >&2
}

wait_for_db() {
    local db_url="$1"
    local max_attempts="$2"
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if timeout 2 psql "$db_url" -c "SELECT 1" > /dev/null 2>&1; then
            log_info "Database available"
            return 0
        fi
        
        attempt=$((attempt + 1))
        log_info "Database not ready (attempt $attempt/$max_attempts)"
        sleep 2
    done
    
    log_error "Database unavailable after $max_attempts attempts"
    return 1
}

# Execution
if ! wait_for_db "$REGISTRY_DATABASE_URL" 30; then
    log_error "Failed to connect to database"
    exit 1
fi

log_info "Running migrations..."
if ! alembic upgrade head; then
    log_error "Migration failed"
    exit 1
fi

log_info "Starting server"
exec python server_fastmcp.py
```

### 5.3 Migration Failure Handling

**Scenario 1: Migration Succeeds**
```
✓ Server starts normally
✓ All tables present
✓ Application ready for requests
```

**Scenario 2: Migration Fails (database corrupted)**
```
✗ Container exits with non-zero code
✗ Docker does NOT restart container (unless policy set)
✓ Admin investigates, fixes database
✓ Manual restart of container after fix
```

**Docker Restart Policy**:

```yaml
mcp-server:
  restart_policy:
    condition: on-failure
    max_retries: 3
    delay: 10s
```

This means:
- Retry startup 3 times if exit code != 0
- Wait 10 seconds between retries
- After 3 failures, stop retrying (manual intervention needed)

### 5.4 Database Availability Retries

**Best Practice: Exponential Backoff**

```bash
#!/bin/bash

wait_for_postgres() {
    local max_time_sec=120
    local start_time=$(date +%s)
    local attempt=1
    
    while true; do
        if psql "$REGISTRY_DATABASE_URL" -c "SELECT 1" > /dev/null 2>&1; then
            echo "Database ready"
            return 0
        fi
        
        local elapsed=$(($(date +%s) - start_time))
        if [ $elapsed -gt $max_time_sec ]; then
            echo "Timeout waiting for database after ${elapsed}s"
            return 1
        fi
        
        # Exponential backoff: 1s, 2s, 4s, 8s, max 10s
        local delay=$((2 ** (attempt - 1)))
        [ $delay -gt 10 ] && delay=10
        
        echo "Waiting... (attempt $attempt, waited ${elapsed}s)"
        sleep $delay
        attempt=$((attempt + 1))
    done
}

if ! wait_for_postgres; then
    exit 1
fi
```

### 5.5 Configuration for Testing

**docker-compose.test.yml**:

```yaml
services:
  postgres-test:
    image: postgres:14
    environment:
      POSTGRES_DB: test_db
      POSTGRES_PASSWORD: test
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 3s
      retries: 5

  mcp-server-test:
    build:
      context: .
    depends_on:
      postgres-test:
        condition: service_healthy
    environment:
      REGISTRY_DATABASE_URL: "postgresql+asyncpg://postgres:test@postgres-test:5432/test_db"
    command: ["sh", "-c", "alembic upgrade head && pytest tests/"]
```

---

## 6. Implementation Priorities

### Phase 1: Core Functionality
1. Multi-stage Dockerfile (python:3.12-slim builder + runtime)
2. Basic docker-compose.yml (PostgreSQL + Ollama + MCP server)
3. entrypoint.sh with migration handling
4. Environment variable configuration (.env.example)
5. Simple health check (process-based)

### Phase 2: Polish
1. Graceful shutdown handling (SIGTERM)
2. Comprehensive health checks (db + ollama)
3. Documentation and troubleshooting guide
4. Production compose file (docker-compose.prod.yml)
5. CI/CD integration (docker-compose.test.yml)

### Phase 3: Optimization
1. Image size optimization (<500MB target)
2. Build cache optimization
3. Multi-architecture builds (amd64, arm64)
4. Security scanning and hardening
5. Performance benchmarking in containers

---

## 7. Specific Recommendations for MCP Server

### 7.1 Dockerfile Structure

```dockerfile
# Stage 1: Builder
FROM python:3.12-slim as builder
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 postgresql-client && rm -rf /var/lib/apt/lists/*
COPY --from=builder /root/.local /root/.local
COPY src/ src/
COPY migrations/ migrations/
COPY alembic.ini server_fastmcp.py ./
RUN useradd -m -u 1000 mcp && chown -R mcp:mcp /app
USER mcp
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD pgrep -f "python server_fastmcp.py" || exit 1
ENTRYPOINT ["/entrypoint.sh"]
```

### 7.2 docker-compose.yml Structure

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:14
    environment:
      POSTGRES_DB: codebase_mcp
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
    volumes:
      - db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama-data:/root/.ollama
    environment:
      OLLAMA_HOST: 0.0.0.0:11434
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 5s
      retries: 3

  mcp-server:
    build:
      context: .
      dockerfile: Dockerfile
    depends_on:
      postgres:
        condition: service_healthy
      ollama:
        condition: service_healthy
    environment:
      REGISTRY_DATABASE_URL: postgresql+asyncpg://postgres:${POSTGRES_PASSWORD:-postgres}@postgres:5432/codebase_mcp
      OLLAMA_BASE_URL: http://ollama:11434
    volumes:
      - ./src:/app/src:cached
      - ./migrations:/app/migrations:cached
    stop_grace_period: 10s
    healthcheck:
      test: ["CMD", "pgrep", "-f", "python server_fastmcp.py"]
      interval: 30s
      timeout: 5s
      retries: 3

volumes:
  db-data:
  ollama-data:
```

### 7.3 entrypoint.sh for MCP Server

```bash
#!/bin/bash
set -e

log_info() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $*" >&2; }
log_error() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $*" >&2; }

log_info "Starting Codebase MCP Server"

# Wait for PostgreSQL
log_info "Waiting for PostgreSQL..."
for i in {1..30}; do
    if timeout 2 psql "$REGISTRY_DATABASE_URL" -c "SELECT 1" > /dev/null 2>&1; then
        log_info "PostgreSQL is ready"
        break
    fi
    [ $i -eq 30 ] && { log_error "PostgreSQL timeout"; exit 1; }
    sleep 2
done

# Run migrations
log_info "Running database migrations..."
if ! alembic upgrade head; then
    log_error "Migration failed"
    exit 1
fi
log_info "Migrations completed"

# Start server
log_info "Starting FastMCP server"
exec python server_fastmcp.py
```

---

## Summary: Implementation Checklist

- [x] Multi-stage Dockerfile (python:3.12-slim) → <450MB target
- [x] docker-compose.yml (PostgreSQL 14 + Ollama + MCP server)
- [x] entrypoint.sh (migration handling, db retry logic)
- [x] .env.example (environment configuration)
- [x] Health checks (process-based minimum, composite optional)
- [x] Graceful shutdown (SIGTERM handling in server)
- [x] Volume mounts for development (source code hot reload)
- [x] Network isolation (docker-compose bridge network)
- [x] Error handling (migration failures, retry logic)
- [x] Documentation (setup, troubleshooting, examples)

---

## References

- Docker Best Practices: https://docs.docker.com/develop/dev-best-practices/
- Multi-Stage Builds: https://docs.docker.com/build/building/multi-stage/
- Docker Compose: https://docs.docker.com/compose/
- Health Checks: https://docs.docker.com/engine/reference/builder/#healthcheck
- Signal Handling: https://docs.docker.com/engine/reference/run/#foreground
