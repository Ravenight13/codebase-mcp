-- Codebase MCP Database Initialization
-- Run this once: psql -d codebase_mcp -f init_tables.sql

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 1. Repositories table
CREATE TABLE IF NOT EXISTS repositories (
    id UUID PRIMARY KEY,
    path VARCHAR NOT NULL UNIQUE,
    name VARCHAR NOT NULL,
    last_indexed_at TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_repositories_path ON repositories(path);

-- 2. Code files table
CREATE TABLE IF NOT EXISTS code_files (
    id UUID PRIMARY KEY,
    repository_id UUID NOT NULL REFERENCES repositories(id),
    path VARCHAR NOT NULL,
    relative_path VARCHAR NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    size_bytes INTEGER NOT NULL,
    language VARCHAR,
    modified_at TIMESTAMP NOT NULL,
    indexed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    deleted_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_code_files_path ON code_files(path);
CREATE UNIQUE INDEX IF NOT EXISTS ix_code_files_repo_path ON code_files(repository_id, relative_path);

-- 3. Code chunks table (with vector embeddings)
CREATE TABLE IF NOT EXISTS code_chunks (
    id UUID PRIMARY KEY,
    code_file_id UUID NOT NULL REFERENCES code_files(id),
    content TEXT NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    chunk_type VARCHAR NOT NULL,
    embedding vector(768),  -- 768-dim vectors for nomic-embed-text
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- HNSW index for fast vector similarity search
CREATE INDEX IF NOT EXISTS ix_chunks_embedding_cosine ON code_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- 4. Tasks table
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY,
    title VARCHAR NOT NULL,
    description TEXT,
    notes TEXT,
    status VARCHAR NOT NULL DEFAULT 'need to be done'
        CHECK (status IN ('need to be done', 'in-progress', 'complete')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_tasks_status ON tasks(status);

-- 5. Task planning references
CREATE TABLE IF NOT EXISTS task_planning_references (
    id UUID PRIMARY KEY,
    task_id UUID NOT NULL REFERENCES tasks(id),
    file_path VARCHAR NOT NULL,
    reference_type VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 6. Task branch links
CREATE TABLE IF NOT EXISTS task_branch_links (
    id UUID PRIMARY KEY,
    task_id UUID NOT NULL REFERENCES tasks(id),
    branch_name VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_branch_links_task_branch ON task_branch_links(task_id, branch_name);

-- 7. Task commit links
CREATE TABLE IF NOT EXISTS task_commit_links (
    id UUID PRIMARY KEY,
    task_id UUID NOT NULL REFERENCES tasks(id),
    commit_hash VARCHAR(40) NOT NULL,
    commit_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_commit_links_task_commit ON task_commit_links(task_id, commit_hash);

-- 8. Task status history
CREATE TABLE IF NOT EXISTS task_status_history (
    id UUID PRIMARY KEY,
    task_id UUID NOT NULL REFERENCES tasks(id),
    from_status VARCHAR,
    to_status VARCHAR NOT NULL,
    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_task_status_history_changed_at ON task_status_history(changed_at);

-- 9. Change events (for incremental indexing)
CREATE TABLE IF NOT EXISTS change_events (
    id UUID PRIMARY KEY,
    code_file_id UUID NOT NULL REFERENCES code_files(id),
    event_type VARCHAR NOT NULL,
    detected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN NOT NULL DEFAULT false
);
CREATE INDEX IF NOT EXISTS ix_change_events_detected_at ON change_events(detected_at);

-- 10. Embedding metadata (analytics)
CREATE TABLE IF NOT EXISTS embedding_metadata (
    id UUID PRIMARY KEY,
    model_name VARCHAR NOT NULL DEFAULT 'nomic-embed-text',
    model_version VARCHAR,
    dimensions INTEGER NOT NULL DEFAULT 768,
    generation_time_ms INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 11. Search queries (analytics)
CREATE TABLE IF NOT EXISTS search_queries (
    id UUID PRIMARY KEY,
    query_text TEXT NOT NULL,
    result_count INTEGER NOT NULL,
    latency_ms INTEGER NOT NULL,
    filters JSON,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_search_queries_created_at ON search_queries(created_at);

-- Done
\echo 'Database initialized successfully!'
\echo 'Tables: 11'
\echo 'Indexes: 13'
\echo 'Extensions: vector'
