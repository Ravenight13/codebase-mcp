# Recommended Contract Test Fixes
**Feature**: FastMCP Migration (002-refactor-mcp-server)
**Priority**: Low (Not blocking, implementation is correct)
**Impact**: 3 contract tests need updating for FastMCP architecture

---

## Fix 1: Update `test_tools_are_callable`

**File**: `tests/contract/test_tool_registration.py`
**Line**: 131
**Status**: Test expectation incorrect for FastMCP architecture

### Current Code (Failing)
```python
# Check if tool has __call__ attribute (is callable)
assert hasattr(tool_obj, "__call__"), (
    f"Tool '{tool_name}' is not callable\n"
    f"Fix: Ensure tool is properly registered with @mcp.tool() decorator"
)
```

### Recommended Fix
```python
# Check if tool has underlying callable function (FastMCP pattern)
assert hasattr(tool_obj, "fn") and callable(tool_obj.fn), (
    f"Tool '{tool_name}' does not have callable function\n"
    f"Fix: Ensure tool is properly registered with @mcp.tool() decorator"
)
```

### Explanation
- FastMCP returns `FunctionTool` objects (not directly callable)
- `FunctionTool.fn` contains the actual callable function
- Test should check for `fn` attribute instead of `__call__`

---

## Fix 2: Update `test_server_validation_fails_with_no_tools`

**File**: `tests/contract/test_transport_compliance.py`
**Line**: 270
**Status**: Obsolete TDD test (tools now registered)

### Current Code (Failing)
```python
@pytest.mark.contract
@pytest.mark.asyncio
async def test_server_validation_fails_with_no_tools() -> None:
    """
    Test server startup validation MUST fail when no tools are registered.

    This is the PRIMARY test that validates TDD approach - it MUST fail
    until tools are registered in subsequent tasks (T008-T013).
    """
    from src.mcp.server_fastmcp import mcp, validate_server_startup

    # Server validation should fail because no tools are registered yet
    with pytest.raises(RuntimeError) as exc_info:
        await validate_server_startup(mcp)

    error_message = str(exc_info.value)
    assert "validation failed" in error_message.lower()
    assert "no tools registered" in error_message.lower()
```

### Recommended Fix Option 1: Mark as Obsolete
```python
@pytest.mark.skip(reason="Obsolete TDD test - all tools now registered (Phase 3.3)")
@pytest.mark.contract
@pytest.mark.asyncio
async def test_server_validation_fails_with_no_tools() -> None:
    """
    OBSOLETE: This test validated TDD approach during Phase 3.1.
    Now that all tools are registered (Phase 3.3), this test is no longer valid.

    Original purpose: Verify server validation fails when no tools registered.
    Current state: All 6 tools registered, validation succeeds.
    """
    pass
```

### Recommended Fix Option 2: Test Opposite Case
```python
@pytest.mark.contract
@pytest.mark.asyncio
async def test_server_validation_succeeds_with_all_tools() -> None:
    """
    Test server startup validation succeeds when all tools are registered.

    This validates that after Phase 3.3 (tool migration), the server
    properly validates all 6 expected tools are registered.
    """
    from src.mcp.server_fastmcp import mcp, validate_server_startup

    # Server validation should succeed with all tools registered
    await validate_server_startup(mcp)  # Should not raise

    # Verify all expected tools present
    registered_tools = await mcp.get_tools()
    assert len(registered_tools) == 6
```

---

## Fix 3: Update `test_server_get_tools_returns_empty_dict`

**File**: `tests/contract/test_transport_compliance.py`
**Line**: 334
**Status**: Obsolete TDD test (tools now registered)

### Current Code (Failing)
```python
@pytest.mark.contract
@pytest.mark.asyncio
async def test_server_get_tools_returns_empty_dict() -> None:
    """
    Test mcp.get_tools() currently returns empty dict.

    This test documents current state (no tools registered).
    After T008-T013, this test will need updating to verify tools exist.
    """
    from src.mcp.server_fastmcp import mcp

    registered_tools = await mcp.get_tools()

    # Currently no tools registered
    assert isinstance(registered_tools, dict)
    assert len(registered_tools) == 0
```

### Recommended Fix
```python
@pytest.mark.contract
@pytest.mark.asyncio
async def test_server_get_tools_returns_all_tools() -> None:
    """
    Test mcp.get_tools() returns all 6 registered tools.

    After Phase 3.3 (tool migration), this test validates that
    all expected tools are registered and accessible.
    """
    from src.mcp.server_fastmcp import mcp

    registered_tools = await mcp.get_tools()

    # All 6 tools should be registered
    assert isinstance(registered_tools, dict)
    assert len(registered_tools) == 6

    # Verify expected tool set
    expected_tools = {
        "search_code",
        "index_repository",
        "create_task",
        "get_task",
        "list_tasks",
        "update_task",
    }
    assert set(registered_tools.keys()) == expected_tools
```

---

## Implementation Checklist

### Fix 1: Tool Callability Test ✅ READY TO APPLY
- [ ] Open `tests/contract/test_tool_registration.py`
- [ ] Navigate to line 131 (inside `test_tools_are_callable`)
- [ ] Replace `hasattr(tool_obj, "__call__")` with `hasattr(tool_obj, "fn") and callable(tool_obj.fn)`
- [ ] Run test: `uv run pytest tests/contract/test_tool_registration.py::test_tools_are_callable -v`
- [ ] Verify: Test should now PASS

### Fix 2: Server Validation Test ✅ READY TO APPLY
Choose **Option 1** (Mark as Obsolete) OR **Option 2** (Test Opposite Case)

**Recommended**: Option 1 (simpler, documents history)

- [ ] Open `tests/contract/test_transport_compliance.py`
- [ ] Navigate to line 270 (`test_server_validation_fails_with_no_tools`)
- [ ] Apply chosen fix (Option 1 or Option 2)
- [ ] Run test: `uv run pytest tests/contract/test_transport_compliance.py::test_server_validation_fails_with_no_tools -v`
- [ ] Verify: Test should SKIP (Option 1) or PASS (Option 2)

### Fix 3: Get Tools Test ✅ READY TO APPLY
- [ ] Open `tests/contract/test_transport_compliance.py`
- [ ] Navigate to line 334 (`test_server_get_tools_returns_empty_dict`)
- [ ] Replace test implementation with recommended fix
- [ ] Run test: `uv run pytest tests/contract/test_transport_compliance.py::test_server_get_tools_returns_empty_dict -v`
- [ ] Verify: Test should now PASS

### Validation After Fixes
```bash
# Run all contract tests
uv run pytest tests/contract/ -v --tb=short -m contract

# Expected result: 121/121 PASSED (100%)
```

---

## Why These Fixes Are Low Priority

1. **Implementation is Correct**: All failures are test contract issues, not bugs
2. **No Functional Impact**: Server works correctly, tools are operational
3. **High Pass Rate**: 97.5% of tests already passing (118/121)
4. **Documented Issues**: Clear understanding of root causes
5. **Non-Blocking**: Does not prevent Phase 4 (Git Integration & Claude Desktop)

### When to Apply Fixes

**Option A**: Before Pull Request
- Clean up all test failures for 100% pass rate
- Professional presentation for code review

**Option B**: Separate Cleanup PR
- Complete FastMCP migration first
- Create follow-up PR for test contract updates

**Option C**: During Phase 4
- Apply fixes alongside Claude Desktop integration
- Batch related test updates together

**Recommendation**: Apply during Phase 4 for efficiency.

---

## Testing Commands

### Individual Test Execution
```bash
# Test 1: Tool callability
uv run pytest tests/contract/test_tool_registration.py::test_tools_are_callable -v

# Test 2: Server validation
uv run pytest tests/contract/test_transport_compliance.py::test_server_validation_fails_with_no_tools -v

# Test 3: Get tools
uv run pytest tests/contract/test_transport_compliance.py::test_server_get_tools_returns_empty_dict -v
```

### Full Suite Validation
```bash
# All contract tests
uv run pytest tests/contract/ -v -m contract

# Current expected: 118/121 PASSED
# After fixes: 121/121 PASSED
```

---

**Document Created**: 2025-10-06
**Phase**: 3.4 - Integration & Validation
**Status**: Ready for implementation
