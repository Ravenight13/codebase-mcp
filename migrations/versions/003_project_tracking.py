"""Add project tracking tables for hierarchical work items and vendor deployment tracking.

Creates 9 new tables and extends the existing work_items table (formerly tasks) with
hierarchical project/session/task organization, soft deletion, and comprehensive
vendor deployment tracking.

Tables Created:
- vendor_extractors: Vendor extraction module tracking with operational status
- deployment_events: Git-based deployment history with commit hash tracking
- project_configuration: Singleton configuration for active context and health monitoring
- future_enhancements: Planned features with priority and constitutional principle tracking
- work_item_dependencies: Junction table for task dependency graphs
- vendor_deployment_links: Many-to-many vendor-deployment associations
- work_item_deployment_links: Many-to-many work item-deployment associations
- archived_work_items: Soft-deleted work items with full historical context

Tables Extended:
- work_items: Added hierarchical structure (parent_id, path, depth), item_type,
  version, and soft deletion (deleted_at)

Performance Features:
- Indexes for hierarchical queries (parent_id, path)
- Partial index for non-deleted items
- Indexes for deployment timestamp and commit hash lookups
- Composite primary keys for junction tables
- Check constraints for data validation (status enums, depth limits, commit hash format)

Constitutional Compliance:
- Principle 10: Git micro-commit strategy enforced via commit_hash validation
- Principle 8: Type safety via CHECK constraints and JSONB validation
- Principle 6: Specification-first development tracked via work_items hierarchy

Revision ID: 003
Revises: 001
Create Date: 2025-10-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply migration changes to add project tracking tables.

    Creates:
    1. vendor_extractors table with operational status tracking
    2. deployment_events table with git commit history
    3. Extends work_items (tasks) with hierarchical structure
    4. project_configuration singleton table
    5. future_enhancements table with priority tracking
    6. Junction tables for many-to-many relationships
    7. archived_work_items table for soft-deleted items
    8. All required indexes and constraints
    """

    # 1. Create vendor_extractors table
    op.create_table(
        'vendor_extractors',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('extractor_version', sa.String(length=50), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(length=100), nullable=False),
        sa.CheckConstraint(
            "status IN ('operational', 'broken')",
            name='ck_vendor_status'
        )
    )
    op.create_index(
        'idx_vendor_name',
        'vendor_extractors',
        ['name'],
        unique=True
    )
    op.create_index(
        'idx_vendor_status',
        'vendor_extractors',
        ['status']
    )

    # 2. Create deployment_events table
    op.create_table(
        'deployment_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('deployed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('commit_hash', sa.String(length=40), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(length=100), nullable=False),
        sa.CheckConstraint(
            "commit_hash ~ '^[a-f0-9]{40}$'",
            name='ck_commit_hash_format'
        )
    )
    op.create_index(
        'idx_deployment_deployed_at',
        'deployment_events',
        [sa.text('deployed_at DESC')]
    )
    op.create_index(
        'idx_deployment_commit_hash',
        'deployment_events',
        ['commit_hash']
    )

    # 3. Extend work_items table (formerly tasks)
    # Add new columns for hierarchical structure
    op.add_column(
        'tasks',
        sa.Column('version', sa.Integer(), nullable=False, server_default='1')
    )
    op.add_column(
        'tasks',
        sa.Column('item_type', sa.String(length=20), nullable=False, server_default='task')
    )
    op.add_column(
        'tasks',
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.add_column(
        'tasks',
        sa.Column('path', sa.String(length=500), nullable=False, server_default='/')
    )
    op.add_column(
        'tasks',
        sa.Column('depth', sa.Integer(), nullable=False, server_default='0')
    )
    op.add_column(
        'tasks',
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True)
    )

    # Add foreign key constraint for hierarchical structure
    op.create_foreign_key(
        'fk_work_item_parent',
        'tasks',
        'tasks',
        ['parent_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # Add indexes for hierarchical queries and filtering
    op.create_index(
        'idx_work_item_parent_id',
        'tasks',
        ['parent_id']
    )
    op.create_index(
        'idx_work_item_path',
        'tasks',
        ['path']
    )
    op.create_index(
        'idx_work_item_type',
        'tasks',
        ['item_type']
    )
    # Partial index for non-deleted items (most common query)
    op.create_index(
        'idx_work_item_deleted_at',
        'tasks',
        ['deleted_at'],
        postgresql_where=sa.text('deleted_at IS NULL')
    )

    # Add check constraints for validation
    op.create_check_constraint(
        'ck_work_item_type',
        'tasks',
        "item_type IN ('project', 'session', 'task', 'research')"
    )
    op.create_check_constraint(
        'ck_work_item_depth',
        'tasks',
        'depth >= 0 AND depth <= 5'
    )

    # 4. Create project_configuration singleton table
    op.create_table(
        'project_configuration',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('active_context_type', sa.String(length=50), nullable=False),
        sa.Column('current_session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('git_branch', sa.String(length=100), nullable=True),
        sa.Column('git_head_commit', sa.String(length=40), nullable=True),
        sa.Column('default_token_budget', sa.Integer(), nullable=False, server_default='200000'),
        sa.Column('database_healthy', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_health_check_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_by', sa.String(length=100), nullable=False),
        sa.CheckConstraint('id = 1', name='ck_singleton')
    )
    op.create_foreign_key(
        'fk_current_session',
        'project_configuration',
        'tasks',
        ['current_session_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # 5. Create future_enhancements table
    op.create_table(
        'future_enhancements',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='planned'),
        sa.Column('target_quarter', sa.String(length=10), nullable=True),
        sa.Column(
            'requires_constitutional_principles',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default='[]'
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(length=100), nullable=False),
        sa.CheckConstraint(
            'priority >= 1 AND priority <= 5',
            name='ck_priority_range'
        ),
        sa.CheckConstraint(
            "status IN ('planned', 'approved', 'implementing', 'completed')",
            name='ck_enhancement_status'
        )
    )
    op.create_index(
        'idx_enhancement_priority',
        'future_enhancements',
        ['priority']
    )
    op.create_index(
        'idx_enhancement_status',
        'future_enhancements',
        ['status']
    )

    # 6. Create work_item_dependencies junction table
    op.create_table(
        'work_item_dependencies',
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('dependency_type', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint('source_id', 'target_id'),
        sa.ForeignKeyConstraint(
            ['source_id'],
            ['tasks.id'],
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['target_id'],
            ['tasks.id'],
            ondelete='CASCADE'
        ),
        sa.CheckConstraint(
            "dependency_type IN ('blocks', 'depends_on')",
            name='ck_dependency_type'
        ),
        sa.CheckConstraint(
            'source_id != target_id',
            name='ck_no_self_dependency'
        )
    )
    op.create_index(
        'idx_dependency_source_id',
        'work_item_dependencies',
        ['source_id']
    )
    op.create_index(
        'idx_dependency_target_id',
        'work_item_dependencies',
        ['target_id']
    )

    # 7. Create vendor_deployment_links junction table
    op.create_table(
        'vendor_deployment_links',
        sa.Column('deployment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('vendor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('deployment_id', 'vendor_id'),
        sa.ForeignKeyConstraint(
            ['deployment_id'],
            ['deployment_events.id'],
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['vendor_id'],
            ['vendor_extractors.id'],
            ondelete='CASCADE'
        )
    )
    op.create_index(
        'idx_vendor_deployment_deployment_id',
        'vendor_deployment_links',
        ['deployment_id']
    )
    op.create_index(
        'idx_vendor_deployment_vendor_id',
        'vendor_deployment_links',
        ['vendor_id']
    )

    # 8. Create work_item_deployment_links junction table
    op.create_table(
        'work_item_deployment_links',
        sa.Column('deployment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('work_item_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('deployment_id', 'work_item_id'),
        sa.ForeignKeyConstraint(
            ['deployment_id'],
            ['deployment_events.id'],
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['work_item_id'],
            ['tasks.id'],
            ondelete='CASCADE'
        )
    )
    op.create_index(
        'idx_work_item_deployment_deployment_id',
        'work_item_deployment_links',
        ['deployment_id']
    )
    op.create_index(
        'idx_work_item_deployment_work_item_id',
        'work_item_deployment_links',
        ['work_item_id']
    )

    # 9. Create archived_work_items table
    op.create_table(
        'archived_work_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('item_type', sa.String(length=20), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('path', sa.String(length=500), nullable=False),
        sa.Column('depth', sa.Integer(), nullable=False),
        sa.Column('branch_name', sa.String(length=100), nullable=True),
        sa.Column('commit_hash', sa.String(length=40), nullable=True),
        sa.Column('pr_number', sa.Integer(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(length=100), nullable=False),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index(
        'idx_archived_work_item_created_at',
        'archived_work_items',
        ['created_at']
    )
    op.create_index(
        'idx_archived_work_item_type',
        'archived_work_items',
        ['item_type']
    )
    op.create_index(
        'idx_archived_work_item_archived_at',
        'archived_work_items',
        ['archived_at']
    )


def downgrade() -> None:
    """Revert migration changes to remove project tracking tables.

    Drops all created tables and removes extensions to work_items table.
    Order is critical to respect foreign key constraints.
    """

    # Drop tables in reverse order of creation (respecting FK constraints)
    op.drop_table('archived_work_items')
    op.drop_table('work_item_deployment_links')
    op.drop_table('vendor_deployment_links')
    op.drop_table('work_item_dependencies')
    op.drop_table('future_enhancements')
    op.drop_table('project_configuration')
    op.drop_table('deployment_events')
    op.drop_table('vendor_extractors')

    # Revert work_items (tasks) table extensions
    # Drop indexes first
    op.drop_index('idx_work_item_deleted_at', 'tasks')
    op.drop_index('idx_work_item_type', 'tasks')
    op.drop_index('idx_work_item_path', 'tasks')
    op.drop_index('idx_work_item_parent_id', 'tasks')

    # Drop check constraints
    op.drop_constraint('ck_work_item_depth', 'tasks', type_='check')
    op.drop_constraint('ck_work_item_type', 'tasks', type_='check')

    # Drop foreign key constraint
    op.drop_constraint('fk_work_item_parent', 'tasks', type_='foreignkey')

    # Drop columns added in this migration
    op.drop_column('tasks', 'deleted_at')
    op.drop_column('tasks', 'depth')
    op.drop_column('tasks', 'path')
    op.drop_column('tasks', 'parent_id')
    op.drop_column('tasks', 'item_type')
    op.drop_column('tasks', 'version')
