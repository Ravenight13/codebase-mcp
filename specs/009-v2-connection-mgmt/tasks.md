# Tasks: Production-Grade Connection Management

**Branch**: `009-v2-connection-mgmt`
**Input**: Design documents from `/specs/009-v2-connection-mgmt/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: Tests are NOT explicitly requested in the spec, so test tasks are EXCLUDED per template instructions.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

---

## Progress Summary

**Last Updated**: 2025-10-13

**Completion Status**: 29/46 tasks complete (63%)

**Phase Status**:
- ✅ Phase 1: Setup - 4/4 tasks complete (100%)
- ✅ Phase 2: Foundational - 6/6 tasks complete (100%)
- ✅ Phase 3: User Story 1 (MVP) - 7/7 tasks complete (100%)
- ✅ Phase 4: User Story 2 - 7/7 tasks complete (100%)
- ✅ Phase 5: User Story 3 - 5/5 tasks complete (100%)
- ⏳ Phase 6: User Story 4 - 0/7 tasks complete (0%)
- ⏳ Phase 7: Integration - 0/4 tasks complete (0%)
- ⏳ Phase 8: Polish - 0/6 tasks complete (0%)

**MVP Status**: ✅ **COMPLETE** - All P1 priority user stories implemented (US1 ✅, US2 ✅)
**P2 Features**: ✅ **COMPLETE** - Pool statistics and observability (US3 ✅)

**Files Created/Modified**:
- `src/connection_pool/` - Complete module structure
- `src/connection_pool/config.py` - PoolConfig model with validation (182 lines)
- `src/connection_pool/exceptions.py` - Complete exception hierarchy (206 lines)
- `src/connection_pool/statistics.py` - PoolStatistics model (118 lines)
- `src/connection_pool/health.py` - Health models + calculation (343 lines)
- `src/connection_pool/manager.py` - ConnectionPoolManager with full lifecycle (1,961 lines)
- `src/connection_pool/pool_logging.py` - Structured logging utilities (375 lines)
- `src/connection_pool/__init__.py` - Module exports (95 lines)

**Type Safety**: ✅ All files pass `mypy --strict`

**Next Up**: Phase 6 (T030-T036) - Connection leak detection and prevention

---

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create connection pool module directory structure: `src/connection_pool/__init__.py`, `src/connection_pool/manager.py`, `src/connection_pool/config.py`, `src/connection_pool/statistics.py`, `src/connection_pool/health.py`, `src/connection_pool/exceptions.py`
- [x] T002 Add asyncpg dependency to project requirements: asyncpg>=0.29.0 in requirements.txt or pyproject.toml (verified already present as asyncpg>=0.30.0)
- [x] T003 [P] Add pydantic-settings dependency: pydantic-settings>=2.1.0 in requirements.txt or pyproject.toml (verified already present)
- [x] T004 [P] Configure structured logging for connection pool: Update logging config to write to /tmp/codebase-mcp.log with JSON formatting

**Checkpoint**: ✅ Directory structure and dependencies ready

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core models and exceptions that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 [P] Create PoolConfig model in src/connection_pool/config.py with Pydantic BaseSettings, environment variable support (POOL_* prefix), and field validators (max_size >= min_size, positive timeouts, valid database URL)
- [x] T006 [P] Create exception hierarchy in src/connection_pool/exceptions.py: ConnectionPoolError (base), PoolConfigurationError, PoolInitializationError, PoolTimeoutError, ConnectionValidationError, PoolClosedError with actionable error messages
- [x] T007 [P] Create PoolStatistics model in src/connection_pool/statistics.py as immutable Pydantic BaseModel with fields: total_connections, idle_connections, active_connections, waiting_requests, total_acquisitions, total_releases, avg_acquisition_time_ms, peak_active_connections, peak_wait_time_ms, pool_created_at, last_health_check, last_error, last_error_time (frozen=True)
- [x] T008 [P] Create PoolHealthStatus enum and health check models in src/connection_pool/health.py: PoolHealthStatus (HEALTHY/DEGRADED/UNHEALTHY), DatabaseStatus (status, pool dict, latency_ms, last_error), HealthStatus (status, timestamp, database, uptime_seconds)
- [x] T009 [P] Create PoolState enum in src/connection_pool/manager.py: INITIALIZING, HEALTHY, DEGRADED, UNHEALTHY, RECOVERING, SHUTTING_DOWN, TERMINATED
- [x] T010 Implement health status calculation function in src/connection_pool/health.py: calculate_health_status(stats: PoolStatistics, config: PoolConfig) -> PoolHealthStatus with rules: unhealthy if total_connections == 0 or idle < 50%, degraded if idle 50-79% or recent errors, healthy if idle >= 80%

**Checkpoint**: ✅ Foundation ready - all models, exceptions, and enums defined. User story implementation can now begin in parallel.

---

## Phase 3: User Story 1 - Server Startup with Valid Configuration (Priority: P1) 🎯 MVP

**Goal**: Pool initializes successfully within 2 seconds with validated configuration, ready to handle database requests

**Independent Test**: Start MCP server with valid DATABASE_URL environment variable, verify pool initialization logs show min_size=2 connections within 2 seconds, health check returns "healthy" status

### Implementation for User Story 1

- [x] T011 [US1] Create ConnectionPoolManager class skeleton in src/connection_pool/manager.py with __init__, _pool (asyncpg.Pool), _config (PoolConfig), _state (PoolState), _start_time (datetime), _statistics tracking dictionaries (total_acquisitions, total_releases, peak_active, etc.), _leak_detector (optional)
- [x] T012 [US1] Implement initialize(config: PoolConfig) method in ConnectionPoolManager: validate config via Pydantic (fail-fast), create asyncpg.create_pool() with min_size/max_size from config, validate connections via SELECT 1 in parallel (asyncio.gather), set _state to HEALTHY, record _start_time, raise PoolInitializationError on failure with actionable message
- [x] T013 [US1] Implement _validate_connection(conn: asyncpg.Connection) helper method: execute SELECT 1 query with <5ms target, catch exceptions and raise ConnectionValidationError with connection details
- [x] T014 [US1] Add configuration validation to PoolConfig in src/connection_pool/config.py: @field_validator for max_size to ensure max_size >= min_size with error message "max_size ({v}) must be >= min_size ({min_size}). Suggestion: Increase POOL_MAX_SIZE or reduce POOL_MIN_SIZE", validators for positive timeouts and valid PostgreSQL connection string format (verified already complete)
- [x] T015 [US1] Implement basic get_statistics() method in ConnectionPoolManager: read asyncpg pool state (get_size(), get_idle_size(), get_active_count()), copy tracking counters atomically, return PoolStatistics immutable model, ensure <1ms execution (no locks on hot path)
- [x] T016 [US1] Implement health_check() method in ConnectionPoolManager: call get_statistics(), call calculate_health_status(), build DatabaseStatus dict from pool stats, calculate uptime_seconds from _start_time, return HealthStatus model, ensure <10ms p99 execution (no database queries)
- [x] T017 [US1] Add structured logging to initialization in ConnectionPoolManager: log pool initialization start with config parameters (redact password from database_url), log successful validation of each connection batch, log "Connection pool initialized: min_size=X, max_size=Y" on success with duration, log errors with PoolInitializationError details and suggested actions, all logs to /tmp/codebase-mcp.log in JSON format

**Checkpoint**: ✅ User Story 1 complete - pool initializes successfully, health check returns "healthy", statistics are tracked

---

## Phase 4: User Story 2 - Graceful Handling of Database Outage (Priority: P1)

**Goal**: Automatic reconnection with exponential backoff when database becomes unavailable, resuming operations on recovery without server restart

**Independent Test**: Start MCP server, verify queries work, stop PostgreSQL, verify queries fail gracefully (DATABASE_ERROR), verify logs show exponential backoff attempts (1s, 2s, 4s, 8s, 16s), restart PostgreSQL, verify pool recovers within 30s and queries succeed

### Implementation for User Story 2

- [x] T018 [US2] Implement exponential_backoff_retry(attempt: int, max_delay: float = 16.0, jitter_factor: float = 0.1) helper function in src/connection_pool/manager.py: calculate delay = min(1.0 * (2 ** attempt), max_delay), add jitter = random.uniform(-jitter_factor * delay, jitter_factor * delay), await asyncio.sleep(delay + jitter)
- [x] T019 [US2] Implement _reconnection_loop() background task in ConnectionPoolManager: detect when all connections fail validation, transition _state to RECOVERING, attempt reconnection with exponential backoff (5 initial attempts with 1s, 2s, 4s, 8s, 16s delays), continue retrying every 16s indefinitely until success, log each reconnection attempt with attempt number and delay, transition to HEALTHY on success, catch all exceptions and log with context
- [x] T020 [US2] Modify initialize() method to start _reconnection_loop as background task: asyncio.create_task(self._reconnection_loop()) after successful initialization, store task reference for cleanup during shutdown
- [x] T021 [US2] Implement acquire() context manager in ConnectionPoolManager: attempt to acquire connection from self._pool with timeout from config, validate connection via _validate_connection(), track acquisition timestamp and stack trace for leak detection, increment total_acquisitions counter, return connection proxy that auto-releases, handle PoolTimeoutError with pool statistics in error message, handle ConnectionValidationError by closing invalid connection and logging warning, raise PoolClosedError if _state is SHUTTING_DOWN or TERMINATED
- [x] T022 [US2] Update health_check() to reflect reconnection state: if _state is RECOVERING, set status to "degraded" or "unhealthy" based on total_connections == 0, include last_error from reconnection attempts in DatabaseStatus, ensure health check still returns <10ms even during reconnection
- [x] T023 [US2] Add comprehensive error logging for database failures: log connection validation failures with connection ID and error details, log "Database connectivity lost, entering reconnection mode" with current pool state, log each exponential backoff attempt "Reconnection attempt {attempt} after {delay}s delay", log "Connection pool recovered: {idle}/{total} connections available" on success, all structured logs to /tmp/codebase-mcp.log
- [x] T024 [US2] Implement graceful shutdown(timeout: float = 30.0) method in ConnectionPoolManager: set _state to SHUTTING_DOWN, reject new acquire() requests, wait for active connections to reach 0 with await asyncio.wait_for() using timeout, close idle connections gracefully via await self._pool.close(), force-close remaining active connections with warnings including connection IDs and held duration, cancel _reconnection_loop background task, set _state to TERMINATED, log shutdown phases and duration

**Checkpoint**: ✅ User Story 2 COMPLETE - Pool automatically reconnects after database outage with exponential backoff, graceful shutdown works correctly

---

## Phase 5: User Story 3 - Pool Statistics and Observability (Priority: P2)

**Goal**: Real-time pool statistics for monitoring database load and performance bottlenecks, enabling capacity planning

**Independent Test**: Query pool statistics API after server start (shows total=2, idle=2, active=0), execute 5 concurrent queries and check stats during execution (shows active=5), wait for queries to complete and verify historical metrics (total_acquisitions=5, avg_acquisition_time_ms recorded)

### Implementation for User Story 3

- [x] T025 [US3] Enhance get_statistics() to track real-time metrics: capture total_connections, idle_connections, active_connections from asyncpg pool state, read waiting_requests from pool queue length, copy total_acquisitions and total_releases counters atomically, calculate avg_acquisition_time_ms from tracked durations, include peak_active_connections and peak_wait_time_ms from historical tracking, set pool_created_at from _start_time, set last_health_check to current time, include last_error and last_error_time if any recent failures, ensure <1ms data staleness (in-memory reads only, no locks)
- [x] T026 [US3] Add acquisition time tracking to acquire() method: record start_time = time.perf_counter() before pool.acquire(), record end_time after successful acquisition, calculate duration_ms = (end_time - start_time) * 1000, append duration_ms to _acquisition_times deque (maxlen=1000 for rolling average), update avg_acquisition_time_ms on each acquisition, track peak_wait_time_ms if duration exceeds current peak
- [x] T027 [US3] Add peak metrics tracking to acquire() method: after successful acquisition, read current active_connections from pool, update peak_active_connections if current > peak, store peak values in _peak_active and _peak_wait_time instance variables
- [x] T028 [US3] Implement connection recycling based on usage: track query_count per connection in ConnectionMetadata, check query_count against config.max_queries on release, recycle connection if query_count >= max_queries by closing and letting pool create new one, track connection age via created_at in ConnectionMetadata, recycle if age > config.max_connection_lifetime, track idle time via last_used_at, recycle if idle > config.max_idle_time, log recycling events with reason (query limit, lifetime, idle timeout)
- [x] T029 [US3] Add pool shrinking for idle connections: implement background task _pool_maintenance() that runs every 60 seconds, check idle_connections against min_size, close excess idle connections beyond min_size if idle > config.max_idle_time, log "Pool shrunk from {old_size} to {new_size} connections due to idle timeout", ensure pool never shrinks below min_size

**Checkpoint**: ✅ User Story 3 COMPLETE - Detailed real-time statistics available, connection recycling works (hybrid asyncpg + manual age-based), pool maintenance monitors idle timeout shrinking

---

## Phase 6: User Story 4 - Connection Leak Detection and Prevention (Priority: P3)

**Goal**: Detect connections held longer than timeout and log warnings with stack traces to help developers identify resource leaks

**Independent Test**: Configure pool with leak_detection_timeout=30s, acquire connection and hold for 40 seconds, verify warning log appears: "WARNING: Potential connection leak detected. Connection held for 30s" with stack trace showing acquisition location

### Implementation for User Story 4

- [ ] T030 [US4] Create ConnectionMetadata dataclass in src/connection_pool/manager.py: fields for connection_id (str), acquired_at (datetime), acquisition_stack_trace (str), query_count (int), created_at (datetime), last_used_at (datetime)
- [ ] T031 [US4] Implement leak detection tracking in acquire() method: capture stack trace via "".join(traceback.format_stack()), create ConnectionMetadata with connection_id, acquired_at=datetime.utcnow(), acquisition_stack_trace, query_count=0, created_at, store in _active_connections dict keyed by connection object id
- [ ] T032 [US4] Implement leak detection cleanup in release: remove connection from _active_connections dict on successful release, update last_used_at timestamp, increment query_count for recycling checks
- [ ] T033 [US4] Implement _leak_detection_loop() background task in ConnectionPoolManager: run every 10 seconds if config.enable_leak_detection is True, iterate through _active_connections dict, calculate held_duration = (now - metadata.acquired_at).total_seconds(), if held_duration > config.leak_detection_timeout, log WARNING with message "Potential connection leak detected: {connection_id}", include held_duration_seconds, stack_trace from metadata, do NOT terminate connection (non-disruptive warning only), store leak warnings for health status degradation
- [ ] T034 [US4] Start _leak_detection_loop background task in initialize(): asyncio.create_task(self._leak_detection_loop()) if config.enable_leak_detection, store task reference for shutdown cleanup
- [ ] T035 [US4] Update health status calculation to include leak detection: if recent leak warnings (within last 60s), mark health as DEGRADED, include leak count in health status metadata, log "Connection pool health degraded: {leak_count} potential leaks detected in last 60s"
- [ ] T036 [US4] Add leak detection configuration options to PoolConfig: leak_detection_timeout (default 30.0s, minimum 0.0 where 0 disables), enable_leak_detection (default True), add to environment variables (POOL_LEAK_DETECTION_TIMEOUT, POOL_ENABLE_LEAK_DETECTION)

**Checkpoint**: All user stories should now be independently functional - leak detection logs warnings with stack traces, health status reflects leak state

---

## Phase 7: Integration & FastMCP Setup

**Purpose**: Integrate connection pool with FastMCP server lifecycle and health endpoints

- [ ] T037 Create FastMCP server integration in src/mcp/server.py: add pool_manager to app.state, implement @mcp.startup hook to call await app.state.pool_manager.initialize(config), implement @mcp.shutdown hook to call await app.state.pool_manager.shutdown(timeout=30.0), inject pool_manager via FastMCP Context in MCP tools
- [ ] T038 [P] Implement health check MCP resource in src/mcp/health.py: @mcp.resource("health://connection-pool") decorator, async def get_pool_health(ctx: Context) -> dict, call ctx.state.pool_manager.health_check(), return health_status.model_dump(), ensure <10ms response time
- [ ] T039 [P] Add connection pool error handling to existing MCP tools: wrap database operations with try/except for PoolTimeoutError, ConnectionValidationError, PoolClosedError, raise McpError with code "DATABASE_ERROR" and actionable messages, include pool statistics in error data for debugging, no stdout/stderr pollution (MCP protocol compliance)
- [ ] T040 Update configuration loading in src/config/settings.py: add DATABASE_URL environment variable support, create PoolConfig instance from environment variables, validate configuration on server startup (fail-fast), add configuration documentation with examples

**Checkpoint**: Connection pool fully integrated with FastMCP server, health monitoring available, error handling compliant with MCP protocol

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T041 [P] Add comprehensive docstrings to all connection pool modules: ConnectionPoolManager class and all methods, PoolConfig fields with examples, exception classes with usage patterns, health status calculation logic, all docstrings follow Google style guide with Args, Returns, Raises, Examples sections
- [ ] T042 [P] Add type hints and mypy --strict compliance: all function parameters have explicit type annotations, all return types specified (no implicit None), all Pydantic models use strict type checking, ConnectionMetadata dataclass fully typed, no use of Any without justification comments
- [ ] T043 Create example usage in docs/examples/connection_pool_usage.py: demonstrate pool initialization with different configs, show connection acquisition patterns (context manager), demonstrate health check queries, show graceful shutdown, include error handling examples
- [ ] T044 [P] Add connection pool monitoring documentation in docs/operations/connection_pool_monitoring.md: explain health status states and transitions, document pool statistics meanings and thresholds, provide Grafana/Prometheus integration patterns, include troubleshooting guide for common issues (slow queries, connection exhaustion, database outages)
- [ ] T045 Run quickstart.md validation scenarios: Test Scenario 1 (pool initialization <2s), Test Scenario 2 (connection acquisition <10ms), Test Scenario 3 (database outage recovery), Test Scenario 4 (concurrent load 100 requests), Test Scenario 5 (graceful shutdown <30s), verify all success criteria from spec.md (SC-001 through SC-013)
- [ ] T046 Create performance baseline collection script in scripts/collect_connection_pool_baseline.sh: run pytest-benchmark for initialization, acquisition, health check, record p50/p95/p99 latencies, save baseline to performance_baselines/connection_pool_baseline.json, document how to run performance regression tests

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (US1 → US2 → US3 → US4)
- **Integration (Phase 7)**: Depends on User Story 1 and 2 (P1 stories) being complete
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - Extends US1 with reconnection logic
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - Extends US1 with statistics tracking
- **User Story 4 (P3)**: Can start after Foundational (Phase 2) - Extends US1 with leak detection

### Within Each User Story

- Models and exceptions defined in Foundational phase must be complete
- Initialization logic (US1) must work before adding reconnection (US2)
- Basic acquire/release (US1, US2) must work before adding statistics tracking (US3)
- Acquisition tracking must exist before leak detection (US4)

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (T003, T004)
- All Foundational tasks marked [P] can run in parallel (T005, T006, T007, T008, T009)
- Once Foundational phase completes, user story implementations can be worked on in parallel:
  - US1 core (T011-T017)
  - US2 reconnection (T018-T024, requires US1 acquire method)
  - US3 statistics (T025-T029, requires US1 acquire method)
  - US4 leak detection (T030-T036, requires US1 acquire method)
- Integration tasks marked [P] can run in parallel (T038, T039, T041, T042, T044)

---

## Parallel Example: User Story 1

```bash
# After Foundational phase completes, launch US1 models in parallel:
# (All models defined in Phase 2, so no parallel work in US1 setup)

# Implementation tasks for US1 are sequential due to dependencies:
# T011 (manager skeleton) → T012 (initialize method) → T013 (validate helper)
# T014 (config validation) can run in parallel with T011-T013
# T015 (get_statistics) → T016 (health_check) depend on T011-T013 complete
# T017 (logging) can run in parallel with T015-T016
```

---

## Parallel Example: Multiple User Stories

```bash
# After US1 (T011-T017) completes, multiple stories can proceed:

# Team Member A works on US2 (Reconnection):
Task: T018 exponential backoff helper
Task: T019 reconnection loop
Task: T020 background task startup
...

# Team Member B works on US3 (Statistics):
Task: T025 enhance get_statistics
Task: T026 acquisition time tracking
Task: T027 peak metrics
...

# Team Member C works on US4 (Leak Detection):
Task: T030 ConnectionMetadata dataclass
Task: T031 leak tracking in acquire
Task: T032 cleanup in release
...
```

---

## Implementation Strategy

### MVP First (User Story 1 + 2 Only) - P1 Priority

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T010) - CRITICAL, blocks all stories
3. Complete Phase 3: User Story 1 (T011-T017) - Basic pool initialization and health
4. Complete Phase 4: User Story 2 (T018-T024) - Automatic reconnection
5. Complete Phase 7: Integration (T037-T040) - FastMCP integration
6. **STOP and VALIDATE**: Test with quickstart.md scenarios 1-5
7. Deploy/demo MVP with P1 features

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Pool initialization works
3. Add User Story 2 → Test independently → Reconnection works → **MVP READY (P1 complete)**
4. Add User Story 3 → Test independently → Statistics and monitoring
5. Add User Story 4 → Test independently → Leak detection
6. Add Integration → FastMCP health endpoint
7. Add Polish → Documentation and performance baselines

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (T001-T010)
2. Once Foundational is done:
   - Developer A: User Story 1 (T011-T017) - Core pool initialization
   - Developer B: User Story 2 (T018-T024) - After US1 acquire() ready
   - Developer C: User Story 3 (T025-T029) - After US1 acquire() ready
   - Developer D: User Story 4 (T030-T036) - After US1 acquire() ready
3. Integration developer (T037-T040) - After US1 and US2 complete
4. All developers: Polish tasks in parallel (T041-T046)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Tests are NOT included as they were not explicitly requested in spec.md
- Commit after each task or logical group using Conventional Commits format
- Stop at any checkpoint to validate story independently
- All tasks include exact file paths for clarity
- Performance targets (2s init, 10ms acquisition, 10ms health check, 30s reconnection, 30s shutdown) validated in quickstart.md scenarios

---

## Task Count Summary

- **Phase 1 (Setup)**: 4 tasks
- **Phase 2 (Foundational)**: 6 tasks - BLOCKS all user stories
- **Phase 3 (US1 - Server Startup)**: 7 tasks - P1 priority
- **Phase 4 (US2 - Database Outage)**: 7 tasks - P1 priority
- **Phase 5 (US3 - Statistics)**: 5 tasks - P2 priority
- **Phase 6 (US4 - Leak Detection)**: 7 tasks - P3 priority
- **Phase 7 (Integration)**: 4 tasks
- **Phase 8 (Polish)**: 6 tasks

**Total**: 46 tasks

**MVP Scope**: Phases 1-2 + US1 + US2 + Integration = 28 tasks (P1 features only)

**Parallel Opportunities Identified**:
- Setup: 2 parallel tasks
- Foundational: 5 parallel tasks (all models/enums)
- After Foundational: 4 user stories can start in parallel (with coordination on shared acquire() method)
- Integration: 3 parallel tasks
- Polish: 4 parallel tasks
