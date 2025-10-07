"""Contract test for automatic schema generation validation.

This test suite validates that FastMCP automatically generates tool schemas
that match the expected MCP protocol format defined in contract JSON files.

Constitutional Compliance:
- Principle III: Protocol Compliance (MCP protocol schema validation)
- Principle VII: TDD (tests written before tool implementation)
- Principle VIII: Type Safety (complete type annotations, mypy --strict)

Test Expectations:
- MUST FAIL initially (no tools registered yet)
- Will pass after T008-T013 (tool migration complete)
- Validates schema structure, not just presence
- Ensures FastMCP auto-generation matches expected contracts

TDD Approach:
1. Load expected schemas from contracts/*.json
2. Retrieve auto-generated schemas from FastMCP server
3. Compare schemas structurally (not just presence)
4. Validate against MCP protocol format requirements
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from src.mcp.server_fastmcp import mcp

# ==============================================================================
# Constants and Setup
# ==============================================================================

CONTRACTS_DIR = Path(__file__).parent.parent.parent / "specs" / "002-refactor-mcp-server" / "contracts"

# Expected tool names
EXPECTED_SEARCH_TOOL = "search_code"
EXPECTED_INDEXING_TOOL = "index_repository"
EXPECTED_TASK_TOOLS = ["create_task", "get_task", "list_tasks", "update_task"]


# ==============================================================================
# Schema Comparison Utilities
# ==============================================================================


def normalize_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Normalize schema for comparison.

    FastMCP may generate schemas with slight variations in structure
    (e.g., property ordering, additional metadata). This function
    normalizes schemas to enable meaningful comparison.

    Args:
        schema: Schema dictionary to normalize

    Returns:
        Normalized schema dictionary
    """
    # Remove FastMCP-specific metadata that doesn't affect MCP protocol compliance
    normalized = schema.copy()

    # Ensure consistent ordering for comparison
    if "properties" in normalized:
        normalized["properties"] = dict(sorted(normalized["properties"].items()))

    return normalized


def compare_schema_structure(
    generated: dict[str, Any],
    expected: dict[str, Any],
    path: str = "root"
) -> list[str]:
    """Recursively compare schema structures and report differences.

    Args:
        generated: Auto-generated schema from FastMCP
        expected: Expected schema from contract JSON
        path: Current path in schema tree (for error reporting)

    Returns:
        List of difference descriptions (empty if schemas match)
    """
    differences: list[str] = []

    # Check type consistency
    if type(generated) != type(expected):
        differences.append(
            f"{path}: Type mismatch - generated={type(generated).__name__}, "
            f"expected={type(expected).__name__}"
        )
        return differences

    # Compare dictionaries recursively
    if isinstance(expected, dict):
        # Check for missing keys in generated schema
        for key in expected:
            if key not in generated:
                differences.append(f"{path}.{key}: Missing in generated schema")
            else:
                # Recursively compare nested structures
                nested_diffs = compare_schema_structure(
                    generated[key],
                    expected[key],
                    f"{path}.{key}"
                )
                differences.extend(nested_diffs)

        # Check for extra keys in generated schema (warnings, not failures)
        for key in generated:
            if key not in expected:
                differences.append(f"{path}.{key}: Extra key in generated schema (may be acceptable)")

    # Compare lists (order-independent for arrays of primitives)
    elif isinstance(expected, list):
        if len(generated) != len(expected):
            differences.append(
                f"{path}: Length mismatch - generated={len(generated)}, "
                f"expected={len(expected)}"
            )
        else:
            for i, (gen_item, exp_item) in enumerate(zip(generated, expected)):
                nested_diffs = compare_schema_structure(
                    gen_item,
                    exp_item,
                    f"{path}[{i}]"
                )
                differences.extend(nested_diffs)

    # Compare primitive values
    else:
        if generated != expected:
            differences.append(
                f"{path}: Value mismatch - generated={generated!r}, "
                f"expected={expected!r}"
            )

    return differences


# ==============================================================================
# Test: Search Tool Schema Generation
# ==============================================================================


@pytest.mark.asyncio
async def test_search_code_tool_schema_generation() -> None:
    """Verify search_code tool schema matches expected contract.

    This test validates that FastMCP automatically generates a schema for
    the search_code tool that matches the expected MCP protocol format.

    Expected Behavior (TDD):
    - FAILS initially: No tools registered yet (server validation fails)
    - PASSES after T008: search_code tool registered with @mcp.tool()

    Validation:
    - Tool name matches expected identifier
    - Input schema matches contract specification
    - Required fields are properly defined
    - Field types and constraints match expectations

    Constitutional Compliance:
    - Principle III: Protocol Compliance (MCP schema format validation)
    - Principle VII: TDD (test fails before implementation)
    """
    # Load expected schema from contract
    contract_file = CONTRACTS_DIR / "search_tool.json"
    assert contract_file.exists(), (
        f"Contract file not found: {contract_file}\n"
        f"Fix: Ensure contracts/search_tool.json exists in specs directory."
    )

    expected_contract = json.loads(contract_file.read_text())

    # Retrieve registered tools from FastMCP server
    try:
        registered_tools = await mcp.get_tools()
    except Exception as e:
        pytest.fail(
            f"Failed to retrieve tools from FastMCP server: {e}\n"
            f"This is EXPECTED to fail until T008 registers search_code tool.\n"
            f"Current status: No tools registered yet."
        )

    # Check that search_code tool is registered
    if EXPECTED_SEARCH_TOOL not in registered_tools:
        pytest.fail(
            f"Tool '{EXPECTED_SEARCH_TOOL}' not found in registered tools.\n"
            f"Registered tools: {list(registered_tools.keys())}\n"
            f"This is EXPECTED to fail until T008 registers search_code tool.\n"
            f"Fix: Complete T008 to register search_code with @mcp.tool() decorator."
        )

    # Get tool object
    search_tool = registered_tools[EXPECTED_SEARCH_TOOL]

    # Extract generated schema from tool
    # FastMCP tools should have input schema accessible
    # (exact attribute name depends on FastMCP implementation)
    generated_schema: dict[str, Any]
    if hasattr(search_tool, "input_schema"):
        generated_schema = search_tool.input_schema
    elif hasattr(search_tool, "parameters"):
        generated_schema = search_tool.parameters
    else:
        pytest.fail(
            f"Cannot extract input schema from tool '{EXPECTED_SEARCH_TOOL}'.\n"
            f"Tool attributes: {dir(search_tool)}\n"
            f"Fix: Verify FastMCP tool schema generation."
        )

    # Normalize schemas for comparison
    expected_input_schema = expected_contract["inputSchema"]
    normalized_generated = normalize_schema(generated_schema)
    normalized_expected = normalize_schema(expected_input_schema)

    # Compare schema structures
    differences = compare_schema_structure(
        normalized_generated,
        normalized_expected,
        path="search_code.inputSchema"
    )

    # Assert no critical differences
    critical_diffs = [d for d in differences if "Extra key" not in d]
    if critical_diffs:
        pytest.fail(
            f"Search code schema validation failed:\n"
            + "\n".join(f"  - {diff}" for diff in critical_diffs)
        )

    # Log warnings for extra keys (acceptable if they don't break protocol)
    warnings = [d for d in differences if "Extra key" in d]
    if warnings:
        print("\nWarnings (extra keys in generated schema):")
        for warning in warnings:
            print(f"  - {warning}")


# ==============================================================================
# Test: Indexing Tool Schema Generation
# ==============================================================================


@pytest.mark.asyncio
async def test_index_repository_tool_schema_generation() -> None:
    """Verify index_repository tool schema matches expected contract.

    Expected Behavior (TDD):
    - FAILS initially: No tools registered yet
    - PASSES after T009: index_repository tool registered

    Constitutional Compliance:
    - Principle III: Protocol Compliance (MCP schema validation)
    - Principle VII: TDD (test-first development)
    """
    # Load expected schema from contract
    contract_file = CONTRACTS_DIR / "indexing_tool.json"
    assert contract_file.exists(), (
        f"Contract file not found: {contract_file}\n"
        f"Fix: Ensure contracts/indexing_tool.json exists."
    )

    expected_contract = json.loads(contract_file.read_text())

    # Retrieve registered tools
    try:
        registered_tools = await mcp.get_tools()
    except Exception as e:
        pytest.fail(
            f"Failed to retrieve tools: {e}\n"
            f"EXPECTED FAILURE: No tools registered until T009.\n"
        )

    # Check tool registration
    if EXPECTED_INDEXING_TOOL not in registered_tools:
        pytest.fail(
            f"Tool '{EXPECTED_INDEXING_TOOL}' not registered.\n"
            f"Registered: {list(registered_tools.keys())}\n"
            f"EXPECTED FAILURE: Complete T009 to register index_repository."
        )

    # Get tool and extract schema
    indexing_tool = registered_tools[EXPECTED_INDEXING_TOOL]

    generated_schema: dict[str, Any]
    if hasattr(indexing_tool, "input_schema"):
        generated_schema = indexing_tool.input_schema
    elif hasattr(indexing_tool, "parameters"):
        generated_schema = indexing_tool.parameters
    else:
        pytest.fail(
            f"Cannot extract schema from '{EXPECTED_INDEXING_TOOL}'.\n"
            f"Tool attributes: {dir(indexing_tool)}"
        )

    # Compare schemas
    expected_input_schema = expected_contract["inputSchema"]
    differences = compare_schema_structure(
        normalize_schema(generated_schema),
        normalize_schema(expected_input_schema),
        path="index_repository.inputSchema"
    )

    # Validate no critical differences
    critical_diffs = [d for d in differences if "Extra key" not in d]
    if critical_diffs:
        pytest.fail(
            f"Index repository schema validation failed:\n"
            + "\n".join(f"  - {diff}" for diff in critical_diffs)
        )


# ==============================================================================
# Test: Task Tools Schema Generation
# ==============================================================================


@pytest.mark.asyncio
async def test_task_tools_schemas_generation() -> None:
    """Verify all 4 task tool schemas match expected contracts.

    Validates schemas for:
    - create_task
    - get_task
    - list_tasks
    - update_task

    Expected Behavior (TDD):
    - FAILS initially: No tools registered
    - PASSES after T010-T013: All task tools registered

    Constitutional Compliance:
    - Principle III: Protocol Compliance (MCP schema validation)
    - Principle VII: TDD (comprehensive test coverage before implementation)
    """
    # Load expected schemas from contract
    contract_file = CONTRACTS_DIR / "task_tools.json"
    assert contract_file.exists(), (
        f"Contract file not found: {contract_file}\n"
        f"Fix: Ensure contracts/task_tools.json exists."
    )

    task_contracts = json.loads(contract_file.read_text())

    # Map tool names to their contract definitions
    tool_schemas: dict[str, dict[str, Any]] = {
        tool["name"]: tool["inputSchema"]
        for tool in task_contracts["tools"]
    }

    # Retrieve registered tools
    try:
        registered_tools = await mcp.get_tools()
    except Exception as e:
        pytest.fail(
            f"Failed to retrieve tools: {e}\n"
            f"EXPECTED FAILURE: No tools registered until T010-T013.\n"
        )

    # Validate each task tool
    all_failures: list[str] = []

    for tool_name in EXPECTED_TASK_TOOLS:
        # Check tool registration
        if tool_name not in registered_tools:
            all_failures.append(
                f"Tool '{tool_name}' not registered. "
                f"Fix: Complete task tools migration (T010-T013)."
            )
            continue

        # Get expected schema for this tool
        if tool_name not in tool_schemas:
            all_failures.append(
                f"No contract schema found for '{tool_name}' in task_tools.json"
            )
            continue

        expected_schema = tool_schemas[tool_name]

        # Extract generated schema
        tool_obj = registered_tools[tool_name]

        generated_schema: dict[str, Any]
        if hasattr(tool_obj, "input_schema"):
            generated_schema = tool_obj.input_schema
        elif hasattr(tool_obj, "parameters"):
            generated_schema = tool_obj.parameters
        else:
            all_failures.append(
                f"Cannot extract schema from '{tool_name}'. "
                f"Tool attributes: {dir(tool_obj)}"
            )
            continue

        # Compare schemas
        differences = compare_schema_structure(
            normalize_schema(generated_schema),
            normalize_schema(expected_schema),
            path=f"{tool_name}.inputSchema"
        )

        # Collect critical differences
        critical_diffs = [d for d in differences if "Extra key" not in d]
        if critical_diffs:
            all_failures.append(
                f"Schema validation failed for '{tool_name}':\n"
                + "\n".join(f"    - {diff}" for diff in critical_diffs)
            )

    # Report all failures together
    if all_failures:
        pytest.fail(
            "Task tools schema validation failures:\n\n"
            + "\n\n".join(all_failures)
            + "\n\nEXPECTED FAILURES: Complete T010-T013 to register all task tools."
        )


# ==============================================================================
# Test: MCP Protocol Format Validation
# ==============================================================================


@pytest.mark.asyncio
async def test_mcp_protocol_format_compliance() -> None:
    """Validate that all generated schemas comply with MCP protocol format.

    Ensures that auto-generated schemas include all required MCP fields:
    - name (tool identifier)
    - description (tool purpose)
    - inputSchema (Pydantic model -> JSON Schema)

    This test validates protocol-level compliance beyond individual
    tool schema correctness.

    Expected Behavior:
    - FAILS initially: No tools to validate
    - PASSES after tool migration: All tools have proper MCP format

    Constitutional Compliance:
    - Principle III: Protocol Compliance (MCP format requirements)
    """
    # Retrieve registered tools
    try:
        registered_tools = await mcp.get_tools()
    except Exception as e:
        pytest.fail(
            f"Failed to retrieve tools: {e}\n"
            f"EXPECTED FAILURE: No tools registered yet."
        )

    if not registered_tools:
        pytest.fail(
            "No tools registered for protocol validation.\n"
            "EXPECTED FAILURE: Complete T008-T013 to register tools."
        )

    # Validate each registered tool
    protocol_failures: list[str] = []

    for tool_name, tool_obj in registered_tools.items():
        # Check for required MCP protocol fields

        # 1. Tool must have a name
        if not tool_name or not isinstance(tool_name, str):
            protocol_failures.append(
                f"Invalid tool name: {tool_name!r} (must be non-empty string)"
            )

        # 2. Tool must have a description
        if not hasattr(tool_obj, "description") or not tool_obj.description:
            protocol_failures.append(
                f"Tool '{tool_name}' missing description (required by MCP protocol)"
            )

        # 3. Tool must have input schema
        has_schema = (
            hasattr(tool_obj, "input_schema")
            or hasattr(tool_obj, "parameters")
        )
        if not has_schema:
            protocol_failures.append(
                f"Tool '{tool_name}' missing input schema (required by MCP protocol)"
            )

        # 4. Tool must be callable
        if not hasattr(tool_obj, "__call__") and not callable(tool_obj):
            protocol_failures.append(
                f"Tool '{tool_name}' is not callable (must be executable)"
            )

    # Report protocol compliance failures
    if protocol_failures:
        pytest.fail(
            "MCP protocol compliance validation failures:\n\n"
            + "\n".join(f"  - {failure}" for failure in protocol_failures)
        )


# ==============================================================================
# Test: Schema Consistency Across All Tools
# ==============================================================================


@pytest.mark.asyncio
async def test_schema_consistency_across_tools() -> None:
    """Validate consistent schema structure across all registered tools.

    Ensures that all tools follow consistent patterns:
    - All schemas use "type": "object" for inputs
    - All schemas define "properties" and "required" fields
    - All field types are valid JSON Schema types

    This catch-all test validates overall schema quality beyond
    individual tool correctness.

    Expected Behavior:
    - FAILS initially: No tools to validate
    - PASSES after migration: All tools have consistent schema structure
    """
    # Retrieve registered tools
    try:
        registered_tools = await mcp.get_tools()
    except Exception as e:
        pytest.fail(
            f"Failed to retrieve tools: {e}\n"
            f"EXPECTED FAILURE: No tools registered yet."
        )

    if not registered_tools:
        pytest.fail(
            "No tools registered for consistency validation.\n"
            "EXPECTED FAILURE: Complete T008-T013 to register tools."
        )

    # Validate schema consistency
    consistency_failures: list[str] = []

    for tool_name, tool_obj in registered_tools.items():
        # Extract schema
        schema: dict[str, Any] | None = None
        if hasattr(tool_obj, "input_schema"):
            schema = tool_obj.input_schema
        elif hasattr(tool_obj, "parameters"):
            schema = tool_obj.parameters

        if not schema:
            consistency_failures.append(
                f"Tool '{tool_name}': No schema found"
            )
            continue

        # Validate schema structure

        # 1. Schema must be an object type
        if schema.get("type") != "object":
            consistency_failures.append(
                f"Tool '{tool_name}': Schema type must be 'object', "
                f"got {schema.get('type')!r}"
            )

        # 2. Schema must define properties
        if "properties" not in schema:
            consistency_failures.append(
                f"Tool '{tool_name}': Schema missing 'properties' field"
            )

        # 3. Validate property types
        if "properties" in schema:
            for prop_name, prop_def in schema["properties"].items():
                if "type" not in prop_def and "$ref" not in prop_def:
                    consistency_failures.append(
                        f"Tool '{tool_name}', property '{prop_name}': "
                        f"Missing 'type' or '$ref' field"
                    )

        # 4. Required fields should be an array
        if "required" in schema:
            if not isinstance(schema["required"], list):
                consistency_failures.append(
                    f"Tool '{tool_name}': 'required' must be an array, "
                    f"got {type(schema['required']).__name__}"
                )

    # Report consistency failures
    if consistency_failures:
        pytest.fail(
            "Schema consistency validation failures:\n\n"
            + "\n".join(f"  - {failure}" for failure in consistency_failures)
        )
