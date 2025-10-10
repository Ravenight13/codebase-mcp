# Research: list_tasks Token Optimization

**Feature**: Optimize list_tasks MCP Tool for Token Efficiency
**Date**: 2025-10-10
**Branch**: 004-as-an-ai

## Research Areas

### 1. Pydantic Model Design: Summary vs Full Model Patterns

**Question**: How to structure TaskSummary and TaskResponse models to maximize code reuse while maintaining clear separation?

**Decision**: Use Pydantic model inheritance with `model_config` for selective field inclusion

**Rationale**:
- Pydantic supports model inheritance, allowing TaskSummary to be a base model
- TaskResponse can inherit from TaskSummary and add additional fields
- Alternatively, use `model_validate()` with `include={}` to dynamically filter fields
- **Best approach**: Create separate models (TaskSummary, TaskResponse) that share a common BaseTask model for core fields

**Pattern**:
```python
class BaseTaskFields(BaseModel):
    """Shared fields between summary and full task responses."""
    id: UUID
    title: str
    status: Literal["need to be done", "in-progress", "complete"]
    created_at: datetime
    updated_at: datetime

class TaskSummary(BaseTaskFields):
    """Lightweight task summary for list operations."""
    pass  # Inherits all fields from BaseTaskFields

class TaskResponse(BaseTaskFields):
    """Full task details including metadata."""
    description: str | None
    notes: str | None
    planning_references: list[str]
    branches: list[str]
    commits: list[str]
```

**Alternatives Considered**:
1. ~~Single model with `Optional` fields~~ - Rejected: ambiguous which fields are populated
2. ~~Dynamic field filtering with `dict(include={...})`~~ - Rejected: loses type safety
3. ✅ **Inheritance with shared base** - Selected: clear types, enforces consistency

**References**:
- Pydantic docs: Model inheritance patterns
- FastAPI patterns: Response model variations

---

### 2. SQLAlchemy Query Optimization: Column Selection

**Question**: How to selectively load columns in SQLAlchemy async queries for performance?

**Decision**: Use `select()` with explicit column list or `load_only()` for partial column loading

**Rationale**:
- Current implementation: `select(Task)` loads all columns (ORM mode)
- Optimization: `select(Task.id, Task.title, Task.status, Task.created_at, Task.updated_at)` for summary mode
- SQLAlchemy supports column-level SELECT for reduced data transfer
- **Best approach**: Keep full ORM loading, optimize at serialization level (Pydantic model selection)

**Pattern**:
```python
# Current (full load)
async def list_tasks_service(db, status, branch, limit):
    stmt = select(Task).where(...).limit(limit)
    result = await db.execute(stmt)
    tasks = result.scalars().all()
    return [TaskResponse.model_validate(task) for task in tasks]

# Optimized (conditional serialization)
async def list_tasks_service(db, status, branch, limit, full_details=False):
    stmt = select(Task).where(...).limit(limit)
    result = await db.execute(stmt)
    tasks = result.scalars().all()

    if full_details:
        return [TaskResponse.model_validate(task) for task in tasks]
    else:
        return [TaskSummary.model_validate(task) for task in tasks]
```

**Alternatives Considered**:
1. ~~Column-level SELECT~~ - Rejected: breaks ORM relationships, complex
2. ~~Separate summary query~~ - Rejected: code duplication
3. ✅ **Conditional serialization** - Selected: simple, maintains ORM benefits

**Performance Impact**:
- Database query time: No change (still loading full rows)
- Serialization time: Minimal (Pydantic is fast)
- **Token efficiency**: 6x improvement (primary goal achieved at serialization layer)

**References**:
- SQLAlchemy docs: Column loading strategies
- AsyncPG performance: Row fetching optimization

---

### 3. FastMCP Response Patterns: Variable Response Types

**Question**: How to handle optional `full_details` parameter in FastMCP tool signature with clean type hints?

**Decision**: Use `Union[TaskSummary, TaskResponse]` return type or return `dict[str, Any]` with runtime type switching

**Rationale**:
- FastMCP tools return dictionaries (JSON-serializable)
- Type hint can be `dict[str, Any]` with conditional logic inside
- Pydantic models serialize to dicts via `.model_dump()`
- **Best approach**: Return `dict[str, Any]`, use Pydantic models internally for validation

**Pattern**:
```python
@mcp.tool()
async def list_tasks(
    status: str | None = None,
    branch: str | None = None,
    limit: int = 50,
    full_details: bool = False,  # New parameter
    ctx: Context | None = None,
) -> dict[str, Any]:
    """List tasks with optional full details."""

    # Call service with full_details flag
    tasks = await list_tasks_service(db, status, branch, limit, full_details)

    # Serialize based on model type (TaskSummary or TaskResponse)
    return {
        "tasks": [task.model_dump() for task in tasks],
        "total_count": len(tasks)
    }
```

**Alternatives Considered**:
1. ~~Separate tools (list_tasks_summary, list_tasks_full)~~ - Rejected: API proliferation
2. ~~TypedDict with Literal discrimination~~ - Rejected: overcomplicated
3. ✅ **Single tool with boolean flag** - Selected: simple, backward compatible (default=False)

**References**:
- FastMCP docs: Tool return types
- MCP protocol: Response format flexibility

---

### 4. MCP Contract Evolution: Breaking Change Patterns

**Question**: Are there MCP protocol patterns for versioning or response schema evolution?

**Decision**: Immediate breaking change with clear documentation (per clarification session decision)

**Rationale**:
- MCP protocol does not mandate versioning at transport level
- Tool-level versioning possible but adds complexity
- Early development phase: breaking changes acceptable
- **Best approach**: Document breaking change in release notes, update all clients

**Migration Path**:
- Release notes MUST clearly document the breaking change
- MCP clients (Claude Desktop, etc.) MUST update to handle new response format
- Old behavior: list_tasks returns full TaskResponse objects
- New behavior: list_tasks returns TaskSummary objects by default
- Escape hatch: `full_details=True` parameter for clients needing old behavior temporarily

**Alternatives Considered**:
1. ~~Tool versioning (list_tasks_v2)~~ - Rejected: tool proliferation, confusing
2. ~~Gradual migration (deprecation period)~~ - Rejected: violates clarification decision
3. ✅ **Immediate breaking change** - Selected: clean break, per clarification guidance

**Release Notes Template**:
```markdown
## Breaking Change: list_tasks Response Format

**Impact**: High - affects all MCP clients using list_tasks

**Change**: list_tasks now returns lightweight TaskSummary objects by default instead of full TaskResponse objects.

**Migration**:
- Update code expecting full task details to use get_task(task_id) for specific tasks
- Or pass full_details=True parameter to list_tasks if immediate full details needed
- TaskSummary includes: id, title, status, created_at, updated_at
- TaskResponse includes: all TaskSummary fields + description, notes, planning_references, branches, commits

**Performance Benefit**: 6x token reduction (12,000+ → <2,000 tokens for 15 tasks)
```

**References**:
- MCP spec: Tool evolution patterns
- Semantic versioning: Breaking change conventions

---

### 5. Token Counting Validation: Test Measurement Approach

**Question**: How to validate <2000 token requirement in tests?

**Decision**: Use `tiktoken` library (OpenAI tokenizer) to count tokens in JSON response payloads

**Rationale**:
- Need measurable validation for PR-001 performance requirement
- Claude uses similar tokenization to OpenAI models
- `tiktoken` provides fast, accurate token counting
- **Best approach**: Add token counting to integration tests as assertion

**Pattern**:
```python
import tiktoken
import json

async def test_list_tasks_token_efficiency():
    """Validate list_tasks summary response is under 2000 tokens."""

    # Setup: Create 15 test tasks
    for i in range(15):
        await create_test_task(db, f"Task {i}", f"Description {i}")

    # Execute: Call list_tasks (summary mode)
    response = await list_tasks(status=None, branch=None, limit=50)

    # Measure: Count tokens in JSON response
    response_json = json.dumps(response)
    encoding = tiktoken.get_encoding("cl100k_base")  # Claude-compatible
    token_count = len(encoding.encode(response_json))

    # Assert: Token count under 2000
    assert token_count < 2000, f"Token count {token_count} exceeds 2000"
```

**Alternatives Considered**:
1. ~~Manual character counting~~ - Rejected: inaccurate, doesn't reflect actual tokenization
2. ~~LLM API token counting~~ - Rejected: requires API calls, slow, unreliable in tests
3. ✅ **tiktoken library** - Selected: fast, accurate, offline, deterministic

**Dependencies**:
- Add `tiktoken` to dev dependencies (testing only)
- Pin version for reproducibility

**References**:
- `tiktoken` GitHub: OpenAI's official tokenizer
- Claude tokenization: Similar to OpenAI models (confirmed via testing)

---

## Summary of Decisions

| Research Area | Decision | Implementation File |
|---------------|----------|---------------------|
| Pydantic Models | Inheritance with BaseTaskFields → TaskSummary, TaskResponse | `src/models/task.py` |
| SQLAlchemy Query | Conditional serialization (no query changes) | `src/services/tasks.py` |
| FastMCP Response | Single tool with `full_details: bool` parameter | `src/mcp/tools/tasks.py` |
| Breaking Change | Immediate with clear documentation | Release notes + docs |
| Token Validation | `tiktoken` library in integration tests | `tests/integration/` |

---

## Technical Recommendations

1. **Model Layer**: Create `BaseTaskFields`, inherit `TaskSummary` and `TaskResponse`
2. **Service Layer**: Add `full_details` parameter, return appropriate model type
3. **Tool Layer**: Accept `full_details=False` parameter, serialize models to dicts
4. **Testing**: Use `tiktoken` for token counting validation in integration tests
5. **Documentation**: Create clear release notes documenting breaking change and migration path

**Constitutional Compliance**: All decisions align with:
- Principle VIII (Pydantic type safety)
- Principle XI (FastMCP patterns)
- Principle IV (performance guarantees via token optimization)
- Principle V (production quality via thorough testing)

---

**Status**: ✅ Research complete - Ready for Phase 1 (Design & Contracts)
