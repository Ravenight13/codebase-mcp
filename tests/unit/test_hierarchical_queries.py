"""Unit tests for hierarchical work item query service.

Tests the hierarchy service functions:
- get_work_item_with_hierarchy() - Full hierarchy retrieval
- get_ancestors() - Materialized path parsing
- get_descendants() - Recursive CTE traversal
- update_materialized_path() - Path propagation and validation

Performance Validation:
- <10ms for 5-level hierarchies (FR-013)
- <1ms for single work item lookup

Constitutional Compliance:
- Principle VII: TDD (tests before implementation)
- Principle VIII: Type safety (complete type annotations)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.task import WorkItem
from src.services.hierarchy import (
    CircularReferenceError,
    HierarchyServiceError,
    InvalidDepthError,
    WorkItemNotFoundError,
    get_ancestors,
    get_descendants,
    get_work_item_with_hierarchy,
    update_materialized_path,
)


@pytest.fixture
async def sample_hierarchy(session: AsyncSession) -> dict[str, WorkItem]:
    """Create a 5-level work item hierarchy for testing.

    Structure:
        project (depth 0)
        └── session1 (depth 1)
            ├── task1 (depth 2)
            │   └── subtask1 (depth 3)
            │       └── subtask2 (depth 4)
            └── task2 (depth 2)

    Returns:
        Dictionary mapping names to WorkItem instances
    """
    # Create root project
    project = WorkItem(
        id=uuid.uuid4(),
        item_type="project",
        title="Test Project",
        status="active",
        path="/",
        depth=0,
        created_by="test-fixture",
    )
    session.add(project)
    await session.flush()

    # Update path with actual ID
    project.path = f"/{project.id}"
    await session.flush()

    # Create session under project
    session1 = WorkItem(
        id=uuid.uuid4(),
        item_type="session",
        title="Test Session",
        status="active",
        parent_id=project.id,
        path=f"/{project.id}",
        depth=1,
        created_by="test-fixture",
    )
    session.add(session1)
    await session.flush()

    # Update path with actual ID
    session1.path = f"/{project.id}/{session1.id}"
    await session.flush()

    # Create task1 under session
    task1 = WorkItem(
        id=uuid.uuid4(),
        item_type="task",
        title="Task 1",
        status="active",
        parent_id=session1.id,
        path=f"/{project.id}/{session1.id}",
        depth=2,
        created_by="test-fixture",
    )
    session.add(task1)
    await session.flush()

    task1.path = f"/{project.id}/{session1.id}/{task1.id}"
    await session.flush()

    # Create subtask1 under task1
    subtask1 = WorkItem(
        id=uuid.uuid4(),
        item_type="task",
        title="Subtask 1",
        status="active",
        parent_id=task1.id,
        path=f"/{project.id}/{session1.id}/{task1.id}",
        depth=3,
        created_by="test-fixture",
    )
    session.add(subtask1)
    await session.flush()

    subtask1.path = f"/{project.id}/{session1.id}/{task1.id}/{subtask1.id}"
    await session.flush()

    # Create subtask2 under subtask1 (5th level)
    subtask2 = WorkItem(
        id=uuid.uuid4(),
        item_type="task",
        title="Subtask 2",
        status="active",
        parent_id=subtask1.id,
        path=f"/{project.id}/{session1.id}/{task1.id}/{subtask1.id}",
        depth=4,
        created_by="test-fixture",
    )
    session.add(subtask2)
    await session.flush()

    subtask2.path = f"/{project.id}/{session1.id}/{task1.id}/{subtask1.id}/{subtask2.id}"
    await session.flush()

    # Create task2 under session (sibling to task1)
    task2 = WorkItem(
        id=uuid.uuid4(),
        item_type="task",
        title="Task 2",
        status="active",
        parent_id=session1.id,
        path=f"/{project.id}/{session1.id}",
        depth=2,
        created_by="test-fixture",
    )
    session.add(task2)
    await session.flush()

    task2.path = f"/{project.id}/{session1.id}/{task2.id}"
    await session.flush()

    await session.commit()

    return {
        "project": project,
        "session1": session1,
        "task1": task1,
        "subtask1": subtask1,
        "subtask2": subtask2,
        "task2": task2,
    }


class TestGetAncestors:
    """Test ancestor retrieval via materialized path parsing."""

    async def test_get_ancestors_root_item(
        self,
        session: AsyncSession,
        sample_hierarchy: dict[str, WorkItem],
    ) -> None:
        """Root item has no ancestors."""
        project = sample_hierarchy["project"]
        ancestors = await get_ancestors(project.id, session)
        assert ancestors == []

    async def test_get_ancestors_one_level(
        self,
        session: AsyncSession,
        sample_hierarchy: dict[str, WorkItem],
    ) -> None:
        """Session has project as ancestor."""
        session1 = sample_hierarchy["session1"]
        project = sample_hierarchy["project"]

        ancestors = await get_ancestors(session1.id, session)
        assert len(ancestors) == 1
        assert ancestors[0].id == project.id
        assert ancestors[0].title == "Test Project"

    async def test_get_ancestors_multiple_levels(
        self,
        session: AsyncSession,
        sample_hierarchy: dict[str, WorkItem],
    ) -> None:
        """Subtask2 has 4 ancestors (project, session, task1, subtask1)."""
        subtask2 = sample_hierarchy["subtask2"]
        project = sample_hierarchy["project"]
        session1 = sample_hierarchy["session1"]
        task1 = sample_hierarchy["task1"]
        subtask1 = sample_hierarchy["subtask1"]

        ancestors = await get_ancestors(subtask2.id, session)
        assert len(ancestors) == 4

        # Verify order (root to parent)
        assert ancestors[0].id == project.id
        assert ancestors[1].id == session1.id
        assert ancestors[2].id == task1.id
        assert ancestors[3].id == subtask1.id

    async def test_get_ancestors_nonexistent_item(
        self,
        session: AsyncSession,
    ) -> None:
        """Raises WorkItemNotFoundError for nonexistent item."""
        fake_id = uuid.uuid4()
        with pytest.raises(WorkItemNotFoundError, match=str(fake_id)):
            await get_ancestors(fake_id, session)


class TestGetDescendants:
    """Test descendant retrieval via recursive CTE."""

    async def test_get_descendants_leaf_item(
        self,
        session: AsyncSession,
        sample_hierarchy: dict[str, WorkItem],
    ) -> None:
        """Leaf item (subtask2) has no descendants."""
        subtask2 = sample_hierarchy["subtask2"]
        descendants = await get_descendants(subtask2.id, session)
        assert descendants == []

    async def test_get_descendants_one_level(
        self,
        session: AsyncSession,
        sample_hierarchy: dict[str, WorkItem],
    ) -> None:
        """Task1 has 2 descendants (subtask1, subtask2)."""
        task1 = sample_hierarchy["task1"]
        subtask1 = sample_hierarchy["subtask1"]
        subtask2 = sample_hierarchy["subtask2"]

        descendants = await get_descendants(task1.id, session, max_depth=5)
        assert len(descendants) == 2

        # Verify IDs (order by depth, path)
        descendant_ids = {d.id for d in descendants}
        assert descendant_ids == {subtask1.id, subtask2.id}

    async def test_get_descendants_multiple_levels(
        self,
        session: AsyncSession,
        sample_hierarchy: dict[str, WorkItem],
    ) -> None:
        """Project has 5 descendants (all child items)."""
        project = sample_hierarchy["project"]
        session1 = sample_hierarchy["session1"]
        task1 = sample_hierarchy["task1"]
        task2 = sample_hierarchy["task2"]
        subtask1 = sample_hierarchy["subtask1"]
        subtask2 = sample_hierarchy["subtask2"]

        descendants = await get_descendants(project.id, session, max_depth=5)
        assert len(descendants) == 5

        # Verify all descendants present
        descendant_ids = {d.id for d in descendants}
        expected_ids = {
            session1.id,
            task1.id,
            task2.id,
            subtask1.id,
            subtask2.id,
        }
        assert descendant_ids == expected_ids

    async def test_get_descendants_max_depth_limit(
        self,
        session: AsyncSession,
        sample_hierarchy: dict[str, WorkItem],
    ) -> None:
        """max_depth limits recursion depth."""
        project = sample_hierarchy["project"]
        session1 = sample_hierarchy["session1"]
        task1 = sample_hierarchy["task1"]
        task2 = sample_hierarchy["task2"]

        # Limit to 2 levels (session + tasks, no subtasks)
        descendants = await get_descendants(project.id, session, max_depth=2)
        assert len(descendants) == 3

        descendant_ids = {d.id for d in descendants}
        assert descendant_ids == {session1.id, task1.id, task2.id}

    async def test_get_descendants_invalid_max_depth(
        self,
        session: AsyncSession,
        sample_hierarchy: dict[str, WorkItem],
    ) -> None:
        """Raises InvalidDepthError for invalid max_depth."""
        project = sample_hierarchy["project"]

        with pytest.raises(InvalidDepthError, match="must be 1-5"):
            await get_descendants(project.id, session, max_depth=0)

        with pytest.raises(InvalidDepthError, match="must be 1-5"):
            await get_descendants(project.id, session, max_depth=6)

    async def test_get_descendants_nonexistent_item(
        self,
        session: AsyncSession,
    ) -> None:
        """Raises WorkItemNotFoundError for nonexistent item."""
        fake_id = uuid.uuid4()
        with pytest.raises(WorkItemNotFoundError, match=str(fake_id)):
            await get_descendants(fake_id, session)


class TestGetWorkItemWithHierarchy:
    """Test full hierarchy retrieval (ancestors + descendants)."""

    async def test_get_full_hierarchy(
        self,
        session: AsyncSession,
        sample_hierarchy: dict[str, WorkItem],
    ) -> None:
        """Retrieve work item with ancestors and descendants."""
        task1 = sample_hierarchy["task1"]
        project = sample_hierarchy["project"]
        session1 = sample_hierarchy["session1"]
        subtask1 = sample_hierarchy["subtask1"]
        subtask2 = sample_hierarchy["subtask2"]

        work_item = await get_work_item_with_hierarchy(
            task1.id,
            session,
            max_depth=5,
        )

        # Verify work item loaded
        assert work_item.id == task1.id
        assert work_item.title == "Task 1"

        # Verify ancestors populated
        assert len(work_item.ancestors) == 2  # type: ignore
        ancestor_ids = {a.id for a in work_item.ancestors}  # type: ignore
        assert ancestor_ids == {project.id, session1.id}

        # Verify descendants populated
        assert len(work_item.descendants) == 2  # type: ignore
        descendant_ids = {d.id for d in work_item.descendants}  # type: ignore
        assert descendant_ids == {subtask1.id, subtask2.id}

    async def test_get_hierarchy_invalid_depth(
        self,
        session: AsyncSession,
        sample_hierarchy: dict[str, WorkItem],
    ) -> None:
        """Raises InvalidDepthError for invalid max_depth."""
        task1 = sample_hierarchy["task1"]

        with pytest.raises(InvalidDepthError, match="must be 1-5"):
            await get_work_item_with_hierarchy(task1.id, session, max_depth=6)

    async def test_get_hierarchy_nonexistent_item(
        self,
        session: AsyncSession,
    ) -> None:
        """Raises WorkItemNotFoundError for nonexistent item."""
        fake_id = uuid.uuid4()
        with pytest.raises(WorkItemNotFoundError, match=str(fake_id)):
            await get_work_item_with_hierarchy(fake_id, session)


class TestUpdateMaterializedPath:
    """Test path propagation when parent changes."""

    async def test_update_path_set_parent(
        self,
        session: AsyncSession,
        sample_hierarchy: dict[str, WorkItem],
    ) -> None:
        """Setting parent updates path and depth."""
        # Create orphan item (no parent)
        orphan = WorkItem(
            id=uuid.uuid4(),
            item_type="task",
            title="Orphan Task",
            status="active",
            path="/",
            depth=0,
            created_by="test",
        )
        session.add(orphan)
        await session.flush()

        orphan.path = f"/{orphan.id}"
        await session.flush()

        # Set parent to session1
        session1 = sample_hierarchy["session1"]
        orphan.parent_id = session1.id
        await update_materialized_path(orphan, session)
        await session.commit()

        # Reload from database
        await session.refresh(orphan)

        # Verify path and depth updated
        expected_path = f"/{sample_hierarchy['project'].id}/{session1.id}/{orphan.id}"
        assert orphan.path == expected_path
        assert orphan.depth == 2

    async def test_update_path_change_parent(
        self,
        session: AsyncSession,
        sample_hierarchy: dict[str, WorkItem],
    ) -> None:
        """Changing parent updates path and depth."""
        task1 = sample_hierarchy["task1"]
        task2 = sample_hierarchy["task2"]

        # Move task1 to be sibling of task2 (both under session1)
        # Before: /project/session1/task1
        # After: /project/session1/task2/task1
        original_parent = task1.parent_id
        task1.parent_id = task2.id

        await update_materialized_path(task1, session)
        await session.commit()

        # Reload from database
        await session.refresh(task1)

        # Verify new path
        project_id = sample_hierarchy["project"].id
        session_id = sample_hierarchy["session1"].id
        expected_path = f"/{project_id}/{session_id}/{task2.id}/{task1.id}"
        assert task1.path == expected_path
        assert task1.depth == 3

    async def test_update_path_propagates_to_descendants(
        self,
        session: AsyncSession,
        sample_hierarchy: dict[str, WorkItem],
    ) -> None:
        """Path updates propagate to all descendants."""
        task1 = sample_hierarchy["task1"]
        task2 = sample_hierarchy["task2"]
        subtask1 = sample_hierarchy["subtask1"]
        subtask2 = sample_hierarchy["subtask2"]

        # Move task1 (with subtasks) under task2
        task1.parent_id = task2.id
        await update_materialized_path(task1, session)
        await session.commit()

        # Reload descendants
        await session.refresh(subtask1)
        await session.refresh(subtask2)

        # Verify all descendant paths updated
        project_id = sample_hierarchy["project"].id
        session_id = sample_hierarchy["session1"].id

        # task1 path should reflect new parent
        assert task1.depth == 3
        assert str(task2.id) in task1.path

        # subtask1 path should reflect task1's new path
        assert subtask1.depth == 4
        assert str(task2.id) in subtask1.path

        # subtask2 path should reflect subtask1's new path
        assert subtask2.depth == 5
        assert str(task2.id) in subtask2.path

    async def test_update_path_prevents_circular_reference(
        self,
        session: AsyncSession,
        sample_hierarchy: dict[str, WorkItem],
    ) -> None:
        """Cannot set parent to own descendant (circular reference)."""
        task1 = sample_hierarchy["task1"]
        subtask1 = sample_hierarchy["subtask1"]

        # Try to make task1 a child of its own descendant (subtask1)
        task1.parent_id = subtask1.id

        with pytest.raises(CircularReferenceError, match="circular reference"):
            await update_materialized_path(task1, session)

    async def test_update_path_validates_max_depth(
        self,
        session: AsyncSession,
        sample_hierarchy: dict[str, WorkItem],
    ) -> None:
        """Cannot exceed max depth of 5 levels."""
        subtask2 = sample_hierarchy["subtask2"]

        # Create new item to make subtask2 depth 5
        # Then try to add child (would be depth 6)
        new_child = WorkItem(
            id=uuid.uuid4(),
            item_type="task",
            title="Invalid Deep Child",
            status="active",
            parent_id=subtask2.id,
            path=f"{subtask2.path}",
            depth=5,
            created_by="test",
        )
        session.add(new_child)
        await session.flush()

        with pytest.raises(InvalidDepthError, match="exceeds maximum"):
            await update_materialized_path(new_child, session)

    async def test_update_path_nonexistent_parent(
        self,
        session: AsyncSession,
        sample_hierarchy: dict[str, WorkItem],
    ) -> None:
        """Raises WorkItemNotFoundError for nonexistent parent."""
        task1 = sample_hierarchy["task1"]
        fake_parent_id = uuid.uuid4()

        task1.parent_id = fake_parent_id

        with pytest.raises(WorkItemNotFoundError, match=str(fake_parent_id)):
            await update_materialized_path(task1, session)


class TestPerformance:
    """Performance validation tests (FR-013)."""

    @pytest.mark.asyncio
    async def test_hierarchical_query_performance(
        self,
        session: AsyncSession,
        sample_hierarchy: dict[str, WorkItem],
    ) -> None:
        """Hierarchical queries complete in <10ms for 5-level hierarchies."""
        import time

        project = sample_hierarchy["project"]

        # Measure full hierarchy query performance
        start = time.perf_counter()
        work_item = await get_work_item_with_hierarchy(
            project.id,
            session,
            max_depth=5,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Verify performance target (<10ms)
        assert elapsed_ms < 10.0, f"Query took {elapsed_ms:.2f}ms (target: <10ms)"

        # Verify complete hierarchy retrieved
        assert len(work_item.descendants) == 5  # type: ignore

    @pytest.mark.asyncio
    async def test_ancestor_query_performance(
        self,
        session: AsyncSession,
        sample_hierarchy: dict[str, WorkItem],
    ) -> None:
        """Ancestor queries complete in <1ms."""
        import time

        subtask2 = sample_hierarchy["subtask2"]

        # Measure ancestor query performance
        start = time.perf_counter()
        ancestors = await get_ancestors(subtask2.id, session)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Verify performance target (<1ms)
        assert elapsed_ms < 1.0, f"Query took {elapsed_ms:.2f}ms (target: <1ms)"

        # Verify all ancestors retrieved
        assert len(ancestors) == 4
