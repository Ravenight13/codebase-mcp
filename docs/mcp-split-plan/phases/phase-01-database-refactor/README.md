# Phase 01: Database Refactoring

**Phase**: 01 - Database Refactoring (Phase 2 from FINAL-IMPLEMENTATION-PLAN.md)
**Duration**: 4-6 hours
**Dependencies**: Phase 00 (baseline established, branch created)
**Status**: Planned

---

## Objective

Remove non-search database tables and add multi-project support column to remaining tables.

This phase:
1. Drops 9 database tables (work_items, tasks, vendors, deployments, etc.)
2. Adds `project_id` column to `repositories` and `code_chunks` tables
3. Creates migration script with proper validation and constraints
4. Ensures schema changes are reversible

---

## Scope

### What's Included

- **Migration Script Creation**
  - Drop 9 non-search tables (work_items, tasks, vendors, etc.)
  - Add `project_id VARCHAR(50) NOT NULL DEFAULT 'default'` to `repositories`
  - Add `project_id VARCHAR(50) NOT NULL` to `code_chunks`
  - Add check constraint: `CHECK (project_id ~ '^[a-z0-9-]{1,50}$')`
  - Create index on `(project_id, repository_id)` for search performance

- **Schema Validation**
  - Pydantic model for project_id validation
  - SQL injection prevention tests
  - Schema consistency verification

- **Migration Testing**
  - Test migration script on copy of database
  - Verify constraint enforcement
  - Test rollback script

### What's NOT Included

- Removing code that references dropped tables (that's Phase 02)
- Connection pool implementation (that's Phase 04)
- Multi-project search/indexing logic (that's Phase 03)

---

## Prerequisites

- Phase 00 completed (baseline established)
- Feature branch `002-refactor-pure-search` active
- Database backup exists (`backups/backup-before-002.sql`)
- Git tag `pre-refactor` created

---

## Key Deliverables

1. **Migration Script**: `migrations/002_remove_non_search_tables.sql`
   - DROP TABLE statements for 9 tables
   - ALTER TABLE statements for project_id
   - CREATE INDEX statements
   - Comprehensive comments

2. **Rollback Script**: `migrations/002_rollback.sql`
   - Reverse project_id changes
   - Cannot restore dropped tables (use database backup)

3. **Validation Script**: `migrations/002_validate.sql`
   - Verify tables dropped
   - Verify project_id columns exist
   - Verify constraints active

4. **Schema Tests**: `tests/test_schema_002.py`
   - Test project_id constraint enforcement
   - Test SQL injection attempts blocked
   - Test index existence

---

## Acceptance Criteria

- [ ] Migration script created and reviewed
- [ ] Migration tested on database copy (success)
- [ ] Rollback script tested (success)
- [ ] 9 tables dropped: work_items, tasks, vendors, etc.
- [ ] `repositories` table has project_id column with default 'default'
- [ ] `code_chunks` table has project_id column (not nullable)
- [ ] Check constraint enforces: `^[a-z0-9-]{1,50}$`
- [ ] Index created on `(project_id, repository_id)`
- [ ] Schema tests pass (constraint validation, SQL injection blocked)
- [ ] Git commit: "refactor(schema): remove non-search tables, add project_id"

---

## Tables to Drop

1. `work_items` - Project/session/task/research hierarchy
2. `work_item_dependencies` - Dependency relationships
3. `tasks` - Legacy task tracking
4. `task_branches` - Task git branches
5. `task_commits` - Task git commits
6. `vendors` - Commission extraction vendors
7. `vendor_test_results` - Vendor test outcomes
8. `deployments` - Deployment events
9. `deployment_vendors` - Deployment vendor relationships

**Total**: 9 tables removed

---

## Tables to Modify

1. **`repositories`**
   - Add: `project_id VARCHAR(50) NOT NULL DEFAULT 'default'`
   - Constraint: CHECK (project_id ~ '^[a-z0-9-]{1,50}$')
   - Index: (project_id, id)

2. **`code_chunks`**
   - Add: `project_id VARCHAR(50) NOT NULL`
   - Constraint: CHECK (project_id ~ '^[a-z0-9-]{1,50}$')
   - Index: (project_id, repository_id)

**Total**: 2 tables modified

---

## Rollback Procedure

### If Migration Fails

```bash
# Rollback schema changes
psql -U your_user -d codebase_mcp -f migrations/002_rollback.sql

# Or restore from backup
dropdb codebase_mcp
createdb codebase_mcp
psql -U your_user -d codebase_mcp < backups/backup-before-002.sql
```

### If Phase Needs Abort

```bash
# Restore database
dropdb codebase_mcp
createdb codebase_mcp
psql -U your_user -d codebase_mcp < backups/backup-before-002.sql

# Reset branch
git checkout 002-refactor-pure-search
git reset --hard HEAD~N  # N = number of commits to undo
```

---

## Execution Notes

### Project ID Validation Pattern

The regex `^[a-z0-9-]{1,50}$` enforces:
- Lowercase letters only (a-z)
- Numbers allowed (0-9)
- Hyphens allowed (-)
- Length: 1-50 characters
- No spaces, underscores, or special characters

**Examples**:
- Valid: `default`, `my-project`, `commission-extraction-2024`
- Invalid: `My_Project`, `test project`, `a`, `toolongprojectnamewithmorethanfiftycharacters`

### Testing Migration

```bash
# Create test database
createdb codebase_mcp_test
pg_dump codebase_mcp | psql codebase_mcp_test

# Run migration on test
psql -U your_user -d codebase_mcp_test -f migrations/002_remove_non_search_tables.sql

# Verify changes
psql -U your_user -d codebase_mcp_test -f migrations/002_validate.sql

# If successful, run on production
psql -U your_user -d codebase_mcp -f migrations/002_remove_non_search_tables.sql

# Clean up test
dropdb codebase_mcp_test
```

---

## Next Phase

After completing Phase 01:
- Verify all acceptance criteria met
- Commit migration scripts and schema tests
- Navigate to `../phase-02-remove-tools/`
- Database schema now ready for code cleanup

---

## Related Documentation

- **Phase 2 details**: See `../../_archive/01-codebase-mcp/FINAL-IMPLEMENTATION-PLAN.md` lines 1864-1971
- **Database design**: See `../../_archive/shared-architecture/00-architecture/database-design.md`
- **Critical Issue C1**: Database naming strategy (resolved in FINAL-IMPLEMENTATION-PLAN.md)

---

**Status**: Planned
**Last Updated**: 2025-10-11
**Estimated Time**: 4-6 hours
