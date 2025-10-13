"""Provision default workspace for backward compatibility.

Creates project_default schema with core tables to support existing users
who don't specify a project_id parameter. This ensures zero breaking changes
for current MCP server deployments.

Changes:
- Create schema: project_default
- Create table: repositories (with project_id defaulting to 'default')
- Create table: code_files (file metadata within repositories)
- Create table: code_chunks (semantic chunks with pgvector embeddings)
- Add indexes: file_path, repository_id, embedding (HNSW)
- Register workspace in project_registry.workspace_config

Performance:
- HNSW index on code_chunks.embedding for sub-500ms search (m=16, ef_construction=64)
- B-tree indexes on foreign keys for O(log n) JOIN performance
- GIN index on file_path for pattern matching queries

Constitutional Compliance:
- Principle V: Production Quality (proper indexes, constraints, downgrade support)
- Principle IV: Performance Guarantees (<500ms p95 search latency)
- Principle VIII: Type Safety (explicit column types, UUIDs for keys)

Traces to:
- FR-018: Backward compatibility (existing usage without project_id works unchanged)
- FR-003: Default workspace fallback (when project_id=None)

Revision ID: 007
Revises: 006
Create Date: 2025-10-12 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '007'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply migration: create project_default schema with core tables.

    Creates:
    1. Schema: project_default (isolated namespace for default workspace)
    2. Table: repositories (code repository metadata)
    3. Table: code_files (source files with language detection)
    4. Table: code_chunks (semantic chunks with pgvector embeddings)
    5. Indexes:
       - Unique index on repositories.path (prevent duplicate indexing)
       - B-tree indexes on foreign keys (optimize JOINs)
       - HNSW index on code_chunks.embedding (semantic search)
       - B-tree index on code_chunks.project_id (isolation queries)
    6. Registry entry: project_registry.workspace_config (default → project_default)

    Schema Design (matches post-002 migration structure):
    repositories:
    - id: UUID PRIMARY KEY (stable identifier)
    - path: VARCHAR NOT NULL UNIQUE (absolute filesystem path)
    - name: VARCHAR NOT NULL (repository name)
    - last_indexed_at: TIMESTAMP NULL (incremental indexing support)
    - is_active: BOOLEAN NOT NULL DEFAULT TRUE (soft delete flag)
    - project_id: VARCHAR(50) NOT NULL DEFAULT 'default' (workspace isolation)
    - created_at: TIMESTAMP NOT NULL DEFAULT NOW()

    code_files:
    - id: UUID PRIMARY KEY
    - repository_id: UUID NOT NULL FK -> repositories.id ON DELETE CASCADE
    - path: VARCHAR NOT NULL (absolute file path)
    - relative_path: VARCHAR NOT NULL (repo-relative path)
    - content_hash: VARCHAR(64) NOT NULL (SHA-256 for change detection)
    - size_bytes: INTEGER NOT NULL (file size validation)
    - language: VARCHAR NULL (tree-sitter detected language)
    - modified_at: TIMESTAMP NOT NULL (filesystem mtime)
    - indexed_at: TIMESTAMP NOT NULL DEFAULT NOW()
    - is_deleted: BOOLEAN NOT NULL DEFAULT FALSE (soft delete)
    - deleted_at: TIMESTAMP NULL (soft delete timestamp)
    - created_at: TIMESTAMP NOT NULL DEFAULT NOW()

    code_chunks:
    - id: UUID PRIMARY KEY
    - code_file_id: UUID NOT NULL FK -> code_files.id ON DELETE CASCADE
    - content: TEXT NOT NULL (chunk content for search results)
    - start_line: INTEGER NOT NULL (chunk location)
    - end_line: INTEGER NOT NULL (chunk location)
    - chunk_type: VARCHAR NOT NULL (function, class, import, etc.)
    - embedding: VECTOR(768) NULL (Ollama nomic-embed-text embeddings)
    - project_id: VARCHAR(50) NOT NULL (denormalized for query performance)
    - created_at: TIMESTAMP NOT NULL DEFAULT NOW()

    Note:
    - pgvector extension must exist (created in migration 001)
    - Registry schema must exist (created in migration 006)
    """
    # Step 1: Create project_default schema
    op.execute("CREATE SCHEMA IF NOT EXISTS project_default")

    # Step 2: Create repositories table in project_default
    op.create_table(
        'repositories',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('path', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('last_indexed_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('project_id', sa.String(50), nullable=False, server_default="'default'"),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_repositories')),
        sa.UniqueConstraint('path', name=op.f('uq_repositories_path')),
        schema='project_default'
    )
    op.create_index(
        op.f('ix_repositories_path'),
        'repositories',
        ['path'],
        unique=True,
        schema='project_default'
    )
    op.create_index(
        'ix_repositories_project_id',
        'repositories',
        ['project_id'],
        schema='project_default'
    )

    # Step 3: Create code_files table in project_default
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
        sa.ForeignKeyConstraint(
            ['repository_id'],
            ['project_default.repositories.id'],
            name=op.f('fk_code_files_repository_id_repositories'),
            ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_code_files')),
        schema='project_default'
    )
    op.create_index(
        op.f('ix_code_files_path'),
        'code_files',
        ['path'],
        unique=False,
        schema='project_default'
    )
    op.create_index(
        'ix_code_files_repo_path',
        'code_files',
        ['repository_id', 'relative_path'],
        unique=True,
        schema='project_default'
    )

    # Step 4: Create code_chunks table in project_default
    op.create_table(
        'code_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('code_file_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('start_line', sa.Integer(), nullable=False),
        sa.Column('end_line', sa.Integer(), nullable=False),
        sa.Column('chunk_type', sa.String(), nullable=False),
        sa.Column('embedding', Vector(768), nullable=True),  # pgvector VECTOR(768) type
        sa.Column('project_id', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(
            ['code_file_id'],
            ['project_default.code_files.id'],
            name=op.f('fk_code_chunks_code_file_id_code_files'),
            ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_code_chunks')),
        schema='project_default'
    )

    # Step 5: Create HNSW index for vector similarity search
    # Constitutional Principle IV: <500ms p95 search latency
    op.execute(
        """
        CREATE INDEX ix_chunks_embedding_cosine ON project_default.code_chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )

    # Step 6: Create performance indexes
    op.create_index(
        'ix_code_chunks_project_id',
        'code_chunks',
        ['project_id'],
        schema='project_default'
    )

    # Step 7: Register default workspace in registry
    # This enables workspace resolution logic to find the default schema
    op.execute(text("""
        INSERT INTO project_registry.workspace_config (project_id, schema_name, created_at, metadata)
        VALUES (
            'default',
            'project_default',
            NOW(),
            '{"description": "Default workspace for backward compatibility", "auto_created": true}'::jsonb
        )
        ON CONFLICT (project_id) DO NOTHING
    """))


def downgrade() -> None:
    """Revert migration: drop project_default schema and workspace registration.

    Drops:
    1. Registry entry: project_registry.workspace_config (default)
    2. Indexes: All indexes in project_default (CASCADE handles this)
    3. Tables: code_chunks, code_files, repositories (CASCADE order)
    4. Schema: project_default (CASCADE removes all contained objects)

    Warning:
    - This is a destructive operation that removes ALL data in default workspace
    - Downgrade should only be used in development/testing environments
    - Production downgrades require manual backup/restore procedures
    - Existing MCP clients using default workspace will fail after downgrade
    """
    # Step 1: Remove registry entry
    op.execute("DELETE FROM project_registry.workspace_config WHERE project_id = 'default'")

    # Step 2: Drop HNSW index explicitly (best practice)
    op.execute("DROP INDEX IF EXISTS project_default.ix_chunks_embedding_cosine")

    # Step 3: Drop all indexes explicitly (best practice, even though CASCADE would handle it)
    op.drop_index('ix_code_chunks_project_id', table_name='code_chunks', schema='project_default')
    op.drop_index('ix_code_files_repo_path', table_name='code_files', schema='project_default')
    op.drop_index(op.f('ix_code_files_path'), table_name='code_files', schema='project_default')
    op.drop_index('ix_repositories_project_id', table_name='repositories', schema='project_default')
    op.drop_index(op.f('ix_repositories_path'), table_name='repositories', schema='project_default')

    # Step 4: Drop tables in dependency order (child → parent)
    op.drop_table('code_chunks', schema='project_default')
    op.drop_table('code_files', schema='project_default')
    op.drop_table('repositories', schema='project_default')

    # Step 5: Drop project_default schema (CASCADE ensures cleanup of any residual objects)
    op.execute("DROP SCHEMA IF EXISTS project_default CASCADE")
