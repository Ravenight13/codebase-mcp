# Tool Annotations Implementation Plan

## Overview

**Purpose**: Add MCP tool hints (`openWorldHint`, `readOnlyHint`, `idempotentHint`) to all tools in the codebase-mcp server to help LLMs understand tool behavior patterns and make better decisions about tool usage.

**MCP Best Practice Alignment**: This aligns with MCP best practices for tool annotation. Hints help LLMs understand:
- **openWorldHint**: Tool interacts with external systems (filesystem, databases, sessions)
- **readOnlyHint**: Tool doesn't modify state (safe to call repeatedly)
- **idempotentHint**: Tool can be called multiple times with same result

**Expected Benefits**:
- LLMs make smarter tool selection decisions
- Reduced unnecessary tool calls (LLMs know which tools are safe to retry)
- Better parallel execution planning (LLMs know which tools can run concurrently)
- Improved error recovery (LLMs know which operations are safe to retry)
- Better user experience through optimized tool orchestration

## Current State Analysis

### What Exists Today
- Three MCP tools implemented with `@mcp.tool()` decorator:
  - `index_repository`: Indexes code repository
  - `search_code`: Performs semantic search
  - `set_working_directory`: Sets session working directory
- Tools defined in:
  - `src/mcp/tools/indexing.py` (index_repository)
  - `src/mcp/tools/search.py` (search_code)
  - `src/mcp/tools/project.py` (set_working_directory)
- No MCP hints currently applied

### Gaps/Limitations
- LLMs must infer tool behavior from docstrings alone
- No explicit indication of:
  - Which tools interact with external state (filesystem, database)
  - Which tools are read-only vs. write operations
  - Which tools are idempotent (safe to retry)
- LLMs may make suboptimal decisions about:
  - When to retry failed operations
  - Which tools to run in parallel
  - Which tools are safe to call speculatively

## Proposed Solution

### High-Level Approach
Add MCP hints to the `@mcp.tool()` decorator for all three tools based on their actual behavior:

1. **index_repository**:
   - `openWorldHint=True`: Interacts with filesystem (reads files) and database (writes chunks)
   - `readOnlyHint=False`: Modifies database state (creates repository, chunks)
   - `idempotentHint=False`: Multiple calls may have side effects (re-indexing logic)

2. **search_code**:
   - `openWorldHint=True`: Interacts with database (reads chunks) and Ollama (embeddings)
   - `readOnlyHint=True`: Only reads from database, no state modifications
   - `idempotentHint=True`: Same query always returns same results (deterministic)

3. **set_working_directory**:
   - `openWorldHint=True`: Modifies session state (stores working directory context)
   - `readOnlyHint=False`: Modifies session manager state
   - `idempotentHint=True`: Setting same directory multiple times has same effect

### Key Design Decisions

**Decision 1: Conservative Hint Application**
- **Choice**: Only apply hints when behavior is clear and deterministic
- **Rationale**: Wrong hints are worse than no hints (mislead LLMs)
- **Trade-off**: May miss optimization opportunities, but ensures correctness

**Decision 2: Document Hint Rationale**
- **Choice**: Add inline comments explaining each hint's reasoning
- **Rationale**: Helps future maintainers understand hint choices
- **Trade-off**: Slightly more verbose code, but much clearer intent

**Decision 3: Validate Against Actual Behavior**
- **Choice**: Audit actual tool implementation before adding hints
- **Rationale**: Hints must match reality, not assumptions
- **Trade-off**: Requires thorough code review, but ensures accuracy

**Decision 4: Test Hint Effectiveness**
- **Choice**: Create integration tests validating LLM behavior with hints
- **Rationale**: Verify hints actually improve LLM decision-making
- **Trade-off**: Harder to test, but proves value

### Trade-offs Considered

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| Add hints to all tools | Complete coverage | Risk of wrong hints | ✅ **Selected** (after audit) |
| Add hints incrementally | Low risk | Incomplete optimization | ❌ Rejected |
| No hints | No maintenance | LLMs guess behavior | ❌ Rejected |
| Document in docstrings | Human-readable | LLMs may miss | ❌ Rejected |
| Infer from code | Automatic | Complex, error-prone | ❌ Rejected |
| Manual annotation | Explicit, auditable | Requires review | ✅ **Selected** |

## Technical Design

### Hint Definitions for Each Tool

#### 1. index_repository

**Current Decorator**:
```python
@mcp.tool()
async def index_repository(
    repo_path: str,
    project_id: str | None = None,
    force_reindex: bool = False,
    ctx: Context | None = None,
) -> dict[str, Any]:
```

**Updated Decorator with Hints**:
```python
@mcp.tool(
    # Hint: Interacts with filesystem (reads files) and database (writes chunks/embeddings)
    openWorldHint=True,
    # Hint: Modifies database state by creating/updating repository and chunk records
    readOnlyHint=False,
    # Hint: NOT idempotent - force_reindex=True causes different behavior on repeated calls
    # First call creates records, subsequent calls may update or skip based on state
    idempotentHint=False,
)
async def index_repository(
    repo_path: str,
    project_id: str | None = None,
    force_reindex: bool = False,
    ctx: Context | None = None,
) -> dict[str, Any]:
```

**Rationale**:
- **openWorldHint=True**: Tool reads from filesystem (via `Path(repo_path)`) and writes to PostgreSQL
- **readOnlyHint=False**: Creates Repository, CodeFile, and CodeChunk records in database
- **idempotentHint=False**: Behavior changes based on existing state:
  - First call: Creates all records
  - Subsequent call without `force_reindex`: May skip already-indexed files
  - Subsequent call with `force_reindex=True`: Re-indexes everything
  - Not deterministic across calls

**Expected LLM Behavior Change**:
- LLMs will recognize this as a "heavy" operation with side effects
- Won't retry on failure without explicit user confirmation
- Won't run in parallel with other database-modifying operations
- Will check if indexing already occurred before calling again

#### 2. search_code

**Current Decorator**:
```python
@mcp.tool()
async def search_code(
    query: str,
    project_id: str | None = None,
    repository_id: str | None = None,
    file_type: str | None = None,
    directory: str | None = None,
    limit: int = 10,
    ctx: Context | None = None,
) -> dict[str, Any]:
```

**Updated Decorator with Hints**:
```python
@mcp.tool(
    # Hint: Interacts with database (reads chunks via pgvector) and Ollama (generates embeddings)
    openWorldHint=True,
    # Hint: Read-only operation - only queries database, doesn't modify state
    readOnlyHint=True,
    # Hint: Idempotent - same query parameters always return same results
    # (Deterministic given same database state and embedding model)
    idempotentHint=True,
)
async def search_code(
    query: str,
    project_id: str | None = None,
    repository_id: str | None = None,
    file_type: str | None = None,
    directory: str | None = None,
    limit: int = 10,
    ctx: Context | None = None,
) -> dict[str, Any]:
```

**Rationale**:
- **openWorldHint=True**: Queries PostgreSQL database and Ollama embedding service
- **readOnlyHint=True**: Only performs SELECT queries, no INSERT/UPDATE/DELETE
- **idempotentHint=True**: Same query with same parameters returns same results (deterministic)
  - Embedding generation is deterministic for same query text
  - pgvector similarity search is deterministic for same embedding
  - Filters (repository_id, file_type, directory) are deterministic

**Expected LLM Behavior Change**:
- LLMs will recognize this as safe to retry on transient failures
- Can run multiple searches in parallel (read-only, no conflicts)
- Safe to call speculatively to explore results
- Can cache results for same query parameters

#### 3. set_working_directory

**Current Decorator**:
```python
@mcp.tool()
async def set_working_directory(
    directory: str,
    ctx: Context | None = None,
) -> dict[str, Any]:
```

**Updated Decorator with Hints**:
```python
@mcp.tool(
    # Hint: Modifies session state in SessionContextManager (stores working directory)
    openWorldHint=True,
    # Hint: Modifies session state - not a read-only operation
    readOnlyHint=False,
    # Hint: Idempotent - setting same directory multiple times has same effect
    # (Last-write-wins semantics, no accumulation of state)
    idempotentHint=True,
)
async def set_working_directory(
    directory: str,
    ctx: Context | None = None,
) -> dict[str, Any]:
```

**Rationale**:
- **openWorldHint=True**: Modifies session context state in SessionContextManager
- **readOnlyHint=False**: Updates session state (working_directory field)
- **idempotentHint=True**: Calling with same directory multiple times results in same final state
  - Last write wins
  - No accumulation or side effects
  - Deterministic outcome regardless of call count

**Expected LLM Behavior Change**:
- LLMs will recognize this as a state-modifying operation
- Won't retry unnecessarily (since it's idempotent)
- Can call multiple times without concern (idempotent)
- Will recognize this as a "setup" operation to call early in workflow

### FastMCP Hint Syntax

FastMCP uses a `hints` parameter in the `@mcp.tool()` decorator. The full syntax is:

```python
from fastmcp import FastMCP
from fastmcp.hints import ToolHints

@mcp.tool(
    hints=ToolHints(
        openWorld=True,
        readOnly=False,
        idempotent=False,
    )
)
async def my_tool(...) -> ...:
    pass
```

**Note**: FastMCP 0.4.0+ supports inline hint parameters:

```python
@mcp.tool(
    openWorldHint=True,
    readOnlyHint=False,
    idempotentHint=False,
)
async def my_tool(...) -> ...:
    pass
```

We'll use the inline parameter syntax for cleaner code.

### Expected LLM Behavior Improvements

#### Before Hints
```
LLM: "User wants to search for authentication code. Let me call search_code."
[search_code fails with connection error]
LLM: "Hmm, not sure if I should retry. This might modify state. I'll ask the user."
User: "Just retry it"
LLM: [retries successfully]
```

#### After Hints
```
LLM: "User wants to search for authentication code. Let me call search_code."
[search_code fails with connection error]
LLM: "This is a read-only, idempotent operation. Safe to retry automatically."
LLM: [retries successfully without asking]
User: "Found it, thanks!"
```

#### Parallel Execution Before Hints
```
LLM: "User wants to search in Python and JavaScript files. Not sure if I can run these in parallel."
LLM: [runs searches sequentially]
[Takes 1000ms total]
```

#### Parallel Execution After Hints
```
LLM: "User wants to search in Python and JavaScript files. Both are read-only and idempotent."
LLM: [runs searches in parallel]
[Takes 500ms total]
```

### Testing Approach for Hint Effectiveness

Create `tests/integration/test_tool_hints.py`:

```python
"""Integration tests validating MCP tool hints improve LLM behavior.

Tests scenarios where hints should improve tool selection and orchestration.
"""

import pytest


class TestToolHintsBehavior:
    """Test that tool hints correctly describe actual behavior."""

    async def test_index_repository_openworld_hint(self):
        """Verify index_repository actually interacts with filesystem and database."""
        # Verify filesystem interaction (reads files)
        # Verify database interaction (creates records)
        pass

    async def test_index_repository_not_readonly(self):
        """Verify index_repository modifies database state."""
        # Call index_repository
        # Verify new records exist in database
        pass

    async def test_index_repository_not_idempotent(self):
        """Verify index_repository behavior changes on repeated calls."""
        # First call: Creates records
        # Second call without force_reindex: May skip files
        # Second call with force_reindex: Re-indexes
        pass

    async def test_search_code_openworld_hint(self):
        """Verify search_code interacts with database and Ollama."""
        # Verify database query executed
        # Verify Ollama embedding call made
        pass

    async def test_search_code_readonly(self):
        """Verify search_code doesn't modify database state."""
        # Take database snapshot
        # Call search_code
        # Verify database unchanged
        pass

    async def test_search_code_idempotent(self):
        """Verify search_code returns same results on repeated calls."""
        # Call search_code with same parameters
        # Verify results identical
        pass

    async def test_set_working_directory_openworld_hint(self):
        """Verify set_working_directory modifies session state."""
        # Verify session context updated
        pass

    async def test_set_working_directory_not_readonly(self):
        """Verify set_working_directory modifies state."""
        # Get initial session state
        # Call set_working_directory
        # Verify state changed
        pass

    async def test_set_working_directory_idempotent(self):
        """Verify set_working_directory can be called multiple times safely."""
        # Call set_working_directory 3 times with same directory
        # Verify final state same as after first call
        pass
```

### Error Handling

**Scenario 1: FastMCP Doesn't Support Hints**
```python
# Fallback for older FastMCP versions
try:
    @mcp.tool(openWorldHint=True, readOnlyHint=True, idempotentHint=True)
    async def search_code(...):
        pass
except TypeError:
    # FastMCP version doesn't support hints, use decorator without hints
    logger.warning("FastMCP version doesn't support tool hints - upgrade to 0.4.0+")
    @mcp.tool()
    async def search_code(...):
        pass
```

**Scenario 2: Incorrect Hints**
```python
# If behavior changes, update hints immediately
# Example: If search_code becomes non-deterministic due to caching invalidation
@mcp.tool(
    openWorldHint=True,
    readOnlyHint=True,
    idempotentHint=False,  # CHANGED: No longer deterministic
)
async def search_code(...):
    pass
```

## Implementation Steps

### Step 1: Audit Tool Implementations
- Review `index_repository` implementation in `src/services/indexer.py`
- Review `search_code` implementation in `src/services/searcher.py`
- Review `set_working_directory` implementation in `src/mcp/tools/project.py`
- Document actual behavior for each tool (filesystem, database, state changes)
- **Dependencies**: None
- **Testing**: Manual code review

### Step 2: Add Hints to index_repository
- Update `@mcp.tool()` decorator in `src/mcp/tools/indexing.py`
- Add inline comments explaining each hint
- Update docstring to mention hint behavior
- **Dependencies**: Step 1
- **Testing**: mypy --strict validation, server starts successfully

### Step 3: Add Hints to search_code
- Update `@mcp.tool()` decorator in `src/mcp/tools/search.py`
- Add inline comments explaining each hint
- Update docstring to mention hint behavior
- **Dependencies**: Step 1
- **Testing**: mypy --strict validation, server starts successfully

### Step 4: Add Hints to set_working_directory
- Update `@mcp.tool()` decorator in `src/mcp/tools/project.py`
- Add inline comments explaining each hint
- Update docstring to mention hint behavior
- **Dependencies**: Step 1
- **Testing**: mypy --strict validation, server starts successfully

### Step 5: Create Hint Validation Tests
- Create `tests/integration/test_tool_hints.py`
- Implement tests validating each hint matches actual behavior
- Test openWorldHint (filesystem/database interaction)
- Test readOnlyHint (no state modification)
- Test idempotentHint (deterministic results)
- **Dependencies**: Steps 2-4
- **Testing**: 100% pass rate on new tests

### Step 6: Update Documentation
- Update tool docstrings with hint explanations
- Add "Tool Hints" section to README.md
- Document expected LLM behavior improvements
- Add troubleshooting guide for hint-related issues
- **Dependencies**: Step 5
- **Testing**: Manual documentation review

## Success Criteria

### Measurable Outcomes
1. **Coverage**: All 3 tools have appropriate hints applied
2. **Accuracy**: All hints match actual tool behavior (validated by tests)
3. **Documentation**: Each hint has inline comment explaining rationale
4. **Testing**: Integration tests validate each hint claim
5. **Type Safety**: mypy --strict passes with no errors

### How to Validate Completion
1. Run `grep -r "@mcp.tool(" src/mcp/tools/` - verify hints on all decorators
2. Run integration tests - verify all hint validation tests pass
3. Run mypy --strict - verify no type errors
4. Start server - verify tools register with hints (check MCP protocol)
5. Review documentation - verify hints documented in README.md

### Quality Gates
- All 3 tools have openWorldHint, readOnlyHint, idempotentHint defined
- Each hint has inline comment explaining rationale
- Integration tests validate hint accuracy
- mypy --strict compliance maintained
- Server startup successful with hints applied

## Risks & Mitigations

### Risk 1: FastMCP Version Incompatibility
**Potential Issue**: Older FastMCP versions may not support hint parameters
**Mitigation**:
- Document minimum FastMCP version (0.4.0+) in requirements.txt
- Add version check in server startup
- Provide fallback decorator without hints for older versions

### Risk 2: Incorrect Hints Misleading LLMs
**Potential Issue**: Wrong hints could cause LLMs to make bad decisions
**Mitigation**:
- Thorough code audit before adding hints
- Integration tests validating hint accuracy
- Monitor LLM behavior after deployment
- Quick rollback plan if hints cause issues

### Risk 3: Hints Becoming Stale
**Potential Issue**: Code changes may invalidate hints over time
**Mitigation**:
- Add hint validation to CI pipeline (integration tests)
- Document hints in code review checklist
- Quarterly audit of all tool hints

### Risk 4: LLMs Ignoring Hints
**Potential Issue**: Some LLMs may not use hints effectively
**Mitigation**:
- Hints are additive - no harm if ignored
- Document expected behavior improvements
- Monitor metrics to validate effectiveness

## Alternative Approaches Considered

### Approach 1: No Hints (Status Quo)
**Considered**: Leave tools without hints
**Why Rejected**: Misses optimization opportunities, LLMs must guess behavior

### Approach 2: Infer Hints from Code Analysis
**Considered**: Automatically detect hints via static analysis
**Why Rejected**: Too complex, error-prone; manual annotation more reliable

### Approach 3: Document in Docstrings Only
**Considered**: Add hint information to docstrings instead of decorator
**Why Rejected**: LLMs may miss docstring details; formal hints more reliable

### Approach 4: Add Hints to Resources Too
**Considered**: Also add hints to `health://` and `metrics://` resources
**Why Rejected**: MCP hints primarily designed for tools; defer for now

### Approach 5: Runtime Hint Validation
**Considered**: Validate hints match behavior at runtime
**Why Rejected**: Complex, adds overhead; integration tests sufficient

## Constitutional Compliance Checklist

- ✅ **Principle I (Simplicity)**: Hints add minimal complexity, just decorator parameters
- ✅ **Principle II (Local-First)**: Hints don't affect offline operation
- ✅ **Principle III (Protocol Compliance)**: Hints are standard MCP feature
- ✅ **Principle IV (Performance)**: Hints have zero runtime overhead
- ✅ **Principle V (Production Quality)**: Comprehensive testing validates hint accuracy
- ✅ **Principle VI (Specification-First)**: This plan created before implementation
- ✅ **Principle VII (TDD)**: Integration tests written to validate hints
- ✅ **Principle VIII (Type Safety)**: Hints fully typed, mypy --strict compliant
- ✅ **Principle IX (Orchestration)**: N/A - single-developer task
- ✅ **Principle X (Git Micro-Commits)**: Implementation follows micro-commit strategy
- ✅ **Principle XI (FastMCP)**: Uses FastMCP hint feature as designed

## Next Steps After Completion

1. **Metrics Collection**: Track LLM retry behavior before/after hints
2. **Prompt Optimization**: Use hints to generate better tool selection prompts
3. **Resource Hints**: Add hints to health/metrics resources if beneficial
4. **Documentation**: Create "Best Practices for Tool Hints" guide
5. **Monitoring**: Track hint-related LLM behavior in production analytics
