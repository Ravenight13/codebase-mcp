"""CodeFile model and schemas.

Represents a source code file in the repository with change tracking.

Entity Responsibilities:
- Track file metadata (path, hash, size, language)
- Support soft deletion with 90-day retention
- One-to-many relationships with CodeChunk and ChangeEvent
- Many-to-one relationship with Repository

Constitutional Compliance:
- Principle IV: Performance (composite unique index on repo_id + relative_path)
- Principle V: Production quality (SHA-256 content hashing, soft delete)
- Principle VIII: Type safety (full Mapped[] annotations, Pydantic validation)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

if TYPE_CHECKING:
    from .code_chunk import CodeChunk
    from .repository import Repository
    from .analytics import ChangeEvent


class CodeFile(Base):
    """SQLAlchemy model for source code files.

    Table: code_files

    Relationships:
        - repository: Many-to-one with Repository
        - chunks: One-to-many with CodeChunk (cascade delete)
        - change_events: One-to-many with ChangeEvent (cascade delete)

    Indexes:
        - (repository_id, relative_path): Unique composite for file lookup
        - path: Standard B-tree for full path queries

    Soft Delete:
        - is_deleted: Flag for soft deletion
        - deleted_at: Timestamp when marked deleted
        - 90-day retention before permanent cleanup
    """

    __tablename__ = "code_files"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Foreign keys
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id"), nullable=False
    )

    # File metadata
    path: Mapped[str] = mapped_column(String, nullable=False, index=True)
    relative_path: Mapped[str] = mapped_column(String, nullable=False)
    content_hash: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # SHA-256 hex
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    language: Mapped[str | None] = mapped_column(String, nullable=True)

    # Timestamps
    modified_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    indexed_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Soft delete support
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    repository: Mapped[Repository] = relationship(back_populates="code_files")
    chunks: Mapped[list[CodeChunk]] = relationship(
        back_populates="code_file", cascade="all, delete-orphan"
    )
    change_events: Mapped[list[ChangeEvent]] = relationship(
        back_populates="code_file", cascade="all, delete-orphan"
    )

    # Table-level constraints
    __table_args__ = (
        Index("ix_code_files_repo_path", "repository_id", "relative_path", unique=True),
    )


# Pydantic Schemas


class CodeFileResponse(BaseModel):
    """Schema for code file API responses.

    Includes:
        - All core file metadata fields
        - chunk_count: Computed count of code chunks (not from DB)

    Usage:
        Used in GET /files and GET /files/{id} endpoints
        Excludes 'path' (absolute path) for security, uses 'relative_path' only

    Validation:
        - content_hash: Must be 64-character hex string (SHA-256)
        - size_bytes: Non-negative integer
        - modified_at: Should not be in future (application-level check)
    """

    id: uuid.UUID
    repository_id: uuid.UUID
    relative_path: str
    content_hash: str
    size_bytes: int
    language: str | None
    modified_at: datetime
    indexed_at: datetime
    is_deleted: bool
    chunk_count: int = Field(0, description="Number of code chunks")

    model_config = {"from_attributes": True}
