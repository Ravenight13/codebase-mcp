# Tasks: Performance Validation & Multi-Tenant Testing

**Input**: Design documents from `/specs/011-performance-validation-multi/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Note**: This is a validation/testing feature - tests ARE the implementation. All tasks involve writing tests to validate constitutional compliance.

**Organization**: Tasks grouped by user story (US1-US5) for independent validation of each acceptance scenario.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task validates (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions
- Tests: `tests/` at repository root
- Models: `src/models/` for Pydantic validation models
- Scripts: `scripts/` for automation
- Docs: `docs/performance/` and `docs/operations/` for reports

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Test infrastructure initialization and fixture creation

- [X] T001 Create test directory structure for performance validation (tests/benchmarks/, tests/load/, tests/integration/resilience/, tests/integration/observability/)
- [X] T002 Create test fixtures for repository generation in tests/fixtures/test_repository.py (10k and 50k file fixtures using tree-sitter)
- [X] T003 [P] Create test fixtures for workflow-mcp data in tests/fixtures/workflow_fixtures.py (projects, entities, work items)
- [X] T004 [P] Install testing dependencies (pytest-benchmark, pytest-asyncio, httpx, k6) via pip/uv
- [X] T005 [P] Create performance baseline storage directory structure (performance_baselines/, docs/performance/)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core models and services needed by ALL user stories

**⚠️ CRITICAL**: No user story validation can begin until these models exist

- [X] T006 [P] Create PerformanceBenchmarkResult Pydantic model in src/models/performance.py (with percentile validators per data-model.md lines 20-141)
- [X] T007 [P] Create IntegrationTestCase and IntegrationTestStep models in src/models/testing.py (per data-model.md lines 160-305)
- [X] T008 [P] Create LoadTestResult with nested ErrorBreakdown and ResourceUsageStats models in src/models/load_testing.py (per data-model.md lines 327-520)
- [X] T009 [P] Create HealthCheckResponse and ConnectionPoolStats models in src/models/health.py (per data-model.md lines 540-627)
- [X] T010 [P] Create MetricsResponse with LatencyHistogram and MetricCounter models in src/models/metrics.py (per data-model.md lines 648-756)
- [X] T011 Create baseline comparison script in scripts/compare_baselines.py (hybrid regression detection: 10% degradation + constitutional targets per research.md lines 268-305)
- [X] T012 Create performance validation automation script in scripts/validate_performance.sh (orchestrates benchmarks and comparison)

**Checkpoint**: Foundation ready - all Pydantic models validated, baseline infrastructure complete

---

## Phase 3: User Story 1 - Performance Baseline Validation (Priority: P1) 🎯 MVP

**Goal**: Verify both servers meet constitutional performance targets with <10% variance from pre-split baseline

**Independent Test**: Run benchmark suite against test repository and compare results to baseline JSON files

### Implementation for User Story 1

- [X] T013 [P] [US1] Create indexing performance benchmark in tests/benchmarks/test_indexing_perf.py (pytest-benchmark with 5 iterations, validate <60s p95 per quickstart.md lines 69-90)
- [X] T014 [P] [US1] Create search performance benchmark in tests/benchmarks/test_search_perf.py (10 concurrent clients, validate <500ms p95)
- [X] T015 [P] [US1] Create workflow-mcp project switching benchmark in tests/benchmarks/test_workflow_perf.py (20 consecutive switches, validate <50ms p95)
- [X] T016 [P] [US1] Create workflow-mcp entity query benchmark in tests/benchmarks/test_workflow_perf.py (1000 entities, validate <100ms p95)
- [X] T017 [US1] Create pytest benchmark runner script in scripts/run_benchmarks.sh (executes all benchmarks and saves results to performance_baselines/)
- [X] T018 [US1] Collect pre-split baseline measurements and save to docs/performance/baseline-pre-split.json (if missing)
- [ ] T019 [US1] Run all benchmarks and generate post-split baseline in docs/performance/baseline-post-split.json
- [ ] T020 [US1] Execute baseline comparison script and validate performance variance within 10% (SC-005 validation)

**Checkpoint**: Performance baseline validated - all constitutional targets met, variance within acceptable range

---

## Phase 4: User Story 2 - Cross-Server Integration Validation (Priority: P1)

**Goal**: Validate workflows spanning both servers work seamlessly with proper entity references and server isolation

**Independent Test**: Execute search → work item workflow, verify entity references persist, test server failure isolation

### Implementation for User Story 2

- [ ] T021 [P] [US2] Create cross-server workflow integration test in tests/integration/test_cross_server_workflow.py::test_search_to_work_item_workflow (httpx async client, validate entity reference persistence per quickstart.md lines 141-176)
- [ ] T022 [P] [US2] Create server failure isolation test in tests/integration/test_resilience.py::test_workflow_continues_when_codebase_down (mock codebase-mcp unavailable, validate workflow continues per quickstart.md lines 196-210)
- [ ] T023 [P] [US2] Create reverse isolation test in tests/integration/test_resilience.py::test_codebase_continues_when_workflow_down (mock workflow-mcp unavailable, validate search continues per quickstart.md lines 215-227)
- [ ] T024 [P] [US2] Create stale entity reference handling test in tests/integration/test_resilience.py::test_stale_entity_reference_handled_gracefully (delete entity after work item creation, validate graceful handling per quickstart.md lines 232-245)
- [ ] T025 [US2] Run all cross-server integration tests and validate 100% pass rate (SC-011 validation)

**Checkpoint**: Cross-server integration validated - workflows work seamlessly, servers fail independently, stale references handled

---

## Phase 5: User Story 3 - Load and Stress Testing (Priority: P2)

**Goal**: Verify servers handle 50 concurrent clients without failure, maintaining 99.9% uptime

**Independent Test**: Run k6 load tests simulating concurrent clients, measure latency degradation and error rates

### Implementation for User Story 3

- [ ] T026 [P] [US3] Create k6 load test scenario for codebase-mcp in tests/load/k6_codebase_load.js (ramp to 50 users, 10min sustained load, p95<2000ms threshold per quickstart.md lines 273-303)
- [ ] T027 [P] [US3] Create k6 load test scenario for workflow-mcp in tests/load/k6_workflow_load.js (ramp to 50 users, 10min sustained load, error rate <1%)
- [ ] T028 [P] [US3] Create load test orchestration script in scripts/run_load_tests.sh (executes both k6 scenarios, collects results)
- [ ] T029 [US3] Run codebase-mcp load test and save results to tests/load/results/codebase_load_results.json
- [ ] T030 [US3] Run workflow-mcp load test and save results to tests/load/results/workflow_load_results.json
- [ ] T031 [US3] Validate load test results against thresholds (50 concurrent clients, 99.9% uptime, error rate <1%, SC-006 and SC-007 validation)
- [ ] T032 [US3] Generate load testing capacity report in docs/performance/load-testing-report.md

**Checkpoint**: Load testing validated - servers handle 50 concurrent clients, maintain uptime, graceful degradation under extreme load

---

## Phase 6: User Story 4 - Error Recovery and Resilience (Priority: P2)

**Goal**: Verify automatic recovery from database failures within 10 seconds with zero data loss

**Independent Test**: Simulate database disconnection, measure detection time and reconnection behavior

### Implementation for User Story 4

- [ ] T033 [P] [US4] Create database reconnection test in tests/integration/test_resilience.py::test_database_reconnection_after_failure (pytest-mock with asyncpg exceptions, validate <5s detection per quickstart.md lines 346-386)
- [ ] T034 [P] [US4] Create connection pool exhaustion test in tests/integration/test_resilience.py::test_connection_pool_exhaustion_handling (simulate max pool usage, validate queuing and 503 responses per FR-016)
- [ ] T035 [P] [US4] Create port conflict detection test in tests/integration/test_resilience.py::test_port_conflict_error_handling (attempt to start server on used port, validate clear error message)
- [ ] T036 [US4] Run all resilience tests and validate automatic recovery behavior (SC-008 validation)
- [ ] T037 [US4] Validate structured logs contain failure detection and recovery events with correct timestamps
- [ ] T038 [US4] Generate resilience testing report in docs/operations/resilience-validation-report.md

**Checkpoint**: Resilience validated - automatic recovery from failures, no data loss, clear error messaging

---

## Phase 7: User Story 5 - Observability and Monitoring (Priority: P3)

**Goal**: Provide comprehensive health check and metrics endpoints for production monitoring

**Independent Test**: Query health and metrics endpoints, validate response structure and timing

### Implementation for User Story 5

- [ ] T039 [P] [US5] Implement health check endpoint in src/mcp/server_fastmcp.py (FastMCP resource registration `@mcp.resource("health://status")`, returns HealthCheckResponse per contracts/health-endpoint.yaml)
- [ ] T040 [P] [US5] Implement metrics endpoint in src/mcp/server_fastmcp.py (FastMCP resource registration `@mcp.resource("metrics://prometheus")`, returns MetricsResponse with both JSON and Prometheus text format per contracts/metrics-endpoint.yaml)
- [ ] T041 [P] [US5] Create health check service in src/services/health_service.py (database connectivity check, connection pool stats, uptime calculation, <50ms response time requirement)
- [ ] T042 [P] [US5] Create metrics collection service in src/services/metrics_service.py (in-memory metrics storage, counter and histogram support, Prometheus format export)
- [ ] T043 [P] [US5] Create health check response time test in tests/integration/test_observability.py::test_health_check_response_time (validate <50ms per quickstart.md lines 413-430)
- [ ] T044 [P] [US5] Create health check schema validation test in tests/integration/test_observability.py::test_health_check_response_schema (validate OpenAPI contract compliance)
- [ ] T045 [P] [US5] Create metrics endpoint format test in tests/integration/test_observability.py::test_metrics_prometheus_format (validate both JSON and text formats per quickstart.md lines 435-468)
- [ ] T046 [P] [US5] Create structured logging validation test in tests/integration/test_observability.py::test_structured_logging_format (validate JSON format with required fields per quickstart.md lines 473-489)
- [ ] T047 [US5] Run all observability tests and validate 100% pass rate (SC-010 validation)
- [ ] T048 [US5] Create health monitoring operations guide in docs/operations/health-monitoring.md (health check usage, interpretation, alerting thresholds)
- [ ] T049 [US5] Create Prometheus integration guide in docs/operations/prometheus-integration.md (scraping configuration, alert rules, dashboard recommendations)

**Checkpoint**: Observability validated - health checks respond in <50ms, metrics expose comprehensive data, logs are structured

---

## Phase 8: Polish & Validation

**Purpose**: Cross-story validation, documentation, and completion

- [ ] T050 [P] Run complete test suite and validate 100% pass rate (pytest tests/ -v -m "integration or performance or contract")
- [ ] T051 [P] Generate test coverage report and validate >95% coverage for new code (pytest --cov=src --cov-report=html)
- [ ] T052 [US1] Generate performance comparison report in docs/performance/validation-report.md (baseline comparison, latency histograms, percentile tables)
- [ ] T053 [P] Create performance tuning operations guide in docs/operations/performance-tuning.md (connection pool sizing, index optimization, caching strategies)
- [ ] T054 [P] Create incident response runbook in docs/operations/incident-response.md (failure scenarios, resolution steps, escalation paths)
- [ ] T055 Run quickstart.md validation scenarios end-to-end (all 6 scenarios per quickstart.md lines 40-589)
- [ ] T056 Update CLAUDE.md with Phase 06 completion status and validation results
- [ ] T057 Create Phase 06 completion summary document in specs/011-performance-validation-multi/completion-summary.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - create test infrastructure
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories (models required)
- **User Story 1 (Phase 3)**: Depends on Foundational - Performance baseline validation (P1 - MVP)
- **User Story 2 (Phase 4)**: Depends on Foundational - Cross-server integration (P1)
- **User Story 3 (Phase 5)**: Depends on US1, US2 - Load testing requires working system (P2)
- **User Story 4 (Phase 6)**: Depends on US1, US2 - Resilience testing requires working system (P2)
- **User Story 5 (Phase 7)**: Depends on Foundational - Observability endpoints can be developed independently (P3)
- **Polish (Phase 8)**: Depends on all desired user stories - Final validation and documentation

### User Story Dependencies

- **US1 (P1 - Performance)**: Can start after Foundational - No dependencies on other stories
- **US2 (P1 - Integration)**: Can start after Foundational - No dependencies on other stories
- **US3 (P2 - Load Testing)**: Should run after US1 and US2 to test a working system
- **US4 (P2 - Resilience)**: Should run after US1 and US2 to test a working system
- **US5 (P3 - Observability)**: Can start after Foundational in parallel with US1/US2, but requires endpoint implementation

### Within Each User Story

- Models (Phase 2) before tests
- Test fixtures before benchmark/integration tests
- Benchmarks/tests before validation
- Implementation (US5 only) before tests
- Story complete before moving to next priority

### Parallel Opportunities

**Phase 1 (Setup)**: Tasks T002-T005 can run in parallel (different directories)

**Phase 2 (Foundational)**: Tasks T006-T010 can run in parallel (different model files)

**Phase 3 (US1)**: Tasks T013-T016 can run in parallel (different benchmark files)

**Phase 4 (US2)**: Tasks T021-T024 can run in parallel (different test scenarios in same file with pytest-xdist)

**Phase 5 (US3)**: Tasks T026-T028 can run in parallel (different k6 scripts and orchestration)

**Phase 6 (US4)**: Tasks T033-T035 can run in parallel (different test scenarios)

**Phase 7 (US5)**:
- Tasks T039-T042 can run in parallel (different service files)
- Tasks T043-T046 can run in parallel (different test scenarios)
- Tasks T048-T049 can run in parallel (different documentation files)

**Phase 8 (Polish)**: Tasks T050-T051, T053-T054 can run in parallel (independent validation and documentation)

---

## Parallel Example: User Story 1 (Performance Baseline)

```bash
# Launch all benchmark creation tasks together:
Task T013: "Create indexing performance benchmark in tests/benchmarks/test_indexing_perf.py"
Task T014: "Create search performance benchmark in tests/benchmarks/test_search_perf.py"
Task T015: "Create project switching benchmark in tests/benchmarks/test_workflow_perf.py"
Task T016: "Create entity query benchmark in tests/benchmarks/test_workflow_perf.py"

# Then run sequentially:
Task T017: "Create benchmark runner script" (uses output from T013-T016)
Task T018: "Collect pre-split baseline" (needs runner)
Task T019: "Run all benchmarks" (needs runner and baseline)
Task T020: "Execute baseline comparison" (needs both baselines)
```

---

## Implementation Strategy

### MVP First (User Stories 1 and 2 Only - Both P1)

1. Complete Phase 1: Setup (test infrastructure)
2. Complete Phase 2: Foundational (all Pydantic models - CRITICAL)
3. Complete Phase 3: User Story 1 (performance baseline validation)
4. Complete Phase 4: User Story 2 (cross-server integration validation)
5. **STOP and VALIDATE**: Both P1 stories complete - system proven to meet performance targets and work cross-server
6. Decision point: Deploy to production OR continue with P2 stories

### Incremental Delivery

1. Setup + Foundational → Models ready, test infrastructure complete
2. Add US1 (Performance) → Validate constitutional targets met → **Go/No-Go for production**
3. Add US2 (Integration) → Validate cross-server workflows → **Confidence for production deployment**
4. Add US3 (Load Testing) → Understand capacity limits → Capacity planning data
5. Add US4 (Resilience) → Validate failure recovery → Production confidence boost
6. Add US5 (Observability) → Enable monitoring → Operational excellence

### Parallel Team Strategy

With multiple developers after Foundational phase:

1. **Developer A**: User Story 1 (Performance benchmarks)
2. **Developer B**: User Story 2 (Integration tests)
3. **Developer C**: User Story 5 (Observability endpoints - can start early)

Then sequentially:
4. **Team**: User Story 3 (Load testing - requires working system)
5. **Team**: User Story 4 (Resilience - requires working system)

---

## Success Criteria Validation

**After completing all tasks, validate these success criteria from spec.md:**

- [ ] SC-001: Codebase-mcp indexes 10k files in <60s (p95) with <5% variance (validated by T013, T019, T020)
- [ ] SC-002: Search queries return in <500ms (p95) with 10 concurrent clients (validated by T014, T019, T020)
- [ ] SC-003: Project switching completes in <50ms (p95) (validated by T015, T019, T020)
- [ ] SC-004: Entity queries complete in <100ms (p95) (validated by T016, T019, T020)
- [ ] SC-005: All metrics within 10% of baseline (validated by T020)
- [ ] SC-006: 50 concurrent clients handled without crash (validated by T026-T031)
- [ ] SC-007: 99.9% uptime during extended load testing (validated by T029-T031)
- [ ] SC-008: Automatic recovery from DB disconnections within 10s (validated by T033, T036)
- [ ] SC-009: Server failures remain isolated (validated by T022-T023)
- [ ] SC-010: Health checks respond within 50ms (validated by T043, T047)
- [ ] SC-011: Integration test suite 100% pass rate (validated by T025)
- [ ] SC-012: Performance regression detection in CI/CD (validated by T011, T012, T020)
- [ ] SC-013: Performance reports generated (validated by T052)
- [ ] SC-014: Error messages guide users to resolution (validated by T035, T037)

---

## Notes

- **[P] tasks**: Different files, can execute in parallel
- **[Story] label**: Maps task to specific user story for traceability
- **This is a testing feature**: Tests ARE the implementation
- **No new features**: Only validation of existing functionality from Phases 01-05
- **Constitutional compliance**: All tests validate Principle IV (Performance Guarantees)
- **TDD approach**: Models and fixtures first, then tests
- **Commit strategy**: Micro-commit after each task or logical test suite
- **Checkpoint validation**: Stop after each user story to validate independently
- **Documentation**: Operational runbooks for production deployment readiness
