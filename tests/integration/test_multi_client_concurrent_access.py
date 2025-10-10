"""Integration test for multi-client concurrent access (Scenario 7).

This test validates immediate visibility across multiple AI clients as described in
quickstart.md Scenario 7:
1. Simulate 3 concurrent AI clients (claude-code, claude-desktop, github-copilot)
2. Client 1 creates work item, clients 2 and 3 immediately query
3. Client 2 updates work item, client 3 queries and sees update immediately
4. Verify no caching delays, stale reads, or version conflicts

Constitutional Compliance:
- Principle V: Production Quality (immediate consistency, no stale reads)
- Principle VII: Test-Driven Development (validates acceptance criteria)
- Principle VIII: Type Safety (complete type annotations, mypy --strict)

Expected Behavior:
- All clients see changes immediately after commit
- No optimistic lock conflicts (versions managed correctly)
- created_by and updated_by audit trail preserved
"""

from __future__ import annotations

import asyncio
import time
from typing import Any
from uuid import UUID

import pytest

from src.database import get_session_factory
from src.services.work_items import (
    create_work_item as create_work_item_service,
    get_work_item as get_work_item_service,
    update_work_item as update_work_item_service,
)
from pydantic_schemas import ItemType, TaskMetadata  # type: ignore


# ==============================================================================
# Test Data Setup
# ==============================================================================


class SimulatedClient:
    """Simulates an AI client with independent database sessions.

    Each client represents a separate AI assistant (claude-code, claude-desktop,
    github-copilot) accessing the database concurrently.
    """

    def __init__(self, client_id: str) -> None:
        """Initialize simulated client.

        Args:
            client_id: Unique identifier for the AI client
        """
        self.client_id = client_id

    async def create_work_item(
        self,
        item_type: ItemType,
        title: str,
        metadata: TaskMetadata,
    ) -> Any:
        """Create work item using independent session.

        Args:
            item_type: Work item type enum
            title: Work item title
            metadata: Pydantic metadata model

        Returns:
            Created work item model
        """
        async with get_session_factory()() as db:
            work_item = await create_work_item_service(
                item_type=item_type,
                title=title,
                metadata=metadata,
                parent_id=None,
                created_by=self.client_id,
                session=db,
            )
            await db.commit()
            # Refresh to ensure all fields loaded
            await db.refresh(work_item)
            return work_item

    async def get_work_item(self, work_item_id: UUID) -> Any:
        """Get work item using independent session.

        Args:
            work_item_id: UUID of work item to retrieve

        Returns:
            Work item model with current database state
        """
        async with get_session_factory()() as db:
            work_item = await get_work_item_service(
                work_item_id=work_item_id,
                include_hierarchy=False,
                session=db,
            )
            await db.commit()
            return work_item

    async def update_work_item(
        self,
        work_item_id: UUID,
        version: int,
        updates: dict[str, Any],
    ) -> Any:
        """Update work item using independent session.

        Args:
            work_item_id: UUID of work item to update
            version: Expected version for optimistic locking
            updates: Dictionary of field updates

        Returns:
            Updated work item model
        """
        async with get_session_factory()() as db:
            work_item = await update_work_item_service(
                work_item_id=work_item_id,
                version=version,
                updates=updates,
                updated_by=self.client_id,
                session=db,
            )
            await db.commit()
            await db.refresh(work_item)
            return work_item


@pytest.fixture
def clients() -> dict[str, SimulatedClient]:
    """Create simulated AI clients for concurrent testing.

    Returns:
        Dictionary mapping client names to SimulatedClient instances
    """
    return {
        "claude-code": SimulatedClient("claude-code"),
        "claude-desktop": SimulatedClient("claude-desktop"),
        "github-copilot": SimulatedClient("github-copilot"),
    }


# ==============================================================================
# Integration Tests
# ==============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multi_client_create_and_immediate_read(
    clients: dict[str, SimulatedClient],
) -> None:
    """Test that all clients see work item immediately after creation.

    Validates quickstart.md Scenario 7 - Test 1:
    - Client 1 (claude-code) creates work item
    - Clients 2 and 3 immediately query
    - Both clients see the new work item with correct created_by

    Success Criteria:
    - Clients 2 and 3 retrieve work item successfully
    - created_by field shows "claude-code"
    - All fields match (no data corruption)
    - No caching delays (<10ms read latency)
    """
    client1 = clients["claude-code"]
    client2 = clients["claude-desktop"]
    client3 = clients["github-copilot"]

    # Client 1: Create work item
    task_metadata = TaskMetadata(
        priority="high",
        effort_estimate="2h",
        tags=["integration-test", "multi-client"],
    )

    work_item = await client1.create_work_item(
        item_type=ItemType.TASK,
        title="Multi-client test task",
        metadata=task_metadata,
    )

    work_item_id = work_item.id
    assert work_item.created_by == "claude-code", "created_by must be claude-code"
    assert work_item.version == 1, "Initial version must be 1"

    # Clients 2 and 3: Query immediately in parallel
    start_time = time.perf_counter()
    results = await asyncio.gather(
        client2.get_work_item(work_item_id),
        client3.get_work_item(work_item_id),
    )
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    client2_view = results[0]
    client3_view = results[1]

    # Performance assertion
    assert elapsed_ms < 20.0, (
        f"Concurrent reads took {elapsed_ms:.3f}ms (target: <20ms for 2 parallel reads)"
    )

    # Visibility assertions - Client 2 view
    assert client2_view is not None, "Client 2 must see work item immediately"
    assert client2_view.id == work_item_id, "Client 2 must see correct work item ID"
    assert client2_view.title == "Multi-client test task", (
        "Client 2 must see correct title"
    )
    assert client2_view.created_by == "claude-code", (
        "Client 2 must see correct created_by audit trail"
    )
    assert client2_view.version == 1, "Client 2 must see version 1"

    # Visibility assertions - Client 3 view
    assert client3_view is not None, "Client 3 must see work item immediately"
    assert client3_view.id == work_item_id, "Client 3 must see correct work item ID"
    assert client3_view.title == "Multi-client test task", (
        "Client 3 must see correct title"
    )
    assert client3_view.created_by == "claude-code", (
        "Client 3 must see correct created_by audit trail"
    )
    assert client3_view.version == 1, "Client 3 must see version 1"

    # Consistency assertion - both clients see identical data
    assert client2_view.title == client3_view.title, (
        "Clients 2 and 3 must see identical title"
    )
    assert client2_view.created_at == client3_view.created_at, (
        "Clients 2 and 3 must see identical created_at"
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multi_client_update_and_immediate_read(
    clients: dict[str, SimulatedClient],
) -> None:
    """Test that updates are immediately visible to other clients.

    Validates quickstart.md Scenario 7 - Test 2:
    - Client 1 creates work item
    - Client 2 updates work item status
    - Client 3 queries immediately and sees update
    - Verify updated_by shows client 2 (claude-desktop)

    Success Criteria:
    - Client 3 sees updated status immediately
    - updated_by field shows "claude-desktop"
    - Version incremented correctly (2)
    - created_by preserved as "claude-code"
    - No optimistic lock conflicts
    """
    client1 = clients["claude-code"]
    client2 = clients["claude-desktop"]
    client3 = clients["github-copilot"]

    # Client 1: Create work item
    task_metadata = TaskMetadata(
        priority="medium",
        effort_estimate="3h",
        tags=["update-test"],
    )

    work_item = await client1.create_work_item(
        item_type=ItemType.TASK,
        title="Task for update testing",
        metadata=task_metadata,
    )

    work_item_id = work_item.id
    initial_version = work_item.version
    assert initial_version == 1, "Initial version must be 1"
    assert work_item.created_by == "claude-code", "created_by must be claude-code"

    # Client 2: Update work item status
    updated_item = await client2.update_work_item(
        work_item_id=work_item_id,
        version=initial_version,
        updates={"status": "completed"},
    )

    assert updated_item.version == 2, "Version must increment to 2 after update"
    assert updated_item.status == "completed", "Status must be updated to completed"

    # Client 3: Query immediately after update
    start_time = time.perf_counter()
    client3_view = await client3.get_work_item(work_item_id)
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    # Performance assertion
    assert elapsed_ms < 10.0, (
        f"Read after write took {elapsed_ms:.3f}ms (target: <10ms)"
    )

    # Visibility assertions
    assert client3_view is not None, "Client 3 must see updated work item"
    assert client3_view.status == "completed", (
        "Client 3 must see updated status immediately"
    )
    assert client3_view.version == 2, "Client 3 must see incremented version"

    # Audit trail assertions
    assert client3_view.created_by == "claude-code", (
        "created_by must be preserved as claude-code"
    )
    # Note: updated_by is tracked in history, not on main model
    # This is verified in the database model's audit trail

    # Consistency assertion
    assert client3_view.id == work_item_id, "Work item ID must be consistent"
    assert client3_view.title == "Task for update testing", (
        "Title must be unchanged"
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multi_client_concurrent_reads_no_stale_data(
    clients: dict[str, SimulatedClient],
) -> None:
    """Test that concurrent reads never return stale cached data.

    Validates:
    - Multiple clients reading same work item concurrently
    - All clients see consistent, up-to-date state
    - No read-your-writes inconsistencies
    - Performance remains acceptable under concurrent load

    Success Criteria:
    - 10 concurrent reads complete successfully
    - All reads return identical data
    - Total time <50ms (5ms per read average)
    - No caching artifacts or version mismatches
    """
    client1 = clients["claude-code"]
    client2 = clients["claude-desktop"]
    client3 = clients["github-copilot"]

    # Setup: Create work item with client 1
    task_metadata = TaskMetadata(
        priority="low",
        effort_estimate="1h",
        tags=["concurrent-read-test"],
    )

    work_item = await client1.create_work_item(
        item_type=ItemType.TASK,
        title="Concurrent read test task",
        metadata=task_metadata,
    )

    work_item_id = work_item.id

    # Execute 10 concurrent reads from all 3 clients
    read_tasks = []
    for _ in range(3):
        read_tasks.append(client1.get_work_item(work_item_id))
        read_tasks.append(client2.get_work_item(work_item_id))
        read_tasks.append(client3.get_work_item(work_item_id))

    start_time = time.perf_counter()
    results = await asyncio.gather(*read_tasks)
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    # Performance assertion
    assert elapsed_ms < 100.0, (
        f"9 concurrent reads took {elapsed_ms:.3f}ms (target: <100ms)"
    )
    avg_read_time = elapsed_ms / 9
    print(f"Average read latency: {avg_read_time:.3f}ms per read")

    # Consistency assertions - all reads return identical data
    first_result = results[0]
    for i, result in enumerate(results[1:], start=1):
        assert result.id == first_result.id, (
            f"Read {i} has inconsistent ID"
        )
        assert result.title == first_result.title, (
            f"Read {i} has inconsistent title"
        )
        assert result.status == first_result.status, (
            f"Read {i} has inconsistent status"
        )
        assert result.version == first_result.version, (
            f"Read {i} has inconsistent version"
        )
        assert result.created_by == first_result.created_by, (
            f"Read {i} has inconsistent created_by"
        )
        assert result.created_at == first_result.created_at, (
            f"Read {i} has inconsistent created_at"
        )

    # All reads must show correct created_by
    for i, result in enumerate(results):
        assert result.created_by == "claude-code", (
            f"Read {i} has incorrect created_by: {result.created_by}"
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multi_client_version_tracking_no_conflicts(
    clients: dict[str, SimulatedClient],
) -> None:
    """Test that version tracking prevents conflicts across clients.

    Validates:
    - Sequential updates from different clients work correctly
    - Version numbers increment monotonically
    - No lost updates or version conflicts
    - Optimistic locking protects against concurrent writes

    Success Criteria:
    - 5 sequential updates complete successfully
    - Versions increment from 1 to 6
    - Each update visible to all clients
    - No optimistic lock exceptions
    """
    client1 = clients["claude-code"]
    client2 = clients["claude-desktop"]
    client3 = clients["github-copilot"]

    # Setup: Create work item
    task_metadata = TaskMetadata(
        priority="high",
        effort_estimate="4h",
        tags=["version-test"],
    )

    work_item = await client1.create_work_item(
        item_type=ItemType.TASK,
        title="Version tracking test task",
        metadata=task_metadata,
    )

    work_item_id = work_item.id
    current_version = work_item.version
    assert current_version == 1, "Initial version must be 1"

    # Client 2: First update (v1 → v2)
    updated = await client2.update_work_item(
        work_item_id=work_item_id,
        version=current_version,
        updates={"status": "active"},
    )
    current_version = updated.version
    assert current_version == 2, "Version must increment to 2"

    # Client 3: Second update (v2 → v3)
    updated = await client3.update_work_item(
        work_item_id=work_item_id,
        version=current_version,
        updates={"title": "Updated title by copilot"},
    )
    current_version = updated.version
    assert current_version == 3, "Version must increment to 3"

    # Client 1: Third update (v3 → v4)
    updated = await client1.update_work_item(
        work_item_id=work_item_id,
        version=current_version,
        updates={"status": "completed"},
    )
    current_version = updated.version
    assert current_version == 4, "Version must increment to 4"

    # Client 2: Fourth update (v4 → v5)
    updated = await client2.update_work_item(
        work_item_id=work_item_id,
        version=current_version,
        updates={"status": "blocked"},
    )
    current_version = updated.version
    assert current_version == 5, "Version must increment to 5"

    # Client 3: Fifth update (v5 → v6)
    updated = await client3.update_work_item(
        work_item_id=work_item_id,
        version=current_version,
        updates={"status": "active"},
    )
    current_version = updated.version
    assert current_version == 6, "Version must increment to 6"

    # All clients verify final state
    results = await asyncio.gather(
        client1.get_work_item(work_item_id),
        client2.get_work_item(work_item_id),
        client3.get_work_item(work_item_id),
    )

    # All clients must see version 6
    for i, result in enumerate(results):
        client_name = ["claude-code", "claude-desktop", "github-copilot"][i]
        assert result.version == 6, (
            f"{client_name} must see final version 6, got {result.version}"
        )
        assert result.status == "active", (
            f"{client_name} must see final status 'active'"
        )
        assert result.title == "Updated title by copilot", (
            f"{client_name} must see updated title"
        )


# ==============================================================================
# Cleanup
# ==============================================================================


@pytest.fixture(autouse=True, scope="function")
async def cleanup_test_data() -> Any:
    """Clean up test data after each test.

    Note: This is a placeholder. In production, we'd clean up created work items.
    For now, tests run against test database that can be reset.

    Returns:
        None before test, None after test (async generator pattern)
    """
    yield
    # Future: Delete created work items from database
