# Character Limits and Truncation Implementation Plan

## Overview

**Purpose**: Implement a 25,000 token limit (~100,000 characters) on search results with smart truncation strategies to respect agent context windows while preserving the most relevant information.

**MCP Best Practice Alignment**: This aligns with "Optimize for Limited Context" - respecting agent context windows by proactively managing response size. Many AI agents have 25K-30K token context limits; responses should never exceed these limits.

**Expected Benefits**:
- Prevents context window overflow for AI agents
- Ensures most relevant results are always included
- Provides clear truncation indicators when limits are hit
- Enables monitoring of truncation frequency for optimization
- Improves server reliability by preventing oversized responses

## Current State Analysis

### What Exists Today
- `search_code` returns all matching results up to `limit` parameter (max 50)
- No character/token counting in responses
- No truncation logic for large result sets
- No warnings when responses might overflow context windows
- `limit` parameter caps result count but not total size

### Gaps/Limitations
- A single result with large chunks could exceed context limits
- 50 results with full context could easily exceed 25K tokens
- No visibility into actual response size
- No protection against context overflow
- LLMs may fail or truncate responses unexpectedly

### Concrete Example of Problem
```python
# Searching across large codebase
results = await search_code(query="database", limit=50)

# Each result has:
# - content: ~500 chars (chunk)
# - context_before: ~500 chars (10 lines)
# - context_after: ~500 chars (10 lines)
# - metadata: ~200 chars
# Total per result: ~1,700 chars

# 50 results × 1,700 chars = 85,000 chars (~21,000 tokens)
# With JSON formatting: ~100,000 chars (~25,000 tokens)
# This EXCEEDS many agent context windows!
```

## Proposed Solution

### High-Level Approach
Implement character-based truncation with the following strategy:

1. **Character Limit**: Set hard limit at 100,000 characters (~25,000 tokens)
2. **Estimation**: Use 4:1 character-to-token ratio (conservative estimate)
3. **Prioritization**: Always include highest similarity results first
4. **Smart Truncation**: Truncate at result boundaries, never mid-result
5. **Indicators**: Add `truncated` flag and `truncation_info` to responses
6. **Logging**: Log warnings when truncation occurs for monitoring

### Key Design Decisions

**Decision 1: Character-Based vs. Token-Based Counting**
- **Choice**: Use character count as proxy for tokens (4:1 ratio)
- **Rationale**: Fast to compute, no external tokenizer dependency (offline-first)
- **Trade-off**: Less accurate than actual token counting, but 20% margin provides safety

**Decision 2: Hard Limit at 100K Characters**
- **Choice**: Set CHARACTER_LIMIT = 100,000 (conservative ~25K tokens)
- **Rationale**: Stays under most context windows (25K-30K tokens)
- **Trade-off**: May be too conservative for some agents, but prevents failures

**Decision 3: Result-Boundary Truncation Only**
- **Choice**: Never truncate within a result; remove entire results if needed
- **Rationale**: Preserves result integrity, easier to understand
- **Trade-off**: May remove more data than strictly necessary

**Decision 4: Similarity-Based Prioritization**
- **Choice**: Always include highest similarity_score results first
- **Rationale**: Most relevant results are most valuable to preserve
- **Trade-off**: None - this is strictly better than arbitrary ordering

**Decision 5: Truncation Indicators in Response**
- **Choice**: Add `truncated: bool` and `truncation_info` dict to responses
- **Rationale**: Clients need to know data is incomplete
- **Trade-off**: Adds complexity to response schema, but critical for transparency

### Trade-offs Considered

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| No truncation | Simple | Context overflow risk | ❌ Rejected |
| Hard truncation | Prevents overflow | May lose data | ✅ **Selected** |
| Token counting | Accurate | Requires tokenizer | ❌ Rejected |
| Character estimation | Fast, offline | Less accurate | ✅ **Selected** |
| Mid-result truncation | Maximizes data | Breaks integrity | ❌ Rejected |
| Result-boundary truncation | Clean boundaries | May remove more | ✅ **Selected** |
| Alphabetical priority | Deterministic | Ignores relevance | ❌ Rejected |
| Similarity priority | Relevance-based | Slightly complex | ✅ **Selected** |

## Technical Design

### Constants

Add to `src/services/searcher.py`:

```python
from typing import Final

# Character/token limits (Constitutional Principle IV: Performance)
CHARACTER_LIMIT: Final[int] = 100_000  # ~25,000 tokens at 4:1 ratio
CHAR_TO_TOKEN_RATIO: Final[float] = 4.0  # Conservative estimate
TRUNCATION_MARGIN: Final[float] = 0.8  # Use 80% of limit for safety
EFFECTIVE_CHAR_LIMIT: Final[int] = int(CHARACTER_LIMIT * TRUNCATION_MARGIN)  # 80,000

# Truncation warning threshold (log if approaching limit)
TRUNCATION_WARNING_THRESHOLD: Final[float] = 0.7  # 70% of limit
```

### Data Structures

#### Updated SearchResult Response

```python
# Current response schema (in search.py)
{
    "results": [...],
    "total_count": 10,
    "project_id": "my-project",
    "database_name": "cb_proj_...",
    "latency_ms": 250
}

# New response schema (with truncation info)
{
    "results": [...],
    "total_count": 10,
    "returned_count": 8,  # NEW: Actual results returned (after truncation)
    "project_id": "my-project",
    "database_name": "cb_proj_...",
    "latency_ms": 250,
    "truncated": false,  # NEW: Whether results were truncated
    "truncation_info": {  # NEW: Details about truncation
        "reason": null,  # "character_limit" | "token_estimate" | null
        "original_count": 10,
        "returned_count": 8,
        "estimated_chars": 75000,
        "limit_chars": 80000,
        "estimated_tokens": 18750,
        "limit_tokens": 20000
    }
}
```

#### TruncationInfo Model

```python
from pydantic import BaseModel, Field

class TruncationInfo(BaseModel):
    """Information about result truncation.

    Attributes:
        reason: Why truncation occurred (None if no truncation)
        original_count: Total results before truncation
        returned_count: Actual results returned after truncation
        estimated_chars: Estimated character count of response
        limit_chars: Character limit applied
        estimated_tokens: Estimated token count (chars / CHAR_TO_TOKEN_RATIO)
        limit_tokens: Token limit (limit_chars / CHAR_TO_TOKEN_RATIO)
    """
    reason: str | None = Field(
        None,
        description="Truncation reason ('character_limit' | 'token_estimate' | null)"
    )
    original_count: int = Field(
        description="Total results before truncation"
    )
    returned_count: int = Field(
        description="Results returned after truncation"
    )
    estimated_chars: int = Field(
        description="Estimated character count of full response"
    )
    limit_chars: int = Field(
        description="Character limit applied"
    )
    estimated_tokens: int = Field(
        description="Estimated token count (chars / 4)"
    )
    limit_tokens: int = Field(
        description="Token limit (limit_chars / 4)"
    )
```

### Helper Functions/Utilities

Add to `src/services/searcher.py`:

```python
def estimate_result_size(result: SearchResult) -> int:
    """Estimate character count of a single search result.

    Args:
        result: SearchResult object to estimate

    Returns:
        Estimated character count including JSON formatting overhead
    """
    # Base fields
    size = 0
    size += len(str(result.chunk_id))  # UUID string
    size += len(result.file_path)
    size += len(result.content)
    size += len(str(result.start_line)) + len(str(result.end_line))
    size += 20  # similarity_score as string

    # Context fields (if present)
    if result.context_before:
        size += len(result.context_before)
    if result.context_after:
        size += len(result.context_after)

    # JSON formatting overhead (~20% for brackets, quotes, commas)
    size = int(size * 1.2)

    return size


def estimate_response_size(results: list[SearchResult]) -> int:
    """Estimate total character count of response including metadata.

    Args:
        results: List of SearchResult objects

    Returns:
        Estimated total character count
    """
    # Sum individual result sizes
    total_size = sum(estimate_result_size(r) for r in results)

    # Add metadata overhead (~500 chars for project_id, latency, etc.)
    total_size += 500

    return total_size


def truncate_results_by_size(
    results: list[SearchResult],
    char_limit: int = EFFECTIVE_CHAR_LIMIT,
) -> tuple[list[SearchResult], TruncationInfo]:
    """Truncate results to fit within character limit.

    Results are sorted by similarity score (descending) before truncation
    to ensure most relevant results are preserved.

    Args:
        results: List of SearchResult objects (unsorted)
        char_limit: Maximum character count allowed (default: 80,000)

    Returns:
        Tuple of (truncated_results, truncation_info)
    """
    # Sort by similarity score descending (highest first)
    sorted_results = sorted(
        results,
        key=lambda r: r.similarity_score,
        reverse=True
    )

    # Accumulate results until limit reached
    accumulated_results: list[SearchResult] = []
    accumulated_size = 500  # Start with metadata overhead

    for result in sorted_results:
        result_size = estimate_result_size(result)

        # Check if adding this result would exceed limit
        if accumulated_size + result_size > char_limit:
            # Stop here - don't add partial results
            break

        accumulated_results.append(result)
        accumulated_size += result_size

    # Build truncation info
    original_count = len(results)
    returned_count = len(accumulated_results)
    truncated = (returned_count < original_count)

    truncation_info = TruncationInfo(
        reason="character_limit" if truncated else None,
        original_count=original_count,
        returned_count=returned_count,
        estimated_chars=accumulated_size,
        limit_chars=char_limit,
        estimated_tokens=accumulated_size // 4,
        limit_tokens=char_limit // 4,
    )

    return accumulated_results, truncation_info
```

### Integration into search_code Tool

Update `src/mcp/tools/search.py`:

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
    """Search codebase using semantic similarity.

    ...existing docstring...

    Returns:
        Dictionary with search results and truncation info:
        {
            "results": [...],
            "total_count": 10,
            "returned_count": 8,  # May be less if truncated
            "truncated": false,
            "truncation_info": {...},  # Details if truncated
            ...
        }
    """
    start_time = time.perf_counter()

    # ...existing validation and search logic...

    # Perform semantic search
    async with get_session(project_id=resolved_project_id) as db:
        results: list[SearchResult] = await search_code_service(query, db, filters)

    # TRUNCATION LOGIC (NEW)
    truncated_results, truncation_info = truncate_results_by_size(results)

    # Log truncation warnings
    if truncation_info.truncated:
        logger.warning(
            "Search results truncated to fit character limit",
            extra={
                "context": {
                    "query": query[:100],
                    "original_count": truncation_info.original_count,
                    "returned_count": truncation_info.returned_count,
                    "estimated_chars": truncation_info.estimated_chars,
                    "limit_chars": truncation_info.limit_chars,
                }
            },
        )
        if ctx:
            await ctx.warning(
                f"Results truncated: {truncation_info.returned_count}/"
                f"{truncation_info.original_count} results fit in "
                f"{truncation_info.limit_chars:,} character limit"
            )

    # Log approaching limit warnings
    if not truncation_info.truncated:
        utilization = truncation_info.estimated_chars / truncation_info.limit_chars
        if utilization > TRUNCATION_WARNING_THRESHOLD:
            logger.info(
                "Search results approaching character limit",
                extra={
                    "context": {
                        "query": query[:100],
                        "utilization_pct": int(utilization * 100),
                        "estimated_chars": truncation_info.estimated_chars,
                        "limit_chars": truncation_info.limit_chars,
                    }
                },
            )

    # Calculate latency
    latency_ms = int((time.perf_counter() - start_time) * 1000)

    # Format response with truncation info
    response: dict[str, Any] = {
        "results": [
            {
                "chunk_id": str(result.chunk_id),
                "file_path": result.file_path,
                "content": result.content,
                "start_line": result.start_line,
                "end_line": result.end_line,
                "similarity_score": result.similarity_score,
                "context_before": result.context_before,
                "context_after": result.context_after,
            }
            for result in truncated_results  # Use truncated results
        ],
        "total_count": len(results),  # Original count
        "returned_count": len(truncated_results),  # Actual count returned
        "truncated": truncation_info.reason is not None,
        "truncation_info": truncation_info.model_dump(),
        "project_id": resolved_project_id,
        "database_name": database_name,
        "latency_ms": latency_ms,
    }

    return response
```

### Error Handling

**Scenario 1: Single Result Exceeds Limit**
```python
# If even the top result is too large, return it anyway with warning
if not accumulated_results and sorted_results:
    logger.warning(
        "Single result exceeds character limit - returning anyway",
        extra={"context": {"result_size": result_size, "limit": char_limit}}
    )
    accumulated_results = [sorted_results[0]]
    truncation_info.reason = "single_result_too_large"
```

**Scenario 2: Empty Results**
```python
# If no results match, truncation_info still provides context
if not results:
    truncation_info = TruncationInfo(
        reason=None,
        original_count=0,
        returned_count=0,
        estimated_chars=500,  # Just metadata
        limit_chars=char_limit,
        estimated_tokens=125,
        limit_tokens=char_limit // 4,
    )
```

**Scenario 3: Estimation Error**
```python
# If actual size exceeds estimate (serialization overhead), log error
actual_size = len(json.dumps(response))
if actual_size > CHARACTER_LIMIT:
    logger.error(
        "Response size exceeded limit despite truncation",
        extra={
            "context": {
                "estimated_size": truncation_info.estimated_chars,
                "actual_size": actual_size,
                "limit": CHARACTER_LIMIT,
            }
        },
    )
```

## Implementation Steps

### Step 1: Add Truncation Constants and Models
- Add CHARACTER_LIMIT and related constants to `src/services/searcher.py`
- Create TruncationInfo Pydantic model
- Add type hints and docstrings
- **Dependencies**: None
- **Testing**: mypy --strict validation

### Step 2: Implement Size Estimation Functions
- Implement `estimate_result_size()`
- Implement `estimate_response_size()`
- Add unit tests with known result sizes
- **Dependencies**: Step 1
- **Testing**: Unit tests verify estimates within 20% of actual

### Step 3: Implement Truncation Logic
- Implement `truncate_results_by_size()`
- Add sorting by similarity_score
- Add accumulation loop with size checking
- Build TruncationInfo object
- **Dependencies**: Step 2
- **Testing**: Unit tests with various result counts and sizes

### Step 4: Integrate into search_code Tool
- Add truncation call after search service
- Update response schema with new fields
- Add truncation logging (warnings and info)
- Update Context notifications
- **Dependencies**: Step 3
- **Testing**: Integration tests with real searches

### Step 5: Add Monitoring and Metrics
- Add truncation count to metrics service
- Add average utilization metric
- Add truncation rate histogram
- **Dependencies**: Step 4
- **Testing**: Validate metrics collection in tests

### Step 6: Update Documentation
- Update search_code docstring with truncation info
- Add truncation examples to README.md
- Document how to handle truncated responses
- Add troubleshooting guide for truncation issues
- **Dependencies**: Step 5
- **Testing**: Manual documentation review

## Success Criteria

### Measurable Outcomes
1. **Never Exceeds Limit**: No responses over 100,000 characters
2. **Preserves Relevance**: Top 3 results always included (if <80K chars total)
3. **Transparency**: 100% of truncated responses include truncation_info
4. **Performance**: Truncation logic adds <10ms overhead
5. **Accuracy**: Size estimates within 20% of actual JSON size

### How to Validate Completion
1. Run search with limit=50 on large codebase - verify truncation occurs
2. Verify truncated response has `truncated: true` flag
3. Verify highest similarity results are preserved
4. Verify actual JSON size < 100,000 chars
5. Verify truncation_info matches actual results

### Quality Gates
- Unit tests for estimation functions (95%+ accuracy)
- Integration tests for truncation scenarios
- mypy --strict passes with no errors
- No performance regression (truncation adds <10ms)
- Documentation includes truncation handling examples

## Risks & Mitigations

### Risk 1: Size Estimation Inaccuracy
**Potential Issue**: Character-to-token ratio may be inaccurate for code
**Mitigation**:
- Use conservative 4:1 ratio (most LLMs use 3:1 to 4:1)
- Apply 80% safety margin (TRUNCATION_MARGIN)
- Log estimation errors for monitoring
- Future: Add actual token counting with tiktoken

### Risk 2: Removing Critical Results
**Potential Issue**: Truncation may remove results user needs
**Mitigation**:
- Prioritize by similarity_score (most relevant first)
- Inform user via truncation_info
- Suggest reducing limit or using filters
- Future: Add pagination support

### Risk 3: Performance Overhead
**Potential Issue**: Size estimation on every search may slow responses
**Mitigation**:
- Estimation is O(n) where n is result count (fast)
- Only sort once (O(n log n))
- Cache result sizes if needed
- Target: <10ms overhead (negligible vs. 500ms target)

### Risk 4: Single Large Result
**Potential Issue**: One result could exceed entire limit
**Mitigation**:
- Return largest result anyway with warning
- Set truncation_info.reason = "single_result_too_large"
- Log for monitoring and optimization
- Future: Add result-level truncation option

## Alternative Approaches Considered

### Approach 1: Token-Based Counting with tiktoken
**Considered**: Use actual tokenizer (tiktoken) for accurate counting
**Why Rejected**: Requires external dependency, slower, breaks offline-first principle

### Approach 2: Configurable Limit Parameter
**Considered**: Add `max_chars` parameter to search_code
**Why Rejected**: Adds complexity, most users don't know their context limits

### Approach 3: Pagination Instead of Truncation
**Considered**: Return results in pages with continuation tokens
**Why Rejected**: More complex, requires stateful server; defer to future iteration

### Approach 4: No Limit (Trust Client to Handle)
**Considered**: Let clients handle truncation themselves
**Why Rejected**: Server is better positioned to truncate intelligently with relevance sorting

### Approach 5: Mid-Result Truncation
**Considered**: Truncate content/context fields within results
**Why Rejected**: Breaks result integrity, confusing UX; result-boundary truncation is cleaner

## Constitutional Compliance Checklist

- ✅ **Principle I (Simplicity)**: Simple character-based estimation, no external dependencies
- ✅ **Principle II (Local-First)**: No external tokenizer, fully offline
- ✅ **Principle III (Protocol Compliance)**: Returns valid MCP responses with truncation metadata
- ✅ **Principle IV (Performance)**: <10ms overhead, maintains <500ms p95 target
- ✅ **Principle V (Production Quality)**: Comprehensive error handling, logging, transparency
- ✅ **Principle VI (Specification-First)**: This plan created before implementation
- ✅ **Principle VII (TDD)**: Tests written before truncation logic implementation
- ✅ **Principle VIII (Type Safety)**: TruncationInfo model uses Pydantic, mypy --strict compliant
- ✅ **Principle IX (Orchestration)**: N/A - single-developer task
- ✅ **Principle X (Git Micro-Commits)**: Implementation follows micro-commit strategy
- ✅ **Principle XI (FastMCP)**: No protocol changes, uses FastMCP tool patterns

## Next Steps After Completion

1. **Token Analytics**: Add actual tiktoken counting for accuracy validation
2. **Pagination Support**: Implement continuation tokens for large result sets
3. **Result-Level Truncation**: Add option to truncate content within results
4. **Adaptive Limits**: Adjust limit based on detected agent context window
5. **Truncation Metrics**: Dashboard showing truncation rate and utilization trends
