"""Add missing columns to work_items table (amendment to 003).

Adds columns that were specified in data-model.md but missing from migration 003:
- branch_name: VARCHAR(100), nullable
- commit_hash: VARCHAR(40), nullable
- pr_number: INTEGER, nullable
- metadata: JSONB, nullable (type-specific metadata)
- created_by: VARCHAR(100), not null with default 'system'

These columns enable:
1. Git integration tracking (branch_name, commit_hash, pr_number)
2. Type-specific metadata via Pydantic JSONB validation
3. Audit trail (created_by field)

Constitutional Compliance:
- Principle 8: Type safety via Pydantic JSONB validation
- Principle 10: Git micro-commit strategy via commit tracking

Revision ID: 003a
Revises: 003
Create Date: 2025-10-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003a'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing columns to tasks table.

    Adds columns specified in specs/003-database-backed-project/data-model.md
    that were inadvertently omitted from migration 003.
    """

    # Add git integration columns
    op.add_column(
        'tasks',
        sa.Column('branch_name', sa.String(length=100), nullable=True)
    )
    op.add_column(
        'tasks',
        sa.Column('commit_hash', sa.String(length=40), nullable=True)
    )
    op.add_column(
        'tasks',
        sa.Column('pr_number', sa.Integer(), nullable=True)
    )

    # Add type-specific metadata JSONB column
    op.add_column(
        'tasks',
        sa.Column(
            'metadata',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True
        )
    )

    # Add audit trail column
    op.add_column(
        'tasks',
        sa.Column(
            'created_by',
            sa.String(length=100),
            nullable=False,
            server_default='system'
        )
    )


def downgrade() -> None:
    """Remove columns added by this amendment migration."""

    # Drop columns in reverse order
    op.drop_column('tasks', 'created_by')
    op.drop_column('tasks', 'metadata')
    op.drop_column('tasks', 'pr_number')
    op.drop_column('tasks', 'commit_hash')
    op.drop_column('tasks', 'branch_name')
