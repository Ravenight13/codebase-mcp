"""Integration test for 4-layer database unavailable fallback system.

This test validates quickstart.md Scenario 4 - database unavailability fallback:
1. PostgreSQL (primary) → 2. SQLite cache (30-min TTL) →
3. Git history → 4. Manual markdown file

Test Flow:
- Setup: Create work items in PostgreSQL, sync to SQLite, generate markdown
- Test 1: PostgreSQL down → Query via SQLite cache (layer 2)
- Test 2: SQLite cache cleared → Query via git history (layer 3)
- Test 3: Git unavailable → Query via markdown file (layer 4)
- Test 4: Update when PostgreSQL down → Parallel writes to SQLite + markdown
- Verify: Queries succeed with warnings (not errors), system continues

Constitutional Compliance:
- Principle II: Local-First Architecture (fallback to local data sources)
- Principle V: Production Quality (graceful degradation, no hard failures)
- Principle VII: TDD (validates acceptance criteria from spec)
- Principle VIII: Type Safety (full mypy --strict compliance)
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import aiosqlite
import pytest
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.models.database import Base
from src.models.task import WorkItem
from src.services.cache import SQLiteCache
from src.services.fallback import (
    AllFallbackLayersFailedError,
    InvalidCacheDataError,
    PostgreSQLUnavailableError,
    check_postgresql_health,
    execute_with_fallback,
    get_fallback_data,
    write_with_fallback,
    CACHE_DB_PATH,
    MARKDOWN_FALLBACK_PATH,
)
from src.services.git_history import get_work_item_from_branch
# Note: markdown service imports skipped - not needed for fallback testing

# ==============================================================================
# Test Configuration
# ==============================================================================

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/codebase_mcp_test"
)

# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture(scope="function")
def temp_cache_dir() -> Path:
    """Create temporary directory for cache database.

    Returns:
        Path to temporary cache directory

    Cleanup:
        Removes temporary directory after test
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="cache_test_"))
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def temp_markdown_file() -> Path:
    """Create temporary markdown file for fallback.

    Returns:
        Path to temporary markdown file

    Cleanup:
        Removes temporary file after test
    """
    temp_file = Path(tempfile.mktemp(suffix=".md", prefix="project_status_"))
    temp_file.write_text("# Project Status\n\n## Work Items\n\n", encoding="utf-8")
    yield temp_file
    if temp_file.exists():
        temp_file.unlink()


@pytest.fixture(scope="function")
async def test_session() -> AsyncSession:
    """Create test database session using existing database.

    Uses existing test database without recreating schema.
    This avoids foreign key issues with incomplete migrations.

    Yields:
        AsyncSession for database operations

    Cleanup:
        Rolls back transaction and closes session
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
    )

    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        # Start transaction (will be rolled back after test)
        async with session.begin():
            yield session
            # Rollback to clean up test data
            await session.rollback()

    await engine.dispose()


@pytest.fixture(scope="function")
async def seeded_work_items(
    test_session: AsyncSession,
    temp_cache_dir: Path,
    temp_markdown_file: Path,
) -> dict[str, Any]:
    """Seed test database with work items and sync to all fallback layers.

    Creates work items in PostgreSQL, syncs to SQLite cache, and generates
    markdown file for complete 4-layer fallback testing.

    Args:
        test_session: Test database session
        temp_cache_dir: Temporary cache directory
        temp_markdown_file: Temporary markdown file

    Returns:
        dict containing:
            - work_item_ids: list[UUID] of created work items
            - cache_path: Path to SQLite cache database
            - markdown_path: Path to markdown fallback file
            - work_item_data: dict[UUID, dict] mapping IDs to data
    """
    # Create 3 test work items in PostgreSQL
    work_items: list[WorkItem] = []
    work_item_data: dict[UUID, dict[str, Any]] = {}

    for i in range(3):
        work_item = WorkItem(
            id=uuid4(),
            item_type="task",
            title=f"Test Task {i+1}",
            description=f"Test description for task {i+1}",
            status="active",
            metadata_={"priority": "high" if i == 0 else "medium"},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by="test-client",
            version=1,
        )
        test_session.add(work_item)
        work_items.append(work_item)

        # Store work item data for later validation
        work_item_data[work_item.id] = {
            "id": str(work_item.id),
            "item_type": work_item.item_type,
            "title": work_item.title,
            "description": work_item.description,
            "status": work_item.status,
            "metadata_": work_item.metadata_,
            "created_at": work_item.created_at.isoformat(),
            "updated_at": work_item.updated_at.isoformat(),
            "created_by": work_item.created_by,
            "version": work_item.version,
        }

    await test_session.commit()

    # Sync to SQLite cache (layer 2)
    cache_db_path = temp_cache_dir / "fallback_cache.db"
    async with SQLiteCache(cache_db_path) as cache:
        for work_item in work_items:
            await cache.set_work_item(work_item.id, work_item_data[work_item.id])

    # Generate markdown file (layer 4)
    markdown_content = f"""# Project Status

## Work Items ({len(work_items)} total)

"""
    for work_item in work_items:
        markdown_content += f"""### {work_item.title} ({work_item.item_type})
- **Status**: {work_item.status}
- **Created**: {work_item.created_at.isoformat()}
- **Created By**: {work_item.created_by}

"""

    temp_markdown_file.write_text(markdown_content, encoding="utf-8")

    return {
        "work_item_ids": [item.id for item in work_items],
        "cache_path": cache_db_path,
        "markdown_path": temp_markdown_file,
        "work_item_data": work_item_data,
    }


# ==============================================================================
# Layer 1: PostgreSQL Health Check
# ==============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgresql_health_check_success(test_session: AsyncSession) -> None:
    """Test PostgreSQL health check returns True when database is available.

    Validates:
    - Health check executes SELECT 1 query
    - Returns True for healthy database
    - Completes in <100ms

    Args:
        test_session: Test database session
    """
    start_time = time.perf_counter()
    is_healthy = await check_postgresql_health(test_session)
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    assert is_healthy is True, "PostgreSQL should be healthy"
    assert elapsed_ms < 100.0, f"Health check took {elapsed_ms:.1f}ms (expected <100ms)"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgresql_health_check_failure_timeout() -> None:
    """Test PostgreSQL health check returns False on connection timeout.

    Validates:
    - Health check handles connection timeout gracefully
    - Returns False (not exception) on timeout
    - Does not exceed timeout threshold
    """
    # Create mock session that times out
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute = AsyncMock(side_effect=asyncio.TimeoutError("Connection timed out"))

    start_time = time.perf_counter()
    is_healthy = await check_postgresql_health(mock_session)
    elapsed = time.perf_counter() - start_time

    assert is_healthy is False, "Health check should return False on timeout"
    assert elapsed < 3.0, f"Health check took {elapsed:.1f}s (expected <3s)"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgresql_health_check_failure_operational_error() -> None:
    """Test PostgreSQL health check returns False on OperationalError.

    Validates:
    - Health check handles database connection errors
    - Returns False (not exception) on OperationalError
    """
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute = AsyncMock(
        side_effect=OperationalError("Connection refused", params=None, orig=None)
    )

    is_healthy = await check_postgresql_health(mock_session)

    assert is_healthy is False, "Health check should return False on OperationalError"


# ==============================================================================
# Layer 2: SQLite Cache Fallback
# ==============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fallback_layer_2_sqlite_cache_hit(
    test_session: AsyncSession,
    seeded_work_items: dict[str, Any],
) -> None:
    """Test fallback to SQLite cache when PostgreSQL is unavailable.

    Scenario:
    - PostgreSQL down (mocked connection failure)
    - SQLite cache has fresh data (<30 minutes old)
    - Query succeeds with warning about using cache

    Args:
        test_session: Test database session (will be mocked as unavailable)
        seeded_work_items: Seeded work items in all layers
    """
    work_item_id = seeded_work_items["work_item_ids"][0]
    cache_path = seeded_work_items["cache_path"]
    expected_data = seeded_work_items["work_item_data"][work_item_id]

    # Mock PostgreSQL failure
    async def mock_query_failure(session: AsyncSession) -> None:
        raise OperationalError("Connection refused", params=None, orig=None)

    # Patch cache path to use test cache
    with patch("src.services.fallback.CACHE_DB_PATH", cache_path):
        # Execute query with fallback
        data, layer, warnings = await execute_with_fallback(
            query_func=mock_query_failure,
            session=test_session,
            fallback_query_type="work_item",
            fallback_params={"id": str(work_item_id)},
            fallback_enabled=True,
        )

    # Verify fallback to layer 2 (SQLite cache)
    assert layer == "sqlite_cache", f"Expected sqlite_cache layer, got {layer}"
    assert data is not None, "Data should be returned from cache"

    # Verify warnings indicate PostgreSQL unavailable
    assert len(warnings) > 0, "Should have warnings about PostgreSQL unavailability"
    assert any("PostgreSQL unavailable" in w for w in warnings), \
        "Should warn about PostgreSQL unavailability"

    # Verify data correctness
    assert data["id"] == expected_data["id"], "Cached data ID should match"
    assert data["title"] == expected_data["title"], "Cached data title should match"
    assert data["status"] == expected_data["status"], "Cached data status should match"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fallback_layer_2_cache_stale_data(
    test_session: AsyncSession,
    temp_cache_dir: Path,
) -> None:
    """Test SQLite cache rejects stale data exceeding 30-minute TTL.

    Scenario:
    - Cache entry older than 30 minutes
    - Cache layer rejects stale entry
    - Fallback cascades to layer 3 (git history)

    Args:
        test_session: Test database session
        temp_cache_dir: Temporary cache directory
    """
    cache_path = temp_cache_dir / "stale_cache.db"
    work_item_id = uuid4()

    # Create cache with stale entry (>30 minutes old)
    async with aiosqlite.connect(str(cache_path)) as db:
        # Create schema
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS cached_work_items (
                id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                cached_at REAL NOT NULL
            )
            """
        )

        # Insert stale entry (2 hours old)
        stale_timestamp = time.time() - (2 * 60 * 60)  # 2 hours ago
        stale_data = json.dumps({
            "id": str(work_item_id),
            "title": "Stale Work Item",
            "status": "active",
        })

        await db.execute(
            "INSERT INTO cached_work_items (id, data, cached_at) VALUES (?, ?, ?)",
            (str(work_item_id), stale_data, stale_timestamp),
        )
        await db.commit()

    # Mock PostgreSQL failure
    async def mock_query_failure(session: AsyncSession) -> None:
        raise OperationalError("Connection refused", params=None, orig=None)

    # Attempt to query with stale cache
    with patch("src.services.fallback.CACHE_DB_PATH", cache_path):
        # This should cascade past layer 2 due to staleness
        # Layer 3 (git) and layer 4 (markdown) will also fail (not mocked)
        # So we expect AllFallbackLayersFailedError
        with pytest.raises(AllFallbackLayersFailedError) as exc_info:
            await execute_with_fallback(
                query_func=mock_query_failure,
                session=test_session,
                fallback_query_type="work_item",
                fallback_params={"id": str(work_item_id)},
                fallback_enabled=True,
            )

        # Verify error message indicates all layers failed
        assert "All fallback layers exhausted" in str(exc_info.value)


# ==============================================================================
# Layer 3: Git History Fallback
# ==============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fallback_layer_3_git_history(
    test_session: AsyncSession,
    temp_cache_dir: Path,
) -> None:
    """Test fallback to git history when PostgreSQL and cache are unavailable.

    Scenario:
    - PostgreSQL down
    - SQLite cache miss (no cached entry)
    - Git history provides work item from branch name

    Args:
        test_session: Test database session
        temp_cache_dir: Temporary cache directory
    """
    # Use current branch for testing (should match pattern)
    branch_name = "003-database-backed-project"

    # Mock PostgreSQL failure
    async def mock_query_failure(session: AsyncSession) -> None:
        raise OperationalError("Connection refused", params=None, orig=None)

    # Create empty cache (cache miss)
    cache_path = temp_cache_dir / "empty_cache.db"
    async with SQLiteCache(cache_path):
        pass  # Just initialize schema, no data

    # Mock git history to return work item
    expected_git_data = {
        "title": "database backed project",
        "item_type": "project",
        "branch_name": branch_name,
        "feature_number": 3,
    }

    with patch("src.services.fallback.CACHE_DB_PATH", cache_path):
        with patch("src.services.fallback._get_from_git_history") as mock_git:
            mock_git.return_value = (expected_git_data, ["Data from git history"])

            # Execute query with fallback
            data, layer, warnings = await execute_with_fallback(
                query_func=mock_query_failure,
                session=test_session,
                fallback_query_type="work_item",
                fallback_params={"id": "003"},
                fallback_enabled=True,
            )

    # Verify fallback to layer 3 (git history)
    assert layer == "git_history", f"Expected git_history layer, got {layer}"
    assert data is not None, "Data should be returned from git history"

    # Verify warnings
    assert len(warnings) > 0, "Should have warnings"
    assert any("PostgreSQL unavailable" in w for w in warnings)
    assert any("git history" in w.lower() for w in warnings)

    # Verify data matches git history
    assert data["title"] == expected_git_data["title"]
    assert data["branch_name"] == expected_git_data["branch_name"]


# ==============================================================================
# Layer 4: Markdown Fallback
# ==============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fallback_layer_4_markdown_file(
    test_session: AsyncSession,
    seeded_work_items: dict[str, Any],
) -> None:
    """Test fallback to markdown file when all other layers fail.

    Scenario:
    - PostgreSQL down
    - SQLite cache miss
    - Git history unavailable
    - Markdown file provides final fallback

    Args:
        test_session: Test database session
        seeded_work_items: Seeded work items with markdown file
    """
    markdown_path = seeded_work_items["markdown_path"]

    # Mock PostgreSQL failure
    async def mock_query_failure(session: AsyncSession) -> None:
        raise OperationalError("Connection refused", params=None, orig=None)

    # Create empty cache (cache miss)
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_path = Path(temp_dir) / "empty_cache.db"
        async with SQLiteCache(cache_path):
            pass

        # Mock all layers to force markdown fallback
        with patch("src.services.fallback.CACHE_DB_PATH", cache_path):
            with patch("src.services.fallback.MARKDOWN_FALLBACK_PATH", markdown_path):
                with patch("src.services.fallback._get_from_git_history") as mock_git:
                    # Git returns None (no data found)
                    mock_git.return_value = (None, ["No data in git history"])

                    # Execute query with fallback
                    data, layer, warnings = await execute_with_fallback(
                        query_func=mock_query_failure,
                        session=test_session,
                        fallback_query_type="work_item",
                        fallback_params={"id": "unknown"},
                        fallback_enabled=True,
                    )

        # Verify fallback to layer 4 (markdown)
        assert layer == "markdown_file", f"Expected markdown_file layer, got {layer}"
        assert data is not None, "Data should be returned from markdown"

        # Verify warnings indicate all prior layers failed
        assert len(warnings) > 0
        assert any("PostgreSQL unavailable" in w for w in warnings)
        assert any("Cache" in w for w in warnings)
        assert any("manual .project_status.md" in w.lower() for w in warnings)

        # Verify markdown content is returned
        assert "content" in data
        assert "Work Items" in data["content"], "Markdown should contain work items"


# ==============================================================================
# Write Operations During Database Unavailability
# ==============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_parallel_writes_on_postgresql_failure(
    test_session: AsyncSession,
    temp_cache_dir: Path,
    temp_markdown_file: Path,
) -> None:
    """Test parallel writes to SQLite cache and markdown on PostgreSQL failure.

    Scenario (per spec FR-029 clarification #2):
    - PostgreSQL unavailable
    - Write operation fails on PostgreSQL
    - System writes to BOTH SQLite cache AND markdown file in parallel
    - Both writes succeed (maximum redundancy)
    - Warning returned about pending PostgreSQL sync

    Args:
        test_session: Test database session
        temp_cache_dir: Temporary cache directory
        temp_markdown_file: Temporary markdown file
    """
    cache_path = temp_cache_dir / "write_cache.db"

    # Initialize cache schema
    async with SQLiteCache(cache_path):
        pass

    # Prepare write data
    work_item_id = uuid4()
    write_data = {
        "type": "work_item",
        "id": str(work_item_id),
        "title": "Updated During PostgreSQL Outage",
        "status": "in_progress",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    # Mock PostgreSQL write failure
    async def mock_write_failure(session: AsyncSession) -> None:
        raise OperationalError("Connection refused", params=None, orig=None)

    # Execute write with fallback
    with patch("src.services.fallback.CACHE_DB_PATH", cache_path):
        with patch("src.services.fallback.MARKDOWN_FALLBACK_PATH", temp_markdown_file):
            success, layer, warnings = await write_with_fallback(
                write_func=mock_write_failure,
                session=test_session,
                data=write_data,
                fallback_enabled=True,
            )

    # Verify write succeeded to fallback layers
    assert success is True, "Write should succeed to fallback layers"
    assert layer == "sqlite_cache", "Write should target cache layer"

    # Verify warnings indicate PostgreSQL failure and pending sync
    assert len(warnings) > 0
    assert any("PostgreSQL write failed" in w for w in warnings)
    assert any("sync to PostgreSQL when reconnected" in w for w in warnings)

    # Verify data written to SQLite cache
    async with SQLiteCache(cache_path) as cache:
        cached_data = await cache.get_work_item(work_item_id)
        assert cached_data is not None, "Data should be in cache"
        assert cached_data["title"] == write_data["title"]
        assert cached_data["status"] == write_data["status"]

    # Verify data written to markdown file
    markdown_content = temp_markdown_file.read_text(encoding="utf-8")
    assert "FALLBACK WRITE" in markdown_content, "Markdown should have fallback marker"
    assert write_data["title"] in markdown_content, "Markdown should contain update"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_write_fallback_both_layers_fail() -> None:
    """Test write failure when both cache and markdown writes fail.

    Scenario:
    - PostgreSQL unavailable
    - SQLite cache write fails (disk full, permissions)
    - Markdown write fails (file locked, permissions)
    - System returns failure with comprehensive warnings

    Expected:
    - success=False
    - Warnings list all failure reasons
    - No exceptions raised (graceful degradation)
    """
    # Mock PostgreSQL write failure
    async def mock_write_failure(session: AsyncSession) -> None:
        raise OperationalError("Connection refused", params=None, orig=None)

    write_data = {
        "type": "work_item",
        "id": str(uuid4()),
        "title": "Test Write",
    }

    # Mock cache write failure
    with patch("src.services.fallback._write_to_sqlite_cache") as mock_cache:
        mock_cache.side_effect = RuntimeError("Disk full")

        # Mock markdown write failure
        with patch("src.services.fallback._write_to_markdown_fallback") as mock_markdown:
            mock_markdown.side_effect = OSError("Permission denied")

            # Create mock session
            mock_session = AsyncMock(spec=AsyncSession)

            # Execute write (should handle all failures gracefully)
            success, layer, warnings = await write_with_fallback(
                write_func=mock_write_failure,
                session=mock_session,
                data=write_data,
                fallback_enabled=True,
            )

    # Verify graceful failure
    assert success is False, "Write should fail when all layers fail"
    assert len(warnings) > 0, "Should have warnings about failures"
    assert any("PostgreSQL write failed" in w for w in warnings)
    assert any("Fallback writes failed" in w for w in warnings)


# ==============================================================================
# All Layers Failed Error Handling
# ==============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_all_fallback_layers_failed_error() -> None:
    """Test AllFallbackLayersFailedError when all 4 layers fail.

    Scenario:
    - PostgreSQL unavailable
    - SQLite cache miss
    - Git history returns no data
    - Markdown file not found
    - Exception raised with comprehensive error message
    """
    # Mock PostgreSQL failure
    async def mock_query_failure(session: AsyncSession) -> None:
        raise OperationalError("Connection refused", params=None, orig=None)

    # Mock cache miss
    with patch("src.services.fallback._get_from_sqlite_cache") as mock_cache:
        mock_cache.side_effect = FileNotFoundError("Cache database not found")

        # Mock git failure
        with patch("src.services.fallback._get_from_git_history") as mock_git:
            mock_git.return_value = (None, ["No data in git"])

            # Mock markdown failure
            with patch("src.services.fallback._get_from_markdown_fallback") as mock_markdown:
                mock_markdown.side_effect = FileNotFoundError("Markdown file not found")

                # Create mock session
                mock_session = AsyncMock(spec=AsyncSession)

                # Execute query expecting failure
                with pytest.raises(AllFallbackLayersFailedError) as exc_info:
                    await execute_with_fallback(
                        query_func=mock_query_failure,
                        session=mock_session,
                        fallback_query_type="work_item",
                        fallback_params={"id": "unknown"},
                        fallback_enabled=True,
                    )

                # Verify error message is comprehensive
                error_msg = str(exc_info.value)
                assert "All fallback layers exhausted" in error_msg
                assert "Warnings:" in error_msg


# ==============================================================================
# System Continues Operation (No Hard Failures)
# ==============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_system_continues_with_warnings_not_errors(
    test_session: AsyncSession,
    seeded_work_items: dict[str, Any],
) -> None:
    """Test system continues operating with warnings (not errors) on PostgreSQL failure.

    Validates spec FR-030: System MUST continue operating with warnings (not errors)
    when database is unavailable.

    Scenario:
    - PostgreSQL down
    - Multiple queries executed
    - All queries return data with warnings
    - No exceptions raised (graceful degradation)

    Args:
        test_session: Test database session
        seeded_work_items: Seeded work items in all layers
    """
    cache_path = seeded_work_items["cache_path"]
    work_item_ids = seeded_work_items["work_item_ids"]

    # Mock PostgreSQL failure
    async def mock_query_failure(session: AsyncSession) -> None:
        raise OperationalError("Connection refused", params=None, orig=None)

    # Execute multiple queries (should all succeed via cache)
    results: list[tuple[Any, str, list[str]]] = []

    with patch("src.services.fallback.CACHE_DB_PATH", cache_path):
        for work_item_id in work_item_ids:
            data, layer, warnings = await execute_with_fallback(
                query_func=mock_query_failure,
                session=test_session,
                fallback_query_type="work_item",
                fallback_params={"id": str(work_item_id)},
                fallback_enabled=True,
            )
            results.append((data, layer, warnings))

    # Verify all queries succeeded
    assert len(results) == len(work_item_ids), "All queries should succeed"

    for data, layer, warnings in results:
        # No exceptions raised - system continues
        assert data is not None, "Query should return data"
        assert layer == "sqlite_cache", "All queries should use cache layer"

        # Warnings provided (not errors)
        assert len(warnings) > 0, "Warnings should be provided"
        assert any("PostgreSQL unavailable" in w for w in warnings)

    # Verify system continued operation without hard failures
    # (if this test completes without exception, requirement is met)
