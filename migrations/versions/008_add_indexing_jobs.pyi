"""Type stubs for migration 008_add_indexing_jobs.

Constitutional Compliance:
- Principle VIII: Type Safety (complete type annotations for migration functions)
"""
from __future__ import annotations

from typing import Sequence, Union

# Alembic revision identifiers
revision: str
down_revision: Union[str, None]
branch_labels: Union[str, Sequence[str], None]
depends_on: Union[str, Sequence[str], None]

def upgrade() -> None:
    """Apply migration: create indexing_jobs table with MVP schema."""
    ...

def downgrade() -> None:
    """Revert migration: drop indexing_jobs table and all indexes."""
    ...
