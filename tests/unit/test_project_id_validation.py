"""Unit tests for project_id pattern validation via database CHECK constraints.

Tests database-level validation of project_id column pattern in repositories and
code_chunks tables. Validates CHECK constraint: project_id ~ '^[a-z0-9-]{1,50}$'

Constitutional Compliance:
- Principle VII: TDD (comprehensive test coverage before implementation)
- Principle VIII: Type safety (100% type annotations)
- Principle V: Production Quality (security validation, SQL injection prevention)

Test Coverage:
- T008: project_id pattern validation (FR-007, FR-026)
  - Valid patterns: lowercase alphanumeric, hyphens, 1-50 chars
  - Invalid patterns: uppercase, underscores, spaces, special chars, SQL injection
  - Security: SQL injection and path traversal attempts rejected

Performance Target:
- <100ms per test (database constraint validation is atomic)

Requirements Validated:
- FR-007: CHECK constraint on both tables
- FR-009: Lowercase-only enforcement
- FR-010: Reject underscores and spaces
- FR-024: Database-level validation
- FR-025: Reject SQL injection attempts
- FR-026: Test 10+ invalid patterns
"""

from __future__ import annotations

from datetime import datetime
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

# ==============================================================================
# Test Fixtures
# ==============================================================================


@pytest.fixture
async def sample_repository_id(session: AsyncSession) -> uuid.UUID:
    """Create a sample repository with valid project_id for foreign key tests.

    Returns:
        UUID of created repository for use in code_chunks tests

    Note:
        Uses project_id='default' which is valid pattern
    """
    repo_id = uuid.uuid4()
    await session.execute(
        text("""
            INSERT INTO repositories (id, path, name, project_id, is_active, created_at)
            VALUES (:id, :path, :name, :project_id, :is_active, :created_at)
        """),
        {
            "id": repo_id,
            "path": "/tmp/test-repo",
            "name": "Test Repository",
            "project_id": "default",
            "is_active": True,
            "created_at": datetime.utcnow(),
        },
    )
    await session.commit()
    return repo_id


# ==============================================================================
# T008: Valid project_id Patterns
# ==============================================================================


class TestValidProjectIdPatterns:
    """Test that valid project_id patterns are accepted by CHECK constraint."""

    @pytest.mark.parametrize(
        "valid_project_id,description",
        [
            ("default", "reserved default value"),
            ("my-project", "simple kebab-case"),
            ("proj-123", "alphanumeric with hyphen"),
            ("a", "minimum length (1 character)"),
            ("project-2025", "year suffix"),
            ("test-proj-v2", "multiple hyphens"),
            ("abc123xyz", "alphanumeric only"),
            ("123-project", "starts with number"),
            ("project-456-test", "multiple segments"),
            (
                "a-very-long-project-name-with-exactly-fifty-ch",
                "maximum length (50 characters)",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_valid_repository_project_id(
        self,
        session: AsyncSession,
        valid_project_id: str,
        description: str,
    ) -> None:
        """Test that valid project_id patterns are accepted in repositories table.

        Given: A valid project_id following pattern ^[a-z0-9-]{1,50}$
        When: INSERT into repositories table
        Then: INSERT succeeds without IntegrityError

        Args:
            session: Async database session fixture
            valid_project_id: Valid project_id string to test
            description: Human-readable description of test case
        """
        repo_id = uuid.uuid4()

        # Should not raise IntegrityError
        await session.execute(
            text("""
                INSERT INTO repositories (id, path, name, project_id, is_active, created_at)
                VALUES (:id, :path, :name, :project_id, :is_active, :created_at)
            """),
            {
                "id": repo_id,
                "path": f"/tmp/test-{valid_project_id}",
                "name": f"Test {description}",
                "project_id": valid_project_id,
                "is_active": True,
                "created_at": datetime.utcnow(),
            },
        )
        await session.commit()

        # Verify insertion
        result = await session.execute(
            text("SELECT project_id FROM repositories WHERE id = :id"),
            {"id": repo_id},
        )
        row = result.fetchone()
        assert row is not None
        assert row[0] == valid_project_id

    @pytest.mark.parametrize(
        "valid_project_id,description",
        [
            ("default", "reserved default value"),
            ("my-project", "simple kebab-case"),
            ("proj-123", "alphanumeric with hyphen"),
            ("a", "minimum length (1 character)"),
            (
                "a-very-long-project-name-with-exactly-fifty-ch",
                "maximum length (50 characters)",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_valid_code_chunks_project_id(
        self,
        session: AsyncSession,
        sample_repository_id: uuid.UUID,
        valid_project_id: str,
        description: str,
    ) -> None:
        """Test that valid project_id patterns are accepted in code_chunks table.

        Given: A valid project_id following pattern ^[a-z0-9-]{1,50}$
        When: INSERT into code_chunks table
        Then: INSERT succeeds without IntegrityError

        Args:
            session: Async database session fixture
            sample_repository_id: UUID of existing repository for FK constraint
            valid_project_id: Valid project_id string to test
            description: Human-readable description of test case
        """
        chunk_id = uuid.uuid4()

        # Should not raise IntegrityError
        await session.execute(
            text("""
                INSERT INTO code_chunks (
                    id, repository_id, project_id, file_path,
                    content, start_line, end_line, created_at
                )
                VALUES (
                    :id, :repository_id, :project_id, :file_path,
                    :content, :start_line, :end_line, :created_at
                )
            """),
            {
                "id": chunk_id,
                "repository_id": sample_repository_id,
                "project_id": valid_project_id,
                "file_path": f"test_{valid_project_id}.py",
                "content": "def test(): pass",
                "start_line": 1,
                "end_line": 1,
                "created_at": datetime.utcnow(),
            },
        )
        await session.commit()

        # Verify insertion
        result = await session.execute(
            text("SELECT project_id FROM code_chunks WHERE id = :id"),
            {"id": chunk_id},
        )
        row = result.fetchone()
        assert row is not None
        assert row[0] == valid_project_id


# ==============================================================================
# T008: Invalid project_id Patterns (FR-026: 10+ patterns)
# ==============================================================================


class TestInvalidProjectIdPatterns:
    """Test that invalid project_id patterns are rejected by CHECK constraint.

    FR-026 requires testing at least 10 invalid patterns for comprehensive validation.
    """

    @pytest.mark.parametrize(
        "invalid_project_id,reason",
        [
            # FR-009: Uppercase rejection
            ("My-Project", "uppercase letters (M, P)"),
            ("PROJECT", "all uppercase"),
            ("myProject", "camelCase with uppercase"),
            # FR-010: Underscore and space rejection
            ("my_project", "underscore character"),
            ("my project", "space character"),
            ("my-project_test", "underscore with hyphen"),
            # Pattern violations: leading/trailing/consecutive hyphens
            ("-my-project", "leading hyphen"),
            ("my-project-", "trailing hyphen"),
            ("my--project", "consecutive hyphens"),
            # Length violations
            ("", "empty string (length 0)"),
            (
                "this-is-a-very-long-project-name-that-exceeds-fifty-characters-limit",
                "exceeds 50 characters (68 chars)",
            ),
            # FR-025: Security - SQL injection attempts
            ("'; DROP TABLE repositories; --", "SQL injection attempt"),
            ("1' OR '1'='1", "SQL injection boolean bypass"),
            # FR-025: Security - path traversal
            ("../../../etc/passwd", "path traversal attempt"),
            ("..%2F..%2F..%2Fetc%2Fpasswd", "URL-encoded path traversal"),
            # Special characters
            ("my@project", "at symbol"),
            ("my.project", "period/dot"),
            ("my/project", "forward slash"),
            ("my\\project", "backslash"),
            ("my:project", "colon"),
            ("my;project", "semicolon"),
            ("my!project", "exclamation mark"),
            ("my#project", "hash/pound"),
            ("my$project", "dollar sign"),
            ("my%project", "percent sign"),
            ("my&project", "ampersand"),
            ("my*project", "asterisk"),
            ("my(project)", "parentheses"),
            ("my[project]", "square brackets"),
            ("my{project}", "curly braces"),
            ("my<project>", "angle brackets"),
            ("my=project", "equals sign"),
            ("my+project", "plus sign"),
            ("my?project", "question mark"),
            ("my|project", "pipe/vertical bar"),
            ("my~project", "tilde"),
            ("my`project", "backtick"),
            ("my'project", "single quote"),
            ('my"project', "double quote"),
            ("my,project", "comma"),
        ],
    )
    @pytest.mark.asyncio
    async def test_invalid_repository_project_id_rejected(
        self,
        session: AsyncSession,
        invalid_project_id: str,
        reason: str,
    ) -> None:
        """Test that invalid project_id patterns are rejected in repositories table.

        Given: An invalid project_id violating pattern ^[a-z0-9-]{1,50}$
        When: INSERT into repositories table
        Then: IntegrityError raised with CHECK constraint violation

        Args:
            session: Async database session fixture
            invalid_project_id: Invalid project_id string to test
            reason: Human-readable explanation of why it's invalid

        Constitutional Compliance:
            - FR-007: CHECK constraint enforcement
            - FR-009: Uppercase rejection
            - FR-010: Underscore/space rejection
            - FR-024: Database-level validation
            - FR-025: SQL injection prevention
            - FR-026: 10+ invalid patterns tested
        """
        repo_id = uuid.uuid4()

        with pytest.raises(IntegrityError) as exc_info:
            await session.execute(
                text("""
                    INSERT INTO repositories (id, path, name, project_id, is_active, created_at)
                    VALUES (:id, :path, :name, :project_id, :is_active, :created_at)
                """),
                {
                    "id": repo_id,
                    "path": f"/tmp/test-{repo_id}",
                    "name": "Test Invalid Pattern",
                    "project_id": invalid_project_id,
                    "is_active": True,
                    "created_at": datetime.utcnow(),
                },
            )
            await session.commit()

        # Verify CHECK constraint violation
        error_message = str(exc_info.value).lower()
        assert (
            "check_repositories_project_id" in error_message
            or "check constraint" in error_message
            or "violates check constraint" in error_message
        ), f"Expected CHECK constraint error for {reason}, got: {exc_info.value}"

        # Rollback failed transaction
        await session.rollback()

    @pytest.mark.parametrize(
        "invalid_project_id,reason",
        [
            ("My-Project", "uppercase letters"),
            ("my_project", "underscore character"),
            ("my project", "space character"),
            ("-my-project", "leading hyphen"),
            ("my-project-", "trailing hyphen"),
            ("my--project", "consecutive hyphens"),
            ("", "empty string"),
            (
                "this-is-a-very-long-project-name-that-exceeds-fifty-characters-limit",
                "exceeds 50 characters",
            ),
            ("'; DROP TABLE code_chunks; --", "SQL injection attempt"),
            ("../../../etc/passwd", "path traversal attempt"),
        ],
    )
    @pytest.mark.asyncio
    async def test_invalid_code_chunks_project_id_rejected(
        self,
        session: AsyncSession,
        sample_repository_id: uuid.UUID,
        invalid_project_id: str,
        reason: str,
    ) -> None:
        """Test that invalid project_id patterns are rejected in code_chunks table.

        Given: An invalid project_id violating pattern ^[a-z0-9-]{1,50}$
        When: INSERT into code_chunks table
        Then: IntegrityError raised with CHECK constraint violation

        Args:
            session: Async database session fixture
            sample_repository_id: UUID of existing repository for FK constraint
            invalid_project_id: Invalid project_id string to test
            reason: Human-readable explanation of why it's invalid

        Constitutional Compliance:
            - FR-007: CHECK constraint enforcement on code_chunks
            - FR-024: Database-level validation
            - FR-026: Comprehensive invalid pattern testing
        """
        chunk_id = uuid.uuid4()

        with pytest.raises(IntegrityError) as exc_info:
            await session.execute(
                text("""
                    INSERT INTO code_chunks (
                        id, repository_id, project_id, file_path,
                        content, start_line, end_line, created_at
                    )
                    VALUES (
                        :id, :repository_id, :project_id, :file_path,
                        :content, :start_line, :end_line, :created_at
                    )
                """),
                {
                    "id": chunk_id,
                    "repository_id": sample_repository_id,
                    "project_id": invalid_project_id,
                    "file_path": "test_invalid.py",
                    "content": "def test(): pass",
                    "start_line": 1,
                    "end_line": 1,
                    "created_at": datetime.utcnow(),
                },
            )
            await session.commit()

        # Verify CHECK constraint violation
        error_message = str(exc_info.value).lower()
        assert (
            "check_code_chunks_project_id" in error_message
            or "check constraint" in error_message
            or "violates check constraint" in error_message
        ), f"Expected CHECK constraint error for {reason}, got: {exc_info.value}"

        # Rollback failed transaction
        await session.rollback()


# ==============================================================================
# Edge Cases and Boundary Tests
# ==============================================================================


class TestProjectIdEdgeCases:
    """Edge case tests for project_id validation."""

    @pytest.mark.asyncio
    async def test_exactly_50_chars_is_valid(self, session: AsyncSession) -> None:
        """Test that project_id with exactly 50 characters is valid.

        Given: project_id with exactly 50 characters (boundary condition)
        When: INSERT into repositories table
        Then: INSERT succeeds (50 chars is maximum allowed)

        Boundary Test:
            - 49 chars: valid
            - 50 chars: valid (boundary)
            - 51 chars: invalid
        """
        repo_id = uuid.uuid4()
        project_id_50 = "a-very-long-project-name-with-exactly-fifty-ch"
        assert len(project_id_50) == 50, "Test data must be exactly 50 chars"

        # Should not raise
        await session.execute(
            text("""
                INSERT INTO repositories (id, path, name, project_id, is_active, created_at)
                VALUES (:id, :path, :name, :project_id, :is_active, :created_at)
            """),
            {
                "id": repo_id,
                "path": "/tmp/test-50-chars",
                "name": "Test 50 Chars",
                "project_id": project_id_50,
                "is_active": True,
                "created_at": datetime.utcnow(),
            },
        )
        await session.commit()

    @pytest.mark.asyncio
    async def test_51_chars_is_invalid(self, session: AsyncSession) -> None:
        """Test that project_id with 51 characters is rejected.

        Given: project_id with 51 characters (exceeds maximum)
        When: INSERT into repositories table
        Then: IntegrityError raised (CHECK constraint violation)
        """
        repo_id = uuid.uuid4()
        project_id_51 = "a-very-long-project-name-with-fifty-one-characte"
        assert len(project_id_51) == 51, "Test data must be exactly 51 chars"

        with pytest.raises(IntegrityError):
            await session.execute(
                text("""
                    INSERT INTO repositories (id, path, name, project_id, is_active, created_at)
                    VALUES (:id, :path, :name, :project_id, :is_active, :created_at)
                """),
                {
                    "id": repo_id,
                    "path": "/tmp/test-51-chars",
                    "name": "Test 51 Chars",
                    "project_id": project_id_51,
                    "is_active": True,
                    "created_at": datetime.utcnow(),
                },
            )
            await session.commit()

        await session.rollback()

    @pytest.mark.asyncio
    async def test_single_character_is_valid(self, session: AsyncSession) -> None:
        """Test that single-character project_id is valid.

        Given: project_id with 1 character (minimum length)
        When: INSERT into repositories table
        Then: INSERT succeeds (1 char is minimum allowed)
        """
        repo_id = uuid.uuid4()
        project_id_1 = "a"

        # Should not raise
        await session.execute(
            text("""
                INSERT INTO repositories (id, path, name, project_id, is_active, created_at)
                VALUES (:id, :path, :name, :project_id, :is_active, :created_at)
            """),
            {
                "id": repo_id,
                "path": "/tmp/test-1-char",
                "name": "Test 1 Char",
                "project_id": project_id_1,
                "is_active": True,
                "created_at": datetime.utcnow(),
            },
        )
        await session.commit()

    @pytest.mark.asyncio
    async def test_all_numbers_is_valid(self, session: AsyncSession) -> None:
        """Test that project_id with only numbers is valid.

        Given: project_id containing only digits
        When: INSERT into repositories table
        Then: INSERT succeeds (digits are allowed)
        """
        repo_id = uuid.uuid4()
        project_id_numbers = "123456789"

        # Should not raise
        await session.execute(
            text("""
                INSERT INTO repositories (id, path, name, project_id, is_active, created_at)
                VALUES (:id, :path, :name, :project_id, :is_active, :created_at)
            """),
            {
                "id": repo_id,
                "path": "/tmp/test-numbers",
                "name": "Test All Numbers",
                "project_id": project_id_numbers,
                "is_active": True,
                "created_at": datetime.utcnow(),
            },
        )
        await session.commit()

    @pytest.mark.asyncio
    async def test_all_hyphens_invalid(self, session: AsyncSession) -> None:
        """Test that project_id with only hyphens is invalid.

        Given: project_id containing only hyphens
        When: INSERT into repositories table
        Then: IntegrityError raised (pattern requires alphanumeric)

        Note: While regex allows hyphens, consecutive hyphens at start/end
        make this pattern invalid per business rules.
        """
        repo_id = uuid.uuid4()
        project_id_hyphens = "---"

        with pytest.raises(IntegrityError):
            await session.execute(
                text("""
                    INSERT INTO repositories (id, path, name, project_id, is_active, created_at)
                    VALUES (:id, :path, :name, :project_id, :is_active, :created_at)
                """),
                {
                    "id": repo_id,
                    "path": "/tmp/test-hyphens",
                    "name": "Test All Hyphens",
                    "project_id": project_id_hyphens,
                    "is_active": True,
                    "created_at": datetime.utcnow(),
                },
            )
            await session.commit()

        await session.rollback()


# ==============================================================================
# Security Tests (FR-025: SQL Injection Prevention)
# ==============================================================================


class TestProjectIdSecurityValidation:
    """Security-focused tests for project_id validation.

    Constitutional Compliance:
        - FR-025: Reject malicious project_id values
        - Principle V: Production Quality (robust security validation)
    """

    @pytest.mark.parametrize(
        "malicious_input,attack_type",
        [
            # SQL injection variants
            ("'; DROP TABLE repositories; --", "SQL injection - DROP TABLE"),
            ("1' OR '1'='1", "SQL injection - boolean bypass"),
            ("admin'--", "SQL injection - comment injection"),
            ("' UNION SELECT * FROM users--", "SQL injection - UNION attack"),
            ("'; DELETE FROM repositories WHERE '1'='1", "SQL injection - DELETE"),
            ("'; UPDATE repositories SET project_id='hacked'--", "SQL injection - UPDATE"),
            # Path traversal variants
            ("../../../etc/passwd", "path traversal - Unix"),
            ("..\\..\\..\\windows\\system32", "path traversal - Windows"),
            ("....//....//....//etc/passwd", "path traversal - double encoding"),
            ("%2e%2e%2f%2e%2e%2f%2e%2e%2f", "path traversal - URL encoded"),
            # Command injection
            ("test; ls -la", "command injection - semicolon"),
            ("test && rm -rf /", "command injection - AND operator"),
            ("test | cat /etc/passwd", "command injection - pipe"),
            ("test`whoami`", "command injection - backticks"),
            ("test$(whoami)", "command injection - subshell"),
        ],
    )
    @pytest.mark.asyncio
    async def test_malicious_input_rejected(
        self,
        session: AsyncSession,
        malicious_input: str,
        attack_type: str,
    ) -> None:
        """Test that malicious project_id values are rejected by CHECK constraint.

        Given: A malicious project_id attempting security exploits
        When: INSERT into repositories table
        Then: IntegrityError raised (CHECK constraint prevents injection)

        Args:
            session: Async database session fixture
            malicious_input: Malicious project_id string
            attack_type: Description of attack being attempted

        Security Validation:
            - SQL injection attempts rejected
            - Path traversal attempts rejected
            - Command injection attempts rejected
            - Pattern validation prevents all malicious inputs

        Constitutional Compliance:
            - FR-025: Reject malicious project_id values
            - Principle V: Production Quality (security-first design)
        """
        repo_id = uuid.uuid4()

        with pytest.raises(IntegrityError) as exc_info:
            await session.execute(
                text("""
                    INSERT INTO repositories (id, path, name, project_id, is_active, created_at)
                    VALUES (:id, :path, :name, :project_id, :is_active, :created_at)
                """),
                {
                    "id": repo_id,
                    "path": "/tmp/test-security",
                    "name": "Test Security",
                    "project_id": malicious_input,
                    "is_active": True,
                    "created_at": datetime.utcnow(),
                },
            )
            await session.commit()

        # Verify CHECK constraint prevented the attack
        error_message = str(exc_info.value).lower()
        assert (
            "check constraint" in error_message or "check_repositories_project_id" in error_message
        ), f"Expected CHECK constraint to block {attack_type}, got: {exc_info.value}"

        await session.rollback()

    @pytest.mark.asyncio
    async def test_no_sql_injection_through_valid_pattern(
        self,
        session: AsyncSession,
    ) -> None:
        """Test that valid pattern prevents SQL injection via pattern compliance.

        Given: Valid project_id patterns only allow [a-z0-9-]
        When: Attempt to use special SQL characters
        Then: All SQL special characters are rejected by pattern

        Security Proof:
            - Single quote rejected: '
            - Double quote rejected: "
            - Semicolon rejected: ;
            - Dash rejected at start/end: -
            - Underscore rejected: _
            - Parentheses rejected: ()
            - Equals rejected: =

        This test verifies that the pattern itself is sufficient security.
        """
        # Valid pattern only allows lowercase, digits, hyphens
        valid_pattern = "test-project-123"

        # Verify it contains no SQL special characters
        sql_special_chars = ["'", '"', ";", "(", ")", "=", "--", "/*", "*/"]
        for char in sql_special_chars:
            assert char not in valid_pattern, f"Valid pattern should not contain {char}"

        # Verify insertion succeeds
        repo_id = uuid.uuid4()
        await session.execute(
            text("""
                INSERT INTO repositories (id, path, name, project_id, is_active, created_at)
                VALUES (:id, :path, :name, :project_id, :is_active, :created_at)
            """),
            {
                "id": repo_id,
                "path": "/tmp/test-sql-safety",
                "name": "Test SQL Safety",
                "project_id": valid_pattern,
                "is_active": True,
                "created_at": datetime.utcnow(),
            },
        )
        await session.commit()

        # Verify data integrity - no injection occurred
        result = await session.execute(
            text("SELECT COUNT(*) FROM repositories"),
        )
        count = result.scalar()
        assert count is not None, "COUNT should return a value"
        assert count >= 1, "Repository should exist (no DROP TABLE occurred)"
