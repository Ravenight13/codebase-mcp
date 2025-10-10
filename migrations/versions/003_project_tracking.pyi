"""Type stub for 003_project_tracking.py migration.

Provides complete type annotations for mypy --strict compliance.
"""
from __future__ import annotations

from typing import Sequence, Union

# Alembic revision identifiers
revision: str
down_revision: Union[str, None]
branch_labels: Union[str, Sequence[str], None]
depends_on: Union[str, Sequence[str], None]

def upgrade() -> None:
    """Apply migration changes to add project tracking tables.

    Creates:
    - 9 new tables (vendor_extractors, deployment_events, etc.)
    - Extends work_items (tasks) table with hierarchical columns
    - 11 indexes (including partial index for non-deleted items)
    - 8 CHECK constraints for validation
    - 6 foreign key constraints
    """
    ...

def downgrade() -> None:
    """Revert migration changes to remove project tracking tables.

    Drops all created tables and removes extensions to work_items table.
    Order respects foreign key constraints.
    """
    ...
