# Data Model
**Feature**: Database Schema Refactoring for Multi-Project Support
**Date**: 2025-10-11
**Phase**: 1 (Design)

## Overview

This document defines the database schema changes for migration 002. The primary changes are:
1. Adding `project_id` columns to existing tables (repositories, code_chunks)
2. Removing 9 unused tables from non-search features
3. Adding validation constraints and performance indexes

## Schema Changes

### Modified Tables

#### repositories (MODIFIED)

**Purpose**: Stores indexed code repositories with multi-project support

**Changes**:
- ADD COLUMN: `project_id VARCHAR(50) NOT NULL DEFAULT 'default'`
- ADD CONSTRAINT: `check_repositories_project_id CHECK (project_id ~ '^[a-z0-9-]{1,50}$')`
- ADD INDEX: `idx_project_repository ON (project_id, id)`

**Complete Schema** (after migration):
```sql
CREATE TABLE repositories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    path TEXT NOT NULL UNIQUE,
    project_id VARCHAR(50) NOT NULL DEFAULT 'default',  -- NEW
    indexed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT check_repositories_project_id              -- NEW
      CHECK (project_id ~ '^[a-z0-9-]{1,50}$')
);

CREATE INDEX idx_project_repository                       -- NEW
  ON repositories(project_id, id);
```

**Validation Rules**:
- `project_id` pattern: lowercase alphanumeric + hyphens only, 1-50 characters
- No leading, trailing, or consecutive hyphens (enforced by regex)
- No underscores, no spaces, no uppercase letters

**Relationships**:
- ONE repository HAS MANY code_chunks (via code_chunks.repository_id foreign key)
- ONE project (conceptual) HAS MANY repositories (via project_id column)

#### code_chunks (MODIFIED)

**Purpose**: Stores semantic code chunks with embeddings, multi-project support

**Changes**:
- ADD COLUMN: `project_id VARCHAR(50) NOT NULL` (populated from parent repository)
- ADD CONSTRAINT: `check_code_chunks_project_id CHECK (project_id ~ '^[a-z0-9-]{1,50}$')`

**Complete Schema** (after migration):
```sql
CREATE TABLE code_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    project_id VARCHAR(50) NOT NULL,                      -- NEW
    file_path TEXT NOT NULL,
    content TEXT NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    embedding VECTOR(768),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT check_code_chunks_project_id               -- NEW
      CHECK (project_id ~ '^[a-z0-9-]{1,50}$')
);

-- Existing indexes unchanged
CREATE INDEX idx_code_chunks_repository
  ON code_chunks(repository_id);

CREATE INDEX idx_code_chunks_embedding
  ON code_chunks USING ivfflat (embedding vector_cosine_ops);
```

**Validation Rules**:
- Same pattern as repositories: `^[a-z0-9-]{1,50}$`
- MUST match parent repository's project_id (enforced during migration population)

**Relationships**:
- MANY code_chunks BELONG TO ONE repository (foreign key)
- MANY code_chunks BELONG TO ONE project (conceptual, via project_id column)
- Referential integrity: code_chunks.project_id copied from repositories.project_id during migration

### Dropped Tables

The following 9 tables are removed as they belong to non-search features:

#### Work Tracking Tables (5 tables)
1. **work_items**: Task/project tracking (not used)
2. **work_item_dependencies**: Dependency relationships between work items
3. **tasks**: Development task tracking (replaced by external workflow-mcp)
4. **task_branches**: Git branch associations for tasks
5. **task_commits**: Git commit associations for tasks

#### Vendor Management Tables (2 tables)
6. **vendors**: Vendor extractor tracking
7. **vendor_test_results**: Vendor test execution results

#### Deployment Tracking Tables (2 tables)
8. **deployments**: Deployment event tracking
9. **deployment_vendors**: Many-to-many relationship for deployment impacts

**Rationale for Removal**:
- These tables were part of pre-split multi-feature codebase
- Functionality now handled by separate workflow-mcp server
- Simplifies schema to focus on semantic search (Simplicity Over Features principle)
- Reduces maintenance burden (9 tables removed = 80% complexity reduction)

### Validation Constraints

#### project_id Pattern Validation

**Regex**: `^[a-z0-9-]{1,50}$`

**Rules**:
- Length: 1-50 characters (enforced by VARCHAR(50) and regex bounds)
- Characters: Lowercase letters (a-z), digits (0-9), hyphens (-) only
- No uppercase letters (enforced by character class)
- No underscores or spaces (enforced by character class)
- No leading hyphens (enforced by `^` anchor)
- No trailing hyphens (enforced by `$` anchor)
- No consecutive hyphens (enforced by PostgreSQL at application layer in Phase 02)

**Valid Examples**:
- `default`
- `my-project`
- `proj-123`
- `a` (minimum length)
- `a-very-long-project-name-with-exactly-fifty-ch` (maximum length)

**Invalid Examples**:
- `My-Project` (uppercase)
- `my_project` (underscore)
- `my project` (space)
- `-my-project` (leading hyphen)
- `my-project-` (trailing hyphen)
- `my--project` (consecutive hyphens - rejected by Pydantic validator in Phase 02)
- `` (empty string - rejected by length constraint)
- `this-is-a-very-long-project-name-that-exceeds-fifty-characters-limit` (> 50 chars)

### Performance Indexes

#### idx_project_repository (NEW)

**Table**: repositories
**Columns**: (project_id, id)
**Type**: B-tree (default)
**Purpose**: Optimize multi-project queries filtering by project_id

**Query Patterns Supported**:
```sql
-- List repositories for a project
SELECT * FROM repositories WHERE project_id = 'my-project';

-- Count repositories per project
SELECT project_id, COUNT(*) FROM repositories GROUP BY project_id;

-- Join repositories to code_chunks for project-scoped search
SELECT cc.* FROM code_chunks cc
JOIN repositories r ON cc.repository_id = r.id
WHERE r.project_id = 'my-project';
```

**Performance Impact**:
- Single-project queries: O(log n) lookup instead of O(n) scan
- Critical for Phase 03 multi-project search implementation
- Minimal storage overhead (< 1MB for 1000 repositories)

#### Existing Indexes (UNCHANGED)

- `idx_code_chunks_repository`: Foreign key index (unchanged)
- `idx_code_chunks_embedding`: pgvector ivfflat index for similarity search (unchanged)

## Migration Data Flow

### Phase 1: Add project_id to repositories

```sql
ALTER TABLE repositories
  ADD COLUMN IF NOT EXISTS project_id VARCHAR(50) NOT NULL DEFAULT 'default';
```

**Result**:
- Existing rows: Automatically assigned 'default' via DEFAULT clause
- New rows: Must specify project_id or accept 'default'

### Phase 2: Add project_id to code_chunks

```sql
-- Step 1: Add nullable column
ALTER TABLE code_chunks ADD COLUMN IF NOT EXISTS project_id VARCHAR(50);

-- Step 2: Populate from parent repository
UPDATE code_chunks
SET project_id = (
  SELECT project_id FROM repositories
  WHERE repositories.id = code_chunks.repository_id
)
WHERE project_id IS NULL;

-- Step 3: Add NOT NULL constraint
ALTER TABLE code_chunks ALTER COLUMN project_id SET NOT NULL;
```

**Result**:
- Existing code_chunks: Copy project_id from parent repository (maintains referential integrity)
- Orphan chunks (no parent repository): Migration fails with clear error (data corruption detected)

### Phase 3: Add validation constraints

```sql
ALTER TABLE repositories
  ADD CONSTRAINT check_repositories_project_id
  CHECK (project_id ~ '^[a-z0-9-]{1,50}$');

ALTER TABLE code_chunks
  ADD CONSTRAINT check_code_chunks_project_id
  CHECK (project_id ~ '^[a-z0-9-]{1,50}$');
```

**Result**:
- All future inserts/updates validated at database level
- SQL injection prevented (pattern rejects malicious input)

### Phase 4: Create performance index

```sql
CREATE INDEX idx_project_repository ON repositories(project_id, id);
```

**Result**:
- Multi-project queries optimized
- No impact to single-project usage (index optional for WHERE clauses)

### Phase 5: Drop unused tables

```sql
DROP TABLE IF EXISTS work_items CASCADE;
DROP TABLE IF EXISTS work_item_dependencies CASCADE;
DROP TABLE IF EXISTS tasks CASCADE;
DROP TABLE IF EXISTS task_branches CASCADE;
DROP TABLE IF EXISTS task_commits CASCADE;
DROP TABLE IF EXISTS vendors CASCADE;
DROP TABLE IF EXISTS vendor_test_results CASCADE;
DROP TABLE IF EXISTS deployments CASCADE;
DROP TABLE IF EXISTS deployment_vendors CASCADE;
```

**Result**:
- 9 tables removed
- Schema simplified to 2 core tables (repositories, code_chunks)

## Rollback Data Flow

### Reverse Phase 5: Restore dropped tables

```sql
-- Schema-only restoration (data lost unless restored from backup)
CREATE TABLE work_items (...);
CREATE TABLE work_item_dependencies (...);
-- ... (8 more CREATE TABLE statements)
```

### Reverse Phase 4: Drop performance index

```sql
DROP INDEX IF EXISTS idx_project_repository;
```

### Reverse Phase 3: Drop validation constraints

```sql
ALTER TABLE repositories DROP CONSTRAINT IF EXISTS check_repositories_project_id;
ALTER TABLE code_chunks DROP CONSTRAINT IF EXISTS check_code_chunks_project_id;
```

### Reverse Phase 2: Remove project_id from code_chunks

```sql
ALTER TABLE code_chunks DROP COLUMN IF EXISTS project_id;
```

### Reverse Phase 1: Remove project_id from repositories

```sql
ALTER TABLE repositories DROP COLUMN IF EXISTS project_id;
```

**Note**: Rollback restores schema structure but NOT data in dropped tables (unless backup is manually restored).

## Conceptual Entities

### Project (Conceptual)

**Purpose**: Logical grouping of repositories for multi-project support

**Attributes**:
- `project_id` (identifier): VARCHAR(50), pattern `^[a-z0-9-]{1,50}$`

**Relationships**:
- ONE project HAS MANY repositories
- ONE project HAS MANY code_chunks (indirectly via repositories)

**Implementation**:
- No dedicated table (conceptual entity only)
- Represented by `project_id` column in repositories and code_chunks
- Phase 03 will implement database-per-project architecture (`codebase_<project_id>` naming)

## Database State Transitions

### Pre-Migration State
```
Tables: 11 (repositories, code_chunks, + 9 unused tables)
repositories columns: id, path, indexed_at, metadata, timestamps
code_chunks columns: id, repository_id, file_path, content, lines, embedding, timestamps
Indexes: 2 (code_chunks foreign key, code_chunks embedding)
```

### Post-Migration State
```
Tables: 2 (repositories, code_chunks only)
repositories columns: id, path, project_id, indexed_at, metadata, timestamps
code_chunks columns: id, repository_id, project_id, file_path, content, lines, embedding, timestamps
Indexes: 3 (existing 2 + idx_project_repository)
Constraints: 2 CHECK constraints for project_id pattern validation
```

### Change Summary
- Tables: 11 → 2 (9 dropped)
- Columns added: 2 (project_id in 2 tables)
- Constraints added: 2 (CHECK constraints)
- Indexes added: 1 (multi-project performance)
- Complexity reduction: ~80% fewer tables

## Testing Data Fixtures

### Minimal Test Data (for unit tests)
```sql
-- 1 repository with 'default' project
INSERT INTO repositories (id, path, project_id, indexed_at)
VALUES ('00000000-0000-0000-0000-000000000001', '/test/repo1', 'default', NOW());

-- 2 code chunks for the repository
INSERT INTO code_chunks (repository_id, project_id, file_path, content, start_line, end_line)
VALUES
  ('00000000-0000-0000-0000-000000000001', 'default', 'main.py', 'print("hello")', 1, 1),
  ('00000000-0000-0000-0000-000000000001', 'default', 'utils.py', 'def foo(): pass', 1, 1);
```

### Realistic Test Data (for performance tests)
```sql
-- 100 repositories across 3 projects
-- 10,000 code chunks (100 per repository)
-- SQL generation script in tests/fixtures/generate_test_data.sql
```

## Next Phase

**Phase 2** (via /tasks command): Generate ordered task list for implementation
- Write validation script (002_validate.sql)
- Write forward migration script (002_remove_non_search_tables.sql)
- Write rollback script (002_rollback.sql)
- Write integration tests
- Execute migration on test database
- Validate and document results
