"""Add indexing_jobs table for background indexing support.

Creates indexing_jobs table to track asynchronous repository indexing operations.
This enables non-blocking indexing with status polling for the Background Indexing MVP.

Changes:
- Create table: indexing_jobs (10 essential columns for MVP)
- Add CHECK constraint on status field (pending, running, completed, failed)
- Add partial index on (project_id, status) for active job queries
- Add index on created_at DESC for job history sorting

Performance:
- Partial index on active jobs (WHERE status IN ('pending', 'running')): O(log n) active job lookups
- created_at DESC index: Efficient pagination for job history
- Status CHECK constraint: Database-level validation, prevents invalid states

Constitutional Compliance:
- Principle I: Simplicity Over Features (10 columns vs. 18 in full plan)
- Principle V: Production Quality (indexes, constraints, downgrade support)
- Principle IV: Performance Guarantees (indexed queries for job status polling)
- Principle VIII: Type Safety (explicit column types, UUID primary key)

Traces to:
- FR-US1: Start background indexing job (creates job record)
- FR-US2: Poll indexing status (queries by project_id + status)
- MVP Phase 1: Non-blocking indexing with status tracking

Revision ID: 008
Revises: 007
Create Date: 2025-10-17 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '008'
down_revision: Union[str, None] = '007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply migration: create indexing_jobs table with MVP schema.

    Creates:
    1. Table: indexing_jobs (background indexing job tracker)
    2. Indexes:
       - Partial index on (project_id, status) for active job queries
       - Index on created_at DESC for job history pagination
    3. Constraints:
       - CHECK constraint on status (valid states only)

    Schema Design (10 essential columns for MVP):
    - id: UUID PRIMARY KEY (stable job identifier)
    - repo_path: TEXT NOT NULL (repository filesystem path)
    - project_id: VARCHAR(255) NOT NULL (workspace isolation)
    - status: VARCHAR(20) NOT NULL DEFAULT 'pending' (job lifecycle state)
    - error_message: TEXT NULL (failure diagnostics)
    - files_indexed: INTEGER DEFAULT 0 (progress counter)
    - chunks_created: INTEGER DEFAULT 0 (progress counter)
    - started_at: TIMESTAMPTZ NULL (job start time)
    - completed_at: TIMESTAMPTZ NULL (job completion time)
    - created_at: TIMESTAMPTZ DEFAULT NOW() (job creation time)

    Status States:
    - pending: Job queued, not yet started
    - running: Job actively processing
    - completed: Job finished successfully
    - failed: Job encountered error (see error_message)

    Note:
    - Partial index optimized for active job queries (status IN ('pending', 'running'))
    - created_at index enables efficient job history retrieval
    - CHECK constraint enforces valid status transitions at database level
    """
    # Step 1: Create indexing_jobs table
    op.create_table(
        'indexing_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('repo_path', sa.Text(), nullable=False),
        sa.Column('project_id', sa.String(255), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('files_indexed', sa.Integer(), server_default='0'),
        sa.Column('chunks_created', sa.Integer(), server_default='0'),
        sa.Column('started_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_indexing_jobs')),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name=op.f('ck_indexing_jobs_status')
        )
    )

    # Step 2: Create partial index for active job queries
    # Optimizes: SELECT * FROM indexing_jobs WHERE project_id = ? AND status IN ('pending', 'running')
    op.create_index(
        'idx_active_jobs',
        'indexing_jobs',
        ['project_id', 'status'],
        postgresql_where=sa.text("status IN ('pending', 'running')")
    )

    # Step 3: Create index on created_at DESC for job history sorting
    # Optimizes: SELECT * FROM indexing_jobs ORDER BY created_at DESC LIMIT ?
    op.create_index(
        'idx_created_at',
        'indexing_jobs',
        [sa.text('created_at DESC')]
    )


def downgrade() -> None:
    """Revert migration: drop indexing_jobs table and all indexes.

    Drops:
    1. Indexes: idx_created_at, idx_active_jobs
    2. Table: indexing_jobs (includes CHECK constraint)

    Warning:
    - This is a destructive operation that removes ALL indexing job history
    - Downgrade should only be used in development/testing environments
    - Production downgrades require manual backup/restore procedures
    - Any active indexing jobs will be lost after downgrade
    """
    # Step 1: Drop indexes explicitly (best practice)
    op.drop_index('idx_created_at', table_name='indexing_jobs')
    op.drop_index('idx_active_jobs', table_name='indexing_jobs')

    # Step 2: Drop indexing_jobs table (includes CHECK constraint)
    op.drop_table('indexing_jobs')
