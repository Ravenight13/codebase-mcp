# AI Agent Guide: Generating spec.md for Phase 06 - Performance Validation & Testing

## Your Mission

Transform this phase-specific validation requirement into a clear, complete feature specification that follows SpecKit principles while capturing the critical validation work needed to ensure the split MCP servers meet all performance targets.

## Pre-Flight Checks (MANDATORY)

Before you begin writing the spec, verify these conditions:

1. **Constitution Familiarity**: Review `.specify/memory/constitution.md` to understand project principles
2. **Template Structure**: Load `.specify/templates/spec-template.md` for the canonical structure
3. **Phase Context**: Read `docs/mcp-split-plan/phases/phase-06-performance/analysis.md` to understand validation requirements
4. **Dependency Awareness**: Confirm Phases 01-05 are complete (workflow-mcp functional, both servers integrated)
5. **Original Split Context**: Review `specs/008-mcp-server-split/spec.md` for the parent feature requirements

If any check fails, STOP and request clarification before proceeding.

## Phase-Specific Context

### What This Phase Delivers

Phase 06 is the **validation and hardening phase** that ensures both `workflow-mcp` and `codebase-mcp` meet performance, reliability, and production-readiness requirements after the split. This phase focuses on:

1. **Performance Validation**: Verify both servers meet original performance targets (indexing <60s, search <500ms p95)
2. **Integration Testing**: Comprehensive client-side integration tests with both servers running simultaneously
3. **Load & Stress Testing**: Validate behavior under high concurrent load (50+ clients)
4. **Observability Enhancement**: Metrics, logging, and debugging capabilities for both servers
5. **Production Readiness**: Connection pooling, error recovery, edge case handling, documentation

### Split Architecture Recap

This phase validates the architecture created in Phases 01-05:

```
┌─────────────────────────────────────────────────────────────────┐
│                        MCP Client (Claude Code)                  │
│                     Uses BOTH servers simultaneously             │
└────────────────┬────────────────────────────────┬────────────────┘
                 │                                │
        ┌────────▼─────────┐            ┌────────▼─────────┐
        │  workflow-mcp    │            │  codebase-mcp    │
        │  Port: 8010      │            │  Port: 8020      │
        │  SSE Transport   │            │  SSE Transport   │
        └────────┬─────────┘            └────────┬─────────┘
                 │                                │
        ┌────────▼─────────┐            ┌────────▼─────────┐
        │ Registry DB      │            │ Indexed Code DB  │
        │ workflow_registry│            │ codebase_mcp     │
        │ + Per-project DB │            │ (single database)│
        └──────────────────┘            └──────────────────┘
```

### Critical Validation Areas

**Performance Targets** (from constitution):
- Indexing: <60 seconds for 10,000 files
- Search: <500ms p95 latency
- Project switching: <50ms
- Entity queries: <100ms

**Integration Scenarios**:
- Cross-server workflows (search code → create work item referencing found entity)
- Concurrent operations (index repository while querying work items)
- Multi-project isolation (workflow project switching doesn't affect codebase indexing)

**Production Readiness**:
- Connection pool behavior under load
- Error recovery (DB disconnect, port conflicts, resource exhaustion)
- Graceful degradation (one server fails, other continues)
- Client reconnection handling

## Anti-Patterns to Avoid

### ❌ Implementation Leakage
**DON'T**: "Add pytest fixtures in `tests/integration/test_split_performance.py`"
**DO**: "FR-003: Provide performance benchmarking that validates indexing completes in <60s for 10,000 files"

### ❌ Copy-Paste from analysis.md
**DON'T**: "Phase 06 focuses on validation (see analysis.md for details)"
**DO**: Rewrite in spec language focusing on user needs and success criteria

### ❌ Missing Alternative Paths
**DON'T**: User Scenario 1 with only happy path
**DO**: Include "What if performance targets aren't met?" and "What if servers fail under load?" alternatives

### ❌ Vague Functional Requirements
**DON'T**: "FR-001: Performance should be good"
**DO**: "FR-001: Validate codebase-mcp indexing performance meets <60s for 10,000 files with <5% variance across 5 runs"

### ❌ Ignoring Constitutional Principles
**DON'T**: Skip validation of Principle IV (Performance Guarantees)
**DO**: FR-001 through FR-010 explicitly map to constitutional performance targets

## The spec.md You Will Generate

Below is the COMPLETE structure with guidance for each section. Replace `[PLACEHOLDERS]` with phase-specific content.

---

# Feature Specification: [FEATURE_NAME]

**Feature ID**: `[FEATURE_NUM]`
**Status**: Draft
**Created**: [YYYY-MM-DD]
**Last Updated**: [YYYY-MM-DD]
**Parent Feature**: `specs/008-mcp-server-split/`
**Phase**: 06 - Performance Validation & Testing

---

## Feature Metadata

| Field | Value |
|-------|-------|
| **Feature Name** | [FEATURE_NAME] |
| **Feature ID** | [FEATURE_NUM] |
| **Complexity** | [Low/Medium/High] |
| **Priority** | [Critical/High/Medium/Low] |
| **Estimated Effort** | [Hours/Days] |
| **Phase** | 06 - Performance Validation & Testing |
| **Dependencies** | Phase 05 (Both servers integrated and functional) |
| **Stakeholders** | Development team, End users (Claude Code, Cursor IDE users) |

**Complexity Guidance**:
- **Low**: Validation of existing functionality (e.g., running existing performance tests)
- **Medium**: New integration test suites, load testing infrastructure
- **High**: Significant observability enhancements, complex error recovery scenarios

---

## Original User Description

> "Phase 06 focuses on validating that the split MCP servers (`workflow-mcp` and `codebase-mcp`) meet all performance targets, handle concurrent load, recover from errors gracefully, and are production-ready. This phase ensures the architecture delivers on its promises of <60s indexing, <500ms search latency, and robust operation under real-world conditions."

### User Intent (Inferred)

**What the user really needs**:
1. **Confidence**: Proof that the split didn't degrade performance or introduce new failure modes
2. **Production Readiness**: Both servers can handle real-world load (50+ concurrent clients, large repositories)
3. **Observability**: Ability to debug issues when they occur (metrics, logs, health checks)
4. **Reliability**: Graceful error recovery, no cascading failures between servers

**Why this matters**:
- **Risk Mitigation**: Catch performance regressions before production deployment
- **User Experience**: Ensure Claude Code and Cursor IDE users see fast, reliable responses
- **Maintainability**: Observability tools reduce time-to-resolution for production incidents

---

## User Scenarios & Testing

### Scenario 1: Performance Engineer Validates Split Architecture

**Primary Path**:
1. Engineer runs performance benchmark suite against both servers
2. Codebase-mcp indexes 10,000-file repository in <60s (baseline: 45s pre-split)
3. Workflow-mcp project switching completes in <50ms (baseline: 30ms pre-split)
4. Search queries return in <500ms p95 (baseline: 250ms p95 pre-split)
5. Engineer generates performance report comparing pre-split vs post-split metrics
6. ✅ All targets met, split approved for production

**Alternative Path 1: Performance Regression Detected**:
- Step 3 fails: Project switching now takes 150ms (3x slower)
- System identifies bottleneck: Database connection pool exhaustion
- Engineer adjusts pool settings, re-runs benchmark
- Performance restored to <50ms
- 🔧 Configuration tuning required before production

**Alternative Path 2: Load Test Failure**:
- Step 4 fails under 50 concurrent clients: Search latency spikes to 2000ms p95
- System logs show connection pool starvation
- Engineer implements connection queuing with backpressure
- Re-test shows graceful degradation: 600ms p95 (acceptable under extreme load)
- ✅ Acceptable with documentation of limits

**Success Criteria**:
- Performance targets met within 10% variance of pre-split baselines
- Regressions identified with clear root cause analysis
- Tuning recommendations documented for production deployment

---

### Scenario 2: DevOps Engineer Tests Error Recovery

**Primary Path**:
1. Engineer simulates PostgreSQL disconnect during active indexing
2. Codebase-mcp detects connection loss, logs error, pauses indexing
3. DB reconnects after 5 seconds (simulated network partition)
4. Codebase-mcp resumes indexing from last checkpoint
5. Workflow-mcp continues operating (unaffected by codebase-mcp DB issue)
6. ✅ Graceful recovery, no data loss, services isolated

**Alternative Path 1: Cascading Failure**:
- Step 5 fails: Workflow-mcp also reports errors (unexpected)
- Investigation reveals shared connection pool misconfiguration
- Engineer fixes isolation between server DB connections
- Re-test confirms servers operate independently
- 🔧 Architecture flaw fixed

**Alternative Path 2: Partial Recovery**:
- Step 4 fails: Indexing resumes but duplicates chunks (idempotency bug)
- System detects duplicate embeddings in database
- Engineer adds deduplication logic to recovery path
- Re-test confirms clean recovery without duplicates
- 🔧 Recovery logic hardened

**Success Criteria**:
- Both servers recover from transient DB failures within 10 seconds
- No cascading failures between workflow-mcp and codebase-mcp
- Data integrity maintained (no duplicates, no data loss)

---

### Scenario 3: End User (Claude Code) Performs Cross-Server Workflow

**Primary Path**:
1. User runs `/search_code` to find authentication logic
2. Claude Code sends request to codebase-mcp, receives 10 code chunks
3. User identifies entity (AuthService class) and runs workflow command
4. Claude Code sends `create_work_item` to workflow-mcp with entity reference
5. Work item created with embedded code context from codebase-mcp results
6. User queries work items, sees inline code snippets from original search
7. ✅ Seamless cross-server integration, natural user experience

**Alternative Path 1: Codebase-MCP Unavailable**:
- Step 2 fails: codebase-mcp returns 503 Service Unavailable
- Claude Code shows error: "Code search unavailable, workflow commands still functional"
- User proceeds with workflow commands (create project, work items)
- Codebase-mcp restarts, user retries search successfully
- ✅ Graceful degradation, clear error messaging

**Alternative Path 2: High-Latency Search**:
- Step 2 completes in 1500ms (exceeds 500ms p95 target)
- Claude Code shows progress indicator: "Searching large codebase..."
- Results eventually return, user proceeds with workflow
- System logs performance anomaly for investigation
- 🔧 Acceptable UX, flagged for optimization

**Alternative Path 3: Invalid Cross-Server Reference**:
- Step 4 fails: Work item references non-existent entity_id from codebase-mcp
- Workflow-mcp validates reference, returns error: "Entity not found in codebase index"
- Claude Code prompts user to re-run search or use different entity
- User corrects entity reference, work item created successfully
- ✅ Data integrity preserved, helpful error messages

**Success Criteria**:
- Cross-server workflows complete end-to-end without manual configuration
- Server failures don't block unrelated operations (isolation)
- Error messages guide users to resolution
- Performance meets targets under typical concurrent load (10 clients)

---

## Functional Requirements

### FR-001: Codebase-MCP Performance Validation
**Description**: Validate that codebase-mcp meets indexing and search performance targets after the split.

**Acceptance Criteria**:
- Indexing 10,000 files completes in <60 seconds (p95) across 5 benchmark runs
- Search queries return in <500ms (p95) under load of 10 concurrent clients
- Performance variance <10% compared to pre-split baseline measurements
- Benchmark suite generates report with latency histograms and p50/p95/p99 percentiles

**Constitutional Mapping**: Principle IV (Performance Guarantees - indexing <60s, search <500ms)

**Edge Cases**:
- Repository with 50,000 files (test scalability beyond target)
- Search queries against freshly indexed repository (cold cache)
- Concurrent indexing + search operations (resource contention)

---

### FR-002: Workflow-MCP Performance Validation
**Description**: Validate that workflow-mcp meets project switching and entity query performance targets.

**Acceptance Criteria**:
- Project switching completes in <50ms (p95) across 20 test switches
- Entity queries return in <100ms (p95) with 1000 entities in database
- Work item hierarchy queries (<10ms) unaffected by entity table size
- Performance report compares pre-split vs post-split metrics

**Constitutional Mapping**: Principle IV (Performance Guarantees - project switch <50ms, entity query <100ms)

**Edge Cases**:
- Project with 10,000 work items (stress test hierarchy queries)
- Entity query with complex JSONB filters (test GIN index performance)
- Rapid project switching (10 switches in 1 second)

---

### FR-003: Integration Test Suite for Dual-Server Workflows
**Description**: Provide comprehensive integration tests that validate both servers working together in realistic workflows.

**Acceptance Criteria**:
- Test suite covers 10+ cross-server scenarios (search code → create work item, index repo → query deployments, etc.)
- Tests run both servers in isolated environments (Docker or subprocess)
- Assertions validate end-to-end behavior (not just individual server responses)
- Tests detect common failure modes (port conflicts, DB connection issues, timeout errors)

**Constitutional Mapping**: Principle VII (Test-Driven Development - protocol compliance validation)

**Edge Cases**:
- Codebase-mcp unavailable during workflow operations (test isolation)
- Workflow-mcp unavailable during code search (test isolation)
- Both servers restart simultaneously (test client reconnection)

---

### FR-004: Load and Stress Testing
**Description**: Validate server behavior under high concurrent load and resource exhaustion scenarios.

**Acceptance Criteria**:
- Both servers handle 50 concurrent clients without crashing
- Search latency remains <1000ms (p95) under 50-client load (acceptable degradation)
- Connection pools configured to prevent resource exhaustion
- Load test report documents breaking points (max clients before failure)

**Constitutional Mapping**: Principle V (Production Quality - comprehensive error handling)

**Edge Cases**:
- 100 concurrent indexing requests (test queue/backpressure mechanisms)
- Rapid connect/disconnect cycles (test connection pool churn)
- Memory-intensive operations (large repository indexing + heavy queries)

---

### FR-005: Error Recovery and Resilience Testing
**Description**: Validate graceful error recovery for transient failures (DB disconnect, network partition, resource exhaustion).

**Acceptance Criteria**:
- Both servers detect and log DB connection failures within 5 seconds
- Servers retry failed operations with exponential backoff (max 3 retries)
- Operations in progress pause/resume without data loss
- Servers recover automatically when DB reconnects

**Constitutional Mapping**: Principle V (Production Quality - comprehensive error handling)

**Edge Cases**:
- DB disconnect during critical section (mid-transaction)
- Connection pool exhausted (all connections in use)
- Disk full during indexing (codebase-mcp specific)

---

### FR-006: Observability Enhancements
**Description**: Provide metrics, logging, and health checks for debugging and monitoring in production.

**Acceptance Criteria**:
- Health check endpoints (`/health`) return detailed status (DB connection, pool stats, uptime)
- Metrics endpoint (`/metrics`) exposes Prometheus-compatible metrics (request count, latency histograms, error rates)
- Structured logging (JSON format) includes request IDs, operation names, latency
- Logs include performance warnings (queries >1s, connection pool >80% utilization)

**Constitutional Mapping**: Principle V (Production Quality - comprehensive error handling), Principle III (Protocol Compliance - no stdout pollution)

**Edge Cases**:
- Metrics endpoint under high load (must not impact main operations)
- Log volume during error storm (rate limiting to prevent disk exhaustion)
- Health check when DB is down (should report degraded, not crash)

---

### FR-007: Connection Pool Optimization
**Description**: Optimize PostgreSQL connection pool settings for both servers to prevent resource exhaustion under load.

**Acceptance Criteria**:
- Workflow-mcp pool: min_size=2, max_size=10 (supports registry + active project DBs)
- Codebase-mcp pool: min_size=5, max_size=20 (handles concurrent search queries)
- Pool metrics exposed via `/health` endpoint (size, free connections, wait time)
- Documentation describes tuning guidelines for production deployment

**Constitutional Mapping**: Principle V (Production Quality - resource management)

**Edge Cases**:
- Pool exhaustion under 50 concurrent clients (test queue behavior)
- Long-running queries (indexing) holding connections (test timeout settings)
- Connection leak detection (max_overflow triggers alerts)

---

### FR-008: Client Reconnection Handling
**Description**: Validate that MCP clients (Claude Code, Cursor IDE) can reconnect to servers after transient failures.

**Acceptance Criteria**:
- Servers support SSE reconnection with `Last-Event-ID` header
- In-progress operations resume after reconnect (no duplicate work)
- Client libraries (Python SDK) handle reconnection automatically
- Integration tests simulate disconnect/reconnect scenarios

**Constitutional Mapping**: Principle III (Protocol Compliance - SSE transport)

**Edge Cases**:
- Reconnect during long-running operation (indexing 10,000 files)
- Multiple rapid reconnects (test exponential backoff)
- Server restart while client connected (clean shutdown with 503 response)

---

### FR-009: Performance Regression Detection
**Description**: Establish baseline performance metrics and automated tests to detect future regressions.

**Acceptance Criteria**:
- Benchmark suite runs in CI/CD pipeline on every commit
- CI fails if performance degrades >20% from baseline (configurable threshold)
- Performance report archived with each build (historical trend analysis)
- Documentation describes how to update baselines after intentional changes

**Constitutional Mapping**: Principle IV (Performance Guarantees - proactive regression prevention)

**Edge Cases**:
- Hardware variance in CI runners (normalize metrics to baseline hardware)
- Cold start vs warm cache (run benchmarks multiple times, report average)
- Database state dependency (reset DB to known state before each benchmark)

---

### FR-010: Production Readiness Documentation
**Description**: Provide comprehensive documentation for deploying, monitoring, and troubleshooting both servers in production.

**Acceptance Criteria**:
- Deployment guide covers Docker, systemd, and manual installation
- Monitoring guide describes key metrics to watch (latency, error rate, connection pool)
- Troubleshooting guide covers common issues (port conflicts, DB connection errors, performance degradation)
- Runbook includes emergency procedures (server restart, DB failover, log analysis)

**Constitutional Mapping**: Principle V (Production Quality - operational excellence)

**Edge Cases**:
- Multi-instance deployment (load balancing, shared DB)
- Blue-green deployment (zero-downtime upgrades)
- Disaster recovery (backup/restore procedures)

---

## Success Criteria

### Quantitative Metrics
1. **Performance Targets Met**:
   - Codebase-mcp indexing: <60s for 10,000 files (p95)
   - Codebase-mcp search: <500ms (p95) under 10-client load
   - Workflow-mcp project switch: <50ms (p95)
   - Workflow-mcp entity query: <100ms (p95)

2. **Load Capacity**:
   - Both servers handle 50 concurrent clients without crashing
   - Graceful degradation under load (latency <1000ms p95 at 50 clients)

3. **Reliability**:
   - 99.9% uptime during 24-hour stress test
   - Automatic recovery from transient DB failures within 10 seconds
   - Zero data loss or corruption during error scenarios

4. **Observability**:
   - 100% of operations logged with latency and outcome
   - Health checks respond <50ms
   - Metrics endpoint captures all key performance indicators

### Qualitative Criteria
- Integration tests cover realistic cross-server workflows
- Error messages guide users/operators to resolution
- Documentation enables new team members to deploy and monitor servers
- Performance regression tests run automatically in CI/CD

### Constitutional Compliance
- ✅ Principle IV: Performance targets validated with <10% variance
- ✅ Principle V: Error recovery and observability validated
- ✅ Principle VII: Comprehensive integration test suite
- ✅ Principle III: Protocol compliance (SSE, no stdout pollution) verified

---

## Key Entities

### Performance Benchmark Result
**Description**: Record of a single performance benchmark run for regression detection.

**Attributes**:
- `benchmark_id` (UUID): Unique identifier
- `server` (enum): `codebase-mcp` | `workflow-mcp`
- `operation` (string): `index_repository` | `search_code` | `switch_project` | `query_entities`
- `run_timestamp` (datetime): When benchmark executed
- `latency_p50` (float): 50th percentile latency in milliseconds
- `latency_p95` (float): 95th percentile latency in milliseconds
- `latency_p99` (float): 99th percentile latency in milliseconds
- `sample_size` (int): Number of operations measured
- `test_parameters` (JSON): Configuration (file count, client count, etc.)
- `passed` (boolean): Whether benchmark met target thresholds

**Relationships**:
- Belongs to test suite run (batch of benchmarks)
- References baseline benchmark for comparison

**Validation Rules**:
- `latency_p95` must be >= `latency_p50`
- `latency_p99` must be >= `latency_p95`
- `sample_size` must be >= 10 for statistical validity

---

### Integration Test Case
**Description**: Definition of a cross-server workflow test scenario.

**Attributes**:
- `test_id` (UUID): Unique identifier
- `test_name` (string): Descriptive name (e.g., "Search code → Create work item")
- `description` (string): Detailed scenario explanation
- `servers_required` (list): `['codebase-mcp', 'workflow-mcp']`
- `setup_steps` (JSON): Pre-test configuration (start servers, load test data)
- `test_steps` (JSON): Sequence of API calls with expected responses
- `assertions` (JSON): Validation checks (status codes, response schemas, latency)
- `teardown_steps` (JSON): Cleanup actions
- `last_run_status` (enum): `passed` | `failed` | `skipped`
- `last_run_timestamp` (datetime): Most recent execution

**Relationships**:
- Part of integration test suite
- May depend on other tests (setup order)

**Validation Rules**:
- `servers_required` must not be empty
- `test_steps` must have at least 1 step
- `assertions` must validate both success and error cases

---

### Load Test Result
**Description**: Record of a load/stress test execution.

**Attributes**:
- `load_test_id` (UUID): Unique identifier
- `server` (enum): `codebase-mcp` | `workflow-mcp`
- `concurrent_clients` (int): Number of simulated clients
- `test_duration_seconds` (int): How long test ran
- `total_requests` (int): Total operations attempted
- `successful_requests` (int): Requests that completed successfully
- `failed_requests` (int): Requests that errored or timed out
- `avg_latency_ms` (float): Mean latency across all requests
- `p95_latency_ms` (float): 95th percentile latency
- `max_latency_ms` (float): Worst-case latency observed
- `errors` (JSON): Breakdown of error types and counts
- `resource_usage` (JSON): CPU, memory, connection pool stats

**Relationships**:
- References load test configuration
- May trigger performance regression alerts

**Validation Rules**:
- `successful_requests` + `failed_requests` must equal `total_requests`
- `p95_latency_ms` must be <= `max_latency_ms`
- `concurrent_clients` must be > 0

---

## Edge Cases & Error Handling

### Edge Case 1: Port Conflict on Startup
**Scenario**: Codebase-mcp attempts to start on port 8020, but port is already in use.

**Expected Behavior**:
- Server logs error: "Port 8020 already in use, cannot start"
- Server exits with non-zero status code
- Health check script detects startup failure

**Error Message**: `ERROR: Address already in use (port 8020). Stop conflicting process or configure alternative port via CODEBASE_MCP_PORT environment variable.`

**Recovery**: User stops conflicting process or changes port configuration.

---

### Edge Case 2: Database Schema Version Mismatch
**Scenario**: Workflow-mcp starts with Alembic migration version 003, but DB is at version 002.

**Expected Behavior**:
- Server detects schema version mismatch during startup health check
- Server logs error with current version (002) and expected version (003)
- Server exits gracefully, prompting user to run migrations

**Error Message**: `ERROR: Database schema version mismatch. Current: 002, Expected: 003. Run 'alembic upgrade head' before starting server.`

**Recovery**: User runs Alembic migration, restarts server.

---

### Edge Case 3: Connection Pool Exhaustion Under Load
**Scenario**: 50 concurrent clients query workflow-mcp, exhausting connection pool (max_size=10).

**Expected Behavior**:
- Requests 11-50 wait in queue (asyncpg pool behavior)
- If wait time exceeds timeout (30s), requests fail with 503 Service Unavailable
- Server logs warning: "Connection pool saturation (10/10 connections in use)"
- Health check endpoint reports degraded status

**Error Message** (client-side): `503 Service Unavailable: Connection pool exhausted. Retry after 5 seconds.`

**Recovery**: Server processes queued requests as connections free up. User retries failed requests.

---

### Edge Case 4: Large Repository Indexing Timeout
**Scenario**: Codebase-mcp attempts to index 50,000-file repository, exceeding 60s target.

**Expected Behavior**:
- Indexing continues beyond 60s (no hard timeout)
- Server logs performance warning: "Indexing exceeded target (60s): completed in 120s"
- Metrics endpoint records latency (120s) for regression detection
- Client receives success response once indexing completes

**Error Message** (log): `WARN: Indexing performance degraded. Target: 60s, Actual: 120s. Consider batch size tuning or hardware upgrade.`

**Recovery**: Acceptable for repositories exceeding design target. Document performance characteristics in runbook.

---

### Edge Case 5: Stale Cross-Server Reference
**Scenario**: Workflow-mcp work item references `entity_id=abc123` from codebase-mcp, but entity was deleted/re-indexed.

**Expected Behavior**:
- Workflow-mcp stores reference as opaque string (no foreign key constraint)
- When user queries work item with entity context, codebase-mcp returns empty result for `abc123`
- Client displays work item with placeholder: "Referenced entity not found (may have been re-indexed)"

**Error Message** (client-side): `WARN: Entity abc123 referenced in work item but not found in current codebase index. Entity may have been deleted or re-indexed.`

**Recovery**: User can update work item with new entity reference or ignore stale reference.

---

### Edge Case 6: Both Servers Restart Simultaneously
**Scenario**: Docker Compose restarts both codebase-mcp and workflow-mcp at the same time (e.g., after configuration change).

**Expected Behavior**:
- Clients (Claude Code) detect SSE connection loss for both servers
- Clients retry connections with exponential backoff (1s, 2s, 4s, max 30s)
- Servers start up, pass health checks, begin accepting connections
- Clients reconnect, resume operations seamlessly

**Error Message** (client-side): `Connection lost to workflow-mcp and codebase-mcp. Retrying... (attempt 2/5)`

**Recovery**: Automatic client reconnection once servers are healthy.

---

## Review & Acceptance Checklist

Use this checklist to verify the specification is complete before moving to `/plan`:

### Completeness
- [ ] All 10 Functional Requirements (FR-001 to FR-010) are clearly defined with acceptance criteria
- [ ] All 3 User Scenarios include primary path + 2 alternative paths each
- [ ] Edge Cases section covers 6+ realistic failure scenarios with recovery steps
- [ ] Key Entities section defines 3 critical data structures (Benchmark Result, Test Case, Load Test Result)

### Clarity
- [ ] User scenarios describe observable user actions (not implementation steps)
- [ ] Functional requirements use active voice ("Validate that...", "Provide...")
- [ ] Success criteria are measurable (quantitative targets: <60s, <500ms, 99.9% uptime)
- [ ] Technical jargon is explained (e.g., "p95 latency = 95th percentile response time")

### Constitutional Alignment
- [ ] Each FR maps to at least one constitutional principle (Principles III, IV, V, VII)
- [ ] Performance targets (FR-001, FR-002) align with Principle IV (Performance Guarantees)
- [ ] Error recovery (FR-005) aligns with Principle V (Production Quality)
- [ ] Integration testing (FR-003) aligns with Principle VII (Test-Driven Development)

### Completeness vs. Brevity
- [ ] Spec avoids implementation details (no pytest fixture names, no file paths)
- [ ] Spec focuses on "what" and "why", not "how"
- [ ] Spec is scannable (clear headings, tables, bullet points)
- [ ] Spec is complete enough for `/plan` to generate design without ambiguity

### Phase-Specific Validation
- [ ] Spec acknowledges dependencies on Phases 01-05 (both servers must be functional)
- [ ] Spec references parent feature `specs/008-mcp-server-split/spec.md` for context
- [ ] Spec addresses validation requirements from `docs/mcp-split-plan/phases/phase-06-performance/analysis.md`

---

## Clarifications

*This section will be populated during the `/clarify` phase if any ambiguities are identified.*

### Identified Ambiguities
1. **[NEEDS CLARIFICATION]**: What is the acceptable performance degradation under 50-client load? (Current: <1000ms p95, but original target is <500ms)
2. **[NEEDS CLARIFICATION]**: Should load tests run continuously (24-hour soak test) or in bounded intervals (1-hour stress test)?
3. **[NEEDS CLARIFICATION]**: How should the benchmark suite handle CI/CD hardware variance? (Normalize to baseline runner specs or allow variance?)

### Resolved Clarifications
*Populate this after running `/clarify` to document Q&A*

---

## Non-Goals

Explicitly out of scope for this phase:

1. **Production Deployment**: This phase validates readiness but does not deploy servers to production environments
2. **Multi-Instance Load Balancing**: Testing focuses on single-instance performance (load balancing is future work)
3. **Advanced Monitoring (Grafana, Prometheus)**: Basic metrics exposed, but full monitoring stack setup is post-Phase 06
4. **Client Library Updates**: MCP Python SDK integration is tested as-is (no SDK modifications in this phase)
5. **Performance Optimization Beyond Targets**: If targets are met, no further optimization work (diminishing returns)
6. **Cross-Platform Testing**: Testing on macOS/Linux (primary development platforms), Windows support deferred

---

## Additional Context

### Phase Dependencies
- **Phase 01-05 Complete**: Both `workflow-mcp` and `codebase-mcp` must be functional and integrated
- **Original Specification**: Reference `specs/008-mcp-server-split/spec.md` for parent feature requirements
- **Baseline Metrics**: Pre-split performance data from monolith server (for regression comparison)

### Related Work
- **Migration Testing**: Phase 02 validated data migration; this phase validates performance post-migration
- **Integration Layer**: Phase 05 client integration informs the cross-server test scenarios in FR-003

### Future Enhancements (Post-Phase 06)
1. **Advanced Monitoring**: Integrate Prometheus + Grafana for real-time dashboards
2. **Multi-Region Deployment**: Test latency and failover for geographically distributed servers
3. **Chaos Engineering**: Introduce random failures (network partitions, process kills) to validate resilience
4. **Automated Performance Tuning**: ML-based connection pool sizing based on workload patterns

### References
- Constitutional Principles: `.specify/memory/constitution.md`
- Phase 06 Analysis: `docs/mcp-split-plan/phases/phase-06-performance/analysis.md`
- Original Split Spec: `specs/008-mcp-server-split/spec.md`
- Performance Testing Guide: `docs/operations/PERFORMANCE_TESTING.md` (to be created in Phase 06)

---

## Final Directive to AI Agent

You have now generated a **complete, SpecKit-compliant feature specification** for Phase 06 - Performance Validation & Testing.

**Next Steps**:
1. **Save this spec** as `specs/[FEATURE_NUM]-phase-06-performance-validation/spec.md`
2. **Run `/clarify`** to resolve the 3 identified ambiguities in the Clarifications section
3. **After clarifications**, run `/plan` to generate the implementation plan (research.md, data-model.md, contracts/, quickstart.md)

**Key Reminders**:
- This spec describes **what** to validate and **why** it matters (no implementation details)
- User scenarios show **observable behaviors** from user/operator perspective
- Functional requirements map to **constitutional principles** (Principles III, IV, V, VII)
- Success criteria are **measurable** (latency targets, uptime percentages, test coverage)

**Quality Gates Before `/plan`**:
- [ ] All 10 FRs have clear acceptance criteria
- [ ] All 3 user scenarios have 2+ alternative paths
- [ ] Edge cases cover realistic failure modes with recovery steps
- [ ] Success criteria include quantitative targets (<60s, <500ms, 99.9%)

If any section is unclear or incomplete, **flag it in the Clarifications section** with `[NEEDS CLARIFICATION: specific question]` before proceeding to `/plan`.

---

**END OF ENHANCED PROMPT**
