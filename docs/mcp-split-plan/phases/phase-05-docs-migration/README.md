# Phase 05: Documentation & Migration

**Phase**: 05 - Documentation & Migration (Phases 9-10 from FINAL-IMPLEMENTATION-PLAN.md)
**Duration**: 3-4 hours
**Dependencies**: Phase 04 (connection management implemented)
**Status**: Planned

---

## Objective

Update all documentation to reflect refactored architecture and create migration guide for users upgrading from v1.x.

---

## Scope

### What's Included

- **Updated README.md**
  - Reflect 2 tools (not 16)
  - Multi-project support explanation
  - workflow-mcp integration (optional)
  - Updated installation instructions

- **API Documentation**
  - Document `index_repository` with project_id
  - Document `search_code` with project_id
  - Remove documentation for deleted tools

- **Migration Guide**
  - v1.x → v2.0 migration steps
  - Database migration instructions
  - Breaking changes explained
  - Rollback procedures

- **Configuration Guide**
  - Environment variables (MAX_PROJECTS, etc.)
  - PostgreSQL configuration (max_connections)
  - Connection pool tuning

- **Architecture Documentation**
  - Multi-project architecture diagram
  - Database-per-project explanation
  - Connection pool design

### What's NOT Included

- Performance benchmarks (Phase 06)
- Release notes (Phase 07)
- Changelog updates (Phase 07)

---

## Key Deliverables

1. **Updated README.md**:
   - Overview of refactored MCP
   - Installation guide
   - Quick start examples

2. **Migration Guide**: `docs/migration/v1-to-v2.md`
   - Breaking changes
   - Step-by-step migration
   - Rollback instructions

3. **Configuration Guide**: `docs/configuration.md`
   - Environment variables
   - PostgreSQL tuning
   - Production recommendations

4. **Architecture Docs**: `docs/architecture/`
   - Multi-project architecture
   - Connection pool design
   - Database naming strategy

5. **API Reference**: `docs/api/`
   - Tool signatures
   - Parameter descriptions
   - Example usage

---

## Acceptance Criteria

- [ ] README.md updated (2 tools, multi-project)
- [ ] Migration guide created (v1.x → v2.0)
- [ ] Configuration guide created (env vars, PostgreSQL)
- [ ] Architecture docs updated (multi-project, pools)
- [ ] API reference updated (index_repository, search_code)
- [ ] All documentation links working (no 404s)
- [ ] Examples tested and working
- [ ] No references to deleted tools
- [ ] Git commit: "docs: update documentation for v2.0 refactoring"

---

## Migration Guide Structure

### Breaking Changes

1. **Removed Tools**: 14 tools removed (list them)
2. **Database Schema**: 9 tables dropped, project_id added
3. **API Changes**: project_id parameter added to both tools
4. **Configuration**: New environment variables

### Migration Steps

```markdown
## Migration Steps

### 1. Backup Current State

```bash
# Backup database
pg_dump codebase_mcp > backup-v1.sql

# Backup configuration
cp .env .env.backup
```

### 2. Update codebase-mcp

```bash
git pull origin main
git checkout v2.0.0
pip install -e .
```

### 3. Run Migration Script

```bash
psql -d codebase_mcp -f migrations/002_remove_non_search_tables.sql
```

### 4. Update Configuration

```bash
# Add new environment variables
echo "MAX_PROJECTS=10" >> .env
echo "MAX_CONNECTIONS_PER_POOL=20" >> .env
```

### 5. Test Multi-Project

```bash
# Index with default project
index_repository project_id="default" repo_path="/path/to/repo"

# Create new project database
index_repository project_id="my-app" repo_path="/path/to/app"
```

### 6. Rollback (if needed)

```bash
# Restore database
dropdb codebase_mcp
createdb codebase_mcp
psql -d codebase_mcp < backup-v1.sql

# Restore configuration
mv .env.backup .env

# Rollback code
git checkout v1.x
pip install -e .
```
```

---

## Configuration Documentation

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | `localhost` | PostgreSQL host |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_USER` | `postgres` | PostgreSQL user (needs CREATEDB) |
| `POSTGRES_PASSWORD` | (none) | PostgreSQL password |
| `MAX_PROJECTS` | `10` | Max concurrent connection pools |
| `MAX_CONNECTIONS_PER_POOL` | `20` | Max connections per pool |
| `WORKFLOW_MCP_URL` | (none) | workflow-mcp URL (optional) |
| `WORKFLOW_MCP_TIMEOUT` | `5` | workflow-mcp timeout (seconds) |

### PostgreSQL Configuration

**For production deployments**:

```postgresql
# postgresql.conf
max_connections = 300  # Must exceed MAX_PROJECTS * MAX_CONNECTIONS_PER_POOL
shared_buffers = 256MB  # Or 25% of RAM
effective_cache_size = 1GB  # Or 50% of RAM
work_mem = 16MB
maintenance_work_mem = 128MB
```

---

## Architecture Diagrams

### Multi-Project Architecture

```
┌─────────────────────────────────────────────────────┐
│                   codebase-mcp                      │
│                                                     │
│  ┌────────────────┐      ┌────────────────┐       │
│  │ index_repository│      │  search_code   │       │
│  └────────┬───────┘      └────────┬───────┘       │
│           │                       │                │
│           └───────────┬───────────┘                │
│                       │                            │
│           ┌───────────▼───────────┐                │
│           │  Connection Pool Mgr  │                │
│           │  (LRU, MAX_PROJECTS)  │                │
│           └───────────┬───────────┘                │
└───────────────────────┼────────────────────────────┘
                        │
          ┌─────────────┼─────────────┐
          │             │             │
    ┌─────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐
    │codebase_  │ │codebase_  │ │codebase_  │
    │ default   │ │  my-app   │ │ project-x │
    │           │ │           │ │           │
    │- repos    │ │- repos    │ │- repos    │
    │- chunks   │ │- chunks   │ │- chunks   │
    └───────────┘ └───────────┘ └───────────┘
       PostgreSQL Database Server
```

---

## Example Usage

### Basic Usage (Default Project)

```python
# Index repository
await index_repository(
    repo_path="/path/to/repo"
)  # Uses project_id="default"

# Search code
results = await search_code(
    query="async function handler"
)  # Uses project_id="default"
```

### Multi-Project Usage

```python
# Index app repository
await index_repository(
    project_id="my-app",
    repo_path="/path/to/my-app"
)

# Index library repository (different project)
await index_repository(
    project_id="my-library",
    repo_path="/path/to/my-library"
)

# Search in specific project
results = await search_code(
    project_id="my-app",
    query="database connection"
)  # Only searches my-app database
```

---

## Rollback Procedure

No rollback needed - documentation changes only.

If documentation is incorrect:
```bash
git checkout 002-refactor-pure-search
git reset --hard <commit-before-phase-05>
```

---

## Next Phase

After completing Phase 05:
- Verify all documentation accurate
- Test migration guide steps
- Navigate to `../phase-06-performance/`
- Ready for performance validation

---

## Related Documentation

- **Phases 9-10 details**: See `../../_archive/01-codebase-mcp/FINAL-IMPLEMENTATION-PLAN.md` lines 2135-2142
- **Recommendation R2**: PostgreSQL configuration (documented)
- **User stories**: See `../../_archive/01-codebase-mcp/user-stories.md`

---

**Status**: Planned
**Last Updated**: 2025-10-11
**Estimated Time**: 3-4 hours
