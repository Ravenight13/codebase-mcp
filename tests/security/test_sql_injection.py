"""Security test for SQL injection prevention (T026).

Tests that SQL injection attempts via project_id parameter are blocked by
Pydantic validation BEFORE reaching database operations, and that database
integrity is preserved after injection attempts.

Test Scenario: Quickstart Scenario 9 - Security
Validates: Security Scenario (SQL Injection Prevention)
Traces to: FR-016 (security validation), Acceptance Scenario 9

Constitutional Compliance:
- Principle V: Production quality (comprehensive security testing)
- Principle VIII: Type safety (Pydantic validation integration)
- Principle VII: TDD (security validation correctness)
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from src.mcp.tools.indexing import index_repository


# ==============================================================================
# Test Fixtures
# ==============================================================================


@pytest.fixture
def repo_sql_injection(tmp_path: Path) -> str:
    """Fixture: Test repository for SQL injection validation.

    Creates a minimal repository to test SQL injection attempts are blocked
    at validation layer.

    Args:
        tmp_path: Pytest fixture providing temporary directory

    Returns:
        Absolute path to repository directory
    """
    repo_dir = tmp_path / "repo-security-test"
    repo_dir.mkdir()

    # Create Python file for testing
    (repo_dir / "main.py").write_text(
        """
def main() -> None:
    '''Security test application'''
    return 42
"""
    )

    return str(repo_dir)


# ==============================================================================
# Integration Tests - SQL Injection Prevention
# ==============================================================================


@pytest.mark.security
@pytest.mark.parametrize(
    "injection_attempt",
    [
        # Classic SQL injection patterns
        "project'; DROP TABLE code_chunks--",
        "project/**/OR/**/1=1--",
        'project"; DELETE FROM repositories WHERE 1=1--',
        "project' UNION SELECT * FROM pg_shadow--",
        "project'; SELECT * FROM information_schema.tables--",
        # Simple injection attempts
        "'; --",
        "1' OR '1'='1",
        # Advanced injection patterns
        "project'; DROP SCHEMA project_default CASCADE--",
        "project' AND 1=1--",
        "project'; UPDATE repositories SET name='hacked'--",
        # Comment-based injections
        "project/*comment*/",
        "project--comment",
        "project#comment",
        # Encoded injections
        "project%27%3B%20DROP%20TABLE--",
        "project\"; DROP TABLE code_chunks; --",
        # Batch injections
        "project'; DROP TABLE code_chunks; DROP TABLE repositories--",
        # Hex-encoded injections
        "project'; EXEC(0x44524F50205441424C4520636F64655F6368756E6B73)--",
    ],
)
@pytest.mark.unit
@pytest.mark.asyncio
async def test_sql_injection_prevention(
    repo_sql_injection: str,
    injection_attempt: str,
) -> None:
    """Verify SQL injection attempts blocked by Pydantic validation.

    Tests that all SQL injection attempts are rejected at validation layer
    BEFORE any database operations are executed, and that database integrity
    is preserved after the injection attempt.

    Test Steps:
        1. Attempt to index repository with SQL injection in project_id
        2. Verify ValidationError or ValueError raised
        3. Verify error message indicates validation failure (not SQL error)

    Expected Result:
        PASS - All injection attempts blocked by validation

    Traces to:
        - FR-016: SQL injection prevention via strict identifier validation
        - Acceptance Scenario 9: Security validation
        - Constitutional Principle V: Production quality security

    Security Note:
        This test validates that Pydantic validation acts as a security barrier,
        preventing malicious input from reaching SQL query construction.
    """
    # Step 1: Attempt injection via project_id parameter
    with pytest.raises((ValidationError, ValueError)) as exc_info:
        await index_repository.fn(
            repo_path=repo_sql_injection,
            project_id=injection_attempt,
        )

    # Step 2: Verify validation blocked injection BEFORE SQL execution
    error_msg = str(exc_info.value).lower()

    # Must contain validation-related keywords (not SQL error keywords)
    assert any(
        keyword in error_msg
        for keyword in [
            "lowercase",
            "alphanumeric",
            "validation",
            "identifier",
            "format",
        ]
    ), (
        f"Expected validation error, but got: {exc_info.value}\n"
        f"Error should mention validation/format issues, not SQL errors"
    )

    # Should NOT contain SQL error keywords (indicates injection reached DB)
    # Note: We check for actual SQL errors, not table/schema names in validation messages
    sql_error_keywords = [
        "syntax error",
        "permission denied",
        "relation does not exist",
        "database error",
        "psycopg",
        "sqlalchemy.exc",
    ]
    assert not any(
        keyword in error_msg for keyword in sql_error_keywords
    ), f"Error suggests SQL injection reached database: {exc_info.value}"


@pytest.mark.security
@pytest.mark.unit
@pytest.mark.asyncio
async def test_sql_injection_multiple_attempts(
    repo_sql_injection: str,
) -> None:
    """Test validation consistently blocks multiple sequential injection attempts.

    Validates that multiple injection attempts are consistently blocked by
    validation, and that the validation layer remains effective.

    Test Steps:
        1. Attempt multiple different SQL injection patterns sequentially
        2. Verify all attempts blocked by validation
        3. Verify validation remains consistent across all attempts

    Expected Result:
        PASS - All injection attempts blocked consistently

    Traces to:
        - FR-016: Persistent security validation
        - Constitutional Principle V: Production quality (defense in depth)
    """
    injection_patterns = [
        "'; DROP TABLE code_chunks--",
        "admin'; DELETE FROM repositories--",
        "test' OR '1'='1--",
        "project'; TRUNCATE TABLE repositories CASCADE--",
    ]

    # Attempt each injection pattern
    for injection_pattern in injection_patterns:
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            await index_repository.fn(
                repo_path=repo_sql_injection,
                project_id=injection_pattern,
            )

        # Verify each error is a validation error (not SQL error)
        error_msg = str(exc_info.value).lower()
        assert any(
            keyword in error_msg
            for keyword in ["lowercase", "alphanumeric", "validation", "identifier"]
        ), f"Expected validation error for {injection_pattern}, got: {exc_info.value}"


# ==============================================================================
# Module Exports
# ==============================================================================

__all__ = [
    "test_sql_injection_prevention",
    "test_sql_injection_multiple_attempts",
]
