"""CodeChunk model and schemas with pgvector embeddings.

Represents semantic chunks of code (functions, classes, blocks) with vector embeddings
for similarity search.

Entity Responsibilities:
- Store code chunk content with line boundaries
- Maintain 768-dimensional embeddings (nomic-embed-text)
- Support fast similarity search via HNSW index
- Many-to-one relationship with CodeFile

Constitutional Compliance:
- Principle IV: Performance (HNSW index, cosine distance, optimized params)
- Principle V: Production quality (line validation, chunk type constraints)
- Principle VIII: Type safety (full Mapped[] annotations, Pydantic validation)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

if TYPE_CHECKING:
    from .code_file import CodeFile


class CodeChunk(Base):
    """SQLAlchemy model for code chunks with vector embeddings.

    Table: code_chunks

    Relationships:
        - code_file: Many-to-one with CodeFile

    Indexes:
        - embedding: HNSW index for fast similarity search
            - Distance: Cosine (vector_cosine_ops)
            - Parameters: m=16, ef_construction=64
            - Target: <500ms search latency (p95)

    Chunk Types:
        - function: Function or method definition
        - class: Class definition
        - block: Logical code block (if/for/try, etc.)

    Embedding:
        - Model: nomic-embed-text (Ollama)
        - Dimensions: 768
        - Nullable: True (supports lazy embedding generation)
    """

    __tablename__ = "code_chunks"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Foreign keys
    code_file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("code_files.id"), nullable=False
    )

    # Content fields
    content: Mapped[str] = mapped_column(Text, nullable=False)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # function|class|block

    # Vector embedding (768 dimensions for nomic-embed-text)
    embedding: Mapped[Vector | None] = mapped_column(Vector(768), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    code_file: Mapped[CodeFile] = relationship(back_populates="chunks")

    # Table-level constraints
    __table_args__ = (
        Index(
            "ix_chunks_embedding_cosine",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


# Pydantic Schemas


class CodeChunkCreate(BaseModel):
    """Schema for creating a new code chunk.

    Validation:
        - start_line: Must be >= 1
        - end_line: Must be >= 1 and >= start_line
        - chunk_type: Must be 'function', 'class', or 'block'
    """

    code_file_id: uuid.UUID
    content: str
    start_line: int = Field(..., ge=1, description="Starting line number (1-indexed)")
    end_line: int = Field(..., ge=1, description="Ending line number (1-indexed)")
    chunk_type: str = Field(
        ..., pattern="^(function|class|block)$", description="Type of code chunk"
    )

    @field_validator("end_line")
    @classmethod
    def validate_line_order(cls, v: int, info: dict) -> int:
        """Validate that end_line >= start_line."""
        if "start_line" in info.data and v < info.data["start_line"]:
            raise ValueError("end_line must be >= start_line")
        return v

    model_config = {"from_attributes": True}


class CodeChunkResponse(BaseModel):
    """Schema for code chunk API responses.

    Includes:
        - All core chunk fields (except raw embedding vector)
        - has_embedding: Boolean flag for embedding presence
        - similarity_score: Optional score from similarity search

    Usage:
        Used in GET /chunks and search endpoints
        Excludes raw embedding vector for performance (large payload)

    Search Results:
        - similarity_score: Populated by search queries (1-distance)
        - Higher score = more similar (0.0 to 1.0 range)
    """

    id: uuid.UUID
    code_file_id: uuid.UUID
    content: str
    start_line: int
    end_line: int
    chunk_type: str
    has_embedding: bool = Field(
        default=False, description="Whether embedding is generated"
    )
    similarity_score: float | None = Field(
        None, description="Similarity score when from search"
    )

    model_config = {"from_attributes": True}
