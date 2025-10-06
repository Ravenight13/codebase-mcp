"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    """Apply migration changes to database schema.

    This function should contain all changes to move forward from the
    previous revision to this revision.
    """
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Revert migration changes from database schema.

    This function should contain all changes to move backward from this
    revision to the previous revision. Should mirror upgrade() operations
    in reverse order.
    """
    ${downgrades if downgrades else "pass"}
