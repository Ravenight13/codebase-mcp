# Quickstart: Docker Integration Testing & Deployment Scenarios

**Feature**: 015-add-support-docker
**Date**: 2025-11-06
**Purpose**: Step-by-step scenarios for validating Docker support across development, testing, and production use cases.

## User Story 1: Local Development Setup (P1)

### Scenario 1.1: Fresh Clone, `docker-compose up`, Run Tests

**Actor**: Developer (on Linux, macOS, or Windows with WSL2)

**Prerequisites**:
- Docker and Docker Compose installed
- Fresh clone of repository
- No local PostgreSQL or Ollama running
- Internet connection (for pulling images)

**Steps**:

1. Clone repository
   ```bash
   git clone https://github.com/anthropics/codebase-mcp.git
   cd codebase-mcp
   ```

2. Create .env file from template
   ```bash
   cp .env.example .env
   ```

3. Start the stack
   ```bash
   docker-compose up
   ```

   **Expected Output** (in order):
   - PostgreSQL container starts
   - Ollama container starts
   - MCP server container starts
   - Database migrations run automatically
   - Server logs show "Server ready" or similar
   - Total time: <120 seconds
   - All containers: "healthy" status

4. In another terminal, verify stack is healthy
   ```bash
   docker-compose ps
   # Output:
   # NAME                   STATUS
   # codebase-postgresql    Up (healthy)
   # codebase-ollama        Up (healthy)
   # codebase-mcp           Up (healthy)
   ```

5. Run integration tests
   ```bash
   docker-compose exec codebase-mcp pytest tests/integration/ -v
   ```

   **Expected Outcome**: All integration tests pass
   - No "connection refused" errors
   - No "database not ready" errors
   - All MCP tools callable
   - Search returns results

6. Modify source code (hot reload)
   ```bash
   # In src/mcp/server_fastmcp.py, change a comment
   # Watch container logs - should show no restart (volume mount in effect)
   ```

   **Expected Outcome**: File changes reflected immediately (no container restart needed)

7. Clean up
   ```bash
   docker-compose down -v
   ```

   **Expected Outcome**: All containers stopped, all volumes removed, clean state

**Acceptance Criteria**:
- ✅ `docker-compose up` starts all services
- ✅ All services healthy within 120 seconds
- ✅ Migrations run automatically
- ✅ Tests pass
- ✅ Hot reload works (volume mount)
- ✅ `docker-compose down -v` cleanly stops all services

---

### Scenario 1.2: Partial Restart (Develop Without Full Stack Rebuild)

**Actor**: Developer iterating on code

**Prerequisites**:
- Completed scenario 1.1
- Stack is running

**Steps**:

1. Restart only the MCP server (preserve PostgreSQL and Ollama)
   ```bash
   docker-compose restart codebase-mcp
   ```

2. Verify server restarted but databases persisted
   ```bash
   docker-compose exec codebase-mcp pytest tests/integration/test_database_connection.py
   ```

**Expected Outcome**:
- MCP server restarted quickly
- PostgreSQL and Ollama untouched
- Tests pass immediately (no re-indexing)
- Development cycle time: <10 seconds

**Acceptance Criteria**:
- ✅ Selective service restart works
- ✅ Databases not reset
- ✅ Fast iteration cycle

---

## User Story 2: Production Deployment (P2)

### Scenario 2.1: Build Production Image and Run with External Database

**Actor**: DevOps engineer

**Prerequisites**:
- Docker installed on production server
- External PostgreSQL 14+ instance running
- External Ollama instance available
- Network access between server and external services

**Steps**:

1. Build production image
   ```bash
   docker build -t codebase-mcp:0.15.0 .
   ```

   **Expected Output**:
   - Build completes successfully
   - Final image size: <500 MB (display with `docker images`)
   - No errors or warnings
   - Build time: <5 minutes (first build with cache warm)

2. Verify image size
   ```bash
   docker images | grep codebase-mcp
   # Output should show size < 500 MB
   ```

3. Run container with external services
   ```bash
   docker run -d \
     --name codebase-mcp \
     -e REGISTRY_DATABASE_URL="postgresql+asyncpg://user:pass@db.example.com:5432/codebase" \
     -e OLLAMA_BASE_URL="http://ollama.example.com:11434" \
     codebase-mcp:0.15.0
   ```

4. Check logs and health
   ```bash
   docker logs codebase-mcp
   # Should show: "Waiting for PostgreSQL..." → "Running migrations..." → "Server ready"

   sleep 30  # Wait for server startup
   docker ps | grep codebase-mcp
   # Should show "healthy" status
   ```

5. Verify server is functional
   ```bash
   # Query the health status via MCP resource (if health check script available)
   # Or use docker health check
   docker inspect codebase-mcp --format='{{.State.Health.Status}}'
   # Output: healthy
   ```

6. Test server with sample indexing
   ```bash
   # Index a small repository
   docker logs codebase-mcp
   # Should show indexing progress
   ```

**Acceptance Criteria**:
- ✅ Image builds successfully
- ✅ Image size < 500 MB
- ✅ Container starts with only environment variables
- ✅ Migrations run automatically (no manual step)
- ✅ Health check reports healthy
- ✅ Server accepts indexing requests

---

### Scenario 2.2: Graceful Restart with In-Flight Operation

**Actor**: DevOps engineer performing maintenance

**Prerequisites**:
- Completed scenario 2.1
- Container running and accepting requests

**Steps**:

1. Initiate indexing of large repository
   ```bash
   # Submit indexing request via MCP tool
   # (Details depend on MCP client implementation)
   ```

2. Send SIGTERM during indexing
   ```bash
   docker stop --time=30 codebase-mcp
   # This sends SIGTERM, waits up to 30 seconds for graceful shutdown
   ```

3. Verify clean shutdown
   ```bash
   docker logs codebase-mcp | tail -20
   # Should show: "Received SIGTERM..." → "Shutting down..." → exit code 0 or 1

   docker ps | grep codebase-mcp
   # Should show "Exited" status (not killed)
   ```

4. Restart and verify state
   ```bash
   docker start codebase-mcp
   sleep 30
   docker ps | grep codebase-mcp
   # Should be running and healthy
   ```

**Acceptance Criteria** (Phase 1: basic timeout, Phase 2: full handler):
- ✅ Container stops within grace period
- ✅ No data corruption on restart
- ✅ Previous indexing state recoverable

---

## User Story 3: CI/CD Integration (P3)

### Scenario 3.1: Run Tests in Docker (GitHub Actions Example)

**Actor**: CI/CD system (GitHub Actions, GitLab CI, etc.)

**Prerequisites**:
- Docker and Docker Compose available in CI environment
- Repository cloned
- Git branch with changes

**Steps**:

1. Build Docker image (with cache)
   ```bash
   docker-compose build
   ```

   **Expected Output**:
   - Leverages layer cache if dependencies unchanged
   - First build: ~2 minutes
   - Subsequent builds (code-only changes): <30 seconds

2. Start test environment
   ```bash
   docker-compose -f docker-compose.test.yml up -d
   ```

   **Expected Output**:
   - Starts PostgreSQL, Ollama, MCP server
   - Runs migrations automatically
   - All services healthy within 60 seconds

3. Run full test suite
   ```bash
   docker-compose -f docker-compose.test.yml exec codebase-mcp pytest -v --cov=src
   ```

   **Expected Output**:
   - Unit tests pass (quick, no containers)
   - Integration tests pass (use containerized services)
   - Contract tests pass (validate MCP protocol)
   - Coverage report generated
   - Total time: <5 minutes

4. Collect artifacts
   ```bash
   docker-compose -f docker-compose.test.yml exec codebase-mcp cat coverage.xml > coverage.xml
   # Upload to coverage service (Codecov, etc.)
   ```

5. Clean up
   ```bash
   docker-compose -f docker-compose.test.yml down -v
   ```

**Acceptance Criteria**:
- ✅ Build leverages cache effectively
- ✅ All tests pass in Docker
- ✅ CI/CD can extract artifacts
- ✅ Total CI time: <10 minutes
- ✅ Clean up removes all containers/volumes

---

### Scenario 3.2: Multi-Build Layer Caching

**Actor**: CI/CD system with multiple commits

**Prerequisites**:
- Completed scenario 3.1
- Multiple code commits in PR

**Steps**:

1. First commit: change requirements
   ```bash
   docker-compose build
   # Cache miss on dependency layer
   # Build time: ~2 minutes
   ```

2. Second commit: change only application code
   ```bash
   docker-compose build
   # Cache hit on dependency layer (only 300 MB install skipped)
   # Build time: <30 seconds
   ```

3. Third commit: change source code again
   ```bash
   docker-compose build
   # Cache hit on dependency layer
   # Build time: <30 seconds
   ```

**Expected Outcome**:
- Layer ordering optimized (dependencies before code)
- Dependency-only changes cached
- Code-only changes rebuild quickly

**Acceptance Criteria**:
- ✅ Cache hit rate >90% for code-only changes
- ✅ No unnecessary rebuilds
- ✅ Fast CI feedback loop

---

## Cross-Platform Validation Scenarios

### Scenario 4.1: Volume Mount Performance on macOS

**Actor**: Developer on macOS with Docker Desktop

**Prerequisites**:
- Completed scenario 1.1 on macOS

**Steps**:

1. Measure file I/O performance
   ```bash
   docker-compose exec codebase-mcp python -m timeit "
   with open('/workspace/src/mcp/server_fastmcp.py') as f:
     f.read()
   "
   # Expected: <100ms
   ```

2. Verify `:cached` consistency mode in compose
   ```bash
   grep -A5 "volumes:" docker-compose.yml | grep cached
   # Should show: .:/workspace:cached
   ```

**Expected Outcome**:
- File reads <100ms (acceptable for development)
- `:cached` mode documented for macOS users
- Alternative: docker-sync for extreme performance needs

**Acceptance Criteria**:
- ✅ File I/O reasonable for development
- ✅ Documentation mentions macOS optimization

---

### Scenario 4.2: Windows/WSL2 Docker Desktop

**Actor**: Developer on Windows with Docker Desktop + WSL2

**Prerequisites**:
- Windows with WSL2
- Docker Desktop running
- Repository cloned in WSL2 filesystem

**Steps**:

1. Start stack from WSL2 terminal
   ```bash
   docker-compose up
   ```

2. Verify volume mounts work
   ```bash
   docker-compose exec codebase-mcp ls /workspace
   # Should list repository contents
   ```

3. Test write permissions
   ```bash
   docker-compose exec codebase-mcp touch /workspace/test-write.txt
   # From WSL2: ls -la test-write.txt
   # Should show file exists (cross-filesystem permission)
   ```

**Expected Outcome**:
- Volumes mount correctly in WSL2
- Write permissions work both directions
- No permission errors

**Acceptance Criteria**:
- ✅ WSL2 integration works
- ✅ No platform-specific workarounds needed

---

## Health Check Validation Scenarios

### Scenario 5.1: PostgreSQL Health Check Failure Recovery

**Actor**: DevOps monitor

**Prerequisites**:
- Stack running (scenario 1.1)

**Steps**:

1. Simulate PostgreSQL unavailability
   ```bash
   docker-compose pause postgresql
   ```

2. Observe health check failure
   ```bash
   sleep 35
   docker-compose ps
   # PostgreSQL should show "unhealthy" after 30s interval + retries
   ```

3. Recover PostgreSQL
   ```bash
   docker-compose unpause postgresql
   ```

4. Verify recovery
   ```bash
   docker-compose ps
   # PostgreSQL should return to "healthy"
   ```

**Acceptance Criteria**:
- ✅ Health check detects failure
- ✅ Container marked unhealthy
- ✅ Restart policy can handle recovery

---

### Scenario 5.2: Cascading Service Recovery

**Actor**: DevOps monitor (verifying startup order)

**Prerequisites**:
- Fresh stack with `docker-compose down -v`

**Steps**:

1. Start stack and observe startup order
   ```bash
   docker-compose up
   watch -n 1 'docker-compose ps'  # Monitor in terminal
   ```

2. Expected order in logs:
   ```
   postgresql: "database system is ready to accept connections"
   ollama: "Listening on 127.0.0.1:11434"
   codebase-mcp: "Server ready to accept connections"
   ```

3. Verify dependencies enforced
   ```bash
   grep "depends_on:" docker-compose.yml
   # Should show: ollama depends_on postgresql
   # Should show: codebase-mcp depends_on [postgresql, ollama]
   ```

**Acceptance Criteria**:
- ✅ Services start in dependency order
- ✅ Logs show startup progression
- ✅ No "connection refused" errors

---

## Success Metrics

After completing all scenarios, validate:

| Metric | Target | Scenario(s) |
|--------|--------|-------------|
| Stack startup time | <120s | 1.1, 4.1, 4.2 |
| Image size | <500 MB | 2.1 |
| Build cache hit | >90% (code-only) | 3.2 |
| Health check latency | <5s | 5.1, 5.2 |
| Test suite in Docker | <5 min | 3.1 |
| Development iteration | <10s restart | 1.2 |
| Cross-platform support | All 3 (Linux, macOS, Windows) | 1.1, 4.1, 4.2 |

---

## Troubleshooting Checklist

If scenarios fail, consult:

1. **Port conflicts**: Change ports in docker-compose.yml (see DOCKER_SETUP.md)
2. **Image size exceeded 500 MB**: Verify multi-stage build (see plan.md)
3. **Migrations timeout**: Check database logs (see TROUBLESHOOTING.md)
4. **Health check failures**: Verify process is running (see HEALTH_CHECKS.md)
5. **macOS volume slowness**: Use `:cached` mode or docker-sync (see DOCKER_SETUP.md)
6. **WSL2 permission errors**: Ensure cloned in WSL2 filesystem, not Windows filesystem (see DOCKER_SETUP.md)

---

## Sign-Off

All scenarios must pass before feature is considered complete. Each scenario maps to specific success criteria in spec.md.

**Checklist**:
- [ ] Scenario 1.1: Local development (P1)
- [ ] Scenario 1.2: Partial restart (P1)
- [ ] Scenario 2.1: Production image and run (P2)
- [ ] Scenario 2.2: Graceful restart (P2 / Phase 2)
- [ ] Scenario 3.1: CI/CD testing (P3)
- [ ] Scenario 3.2: Layer caching (P3)
- [ ] Scenario 4.1: macOS performance (cross-platform)
- [ ] Scenario 4.2: WSL2 support (cross-platform)
- [ ] Scenario 5.1: PostgreSQL health recovery (health checks)
- [ ] Scenario 5.2: Startup order (dependencies)

**Status**: Ready for implementation phase
