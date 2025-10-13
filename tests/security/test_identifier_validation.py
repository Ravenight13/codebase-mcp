"""Security test for identifier validation (T027).

Tests comprehensive validation of project identifiers including valid formats,
invalid formats, edge cases, and security constraints.

Test Scenario: Quickstart Scenario 9 - Security
Validates: Security Scenario (Identifier Validation)
Traces to: FR-005, FR-006, FR-007, FR-008 (validation rules)

Constitutional Compliance:
- Principle V: Production quality (comprehensive validation testing)
- Principle VIII: Type safety (Pydantic model validation)
- Principle VII: TDD (validation correctness)
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.models.project_identifier import ProjectIdentifier


# ==============================================================================
# Unit Tests - Valid Identifier Acceptance
# ==============================================================================


@pytest.mark.security
@pytest.mark.parametrize(
    "valid_id,expected_schema_name",
    [
        # Simple valid formats
        ("client-a", "project_client_a"),
        ("frontend", "project_frontend"),
        ("my-project-123", "project_my_project_123"),
        # Edge cases (valid)
        ("a", "project_a"),  # Minimum length (1 char)
        ("z", "project_z"),  # Single letter
        ("0", "project_0"),  # Single digit
        ("abc123", "project_abc123"),  # Alphanumeric only
        ("123abc", "project_123abc"),  # Starts with digit
        ("project-2024-q1-test", "project_project_2024_q1_test"),  # Complex format
        # Max length (50 chars)
        ("a" * 50, f"project_{'a' * 50}"),
        ("x" * 49 + "9", f"project_{'x' * 49}9"),
        # Multiple hyphens (non-consecutive)
        ("a-b-c-d-e", "project_a_b_c_d_e"),
        ("test-project-name-123", "project_test_project_name_123"),
        # Mixed formats
        ("client-123", "project_client_123"),
        ("v1-api-backend", "project_v1_api_backend"),
        ("prod-2024", "project_prod_2024"),
    ],
)
@pytest.mark.unit
def test_valid_identifiers(valid_id: str, expected_schema_name: str) -> None:
    """Test valid identifiers are accepted with correct schema conversion.

    Validates that ProjectIdentifier model accepts all valid identifier formats
    and correctly converts them to PostgreSQL schema names.

    Valid Format Rules (FR-005, FR-006, FR-007, FR-008):
        - Lowercase alphanumeric characters: a-z, 0-9
        - Hyphens allowed: - (not at start/end, not consecutive)
        - Length: 1-50 characters
        - Schema name: "project_" + identifier (hyphens → underscores)

    Test Steps:
        1. Create ProjectIdentifier with valid identifier
        2. Verify no validation error raised
        3. Verify identifier value preserved
        4. Verify schema name correctly generated

    Expected Result:
        PASS - All valid identifiers accepted, schema names correct

    Traces to:
        - FR-005: Lowercase alphanumeric + hyphen format
        - FR-006: Max 50 characters
        - FR-007: No leading/trailing hyphens
        - FR-008: No consecutive hyphens
    """
    # Create identifier (should not raise validation error)
    identifier = ProjectIdentifier(value=valid_id)

    # Verify value preserved
    assert identifier.value == valid_id

    # Verify schema name conversion
    schema_name = identifier.to_schema_name()
    assert schema_name == expected_schema_name

    # Verify schema name format
    assert schema_name.startswith("project_")
    assert "-" not in schema_name  # All hyphens converted to underscores
    # Verify conversion: remove prefix, compare rest
    assert schema_name[8:] == valid_id.replace("-", "_")  # Skip "project_" prefix


# ==============================================================================
# Unit Tests - Invalid Identifier Rejection
# ==============================================================================


@pytest.mark.security
@pytest.mark.parametrize(
    "invalid_id,error_pattern",
    [
        # Uppercase characters (FR-005: lowercase only)
        ("My_Project", "lowercase"),
        ("PROJECT", "lowercase"),
        ("Client-A", "lowercase"),
        ("myProject", "lowercase"),
        ("ABC", "lowercase"),
        ("Test-123", "lowercase"),
        # Underscores not allowed (FR-005: alphanumeric + hyphen only)
        ("_project", "lowercase"),
        ("project_name", "lowercase"),
        ("my_project_123", "lowercase"),
        # Leading hyphens (FR-007: cannot start with hyphen)
        ("-project", "start"),
        ("-client", "start"),
        ("-a", "start"),
        ("--project", "start"),
        # Trailing hyphens (FR-007: cannot end with hyphen)
        ("project-", "end"),
        ("client-", "end"),
        ("a-", "end"),
        ("project--", "end"),
        # Consecutive hyphens (FR-008: no consecutive hyphens)
        ("project--name", "consecutive"),
        ("client---a", "consecutive"),
        ("a--b", "consecutive"),
        ("test--project--name", "consecutive"),
        # Special characters not allowed (FR-005: alphanumeric + hyphen only)
        ("project name", "lowercase"),  # Space
        ("project.name", "lowercase"),  # Period
        ("project@123", "lowercase"),  # At sign
        ("project#name", "lowercase"),  # Hash
        ("project$name", "lowercase"),  # Dollar
        ("project%name", "lowercase"),  # Percent
        ("project&name", "lowercase"),  # Ampersand
        ("project*name", "lowercase"),  # Asterisk
        ("project+name", "lowercase"),  # Plus
        ("project=name", "lowercase"),  # Equals
        ("project/name", "lowercase"),  # Slash
        ("project\\name", "lowercase"),  # Backslash
        ("project|name", "lowercase"),  # Pipe
        ("project:name", "lowercase"),  # Colon
        ("project;name", "lowercase"),  # Semicolon
        ("project'name", "lowercase"),  # Single quote
        ('project"name', "lowercase"),  # Double quote
        ("project<name", "lowercase"),  # Less than
        ("project>name", "lowercase"),  # Greater than
        ("project?name", "lowercase"),  # Question mark
        ("project!name", "lowercase"),  # Exclamation
        # Exceeds max length (FR-006: 50 characters max)
        ("a" * 51, "50"),
        ("project-" + "x" * 50, "50"),
        ("x" * 100, "50"),
        # Empty string (Pydantic min_length validation)
        ("", "at least 1"),
        # Unicode characters not allowed (FR-005: ASCII alphanumeric only)
        ("project-名前", "lowercase"),
        ("projet-café", "lowercase"),
        ("test-проект", "lowercase"),
        ("client-मेरा", "lowercase"),
        # SQL injection patterns (already tested in test_sql_injection.py)
        ("'; DROP TABLE--", "lowercase"),
        ("' OR '1'='1", "lowercase"),
    ],
)
@pytest.mark.unit
def test_invalid_identifiers(invalid_id: str, error_pattern: str) -> None:
    """Test invalid identifiers are rejected with clear error messages.

    Validates that ProjectIdentifier model rejects all invalid identifier
    formats with clear, actionable error messages.

    Invalid Format Examples:
        - Uppercase characters
        - Special characters (except hyphen)
        - Leading/trailing hyphens
        - Consecutive hyphens
        - Exceeds 50 characters
        - Empty string

    Test Steps:
        1. Attempt to create ProjectIdentifier with invalid identifier
        2. Verify ValidationError raised
        3. Verify error message contains expected pattern
        4. Verify error message is actionable (describes the problem)

    Expected Result:
        PASS - All invalid identifiers rejected with clear error messages

    Traces to:
        - FR-005: Lowercase alphanumeric + hyphen enforcement
        - FR-006: 50 character maximum
        - FR-007: No leading/trailing hyphens
        - FR-008: No consecutive hyphens
        - Constitutional Principle V: Production quality (clear error messages)
    """
    # Attempt to create identifier (should raise validation error)
    with pytest.raises(ValidationError) as exc_info:
        ProjectIdentifier(value=invalid_id)

    # Verify error message contains expected pattern
    error_msg = str(exc_info.value).lower()
    assert error_pattern in error_msg, (
        f"Expected error message to contain '{error_pattern}', "
        f"but got: {exc_info.value}"
    )

    # Verify error message is informative (mentions validation aspect)
    assert any(
        keyword in error_msg
        for keyword in [
            "lowercase",
            "alphanumeric",
            "hyphen",
            "start",
            "end",
            "consecutive",
            "50",
            "length",
            "identifier",
            "format",
        ]
    ), f"Error message should be informative, got: {exc_info.value}"


# ==============================================================================
# Unit Tests - Edge Cases
# ==============================================================================


@pytest.mark.security
@pytest.mark.unit
def test_edge_case_minimum_length() -> None:
    """Test minimum valid identifier length (1 character).

    Validates that single-character identifiers are accepted.

    Expected Result:
        PASS - Single character identifiers accepted
    """
    # Single lowercase letter
    identifier = ProjectIdentifier(value="a")
    assert identifier.value == "a"
    assert identifier.to_schema_name() == "project_a"

    # Single digit
    identifier = ProjectIdentifier(value="0")
    assert identifier.value == "0"
    assert identifier.to_schema_name() == "project_0"


@pytest.mark.security
@pytest.mark.unit
def test_edge_case_maximum_length() -> None:
    """Test maximum valid identifier length (50 characters).

    Validates that 50-character identifiers are accepted, but 51+ are rejected.

    Expected Result:
        PASS - 50 chars accepted, 51 chars rejected
    """
    # Maximum length (50 chars) - should pass
    max_length_id = "a" * 50
    identifier = ProjectIdentifier(value=max_length_id)
    assert identifier.value == max_length_id
    assert len(identifier.value) == 50

    # Exceeds max length (51 chars) - should fail
    over_length_id = "a" * 51
    with pytest.raises(ValidationError) as exc_info:
        ProjectIdentifier(value=over_length_id)

    error_msg = str(exc_info.value).lower()
    assert "50" in error_msg or "length" in error_msg


@pytest.mark.security
@pytest.mark.unit
def test_edge_case_hyphen_placement() -> None:
    """Test hyphen placement rules (not at start/end, not consecutive).

    Validates that hyphens are only allowed in valid positions.

    Valid Positions:
        - Between alphanumeric characters: "a-b"
        - Multiple hyphens (non-consecutive): "a-b-c"

    Invalid Positions:
        - Leading hyphen: "-abc"
        - Trailing hyphen: "abc-"
        - Consecutive hyphens: "a--b"

    Expected Result:
        PASS - Valid hyphen placements accepted, invalid rejected
    """
    # Valid: hyphen between characters
    identifier = ProjectIdentifier(value="a-b")
    assert identifier.value == "a-b"

    # Valid: multiple hyphens (non-consecutive)
    identifier = ProjectIdentifier(value="a-b-c-d")
    assert identifier.value == "a-b-c-d"

    # Invalid: leading hyphen
    with pytest.raises(ValidationError) as exc_info:
        ProjectIdentifier(value="-abc")
    assert "start" in str(exc_info.value).lower()

    # Invalid: trailing hyphen
    with pytest.raises(ValidationError) as exc_info:
        ProjectIdentifier(value="abc-")
    assert "end" in str(exc_info.value).lower()

    # Invalid: consecutive hyphens
    with pytest.raises(ValidationError) as exc_info:
        ProjectIdentifier(value="a--b")
    assert "consecutive" in str(exc_info.value).lower()


@pytest.mark.security
@pytest.mark.unit
def test_schema_name_conversion_consistency() -> None:
    """Test that schema name conversion is consistent and reversible.

    Validates that:
        - Hyphens are consistently converted to underscores
        - Schema names always start with "project_"
        - Conversion is deterministic (same input → same output)

    Expected Result:
        PASS - Schema name conversion is consistent
    """
    test_cases = [
        ("client-a", "project_client_a"),
        ("my-project-name", "project_my_project_name"),
        ("test-123-abc", "project_test_123_abc"),
        ("abc", "project_abc"),  # No hyphens
    ]

    for identifier_value, expected_schema in test_cases:
        identifier = ProjectIdentifier(value=identifier_value)
        schema_name = identifier.to_schema_name()

        # Verify expected schema name
        assert schema_name == expected_schema

        # Verify schema name format
        assert schema_name.startswith("project_")
        assert "-" not in schema_name  # All hyphens converted

        # Verify consistency (calling again produces same result)
        assert identifier.to_schema_name() == schema_name


@pytest.mark.security
@pytest.mark.unit
def test_error_message_clarity() -> None:
    """Test that error messages provide clear guidance for fixing identifiers.

    Validates that error messages:
        - Explain what's wrong with the identifier
        - Provide examples of valid formats
        - Are actionable (user knows how to fix the issue)

    Expected Result:
        PASS - Error messages are clear and actionable
    """
    # Test uppercase error message
    with pytest.raises(ValidationError) as exc_info:
        ProjectIdentifier(value="MyProject")

    error_msg = str(exc_info.value)
    assert "lowercase" in error_msg.lower()
    assert "alphanumeric" in error_msg.lower()

    # Verify examples provided in error message
    # (from ProjectIdentifier.validate_format docstring)
    assert any(
        example in error_msg for example in ["client-a", "example"]
    ) or "format" in error_msg.lower()


# ==============================================================================
# Module Exports
# ==============================================================================

__all__ = [
    "test_valid_identifiers",
    "test_invalid_identifiers",
    "test_edge_case_minimum_length",
    "test_edge_case_maximum_length",
    "test_edge_case_hyphen_placement",
    "test_schema_name_conversion_consistency",
    "test_error_message_clarity",
]
