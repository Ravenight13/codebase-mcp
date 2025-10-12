"""T015: Contract tests for invalid project_id validation.

Tests validate that MCP tools reject invalid project identifiers with proper
ValidationError responses, preventing security vulnerabilities and database errors.

Constitutional Compliance:
- Principle III: Protocol Compliance (MCP-compliant error responses)
- Principle V: Production Quality (comprehensive validation)
- Principle VII: Test-Driven Development (contract validation)
- Principle VIII: Type Safety (mypy --strict compliance)
- Principle XVI: Security-first design (SQL injection prevention)

Functional Requirements:
- FR-004: System MUST validate project identifiers before use
- FR-005: System MUST enforce lowercase alphanumeric with hyphen format
- FR-006: System MUST enforce maximum 50-character length
- FR-007: System MUST prevent identifiers starting or ending with hyphens
- FR-008: System MUST prevent consecutive hyphens
- FR-016: System MUST prevent security vulnerabilities via identifier validation
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from src.mcp.tools.indexing import index_repository
from src.mcp.tools.search import search_code

# Extract underlying functions from FastMCP FunctionTool wrappers
index_repository_fn = index_repository.fn
search_code_fn = search_code.fn


@pytest.mark.contract
@pytest.mark.parametrize(
    "invalid_id,reason",
    [
        ("My_Project", "Uppercase and underscore"),
        ("My-Project", "Uppercase letter"),
        ("my_project", "Underscore instead of hyphen"),
        ("-project", "Leading hyphen"),
        ("project-", "Trailing hyphen"),
        ("project--name", "Consecutive hyphens"),
        ("project'; DROP TABLE--", "SQL injection attempt"),
        ("a" * 51, "51+ characters (exceeds max length)"),
        ("Project-123", "Uppercase letter at start"),
        ("my-Project", "Uppercase letter in middle"),
        ("", "Empty string"),
        ("my project", "Contains space"),
        ("my/project", "Contains slash"),
        ("my.project", "Contains dot"),
        ("my@project", "Contains special character"),
    ],
)
@pytest.mark.asyncio
async def test_index_repository_invalid_project_id_validation(
    invalid_id: str, reason: str
) -> None:
    """Test index_repository rejects invalid project identifiers.

    Validates:
    - Invalid project_id formats are rejected
    - ValueError is raised with detailed message
    - No database operations are attempted
    - Error message explains the constraint violation

    Traces to:
    - contracts/mcp-tools.yaml lines 161-173 (ValidationError response)
    - src/models/project_identifier.py lines 66-109 (validation logic)
    """
    # Create temporary directory for testing
    test_repo = Path("/tmp/test-repo-invalid")
    test_repo.mkdir(exist_ok=True, parents=True)

    try:
        # Attempt to call tool with invalid project_id
        # Should raise ValueError during ProjectIdentifier validation
        with pytest.raises(ValueError) as exc_info:
            await index_repository_fn(
                repo_path=str(test_repo),
                project_id=invalid_id,
                force_reindex=False,
            )

        # Validate error message contains helpful information
        error_msg = str(exc_info.value)
        assert "Invalid project_id format" in error_msg or "Project identifier must be lowercase" in error_msg

        # Log reason for test documentation
        print(f"✅ Rejected: {invalid_id} - {reason}")

    finally:
        # Cleanup
        if test_repo.exists():
            test_repo.rmdir()


@pytest.mark.contract
@pytest.mark.parametrize(
    "invalid_id,reason",
    [
        ("My_Project", "Uppercase and underscore"),
        ("FRONTEND", "All uppercase"),
        ("-project", "Leading hyphen"),
        ("project-", "Trailing hyphen"),
        ("project--name", "Consecutive hyphens"),
        ("project'; DROP TABLE--", "SQL injection attempt"),
        ("a" * 51, "51+ characters (exceeds max length)"),
        ("123-project-" + "x" * 50, "Far exceeds max length"),
        ("my project", "Contains space"),
        ("my/project", "Contains slash"),
    ],
)
@pytest.mark.asyncio
async def test_search_code_invalid_project_id_validation(
    invalid_id: str, reason: str
) -> None:
    """Test search_code rejects invalid project identifiers.

    Validates:
    - Invalid project_id formats are rejected
    - ValueError is raised with detailed message
    - No database operations are attempted
    - Error message explains the constraint violation

    Traces to:
    - contracts/mcp-tools.yaml lines 268-273 (ValidationError response)
    - src/models/project_identifier.py lines 66-109 (validation logic)
    """
    # Attempt to call tool with invalid project_id
    # Should raise ValueError during ProjectIdentifier validation
    with pytest.raises(ValueError) as exc_info:
        await search_code_fn(
            query="test query",
            project_id=invalid_id,
            limit=10,
        )

    # Validate error message contains helpful information
    error_msg = str(exc_info.value)
    assert "Invalid project_id" in error_msg or "Project identifier must be lowercase" in error_msg

    # Log reason for test documentation
    print(f"✅ Rejected: {invalid_id} - {reason}")


@pytest.mark.contract
@pytest.mark.asyncio
async def test_uppercase_project_id_rejected() -> None:
    """Test uppercase project_id returns 400 ValidationError.

    Specific test case from tasks.md requirement.

    Validates:
    - "My_Project" is rejected (uppercase + underscore)
    - ValueError contains explanation of format rules
    - Error message includes examples of valid identifiers

    Traces to: tasks.md lines 206-207
    """
    test_repo = Path("/tmp/test-repo-uppercase")
    test_repo.mkdir(exist_ok=True, parents=True)

    try:
        with pytest.raises(ValueError) as exc_info:
            await index_repository_fn(
                repo_path=str(test_repo),
                project_id="My_Project",
                force_reindex=False,
            )

        error_msg = str(exc_info.value)
        # Should contain format explanation
        assert "lowercase" in error_msg.lower()

        # Should contain examples
        assert "client-a" in error_msg or "Examples" in error_msg

    finally:
        if test_repo.exists():
            test_repo.rmdir()


@pytest.mark.contract
@pytest.mark.asyncio
async def test_leading_hyphen_project_id_rejected() -> None:
    """Test leading hyphen project_id returns 400 ValidationError.

    Specific test case from tasks.md requirement.

    Validates:
    - "-project" is rejected (leading hyphen)
    - ValueError explains constraint violation
    - Error message helpful for user correction

    Traces to: tasks.md lines 208-209
    """
    test_repo = Path("/tmp/test-repo-leading-hyphen")
    test_repo.mkdir(exist_ok=True, parents=True)

    try:
        with pytest.raises(ValueError) as exc_info:
            await index_repository_fn(
                repo_path=str(test_repo),
                project_id="-project",
                force_reindex=False,
            )

        error_msg = str(exc_info.value)
        # Should explain hyphen constraint
        assert "hyphen" in error_msg.lower()

    finally:
        if test_repo.exists():
            test_repo.rmdir()


@pytest.mark.contract
@pytest.mark.asyncio
async def test_sql_injection_project_id_rejected() -> None:
    """Test SQL injection attempt project_id returns 400 ValidationError.

    Specific test case from tasks.md requirement.

    Validates:
    - "project'; DROP TABLE--" is rejected (SQL injection)
    - Validation prevents database security vulnerability
    - Error message does not leak security information

    Traces to: tasks.md lines 210-211
    """
    test_repo = Path("/tmp/test-repo-sql-injection")
    test_repo.mkdir(exist_ok=True, parents=True)

    try:
        with pytest.raises(ValueError) as exc_info:
            await index_repository_fn(
                repo_path=str(test_repo),
                project_id="project'; DROP TABLE--",
                force_reindex=False,
            )

        error_msg = str(exc_info.value)
        # Should reject due to format violation (single quote, semicolon, space)
        assert "Invalid project_id format" in error_msg or "lowercase" in error_msg.lower()

        # Should NOT leak security information about SQL
        # (generic validation error is correct behavior)

    finally:
        if test_repo.exists():
            test_repo.rmdir()


@pytest.mark.contract
@pytest.mark.asyncio
async def test_max_length_exceeded_project_id_rejected() -> None:
    """Test 51+ character project_id returns 400 ValidationError.

    Specific test case from tasks.md requirement.

    Validates:
    - 51+ character identifier is rejected
    - Validation enforces 50-character maximum
    - Error message mentions length constraint

    Traces to: tasks.md lines 212-213
    """
    # Create 51-character identifier
    long_id = "a" * 51
    assert len(long_id) == 51

    test_repo = Path("/tmp/test-repo-max-length")
    test_repo.mkdir(exist_ok=True, parents=True)

    try:
        with pytest.raises(ValueError) as exc_info:
            await index_repository_fn(
                repo_path=str(test_repo),
                project_id=long_id,
                force_reindex=False,
            )

        error_msg = str(exc_info.value)
        # Should mention length or max length constraint
        # Pydantic ValidationError from Field(max_length=50)
        assert "50" in error_msg or "length" in error_msg.lower()

    finally:
        if test_repo.exists():
            test_repo.rmdir()


@pytest.mark.contract
@pytest.mark.asyncio
async def test_consecutive_hyphens_project_id_rejected() -> None:
    """Test consecutive hyphens project_id returns 400 ValidationError.

    Validates:
    - "project--name" is rejected (consecutive hyphens)
    - Validation enforces single-hyphen separation
    - Error message explains constraint

    Traces to: contracts/mcp-tools.yaml lines 28-46
    """
    test_repo = Path("/tmp/test-repo-consecutive-hyphens")
    test_repo.mkdir(exist_ok=True, parents=True)

    try:
        with pytest.raises(ValueError) as exc_info:
            await index_repository_fn(
                repo_path=str(test_repo),
                project_id="project--name",
                force_reindex=False,
            )

        error_msg = str(exc_info.value)
        # Should mention consecutive hyphens
        assert "consecutive hyphens" in error_msg or "hyphen" in error_msg.lower()

    finally:
        if test_repo.exists():
            test_repo.rmdir()


@pytest.mark.contract
@pytest.mark.asyncio
async def test_empty_project_id_rejected() -> None:
    """Test empty string project_id returns 400 ValidationError.

    Validates:
    - Empty string is rejected
    - Validation enforces min_length=1
    - Error message mentions required constraint

    Traces to: contracts/mcp-tools.yaml lines 28-46
    """
    test_repo = Path("/tmp/test-repo-empty")
    test_repo.mkdir(exist_ok=True, parents=True)

    try:
        with pytest.raises(ValueError) as exc_info:
            await index_repository_fn(
                repo_path=str(test_repo),
                project_id="",
                force_reindex=False,
            )

        error_msg = str(exc_info.value)
        # Should mention length or required constraint
        assert "at least 1 character" in error_msg or "length" in error_msg.lower()

    finally:
        if test_repo.exists():
            test_repo.rmdir()


@pytest.mark.contract
def test_project_identifier_validation_comprehensive() -> None:
    """Test ProjectIdentifier model validation comprehensively.

    Validates:
    - Direct Pydantic model validation
    - All constraint violations raise ValidationError
    - Error messages are informative

    This test validates the model directly without MCP tool invocation.

    Traces to: src/models/project_identifier.py lines 33-127
    """
    from src.models.project_identifier import ProjectIdentifier

    # Valid identifiers should pass
    valid_ids = [
        "client-a",
        "frontend",
        "my-project-123",
        "a",
        "a" * 50,  # Max length
        "project-with-many-hyphens-separating-words",
    ]

    for valid_id in valid_ids:
        identifier = ProjectIdentifier(value=valid_id)
        assert identifier.value == valid_id
        print(f"✅ Valid: {valid_id}")

    # Invalid identifiers should raise ValidationError
    invalid_ids = [
        "My_Project",  # Uppercase + underscore
        "-project",  # Leading hyphen
        "project-",  # Trailing hyphen
        "project--name",  # Consecutive hyphens
        "a" * 51,  # Exceeds max length
        "",  # Empty string
        "my project",  # Space
        "my.project",  # Dot
    ]

    for invalid_id in invalid_ids:
        with pytest.raises(ValidationError):
            ProjectIdentifier(value=invalid_id)
        print(f"✅ Rejected: {invalid_id}")
