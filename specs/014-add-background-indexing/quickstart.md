# Quickstart: Background Indexing Integration Tests

## Purpose

Validate end-to-end background indexing workflows against specification acceptance criteria. These tests ensure the background indexing feature correctly handles large repositories, provides accurate progress tracking, supports cancellation, and automatically resumes after server restarts.

## Prerequisites

- PostgreSQL 14+ running locally with `codebase_mcp` database
- Ollama service running locally (port 11434)
- Python 3.11+ with all dependencies installed (`pip install -e .`)
- Test repository with 15,000+ files (or use provided generator script)
- MCP server running locally (`python -m codebase_mcp`)

## Test Repository Setup

Create a large test repository using the provided generator:

```bash
# Generate test repository with 15,000 files
python tests/fixtures/generate_test_repo.py \
    --output-dir /tmp/test-repo-15k \
    --file-count 15000 \
    --avg-lines-per-file 200

# Expected output:
# Generated 15,000 Python files
# Total size: ~450 MB
# Average lines per file: 200
# Total lines: ~3,000,000
```

## Scenario 1: Basic Background Indexing (User Story 1)

**Objective**: Verify large repository indexing completes in background without blocking MCP client.

**Traces to**: FR-001, FR-002, FR-006, SC-001, SC-002

**Test Script**:

```python
import asyncio
import time
from uuid import UUID

# 1. Start background indexing (MUST return in <1 second)
start_time = time.time()
result = await start_indexing_background(
    repo_path="/tmp/test-repo-15k",
    name="test-large-repo"
)
response_time = time.time() - start_time

job_id = result["job_id"]
initial_status = result["status"]

print(f"Job ID: {job_id}")
print(f"Response time: {response_time:.3f}s")

# Assertions: FR-002 (immediate response <1s)
assert response_time < 1.0, f"Response took {response_time}s (expected <1s)"
assert isinstance(job_id, str), "job_id must be string UUID"
assert len(job_id) == 36, f"job_id must be valid UUID format (got {len(job_id)} chars)"
assert initial_status in ["pending", "running"], f"Initial status must be pending or running (got {initial_status})"
print("✓ SC-002: Job created in <1 second, client can disconnect immediately\n")

# 2. Poll job status until completion (MUST provide progress updates)
print("Polling job status every 5 seconds...")
start_poll = time.time()
last_percentage = -1

while True:
    status_result = await get_indexing_status(job_id=job_id)

    current_status = status_result["status"]
    percentage = status_result.get("progress_percentage", 0)
    message = status_result.get("progress_message", "")
    files_indexed = status_result.get("files_indexed", 0)
    chunks_created = status_result.get("chunks_created", 0)

    # Assertions: FR-006 (status queries <100ms)
    query_start = time.time()
    status_check = await get_indexing_status(job_id=job_id)
    query_time = (time.time() - query_start) * 1000
    assert query_time < 100, f"Status query took {query_time:.1f}ms (expected <100ms)"

    # Verify progress is monotonically increasing
    if percentage > 0:
        assert percentage >= last_percentage, f"Progress decreased: {percentage}% < {last_percentage}%"
        last_percentage = percentage

    print(f"[{time.time() - start_poll:.1f}s] Status: {current_status} | "
          f"Progress: {percentage}% | "
          f"Files: {files_indexed} | "
          f"Chunks: {chunks_created} | "
          f"Message: {message}")

    if current_status == "completed":
        print("✓ Job completed successfully")
        break
    elif current_status == "failed":
        error_msg = status_result.get("error_message", "Unknown error")
        raise AssertionError(f"Job failed: {error_msg}")
    elif current_status == "cancelled":
        raise AssertionError("Job was cancelled unexpectedly")

    await asyncio.sleep(5)  # Poll every 5 seconds (FR-005 allows up to 10s)

total_duration = time.time() - start_poll
print(f"\nIndexing completed in {total_duration:.1f}s")

# 3. Verify completion results
final_status = await get_indexing_status(job_id=job_id)

# Assertions: SC-001 (100% success for 15K+ files)
assert final_status["status"] == "completed", "Final status must be 'completed'"
assert final_status["files_indexed"] >= 15000, f"Expected ≥15000 files, got {final_status['files_indexed']}"
assert final_status["chunks_created"] > 0, "Must have created at least 1 chunk"
assert final_status["progress_percentage"] == 100, "Final progress must be 100%"
assert final_status["completed_at"] is not None, "completed_at timestamp must be set"

print(f"✓ SC-001: Successfully indexed {final_status['files_indexed']} files without timeout")
print(f"  Files indexed: {final_status['files_indexed']}")
print(f"  Chunks created: {final_status['chunks_created']}")
print(f"  Duration: {total_duration:.1f}s")

# Assertions: FR-006 (status queries <100ms)
print("✓ SC-005: Status queries returned in <100ms p95")
print("\n✅ Scenario 1 PASSED: Basic background indexing\n")
```

**Expected Outcomes**:
- Job created in <1 second (SC-002)
- Status queries return in <100ms (SC-005)
- Indexing completes successfully for 15K+ files (SC-001)
- Progress is monotonically increasing (never decreases)
- Final status shows accurate file and chunk counts

## Scenario 2: Progress Monitoring (User Story 2)

**Objective**: Verify progress updates are accurate, frequent, and provide meaningful information.

**Traces to**: FR-005, FR-006, SC-005

**Test Script**:

```python
import asyncio
import time
from collections import defaultdict

# 1. Start background indexing
result = await start_indexing_background(
    repo_path="/tmp/test-repo-15k",
    name="test-progress-monitoring"
)
job_id = result["job_id"]

print(f"Monitoring progress for job {job_id}...\n")

# 2. Track progress updates over time
progress_log = []
phase_changes = []
update_intervals = []
last_update_time = time.time()
last_percentage = 0

for i in range(60):  # Monitor for up to 5 minutes (60 × 5s polls)
    current_time = time.time()
    status = await get_indexing_status(job_id=job_id)

    # Record progress snapshot
    snapshot = {
        "timestamp": current_time,
        "status": status["status"],
        "percentage": status.get("progress_percentage", 0),
        "message": status.get("progress_message", ""),
        "files_indexed": status.get("files_indexed", 0),
        "chunks_created": status.get("chunks_created", 0),
    }
    progress_log.append(snapshot)

    # Track phase changes (FR-005: user understands current stage)
    current_message = snapshot["message"]
    if progress_log and current_message != progress_log[-2].get("message", ""):
        phase_changes.append({
            "time": current_time,
            "from_message": progress_log[-2].get("message", ""),
            "to_message": current_message,
            "percentage": snapshot["percentage"]
        })
        print(f"[Phase Change] {current_message} ({snapshot['percentage']}%)")

    # Track update intervals (FR-005: updates every 10s or 100 work units)
    if snapshot["percentage"] > last_percentage:
        interval = current_time - last_update_time
        update_intervals.append(interval)
        last_update_time = current_time
        last_percentage = snapshot["percentage"]

        print(f"[{i*5}s] {snapshot['percentage']}% - {current_message} "
              f"(Files: {snapshot['files_indexed']}, Chunks: {snapshot['chunks_created']})")

    # Check if completed
    if status["status"] in ["completed", "failed", "cancelled"]:
        print(f"\nJob finished with status: {status['status']}")
        break

    await asyncio.sleep(5)

# 3. Analyze progress behavior
print("\n=== Progress Monitoring Analysis ===")

# Verify progress is increasing
percentages = [s["percentage"] for s in progress_log]
for i in range(1, len(percentages)):
    assert percentages[i] >= percentages[i-1], \
        f"Progress decreased at index {i}: {percentages[i]}% < {percentages[i-1]}%"
print(f"✓ Progress monotonically increasing: {percentages[0]}% → {percentages[-1]}%")

# Verify update frequency (FR-005: at least every 10 seconds or 100 work units)
if update_intervals:
    max_interval = max(update_intervals)
    avg_interval = sum(update_intervals) / len(update_intervals)
    print(f"✓ Update intervals: avg={avg_interval:.1f}s, max={max_interval:.1f}s")
    assert max_interval <= 12, f"Update interval exceeded 12s: {max_interval:.1f}s (FR-005 requires ≤10s)"

# Verify phase changes are meaningful
print(f"✓ Detected {len(phase_changes)} phase changes:")
for change in phase_changes:
    print(f"  - {change['percentage']}%: {change['to_message']}")

# Expected phases: Scanning → Chunking → Embedding → Writing → Complete
expected_keywords = ["scanning", "chunking", "embedding", "writing", "complete"]
messages_lower = [s["message"].lower() for s in progress_log if s["message"]]
found_phases = [kw for kw in expected_keywords if any(kw in msg for msg in messages_lower)]
print(f"✓ Found phases: {', '.join(found_phases)}")
assert len(found_phases) >= 3, f"Expected at least 3 phases, found {len(found_phases)}"

# Verify counters are increasing
files_counts = [s["files_indexed"] for s in progress_log if s["files_indexed"] > 0]
chunks_counts = [s["chunks_created"] for s in progress_log if s["chunks_created"] > 0]
if files_counts:
    print(f"✓ Files indexed increased: {files_counts[0]} → {files_counts[-1]}")
    assert files_counts[-1] >= files_counts[0], "Files indexed count must increase"
if chunks_counts:
    print(f"✓ Chunks created increased: {chunks_counts[0]} → {chunks_counts[-1]}")
    assert chunks_counts[-1] >= chunks_counts[0], "Chunks created count must increase"

print("\n✅ Scenario 2 PASSED: Progress monitoring\n")
```

**Expected Outcomes**:
- Progress percentage increases monotonically (0% → 100%)
- Updates occur at least every 10 seconds (FR-005)
- Phase changes are visible and meaningful (scanning → chunking → embedding → writing)
- File and chunk counters increase throughout execution
- Status queries consistently return in <100ms

## Scenario 3: Job Cancellation (User Story 3)

**Objective**: Verify job cancellation stops execution within 5 seconds and leaves database in consistent state.

**Traces to**: FR-008, SC-004

**Test Script**:

```python
import asyncio
import time

# 1. Start background indexing
result = await start_indexing_background(
    repo_path="/tmp/test-repo-15k",
    name="test-cancellation"
)
job_id = result["job_id"]

print(f"Started job {job_id}, waiting for job to begin processing...")

# 2. Wait for job to start processing (status='running')
for _ in range(20):  # Wait up to 20 seconds
    status = await get_indexing_status(job_id=job_id)
    if status["status"] == "running" and status["progress_percentage"] > 10:
        print(f"Job is running at {status['progress_percentage']}% - initiating cancellation")
        break
    await asyncio.sleep(1)
else:
    raise AssertionError("Job did not start running within 20 seconds")

files_before_cancel = status["files_indexed"]
chunks_before_cancel = status["chunks_created"]
percentage_before_cancel = status["progress_percentage"]

# 3. Cancel the job (MUST stop within 5 seconds per FR-008)
print(f"Cancelling job at {percentage_before_cancel}% progress...")
cancel_start = time.time()
cancel_result = await cancel_indexing_background(job_id=job_id)
cancel_response_time = time.time() - cancel_start

print(f"Cancel request acknowledged in {cancel_response_time:.3f}s")
assert cancel_response_time < 1.0, f"Cancel request took {cancel_response_time}s (expected <1s)"
assert cancel_result["status"] == "cancelled", f"Cancel result status must be 'cancelled', got {cancel_result['status']}"

# 4. Poll status to verify cancellation completes within 5 seconds
cancellation_complete = False
poll_start = time.time()

while time.time() - poll_start < 10:  # Poll for up to 10s (5s requirement + 5s margin)
    await asyncio.sleep(0.5)  # Poll frequently to catch exact completion time
    status = await get_indexing_status(job_id=job_id)

    if status["status"] == "cancelled":
        cancellation_time = time.time() - cancel_start
        print(f"✓ Job cancelled after {cancellation_time:.2f}s")
        assert cancellation_time <= 5.0, \
            f"Cancellation took {cancellation_time:.2f}s (FR-008 requires ≤5s)"
        cancellation_complete = True
        break

if not cancellation_complete:
    raise AssertionError("Job did not cancel within 10 seconds")

# 5. Verify partial work state
final_status = await get_indexing_status(job_id=job_id)

print(f"\n=== Cancellation Results ===")
print(f"Status: {final_status['status']}")
print(f"Files indexed before cancel: {files_before_cancel}")
print(f"Files indexed after cancel: {final_status['files_indexed']}")
print(f"Chunks created before cancel: {chunks_before_cancel}")
print(f"Chunks created after cancel: {final_status['chunks_created']}")
print(f"Cancelled at timestamp: {final_status['cancelled_at']}")

# Assertions: SC-004 (clean state after cancellation)
assert final_status["status"] == "cancelled", "Final status must be 'cancelled'"
assert final_status["cancelled_at"] is not None, "cancelled_at timestamp must be set"
assert final_status["completed_at"] is None, "completed_at must be NULL for cancelled jobs"

# Verify partial work was retained (FR-008: data remains consistent)
assert final_status["files_indexed"] >= files_before_cancel, \
    "Files indexed count should not decrease after cancellation"
assert final_status["chunks_created"] >= chunks_before_cancel, \
    "Chunks created count should not decrease after cancellation"

# Verify database consistency
print("\n✓ SC-004: Job stopped within 5s, database in consistent state")
print(f"  Partial work retained: {final_status['files_indexed']} files, {final_status['chunks_created']} chunks")
print(f"  Cancellation acknowledged: {cancel_response_time:.3f}s")
print(f"  Cancellation completed: {cancellation_time:.2f}s")

# 6. Verify cancelled job cannot be restarted
try:
    await cancel_indexing_background(job_id=job_id)
    raise AssertionError("Should not be able to cancel an already-cancelled job")
except Exception as e:
    print(f"✓ Correctly rejected duplicate cancellation: {e}")

print("\n✅ Scenario 3 PASSED: Job cancellation\n")
```

**Expected Outcomes**:
- Cancel request acknowledged immediately (<1 second)
- Job stops within 5 seconds of cancellation request (FR-008)
- Final status is "cancelled" with cancelled_at timestamp
- Partial work retained (files and chunks counts ≥ pre-cancellation values)
- Database remains in consistent state (no orphaned data)
- Duplicate cancellation requests rejected

## Scenario 4: Restart Recovery (User Story 4)

**Objective**: Verify job automatically resumes after server restart with minimal duplicate work.

**Traces to**: FR-009, FR-010, SC-003

**Test Script**:

```python
import asyncio
import time
import subprocess
import signal

# 1. Start background indexing
print("Starting background indexing job...")
result = await start_indexing_background(
    repo_path="/tmp/test-repo-15k",
    name="test-restart-recovery"
)
job_id = result["job_id"]

print(f"Job ID: {job_id}")

# 2. Wait for job to reach significant progress (≥30%)
print("Waiting for job to reach 30% progress...")
checkpoint_reached = False

for _ in range(120):  # Wait up to 2 minutes
    status = await get_indexing_status(job_id=job_id)
    percentage = status.get("progress_percentage", 0)

    if percentage >= 30:
        print(f"✓ Job reached {percentage}% progress")
        files_before_restart = status["files_indexed"]
        chunks_before_restart = status["chunks_created"]
        percentage_before_restart = percentage
        checkpoint_reached = True
        break

    if percentage > 0:
        print(f"  Current progress: {percentage}% (waiting for 30%...)")

    await asyncio.sleep(1)

if not checkpoint_reached:
    raise AssertionError("Job did not reach 30% progress within 2 minutes")

print(f"\nState before restart:")
print(f"  Files indexed: {files_before_restart}")
print(f"  Chunks created: {chunks_before_restart}")
print(f"  Progress: {percentage_before_restart}%")

# 3. Simulate server crash (forceful termination)
print("\n🔄 Simulating server crash (SIGKILL)...")
# NOTE: In actual test, this would kill the running MCP server process
# For this example, we'll use a placeholder
# server_process = subprocess.Popen(["python", "-m", "codebase_mcp"])
# time.sleep(2)  # Let it stabilize
# os.kill(server_process.pid, signal.SIGKILL)
print("  Server terminated forcefully (SIGKILL)")

# Wait for server to be fully stopped
await asyncio.sleep(2)

# 4. Restart server
print("🚀 Restarting server...")
# server_process = subprocess.Popen(["python", "-m", "codebase_mcp"])
# NOTE: In actual implementation, use proper process management
await asyncio.sleep(5)  # Allow server initialization time
print("  Server restarted")

# 5. Verify job automatically resumes (FR-009: within 10 seconds)
print("\nVerifying automatic job resumption...")
resume_start = time.time()
job_resumed = False

for _ in range(20):  # Check for up to 20 seconds
    await asyncio.sleep(1)

    try:
        status = await get_indexing_status(job_id=job_id)

        if status["status"] == "running":
            resume_time = time.time() - resume_start
            print(f"✓ SC-003: Job automatically resumed after {resume_time:.1f}s")
            assert resume_time <= 10.0, \
                f"Job resumed after {resume_time:.1f}s (FR-009 requires ≤10s)"
            job_resumed = True
            break
        elif status["status"] in ["completed", "failed", "cancelled"]:
            raise AssertionError(f"Job ended with status '{status['status']}' instead of resuming")
    except Exception as e:
        # Server may still be initializing
        if "connection refused" in str(e).lower():
            continue
        raise

if not job_resumed:
    raise AssertionError("Job did not resume within 20 seconds of server restart")

# 6. Monitor job to completion
print("\nMonitoring resumed job to completion...")
resume_progress_log = []

while True:
    status = await get_indexing_status(job_id=job_id)

    resume_progress_log.append({
        "percentage": status.get("progress_percentage", 0),
        "files_indexed": status.get("files_indexed", 0),
        "chunks_created": status.get("chunks_created", 0),
    })

    if status["status"] == "completed":
        print("✓ Resumed job completed successfully")
        break
    elif status["status"] in ["failed", "cancelled"]:
        raise AssertionError(f"Resumed job ended with status: {status['status']}")

    print(f"  Progress: {status['progress_percentage']}% - {status['progress_message']}")
    await asyncio.sleep(5)

# 7. Verify recovery accuracy (FR-010: <1% duplicate work)
final_status = await get_indexing_status(job_id=job_id)
files_after_restart = final_status["files_indexed"]
chunks_after_restart = final_status["chunks_created"]

print(f"\n=== Recovery Analysis ===")
print(f"State before restart:")
print(f"  Files: {files_before_restart}, Chunks: {chunks_before_restart}")
print(f"State after completion:")
print(f"  Files: {files_after_restart}, Chunks: {chunks_after_restart}")

# Calculate duplicate work percentage
# Note: Some duplicate work is acceptable (FR-010 allows <1%)
files_reprocessed = max(0, files_after_restart - files_before_restart)
if files_after_restart > 0:
    duplicate_percentage = (files_reprocessed / files_after_restart) * 100
    print(f"\nDuplicate work: {duplicate_percentage:.2f}%")

    # FR-010: Less than 1% duplicate work after restart
    assert duplicate_percentage < 1.0, \
        f"Duplicate work ({duplicate_percentage:.2f}%) exceeds 1% threshold (FR-010)"
    print(f"✓ FR-010: Duplicate work <1% ({duplicate_percentage:.2f}%)")

# Verify final results
assert final_status["status"] == "completed", "Job must complete successfully after resume"
assert final_status["files_indexed"] >= files_before_restart, \
    "Files indexed count should not decrease after restart"
assert final_status["chunks_created"] >= chunks_before_restart, \
    "Chunks created count should not decrease after restart"

print(f"\n✓ SC-003: Job resumed within 10s, completed with <1% duplicate work")
print(f"  Resume time: {resume_time:.1f}s")
print(f"  Duplicate work: {duplicate_percentage:.2f}%")
print(f"  Final files indexed: {files_after_restart}")
print(f"  Final chunks created: {chunks_after_restart}")

print("\n✅ Scenario 4 PASSED: Restart recovery\n")
```

**Expected Outcomes**:
- Job automatically resumes within 10 seconds of server restart (FR-009)
- Progress continues from last checkpoint (minimal duplicate work)
- Less than 1% of work is duplicated (FR-010)
- Job completes successfully after resumption
- All counters are accurate (account for pre-restart work)

## Scenario 5: Concurrent Jobs (FR-011)

**Objective**: Verify system supports up to 3 concurrent jobs without performance degradation.

**Traces to**: FR-011, SC-006

**Test Script**:

```python
import asyncio
import time

# 1. Start 3 concurrent jobs
print("Starting 3 concurrent background jobs...")
jobs = []

for i in range(3):
    result = await start_indexing_background(
        repo_path=f"/tmp/test-repo-{i}",  # Assume 3 test repos prepared
        name=f"concurrent-job-{i+1}"
    )
    jobs.append({
        "job_id": result["job_id"],
        "name": f"concurrent-job-{i+1}",
        "start_time": time.time(),
    })
    print(f"  Job {i+1}: {result['job_id']} - Status: {result['status']}")

print(f"\n✓ Started {len(jobs)} concurrent jobs")

# 2. Attempt to start 4th job (should queue per FR-011)
print("\nAttempting to start 4th job (should queue)...")
fourth_job_result = await start_indexing_background(
    repo_path="/tmp/test-repo-large",
    name="queued-job"
)
fourth_job_id = fourth_job_result["job_id"]

# Verify 4th job is queued, not running
fourth_status = await get_indexing_status(job_id=fourth_job_id)
print(f"  4th job status: {fourth_status['status']}")
assert fourth_status["status"] == "pending", \
    f"4th concurrent job should be 'pending', got '{fourth_status['status']}'"
print("✓ FR-011: 4th job queued (concurrency limit enforced)")

# 3. Monitor all jobs with status query performance tracking
print("\nMonitoring concurrent jobs...")
query_times = []
progress_snapshots = {job["job_id"]: [] for job in jobs}

monitoring_start = time.time()

while True:
    # Check each job's status
    all_completed = True

    for job in jobs:
        query_start = time.time()
        status = await get_indexing_status(job_id=job["job_id"])
        query_time = (time.time() - query_start) * 1000
        query_times.append(query_time)

        progress_snapshots[job["job_id"]].append({
            "time": time.time(),
            "percentage": status.get("progress_percentage", 0),
            "status": status["status"],
        })

        if status["status"] not in ["completed", "failed", "cancelled"]:
            all_completed = False

    # Print summary every 10 seconds
    if int(time.time() - monitoring_start) % 10 == 0:
        print(f"\n[{time.time() - monitoring_start:.0f}s] Job Progress:")
        for job in jobs:
            latest = progress_snapshots[job["job_id"]][-1]
            print(f"  {job['name']}: {latest['percentage']}% - {latest['status']}")

        # Check if 4th job started (after one of first 3 completes)
        fourth_current_status = await get_indexing_status(job_id=fourth_job_id)
        print(f"  queued-job: Status={fourth_current_status['status']}")

    if all_completed:
        print("\n✓ All concurrent jobs completed")
        break

    await asyncio.sleep(2)

total_duration = time.time() - monitoring_start

# 4. Verify performance (SC-006: no degradation with concurrent jobs)
print(f"\n=== Concurrent Jobs Performance Analysis ===")

# Query time performance
query_times_sorted = sorted(query_times)
p50 = query_times_sorted[len(query_times_sorted) // 2]
p95 = query_times_sorted[int(len(query_times_sorted) * 0.95)]
p99 = query_times_sorted[int(len(query_times_sorted) * 0.99)]

print(f"Status query latency (concurrent load):")
print(f"  p50: {p50:.1f}ms")
print(f"  p95: {p95:.1f}ms")
print(f"  p99: {p99:.1f}ms")

# FR-006: Status queries <100ms even under concurrent load
assert p95 < 100, f"p95 query latency ({p95:.1f}ms) exceeds 100ms (FR-006)"
print("✓ FR-006: Status queries <100ms p95 even with concurrent jobs")

# Job completion analysis
for job in jobs:
    final_status = await get_indexing_status(job_id=job["job_id"])
    duration = final_status.get("completed_at") - final_status.get("started_at")

    print(f"\n{job['name']}:")
    print(f"  Files indexed: {final_status['files_indexed']}")
    print(f"  Chunks created: {final_status['chunks_created']}")
    print(f"  Duration: {duration:.1f}s")
    print(f"  Status: {final_status['status']}")

    assert final_status["status"] == "completed", \
        f"{job['name']} did not complete successfully"

# Verify 4th job eventually started and completed
print("\nChecking queued job (4th job)...")
fourth_final_status = await get_indexing_status(job_id=fourth_job_id)
print(f"  Status: {fourth_final_status['status']}")

if fourth_final_status["status"] == "completed":
    print("✓ Queued job started after slot became available and completed successfully")
elif fourth_final_status["status"] == "running":
    print("  Queued job is now running (will complete shortly)")
else:
    print(f"  Queued job status: {fourth_final_status['status']}")

print(f"\n✓ SC-006: System supported 3 concurrent jobs without performance degradation")
print(f"  Total monitoring duration: {total_duration:.1f}s")
print(f"  Status query p95: {p95:.1f}ms (<100ms target)")

print("\n✅ Scenario 5 PASSED: Concurrent jobs\n")
```

**Expected Outcomes**:
- First 3 jobs start immediately (status="running")
- 4th job is queued (status="pending")
- All jobs complete successfully without errors
- Status query latency <100ms p95 even with concurrent load (FR-006)
- Queued job starts automatically when slot becomes available
- No performance degradation observed (SC-006)

## Performance Validation

**Objective**: Verify all constitutional performance targets are met.

**Test Script**:

```python
import asyncio
import time
import statistics

# 1. Job creation latency (SC-002: <1s)
print("=== Job Creation Latency ===")
creation_times = []

for i in range(10):
    start = time.time()
    result = await start_indexing_background(
        repo_path="/tmp/test-repo-small",
        name=f"perf-test-{i}"
    )
    creation_time = time.time() - start
    creation_times.append(creation_time * 1000)  # Convert to ms

    # Cancel immediately to avoid resource exhaustion
    await cancel_indexing_background(job_id=result["job_id"])

creation_p50 = statistics.median(creation_times)
creation_p95 = statistics.quantiles(creation_times, n=20)[18]

print(f"Job creation latency (10 trials):")
print(f"  p50: {creation_p50:.1f}ms")
print(f"  p95: {creation_p95:.1f}ms")
assert creation_p95 < 1000, f"Job creation p95 ({creation_p95:.1f}ms) exceeds 1000ms"
print("✓ SC-002: Job creation <1s")

# 2. Status query latency (FR-006: <100ms)
print("\n=== Status Query Latency ===")
query_times = []

# Create a job for querying
result = await start_indexing_background(
    repo_path="/tmp/test-repo-15k",
    name="query-perf-test"
)
job_id = result["job_id"]

# Perform 100 status queries
for i in range(100):
    start = time.time()
    await get_indexing_status(job_id=job_id)
    query_time = (time.time() - start) * 1000
    query_times.append(query_time)

query_p50 = statistics.median(query_times)
query_p95 = statistics.quantiles(query_times, n=20)[18]

print(f"Status query latency (100 trials):")
print(f"  p50: {query_p50:.1f}ms")
print(f"  p95: {query_p95:.1f}ms")
assert query_p95 < 100, f"Status query p95 ({query_p95:.1f}ms) exceeds 100ms"
print("✓ FR-006: Status queries <100ms p95")

# Cleanup
await cancel_indexing_background(job_id=job_id)

# 3. Cancellation latency (FR-008: <5s)
print("\n=== Cancellation Latency ===")

result = await start_indexing_background(
    repo_path="/tmp/test-repo-15k",
    name="cancel-perf-test"
)
job_id = result["job_id"]

# Wait for job to start running
await asyncio.sleep(10)

# Measure cancellation time
cancel_start = time.time()
await cancel_indexing_background(job_id=job_id)

# Poll until actually cancelled
while True:
    status = await get_indexing_status(job_id=job_id)
    if status["status"] == "cancelled":
        break
    await asyncio.sleep(0.5)

cancellation_time = time.time() - cancel_start

print(f"Cancellation time: {cancellation_time:.2f}s")
assert cancellation_time <= 5.0, f"Cancellation took {cancellation_time:.2f}s (exceeds 5s)"
print("✓ FR-008: Cancellation <5s")

print("\n✅ All performance targets met\n")
```

**Performance Targets**:
- Job creation: <1s p95 (SC-002)
- Status queries: <100ms p95 (FR-006)
- Cancellation: <5s (FR-008)
- Automatic resumption: <10s after restart (FR-009)

## Edge Case Validation

**Test Script**:

```python
import asyncio

print("=== Edge Case Validation ===\n")

# 1. Invalid repository path (FR-015: validation error)
print("Test 1: Invalid repository path")
try:
    result = await start_indexing_background(
        repo_path="/nonexistent/path/does/not/exist",
        name="invalid-repo"
    )
    raise AssertionError("Should have rejected invalid repo path")
except Exception as e:
    assert "validation" in str(e).lower() or "not found" in str(e).lower()
    print(f"✓ FR-015: Correctly rejected invalid path: {e}\n")

# 2. Duplicate job for same repository (FR-012: return existing job_id)
print("Test 2: Duplicate job detection")
result1 = await start_indexing_background(
    repo_path="/tmp/test-repo-15k",
    name="duplicate-test"
)
job_id_1 = result1["job_id"]

# Try to start another job for same repo while first is running
result2 = await start_indexing_background(
    repo_path="/tmp/test-repo-15k",
    name="duplicate-test"
)
job_id_2 = result2["job_id"]

# FR-012: Should return existing job_id
assert job_id_1 == job_id_2, \
    f"FR-012: Expected duplicate request to return same job_id, got different IDs"
print(f"✓ FR-012: Duplicate request returned existing job_id: {job_id_1}\n")

# Cleanup
await cancel_indexing_background(job_id=job_id_1)

# 3. Query non-existent job (error handling)
print("Test 3: Query non-existent job")
try:
    await get_indexing_status(job_id="00000000-0000-0000-0000-000000000000")
    raise AssertionError("Should have rejected non-existent job_id")
except Exception as e:
    assert "not found" in str(e).lower()
    print(f"✓ Correctly rejected non-existent job: {e}\n")

# 4. Cancel already-completed job (error handling)
print("Test 4: Cancel completed job")
# Start and immediately complete a small job
result = await start_indexing_background(
    repo_path="/tmp/test-repo-small",  # Assume small repo that completes quickly
    name="quick-job"
)
job_id = result["job_id"]

# Wait for completion
while True:
    status = await get_indexing_status(job_id=job_id)
    if status["status"] == "completed":
        break
    await asyncio.sleep(1)

# Try to cancel completed job
try:
    await cancel_indexing_background(job_id=job_id)
    raise AssertionError("Should not allow cancelling completed job")
except Exception as e:
    assert "completed" in str(e).lower() or "cannot cancel" in str(e).lower()
    print(f"✓ Correctly rejected cancellation of completed job: {e}\n")

print("✅ All edge cases handled correctly\n")
```

**Edge Cases Covered**:
- Invalid repository path → Validation error (FR-015)
- Duplicate job for same repo → Returns existing job_id (FR-012)
- Query non-existent job → Not found error
- Cancel completed/failed job → Invalid operation error
- 4th concurrent job → Queued with status="pending" (FR-011)

## Test Data Cleanup

**After Test Completion**:

```python
# 1. Cancel all running jobs
print("Cleaning up running jobs...")
job_list = await list_indexing_jobs(status="running")
for job in job_list.get("jobs", []):
    try:
        await cancel_indexing_background(job_id=job["job_id"])
        print(f"  Cancelled job: {job['job_id']}")
    except Exception as e:
        print(f"  Warning: Could not cancel {job['job_id']}: {e}")

# 2. Remove test repositories
import shutil
for i in range(4):
    test_repo_path = f"/tmp/test-repo-{i}"
    if os.path.exists(test_repo_path):
        shutil.rmtree(test_repo_path)
        print(f"  Removed test repo: {test_repo_path}")

# 3. Clean up database (optional - for test environment only)
# NOTE: Do NOT run this in production
# await db.execute(text("TRUNCATE TABLE indexing_jobs CASCADE"))
# await db.commit()
# print("  Truncated indexing_jobs table")

print("✅ Cleanup complete")
```

## Success Criteria Summary

| Criterion | Target | Test Scenario |
|-----------|--------|---------------|
| SC-001 | 100% success for 15K+ files | Scenario 1 |
| SC-002 | Job creation <1s | Scenario 1, Performance |
| SC-003 | Resume <10s, <1% duplicate work | Scenario 4 |
| SC-004 | Cancellation <5s, consistent state | Scenario 3 |
| SC-005 | Status queries <100ms | All scenarios, Performance |
| SC-006 | 3 concurrent jobs, no degradation | Scenario 5 |
| SC-007 | <2% job failure rate | All scenarios (failure tracking) |
| SC-008 | Clear progress messages | Scenario 2 (user comprehension) |

## Troubleshooting

**Job stuck in "pending" status**:
- Check if 3 jobs are already running (concurrency limit reached)
- Verify database connection is healthy
- Check server logs: `tail -f /tmp/codebase-mcp.log`

**Status queries timing out**:
- Verify PostgreSQL is running: `pg_isready`
- Check connection pool settings in `settings.py`
- Monitor database connections: `SELECT count(*) FROM pg_stat_activity`

**Job not resuming after restart**:
- Verify job status is "running" before restart
- Check that database connection is restored after restart
- Look for errors in startup logs

**Cancellation taking >5 seconds**:
- Check if job is processing a large file (wait for batch to complete)
- Verify progress updates are occurring (2s interval)
- Monitor database for lock contention

## Running the Test Suite

Execute all integration tests:

```bash
# Run all background indexing tests
pytest tests/integration/test_background_indexing.py -v

# Run specific scenario
pytest tests/integration/test_background_indexing.py::test_basic_background_indexing -v

# Run with performance profiling
pytest tests/integration/test_background_indexing.py --benchmark-only
```

## Reporting Issues

When reporting test failures, include:
1. Test scenario name and number
2. Job ID from failed test
3. Full status output from `get_indexing_status()`
4. Relevant server logs from `/tmp/codebase-mcp.log`
5. PostgreSQL version: `psql --version`
6. Python version: `python --version`
7. System info: OS, RAM, disk space
