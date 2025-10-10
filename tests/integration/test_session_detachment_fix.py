"""Integration test for SQLAlchemy session management fix in work_items tools.

Verifies that _work_item_to_dict() safely handles detached SQLAlchemy objects
without triggering "Parent instance is not bound to a Session" errors.

Constitutional Compliance:
- Principle V: Production quality (comprehensive error handling)
- Principle VIII: Type safety (mypy --strict compliance)
"""

from __future__ import annotations

import pytest
from uuid import uuid4

from src.database import get_session_factory
from src.models.task import WorkItem


@pytest.mark.asyncio
async def test_work_item_to_dict_with_detached_object() -> None:
    """Test that _work_item_to_dict() handles detached objects safely.

    This test simulates the actual bug scenario:
    1. Create a work item in a session
    2. Commit and close the session (object becomes detached)
    3. Call _work_item_to_dict() on the detached object
    4. Verify no "not bound to a Session" error occurs
    """
    # Import the function to test
    from src.mcp.tools.work_items import _work_item_to_dict

    # Step 1: Create work item within session
    work_item_id = uuid4()
    async with get_session_factory()() as db:
        work_item = WorkItem(
            id=work_item_id,
            item_type="project",
            title="Test Project",
            status="active",
            path=f"/{work_item_id}",
            depth=0,
            metadata_={
                "description": "Test project for session management",
                "target_quarter": "2025-Q1",
                "constitutional_principles": []
            },
            created_by="test-user",
        )
        db.add(work_item)
        await db.commit()
        await db.refresh(work_item)

        # At this point, work_item is attached to the session
        # Store the work_item reference
        detached_work_item = work_item

    # Step 2: Session is closed, work_item is now detached
    # This simulates the exact bug scenario in the tool functions

    # Step 3: Call _work_item_to_dict() on detached object
    # BEFORE FIX: This would raise:
    #   "Parent instance <WorkItem> is not bound to a Session;
    #    lazy load operation of attribute 'children' cannot proceed"
    # AFTER FIX: This should work without errors
    result = _work_item_to_dict(detached_work_item)

    # Step 4: Verify result
    assert result["id"] == str(work_item_id)
    assert result["item_type"] == "project"
    assert result["title"] == "Test Project"
    assert result["status"] == "active"
    assert result["version"] == 1
    assert "children" not in result  # Not loaded, so not included
    assert "dependencies" not in result  # Not loaded, so not included

    # Clean up
    async with get_session_factory()() as db:
        work_item = await db.get(WorkItem, work_item_id)
        if work_item:
            await db.delete(work_item)
            await db.commit()


@pytest.mark.asyncio
async def test_work_item_to_dict_with_loaded_children() -> None:
    """Test that _work_item_to_dict() includes children when already loaded.

    Verifies that the fix doesn't break the case where children ARE loaded.
    """
    from src.mcp.tools.work_items import _work_item_to_dict
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    # Create parent and child work items
    parent_id = uuid4()
    child_id = uuid4()

    async with get_session_factory()() as db:
        parent = WorkItem(
            id=parent_id,
            item_type="project",
            title="Parent Project",
            status="active",
            path=f"/{parent_id}",
            depth=0,
            metadata_={"description": "Parent project"},
            created_by="test-user",
        )
        db.add(parent)
        await db.commit()
        await db.refresh(parent)

        child = WorkItem(
            id=child_id,
            item_type="task",
            title="Child Task",
            status="active",
            parent_id=parent_id,
            path=f"/{parent_id}/{child_id}",
            depth=1,
            metadata_={},
            created_by="test-user",
        )
        db.add(child)
        await db.commit()

        # Query parent with children eagerly loaded
        stmt = (
            select(WorkItem)
            .where(WorkItem.id == parent_id)
            .options(selectinload(WorkItem.children))
        )
        result = await db.execute(stmt)
        parent_with_children = result.scalar_one()

        # Convert to dict while session is still open (children are loaded)
        parent_dict = _work_item_to_dict(parent_with_children)

    # Verify children are included
    assert parent_dict["id"] == str(parent_id)
    assert "children" in parent_dict
    assert len(parent_dict["children"]) == 1
    assert parent_dict["children"][0]["id"] == str(child_id)
    assert parent_dict["children"][0]["title"] == "Child Task"

    # Clean up
    async with get_session_factory()() as db:
        child_item = await db.get(WorkItem, child_id)
        parent_item = await db.get(WorkItem, parent_id)
        if child_item:
            await db.delete(child_item)
        if parent_item:
            await db.delete(parent_item)
        await db.commit()


@pytest.mark.asyncio
async def test_work_item_to_dict_with_detached_object_after_commit() -> None:
    """Test the exact pattern used in tool functions that was causing the bug.

    This replicates the exact code pattern from create_work_item, update_work_item,
    query_work_item, and list_work_items:

    async with get_session_factory()() as db:
        work_item = await service_function(...)
        await db.commit()
    # Session closed here - work_item is detached
    response = _work_item_to_dict(work_item)  # Bug was here
    """
    from src.mcp.tools.work_items import _work_item_to_dict
    from src.services.work_items import create_work_item as create_work_item_service

    # Import Pydantic schemas from contracts (handle path with leading digits)
    import sys
    from pathlib import Path
    specs_contracts_path = (
        Path(__file__).parent.parent.parent
        / "specs"
        / "003-database-backed-project"
        / "contracts"
    )
    if str(specs_contracts_path) not in sys.path:
        sys.path.insert(0, str(specs_contracts_path))

    from pydantic_schemas import ItemType, ProjectMetadata  # type: ignore

    # Replicate the exact pattern from the tool functions
    metadata = ProjectMetadata(
        description="Test project for session management",
        target_quarter="2025-Q1",
        constitutional_principles=[]
    )

    # This is the pattern used in all 4 tool functions
    async with get_session_factory()() as db:
        work_item = await create_work_item_service(
            item_type=ItemType.PROJECT,
            title="Test Session Management",
            metadata=metadata,
            parent_id=None,
            created_by="test-user",
            session=db,
            branch_name=None,
        )
        await db.commit()
    # Session closed here - work_item is now detached

    # BEFORE FIX: This would raise "not bound to a Session" error
    # AFTER FIX: This should work without errors
    response = _work_item_to_dict(work_item)

    # Verify response
    assert response["title"] == "Test Session Management"
    assert response["item_type"] == "project"
    assert response["status"] == "active"
    assert response["version"] == 1
    assert "id" in response
    assert "created_at" in response
    assert "updated_at" in response

    # Children and dependencies not loaded, so shouldn't be in response
    assert "children" not in response
    assert "dependencies" not in response

    # Clean up
    async with get_session_factory()() as db:
        work_item_obj = await db.get(WorkItem, work_item.id)
        if work_item_obj:
            await db.delete(work_item_obj)
            await db.commit()
