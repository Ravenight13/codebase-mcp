"""
Pydantic Schemas for Database-Backed Project Tracking System

This module contains all Pydantic models for JSONB validation and MCP tool input/output schemas.
Follows Pydantic 2.0+ conventions with Field constraints and custom validators.

Feature: 003-database-backed-project
Date: 2025-10-10
"""

from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


# ============================================================================
# Enums
# ============================================================================


class ItemType(str, Enum):
    """Work item type enumeration"""

    PROJECT = "project"
    SESSION = "session"
    TASK = "task"
    RESEARCH = "research"


class WorkItemStatus(str, Enum):
    """Work item status enumeration"""

    ACTIVE = "active"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class VendorStatus(str, Enum):
    """Vendor operational status enumeration"""

    OPERATIONAL = "operational"
    BROKEN = "broken"


class DependencyType(str, Enum):
    """Work item dependency type enumeration"""

    BLOCKS = "blocks"
    DEPENDS_ON = "depends_on"


class EnhancementStatus(str, Enum):
    """Future enhancement status enumeration"""

    PLANNED = "planned"
    APPROVED = "approved"
    IMPLEMENTING = "implementing"
    COMPLETED = "completed"


class ContextType(str, Enum):
    """Project context type enumeration"""

    FEATURE = "feature"
    MAINTENANCE = "maintenance"
    RESEARCH = "research"


# ============================================================================
# Metadata Schemas (for JSONB validation)
# ============================================================================


class VendorMetadata(BaseModel):
    """
    JSONB metadata for VendorExtractor entity.

    Validates format support flags, test results, version, and compliance status.
    """

    format_support: dict[Literal["excel", "csv", "pdf", "ocr"], bool] = Field(
        description="Supported file formats with capability flags",
        examples=[{"excel": True, "csv": True, "pdf": False, "ocr": False}],
    )
    test_results: dict[Literal["passing", "total", "skipped"], int] = Field(
        description="Test execution summary counts",
        examples=[{"passing": 45, "total": 50, "skipped": 5}],
    )
    extractor_version: str = Field(
        min_length=1,
        max_length=50,
        description="Semantic version string (e.g., '2.3.1')",
        examples=["2.3.1"],
    )
    manifest_compliant: bool = Field(
        description="Whether vendor follows manifest standards"
    )

    @field_validator("test_results")
    @classmethod
    def validate_test_counts(cls, v: dict[str, int]) -> dict[str, int]:
        """Validate test result counts are logical"""
        passing = v.get("passing", 0)
        total = v.get("total", 0)
        skipped = v.get("skipped", 0)

        if passing > total:
            raise ValueError(f"passing tests ({passing}) cannot exceed total tests ({total})")
        if passing + skipped > total:
            raise ValueError(
                f"passing + skipped ({passing + skipped}) cannot exceed total tests ({total})"
            )
        if any(count < 0 for count in v.values()):
            raise ValueError("test counts must be non-negative")

        return v


class ProjectMetadata(BaseModel):
    """
    Metadata for item_type='project' work items.

    Contains high-level project information, target timeline, and constitutional principles.
    """

    description: str = Field(
        max_length=1000,
        description="Project description and purpose",
    )
    target_quarter: Optional[str] = Field(
        None,
        pattern=r"^\d{4}-Q[1-4]$",
        description="Target completion quarter in YYYY-Q# format",
        examples=["2025-Q1"],
    )
    constitutional_principles: list[str] = Field(
        default_factory=list,
        description="List of constitutional principles relevant to this project",
        examples=[["Simplicity Over Features", "Local-First Architecture"]],
    )


class SessionMetadata(BaseModel):
    """
    Metadata for item_type='session' work items.

    Contains session-specific tracking data including token budget and YAML frontmatter.
    """

    token_budget: int = Field(
        ge=1000,
        le=1000000,
        description="Token budget allocated for this session",
        examples=[200000],
    )
    prompts_count: int = Field(
        ge=0,
        description="Number of prompts executed in this session",
        examples=[15],
    )
    yaml_frontmatter: dict[str, Any] = Field(
        description="Raw YAML frontmatter from session prompt file",
        examples=[{"schema_version": "1.0", "mode": "implement"}],
    )

    @field_validator("yaml_frontmatter")
    @classmethod
    def validate_schema_version(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Ensure YAML frontmatter includes required schema_version field"""
        if "schema_version" not in v:
            raise ValueError("YAML frontmatter must include schema_version")
        return v


class TaskMetadata(BaseModel):
    """
    Metadata for item_type='task' work items.

    Contains task execution tracking data including time estimates and blocking reasons.
    """

    estimated_hours: Optional[float] = Field(
        None,
        ge=0,
        le=1000,
        description="Estimated hours to complete task",
        examples=[2.5],
    )
    actual_hours: Optional[float] = Field(
        None,
        ge=0,
        le=1000,
        description="Actual hours spent on task",
        examples=[3.0],
    )
    blocked_reason: Optional[str] = Field(
        None,
        max_length=500,
        description="Reason why task is blocked (if status='blocked')",
        examples=["Waiting for database migration to complete"],
    )


class ResearchMetadata(BaseModel):
    """
    Metadata for item_type='research' work items.

    Contains research-specific data including questions, findings, and references.
    """

    research_questions: list[str] = Field(
        default_factory=list,
        description="List of research questions addressed",
        examples=[["What is the best caching strategy?", "How to handle offline fallback?"]],
    )
    findings_summary: Optional[str] = Field(
        None,
        max_length=2000,
        description="Summary of research findings",
        examples=["SQLite provides best offline fallback with minimal overhead"],
    )
    references: list[str] = Field(
        default_factory=list,
        description="List of reference URLs or documents",
        examples=[["https://docs.sqlalchemy.org/en/20/", "RFC 7234"]],
    )


class DeploymentMetadata(BaseModel):
    """
    JSONB metadata for DeploymentEvent entity.

    Contains PR details, commit hash, test results, and constitutional compliance status.
    """

    pr_number: int = Field(
        ge=1,
        description="GitHub pull request number",
        examples=[123],
    )
    pr_title: str = Field(
        min_length=1,
        max_length=200,
        description="Pull request title",
        examples=["feat(indexer): add tree-sitter AST parsing"],
    )
    commit_hash: str = Field(
        pattern=r"^[a-f0-9]{40}$",
        description="Git SHA-1 commit hash (40 lowercase hex characters)",
        examples=["84b04732a1f5e9c8d3b2a0e6f7c8d9e0a1b2c3d4"],
    )
    test_summary: dict[str, int] = Field(
        description="Test results by category (e.g., {'unit': 150, 'integration': 30})",
        examples=[{"unit": 150, "integration": 30, "contract": 8}],
    )
    constitutional_compliance: bool = Field(
        description="Whether deployment passes constitutional validation"
    )

    @field_validator("test_summary")
    @classmethod
    def validate_test_counts_non_negative(cls, v: dict[str, int]) -> dict[str, int]:
        """Ensure all test counts are non-negative"""
        if any(count < 0 for count in v.values()):
            raise ValueError("test counts must be non-negative")
        return v


# ============================================================================
# Union Types for Polymorphic Metadata
# ============================================================================

# WorkItemMetadata is a union of all work item metadata types
# The appropriate type is selected based on WorkItem.item_type
WorkItemMetadata = Annotated[
    Union[ProjectMetadata, SessionMetadata, TaskMetadata, ResearchMetadata],
    Field(discriminator="item_type"),
]


# ============================================================================
# MCP Tool Input Schemas
# ============================================================================


class WorkItemCreate(BaseModel):
    """
    Input schema for create_work_item MCP tool.

    Creates a new work item with type-specific metadata and optional parent relationship.
    """

    item_type: ItemType = Field(
        description="Type of work item to create",
        examples=["project"],
    )
    title: str = Field(
        max_length=200,
        description="Work item title",
        examples=["Implement semantic code search"],
    )
    parent_id: Optional[UUID] = Field(
        None,
        description="Parent work item UUID (null for root items)",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    metadata: Union[ProjectMetadata, SessionMetadata, TaskMetadata, ResearchMetadata] = Field(
        description="Type-specific metadata (must match item_type)",
    )
    branch_name: Optional[str] = Field(
        None,
        max_length=100,
        description="Git branch name associated with this work item",
        examples=["001-semantic-search"],
    )
    created_by: str = Field(
        max_length=100,
        description="AI client identifier creating this work item",
        examples=["claude-code-v1"],
    )

    @model_validator(mode="after")
    def validate_metadata_matches_type(self) -> "WorkItemCreate":
        """Ensure metadata type matches item_type"""
        type_map = {
            ItemType.PROJECT: ProjectMetadata,
            ItemType.SESSION: SessionMetadata,
            ItemType.TASK: TaskMetadata,
            ItemType.RESEARCH: ResearchMetadata,
        }
        expected_type = type_map[self.item_type]
        if not isinstance(self.metadata, expected_type):
            raise ValueError(
                f"metadata must be {expected_type.__name__} when item_type is {self.item_type.value}"
            )
        return self


class WorkItemUpdate(BaseModel):
    """
    Input schema for update_work_item MCP tool.

    Updates an existing work item with optimistic locking via version check.
    All fields except id and version are optional (partial updates supported).
    """

    id: UUID = Field(
        description="Work item UUID to update",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    version: int = Field(
        ge=1,
        description="Current version for optimistic locking (prevents concurrent updates)",
        examples=[3],
    )
    title: Optional[str] = Field(
        None,
        max_length=200,
        description="Updated work item title",
    )
    status: Optional[WorkItemStatus] = Field(
        None,
        description="Updated work item status",
    )
    metadata: Optional[Union[ProjectMetadata, SessionMetadata, TaskMetadata, ResearchMetadata]] = Field(
        None,
        description="Updated type-specific metadata",
    )
    branch_name: Optional[str] = Field(
        None,
        max_length=100,
        description="Updated git branch name",
    )
    commit_hash: Optional[str] = Field(
        None,
        pattern=r"^[a-f0-9]{40}$",
        description="Git commit hash (40 lowercase hex characters)",
    )
    pr_number: Optional[int] = Field(
        None,
        ge=1,
        description="GitHub pull request number",
    )
    deleted_at: Optional[datetime] = Field(
        None,
        description="Soft delete timestamp (set to NOW() to delete)",
    )


class WorkItemQuery(BaseModel):
    """
    Input schema for query_work_item MCP tool.

    Retrieves a single work item with optional full hierarchy (ancestors and descendants).
    """

    id: UUID = Field(
        description="Work item UUID to query",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    include_hierarchy: bool = Field(
        default=False,
        description="Include ancestors and descendants in response",
    )
    max_depth: int = Field(
        default=5,
        ge=1,
        le=5,
        description="Maximum hierarchy depth to retrieve (1-5 levels)",
    )


class WorkItemList(BaseModel):
    """
    Input schema for list_work_items MCP tool.

    Lists work items with filtering and pagination support.
    """

    item_type: Optional[ItemType] = Field(
        None,
        description="Filter by work item type",
    )
    status: Optional[WorkItemStatus] = Field(
        None,
        description="Filter by work item status",
    )
    parent_id: Optional[UUID] = Field(
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
        le=1000,
        description="Maximum number of results to return",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Number of results to skip (for pagination)",
    )


class DeploymentCreate(BaseModel):
    """
    Input schema for record_deployment MCP tool.

    Records a deployment event with PR details, affected vendors, and related work items.
    """

    deployed_at: datetime = Field(
        description="Deployment timestamp",
        examples=["2025-10-10T14:30:00Z"],
    )
    metadata: DeploymentMetadata = Field(
        description="Deployment metadata including PR details and test results",
    )
    vendor_ids: list[UUID] = Field(
        default_factory=list,
        description="List of vendor UUIDs affected by this deployment",
        examples=[["550e8400-e29b-41d4-a716-446655440000"]],
    )
    work_item_ids: list[UUID] = Field(
        default_factory=list,
        description="List of work item UUIDs included in this deployment",
        examples=[["660e8400-e29b-41d4-a716-446655440001"]],
    )
    created_by: str = Field(
        max_length=100,
        description="AI client identifier recording this deployment",
        examples=["claude-code-v1"],
    )

    @field_validator("vendor_ids", "work_item_ids")
    @classmethod
    def validate_no_duplicate_ids(cls, v: list[UUID]) -> list[UUID]:
        """Ensure no duplicate UUIDs in lists"""
        if len(v) != len(set(v)):
            raise ValueError("duplicate UUIDs not allowed")
        return v


class VendorStatusUpdate(BaseModel):
    """
    Input schema for update_vendor_status MCP tool.

    Updates vendor operational status, test results, and capability flags.
    """

    vendor_id: UUID = Field(
        description="Vendor UUID to update",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    version: int = Field(
        ge=1,
        description="Current version for optimistic locking",
        examples=[2],
    )
    status: Optional[VendorStatus] = Field(
        None,
        description="Updated operational status",
    )
    test_results: Optional[dict[Literal["passing", "total", "skipped"], int]] = Field(
        None,
        description="Updated test execution results",
    )
    format_support: Optional[dict[Literal["excel", "csv", "pdf", "ocr"], bool]] = Field(
        None,
        description="Updated format support flags",
    )
    extractor_version: Optional[str] = Field(
        None,
        min_length=1,
        max_length=50,
        description="Updated extractor version string",
    )

    @field_validator("test_results")
    @classmethod
    def validate_test_counts(cls, v: Optional[dict[str, int]]) -> Optional[dict[str, int]]:
        """Validate test result counts if provided"""
        if v is None:
            return v

        passing = v.get("passing", 0)
        total = v.get("total", 0)
        skipped = v.get("skipped", 0)

        if passing > total:
            raise ValueError(f"passing tests ({passing}) cannot exceed total tests ({total})")
        if passing + skipped > total:
            raise ValueError(
                f"passing + skipped ({passing + skipped}) cannot exceed total tests ({total})"
            )
        if any(count < 0 for count in v.values()):
            raise ValueError("test counts must be non-negative")

        return v


class VendorQuery(BaseModel):
    """
    Input schema for query_vendor_status MCP tool.

    Queries vendor operational status and metadata.
    Performance target: <1ms for single vendor lookup.
    """

    vendor_id: Optional[UUID] = Field(
        None,
        description="Vendor UUID to query (null for all vendors)",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    name: Optional[str] = Field(
        None,
        max_length=100,
        description="Vendor name to query (alternative to vendor_id)",
        examples=["vendor_abc"],
    )
    status_filter: Optional[VendorStatus] = Field(
        None,
        description="Filter vendors by operational status",
    )

    @model_validator(mode="after")
    def validate_query_fields(self) -> "VendorQuery":
        """Ensure at least one query field is provided, or querying all vendors"""
        if self.vendor_id is None and self.name is None and self.status_filter is None:
            # Query all vendors - valid use case
            pass
        return self


# ============================================================================
# MCP Tool Output Schemas
# ============================================================================


class WorkItemResponse(BaseModel):
    """
    Output schema for work item queries.

    Returns complete work item data with optional hierarchy information.
    """

    id: UUID = Field(description="Work item UUID")
    version: int = Field(description="Current version number (for optimistic locking)")
    item_type: ItemType = Field(description="Work item type")
    title: str = Field(description="Work item title")
    status: WorkItemStatus = Field(description="Work item status")
    parent_id: Optional[UUID] = Field(None, description="Parent work item UUID")
    path: str = Field(description="Materialized path (/parent1/parent2/current)")
    depth: int = Field(description="Hierarchy depth (0-5)")
    branch_name: Optional[str] = Field(None, description="Git branch name")
    commit_hash: Optional[str] = Field(None, description="Git commit hash")
    pr_number: Optional[int] = Field(None, description="GitHub PR number")
    metadata: Union[ProjectMetadata, SessionMetadata, TaskMetadata, ResearchMetadata] = Field(
        description="Type-specific metadata"
    )
    deleted_at: Optional[datetime] = Field(None, description="Soft delete timestamp")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    created_by: str = Field(description="AI client identifier")

    # Optional hierarchy fields
    ancestors: Optional[list["WorkItemResponse"]] = Field(
        None,
        description="Ancestor work items (if include_hierarchy=True)",
    )
    descendants: Optional[list["WorkItemResponse"]] = Field(
        None,
        description="Descendant work items (if include_hierarchy=True)",
    )


class VendorResponse(BaseModel):
    """
    Output schema for vendor queries.

    Returns vendor operational status and metadata.
    """

    id: UUID = Field(description="Vendor UUID")
    version: int = Field(description="Current version number (for optimistic locking)")
    name: str = Field(description="Vendor name (unique)")
    status: VendorStatus = Field(description="Operational status")
    extractor_version: str = Field(description="Extractor version string")
    metadata: VendorMetadata = Field(description="Vendor metadata")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    created_by: str = Field(description="AI client identifier")


class DeploymentResponse(BaseModel):
    """
    Output schema for deployment queries.

    Returns deployment event data with relationships.
    """

    id: UUID = Field(description="Deployment event UUID")
    deployed_at: datetime = Field(description="Deployment timestamp")
    commit_hash: str = Field(description="Git commit hash (40 hex chars)")
    metadata: DeploymentMetadata = Field(description="Deployment metadata")
    vendor_ids: list[UUID] = Field(description="Affected vendor UUIDs")
    work_item_ids: list[UUID] = Field(description="Included work item UUIDs")
    created_at: datetime = Field(description="Creation timestamp")
    created_by: str = Field(description="AI client identifier")


class ProjectConfigurationResponse(BaseModel):
    """
    Output schema for get_project_configuration MCP tool.

    Returns singleton global configuration.
    """

    id: int = Field(description="Singleton ID (always 1)")
    active_context_type: ContextType = Field(description="Current project context type")
    current_session_id: Optional[UUID] = Field(None, description="Active session work item UUID")
    git_branch: Optional[str] = Field(None, description="Current git branch")
    git_head_commit: Optional[str] = Field(None, description="Current git HEAD commit hash")
    default_token_budget: int = Field(description="Default token budget for sessions")
    database_healthy: bool = Field(description="Database health status")
    last_health_check_at: Optional[datetime] = Field(None, description="Last health check timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    updated_by: str = Field(description="AI client identifier")


class PaginatedWorkItemsResponse(BaseModel):
    """
    Output schema for list_work_items MCP tool.

    Returns paginated work items with total count.
    """

    items: list[WorkItemResponse] = Field(description="Work items in current page")
    total_count: int = Field(description="Total number of items matching filter")
    limit: int = Field(description="Maximum items per page")
    offset: int = Field(description="Number of items skipped")
    has_more: bool = Field(description="Whether more items exist beyond current page")


class PaginatedVendorsResponse(BaseModel):
    """
    Output schema for list vendors.

    Returns paginated vendors with total count.
    """

    items: list[VendorResponse] = Field(description="Vendors in current page")
    total_count: int = Field(description="Total number of vendors matching filter")
    limit: int = Field(description="Maximum items per page")
    offset: int = Field(description="Number of items skipped")
    has_more: bool = Field(description="Whether more items exist beyond current page")


# ============================================================================
# Error Response Schemas
# ============================================================================


class ValidationError(BaseModel):
    """
    Standard validation error response.

    Returned when input validation fails.
    """

    error_type: Literal["validation_error"] = "validation_error"
    message: str = Field(description="Human-readable error message")
    field: Optional[str] = Field(None, description="Field that failed validation")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional error details")


class OptimisticLockError(BaseModel):
    """
    Optimistic locking error response.

    Returned when version mismatch occurs during update.
    """

    error_type: Literal["optimistic_lock_error"] = "optimistic_lock_error"
    message: str = Field(description="Human-readable error message")
    current_version: int = Field(description="Current version in database")
    requested_version: int = Field(description="Version provided in update request")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional error details")


class NotFoundError(BaseModel):
    """
    Resource not found error response.

    Returned when requested entity does not exist.
    """

    error_type: Literal["not_found_error"] = "not_found_error"
    message: str = Field(description="Human-readable error message")
    resource_type: str = Field(description="Type of resource that was not found")
    resource_id: str = Field(description="ID of resource that was not found")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional error details")


# Enable forward references for recursive WorkItemResponse
WorkItemResponse.model_rebuild()
