-- Registry Database Schema for Codebase MCP
--
-- This schema defines the central registry that tracks all project databases.
-- Each project gets its own isolated PostgreSQL database for complete isolation.
--
-- Architecture:
-- - codebase_mcp_registry (this database): Central registry tracking projects
-- - cb_proj_* (project databases): Isolated databases with repositories and code_chunks
--
-- Run this script ONCE to initialize the registry database:
--   psql -d codebase_mcp_registry -f scripts/init_registry_schema.sql

-- ============================================================================
-- Projects Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS projects (
    -- Unique identifier for the project
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Human-readable project name (unique)
    name VARCHAR(255) UNIQUE NOT NULL,

    -- Optional project description
    description TEXT,

    -- Physical database name for this project (unique)
    -- Format: cb_proj_{sanitized_name}_{uuid8}
    -- Example: cb_proj_codebase_mcp_abc123de
    database_name VARCHAR(255) UNIQUE NOT NULL,

    -- Timestamps for tracking
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Flexible metadata storage (JSON)
    -- Can store: owner, tags, data_classification, etc.
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Database name validation constraint
    -- Enforces naming convention: cb_proj_{name}_{hash}
    CONSTRAINT valid_database_name CHECK (
        database_name ~ '^cb_proj_[a-z0-9_]+_[a-f0-9]{8}$'
    ),

    -- Project name validation constraint
    -- Alphanumeric, spaces, hyphens, underscores only
    CONSTRAINT valid_name CHECK (
        name ~ '^[a-zA-Z0-9_ -]+$'
    )
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================

-- Fast lookup by name
CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name);

-- Fast lookup by creation time (newest first)
CREATE INDEX IF NOT EXISTS idx_projects_created ON projects(created_at DESC);

-- Fast JSONB metadata queries
CREATE INDEX IF NOT EXISTS idx_projects_metadata ON projects USING GIN(metadata);

-- ============================================================================
-- Triggers for Automatic Timestamp Updates
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger on projects table
DROP TRIGGER IF EXISTS update_projects_updated_at ON projects;
CREATE TRIGGER update_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Comments for Documentation
-- ============================================================================

COMMENT ON TABLE projects IS 'Central registry tracking all project databases';
COMMENT ON COLUMN projects.id IS 'Unique UUID identifier';
COMMENT ON COLUMN projects.name IS 'Human-readable project name (unique)';
COMMENT ON COLUMN projects.database_name IS 'Physical database name (cb_proj_*)';
COMMENT ON COLUMN projects.metadata IS 'Flexible JSONB storage for project metadata';

-- ============================================================================
-- Initial Status Report
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Codebase MCP Registry Schema Initialized';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Tables created:';
    RAISE NOTICE '  - projects';
    RAISE NOTICE '';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '  1. Use create_project() to provision new project databases';
    RAISE NOTICE '  2. Each project gets isolated database: cb_proj_{name}_{hash}';
    RAISE NOTICE '  3. MCP tools automatically switch databases based on config';
END $$;
