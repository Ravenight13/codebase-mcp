# Implementation Plan: Docker Support for Codebase MCP Server

**Branch**: `015-add-support-docker` | **Date**: 2025-11-06 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/015-add-support-docker/spec.md`

## Summary

Enable containerized deployment of the Codebase MCP Server by providing a production-ready Dockerfile (multi-stage, <500 MB), docker-compose.yml orchestration for local development (PostgreSQL + Ollama + MCP server), and comprehensive deployment documentation. Implementation uses python:3.12-slim base image, two-stage builds for optimization, MCP resource-based health checks (no HTTP endpoint), and entrypoint script for automatic database migrations. This feature addresses three prioritized user stories: P1 frictionless local development with `docker-compose up`, P2 production deployment with environment variable configuration, and P3 CI/CD test automation in containers.

## Technical Context

**Language/Version**: Python 3.12 (clarified from 3.11+ to simplify multi-version complexity)
**Primary Dependencies**: Docker Engine 20.10+, Docker Compose 2.0+, FastMCP (existing), PostgreSQL 14+ (official image), Ollama (official image)
**Storage**: PostgreSQL 14+ with pgvector (containerized or external via env vars), mounted volumes for data persistence
**Testing**: pytest with docker-compose test variant, integration tests validate containerized behavior
**Target Platform**: Linux (primary), macOS (Docker Desktop), Windows (WSL2)
**Project Type**: Single-project MCP server (no frontend/backend split)
**Performance Goals**: 120s stack startup (SC-001), 30s server readiness (SC-003), 10s graceful shutdown (SC-005)
**Constraints**: <500 MB image size (SC-002), multi-OS compatibility (SC-006), zero changes to core server code required
**Scale/Scope**: 1 Dockerfile, 1 docker-compose.yml (dev), 1 docker-compose.test.yml, entrypoint script, .env.example, deployment docs

## Constitution Check

**Gate: Phase 0 Research** - PASS ✅

| Principle | Status | Validation |
|-----------|--------|-----------|
| I. Simplicity Over Features | ✅ PASS | Containerization only (no schema changes, feature extensions, or scope creep). Docker support explicitly in-scope per spec. Out-of-scope items (Kubernetes, secret management) deferred. |
| II. Local-First Architecture | ✅ PASS | Containerized PostgreSQL and Ollama stay local. No cloud APIs added. Database remains standard PostgreSQL. Network traffic limited to localhost/container network. |
| III. Protocol Compliance (MCP via SSE) | ✅ PASS | Docker containers don't affect MCP protocol (stdio/SSE transport unchanged). Health checks use MCP `health://status` resource (no protocol violation). Logging via entrypoint captures output properly. |
| IV. Performance Guarantees | ✅ PASS | Containerization adds ~2-5% overhead (acceptable per risks). Success criteria include explicit performance targets (120s startup, 500ms search unchanged). Docker health check probes are <5s. |
| V. Production Quality Standards | ✅ PASS | Error handling in entrypoint script validates database connectivity with retries. Configuration validates via Pydantic BaseSettings (unchanged). Logging remains file-based (no stdout pollution). |
| VI. Specification-First Development | ✅ PASS | Feature specification complete with 13 functional requirements, 3 user stories, 10 success criteria, edge cases, assumptions. Clarifications resolved. This plan follows spec. |
| VII. Test-Driven Development | ✅ PASS | Tests written before implementation (marked in tasks.md). Contract tests validate MCP transport works in Docker. Integration tests validate postgres/ollama connectivity. |
| VIII. Pydantic-Based Type Safety | ✅ PASS | No changes to existing Pydantic models. Entrypoint script uses shell (simple validation). Configuration remains via environment variables (validated by Pydantic at runtime). |
| IX. Orchestrated Subagent Execution | ✅ PASS | Three independent artifact areas (Dockerfile, docker-compose, entrypoint) can be implemented in parallel. Test layer separate. |
| X. Git Micro-Commit Strategy | ✅ PASS | Feature branch 015-add-support-docker created. Tasks will use Conventional Commits (feat, test, docs). One logical change per commit. |
| XI. FastMCP and Python SDK Foundation | ✅ PASS | Docker containers run existing FastMCP-based server. No changes to FastMCP code. SSE transport works through container stdio. |

**Gate Result**: ✅ ALL PRINCIPLES SATISFIED - Proceed to Phase 1

## Project Structure

### Documentation (this feature)

```
specs/015-add-support-docker/
├── spec.md                      # Feature specification (complete ✅)
├── plan.md                      # This file (Phase 0-1 planning)
├── research.md                  # Phase 0 output (Docker best practices)
├── data-model.md                # Phase 1 output (configuration entities)
├── contracts/                   # Phase 1 output (API contracts if applicable)
│   └── docker-compose.schema.json  # docker-compose validation schema
└── quickstart.md                # Phase 1 output (integration test scenarios)
```

### Source Code (repository root)

```
Root Directory:
├── Dockerfile                   # Production image definition (python:3.12-slim, multi-stage)
├── docker-compose.yml           # Development orchestration (PostgreSQL + Ollama + MCP)
├── docker-compose.test.yml      # Test environment variant
├── .dockerignore                # Files to exclude from Docker build context
├── .env.example                 # Template for environment configuration
├── scripts/docker/
│   └── entrypoint.sh           # Container startup script (migrations + server)
├── docs/deployment/             # New documentation directory
│   ├── DOCKER_SETUP.md         # Local setup guide
│   ├── PRODUCTION_DEPLOYMENT.md # Production deployment guide
│   ├── TROUBLESHOOTING.md       # Common issues and solutions
│   └── HEALTH_CHECKS.md         # Health check configuration

Existing Structure (unchanged):
src/mcp/
├── server_fastmcp.py           # Entry point (unchanged)
alembic/
├── versions/                    # Database migrations (unchanged)
pyproject.toml                   # Dependencies (unchanged)
```

**Structure Decision**: Single-project structure (no monorepo/multi-app). Docker support is additive - Dockerfile, compose files, entrypoint script, and documentation are new additions. No changes to existing source code structure. All paths relative to repository root.

## Phase 0: Research Complete ✅

**Research Deliverables**: `/workspace/DOCKER_RESEARCH.md`, `/workspace/DOCKER_BEST_PRACTICES_SUMMARY.md`

### Key Research Findings

1. **Multi-Stage Dockerfile**: python:3.12-slim base image with two-stage build (builder + runtime) achieves 320-390 MB image size (under 500 MB spec). Layer ordering for cache efficiency.

2. **Health Checks for Stdio Services**: Custom shell script using `pgrep` (process-based check) is recommended for MCP stdio servers. Minimal overhead (<1ms), <100 bytes script. Configuration: `start_period: 20s`, `interval: 30s`, `retries: 3`.

3. **Docker-Compose Orchestration**: Service dependency ordering with health checks ensures PostgreSQL starts first, then Ollama, then MCP server. Volume mounting (`:cached` for source code) enables hot reload for development.

4. **Graceful Shutdown**: SIGTERM signal handler in Python with timeout strategy. Docker `stop_grace_period` set appropriately. Deferred to Phase 2 (not blocking core functionality).

5. **Database Migrations**: Entrypoint script wrapper executes `alembic upgrade head` before starting server. Retry logic handles transient database unavailability.

## Phase 1: Design Artifacts (IN PROGRESS)

### Data Model (entities, configuration)

See `data-model.md` - Defines configuration entities (DockerConfig, ComposeServiceConfig, HealthCheckConfig) and their relationships.

### API Contracts

See `contracts/` - OpenAPI/JSON schemas for docker-compose.yml structure and environment variable schema.

### Quickstart Integration Test Scenarios

See `quickstart.md` - Step-by-step scenarios for testing Docker deployment locally and in CI/CD.

## Complexity Tracking

No complexity violations. Containerization is pure addition (new files, no changes to core server). Constitution compliance verified above.

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Python Version | 3.12 only | Simplification from multi-version support. Reduces build/test complexity. Can be extended in future feature. |
| Health Check | MCP resource-based (no HTTP) | Aligns with stdio architecture. No additional framework needed. Simple shell script. |
| Logging | Existing behavior (no changes) | Uses current file-based logging. Structured logging deferred to future. |
| Graceful Shutdown | Deferred to Phase 2 | Core containerization (startup, migrations, compose) implemented in Phase 1. Shutdown handler a nice-to-have. |
| Kubernetes Support | Out of scope | Explicitly deferred per spec. docker-compose is sufficient for MVP. |
