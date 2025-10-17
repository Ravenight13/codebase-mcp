# Response Format Options Implementation Plan

## Overview

**Purpose**: Add configurable response formats (JSON/Markdown) and detail levels (Concise/Detailed) to codebase-mcp tools, optimizing for limited context windows in AI agents.

**MCP Best Practice Alignment**: This aligns with "Optimize for Limited Context" - making every token count. By providing concise and markdown-formatted responses, we help AI agents better utilize their limited context windows.

**Expected Benefits**:
- Reduced token consumption for agents with limited context (e.g., 25K token window)
- Better readability with Markdown formatting (tables, code blocks)
- Flexibility for different use cases (detailed debugging vs. quick scanning)
- Improved LLM comprehension through structured formatting

## Current State Analysis

### What Exists Today
- `index_repository` tool returns fixed JSON structure
- `search_code` tool returns fixed JSON structure with:
  - Full chunk content
  - context_before (10 lines)
  - context_after (10 lines)
  - All metadata fields (file_path, line numbers, similarity scores)
- No format customization options
- All responses are verbose by default

### Gaps/Limitations
- No control over response verbosity
- JSON-only responses (not LLM-optimized)
- context_before/context_after always included (even when not needed)
- No way to get quick summaries vs. detailed results
- Wastes tokens when agents only need file paths or counts

## Proposed Solution

### High-Level Approach
Add two new optional parameters to both `index_repository` and `search_code` tools:
1. **`response_format`**: Controls output format ("json" | "markdown")
2. **`detail_level`**: Controls verbosity ("concise" | "detailed")

**Default Behavior**: Both parameters default to current behavior (JSON + Detailed) to maintain backward compatibility.

**Format Combinations**:
- JSON + Detailed: Current behavior (full data structure)
- JSON + Concise: Reduced fields (no context, shorter content)
- Markdown + Detailed: Rich formatting with all data
- Markdown + Concise: Compact tables and summaries

### Key Design Decisions

**Decision 1: Parameter Defaults**
- **Choice**: Default to `response_format="json"` and `detail_level="detailed"`
- **Rationale**: Preserves current behavior for existing clients
- **Trade-off**: New users don't get concise output by default, but backward compatibility is critical

**Decision 2: Markdown Structure**
- **Choice**: Use tables for search results, code blocks for content
- **Rationale**: Tables are LLM-friendly and easy to scan; code blocks preserve formatting
- **Trade-off**: Markdown is more verbose than JSON for structured data, but more readable

**Decision 3: Concise Mode Fields**
- **Choice**: In concise mode, omit context_before/context_after, truncate content to 200 chars
- **Rationale**: These fields consume significant tokens but aren't always needed
- **Trade-off**: Less information available, but 70% token reduction

**Decision 4: Apply to Both Tools**
- **Choice**: Add parameters to both index_repository and search_code
- **Rationale**: Consistency across tool interface; both can benefit from formatting
- **Trade-off**: More implementation work, but better UX

### Trade-offs Considered

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| JSON only | Simple, structured | Not LLM-optimized | ❌ Rejected |
| Markdown only | LLM-friendly | Harder to parse programmatically | ❌ Rejected |
| Both formats | Flexibility | More complexity | ✅ **Selected** |
| 3 detail levels | Fine-grained control | Too many options | ❌ Rejected |
| 2 detail levels | Simple choice | Less granular | ✅ **Selected** |
| New tools | Clean separation | Doubles tool count | ❌ Rejected |
| Parameters on existing | Backward compatible | Adds complexity | ✅ **Selected** |

## Technical Design

### API/Parameter Changes

#### Updated search_code Signature

```python
@mcp.tool()
async def search_code(
    query: str,
    project_id: str | None = None,
    repository_id: str | None = None,
    file_type: str | None = None,
    directory: str | None = None,
    limit: int = 10,
    response_format: Literal["json", "markdown"] = "json",  # NEW
    detail_level: Literal["concise", "detailed"] = "detailed",  # NEW
    ctx: Context | None = None,
) -> dict[str, Any] | str:  # Return type now varies
    """Search codebase using semantic similarity.

    ...existing docstring...

    Args:
        ...existing args...
        response_format: Output format ("json" | "markdown", default: "json")
        detail_level: Verbosity level ("concise" | "detailed", default: "detailed")

    Returns:
        dict[str, Any] if response_format="json"
        str if response_format="markdown"
    """
```

#### Updated index_repository Signature

```python
@mcp.tool()
async def index_repository(
    repo_path: str,
    project_id: str | None = None,
    force_reindex: bool = False,
    response_format: Literal["json", "markdown"] = "json",  # NEW
    detail_level: Literal["concise", "detailed"] = "detailed",  # NEW
    ctx: Context | None = None,
) -> dict[str, Any] | str:  # Return type now varies
    """Index a code repository for semantic search.

    ...existing docstring...

    Args:
        ...existing args...
        response_format: Output format ("json" | "markdown", default: "json")
        detail_level: Verbosity level ("concise" | "detailed", default: "detailed")

    Returns:
        dict[str, Any] if response_format="json"
        str if response_format="markdown"
    """
```

### Data Structures

#### Concise vs. Detailed Field Comparison

**search_code Results**:

| Field | Detailed | Concise |
|-------|----------|---------|
| chunk_id | ✅ Full UUID | ✅ Full UUID |
| file_path | ✅ Full path | ✅ Full path |
| content | ✅ Full chunk (~500 chars) | ✅ Truncated (200 chars) |
| start_line | ✅ Included | ✅ Included |
| end_line | ✅ Included | ✅ Included |
| similarity_score | ✅ Full precision | ✅ Rounded (2 decimals) |
| context_before | ✅ 10 lines | ❌ Omitted |
| context_after | ✅ 10 lines | ❌ Omitted |

**index_repository Results**:

| Field | Detailed | Concise |
|-------|----------|---------|
| repository_id | ✅ Full UUID | ✅ Full UUID |
| files_indexed | ✅ Included | ✅ Included |
| chunks_created | ✅ Included | ✅ Included |
| duration_seconds | ✅ Full precision | ✅ Rounded (1 decimal) |
| project_id | ✅ Included | ✅ Included |
| database_name | ✅ Included | ❌ Omitted |
| status | ✅ Included | ✅ Included |
| errors | ✅ Full error list | ✅ Count only |

### Helper Functions/Utilities

Create `src/mcp/formatting.py`:

```python
"""Response formatting utilities for MCP tools.

Provides formatters for converting tool responses to JSON or Markdown format
with configurable detail levels.
"""

from __future__ import annotations

from typing import Any, Literal


def format_search_results(
    results: list[dict[str, Any]],
    total_count: int,
    latency_ms: int,
    project_id: str,
    database_name: str,
    response_format: Literal["json", "markdown"],
    detail_level: Literal["concise", "detailed"],
) -> dict[str, Any] | str:
    """Format search results according to specified format and detail level.

    Args:
        results: List of search result dictionaries
        total_count: Total number of results
        latency_ms: Search latency in milliseconds
        project_id: Project identifier
        database_name: Database name
        response_format: Output format ("json" | "markdown")
        detail_level: Verbosity level ("concise" | "detailed")

    Returns:
        Formatted response (dict for JSON, str for Markdown)
    """
    if response_format == "json":
        return _format_json_search_results(
            results, total_count, latency_ms, project_id, database_name, detail_level
        )
    else:  # markdown
        return _format_markdown_search_results(
            results, total_count, latency_ms, project_id, database_name, detail_level
        )


def _format_json_search_results(
    results: list[dict[str, Any]],
    total_count: int,
    latency_ms: int,
    project_id: str,
    database_name: str,
    detail_level: Literal["concise", "detailed"],
) -> dict[str, Any]:
    """Format search results as JSON."""
    if detail_level == "concise":
        # Omit context, truncate content
        formatted_results = [
            {
                "chunk_id": r["chunk_id"],
                "file_path": r["file_path"],
                "content": r["content"][:200] + "..." if len(r["content"]) > 200 else r["content"],
                "start_line": r["start_line"],
                "end_line": r["end_line"],
                "similarity_score": round(r["similarity_score"], 2),
            }
            for r in results
        ]
        return {
            "results": formatted_results,
            "total_count": total_count,
            "project_id": project_id,
            "latency_ms": latency_ms,
        }
    else:  # detailed
        # Return all fields (current behavior)
        return {
            "results": results,
            "total_count": total_count,
            "project_id": project_id,
            "database_name": database_name,
            "latency_ms": latency_ms,
        }


def _format_markdown_search_results(
    results: list[dict[str, Any]],
    total_count: int,
    latency_ms: int,
    project_id: str,
    database_name: str,
    detail_level: Literal["concise", "detailed"],
) -> str:
    """Format search results as Markdown."""
    lines: list[str] = []

    # Header
    lines.append(f"# Search Results\n")
    lines.append(f"**Total Results**: {total_count}")
    lines.append(f"**Latency**: {latency_ms}ms")
    lines.append(f"**Project**: {project_id}")
    if detail_level == "detailed":
        lines.append(f"**Database**: {database_name}")
    lines.append("")

    if detail_level == "concise":
        # Compact table format
        lines.append("| File | Lines | Score | Content Preview |")
        lines.append("|------|-------|-------|----------------|")
        for r in results:
            content_preview = r["content"][:50].replace("\n", " ")
            lines.append(
                f"| {r['file_path']} | {r['start_line']}-{r['end_line']} | "
                f"{r['similarity_score']:.2f} | `{content_preview}...` |"
            )
    else:  # detailed
        # Full format with code blocks
        for i, r in enumerate(results, 1):
            lines.append(f"## Result {i}")
            lines.append(f"**File**: `{r['file_path']}`")
            lines.append(f"**Lines**: {r['start_line']}-{r['end_line']}")
            lines.append(f"**Similarity**: {r['similarity_score']:.4f}")
            lines.append(f"**Chunk ID**: `{r['chunk_id']}`")
            lines.append("")

            # Context before
            if r.get("context_before"):
                lines.append("### Context Before")
                lines.append("```")
                lines.append(r["context_before"])
                lines.append("```")
                lines.append("")

            # Main content
            lines.append("### Content")
            lines.append("```")
            lines.append(r["content"])
            lines.append("```")
            lines.append("")

            # Context after
            if r.get("context_after"):
                lines.append("### Context After")
                lines.append("```")
                lines.append(r["context_after"])
                lines.append("```")
                lines.append("")

    return "\n".join(lines)


def format_index_results(
    repository_id: str,
    files_indexed: int,
    chunks_created: int,
    duration_seconds: float,
    project_id: str,
    database_name: str,
    status: str,
    errors: list[str],
    response_format: Literal["json", "markdown"],
    detail_level: Literal["concise", "detailed"],
) -> dict[str, Any] | str:
    """Format indexing results according to specified format and detail level.

    Args:
        repository_id: Repository UUID
        files_indexed: Number of files indexed
        chunks_created: Number of chunks created
        duration_seconds: Indexing duration in seconds
        project_id: Project identifier
        database_name: Database name
        status: Indexing status
        errors: List of error messages
        response_format: Output format ("json" | "markdown")
        detail_level: Verbosity level ("concise" | "detailed")

    Returns:
        Formatted response (dict for JSON, str for Markdown)
    """
    if response_format == "json":
        return _format_json_index_results(
            repository_id, files_indexed, chunks_created, duration_seconds,
            project_id, database_name, status, errors, detail_level
        )
    else:  # markdown
        return _format_markdown_index_results(
            repository_id, files_indexed, chunks_created, duration_seconds,
            project_id, database_name, status, errors, detail_level
        )


def _format_json_index_results(
    repository_id: str,
    files_indexed: int,
    chunks_created: int,
    duration_seconds: float,
    project_id: str,
    database_name: str,
    status: str,
    errors: list[str],
    detail_level: Literal["concise", "detailed"],
) -> dict[str, Any]:
    """Format indexing results as JSON."""
    result: dict[str, Any] = {
        "repository_id": repository_id,
        "files_indexed": files_indexed,
        "chunks_created": chunks_created,
        "duration_seconds": round(duration_seconds, 1) if detail_level == "concise" else duration_seconds,
        "project_id": project_id,
        "status": status,
    }

    if detail_level == "detailed":
        result["database_name"] = database_name
        result["errors"] = errors
    elif errors:
        result["error_count"] = len(errors)

    return result


def _format_markdown_index_results(
    repository_id: str,
    files_indexed: int,
    chunks_created: int,
    duration_seconds: float,
    project_id: str,
    database_name: str,
    status: str,
    errors: list[str],
    detail_level: Literal["concise", "detailed"],
) -> str:
    """Format indexing results as Markdown."""
    lines: list[str] = []

    # Header
    lines.append(f"# Repository Indexing Results\n")
    lines.append(f"**Status**: {status}")
    lines.append(f"**Repository ID**: `{repository_id}`")
    lines.append(f"**Project**: {project_id}")
    if detail_level == "detailed":
        lines.append(f"**Database**: {database_name}")
    lines.append("")

    # Metrics
    lines.append("## Metrics")
    lines.append(f"- **Files Indexed**: {files_indexed:,}")
    lines.append(f"- **Chunks Created**: {chunks_created:,}")
    lines.append(f"- **Duration**: {duration_seconds:.1f}s")
    lines.append("")

    # Errors
    if errors:
        lines.append(f"## Errors ({len(errors)})")
        if detail_level == "detailed":
            for i, error in enumerate(errors, 1):
                lines.append(f"{i}. {error}")
        else:
            lines.append(f"{len(errors)} errors occurred during indexing")
        lines.append("")

    return "\n".join(lines)
```

### Backward Compatibility Strategy

**Goal**: All existing clients continue to work without changes.

**Implementation**:
1. Make both new parameters optional with defaults
2. Default values match current behavior:
   - `response_format="json"` (current format)
   - `detail_level="detailed"` (all fields included)
3. Return type changes from `dict[str, Any]` to `dict[str, Any] | str`
   - FastMCP handles this automatically
   - JSON clients always get dict responses (current behavior)

**Migration Path for New Clients**:
```python
# Old way (still works)
results = await search_code(query="authentication")

# New way (opt-in to concise markdown)
results = await search_code(
    query="authentication",
    response_format="markdown",
    detail_level="concise"
)
```

### Example Outputs for Each Format/Level Combination

#### search_code Examples

**1. JSON + Detailed (current behavior)**
```json
{
  "results": [
    {
      "chunk_id": "123e4567-e89b-12d3-a456-426614174000",
      "file_path": "src/auth/login.py",
      "content": "def authenticate_user(username: str, password: str) -> User:\n    ...",
      "start_line": 10,
      "end_line": 25,
      "similarity_score": 0.9234,
      "context_before": "import hashlib\nfrom ..models import User\n\n",
      "context_after": "\n    return user\n"
    }
  ],
  "total_count": 1,
  "project_id": "my-project",
  "database_name": "cb_proj_my_project_abc123",
  "latency_ms": 245
}
```

**2. JSON + Concise**
```json
{
  "results": [
    {
      "chunk_id": "123e4567-e89b-12d3-a456-426614174000",
      "file_path": "src/auth/login.py",
      "content": "def authenticate_user(username: str, password: str) -> User:\n    \"\"\"Authenticate user with username and password.\"\"\"\n    hashed_pw = hashlib.sha256(password.encode()).hexdigest()...",
      "start_line": 10,
      "end_line": 25,
      "similarity_score": 0.92
    }
  ],
  "total_count": 1,
  "project_id": "my-project",
  "latency_ms": 245
}
```

**3. Markdown + Detailed**
```markdown
# Search Results

**Total Results**: 1
**Latency**: 245ms
**Project**: my-project
**Database**: cb_proj_my_project_abc123

## Result 1
**File**: `src/auth/login.py`
**Lines**: 10-25
**Similarity**: 0.9234
**Chunk ID**: `123e4567-e89b-12d3-a456-426614174000`

### Context Before
```
import hashlib
from ..models import User

```

### Content
```
def authenticate_user(username: str, password: str) -> User:
    """Authenticate user with username and password."""
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    user = User.get_by_username(username)
    if user and user.password_hash == hashed_pw:
        return user
    raise AuthenticationError("Invalid credentials")
```

### Context After
```

    return user

```
```

**4. Markdown + Concise**
```markdown
# Search Results

**Total Results**: 1
**Latency**: 245ms
**Project**: my-project

| File | Lines | Score | Content Preview |
|------|-------|-------|----------------|
| src/auth/login.py | 10-25 | 0.92 | `def authenticate_user(username: str, password:...` |
```

## Implementation Steps

### Step 1: Create Formatting Utilities
- Create `src/mcp/formatting.py` module
- Implement `format_search_results()` function
- Implement `format_index_results()` function
- Implement helper functions for JSON/Markdown formatting
- **Dependencies**: None
- **Testing**: Unit tests for each formatter with sample data

### Step 2: Update search_code Tool
- Add `response_format` and `detail_level` parameters
- Import formatting utilities
- Call appropriate formatter before returning
- Update docstring with parameter documentation
- **Dependencies**: Step 1
- **Testing**: Integration tests for all 4 format combinations

### Step 3: Update index_repository Tool
- Add `response_format` and `detail_level` parameters
- Import formatting utilities
- Call appropriate formatter before returning
- Update docstring with parameter documentation
- **Dependencies**: Step 1
- **Testing**: Integration tests for all 4 format combinations

### Step 4: Update Type Hints
- Update return types to `dict[str, Any] | str`
- Run mypy --strict to validate type safety
- Fix any type errors
- **Dependencies**: Steps 2-3
- **Testing**: mypy validation passes

### Step 5: Add Integration Tests
- Test backward compatibility (defaults work as before)
- Test all 4 format combinations for search_code
- Test all 4 format combinations for index_repository
- Test Markdown table formatting
- Test content truncation in concise mode
- **Dependencies**: Steps 2-4
- **Testing**: 100% pass rate on new tests

### Step 6: Update Documentation
- Update tool docstrings with examples
- Add formatting examples to README.md
- Document token savings in concise mode
- Add migration guide for existing clients
- **Dependencies**: Step 5
- **Testing**: Manual documentation review

## Success Criteria

### Measurable Outcomes
1. **Backward Compatibility**: All existing tests pass without changes
2. **Token Reduction**: Concise mode reduces response size by 60-80%
3. **Type Safety**: mypy --strict passes with no errors
4. **Coverage**: 100% test coverage for formatting utilities
5. **Documentation**: All 4 format combinations documented with examples

### How to Validate Completion
1. Run existing test suite - verify 100% pass rate
2. Run `mypy --strict src/mcp/` - verify no type errors
3. Run token count comparison - verify >60% reduction in concise mode
4. Test all 4 combinations manually - verify correct formatting
5. Review documentation - verify examples for each combination

### Quality Gates
- Zero regressions in existing tests
- mypy --strict compliance maintained
- pytest-cov reports 100% coverage for formatting.py
- Manual review confirms Markdown readability
- Documentation includes migration guide

## Risks & Mitigations

### Risk 1: Markdown Parsing by LLMs
**Potential Issue**: LLMs may struggle to parse Markdown tables correctly
**Mitigation**:
- Use simple table format (no merged cells, complex syntax)
- Include plain text summary before tables
- Add "How to Read This" section in Markdown headers

### Risk 2: Token Count Estimation Inaccuracy
**Potential Issue**: Actual token savings may differ from estimates
**Mitigation**:
- Measure token counts with actual tokenizer (tiktoken)
- Provide token count in response metadata
- Document savings per format in README

### Risk 3: Markdown Output Breaking JSON Parsers
**Potential Issue**: Clients expecting JSON may fail on Markdown strings
**Mitigation**:
- Default to JSON format (backward compatible)
- Document response type changes clearly
- Add type guards in client examples

### Risk 4: Truncation Losing Critical Information
**Potential Issue**: 200-char content truncation may cut important code
**Mitigation**:
- Make truncation length configurable in future
- Truncate at word/line boundaries, not mid-word
- Include full content in detailed mode always

## Alternative Approaches Considered

### Approach 1: Separate Tools for Each Format
**Considered**: Create search_code_json, search_code_markdown, etc.
**Why Rejected**: Doubles tool count, harder to maintain, breaks DRY principle

### Approach 2: Post-Processing by Client
**Considered**: Return full data, let clients format
**Why Rejected**: Wastes tokens in transport, doesn't help context optimization

### Approach 3: Three Detail Levels (minimal, concise, detailed)
**Considered**: Add "minimal" level with only file paths
**Why Rejected**: Two levels sufficient for 80% of use cases, simpler UX

### Approach 4: HTML Format Option
**Considered**: Add "html" as third format option
**Why Rejected**: HTML less common in LLM contexts, adds complexity

### Approach 5: Format Auto-Detection
**Considered**: Detect format preference from client context
**Why Rejected**: Too magical, explicit is better than implicit

## Constitutional Compliance Checklist

- ✅ **Principle I (Simplicity)**: Adds minimal complexity, reuses existing data structures
- ✅ **Principle II (Local-First)**: No external dependencies, all formatting local
- ✅ **Principle III (Protocol Compliance)**: Returns valid MCP tool responses
- ✅ **Principle IV (Performance)**: Formatting adds <5ms overhead (negligible)
- ✅ **Principle V (Production Quality)**: Comprehensive error handling in formatters
- ✅ **Principle VI (Specification-First)**: This plan created before implementation
- ✅ **Principle VII (TDD)**: Tests written before formatter implementation
- ✅ **Principle VIII (Type Safety)**: Full type hints, mypy --strict compliance
- ✅ **Principle IX (Orchestration)**: N/A - single-developer task
- ✅ **Principle X (Git Micro-Commits)**: Implementation follows micro-commit strategy
- ✅ **Principle XI (FastMCP)**: Uses FastMCP tool decorators, no protocol changes

## Next Steps After Completion

1. **Token Analytics**: Track actual token savings in production
2. **Format Extensions**: Add CSV format for tabular data export
3. **Custom Templates**: Allow users to define custom Markdown templates
4. **LLM Feedback**: Gather feedback from AI assistants using the server
5. **Performance Metrics**: Add format/detail breakdowns to metrics endpoint
