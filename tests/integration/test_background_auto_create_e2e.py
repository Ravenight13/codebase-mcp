"""Integration tests for Bug 2: End-to-end background indexing auto-creation.

Tests verify the complete flow:
1. Config file exists with project name
2. MCP tool captures config path (while ctx valid)
3. Background worker auto-creates database
4. Indexing completes successfully
5. Files are searchable in new database
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest


@pytest.mark.integration
async def test_background_indexing_auto_creates_from_config(tmp_path):
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

    # Setup: Mock FastMCP context
    mock_ctx = Mock()
    mock_ctx.session_id = f"e2e-session-{uuid4().hex[:8]}"

    # Setup: Mock session context manager to return working directory
    mock_session_mgr = Mock()
    mock_session_mgr.get_working_directory = AsyncMock(return_value=str(tmp_path))

    # Verify: Database doesn't exist yet
    database_name_prefix = f"cb_proj_{project_name}_"
    result = await asyncio.create_subprocess_exec(
        "psql", "-lqt",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await result.communicate()
    assert database_name_prefix not in stdout.decode(), \
        "Database should not exist before indexing"

    # Execute: Start background indexing
    with patch('src.auto_switch.session_context.get_session_context_manager', return_value=mock_session_mgr):
        from src.mcp.tools.background_indexing import start_indexing_background

        result = await start_indexing_background.fn(
            repo_path=str(repo_path),
            project_id=None,
            ctx=mock_ctx,
        )

    job_id = result["job_id"]

    # Wait: Poll until job completes (max 30 seconds)
    from src.mcp.tools.background_indexing import get_indexing_status

    max_attempts = 30
    status = None
    for attempt in range(max_attempts):
        status = await get_indexing_status.fn(job_id=job_id, project_id=None, ctx=None)
        if status["status"] in ["completed", "failed"]:
            break
        await asyncio.sleep(1)

    # Assert: Job completed successfully
    assert status is not None, "Should have received status"
    assert status["status"] == "completed", \
        f"Job should complete, got: {status['status']}, error: {status.get('error_message')}"
    assert status["files_indexed"] == 2, \
        f"Should index 2 files, got: {status['files_indexed']}"

    # Assert: Database was created
    result = await asyncio.create_subprocess_exec(
        "psql", "-lqt",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await result.communicate()
    assert database_name_prefix in stdout.decode(), \
        f"Database {database_name_prefix}* should exist after indexing"

    # Assert: Files are searchable
    with patch('src.auto_switch.session_context.get_session_context_manager', return_value=mock_session_mgr):
        from src.mcp.tools.search import search_code

        search_results = await search_code.fn(
            query="hello world function",
            project_id=None,
            ctx=mock_ctx,  # Uses same session context
        )

    assert len(search_results["results"]) > 0, "Should find indexed files via search"
    assert any("hello_world" in r["content"] for r in search_results["results"]), \
        "Search should return hello_world function"
