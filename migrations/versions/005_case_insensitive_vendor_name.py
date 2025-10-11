"""Add case-insensitive unique index for vendor names.

Replaces the existing case-sensitive unique constraint on vendor_extractors.name
with a functional unique index on LOWER(name) to enforce case-insensitive uniqueness
per FR-012 requirement.

This ensures that vendors "NewCorp", "newcorp", and "NEWCORP" are treated as duplicates,
preventing issues with vendor name variations.

Changes:
- Drop existing unique constraint: vendor_extractors_name_key or idx_vendor_name
- Create functional unique index: idx_vendor_name_lower on LOWER(name)

Performance:
- Index remains B-tree with O(log n) lookup
- Case-insensitive queries can use the index: WHERE LOWER(name) = LOWER(:name)
- No impact on query performance (<1ms p95 target maintained)

Constitutional Compliance:
- Principle V: Production Quality (robust uniqueness enforcement)
- Principle IV: Performance Guarantees (maintains <1ms vendor lookup)

Revision ID: 005
Revises: 003b
Create Date: 2025-10-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '003b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply migration: add case-insensitive unique index for vendor names.

    Drops the existing case-sensitive unique constraint/index and creates a
    functional unique index on LOWER(name) to enforce case-insensitive uniqueness.

    Note: This migration uses raw SQL for the functional index as SQLAlchemy's
    create_index doesn't fully support functional indexes in a cross-database way.
    """
    # Drop existing unique index (created in migration 003)
    # Using IF EXISTS to handle both constraint and index names
    op.drop_index(
        'idx_vendor_name',
        table_name='vendor_extractors',
        if_exists=True
    )

    # Also drop constraint if it exists (in case it was created as a constraint)
    op.execute(
        'ALTER TABLE vendor_extractors DROP CONSTRAINT IF EXISTS vendor_extractors_name_key'
    )

    # Create functional unique index on LOWER(name)
    # This enforces case-insensitive uniqueness at the database level
    op.execute(
        'CREATE UNIQUE INDEX idx_vendor_name_lower ON vendor_extractors (LOWER(name))'
    )


def downgrade() -> None:
    """Revert migration: restore case-sensitive unique constraint.

    Drops the functional unique index and restores the original case-sensitive
    unique index on the name column.
    """
    # Drop functional unique index
    op.execute(
        'DROP INDEX IF EXISTS idx_vendor_name_lower'
    )

    # Restore original case-sensitive unique index
    op.create_index(
        'idx_vendor_name',
        'vendor_extractors',
        ['name'],
        unique=True
    )
