"""Type stub for Alembic migration 002.

This type stub provides complete type annotations for the migration module,
ensuring mypy --strict compliance.
"""
from __future__ import annotations

from typing import Sequence, Union

# Alembic revision identifiers
revision: str
down_revision: Union[str, None]
branch_labels: Union[str, Sequence[str], None]
depends_on: Union[str, Sequence[str], None]

def upgrade() -> None:
    """Apply migration: remove non-search tables and add project_id columns.

    Executes 10 steps in single atomic transaction:
    1. Prerequisites check
    2. Foreign key verification
    3. Add project_id to repositories
    4. Add project_id to code_chunks (3-step approach)
    5. Add CHECK constraints
    6. Create performance index
    7. Drop 9 unused tables
    8. Validation checks
    9. Log completion with duration
    10. COMMIT (automatic via Alembic)

    Raises:
        ValueError: If foreign keys found from dropped tables to core tables
        Exception: If any DDL operation fails (transaction auto-rolled back)
    """
    ...

def downgrade() -> None:
    """Rollback migration: restore dropped tables and remove project_id columns.

    Executes 6 rollback steps in single atomic transaction:
    1. Drop performance index
    2. Drop CHECK constraints
    3. Drop project_id from code_chunks
    4. Drop project_id from repositories
    5. Restore 9 dropped tables (schema only, data NOT restored)
    6. Run validation, log completion

    WARNING: Data in dropped tables is NOT restored by this function.
    Data restoration requires manual import from backup.

    Raises:
        Exception: If any rollback operation fails (transaction auto-rolled back)
    """
    ...
