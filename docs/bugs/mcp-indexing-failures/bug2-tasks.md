# Bug 2 Tasks: Background Indexing Auto-Creation Failure

**Bug**: Background indexing doesn't trigger auto-creation of project databases
**Root Cause**: FastMCP Context object becomes invalid/stale when background worker executes
**Fix Strategy**: Option A - Capture config path in foreground, pass to worker instead of ctx
**Complexity**: HIGH (context lifecycle, async background tasks, auto-creation flow)

**Dependencies**:
- ✅ Bug 3 (error reporting) must be fixed FIRST
- ✅ Bug 1 (baseline functionality) should be fixed SECOND
- This is Bug 2 (most complex) - fix THIRD

**Files Modified**: 2
- `/Users/cliffclarke/Claude_Code/codebase-mcp/src/mcp/tools/background_indexing.py`
- `/Users/cliffclarke/Claude_Code/codebase-mcp/src/services/background_worker.py`

**Estimated Effort**: 3-4 hours
- Preparation: 30 min
- Testing: 1-1.5 hours (most complex bug, needs comprehensive tests)
- Implementation: 45 min
- Verification: 45 min

---

## Phase 1: Preparation (Setup & Analysis)

**Purpose**: Understand the context lifecycle and verify the fix approach

### T001: Verify current behavior and error path

**Description**: Run manual test to confirm stale context hypothesis

**Steps**:
```bash
# 1. Create test directory with config
mkdir -p /tmp/test-bug2/.codebase-mcp
echo '{"project": {"name": "test-bug2"}}' > /tmp/test-bug2/.codebase-mcp/config.json
echo "def test(): pass" > /tmp/test-bug2/test.py

# 2. Ensure database doesn't exist yet
psql -l | grep cb_proj_test_bug2 || echo "Database not found (expected)"

# 3. Try background indexing via MCP tool
# Expected: Fails with "database does not exist" error
# Call: set_working_directory("/tmp/test-bug2")
# Call: start_indexing_background(repo_path="/tmp/test-bug2")
# Call: get_indexing_status(job_id=<returned_id>)
```

**Acceptance**:
- Job status shows "failed" with database error
- Confirms stale context doesn't trigger auto-creation
- Documents exact error message for comparison

**Output**: Log file showing error before fix

**Commit**: None (exploration only)

---

### T002: Review auto-creation code and config resolution flow

**Description**: Study how foreground indexing successfully triggers auto-creation

**Files to Read**:
- `/Users/cliffclarke/Claude_Code/codebase-mcp/src/database/auto_create.py:227-559`
- `/Users/cliffclarke/Claude_Code/codebase-mcp/src/auto_switch/config.py` (find_config_file)
- `/Users/cliffclarke/Claude_Code/codebase-mcp/src/database/session.py:320-322` (context validation)
- `/Users/cliffclarke/Claude_Code/codebase-mcp/src/database/session.py:394-399` (_resolve_project_context)

**Questions to Answer**:
1. How does `get_or_create_project_from_config()` work? (parameters, flow, error handling)
2. How does `find_config_file()` search for config? (search depth, caching, errors)
3. What happens if config_path is invalid when worker runs? (file deleted, moved, etc.)
4. Is `get_or_create_project_from_config()` idempotent? (safe to call multiple times)

**Acceptance**:
- Understand config search algorithm (up to 20 parent dirs)
- Confirm auto-creation is idempotent (returns existing if present)
- Understand error cases (invalid config, missing name, creation failure)

**Commit**: None (research only)

---

## Phase 2: Test-Driven Development (Write Tests First)

**Purpose**: Create comprehensive tests that capture expected behavior BEFORE implementation

**TDD Principle**: All tests should FAIL initially, then PASS after implementation

---

### T003: Create unit test for config path capture in start_indexing_background

**File**: `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/unit/test_background_auto_create.py` (NEW)

**Test**: `test_start_indexing_captures_config_path_when_ctx_valid()`

**Description**: Verify that `start_indexing_background` captures config_path while ctx is still valid

```python
async def test_start_indexing_captures_config_path_when_ctx_valid(tmp_path, mock_ctx):
    """Verify config path is resolved in foreground before background task starts.

    This test verifies Bug 2 fix: config path must be captured while ctx is valid,
    then passed to background worker instead of ctx itself.
    """
    # Setup: Create config file
    config_dir = tmp_path / ".codebase-mcp"
    config_dir.mkdir()
    config_file = config_dir / "config.json"
    config_file.write_text('{"project": {"name": "test-project"}}')

    # Setup: Create test repo
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    (repo_path / "test.py").write_text("def test(): pass")

    # Setup: Mock session context manager to return working_directory
    mock_session_mgr = Mock()
    mock_session_mgr.get_working_directory = AsyncMock(return_value=str(tmp_path))

    # Setup: Mock _background_indexing_worker to capture arguments
    captured_args = {}
    original_worker = background_worker._background_indexing_worker
    async def capture_worker_args(**kwargs):
        captured_args.update(kwargs)
        # Don't actually run worker
        return None

    with patch('src.services.background_worker._background_indexing_worker', capture_worker_args):
        with patch('src.mcp.tools.background_indexing.get_session_context_manager', return_value=mock_session_mgr):
            # Execute: Call start_indexing_background with ctx
            result = await start_indexing_background(
                repo_path=str(repo_path),
                project_id=None,
                ctx=mock_ctx,
            )

    # Assert: config_path was captured and passed to worker
    assert "config_path" in captured_args, "Worker should receive config_path parameter"
    assert captured_args["config_path"] is not None, "config_path should be resolved"
    assert captured_args["config_path"] == config_file, f"Expected {config_file}, got {captured_args['config_path']}"

    # Assert: ctx should NOT be passed to worker
    assert "ctx" not in captured_args or captured_args["ctx"] is None, "ctx should not be passed to worker"
```

**Expected Result**: FAILS (worker doesn't accept config_path yet)

**Commit**: `test: add unit test for config path capture in background indexing (Bug 2)`

---

### T004: Create unit test for config path fallback (no ctx)

**File**: `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/unit/test_background_auto_create.py`

**Test**: `test_start_indexing_without_ctx_has_none_config_path()`

**Description**: Verify graceful fallback when ctx is None or config lookup fails

```python
async def test_start_indexing_without_ctx_has_none_config_path(tmp_path):
    """Verify background indexing works without ctx (config_path=None fallback).

    When ctx is None or config lookup fails, config_path should be None.
    Worker should continue with default database (no auto-creation).
    """
    # Setup: Create test repo (NO config file)
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    (repo_path / "test.py").write_text("def test(): pass")

    # Setup: Mock worker to capture arguments
    captured_args = {}
    async def capture_worker_args(**kwargs):
        captured_args.update(kwargs)
        return None

    with patch('src.services.background_worker._background_indexing_worker', capture_worker_args):
        # Execute: Call start_indexing_background WITHOUT ctx
        result = await start_indexing_background(
            repo_path=str(repo_path),
            project_id=None,
            ctx=None,  # No context
        )

    # Assert: config_path should be None (no auto-creation)
    assert captured_args.get("config_path") is None, "config_path should be None when ctx is None"
```

**Expected Result**: FAILS (parameter doesn't exist yet)

**Commit**: `test: add unit test for config path fallback without ctx (Bug 2)`

---

### T005: Create unit test for worker auto-creation with config_path

**File**: `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/unit/test_background_auto_create.py`

**Test**: `test_worker_triggers_auto_creation_when_config_path_provided()`

**Description**: Verify worker calls auto-creation when config_path is provided

```python
async def test_worker_triggers_auto_creation_when_config_path_provided(tmp_path, mock_project):
    """Verify worker triggers auto-creation when config_path is provided.

    This is the core Bug 2 fix: worker must call get_or_create_project_from_config()
    at startup if config_path is not None.
    """
    # Setup: Create config file
    config_dir = tmp_path / ".codebase-mcp"
    config_dir.mkdir()
    config_file = config_dir / "config.json"
    config_file.write_text('{"project": {"name": "worker-test"}}')

    # Setup: Create test repo
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    (repo_path / "test.py").write_text("def test(): pass")

    # Setup: Create job in database
    job_id = uuid4()
    async with AsyncSession(engine) as session:
        job = IndexingJob(
            id=job_id,
            repo_path=str(repo_path),
            project_id="worker-test",
            status="pending",
        )
        session.add(job)
        await session.commit()

    # Setup: Mock auto-creation to capture calls
    auto_create_called = False
    auto_create_config_path = None
    original_auto_create = auto_create.get_or_create_project_from_config

    async def mock_auto_create(config_path, registry=None):
        nonlocal auto_create_called, auto_create_config_path
        auto_create_called = True
        auto_create_config_path = config_path
        return mock_project  # Return mock project

    # Setup: Mock indexer to avoid actual indexing
    with patch('src.database.auto_create.get_or_create_project_from_config', mock_auto_create):
        with patch('src.services.background_worker.index_repository', AsyncMock(return_value={"files_indexed": 1})):
            # Execute: Run worker with config_path
            await _background_indexing_worker(
                job_id=job_id,
                repo_path=str(repo_path),
                project_id="worker-test",
                config_path=config_file,  # NEW PARAMETER
            )

    # Assert: Auto-creation was called
    assert auto_create_called, "Worker should call get_or_create_project_from_config"
    assert auto_create_config_path == config_file, f"Expected {config_file}, got {auto_create_config_path}"

    # Assert: Job completed successfully
    async with AsyncSession(engine) as session:
        result = await session.get(IndexingJob, job_id)
        assert result.status == "completed", f"Expected completed, got {result.status}"
```

**Expected Result**: FAILS (worker doesn't accept config_path parameter yet)

**Commit**: `test: add unit test for worker auto-creation with config path (Bug 2)`

---

### T006: Create unit test for worker without config_path (backward compat)

**File**: `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/unit/test_background_auto_create.py`

**Test**: `test_worker_without_config_path_skips_auto_creation()`

**Description**: Verify worker works correctly when config_path is None (backward compatibility)

```python
async def test_worker_without_config_path_skips_auto_creation(tmp_path, existing_project_db):
    """Verify worker works without config_path if database already exists.

    Backward compatibility test: worker should work with config_path=None
    if the project database already exists (e.g., created manually).
    """
    # Setup: Create test repo
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    (repo_path / "test.py").write_text("def test(): pass")

    # Setup: Create job in database
    job_id = uuid4()
    async with AsyncSession(engine) as session:
        job = IndexingJob(
            id=job_id,
            repo_path=str(repo_path),
            project_id="existing-project",  # Database exists via fixture
            status="pending",
        )
        session.add(job)
        await session.commit()

    # Setup: Mock auto-creation to detect calls
    auto_create_called = False
    async def mock_auto_create(config_path, registry=None):
        nonlocal auto_create_called
        auto_create_called = True
        raise AssertionError("Auto-creation should not be called when config_path is None")

    # Setup: Mock indexer
    with patch('src.database.auto_create.get_or_create_project_from_config', mock_auto_create):
        with patch('src.services.background_worker.index_repository', AsyncMock(return_value={"files_indexed": 1})):
            # Execute: Run worker WITHOUT config_path
            await _background_indexing_worker(
                job_id=job_id,
                repo_path=str(repo_path),
                project_id="existing-project",
                config_path=None,  # No config path
            )

    # Assert: Auto-creation was NOT called
    assert not auto_create_called, "Auto-creation should be skipped when config_path is None"

    # Assert: Job completed successfully
    async with AsyncSession(engine) as session:
        result = await session.get(IndexingJob, job_id)
        assert result.status == "completed", f"Expected completed, got {result.status}"
```

**Expected Result**: FAILS (parameter doesn't exist yet)

**Commit**: `test: add unit test for worker backward compatibility without config (Bug 2)`

---

### T007: Create unit test for auto-creation failure handling

**File**: `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/unit/test_background_auto_create.py`

**Test**: `test_worker_continues_on_auto_creation_failure()`

**Description**: Verify worker logs warning but continues if auto-creation fails

```python
async def test_worker_continues_on_auto_creation_failure(tmp_path, caplog):
    """Verify worker logs warning but continues if auto-creation fails.

    Error handling test: if auto-creation fails (e.g., invalid config, permission error),
    worker should log warning and attempt to proceed anyway (database might exist already).
    """
    # Setup: Create INVALID config file
    config_dir = tmp_path / ".codebase-mcp"
    config_dir.mkdir()
    config_file = config_dir / "config.json"
    config_file.write_text('{"invalid": "json"}')  # Missing project.name

    # Setup: Create test repo
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    (repo_path / "test.py").write_text("def test(): pass")

    # Setup: Create job
    job_id = uuid4()
    async with AsyncSession(engine) as session:
        job = IndexingJob(
            id=job_id,
            repo_path=str(repo_path),
            project_id="test-project",
            status="pending",
        )
        session.add(job)
        await session.commit()

    # Setup: Mock auto-creation to raise error
    async def failing_auto_create(config_path, registry=None):
        raise ValueError("Invalid config: missing project.name")

    # Setup: Mock indexer to simulate success after auto-creation failure
    with patch('src.database.auto_create.get_or_create_project_from_config', failing_auto_create):
        with patch('src.services.background_worker.index_repository', AsyncMock(return_value={"files_indexed": 1})):
            with caplog.at_level(logging.WARNING):
                # Execute: Run worker with invalid config
                await _background_indexing_worker(
                    job_id=job_id,
                    repo_path=str(repo_path),
                    project_id="test-project",
                    config_path=config_file,
                )

    # Assert: Warning was logged
    assert any("Failed to auto-create project database" in record.message for record in caplog.records), \
        "Should log warning when auto-creation fails"

    # Assert: Worker continued and completed
    async with AsyncSession(engine) as session:
        result = await session.get(IndexingJob, job_id)
        assert result.status == "completed", "Worker should continue despite auto-creation failure"
```

**Expected Result**: FAILS (error handling doesn't exist yet)

**Commit**: `test: add unit test for auto-creation failure handling (Bug 2)`

---

### T008: Create integration test for end-to-end auto-creation

**File**: `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/integration/test_background_auto_create_e2e.py` (NEW)

**Test**: `test_background_indexing_auto_creates_project_from_config()`

**Description**: Full end-to-end test verifying auto-creation works in background indexing

```python
@pytest.mark.integration
async def test_background_indexing_auto_creates_project_from_config(tmp_path, mock_ctx):
    """End-to-end test: background indexing creates database from config.

    This is the complete Bug 2 fix validation:
    1. Create config file (project doesn't exist yet)
    2. Call start_indexing_background via MCP tool
    3. Verify database is created automatically
    4. Verify indexing completes successfully
    5. Verify files are searchable in new database
    """
    # Setup: Create config file for NEW project
    config_dir = tmp_path / ".codebase-mcp"
    config_dir.mkdir()
    config_file = config_dir / "config.json"
    project_name = f"e2e-test-{uuid4().hex[:8]}"
    config_file.write_text(f'{{"project": {{"name": "{project_name}"}}}}')

    # Setup: Create test repository
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    (repo_path / "test.py").write_text("def hello_world(): pass")
    (repo_path / "utils.py").write_text("def utility_func(): pass")

    # Setup: Mock session context to return working directory
    mock_session_mgr = Mock()
    mock_session_mgr.get_working_directory = AsyncMock(return_value=str(tmp_path))

    # Verify: Database doesn't exist yet
    database_name = f"cb_proj_{project_name}_"  # Prefix only
    result = await asyncio.create_subprocess_exec(
        "psql", "-lqt",
        stdout=asyncio.subprocess.PIPE,
    )
    stdout, _ = await result.communicate()
    assert database_name not in stdout.decode(), "Database should not exist before indexing"

    # Execute: Start background indexing
    with patch('src.mcp.tools.background_indexing.get_session_context_manager', return_value=mock_session_mgr):
        result = await start_indexing_background(
            repo_path=str(repo_path),
            project_id=None,
            ctx=mock_ctx,
        )

    job_id = result["job_id"]

    # Wait: Poll until job completes (max 30 seconds)
    max_attempts = 30
    for attempt in range(max_attempts):
        status = await get_indexing_status(job_id=job_id, project_id=None, ctx=None)
        if status["status"] in ["completed", "failed"]:
            break
        await asyncio.sleep(1)

    # Assert: Job completed successfully
    assert status["status"] == "completed", f"Job should complete, got: {status['status']}, error: {status.get('error_message')}"
    assert status["files_indexed"] == 2, f"Should index 2 files, got: {status['files_indexed']}"

    # Assert: Database was created
    result = await asyncio.create_subprocess_exec(
        "psql", "-lqt",
        stdout=asyncio.subprocess.PIPE,
    )
    stdout, _ = await result.communicate()
    assert database_name in stdout.decode(), f"Database {database_name}* should exist after indexing"

    # Assert: Files are searchable
    from src.mcp.tools.search import search_code
    search_results = await search_code(
        query="hello world function",
        project_id=None,
        ctx=mock_ctx,  # Uses same session context
    )
    assert len(search_results["results"]) > 0, "Should find indexed files via search"
    assert any("hello_world" in r["content"] for r in search_results["results"]), \
        "Search should return hello_world function"
```

**Expected Result**: FAILS (config_path not captured/passed yet)

**Commit**: `test: add integration test for background auto-creation end-to-end (Bug 2)`

---

### T009: Create integration test for background indexing without config

**File**: `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/integration/test_background_auto_create_e2e.py`

**Test**: `test_background_indexing_uses_default_database_without_config()`

**Description**: Verify fallback to default database when no config exists

```python
@pytest.mark.integration
async def test_background_indexing_uses_default_database_without_config(tmp_path):
    """Verify background indexing falls back to default database without config.

    Fallback test: when no config exists and no ctx provided,
    indexing should use default project database.
    """
    # Setup: Create test repo (NO config file)
    repo_path = tmp_path / "repo-no-config"
    repo_path.mkdir()
    (repo_path / "test.py").write_text("def test(): pass")

    # Execute: Start background indexing WITHOUT ctx
    result = await start_indexing_background(
        repo_path=str(repo_path),
        project_id=None,
        ctx=None,  # No context
    )

    job_id = result["job_id"]

    # Wait: Poll until complete
    for _ in range(30):
        status = await get_indexing_status(job_id=job_id)
        if status["status"] in ["completed", "failed"]:
            break
        await asyncio.sleep(1)

    # Assert: Uses default database
    assert result["database_name"] == "cb_proj_default_00000000", \
        f"Should use default database, got: {result['database_name']}"
    assert status["status"] == "completed", f"Should complete with default DB, got: {status['status']}"
```

**Expected Result**: SHOULD PASS (tests existing fallback behavior)

**Commit**: `test: add integration test for default database fallback (Bug 2)`

---

## Phase 3: Implementation (Make Tests Pass)

**Purpose**: Implement Option A fix - capture config path in foreground, pass to worker

**Strategy**: Small incremental changes, run tests after each step

---

### T010: Add config path capture to start_indexing_background

**File**: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/mcp/tools/background_indexing.py`

**Location**: After line 88 (after `resolve_project_id` call, before job creation)

**Changes**: Add config path resolution logic

```python
# After line 88: resolved_id, database_name = await resolve_project_id(...)

# NEW: Resolve config path while ctx is still valid (Bug 2 fix)
config_path: Path | None = None
if ctx:
    try:
        from src.auto_switch.config import find_config_file
        from src.database.session import get_session_context_manager

        session_ctx_mgr = get_session_context_manager()
        working_dir = await session_ctx_mgr.get_working_directory(ctx.session_id)

        if working_dir:
            config_path = find_config_file(Path(working_dir))
            if config_path:
                logger.debug(
                    f"Resolved config path for background indexing: {config_path}",
                    extra={
                        "context": {
                            "operation": "start_indexing_background",
                            "config_path": str(config_path),
                            "working_dir": working_dir,
                        }
                    },
                )
    except Exception as e:
        logger.debug(
            f"Failed to resolve config path for background indexing: {e}",
            extra={
                "context": {
                    "operation": "start_indexing_background",
                    "error": str(e),
                }
            },
        )
        # Continue with config_path=None (fallback to default)
```

**Validation**:
```bash
# Run unit test T003
pytest tests/unit/test_background_auto_create.py::test_start_indexing_captures_config_path_when_ctx_valid -v

# Expected: Still fails (worker doesn't accept parameter yet)
```

**Commit**: `fix(background): capture config path in start_indexing_background (Bug 2)`

---

### T011: Update worker invocation to pass config_path

**File**: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/mcp/tools/background_indexing.py`

**Location**: Line 111-118 (asyncio.create_task call)

**Changes**: Replace `ctx` parameter with `config_path`

```python
# BEFORE (line 111-118):
asyncio.create_task(
    _background_indexing_worker(
        job_id=job_id,
        repo_path=job_input.repo_path,
        project_id=resolved_id,
        ctx=ctx,  # OLD: stale context
    )
)

# AFTER:
asyncio.create_task(
    _background_indexing_worker(
        job_id=job_id,
        repo_path=job_input.repo_path,
        project_id=resolved_id,
        config_path=config_path,  # NEW: captured config path
    )
)
```

**Validation**:
```bash
# This will now fail with signature mismatch (expected)
pytest tests/unit/test_background_auto_create.py::test_start_indexing_captures_config_path_when_ctx_valid -v
```

**Commit**: `fix(background): pass config_path to worker instead of ctx (Bug 2)`

---

### T012: Update worker signature to accept config_path

**File**: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/services/background_worker.py`

**Location**: Line 83-99 (function signature and docstring)

**Changes**: Replace `ctx` parameter with `config_path`

```python
# BEFORE (line 83-99):
async def _background_indexing_worker(
    job_id: UUID,
    repo_path: str,
    project_id: str,
    ctx: Context | None = None,
) -> None:
    """Background worker that executes indexing and updates PostgreSQL.

    Simple state machine: pending → running → completed/failed
    No progress callbacks - binary state only.

    Args:
        job_id: UUID of indexing_jobs row
        repo_path: Absolute path to repository
        project_id: Resolved project identifier
        ctx: Optional FastMCP Context for session resolution

    ...
    """

# AFTER:
async def _background_indexing_worker(
    job_id: UUID,
    repo_path: str,
    project_id: str,
    config_path: Path | None = None,
) -> None:
    """Background worker that executes indexing and updates PostgreSQL.

    Simple state machine: pending → running → completed/failed
    No progress callbacks - binary state only.

    Args:
        job_id: UUID of indexing_jobs row
        repo_path: Absolute path to repository
        project_id: Resolved project identifier
        config_path: Optional path to .codebase-mcp/config.json for auto-creation
                     If provided, worker will attempt to auto-create project database.
                     If None, worker uses existing database or default database.

    Bug Fix:
        Resolves Bug 2 - Background indexing auto-creation failure.
        Previously passed FastMCP Context which becomes stale in background task.
        Now captures config path in foreground (while ctx valid) and passes path.

    ...
    """
```

**Validation**:
```bash
# Should now compile but tests still fail (no auto-creation logic yet)
pytest tests/unit/test_background_auto_create.py::test_start_indexing_captures_config_path_when_ctx_valid -v
```

**Commit**: `fix(worker): update signature to accept config_path instead of ctx (Bug 2)`

---

### T013: Add import for Path type in worker

**File**: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/services/background_worker.py`

**Location**: Top of file (imports section)

**Changes**: Add Path import

```python
from pathlib import Path  # ADD THIS
```

**Commit**: Include in next commit (minor change)

---

### T014: Implement auto-creation logic at start of worker

**File**: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/services/background_worker.py`

**Location**: After line 124 (after status update to "running", before get_session)

**Changes**: Add auto-creation block

```python
# After line 124: await update_job(job_id=job_id, status="running", ...)

# NEW: Auto-create project database if config provided (Bug 2 fix)
if config_path:
    try:
        from src.database.auto_create import get_or_create_project_from_config

        logger.info(
            f"Auto-creating project database from config: {config_path}",
            extra={
                "context": {
                    "operation": "background_indexing",
                    "job_id": str(job_id),
                    "config_path": str(config_path),
                }
            },
        )

        await get_or_create_project_from_config(config_path)

        logger.info(
            f"Successfully auto-created/verified project database for {project_id}",
            extra={
                "context": {
                    "operation": "background_indexing",
                    "job_id": str(job_id),
                    "project_id": project_id,
                }
            },
        )
    except Exception as e:
        logger.warning(
            f"Failed to auto-create project database: {e}",
            extra={
                "context": {
                    "operation": "background_indexing",
                    "job_id": str(job_id),
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            },
        )
        # Continue anyway - database might exist already
        # If database truly doesn't exist, get_session will fail below
```

**Validation**:
```bash
# Run all unit tests - should now pass!
pytest tests/unit/test_background_auto_create.py -v

# Expected: T003-T007 all PASS
```

**Commit**: `fix(worker): implement auto-creation from config path (Bug 2)`

---

### T015: Remove ctx parameter from get_session call in worker

**File**: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/services/background_worker.py`

**Location**: Line 127 (get_session call)

**Changes**: Remove `ctx` parameter since we no longer pass it to worker

```python
# BEFORE (line 127):
async with get_session(project_id=project_id, ctx=ctx) as session:

# AFTER:
async with get_session(project_id=project_id, ctx=None) as session:
```

**Rationale**:
- Worker no longer receives ctx parameter
- Auto-creation happens BEFORE get_session
- get_session will use project_id to find existing database
- ctx=None prevents stale context issues

**Commit**: `fix(worker): remove ctx from get_session call (Bug 2)`

---

## Phase 4: Verification (Validate Fix Works)

**Purpose**: Run all tests and manual verification to confirm bug is fixed

---

### T016: Run complete unit test suite

**Command**:
```bash
# Run all Bug 2 unit tests
pytest tests/unit/test_background_auto_create.py -v

# Expected: All 5 tests PASS
# - test_start_indexing_captures_config_path_when_ctx_valid ✓
# - test_start_indexing_without_ctx_has_none_config_path ✓
# - test_worker_triggers_auto_creation_when_config_path_provided ✓
# - test_worker_without_config_path_skips_auto_creation ✓
# - test_worker_continues_on_auto_creation_failure ✓
```

**Acceptance**: All unit tests pass

**Commit**: None (verification only)

---

### T017: Run integration tests

**Command**:
```bash
# Run end-to-end integration tests
pytest tests/integration/test_background_auto_create_e2e.py -v

# Expected: Both tests PASS
# - test_background_indexing_auto_creates_project_from_config ✓
# - test_background_indexing_uses_default_database_without_config ✓
```

**Acceptance**: Both integration tests pass

**Commit**: None (verification only)

---

### T018: Manual testing with MCP client

**Test Scenario**: Reproduce original bug scenario and verify it's fixed

**Steps**:
```bash
# 1. Clean up previous test
rm -rf /tmp/test-bug2-final
psql -c "DROP DATABASE IF EXISTS cb_proj_test_bug2_final_*" 2>/dev/null || true

# 2. Create test directory with config
mkdir -p /tmp/test-bug2-final/.codebase-mcp
echo '{"project": {"name": "test-bug2-final"}}' > /tmp/test-bug2-final/.codebase-mcp/config.json

# 3. Add test files
echo "def hello(): return 'world'" > /tmp/test-bug2-final/hello.py
echo "def goodbye(): return 'world'" > /tmp/test-bug2-final/goodbye.py

# 4. Via MCP client (Claude Code, etc.):
# Call: set_working_directory("/tmp/test-bug2-final")
# Call: start_indexing_background(repo_path="/tmp/test-bug2-final")
#   -> Should return job_id immediately
# Call: get_indexing_status(job_id=<returned_id>)
#   -> Poll until status="completed"

# 5. Verify database created
psql -l | grep cb_proj_test_bug2_final

# 6. Verify search works
# Call: search_code(query="hello world")
#   -> Should find hello.py
```

**Expected Results**:
1. ✅ Job created instantly (<1s)
2. ✅ Database created automatically (visible in psql -l)
3. ✅ Job completes with status="completed"
4. ✅ files_indexed=2
5. ✅ Search finds indexed files
6. ✅ NO "database does not exist" error

**Acceptance**: All steps succeed without errors

**Output**: Log showing successful completion

**Commit**: None (manual test only)

---

### T019: Verify no regression in foreground indexing

**Test**: Ensure foreground indexing still works correctly

**Command**:
```bash
# Test foreground indexing (should be unaffected)
pytest tests/integration/test_indexing.py -v -k "test_index_repository"

# Test search after indexing
pytest tests/integration/test_search.py -v -k "test_search_after_indexing"
```

**Acceptance**: All existing tests still pass (no regression)

**Commit**: None (regression check)

---

### T020: Run full test suite

**Command**:
```bash
# Run ALL tests to check for unexpected side effects
pytest tests/ -v --ignore=tests/performance/

# Check for any new failures
```

**Acceptance**: No new test failures introduced

**Commit**: None (full validation)

---

### T021: Update CHANGELOG or bug tracker

**File**: `/Users/cliffclarke/Claude_Code/codebase-mcp/docs/bugs/mcp-indexing-failures/FIXES.md` (or similar)

**Content**:
```markdown
## Bug 2: Background Indexing Auto-Creation Failure

**Status**: ✅ FIXED
**Date**: 2025-10-18
**Commits**: <list commit SHAs>

**Summary**:
Background indexing failed to trigger project database auto-creation because
FastMCP Context objects became stale when background worker executed.

**Root Cause**:
Context objects are request-scoped and invalid after MCP tool returns.
Background worker received stale ctx parameter.

**Fix**:
Implemented Option A:
1. Capture config file path in foreground (while ctx valid)
2. Pass config_path to background worker instead of ctx
3. Worker calls get_or_create_project_from_config() at startup
4. Graceful fallback if config_path is None

**Files Modified**:
- src/mcp/tools/background_indexing.py (config path capture + worker invocation)
- src/services/background_worker.py (signature change + auto-creation logic)

**Tests Added**:
- 5 unit tests (config capture, auto-creation, error handling)
- 2 integration tests (end-to-end, fallback)

**Validation**:
- All new tests pass
- Manual testing confirms bug fixed
- No regression in existing functionality
```

**Commit**: `docs: update bug tracker with Bug 2 fix (Background Auto-Creation)`

---

## Summary: Implementation Order

**Critical Path**:
1. ✅ **Preparation** (T001-T002): Understand problem (30 min)
2. ✅ **Testing** (T003-T009): Write 7 tests FIRST (1-1.5 hours)
3. ✅ **Implementation** (T010-T015): Make tests pass (45 min)
   - T010: Capture config_path
   - T011: Update worker invocation
   - T012-T013: Update worker signature
   - T014: Implement auto-creation logic
   - T015: Remove ctx from get_session
4. ✅ **Verification** (T016-T021): Validate fix (45 min)

**Total Tasks**: 21
**Parallel Opportunities**: None (sequential, TDD-driven)
**Estimated Time**: 3-4 hours

---

## Micro-Commit Strategy

**Commit after each major step**:

1. `test: add unit test for config path capture in background indexing (Bug 2)` (T003)
2. `test: add unit test for config path fallback without ctx (Bug 2)` (T004)
3. `test: add unit test for worker auto-creation with config path (Bug 2)` (T005)
4. `test: add unit test for worker backward compatibility without config (Bug 2)` (T006)
5. `test: add unit test for auto-creation failure handling (Bug 2)` (T007)
6. `test: add integration test for background auto-creation end-to-end (Bug 2)` (T008)
7. `test: add integration test for default database fallback (Bug 2)` (T009)
8. `fix(background): capture config path in start_indexing_background (Bug 2)` (T010)
9. `fix(background): pass config_path to worker instead of ctx (Bug 2)` (T011)
10. `fix(worker): update signature to accept config_path instead of ctx (Bug 2)` (T012)
11. `fix(worker): implement auto-creation from config path (Bug 2)` (T014)
12. `fix(worker): remove ctx from get_session call (Bug 2)` (T015)
13. `docs: update bug tracker with Bug 2 fix (Background Auto-Creation)` (T021)

**Total Commits**: 13 micro-commits

---

## Risk Mitigation

**Risks Identified**:

1. **Config file race condition** (file deleted between capture and worker)
   - ✅ Mitigation: Try/except around auto-creation, log warning, continue
   - Test: T007

2. **Database already exists** (idempotency)
   - ✅ Mitigation: get_or_create_project_from_config() is idempotent
   - Test: T006

3. **Stale context in worker** (original bug)
   - ✅ Mitigation: Don't pass ctx to worker at all
   - Test: T003, T008

4. **Backward compatibility** (existing code breaks)
   - ✅ Mitigation: config_path=None is safe fallback
   - Test: T004, T006, T009, T019

**Rollback Plan**:
If issues occur, revert commits in reverse order:
- T015 → T014 → T012 → T011 → T010
- Restores original ctx-based behavior
- Background indexing will fail with original error (known state)

---

## Success Criteria

**All must be true**:

1. ✅ Background indexing auto-creates database from config file
2. ✅ Background indexing works without config (uses default database)
3. ✅ Foreground indexing remains unaffected (no regression)
4. ✅ All 7 new tests pass (5 unit + 2 integration)
5. ✅ All existing tests still pass (no regression)
6. ✅ Manual testing shows "database does not exist" error is gone
7. ✅ Error handling is graceful (logs warnings, continues when appropriate)
8. ✅ No performance regression (worker startup <200ms additional overhead)

---

## Dependencies

**Must be completed BEFORE starting Bug 2**:
- ✅ Bug 3 (error reporting) - REQUIRED for proper error visibility
- ✅ Bug 1 (baseline functionality) - RECOMMENDED for stable foundation

**Can be completed AFTER Bug 2**:
- Any other bugs or features (Bug 2 is self-contained)

---

## Notes

- **TDD Approach**: All tests written BEFORE implementation (Phase 2 before Phase 3)
- **Incremental**: Each implementation step is testable independently
- **Micro-commits**: 13 small commits, each atomic and revertable
- **Comprehensive**: 7 tests cover happy path, error cases, edge cases, backward compat
- **Production-ready**: Includes logging, error handling, graceful degradation
- **Constitutional compliance**: Maintains Principle V (Production Quality)

**Total Code Changes**: ~40 lines
- Config capture: 10 lines
- Worker signature: 2 lines
- Auto-creation block: 25 lines
- get_session fix: 1 line
- Imports: 2 lines

**Total Test Code**: ~300 lines
- Unit tests: 5 × 40 lines = 200 lines
- Integration tests: 2 × 50 lines = 100 lines
