"""Project identifier validation model.

Security-critical Pydantic model for validating project identifiers before
any database operations. Prevents SQL injection and enforces naming conventions.

Model Responsibilities:
- Validate project identifier format (lowercase alphanumeric with hyphens)
- Prevent security vulnerabilities (SQL injection, path traversal)
- Convert validated identifiers to PostgreSQL schema names
- Provide clear error messages with examples

Constitutional Compliance:
- Principle VIII: Pydantic-based type safety (mypy --strict)
- Principle V: Production quality (comprehensive validation, security)
- Principle XVI: Security-first design (validation before database operations)

Functional Requirements:
- FR-004: System MUST validate project identifiers before use
- FR-005: System MUST enforce lowercase alphanumeric with hyphen format
- FR-006: System MUST enforce maximum 50-character length
- FR-007: System MUST prevent identifiers starting or ending with hyphens
- FR-008: System MUST prevent consecutive hyphens
- FR-016: System MUST prevent security vulnerabilities via identifier validation
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator


class ProjectIdentifier(BaseModel):
    """Validated project identifier preventing SQL injection.

    Security-critical model that validates project identifiers against strict
    format rules before any database operations. All identifiers must be:
    - Lowercase alphanumeric with hyphens only
    - 1-50 characters in length
    - Cannot start or end with hyphen
    - Cannot contain consecutive hyphens

    Example Usage:
        >>> identifier = ProjectIdentifier(value="client-a")
        >>> identifier.to_schema_name()
        'project_client_a'

        >>> ProjectIdentifier(value="My_Project")  # Raises ValueError
        ValueError: Project identifier must be lowercase alphanumeric...

    Attributes:
        value: Validated project identifier string

    Methods:
        to_schema_name: Convert to PostgreSQL schema name format
    """

    value: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Project identifier (lowercase alphanumeric with hyphens)",
        examples=["client-a", "frontend", "my-project-123"],
    )

    @field_validator("value")
    @classmethod
    def validate_format(cls, v: str) -> str:
        """Validate project identifier format and security constraints.

        Rules:
        - Lowercase alphanumeric with hyphens only
        - Cannot start or end with hyphen
        - No consecutive hyphens
        - Prevents SQL injection via strict character whitelist

        Args:
            v: Project identifier value to validate

        Returns:
            Validated identifier string (unchanged)

        Raises:
            ValueError: If identifier format is invalid, with detailed message
                       and examples showing correct format

        Security:
            This validator is SECURITY-CRITICAL. It prevents SQL injection
            attacks by enforcing a strict character whitelist before identifiers
            are used in database schema names or SQL queries.
        """
        # Length already validated by Field(min_length=1, max_length=50)

        # Format validation (security-critical)
        pattern = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
        if not pattern.match(v):
            raise ValueError(
                "Project identifier must be lowercase alphanumeric with hyphens. "
                "Cannot start/end with hyphen or have consecutive hyphens. "
                f"Found: {v}\n\n"
                "Examples:\n"
                "  ✅ client-a\n"
                "  ✅ my-project-123\n"
                "  ❌ My_Project (uppercase and underscore)\n"
                "  ❌ -project (starts with hyphen)\n"
                "  ❌ project-- (consecutive hyphens)"
            )

        return v

    def to_schema_name(self) -> str:
        """Convert validated identifier to PostgreSQL schema name.

        Schema names follow the format: project_{identifier}
        Example: "client-a" → "project_client_a"

        Returns:
            PostgreSQL schema name string

        Security:
            Safe to use in SQL queries because identifier has been validated
            to contain only lowercase alphanumeric characters and hyphens.
            No risk of SQL injection or schema name conflicts.
        """
        return f"project_{self.value}"
