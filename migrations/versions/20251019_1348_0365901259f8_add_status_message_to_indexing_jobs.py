"""add status_message to indexing_jobs

Revision ID: 0365901259f8
Revises: 008
Create Date: 2025-10-19 13:48:49.551801+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0365901259f8'
down_revision: Union[str, None] = '008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply migration changes to database schema.

    This function should contain all changes to move forward from the
    previous revision to this revision.
    """
    # Add status_message column to indexing_jobs table
    op.add_column('indexing_jobs', sa.Column('status_message', sa.Text(), nullable=True))


def downgrade() -> None:
    """Revert migration changes from database schema.

    This function should contain all changes to move backward from this
    revision to the previous revision. Should mirror upgrade() operations
    in reverse order.
    """
    # Remove status_message column from indexing_jobs table
    op.drop_column('indexing_jobs', 'status_message')
