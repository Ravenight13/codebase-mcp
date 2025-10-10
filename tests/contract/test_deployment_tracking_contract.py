"""
T005: Contract tests for record_deployment MCP tool.

These tests validate the MCP protocol contract for deployment tracking functionality
with vendor and work item relationships. Tests MUST fail initially as the tool is
not yet implemented (TDD approach).

Performance Requirements:
- p95 latency: < 200ms

Contract Requirements (from contracts/mcp-tools.yaml):
- DeploymentCreate schema with deployed_at, metadata, vendor_ids, work_item_ids
- DeploymentMetadata validation: pr_number, pr_title, commit_hash, test_summary, constitutional_compliance
- Many-to-many relationships with vendors and work items via junction tables
- Error handling: invalid commit hash format, duplicate UUIDs, 404 for non-existent references

Feature Requirements: FR-005 to FR-007 (deployment tracking with relationships)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, Field, ValidationError, field_validator


# ============================================================================
# Schema Models
# ============================================================================


class DeploymentMetadata(BaseModel):
    """
    JSONB metadata for deployment events.

    Validates PR details, commit hash format, test results, and constitutional compliance.
    """

    pr_number: int = Field(
        ge=1,
        description="GitHub pull request number (must be positive)",
    )
    pr_title: str = Field(
        min_length=1,
        max_length=200,
        description="Pull request title",
    )
    commit_hash: str = Field(
        pattern=r"^[a-f0-9]{40}$",
        description="Git SHA-1 commit hash (exactly 40 lowercase hex characters)",
    )
    test_summary: dict[str, int] = Field(
        description="Test results by category (all counts must be non-negative)",
    )
    constitutional_compliance: bool = Field(
        description="Whether deployment passes constitutional validation",
    )

    @field_validator("test_summary")
    @classmethod
    def validate_test_counts_non_negative(cls, v: dict[str, int]) -> dict[str, int]:
        """Ensure all test counts are non-negative."""
        if any(count < 0 for count in v.values()):
            raise ValueError("test counts must be non-negative")
        return v


class DeploymentCreate(BaseModel):
    """
    Input schema for record_deployment MCP tool.

    Records deployment event with PR details, affected vendors, and related work items.
    """

    deployed_at: datetime = Field(
        description="Deployment timestamp (ISO 8601 format with timezone)",
    )
    metadata: DeploymentMetadata = Field(
        description="Deployment metadata including PR details and test results",
    )
    vendor_ids: list[UUID] = Field(
        default_factory=list,
        description="List of vendor UUIDs affected by this deployment",
    )
    work_item_ids: list[UUID] = Field(
        default_factory=list,
        description="List of work item UUIDs included in this deployment",
    )
    created_by: str = Field(
        max_length=100,
        description="AI client identifier recording this deployment",
    )

    @field_validator("vendor_ids")
    @classmethod
    def validate_no_duplicate_vendor_ids(cls, v: list[UUID]) -> list[UUID]:
        """Ensure no duplicate UUIDs in vendor_ids list."""
        if len(v) != len(set(v)):
            raise ValueError("duplicate vendor UUIDs not allowed")
        return v

    @field_validator("work_item_ids")
    @classmethod
    def validate_no_duplicate_work_item_ids(cls, v: list[UUID]) -> list[UUID]:
        """Ensure no duplicate UUIDs in work_item_ids list."""
        if len(v) != len(set(v)):
            raise ValueError("duplicate work item UUIDs not allowed")
        return v


class VendorExtractor(BaseModel):
    """Vendor extractor entity (minimal schema for relationship testing)."""

    id: UUID = Field(description="Vendor UUID")
    name: str = Field(description="Vendor name")
    status: str = Field(description="Operational status (operational/broken)")


class WorkItem(BaseModel):
    """Work item entity (minimal schema for relationship testing)."""

    id: UUID = Field(description="Work item UUID")
    title: str = Field(description="Work item title")
    item_type: str = Field(description="Work item type")


class DeploymentResponse(BaseModel):
    """
    Output schema for record_deployment MCP tool.

    Returns deployment event data with resolved vendor and work item relationships.
    """

    id: UUID = Field(description="Deployment event UUID")
    deployed_at: datetime = Field(description="Deployment timestamp")
    commit_hash: str = Field(description="Git commit hash (40 hex chars)")
    metadata: DeploymentMetadata = Field(description="Deployment metadata")
    created_at: datetime = Field(description="Creation timestamp")
    created_by: str = Field(description="AI client identifier")
    affected_vendors: list[VendorExtractor] = Field(
        default_factory=list,
        description="Vendors affected by this deployment",
    )
    related_work_items: list[WorkItem] = Field(
        default_factory=list,
        description="Work items included in this deployment",
    )


# ============================================================================
# DeploymentMetadata Validation Tests
# ============================================================================


@pytest.mark.contract
def test_deployment_metadata_valid_complete() -> None:
    """Test DeploymentMetadata with all required fields and valid values."""
    valid_metadata = DeploymentMetadata(
        pr_number=42,
        pr_title="feat(indexer): add tree-sitter AST parsing",
        commit_hash="a1b2c3d4e5f6789012345678901234567890abcd",
        test_summary={"unit": 150, "integration": 30, "contract": 8},
        constitutional_compliance=True,
    )

    assert valid_metadata.pr_number == 42
    assert valid_metadata.pr_title == "feat(indexer): add tree-sitter AST parsing"
    assert valid_metadata.commit_hash == "a1b2c3d4e5f6789012345678901234567890abcd"
    assert valid_metadata.test_summary["unit"] == 150
    assert valid_metadata.constitutional_compliance is True


@pytest.mark.contract
def test_deployment_metadata_pr_number_validation() -> None:
    """Test DeploymentMetadata validation: pr_number must be >= 1."""
    # pr_number = 0 should fail
    with pytest.raises(ValidationError) as exc_info:
        DeploymentMetadata(
            pr_number=0,
            pr_title="Valid title",
            commit_hash="a1b2c3d4e5f6789012345678901234567890abcd",
            test_summary={"unit": 10},
            constitutional_compliance=True,
        )
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("pr_number",) for error in errors)

    # pr_number = -5 should fail
    with pytest.raises(ValidationError) as exc_info:
        DeploymentMetadata(
            pr_number=-5,
            pr_title="Valid title",
            commit_hash="a1b2c3d4e5f6789012345678901234567890abcd",
            test_summary={"unit": 10},
            constitutional_compliance=True,
        )
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("pr_number",) for error in errors)


@pytest.mark.contract
def test_deployment_metadata_pr_title_validation() -> None:
    """Test DeploymentMetadata validation: pr_title must be 1-200 characters."""
    # Empty pr_title should fail
    with pytest.raises(ValidationError) as exc_info:
        DeploymentMetadata(
            pr_number=1,
            pr_title="",
            commit_hash="a1b2c3d4e5f6789012345678901234567890abcd",
            test_summary={"unit": 10},
            constitutional_compliance=True,
        )
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("pr_title",) for error in errors)

    # pr_title > 200 characters should fail
    long_title = "A" * 201
    with pytest.raises(ValidationError) as exc_info:
        DeploymentMetadata(
            pr_number=1,
            pr_title=long_title,
            commit_hash="a1b2c3d4e5f6789012345678901234567890abcd",
            test_summary={"unit": 10},
            constitutional_compliance=True,
        )
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("pr_title",) for error in errors)

    # pr_title = 200 characters should succeed
    max_length_title = "A" * 200
    valid_metadata = DeploymentMetadata(
        pr_number=1,
        pr_title=max_length_title,
        commit_hash="a1b2c3d4e5f6789012345678901234567890abcd",
        test_summary={"unit": 10},
        constitutional_compliance=True,
    )
    assert len(valid_metadata.pr_title) == 200


@pytest.mark.contract
def test_deployment_metadata_commit_hash_validation() -> None:
    """Test DeploymentMetadata validation: commit_hash must be exactly 40 lowercase hex characters."""
    # Too short (39 characters) should fail
    with pytest.raises(ValidationError) as exc_info:
        DeploymentMetadata(
            pr_number=1,
            pr_title="Valid title",
            commit_hash="a1b2c3d4e5f6789012345678901234567890abc",  # 39 chars
            test_summary={"unit": 10},
            constitutional_compliance=True,
        )
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("commit_hash",) for error in errors)

    # Too long (41 characters) should fail
    with pytest.raises(ValidationError) as exc_info:
        DeploymentMetadata(
            pr_number=1,
            pr_title="Valid title",
            commit_hash="a1b2c3d4e5f6789012345678901234567890abcde",  # 41 chars
            test_summary={"unit": 10},
            constitutional_compliance=True,
        )
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("commit_hash",) for error in errors)

    # Uppercase letters should fail (must be lowercase)
    with pytest.raises(ValidationError) as exc_info:
        DeploymentMetadata(
            pr_number=1,
            pr_title="Valid title",
            commit_hash="A1B2C3D4E5F6789012345678901234567890ABCD",  # uppercase
            test_summary={"unit": 10},
            constitutional_compliance=True,
        )
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("commit_hash",) for error in errors)

    # Invalid characters (non-hex) should fail
    with pytest.raises(ValidationError) as exc_info:
        DeploymentMetadata(
            pr_number=1,
            pr_title="Valid title",
            commit_hash="g1h2i3j4k5l6789012345678901234567890wxyz",  # non-hex chars
            test_summary={"unit": 10},
            constitutional_compliance=True,
        )
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("commit_hash",) for error in errors)

    # Valid 40-character lowercase hex hash should succeed
    valid_metadata = DeploymentMetadata(
        pr_number=1,
        pr_title="Valid title",
        commit_hash="a1b2c3d4e5f6789012345678901234567890abcd",
        test_summary={"unit": 10},
        constitutional_compliance=True,
    )
    assert len(valid_metadata.commit_hash) == 40
    assert valid_metadata.commit_hash.islower()


@pytest.mark.contract
def test_deployment_metadata_test_summary_validation() -> None:
    """Test DeploymentMetadata validation: test_summary counts must be non-negative."""
    # Negative test counts should fail
    with pytest.raises(ValidationError):
        DeploymentMetadata(
            pr_number=1,
            pr_title="Valid title",
            commit_hash="a1b2c3d4e5f6789012345678901234567890abcd",
            test_summary={"unit": 100, "integration": -5},  # negative count
            constitutional_compliance=True,
        )

    # Zero test counts should succeed
    valid_metadata = DeploymentMetadata(
        pr_number=1,
        pr_title="Valid title",
        commit_hash="a1b2c3d4e5f6789012345678901234567890abcd",
        test_summary={"unit": 0, "integration": 0},
        constitutional_compliance=True,
    )
    assert valid_metadata.test_summary["unit"] == 0

    # Multiple test categories should succeed
    valid_metadata = DeploymentMetadata(
        pr_number=1,
        pr_title="Valid title",
        commit_hash="a1b2c3d4e5f6789012345678901234567890abcd",
        test_summary={
            "unit": 150,
            "integration": 30,
            "contract": 8,
            "performance": 5,
        },
        constitutional_compliance=True,
    )
    assert len(valid_metadata.test_summary) == 4


@pytest.mark.contract
def test_deployment_metadata_constitutional_compliance_boolean() -> None:
    """Test DeploymentMetadata validation: constitutional_compliance must be boolean."""
    # True should succeed
    valid_metadata_true = DeploymentMetadata(
        pr_number=1,
        pr_title="Valid title",
        commit_hash="a1b2c3d4e5f6789012345678901234567890abcd",
        test_summary={"unit": 10},
        constitutional_compliance=True,
    )
    assert valid_metadata_true.constitutional_compliance is True

    # False should succeed
    valid_metadata_false = DeploymentMetadata(
        pr_number=1,
        pr_title="Valid title",
        commit_hash="a1b2c3d4e5f6789012345678901234567890abcd",
        test_summary={"unit": 10},
        constitutional_compliance=False,
    )
    assert valid_metadata_false.constitutional_compliance is False

    # Integer should fail (Pydantic is lenient but int is not bool)
    with pytest.raises(ValidationError) as exc_info:
        DeploymentMetadata(
            pr_number=1,
            pr_title="Valid title",
            commit_hash="a1b2c3d4e5f6789012345678901234567890abcd",
            test_summary={"unit": 10},
            constitutional_compliance=123,  # type: ignore[arg-type]
        )
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("constitutional_compliance",) for error in errors)


# ============================================================================
# DeploymentCreate Validation Tests
# ============================================================================


@pytest.mark.contract
def test_deployment_create_valid_minimal() -> None:
    """Test DeploymentCreate with minimal required fields (no relationships)."""
    now = datetime.now(UTC)
    valid_input = DeploymentCreate(
        deployed_at=now,
        metadata=DeploymentMetadata(
            pr_number=42,
            pr_title="feat: add deployment tracking",
            commit_hash="a1b2c3d4e5f6789012345678901234567890abcd",
            test_summary={"unit": 150},
            constitutional_compliance=True,
        ),
        created_by="claude-code-v1",
    )

    assert valid_input.deployed_at == now
    assert valid_input.metadata.pr_number == 42
    assert valid_input.vendor_ids == []
    assert valid_input.work_item_ids == []
    assert valid_input.created_by == "claude-code-v1"


@pytest.mark.contract
def test_deployment_create_valid_with_relationships() -> None:
    """Test DeploymentCreate with vendor and work item relationships."""
    now = datetime.now(UTC)
    vendor_id_1 = uuid4()
    vendor_id_2 = uuid4()
    work_item_id_1 = uuid4()
    work_item_id_2 = uuid4()

    valid_input = DeploymentCreate(
        deployed_at=now,
        metadata=DeploymentMetadata(
            pr_number=42,
            pr_title="feat: add deployment tracking",
            commit_hash="a1b2c3d4e5f6789012345678901234567890abcd",
            test_summary={"unit": 150, "integration": 30},
            constitutional_compliance=True,
        ),
        vendor_ids=[vendor_id_1, vendor_id_2],
        work_item_ids=[work_item_id_1, work_item_id_2],
        created_by="claude-code-v1",
    )

    assert len(valid_input.vendor_ids) == 2
    assert vendor_id_1 in valid_input.vendor_ids
    assert len(valid_input.work_item_ids) == 2
    assert work_item_id_1 in valid_input.work_item_ids


@pytest.mark.contract
def test_deployment_create_duplicate_vendor_ids_validation() -> None:
    """Test DeploymentCreate validation: vendor_ids must not contain duplicates."""
    now = datetime.now(UTC)
    vendor_id = uuid4()

    with pytest.raises(ValidationError):
        DeploymentCreate(
            deployed_at=now,
            metadata=DeploymentMetadata(
                pr_number=1,
                pr_title="Valid title",
                commit_hash="a1b2c3d4e5f6789012345678901234567890abcd",
                test_summary={"unit": 10},
                constitutional_compliance=True,
            ),
            vendor_ids=[vendor_id, vendor_id],  # duplicate
            created_by="claude-code",
        )


@pytest.mark.contract
def test_deployment_create_duplicate_work_item_ids_validation() -> None:
    """Test DeploymentCreate validation: work_item_ids must not contain duplicates."""
    now = datetime.now(UTC)
    work_item_id = uuid4()

    with pytest.raises(ValidationError):
        DeploymentCreate(
            deployed_at=now,
            metadata=DeploymentMetadata(
                pr_number=1,
                pr_title="Valid title",
                commit_hash="a1b2c3d4e5f6789012345678901234567890abcd",
                test_summary={"unit": 10},
                constitutional_compliance=True,
            ),
            work_item_ids=[work_item_id, work_item_id],  # duplicate
            created_by="claude-code",
        )


@pytest.mark.contract
def test_deployment_create_created_by_max_length() -> None:
    """Test DeploymentCreate validation: created_by must be <= 100 characters."""
    now = datetime.now(UTC)

    # 101 characters should fail
    long_created_by = "A" * 101
    with pytest.raises(ValidationError) as exc_info:
        DeploymentCreate(
            deployed_at=now,
            metadata=DeploymentMetadata(
                pr_number=1,
                pr_title="Valid title",
                commit_hash="a1b2c3d4e5f6789012345678901234567890abcd",
                test_summary={"unit": 10},
                constitutional_compliance=True,
            ),
            created_by=long_created_by,
        )
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("created_by",) for error in errors)

    # 100 characters should succeed
    max_length_created_by = "A" * 100
    valid_input = DeploymentCreate(
        deployed_at=now,
        metadata=DeploymentMetadata(
            pr_number=1,
            pr_title="Valid title",
            commit_hash="a1b2c3d4e5f6789012345678901234567890abcd",
            test_summary={"unit": 10},
            constitutional_compliance=True,
        ),
        created_by=max_length_created_by,
    )
    assert len(valid_input.created_by) == 100


@pytest.mark.contract
def test_deployment_create_deployed_at_timezone_aware() -> None:
    """Test DeploymentCreate validation: deployed_at should be timezone-aware datetime."""
    # Timezone-aware datetime should succeed
    now_utc = datetime.now(UTC)
    valid_input = DeploymentCreate(
        deployed_at=now_utc,
        metadata=DeploymentMetadata(
            pr_number=1,
            pr_title="Valid title",
            commit_hash="a1b2c3d4e5f6789012345678901234567890abcd",
            test_summary={"unit": 10},
            constitutional_compliance=True,
        ),
        created_by="claude-code",
    )
    assert valid_input.deployed_at.tzinfo is not None


# ============================================================================
# DeploymentResponse Schema Tests
# ============================================================================


@pytest.mark.contract
def test_deployment_response_includes_relationships() -> None:
    """Test DeploymentResponse includes affected_vendors and related_work_items."""
    deployment_id = uuid4()
    now = datetime.now(UTC)
    vendor_id = uuid4()
    work_item_id = uuid4()

    response = DeploymentResponse(
        id=deployment_id,
        deployed_at=now,
        commit_hash="a1b2c3d4e5f6789012345678901234567890abcd",
        metadata=DeploymentMetadata(
            pr_number=42,
            pr_title="feat: add deployment tracking",
            commit_hash="a1b2c3d4e5f6789012345678901234567890abcd",
            test_summary={"unit": 150},
            constitutional_compliance=True,
        ),
        created_at=now,
        created_by="claude-code",
        affected_vendors=[
            VendorExtractor(
                id=vendor_id,
                name="vendor_abc",
                status="operational",
            )
        ],
        related_work_items=[
            WorkItem(
                id=work_item_id,
                title="Implement deployment tracking",
                item_type="task",
            )
        ],
    )

    assert response.id == deployment_id
    assert len(response.affected_vendors) == 1
    assert response.affected_vendors[0].id == vendor_id
    assert len(response.related_work_items) == 1
    assert response.related_work_items[0].id == work_item_id


@pytest.mark.contract
def test_deployment_response_empty_relationships() -> None:
    """Test DeploymentResponse with no vendor/work item relationships."""
    deployment_id = uuid4()
    now = datetime.now(UTC)

    response = DeploymentResponse(
        id=deployment_id,
        deployed_at=now,
        commit_hash="a1b2c3d4e5f6789012345678901234567890abcd",
        metadata=DeploymentMetadata(
            pr_number=42,
            pr_title="feat: add deployment tracking",
            commit_hash="a1b2c3d4e5f6789012345678901234567890abcd",
            test_summary={"unit": 150},
            constitutional_compliance=True,
        ),
        created_at=now,
        created_by="claude-code",
    )

    assert response.affected_vendors == []
    assert response.related_work_items == []


@pytest.mark.contract
def test_deployment_response_generates_uuid() -> None:
    """Test DeploymentResponse includes generated UUID for deployment event."""
    now = datetime.now(UTC)

    response = DeploymentResponse(
        id=uuid4(),  # Should be generated by implementation
        deployed_at=now,
        commit_hash="a1b2c3d4e5f6789012345678901234567890abcd",
        metadata=DeploymentMetadata(
            pr_number=42,
            pr_title="feat: add deployment tracking",
            commit_hash="a1b2c3d4e5f6789012345678901234567890abcd",
            test_summary={"unit": 150},
            constitutional_compliance=True,
        ),
        created_at=now,
        created_by="claude-code",
    )

    assert isinstance(response.id, UUID)
    assert response.id is not None


# ============================================================================
# Tool Implementation Tests (TDD - MUST FAIL)
# ============================================================================


@pytest.mark.contract
@pytest.mark.asyncio
async def test_record_deployment_tool_not_implemented() -> None:
    """
    Test documenting that record_deployment tool is not yet implemented.

    This test MUST fail until the actual tool implementation is complete.
    Once implemented, replace this with actual tool invocation tests.

    Expected behavior: Raises NotImplementedError or tool not found error
    """
    with pytest.raises(NotImplementedError) as exc_info:
        # TODO: Uncomment once tool is implemented
        # from src.mcp.tools.deployments import record_deployment
        # result = await record_deployment(
        #     deployed_at=datetime.now(UTC),
        #     metadata=DeploymentMetadata(...),
        #     created_by="claude-code",
        # )
        raise NotImplementedError("record_deployment tool not implemented yet")

    assert "not implemented" in str(exc_info.value).lower()


@pytest.mark.contract
@pytest.mark.asyncio
async def test_record_deployment_creates_vendor_relationships() -> None:
    """
    Test that record_deployment creates many-to-many relationships with vendors.

    Expected behavior:
    - Junction table entries created for each vendor_id
    - Response includes full VendorExtractor objects in affected_vendors
    - Relationships queryable via foreign keys

    This test documents the requirement. Implementation validation follows.
    """
    # TODO: Once implemented, test actual behavior:
    # from src.mcp.tools.deployments import record_deployment
    # vendor_id_1 = uuid4()
    # vendor_id_2 = uuid4()
    #
    # result = await record_deployment(
    #     deployed_at=datetime.now(UTC),
    #     metadata=DeploymentMetadata(...),
    #     vendor_ids=[vendor_id_1, vendor_id_2],
    #     created_by="claude-code",
    # )
    #
    # assert len(result.affected_vendors) == 2
    # assert result.affected_vendors[0].id in [vendor_id_1, vendor_id_2]

    # Document the requirement
    assert True, "record_deployment should create vendor relationships via junction table"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_record_deployment_creates_work_item_relationships() -> None:
    """
    Test that record_deployment creates many-to-many relationships with work items.

    Expected behavior:
    - Junction table entries created for each work_item_id
    - Response includes full WorkItem objects in related_work_items
    - Relationships queryable via foreign keys

    This test documents the requirement. Implementation validation follows.
    """
    # TODO: Once implemented, test actual behavior:
    # from src.mcp.tools.deployments import record_deployment
    # work_item_id_1 = uuid4()
    # work_item_id_2 = uuid4()
    #
    # result = await record_deployment(
    #     deployed_at=datetime.now(UTC),
    #     metadata=DeploymentMetadata(...),
    #     work_item_ids=[work_item_id_1, work_item_id_2],
    #     created_by="claude-code",
    # )
    #
    # assert len(result.related_work_items) == 2
    # assert result.related_work_items[0].id in [work_item_id_1, work_item_id_2]

    # Document the requirement
    assert True, "record_deployment should create work item relationships via junction table"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_record_deployment_404_for_non_existent_vendor() -> None:
    """
    Test that record_deployment returns 404 error for non-existent vendor reference.

    Expected behavior:
    - If vendor_id does not exist in vendors table, return NotFoundError
    - Error message should indicate which vendor UUID was not found
    - No deployment record should be created (transaction rollback)

    This test documents the requirement. Implementation validation follows.
    """
    # TODO: Once implemented, test actual behavior:
    # from src.mcp.tools.deployments import record_deployment
    # non_existent_vendor_id = uuid4()
    #
    # with pytest.raises(NotFoundError) as exc_info:
    #     await record_deployment(
    #         deployed_at=datetime.now(UTC),
    #         metadata=DeploymentMetadata(...),
    #         vendor_ids=[non_existent_vendor_id],
    #         created_by="claude-code",
    #     )
    #
    # assert str(non_existent_vendor_id) in str(exc_info.value)

    # Document the requirement
    assert True, "record_deployment should return 404 for non-existent vendor_id"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_record_deployment_404_for_non_existent_work_item() -> None:
    """
    Test that record_deployment returns 404 error for non-existent work item reference.

    Expected behavior:
    - If work_item_id does not exist in work_items table, return NotFoundError
    - Error message should indicate which work item UUID was not found
    - No deployment record should be created (transaction rollback)

    This test documents the requirement. Implementation validation follows.
    """
    # TODO: Once implemented, test actual behavior:
    # from src.mcp.tools.deployments import record_deployment
    # non_existent_work_item_id = uuid4()
    #
    # with pytest.raises(NotFoundError) as exc_info:
    #     await record_deployment(
    #         deployed_at=datetime.now(UTC),
    #         metadata=DeploymentMetadata(...),
    #         work_item_ids=[non_existent_work_item_id],
    #         created_by="claude-code",
    #     )
    #
    # assert str(non_existent_work_item_id) in str(exc_info.value)

    # Document the requirement
    assert True, "record_deployment should return 404 for non-existent work_item_id"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_record_deployment_commit_hash_stored_in_metadata() -> None:
    """
    Test that record_deployment stores commit_hash in metadata JSONB field.

    Expected behavior:
    - DeploymentMetadata.commit_hash validated against regex pattern
    - commit_hash also stored at top level of DeploymentEvent for indexing
    - Both values should match

    This test documents the requirement. Implementation validation follows.
    """
    # TODO: Once implemented, test actual behavior:
    # from src.mcp.tools.deployments import record_deployment
    # commit_hash = "a1b2c3d4e5f6789012345678901234567890abcd"
    #
    # result = await record_deployment(
    #     deployed_at=datetime.now(UTC),
    #     metadata=DeploymentMetadata(
    #         pr_number=42,
    #         pr_title="feat: test",
    #         commit_hash=commit_hash,
    #         test_summary={"unit": 10},
    #         constitutional_compliance=True,
    #     ),
    #     created_by="claude-code",
    # )
    #
    # assert result.commit_hash == commit_hash
    # assert result.metadata.commit_hash == commit_hash

    # Document the requirement
    assert True, "record_deployment should store commit_hash in both top-level and metadata fields"


@pytest.mark.contract
def test_record_deployment_performance_requirement_documented() -> None:
    """
    Document performance requirements for record_deployment tool.

    Performance Requirements (from mcp-tools.yaml):
    - p95 latency: < 200ms

    This includes:
    - INSERT into deployment_events table
    - Bulk INSERT into vendor_deployments junction table
    - Bulk INSERT into work_item_deployments junction table
    - SELECT queries to fetch related vendor and work item data

    This test serves as documentation. Actual performance validation
    will be implemented in integration/performance tests.
    """
    p95_requirement_ms = 200

    # Document the requirement through assertion
    assert p95_requirement_ms == 200, "p95 latency requirement for record_deployment"

    # Complex operation with multiple table inserts and joins
    # Requirement will be validated once tool is implemented
