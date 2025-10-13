"""Repository model and schemas.

Represents a code repository being indexed by the MCP server.

Entity Responsibilities:
- Track repository metadata (path, name, last indexed time)
- Maintain active/inactive status for indexing control
- One-to-many relationship with CodeFile entities

Constitutional Compliance:
- Principle V: Production quality (unique constraints, proper indexes)
- Principle VIII: Type safety (full Mapped[] annotations, Pydantic validation)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field
from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

if TYPE_CHECKING:
    from .code_file import CodeFile
    from .analytics import ChangeEvent


class Repository(Base):
    """SQLAlchemy model for code repositories.

    Table: repositories

    Relationships:
        - code_files: One-to-many with CodeFile (cascade delete)
        - change_events: One-to-many with ChangeEvent (analytics)

    Constraints:
        - path: Unique index for fast lookups
        - id: Primary key (UUID)

    State Management:
        - is_active: Controls whether repository is included in indexing
        - last_indexed_at: Timestamp of most recent successful indexing run
    """

    __tablename__ = "repositories"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Core fields
    path: Mapped[str] = mapped_column(
        String, unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)

    # Indexing metadata
    last_indexed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    code_files: Mapped[list[CodeFile]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )
    change_events: Mapped[list["ChangeEvent"]] = relationship(
        back_populates="repository"
    )


# Pydantic Schemas


class RepositoryCreate(BaseModel):
    """Schema for creating a new repository.

    Validation:
        - path: Must be absolute path to repository
        - name: Display name for UI/API responses
    """

    path: str = Field(..., description="Absolute path to repository")
    name: str = Field(..., description="Repository display name")

    model_config = {"from_attributes": True}


class RepositoryResponse(BaseModel):
    """Schema for repository API responses.

    Includes:
        - All core repository fields
        - file_count: Computed count of indexed files (not from DB)

    Usage:
        Used in GET /repositories and GET /repositories/{id} endpoints
    """

    id: uuid.UUID
    path: str
    name: str
    last_indexed_at: datetime | None
    is_active: bool
    created_at: datetime
    file_count: int = Field(0, description="Number of indexed files")

    model_config = {"from_attributes": True}
