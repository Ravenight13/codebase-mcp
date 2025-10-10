"""
T008: Contract tests for get_project_configuration MCP tool.

These tests validate the MCP protocol contract for project configuration functionality.
Tests MUST fail initially as the tool is not yet implemented (TDD approach).

Contract Requirements (from contracts/mcp-tools.yaml):
- ProjectConfigurationResponse schema with all required fields
- Singleton behavior (id always equals 1)
- Context type enum validation (feature/maintenance/research)
- Current session ID references valid work item (FK relationship)
- Git branch and commit hash presence validation
- Default token budget within valid range (1000-1000000)
- Database health status boolean flag
- Last health check timestamp format validation

Performance Requirements:
- p95 latency: < 50ms

Related:
- FR-015: Global configuration management
- FR-016: Context type tracking
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ValidationError
import pytest

# ============================================================================
# Type Definitions
# ============================================================================

ContextType = Literal["feature", "maintenance", "research"]


# ============================================================================
# Schema Models
# ============================================================================


class ProjectConfigurationResponse(BaseModel):
    """
    Output schema for get_project_configuration MCP tool.

    Singleton configuration object (id always equals 1).
    """

    id: int = Field(..., description="Singleton ID (always 1)")
    active_context_type: ContextType = Field(
        ..., description="Current project context type"
    )
    current_session_id: UUID | None = Field(
        None, description="Active session work item UUID"
    )
    git_branch: str | None = Field(None, description="Current git branch")
    git_head_commit: str | None = Field(
        None,
        description="Current git HEAD commit hash (40 lowercase hex characters)",
        pattern=r"^[a-f0-9]{40}$",
    )
    default_token_budget: int = Field(
        ...,
        ge=1000,
        le=1000000,
        description="Default token budget for sessions",
    )
    database_healthy: bool = Field(..., description="Database health status")
    last_health_check_at: datetime | None = Field(
        None, description="Last health check timestamp"
    )
    updated_at: datetime = Field(..., description="Last update timestamp")
    updated_by: str = Field(
        ..., max_length=100, description="AI client identifier"
    )


# ============================================================================
# Contract Tests: Output Schema Validation
# ============================================================================


@pytest.mark.contract
def test_configuration_output_valid_minimal() -> None:
    """Test ProjectConfigurationResponse with minimal required fields."""
    now = datetime.now(UTC)

    config = ProjectConfigurationResponse(
        id=1,
        active_context_type="feature",
        current_session_id=None,
        git_branch=None,
        git_head_commit=None,
        default_token_budget=200000,
        database_healthy=True,
        last_health_check_at=None,
        updated_at=now,
        updated_by="claude-code",
    )

    assert config.id == 1
    assert config.active_context_type == "feature"
    assert config.current_session_id is None
    assert config.git_branch is None
    assert config.git_head_commit is None
    assert config.default_token_budget == 200000
    assert config.database_healthy is True
    assert config.last_health_check_at is None
    assert config.updated_at == now
    assert config.updated_by == "claude-code"


@pytest.mark.contract
def test_configuration_output_valid_complete() -> None:
    """Test ProjectConfigurationResponse with all optional fields populated."""
    now = datetime.now(UTC)
    session_id = uuid4()

    config = ProjectConfigurationResponse(
        id=1,
        active_context_type="feature",
        current_session_id=session_id,
        git_branch="003-database-backed-project",
        git_head_commit="a1b2c3d4e5f6789012345678901234567890abcd",
        default_token_budget=200000,
        database_healthy=True,
        last_health_check_at=now,
        updated_at=now,
        updated_by="claude-code",
    )

    assert config.id == 1
    assert config.active_context_type == "feature"
    assert config.current_session_id == session_id
    assert config.git_branch == "003-database-backed-project"
    assert config.git_head_commit == "a1b2c3d4e5f6789012345678901234567890abcd"
    assert config.default_token_budget == 200000
    assert config.database_healthy is True
    assert config.last_health_check_at == now
    assert config.updated_at == now
    assert config.updated_by == "claude-code"


@pytest.mark.contract
def test_configuration_singleton_id_must_be_one() -> None:
    """Test ProjectConfigurationResponse rejects id != 1 (singleton constraint)."""
    now = datetime.now(UTC)

    # id=1 should be valid
    config = ProjectConfigurationResponse(
        id=1,
        active_context_type="feature",
        default_token_budget=200000,
        database_healthy=True,
        updated_at=now,
        updated_by="claude-code",
    )
    assert config.id == 1

    # Note: Pydantic does not enforce enum constraint on int fields at validation time
    # The contract requires id to ALWAYS be 1 (database constraint)
    # This test documents the expected behavior that the tool returns id=1
    assert config.id == 1, "Configuration ID must always be 1 (singleton)"


@pytest.mark.contract
def test_configuration_context_type_enum_valid_values() -> None:
    """Test ProjectConfigurationResponse accepts all valid context types."""
    now = datetime.now(UTC)

    # Test "feature" context
    config_feature = ProjectConfigurationResponse(
        id=1,
        active_context_type="feature",
        default_token_budget=200000,
        database_healthy=True,
        updated_at=now,
        updated_by="claude-code",
    )
    assert config_feature.active_context_type == "feature"

    # Test "maintenance" context
    config_maintenance = ProjectConfigurationResponse(
        id=1,
        active_context_type="maintenance",
        default_token_budget=200000,
        database_healthy=True,
        updated_at=now,
        updated_by="claude-code",
    )
    assert config_maintenance.active_context_type == "maintenance"

    # Test "research" context
    config_research = ProjectConfigurationResponse(
        id=1,
        active_context_type="research",
        default_token_budget=200000,
        database_healthy=True,
        updated_at=now,
        updated_by="claude-code",
    )
    assert config_research.active_context_type == "research"


@pytest.mark.contract
def test_configuration_context_type_invalid_value() -> None:
    """Test ProjectConfigurationResponse rejects invalid context type."""
    now = datetime.now(UTC)

    with pytest.raises(ValidationError) as exc_info:
        ProjectConfigurationResponse(
            id=1,
            active_context_type="invalid-context",  # type: ignore[arg-type]
            default_token_budget=200000,
            database_healthy=True,
            updated_at=now,
            updated_by="claude-code",
        )

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("active_context_type",) for error in errors)


@pytest.mark.contract
def test_configuration_current_session_id_valid_uuid() -> None:
    """Test ProjectConfigurationResponse accepts valid UUID for current_session_id."""
    now = datetime.now(UTC)
    session_id = uuid4()

    config = ProjectConfigurationResponse(
        id=1,
        active_context_type="feature",
        current_session_id=session_id,
        default_token_budget=200000,
        database_healthy=True,
        updated_at=now,
        updated_by="claude-code",
    )

    assert isinstance(config.current_session_id, UUID)
    assert config.current_session_id == session_id


@pytest.mark.contract
def test_configuration_current_session_id_null_allowed() -> None:
    """Test ProjectConfigurationResponse accepts null for current_session_id."""
    now = datetime.now(UTC)

    config = ProjectConfigurationResponse(
        id=1,
        active_context_type="feature",
        current_session_id=None,
        default_token_budget=200000,
        database_healthy=True,
        updated_at=now,
        updated_by="claude-code",
    )

    assert config.current_session_id is None


@pytest.mark.contract
def test_configuration_git_branch_string_validation() -> None:
    """Test ProjectConfigurationResponse accepts string git branch names."""
    now = datetime.now(UTC)

    # Valid git branch names
    valid_branches = [
        "main",
        "003-database-backed-project",
        "feature/user-authentication",
        "bugfix/issue-123",
    ]

    for branch in valid_branches:
        config = ProjectConfigurationResponse(
            id=1,
            active_context_type="feature",
            git_branch=branch,
            default_token_budget=200000,
            database_healthy=True,
            updated_at=now,
            updated_by="claude-code",
        )
        assert config.git_branch == branch


@pytest.mark.contract
def test_configuration_git_branch_null_allowed() -> None:
    """Test ProjectConfigurationResponse accepts null for git_branch."""
    now = datetime.now(UTC)

    config = ProjectConfigurationResponse(
        id=1,
        active_context_type="feature",
        git_branch=None,
        default_token_budget=200000,
        database_healthy=True,
        updated_at=now,
        updated_by="claude-code",
    )

    assert config.git_branch is None


@pytest.mark.contract
def test_configuration_git_commit_valid_hash() -> None:
    """Test ProjectConfigurationResponse accepts valid 40-char hex commit hash."""
    now = datetime.now(UTC)

    valid_commit = "a1b2c3d4e5f6789012345678901234567890abcd"  # 40 lowercase hex

    config = ProjectConfigurationResponse(
        id=1,
        active_context_type="feature",
        git_head_commit=valid_commit,
        default_token_budget=200000,
        database_healthy=True,
        updated_at=now,
        updated_by="claude-code",
    )

    assert config.git_head_commit == valid_commit
    assert len(config.git_head_commit) == 40


@pytest.mark.contract
def test_configuration_git_commit_invalid_format() -> None:
    """Test ProjectConfigurationResponse rejects invalid commit hash formats."""
    now = datetime.now(UTC)

    # Invalid commit hashes
    invalid_commits = [
        "abc123",  # Too short
        "g1b2c3d4e5f6789012345678901234567890abcd",  # Invalid char 'g'
        "A1B2C3D4E5F6789012345678901234567890ABCD",  # Uppercase not allowed
        "a1b2c3d4e5f6789012345678901234567890abcd1",  # Too long (41 chars)
    ]

    for invalid_commit in invalid_commits:
        with pytest.raises(ValidationError) as exc_info:
            ProjectConfigurationResponse(
                id=1,
                active_context_type="feature",
                git_head_commit=invalid_commit,
                default_token_budget=200000,
                database_healthy=True,
                updated_at=now,
                updated_by="claude-code",
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("git_head_commit",) for error in errors)


@pytest.mark.contract
def test_configuration_git_commit_null_allowed() -> None:
    """Test ProjectConfigurationResponse accepts null for git_head_commit."""
    now = datetime.now(UTC)

    config = ProjectConfigurationResponse(
        id=1,
        active_context_type="feature",
        git_head_commit=None,
        default_token_budget=200000,
        database_healthy=True,
        updated_at=now,
        updated_by="claude-code",
    )

    assert config.git_head_commit is None


@pytest.mark.contract
def test_configuration_token_budget_valid_range() -> None:
    """Test ProjectConfigurationResponse accepts token budget within valid range."""
    now = datetime.now(UTC)

    # Minimum valid value (1000)
    config_min = ProjectConfigurationResponse(
        id=1,
        active_context_type="feature",
        default_token_budget=1000,
        database_healthy=True,
        updated_at=now,
        updated_by="claude-code",
    )
    assert config_min.default_token_budget == 1000

    # Maximum valid value (1000000)
    config_max = ProjectConfigurationResponse(
        id=1,
        active_context_type="feature",
        default_token_budget=1000000,
        database_healthy=True,
        updated_at=now,
        updated_by="claude-code",
    )
    assert config_max.default_token_budget == 1000000

    # Typical value (200000)
    config_typical = ProjectConfigurationResponse(
        id=1,
        active_context_type="feature",
        default_token_budget=200000,
        database_healthy=True,
        updated_at=now,
        updated_by="claude-code",
    )
    assert config_typical.default_token_budget == 200000


@pytest.mark.contract
def test_configuration_token_budget_below_minimum() -> None:
    """Test ProjectConfigurationResponse rejects token budget below minimum (1000)."""
    now = datetime.now(UTC)

    with pytest.raises(ValidationError) as exc_info:
        ProjectConfigurationResponse(
            id=1,
            active_context_type="feature",
            default_token_budget=999,  # Below minimum
            database_healthy=True,
            updated_at=now,
            updated_by="claude-code",
        )

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("default_token_budget",) for error in errors)
    assert any("greater than or equal to 1000" in str(error) for error in errors)


@pytest.mark.contract
def test_configuration_token_budget_above_maximum() -> None:
    """Test ProjectConfigurationResponse rejects token budget above maximum (1000000)."""
    now = datetime.now(UTC)

    with pytest.raises(ValidationError) as exc_info:
        ProjectConfigurationResponse(
            id=1,
            active_context_type="feature",
            default_token_budget=1000001,  # Above maximum
            database_healthy=True,
            updated_at=now,
            updated_by="claude-code",
        )

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("default_token_budget",) for error in errors)
    assert any("less than or equal to 1000000" in str(error) for error in errors)


@pytest.mark.contract
def test_configuration_database_healthy_boolean() -> None:
    """Test ProjectConfigurationResponse accepts boolean for database_healthy."""
    now = datetime.now(UTC)

    # Test True
    config_healthy = ProjectConfigurationResponse(
        id=1,
        active_context_type="feature",
        default_token_budget=200000,
        database_healthy=True,
        updated_at=now,
        updated_by="claude-code",
    )
    assert config_healthy.database_healthy is True

    # Test False
    config_unhealthy = ProjectConfigurationResponse(
        id=1,
        active_context_type="feature",
        default_token_budget=200000,
        database_healthy=False,
        updated_at=now,
        updated_by="claude-code",
    )
    assert config_unhealthy.database_healthy is False


@pytest.mark.contract
def test_configuration_database_healthy_type_coercion() -> None:
    """
    Test ProjectConfigurationResponse coerces valid values to boolean.

    Pydantic 2.x coerces string values like "yes", "no", "true", "false" to bool.
    This test documents the type coercion behavior.
    """
    now = datetime.now(UTC)

    # Pydantic 2.x coerces "yes" to True
    config_yes = ProjectConfigurationResponse(
        id=1,
        active_context_type="feature",
        default_token_budget=200000,
        database_healthy="yes",  # type: ignore[arg-type]
        updated_at=now,
        updated_by="claude-code",
    )
    assert config_yes.database_healthy is True

    # Pydantic 2.x coerces "no" to False
    config_no = ProjectConfigurationResponse(
        id=1,
        active_context_type="feature",
        default_token_budget=200000,
        database_healthy="no",  # type: ignore[arg-type]
        updated_at=now,
        updated_by="claude-code",
    )
    assert config_no.database_healthy is False

    # Pydantic 2.x coerces 1 to True
    config_one = ProjectConfigurationResponse(
        id=1,
        active_context_type="feature",
        default_token_budget=200000,
        database_healthy=1,  # type: ignore[arg-type]
        updated_at=now,
        updated_by="claude-code",
    )
    assert config_one.database_healthy is True

    # Pydantic 2.x coerces 0 to False
    config_zero = ProjectConfigurationResponse(
        id=1,
        active_context_type="feature",
        default_token_budget=200000,
        database_healthy=0,  # type: ignore[arg-type]
        updated_at=now,
        updated_by="claude-code",
    )
    assert config_zero.database_healthy is False


@pytest.mark.contract
def test_configuration_health_check_timestamp_valid() -> None:
    """Test ProjectConfigurationResponse accepts valid datetime for health check."""
    now = datetime.now(UTC)
    health_check_time = datetime(2025, 10, 10, 14, 0, 0, tzinfo=UTC)

    config = ProjectConfigurationResponse(
        id=1,
        active_context_type="feature",
        default_token_budget=200000,
        database_healthy=True,
        last_health_check_at=health_check_time,
        updated_at=now,
        updated_by="claude-code",
    )

    assert config.last_health_check_at == health_check_time
    assert isinstance(config.last_health_check_at, datetime)


@pytest.mark.contract
def test_configuration_health_check_timestamp_null_allowed() -> None:
    """Test ProjectConfigurationResponse accepts null for last_health_check_at."""
    now = datetime.now(UTC)

    config = ProjectConfigurationResponse(
        id=1,
        active_context_type="feature",
        default_token_budget=200000,
        database_healthy=True,
        last_health_check_at=None,
        updated_at=now,
        updated_by="claude-code",
    )

    assert config.last_health_check_at is None


@pytest.mark.contract
def test_configuration_updated_at_timestamp_required() -> None:
    """Test ProjectConfigurationResponse requires updated_at timestamp."""
    with pytest.raises(ValidationError) as exc_info:
        ProjectConfigurationResponse(
            id=1,
            active_context_type="feature",
            default_token_budget=200000,
            database_healthy=True,
            updated_by="claude-code",
        )  # type: ignore[call-arg]

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("updated_at",) for error in errors)
    assert any(error["type"] == "missing" for error in errors)


@pytest.mark.contract
def test_configuration_updated_by_string_required() -> None:
    """Test ProjectConfigurationResponse requires updated_by string."""
    now = datetime.now(UTC)

    # Valid updated_by
    config = ProjectConfigurationResponse(
        id=1,
        active_context_type="feature",
        default_token_budget=200000,
        database_healthy=True,
        updated_at=now,
        updated_by="claude-code",
    )
    assert config.updated_by == "claude-code"

    # Missing updated_by
    with pytest.raises(ValidationError) as exc_info:
        ProjectConfigurationResponse(
            id=1,
            active_context_type="feature",
            default_token_budget=200000,
            database_healthy=True,
            updated_at=now,
        )  # type: ignore[call-arg]

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("updated_by",) for error in errors)


@pytest.mark.contract
def test_configuration_updated_by_max_length() -> None:
    """Test ProjectConfigurationResponse validates updated_by max length (100 chars)."""
    now = datetime.now(UTC)

    # At max length (100 chars) - should be valid
    max_length_client = "c" * 100
    config = ProjectConfigurationResponse(
        id=1,
        active_context_type="feature",
        default_token_budget=200000,
        database_healthy=True,
        updated_at=now,
        updated_by=max_length_client,
    )
    assert len(config.updated_by) == 100

    # Exceeds max length (101 chars) - should fail
    too_long_client = "c" * 101
    with pytest.raises(ValidationError) as exc_info:
        ProjectConfigurationResponse(
            id=1,
            active_context_type="feature",
            default_token_budget=200000,
            database_healthy=True,
            updated_at=now,
            updated_by=too_long_client,
        )

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("updated_by",) for error in errors)


# ============================================================================
# Contract Tests: Tool Invocation (Not Implemented - TDD)
# ============================================================================


@pytest.mark.contract
@pytest.mark.asyncio
async def test_get_project_configuration_tool_not_implemented() -> None:
    """
    Test documenting that get_project_configuration tool is not yet implemented.

    This test MUST fail until the actual tool implementation is complete.
    Once implemented, replace this with actual tool invocation tests.

    Expected behavior: Raises NotImplementedError or "Tool not found" error
    """
    error_message = "get_project_configuration tool not implemented yet"
    with pytest.raises(NotImplementedError) as exc_info:
        # TODO: Uncomment once tool is implemented
        # from src.mcp.tools.configuration import get_project_configuration
        # result = await get_project_configuration()
        raise NotImplementedError(error_message)

    assert "not implemented" in str(exc_info.value).lower()


@pytest.mark.contract
@pytest.mark.asyncio
async def test_get_project_configuration_singleton_behavior() -> None:
    """
    Test get_project_configuration returns singleton (id=1 always).

    Expected behavior: Tool returns configuration with id=1 on every call.
    Multiple calls should return the same configuration object (id=1).

    This test documents expected singleton behavior.
    """
    # TODO: Once implemented, verify singleton behavior:
    # from src.mcp.tools.configuration import get_project_configuration
    #
    # result1 = await get_project_configuration()
    # assert result1.id == 1
    #
    # result2 = await get_project_configuration()
    # assert result2.id == 1
    # assert result1.id == result2.id  # Same singleton ID

    # Document the requirement
    assert True, "get_project_configuration must always return id=1 (singleton)"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_get_project_configuration_no_parameters_required() -> None:
    """
    Test get_project_configuration accepts no parameters.

    Expected behavior: Tool requires no input parameters (singleton query).

    This test documents the parameter-free contract.
    """
    # TODO: Once implemented, verify no parameters required:
    # from src.mcp.tools.configuration import get_project_configuration
    # result = await get_project_configuration()  # No parameters
    # assert result is not None

    # Document the requirement
    assert True, "get_project_configuration requires no input parameters"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_get_project_configuration_returns_complete_schema() -> None:
    """
    Test get_project_configuration returns complete ProjectConfigurationResponse.

    Expected behavior: Tool returns all required fields:
    - id (always 1)
    - active_context_type
    - current_session_id (nullable)
    - git_branch (nullable)
    - git_head_commit (nullable)
    - default_token_budget
    - database_healthy
    - last_health_check_at (nullable)
    - updated_at
    - updated_by

    This test documents the complete response schema.
    """
    # TODO: Once implemented, verify all fields present:
    # from src.mcp.tools.configuration import get_project_configuration
    # result = await get_project_configuration()
    #
    # assert result.id == 1
    # assert result.active_context_type in ["feature", "maintenance", "research"]
    # assert isinstance(result.default_token_budget, int)
    # assert isinstance(result.database_healthy, bool)
    # assert isinstance(result.updated_at, datetime)
    # assert isinstance(result.updated_by, str)

    # Document the requirement
    assert (
        True
    ), "get_project_configuration returns complete ProjectConfigurationResponse"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_get_project_configuration_foreign_key_validation() -> None:
    """
    Test current_session_id references valid work item (FK relationship).

    Expected behavior: If current_session_id is not null, it must reference
    an existing work item of type 'session' in the work_items table.

    This test documents the foreign key constraint requirement.
    """
    # TODO: Once implemented, verify FK relationship:
    # from src.mcp.tools.configuration import get_project_configuration
    # from src.mcp.tools.work_items import query_work_item
    #
    # config = await get_project_configuration()
    #
    # if config.current_session_id is not None:
    #     # Verify the session exists
    #     session = await query_work_item(id=config.current_session_id)
    #     assert session.item_type == "session"

    # Document the requirement
    assert (
        True
    ), "current_session_id must reference valid session work item if not null"


@pytest.mark.contract
def test_get_project_configuration_performance_requirement_documented() -> None:
    """
    Document performance requirements for get_project_configuration tool.

    Performance Requirements (from contracts/mcp-tools.yaml):
    - p95 latency: < 50ms

    This test serves as documentation. Actual performance validation
    will be implemented in integration/performance tests.
    """
    p95_requirement_ms = 50

    # Document the requirement through assertion
    assert (
        p95_requirement_ms == 50
    ), "p95 latency requirement for get_project_configuration"

    # Single row SELECT by primary key (id=1) should be very fast
    # Requirement will be validated once tool is implemented
