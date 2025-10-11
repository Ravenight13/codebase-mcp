"""JSONB Pydantic validation service for type-safe metadata storage.

Provides validation functions for all JSONB columns in the database-backed
project tracking system. Uses Pydantic models from contracts/pydantic-schemas.py
to ensure type safety and field-level validation before database writes.

Constitutional Compliance:
- Principle V: Production quality (comprehensive error handling, field-level details)
- Principle VIII: Type safety (100% type annotations, mypy --strict)

Key Features:
- Validates VendorMetadata (format_support, test_results, version, compliance)
- Validates DeploymentMetadata (PR details, commit hash, test summary)
- Validates WorkItemMetadata (polymorphic based on item_type)
- Validates vendor name format and constraints (FR-012)
- Validates vendor creation metadata with flexible schema
- Returns detailed ValidationError with field-level error messages
- Type-safe validation with complete Pydantic integration

Performance:
- <1ms validation time for typical metadata structures
- No database I/O (pure Pydantic validation)
"""

from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Union

from pydantic import ValidationError as PydanticValidationError

from src.mcp.mcp_logging import get_logger

# ==============================================================================
# Import Pydantic Schemas from Contracts
# ==============================================================================

# Add specs/003-database-backed-project/contracts to Python path
specs_contracts_path = (
    Path(__file__).parent.parent.parent
    / "specs"
    / "003-database-backed-project"
    / "contracts"
)
if specs_contracts_path.exists() and str(specs_contracts_path) not in sys.path:
    sys.path.insert(0, str(specs_contracts_path))

try:
    from pydantic_schemas import (  # type: ignore
        DeploymentMetadata,
        ItemType,
        ProjectMetadata,
        ResearchMetadata,
        SessionMetadata,
        TaskMetadata,
        VendorMetadata,
    )
except ImportError as e:
    raise ImportError(
        f"Failed to import Pydantic schemas from {specs_contracts_path}. "
        f"Ensure contracts/pydantic-schemas.py exists and is valid. Error: {e}"
    ) from e

# ==============================================================================
# Type Aliases
# ==============================================================================

logger = get_logger(__name__)

# Union type for all work item metadata types
WorkItemMetadata = Union[
    ProjectMetadata,
    SessionMetadata,
    TaskMetadata,
    ResearchMetadata,
]

# ==============================================================================
# Constants
# ==============================================================================

# Vendor name validation pattern: alphanumeric, spaces, hyphens, underscores only
VENDOR_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9 \-_]+$')

# ==============================================================================
# Exception Classes
# ==============================================================================


class ValidationError(Exception):
    """Custom validation error with field-level details.

    Raised when Pydantic validation fails for JSONB metadata.
    Provides detailed error messages for client-side rendering.

    Attributes:
        errors: List of validation error dictionaries from Pydantic
        field_errors: Mapping of field names to error messages
        raw_data: Original input data that failed validation

    HTTP Mapping:
        400 Bad Request - Invalid input data
    """

    def __init__(
        self,
        *,
        errors: list[dict[str, Any]],
        field_errors: dict[str, str],
        raw_data: dict[str, Any],
    ) -> None:
        """Initialize ValidationError with detailed field-level errors.

        Args:
            errors: Pydantic validation errors (from exc.errors())
            field_errors: Simplified mapping of field -> error message
            raw_data: Original input data that failed validation
        """
        self.errors = errors
        self.field_errors = field_errors
        self.raw_data = raw_data

        # Construct human-readable error message
        error_summary = ", ".join(
            f"{field}: {msg}" for field, msg in field_errors.items()
        )
        message = f"Validation failed: {error_summary}"
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for MCP error responses.

        Returns:
            Dictionary with validation errors for JSON serialization
        """
        return {
            "error_type": "ValidationError",
            "errors": self.errors,
            "field_errors": self.field_errors,
            "http_status": 400,
        }


# ==============================================================================
# Validation Functions
# ==============================================================================


def validate_vendor_name(name: str) -> None:
    """Validate vendor name format and constraints per FR-012.

    Validates that vendor name:
    - Is not empty or whitespace-only
    - Has length between 1-100 characters
    - Contains only alphanumeric characters, spaces, hyphens, and underscores

    Args:
        name: Vendor name to validate

    Raises:
        ValueError: If validation fails with descriptive error message

    Example:
        >>> validate_vendor_name("Acme Corp")  # Valid
        >>> validate_vendor_name("Acme-Corp_123")  # Valid
        >>> validate_vendor_name("")  # Raises ValueError
        >>> validate_vendor_name("Acme@Corp")  # Raises ValueError (invalid char)

    Performance:
        <1ms for typical vendor names
    """
    if not name or not name.strip():
        raise ValueError("Vendor name cannot be empty")

    if len(name) < 1 or len(name) > 100:
        raise ValueError(f"Vendor name must be 1-100 characters, got {len(name)}")

    if not VENDOR_NAME_PATTERN.match(name):
        raise ValueError(
            "Vendor name must contain only alphanumeric characters, "
            "spaces, hyphens, and underscores"
        )


def validate_create_vendor_metadata(
    metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    """Validate vendor creation metadata with flexible schema.

    Validates known fields if present, allows unknown fields without validation.
    This provides a flexible schema for vendor creation metadata.

    Known fields (validated if present):
    - scaffolder_version: Must be string
    - created_at: Must be ISO 8601 format string

    Unknown fields: Passed through without validation

    Args:
        metadata: Optional metadata dictionary from create_vendor tool

    Returns:
        Validated metadata dictionary (empty dict if input is None)

    Raises:
        ValueError: If known fields fail validation

    Example:
        >>> validate_create_vendor_metadata(None)
        {}
        >>> validate_create_vendor_metadata({"scaffolder_version": "1.0.0"})
        {"scaffolder_version": "1.0.0"}
        >>> validate_create_vendor_metadata({"custom_field": "value"})
        {"custom_field": "value"}
        >>> validate_create_vendor_metadata({"created_at": "2025-10-11T12:00:00Z"})
        {"created_at": "2025-10-11T12:00:00Z"}

    Performance:
        <1ms for typical metadata structures
    """
    if metadata is None:
        return {}

    validated: dict[str, Any] = {}

    # Validate scaffolder_version if present
    if "scaffolder_version" in metadata:
        if not isinstance(metadata["scaffolder_version"], str):
            raise ValueError("scaffolder_version must be string")
        validated["scaffolder_version"] = metadata["scaffolder_version"]

    # Validate created_at if present (ISO 8601 format)
    if "created_at" in metadata:
        if not isinstance(metadata["created_at"], str):
            raise ValueError("created_at must be ISO 8601 string")
        try:
            datetime.fromisoformat(metadata["created_at"])
        except ValueError as e:
            raise ValueError("created_at must be valid ISO 8601 format") from e
        validated["created_at"] = metadata["created_at"]

    # Copy unknown fields without validation (flexible schema)
    for key, value in metadata.items():
        if key not in validated:
            validated[key] = value

    return validated


def validate_vendor_metadata(metadata: dict[str, Any]) -> VendorMetadata:
    """Validate vendor metadata JSONB structure.

    Validates format support flags, test results, extractor version,
    and manifest compliance status using VendorMetadata Pydantic model.

    Args:
        metadata: Raw dictionary from JSONB column or MCP tool input

    Returns:
        Validated VendorMetadata instance

    Raises:
        ValidationError: Field-level validation failures with detailed messages

    Example:
        >>> metadata = {
        ...     "format_support": {"excel": True, "csv": True, "pdf": False, "ocr": False},
        ...     "test_results": {"passing": 45, "total": 50, "skipped": 5},
        ...     "extractor_version": "2.3.1",
        ...     "manifest_compliant": True
        ... }
        >>> validated = validate_vendor_metadata(metadata)
        >>> assert validated.test_results["passing"] <= validated.test_results["total"]

    Performance:
        <1ms for typical vendor metadata structures
    """
    logger.debug(
        "Validating vendor metadata",
        extra={
            "context": {
                "metadata_keys": list(metadata.keys()),
            }
        },
    )

    try:
        validated = VendorMetadata.model_validate(metadata)
        logger.debug(
            "Vendor metadata validation succeeded",
            extra={
                "context": {
                    "extractor_version": validated.extractor_version,
                    "manifest_compliant": validated.manifest_compliant,
                }
            },
        )
        return validated

    except PydanticValidationError as e:
        # Extract field-level errors for client-friendly response
        field_errors: dict[str, str] = {}
        for error in e.errors():
            field_path = ".".join(str(loc) for loc in error["loc"])
            field_errors[field_path] = error["msg"]

        logger.warning(
            "Vendor metadata validation failed",
            extra={
                "context": {
                    "field_errors": field_errors,
                    "raw_metadata_keys": list(metadata.keys()),
                }
            },
        )

        raise ValidationError(
            errors=[dict(error) for error in e.errors()],
            field_errors=field_errors,
            raw_data=metadata,
        ) from e


def validate_deployment_metadata(metadata: dict[str, Any]) -> DeploymentMetadata:
    """Validate deployment metadata JSONB structure.

    Validates PR number, title, commit hash format, test results,
    and constitutional compliance flag using DeploymentMetadata Pydantic model.

    Args:
        metadata: Raw dictionary from JSONB column or MCP tool input

    Returns:
        Validated DeploymentMetadata instance

    Raises:
        ValidationError: Field-level validation failures with detailed messages

    Example:
        >>> metadata = {
        ...     "pr_number": 123,
        ...     "pr_title": "feat(indexer): add tree-sitter AST parsing",
        ...     "commit_hash": "84b04732a1f5e9c8d3b2a0e6f7c8d9e0a1b2c3d4",
        ...     "test_summary": {"unit": 150, "integration": 30},
        ...     "constitutional_compliance": True
        ... }
        >>> validated = validate_deployment_metadata(metadata)
        >>> assert len(validated.commit_hash) == 40

    Performance:
        <1ms for typical deployment metadata structures
    """
    logger.debug(
        "Validating deployment metadata",
        extra={
            "context": {
                "metadata_keys": list(metadata.keys()),
                "pr_number": metadata.get("pr_number"),
            }
        },
    )

    try:
        validated = DeploymentMetadata.model_validate(metadata)
        logger.debug(
            "Deployment metadata validation succeeded",
            extra={
                "context": {
                    "pr_number": validated.pr_number,
                    "commit_hash": validated.commit_hash[:8],
                    "constitutional_compliance": validated.constitutional_compliance,
                }
            },
        )
        return validated

    except PydanticValidationError as e:
        # Extract field-level errors for client-friendly response
        field_errors: dict[str, str] = {}
        for error in e.errors():
            field_path = ".".join(str(loc) for loc in error["loc"])
            field_errors[field_path] = error["msg"]

        logger.warning(
            "Deployment metadata validation failed",
            extra={
                "context": {
                    "field_errors": field_errors,
                    "raw_metadata_keys": list(metadata.keys()),
                }
            },
        )

        raise ValidationError(
            errors=[dict(error) for error in e.errors()],
            field_errors=field_errors,
            raw_data=metadata,
        ) from e


def validate_work_item_metadata(
    item_type: ItemType,
    metadata: dict[str, Any],
) -> WorkItemMetadata:
    """Validate work item metadata JSONB structure based on item_type.

    Validates polymorphic metadata structures using type-specific Pydantic models:
    - project: ProjectMetadata (description, target_quarter, constitutional_principles)
    - session: SessionMetadata (token_budget, prompts_count, yaml_frontmatter)
    - task: TaskMetadata (estimated_hours, actual_hours, blocked_reason)
    - research: ResearchMetadata (research_questions, findings_summary, references)

    Args:
        item_type: Work item type discriminator (project|session|task|research)
        metadata: Raw dictionary from JSONB column or MCP tool input

    Returns:
        Validated WorkItemMetadata instance (correct subtype based on item_type)

    Raises:
        ValidationError: Field-level validation failures with detailed messages
        ValueError: Invalid or unsupported item_type

    Example:
        >>> metadata = {
        ...     "description": "Add semantic search to MCP server",
        ...     "target_quarter": "2025-Q1",
        ...     "constitutional_principles": ["Simplicity Over Features"]
        ... }
        >>> validated = validate_work_item_metadata(ItemType.PROJECT, metadata)
        >>> assert isinstance(validated, ProjectMetadata)

    Performance:
        <1ms for typical work item metadata structures
    """
    logger.debug(
        "Validating work item metadata",
        extra={
            "context": {
                "item_type": item_type.value,
                "metadata_keys": list(metadata.keys()),
            }
        },
    )

    # Map item_type to appropriate Pydantic model
    model_map = {
        ItemType.PROJECT: ProjectMetadata,
        ItemType.SESSION: SessionMetadata,
        ItemType.TASK: TaskMetadata,
        ItemType.RESEARCH: ResearchMetadata,
    }

    if item_type not in model_map:
        raise ValueError(
            f"Invalid item_type: {item_type}. Must be one of {list(model_map.keys())}"
        )

    model_class = model_map[item_type]

    try:
        validated = model_class.model_validate(metadata)
        logger.debug(
            f"Work item metadata validation succeeded for {item_type.value}",
            extra={
                "context": {
                    "item_type": item_type.value,
                    "model_class": model_class.__name__,
                }
            },
        )
        return validated

    except PydanticValidationError as e:
        # Extract field-level errors for client-friendly response
        field_errors: dict[str, str] = {}
        for error in e.errors():
            field_path = ".".join(str(loc) for loc in error["loc"])
            field_errors[field_path] = error["msg"]

        logger.warning(
            f"Work item metadata validation failed for {item_type.value}",
            extra={
                "context": {
                    "item_type": item_type.value,
                    "field_errors": field_errors,
                    "raw_metadata_keys": list(metadata.keys()),
                }
            },
        )

        raise ValidationError(
            errors=[dict(error) for error in e.errors()],
            field_errors=field_errors,
            raw_data=metadata,
        ) from e


# ==============================================================================
# Public API
# ==============================================================================

__all__ = [
    "ValidationError",
    "validate_vendor_name",
    "validate_create_vendor_metadata",
    "validate_vendor_metadata",
    "validate_deployment_metadata",
    "validate_work_item_metadata",
]
