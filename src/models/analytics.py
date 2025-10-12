"""Analytics models for change events and embedding metadata.

These models track non-essential analytics for indexing operations.
They were preserved from the pre-simplification codebase to avoid
breaking the indexer service.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class ChangeEvent(Base):
    """Track file change events during repository indexing.

    Non-essential analytics table for tracking which files changed
    during incremental indexing operations.
    """

    __tablename__ = "change_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    change_type: Mapped[str] = mapped_column(String, nullable=False)  # added, modified, deleted
    detected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class EmbeddingMetadata(Base):
    """Track embedding generation metadata for performance analytics.

    Non-essential analytics table for tracking embedding generation
    performance metrics.
    """

    __tablename__ = "embedding_metadata"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    count: Mapped[int] = mapped_column(Integer, nullable=False)  # Number of embeddings generated
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False)  # Generation time in milliseconds
    model_name: Mapped[str | None] = mapped_column(String, nullable=True)  # Embedding model used
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
