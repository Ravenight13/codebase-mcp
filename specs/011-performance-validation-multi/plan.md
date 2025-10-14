# Implementation Plan: Performance Validation & Multi-Tenant Testing

**Branch**: `011-performance-validation-multi` | **Date**: 2025-10-13 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/011-performance-validation-multi/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This phase validates that the split MCP architecture (workflow-mcp on port 8010, codebase-mcp on port 8020) meets all constitutional performance targets, handles concurrent load gracefully, and maintains operational resilience after Phases 01-05 implementation. The technical approach uses pytest-benchmark for performance regression detection, k6 for load testing, integration test suites for cross-server workflows, and comprehensive observability via health/metrics endpoints.

## Technical Context

**Language/Version**: Python 3.11+ (required for async features and modern type hints)
**Primary Dependencies**: FastAPI, FastMCP, MCP Python SDK, pytest-benchmark, pytest-asyncio, httpx, k6 (for load testing)
**Storage**: PostgreSQL 14+ with pgvector (separate databases per server: workflow-mcp and codebase-mcp)

**Tool Version Requirements** (for reproducibility):

| Tool | Minimum Version | Rationale |
|------|-----------------|-----------|
| Python | 3.11+ | Async features, modern type hints (Constitutional Principle VIII) |
| PostgreSQL | 14+ | pgvector extension for semantic search |
| pytest-benchmark | 4.0+ | JSON baseline format support |
| k6 | 0.45+ | SSE transport support for MCP protocol testing |
| tree-sitter | 0.20+ | Python/JavaScript parser support for test fixtures |
| pytest | 7.0+ | Modern async test support |
| httpx | 0.24+ | Async HTTP client for integration tests |
| pytest-asyncio | 0.21+ | Async test fixture support |

**Testing**: pytest with pytest-benchmark (performance), pytest-asyncio (async), k6 (load testing), contract tests (MCP protocol)
**Target Platform**: macOS and Linux development platforms (production deployment follows Phase 06 validation)
**Project Type**: Single project with dual MCP servers (split architecture validated in Phase 05)
**Performance Goals**:
  - Codebase-mcp: 10k files indexed in <60s (p95), search queries <500ms (p95)
  - Workflow-mcp: project switching <50ms (p95), entity queries <100ms (p95)
  - Both servers: 50 concurrent clients without degradation, 99.9% uptime over 1 hour
**Constraints**:
  - Performance variance ≤10% from pre-split baseline measurements
  - Connection pool limits: workflow-mcp (min=2, max=10), codebase-mcp (min=5, max=20)
  - Health check response time <50ms
  - Database reconnection within 5 seconds with exponential backoff
**Scale/Scope**:
  - Test repositories: 10,000 files (baseline), 50,000 files (edge case)
  - Entity count: 1,000 entities across multiple projects for workflow-mcp
  - Concurrent clients: 10 (normal load), 50 (stress test)
  - Test duration: 1 hour continuous load testing for uptime validation

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Simplicity Over Features
- **Status**: ✅ PASS
- **Justification**: This feature focuses exclusively on validating existing functionality (performance, resilience, observability). No new features are added - only testing infrastructure to validate constitutional compliance. Scope is tightly bounded to Phase 06 validation activities.

### Principle II: Local-First Architecture
- **Status**: ✅ PASS
- **Justification**: Performance validation tests local operations against local PostgreSQL and Ollama instances. Load testing simulates local concurrent clients. No cloud APIs or external dependencies introduced.

### Principle III: Protocol Compliance (MCP via SSE)
- **Status**: ✅ PASS
- **Justification**: Integration tests validate MCP protocol compliance for both servers. Contract tests ensure no stdout/stderr pollution. Performance tests validate protocol behavior under load. No protocol modifications required.

### Principle IV: Performance Guarantees
- **Status**: ✅ PASS - This is the PRIMARY focus
- **Justification**: This entire feature validates constitutional performance targets:
  - Indexing <60s (p95) for 10k files
  - Search <500ms (p95)
  - Project switching <50ms (p95)
  - Entity queries <100ms (p95)
  - Performance regression detection ensures ongoing compliance

### Principle V: Production Quality Standards
- **Status**: ✅ PASS
- **Justification**: Feature validates error handling, database resilience, graceful degradation patterns. Health/metrics endpoints provide comprehensive observability. Structured logging validation ensures JSON format compliance.

### Principle VI: Specification-First Development
- **Status**: ✅ PASS
- **Justification**: spec.md completed before planning (includes acceptance criteria, test scenarios, success criteria). This plan.md follows specification-first workflow.

### Principle VII: Test-Driven Development
- **Status**: ✅ PASS
- **Justification**: This feature IS the test development phase. All tasks involve writing performance tests, integration tests, load tests, and observability validation. Tests validate acceptance criteria from spec.md.

### Principle VIII: Pydantic-Based Type Safety
- **Status**: ✅ PASS
- **Justification**: Test code follows mypy --strict requirements. Performance metrics use Pydantic models for validation. Health check responses use Pydantic for schema enforcement.

### Principle IX: Orchestrated Subagent Execution
- **Status**: ✅ PASS
- **Justification**: Implementation phase will use orchestrated subagents to write tests in parallel (performance tests, integration tests, load tests can be developed concurrently per server).

### Principle X: Git Micro-Commit Strategy
- **Status**: ✅ PASS
- **Justification**: Feature branch `011-performance-validation-multi` created. Commits will follow Conventional Commits (`test(perf): add indexing benchmark`, `test(integration): validate cross-server workflow`). Micro-commits after each test suite completion.

### Principle XI: FastMCP and Python SDK Foundation
- **Status**: ✅ PASS
- **Justification**: Tests validate existing FastMCP/MCP SDK implementation. No framework changes required. Integration tests ensure FastMCP protocol compliance under load.

**Overall Assessment**: ✅ ALL GATES PASS - Feature is purely validation/testing, no architectural changes required.

## Project Structure

### Documentation (this feature)

```
specs/011-performance-validation-multi/
├── spec.md              # Feature specification (WHAT/WHY)
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output - research on testing approaches
├── data-model.md        # Phase 1 output - performance metrics data models
├── quickstart.md        # Phase 1 output - validation test scenarios
├── contracts/           # Phase 1 output - health/metrics endpoint schemas
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
src/
├── config/                    # Configuration management
│   ├── settings.py           # Pydantic settings (connection pools, ports)
│   └── logging_config.py     # Structured logging configuration
├── connection_pool/          # Connection pool management (NEW: Phase 03)
│   ├── manager.py           # Pool manager with monitoring
│   ├── metrics.py           # Pool utilization metrics
│   └── health.py            # Pool health checks
├── database/                 # Database layer
│   ├── session.py           # Async session management
│   └── migrations/          # Alembic migrations
├── mcp/                      # MCP server implementations
│   ├── server_fastmcp.py    # Codebase-mcp server (port 8020)
│   └── workflow_server.py   # Workflow-mcp server (port 8010) [hypothetical]
├── models/                   # Pydantic data models
│   ├── performance.py       # Performance metrics models (NEW: Phase 06)
│   └── health.py            # Health check response models (NEW: Phase 06)
└── services/                 # Business logic
    ├── indexer.py           # Code indexing service
    ├── search.py            # Semantic search service
    ├── embeddings.py        # Embedding generation
    └── health_service.py    # Health/metrics service (NEW: Phase 06)

tests/
├── benchmarks/               # Performance baseline tests (NEW: Phase 06)
│   ├── test_indexing_perf.py       # Indexing performance validation
│   ├── test_search_perf.py         # Search performance validation
│   └── test_workflow_perf.py       # Workflow-mcp performance validation
├── contract/                 # MCP protocol compliance tests
│   ├── test_transport_compliance.py
│   └── test_schema_generation.py
├── integration/              # Integration tests
│   ├── test_cross_server_workflow.py  # Cross-server integration (NEW)
│   ├── test_resilience.py            # Error recovery validation (NEW)
│   └── test_observability.py         # Health/metrics validation (NEW)
├── performance/              # Performance regression tests
│   ├── test_baseline.py              # Baseline tracking
│   └── test_regression.py            # Regression detection (NEW)
└── load/                     # Load testing scripts (NEW: Phase 06)
    ├── k6_codebase_load.js          # Codebase-mcp load test
    ├── k6_workflow_load.js          # Workflow-mcp load test
    └── scenarios/                    # Load test scenarios

scripts/
├── collect_baseline.sh       # Baseline metrics collection
├── run_load_tests.sh         # Load testing orchestration (NEW: Phase 06)
└── validate_performance.sh   # Performance validation automation (NEW: Phase 06)

docs/
├── performance/              # Performance documentation
│   ├── baseline-pre-split.json   # Pre-split baseline (assumed exists)
│   ├── baseline-post-split.json  # Post-split baseline (NEW: Phase 06)
│   └── validation-report.md      # Phase 06 validation report (NEW)
└── operations/               # Operational runbooks
    ├── health-monitoring.md      # Health check guide (NEW: Phase 06)
    ├── performance-tuning.md     # Performance tuning guide (NEW: Phase 06)
    └── incident-response.md      # Incident response runbook (NEW: Phase 06)
```

**Structure Decision**: This feature uses the existing single-project structure (Option 1) with extensions for Phase 06 validation activities. New directories include:
- `tests/benchmarks/` - Performance baseline validation tests
- `tests/load/` - k6 load testing scripts for concurrent client simulation
- `tests/integration/` additions - Cross-server workflow validation
- `scripts/` additions - Performance validation automation
- `docs/performance/` - Baseline metrics and validation reports
- `docs/operations/` - Operational runbooks for production deployment

The structure maintains separation between codebase-mcp (existing) and workflow-mcp (hypothetical for cross-server testing). All new code follows constitutional principles (async operations, Pydantic models, mypy --strict compliance).

## Complexity Tracking

*No complexity violations - all constitutional gates passed. This section is empty per template guidance.*

---

## Phase 1 Completion: Post-Design Constitution Re-Evaluation

**Status**: ✅ ALL GATES REMAIN PASSED

### Re-Evaluation Summary

After completing Phase 1 design (research.md, data-model.md, contracts/, quickstart.md), all constitutional principles remain compliant:

### Principle I: Simplicity Over Features
- **Re-evaluation**: ✅ PASS
- **Design Impact**: Testing infrastructure focuses exclusively on validation (no feature additions)
- **Artifacts**: 6 test scenarios, 2 API endpoints (health, metrics), 5 Pydantic models
- **Justification**: Minimal testing infrastructure required for constitutional validation

### Principle II: Local-First Architecture
- **Re-evaluation**: ✅ PASS
- **Design Impact**: All testing against local PostgreSQL and Ollama
- **Dependencies Added**: k6 (local load testing), pytest-benchmark (local performance testing)
- **Justification**: No cloud dependencies introduced

### Principle III: Protocol Compliance (MCP via SSE)
- **Re-evaluation**: ✅ PASS
- **Design Impact**: Health/metrics endpoints exposed via FastMCP resources (`@mcp.resource()`)
- **Contract Tests**: OpenAPI schemas validate MCP protocol compliance
- **Justification**: Framework-level protocol handling via FastMCP maintains compliance

### Principle IV: Performance Guarantees
- **Re-evaluation**: ✅ PASS - PRIMARY VALIDATION
- **Design Impact**: Comprehensive performance validation infrastructure
  - pytest-benchmark for baseline tracking
  - k6 for load testing (50 concurrent clients)
  - Hybrid regression detection (10% degradation + constitutional targets)
- **Targets Validated**:
  - Indexing <60s (p95)
  - Search <500ms (p95)
  - Project switching <50ms (p95)
  - Entity queries <100ms (p95)
- **Justification**: This feature IS the enforcement mechanism for Principle IV

### Principle V: Production Quality Standards
- **Re-evaluation**: ✅ PASS
- **Design Impact**:
  - Health check endpoint with <50ms response time requirement
  - Metrics endpoint with Prometheus-compatible format
  - Structured logging validation (JSON format with required fields)
  - Database reconnection with 5-second detection window
- **Justification**: Observability infrastructure validates production quality

### Principle VI: Specification-First Development
- **Re-evaluation**: ✅ PASS
- **Design Impact**: Planning completed with all Phase 1 artifacts generated
- **Workflow Compliance**: `/specify` → `/plan` → Phase 0 (research) → Phase 1 (design)
- **Justification**: Spec-first workflow followed correctly

### Principle VII: Test-Driven Development
- **Re-evaluation**: ✅ PASS
- **Design Impact**: Comprehensive test scenarios defined in quickstart.md
- **Test Coverage**:
  - 6 integration test scenarios
  - Performance benchmarks for all constitutional targets
  - Load testing scenarios (10 and 50 concurrent clients)
  - Resilience tests (database failures, server isolation)
- **Justification**: Testing infrastructure is the feature

### Principle VIII: Pydantic-Based Type Safety
- **Re-evaluation**: ✅ PASS
- **Design Impact**: 5 Pydantic models with validators
  - PerformanceBenchmarkResult (with percentile ordering validators)
  - IntegrationTestCase (with step sequencing validators)
  - LoadTestResult (with computed fields for derived metrics)
  - HealthCheckResponse (with pool utilization calculation)
  - MetricsResponse (with histogram bucket validation)
- **Justification**: All data models use Pydantic with explicit validators

### Principle IX: Orchestrated Subagent Execution
- **Re-evaluation**: ✅ PASS
- **Design Impact**: Implementation phase will use orchestrated subagents
- **Parallelization Opportunities**:
  - Performance tests can run in parallel (different operations)
  - Integration tests can run in parallel (different scenarios)
  - Load tests can run in parallel (different servers)
- **Justification**: Test implementation lends itself to parallel execution

### Principle X: Git Micro-Commit Strategy
- **Re-evaluation**: ✅ PASS
- **Design Impact**: Feature branch `011-performance-validation-multi` active
- **Commit Strategy**: Micro-commits after each test suite completion
  - `test(perf): add indexing benchmark`
  - `test(integration): add cross-server workflow validation`
  - `test(load): add k6 load testing for codebase-mcp`
- **Justification**: TDD approach with micro-commits aligns with principle

### Principle XI: FastMCP and Python SDK Foundation
- **Re-evaluation**: ✅ PASS
- **Design Impact**: Health/metrics exposed via FastMCP resource registration
  - `@mcp.resource("health://status")` for health checks
  - `@mcp.resource("metrics://prometheus")` for metrics
- **No Protocol Changes**: Tests validate existing FastMCP implementation
- **Justification**: Framework usage consistent with constitutional principle

### Design Complexity Analysis

**Artifacts Generated**:
- 1 research document (7 research areas, 7 technical decisions)
- 1 data model document (5 Pydantic models, 4 relationships)
- 3 contract files (2 OpenAPI schemas, 1 README)
- 1 quickstart document (6 test scenarios, 15+ test cases)

**Dependencies Added**:
- k6 (load testing) - widely adopted standard tool
- pytest-benchmark (performance testing) - pytest ecosystem integration

**Complexity Justification**: Minimal complexity added relative to validation scope. All infrastructure serves constitutional validation purpose.

### Overall Assessment

✅ **ALL CONSTITUTIONAL GATES PASSED POST-DESIGN**

No architectural changes required. Design artifacts (research, data models, contracts, test scenarios) maintain constitutional compliance. Ready to proceed to Phase 2 (task generation via `/speckit.tasks` command).

---

## Phase 2 Planning (NOT EXECUTED - described only)

The `/speckit.plan` command stops after Phase 1 completion. Phase 2 (task generation) is executed by the separate `/speckit.tasks` command.

**Phase 2 Overview**:
- Generate ordered task breakdown in `tasks.md`
- Tasks marked `[P]` for parallel execution where applicable
- TDD approach: test tasks before implementation tasks
- Dependency analysis ensures proper task ordering

**Expected Task Categories**:
1. **Setup Tasks**: Test fixtures, repository generation, database setup
2. **Model Implementation**: Pydantic models in `src/models/`
3. **Endpoint Implementation**: Health/metrics endpoints in `src/mcp/`
4. **Test Implementation**: Benchmarks, integration tests, load tests
5. **Documentation**: Performance reports, operational runbooks
6. **Validation**: End-to-end scenario validation

---

## Planning Completion Summary

### Artifacts Generated

| Artifact | Path | Lines | Purpose |
|----------|------|-------|---------|
| plan.md | specs/011-performance-validation-multi/ | 280+ | This file - implementation plan |
| research.md | specs/011-performance-validation-multi/ | 450+ | Technical research decisions |
| data-model.md | specs/011-performance-validation-multi/ | 550+ | Pydantic model definitions |
| contracts/health-endpoint.yaml | specs/011-performance-validation-multi/ | 180+ | Health check OpenAPI schema |
| contracts/metrics-endpoint.yaml | specs/011-performance-validation-multi/ | 220+ | Metrics OpenAPI schema |
| contracts/README.md | specs/011-performance-validation-multi/ | 150+ | Contract usage guide |
| quickstart.md | specs/011-performance-validation-multi/ | 700+ | Integration test scenarios |

**Total**: 7 artifacts, ~2500 lines of planning documentation

### Key Decisions Documented

1. **Performance Testing**: pytest-benchmark with JSON baseline storage
2. **Load Testing**: k6 with JavaScript scenario definitions
3. **Integration Testing**: pytest + httpx async client
4. **Health/Metrics**: FastMCP resources with Pydantic models
5. **Resilience Testing**: pytest-mock with timeout simulation
6. **Regression Detection**: Hybrid approach (10% degradation + constitutional targets)
7. **Test Data**: Fixture-based generation with tree-sitter

### Constitutional Compliance Verified

- ✅ All 11 principles pass pre-design gate
- ✅ All 11 principles pass post-design re-evaluation
- ✅ No complexity violations requiring justification
- ✅ No architectural changes required
- ✅ Feature scope tightly bounded to validation activities

### Next Steps

Execute `/speckit.tasks` command to generate dependency-ordered task breakdown in `tasks.md`.

**Command**: `/speckit.tasks`

**Expected Output**: `specs/011-performance-validation-multi/tasks.md` with TDD-ordered tasks, parallel execution markers `[P]`, and dependency analysis.

---

## References

- **Feature Specification**: `specs/011-performance-validation-multi/spec.md`
- **Constitution**: `.specify/memory/constitution.md`
- **Branch**: `011-performance-validation-multi`
- **Planning Workflow**: `.specify/templates/commands/plan.md`
