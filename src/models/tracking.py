"""Tracking and analytics models.

Supporting entities for operational tracking:
- ChangeEvent: Records file system changes for incremental indexing
- EmbeddingMetadata: Analytics for embedding generation performance
- SearchQuery: Analytics for search query performance

Entity Responsibilities:
- Track file changes for incremental re-indexing
- Monitor embedding generation performance
- Analyze search query patterns and latency
- Support performance optimization and debugging

Constitutional Compliance:
- Principle IV: Performance (change detection for incremental indexing)
- Principle V: Production quality (comprehensive logging and analytics)
- Principle VIII: Type safety (full Mapped[] annotations)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.schema import ForeignKey

from .database import Base

if TYPE_CHECKING:
    from .code_file import CodeFile


class ChangeEvent(Base):
    """Records file system changes for incremental indexing.

    Table: change_events

    Relationships:
        - code_file: Many-to-one with CodeFile

    Indexes:
        - detected_at: B-tree for temporal queries

    Purpose:
        - Track added/modified/deleted files
        - Enable incremental re-indexing (avoid full scans)
        - Support change batching for performance

    Event Types:
        - added: New file detected
        - modified: Existing file content changed
        - deleted: File removed from filesystem

    Workflow:
        1. File system watcher creates ChangeEvent
        2. Background worker processes unprocessed events
        3. Event marked processed=True after handling
        4. Periodic cleanup of old processed events
    """

    __tablename__ = "change_events"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Foreign keys
    code_file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("code_files.id"), nullable=False
    )

    # Event metadata
    event_type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # added|modified|deleted
    detected_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )
    processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    code_file: Mapped[CodeFile] = relationship(back_populates="change_events")


class EmbeddingMetadata(Base):
    """Analytics for embedding generation performance.

    Table: embedding_metadata

    Purpose:
        - Track embedding model performance
        - Monitor generation latency
        - Support model version tracking
        - Enable performance optimization

    Model Information:
        - model_name: Default 'nomic-embed-text'
        - model_version: Optional version string from Ollama
        - dimensions: Default 768 (nomic-embed-text output)

    Performance Metrics:
        - generation_time_ms: Time to generate single embedding
        - Target: <100ms per embedding (60s for ~600 embeddings)

    Usage:
        Created automatically during batch embedding generation
        to track per-batch performance statistics.
    """

    __tablename__ = "embedding_metadata"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Model information
    model_name: Mapped[str] = mapped_column(
        String, nullable=False, default="nomic-embed-text"
    )
    model_version: Mapped[str | None] = mapped_column(String, nullable=True)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False, default=768)

    # Performance metrics
    generation_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )


class SearchQuery(Base):
    """Analytics for search queries.

    Table: search_queries

    Indexes:
        - created_at: B-tree for temporal analysis

    Purpose:
        - Track search query patterns
        - Monitor search performance
        - Identify slow queries for optimization
        - Support usage analytics

    Performance Metrics:
        - latency_ms: Time from query to results
        - Target: <500ms (p95)
        - result_count: Number of results returned

    Filter Tracking:
        - filters: JSON object of applied filters
        - Examples: {"language": "python", "repository_id": "uuid"}
        - Supports analysis of filter effectiveness

    Usage:
        Created automatically for each search request
        to track performance and usage patterns.
    """

    __tablename__ = "search_queries"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Query information
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    result_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # Performance metrics
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)

    # Filter tracking
    filters: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )
