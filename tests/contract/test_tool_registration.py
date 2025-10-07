"""
T005: Contract test for tool registration validation.

This test validates that all 6 MCP tools are correctly registered with the @mcp.tool()
decorator in the FastMCP server implementation.

TDD Approach:
- Test MUST fail initially (tools not yet decorated in server_fastmcp.py)
- After T008-T013 (tool migration), test should pass
- Validates both registration and callability of tools

Constitutional Compliance:
- Principle VII: TDD (tests written first, must fail initially)
- Principle VIII: Type Safety (full type annotations)
- Principle XI: FastMCP Foundation (validates FastMCP decorator registration)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastmcp import FastMCP

# Expected tools for Codebase MCP Server
EXPECTED_TOOLS = {
    "search_code",
    "index_repository",
    "create_task",
    "get_task",
    "list_tasks",
    "update_task",
}


@pytest.fixture
def mcp_server() -> FastMCP:
    """Fixture providing the FastMCP server instance.

    Returns:
        FastMCP server instance from server_fastmcp.py
    """
    from src.mcp.server_fastmcp import mcp

    return mcp


@pytest.mark.contract
@pytest.mark.asyncio
async def test_all_tools_registered(mcp_server: FastMCP) -> None:
    """Verify all 6 MCP tools are registered with @mcp.tool() decorator.

    This test validates that the server has registered all required tools
    for the Codebase MCP Server functionality.

    Expected to FAIL initially:
    - server_fastmcp.py has no @mcp.tool() decorators yet
    - Tools will be migrated in T008-T013

    Expected to PASS after:
    - T008: search_code migration
    - T009: index_repository migration
    - T010: create_task migration
    - T011: get_task migration
    - T012: list_tasks migration
    - T013: update_task migration

    Args:
        mcp_server: FastMCP server instance from fixture

    Raises:
        AssertionError: If registered tools don't match expected tools
    """
    # Get registered tools from FastMCP server
    registered_tools_dict = await mcp_server.get_tools()
    registered_tool_names = set(registered_tools_dict.keys())

    # Validate: All expected tools are registered
    missing_tools = EXPECTED_TOOLS - registered_tool_names
    extra_tools = registered_tool_names - EXPECTED_TOOLS

    # Assertion 1: Check for missing tools
    assert not missing_tools, (
        f"Missing expected tools: {missing_tools}\n"
        f"Expected: {sorted(EXPECTED_TOOLS)}\n"
        f"Registered: {sorted(registered_tool_names)}\n"
        f"Fix: Add @mcp.tool() decorator to missing tool handlers in T008-T013"
    )

    # Assertion 2: Check for unexpected extra tools
    assert not extra_tools, (
        f"Unexpected tools registered: {extra_tools}\n"
        f"Expected: {sorted(EXPECTED_TOOLS)}\n"
        f"Registered: {sorted(registered_tool_names)}\n"
        f"Fix: Remove unexpected tool registrations from server_fastmcp.py"
    )

    # Assertion 3: Validate exact count
    assert len(registered_tool_names) == 6, (
        f"Expected exactly 6 tools, found {len(registered_tool_names)}\n"
        f"Registered: {sorted(registered_tool_names)}"
    )


@pytest.mark.contract
@pytest.mark.asyncio
async def test_tools_are_callable(mcp_server: FastMCP) -> None:
    """Verify each registered tool is callable (proper decorator registration).

    This test validates that all registered tools have been properly decorated
    with @mcp.tool() and are callable functions.

    Args:
        mcp_server: FastMCP server instance from fixture

    Raises:
        AssertionError: If any tool is not callable
    """
    # Get registered tools from FastMCP server
    registered_tools_dict = await mcp_server.get_tools()

    # Skip test if no tools registered (expected initial state)
    if not registered_tools_dict:
        pytest.skip("No tools registered yet - expected for TDD initial state")

    # Validate: Each tool is callable
    for tool_name, tool_obj in registered_tools_dict.items():
        # Check if tool has __call__ attribute (is callable)
        assert hasattr(tool_obj, "__call__"), (
            f"Tool '{tool_name}' is not callable\n"
            f"Fix: Ensure tool is properly registered with @mcp.tool() decorator"
        )

        # Validate tool name matches expected set
        assert tool_name in EXPECTED_TOOLS, (
            f"Tool '{tool_name}' is not in expected tool set\n"
            f"Expected: {sorted(EXPECTED_TOOLS)}\n"
            f"Fix: Remove unexpected tool registration or update EXPECTED_TOOLS"
        )


@pytest.mark.contract
@pytest.mark.asyncio
async def test_tool_registration_count(mcp_server: FastMCP) -> None:
    """Verify exactly 6 tools are registered (no more, no less).

    This test provides a focused assertion on the tool count, making it
    easy to identify when tools are missing or extras are added.

    Args:
        mcp_server: FastMCP server instance from fixture

    Raises:
        AssertionError: If tool count is not exactly 6
    """
    registered_tools_dict = await mcp_server.get_tools()
    tool_count = len(registered_tools_dict)

    assert tool_count == 6, (
        f"Expected exactly 6 tools registered, found {tool_count}\n"
        f"Registered tools: {sorted(registered_tools_dict.keys()) if tool_count > 0 else 'None'}\n"
        f"Expected tools: {sorted(EXPECTED_TOOLS)}\n"
        f"Fix: Complete tool migration in T008-T013"
    )


@pytest.mark.contract
@pytest.mark.asyncio
async def test_search_code_tool_registered(mcp_server: FastMCP) -> None:
    """Verify search_code tool is registered (T008 validation)."""
    registered_tools_dict = await mcp_server.get_tools()
    assert "search_code" in registered_tools_dict, (
        "search_code tool not registered\n"
        "Fix: Complete T008 - migrate search_code tool with @mcp.tool() decorator"
    )


@pytest.mark.contract
@pytest.mark.asyncio
async def test_index_repository_tool_registered(mcp_server: FastMCP) -> None:
    """Verify index_repository tool is registered (T009 validation)."""
    registered_tools_dict = await mcp_server.get_tools()
    assert "index_repository" in registered_tools_dict, (
        "index_repository tool not registered\n"
        "Fix: Complete T009 - migrate index_repository tool with @mcp.tool() decorator"
    )


@pytest.mark.contract
@pytest.mark.asyncio
async def test_create_task_tool_registered(mcp_server: FastMCP) -> None:
    """Verify create_task tool is registered (T010 validation)."""
    registered_tools_dict = await mcp_server.get_tools()
    assert "create_task" in registered_tools_dict, (
        "create_task tool not registered\n"
        "Fix: Complete T010 - migrate create_task tool with @mcp.tool() decorator"
    )


@pytest.mark.contract
@pytest.mark.asyncio
async def test_get_task_tool_registered(mcp_server: FastMCP) -> None:
    """Verify get_task tool is registered (T011 validation)."""
    registered_tools_dict = await mcp_server.get_tools()
    assert "get_task" in registered_tools_dict, (
        "get_task tool not registered\n"
        "Fix: Complete T011 - migrate get_task tool with @mcp.tool() decorator"
    )


@pytest.mark.contract
@pytest.mark.asyncio
async def test_list_tasks_tool_registered(mcp_server: FastMCP) -> None:
    """Verify list_tasks tool is registered (T012 validation)."""
    registered_tools_dict = await mcp_server.get_tools()
    assert "list_tasks" in registered_tools_dict, (
        "list_tasks tool not registered\n"
        "Fix: Complete T012 - migrate list_tasks tool with @mcp.tool() decorator"
    )


@pytest.mark.contract
@pytest.mark.asyncio
async def test_update_task_tool_registered(mcp_server: FastMCP) -> None:
    """Verify update_task tool is registered (T013 validation)."""
    registered_tools_dict = await mcp_server.get_tools()
    assert "update_task" in registered_tools_dict, (
        "update_task tool not registered\n"
        "Fix: Complete T013 - migrate update_task tool with @mcp.tool() decorator"
    )


@pytest.mark.contract
@pytest.mark.asyncio
async def test_no_duplicate_tool_registrations(mcp_server: FastMCP) -> None:
    """Verify no duplicate tool registrations exist.

    This test ensures that each tool is registered exactly once,
    preventing registration conflicts or unexpected behavior.

    Args:
        mcp_server: FastMCP server instance from fixture

    Raises:
        AssertionError: If duplicate tool registrations are detected
    """
    registered_tools_dict = await mcp_server.get_tools()
    tool_names = list(registered_tools_dict.keys())

    # Check for duplicates by comparing list length to set length
    unique_tool_names = set(tool_names)

    assert len(tool_names) == len(unique_tool_names), (
        f"Duplicate tool registrations detected\n"
        f"Tool names: {tool_names}\n"
        f"Unique names: {unique_tool_names}\n"
        f"Fix: Ensure each tool is registered only once with @mcp.tool()"
    )
