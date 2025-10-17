# Tasks: Background Indexing for Large Repositories

**Input**: Design documents from `/specs/014-add-background-indexing/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and database schema setup

- [ ] T001 Create database migration for indexing_jobs and job_events tables in alembic/versions/015_add_background_indexing.py
- [ ] T002 [P] Create IndexingJob SQLAlchemy model in src/models/indexing_job.py
- [ ] T003 [P] Create JobEvent SQLAlchemy model in src/models/indexing_job.py
- [ ] T004 [P] Create Pydantic schemas in src/models/indexing_job_schema.py (IndexingJobStatus, IndexingJobCreate, IndexingJobProgress, IndexingJobResult, JobEventCreate, JobEventResponse)
- [ ] T005 Run database migration to create indexing_jobs and job_events tables

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core background job infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T006 Implement duration estimation service in src/services/duration_estimator.py (historical averaging + file count heuristic per research.md Decision 2)
- [ ] T007 Create progress callback type and helper functions in src/services/background_indexing.py
- [ ] T008 Add optional progress_callback parameter to index_repository() in src/services/indexer.py (backward compatible, research.md Decision 7)
- [ ] T009 Implement progress callback invocations at scanning (10%), chunking (10-50%), embedding (50-90%), writing (90-100%) phases in src/services/indexer.py
- [ ] T010 [P] Create background job service skeleton with asyncio.Task management in src/services/background_indexing.py
- [ ] T011 [P] Implement checkpoint save/load logic using metadata JSONB column in src/services/background_indexing.py
- [ ] T012 Implement concurrency control with MAX_CONCURRENT_JOBS=3 limit in src/services/background_indexing.py (research.md Decision 6)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Index Large Repositories Without Interruption (Priority: P1) 🎯 MVP

**Goal**: Enable indexing of 15K+ file repositories in background without blocking MCP client, with real-time progress tracking and completion summary

**Independent Test**: Start indexing on 15K+ file repository, verify user receives immediate confirmation (<1s), job completes successfully in background with accurate summary

**Acceptance Criteria**:
- FR-001: Automatic detection when estimated duration >60s
- FR-002: Job ID returned in <1s
- FR-006: Status queries in <100ms
- SC-001: 100% success rate for 15K+ files
- SC-002: Job creation in <1s

### Implementation for User Story 1

- [ ] T013 [US1] Implement start_indexing_background() MCP tool in src/server.py (job creation, duration estimation, asyncio.Task spawning)
- [ ] T014 [US1] Implement _background_worker() function in src/services/background_indexing.py (orchestrates indexing, progress updates, error handling)
- [ ] T015 [US1] Implement _update_job_progress() helper in src/services/background_indexing.py (PostgreSQL UPDATE every 2s per research.md Decision 4)
- [ ] T016 [US1] Implement get_indexing_status() MCP tool in src/server.py (query single job by ID, <100ms target)
- [ ] T017 [US1] Implement _create_job_record() helper in src/services/background_indexing.py (INSERT into indexing_jobs, return UUID)
- [ ] T018 [US1] Implement job event logging in src/services/background_indexing.py (created, started, progress, completed, failed events per FR-014)
- [ ] T019 [US1] Add error handling and structured logging to _background_worker() (error_message, error_type, error_traceback capture per data-model.md)
- [ ] T020 [US1] Implement job completion logic with result summary (files_indexed, chunks_created, duration, phase timings)

**Checkpoint**: At this point, User Story 1 should be fully functional - can index large repos in background with status tracking

---

## Phase 4: User Story 2 - Monitor Indexing Progress (Priority: P2)

**Goal**: Provide accurate, frequent progress updates showing work completed, current phase, and estimated completion time

**Independent Test**: Start background job, poll status at intervals, verify progress increases monotonically with meaningful phase messages

**Acceptance Criteria**:
- FR-005: Progress updates every 10s or 100 work units
- FR-006: Status queries <100ms
- FR-007: List jobs with filtering <200ms
- SC-005: Status queries <100ms p95

### Implementation for User Story 2

- [ ] T021 [US2] Implement list_background_jobs() MCP tool in src/server.py (with status, repo, project filters, pagination support)
- [ ] T022 [US2] Implement estimated completion time calculation in src/services/background_indexing.py (based on progress rate and files remaining)
- [ ] T023 [US2] Add phase-specific progress messages to progress callback in src/services/indexer.py ("Scanning...", "Chunking files: X/Y", "Generating embeddings: X/Y", "Writing to database...")
- [ ] T024 [US2] Implement progress percentage calculation for each phase in src/services/indexer.py (scanning 0-10%, chunking 10-50%, embedding 50-90%, writing 90-100%)
- [ ] T025 [US2] Add database indexes for list queries in alembic migration (idx_indexing_jobs_status, idx_indexing_jobs_project_id, idx_indexing_jobs_created_at per data-model.md)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work - background indexing with detailed progress monitoring

---

## Phase 5: User Story 3 - Cancel Unwanted Indexing Tasks (Priority: P3)

**Goal**: Allow users to gracefully cancel running jobs within 5 seconds, cleaning up partial work and maintaining database consistency

**Independent Test**: Start large indexing job, cancel mid-execution, verify job stops in <5s with partial work retained and consistent database state

**Acceptance Criteria**:
- FR-008: Cancellation within 5s
- SC-004: Cancellation <5s, consistent state

### Implementation for User Story 3

- [ ] T026 [US3] Implement cancel_indexing_background() MCP tool in src/server.py (set status='cancelled', requires confirmation)
- [ ] T027 [US3] Implement _check_cancellation() helper in src/services/background_indexing.py (database polling every 2s per research.md Decision 5)
- [ ] T028 [US3] Add cancellation check to progress callback in src/services/background_indexing.py (raise asyncio.CancelledError when detected)
- [ ] T029 [US3] Implement graceful shutdown logic in _background_worker() (catch CancelledError, finish current batch, update status)
- [ ] T030 [US3] Implement _cleanup_partial_work() helper in src/services/background_indexing.py (update cancelled_at timestamp, retain chunks)
- [ ] T031 [US3] Add cancellation validation (reject if already completed/failed/cancelled) in src/services/background_indexing.py

**Checkpoint**: All core user stories (US1, US2, US3) should now be independently functional

---

## Phase 6: User Story 4 - Resume Indexing After Interruptions (Priority: P2)

**Goal**: Automatically resume interrupted jobs on server restart from last checkpoint with <1% duplicate work

**Independent Test**: Start job, interrupt server mid-execution, restart server, verify job auto-resumes in <10s with <1% duplicate work

**Acceptance Criteria**:
- FR-009: Auto-resume within 10s of restart
- FR-010: <1% duplicate work via checkpoints every 500 files or 30s
- SC-003: Resume <10s, <1% duplicate work

### Implementation for User Story 4

- [ ] T032 [US4] Implement checkpoint save logic in src/services/background_indexing.py (every 500 files or 30s, file list snapshot in metadata JSONB per research.md Decision 3)
- [ ] T033 [US4] Implement _save_checkpoint() helper in src/services/background_indexing.py (PostgreSQL UPDATE with files_processed list)
- [ ] T034 [US4] Implement resume_interrupted_job() function in src/services/background_indexing.py (load checkpoint, diff files, resume from unprocessed)
- [ ] T035 [US4] Add server startup hook in src/server.py to query jobs with status='running' and spawn resume tasks
- [ ] T036 [US4] Implement checkpoint-based file filtering in src/services/indexer.py (skip already-processed files, update initial_progress counters)
- [ ] T037 [US4] Add 'blocked' status transition logic for external resource unavailability (embedding service down) in src/services/background_indexing.py

**Checkpoint**: All user stories (US1-4) complete - full background indexing with resumption support

---

## Phase 7: Integration Tests

**Purpose**: Validate end-to-end workflows against acceptance criteria

- [ ] T038 [P] Create test fixture generator for 15K file repositories in tests/fixtures/generate_test_repo.py
- [ ] T039 [P] Integration test for Scenario 1 (Basic background indexing) in tests/integration/test_background_indexing_basic.py - validates FR-001, FR-002, FR-006, SC-001, SC-002
- [ ] T040 [P] Integration test for Scenario 2 (Progress monitoring) in tests/integration/test_background_indexing_progress.py - validates FR-005, FR-006, SC-005
- [ ] T041 [P] Integration test for Scenario 3 (Job cancellation) in tests/integration/test_background_indexing_cancel.py - validates FR-008, SC-004
- [ ] T042 [P] Integration test for Scenario 4 (Restart recovery) in tests/integration/test_background_indexing_recovery.py - validates FR-009, FR-010, SC-003
- [ ] T043 [P] Integration test for Scenario 5 (Concurrent jobs) in tests/integration/test_background_indexing_concurrent.py - validates FR-011, SC-006
- [ ] T044 [P] Performance test for job creation latency in tests/performance/test_job_creation_latency.py - validates <1s p95
- [ ] T045 [P] Performance test for status query latency in tests/performance/test_status_query_latency.py - validates <100ms p95
- [ ] T046 [P] Performance test for cancellation timing in tests/performance/test_cancellation_timing.py - validates <5s

---

## Phase 8: Contract & Unit Tests

**Purpose**: Validate MCP tool contracts and model behavior

- [ ] T047 [P] Contract test for start_indexing_background tool in tests/contract/test_start_indexing_background.py (validate input/output schemas per contracts/mcp-tools.json)
- [ ] T048 [P] Contract test for get_indexing_status tool in tests/contract/test_get_indexing_status.py (validate response schema)
- [ ] T049 [P] Contract test for list_background_jobs tool in tests/contract/test_list_background_jobs.py (validate filters, pagination)
- [ ] T050 [P] Contract test for cancel_indexing_background tool in tests/contract/test_cancel_indexing_background.py (validate confirmation requirement)
- [ ] T051 [P] Unit test for duration estimation algorithm in tests/unit/test_duration_estimator.py (historical averaging, fallback heuristic)
- [ ] T052 [P] Unit test for IndexingJob model in tests/unit/test_indexing_job_model.py (state transitions, business invariants)
- [ ] T053 [P] Unit test for checkpoint save/load in tests/unit/test_checkpoint_logic.py (JSONB serialization, recovery)
- [ ] T054 [P] Unit test for progress callback in tests/unit/test_progress_callback.py (invocation frequency, cancellation detection)

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T055 Implement 7-day retention cleanup job in src/services/background_indexing.py (FR-013: remove completed/failed/cancelled jobs after 7 days)
- [ ] T056 Add cleanup scheduler to server startup in src/server.py (runs on startup and every 24 hours per FR-013)
- [ ] T057 Implement duplicate job prevention in src/services/background_indexing.py (FR-012: check for existing pending/running job for same repo)
- [ ] T058 Add prerequisite validation in src/services/background_indexing.py (FR-015: path exists, read permissions, sufficient disk space)
- [ ] T059 [P] Add structured logging for all job lifecycle events (created, started, progress, completed, failed, cancelled per FR-014)
- [ ] T060 [P] Add connection pool monitoring and adjustment if needed in src/database/session.py (3 concurrent jobs × 7 connections = 21, verify pool capacity)
- [ ] T061 Update CLAUDE.md agent context file with background indexing implementation details
- [ ] T062 Run quickstart.md validation scenarios (all 5 scenarios from quickstart.md)
- [ ] T063 Run mypy --strict type checking on all new files
- [ ] T064 Verify ≥80% code coverage for background indexing modules

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (US1 → US2 → US4 → US3)
- **Tests (Phase 7-8)**: Can run in parallel, depend on corresponding implementation phases
- **Polish (Phase 9)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories - **MVP TARGET**
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Extends US1 with enhanced monitoring
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Adds cancellation to US1
- **User Story 4 (P2)**: Can start after Foundational (Phase 2) - Adds resumption to US1

### Within Each User Story

- Core implementation before integration
- Services before MCP tools
- Story complete before moving to next priority

### Parallel Opportunities

- **Phase 1**: T002, T003, T004 (different models/schemas)
- **Phase 2**: T006, T010, T011 (different services/modules)
- **Phase 7**: T038-T046 (all integration tests)
- **Phase 8**: T047-T054 (all contract and unit tests)
- **Phase 9**: T059, T060 (logging and monitoring)
- **Across User Stories**: US1, US2, US3, US4 can be worked on in parallel by different developers after Foundational phase

---

## Parallel Example: User Story 1

```bash
# Core implementation tasks that can run in parallel (different files):
Task T013: "Implement start_indexing_background() MCP tool in src/server.py"
Task T014: "Implement _background_worker() function in src/services/background_indexing.py"
Task T015: "Implement _update_job_progress() helper in src/services/background_indexing.py"

# Must run sequentially:
T017 → T013 (job creation helper before MCP tool)
T018 → T014 (event logging before worker)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T005) - Database schema ready
2. Complete Phase 2: Foundational (T006-T012) - Core infrastructure ready (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (T013-T020) - Background indexing functional
4. **STOP and VALIDATE**: Run Scenario 1 integration test (T039)
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready (T001-T012)
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!) (T013-T020 + T039)
3. Add User Story 2 → Test independently → Deploy/Demo (T021-T025 + T040)
4. Add User Story 4 → Test independently → Deploy/Demo (T032-T037 + T042)
5. Add User Story 3 → Test independently → Deploy/Demo (T026-T031 + T041)
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (T001-T012)
2. Once Foundational is done:
   - Developer A: User Story 1 (T013-T020)
   - Developer B: User Story 2 (T021-T025)
   - Developer C: User Story 4 (T032-T037)
   - Developer D: User Story 3 (T026-T031)
3. Stories complete and integrate independently

---

## Task Count Summary

- **Phase 1 (Setup)**: 5 tasks
- **Phase 2 (Foundational)**: 7 tasks - **BLOCKING**
- **Phase 3 (US1 - MVP)**: 8 tasks
- **Phase 4 (US2)**: 5 tasks
- **Phase 5 (US3)**: 6 tasks
- **Phase 6 (US4)**: 6 tasks
- **Phase 7 (Integration Tests)**: 9 tasks
- **Phase 8 (Contract/Unit Tests)**: 8 tasks
- **Phase 9 (Polish)**: 10 tasks

**Total**: 64 tasks

**Parallel Opportunities**: 32 tasks marked [P] can run in parallel (50% of total)

**MVP Scope** (recommended initial delivery):
- Phase 1: Setup (5 tasks)
- Phase 2: Foundational (7 tasks)
- Phase 3: User Story 1 (8 tasks)
- Phase 7: Basic integration test (1 task - T039)
- **Total MVP**: 21 tasks (33% of total)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability (US1, US2, US3, US4)
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Constitutional compliance maintained throughout:
  - Principle I: Simplicity (asyncio-only, no external queues)
  - Principle II: Local-First (PostgreSQL state, offline-capable)
  - Principle IV: Performance (<1s job creation, <100ms queries, <5s cancellation)
  - Principle V: Production Quality (comprehensive error handling, type safety)
  - Principle VIII: Pydantic Type Safety (all models use Pydantic, mypy --strict)
