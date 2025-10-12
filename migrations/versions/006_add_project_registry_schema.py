"""Add project_registry schema for multi-project workspace support.

Creates a global registry schema to store workspace metadata across all projects.
This is the foundation for isolated per-project database schemas in workflow-mcp
integration.

Changes:
- Create global schema: project_registry
- Create table: workspace_config with project_id, schema_name, created_at, metadata
- Add unique index on schema_name for fast lookups
- Add index on created_at for archival features (descending order)

Performance:
- UNIQUE constraint on schema_name: O(log n) lookup via B-tree index
- created_at index: Efficient pagination for workspace listing
- JSONB metadata: Flexible storage with GIN index support (future enhancement)

Constitutional Compliance:
- Principle V: Production Quality (proper indexes, constraints, downgrade support)
- Principle IV: Performance Guarantees (indexed lookups for workspace resolution)
- Principle VIII: Type Safety (explicit column types, no ambiguity)

Traces to:
- FR-009: Isolated workspace schema per project
- FR-010: Automatic provisioning via schema_name validation

Revision ID: 006
Revises: 002
Create Date: 2025-10-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '006'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply migration: create project_registry schema and workspace_config table.

    Creates:
    1. Global schema: project_registry (namespace for multi-project metadata)
    2. Table: workspace_config (stores project_id → schema_name mappings)
    3. Indexes:
       - Unique index on schema_name (prevent duplicate schema allocation)
       - Index on created_at DESC (efficient archival queries)

    Schema Design:
    - project_id: VARCHAR(50) PRIMARY KEY (workflow-mcp project UUID)
    - schema_name: VARCHAR(60) NOT NULL UNIQUE (PostgreSQL schema identifier)
    - created_at: TIMESTAMP NOT NULL DEFAULT NOW() (audit trail)
    - metadata: JSONB DEFAULT '{}' (extensibility for future features)

    Note:
    - schema_name max length is 60 chars (PostgreSQL NAMEDATALEN - 4 for safety)
    - metadata field enables feature flags, archival state, etc. without migrations
    """
    # Create global registry schema
    op.execute("CREATE SCHEMA IF NOT EXISTS project_registry")

    # Create workspace_config table in project_registry schema
    op.create_table(
        'workspace_config',
        sa.Column('project_id', sa.String(50), primary_key=True),
        sa.Column('schema_name', sa.String(60), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('metadata', postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        schema='project_registry'
    )

    # Create unique index on schema_name (enforce 1:1 mapping with project_id)
    op.create_index(
        'idx_workspace_schema_unique',
        'workspace_config',
        ['schema_name'],
        unique=True,
        schema='project_registry'
    )

    # Create index on created_at DESC (optimize workspace listing, archival queries)
    op.create_index(
        'idx_workspace_created',
        'workspace_config',
        [sa.text('created_at DESC')],
        schema='project_registry'
    )


def downgrade() -> None:
    """Revert migration: drop project_registry schema and all contents.

    Drops:
    1. Indexes: idx_workspace_created, idx_workspace_schema_unique
    2. Table: workspace_config
    3. Schema: project_registry (CASCADE removes all contained objects)

    Warning:
    - This is a destructive operation that removes ALL workspace metadata
    - Downgrade should only be used in development/testing environments
    - Production downgrades require manual backup/restore procedures
    """
    # Drop indexes explicitly (best practice, even though CASCADE would handle it)
    op.drop_index('idx_workspace_created', table_name='workspace_config', schema='project_registry')
    op.drop_index('idx_workspace_schema_unique', table_name='workspace_config', schema='project_registry')

    # Drop workspace_config table
    op.drop_table('workspace_config', schema='project_registry')

    # Drop project_registry schema (CASCADE ensures cleanup of any residual objects)
    op.execute("DROP SCHEMA IF EXISTS project_registry CASCADE")
