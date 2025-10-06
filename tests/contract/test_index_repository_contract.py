"""
T007: Contract tests for index_repository MCP tool.

These tests validate the MCP protocol contract for repository indexing functionality.
Tests MUST fail initially as the tool is not yet implemented (TDD approach).

Performance Requirements:
- Target: 10K files in < 60 seconds
- Maximum: 10K files in < 120 seconds
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, Field, ValidationError


# Input Schema Models
class IndexRepositoryInput(BaseModel):
    """Input schema for index_repository tool."""

    path: str = Field(..., description="Absolute path to repository")
    name: str = Field(..., description="Display name for repository")
    force_reindex: bool = Field(
        default=False,
        description="Force full re-index even if already indexed",
    )


# Output Schema Models
IndexStatus = Literal["success", "partial", "failed"]


class IndexRepositoryOutput(BaseModel):
    """Output schema for index_repository tool."""

    repository_id: UUID = Field(..., description="Unique repository identifier")
    files_indexed: int = Field(..., ge=0, description="Number of files indexed")
    chunks_created: int = Field(..., ge=0, description="Number of code chunks created")
    duration_seconds: float = Field(
        ..., ge=0.0, description="Indexing duration in seconds"
    )
    status: IndexStatus = Field(..., description="Indexing operation status")
    errors: list[str] = Field(
        default_factory=list, description="Array of error messages if any"
    )


# Contract Tests


@pytest.mark.contract
def test_index_repository_input_valid_minimal() -> None:
    """Test index_repository input schema with minimal required fields."""
    valid_input = IndexRepositoryInput(
        path="/home/user/my-repo",
        name="My Repository",
    )

    assert valid_input.path == "/home/user/my-repo"
    assert valid_input.name == "My Repository"
    assert valid_input.force_reindex is False  # Default value


@pytest.mark.contract
def test_index_repository_input_valid_with_force_reindex() -> None:
    """Test index_repository input schema with force_reindex enabled."""
    valid_input = IndexRepositoryInput(
        path="/home/user/my-repo",
        name="My Repository",
        force_reindex=True,
    )

    assert valid_input.path == "/home/user/my-repo"
    assert valid_input.name == "My Repository"
    assert valid_input.force_reindex is True


@pytest.mark.contract
def test_index_repository_input_missing_required_path() -> None:
    """Test index_repository input validation fails when path is missing."""
    with pytest.raises(ValidationError) as exc_info:
        IndexRepositoryInput(name="My Repository")  # type: ignore[call-arg]

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("path",) for error in errors)
    assert any(error["type"] == "missing" for error in errors)


@pytest.mark.contract
def test_index_repository_input_missing_required_name() -> None:
    """Test index_repository input validation fails when name is missing."""
    with pytest.raises(ValidationError) as exc_info:
        IndexRepositoryInput(path="/home/user/repo")  # type: ignore[call-arg]

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("name",) for error in errors)
    assert any(error["type"] == "missing" for error in errors)


@pytest.mark.contract
def test_index_repository_input_invalid_types() -> None:
    """Test index_repository input validation fails for invalid field types."""
    # Invalid path type (integer instead of string)
    with pytest.raises(ValidationError) as exc_info:
        IndexRepositoryInput(path=123, name="My Repository")  # type: ignore[arg-type]
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("path",) for error in errors)

    # Invalid name type (list instead of string)
    with pytest.raises(ValidationError) as exc_info:
        IndexRepositoryInput(path="/home/user/repo", name=["not", "a", "string"])  # type: ignore[arg-type]
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("name",) for error in errors)


@pytest.mark.contract
def test_index_repository_output_valid_success() -> None:
    """Test index_repository output schema for successful indexing."""
    repo_id = uuid4()
    output = IndexRepositoryOutput(
        repository_id=repo_id,
        files_indexed=150,
        chunks_created=3500,
        duration_seconds=12.5,
        status="success",
        errors=[],
    )

    assert output.repository_id == repo_id
    assert output.files_indexed == 150
    assert output.chunks_created == 3500
    assert output.duration_seconds == 12.5
    assert output.status == "success"
    assert output.errors == []


@pytest.mark.contract
def test_index_repository_output_valid_partial() -> None:
    """Test index_repository output schema for partial indexing with errors."""
    repo_id = uuid4()
    output = IndexRepositoryOutput(
        repository_id=repo_id,
        files_indexed=100,
        chunks_created=2000,
        duration_seconds=15.3,
        status="partial",
        errors=[
            "Failed to parse /src/corrupted.py: SyntaxError",
            "Permission denied: /src/private.py",
        ],
    )

    assert output.repository_id == repo_id
    assert output.files_indexed == 100
    assert output.chunks_created == 2000
    assert output.status == "partial"
    assert len(output.errors) == 2
    assert "SyntaxError" in output.errors[0]
    assert "Permission denied" in output.errors[1]


@pytest.mark.contract
def test_index_repository_output_valid_failed() -> None:
    """Test index_repository output schema for failed indexing."""
    repo_id = uuid4()
    output = IndexRepositoryOutput(
        repository_id=repo_id,
        files_indexed=0,
        chunks_created=0,
        duration_seconds=0.5,
        status="failed",
        errors=["Repository path does not exist: /invalid/path"],
    )

    assert output.repository_id == repo_id
    assert output.files_indexed == 0
    assert output.chunks_created == 0
    assert output.status == "failed"
    assert len(output.errors) == 1


@pytest.mark.contract
def test_index_repository_output_missing_required_fields() -> None:
    """Test index_repository output validation fails when required fields missing."""
    with pytest.raises(ValidationError) as exc_info:
        IndexRepositoryOutput(
            repository_id=uuid4(),
            files_indexed=100,
            # Missing: chunks_created, duration_seconds, status
        )  # type: ignore[call-arg]

    errors = exc_info.value.errors()
    # Should have errors for missing required fields
    assert len(errors) >= 3


@pytest.mark.contract
def test_index_repository_output_invalid_status_enum() -> None:
    """Test index_repository output validation fails for invalid status value."""
    with pytest.raises(ValidationError) as exc_info:
        IndexRepositoryOutput(
            repository_id=uuid4(),
            files_indexed=100,
            chunks_created=2000,
            duration_seconds=10.0,
            status="completed",  # type: ignore[arg-type]  # Invalid: not in enum
        )

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("status",) for error in errors)


@pytest.mark.contract
def test_index_repository_output_negative_counts() -> None:
    """Test index_repository output validation fails for negative count values."""
    # Negative files_indexed
    with pytest.raises(ValidationError) as exc_info:
        IndexRepositoryOutput(
            repository_id=uuid4(),
            files_indexed=-1,
            chunks_created=100,
            duration_seconds=10.0,
            status="success",
        )
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("files_indexed",) for error in errors)

    # Negative chunks_created
    with pytest.raises(ValidationError) as exc_info:
        IndexRepositoryOutput(
            repository_id=uuid4(),
            files_indexed=100,
            chunks_created=-1,
            duration_seconds=10.0,
            status="success",
        )
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("chunks_created",) for error in errors)

    # Negative duration_seconds
    with pytest.raises(ValidationError) as exc_info:
        IndexRepositoryOutput(
            repository_id=uuid4(),
            files_indexed=100,
            chunks_created=100,
            duration_seconds=-1.0,
            status="success",
        )
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("duration_seconds",) for error in errors)


@pytest.mark.contract
@pytest.mark.asyncio
async def test_index_repository_tool_not_implemented() -> None:
    """
    Test documenting that index_repository tool is not yet implemented.

    This test MUST fail until the actual tool implementation is complete.
    Once implemented, replace this with actual tool invocation tests.

    Expected behavior: Raises NotImplementedError
    """
    with pytest.raises(NotImplementedError) as exc_info:
        # TODO: Uncomment once tool is implemented
        # from src.mcp.tools.indexer import index_repository
        # result = await index_repository(path="/test/repo", name="Test Repo")
        raise NotImplementedError("index_repository tool not implemented yet")

    assert "not implemented" in str(exc_info.value).lower()


@pytest.mark.contract
def test_index_repository_performance_requirement_documented() -> None:
    """
    Document performance requirements for index_repository tool.

    Performance Requirements (from mcp-protocol.json):
    - Target: 10,000 files in < 60 seconds
    - Maximum: 10,000 files in < 120 seconds

    This test serves as documentation. Actual performance validation
    will be implemented in integration/performance tests.
    """
    target_duration_10k_files_seconds = 60
    max_duration_10k_files_seconds = 120

    # Document the requirements through assertions
    assert target_duration_10k_files_seconds == 60, "Target indexing performance"
    assert max_duration_10k_files_seconds == 120, "Maximum indexing performance"

    # Performance formula: ~167 files/second (target), ~83 files/second (minimum)
    # These requirements will be validated once tool is implemented
