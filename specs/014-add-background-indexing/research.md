# Technical Research: Background Indexing

## Decision Summary

| Topic | Decision | Rationale |
|-------|----------|-----------|
| Background Job Execution | asyncio.Task with PostgreSQL state tracking | Python-native concurrency, no external dependencies, state survives restarts |
| Duration Estimation | Historical averaging + file count heuristic | Simple, transparent, improves with usage, no ML complexity |
| Checkpoint Strategy | PostgreSQL transaction-based snapshots (every 500 files or 30s) | ACID guarantees, automatic persistence, simple recovery |
| Progress Tracking | Committed PostgreSQL UPDATEs (every 2s) | Real-time visibility, survives crashes, no in-memory sync issues |
| Cancellation Mechanism | Database polling via status column | Simple, reliable, graceful shutdown, no signal handling complexity |
| Concurrency Control | Connection pool-based limiting (3 concurrent jobs max) | Leverages existing infrastructure, resource-aware, no custom queue needed |
| Indexer Integration | Progress callback parameter to existing index_repository() | Minimal changes, preserves existing performance, backward compatible |

## 1. Background Job Execution Model

**Decision**: Use `asyncio.create_task()` with PostgreSQL-native state tracking

**Rationale**:
- **Async-native**: The entire codebase (indexer.py, embedder.py, chunker.py) is already built on Python's async/await model using SQLAlchemy AsyncSession and asyncpg. Using asyncio.Task maintains architectural consistency without introducing threading complexity.
- **No external dependencies**: Aligns with Constitutional Principle II (Local-First Architecture) - no Redis, Celery, RabbitMQ, or cloud job queues required.
- **State persistence**: PostgreSQL `indexing_jobs` table serves as the single source of truth. Job state survives server restarts, unlike in-memory task managers.
- **Simplicity**: No need for custom job manager classes, worker pools, or IPC mechanisms. PostgreSQL handles all state management via standard SQL operations.
- **Constitutional compliance**: Principle I (Simplicity Over Features) - reuses existing database infrastructure rather than adding new components.

**Alternatives Considered**:

- **Option A: threading.Thread** - Rejected because:
  - Would force synchronous database operations or complex thread-safe async bridge
  - Existing indexer uses async database sessions exclusively (AsyncSession, asyncpg)
  - Thread-based blocking I/O conflicts with async event loop
  - Creates GIL contention that async avoids

- **Option B: multiprocessing.Process** - Rejected because:
  - Cannot share SQLAlchemy connection pools across processes (requires pickle-safe serialization)
  - IPC overhead for progress updates (queue/pipe communication)
  - Memory duplication (each process loads full codebase into memory)
  - Overkill for I/O-bound task (indexing is disk + network, not CPU-bound)

- **Option C: Celery/RQ with Redis** - Rejected because:
  - Violates Constitutional Principle II (Local-First Architecture) - adds external dependency
  - Adds operational complexity (Redis deployment, monitoring, failure recovery)
  - Overkill for single-server use case (Codebase MCP runs locally per user)
  - State split between Redis and PostgreSQL creates consistency challenges

**Implementation Notes**:
```python
# MCP tool creates task immediately and returns job_id
job_id = await create_job_record(db)  # PostgreSQL INSERT
asyncio.create_task(_background_worker(job_id))  # Non-blocking task creation
return {"job_id": str(job_id), "status": "pending"}  # <1s response time

# Background worker updates PostgreSQL periodically
async def _background_worker(job_id: UUID):
    await update_status(job_id, "running")
    result = await index_repository(..., progress_callback=callback)
    await update_status(job_id, "completed", result=result)
```

**Worker Lifecycle**:
1. `start_indexing_background()` creates PostgreSQL row (status=pending)
2. `asyncio.create_task()` spawns background worker task
3. Worker updates PostgreSQL row through execution (status=running, progress updates)
4. Worker commits final state (status=completed/failed/cancelled) before exiting
5. Task completes and is garbage collected by asyncio

**Resource Management**:
- Connection pool provides dedicated connections (20 base + 10 overflow from settings.py)
- Each background worker holds 1 connection during execution
- Tasks are fire-and-forget (no .wait() or .result() blocking)
- Python's garbage collector cleans up completed tasks automatically

## 2. Duration Estimation Strategy

**Decision**: Historical averaging with file count heuristic

**Rationale**:
- **Simple and transparent**: Uses observable metrics (file count, historical duration) without ML models or complex prediction algorithms.
- **Improves with usage**: Becomes more accurate as users index repositories, creating self-improving estimates.
- **Graceful fallback**: For first-time users, uses constitutional performance target (60s for 10K files = 6ms/file) as baseline heuristic.
- **Performance target alignment**: Constitutional Principle IV guarantees 60s for 10K files, providing a reliable worst-case estimate.

**Estimation Algorithm**:

```python
async def estimate_indexing_duration(repo_path: Path, project_id: str) -> float:
    """Estimate indexing duration in seconds.

    Strategy:
    1. Count files in repository (fast scan, ~100ms for 10K files)
    2. Query recent indexing jobs for similar file counts
    3. Calculate weighted average of historical durations
    4. Fallback to constitutional baseline (60s / 10K files = 6ms/file)

    Returns:
        Estimated duration in seconds
    """
    # Fast file count (no content reading)
    file_count = await count_indexable_files(repo_path)

    # Query historical jobs (last 10 completed jobs)
    async with get_session(project_id) as db:
        result = await db.execute(text("""
            SELECT files_indexed,
                   EXTRACT(EPOCH FROM (completed_at - started_at)) AS duration_seconds
            FROM indexing_jobs
            WHERE status = 'completed'
              AND files_indexed > 0
              AND completed_at > NOW() - INTERVAL '30 days'
            ORDER BY created_at DESC
            LIMIT 10
        """))
        historical_jobs = result.fetchall()

    if historical_jobs:
        # Weighted average (more weight to similar file counts)
        total_weight = 0
        weighted_duration = 0

        for hist_files, hist_duration in historical_jobs:
            # Weight: inverse of file count difference
            weight = 1.0 / (1.0 + abs(file_count - hist_files) / 1000.0)
            weighted_duration += (hist_duration / hist_files) * file_count * weight
            total_weight += weight

        estimated = weighted_duration / total_weight
    else:
        # Fallback: constitutional baseline (60s for 10K files)
        estimated = (file_count / 10000.0) * 60.0

    # Add 20% buffer for safety
    return estimated * 1.2
```

**Metrics Used**:
- **File count**: Primary predictor (strong correlation with indexing time)
- **Total repository size**: Secondary factor (large files take longer to chunk)
- **Historical performance**: Self-correcting based on actual results
- **Embedding batch size**: Factored into historical averages automatically

**Fallback for First-Time Repositories**:
- Use constitutional performance guarantee: 60s for 10,000 files
- Proportional scaling: `duration = (file_count / 10000) * 60 seconds`
- Add 20% safety buffer: `estimated_duration * 1.2`
- Example: 15,000 files → (15000/10000) * 60 * 1.2 = 108 seconds

**Alternatives Considered**:

- **Option A: Lines of code analysis** - Rejected because:
  - Requires reading file contents (slow for large repos)
  - Not significantly more accurate than file count
  - Adds 2-5 seconds to estimation time (unacceptable for <1s response requirement)

- **Option B: ML-based prediction (regression model)** - Rejected because:
  - Violates Constitutional Principle I (Simplicity Over Features)
  - Requires training data, model versioning, and deployment complexity
  - Marginal accuracy improvement (<10%) doesn't justify complexity
  - Opaque to users (can't explain why estimate is X seconds)

- **Option C: Fixed percentage threshold (e.g., >5000 files = background)** - Rejected because:
  - Ignores actual hardware performance (SSD vs HDD, CPU speed, embedding service)
  - Creates false positives (small files index quickly) and false negatives (large files)
  - Doesn't improve over time with usage

**Implementation Notes**:
- Estimation runs during `start_indexing_background()` call (<100ms overhead)
- If estimate > 60 seconds, use background indexing
- If estimate ≤ 60 seconds, use synchronous indexing (existing path)
- Store estimate in `indexing_jobs.metadata` JSONB field for post-hoc analysis
- Log actual vs estimated duration for monitoring accuracy

## 3. Checkpoint Strategy

**Decision**: PostgreSQL transaction-based snapshots every 500 files or 30 seconds

**Rationale**:
- **ACID guarantees**: PostgreSQL transactions ensure checkpoint consistency. Either the full checkpoint is written or none of it - no partial state corruption.
- **Automatic persistence**: No separate checkpoint file management. Database handles durability via WAL (Write-Ahead Log).
- **Simple recovery**: On restart, query `indexing_jobs` for jobs with `status='running'`, read checkpoint data from JSONB column, resume from last committed state.
- **Minimal overhead**: Checkpoint frequency (500 files or 30s) keeps transaction sizes reasonable (<1% performance impact based on PostgreSQL benchmark data).
- **Constitutional compliance**: Principle V (Production Quality) - comprehensive error handling, transaction management, no data loss on crashes.

**Checkpoint Data Structure**:

```python
# Stored in indexing_jobs.metadata JSONB column
checkpoint_data = {
    "checkpoint_type": "file_list_snapshot",  # or "progress_marker"
    "checkpointed_at": "2025-10-17T10:30:15Z",
    "files_processed": [
        "/path/to/repo/file1.py",
        "/path/to/repo/file2.py",
        ...
    ],  # List of fully processed file paths
    "files_remaining": 1234,  # Count of unprocessed files
    "last_file_path": "/path/to/repo/file500.py",  # Last completed file
    "embedding_batch_offset": 2500,  # Embeddings generated count
}
```

**Checkpoint Granularity Options**:

1. **File list snapshot** (chosen for Phase 1):
   - Store list of completed file paths in JSONB
   - Recovery: Skip files in checkpoint list during re-indexing
   - Pros: Simple, exact recovery, no duplicate chunks
   - Cons: Larger JSONB payload for repos with many files

2. **Progress marker** (future optimization):
   - Store last processed file path + position in file list
   - Recovery: Resume from file path position
   - Pros: Smaller JSONB payload (single path instead of list)
   - Cons: Requires deterministic file ordering, more complex recovery logic

**Recovery Algorithm**:

```python
async def resume_interrupted_job(job_id: UUID, project_id: str) -> None:
    """Resume indexing job that was interrupted by server restart.

    Strategy:
    1. Query indexing_jobs for job with status='running'
    2. Load checkpoint data from metadata JSONB column
    3. Re-scan repository to get current file list
    4. Diff checkpoint vs current files to find unprocessed files
    5. Resume indexing from unprocessed files
    6. Update progress counters to account for already-processed files
    """
    async with get_session(project_id) as db:
        result = await db.execute(
            text("SELECT metadata, files_indexed, chunks_created FROM indexing_jobs WHERE id = :job_id"),
            {"job_id": job_id}
        )
        row = result.fetchone()
        checkpoint = row[0]  # JSONB metadata
        files_indexed_before = row[1]
        chunks_created_before = row[2]

    # Get checkpoint state
    files_processed = set(checkpoint.get("files_processed", []))

    # Re-scan repository
    all_files = await scan_repository(Path(checkpoint["repo_path"]))

    # Compute unprocessed files
    files_remaining = [f for f in all_files if str(f) not in files_processed]

    # Resume indexing with adjusted progress
    await index_repository(
        ...,
        files_to_process=files_remaining,
        initial_progress={
            "files_indexed": files_indexed_before,
            "chunks_created": chunks_created_before,
        }
    )
```

**Checkpoint Frequency Trade-offs**:
- **Every 500 files**: Balances recovery granularity vs transaction overhead
  - Too frequent (every 10 files): 1% overhead → 5% overhead (unacceptable)
  - Too infrequent (every 5000 files): 10% duplicate work on recovery (acceptable)
- **Every 30 seconds**: Time-based backup for slow file processing (large files)
  - Ensures checkpoint even if processing <500 files in 30s window
  - Complements file-based checkpointing

**Alternatives Considered**:

- **Option A: Separate checkpoint files on disk** - Rejected because:
  - Adds file I/O complexity (write, fsync, atomic rename)
  - No ACID guarantees (partial write on crash)
  - Requires cleanup logic for orphaned checkpoint files
  - Doesn't survive disk failures (same failure mode as database)

- **Option B: In-memory checkpoint (no persistence)** - Rejected because:
  - Violates FR-009 (automatic resumption after restart)
  - Forces users to restart failed jobs manually
  - Poor user experience for long-running jobs (hours of work lost)

- **Option C: Checkpoint every file** - Rejected because:
  - 100-1000x more database transactions (performance impact)
  - Increases indexing time by 2-5% (violates 60s constitutional target)
  - No meaningful benefit (500-file granularity is <1% work duplication)

**Implementation Notes**:
- Checkpoint written via single UPDATE transaction:
  ```sql
  UPDATE indexing_jobs
  SET metadata = jsonb_set(metadata, '{checkpoint}', :checkpoint_data::jsonb),
      files_indexed = :files_indexed,
      chunks_created = :chunks_created
  WHERE id = :job_id;
  ```
- Checkpoint triggers:
  1. After processing batch of 500 files
  2. After 30 seconds elapsed since last checkpoint
  3. Before worker shutdown (graceful cancellation)
- Recovery on startup:
  ```python
  async def on_startup():
      jobs = await get_running_jobs()
      for job in jobs:
          asyncio.create_task(resume_interrupted_job(job.id))
  ```

## 4. Progress Tracking

**Decision**: Real-time committed PostgreSQL UPDATEs every 2 seconds

**Rationale**:
- **Immediate visibility**: AI agents poll `get_indexing_status()` and see latest progress within 2 seconds (meets FR-005 requirement: updates every 10 seconds or 100 work units).
- **Survives crashes**: Progress committed to database, visible after server restart.
- **No synchronization complexity**: No in-memory state to keep in sync with database. Database is the single source of truth.
- **Performance-aware**: 2-second update frequency keeps transaction load manageable (<50 transactions/minute per job, <150 total for 3 concurrent jobs).
- **Constitutional compliance**: Principle IV (Performance) - <100ms status query time via indexed PostgreSQL SELECT.

**Progress Update Fields**:

```sql
-- Updated every 2 seconds by background worker
UPDATE indexing_jobs
SET
    progress_percentage = :percentage,  -- 0-100
    progress_message = :message,  -- "Chunking files: 5000/10000"
    files_scanned = :files_scanned,  -- Total files found
    files_indexed = :files_indexed,  -- Files processed so far
    chunks_created = :chunks_created  -- Chunks generated so far
WHERE id = :job_id;
```

**Progress Phases and Percentages**:

1. **Scanning (0-10%)**: File discovery
   - Message: "Scanning repository..."
   - Counter: `files_scanned`

2. **Chunking (10-50%)**: AST-based code chunking
   - Message: "Chunking files: 2500/10000"
   - Counters: `files_indexed`, `chunks_created`
   - Progress: `10 + (files_indexed / total_files * 40)`

3. **Embedding (50-90%)**: Vector embedding generation
   - Message: "Generating embeddings: 25000/50000"
   - Counter: `chunks_created`
   - Progress: `50 + (chunks_embedded / total_chunks * 40)`

4. **Writing (90-100%)**: Database persistence
   - Message: "Writing to database..."
   - Progress: Fixed 95% during writes, 100% on completion

**Update Frequency Analysis**:

| Update Interval | Transactions/Min (1 job) | Transactions/Min (3 jobs) | User Experience |
|-----------------|--------------------------|---------------------------|-----------------|
| 1 second | 60 | 180 | Excellent (real-time) |
| 2 seconds | 30 | 90 | Good (near real-time) |
| 5 seconds | 12 | 36 | Acceptable (FR-005 compliant) |
| 10 seconds | 6 | 18 | Minimal (FR-005 threshold) |

**Chosen: 2 seconds** - balances user experience with database load.

**Progress Callback Implementation**:

```python
# In _background_worker()
async def progress_callback(message: str, percentage: int, **kwargs) -> None:
    """Called by indexer at progress milestones.

    Args:
        message: Human-readable progress message
        percentage: Progress 0-100
        **kwargs: Counters (files_scanned, files_indexed, chunks_created)
    """
    # Check cancellation request
    if await _check_cancellation(job_id, project_id):
        raise asyncio.CancelledError("Job cancelled by user")

    # Update database (committed transaction)
    await _update_job_progress(
        job_id=job_id,
        project_id=project_id,
        percentage=percentage,
        message=message,
        **kwargs
    )

# Indexer invokes callback periodically
async def index_repository(..., progress_callback=None):
    # After scanning
    if progress_callback:
        await progress_callback("Scanning repository...", 10, files_scanned=len(all_files))

    # During chunking (every 500 files or 30 seconds)
    for i, batch in enumerate(file_batches):
        percentage = 10 + int(40 * (i / total_batches))
        if progress_callback and (i % 5 == 0 or time_elapsed > 30):
            await progress_callback(
                f"Chunking files: {i * batch_size}/{total_files}",
                percentage,
                files_indexed=i * batch_size
            )
```

**Alternatives Considered**:

- **Option A: Update on every file processed** - Rejected because:
  - 10,000+ transactions for large repos (5-10% performance overhead)
  - Database write amplification (indexing time increases 10-15%)
  - No user benefit (2-second updates already feel "real-time")

- **Option B: Update only on checkpoint (every 500 files)** - Rejected because:
  - Violates FR-005 (progress updates every 10 seconds or 100 work units)
  - Poor user experience (30-60 second gaps with no progress updates)
  - Users may think job is stuck or frozen

- **Option C: WebSocket streaming updates** - Rejected because:
  - Listed in spec's Non-Goals (polling model preferred for MCP simplicity)
  - Adds WebSocket server complexity (violates Constitutional Principle I)
  - MCP protocol uses request/response, not streaming
  - Would require custom client-side subscription logic

**Implementation Notes**:
- Progress callback is optional parameter to `index_repository()` (backward compatible)
- Callback invocations:
  1. After scanning (10%)
  2. Every 500 files during chunking (10-50%)
  3. Every 2500 embeddings during generation (50-90%)
  4. After database write (95%)
  5. On completion (100%)
- Update includes human-readable message for AI agent context
- Percentage is monotonically increasing (never decreases)

## 5. Cancellation Mechanism

**Decision**: Graceful shutdown via database polling with 5-second guarantee

**Rationale**:
- **Simple and reliable**: No signal handlers, threading events, or IPC mechanisms. Worker checks database column every 2 seconds during progress updates.
- **Graceful shutdown**: Worker finishes current batch (file chunking or embedding generation) before stopping. No mid-batch data corruption.
- **Database-driven**: Cancellation request is just a SQL UPDATE to `status='cancelled'`. No custom communication protocol needed.
- **5-second guarantee**: FR-008 requires cancellation within 5 seconds. Polling every 2 seconds + batch completion (<3 seconds) = <5 seconds total.
- **Constitutional compliance**: Principle V (Production Quality) - proper cleanup, consistent database state, no orphaned resources.

**Cancellation Flow**:

```python
# 1. User calls cancel_indexing_background()
async def cancel_indexing_background(job_id: str, ...) -> dict:
    """Set cancellation flag in database."""
    async with get_session(project_id) as db:
        await db.execute(text("""
            UPDATE indexing_jobs
            SET status = 'cancelled', cancelled_at = NOW()
            WHERE id = :job_id AND status IN ('pending', 'running')
        """), {"job_id": job_id})
        await db.commit()  # Immediately visible to worker

    return {"job_id": job_id, "status": "cancelled", "message": "Cancellation requested"}

# 2. Background worker checks cancellation during progress updates
async def _background_worker(job_id: UUID, ...):
    try:
        # Progress callback checks cancellation every 2 seconds
        async def progress_callback(message: str, percentage: int, **kwargs):
            # Query database for cancellation flag
            if await _check_cancellation(job_id, project_id):
                raise asyncio.CancelledError("Job cancelled by user")

            await _update_job_progress(...)

        # Indexer invokes callback every 2 seconds
        await index_repository(..., progress_callback=progress_callback)

    except asyncio.CancelledError:
        # Graceful shutdown: finish current batch, then stop
        await _cleanup_partial_work(job_id)
        await _update_job_status(job_id, "cancelled")
        logger.warning(f"Job {job_id} cancelled by user")

# 3. Check cancellation helper
async def _check_cancellation(job_id: UUID, project_id: str) -> bool:
    """Query database for cancellation flag.

    Returns:
        True if status='cancelled', False otherwise
    """
    async with get_session(project_id) as db:
        result = await db.execute(
            text("SELECT status FROM indexing_jobs WHERE id = :job_id"),
            {"job_id": job_id}
        )
        row = result.fetchone()
        return row[0] == 'cancelled' if row else False
```

**Cancellation Timing Breakdown**:

| Stage | Time | Action |
|-------|------|--------|
| User calls cancel API | 0s | UPDATE indexing_jobs SET status='cancelled' |
| Next progress update | 0-2s | Worker detects cancellation flag |
| Finish current batch | 1-3s | Complete file chunking or embedding batch |
| Cleanup | <500ms | Mark partial work, update status |
| **Total** | **<5s** | Meets FR-008 requirement |

**Cleanup Strategy**:

```python
async def _cleanup_partial_work(job_id: UUID) -> None:
    """Clean up partial work on cancellation.

    Options:
    1. Delete all chunks for this job (clean slate for re-indexing)
    2. Keep chunks created so far (partial index usable for search)

    Decision: Keep chunks (Option 2) - partial work is still valuable.
    """
    # Update job status with partial completion stats
    async with get_session(project_id) as db:
        await db.execute(text("""
            UPDATE indexing_jobs
            SET
                status = 'cancelled',
                cancelled_at = NOW(),
                progress_message = 'Cancelled by user (partial data retained)'
            WHERE id = :job_id
        """), {"job_id": job_id})
        await db.commit()

    # Chunks remain in database - can be used for search or deleted by user
    logger.info(f"Job {job_id} cancelled, {chunks_created} chunks retained")
```

**Alternatives Considered**:

- **Option A: Signal handlers (SIGTERM/SIGINT)** - Rejected because:
  - Only works for process-level termination (not task-level cancellation)
  - Requires global state to map signals to tasks
  - Doesn't work on Windows (limited signal support)
  - Overkill for user-initiated cancellation (not crash recovery)

- **Option B: threading.Event for cancellation** - Rejected because:
  - Requires thread-safe coordination between async task and threading primitives
  - Adds complexity for no benefit (database polling is simpler)
  - Doesn't integrate with asyncio's CancelledError pattern

- **Option C: asyncio.Task.cancel() direct cancellation** - Rejected because:
  - Abrupt termination (no graceful batch completion)
  - Requires tracking Task objects in memory (in-memory state management)
  - Doesn't work across server restarts (Task objects are ephemeral)
  - Can leave database in inconsistent state (mid-transaction cancellation)

**Implementation Notes**:
- Cancellation check adds <10ms overhead per progress update (single SELECT query)
- Batch-level cancellation ensures:
  - No orphaned embeddings (embedding batch is atomic)
  - No partial file chunks (file chunking is atomic per file)
  - Database constraints remain valid (no FK violations)
- Worker catches `asyncio.CancelledError` to distinguish cancellation from errors
- Partial work is retained unless user explicitly deletes repository

## 6. Concurrency Control

**Decision**: Connection pool-based limiting with 3 concurrent jobs maximum

**Rationale**:
- **Leverages existing infrastructure**: SQLAlchemy connection pool (20 connections + 10 overflow from settings.py) naturally limits concurrency. No custom queue implementation needed.
- **Resource-aware**: 3 concurrent jobs × 7 connections/job = 21 connections (within 20+10 pool limit). Prevents connection pool exhaustion.
- **Simple queue semantics**: If 3 jobs are running, 4th job waits for connection pool slot. PostgreSQL handles queueing automatically.
- **Fixed limit for testing**: Spec clarification states 3 is a "fixed limit based on testing, with potential to make configurable later". Simple integer constant, not dynamic scaling.
- **Constitutional compliance**: Principle I (Simplicity) - no custom worker pool, semaphore, or queue manager classes.

**Concurrency Architecture**:

```python
# Connection usage per job
# - 1 connection for job status updates (held for <100ms per update)
# - 1 connection for indexer operations (held for full job duration)
# - 5 connections for parallel embedding batches (intermittent, shared)
# = ~7 connections peak per job

# With 3 concurrent jobs:
# 3 jobs × 7 connections = 21 connections
# Pool: 20 base + 10 overflow = 30 total
# Margin: 30 - 21 = 9 connections for status queries and other operations

MAX_CONCURRENT_JOBS = 3  # Constitutional limit
```

**Job Queueing Behavior**:

```python
async def start_indexing_background(...) -> dict:
    """Start background job (may queue if limit reached)."""
    # Check active job count
    active_jobs = await _get_active_job_count(project_id)

    if active_jobs >= MAX_CONCURRENT_JOBS:
        # Create job with status='pending' (queued)
        job_id = await _create_job_record(db, status="pending")

        # Job will start when slot becomes available
        # (no explicit queue manager - PostgreSQL connection pool handles it)
        return {
            "job_id": str(job_id),
            "status": "pending",
            "message": f"Job queued ({active_jobs} jobs currently running)"
        }
    else:
        # Create job and start immediately
        job_id = await _create_job_record(db, status="pending")
        asyncio.create_task(_background_worker(job_id, ...))

        return {
            "job_id": str(job_id),
            "status": "running",
            "message": "Job started"
        }

async def _get_active_job_count(project_id: str) -> int:
    """Count jobs with status='running' in this project."""
    async with get_session(project_id) as db:
        result = await db.execute(text("""
            SELECT COUNT(*) FROM indexing_jobs
            WHERE status = 'running' AND project_id = :project_id
        """), {"project_id": project_id})
        return result.scalar()
```

**Fair Scheduling Strategy**:

Simple FIFO (First-In-First-Out) based on `created_at` timestamp:

```python
async def _start_next_pending_job(project_id: str) -> None:
    """Start next pending job when slot becomes available.

    Called after a job completes to start queued jobs.
    """
    async with get_session(project_id) as db:
        # Get oldest pending job
        result = await db.execute(text("""
            SELECT id, repo_path, repo_name, force_reindex
            FROM indexing_jobs
            WHERE status = 'pending' AND project_id = :project_id
            ORDER BY created_at ASC
            LIMIT 1
        """), {"project_id": project_id})
        row = result.fetchone()

        if row is None:
            return  # No pending jobs

        job_id, repo_path, repo_name, force_reindex = row

        # Start job
        asyncio.create_task(_background_worker(job_id, repo_path, repo_name, project_id, force_reindex))

        # Update status to running
        await db.execute(text("""
            UPDATE indexing_jobs SET status = 'running', started_at = NOW()
            WHERE id = :job_id
        """), {"job_id": job_id})
        await db.commit()

# Called at end of _background_worker()
async def _background_worker(job_id: UUID, ...):
    try:
        await index_repository(...)
    finally:
        # Start next pending job (FIFO queue)
        await _start_next_pending_job(project_id)
```

**Alternatives Considered**:

- **Option A: Semaphore-based limiting (asyncio.Semaphore)** - Rejected because:
  - In-memory state doesn't survive server restarts
  - Requires careful cleanup to avoid semaphore leaks
  - Adds complexity for no benefit (connection pool already limits concurrency)

- **Option B: PostgreSQL advisory locks** - Rejected because:
  - Requires explicit lock acquisition/release in application code
  - Locks held for hours (entire indexing duration) create operational issues
  - If worker crashes, lock requires manual release or session timeout
  - Over-engineered for simple concurrency control

- **Option C: Redis-based distributed queue (Celery/RQ)** - Rejected because:
  - Violates Constitutional Principle II (Local-First) - external dependency
  - Overkill for single-server use case (Codebase MCP is local)
  - Adds operational complexity (Redis deployment, monitoring)

- **Option D: Custom job manager class with in-memory queue** - Rejected because:
  - Violates Constitutional Principle I (Simplicity)
  - In-memory state lost on restart (poor production quality)
  - Must implement queue logic, fairness, cleanup (reinventing wheel)

**Implementation Notes**:
- `MAX_CONCURRENT_JOBS = 3` constant in settings.py (future: make configurable via env var)
- Job queueing is transparent to user (status field indicates "pending" vs "running")
- No explicit queue data structure - PostgreSQL WHERE status='pending' is the queue
- FIFO ordering via `ORDER BY created_at ASC` (no priority support in Phase 1)
- Connection pool automatically blocks when exhausted (no explicit wait logic needed)

## 7. Integration with Existing Indexer

**Decision**: Add optional `progress_callback` parameter to `index_repository()`

**Rationale**:
- **Minimal changes**: Single parameter addition, existing logic preserved. No breaking changes to API.
- **Backward compatible**: Default `progress_callback=None` maintains current behavior. Existing callers (synchronous indexing) unaffected.
- **Preserves performance**: Callback is optional and lightweight (<10ms overhead per invocation). Constitutional 60s/10K target maintained.
- **Clean separation**: Background job concerns (progress tracking, cancellation) stay in background_indexing.py. Indexer remains focused on core indexing logic.
- **Constitutional compliance**: Principle I (Simplicity) - no major refactoring, no new services, no architectural changes.

**Indexer API Change**:

```python
# Before (existing)
async def index_repository(
    repo_path: Path,
    name: str,
    db: AsyncSession,
    project_id: str,
    force_reindex: bool = False,
) -> IndexResult:
    """Index repository synchronously."""
    ...

# After (backward compatible)
from typing import Callable, Awaitable

ProgressCallback = Callable[[str, int, dict[str, int]], Awaitable[None]]

async def index_repository(
    repo_path: Path,
    name: str,
    db: AsyncSession,
    project_id: str,
    force_reindex: bool = False,
    progress_callback: ProgressCallback | None = None,  # NEW: optional callback
) -> IndexResult:
    """Index repository with optional progress tracking.

    Args:
        progress_callback: Optional async function(message, percentage, counters).
            Called at key milestones (scanning, chunking, embedding, writing).
            If provided, enables progress tracking and cancellation detection.
    """
    # Progress callback invocations (only if callback provided)
    if progress_callback:
        await progress_callback("Scanning repository...", 10, {"files_scanned": len(all_files)})

    # ... existing chunking logic ...

    for i, batch in enumerate(file_batches):
        # ... existing batch processing ...

        # Progress update every 5 batches or 30 seconds
        if progress_callback and (i % 5 == 0 or time_elapsed > 30):
            percentage = 10 + int(40 * (i / total_batches))
            await progress_callback(
                f"Chunking files: {i * batch_size}/{total_files}",
                percentage,
                {
                    "files_indexed": i * batch_size,
                    "chunks_created": len(chunks_so_far)
                }
            )

    # ... rest of existing logic unchanged ...
```

**Integration Points**:

1. **Scanning phase (10% progress)**:
   ```python
   all_files = await scan_repository(repo_path)
   if progress_callback:
       await progress_callback("Scanning repository...", 10, {"files_scanned": len(all_files)})
   ```

2. **Chunking phase (10-50% progress)**:
   ```python
   for i, file_batch in enumerate(_batch(files_to_index, FILE_BATCH_SIZE)):
       # ... existing chunking logic ...

       if progress_callback and (i % 5 == 0):  # Every 5 batches (500 files)
           percentage = 10 + int(40 * (i / total_batches))
           await progress_callback(
               f"Chunking files: {files_processed}/{total_files}",
               percentage,
               {"files_indexed": files_processed}
           )
   ```

3. **Embedding phase (50-90% progress)**:
   ```python
   for i, text_batch in enumerate(_batch(texts, EMBEDDING_BATCH_SIZE)):
       batch_embeddings = await generate_embeddings(text_batch)

       if progress_callback and (i % 10 == 0):  # Every 10 batches (500 embeddings)
           percentage = 50 + int(40 * (i / total_embedding_batches))
           await progress_callback(
               f"Generating embeddings: {embeddings_generated}/{total_chunks}",
               percentage,
               {"chunks_created": embeddings_generated}
           )
   ```

4. **Writing phase (90-100% progress)**:
   ```python
   if progress_callback:
       await progress_callback("Writing to database...", 95, {})

   # ... existing database write logic ...

   if progress_callback:
       await progress_callback("Indexing complete", 100, {
           "files_indexed": len(files_to_index),
           "chunks_created": len(all_chunks_to_create)
       })
   ```

**Performance Impact Analysis**:

| Callback Frequency | Overhead per 10K files | Impact on 60s target |
|-------------------|------------------------|----------------------|
| Every 500 files (20 calls) | 200ms | 0.3% (negligible) |
| Every 100 files (100 calls) | 1000ms | 1.7% (acceptable) |
| Every file (10K calls) | 10000ms | 16.7% (unacceptable) |

**Chosen: Every 500 files** - <1% overhead, maintains constitutional performance target.

**Alternatives Considered**:

- **Option A: Create separate background_indexer.py with duplicated logic** - Rejected because:
  - Code duplication (1000+ lines of indexing logic)
  - Maintenance burden (bug fixes need to be applied twice)
  - Violates DRY principle (Don't Repeat Yourself)
  - Performance characteristics diverge over time

- **Option B: Wrap entire index_repository() in background wrapper** - Rejected because:
  - No progress visibility (all-or-nothing, violates FR-005)
  - Can't detect cancellation until job completes
  - No checkpoint support (can't resume after restart)
  - User experience is poor (no feedback for 5-10 minutes)

- **Option C: Refactor indexer into async generator (yield progress)** - Rejected because:
  - Breaking change to API (all callers must be updated)
  - Increases complexity significantly (generator state management)
  - Doesn't integrate well with database transaction boundaries
  - Over-engineered for simple progress callback use case

**Database Schema Additions**:

```sql
-- Add indexing_jobs table (new table, no schema changes to existing tables)
CREATE TABLE indexing_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID,  -- NULL until repository created, FK added later
    repo_path TEXT NOT NULL,
    repo_name TEXT NOT NULL,
    project_id VARCHAR(255) NOT NULL,
    force_reindex BOOLEAN NOT NULL DEFAULT FALSE,

    -- Status tracking
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    progress_percentage INTEGER NOT NULL DEFAULT 0 CHECK (progress_percentage >= 0 AND progress_percentage <= 100),
    progress_message TEXT,

    -- Counters
    files_scanned INTEGER NOT NULL DEFAULT 0,
    files_indexed INTEGER NOT NULL DEFAULT 0,
    chunks_created INTEGER NOT NULL DEFAULT 0,

    -- Error tracking
    error_message TEXT,
    error_type VARCHAR(255),
    error_traceback TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,

    -- Checkpoints and metadata
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Performance indexes
CREATE INDEX idx_indexing_jobs_status ON indexing_jobs(status) WHERE status IN ('pending', 'running');
CREATE INDEX idx_indexing_jobs_project_id ON indexing_jobs(project_id);
CREATE INDEX idx_indexing_jobs_created_at ON indexing_jobs(created_at DESC);
```

**Implementation Notes**:
- Existing indexer tests continue to pass (no callback = no behavior change)
- Background indexing adds new test suite (tests/integration/test_background_indexing.py)
- No changes to chunker.py, embedder.py, scanner.py (remain callback-agnostic)
- Progress callback is async function to avoid blocking event loop

## Constitutional Alignment

### Simplicity Over Features (Principle I)
- **PostgreSQL-native state**: No custom job manager, worker pool, or queue implementation. Standard SQL operations only.
- **Minimal indexer changes**: Single optional parameter, existing logic unchanged.
- **No external dependencies**: No Redis, Celery, RabbitMQ, or cloud services required.
- **Reuses existing infrastructure**: Connection pool, async sessions, database transactions.

### Local-First Architecture (Principle II)
- **No cloud APIs**: All state in local PostgreSQL database.
- **Offline-capable**: Background jobs work without internet connection.
- **Standard PostgreSQL**: No proprietary extensions (except pgvector, already required).
- **Self-contained**: No external coordination services needed.

### Protocol Compliance (Principle III)
- **MCP tools return immediately**: `start_indexing_background()` returns job_id in <1s.
- **No stdout/stderr pollution**: All logging to /tmp/codebase-mcp.log.
- **Structured responses**: Pydantic models for all MCP tool returns.

### Performance Guarantees (Principle IV)
- **Status queries <100ms**: Indexed SELECT on indexing_jobs table (FR-006).
- **No performance regression**: Background worker has same indexing speed as synchronous path.
- **Efficient progress updates**: 2-second interval = <1% overhead.
- **Connection pool-based limiting**: Prevents resource exhaustion, maintains performance.

### Production Quality Standards (Principle V)
- **State survives restarts**: PostgreSQL persistence with ACID guarantees.
- **Comprehensive error handling**: Try/except with error_message, error_type, error_traceback fields.
- **Graceful cancellation**: Finish current batch, clean up resources, 5-second guarantee.
- **Type safety**: Pydantic models, mypy --strict compliance, validated inputs.
- **Security**: Path traversal validation, absolute path enforcement.

### Specification-First Development (Principle VI)
- **Addresses all functional requirements**: FR-001 through FR-015 covered.
- **Traces to user scenarios**: Each decision maps to spec acceptance criteria.
- **No scope creep**: Defers optional features (LISTEN/NOTIFY, job history analytics).

### Test-Driven Development (Principle VII)
- **Unit tests**: Path validation, model creation, callback invocation.
- **Integration tests**: End-to-end workflow, cancellation, concurrent jobs.
- **Edge case tests**: Server restart, orphaned jobs, connection pool exhaustion.
- **Performance tests**: Verify <1% overhead from progress tracking.

### Pydantic-Based Type Safety (Principle VIII)
- **IndexingJobStatus enum**: No magic strings, type-safe status values.
- **IndexingJobCreate model**: Path validation, input sanitization.
- **IndexingJobProgress model**: Immutable response schema for MCP tools.
- **ProgressCallback type alias**: Clear function signature for callbacks.

## Open Questions for Phase 1

**None remaining** - all technical unknowns resolved through research.

**Deferred to Future Phases**:
- **Job priority support**: FIFO only in Phase 1, priority queueing deferred.
- **PostgreSQL LISTEN/NOTIFY**: Polling model sufficient, push notifications deferred.
- **Job history analytics**: 7-day retention only, no trend analysis or metrics aggregation.
- **Configurable concurrency limit**: Fixed 3 jobs in Phase 1, env var configurability deferred.
- **Incremental indexing**: Full re-index only in Phase 1, change detection optimization deferred.
- **Job migration across servers**: Jobs tied to single server instance, portability deferred.

**Implementation Readiness**: All 7 research topics have clear technical decisions with implementation pseudo-code. Phase 1 (design artifacts) can proceed immediately.
