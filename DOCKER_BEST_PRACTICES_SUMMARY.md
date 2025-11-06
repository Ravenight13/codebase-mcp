# Docker Best Practices: Summary & Recommendations

**Codebase MCP Server** - Complete research summary for feature 015  
**Date**: 2025-11-06  
**Status**: Ready for implementation

---

## Executive Summary

This document summarizes Docker containerization best practices researched for the Codebase MCP Server. Five key areas were analyzed with specific recommendations for the MCP server context. All recommendations are production-ready and aligned with the existing codebase architecture (FastMCP, Python 3.11+, PostgreSQL 14+, Ollama).

---

## 1. Multi-Stage Dockerfile Optimization

### Recommendation: python:3.12-slim Base Image

**Why**: Balances minimal footprint (~150MB base) with practical build tooling needed for tree-sitter, pgvector, and asyncpg compilation.

**Alternative Comparison**:
- Alpine: Simpler size but incompatibility issues with pgvector
- Distroless: Better security but requires complex 3-stage builds
- Standard: Works but bloated (~910MB base)

### Implementation Strategy

**Two-Stage Build Pattern**:
1. **Builder Stage** (python:3.12-slim)
   - Install gcc, make, libpq-dev
   - Compile all Python dependencies
   - Final size: ~200MB

2. **Runtime Stage** (python:3.12-slim)
   - Only include libpq5 (runtime lib, not dev)
   - Copy compiled packages from builder
   - Final image size: 320-390MB (comfortably under 500MB target)

**Key Optimizations**:
- Layer ordering: requirements.txt before source code (cache efficiency)
- Non-root user: `mcp` (UID 1000) for security
- Minimal layers: Combine apt-get operations with `&&`
- Clean dependency removal: `rm -rf /var/lib/apt/lists/*`

**Expected Build Impact**:
- Initial build: 60-90 seconds
- Code change rebuild: 2-3 seconds (only code layer invalidated)
- Dependency update: 30-45 seconds

---

## 2. Health Check Implementation for Stdio Services

### Challenge

MCP servers use stdio/JSON-RPC, not HTTP. Docker's port-based health checks don't apply.

### Recommended Strategy: Custom Health Check Script

**Minimal Implementation** (lightweight, recommended):
```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD pgrep -f "python server_fastmcp.py" || exit 1
```

**Enhanced Implementation** (optional, for future use):
```dockerfile
COPY docker/healthcheck.sh /healthcheck.sh
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD /healthcheck.sh
```

Health check script can verify:
- Process running (lightweight)
- Database connectivity (indicates service readiness)
- Ollama availability (warns if not responding)

### Configuration Rationale

| Setting | Value | Reason |
|---------|-------|--------|
| `--start-period` | 20s | DB migrations take 5-10s; migrations then health check |
| `--interval` | 30s | Long-running process; reasonable check frequency |
| `--timeout` | 5-10s | Abort if check hangs; prevent cascading failures |
| `--retries` | 3 | Allow transient failures; mark unhealthy after 3 consecutive |

---

## 3. Docker-Compose for Development

### Service Dependency Management

**Startup Order** (enforced by health checks):
1. PostgreSQL (must start first, others depend on it)
2. Ollama (optional but recommended; can start in parallel)
3. MCP Server (waits for both services healthy)

### Volume Strategy for Development

**Source Code Mounting** (enables hot reload):
```yaml
volumes:
  - ./src:/app/src:cached
  - ./migrations:/app/migrations:cached
  - ./server_fastmcp.py:/app/server_fastmcp.py:cached
```

Mount modes:
- `:cached` - Async sync (good for source code, fast on macOS)
- Default - Sync (good for config files)
- `:ro` - Read-only (good for unchanging configs)

### Environment Variable Pattern

**Strategy**: .env.example (checked in) + .env (local overrides)

Example .env.example:
```bash
# Database
REGISTRY_DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/codebase_mcp
REGISTRY_DATABASE_POOL_SIZE=5

# Ollama (service discovery in compose network)
OLLAMA_BASE_URL=http://ollama:11434

# Logging
LOG_LEVEL=INFO
LOG_FILE=/tmp/codebase-mcp.log

# Python runtime
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1
```

### Network Configuration

**Compose Network Topology**:
```
postgres:5432 ──┐
                ├─→ codebase-mcp-network (bridge)
ollama:11434 ──┤
                └─→ mcp-server (no external port exposed)
```

Service discovery: Use hostname (not localhost)
- `postgres` for PostgreSQL connection
- `ollama` for Ollama API calls

---

## 4. Graceful Shutdown Handling

### Container Shutdown Flow

```
docker stop container
    ↓
SIGTERM sent to PID 1
    ↓
Application catches signal
    ↓
Cleanup: close database, cancel in-flight ops
    ↓
Exit with code 0 (within timeout)
    ↓ (if timeout exceeded)
SIGKILL sent (forceful termination)
```

### Recommended Implementation

**Signal Handler in FastMCP Server**:
```python
class GracefulShutdown:
    def register_signal_handlers(self) -> None:
        """Register SIGTERM/SIGINT handlers."""
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
    
    async def shutdown_with_timeout(self) -> None:
        """Wait for tasks with timeout; cancel if exceeded."""
        try:
            await asyncio.wait_for(
                asyncio.gather(*self.tasks_in_flight),
                timeout=self.timeout_seconds
            )
        except asyncio.TimeoutError:
            # Force cancel after timeout
            for task in self.tasks_in_flight:
                task.cancel()
```

### Timeout Configuration

**docker-compose**:
```yaml
mcp-server:
  stop_grace_period: 15s  # Timeout for graceful shutdown
  stop_signal: SIGTERM    # Signal type
```

**Recommended Timeouts**:
- Development: 10s (quick iterations)
- Staging: 30s (realistic workloads)
- Production: 60s (large indexing operations may be in-flight)

---

## 5. Database Migrations in Container Startup

### Recommended Pattern: entrypoint.sh Wrapper

**Flow**:
1. Wait for PostgreSQL availability (with exponential backoff)
2. Run alembic migrations
3. Start MCP server

**Implementation**:
```bash
#!/bin/bash
set -e

log_info() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $*" >&2; }
log_error() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $*" >&2; }

# 1. Wait for PostgreSQL (max 30 attempts, 2s each = 60s total)
for i in {1..30}; do
    if timeout 2 psql "$REGISTRY_DATABASE_URL" -c "SELECT 1" > /dev/null 2>&1; then
        log_info "PostgreSQL ready"
        break
    fi
    [ $i -eq 30 ] && { log_error "PostgreSQL timeout"; exit 1; }
    sleep 2
done

# 2. Run migrations
log_info "Running migrations..."
alembic upgrade head || { log_error "Migration failed"; exit 1; }

# 3. Start server
log_info "Starting server"
exec python server_fastmcp.py
```

### Error Handling Strategies

| Scenario | Behavior | Resolution |
|----------|----------|-----------|
| PostgreSQL unavailable | Retry 30x with 2s delay | Admin starts PostgreSQL; container retries |
| Migration fails | Exit with code 1 | Docker does NOT auto-restart; admin investigates |
| Server starts | Continues normally | Healthy and ready |

### Restart Policy

```yaml
mcp-server:
  restart_policy:
    condition: on-failure
    max_retries: 3
    delay: 10s
```

This allows transient failures (network glitches) to auto-recover but prevents infinite loops if migrations are permanently broken.

---

## Implementation Checklist

### Phase 1: Core (Required for Feature 015)
- [ ] Multi-stage Dockerfile (python:3.12-slim)
- [ ] Minimal health check (process-based)
- [ ] docker-compose.yml (PostgreSQL + Ollama + MCP)
- [ ] entrypoint.sh with migration handling
- [ ] .env.example with environment variables
- [ ] Volume mounts for development
- [ ] Service dependency ordering

### Phase 2: Production Ready (Recommended)
- [ ] Enhanced health checks (database + ollama)
- [ ] Graceful shutdown handling (SIGTERM)
- [ ] docker-compose.prod.yml (production variant)
- [ ] docker-compose.test.yml (CI/CD testing)
- [ ] Deployment documentation
- [ ] Troubleshooting guide

### Phase 3: Optimization (Future)
- [ ] Image size audit (<500MB target)
- [ ] Build cache optimization
- [ ] Multi-architecture builds (arm64 support)
- [ ] Security scanning
- [ ] Performance benchmarking

---

## Key Decision Points for Implementation

### 1. Base Image Selection
**Decision**: Use `python:3.12-slim`
**Rationale**: Balances build capability with final image size; no Alpine compatibility issues

### 2. Health Check Strategy
**Decision**: Minimal process-based check initially; enhanced checks deferred
**Rationale**: Reduces complexity; can be enhanced later without major refactoring

### 3. Shutdown Timeout
**Decision**: 15 seconds for development (docker-compose)
**Rationale**: Reasonable for long-running operations; can be tuned per environment

### 4. Database Migration Strategy
**Decision**: entrypoint.sh wrapper with exponential backoff retry
**Rationale**: Handles transient failures; prevents infinite loops on permanent errors

### 5. Environment Configuration
**Decision**: .env.example + local .env pattern
**Rationale**: Standard practice; allows defaults while supporting local customization

---

## Performance Impact Summary

### Build Performance
| Operation | Time | Notes |
|-----------|------|-------|
| Clean build | 60-90s | First time (downloads base image, compiles deps) |
| Code change rebuild | 2-3s | Only code layer invalidated |
| Dependency update | 30-45s | Full pip install, but builder cached |

### Runtime Performance
- **Startup overhead**: +3-5 seconds (migrations + health check)
- **Memory footprint**: ~150MB base + 50-100MB Python + 50MB app
- **CPU during indexing**: Equivalent to non-containerized (no Docker overhead for CPU-bound ops)
- **I/O performance**: Slight overhead; mitigated by `:cached` volume mounts on macOS

### Image Size
- **Final image**: 320-390MB (target: <500MB)
- **Layer breakdown**:
  - Base: 150MB
  - Python dependencies: 150-200MB
  - Runtime libraries: 20-30MB
  - Application code: <10MB

---

## Risk Mitigation

### Risk: Database port conflicts on developer machines
**Mitigation**: Document port mapping override in docker-compose.yml
```yaml
postgres:
  ports:
    - "5433:5432"  # Use different host port if needed
```

### Risk: Slow volume mounts on macOS
**Mitigation**: Use `:cached` flag for source code mounts
```yaml
volumes:
  - ./src:/app/src:cached
```

### Risk: Migration failures leave container in bad state
**Mitigation**: Explicit restart policy; admin must fix database before container will start again

### Risk: SIGTERM not handled properly
**Mitigation**: Implement graceful shutdown handler in server code; test with `docker-compose down`

---

## Testing Strategy

### Local Development Testing
```bash
# Start stack
docker-compose up

# Verify services
docker-compose ps
docker logs <service-name>

# Test migrations
docker exec <mcp-container> alembic current

# Test health checks
docker ps  # Look for "healthy" status
```

### Shutdown Testing
```bash
docker-compose up -d
sleep 5
docker-compose down  # Verify graceful shutdown in logs
```

### CI/CD Testing
```bash
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
# Verifies: build succeeds, migrations work, tests pass
```

---

## Monitoring & Troubleshooting

### Check Container Logs
```bash
docker logs <container-name>
docker-compose logs mcp-server
```

### Common Issues

| Issue | Symptom | Resolution |
|-------|---------|-----------|
| PostgreSQL unavailable | "FATAL: could not translate host name" | Start postgres service or wait for health check |
| Port conflict | "Address already in use" | Change port in docker-compose.yml |
| Permission denied | "Permission denied: '/app/migrations'" | Check non-root user and volume mount ownership |
| Migration timeout | Long startup then failure | Increase migration timeout in entrypoint.sh |
| Ollama not responding | "Connection refused" | Verify ollama service health; may recover on retry |

---

## References & Standards

- **Docker Official Best Practices**: https://docs.docker.com/develop/dev-best-practices/
- **Multi-Stage Build Guide**: https://docs.docker.com/build/building/multi-stage/
- **Docker Compose Specification**: https://docs.docker.com/compose/compose-file/
- **Health Check Documentation**: https://docs.docker.com/engine/reference/builder/#healthcheck
- **Signal Handling & Graceful Shutdown**: https://docs.docker.com/engine/reference/run/#foreground

---

## Next Steps

1. **Create Dockerfile** with two-stage build (builder + runtime)
2. **Create docker-compose.yml** with PostgreSQL, Ollama, MCP service
3. **Create entrypoint.sh** with migration and startup logic
4. **Create .env.example** with documented environment variables
5. **Test locally** with `docker-compose up` and `docker-compose down`
6. **Document** setup, troubleshooting, and production deployment
7. **Implement graceful shutdown** in server code (Phase 2)
8. **Add enhanced health checks** (Phase 2)

---

**Document Version**: 1.0  
**Last Updated**: 2025-11-06  
**Status**: Ready for Implementation
