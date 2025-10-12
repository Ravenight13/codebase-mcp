"""Type stub for 007_provision_default_workspace migration."""

from __future__ import annotations

from typing import Sequence, Union

# Alembic migration metadata
revision: str
down_revision: Union[str, None]
branch_labels: Union[str, Sequence[str], None]
depends_on: Union[str, Sequence[str], None]

def upgrade() -> None:
    """Apply migration: create project_default schema with core tables."""
    ...

def downgrade() -> None:
    """Revert migration: drop project_default schema and workspace registration."""
    ...
