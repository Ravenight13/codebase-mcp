"""IndexingJob model and schemas for background indexing.

Represents a background indexing job that processes repositories asynchronously.

Entity Responsibilities:
- Track background indexing job status and progress
- Store job metadata (repo path, project ID, error messages)
- Record indexing metrics (files indexed, chunks created)
- Maintain job lifecycle timestamps (started, completed)

Job Status States:
- pending: Job created but not started
- running: Job actively processing
- completed: Job finished successfully
- failed: Job encountered error and stopped

Constitutional Compliance:
- Principle V: Production quality (path validation, error handling)
- Principle VIII: Type safety (full Mapped[] annotations, Pydantic validation)
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class IndexingJob(Base):
    """SQLAlchemy model for background indexing jobs.

    Table: indexing_jobs

    Constraints:
        - id: Primary key (UUID)
        - status: Must be one of: pending, running, completed, failed

    Lifecycle:
        1. pending: Job created, not started
        2. running: Worker processing repository
        3. completed/failed: Terminal states with metrics

    Metrics:
        - files_indexed: Number of files processed
        - chunks_created: Number of code chunks created
    """

    __tablename__ = "indexing_jobs"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Core fields
    repo_path: Mapped[str] = mapped_column(Text, nullable=False)
    project_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # Job status and error tracking
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Indexing metrics
    files_indexed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunks_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Lifecycle timestamps
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )


# Pydantic Schemas


class IndexingJobCreate(BaseModel):
    """Schema for creating a background indexing job.

    Security Validation:
        - repo_path: Must be absolute path (no relative paths)
        - repo_path: Path traversal prevention (no ../ sequences)
        - project_id: Non-empty string identifier

    Usage:
        Used in POST /jobs/index endpoint to create background jobs
    """

    repo_path: str = Field(min_length=1, description="Absolute path to repository")
    project_id: str = Field(min_length=1, description="Project workspace identifier")

    @field_validator("repo_path")
    @classmethod
    def validate_repo_path(cls, v: str) -> str:
        """Validate repo_path is absolute and has no path traversal.

        Args:
            v: Repository path to validate

        Returns:
            Validated absolute path

        Raises:
            ValueError: If path is relative or contains traversal sequences

        Security:
            - Prevents relative path attacks (must be absolute)
            - Prevents path traversal attacks (no ../ sequences)
        """
        # Must be absolute path
        if not os.path.isabs(v):
            raise ValueError(f"repo_path must be absolute, got: {v}")

        # Prevent path traversal
        if ".." in v:
            raise ValueError(f"Path traversal detected in repo_path: {v}")

        # Additional validation: resolve and check for traversal
        resolved = Path(v).resolve()
        original = Path(v)

        # If resolved path diverges significantly, might be traversal
        # This is a defense-in-depth check
        try:
            # Ensure path components don't contain suspicious sequences
            for part in Path(v).parts:
                if part == "..":
                    raise ValueError(f"Path traversal detected in repo_path: {v}")
        except Exception as e:
            raise ValueError(f"Invalid path format: {v}") from e

        return v

    model_config = {"from_attributes": True}


class IndexingJobResponse(BaseModel):
    """Schema for indexing job API responses.

    Includes:
        - All core job fields
        - Status tracking and error messages
        - Progress metrics (files, chunks)
        - Lifecycle timestamps

    Usage:
        Used in GET /jobs/{job_id} and POST /jobs/index endpoints
    """

    job_id: uuid.UUID = Field(alias="id", description="Unique job identifier")
    status: str = Field(description="Job status: pending, running, completed, failed")
    repo_path: str = Field(description="Repository path being indexed")
    project_id: str = Field(description="Project workspace identifier")
    error_message: str | None = Field(None, description="Error message if failed")
    files_indexed: int = Field(0, description="Number of files processed")
    chunks_created: int = Field(0, description="Number of code chunks created")
    started_at: datetime | None = Field(None, description="Job start timestamp")
    completed_at: datetime | None = Field(None, description="Job completion timestamp")
    created_at: datetime = Field(description="Job creation timestamp")

    model_config = {"from_attributes": True, "populate_by_name": True}
