"""Analytics models for change events and embedding metadata.

These models track non-essential analytics for indexing operations.
They were preserved from the pre-simplification codebase to avoid
breaking the indexer service.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

if TYPE_CHECKING:
    from .repository import Repository


class ChangeEvent(Base):
    """Track file change events during repository indexing.

    Non-essential analytics table for tracking which files changed
    during incremental indexing operations.

    Relationships:
        - repository: Many-to-one with Repository
    """

    __tablename__ = "change_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id"), nullable=False
    )
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    change_type: Mapped[str] = mapped_column(String, nullable=False)  # added, modified, deleted
    detected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    repository: Mapped["Repository"] = relationship("Repository", back_populates="change_events")


class EmbeddingMetadata(Base):
    """Track embedding generation metadata for performance analytics.

    Non-essential analytics table for tracking embedding generation
    performance metrics.
    """

    __tablename__ = "embedding_metadata"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    model_name: Mapped[str] = mapped_column(String, nullable=False, server_default="nomic-embed-text")
    model_version: Mapped[str | None] = mapped_column(String, nullable=True)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False, server_default="768")
    generation_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
