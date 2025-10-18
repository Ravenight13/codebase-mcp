# Bug 1: Foreground Indexing Returns No Output

## Symptoms
- Tool called: `mcp__codebase-mcp__index_repository`
- Returns: `<system>Tool ran without output or errors</system>`
- Expected: JSON with indexing results including:
  - `repository_id`
  - `files_indexed`
  - `chunks_created`
  - `duration_seconds`
  - `status`
  - `errors` (if any)

## Root Cause Analysis

The issue is **NOT a hang** - it's a **missing return statement** in the foreground indexing tool.

### Code Flow Analysis

1. **Tool Entry Point** (`src/mcp/tools/indexing.py`, lines 46-376)
   - `@mcp.tool()` decorated async function `index_repository()`
   - Expected to return `dict[str, Any]` with indexing results

2. **Success Path** (lines 172-194)
   ```python
   async with get_session(project_id=resolved_id, ctx=ctx) as db:
       result: IndexResult = await index_repository_service(...)
       # Note: get_session auto-commits on success, no manual commit needed

       if ctx:
           await ctx.info(f"Indexed {result.files_indexed} files...")
   ```
   **PROBLEM**: After the `async with` block completes, execution continues to line 195

3. **Exception Handlers** (lines 195-328)
   - Multiple exception handlers: `PoolTimeoutError`, `ConnectionValidationError`, `PoolClosedError`, `Exception`
   - All handlers properly raise `MCPError` or `RuntimeError`
   - These work correctly

4. **Response Formatting** (lines 330-376)
   ```python
   # Format response according to MCP contract
   response: dict[str, Any] = {
       "repository_id": str(result.repository_id),
       "files_indexed": result.files_indexed,
       ...
   }

   # Include errors if any
   if result.errors:
       response["errors"] = result.errors

   logger.info("index_repository completed", ...)

   # Performance warning (optional)
   if result.duration_seconds > target_seconds:
       logger.warning(...)

   return response  # <-- THIS RETURN NEVER EXECUTES
   ```

### The Critical Bug

**Lines 330-376 are UNREACHABLE CODE**

The response formatting code is placed **outside and after** the try/except block. When the happy path completes:

1. `async with get_session()` block finishes at line 194
2. Execution immediately jumps to line 195: `except PoolTimeoutError as e:`
3. Since no exception occurred, Python skips all exception handlers
4. **Python implicitly returns `None` at the end of the function** (line 376+)
5. The response formatting code (lines 330-376) **NEVER EXECUTES**

### Why Background Indexing Works

**Background indexing** (`src/mcp/tools/background_indexing.py`) has correct structure:

```python
@mcp.tool()
async def start_indexing_background(...) -> dict[str, Any]:
    # ... validation and job creation ...

    # Start worker (non-blocking)
    asyncio.create_task(_background_indexing_worker(...))

    # Return immediately (CORRECTLY PLACED)
    return {
        "job_id": str(job_id),
        "status": "pending",
        ...
    }  # <-- This executes because it's at function scope, not after try/except
```

## Code Locations

### Primary Bug Location
- **File**: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/mcp/tools/indexing.py`
- **Lines**: 330-376 (unreachable response formatting code)
- **Root Cause**: Lines 169-328 (try/except block doesn't contain return statement)

### Correct Reference Implementation
- **File**: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/mcp/tools/background_indexing.py`
- **Lines**: 43-140 (correctly structured with return at function scope)

## Proposed Fix

### Option A: Move Response Formatting Inside Try Block (RECOMMENDED)

```python
async def index_repository(
    repo_path: str,
    project_id: str | None = None,
    force_reindex: bool = False,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """..."""
    # Context logging
    if ctx:
        await ctx.info(f"Indexing repository: {repo_path}")

    # 1. Resolve project_id and database_name
    resolved_id, database_name = await resolve_project_id(explicit_id=project_id, ctx=ctx)

    # ... validation code (lines 148-166) ...

    # Perform indexing
    pool_info: dict[str, Any]
    try:
        # Use get_session with project_id for workspace isolation
        async with get_session(project_id=resolved_id, ctx=ctx) as db:
            result: IndexResult = await index_repository_service(
                repo_path=path_obj,
                name=name,
                db=db,
                project_id=resolved_id,
                force_reindex=force_reindex,
            )

            # Send completion notification
            if ctx:
                await ctx.info(
                    f"Indexed {result.files_indexed} files, "
                    f"created {result.chunks_created} chunks in "
                    f"{result.duration_seconds:.1f}s"
                )

        # ✅ MOVE RESPONSE FORMATTING HERE (inside try block, after async with)
        response: dict[str, Any] = {
            "repository_id": str(result.repository_id),
            "files_indexed": result.files_indexed,
            "chunks_created": result.chunks_created,
            "duration_seconds": result.duration_seconds,
            "project_id": resolved_id,
            "database_name": database_name,
            "status": result.status,
        }

        if result.errors:
            response["errors"] = result.errors

        logger.info(
            "index_repository completed",
            extra={"context": {
                "repository_id": str(result.repository_id),
                "files_indexed": result.files_indexed,
                "chunks_created": result.chunks_created,
                "duration_seconds": result.duration_seconds,
                "project_id": resolved_id,
                "database_name": database_name,
                "status": result.status,
                "error_count": len(result.errors),
            }}
        )

        # Performance warning
        target_seconds = (result.files_indexed / 10000) * 60
        if result.duration_seconds > target_seconds and result.files_indexed > 100:
            logger.warning(
                "index_repository duration exceeded target",
                extra={"context": {
                    "duration_seconds": result.duration_seconds,
                    "target_seconds": target_seconds,
                    "files_indexed": result.files_indexed,
                }}
            )

        return response  # ✅ RETURN INSIDE TRY BLOCK

    except PoolTimeoutError as e:
        # ... existing exception handler ...
    except ConnectionValidationError as e:
        # ... existing exception handler ...
    except PoolClosedError as e:
        # ... existing exception handler ...
    except Exception as e:
        # ... existing exception handler ...
```

### Changes Required
1. **Move lines 330-376** to immediately after the `async with get_session()` block (after line 194)
2. **Place return statement inside try block** before exception handlers
3. **No logic changes** - just code reorganization

### Why This Fix Works
- Response formatting executes in the happy path (after successful indexing)
- `result` variable is in scope (created inside `async with` block)
- Return statement executes before exception handlers
- Exception handlers remain unchanged (they all raise, which is correct)

## Testing Plan

### Unit Tests
1. **Test successful indexing returns JSON**
   ```python
   async def test_foreground_indexing_returns_result():
       result = await index_repository(
           repo_path="/path/to/test/repo",
           project_id="test-project"
       )
       assert "repository_id" in result
       assert "files_indexed" in result
       assert result["status"] in ["success", "partial", "failed"]
   ```

2. **Test response structure matches contract**
   ```python
   async def test_response_contract():
       result = await index_repository(repo_path="/test")
       assert set(result.keys()) >= {
           "repository_id", "files_indexed", "chunks_created",
           "duration_seconds", "project_id", "database_name", "status"
       }
   ```

3. **Test error cases still raise exceptions**
   ```python
   async def test_invalid_path_raises():
       with pytest.raises(ValueError, match="Repository path does not exist"):
           await index_repository(repo_path="/nonexistent")
   ```

### Integration Tests
1. Index a small repository (10 files) and verify return structure
2. Index repository with force_reindex=True and verify return
3. Compare foreground vs background indexing results consistency

### Manual Testing
```bash
# 1. Start codebase-mcp server
uv run python -m src.mcp.server_fastmcp

# 2. Call index_repository via MCP client
# Expected: JSON response with indexing results
# Before fix: No output
# After fix: Complete JSON response
```

## Risk Assessment

### Low Risk Changes
- **No logic changes** - pure code reorganization
- **No new dependencies** - uses existing variables and functions
- **No API changes** - same function signature and return type

### Medium Risk Areas
1. **Variable Scope**: `result` variable must be accessible where response is formatted
   - **Mitigation**: `result` is created in `async with` block, accessible in same `try` block

2. **Exception Handling Flow**: Must ensure exceptions still propagate correctly
   - **Mitigation**: All exception handlers remain unchanged, all raise exceptions

3. **Logging Side Effects**: Logger calls in response formatting may have side effects
   - **Mitigation**: Logging is idempotent, no state changes

### Validation Steps
1. ✅ Verify `result` variable scope (in scope after `async with` completes)
2. ✅ Verify exception handlers don't catch success path (they don't - all expect exceptions)
3. ✅ Verify return type matches `dict[str, Any]` (it does)
4. ✅ Verify no variable shadowing issues (no conflicts)

## Related Issues

### Similar Patterns to Check
Search for other tools with try/except blocks that might have response formatting after the block:

```bash
# Find similar patterns
rg -A 5 'return response' src/mcp/tools/ | grep -B 10 'except.*Error'
```

### Documentation Impact
- Update MCP tool contract tests to verify return values
- Add contract test for foreground indexing specifically
- Document pattern: "Always return inside try block for MCP tools"

## Constitutional Compliance

### Principles Addressed
- ✅ **Principle III**: Protocol Compliance (MCP tools MUST return values)
- ✅ **Principle V**: Production Quality (fix critical return value bug)
- ✅ **Principle VIII**: Type Safety (matches declared return type)

### Principles Maintained
- ✅ **Principle I**: Simplicity (minimal change, no new complexity)
- ✅ **Principle IV**: Performance (no performance impact)
- ✅ **Principle XI**: FastMCP Foundation (compatible with @mcp.tool() decorator)
