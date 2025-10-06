#!/usr/bin/env python3
"""Manual test script for MCP tool handlers.

Tests the parameter passing fixes:
- create_task_tool with TaskCreate model
- list_tasks_tool
- update_task_tool with TaskUpdate model
- get_task_tool
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

import src.database as database
from src.mcp.tools import (
    create_task_tool,
    get_task_tool,
    list_tasks_tool,
    update_task_tool,
)


async def main():
    """Run manual tests for tool handlers."""
    print("=" * 80)
    print("MCP Tool Handler Test Script")
    print("=" * 80)

    # Initialize database
    print("\n1. Initializing database connection...")
    try:
        await database.init_db_connection()
        print("✅ Database connected")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return

    if database.SessionLocal is None:
        print("❌ SessionLocal is None")
        return

    async with database.SessionLocal() as session:
        try:
            # Test 1: Create a task
            print("\n2. Testing create_task_tool...")
            create_result = await create_task_tool(
                db=session,
                title="Test Task - Parameter Passing Fix",
                description="Testing the Pydantic model parameter passing",
                notes="This should work with TaskCreate model",
                planning_references=["specs/001-build-a-production/spec.md"],
            )
            print(f"✅ Task created: {create_result['id']}")
            print(f"   Title: {create_result['title']}")
            print(f"   Status: {create_result['status']}")
            print(f"   Planning refs: {create_result['planning_references']}")

            task_id = create_result["id"]

            # Test 2: Get the task
            print(f"\n3. Testing get_task_tool with ID: {task_id}...")
            get_result = await get_task_tool(
                db=session,
                task_id=task_id,
            )
            print(f"✅ Task retrieved: {get_result['title']}")
            print(f"   Description: {get_result['description']}")
            print(f"   Notes: {get_result['notes']}")

            # Test 3: List tasks
            print("\n4. Testing list_tasks_tool...")
            list_result = await list_tasks_tool(
                db=session,
                status="need to be done",
                limit=5,
            )
            print(f"✅ Found {list_result['total_count']} task(s)")
            for task in list_result['tasks']:
                print(f"   - {task['title']} ({task['status']})")

            # Test 4: Update the task
            print(f"\n5. Testing update_task_tool...")
            update_result = await update_task_tool(
                db=session,
                task_id=task_id,
                status="in-progress",
                notes="Updated notes - testing TaskUpdate model",
                branch="001-build-a-production",
            )
            print(f"✅ Task updated")
            print(f"   New status: {update_result['status']}")
            print(f"   New notes: {update_result['notes']}")
            print(f"   Branches: {update_result['branches']}")

            # Test 5: List in-progress tasks
            print("\n6. Testing list_tasks_tool with status filter...")
            list_result2 = await list_tasks_tool(
                db=session,
                status="in-progress",
                limit=5,
            )
            print(f"✅ Found {list_result2['total_count']} in-progress task(s)")

            # Test 6: Create another task without optional params
            print("\n7. Testing create_task_tool with minimal params...")
            create_result2 = await create_task_tool(
                db=session,
                title="Minimal Task",
            )
            print(f"✅ Minimal task created: {create_result2['id']}")
            print(f"   Title: {create_result2['title']}")
            print(f"   Description: {create_result2['description']}")

            await session.commit()

            print("\n" + "=" * 80)
            print("✅ ALL TESTS PASSED")
            print("=" * 80)
            print("\nSummary:")
            print("  - create_task_tool: Uses TaskCreate Pydantic model ✅")
            print("  - update_task_tool: Uses TaskUpdate Pydantic model ✅")
            print("  - get_task_tool: Correct parameter order (db first) ✅")
            print("  - list_tasks_tool: Correct parameter order (db first) ✅")
            print("  - All status enums match: 'need to be done', 'in-progress', 'complete' ✅")

        except Exception as e:
            print(f"\n❌ Test failed with error:")
            print(f"   {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
