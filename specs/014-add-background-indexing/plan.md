# Implementation Plan: Background Indexing for Large Repositories

**Branch**: `014-add-background-indexing` | **Date**: 2025-10-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/014-add-background-indexing/spec.md`

## Summary

Add background job execution for repository indexing operations that exceed MCP client timeout limits (30 seconds). System automatically detects when estimated indexing duration exceeds 60 seconds and initiates asynchronous execution with PostgreSQL-native job tracking, real-time progress updates, checkpoint-based recovery, and graceful cancellation. Supports up to 3 concurrent indexing operations with automatic queueing and maintains all constitutional performance targets (60s/10K lines indexing, <500ms p95 search).

**Technical Approach**: asyncio.Task-based background workers with PostgreSQL state persistence, progress callback integration into existing indexer, JSONB-based checkpointing every 500 files or 30 seconds, graceful shutdown via database polling, connection pool-based concurrency limiting.

## Technical Context

### Language & Platform
- **Language/Version**: Python 3.11+
- **Target Platform**: Linux/macOS server (local-first MCP server)
- **Project Type**: Existing MCP server (`src/` structure) with background job management extension

### Dependencies & Frameworks
- **Primary Framework**: FastMCP (MCP server framework)
- **MCP Protocol**: MCP Python SDK (official Anthropic SDK)
- **Database**: PostgreSQL 14+ with asyncpg driver
- **ORM**: SQLAlchemy 2.0 (async)
- **Validation**: Pydantic v2 (all models)
- **Job Management**: asyncio (no external queue dependencies per local-first principle)
- **Testing**: pytest, pytest-asyncio, pytest-cov (≥80% coverage required)

### Storage Architecture
- **Primary Database**: PostgreSQL 14+ (existing `codebase_mcp` database)
- **New Tables**:
  - `indexing_jobs` - Job metadata, status, progress tracking
  - `job_events` - Audit log for lifecycle events (created, started, progress, completed, failed, cancelled)
- **Indexing Schema**: pgvector extension (existing `repositories`, `code_chunks`, `embeddings` tables)
- **Isolation**: Schema-based multi-project workspace isolation (existing pattern)

### Performance Requirements
- **Indexing Throughput**: Maintain 60s per 10,000 lines (constitutional baseline)
- **Search Latency**: <500ms p95 (existing requirement, must not degrade)
- **Job Initiation**: <1s from MCP tool call to background execution start
- **Status Queries**: <100ms p95 for `get_job_status` and `list_jobs`
- **Cancellation**: <5s from cancel request to job termination
- **Restart Recovery**: <1% duplicate work on interrupted job resume

### Scale & Capacity
- **Repository Size**: Support 15,000+ file repositories (existing validated scale)
- **Concurrent Jobs**: Maximum 3 concurrent indexing jobs per server instance
- **Job Retention**: 7-day completed/failed job history with automatic cleanup
- **Checkpoint Frequency**: Every 500 files or 30 seconds
- **Event Log**: Unlimited events during job lifecycle, pruned with parent job

### Constraints & Limitations
- **MCP Timeout**: 30-second protocol timeout (background execution validated to avoid blocking)
- **No External Queue**: Use asyncio task management only (local-first architecture)
- **No Cloud Dependencies**: All state persisted in local PostgreSQL (offline-capable)
- **Atomic Operations**: Checkpoint writes must be transactional (crash-safe)
- **Schema Compatibility**: Backward compatible with existing indexing flow (no breaking changes)

### Testing Strategy
- **Unit Tests**: Individual services (BackgroundJobService, CheckpointService, EventService)
- **Integration Tests**: End-to-end background indexing with database persistence
- **Performance Tests**: Baseline validation (indexing, status queries, cancellation timing)
- **Resilience Tests**: Crash recovery, duplicate prevention, concurrent job limits
- **Coverage Target**: ≥80% code coverage (constitutional requirement)

### Constitutional Compliance
- **Principle I**: Simplicity Over Features - asyncio-only job management, no external queues
- **Principle II**: Local-First Architecture - PostgreSQL persistence, no cloud state
- **Principle III**: Protocol Compliance - MCP tool registration, non-blocking background execution
- **Principle IV**: Performance Guarantees - Validated targets above, <10% variance from baseline
- **Principle V**: Production Quality - Comprehensive error handling, crash recovery, structured logging
- **Principle VII**: Test-Driven Development - Tests before implementation, integration coverage
- **Principle VIII**: Pydantic-Based Type Safety - All models use Pydantic, mypy --strict compliance

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Simplicity Over Features | **PASS** | Feature scope is tightly constrained to solving MCP timeout limitations for large repository indexing. All functionality directly serves the core semantic search capability. Non-Goals section explicitly excludes 15+ out-of-scope features (WebSocket streaming, distributed indexing, job prioritization, CI/CD integration, scheduling, multi-user isolation, job chaining, push notifications, migration, incremental indexing). Background job tracking is essential infrastructure, not feature creep. |
| II. Local-First Architecture | **PASS** | Feature maintains offline-first operation with PostgreSQL-native job tracking. No cloud dependencies introduced. All state persisted locally in database. Checkpoint recovery enables resilience across server restarts without external services. Polling-based status checks (not WebSocket/push) align with local-first principles. |
| III. Protocol Compliance (MCP) | **PASS** | Background jobs accessed via MCP tools (job status queries, cancellation). FR-014 requires event logging for audit trail. No stdout/stderr pollution mentioned. Status queries via structured MCP tool responses within 100ms (FR-006). Job creation returns tracking identifier through MCP response (FR-002). |
| IV. Performance Guarantees | **PASS** | SC-006 explicitly requires 3 concurrent background jobs to meet constitutional performance targets (60s indexing, 500ms search). FR-001 triggers background execution when estimated duration exceeds 60 seconds, preserving constitutional 60s target for user-facing operations. Job status queries limited to 100ms (FR-006). No degradation to existing performance guarantees. |
| V. Production Quality | **PASS** | Comprehensive error handling specified: FR-014 (audit logging), FR-015 (prerequisite validation), SC-007 (< 2% failure rate with actionable messages), SC-008 (95% message clarity). Edge cases document failure scenarios (database loss, embedding service unavailable, storage exhaustion). Graceful cancellation within 5 seconds (FR-008). Clear state transitions (FR-004). Progress checkpointing prevents data loss (FR-010). |
| VI. Specification-First | **PASS** | Complete specification with user scenarios, functional requirements, success criteria, and test scenarios. All requirements traced to acceptance scenarios. No implementation details (HOW) included - focuses on WHAT/WHY. Acceptance criteria quantified (1s job creation, 5s cancellation, <1% duplicate work). Spec complete before planning phase. |
| VII. Test-Driven Development | **PASS** | Each user story includes "Independent Test" section defining how to validate functionality. Acceptance scenarios provide testable criteria (Given/When/Then format). Success criteria are measurable (SC-001 through SC-008 with quantitative metrics). Edge cases define failure testing scenarios. Test scenarios defined before implementation begins. |
| VIII. Pydantic Type Safety | **PASS** | Key Entities section defines Background Job, Job Checkpoint, and Job Event with clear attributes and invariants. Structured data models implied (job state, progress metrics, error details, checkpoint data). While implementation details deferred to planning phase, specification structure anticipates Pydantic models for all entities and MCP tool responses. FR-015 requires validation at system boundaries. |
| IX. Orchestrated Subagents | **PASS** | N/A for specification phase. Evaluation deferred to implementation phase. |
| X. Git Micro-Commits | **PASS** | Feature branch `014-add-background-indexing` created per constitutional requirements. Branch naming follows `###-feature-name` pattern. Specification complete before planning. Ready for TDD micro-commit workflow during implementation. |
| XI. FastMCP Foundation | **PASS** | Background job operations will be exposed as MCP tools (status queries, cancellation per FR-006, FR-007, FR-008). While implementation details deferred to planning, specification anticipates @mcp.tool decorators for job management operations. No protocol violations introduced - job tracking enhances rather than replaces existing MCP tool interface. |

**Overall Gate Status**: **PASS**

**Justification for WARN/FAIL**: None - all principles validated.

**Post-Phase 1 Re-evaluation**: All principles remain **PASS** after design artifact generation. Technical decisions (asyncio.Task, PostgreSQL state, progress callbacks) maintain constitutional compliance.

## Project Structure

### Documentation (this feature)

```
specs/014-add-background-indexing/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file (implementation plan)
├── research.md          # Phase 0 technical research (complete)
├── data-model.md        # Phase 1 database schema & Pydantic models (complete)
├── quickstart.md        # Phase 1 integration test scenarios (complete)
├── contracts/           # Phase 1 MCP tool contracts (complete)
│   ├── mcp-tools.json        # Tool registration schemas
│   ├── request-schemas.json  # Request parameter validation
│   └── response-schemas.json # Response schemas with examples
├── checklists/
│   └── requirements.md  # Specification quality validation (complete)
└── tasks.md             # Phase 2 task breakdown (created by /speckit.tasks command)
```

### Source Code (repository root)

```
src/
├── models/
│   ├── indexing_job.py          # NEW: IndexingJob, JobEvent SQLAlchemy models
│   ├── indexing_job_schema.py   # NEW: Pydantic request/response schemas
│   └── repository.py             # EXISTING: Repository model (no changes)
├── services/
│   ├── background_indexing.py   # NEW: Background job orchestration
│   ├── indexer.py                # MODIFIED: Add progress_callback parameter
│   ├── embedder.py               # EXISTING: No changes
│   └── chunker.py                # EXISTING: No changes
├── database/
│   └── session.py                # EXISTING: Connection pool (may need pool size increase)
└── server.py                     # MODIFIED: Register new MCP tools

tests/
├── contract/
│   └── test_background_job_tools.py  # NEW: MCP tool contract validation
├── integration/
│   ├── test_background_indexing.py   # NEW: End-to-end background job workflow
│   ├── test_cancellation.py          # NEW: Cancellation within 5s validation
│   ├── test_restart_recovery.py      # NEW: Checkpoint-based resume validation
│   └── test_concurrent_jobs.py       # NEW: 3-job concurrency limit validation
├── unit/
│   ├── test_indexing_job_model.py    # NEW: Pydantic model validation
│   ├── test_progress_callback.py     # NEW: Callback invocation logic
│   └── test_duration_estimation.py   # NEW: Estimation algorithm accuracy
└── performance/
    ├── test_job_creation_latency.py  # NEW: <1s job creation benchmark
    ├── test_status_query_latency.py  # NEW: <100ms status query benchmark
    └── test_cancellation_timing.py   # NEW: <5s cancellation benchmark

alembic/versions/
└── 015_add_background_indexing.py    # NEW: Migration for indexing_jobs, job_events tables
```

**Structure Decision**: Single project structure (Option 1) selected. This is an extension to the existing Codebase MCP Server codebase (`src/` directory). Background indexing functionality integrates into existing services (indexer.py modified, new background_indexing.py service added). Database models extend existing ORM layer (new models in `src/models/`). MCP tools registered in existing `server.py` via FastMCP `@mcp.tool` decorators.

## Complexity Tracking

*No constitutional violations to justify.*

The background indexing feature introduces necessary complexity (2 new database tables: indexing_jobs, job_events; 1 new service: background_indexing.py) but this complexity is fully justified:

- **Problem**: Constitutional performance targets (60s indexing) become impossible for large repositories (15K+ files) without background processing, making the tool unusable for enterprise codebases
- **Alternatives Considered**:
  - Streaming progress updates (rejected - adds WebSocket complexity, violates Protocol Compliance)
  - Distributed processing (rejected - violates Local-First Architecture)
  - Synchronous blocking (rejected - violates MCP timeout limits)
- **Justification**: Background job infrastructure is the minimal complexity addition required to serve constitutional Principle I (semantic search focus) and Principle IV (performance guarantees) for enterprise-scale repositories
- **Mitigation**:
  - Scope tightly constrained via 15-item Non-Goals section
  - PostgreSQL-native implementation (no external job queue like Redis/Celery)
  - 7-day retention limit prevents unbounded growth
  - Fixed 3-job concurrency limit prevents resource exhaustion
  - asyncio-only (no threading/multiprocessing complexity)

The complexity serves constitutional compliance rather than violating it.

## Phase 0: Research (Complete)

**Output**: [research.md](./research.md)

**Decisions Made**:

1. **Background Job Execution Model**: asyncio.Task with PostgreSQL state tracking
2. **Duration Estimation Strategy**: Historical averaging + file count heuristic with 60s constitutional baseline fallback
3. **Checkpoint Strategy**: PostgreSQL transaction-based snapshots (every 500 files or 30 seconds)
4. **Progress Tracking**: Committed PostgreSQL UPDATEs every 2 seconds
5. **Cancellation Mechanism**: Database polling with 5-second graceful shutdown guarantee
6. **Concurrency Control**: Connection pool-based limiting (3 concurrent jobs maximum)
7. **Indexer Integration**: Optional `progress_callback` parameter to existing `index_repository()`

**Constitutional Alignment Validated**: All decisions maintain Simplicity (no external queues), Local-First (PostgreSQL-only), Performance (<1% overhead), and Production Quality (ACID guarantees, graceful failure).

## Phase 1: Design & Contracts (Complete)

**Outputs**:
- [data-model.md](./data-model.md) - Database schema, Pydantic models, SQLAlchemy ORM
- [contracts/](./contracts/) - MCP tool contracts (4 tools: start, status, list, cancel)
- [quickstart.md](./quickstart.md) - Integration test scenarios (5 scenarios covering all user stories)

**Design Artifacts**:

### Database Schema (data-model.md)

- **indexing_jobs table**: 21 columns (status, progress, counters, errors, timestamps, JSONB metadata)
- **job_events table**: 5 columns (audit log with event types: created, started, progress, completed, failed, cancelled)
- **5 performance indexes** per table optimized for <100ms queries
- **Status enum**: pending, running, completed, failed, cancelled, blocked
- **Checkpoint strategy**: JSONB metadata with file list snapshot (Phase 1) and progress marker (future optimization)

### Pydantic Models (data-model.md)

- `IndexingJobStatus` (enum)
- `IndexingJobCreate` (with path validation, UUID generation)
- `IndexingJobProgress` (status query response)
- `IndexingJobResult` (completion summary)
- `JobEventCreate` (audit log entry)
- `JobEventResponse` (event query response)
- `ProgressCallback` (type alias for callback signature)

### MCP Tool Contracts (contracts/)

1. **start_indexing_background**: Initiate background job, return job_id in <1s
2. **get_job_status**: Query single job status, return in <100ms
3. **list_background_jobs**: List jobs with filters (status, repo, project), pagination support
4. **cancel_job**: Gracefully cancel job within 5s, requires confirmation

All contracts include complete input/output schemas, validation rules, error definitions, and real-world usage examples.

### Integration Tests (quickstart.md)

- **Scenario 1**: Basic background indexing (User Story 1 - 15K files, no timeout)
- **Scenario 2**: Progress monitoring (User Story 2 - monotonic progress, phase transitions)
- **Scenario 3**: Job cancellation (User Story 3 - <5s termination, consistent state)
- **Scenario 4**: Restart recovery (User Story 4 - auto-resume, <1% duplicate work)
- **Scenario 5**: Concurrent jobs (FR-011 - 3 concurrent, 4th queued)

Each scenario includes executable Python code, assertions, performance validation, and traceability to functional requirements.

### Agent Context Update

Updated CLAUDE.md with background indexing technical stack, architectural decisions, and implementation guidance.

## Phase 2: Task Breakdown (Next Step)

**Command**: `/speckit.tasks`

**Prerequisites**: All Phase 1 artifacts complete ✓

**Expected Output**:
- `tasks.md` with dependency-ordered implementation tasks
- TDD approach: test tasks before implementation tasks
- Parallelizable tasks marked `[P]`
- Atomic micro-commits per task

**Readiness**: All technical unknowns resolved, design artifacts complete, ready for task generation.

## Next Steps

1. Run `/speckit.tasks` to generate implementation task breakdown
2. Execute `/speckit.implement` to begin TDD implementation
3. Follow Git micro-commit strategy (one commit per completed task)
4. Validate constitutional compliance at each checkpoint via `/speckit.analyze`

**Estimated Implementation Time**: 8-12 hours (based on task complexity and TDD discipline)

**Branch Ready for PR**: After all tasks complete, tests pass, and constitutional compliance validated.
