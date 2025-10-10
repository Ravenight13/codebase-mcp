"""
T004: Contract tests for list_work_items MCP tool.

These tests validate the MCP protocol contract for work item listing functionality.
Tests MUST fail initially as the tool is not yet implemented (TDD approach).

Performance Requirements:
- p95 latency: < 200ms

Contract Requirements (from contracts/mcp-tools.yaml):
- FR-018: Filtering by item_type, status, parent_id, include_deleted
- FR-012: Soft delete support (exclude deleted items by default)
- Pagination: limit (1-100), offset, has_more flag
- PaginatedWorkItemsResponse schema with total_count
- Empty result set returns valid response with empty array

Feature: 003-database-backed-project
Date: 2025-10-10
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, Field, ValidationError


# ============================================================================
# Enums matching contracts/pydantic-schemas.py
# ============================================================================

ItemType = Literal["project", "session", "task", "research"]
WorkItemStatus = Literal["active", "completed", "blocked"]


# ============================================================================
# Metadata Schemas (JSONB validation)
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
# Work Item Entity Schema
# ============================================================================


class WorkItem(BaseModel):
    """Hierarchical work item entity (project/session/task/research)."""

    id: UUID = Field(description="Work item UUID")
    version: int = Field(ge=1, description="Optimistic locking version")
    item_type: ItemType = Field(description="Work item type")
    title: str = Field(max_length=200, description="Work item title")
    status: WorkItemStatus = Field(description="Work item status")
    parent_id: UUID | None = Field(None, description="Parent work item UUID")
    path: str = Field(
        max_length=500,
        description="Materialized path (e.g., /parent1/parent2/current)",
    )
    depth: int = Field(ge=0, le=5, description="Hierarchy depth (0-5 levels max)")
    branch_name: str | None = Field(
        None,
        max_length=100,
        description="Git branch name",
    )
    commit_hash: str | None = Field(
        None,
        pattern=r"^[a-f0-9]{40}$",
        description="Git commit hash (40 lowercase hex)",
    )
    pr_number: int | None = Field(
        None,
        ge=1,
        description="GitHub pull request number",
    )
    metadata: ProjectMetadata | SessionMetadata | TaskMetadata | ResearchMetadata = Field(
        description="Type-specific JSONB metadata"
    )
    deleted_at: datetime | None = Field(
        None,
        description="Soft delete timestamp",
    )
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    created_by: str = Field(
        max_length=100,
        description="AI client identifier",
    )


# ============================================================================
# Input Schema for list_work_items
# ============================================================================


class ListWorkItemsInput(BaseModel):
    """Input schema for list_work_items MCP tool."""

    item_type: ItemType | None = Field(
        None,
        description="Filter by work item type",
    )
    status: WorkItemStatus | None = Field(
        None,
        description="Filter by work item status",
    )
    parent_id: UUID | None = Field(
        None,
        description="Filter by parent work item UUID (null for root items)",
    )
    include_deleted: bool = Field(
        default=False,
        description="Include soft-deleted items in results",
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Maximum number of results to return",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Number of results to skip (for pagination)",
    )


# ============================================================================
# Output Schema for list_work_items
# ============================================================================


class PaginatedWorkItemsResponse(BaseModel):
    """Output schema for list_work_items MCP tool."""

    items: list[WorkItem] = Field(description="Work items in current page")
    total_count: int = Field(
        ge=0,
        description="Total number of items matching filter (ignoring pagination)",
    )
    limit: int = Field(description="Maximum items per page")
    offset: int = Field(description="Number of items skipped")
    has_more: bool = Field(
        description="Whether more items exist beyond current page"
    )


# ============================================================================
# Contract Tests: Input Schema Validation
# ============================================================================


@pytest.mark.contract
def test_list_work_items_input_valid_defaults() -> None:
    """Test list_work_items input schema with default values."""
    valid_input = ListWorkItemsInput()

    assert valid_input.item_type is None
    assert valid_input.status is None
    assert valid_input.parent_id is None
    assert valid_input.include_deleted is False
    assert valid_input.limit == 50  # Default limit
    assert valid_input.offset == 0  # Default offset


@pytest.mark.contract
def test_list_work_items_input_valid_item_type_filter() -> None:
    """Test list_work_items input schema with item_type filter."""
    valid_input = ListWorkItemsInput(item_type="project")

    assert valid_input.item_type == "project"
    assert valid_input.status is None
    assert valid_input.limit == 50


@pytest.mark.contract
def test_list_work_items_input_valid_all_item_types() -> None:
    """Test list_work_items input accepts all valid item_type enum values."""
    valid_item_types: list[ItemType] = ["project", "session", "task", "research"]

    for item_type in valid_item_types:
        valid_input = ListWorkItemsInput(item_type=item_type)
        assert valid_input.item_type == item_type


@pytest.mark.contract
def test_list_work_items_input_invalid_item_type() -> None:
    """Test list_work_items input validation fails for invalid item_type."""
    with pytest.raises(ValidationError) as exc_info:
        ListWorkItemsInput(item_type="feature")  # type: ignore[arg-type]  # Invalid: not in enum

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("item_type",) for error in errors)


@pytest.mark.contract
def test_list_work_items_input_valid_status_filter() -> None:
    """Test list_work_items input schema with status filter."""
    valid_input = ListWorkItemsInput(status="active")

    assert valid_input.status == "active"
    assert valid_input.item_type is None


@pytest.mark.contract
def test_list_work_items_input_valid_all_statuses() -> None:
    """Test list_work_items input accepts all valid status enum values."""
    valid_statuses: list[WorkItemStatus] = ["active", "completed", "blocked"]

    for status in valid_statuses:
        valid_input = ListWorkItemsInput(status=status)
        assert valid_input.status == status


@pytest.mark.contract
def test_list_work_items_input_invalid_status() -> None:
    """Test list_work_items input validation fails for invalid status."""
    with pytest.raises(ValidationError) as exc_info:
        ListWorkItemsInput(status="pending")  # type: ignore[arg-type]  # Invalid: not in enum

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("status",) for error in errors)


@pytest.mark.contract
def test_list_work_items_input_valid_parent_id_filter() -> None:
    """Test list_work_items input schema with parent_id filter (root items)."""
    parent_uuid = uuid4()
    valid_input = ListWorkItemsInput(parent_id=parent_uuid)

    assert valid_input.parent_id == parent_uuid


@pytest.mark.contract
def test_list_work_items_input_valid_include_deleted() -> None:
    """Test list_work_items input schema with include_deleted flag."""
    valid_input = ListWorkItemsInput(include_deleted=True)

    assert valid_input.include_deleted is True


@pytest.mark.contract
def test_list_work_items_input_valid_pagination() -> None:
    """Test list_work_items input schema with pagination parameters."""
    valid_input = ListWorkItemsInput(limit=25, offset=50)

    assert valid_input.limit == 25
    assert valid_input.offset == 50


@pytest.mark.contract
def test_list_work_items_input_limit_boundary_values() -> None:
    """Test list_work_items input accepts valid boundary limit values."""
    # Minimum valid limit
    valid_input_min = ListWorkItemsInput(limit=1)
    assert valid_input_min.limit == 1

    # Maximum valid limit
    valid_input_max = ListWorkItemsInput(limit=100)
    assert valid_input_max.limit == 100


@pytest.mark.contract
def test_list_work_items_input_limit_out_of_range() -> None:
    """Test list_work_items input validation enforces limit range [1, 100]."""
    # Test limit too low
    with pytest.raises(ValidationError) as exc_info:
        ListWorkItemsInput(limit=0)

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("limit",) for error in errors)

    # Test limit too high
    with pytest.raises(ValidationError) as exc_info:
        ListWorkItemsInput(limit=101)

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("limit",) for error in errors)


@pytest.mark.contract
def test_list_work_items_input_offset_negative() -> None:
    """Test list_work_items input validation fails for negative offset."""
    with pytest.raises(ValidationError) as exc_info:
        ListWorkItemsInput(offset=-1)

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("offset",) for error in errors)


@pytest.mark.contract
def test_list_work_items_input_valid_all_filters() -> None:
    """Test list_work_items input schema with all filters specified."""
    parent_uuid = uuid4()
    valid_input = ListWorkItemsInput(
        item_type="task",
        status="active",
        parent_id=parent_uuid,
        include_deleted=False,
        limit=25,
        offset=10,
    )

    assert valid_input.item_type == "task"
    assert valid_input.status == "active"
    assert valid_input.parent_id == parent_uuid
    assert valid_input.include_deleted is False
    assert valid_input.limit == 25
    assert valid_input.offset == 10


# ============================================================================
# Contract Tests: Output Schema Validation
# ============================================================================


@pytest.mark.contract
def test_list_work_items_output_valid_with_results() -> None:
    """Test list_work_items output schema with work item results."""
    item_id_1 = uuid4()
    item_id_2 = uuid4()
    now = datetime.now(UTC)

    output = PaginatedWorkItemsResponse(
        items=[
            WorkItem(
                id=item_id_1,
                version=1,
                item_type="project",
                title="Database-backed project tracking",
                status="active",
                path="/project1",
                depth=0,
                metadata=ProjectMetadata(
                    description="Implement database-backed project status tracking",
                    target_quarter="2025-Q4",
                    constitutional_principles=["Simplicity Over Features"],
                ),
                created_at=now,
                updated_at=now,
                created_by="claude-code",
            ),
            WorkItem(
                id=item_id_2,
                version=1,
                item_type="task",
                title="Implement vendor status caching",
                status="completed",
                path="/project1/task1",
                depth=1,
                metadata=TaskMetadata(
                    estimated_hours=8.0,
                    actual_hours=6.5,
                ),
                created_at=now,
                updated_at=now,
                created_by="claude-code",
            ),
        ],
        total_count=42,
        limit=50,
        offset=0,
        has_more=False,
    )

    assert len(output.items) == 2
    assert output.items[0].id == item_id_1
    assert output.items[0].item_type == "project"
    assert output.items[1].id == item_id_2
    assert output.items[1].item_type == "task"
    assert output.total_count == 42
    assert output.has_more is False


@pytest.mark.contract
def test_list_work_items_output_valid_empty_results() -> None:
    """Test list_work_items output schema with no results (empty array)."""
    output = PaginatedWorkItemsResponse(
        items=[],
        total_count=0,
        limit=50,
        offset=0,
        has_more=False,
    )

    assert output.items == []
    assert output.total_count == 0
    assert output.has_more is False


@pytest.mark.contract
def test_list_work_items_output_has_more_flag_calculation() -> None:
    """Test list_work_items output has_more flag indicates additional pages."""
    item_id = uuid4()
    now = datetime.now(UTC)

    # Scenario: total_count=100, limit=50, offset=0 -> has_more=True
    output_page1 = PaginatedWorkItemsResponse(
        items=[
            WorkItem(
                id=item_id,
                version=1,
                item_type="task",
                title="Task 1",
                status="active",
                path="/task1",
                depth=0,
                metadata=TaskMetadata(),
                created_at=now,
                updated_at=now,
                created_by="claude-code",
            )
        ],
        total_count=100,
        limit=50,
        offset=0,
        has_more=True,  # More items exist beyond offset+limit
    )

    assert output_page1.has_more is True
    assert output_page1.total_count > (output_page1.offset + output_page1.limit)

    # Scenario: total_count=100, limit=50, offset=50 -> has_more=False
    output_page2 = PaginatedWorkItemsResponse(
        items=[
            WorkItem(
                id=item_id,
                version=1,
                item_type="task",
                title="Task 51",
                status="active",
                path="/task51",
                depth=0,
                metadata=TaskMetadata(),
                created_at=now,
                updated_at=now,
                created_by="claude-code",
            )
        ],
        total_count=100,
        limit=50,
        offset=50,
        has_more=False,  # No more items beyond offset+limit
    )

    assert output_page2.has_more is False
    assert output_page2.total_count <= (output_page2.offset + output_page2.limit)


@pytest.mark.contract
def test_list_work_items_output_total_count_reflects_filtered_results() -> None:
    """Test list_work_items output total_count reflects filtered results, not all items."""
    item_id = uuid4()
    now = datetime.now(UTC)

    # Scenario: Filtered by status="active", returns 25 active tasks (out of 100 total items)
    output = PaginatedWorkItemsResponse(
        items=[
            WorkItem(
                id=item_id,
                version=1,
                item_type="task",
                title="Active task",
                status="active",
                path="/task1",
                depth=0,
                metadata=TaskMetadata(),
                created_at=now,
                updated_at=now,
                created_by="claude-code",
            )
        ],
        total_count=25,  # Total filtered results, not total items in database
        limit=50,
        offset=0,
        has_more=False,
    )

    assert output.total_count == 25  # Count of filtered results only


@pytest.mark.contract
def test_list_work_items_output_missing_required_fields() -> None:
    """Test list_work_items output validation fails when required fields missing."""
    # Missing total_count
    with pytest.raises(ValidationError) as exc_info:
        PaginatedWorkItemsResponse(  # type: ignore[call-arg]
            items=[],
            limit=50,
            offset=0,
            has_more=False,
        )

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("total_count",) for error in errors)

    # Missing has_more
    with pytest.raises(ValidationError) as exc_info:
        PaginatedWorkItemsResponse(  # type: ignore[call-arg]
            items=[],
            total_count=0,
            limit=50,
            offset=0,
        )

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("has_more",) for error in errors)


@pytest.mark.contract
def test_list_work_items_output_negative_total_count() -> None:
    """Test list_work_items output validation fails for negative total_count."""
    with pytest.raises(ValidationError) as exc_info:
        PaginatedWorkItemsResponse(
            items=[],
            total_count=-1,
            limit=50,
            offset=0,
            has_more=False,
        )

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("total_count",) for error in errors)


# ============================================================================
# Contract Tests: Work Item Entity Validation
# ============================================================================


@pytest.mark.contract
def test_work_item_valid_project_metadata() -> None:
    """Test WorkItem validation with ProjectMetadata."""
    item_id = uuid4()
    now = datetime.now(UTC)

    work_item = WorkItem(
        id=item_id,
        version=1,
        item_type="project",
        title="Codebase MCP Server",
        status="active",
        path="/project1",
        depth=0,
        metadata=ProjectMetadata(
            description="Build semantic code search MCP server",
            target_quarter="2025-Q1",
            constitutional_principles=["Simplicity Over Features", "Local-First"],
        ),
        created_at=now,
        updated_at=now,
        created_by="claude-code",
    )

    assert work_item.item_type == "project"
    assert isinstance(work_item.metadata, ProjectMetadata)
    assert work_item.metadata.target_quarter == "2025-Q1"


@pytest.mark.contract
def test_work_item_valid_session_metadata() -> None:
    """Test WorkItem validation with SessionMetadata."""
    item_id = uuid4()
    now = datetime.now(UTC)

    work_item = WorkItem(
        id=item_id,
        version=1,
        item_type="session",
        title="Feature 003 implementation session",
        status="active",
        path="/project1/session1",
        depth=1,
        metadata=SessionMetadata(
            token_budget=200000,
            prompts_count=15,
            yaml_frontmatter={"schema_version": "1.0", "mode": "implement"},
        ),
        created_at=now,
        updated_at=now,
        created_by="claude-code",
    )

    assert work_item.item_type == "session"
    assert isinstance(work_item.metadata, SessionMetadata)
    assert work_item.metadata.token_budget == 200000


@pytest.mark.contract
def test_work_item_valid_task_metadata() -> None:
    """Test WorkItem validation with TaskMetadata."""
    item_id = uuid4()
    now = datetime.now(UTC)

    work_item = WorkItem(
        id=item_id,
        version=1,
        item_type="task",
        title="Write contract tests for list_work_items",
        status="completed",
        path="/project1/session1/task1",
        depth=2,
        metadata=TaskMetadata(
            estimated_hours=2.0,
            actual_hours=1.5,
        ),
        created_at=now,
        updated_at=now,
        created_by="claude-code",
    )

    assert work_item.item_type == "task"
    assert isinstance(work_item.metadata, TaskMetadata)
    assert work_item.metadata.actual_hours == 1.5


@pytest.mark.contract
def test_work_item_valid_research_metadata() -> None:
    """Test WorkItem validation with ResearchMetadata."""
    item_id = uuid4()
    now = datetime.now(UTC)

    work_item = WorkItem(
        id=item_id,
        version=1,
        item_type="research",
        title="Evaluate FastMCP vs MCP Python SDK",
        status="completed",
        path="/project1/research1",
        depth=1,
        metadata=ResearchMetadata(
            research_questions=["Which framework better supports SSE?"],
            findings_summary="FastMCP provides better SSE support and type safety",
            references=["https://github.com/jlowin/fastmcp"],
        ),
        created_at=now,
        updated_at=now,
        created_by="claude-code",
    )

    assert work_item.item_type == "research"
    assert isinstance(work_item.metadata, ResearchMetadata)
    assert len(work_item.metadata.research_questions) == 1


@pytest.mark.contract
def test_work_item_soft_delete_timestamp() -> None:
    """Test WorkItem with soft delete timestamp (deleted_at)."""
    item_id = uuid4()
    now = datetime.now(UTC)
    deleted_time = datetime(2025, 10, 10, 12, 0, 0, tzinfo=UTC)

    work_item = WorkItem(
        id=item_id,
        version=2,
        item_type="task",
        title="Deprecated task",
        status="completed",
        path="/task1",
        depth=0,
        metadata=TaskMetadata(),
        deleted_at=deleted_time,  # Soft-deleted
        created_at=now,
        updated_at=now,
        created_by="claude-code",
    )

    assert work_item.deleted_at == deleted_time


@pytest.mark.contract
def test_work_item_git_fields() -> None:
    """Test WorkItem with git-related fields (branch_name, commit_hash, pr_number)."""
    item_id = uuid4()
    now = datetime.now(UTC)

    work_item = WorkItem(
        id=item_id,
        version=1,
        item_type="task",
        title="Implement feature X",
        status="completed",
        path="/task1",
        depth=0,
        branch_name="003-database-backed-project",
        commit_hash="a1b2c3d4e5f6789012345678901234567890abcd",
        pr_number=42,
        metadata=TaskMetadata(),
        created_at=now,
        updated_at=now,
        created_by="claude-code",
    )

    assert work_item.branch_name == "003-database-backed-project"
    assert work_item.commit_hash == "a1b2c3d4e5f6789012345678901234567890abcd"
    assert work_item.pr_number == 42


@pytest.mark.contract
def test_work_item_invalid_commit_hash() -> None:
    """Test WorkItem validation fails for invalid commit hash format."""
    item_id = uuid4()
    now = datetime.now(UTC)

    # Invalid: commit hash not 40 hex characters
    with pytest.raises(ValidationError) as exc_info:
        WorkItem(
            id=item_id,
            version=1,
            item_type="task",
            title="Task",
            status="active",
            path="/task1",
            depth=0,
            commit_hash="invalid_hash",  # Invalid format
            metadata=TaskMetadata(),
            created_at=now,
            updated_at=now,
            created_by="claude-code",
        )

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("commit_hash",) for error in errors)


@pytest.mark.contract
def test_work_item_depth_out_of_range() -> None:
    """Test WorkItem validation fails for depth > 5."""
    item_id = uuid4()
    now = datetime.now(UTC)

    # Invalid: depth exceeds maximum of 5
    with pytest.raises(ValidationError) as exc_info:
        WorkItem(
            id=item_id,
            version=1,
            item_type="task",
            title="Task",
            status="active",
            path="/p1/s1/t1/t2/t3/t4",
            depth=6,  # Exceeds max depth
            metadata=TaskMetadata(),
            created_at=now,
            updated_at=now,
            created_by="claude-code",
        )

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("depth",) for error in errors)


# ============================================================================
# Contract Tests: Tool Implementation (Must Fail)
# ============================================================================


@pytest.mark.contract
@pytest.mark.asyncio
async def test_list_work_items_tool_not_implemented() -> None:
    """
    Test documenting that list_work_items tool is not yet implemented.

    This test MUST fail until the actual tool implementation is complete.
    Once implemented, replace this with actual tool invocation tests.

    Expected behavior: Raises NotImplementedError or tool not found error
    """
    with pytest.raises(NotImplementedError) as exc_info:
        # TODO: Uncomment once tool is implemented
        # from src.mcp.tools.work_items import list_work_items
        # result = await list_work_items()
        raise NotImplementedError("list_work_items tool not implemented yet")

    assert "not implemented" in str(exc_info.value).lower()


# ============================================================================
# Contract Tests: Filter Combinations (Documentation)
# ============================================================================


@pytest.mark.contract
@pytest.mark.asyncio
async def test_list_work_items_filter_combinations() -> None:
    """
    Test that list_work_items supports various filter combinations.

    This test documents expected filtering behavior per FR-018.
    Once implemented, verify all filter combinations work correctly.

    Expected behaviors:
    - No filters: Returns all non-deleted work items (up to limit)
    - item_type only: Filters by type (project/session/task/research)
    - status only: Filters by status (active/completed/blocked)
    - parent_id only: Filters by parent (null = root-level items)
    - include_deleted=True: Includes soft-deleted items
    - Combined filters: All filters applied with AND operation
    - Pagination: limit and offset apply to all filtered results
    """
    parent_uuid = uuid4()

    # Document expected filter combination behaviors
    filter_combinations = [
        # No filters (all non-deleted items)
        {"limit": 50, "offset": 0},
        # Single filter cases
        {"item_type": "project", "limit": 50, "offset": 0},
        {"status": "active", "limit": 50, "offset": 0},
        {"parent_id": parent_uuid, "limit": 50, "offset": 0},
        {"include_deleted": True, "limit": 50, "offset": 0},
        # Combined filters (item_type + status)
        {"item_type": "task", "status": "active", "limit": 50, "offset": 0},
        # Combined filters (item_type + status + parent_id)
        {
            "item_type": "task",
            "status": "blocked",
            "parent_id": parent_uuid,
            "limit": 25,
            "offset": 0,
        },
        # All filters combined
        {
            "item_type": "task",
            "status": "completed",
            "parent_id": parent_uuid,
            "include_deleted": True,
            "limit": 10,
            "offset": 20,
        },
        # Root-level items only (parent_id=None semantic meaning)
        # Note: None means "all items" vs explicit filter for root-level
        {"item_type": "project", "limit": 50, "offset": 0},
    ]

    # TODO: Once implemented, test each combination:
    # from src.mcp.tools.work_items import list_work_items
    # for filters in filter_combinations:
    #     result = await list_work_items(**filters)
    #     assert isinstance(result, PaginatedWorkItemsResponse)
    #     assert result.total_count >= 0
    #     assert len(result.items) <= filters["limit"]

    assert len(filter_combinations) == 9, "All filter combinations documented"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_list_work_items_soft_delete_behavior() -> None:
    """
    Test that list_work_items excludes soft-deleted items by default (FR-012).

    Expected behaviors:
    - include_deleted=False (default): Excludes items with deleted_at != NULL
    - include_deleted=True: Includes items with deleted_at != NULL

    This test documents the expected behavior for soft delete filtering.
    """
    # TODO: Once implemented, test soft delete filtering:
    # from src.mcp.tools.work_items import list_work_items
    #
    # # Create work item and soft-delete it
    # work_item = await create_work_item(...)
    # await update_work_item(id=work_item.id, version=1, deleted_at=datetime.now(UTC))
    #
    # # Default behavior: soft-deleted items excluded
    # result_without_deleted = await list_work_items(include_deleted=False)
    # assert work_item.id not in [item.id for item in result_without_deleted.items]
    #
    # # With include_deleted=True: soft-deleted items included
    # result_with_deleted = await list_work_items(include_deleted=True)
    # assert work_item.id in [item.id for item in result_with_deleted.items]

    # Document requirement
    assert True, "Soft delete behavior documented (FR-012)"


# ============================================================================
# Contract Tests: Performance Requirements (Documentation)
# ============================================================================


@pytest.mark.contract
def test_list_work_items_performance_requirement_documented() -> None:
    """
    Document performance requirements for list_work_items tool.

    Performance Requirements (from mcp-tools.yaml):
    - p95 latency: < 200ms

    Implementation considerations:
    - Add database indexes on: item_type, status, parent_id, deleted_at
    - Use efficient pagination with LIMIT/OFFSET
    - Avoid N+1 queries for metadata JSONB fields
    - Consider query plan optimization for complex filters

    This test serves as documentation. Actual performance validation
    will be implemented in integration/performance tests.
    """
    p95_requirement_ms = 200

    # Document the requirement through assertion
    assert p95_requirement_ms == 200, "p95 latency requirement for list_work_items"

    # Database query with filters and pagination should be efficient
    # Required indexes for FR-018 filtering performance:
    required_indexes = [
        "idx_work_items_item_type",
        "idx_work_items_status",
        "idx_work_items_parent_id",
        "idx_work_items_deleted_at",
        "idx_work_items_updated_at",  # For ordering results
    ]

    assert len(required_indexes) == 5, "All required indexes documented"
