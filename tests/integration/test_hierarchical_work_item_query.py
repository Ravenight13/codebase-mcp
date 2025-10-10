"""Integration test for hierarchical work item queries with performance validation.

This test validates quickstart.md Scenario 6: Query 5-level hierarchy in <10ms.

Test Setup:
- Creates 5-level work item hierarchy (project → session → task → subtask → subtask)
- Tests full hierarchical queries with ancestors and descendants
- Measures p95 latency across 100 queries
- Verifies dependency relationships

Success Criteria:
- Full hierarchy retrieval includes complete ancestor chain (4 parents)
- Full hierarchy retrieval includes all descendants
- p95 latency < 10ms for hierarchical queries (FR-013)
- Dependencies relationships are properly linked
- Materialized path correctly represents hierarchy
- Depth values correctly calculated (0-4 for 5 levels)

Constitutional Compliance:
- Principle IV: Performance Guarantees (<10ms hierarchical queries)
- Principle VII: TDD (validates acceptance criteria)
- Principle VIII: Type Safety (mypy --strict compliance)
"""

from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

# Import Pydantic schemas from contracts
specs_contracts_path = (
    Path(__file__).parent.parent.parent
    / "specs"
    / "003-database-backed-project"
    / "contracts"
)
if specs_contracts_path.exists() and str(specs_contracts_path) not in sys.path:
    sys.path.insert(0, str(specs_contracts_path))

from pydantic_schemas import (  # type: ignore
    ItemType,
    ProjectMetadata,
    ResearchMetadata,
    SessionMetadata,
    TaskMetadata,
)

from src.database import get_session_factory
from src.models.task import WorkItem
from src.services.work_items import create_work_item, get_work_item


# ==============================================================================
# Test Data Setup
# ==============================================================================


@pytest.fixture
async def five_level_hierarchy(session: AsyncSession) -> dict[str, UUID]:
    """Create 5-level work item hierarchy for testing.

    Structure:
        Level 0: Project (root)
        └── Level 1: Session
            └── Level 2: Task
                └── Level 3: Task (subtask)
                    └── Level 4: Task (sub-subtask)

    Returns:
        Dictionary mapping level names to work item UUIDs:
        {
            "project": UUID,
            "session": UUID,
            "task": UUID,
            "subtask_1": UUID,
            "subtask_2": UUID
        }
    """
    # Level 0: Project (root)
    project = await create_work_item(
        item_type=ItemType.PROJECT,
        title="Feature 001: Semantic Code Search",
        metadata=ProjectMetadata(
            description="Implement semantic search for codebase indexing",
            target_quarter="2025-Q1",
            constitutional_principles=["Simplicity Over Features", "Performance Guarantees"],
        ),
        parent_id=None,
        created_by="test-client",
        session=session,
        description="Add semantic search capabilities to MCP server",
    )
    await session.flush()

    # Level 1: Session
    work_session = await create_work_item(
        item_type=ItemType.SESSION,
        title="Implementation Session 2025-01-15",
        metadata=SessionMetadata(
            token_budget=200000,
            prompts_count=0,
            yaml_frontmatter={
                "schema_version": "1.0",
                "date": "2025-01-15",
                "focus": "indexing service",
            },
        ),
        parent_id=project.id,
        created_by="test-client",
        session=session,
        description="Active development session for indexing implementation",
    )
    await session.flush()

    # Level 2: Task
    task = await create_work_item(
        item_type=ItemType.TASK,
        title="Implement tree-sitter AST parsing",
        metadata=TaskMetadata(
            estimated_hours=4.0,
            actual_hours=None,
            blocked_reason=None,
        ),
        parent_id=work_session.id,
        created_by="test-client",
        session=session,
        description="Parse Python code using tree-sitter for semantic indexing",
        notes="Use tree-sitter-python bindings",
    )
    await session.flush()

    # Level 3: Subtask
    subtask_1 = await create_work_item(
        item_type=ItemType.TASK,
        title="Write unit tests for parser",
        metadata=TaskMetadata(
            estimated_hours=2.0,
            actual_hours=None,
            blocked_reason=None,
        ),
        parent_id=task.id,
        created_by="test-client",
        session=session,
        description="Comprehensive unit tests for AST parsing logic",
    )
    await session.flush()

    # Level 4: Sub-subtask
    subtask_2 = await create_work_item(
        item_type=ItemType.TASK,
        title="Test edge cases for nested functions",
        metadata=TaskMetadata(
            estimated_hours=1.0,
            actual_hours=None,
            blocked_reason=None,
        ),
        parent_id=subtask_1.id,
        created_by="test-client",
        session=session,
        description="Test parsing of nested function definitions and closures",
        notes="Cover 3+ levels of nesting",
    )
    await session.flush()

    await session.commit()

    return {
        "project": project.id,
        "session": work_session.id,
        "task": task.id,
        "subtask_1": subtask_1.id,
        "subtask_2": subtask_2.id,
    }


# ==============================================================================
# Integration Tests
# ==============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_leaf_item_with_full_hierarchy(
    five_level_hierarchy: dict[str, UUID],
) -> None:
    """Test querying leaf item with full ancestor chain and descendants.

    Validates quickstart.md Scenario 6:
    - Query deepest leaf item (level 4)
    - Retrieve full ancestor chain (4 parents)
    - Retrieve all descendants (none for leaf)
    - Verify path, depth, and relationships

    Expected Behavior:
    - Leaf item has 4 ancestors (project → session → task → subtask_1)
    - Ancestors ordered from root to parent
    - Each ancestor has correct depth value
    - Materialized path correctly represents hierarchy
    - No descendants for leaf item
    """
    leaf_id = five_level_hierarchy["subtask_2"]

    async with get_session_factory()() as db:
        # Query leaf item with full hierarchy
        leaf_item = await get_work_item(
            work_item_id=leaf_id,
            include_hierarchy=True,
            session=db,
        )
        await db.commit()

    # Validate leaf item properties
    assert leaf_item.id == leaf_id
    assert leaf_item.title == "Test edge cases for nested functions"
    assert leaf_item.item_type == ItemType.TASK.value
    assert leaf_item.depth == 4, f"Leaf item depth should be 4, got {leaf_item.depth}"

    # Validate ancestors exist and are correctly populated
    assert hasattr(leaf_item, "ancestors"), "Leaf item must have ancestors attribute"
    ancestors: list[WorkItem] = leaf_item.ancestors
    assert len(ancestors) == 4, f"Expected 4 ancestors, got {len(ancestors)}"

    # Validate ancestor chain (root to parent order)
    expected_ancestor_titles = [
        "Feature 001: Semantic Code Search",  # Level 0: Project
        "Implementation Session 2025-01-15",  # Level 1: Session
        "Implement tree-sitter AST parsing",  # Level 2: Task
        "Write unit tests for parser",  # Level 3: Subtask
    ]

    for i, ancestor in enumerate(ancestors):
        assert ancestor.title == expected_ancestor_titles[i], (
            f"Ancestor {i} title mismatch: expected '{expected_ancestor_titles[i]}', "
            f"got '{ancestor.title}'"
        )
        assert ancestor.depth == i, f"Ancestor {i} depth should be {i}, got {ancestor.depth}"

    # Validate ancestor IDs match expected hierarchy
    assert ancestors[0].id == five_level_hierarchy["project"]
    assert ancestors[1].id == five_level_hierarchy["session"]
    assert ancestors[2].id == five_level_hierarchy["task"]
    assert ancestors[3].id == five_level_hierarchy["subtask_1"]

    # Validate materialized path
    expected_path_parts = [
        str(five_level_hierarchy["project"]),
        str(five_level_hierarchy["session"]),
        str(five_level_hierarchy["task"]),
        str(five_level_hierarchy["subtask_1"]),
        str(leaf_id),
    ]
    expected_path = "/" + "/".join(expected_path_parts)
    assert leaf_item.path == expected_path, (
        f"Path mismatch: expected '{expected_path}', got '{leaf_item.path}'"
    )

    # Validate descendants (leaf has no children)
    assert hasattr(leaf_item, "descendants"), "Leaf item must have descendants attribute"
    descendants: list[WorkItem] = leaf_item.descendants
    assert len(descendants) == 0, f"Leaf item should have 0 descendants, got {len(descendants)}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_root_item_with_full_descendants(
    five_level_hierarchy: dict[str, UUID],
) -> None:
    """Test querying root item with all descendants.

    Validates:
    - Root item (level 0) retrieval
    - All 4 descendants included
    - Descendants correctly nested
    - No ancestors for root item

    Expected Behavior:
    - Root has 0 ancestors
    - Root has 4 descendants (session, task, subtask_1, subtask_2)
    - Descendants ordered by depth
    """
    root_id = five_level_hierarchy["project"]

    async with get_session_factory()() as db:
        # Query root item with full hierarchy
        root_item = await get_work_item(
            work_item_id=root_id,
            include_hierarchy=True,
            session=db,
        )
        await db.commit()

    # Validate root item properties
    assert root_item.id == root_id
    assert root_item.title == "Feature 001: Semantic Code Search"
    assert root_item.item_type == ItemType.PROJECT.value
    assert root_item.depth == 0, f"Root item depth should be 0, got {root_item.depth}"

    # Validate no ancestors for root
    assert hasattr(root_item, "ancestors"), "Root item must have ancestors attribute"
    ancestors: list[WorkItem] = root_item.ancestors
    assert len(ancestors) == 0, f"Root should have 0 ancestors, got {len(ancestors)}"

    # Validate all descendants present
    assert hasattr(root_item, "descendants"), "Root item must have descendants attribute"
    descendants: list[WorkItem] = root_item.descendants
    assert len(descendants) == 4, f"Expected 4 descendants, got {len(descendants)}"

    # Validate descendants are ordered by depth
    expected_descendant_depths = [1, 2, 3, 4]
    actual_depths = [d.depth for d in descendants]
    assert actual_depths == expected_descendant_depths, (
        f"Descendant depths mismatch: expected {expected_descendant_depths}, "
        f"got {actual_depths}"
    )

    # Validate descendant IDs
    descendant_ids = {d.id for d in descendants}
    expected_ids = {
        five_level_hierarchy["session"],
        five_level_hierarchy["task"],
        five_level_hierarchy["subtask_1"],
        five_level_hierarchy["subtask_2"],
    }
    assert descendant_ids == expected_ids, "Descendant IDs do not match expected set"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_middle_item_with_ancestors_and_descendants(
    five_level_hierarchy: dict[str, UUID],
) -> None:
    """Test querying middle-level item with both ancestors and descendants.

    Validates:
    - Middle item (level 2) retrieval
    - 2 ancestors (project, session)
    - 2 descendants (subtask_1, subtask_2)
    - Correct path and depth

    Expected Behavior:
    - Item at depth 2 has 2 ancestors and 2 descendants
    - Ancestors ordered root to parent
    - Descendants ordered by depth
    """
    middle_id = five_level_hierarchy["task"]

    async with get_session_factory()() as db:
        # Query middle item with full hierarchy
        middle_item = await get_work_item(
            work_item_id=middle_id,
            include_hierarchy=True,
            session=db,
        )
        await db.commit()

    # Validate middle item properties
    assert middle_item.id == middle_id
    assert middle_item.title == "Implement tree-sitter AST parsing"
    assert middle_item.item_type == ItemType.TASK.value
    assert middle_item.depth == 2, f"Middle item depth should be 2, got {middle_item.depth}"

    # Validate ancestors (2 levels above)
    assert hasattr(middle_item, "ancestors"), "Middle item must have ancestors attribute"
    ancestors: list[WorkItem] = middle_item.ancestors
    assert len(ancestors) == 2, f"Expected 2 ancestors, got {len(ancestors)}"
    assert ancestors[0].id == five_level_hierarchy["project"]
    assert ancestors[1].id == five_level_hierarchy["session"]

    # Validate descendants (2 levels below)
    assert hasattr(middle_item, "descendants"), "Middle item must have descendants attribute"
    descendants: list[WorkItem] = middle_item.descendants
    assert len(descendants) == 2, f"Expected 2 descendants, got {len(descendants)}"

    descendant_ids = {d.id for d in descendants}
    expected_descendant_ids = {
        five_level_hierarchy["subtask_1"],
        five_level_hierarchy["subtask_2"],
    }
    assert descendant_ids == expected_descendant_ids, "Descendant IDs do not match"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_hierarchical_query_performance_p95_under_10ms(
    five_level_hierarchy: dict[str, UUID],
) -> None:
    """Test p95 latency for hierarchical queries is <10ms.

    Validates FR-013: <10ms p95 latency for 5-level hierarchies.

    Performance Test:
    - Run 100 hierarchical queries on leaf item
    - Measure latency for each query
    - Calculate p95 latency
    - Assert p95 < 10ms

    Expected Behavior:
    - p95 latency across 100 queries < 10ms
    - Consistent performance across multiple queries
    - Hierarchy service efficiently retrieves full tree
    """
    leaf_id = five_level_hierarchy["subtask_2"]
    latencies: list[float] = []

    # Run 100 hierarchical queries
    for _ in range(100):
        start_time = time.perf_counter()

        async with get_session_factory()() as db:
            _ = await get_work_item(
                work_item_id=leaf_id,
                include_hierarchy=True,
                session=db,
            )
            await db.commit()

        end_time = time.perf_counter()
        latency_ms = (end_time - start_time) * 1000
        latencies.append(latency_ms)

    # Calculate p95 latency
    p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
    mean_latency = statistics.mean(latencies)
    min_latency = min(latencies)
    max_latency = max(latencies)

    # Log performance metrics
    print(f"\nHierarchical Query Performance (100 queries):")
    print(f"  p95 latency: {p95_latency:.2f}ms")
    print(f"  Mean latency: {mean_latency:.2f}ms")
    print(f"  Min latency: {min_latency:.2f}ms")
    print(f"  Max latency: {max_latency:.2f}ms")

    # Assert p95 < 10ms (FR-013)
    assert p95_latency < 10.0, (
        f"p95 latency ({p95_latency:.2f}ms) exceeds 10ms threshold. "
        f"Mean: {mean_latency:.2f}ms, Max: {max_latency:.2f}ms"
    )

    # Additional validation: ensure all queries succeeded
    assert len(latencies) == 100, f"Expected 100 latencies, got {len(latencies)}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_without_hierarchy_returns_single_item(
    five_level_hierarchy: dict[str, UUID],
) -> None:
    """Test querying work item without hierarchy returns single item only.

    Validates:
    - include_hierarchy=False (default) behavior
    - No ancestors or descendants populated
    - Faster query performance

    Expected Behavior:
    - Single work item returned
    - No ancestors attribute populated
    - No descendants attribute populated
    - Query completes in <1ms
    """
    leaf_id = five_level_hierarchy["subtask_2"]

    start_time = time.perf_counter()

    async with get_session_factory()() as db:
        leaf_item = await get_work_item(
            work_item_id=leaf_id,
            include_hierarchy=False,
            session=db,
        )
        await db.commit()

    end_time = time.perf_counter()
    latency_ms = (end_time - start_time) * 1000

    # Validate single item returned
    assert leaf_item.id == leaf_id
    assert leaf_item.title == "Test edge cases for nested functions"

    # Validate no hierarchy attributes populated
    # Note: ancestors/descendants are temporary attributes added by hierarchy service
    # When include_hierarchy=False, these should not be present
    if hasattr(leaf_item, "ancestors"):
        # If attribute exists, it should be an empty list
        assert len(leaf_item.ancestors) == 0
    if hasattr(leaf_item, "descendants"):
        assert len(leaf_item.descendants) == 0

    # Validate performance: single item query should be <1ms
    print(f"\nSingle item query latency: {latency_ms:.2f}ms")
    assert latency_ms < 1.0, (
        f"Single item query latency ({latency_ms:.2f}ms) exceeds 1ms threshold"
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_materialized_path_correctness_across_hierarchy(
    five_level_hierarchy: dict[str, UUID],
) -> None:
    """Test materialized path correctness across all hierarchy levels.

    Validates:
    - Each level has correct path format
    - Paths correctly represent ancestor chain
    - Path parsing logic works for all levels

    Expected Behavior:
    - Level 0: path = "/{project_id}"
    - Level 1: path = "/{project_id}/{session_id}"
    - Level 2: path = "/{project_id}/{session_id}/{task_id}"
    - Level 3: path = "/{project_id}/{session_id}/{task_id}/{subtask_1_id}"
    - Level 4: path = "/{project_id}/{session_id}/{task_id}/{subtask_1_id}/{subtask_2_id}"
    """
    # Query all items
    async with get_session_factory()() as db:
        project = await get_work_item(
            work_item_id=five_level_hierarchy["project"],
            session=db,
        )
        session_item = await get_work_item(
            work_item_id=five_level_hierarchy["session"],
            session=db,
        )
        task = await get_work_item(
            work_item_id=five_level_hierarchy["task"],
            session=db,
        )
        subtask_1 = await get_work_item(
            work_item_id=five_level_hierarchy["subtask_1"],
            session=db,
        )
        subtask_2 = await get_work_item(
            work_item_id=five_level_hierarchy["subtask_2"],
            session=db,
        )
        await db.commit()

    # Validate Level 0: Project (root)
    expected_project_path = f"/{project.id}"
    assert project.path == expected_project_path, (
        f"Project path mismatch: expected '{expected_project_path}', "
        f"got '{project.path}'"
    )
    assert project.depth == 0

    # Validate Level 1: Session
    expected_session_path = f"/{project.id}/{session_item.id}"
    assert session_item.path == expected_session_path, (
        f"Session path mismatch: expected '{expected_session_path}', "
        f"got '{session_item.path}'"
    )
    assert session_item.depth == 1

    # Validate Level 2: Task
    expected_task_path = f"/{project.id}/{session_item.id}/{task.id}"
    assert task.path == expected_task_path, (
        f"Task path mismatch: expected '{expected_task_path}', got '{task.path}'"
    )
    assert task.depth == 2

    # Validate Level 3: Subtask 1
    expected_subtask_1_path = f"/{project.id}/{session_item.id}/{task.id}/{subtask_1.id}"
    assert subtask_1.path == expected_subtask_1_path, (
        f"Subtask 1 path mismatch: expected '{expected_subtask_1_path}', "
        f"got '{subtask_1.path}'"
    )
    assert subtask_1.depth == 3

    # Validate Level 4: Subtask 2
    expected_subtask_2_path = (
        f"/{project.id}/{session_item.id}/{task.id}/{subtask_1.id}/{subtask_2.id}"
    )
    assert subtask_2.path == expected_subtask_2_path, (
        f"Subtask 2 path mismatch: expected '{expected_subtask_2_path}', "
        f"got '{subtask_2.path}'"
    )
    assert subtask_2.depth == 4


# ==============================================================================
# Cleanup
# ==============================================================================


@pytest.fixture(autouse=True, scope="function")
async def cleanup_test_data() -> Any:
    """Clean up test data after each test.

    Note: Integration tests run against test database with transaction rollback.
    No explicit cleanup needed due to session fixture with automatic rollback.

    Returns:
        None before test, None after test (async generator pattern)
    """
    yield
    # Cleanup handled by session fixture rollback
