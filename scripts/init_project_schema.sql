-- Project Database Schema for Codebase MCP
--
-- This schema is applied to each isolated project database (cb_proj_*).
-- It contains tables for semantic code search: repositories, code_files, and code_chunks.
--
-- Run this automatically via database provisioning (do NOT run manually):
--   Used by: src/database/provisioning.py create_project_database()

-- ============================================================================
-- Extensions
-- ============================================================================

-- Enable pgvector for semantic code search
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- Repositories Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS repositories (
    -- Unique identifier for the repository
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Absolute path to repository on disk
    path VARCHAR NOT NULL UNIQUE,

    -- Repository name (extracted from path)
    name VARCHAR NOT NULL,

    -- Last successful indexing timestamp
    last_indexed_at TIMESTAMPTZ,

    -- Active flag (for soft delete)
    is_active BOOLEAN NOT NULL DEFAULT true,

    -- Creation timestamp
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Fast lookup by path
CREATE INDEX IF NOT EXISTS idx_repositories_path ON repositories(path);

-- Fast lookup by active status
CREATE INDEX IF NOT EXISTS idx_repositories_active ON repositories(is_active) WHERE is_active = true;

-- ============================================================================
-- Code Files Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS code_files (
    -- Unique identifier for the code file
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Repository relationship
    repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,

    -- Absolute path to file
    path VARCHAR NOT NULL,

    -- Relative path within repository
    relative_path VARCHAR NOT NULL,

    -- SHA-256 content hash for change detection
    content_hash VARCHAR(64) NOT NULL,

    -- File size in bytes
    size_bytes INTEGER NOT NULL,

    -- Programming language (detected from extension)
    language VARCHAR,

    -- File modification timestamp
    modified_at TIMESTAMPTZ NOT NULL,

    -- Indexing timestamp
    indexed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Soft delete support
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    deleted_at TIMESTAMPTZ,

    -- Creation timestamp
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Fast lookup by path
CREATE INDEX IF NOT EXISTS idx_code_files_path ON code_files(path);

-- Unique constraint on repository + relative_path
CREATE UNIQUE INDEX IF NOT EXISTS idx_code_files_repo_path
    ON code_files(repository_id, relative_path)
    WHERE is_deleted = false;

-- Fast lookup by repository
CREATE INDEX IF NOT EXISTS idx_code_files_repo ON code_files(repository_id);

-- Fast lookup by language
CREATE INDEX IF NOT EXISTS idx_code_files_language ON code_files(language);

-- ============================================================================
-- Code Chunks Table (Semantic Search)
-- ============================================================================

CREATE TABLE IF NOT EXISTS code_chunks (
    -- Unique identifier for the chunk
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Code file relationship
    code_file_id UUID NOT NULL REFERENCES code_files(id) ON DELETE CASCADE,

    -- Code content (plain text)
    content TEXT NOT NULL,

    -- Line range in source file
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,

    -- Chunk type (function, class, module, etc.)
    chunk_type VARCHAR NOT NULL,

    -- Semantic embedding vector (768-dimensional for nomic-embed-text)
    embedding vector(768),

    -- Creation timestamp
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Validation constraints
    CONSTRAINT valid_line_range CHECK (start_line > 0 AND end_line >= start_line)
);

-- HNSW index for fast cosine similarity search (pgvector)
-- m=16: number of bi-directional links per node
-- ef_construction=64: exploration depth during index build
CREATE INDEX IF NOT EXISTS idx_code_chunks_embedding_cosine
    ON code_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Fast lookup by file
CREATE INDEX IF NOT EXISTS idx_code_chunks_file ON code_chunks(code_file_id);

-- Fast lookup by chunk type
CREATE INDEX IF NOT EXISTS idx_code_chunks_type ON code_chunks(chunk_type);

-- ============================================================================
-- Comments for Documentation
-- ============================================================================

COMMENT ON TABLE repositories IS 'Indexed code repositories';
COMMENT ON TABLE code_files IS 'Individual code files within repositories';
COMMENT ON TABLE code_chunks IS 'Semantic code chunks with vector embeddings';

COMMENT ON COLUMN code_chunks.embedding IS '768-dim vector for semantic search (nomic-embed-text)';
COMMENT ON INDEX idx_code_chunks_embedding_cosine IS 'HNSW index for fast cosine similarity search';

-- ============================================================================
-- Initial Status Report
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Codebase MCP Project Schema Initialized';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Tables created:';
    RAISE NOTICE '  - repositories';
    RAISE NOTICE '  - code_files';
    RAISE NOTICE '  - code_chunks (with vector embeddings)';
    RAISE NOTICE '';
    RAISE NOTICE 'Extensions enabled:';
    RAISE NOTICE '  - pgvector (for semantic search)';
    RAISE NOTICE '';
    RAISE NOTICE 'Ready for code indexing and semantic search!';
END $$;
