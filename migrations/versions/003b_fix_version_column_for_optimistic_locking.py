"""Fix version column for SQLAlchemy optimistic locking.

Removes server_default from version column to allow SQLAlchemy's version_id_col
to properly manage version increments. SQLAlchemy's optimistic locking requires
full control over the version counter and cannot work correctly with server defaults.

Changes:
- Remove server_default='1' from tasks.version column
- Remove server_default='1' from vendor_extractors.version column

This allows SQLAlchemy to:
1. Initialize version to 1 on INSERT (managed by SQLAlchemy)
2. Increment version on UPDATE (via version_id_col mechanism)
3. Detect concurrent modifications via StaleDataError

Constitutional Compliance:
- Principle V: Production quality (optimistic locking for concurrent updates)
- Principle VIII: Type safety (SQLAlchemy version_id_col integration)

Revision ID: 003b
Revises: 003a
Create Date: 2025-10-10 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003b'
down_revision: Union[str, None] = '003a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove server_default from version columns.

    SQLAlchemy's version_id_col requires full control over version management.
    The server_default interferes with SQLAlchemy's increment logic.
    """

    # Remove server default from tasks.version
    op.alter_column(
        'tasks',
        'version',
        existing_type=sa.Integer(),
        server_default=None,
        nullable=False
    )

    # Remove server default from vendor_extractors.version
    op.alter_column(
        'vendor_extractors',
        'version',
        existing_type=sa.Integer(),
        server_default=None,
        nullable=False
    )


def downgrade() -> None:
    """Restore server_default to version columns."""

    # Restore server default for tasks.version
    op.alter_column(
        'tasks',
        'version',
        existing_type=sa.Integer(),
        server_default='1',
        nullable=False
    )

    # Restore server default for vendor_extractors.version
    op.alter_column(
        'vendor_extractors',
        'version',
        existing_type=sa.Integer(),
        server_default='1',
        nullable=False
    )
