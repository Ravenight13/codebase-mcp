"""Unit tests for Bug 2: Background indexing auto-creation from config.

Tests verify that background indexing captures config path in foreground
(while FastMCP Context is valid) and passes it to worker for auto-creation.

Root Cause:
    FastMCP Context objects are request-scoped and become stale when
    background worker executes after MCP tool returns.

Fix:
    1. Capture config path in start_indexing_background (while ctx valid)
    2. Pass config_path to worker instead of ctx
    3. Worker calls get_or_create_project_from_config() at startup
"""

import asyncio
import logging
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest


@pytest.fixture
def mock_ctx():
    """Mock FastMCP Context for testing."""
    ctx = Mock()
    ctx.session_id = f"test-session-{uuid4().hex[:8]}"
    ctx.info = AsyncMock()  # Make ctx.info async-compatible
    ctx.debug = AsyncMock()
    ctx.warn = AsyncMock()
    ctx.error = AsyncMock()
    return ctx


@pytest.fixture
def mock_project():
    """Mock Project object for testing."""
    project = Mock()
    project.id = str(uuid4())
    project.name = "test-project"
    project.database_name = "cb_proj_test_project_abc12345"
    return project


async def test_config_path_capture_success(tmp_path, mock_ctx):
    """Verify config path is captured when ctx is valid.

    This is the core Bug 2 fix: config path must be resolved in foreground
    (while ctx is valid) before background task starts.
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

    # Setup: Mock session context manager to return working directory
    mock_session_mgr = Mock()
    mock_session_mgr.get_working_directory = AsyncMock(return_value=str(tmp_path))

    # Setup: Mock background worker to capture arguments
    captured_args = {}

    async def capture_worker_args(**kwargs):
        captured_args.update(kwargs)
        # Don't actually run worker
        return None

    with patch('src.services.background_worker._background_indexing_worker', capture_worker_args):
        with patch('src.auto_switch.session_context.get_session_context_manager', return_value=mock_session_mgr):
            # Execute: Call start_indexing_background with ctx
            from src.mcp.tools.background_indexing import start_indexing_background

            result = await start_indexing_background.fn(
                repo_path=str(repo_path),
                project_id=None,
                ctx=mock_ctx,
            )

    # Assert: config_path was captured and passed to worker
    assert "config_path" in captured_args, "Worker should receive config_path parameter"
    assert captured_args["config_path"] is not None, "config_path should be resolved"
    assert str(captured_args["config_path"]) == str(config_file), \
        f"Expected {config_file}, got {captured_args['config_path']}"

    # Assert: ctx should NOT be passed to worker
    assert "ctx" not in captured_args or captured_args["ctx"] is None, \
        "ctx should not be passed to worker"


async def test_config_path_capture_no_ctx(tmp_path):
    """Verify config_path=None when ctx is None (graceful fallback).

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
        from src.mcp.tools.background_indexing import start_indexing_background

        result = await start_indexing_background.fn(
            repo_path=str(repo_path),
            project_id=None,
            ctx=None,  # No context
        )

    # Assert: config_path should be None (no auto-creation)
    assert captured_args.get("config_path") is None, \
        "config_path should be None when ctx is None"


async def test_worker_auto_creation_with_config(tmp_path, mock_project):
    """Verify worker triggers auto-creation when config_path is provided.

    This is the core Bug 2 fix validation: worker must call
    get_or_create_project_from_config() at startup if config_path is not None.
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

    # Setup: Mock auto-creation to capture calls
    auto_create_called = False
    auto_create_config_path = None

    async def mock_auto_create(config_path, registry=None):
        nonlocal auto_create_called, auto_create_config_path
        auto_create_called = True
        auto_create_config_path = config_path
        return mock_project

    # Setup: Mock database operations
    with patch('src.database.auto_create.get_or_create_project_from_config', mock_auto_create):
        with patch('src.services.background_worker.update_job', AsyncMock()):
            with patch('src.services.background_worker.get_session'):
                with patch('src.services.indexer.index_repository', AsyncMock(return_value={"files_indexed": 1})):
                    # Execute: Run worker with config_path
                    from src.services.background_worker import _background_indexing_worker

                    await _background_indexing_worker(
                        job_id=uuid4(),
                        repo_path=str(repo_path),
                        project_id="worker-test",
                        config_path=config_file,  # NEW PARAMETER
                    )

    # Assert: Auto-creation was called
    assert auto_create_called, "Worker should call get_or_create_project_from_config"
    assert str(auto_create_config_path) == str(config_file), \
        f"Expected {config_file}, got {auto_create_config_path}"


async def test_worker_auto_creation_without_config(tmp_path):
    """Verify worker skips auto-creation when config_path is None.

    Backward compatibility test: worker should work with config_path=None
    if the project database already exists (e.g., created manually).
    """
    # Setup: Create test repo
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    (repo_path / "test.py").write_text("def test(): pass")

    # Setup: Mock auto-creation to detect calls
    auto_create_called = False

    async def mock_auto_create(config_path, registry=None):
        nonlocal auto_create_called
        auto_create_called = True
        raise AssertionError("Auto-creation should not be called when config_path is None")

    # Setup: Mock database operations
    with patch('src.database.auto_create.get_or_create_project_from_config', mock_auto_create):
        with patch('src.services.background_worker.update_job', AsyncMock()):
            with patch('src.services.background_worker.get_session'):
                with patch('src.services.indexer.index_repository', AsyncMock(return_value={"files_indexed": 1})):
                    # Execute: Run worker WITHOUT config_path
                    from src.services.background_worker import _background_indexing_worker

                    await _background_indexing_worker(
                        job_id=uuid4(),
                        repo_path=str(repo_path),
                        project_id="existing-project",
                        config_path=None,  # No config path
                    )

    # Assert: Auto-creation was NOT called
    assert not auto_create_called, "Auto-creation should be skipped when config_path is None"


async def test_worker_auto_creation_failure(tmp_path, caplog):
    """Verify worker logs warning but continues if auto-creation fails.

    Error handling test: if auto-creation fails (e.g., invalid config,
    permission error), worker should log warning and attempt to proceed
    anyway (database might exist already).
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

    # Setup: Mock auto-creation to raise error
    async def failing_auto_create(config_path, registry=None):
        raise ValueError("Invalid config: missing project.name")

    # Setup: Mock database operations
    with patch('src.database.auto_create.get_or_create_project_from_config', failing_auto_create):
        with patch('src.services.background_worker.update_job', AsyncMock()):
            with patch('src.services.background_worker.get_session'):
                with patch('src.services.indexer.index_repository', AsyncMock(return_value={"files_indexed": 1})):
                    with caplog.at_level(logging.WARNING):
                        # Execute: Run worker with invalid config
                        from src.services.background_worker import _background_indexing_worker

                        await _background_indexing_worker(
                            job_id=uuid4(),
                            repo_path=str(repo_path),
                            project_id="test-project",
                            config_path=config_file,
                        )

    # Assert: Warning was logged
    assert any("Auto-creation failed" in record.message for record in caplog.records), \
        "Should log warning when auto-creation fails"
