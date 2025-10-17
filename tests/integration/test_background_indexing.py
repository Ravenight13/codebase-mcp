"""Integration tests for background indexing workflow.

Tests validate the complete end-to-end background indexing workflow:
- Job creation returns job_id immediately
- Status polling works correctly
- Job completes successfully with accurate metrics
- Error handling for invalid paths
- Security validation for path traversal

Constitutional Compliance:
- Principle VII: TDD (validates complete workflow before production)
- Principle V: Production Quality (error handling, security validation)
- Principle IV: Performance (<60s indexing for 10K files)
- Principle VIII: Type Safety (type-annotated test functions)
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.integration
@pytest.mark.asyncio
async def test_background_indexing_complete_workflow(tmp_path: Path) -> None:
    """Test complete background indexing workflow with small repository.

    Validates:
    - Job creation returns job_id
    - Status polling works
    - Job completes successfully
    - Metrics are accurate (files_indexed, chunks_created)
    - Timestamps are properly set

    Args:
        tmp_path: Pytest temporary directory fixture
    """
    # Create test repository with 4 Python files
    test_repo = tmp_path / "test-repo"
    test_repo.mkdir()

    # Create Python files with different content
    (test_repo / "file1.py").write_text("def foo(): pass\n" * 10)
    (test_repo / "file2.py").write_text("def bar(): pass\n" * 10)
    (test_repo / "file3.py").write_text("def baz(): pass\n" * 10)
    (test_repo / "file4.py").write_text("def qux(): pass\n" * 10)

    # Import MCP tools
    from src.mcp.tools.background_indexing import (
        start_indexing_background,
        get_indexing_status,
    )

    # 1. Start background indexing job
    result = await start_indexing_background.fn(
        repo_path=str(test_repo),
        project_id="test",
    )

    # Verify immediate response
    assert "job_id" in result, "Response missing job_id"
    assert result["status"] == "pending", f"Expected status 'pending', got '{result['status']}'"
    assert result["message"] == "Indexing job started", f"Unexpected message: {result['message']}"
    # Note: "test" project_id resolves to "default" if not in registry
    assert result["project_id"] in ["test", "default"], f"Unexpected project_id: {result['project_id']}'"

    job_id = result["job_id"]

    print(f"\n✅ Job created successfully: {job_id}")

    # 2. Poll status until completion (max 30 seconds)
    max_attempts = 15  # 30 seconds at 2s intervals
    final_status = None

    for attempt in range(max_attempts):
        status = await get_indexing_status.fn(
            job_id=job_id,
            project_id="default",  # Use resolved project_id
        )

        print(f"📊 Attempt {attempt + 1}: Status={status['status']}, "
              f"Files={status['files_indexed']}, "
              f"Chunks={status['chunks_created']}")

        # Check if job completed (success or failure)
        if status["status"] in ["completed", "failed"]:
            final_status = status
            break

        # Wait before next poll
        await asyncio.sleep(2)

    # Verify job completed within timeout
    assert final_status is not None, "Job did not complete within 30 seconds"

    # 3. Verify successful completion
    assert final_status["status"] == "completed", \
        f"Job failed: {final_status.get('error_message')}"

    # 4. Verify metrics
    assert final_status["files_indexed"] == 4, \
        f"Expected 4 files, got {final_status['files_indexed']}"

    assert final_status["chunks_created"] > 0, \
        "Should create at least 1 chunk from 4 Python files"

    # 5. Verify timestamps
    assert final_status["created_at"] is not None, "Missing created_at timestamp"
    assert final_status["started_at"] is not None, "Missing started_at timestamp"
    assert final_status["completed_at"] is not None, "Missing completed_at timestamp"

    # 6. Verify no error message
    assert final_status["error_message"] is None, \
        f"Unexpected error message: {final_status['error_message']}"

    print(f"\n✅ Test passed: Indexed {final_status['files_indexed']} files, "
          f"created {final_status['chunks_created']} chunks in "
          f"{attempt + 1} poll attempts")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_background_indexing_invalid_path() -> None:
    """Test background indexing with non-existent path fails gracefully.

    Validates:
    - Invalid paths trigger job failure (not crash)
    - Error message is captured and stored
    - Job status transitions to 'failed'
    - Worker handles errors gracefully
    """
    from src.mcp.tools.background_indexing import (
        start_indexing_background,
        get_indexing_status,
    )

    # Start job with non-existent path
    result = await start_indexing_background.fn(
        repo_path="/tmp/nonexistent-repo-12345",
        project_id="test",
    )

    job_id = result["job_id"]
    print(f"\n📋 Created job with invalid path: {job_id}")

    # Poll until job fails
    max_attempts = 15
    final_status = None

    for attempt in range(max_attempts):
        status = await get_indexing_status.fn(
            job_id=job_id,
            project_id="default",  # Use resolved project_id
        )

        print(f"📊 Attempt {attempt + 1}: Status={status['status']}, "
              f"Error={status.get('error_message', 'None')[:50] if status.get('error_message') else 'None'}")

        if status["status"] in ["completed", "failed"]:
            final_status = status
            break

        await asyncio.sleep(2)

    # Verify job failed (not completed)
    assert final_status is not None, "Job did not transition to terminal state within 30 seconds"
    assert final_status["status"] == "failed", \
        f"Expected status 'failed', got '{final_status['status']}'"
    assert final_status["error_message"] is not None, "Missing error message for failed job"
    assert len(final_status["error_message"]) > 0, "Error message is empty"

    print(f"\n✅ Test passed: Job failed as expected with error: "
          f"{final_status['error_message'][:100]}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_indexing_status_invalid_job_id() -> None:
    """Test get_indexing_status with invalid job_id raises ValueError.

    Validates:
    - Invalid UUID format raises ValueError with clear message
    - Valid UUID that doesn't exist raises ValueError
    - Error messages are descriptive for debugging
    """
    from src.mcp.tools.background_indexing import get_indexing_status

    # Test 1: Invalid UUID format
    print("\n📋 Testing invalid UUID format...")
    with pytest.raises(ValueError, match="Invalid job_id format"):
        await get_indexing_status.fn(
            job_id="not-a-uuid",
            project_id="default",  # Use resolved project_id
        )

    print("✅ Invalid UUID format rejected correctly")

    # Test 2: Valid UUID that doesn't exist
    print("\n📋 Testing non-existent job_id...")
    with pytest.raises(ValueError, match="Job not found"):
        await get_indexing_status.fn(
            job_id="550e8400-e29b-41d4-a716-446655440000",
            project_id="default",  # Use resolved project_id
        )

    print("✅ Non-existent job_id rejected correctly")
    print("\n✅ Test passed: Invalid job_id handling works correctly")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_start_indexing_path_validation() -> None:
    """Test start_indexing_background validates paths (security).

    Validates:
    - Relative paths are rejected
    - Path traversal sequences are rejected
    - Security validation prevents directory traversal attacks
    - Error messages are clear and actionable
    """
    from src.mcp.tools.background_indexing import start_indexing_background

    # Test 1: Relative path rejection
    print("\n📋 Testing relative path rejection...")
    with pytest.raises(ValueError, match="must be absolute"):
        await start_indexing_background.fn(
            repo_path="./relative/path",
            project_id="default",  # Use resolved project_id
        )

    print("✅ Relative path rejected correctly")

    # Test 2: Path traversal rejection
    print("\n📋 Testing path traversal rejection...")
    with pytest.raises(ValueError, match="Path traversal detected"):
        await start_indexing_background.fn(
            repo_path="/tmp/../../../etc/passwd",
            project_id="default",  # Use resolved project_id
        )

    print("✅ Path traversal rejected correctly")
    print("\n✅ Test passed: Path validation prevents security issues")
