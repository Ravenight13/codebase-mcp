"""Initial database schema for Codebase MCP Server.

Creates all 11 tables with indexes, constraints, and pgvector extension.

Tables Created:
- repositories: Code repository metadata
- code_files: Source code files within repositories
- code_chunks: Semantic code chunks with embeddings
- tasks: Development task tracking
- task_planning_references: Links tasks to planning documents
- task_branch_links: Associates tasks with git branches
- task_commit_links: Associates tasks with git commits
- task_status_history: Tracks task status transitions
- change_events: File system change tracking for incremental indexing
- embedding_metadata: Analytics for embedding generation
- search_queries: Search query analytics

Performance Features:
- HNSW index on code_chunks.embedding (m=16, ef_construction=64)
- Optimized indexes for foreign keys and frequent queries
- Check constraints for data validation

Revision ID: 001
Revises:
Create Date: 2025-10-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply migration changes to database schema.

    Creates:
    1. pgvector extension
    2. All 11 tables with proper types and constraints
    3. Indexes (including HNSW for embeddings)
    4. Foreign key constraints
    5. Check constraints
    """
    # Step 1: Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Step 2: Create repositories table
    op.create_table(
        'repositories',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('path', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('last_indexed_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_repositories')),
        sa.UniqueConstraint('path', name=op.f('uq_repositories_path'))
    )
    op.create_index(op.f('ix_repositories_path'), 'repositories', ['path'], unique=True)

    # Step 3: Create code_files table
    op.create_table(
        'code_files',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('repository_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('path', sa.String(), nullable=False),
        sa.Column('relative_path', sa.String(), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('language', sa.String(), nullable=True),
        sa.Column('modified_at', sa.DateTime(), nullable=False),
        sa.Column('indexed_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], name=op.f('fk_code_files_repository_id_repositories')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_code_files'))
    )
    op.create_index(op.f('ix_code_files_path'), 'code_files', ['path'], unique=False)
    op.create_index('ix_code_files_repo_path', 'code_files', ['repository_id', 'relative_path'], unique=True)

    # Step 4: Create code_chunks table (with vector column)
    op.create_table(
        'code_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('code_file_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('start_line', sa.Integer(), nullable=False),
        sa.Column('end_line', sa.Integer(), nullable=False),
        sa.Column('chunk_type', sa.String(), nullable=False),
        sa.Column('embedding', Vector(768), nullable=True),  # pgvector VECTOR(768) type
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['code_file_id'], ['code_files.id'], name=op.f('fk_code_chunks_code_file_id_code_files')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_code_chunks'))
    )

    # Create HNSW index for vector similarity search (pgvector specific)
    # Note: This uses raw SQL because HNSW index syntax is pgvector-specific
    op.execute(
        """
        CREATE INDEX ix_chunks_embedding_cosine ON code_chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )

    # Step 5: Create tasks table
    op.create_table(
        'tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='need to be done'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.CheckConstraint(
            "status IN ('need to be done', 'in-progress', 'complete')",
            name=op.f('ck_tasks_valid_status')
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_tasks'))
    )
    op.create_index(op.f('ix_tasks_status'), 'tasks', ['status'], unique=False)

    # Step 6: Create task_planning_references table
    op.create_table(
        'task_planning_references',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('file_path', sa.String(), nullable=False),
        sa.Column('reference_type', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], name=op.f('fk_task_planning_references_task_id_tasks')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_task_planning_references'))
    )

    # Step 7: Create task_branch_links table
    op.create_table(
        'task_branch_links',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('branch_name', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], name=op.f('fk_task_branch_links_task_id_tasks')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_task_branch_links'))
    )
    op.create_index('ix_branch_links_task_branch', 'task_branch_links', ['task_id', 'branch_name'], unique=True)

    # Step 8: Create task_commit_links table
    op.create_table(
        'task_commit_links',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('commit_hash', sa.String(length=40), nullable=False),
        sa.Column('commit_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], name=op.f('fk_task_commit_links_task_id_tasks')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_task_commit_links'))
    )
    op.create_index('ix_commit_links_task_commit', 'task_commit_links', ['task_id', 'commit_hash'], unique=True)

    # Step 9: Create task_status_history table
    op.create_table(
        'task_status_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('from_status', sa.String(), nullable=True),
        sa.Column('to_status', sa.String(), nullable=False),
        sa.Column('changed_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], name=op.f('fk_task_status_history_task_id_tasks')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_task_status_history'))
    )
    op.create_index(op.f('ix_task_status_history_changed_at'), 'task_status_history', ['changed_at'], unique=False)

    # Step 10: Create change_events table
    op.create_table(
        'change_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('code_file_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('detected_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('processed', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['code_file_id'], ['code_files.id'], name=op.f('fk_change_events_code_file_id_code_files')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_change_events'))
    )
    op.create_index(op.f('ix_change_events_detected_at'), 'change_events', ['detected_at'], unique=False)

    # Step 11: Create embedding_metadata table
    op.create_table(
        'embedding_metadata',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('model_name', sa.String(), nullable=False, server_default='nomic-embed-text'),
        sa.Column('model_version', sa.String(), nullable=True),
        sa.Column('dimensions', sa.Integer(), nullable=False, server_default='768'),
        sa.Column('generation_time_ms', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_embedding_metadata'))
    )

    # Step 12: Create search_queries table
    op.create_table(
        'search_queries',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('query_text', sa.Text(), nullable=False),
        sa.Column('result_count', sa.Integer(), nullable=False),
        sa.Column('latency_ms', sa.Integer(), nullable=False),
        sa.Column('filters', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_search_queries'))
    )
    op.create_index(op.f('ix_search_queries_created_at'), 'search_queries', ['created_at'], unique=False)


def downgrade() -> None:
    """Revert migration changes from database schema.

    Drops all tables and extensions in reverse dependency order.
    """
    # Drop tables in reverse order (respecting foreign key dependencies)
    op.drop_index(op.f('ix_search_queries_created_at'), table_name='search_queries')
    op.drop_table('search_queries')

    op.drop_table('embedding_metadata')

    op.drop_index(op.f('ix_change_events_detected_at'), table_name='change_events')
    op.drop_table('change_events')

    op.drop_index(op.f('ix_task_status_history_changed_at'), table_name='task_status_history')
    op.drop_table('task_status_history')

    op.drop_index('ix_commit_links_task_commit', table_name='task_commit_links')
    op.drop_table('task_commit_links')

    op.drop_index('ix_branch_links_task_branch', table_name='task_branch_links')
    op.drop_table('task_branch_links')

    op.drop_table('task_planning_references')

    op.drop_index(op.f('ix_tasks_status'), table_name='tasks')
    op.drop_table('tasks')

    # Drop HNSW index explicitly before dropping table
    op.execute("DROP INDEX IF EXISTS ix_chunks_embedding_cosine")
    op.drop_table('code_chunks')

    op.drop_index('ix_code_files_repo_path', table_name='code_files')
    op.drop_index(op.f('ix_code_files_path'), table_name='code_files')
    op.drop_table('code_files')

    op.drop_index(op.f('ix_repositories_path'), table_name='repositories')
    op.drop_table('repositories')

    # Drop pgvector extension
    op.execute("DROP EXTENSION IF EXISTS vector")
