# Data Model: list_tasks Token Optimization

**Feature**: Optimize list_tasks MCP Tool for Token Efficiency
**Date**: 2025-10-10
**Branch**: 004-as-an-ai

## Overview

This document defines the Pydantic models for the two-tier task response pattern: lightweight `TaskSummary` for efficient list operations and full `TaskResponse` for detailed task information.

## Model Hierarchy

```
BaseTaskFields (abstract base)
├── TaskSummary (inherits base fields only)
└── TaskResponse (inherits base fields + adds detail fields)
```

## Entity Definitions

### 1. BaseTaskFields (Base Model)

**Purpose**: Shared core fields between summary and full task representations

**Fields**:

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `id` | UUID | Yes | Valid UUID format | Unique task identifier |
| `title` | str | Yes | 1-200 characters, non-empty | Task title |
| `status` | Literal | Yes | One of: "need to be done", "in-progress", "complete" | Current task status |
| `created_at` | datetime | Yes | ISO 8601 format | Task creation timestamp |
| `updated_at` | datetime | Yes | ISO 8601 format | Last modification timestamp |

**Pydantic Configuration**:
```python
class BaseTaskFields(BaseModel):
    """Shared fields between summary and full task responses.

    Constitutional Compliance:
    - Principle VIII: Pydantic-based type safety with explicit types
    """

    id: UUID
    title: str = Field(min_length=1, max_length=200)
    status: Literal["need to be done", "in-progress", "complete"]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,  # Enable ORM mode for SQLAlchemy
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Implement user authentication",
                "status": "in-progress",
                "created_at": "2025-10-10T10:00:00Z",
                "updated_at": "2025-10-10T15:30:00Z"
            }
        }
    )
```

**Validation Rules**:
- `title` must be non-empty and ≤200 characters (enforced by Field constraints)
- `status` must be one of three valid values (enforced by Literal type)
- `created_at` and `updated_at` must be valid datetime objects
- `id` must be valid UUID format

---

### 2. TaskSummary (Lightweight Model)

**Purpose**: Efficient task representation for list operations, optimized for token usage

**Inheritance**: Inherits all fields from `BaseTaskFields`

**Additional Fields**: None (uses base fields only)

**Token Footprint**: ~120-150 tokens per task (estimated)

**Pydantic Configuration**:
```python
class TaskSummary(BaseTaskFields):
    """Lightweight task summary for list operations.

    Token Efficiency:
    - Includes only: id, title, status, created_at, updated_at
    - Excludes: description, notes, planning_references, branches, commits
    - Target: ~120-150 tokens per task
    - 15 tasks ≈ 1800-2250 tokens (with response envelope)

    Constitutional Compliance:
    - Principle IV: Performance (6x token reduction)
    - Principle VIII: Type safety (Pydantic validation)
    """

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Implement user authentication",
                "status": "in-progress",
                "created_at": "2025-10-10T10:00:00Z",
                "updated_at": "2025-10-10T15:30:00Z"
            }
        }
    )
```

**Use Cases**:
- Default response for `list_tasks()` tool
- Task browsing and scanning
- Quick status overview
- Token-efficient operations

---

### 3. TaskResponse (Full Model)

**Purpose**: Complete task representation including all metadata

**Inheritance**: Inherits all fields from `BaseTaskFields`

**Additional Fields**:

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `description` | str \| None | No | No max length | Detailed task description |
| `notes` | str \| None | No | No max length | Additional notes |
| `planning_references` | list[str] | Yes | Array of file paths | Planning document references |
| `branches` | list[str] | Yes | Array of git branch names | Associated git branches |
| `commits` | list[str] | Yes | Array of 40-char hex strings | Associated git commit hashes |

**Token Footprint**: ~800-1000 tokens per task (estimated, with long descriptions)

**Pydantic Configuration**:
```python
class TaskResponse(BaseTaskFields):
    """Full task details including all metadata.

    Token Footprint:
    - Includes all BaseTaskFields PLUS detail fields
    - Description/notes can be lengthy (varies by task)
    - Planning references, branches, commits add arrays
    - Target: ~800-1000 tokens per task (high variance)

    Constitutional Compliance:
    - Principle VIII: Type safety (Pydantic validation)
    - Principle X: Git integration (branches, commits tracking)
    """

    description: str | None = None
    notes: str | None = None
    planning_references: list[str] = Field(default_factory=list)
    branches: list[str] = Field(default_factory=list)
    commits: list[str] = Field(default_factory=list)

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Implement user authentication",
                "description": "Add JWT-based authentication with refresh tokens...",
                "notes": "Consider OAuth2 integration for social login",
                "status": "in-progress",
                "created_at": "2025-10-10T10:00:00Z",
                "updated_at": "2025-10-10T15:30:00Z",
                "planning_references": [
                    "specs/001-auth/spec.md",
                    "specs/001-auth/plan.md"
                ],
                "branches": ["001-user-auth"],
                "commits": ["a1b2c3d4e5f6..."]
            }
        }
    )
```

**Use Cases**:
- `get_task(task_id)` tool response
- `list_tasks(full_details=True)` tool response (opt-in)
- Detailed task examination
- Full context for implementation

---

## Model Relationships

**Subset Relationship**:
```
TaskSummary ⊂ TaskResponse

All TaskSummary fields are present in TaskResponse.
TaskResponse adds additional detail fields.
```

**Serialization Compatibility**:
- Both models serialize to MCP-compliant JSON
- Both models can deserialize from SQLAlchemy `Task` ORM objects (via `model_validate()`)
- TaskSummary can be constructed from TaskResponse by field selection (though not needed in practice)

---

## Validation Strategy

### Pydantic Field Validators

**Title Validation**:
```python
@field_validator('title')
@classmethod
def validate_title(cls, v: str) -> str:
    """Ensure title is non-empty after stripping whitespace."""
    if not v.strip():
        raise ValueError('Title cannot be empty or whitespace-only')
    return v.strip()
```

**Status Validation**: Enforced by `Literal` type (compile-time + runtime)

**Commit Hash Validation** (in TaskResponse):
```python
@field_validator('commits')
@classmethod
def validate_commits(cls, v: list[str]) -> list[str]:
    """Ensure all commit hashes are 40-character hex strings."""
    for commit in v:
        if not (len(commit) == 40 and all(c in '0123456789abcdef' for c in commit.lower())):
            raise ValueError(f'Invalid commit hash format: {commit}')
    return v
```

### Runtime Validation

- All models validate on construction (`model_validate()`)
- Validation errors raise `pydantic.ValidationError` with field-level messages
- Service layer catches validation errors and converts to user-friendly error responses

---

## Performance Characteristics

### Token Efficiency Comparison

| Model | Fields | Tokens/Task (est.) | 15 Tasks Total |
|-------|--------|-------------------|----------------|
| **TaskSummary** | 5 core fields | ~120-150 | ~1800-2250 |
| **TaskResponse** | 5 core + 5 detail | ~800-1000 | ~12000-15000 |

**Token Reduction**: ~6x improvement (12000 → 2000 tokens)

### Serialization Performance

- Pydantic `model_dump()`: <1ms per task
- JSON serialization: <5ms for 15 tasks
- Total serialization overhead: <10ms (negligible vs 200ms latency target)

---

## Database Mapping

### SQLAlchemy ORM Model (Unchanged)

The underlying `Task` SQLAlchemy model remains unchanged. Both TaskSummary and TaskResponse are constructed from the same ORM object:

```python
# SQLAlchemy Task model (src/models/task.py - existing)
class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    # ... (branches, commits via relationships)
```

**Conversion Pattern**:
```python
# From ORM to Pydantic (service layer)
task_orm = await db.execute(select(Task).where(...))
task = task_orm.scalar_one()

# Summary conversion
summary = TaskSummary.model_validate(task)

# Full conversion
response = TaskResponse.model_validate(task)
```

---

## Migration Impact

**Breaking Change**: `list_tasks` response format changes

**Before**:
```json
{
  "tasks": [
    {
      "id": "...",
      "title": "...",
      "description": "...",  // ❌ No longer in default response
      "notes": "...",         // ❌ No longer in default response
      "status": "...",
      "created_at": "...",
      "updated_at": "...",
      "planning_references": [...],  // ❌ No longer in default response
      "branches": [...],             // ❌ No longer in default response
      "commits": [...]               // ❌ No longer in default response
    }
  ],
  "total_count": 15
}
```

**After (default)**:
```json
{
  "tasks": [
    {
      "id": "...",
      "title": "...",
      "status": "...",
      "created_at": "...",
      "updated_at": "..."
      // ✅ Only 5 core fields
    }
  ],
  "total_count": 15
}
```

**Migration Path**: Use `full_details=True` parameter or call `get_task(task_id)` for specific details

---

## Testing Requirements

### Unit Tests

- Test TaskSummary validation (valid and invalid inputs)
- Test TaskResponse validation (valid and invalid inputs)
- Test model serialization to JSON
- Test model construction from SQLAlchemy ORM objects

### Integration Tests

- Test token count for TaskSummary list (<2000 tokens for 15 tasks)
- Test token count for TaskResponse list (baseline comparison)
- Test field presence in serialized responses
- Test backward compatibility with `full_details=True`

---

## Constitutional Compliance

| Principle | Compliance | Evidence |
|-----------|------------|----------|
| **VIII. Pydantic Type Safety** | ✅ PASS | All models use Pydantic with explicit types, validators |
| **IV. Performance Guarantees** | ✅ PASS | TaskSummary achieves 6x token reduction target |
| **V. Production Quality** | ✅ PASS | Comprehensive validation, clear error messages |

---

**Status**: ✅ Data model design complete - Ready for contract generation
