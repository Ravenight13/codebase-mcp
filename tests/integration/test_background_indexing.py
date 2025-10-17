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
    # Note: Without a config file, explicit project_id "test" falls back to "default"
    # For config-based auto-creation, see test_config_based_project_creation
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


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.timeout(600)  # 10 minutes for large repository indexing
async def test_large_repository_indexing() -> None:
    """Test background indexing with large repository (codebase-mcp itself).

    Validates:
    - No timeout errors with real large repository
    - Job completes successfully
    - Metrics accurate (files_indexed, chunks_created)
    - Production readiness

    This test indexes the codebase-mcp project itself, which should have
    100+ Python files and may take 5-10 minutes to complete with embeddings.

    Note: Test duration depends on:
    - Repository size (number of files)
    - EMBEDDING_BATCH_SIZE setting
    - Ollama response time
    - Network conditions
    """
    from datetime import datetime

    # Use codebase-mcp repository itself (traverse up from tests/)
    test_file_path = Path(__file__).resolve()
    repo_path = test_file_path.parent.parent.parent  # tests/integration/test_*.py -> repo root

    print(f"\n📂 Testing with repository: {repo_path}")
    print(f"   (Should be codebase-mcp root directory)")

    # Verify it's the right directory
    assert (repo_path / "src").exists(), "src/ directory not found"
    assert (repo_path / "pyproject.toml").exists(), "pyproject.toml not found"

    # Import MCP tools
    from src.mcp.tools.background_indexing import (
        start_indexing_background,
        get_indexing_status,
    )

    # 1. Start background indexing
    result = await start_indexing_background.fn(
        repo_path=str(repo_path),
        project_id="test-large-repo",
    )

    job_id = result["job_id"]
    print(f"✅ Job created: {job_id}")

    # 2. Poll until completion (allow up to 10 minutes)
    max_attempts = 300  # 10 minutes at 2s intervals
    final_status = None

    for attempt in range(max_attempts):
        status = await get_indexing_status.fn(
            job_id=job_id,
            project_id="test-large-repo",
        )

        # Log progress every 30 seconds
        if attempt % 15 == 0:
            print(f"⏳ [{attempt * 2}s] Status: {status['status']}, "
                  f"Files: {status['files_indexed']}, "
                  f"Chunks: {status['chunks_created']}")

        # Check if completed
        if status["status"] in ["completed", "failed"]:
            final_status = status
            break

        await asyncio.sleep(2)

    # 3. Verify completion within timeout
    assert final_status is not None, \
        "Job did not complete within 10 minutes (may need longer timeout for very large repos)"

    # 4. Verify successful completion
    assert final_status["status"] == "completed", \
        f"Job failed: {final_status.get('error_message')}"

    # 5. Verify realistic metrics
    files_indexed = final_status["files_indexed"]
    chunks_created = final_status["chunks_created"]

    assert files_indexed > 50, \
        f"Expected >50 files, got {files_indexed} (codebase-mcp should have many Python files)"

    assert chunks_created > 500, \
        f"Expected >500 chunks, got {chunks_created}"

    # 6. Verify timestamps
    assert final_status["created_at"] is not None, "Missing created_at timestamp"
    assert final_status["started_at"] is not None, "Missing started_at timestamp"
    assert final_status["completed_at"] is not None, "Missing completed_at timestamp"

    # 7. Verify no error message
    assert final_status["error_message"] is None, \
        f"Unexpected error message: {final_status['error_message']}"

    # 8. Calculate duration
    started = datetime.fromisoformat(final_status["started_at"])
    completed = datetime.fromisoformat(final_status["completed_at"])
    duration = (completed - started).total_seconds()

    print(f"\n✅ Large repository test PASSED!")
    print(f"   Files indexed: {files_indexed}")
    print(f"   Chunks created: {chunks_created}")
    print(f"   Duration: {duration:.1f}s")
    print(f"   Repository: {repo_path}")

    # Sanity check: duration should be reasonable (not instant, not forever)
    assert 5 < duration < 600, \
        f"Duration {duration}s seems unrealistic (expected 5-600s)"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_job_state_persistence() -> None:
    """Test job state persists across simulated server restarts.

    Validates:
    - Job record survives database pool closure
    - Status queryable after restart
    - All fields preserved

    Constitutional Compliance:
    - Principle VII: TDD (validates persistence before production)
    - Principle II: Local-First (validates offline persistence)
    """
    from src.database.session import engine
    from src.models.indexing_job import IndexingJob
    from datetime import datetime
    from sqlalchemy.ext.asyncio import AsyncSession
    import uuid

    # 1. Create job directly in database (simulating tool call)
    job_id = uuid.uuid4()
    test_repo_path = "/tmp/test-repo-persistence"

    async with AsyncSession(engine) as session:
        job = IndexingJob(
            id=job_id,
            repo_path=test_repo_path,
            project_id="test-persistence",
            status="pending",
            files_indexed=0,
            chunks_created=0,
            created_at=datetime.utcnow(),
        )
        session.add(job)
        await session.commit()

    print(f"✅ Created job {job_id} with status=pending")

    # 2. Simulate server restart (dispose engine connections)
    await engine.dispose()
    print("🔄 Simulated server restart (engine disposed)")

    # 3. Query job after restart using MCP tool
    from src.mcp.tools.background_indexing import get_indexing_status

    status = await get_indexing_status.fn(
        job_id=str(job_id),
        project_id="test-persistence",
    )

    # 4. Verify state preserved
    assert status["job_id"] == str(job_id), "Job ID mismatch"
    assert status["status"] == "pending", f"Expected pending, got {status['status']}"
    assert status["repo_path"] == test_repo_path, "Repo path mismatch"
    assert status["project_id"] == "test-persistence", "Project ID mismatch"
    assert status["files_indexed"] == 0, "Files indexed should be 0"
    assert status["chunks_created"] == 0, "Chunks created should be 0"
    assert status["created_at"] is not None, "Created timestamp missing"

    print(f"✅ Test passed: Job state persisted across restart")
    print(f"   Job ID: {status['job_id']}")
    print(f"   Status: {status['status']}")
    print(f"   Repo: {status['repo_path']}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_job_state_persistence_with_updates() -> None:
    """Test job state with updates persists across simulated restart.

    Validates:
    - Updated job fields survive restart
    - Timestamps preserved
    - Metrics preserved

    Constitutional Compliance:
    - Principle VII: TDD (validates persistence before production)
    - Principle II: Local-First (validates offline persistence)
    """
    from src.database.session import engine
    from src.models.indexing_job import IndexingJob
    from datetime import datetime
    from sqlalchemy.ext.asyncio import AsyncSession
    import uuid

    # 1. Create job with completed status and metrics
    job_id = uuid.uuid4()
    started_time = datetime.utcnow()
    completed_time = datetime.utcnow()

    async with AsyncSession(engine) as session:
        job = IndexingJob(
            id=job_id,
            repo_path="/tmp/test-completed",
            project_id="test-persistence",
            status="completed",
            files_indexed=42,
            chunks_created=420,
            started_at=started_time,
            completed_at=completed_time,
            created_at=datetime.utcnow(),
        )
        session.add(job)
        await session.commit()

    print(f"✅ Created completed job {job_id}")

    # 2. Simulate server restart
    await engine.dispose()
    print("🔄 Simulated server restart")

    # 3. Query job after restart
    from src.mcp.tools.background_indexing import get_indexing_status

    status = await get_indexing_status.fn(
        job_id=str(job_id),
        project_id="test-persistence",
    )

    # 4. Verify all fields preserved
    assert status["status"] == "completed"
    assert status["files_indexed"] == 42
    assert status["chunks_created"] == 420
    assert status["started_at"] is not None
    assert status["completed_at"] is not None
    assert status["error_message"] is None

    print(f"✅ Test passed: Updated job state persisted")
    print(f"   Files indexed: {status['files_indexed']}")
    print(f"   Chunks created: {status['chunks_created']}")
