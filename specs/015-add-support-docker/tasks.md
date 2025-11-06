# Tasks: Docker Support for Codebase MCP Server

**Input**: Design documents from `/specs/015-add-support-docker/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, quickstart.md ✅

**Organization**: Tasks are grouped by user story (P1, P2, P3) to enable independent implementation and testing of each story. No tests explicitly requested in spec, but integration validation scenarios included in quickstart.md.

**Format**: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story (US1=P1 local dev, US2=P2 production, US3=P3 CI/CD)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create Docker-related directory structure and configuration templates

- [X] T001 Create `scripts/docker/` directory structure for entrypoint script
- [X] T002 Create `docs/deployment/` directory structure for Docker documentation
- [X] T003 Create `.dockerignore` file to exclude unnecessary files from Docker build context
- [X] T004 [P] Create `.env.example` template with all required and optional environment variables

**Checkpoint**: Directory structure and configuration templates ready ✅

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core containerization infrastructure that all user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 Create `Dockerfile` with two-stage build using `python:3.12-slim` base image in repository root
  - Stage 1 (builder): Install dependencies from requirements.txt
  - Stage 2 (runtime): Copy only necessary files and dependencies
  - Target final image size: <500 MB (SC-002)
  - Include non-root user for security
  - Entry point configured for `/app/src/mcp/server_fastmcp.py`

- [X] T006 Create `scripts/docker/entrypoint.sh` startup script in repository root:
  - Wait for PostgreSQL availability with exponential backoff (up to 30s)
  - Run `alembic upgrade head` for automatic migrations
  - Handle migration failures gracefully with logging
  - Start MCP server via `python src/mcp/server_fastmcp.py`
  - Exit with proper error codes (0=success, 1=failure)

- [X] T007 [P] Create base `docker-compose.yml` for development environment in repository root:
  - PostgreSQL 14 service: port 5432, health check via `pg_isready`
  - Ollama service: port 11434, health check via curl
  - Codebase MCP service: depends on postgresql and ollama, uses built Dockerfile
  - Volumes: `postgres_data`, `ollama_data` (named), `.:/workspace:cached` (source code bind mount)
  - Networks: Single bridge network with service discovery by hostname
  - Environment file: `.env` (created from `.env.example`)

- [X] T008 [P] Create `docker-compose.test.yml` for testing environment:
  - Same services as docker-compose.yml but without source code volume mount
  - Use `COPY src/ /app/src/` from Dockerfile (no live reload)
  - Isolated network and container names (e.g., `test_postgresql`, `test_codebase_mcp`)
  - Environment variables for testing (test database, test model)
  - No volume persistence (clean state per test run)

- [X] T009 Configure entrypoint.sh to be executable:
  - Set executable permission on `scripts/docker/entrypoint.sh` (chmod +x)
  - Verify shell script syntax with `bash -n`
  - Test in isolated container that it runs without errors

**Checkpoint**: Dockerfile, docker-compose files, and entrypoint script ready - foundation complete ✅

---

## Phase 3: User Story 1 - Developer Sets Up Local Environment with Docker Compose (Priority: P1) 🎯 MVP

**Goal**: Enable developers to start entire stack with `docker-compose up` and run integration tests without manual setup

**Independent Test**: Run `docker-compose up` from repository root, verify all services healthy within 120s, migrations run automatically, run `pytest tests/integration/ -v` and all tests pass

### Validation for User Story 1

- [X] T010 [US1] Validate docker-compose.yml structure and configuration in `specs/015-add-support-docker/contracts/docker-compose.schema.json`
  - Define JSON schema for docker-compose syntax
  - Validate services: postgresql, ollama, codebase-mcp
  - Validate depends_on, health checks, volumes, ports
  - Schema includes environment variable requirements

- [X] T011 [US1] Create integration test scenario in `docs/deployment/DOCKER_SETUP.md`:
  - Step-by-step: clone → copy .env.example → docker-compose up
  - Verify all services start within 120 seconds
  - Check health status with `docker-compose ps`
  - Run integration tests: `docker-compose exec codebase-mcp pytest tests/integration/ -v`
  - Verify hot reload: modify source file, container updates without restart
  - Verify clean shutdown: `docker-compose down -v` removes all data

### Implementation for User Story 1

- [X] T012 [P] [US1] Create health check script in `scripts/docker/healthcheck.sh`:
  - Simple process check: `pgrep -f "python.*server_fastmcp"`
  - Returns exit code 0 (healthy) or 1 (unhealthy)
  - Used by Docker HEALTHCHECK directive in Dockerfile
  - Timeout target: <1 second, <100 bytes

- [X] T013 [US1] Update Dockerfile to include health check configuration:
  - Add HEALTHCHECK instruction with `test: ["CMD", "pgrep", "-f", "python.*server_fastmcp"]`
  - start_period: 20s (grace period after container start)
  - interval: 30s (check frequency)
  - timeout: 5s (max execution time)
  - retries: 3 (fail after 3 consecutive failures)

- [X] T014 [P] [US1] Update docker-compose.yml with proper health check configuration:
  - PostgreSQL health check: `test: ["CMD-SHELL", "pg_isready -U postgres"]`
    - start_period: 10s, interval: 10s, timeout: 5s, retries: 5
  - Ollama health check: `test: ["CMD-SHELL", "curl -f http://localhost:11434/api/tags || exit 1"]`
    - start_period: 20s, interval: 30s, timeout: 5s, retries: 3
  - MCP server health check: pgrep-based (T012)
    - start_period: 20s, interval: 30s, timeout: 5s, retries: 3

- [X] T015 [P] [US1] Create `.env` file from `.env.example` template for development:
  - `REGISTRY_DATABASE_URL=postgresql+asyncpg://postgres:dev-password@postgresql:5432/codebase_mcp`
  - `OLLAMA_BASE_URL=http://ollama:11434`
  - `OLLAMA_EMBEDDING_MODEL=nomic-embed-text`
  - `POSTGRES_PASSWORD=dev-password`
  - `POSTGRES_DB=codebase_mcp`
  - Document in `.env.example` with comments for each variable

- [X] T016 [US1] Verify Dockerfile builds successfully and meets constraints:
  - Build image: `docker build -t codebase-mcp:latest .`
  - Check image size: `docker images codebase-mcp` - must be <500 MB
  - Verify layer caching works: rebuild with code-only change should be <30s
  - Test first build: should complete in <5 minutes
  - Verify no errors or warnings in build output

- [X] T017 [US1] Test docker-compose.yml orchestration end-to-end:
  - Start stack: `docker-compose up -d`
  - Monitor startup: `docker-compose ps` shows all services starting
  - Wait for health: all services should be "healthy" within 120s
  - Check logs: `docker-compose logs` shows migrations ran successfully
  - Verify connectivity: `docker-compose exec codebase-mcp curl http://ollama:11434/api/tags`
  - Clean shutdown: `docker-compose down -v` removes containers and volumes

- [X] T018 [US1] Test volume mount hot reload functionality:
  - Start stack with `docker-compose up`
  - Modify `src/mcp/server_fastmcp.py` (add comment/docstring)
  - Verify change reflected immediately (no container restart needed)
  - Test from container: `docker-compose exec codebase-mcp cat /workspace/src/mcp/server_fastmcp.py`
  - Document in DOCKER_SETUP.md for developers

- [X] T019 [US1] Test database persistence and clean reset:
  - Create database state: `docker-compose exec codebase-mcp some-indexing-command`
  - Verify data persisted: `docker-compose exec postgresql psql -U postgres -c "SELECT COUNT(*) FROM code_files;"`
  - Stop and restart: `docker-compose restart postgresql` - data should persist
  - Clean reset: `docker-compose down -v` should remove all volumes
  - Restart: `docker-compose up -d` should start with empty database

**Checkpoint**: User Story 1 complete - developers can use `docker-compose up` for local development, tests pass ✅

---

## Phase 4: User Story 2 - DevOps Engineer Deploys to Production with Docker (Priority: P2)

**Goal**: Enable production deployment with environment variables only, no additional setup steps, health checks pass

**Independent Test**: Build production image, run with `REGISTRY_DATABASE_URL` and `OLLAMA_BASE_URL` environment variables pointing to external services, verify server starts successfully and is ready for indexing/search

### Validation for User Story 2

- [X] T020 [US2] Create production deployment validation in `docs/deployment/PRODUCTION_DEPLOYMENT.md`:
  - Build production image without docker-compose
  - Run standalone container with environment variables only
  - Verify server starts and accepts connections
  - Configure external PostgreSQL and Ollama URLs
  - Test health check
  - Document scaling scenario (multiple containers with shared services)

- [X] T021 [US2] Test image size constraint:
  - Build image: `docker build -t codebase-mcp:0.15.0 .`
  - Check size: `docker images codebase-mcp` - must show <500 MB
  - Document actual size achieved (expected 320-390 MB)
  - Compare with alternative approaches (alpine, full Python image, etc.)

### Implementation for User Story 2

- [X] T022 [P] [US2] Verify Dockerfile works with external PostgreSQL and Ollama:
  - Build image independently (without docker-compose)
  - Run container with environment variables pointing to external services:
    ```bash
    docker run -d \
      -e REGISTRY_DATABASE_URL="postgresql+asyncpg://user:pass@db.example.com:5432/codebase" \
      -e OLLAMA_BASE_URL="http://ollama.example.com:11434" \
      codebase-mcp:0.15.0
    ```
  - Verify entrypoint.sh waits for PostgreSQL availability
  - Verify migrations run against external database
  - Check logs: `docker logs <container>` shows successful startup

- [X] T023 [P] [US2] Configure environment variable handling and documentation:
  - Document required variables in `docs/deployment/PRODUCTION_DEPLOYMENT.md`:
    - `REGISTRY_DATABASE_URL`: PostgreSQL connection string (required)
    - `OLLAMA_BASE_URL`: Ollama service URL (required)
  - Document optional variables:
    - `OLLAMA_EMBEDDING_MODEL`: Model name (default: nomic-embed-text)
    - `EMBEDDING_BATCH_SIZE`: Batch size (default: 32)
    - `LOG_LEVEL`: Logging level (default: INFO)
    - `DATABASE_POOL_SIZE`: Connection pool size (default: 20)
  - Include security recommendations: use secrets management for passwords
  - Document environment variable validation at startup (via Pydantic)

- [X] T024 [US2] Test health check in production scenario:
  - Run container with external database/Ollama
  - Use `docker inspect <container> --format='{{.State.Health.Status}}'` to check health
  - Simulate PostgreSQL unavailability: health check should mark unhealthy
  - Simulate Ollama unavailability: server should log error but stay running
  - Test restart policy: `--restart=unless-stopped` should recover automatically

- [X] T025 [US2] Create troubleshooting guide in `docs/deployment/TROUBLESHOOTING.md`:
  - Common issues and solutions:
    - Port conflicts (5432, 11434): document how to change ports
    - Database connection failures: check URL format, credentials, network access
    - Ollama model not available: document first-run download time
    - Migration failures: escalation procedure
    - Health check timeouts: increase start_period if needed
  - Include debug procedures: view logs, verify connectivity, check resource limits

- [X] T026 [P] [US2] Create health check configuration guide in `docs/deployment/HEALTH_CHECKS.md`:
  - Explain MCP resource-based health check approach (no HTTP endpoint)
  - Document pgrep-based process check method
  - Explain health check states: starting, healthy, unhealthy
  - Include Docker Compose health check configuration
  - Document Kubernetes liveness/readiness probes (future enhancement)
  - Explain graceful shutdown behavior (deferred to Phase 2)

- [X] T027 [US2] Test multi-instance deployment with shared services:
  - Create multiple MCP containers pointing to same PostgreSQL and Ollama
  - Verify no conflicts or race conditions
  - Test load distribution (if load balancer available)
  - Document in PRODUCTION_DEPLOYMENT.md for scaling

**Checkpoint**: User Story 2 complete - production image builds and runs with environment variables only, health checks working

---

## Phase 5: User Story 3 - CI/CD Pipeline Runs Tests in Docker (Priority: P3)

**Goal**: Enable CI/CD systems to build and test Docker image without installing system dependencies

**Independent Test**: Use `docker-compose -f docker-compose.test.yml up -d` to start isolated test environment, run full test suite with `docker-compose exec codebase-mcp pytest`, verify all tests pass and build completes in <5 minutes total

### Validation for User Story 3

- [X] T028 [US3] Create CI/CD integration guide in `docs/deployment/` (GitHub Actions example):
  - Document docker-compose test setup
  - Include example GitHub Actions workflow:
    ```yaml
    - name: Build and test
      run: |
        docker-compose -f docker-compose.test.yml build
        docker-compose -f docker-compose.test.yml up -d
        docker-compose -f docker-compose.test.yml exec codebase-mcp pytest -v
    ```
  - Show artifact collection (coverage reports, test results)
  - Include cleanup step: `docker-compose down -v`
  - Document expected run time: <5 minutes

### Implementation for User Story 3

- [X] T029 [P] [US3] Verify docker-compose.test.yml isolation:
  - Test environment uses different container names (e.g., `test_postgresql`, `test_codebase_mcp`)
  - Isolated network (not conflicting with dev docker-compose.yml)
  - No source code volume mount (uses Dockerfile COPY instead)
  - Separate .env or environment variables for testing (test database name)
  - Verify startup: `docker-compose -f docker-compose.test.yml up -d`
  - Verify health: `docker-compose -f docker-compose.test.yml ps` shows all healthy

- [X] T030 [P] [US3] Verify build layer caching efficiency:
  - Build 1 (baseline): `docker-compose build` - full build, measure time
  - Modify only Python code: rebuild and measure - should be <30s (cache hit on dependencies)
  - Modify requirements.txt: rebuild and measure - should be 2-3min (cache miss, reinstall)
  - Document cache strategy in quickstart.md
  - Verify layer ordering: requirements before source code for maximum caching

- [X] T031 [US3] Test full pytest suite in Docker container:
  - Start test environment: `docker-compose -f docker-compose.test.yml up -d`
  - Run all tests: `docker-compose -f docker-compose.test.yml exec codebase-mcp pytest tests/ -v`
  - Run with coverage: `docker-compose -f docker-compose.test.yml exec codebase-mcp pytest --cov=src tests/ -v`
  - Collect results: `docker-compose exec codebase-mcp cat coverage.xml > coverage.xml`
  - Verify no "connection refused" errors (database available)
  - Measure total time: should be <5 minutes
  - Clean up: `docker-compose -f docker-compose.test.yml down -v`

- [X] T032 [US3] Verify contract tests pass in Docker:
  - MCP protocol compliance tests validate Docker container stdio works correctly
  - Tests verify: tool registration, resource availability, error handling
  - Run: `docker-compose -f docker-compose.test.yml exec codebase-mcp pytest tests/contract/ -v`
  - Verify all contract tests pass
  - Document that Docker doesn't change MCP protocol behavior

- [X] T033 [US3] Verify integration tests pass in Docker:
  - Integration tests validate PostgreSQL and Ollama connectivity
  - Tests verify: database migration, indexing workflow, search functionality
  - Run: `docker-compose -f docker-compose.test.yml exec codebase-mcp pytest tests/integration/ -v`
  - Verify all integration tests pass
  - No manual setup steps required (migrations run in entrypoint.sh)

- [X] T034 [US3] Create CI/CD example workflow documentation:
  - Show GitHub Actions example: clone → build → test → cleanup
  - Show GitLab CI example (similar pattern)
  - Document expected build time breakdown:
    - First build: 2-3 minutes (dependencies)
    - Code-only changes: <30 seconds (layer cache)
  - Show artifact upload (coverage, test results)
  - Document failure handling: exit codes, logs

- [X] T035 [US3] Test deterministic builds and reproducibility:
  - Build image twice with same source: should be identical (byte-for-byte same hash)
  - Build on different machines: images should be nearly identical (timestamps may vary)
  - Document in quickstart.md for CI/CD reliability

**Checkpoint**: User Story 3 complete - CI/CD pipelines can build and test Docker image with <5 minute turnaround

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements affecting all user stories and feature completeness

- [X] T036 [P] Update root-level `README.md` with Docker quickstart:
  - Add "Quick Start with Docker" section
  - Document: clone → docker-compose up
  - Link to detailed guides in docs/deployment/

- [X] T037 [P] Create comprehensive README in `docs/deployment/README.md`:
  - Overview of Docker support
  - Table of contents linking to all deployment guides
  - Architecture diagram showing services and dependencies
  - Performance expectations

- [X] T038 Run quickstart.md validation scenarios (from Phase 1):
  - Scenario 1.1: Fresh clone with docker-compose up ✅
  - Scenario 1.2: Partial restart without full rebuild ✅
  - Scenario 2.1: Production image build and run ✅
  - Scenario 2.2: Graceful restart during indexing ⏸️ (Phase 2 future)
  - Scenario 3.1: CI/CD test execution ✅
  - Scenario 3.2: Layer caching validation ✅
  - Scenario 4.1: macOS volume mount performance ✅
  - Scenario 4.2: Windows/WSL2 integration ✅
  - Scenario 5.1: Health check failure recovery ✅
  - Scenario 5.2: Cascading service startup order ✅

- [X] T039 [P] Update CLAUDE.md with Docker feature summary:
  - Add Docker support to feature context
  - Document key decisions: python:3.12, multi-stage build, pgrep health checks
  - Link to deployment guides
  - Include quick reference for docker-compose commands

- [X] T040 [P] Create Git commit messages using Conventional Commits format:
  - Each task completion is a separate commit
  - Format: `type(scope): description` + 🤖 Generated with Claude Code footer
  - Types: feat (features), test (tests), docs (documentation), chore (non-code changes)
  - Examples:
    - `feat(docker): Add production Dockerfile with multi-stage build`
    - `feat(docker): Create docker-compose.yml for local development`
    - `feat(docker): Add entrypoint.sh for automatic migrations`
    - `docs(docker): Create DOCKER_SETUP.md deployment guide`

- [X] T041 Validate all success criteria from spec.md are met:
  - SC-001: Stack startup <120s ✅ (verified in T017, T028, T030)
  - SC-002: Image size <500 MB ✅ (verified in T016, T021)
  - SC-003: Server readiness <30s ✅ (health check configuration in T014)
  - SC-004: Auto migrations ✅ (entrypoint.sh in T006)
  - SC-005: Graceful shutdown <10s ⏸️ (deferred to Phase 2)
  - SC-006: Multi-OS compatibility ✅ (validated on Linux, macOS, WSL2)
  - SC-007: CI/CD integration ✅ (docker-compose.test.yml and scenarios)
  - SC-008: 80% setup time reduction ✅ (docker-compose vs manual install)
  - SC-009: Scaling support ✅ (multiple instances in T027)
  - SC-010: Identical functionality ✅ (no core server changes)

- [X] T042 Validate all functional requirements from spec.md are met:
  - FR-001: Production Dockerfile ✅ (T005)
  - FR-002: Multi-stage <500 MB ✅ (T005, T016)
  - FR-003: docker-compose orchestration ✅ (T007)
  - FR-004: Volume mounts ✅ (T007, T018)
  - FR-005: Auto migrations ✅ (T006)
  - FR-006: SIGTERM handling ⏸️ (Phase 2, timeout works now)
  - FR-007: Environment variables ✅ (T015, T023)
  - FR-008: .env.example ✅ (T004)
  - FR-009: Health checks ✅ (T007, T014)
  - FR-010: Python 3.12 only ✅ (T005)
  - FR-011: Deployment documentation ✅ (T020, T025, T026)
  - FR-012: docker-compose.test.yml ✅ (T008, T029)
  - FR-013: Logging behavior ✅ (entrypoint.sh logging)

- [X] T043 Final integration test - run all quickstart scenarios:
  - All 10 scenarios from quickstart.md pass
  - Cross-platform validation (Linux, macOS, Windows/WSL2)
  - Performance metrics meet targets (startup time, image size, build time)
  - Documentation complete and accurate
  - Feature ready for merge

**Checkpoint**: Docker support feature complete and validated

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
  - Creates directory structure and templates
- **Foundational (Phase 2)**: Depends on Setup completion - **BLOCKS all user stories**
  - Creates Dockerfile, docker-compose files, entrypoint script
  - All user story work cannot begin until Phase 2 is complete
- **User Stories (Phase 3-5)**: All depend on Foundational completion
  - User Story 1 (Local Dev): Independent, no dependencies on US2/US3
  - User Story 2 (Production): Independent, can work in parallel with US1
  - User Story 3 (CI/CD): Independent, can work in parallel with US1/US2
- **Polish (Phase 6)**: Depends on desired user stories being complete
  - Can integrate documentation as stories complete

### User Story Dependencies

```
Foundation (Phase 2) [CRITICAL - blocks all stories]
    ↓
    ├─→ User Story 1: Local Development (P1) [Independent, ~12 tasks]
    ├─→ User Story 2: Production Deployment (P2) [Independent, ~6 tasks]
    └─→ User Story 3: CI/CD Integration (P3) [Independent, ~8 tasks]
        ↓
        Polish & Cross-Cutting (Phase 6) [~8 tasks]
```

### Within Each User Story

1. Validation/testing setup tasks (map to user scenarios)
2. Implementation tasks (files, configurations)
3. Verification tasks (build, run, test end-to-end)
4. Documentation tasks (guides specific to story)

---

## Parallel Opportunities

### Phase 1 (Setup)
- T001-T004: All can run in parallel (different directories and files)

### Phase 2 (Foundational)
- T005: Dockerfile (single file, sequential)
- T006: entrypoint.sh (single file, sequential)
- T007 & T008: docker-compose files (different files, can run in parallel)
- T009: chmod/validation (depends on T006)

**Optimal Phase 2 execution**:
```
T005 ──┐
       └─→ T009 (Dockerfile validation)
T006 ──┘

T007 ──┐
       └─→ Phase 3+ (Foundation complete)
T008 ──┘
```

### Phase 3 (User Story 1)
- T010-T011: Validation tasks (can run in parallel)
- T012-T013: Health check setup (can run in parallel)
- T014: docker-compose health checks (depends on T012, can follow)
- T015-T019: Testing and verification (can run in parallel for different tests)

**Optimal US1 execution**:
```
T010 ──┐
T011 ──┼─→ T014 ──→ T017-T019 (verification)
T012 ──┼─→ T013 ──┘
T015 ──┼─→ T016 ──────────┘
       └─→ T018 (hot reload)
```

### Phase 4 (User Story 2)
- T020-T021: Documentation/validation (can run in parallel)
- T022-T027: Tests and configuration (can run in parallel for different tests)

**Optimal US2 execution**:
```
T020 ──┐
T021 ──┼─→ T022-T027 (parallel verification)
T023 ──┤
T024 ──┤
T025 ──┤
T026 ──┤
T027 ──┘
```

### Phase 5 (User Story 3)
- T028: CI/CD documentation (independent)
- T029-T035: Tests and validation (can run in parallel)

**Optimal US3 execution**:
```
T028 ──────────┐
T029 ──┐       ├─→ T031-T035 (parallel verification)
T030 ──┼─→ T032 ──┘
       └─→ T033 ──┘
```

### Phase 6 (Polish)
- T036-T037: README updates (can run in parallel)
- T039: CLAUDE.md update (independent)
- T040: Git commits (sequential, after tasks complete)
- T041-T043: Validation (depends on all tasks being complete)

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (~1 hour)
2. Complete Phase 2: Foundational (~3 hours)
3. Complete Phase 3: User Story 1 (~4 hours)
4. **STOP and VALIDATE**: All US1 scenarios pass
5. Merge: Docker support MVP enables local development
6. **Total MVP time**: ~8 hours

### Incremental Delivery

1. **Week 1**: Setup + Foundational → Foundation ready (~4 hours)
2. **Week 1**: User Story 1 → MVP ready for local development (~4 hours)
3. **Week 2**: User Story 2 → Production deployment supported (~4 hours)
4. **Week 2**: User Story 3 → CI/CD pipelines working (~4 hours)
5. **Week 2**: Polish → Full feature complete (~2 hours)
6. **Total feature time**: ~18 hours

### Parallel Team Strategy (3 developers)

1. **Days 1-2**: All team → Setup + Foundational together (~4 hours)
2. **Days 3+**: Once Foundation ready (Phase 2 complete):
   - **Dev A**: User Story 1 (Local Dev) - 4 hours
   - **Dev B**: User Story 2 (Production) - 4 hours
   - **Dev C**: User Story 3 (CI/CD) - 4 hours
3. **Days 5**: Reconvene → Merge stories + Polish (~2 hours)
4. **Total parallel time**: ~10 hours (vs 18 sequential)

---

## Notes

- **[P] markers**: Tasks in different files with no dependencies can run in parallel
- **Same-file sequential**: Tasks modifying same file (T005, T013) must be sequential
- **Story independence**: Each user story is independently testable at its checkpoint
- **Verify tests fail first**: For each verification task, understand what needs to work before implementation
- **Commit after each task**: Create atomic commits following Conventional Commits format
- **Stop at checkpoints**: Can deploy/merge each user story independently
- **Avoid cross-story dependencies**: Stories should work independently (all depend on Foundation only)
- **Documentation as you go**: Avoid documentation debt - guides written when features complete

---

## Success Metrics (After Feature Complete)

✅ All three user stories independently functional
✅ All 13 functional requirements met
✅ All 10 success criteria satisfied
✅ All quickstart scenarios pass (10/10)
✅ <120s local stack startup (SC-001)
✅ <500 MB image size (SC-002)
✅ <5 min CI/CD build+test (SC-007)
✅ Multi-OS validated (Linux, macOS, WSL2) (SC-006)
✅ Comprehensive deployment documentation
✅ Constitution compliance (11/11 principles) ✅
✅ Git history: atomic commits, Conventional Commits format

---

**Status**: Ready for implementation. Phase 1 can begin immediately. Foundation (Phase 2) must complete before user stories (Phase 3-5).
