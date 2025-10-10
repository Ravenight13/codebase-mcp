"""Custom SQLAlchemy type decorators for JSONB validation.

This module provides custom type decorators for SQLAlchemy that integrate
Pydantic validation with PostgreSQL JSONB columns.

Constitutional Compliance:
- Principle V: Production quality (comprehensive validation and error handling)
- Principle VIII: Type safety (full type annotations, Pydantic integration)
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ValidationError
from sqlalchemy import JSON, TypeDecorator

# Generic type variable for Pydantic models
T = TypeVar("T", bound=BaseModel)


class PydanticJSON(TypeDecorator[T], Generic[T]):
    """SQLAlchemy TypeDecorator for Pydantic-validated JSONB columns.

    This type decorator automatically validates JSONB data using Pydantic models
    on both write (process_bind_param) and read (process_result_value) operations.

    Type Parameters:
        T: Pydantic BaseModel subclass used for validation

    Usage:
        >>> from pydantic import BaseModel, Field
        >>> class MyMetadata(BaseModel):
        ...     value: int = Field(ge=0)
        ...     name: str = Field(min_length=1)
        >>>
        >>> class MyModel(Base):
        ...     __tablename__ = "my_table"
        ...     metadata_: Mapped[MyMetadata] = mapped_column(
        ...         "metadata",
        ...         PydanticJSON(MyMetadata),
        ...         nullable=False
        ...     )

    Validation:
        - On write: Validates Python dict/model → JSONB
        - On read: Validates JSONB → Pydantic model instance
        - Raises ValidationError if validation fails

    Performance:
        - Validation occurs at ORM boundaries (not on every access)
        - cache_ok=True enables SQLAlchemy query caching
    """

    impl = JSON
    cache_ok = True

    def __init__(self, pydantic_model: type[T]) -> None:
        """Initialize PydanticJSON type decorator.

        Args:
            pydantic_model: Pydantic BaseModel subclass for validation
        """
        self.pydantic_model = pydantic_model
        super().__init__()

    def process_bind_param(self, value: T | dict[str, Any] | None, dialect: Any) -> dict[str, Any] | None:
        """Validate and serialize value for database storage.

        Args:
            value: Pydantic model instance or dict to validate
            dialect: SQLAlchemy dialect (unused)

        Returns:
            JSON-serializable dict for JSONB storage, or None

        Raises:
            ValidationError: If value fails Pydantic validation
        """
        if value is None:
            return None

        # If already a Pydantic model instance, validate and serialize
        if isinstance(value, BaseModel):
            validated = self.pydantic_model.model_validate(value.model_dump())
            return validated.model_dump(mode="json")

        # If dict, validate and serialize
        validated = self.pydantic_model.model_validate(value)
        return validated.model_dump(mode="json")

    def process_result_value(self, value: dict[str, Any] | None, dialect: Any) -> T | None:
        """Deserialize and validate value from database.

        Args:
            value: JSONB data from database
            dialect: SQLAlchemy dialect (unused)

        Returns:
            Validated Pydantic model instance, or None

        Raises:
            ValidationError: If value fails Pydantic validation
        """
        if value is None:
            return None

        # Deserialize JSONB → Pydantic model with validation
        return self.pydantic_model.model_validate(value)
