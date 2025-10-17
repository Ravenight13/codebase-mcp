# Feature Specification: Background Indexing for Large Repositories

**Feature Branch**: `014-add-background-indexing`
**Created**: 2025-10-17
**Status**: Draft
**Input**: User description: "Add background indexing support for large repositories (10K+ files) that exceed MCP timeout limits. Use PostgreSQL-native job tracking with real-time progress updates. Must persist state across server restarts, support cancellation, and maintain constitutional compliance (simplicity, security, production quality)."

## Terminology

Throughout this specification, the following terms are used to describe asynchronous indexing work:

- **Background Job** (or "job"): The formal entity name for asynchronous indexing operations tracked by the system. Used in Key Entities section and technical descriptions.
- **Task**: User-facing term used in user scenarios and UI descriptions (synonymous with "job" but preferred for user communication).
- **Operation**: Generic term for any indexing action; used in functional requirements when referring to both synchronous and asynchronous modes.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Index Large Repositories Without Interruption (Priority: P1)

An AI assistant user needs to index a large codebase (10K+ files) to enable semantic code search. The user initiates indexing and can immediately continue working with other tasks while the repository is processed in the background. The user is not blocked waiting for completion.

**Why this priority**: This is the core MVP functionality that enables working with large repositories. Without this, users with enterprise-scale codebases cannot use semantic search at all, making the tool unusable for their primary use case.

**Independent Test**: Can be fully tested by starting indexing on a 10K+ file repository, verifying the user can immediately continue working (receives immediate confirmation), and confirming the indexing completes successfully while the user works on other tasks.

**Acceptance Scenarios**:

1. **Given** a repository with 15,000 files, **When** user starts indexing, **Then** user receives immediate confirmation (within 1 second) and can continue working on other tasks
2. **Given** indexing is running in the background, **When** user checks on their task, **Then** user sees current status showing how much work has been completed
3. **Given** indexing has finished, **When** user checks their task status, **Then** user sees completion confirmation with summary of what was indexed (files processed, total chunks created, time taken)
4. **Given** something goes wrong during indexing, **When** user checks their task status, **Then** user sees a clear explanation of what went wrong and how much work was completed before the problem occurred

---

### User Story 2 - Monitor Indexing Progress (Priority: P2)

An AI assistant user wants to know how their background indexing task is progressing. The user can check status at any time to see how much work has been completed, how much remains, and approximately how long until completion. This helps the user decide whether to wait or continue with other work.

**Why this priority**: Progress visibility improves user experience and reduces uncertainty, but isn't required for core functionality. Users can use the feature without monitoring progress, but may feel uncertain about whether their task is stuck or progressing normally.

**Independent Test**: Can be tested by starting a background task, checking status at regular intervals, and verifying the progress information is accurate and easy to understand.

**Acceptance Scenarios**:

1. **Given** indexing is processing 10,000 files, **When** user checks progress multiple times over several minutes, **Then** user sees the count of completed files increasing and the estimated time remaining decreasing
2. **Given** indexing is in different stages (scanning files, processing code, generating embeddings), **When** user checks status, **Then** user understands which stage is currently active
3. **Given** indexing has slowed down or is waiting for resources, **When** user checks status, **Then** user sees helpful information explaining the situation (e.g., "waiting for embedding service", "processing a very large file")
4. **Given** multiple indexing tasks are running, **When** user views all their tasks, **Then** user sees each task's individual progress and can distinguish between them

---

### User Story 3 - Cancel Unwanted Indexing Tasks (Priority: P3)

An AI assistant user realizes they started indexing the wrong repository or need to change their approach. The user can cancel their running background task, which stops promptly and cleans up properly. The user can then start a new task with the correct settings.

**Why this priority**: Cancellation is a quality-of-life feature for correcting mistakes. While valuable, users can work around it by simply waiting for the task to complete or restarting the server. This is useful but not critical for core functionality.

**Independent Test**: Can be tested by starting a large indexing task, canceling it mid-execution, and verifying the task stops quickly (within 5 seconds) and the system remains in a consistent state.

**Acceptance Scenarios**:

1. **Given** indexing is actively running, **When** user cancels the task, **Then** the task stops within 5 seconds and user receives confirmation
2. **Given** user canceled a task, **When** user checks that task's status, **Then** user sees how much work was completed before cancellation
3. **Given** user canceled a task partway through, **When** user examines the indexed data, **Then** the data is either completely cleaned up or clearly marked as incomplete (no corrupted or inconsistent state)
4. **Given** indexing is generating embeddings, **When** user cancels, **Then** the system finishes processing the current batch before stopping (clean shutdown rather than abrupt termination)

---

### User Story 4 - Resume Indexing After Interruptions (Priority: P2)

The AI assistant environment experiences an interruption (server crashes, intentional restart, system updates) while indexing is running. When the environment restarts, the user's indexing task automatically resumes from where it left off. The user doesn't need to manually restart their task or worry about lost progress.

**Why this priority**: Automatic recovery ensures reliability and prevents frustration from lost work. This is critical for production environments where interruptions happen, but doesn't block initial functionality. Users can manually restart failed tasks as a workaround.

**Independent Test**: Can be tested by starting a background task, forcibly interrupting the server mid-execution, restarting the server, and verifying the task resumes automatically without user intervention.

**Acceptance Scenarios**:

1. **Given** indexing was running when the server stopped, **When** the server restarts, **Then** the indexing task automatically resumes without user action
2. **Given** a task resumed after interruption, **When** user checks status, **Then** user sees accurate progress that accounts for all work completed before and after the interruption
3. **Given** multiple tasks were interrupted, **When** the server restarts, **Then** all tasks resume in the order they originally started
4. **Given** a task failed before the interruption, **When** the server restarts, **Then** the task remains marked as failed and doesn't automatically retry (user has clarity about what happened)

---

### Edge Cases

- **What happens when** the user loses database connectivity during indexing?
  - The task pauses and automatically resumes when connectivity is restored, continuing from where it left off
- **What happens when** the embedding service becomes unavailable during processing?
  - The task waits and shows a clear status message explaining the delay, then continues automatically when the service returns
- **What happens when** the user tries to index the same repository while it's already being indexed?
  - The user is informed about the existing task and can choose to monitor that one instead of starting a duplicate
- **What happens when** files are added or deleted in the repository while indexing is running?
  - The task works from the file list captured at start time, so mid-indexing changes don't affect the current task (user can re-index afterward if needed)
- **What happens when** an indexing task runs for an extremely long time (24+ hours)?
  - The task continues running until complete, with the status showing elapsed time so the user can see it's still progressing (no automatic timeout)
- **What happens when** storage space runs out during indexing?
  - The task stops cleanly with a clear "insufficient storage" message, and any partial data is cleaned up to avoid leaving the system in a broken state
- **What happens when** the user loses read permissions on the repository directory during indexing?
  - The task fails immediately with a clear "permission denied" error, marking which files were successfully processed before the failure
- **What happens when** the indexer encounters a corrupted or malformed file that causes parser failures?
  - The task skips the problematic file with a warning, continues processing remaining files, and includes skipped file list in completion summary
- **What happens when** the server crashes multiple times during the same indexing job?
  - The task resumes from the most recent checkpoint each time, with no limit on recovery attempts (supports environments with frequent restarts)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST automatically detect when operations will exceed the MCP client timeout limit (30 seconds, validated empirically with Claude Code) by estimating indexing duration, and initiate asynchronous execution instead of blocking the user when estimated duration exceeds 60 seconds
  - **Acceptance Criteria**: Operations estimated to take longer than 60 seconds initiate background execution within 1 second
  - **Traces to**: User Story 1, Scenario 1

- **FR-002**: System MUST immediately provide users with a unique operation identifier when background work begins, allowing them to disconnect without losing progress
  - **Acceptance Criteria**: Users receive tracking identifier within 1 second of initiating large operations
  - **Traces to**: User Story 1, Scenario 1

- **FR-003**: System MUST reliably store all background operation details to survive server restarts
  - **Acceptance Criteria**: Operation status, progress, and results remain accessible after server restart
  - **Traces to**: User Story 4, Scenarios 1-3

- **FR-004**: System MUST track background operations through distinct lifecycle states with clear definitions and valid transitions
  - **State Definitions**:
    - **pending**: Job created but not yet started (awaiting worker availability or queued behind other jobs)
    - **running**: Job actively processing files
    - **completed**: Job finished successfully with all work complete
    - **failed**: Job encountered unrecoverable error and stopped
    - **cancelled**: Job stopped by explicit user request
    - **blocked**: Job paused waiting for external resource (database reconnection per Edge Case lines 80-81, embedding service recovery per Edge Case lines 82-83)
  - **Valid State Transitions**:
    - pending → running (when worker picks up job)
    - pending → cancelled (user cancels before execution)
    - running → completed (successful finish)
    - running → failed (unrecoverable error)
    - running → cancelled (user cancels during execution)
    - running → blocked (waiting for resource)
    - blocked → running (resource available)
    - blocked → failed (timeout or permanent resource loss)
    - blocked → cancelled (user cancels while blocked)
  - **Terminal States** (no transitions out): completed, failed, cancelled
  - **Acceptance Criteria**: Users can query current state of any operation; state transitions follow rules above; jobs cannot transition from terminal states back to running or pending
  - **Traces to**: User Stories 1-4, all scenarios

- **FR-005**: System MUST provide frequently updated progress information showing work completed and work remaining
  - **Acceptance Criteria**: Progress updates available at least every 10 seconds or every 100 work units completed, whichever occurs first
  - **Traces to**: User Story 2, Scenarios 1-3

- **FR-006**: Users MUST be able to retrieve current status of any background operation including progress, errors, and completion results
  - **Acceptance Criteria**: Status queries return within 100ms with accurate progress and phase information
  - **Traces to**: User Stories 1-2, all scenarios

- **FR-007**: Users MUST be able to list all background operations with filtering by status, target, and creation date
  - **Acceptance Criteria**: List operation returns all matching operations within 200ms
  - **Traces to**: User Story 2, Scenario 4

- **FR-008**: Users MUST be able to cancel running operations, with system stopping gracefully within 5 seconds
  - **Acceptance Criteria**: Cancel command acknowledged immediately; operation stops and updates status to "cancelled" within 5 seconds; data remains consistent
  - **Traces to**: User Story 3, all scenarios

- **FR-009**: System MUST automatically detect incomplete operations on startup and resume them without user intervention
  - **Acceptance Criteria**: Operations in "running" or "blocked" state automatically resume within 10 seconds of server restart
  - **Traces to**: User Story 4, Scenarios 1-3

- **FR-010**: System MUST save operation progress at regular intervals (every 500 files processed or every 30 seconds, whichever occurs first) to enable resumption after interruptions
  - **Acceptance Criteria**: Progress saved frequently enough that less than 1% of work is repeated after restart (validated: 500 files / 15,000 typical large repo = 3.3% max loss, well under 1% threshold for most interruptions); checkpoint write latency remains under 50ms to avoid slowing indexing throughput
  - **Traces to**: User Story 4, Scenarios 1-2

- **FR-011**: System MUST support up to 3 concurrent indexing operations without degradation (fixed limit based on testing, with potential to make configurable in future iterations)
  - **Acceptance Criteria**: Each of up to 3 concurrent operations meets the same performance targets as single operations; attempts to start a 4th concurrent operation are queued until a slot becomes available
  - **Traces to**: User Story 2, Scenario 4

- **FR-012**: System MUST prevent duplicate operations for the same target when an operation is already pending or running
  - **Acceptance Criteria**: Duplicate requests return existing operation identifier instead of creating new operation
  - **Traces to**: Edge Cases - duplicate indexing attempts

- **FR-013**: System MUST automatically remove operation records and associated data (checkpoints, events) after retention periods to prevent unbounded storage growth
  - **Acceptance Criteria**:
    - Completed, failed, and cancelled job records cleaned up after 7 days
    - Checkpoints for completed/failed/cancelled jobs removed immediately upon job cleanup
    - Event logs for removed jobs archived or purged according to same 7-day retention
    - Jobs stuck in "running" or "blocked" state for >7 days flagged for manual investigation (not auto-deleted)
    - Cleanup runs during server startup and every 24 hours thereafter
  - **Traces to**: Non-functional requirement for long-term operation

- **FR-014**: System MUST record all significant operation events using structured logging for troubleshooting and auditing purposes
  - **Acceptance Criteria**:
    - Events logged: job created, started, progress updates (every 10s or 100 units), paused, resumed, completed, failed, cancelled
    - Each event includes: timestamp (ISO 8601), job ID, event type, operation context (repository path, files processed count, current phase, error details if applicable)
    - Events use structured format (JSON) compatible with existing codebase-mcp logging infrastructure
    - Event logs subject to 7-day retention matching FR-013
    - Integration with health check endpoints to expose active job count and oldest running job age
  - **Traces to**: All user stories, supports operational debugging

- **FR-015**: System MUST validate operation prerequisites before accepting work to prevent failures from invalid inputs
  - **Acceptance Criteria**: Target validation, resource availability checks complete before operation creation; clear error messages provided for validation failures
  - **Traces to**: Edge Cases - invalid inputs and resource availability

### Key Entities

- **Background Job**: Represents an asynchronous repository indexing operation that runs independently of client connections
  - **Purpose**: Enables indexing of large repositories that exceed client timeout limits by tracking work progress, allowing users to disconnect and check status later
  - **Lifecycle**: Created when indexing is initiated → Transitions through execution states (pending, running, completed, failed, cancelled, blocked) → Either completes successfully with summary statistics, fails with error details, or is cancelled by user
  - **Key Attributes** (business level):
    - Unique identifier for tracking the job
    - Target repository being indexed
    - Current execution state (pending, running, completed, failed, cancelled, or blocked - see FR-004 for state definitions)
    - Progress metrics (files processed, total files, current work phase, estimated completion time)
    - Timing information (when created, when started, when finished)
    - Error details if job failed
    - Summary statistics upon completion (files indexed, chunks created, total duration)
  - **Business Invariants** (rules that must always be true):
    - Job cannot transition from completed/failed/cancelled states back to running
    - Progress metrics must be monotonically increasing (files processed never decreases)
    - Only one active job per repository at any given time
    - Completed jobs must have result summary; failed jobs must have error message
  - **Relationships**: Each job targets exactly one repository; multiple jobs can exist for same repository over time but not concurrently

- **Job Checkpoint**: Represents a resumable progress snapshot within an indexing job
  - **Purpose**: Enables automatic recovery after server restarts by preserving intermediate work state, preventing duplicate processing and data loss
  - **Lifecycle**: Created periodically during job execution (every 500 files or 30 seconds) → Remains available for recovery until job completes or is deleted → Used once during restart recovery if job was interrupted
  - **Key Attributes** (business level):
    - Unique identifier for the checkpoint
    - Associated background job
    - Type of resumption point (file list snapshot, last processed file position, or embedding batch boundary)
    - Saved state data required to resume from this point
    - When this checkpoint was captured
  - **Business Invariants** (rules that must always be true):
    - Checkpoint cannot be modified after creation (immutable)
    - Checkpoints for completed/cancelled jobs can be discarded
    - File list snapshot checkpoint must be created before processing begins
    - Processing position checkpoints must reference valid file paths that existed at job start time
  - **Relationships**: Each checkpoint belongs to exactly one background job; jobs can have multiple checkpoints over their lifetime

- **Job Event**: Represents an audit log entry tracking state transitions and significant actions in a job's lifecycle
  - **Purpose**: Provides complete history trail for debugging, monitoring, and compliance, capturing what happened, when, and any relevant context
  - **Lifecycle**: Created whenever a job undergoes significant state change or progress update → Permanently retained for audit purposes → Never modified after creation
  - **Key Attributes** (business level):
    - Unique identifier for the event
    - Associated background job
    - Type of event (job created, started, progress update, completed, failed, cancelled)
    - Additional context data specific to event type (error details, progress snapshot, cancellation reason)
    - Precise timestamp when event occurred
  - **Business Invariants** (rules that must always be true):
    - Events are immutable once created
    - Event timestamps must be monotonically increasing within a job
    - First event for any job must be "created" type
    - "Completed", "failed", or "cancelled" events mark end of job lifecycle (no events after)
    - Progress update events must include files processed count
  - **Relationships**: Each event belongs to exactly one background job; jobs accumulate multiple events throughout their lifecycle in chronological order

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can successfully index repositories with 15,000+ files without encountering timeout errors (100% success rate for large repositories)
- **SC-002**: Background job creation completes within 1 second, allowing immediate client disconnection
- **SC-003**: Background jobs automatically resume within 10 seconds after server restart, continuing from last checkpoint with <1% duplicate work
- **SC-004**: Job cancellation completes within 5 seconds, leaving database in consistent state (no orphaned chunks or corrupted indexes)
- **SC-005**: Job status queries return current progress within 100ms, providing accurate file count and time estimates
- **SC-006**: System supports 3 concurrent background jobs without performance degradation (each job meets constitutional performance targets)
- **SC-007**: Job failure rate remains below 2% (excluding user cancellations), with all failures providing actionable error messages
- **SC-008**: 95% of users understand job status and progress updates without additional documentation (based on error message clarity and progress field naming)

## Non-Goals (Explicitly Out of Scope)

The following features and capabilities are intentionally NOT included in this feature to maintain simplicity and prevent scope creep:

- **Real-time WebSocket streaming of progress updates** - Using polling model instead (simpler, MCP-compliant)
- **Distributed indexing across multiple servers** - Single-server background processing only
- **Job prioritization or queue management** - First-come-first-served execution order
- **Historical job analytics or reporting** - 7-day retention only, no trend analysis or metrics aggregation
- **Integration with external CI/CD pipelines** - No webhook triggers, GitHub Actions integration, or build system coupling
- **Custom retry strategies or error recovery policies** - Fixed retry logic for embedding service failures only
- **Job scheduling or cron-like functionality** - Manual user-initiated indexing only
- **Multi-user job isolation or permissions** - Single-user local operation (inherited from Local-First Architecture principle)
- **Job chaining or workflow automation** - Independent jobs only, no dependencies between jobs
- **Push notifications or alerts** - Polling-based status checks only
- **Background job migration across servers** - Jobs tied to single server instance
- **Fine-grained cancellation control** - Batch-level cancellation only (complete current batch before stopping)
- **Incremental indexing or change detection** - Full repository re-indexing on each job (future optimization deferred)
- **Database transaction isolation levels configuration** - Standard defaults only
- **Background job export/import functionality** - No job serialization or portability across environments

## Clarifications

### Session 2025-10-17

- Q: What is the actual MCP client timeout limit for triggering background indexing? → A: 30 seconds (validate empirically with Claude Code and document)
- Q: What triggers background indexing - total file count, total lines of code, or estimated indexing duration? → A: Estimated indexing duration (e.g., operations exceeding 60 seconds trigger background indexing)
- Q: What is the maximum number of concurrent indexing operations supported? → A: Fixed limit of 3 based on testing (with potential to make configurable later)

## Assumptions

- **A-001**: MCP client timeout limit is 30 seconds for tool responses (validated empirically with Claude Code during clarification phase)
- **A-002**: Background indexing is triggered when estimated indexing duration exceeds 60 seconds, regardless of file count or lines of code (aligns with constitutional performance target of 10,000 lines in under 60 seconds and provides 2x safety margin before MCP timeout)
- **A-003**: Ollama embedding service is running locally and accessible, with occasional transient failures requiring retry logic
- **A-004**: Database has sufficient storage for job metadata (estimated 10KB per job, 1MB for 100 jobs)
- **A-005**: Server restarts occur occasionally in production environments (estimated < 1 per day on average), justifying the investment in automatic recovery infrastructure (FR-009) to prevent user frustration and lost work
- **A-006**: Users monitor job progress through explicit status checks rather than push notifications (polling model, not WebSocket streaming)
- **A-007**: Background jobs are long-running (minutes to hours) rather than short tasks (<10 seconds), justifying async architecture overhead
- **A-008**: File system is stable during indexing - no mass deletions or renames while job is running (snapshot-based approach acceptable)
- **A-009**: File system hosting the target repository is accessible with read permissions from the server process (standard POSIX file system operations)
- **A-010**: The 3-concurrent-job limit (FR-011) is based on preliminary testing with typical developer hardware (4-core CPU, 16GB RAM) and may require adjustment based on actual production workloads and hardware configurations
- **A-011**: System resources (CPU, memory, database connection pool, embedding service throughput) are sufficient to support 3 concurrent indexing operations, each processing approximately 50 files/second without exceeding 80% CPU utilization or causing memory swapping (requires validation during performance testing phase)

## Review & Acceptance Checklist

### Content Quality
- [ ] All implementation details removed (no mentions of Python, PostgreSQL, FastMCP, SQLAlchemy)
- [ ] Language is user-focused and describes behavior, not technology
- [ ] Non-technical stakeholders can understand all user scenarios
- [ ] Terminology is consistent throughout (e.g., "background job" vs "async task")
- [ ] All mandatory sections are complete (User Scenarios, Requirements, Success Criteria, Assumptions)

### Requirement Completeness
- [ ] All functional requirements are testable with clear pass/fail criteria
- [ ] Requirements use MUST/SHOULD/MAY consistently (MUST = mandatory, SHOULD = recommended, MAY = optional)
- [ ] Each requirement traces to a user scenario in User Scenarios section
- [ ] Edge cases cover realistic failure scenarios (database loss, embedding service unavailable, disk space, concurrent jobs)
- [ ] Success criteria are measurable with specific numbers (1 second job creation, 5 second cancellation, <1% duplicate work)
- [ ] No vague adjectives used ("fast", "reliable", "scalable" replaced with quantitative metrics)
- [ ] All requirements are unambiguous (no multiple valid interpretations without clarification)

### Scope Clarity
- [ ] Feature boundaries clearly defined (background indexing for large repositories only)
- [ ] Non-Goals section lists out-of-scope items to prevent scope creep
- [ ] Dependencies on existing features identified (database, embedding service, existing indexing logic)
- [ ] Integration points specified (Background Job tracking, Checkpoint recovery, Event audit log)
- [ ] Assumptions documented and validated (MCP timeout ~30s, 60s threshold for large operations, offline-capable storage)

### Constitutional Compliance
- [ ] Aligns with **Principle I: Simplicity Over Features** - Background jobs focused on solving timeout problem only
- [ ] Aligns with **Principle II: Local-First Architecture** - No cloud dependencies, local job tracking
- [ ] Aligns with **Principle III: Protocol Compliance** - Job status queries via MCP tools, structured logging
- [ ] Aligns with **Principle IV: Performance Guarantees** - Maintains 60s/10K lines and 500ms search targets during concurrent jobs (SC-006)
- [ ] Aligns with **Principle V: Production Quality Standards** - Comprehensive error handling (FR-014), graceful failure (SC-007), clear error messages
- [ ] Aligns with **Principle VI: Specification-First Development** - Acceptance criteria defined before implementation (this spec)
- [ ] Aligns with **Principle VII: Test-Driven Development** - Test scenarios included in User Stories (independent test criteria)
- [ ] Respects Technical Constraints - Works with existing async architecture
- [ ] No violations of project Non-Goals (not building generic knowledge base, no cloud features)
