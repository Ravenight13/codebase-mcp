"""
Validation script for FastMCP Context.session_id attribute.

This script verifies that the FastMCP Context class has a session_id attribute
and that it can be accessed in tool signatures for session tracking.

Requirements:
1. FastMCP Context class has session_id attribute
2. Context can be passed as a parameter to functions
3. The session_id attribute is accessible and writable
"""

from __future__ import annotations

import inspect
import sys
from typing import Any

from fastmcp import Context


def validate_context_session_id() -> dict[str, Any]:
    """
    Validate FastMCP Context.session_id attribute exists and is accessible.

    Returns:
        Dictionary with validation results.

    Raises:
        AssertionError: If validation fails.
    """
    results: dict[str, Any] = {
        "has_session_id": False,
        "session_id_value": None,
        "can_pass_to_function": False,
        "signature_inspection": None,
    }

    # Test 1: Validate Context has session_id attribute
    print("Test 1: Checking Context has session_id attribute...")
    ctx = Context(session_id="test-session")
    results["has_session_id"] = hasattr(ctx, "session_id")
    assert results["has_session_id"], "Context missing session_id attribute"
    print("  ✓ Context has session_id attribute")

    # Test 2: Validate session_id value is accessible
    print("\nTest 2: Checking session_id value is accessible...")
    results["session_id_value"] = ctx.session_id
    assert results["session_id_value"] == "test-session", "session_id not accessible"
    print(f"  ✓ session_id value accessible: {results['session_id_value']}")

    # Test 3: Validate Context can be passed to functions
    print("\nTest 3: Checking Context can be passed to functions...")

    def sample_tool(ctx: Context) -> str:
        """Sample tool that accepts Context parameter."""
        return f"Session ID: {ctx.session_id}"

    result = sample_tool(ctx)
    results["can_pass_to_function"] = True
    assert result == "Session ID: test-session", "Function parameter passing failed"
    print("  ✓ Context can be passed as function parameter")
    print(f"    - Function result: {result}")

    # Test 4: Inspect function signature
    print("\nTest 4: Inspecting function signature...")
    sig = inspect.signature(sample_tool)
    results["signature_inspection"] = {
        "parameters": list(sig.parameters.keys()),
        "ctx_annotation": str(sig.parameters["ctx"].annotation),
    }
    print(f"  ✓ Function signature inspection successful")
    print(f"    - Parameters: {results['signature_inspection']['parameters']}")
    print(f"    - Context annotation: {results['signature_inspection']['ctx_annotation']}")

    # Test 5: Validate session_id can be modified
    print("\nTest 5: Checking session_id can be modified...")
    ctx.session_id = "modified-session"
    assert ctx.session_id == "modified-session", "session_id not writable"
    print(f"  ✓ session_id is writable")
    print(f"    - Modified value: {ctx.session_id}")

    return results


def main() -> int:
    """
    Main validation entry point.

    Returns:
        0 if validation passes, 1 otherwise.
    """
    print("=" * 70)
    print("FastMCP Context.session_id Validation")
    print("=" * 70)
    print()

    try:
        results = validate_context_session_id()

        print("\n" + "=" * 70)
        print("VALIDATION SUMMARY")
        print("=" * 70)
        print("✓ All validation tests PASSED")
        print()
        print("Results:")
        print(f"  - Context has session_id: {results['has_session_id']}")
        print(f"  - session_id accessible: {results['session_id_value'] is not None}")
        print(f"  - Can pass to functions: {results['can_pass_to_function']}")
        print(f"  - Signature parameters: {results['signature_inspection']['parameters']}")
        print()
        print("✓ FastMCP Context.session_id is ready for session tracking implementation")
        print("=" * 70)

        return 0

    except AssertionError as e:
        print("\n" + "=" * 70)
        print("VALIDATION FAILED")
        print("=" * 70)
        print(f"✗ Assertion Error: {e}")
        print()
        print("Please ensure FastMCP Context includes session_id attribute.")
        print("=" * 70)
        return 1

    except Exception as e:
        print("\n" + "=" * 70)
        print("VALIDATION ERROR")
        print("=" * 70)
        print(f"✗ Unexpected Error: {e}")
        print()
        import traceback
        traceback.print_exc()
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
