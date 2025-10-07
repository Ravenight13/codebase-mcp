"""Manual test for FastMCP server startup and tool registration.

This test verifies that:
1. FastMCP server instance is properly initialized
2. All 6 tools are registered correctly
3. Database SessionLocal is initialized
4. Server can start without errors
5. Tool introspection works correctly
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.mcp.server_fastmcp import mcp
from src.database import SessionLocal


async def test_tools_registered() -> None:
    """Verify all 6 tools are registered with correct schemas."""
    print("Testing tool registration...")

    # Get all registered tools (returns dict[str, Tool])
    tools_dict = await mcp.get_tools()
    tool_names = list(tools_dict.keys())

    # Expected tools
    expected_tools = {
        "search_code",
        "index_repository",
        "create_task",
        "get_task",
        "list_tasks",
        "update_task"
    }

    actual_tools = set(tool_names)

    # Verify count
    assert len(tool_names) == 6, f"Expected 6 tools, got {len(tool_names)}"

    # Verify exact set match
    assert actual_tools == expected_tools, (
        f"Tool mismatch:\n"
        f"  Expected: {sorted(expected_tools)}\n"
        f"  Actual:   {sorted(actual_tools)}\n"
        f"  Missing:  {sorted(expected_tools - actual_tools)}\n"
        f"  Extra:    {sorted(actual_tools - expected_tools)}"
    )

    print("✅ All 6 tools registered correctly:")
    for name in sorted(tool_names):
        print(f"  - {name}")

    # Verify each tool has a function and is executable
    print("\nVerifying tool executability...")
    for name, tool in tools_dict.items():
        assert hasattr(tool, 'fn'), f"Tool {name} missing 'fn' attribute"
        assert hasattr(tool, 'run'), f"Tool {name} missing 'run' method"
        assert callable(tool.fn), f"Tool {name}.fn is not callable"
        assert tool.name == name, f"Tool name mismatch: expected {name}, got {tool.name}"
        print(f"  ✅ {name}: executable (fn: {tool.fn.__name__})")


async def test_database_initialized() -> None:
    """Verify database connection is initialized and working."""
    print("\nTesting database initialization...")

    # Import database initialization functions
    from src.database import init_db_connection, close_db_connection, SessionLocal as SL

    # Initialize database connection
    try:
        await init_db_connection()
        print("✅ Database connection pool initialized")
    except Exception as e:
        raise AssertionError(f"Failed to initialize database: {e}")

    # Verify SessionLocal is now initialized
    # Need to import again to get the updated global variable
    from src.database import SessionLocal
    assert SessionLocal is not None, "SessionLocal is None after initialization"
    print("✅ SessionLocal is initialized")

    # Try to create a session and verify it works
    try:
        async with SessionLocal() as session:
            assert session is not None, "Database session creation returned None"

            # Verify we can interact with the session
            from sqlalchemy import text
            result = await session.execute(text("SELECT 1"))
            assert result is not None, "Query returned None"
            print("✅ Database connection working")

    except Exception as e:
        raise AssertionError(f"Failed to create or use database session: {e}")

    # Clean up: close database connection
    try:
        await close_db_connection()
        print("✅ Database connection pool closed")
    except Exception as e:
        print(f"⚠️  Warning: Failed to close database connection: {e}")

    print("✅ Database initialization test complete")


async def test_server_introspection() -> None:
    """Test that server introspection works correctly."""
    print("\nTesting server introspection...")

    # Get server name and version
    assert mcp.name == "codebase-mcp", f"Unexpected server name: {mcp.name}"
    assert mcp.version is not None, "Server version is None"

    print(f"✅ Server info:")
    print(f"  - Name: {mcp.name}")
    print(f"  - Version: {mcp.version}")


async def test_tool_schemas_complete() -> None:
    """Verify that all tools have complete schemas and descriptions."""
    print("\nTesting tool schemas and metadata...")

    tools_dict = await mcp.get_tools()

    # Verify each tool has required metadata
    for tool_name, tool in tools_dict.items():
        assert tool.description is not None, f"Tool '{tool_name}' missing description"
        assert tool.parameters is not None, f"Tool '{tool_name}' missing parameters schema"

        # Check parameter schema has expected structure
        params = tool.parameters
        assert "type" in params, f"Tool '{tool_name}' parameters missing 'type'"
        assert params["type"] == "object", f"Tool '{tool_name}' parameters type not 'object'"

        # All tools should have properties defined (even if empty)
        assert "properties" in params, f"Tool '{tool_name}' parameters missing 'properties'"

        param_count = len(params.get("properties", {}))
        print(f"  ✅ {tool_name}: complete schema ({param_count} parameters)")


async def main() -> None:
    """Run all tests."""
    print("=" * 60)
    print("FastMCP Server Startup Test Suite")
    print("=" * 60)
    print()

    try:
        await test_tools_registered()
        await test_database_initialized()
        await test_server_introspection()
        await test_tool_schemas_complete()

        print()
        print("=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print()
        print("=" * 60)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 60)
        return 1

    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
