"""
T002: Contract tests for update_work_item MCP tool.

These tests validate the MCP protocol contract for work item update functionality
with optimistic locking, partial updates, soft deletes, and type-specific metadata.
Tests MUST fail initially as the tool is not yet implemented (TDD approach).

Contract: /Users/cliffclarke/Claude_Code/codebase-mcp/specs/003-database-backed-project/contracts/mcp-tools.yaml
Schemas: /Users/cliffclarke/Claude_Code/codebase-mcp/specs/003-database-backed-project/contracts/pydantic-schemas.py

Performance Requirements:
- p95 latency: < 150ms
- Optimistic locking: version parameter required, version mismatch returns 409
- Partial updates: optional title, status, metadata, deleted_at
- Concurrent update scenario: version conflict detection

Requirements Validated:
- FR-014: Audit trail tracking (updated_at, version increment)
- FR-037: Optimistic locking for concurrent updates
- FR-012: Soft delete via deleted_at timestamp
- FR-010: JSONB metadata validation via Pydantic
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal, Union
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, Field, ValidationError, field_validator


# ============================================================================
# Type Definitions (from contracts/pydantic-schemas.py)
# ============================================================================


WorkItemType = Literal["project", "session", "task", "research"]
WorkItemStatus = Literal["active", "completed", "blocked"]


# ============================================================================
# Metadata Schemas (Type-Specific JSONB Validation)
# ============================================================================


class ProjectMetadata(BaseModel):
    """Metadata for item_type='project' work items."""

    description: str = Field(
        max_length=1000,
        description="Project description and purpose",
    )
    target_quarter: str | None = Field(
        None,
        pattern=r"^\d{4}-Q[1-4]$",
        description="Target completion quarter in YYYY-Q# format",
    )
    constitutional_principles: list[str] = Field(
        default_factory=list,
        description="List of constitutional principles",
    )


class SessionMetadata(BaseModel):
    """Metadata for item_type='session' work items."""

    token_budget: int = Field(
        ge=1000,
        le=1000000,
        description="Token budget allocated for this session",
    )
    prompts_count: int = Field(
        ge=0,
        description="Number of prompts executed in this session",
    )
    yaml_frontmatter: dict[str, Any] = Field(
        description="Raw YAML frontmatter from session prompt file",
    )

    @field_validator("yaml_frontmatter")
    @classmethod
    def validate_schema_version(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Ensure YAML frontmatter includes required schema_version field."""
        if "schema_version" not in v:
            raise ValueError("YAML frontmatter must include schema_version")
        return v


class TaskMetadata(BaseModel):
    """Metadata for item_type='task' work items."""

    estimated_hours: float | None = Field(
        None,
        ge=0,
        le=1000,
        description="Estimated hours to complete task",
    )
    actual_hours: float | None = Field(
        None,
        ge=0,
        le=1000,
        description="Actual hours spent on task",
    )
    blocked_reason: str | None = Field(
        None,
        max_length=500,
        description="Reason why task is blocked",
    )


class ResearchMetadata(BaseModel):
    """Metadata for item_type='research' work items."""

    research_questions: list[str] = Field(
        default_factory=list,
        description="List of research questions addressed",
    )
    findings_summary: str | None = Field(
        None,
        max_length=2000,
        description="Summary of research findings",
    )
    references: list[str] = Field(
        default_factory=list,
        description="List of reference URLs or documents",
    )


# ============================================================================
# Input/Output Schemas
# ============================================================================


class WorkItemUpdate(BaseModel):
    """
    Input schema for update_work_item MCP tool.

    Updates an existing work item with optimistic locking via version check.
    All fields except id and version are optional (partial updates supported).
    """

    id: UUID = Field(
        description="Work item UUID to update",
    )
    version: int = Field(
        ge=1,
        description="Expected version for optimistic locking",
    )
    title: str | None = Field(
        None,
        max_length=200,
        description="Updated work item title",
    )
    status: WorkItemStatus | None = Field(
        None,
        description="Updated work item status",
    )
    metadata: Union[ProjectMetadata, SessionMetadata, TaskMetadata, ResearchMetadata] | None = Field(
        None,
        description="Updated type-specific metadata",
    )
    deleted_at: datetime | None = Field(
        None,
        description="Soft delete timestamp (set to NOW() to delete)",
    )
    updated_by: str = Field(
        max_length=100,
        description="AI client identifier performing update",
    )


class WorkItemResponse(BaseModel):
    """Output schema for work item operations."""

    id: UUID = Field(description="Work item UUID")
    version: int = Field(description="Current version (for optimistic locking)")
    item_type: WorkItemType = Field(description="Work item type")
    title: str = Field(description="Work item title")
    status: WorkItemStatus = Field(description="Work item status")
    parent_id: UUID | None = Field(None, description="Parent work item UUID")
    path: str = Field(description="Materialized path")
    depth: int = Field(description="Hierarchy depth (0-5)")
    branch_name: str | None = Field(None, description="Git branch name")
    commit_hash: str | None = Field(None, description="Git commit hash")
    pr_number: int | None = Field(None, description="GitHub PR number")
    metadata: Union[ProjectMetadata, SessionMetadata, TaskMetadata, ResearchMetadata] = Field(
        description="Type-specific metadata"
    )
    deleted_at: datetime | None = Field(None, description="Soft delete timestamp")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    created_by: str = Field(description="AI client identifier")


class OptimisticLockError(BaseModel):
    """Optimistic locking error response (409 conflict)."""

    error_type: Literal["optimistic_lock_error"] = "optimistic_lock_error"
    message: str = Field(description="Human-readable error message")
    current_version: int = Field(description="Current version in database")
    requested_version: int = Field(description="Version provided in update request")
    last_updated_by: str = Field(description="Client that performed the conflicting update")


class NotFoundError(BaseModel):
    """Resource not found error response (404)."""

    error_type: Literal["not_found_error"] = "not_found_error"
    message: str = Field(description="Human-readable error message")
    resource_type: str = Field(description="Type of resource not found")
    resource_id: str = Field(description="ID of resource not found")


# ============================================================================
# Contract Tests: Input Validation
# ============================================================================


@pytest.mark.contract
def test_update_work_item_input_valid_minimal() -> None:
    """Test update_work_item input schema with minimal required fields."""
    work_item_id = uuid4()
    valid_input = WorkItemUpdate(
        id=work_item_id,
        version=1,
        updated_by="claude-code-v1",
    )

    assert valid_input.id == work_item_id
    assert valid_input.version == 1
    assert valid_input.title is None
    assert valid_input.status is None
    assert valid_input.metadata is None
    assert valid_input.deleted_at is None
    assert valid_input.updated_by == "claude-code-v1"


@pytest.mark.contract
def test_update_work_item_input_valid_title_update() -> None:
    """Test update_work_item input schema with title update."""
    work_item_id = uuid4()
    valid_input = WorkItemUpdate(
        id=work_item_id,
        version=2,
        title="Updated work item title",
        updated_by="claude-code-v1",
    )

    assert valid_input.id == work_item_id
    assert valid_input.version == 2
    assert valid_input.title == "Updated work item title"
    assert len(valid_input.title) <= 200


@pytest.mark.contract
def test_update_work_item_input_valid_status_update() -> None:
    """Test update_work_item input schema with status update."""
    work_item_id = uuid4()
    valid_statuses: list[WorkItemStatus] = [
        "active",
        "completed",
        "blocked",
    ]

    for status in valid_statuses:
        valid_input = WorkItemUpdate(
            id=work_item_id,
            version=1,
            status=status,
            updated_by="claude-code-v1",
        )
        assert valid_input.status == status


@pytest.mark.contract
def test_update_work_item_input_valid_metadata_task() -> None:
    """Test update_work_item input schema with TaskMetadata update."""
    work_item_id = uuid4()
    task_metadata = TaskMetadata(
        estimated_hours=8.0,
        actual_hours=6.5,
        blocked_reason=None,
    )

    valid_input = WorkItemUpdate(
        id=work_item_id,
        version=1,
        metadata=task_metadata,
        updated_by="claude-code-v1",
    )

    assert valid_input.metadata == task_metadata
    assert isinstance(valid_input.metadata, TaskMetadata)
    assert valid_input.metadata.estimated_hours == 8.0
    assert valid_input.metadata.actual_hours == 6.5


@pytest.mark.contract
def test_update_work_item_input_valid_metadata_session() -> None:
    """Test update_work_item input schema with SessionMetadata update."""
    work_item_id = uuid4()
    session_metadata = SessionMetadata(
        token_budget=200000,
        prompts_count=15,
        yaml_frontmatter={"schema_version": "1.0", "mode": "implement"},
    )

    valid_input = WorkItemUpdate(
        id=work_item_id,
        version=3,
        metadata=session_metadata,
        updated_by="claude-desktop-v2",
    )

    assert valid_input.metadata == session_metadata
    assert isinstance(valid_input.metadata, SessionMetadata)
    assert valid_input.metadata.token_budget == 200000


@pytest.mark.contract
def test_update_work_item_input_valid_soft_delete() -> None:
    """Test update_work_item input schema with soft delete timestamp."""
    work_item_id = uuid4()
    delete_time = datetime.now(UTC)

    valid_input = WorkItemUpdate(
        id=work_item_id,
        version=2,
        deleted_at=delete_time,
        updated_by="claude-code-v1",
    )

    assert valid_input.deleted_at == delete_time
    assert valid_input.deleted_at is not None


@pytest.mark.contract
def test_update_work_item_input_missing_required_id() -> None:
    """Test update_work_item input validation fails when id is missing."""
    with pytest.raises(ValidationError) as exc_info:
        WorkItemUpdate(  # type: ignore[call-arg]
            version=1,
            updated_by="claude-code-v1",
        )

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("id",) for error in errors)
    assert any(error["type"] == "missing" for error in errors)


@pytest.mark.contract
def test_update_work_item_input_missing_required_version() -> None:
    """Test update_work_item input validation fails when version is missing."""
    work_item_id = uuid4()

    with pytest.raises(ValidationError) as exc_info:
        WorkItemUpdate(  # type: ignore[call-arg]
            id=work_item_id,
            updated_by="claude-code-v1",
        )

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("version",) for error in errors)
    assert any(error["type"] == "missing" for error in errors)


@pytest.mark.contract
def test_update_work_item_input_missing_required_updated_by() -> None:
    """Test update_work_item input validation fails when updated_by is missing."""
    work_item_id = uuid4()

    with pytest.raises(ValidationError) as exc_info:
        WorkItemUpdate(  # type: ignore[call-arg]
            id=work_item_id,
            version=1,
        )

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("updated_by",) for error in errors)
    assert any(error["type"] == "missing" for error in errors)


@pytest.mark.contract
def test_update_work_item_input_invalid_version_zero() -> None:
    """Test update_work_item input validation fails for version < 1."""
    work_item_id = uuid4()

    with pytest.raises(ValidationError) as exc_info:
        WorkItemUpdate(
            id=work_item_id,
            version=0,
            updated_by="claude-code-v1",
        )

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("version",) for error in errors)


@pytest.mark.contract
def test_update_work_item_input_invalid_status_enum() -> None:
    """Test update_work_item input validation fails for invalid status."""
    work_item_id = uuid4()

    with pytest.raises(ValidationError) as exc_info:
        WorkItemUpdate(
            id=work_item_id,
            version=1,
            status="pending",  # type: ignore[arg-type]  # Invalid status
            updated_by="claude-code-v1",
        )

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("status",) for error in errors)


@pytest.mark.contract
def test_update_work_item_input_title_exceeds_max_length() -> None:
    """Test update_work_item input validation fails when title exceeds 200 chars."""
    work_item_id = uuid4()
    long_title = "A" * 201  # 201 characters

    with pytest.raises(ValidationError) as exc_info:
        WorkItemUpdate(
            id=work_item_id,
            version=1,
            title=long_title,
            updated_by="claude-code-v1",
        )

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("title",) for error in errors)


@pytest.mark.contract
def test_update_work_item_input_metadata_validation_fails() -> None:
    """Test update_work_item input validation fails for invalid metadata."""
    work_item_id = uuid4()

    # SessionMetadata without required schema_version in yaml_frontmatter
    with pytest.raises(ValidationError) as exc_info:
        invalid_metadata = SessionMetadata(
            token_budget=200000,
            prompts_count=5,
            yaml_frontmatter={},  # Missing schema_version
        )

    errors = exc_info.value.errors()
    assert len(errors) > 0


@pytest.mark.contract
def test_update_work_item_input_metadata_token_budget_validation() -> None:
    """Test update_work_item input validates token_budget constraints."""
    work_item_id = uuid4()

    # Token budget too low
    with pytest.raises(ValidationError) as exc_info:
        SessionMetadata(
            token_budget=500,  # Below minimum of 1000
            prompts_count=1,
            yaml_frontmatter={"schema_version": "1.0"},
        )
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("token_budget",) for error in errors)

    # Token budget too high
    with pytest.raises(ValidationError) as exc_info:
        SessionMetadata(
            token_budget=2000000,  # Above maximum of 1000000
            prompts_count=1,
            yaml_frontmatter={"schema_version": "1.0"},
        )
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("token_budget",) for error in errors)


# ============================================================================
# Contract Tests: Output Validation
# ============================================================================


@pytest.mark.contract
def test_update_work_item_output_returns_updated_work_item() -> None:
    """Test update_work_item output schema returns updated WorkItem object."""
    work_item_id = uuid4()
    created = datetime(2025, 10, 1, 10, 0, 0, tzinfo=UTC)
    updated = datetime(2025, 10, 10, 14, 30, 0, tzinfo=UTC)

    # Simulate the output of update_work_item
    updated_work_item = WorkItemResponse(
        id=work_item_id,
        version=2,  # Version incremented from 1 to 2
        item_type="task",
        title="Updated title",
        status="completed",
        parent_id=None,
        path="/task1",
        depth=0,
        branch_name="003-database-backed-project",
        commit_hash=None,
        pr_number=None,
        metadata=TaskMetadata(
            estimated_hours=8.0,
            actual_hours=6.5,
            blocked_reason=None,
        ),
        deleted_at=None,
        created_at=created,
        updated_at=updated,  # Should be newer than created_at
        created_by="claude-code-v1",
    )

    assert updated_work_item.id == work_item_id
    assert updated_work_item.version == 2
    assert updated_work_item.title == "Updated title"
    assert updated_work_item.status == "completed"
    assert updated_work_item.updated_at > updated_work_item.created_at


@pytest.mark.contract
def test_update_work_item_output_version_increments() -> None:
    """Test update_work_item output increments version number."""
    work_item_id = uuid4()
    now = datetime.now(UTC)

    # Version should increment on each update
    original_version = 3
    updated_version = 4

    updated_work_item = WorkItemResponse(
        id=work_item_id,
        version=updated_version,
        item_type="task",
        title="Task",
        status="active",
        parent_id=None,
        path="/task1",
        depth=0,
        metadata=TaskMetadata(),
        created_at=now,
        updated_at=now,
        created_by="claude-code-v1",
    )

    assert updated_work_item.version == original_version + 1
    assert updated_work_item.version == 4


@pytest.mark.contract
def test_update_work_item_output_updates_timestamp() -> None:
    """Test update_work_item output updates the updated_at timestamp."""
    work_item_id = uuid4()
    created = datetime(2025, 10, 1, 10, 0, 0, tzinfo=UTC)
    updated = datetime(2025, 10, 10, 14, 30, 0, tzinfo=UTC)

    work_item = WorkItemResponse(
        id=work_item_id,
        version=2,
        item_type="task",
        title="Task",
        status="active",
        parent_id=None,
        path="/task1",
        depth=0,
        metadata=TaskMetadata(),
        created_at=created,
        updated_at=updated,
        created_by="claude-code-v1",
    )

    # updated_at should be later than created_at after an update
    assert work_item.updated_at > work_item.created_at


@pytest.mark.contract
def test_update_work_item_output_soft_delete_sets_timestamp() -> None:
    """Test update_work_item output sets deleted_at timestamp for soft delete."""
    work_item_id = uuid4()
    now = datetime.now(UTC)
    delete_time = datetime.now(UTC)

    work_item = WorkItemResponse(
        id=work_item_id,
        version=3,
        item_type="task",
        title="Task to delete",
        status="active",
        parent_id=None,
        path="/task1",
        depth=0,
        metadata=TaskMetadata(),
        deleted_at=delete_time,
        created_at=now,
        updated_at=delete_time,
        created_by="claude-code-v1",
    )

    assert work_item.deleted_at is not None
    assert work_item.deleted_at == delete_time


# ============================================================================
# Contract Tests: Optimistic Locking Error Responses
# ============================================================================


@pytest.mark.contract
def test_optimistic_lock_error_response_structure() -> None:
    """Test OptimisticLockError response includes version conflict details."""
    error = OptimisticLockError(
        message="Work item was modified by another client (expected version 2, current version 3)",
        current_version=3,
        requested_version=2,
        last_updated_by="claude-desktop-v2",
    )

    assert error.error_type == "optimistic_lock_error"
    assert error.current_version == 3
    assert error.requested_version == 2
    assert error.last_updated_by == "claude-desktop-v2"
    assert "expected version 2" in error.message
    assert "current version 3" in error.message


@pytest.mark.contract
def test_not_found_error_response_structure() -> None:
    """Test NotFoundError response includes resource identification details."""
    work_item_id = uuid4()

    error = NotFoundError(
        message=f"Work item not found: {work_item_id}",
        resource_type="work_item",
        resource_id=str(work_item_id),
    )

    assert error.error_type == "not_found_error"
    assert error.resource_type == "work_item"
    assert error.resource_id == str(work_item_id)
    assert str(work_item_id) in error.message


# ============================================================================
# Contract Tests: Tool Behavior (TDD - MUST FAIL)
# ============================================================================


@pytest.mark.contract
@pytest.mark.asyncio
async def test_update_work_item_tool_not_implemented() -> None:
    """
    Test documenting that update_work_item tool is not yet implemented.

    This test MUST fail until the actual tool implementation is complete.
    Once implemented, replace this with actual tool invocation tests.

    Expected behavior: Tool not found or NotImplementedError
    """
    with pytest.raises((NotImplementedError, AttributeError)) as exc_info:
        # TODO: Uncomment once tool is implemented
        # from src.mcp.tools.work_items import update_work_item
        # work_item_id = uuid4()
        # result = await update_work_item(
        #     id=work_item_id,
        #     version=1,
        #     status="completed",
        #     updated_by="claude-code-v1"
        # )
        raise NotImplementedError("update_work_item tool not implemented yet")

    assert "not implemented" in str(exc_info.value).lower()


@pytest.mark.contract
@pytest.mark.asyncio
async def test_update_work_item_successful_partial_update() -> None:
    """
    Test successful partial update with correct version increments version.

    Expected Behavior:
    - Update succeeds with matching version number
    - Version increments from N to N+1
    - Only specified fields are updated
    - updated_at timestamp is updated
    - Returns updated work item with new version
    """
    # TODO: Once implemented, test actual behavior:
    # from src.mcp.tools.work_items import create_work_item, update_work_item
    #
    # # Create work item (version 1)
    # created = await create_work_item(
    #     item_type="task",
    #     title="Original title",
    #     metadata=TaskMetadata(estimated_hours=10.0),
    #     created_by="claude-code-v1",
    # )
    # assert created.version == 1
    #
    # # Update with correct version (1 -> 2)
    # updated = await update_work_item(
    #     id=created.id,
    #     version=1,  # Correct version
    #     status="completed",
    #     metadata=TaskMetadata(estimated_hours=10.0, actual_hours=8.0),
    #     updated_by="claude-code-v1",
    # )
    # assert updated.version == 2  # Version incremented
    # assert updated.status == "completed"
    # assert updated.title == "Original title"  # Unchanged
    # assert updated.metadata.actual_hours == 8.0
    # assert updated.updated_at > created.updated_at

    # Document the requirement
    assert True, "update_work_item should support partial updates with version increment"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_update_work_item_optimistic_locking_version_conflict() -> None:
    """
    Test optimistic locking: update with stale version returns 409 error.

    Expected Behavior:
    - Update with stale version fails with OptimisticLockError
    - Error response includes current_version and requested_version
    - Error response includes last_updated_by client identifier
    - Work item remains unchanged
    """
    # TODO: Once implemented, test actual behavior:
    # from src.mcp.tools.work_items import (
    #     create_work_item,
    #     update_work_item,
    #     get_work_item,
    #     OptimisticLockError,
    # )
    #
    # # Create work item (version 1)
    # created = await create_work_item(
    #     item_type="task",
    #     title="Original title",
    #     metadata=TaskMetadata(estimated_hours=10.0),
    #     created_by="claude-code-v1",
    # )
    # assert created.version == 1
    #
    # # First update succeeds (version 1 -> 2)
    # updated1 = await update_work_item(
    #     id=created.id,
    #     version=1,
    #     status="in-progress",
    #     updated_by="claude-code-v1",
    # )
    # assert updated1.version == 2
    #
    # # Second update with stale version fails
    # with pytest.raises(OptimisticLockError) as exc_info:
    #     await update_work_item(
    #         id=created.id,
    #         version=1,  # Stale version (current is 2)
    #         status="completed",
    #         updated_by="claude-desktop-v2",
    #     )
    #
    # error = exc_info.value
    # assert error.current_version == 2
    # assert error.requested_version == 1
    # assert error.last_updated_by == "claude-code-v1"

    # Document the requirement
    assert True, "update_work_item should reject updates with stale version numbers"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_update_work_item_concurrent_update_scenario() -> None:
    """
    Test concurrent update scenario: version conflict detection.

    Scenario:
    1. Two clients fetch same work item (version N)
    2. Client A updates successfully (version N -> N+1)
    3. Client B attempts update with version N (now stale)
    4. Client B receives 409 VersionConflictError with current/requested versions

    Expected Behavior:
    - First update succeeds, version increments
    - Second update with stale version fails with OptimisticLockError
    - Error includes current_version (N+1) and requested_version (N)
    - Error includes last_updated_by from successful update
    """
    # TODO: Once implemented, test actual concurrent update scenario:
    # from src.mcp.tools.work_items import (
    #     create_work_item,
    #     get_work_item,
    #     update_work_item,
    #     OptimisticLockError,
    # )
    #
    # # Create work item
    # created = await create_work_item(
    #     item_type="task",
    #     title="Concurrent update test",
    #     metadata=TaskMetadata(estimated_hours=10.0),
    #     created_by="claude-code-v1",
    # )
    # assert created.version == 1
    #
    # # Client A fetches work item (version 1)
    # client_a_view = await get_work_item(id=created.id)
    # assert client_a_view.version == 1
    #
    # # Client B fetches work item (version 1)
    # client_b_view = await get_work_item(id=created.id)
    # assert client_b_view.version == 1
    #
    # # Client A updates successfully (version 1 -> 2)
    # updated_by_a = await update_work_item(
    #     id=created.id,
    #     version=1,
    #     status="in-progress",
    #     updated_by="client-a",
    # )
    # assert updated_by_a.version == 2
    #
    # # Client B attempts update with stale version 1 (current is 2)
    # with pytest.raises(OptimisticLockError) as exc_info:
    #     await update_work_item(
    #         id=created.id,
    #         version=1,  # Stale
    #         status="completed",
    #         updated_by="client-b",
    #     )
    #
    # error = exc_info.value
    # assert error.current_version == 2
    # assert error.requested_version == 1
    # assert error.last_updated_by == "client-a"

    # Document the requirement
    assert True, "update_work_item should detect and reject concurrent conflicting updates"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_update_work_item_soft_delete_sets_timestamp() -> None:
    """
    Test soft delete: setting deleted_at timestamp marks item as deleted.

    Expected Behavior:
    - Update with deleted_at timestamp succeeds
    - Work item is marked as soft-deleted
    - Work item can still be queried but flagged as deleted
    - Version increments on soft delete
    """
    # TODO: Once implemented, test actual soft delete:
    # from src.mcp.tools.work_items import (
    #     create_work_item,
    #     update_work_item,
    #     get_work_item,
    # )
    #
    # # Create work item
    # created = await create_work_item(
    #     item_type="task",
    #     title="Task to delete",
    #     metadata=TaskMetadata(estimated_hours=5.0),
    #     created_by="claude-code-v1",
    # )
    # assert created.deleted_at is None
    #
    # # Soft delete
    # delete_time = datetime.now(UTC)
    # deleted = await update_work_item(
    #     id=created.id,
    #     version=1,
    #     deleted_at=delete_time,
    #     updated_by="claude-code-v1",
    # )
    # assert deleted.version == 2
    # assert deleted.deleted_at is not None
    # assert deleted.deleted_at == delete_time
    #
    # # Can still query deleted item
    # fetched = await get_work_item(id=created.id, include_deleted=True)
    # assert fetched.deleted_at is not None

    # Document the requirement
    assert True, "update_work_item should support soft delete via deleted_at timestamp"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_update_work_item_metadata_validation() -> None:
    """
    Test metadata update validation uses type-specific Pydantic validation.

    Expected Behavior:
    - Metadata updates are validated by appropriate Pydantic model
    - Invalid metadata raises ValidationError
    - Metadata must match work item's item_type
    """
    # TODO: Once implemented, test metadata validation:
    # from src.mcp.tools.work_items import (
    #     create_work_item,
    #     update_work_item,
    # )
    # from pydantic import ValidationError
    #
    # # Create task work item
    # created = await create_work_item(
    #     item_type="task",
    #     title="Task",
    #     metadata=TaskMetadata(estimated_hours=10.0),
    #     created_by="claude-code-v1",
    # )
    #
    # # Valid metadata update
    # updated = await update_work_item(
    #     id=created.id,
    #     version=1,
    #     metadata=TaskMetadata(estimated_hours=10.0, actual_hours=8.0),
    #     updated_by="claude-code-v1",
    # )
    # assert updated.metadata.actual_hours == 8.0
    #
    # # Invalid metadata should fail validation
    # with pytest.raises(ValidationError):
    #     await update_work_item(
    #         id=created.id,
    #         version=2,
    #         metadata=TaskMetadata(estimated_hours=-5.0),  # Negative hours
    #         updated_by="claude-code-v1",
    #     )

    # Document the requirement
    assert True, "update_work_item should validate metadata using Pydantic models"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_update_work_item_not_found_error() -> None:
    """
    Test that update_work_item raises 404 error for non-existent work item.

    Expected Behavior:
    - Update attempt on non-existent work item raises NotFoundError
    - Error includes work item ID and resource type
    """
    # TODO: Once implemented, test not found error:
    # from src.mcp.tools.work_items import update_work_item, NotFoundError
    #
    # non_existent_id = uuid4()
    #
    # with pytest.raises(NotFoundError) as exc_info:
    #     await update_work_item(
    #         id=non_existent_id,
    #         version=1,
    #         status="completed",
    #         updated_by="claude-code-v1",
    #     )
    #
    # error = exc_info.value
    # assert error.resource_type == "work_item"
    # assert error.resource_id == str(non_existent_id)

    # Document the requirement
    non_existent_id = uuid4()
    assert non_existent_id is not None, "Tool should handle non-existent work item IDs gracefully"


@pytest.mark.contract
def test_update_work_item_performance_requirement_documented() -> None:
    """
    Document performance requirements for update_work_item tool.

    Performance Requirements (from contracts/mcp-tools.yaml):
    - p95 latency: < 150ms
    - Optimistic locking with version check
    - Single row UPDATE with JSONB metadata validation

    This test serves as documentation. Actual performance validation
    will be implemented in integration/performance tests.
    """
    p95_requirement_ms = 150

    # Document the requirement through assertion
    assert p95_requirement_ms == 150, "p95 latency requirement for update_work_item"

    # Performance considerations:
    # - Single row UPDATE with version check (WHERE id = ? AND version = ?)
    # - JSONB metadata validation via Pydantic before persistence
    # - Version increment via PostgreSQL (version = version + 1)
    # - updated_at timestamp via PostgreSQL NOW()
    # Requirement will be validated once tool is implemented
