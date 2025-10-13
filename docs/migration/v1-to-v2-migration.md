# Migration Guide: v1.x to v2.0

## Overview

This guide provides step-by-step instructions for safely upgrading an existing Codebase MCP Server v1.x installation to v2.0. The v2.0 release represents a major architectural change focused on semantic code search capabilities, with significant breaking changes. For complete v2.0 feature overview, see [README](../../README.md).

**Purpose**: Enable existing v1.x users to migrate to v2.0 with minimal downtime and data preservation where applicable.

**Scope**: This guide covers database-per-project migration, tool API changes, and environment variable updates for production installations.

**Target Audience**: System administrators, DevOps engineers, and development teams managing v1.x installations.

**Glossary Reference**: For terminology used in this guide, see the [Glossary](../glossary.md) for canonical definitions of project ID, connection pool, and other multi-project architecture terms.

**Data Preservation Policy**:
- ✅ **Preserved**: All indexed repositories and code embeddings remain searchable after migration
- ❌ **Discarded**: All v1.x project management data, entities, and work items are permanently removed
- ℹ️ **Rationale**: Project/entity/work item features have been extracted to the separate [workflow-mcp](https://github.com/workflow-mcp) server

---

## Breaking Changes Summary

The following changes are breaking and require action during migration:

### Tool API Changes

In v2.0, 14 tools have been removed entirely as part of the workflow-mcp server extraction, and 2 remaining tools have been modified with the addition of a `project_id` parameter for multi-project workspace support.

**Modified Tools**:
- **`index_repository`**: Now accepts optional `project_id` parameter for workspace isolation. If not provided, repositories are indexed in the default workspace.
- **`search_code`**: Now accepts optional `project_id` parameter to restrict searches to a specific project workspace. If not provided, searches use the default workspace.

All other v1.x tools related to project management, entities, and work items have been removed (see "Removed Tools" section below).

### Database Schema Changes

The v2.0 database schema has been significantly simplified to focus on semantic code search capabilities:

**Dropped Tables** (9 v1.x tables removed entirely):
- `projects`
- `project_sessions`
- `entity_types`
- `entities`
- `work_items`
- `work_item_dependencies`
- `deployments`
- `deployment_entities`
- `deployment_work_items`

**Schema Modifications**:
- `project_id` column added to `repositories` table to support multi-project workspace isolation
- `project_id` column added to `file_chunks` table to scope embeddings to project workspaces
- All other tables remain unchanged from v1.x structure

### Environment Variable Changes

Three new optional environment variables have been added in v2.0 to support workflow-mcp integration and multi-project workspace features:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `WORKFLOW_MCP_URL` | Optional | *(none)* | Optional workflow-mcp server URL for automatic project detection. Enables automatic project ID resolution from Git repository context. See [Glossary](../glossary.md#project_id) for project ID definition. |
| `WORKFLOW_MCP_TIMEOUT` | Optional | `1.0` | Timeout for workflow-mcp queries (seconds). Controls how long to wait for project context resolution. Valid range: 0.1-5.0. |
| `WORKFLOW_MCP_CACHE_TTL` | Optional | `60` | Cache TTL for workflow-mcp responses (seconds). Reduces query overhead for repeated repository checks. Valid range: 10-300. |

All v1.x environment variables remain unchanged and functional in v2.0. See the "Environment Variables" section in the documentation for complete details.

### Data Preservation Policy

> **Warning: Permanent Data Loss**
>
> All v1.x project management data will be **permanently lost** during migration. The following data types will be discarded:
> - Projects and project sessions
> - Entity types and entity instances
> - Work items and work item dependencies
> - Deployments and deployment relationships
>
> **What's Preserved**:
> - Indexed repositories and their metadata
> - Code embeddings (semantic search vectors)
> - Search functionality and performance characteristics
>
> **What's Discarded**:
> - All project management, entity tracking, and work item data
> - Historical deployment records
>
> **Rationale**: Project/entity/work item features have been extracted to the separate [workflow-mcp](https://github.com/workflow-mcp) server to maintain single-responsibility focus on semantic code search.

---

## Removed Tools

The following 14 MCP tools have been removed in v2.0 as part of the architectural refactoring that extracted project management, entity tracking, and work item features into the separate workflow-mcp server. These tools are no longer available in the Codebase MCP Server v2.0 API.

### Removed Project Management Tools

**4 tools removed**:

- **`create_project`**: Created a new project workspace with an isolated PostgreSQL database. Projects served as containers for organizing entities and work items in v1.x.
- **`switch_project`**: Switched the active project context for all subsequent operations. All entity and work item operations were scoped to the active project.
- **`get_active_project`**: Retrieved the currently active project workspace metadata or returned null if no project was active.
- **`list_projects`**: Listed all project workspaces with pagination support, ordered by creation date (newest first).

### Removed Entity Management Tools

**6 tools removed**:

- **`register_entity_type`**: Registered a new entity type with JSON Schema validation. Entity types defined the structure and validation rules for storing arbitrary JSONB data.
- **`create_entity`**: Created a new entity instance with data validated against the registered entity type's JSON Schema. Entities were scoped to the active project.
- **`query_entities`**: Queried entities with JSONB containment filters and tag matching. Supported complex filtering with GIN-indexed JSONB queries for sub-100ms performance.
- **`update_entity`**: Updated entity data with optimistic locking via version numbers to prevent concurrent update conflicts. Changes were validated against the entity type's JSON Schema.
- **`delete_entity`**: Soft-deleted an entity by setting the `deleted_at` timestamp. Required explicit confirmation to prevent accidental deletions.
- **`update_entity_type_schema`**: Updated an entity type's JSON Schema with backward compatibility validation. Automatically incremented schema versions and optionally validated existing entities against the new schema.

### Removed Work Item Management Tools

**4 tools removed**:

- **`create_work_item`**: Created a new work item in a 5-level hierarchy (project → session → task → research → subtask) with automatic materialized path generation for fast ancestor queries.
- **`update_work_item`**: Updated work item fields including title, description, and status. Automatically set `completed_at` timestamp when status changed to 'completed'.
- **`query_work_items`**: Queried work items with filtering by type, status, and parent. Supported recursive descendant queries using materialized paths.
- **`get_work_item_hierarchy`**: Retrieved complete hierarchy information for a work item including ancestors (parents to root), direct children, and all descendants using materialized path queries.

**Migration Path**: If you require project management, entity tracking, or work item capabilities, install the separate [workflow-mcp](https://github.com/workflow-mcp) server which provides these features as an independent MCP server. The workflow-mcp server is designed to work alongside codebase-mcp and provides enhanced workflow tracking capabilities.

---

## Prerequisites

Before starting the migration process, ensure the following requirements are met:

### System Requirements

- **v1.x Running**: Existing Codebase MCP Server v1.x installation must be operational and accessible
- **PostgreSQL Access**: Database administrator privileges required for schema modifications and database creation
- **Python Version**: Python 3.11+ required (verify with `python --version`)
- **Ollama**: Ollama server running with embedding model pulled (verify with `ollama list`)

### Resource Requirements

- **Disk Space**: Minimum 2× current database size for backup storage
  - Check current database size: `psql -c "SELECT pg_size_pretty(pg_database_size('codebase_mcp'));"`
  - Ensure backup destination has adequate free space: `df -h /path/to/backup/location`
- **Downtime Window**: Plan for 30-60 minutes of service interruption for typical installations
  - Small installations (<10 repositories): ~15-30 minutes
  - Medium installations (10-50 repositories): ~30-45 minutes
  - Large installations (>50 repositories): ~45-90 minutes

### Backup Storage

- **Location**: Dedicated backup directory with sufficient space
  - Recommended: External storage or separate volume
  - Verify write permissions: `touch /path/to/backup/test && rm /path/to/backup/test`
- **Retention**: Keep backups for at least 30 days post-migration
- **Verification**: Ensure backup destination is separate from database data directory

### Access Requirements

- **Database Credentials**: PostgreSQL superuser or database owner credentials
- **Configuration Access**: Read/write access to `.env` or configuration files
- **Service Control**: Permission to stop/start the Codebase MCP Server service

---

## Pre-Migration Checklist

Complete the following checklist **before** proceeding with the migration procedure. All items must be checked off to ensure a safe upgrade.

### Required Preparation Steps

- [ ] **Review Breaking Changes**: Read the "Breaking Changes Summary" section below to understand what will be removed
- [ ] **Verify PostgreSQL Version**: Confirm PostgreSQL 14+ is installed
  ```bash
  psql --version
  # Expected output: psql (PostgreSQL) 14.x or higher
  ```
- [ ] **Test Rollback Procedure**: Perform a dry-run migration and rollback in a **non-production environment first**
  - Clone production database to staging
  - Execute full migration procedure in staging
  - Test rollback procedure in staging
  - Verify rollback restores v1.x functionality completely
- [ ] **Notify Users**: Inform all users of planned downtime window
  - Communicate expected duration (30-60 minutes)
  - Provide start time and estimated completion time
  - Include rollback contingency plan
- [ ] **Document Current Configuration**: Record all current v1.x settings
  ```bash
  # Save current .env file
  cat .env > pre-migration-config-$(date +%Y%m%d).txt

  # Record database statistics
  psql codebase_mcp -c "\dt+" > pre-migration-schema-$(date +%Y%m%d).txt
  ```
- [ ] **Verify Backup Destination Space**: Confirm adequate space for database backup
  ```bash
  # Check available space
  df -h /path/to/backup/location

  # Compare with database size
  psql -c "SELECT pg_size_pretty(pg_database_size('codebase_mcp'));"
  ```
- [ ] **Stop All Active Sessions**: Ensure no users are actively using the v1.x server
  ```bash
  # Check for active connections
  psql codebase_mcp -c "SELECT count(*) FROM pg_stat_activity WHERE datname='codebase_mcp';"
  ```
- [ ] **Prepare Rollback Plan**: Document rollback steps and assign responsibility
  - Identify rollback trigger conditions (e.g., validation failures, extended downtime)
  - Assign rollback decision authority
  - Prepare rollback communication template

### Optional Pre-Migration Steps

- [ ] **Export v1.x Data** (if planning to migrate to workflow-mcp later):
  ```bash
  # Export project management data for future workflow-mcp import
  pg_dump -h localhost -U postgres -d codebase_mcp \
    --table=projects --table=entities --table=work_items \
    --data-only --column-inserts \
    > v1x-workflow-data-export-$(date +%Y%m%d).sql
  ```
- [ ] **Performance Baseline**: Record current performance metrics for comparison
  ```bash
  # Test indexing performance
  time codebase-mcp index /path/to/test/repo

  # Test search performance
  time codebase-mcp search "test query"
  ```

---

## Backup Procedures

Perform complete backups of both database and configuration **before** making any changes. These backups are critical for rollback if issues occur during migration.

### Database Backup

Create a full PostgreSQL dump of the v1.x database with timestamp:

```bash
# Create backup with timestamp
pg_dump -h localhost -U postgres -d codebase_mcp > backup_$(date +%Y%m%d_%H%M%S).sql

# Example output filename: backup_20250115_103000.sql
```

**Command Options**:
- `-h localhost`: Database host (adjust if using remote PostgreSQL)
- `-U postgres`: PostgreSQL username (adjust to match your credentials)
- `-d codebase_mcp`: Database name (adjust if using different database name)
- `> backup_$(date +%Y%m%d_%H%M%S).sql`: Output file with timestamp

**Verification Steps**:

1. **Confirm backup file exists**:
   ```bash
   ls -lh backup_*.sql
   # Expected output: -rw-r--r-- 1 user group 45M Jan 15 10:30 backup_20250115_103000.sql
   ```

2. **Verify backup file size > 0**:
   ```bash
   # Check file is not empty
   test -s backup_*.sql && echo "Backup file is valid" || echo "ERROR: Backup file is empty"
   ```

3. **Test backup file readability**:
   ```bash
   # Verify backup contains valid SQL
   head -n 20 backup_*.sql
   # Expected: Should show PostgreSQL dump header and table definitions
   ```

4. **Validate backup integrity**:
   ```bash
   # Test restore to temporary database (optional but recommended)
   psql -c "CREATE DATABASE codebase_mcp_backup_test;"
   psql codebase_mcp_backup_test < backup_*.sql
   psql -c "DROP DATABASE codebase_mcp_backup_test;"
   ```

### Configuration Backup

Backup all configuration files that will be modified during migration:

```bash
# Backup .env file with timestamp
cp .env .env.backup_$(date +%Y%m%d)

# Example output filename: .env.backup_20250115
```

**Additional Configuration Files** (if applicable):

```bash
# Backup systemd service file (if using systemd)
sudo cp /etc/systemd/system/codebase-mcp.service \
        /etc/systemd/system/codebase-mcp.service.backup_$(date +%Y%m%d)

# Backup Docker Compose configuration (if using Docker)
cp docker-compose.yml docker-compose.yml.backup_$(date +%Y%m%d)

# Backup any custom configuration scripts
cp /path/to/custom/config.sh /path/to/custom/config.sh.backup_$(date +%Y%m%d)
```

**Verification Steps**:

1. **Confirm configuration backup exists**:
   ```bash
   ls -lh .env.backup_*
   # Expected output: -rw-r--r-- 1 user group 1.2K Jan 15 10:30 .env.backup_20250115
   ```

2. **Verify backup contains configuration data**:
   ```bash
   # Check backup is not empty and contains expected variables
   test -s .env.backup_* && echo "Configuration backup is valid" || echo "ERROR: Configuration backup is empty"

   # Verify key variables are present
   grep -E "DATABASE_URL|OLLAMA_BASE_URL" .env.backup_* && echo "Key variables found" || echo "ERROR: Missing key variables"
   ```

### Document Backup Locations

**Record backup information for rollback reference**:

```bash
# Create backup manifest
cat > migration-backup-manifest-$(date +%Y%m%d).txt <<EOF
Migration Backup Manifest
Created: $(date)
Location: $(pwd)

Database Backup:
- File: $(ls backup_*.sql | tail -1)
- Size: $(ls -lh backup_*.sql | tail -1 | awk '{print $5}')
- Location: $(pwd)/$(ls backup_*.sql | tail -1)

Configuration Backup:
- File: $(ls .env.backup_* | tail -1)
- Size: $(ls -lh .env.backup_* | tail -1 | awk '{print $5}')
- Location: $(pwd)/$(ls .env.backup_* | tail -1)

Verification:
- Database backup integrity: $(test -s backup_*.sql && echo "PASS" || echo "FAIL")
- Configuration backup integrity: $(test -s .env.backup_* && echo "PASS" || echo "FAIL")

Next Steps:
1. Verify backup files are readable
2. Proceed with migration procedure
3. Keep backups for 30 days post-migration
EOF

# Display backup manifest
cat migration-backup-manifest-*.txt
```

### Backup Validation Checklist

Before proceeding with migration, verify:

- [ ] Database backup file exists and size > 0
- [ ] Database backup file is readable (contains valid SQL)
- [ ] Configuration backup file exists and size > 0
- [ ] Configuration backup contains expected variables (DATABASE_URL, OLLAMA_BASE_URL, etc.)
- [ ] Backup manifest created and reviewed
- [ ] Backup location documented and accessible for rollback
- [ ] Backup files have appropriate read permissions
- [ ] Sufficient disk space remains for migration operations

---

## Diagnostic Commands

The following SQL queries enable direct inspection of the database migration state. Use these commands to detect partial migrations, verify upgrade success, or troubleshoot migration issues.

### Check v2.0 Schema Present

Verify that the v2.0 tables exist in the database:

```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('repositories', 'file_chunks')
ORDER BY table_name;
```

**Expected Output** (successful v2.0 migration):
```
 table_name
-------------
 file_chunks
 repositories
(2 rows)
```

**Interpretation**:
- **2 rows returned**: v2.0 schema present (expected for successful migration)
- **0-1 rows returned**: Incomplete migration or v1.x schema still present (requires investigation)

### Verify v1.x Tables Dropped

Confirm that all v1.x-specific tables have been removed:

```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('projects', 'entities', 'work_items', 'deployments')
ORDER BY table_name;
```

**Expected Output** (successful v2.0 migration):
```
 table_name
------------
(0 rows)
```

**Interpretation**:
- **0 rows returned**: All v1.x tables successfully dropped (expected for clean v2.0 state)
- **1+ rows returned**: Partial migration detected (v1.x tables still exist, migration incomplete)

### Detect Partial Migration State

Check for inconsistent states where v2.0 schema modifications exist but v1.x tables remain:

```sql
-- Check if project_id column exists (v2.0) but v1.x tables still present (incomplete migration)
SELECT
  (SELECT COUNT(*) FROM information_schema.columns
   WHERE table_name = 'repositories' AND column_name = 'project_id') as has_project_id,
  (SELECT COUNT(*) FROM information_schema.tables
   WHERE table_schema = 'public' AND table_name = 'projects') as has_v1x_tables;
```

**Expected Output** (successful v2.0 migration):
```
 has_project_id | has_v1x_tables
----------------+----------------
              1 |              0
(1 row)
```

**Interpretation**:
- **has_project_id=1, has_v1x_tables=0**: Clean v2.0 state (expected)
- **has_project_id=0, has_v1x_tables=1**: v1.x state (migration not started or rolled back)
- **has_project_id=1, has_v1x_tables=1**: Partial migration state (CRITICAL: migration incomplete, requires manual intervention)
- **has_project_id=0, has_v1x_tables=0**: Corrupted state (CRITICAL: neither v1.x nor v2.0 schema complete)

### Using Diagnostic Commands

**When to Run Diagnostics**:
1. **Before migration**: Confirm v1.x state (`has_project_id=0, has_v1x_tables=1`)
2. **After migration**: Verify v2.0 state (`has_project_id=1, has_v1x_tables=0`)
3. **Troubleshooting**: Detect partial migrations or corrupted states
4. **Regular audits**: Periodic validation of schema integrity

**Command Execution**:

```bash
# Connect to database
psql -h localhost -U postgres -d codebase_mcp

# Run diagnostic queries
\i diagnostic-queries.sql

# Or run inline
psql -h localhost -U postgres -d codebase_mcp -c "SELECT ..."
```

**Automated Validation Script**:

```bash
#!/bin/bash
# diagnostic-check.sh - Automated migration state validation

DATABASE_URL="postgresql://localhost/codebase_mcp"

echo "=== Codebase MCP Migration Diagnostics ==="
echo ""

echo "1. Checking v2.0 schema presence..."
RESULT=$(psql $DATABASE_URL -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('repositories', 'file_chunks');")
if [ "$RESULT" -eq 2 ]; then
  echo "   ✓ v2.0 schema present (2 tables found)"
else
  echo "   ✗ v2.0 schema incomplete ($RESULT tables found, expected 2)"
fi

echo ""
echo "2. Verifying v1.x tables dropped..."
RESULT=$(psql $DATABASE_URL -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('projects', 'entities', 'work_items', 'deployments');")
if [ "$RESULT" -eq 0 ]; then
  echo "   ✓ v1.x tables dropped (0 tables found)"
else
  echo "   ✗ v1.x tables still exist ($RESULT tables found)"
fi

echo ""
echo "3. Detecting partial migration state..."
RESULT=$(psql $DATABASE_URL -t -c "SELECT (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'repositories' AND column_name = 'project_id') as has_project_id, (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'projects') as has_v1x_tables;")
HAS_PROJECT_ID=$(echo $RESULT | awk '{print $1}')
HAS_V1X_TABLES=$(echo $RESULT | awk '{print $3}')

if [ "$HAS_PROJECT_ID" -eq 1 ] && [ "$HAS_V1X_TABLES" -eq 0 ]; then
  echo "   ✓ Clean v2.0 state (project_id present, v1.x tables absent)"
elif [ "$HAS_PROJECT_ID" -eq 0 ] && [ "$HAS_V1X_TABLES" -eq 1 ]; then
  echo "   ℹ v1.x state (migration not started or rolled back)"
elif [ "$HAS_PROJECT_ID" -eq 1 ] && [ "$HAS_V1X_TABLES" -eq 1 ]; then
  echo "   ✗ CRITICAL: Partial migration detected (manual intervention required)"
else
  echo "   ✗ CRITICAL: Corrupted state (neither v1.x nor v2.0 schema complete)"
fi

echo ""
echo "=== Diagnostics Complete ==="
```

Save as `diagnostic-check.sh`, make executable with `chmod +x diagnostic-check.sh`, and run with `./diagnostic-check.sh`.

---

## Rollback Procedure

If issues occur during or after migration, this procedure restores the v1.x installation from backups. Complete rollback typically takes 15-30 minutes.

### When to Roll Back

Consider rolling back to v1.x in the following scenarios:

**Critical Rollback Triggers**:
- **Failed Migration**: Alembic migration errors or incomplete schema changes detected by diagnostic commands
- **Data Integrity Issues**: Repository or embedding data corruption discovered during post-migration validation
- **Functionality Problems**: Core search or indexing features non-functional in v2.0
- **Unacceptable Downtime**: Migration exceeds planned downtime window and cannot complete

**Non-Critical Issues** (troubleshooting recommended before rollback):
- Performance degradation within 20% of baseline (may require optimization)
- Minor configuration issues (check environment variables)
- Single repository indexing failures (may be repository-specific)

**Decision Criteria**:
1. **Data Loss Risk**: Is current v2.0 state more valuable than v1.x backup? (Usually no during initial migration)
2. **Time Constraint**: Does troubleshooting exceed available downtime window?
3. **Stakeholder Impact**: Are users unable to perform critical work without v1.x features?

### Rollback Steps

Follow these steps in order to restore v1.x functionality from backup. The procedure mirrors the upgrade process in reverse.

#### Step 1: Stop v2.0 Server

Terminate the v2.0 server to prevent database connections during restoration:

```bash
# Stop systemd service (if using systemd)
sudo systemctl stop codebase-mcp

# Stop Docker container (if using Docker)
docker-compose down

# Stop manual process (if running directly)
pkill -f codebase-mcp
```

**Verification**:
```bash
# Confirm no codebase-mcp processes running
ps aux | grep codebase-mcp
# Expected output: Only the grep command itself (no server processes)

# Check no active database connections
psql codebase_mcp -c "SELECT count(*) FROM pg_stat_activity WHERE datname='codebase_mcp';"
# Expected output: 0 connections
```

#### Step 2: Restore Database Backup

Replace the v2.0 database with the v1.x backup created during pre-migration:

```bash
# Drop the v2.0 database (WARNING: Destructive operation)
psql -h localhost -U postgres -c "DROP DATABASE codebase_mcp;"

# Recreate empty database
psql -h localhost -U postgres -c "CREATE DATABASE codebase_mcp;"

# Restore v1.x backup
psql -h localhost -U postgres -d codebase_mcp < backup_20250115_103000.sql
```

**Alternative: Use pg_restore for custom format backups**:
```bash
# If backup was created with pg_dump -Fc (custom format)
pg_restore -h localhost -U postgres -d codebase_mcp --clean --if-exists backup_20250115_103000.dump
```

**Verification**:
```bash
# Confirm v1.x tables exist
psql codebase_mcp -c "\dt" | grep -E "projects|entities|work_items"
# Expected output: Should show v1.x tables (projects, entities, work_items, etc.)

# Verify project_id column does NOT exist (v1.x state)
psql codebase_mcp -c "\d repositories" | grep project_id
# Expected output: Empty (no project_id column in v1.x)

# Check row counts match pre-migration manifest
psql codebase_mcp -c "SELECT
  (SELECT COUNT(*) FROM repositories) as repositories,
  (SELECT COUNT(*) FROM projects) as projects,
  (SELECT COUNT(*) FROM entities) as entities;"
# Compare output to pre-migration-schema-*.txt
```

#### Step 3: Restore Configuration

Restore the v1.x `.env` file and any other modified configuration files:

```bash
# Restore .env file
cp .env.backup_20250115 .env

# Restore systemd service file (if modified)
sudo cp /etc/systemd/system/codebase-mcp.service.backup_20250115 \
        /etc/systemd/system/codebase-mcp.service
sudo systemctl daemon-reload

# Restore Docker Compose configuration (if modified)
cp docker-compose.yml.backup_20250115 docker-compose.yml
```

**Verification**:
```bash
# Confirm .env contains v1.x configuration
cat .env | grep -E "DATABASE_URL|OLLAMA_BASE_URL"
# Expected output: v1.x environment variables (no WORKFLOW_MCP_URL)

# Verify no v2.0-specific variables present
grep -E "WORKFLOW_MCP" .env
# Expected output: Empty (no v2.0 workflow-mcp integration variables)
```

#### Step 4: Downgrade Dependencies

Reinstall v1.x version of the Codebase MCP Server package:

```bash
# Uninstall v2.0
pip uninstall -y codebase-mcp

# Install v1.x (replace with your specific v1.x version)
pip install codebase-mcp==1.2.3

# Alternative: Install from local v1.x backup
pip install /path/to/backup/codebase-mcp-1.2.3-py3-none-any.whl
```

**Verification**:
```bash
# Confirm v1.x version installed
pip show codebase-mcp | grep Version
# Expected output: Version: 1.2.3 (or your specific v1.x version)

# Verify v1.x tools available (if CLI installed)
codebase-mcp --help | grep -E "create_project|query_entities"
# Expected output: Should show v1.x-specific commands
```

#### Step 5: Restart v1.x Server

Start the restored v1.x server:

```bash
# Start systemd service (if using systemd)
sudo systemctl start codebase-mcp
sudo systemctl status codebase-mcp

# Start Docker container (if using Docker)
docker-compose up -d

# Start manual process (if running directly)
codebase-mcp serve &
```

**Verification**:
```bash
# Confirm server process running
ps aux | grep codebase-mcp
# Expected output: codebase-mcp server process with v1.x binary

# Check server logs for startup messages
tail -f /var/log/codebase-mcp/server.log
# Expected output: v1.x version number, successful database connection

# Test database connectivity
psql codebase_mcp -c "SELECT version();"
# Expected output: PostgreSQL version (confirms database accessible)
```

#### Step 6: Verify Rollback Success

Perform comprehensive validation to confirm v1.x restoration:

**Rollback Validation subsection** follows below.

### Rollback Validation

After completing the rollback procedure, validate that v1.x functionality has been fully restored:

#### Database Schema Validation

Confirm v1.x schema is present and v2.0 modifications are absent:

```bash
# Check v1.x tables exist
psql codebase_mcp -c "SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('projects', 'entities', 'work_items', 'deployments')
ORDER BY table_name;"
# Expected output: All 4 v1.x tables listed

# Verify project_id column removed from repositories table
psql codebase_mcp -c "\d repositories" | grep project_id
# Expected output: Empty (no project_id column in v1.x schema)

# Check file_chunks table reverted to v1.x structure
psql codebase_mcp -c "\d file_chunks" | grep project_id
# Expected output: Empty (no project_id column in v1.x schema)
```

#### v1.x Functionality Tests

Verify core v1.x operations work correctly:

**Project Management** (if v1.x CLI available):
```bash
# List existing projects
codebase-mcp projects list
# Expected output: List of v1.x projects from backup

# Get active project
codebase-mcp projects get-active
# Expected output: Active project details or null
```

**Entity Management**:
```bash
# Query entities (if v1.x CLI available)
codebase-mcp entities query --type vendor
# Expected output: List of vendor entities from backup

# Alternative: Direct SQL query
psql codebase_mcp -c "SELECT id, entity_type, name FROM entities LIMIT 5;"
# Expected output: Entity data from v1.x backup
```

**Work Item Management**:
```bash
# Query work items (if v1.x CLI available)
codebase-mcp work-items query --status active
# Expected output: List of active work items from backup

# Alternative: Direct SQL query
psql codebase_mcp -c "SELECT id, item_type, title, status FROM work_items LIMIT 5;"
# Expected output: Work item data from v1.x backup
```

**Search Functionality** (should work in both v1.x and v2.0):
```bash
# Test semantic search
codebase-mcp search "authentication logic"
# Expected output: Search results from indexed repositories

# Verify search performance
time codebase-mcp search "database query" > /dev/null
# Expected output: Completes in <2 seconds (v1.x baseline)
```

#### Data Integrity Checks

Verify backup data matches pre-migration state:

```bash
# Compare row counts to pre-migration manifest
psql codebase_mcp -c "SELECT
  (SELECT COUNT(*) FROM repositories) as repositories,
  (SELECT COUNT(*) FROM projects) as projects,
  (SELECT COUNT(*) FROM entities) as entities,
  (SELECT COUNT(*) FROM work_items) as work_items,
  (SELECT COUNT(*) FROM file_chunks) as file_chunks;"

# Compare output to pre-migration-schema-*.txt
# Expected: Row counts match pre-migration baseline
```

#### Configuration Validation

Confirm v1.x configuration restored:

```bash
# Verify .env contains v1.x variables only
cat .env | grep -c "WORKFLOW_MCP"
# Expected output: 0 (no v2.0 variables present)

# Check database connection string
cat .env | grep DATABASE_URL
# Expected output: v1.x database connection string

# Verify Ollama configuration unchanged
cat .env | grep OLLAMA_BASE_URL
# Expected output: Original v1.x Ollama URL
```

#### Rollback Validation Checklist

Complete this checklist to confirm successful rollback:

- [ ] All v1.x tables present (`projects`, `entities`, `work_items`, `deployments`)
- [ ] v2.0 schema modifications removed (`project_id` columns absent)
- [ ] v1.x version number confirmed (`pip show codebase-mcp`)
- [ ] Project management functionality tested and working
- [ ] Entity management functionality tested and working
- [ ] Work item management functionality tested and working
- [ ] Search functionality tested and working with expected performance
- [ ] Row counts match pre-migration manifest
- [ ] Configuration files restored (`.env` contains v1.x variables only)
- [ ] Server logs show v1.x version and successful startup
- [ ] No error messages in logs during validation tests

**If all checklist items pass**: Rollback successful, v1.x fully restored. Inform users of service restoration.

**If validation fails**: Investigate failures using diagnostic commands and server logs. Consider restoring from backup again or seeking support.

---

## Upgrade Procedure

Follow these six steps in order to safely migrate from v1.x to v2.0. Each step includes validation commands to confirm success before proceeding to the next step.

### Step 1: Stop v1.x Server

Stop the running Codebase MCP Server v1.x instance to prevent data corruption during migration.

**Systemd Service**:
```bash
sudo systemctl stop codebase-mcp.service
```

**Docker Container**:
```bash
docker stop codebase-mcp
```

**Direct Process**:
```bash
# Find process ID
ps aux | grep codebase-mcp

# Kill process (replace <PID> with actual process ID)
kill <PID>
```

**Validation**:
```bash
# Verify no codebase-mcp processes are running
ps aux | grep codebase-mcp
# Expected output: Only the grep command itself (or no output)
```

### Step 2: Update Dependencies

Upgrade the codebase-mcp package to version 2.0.0.

**Command**:
```bash
pip install --upgrade codebase-mcp==2.0.0
```

**Validation**:
```bash
# Verify installed version is 2.0.0
pip show codebase-mcp | grep Version
# Expected output: Version: 2.0.0
```

**Alternative Validation**:
```bash
# Check codebase-mcp CLI version
codebase-mcp --version
# Expected output: codebase-mcp 2.0.0
```

### Step 3: Run Migration Script

Execute the database migration script to transform the v1.x schema to v2.0 structure. This step applies all schema modifications including table drops and column additions.

**Command**:
```bash
# Set database URL environment variable (adjust if needed)
export DATABASE_URL="postgresql+asyncpg://postgres:password@localhost/codebase_mcp"

# Run Alembic migration to v2.0 schema
alembic upgrade head
```

**Expected Output**:
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade abc123 -> def456, v2.0 schema refactoring
INFO  [alembic.runtime.migration] Dropping project management tables...
INFO  [alembic.runtime.migration] Adding project_id column to repositories...
INFO  [alembic.runtime.migration] Adding project_id column to file_chunks...
INFO  [alembic.runtime.migration] Migration completed successfully.
```

**Duration Estimate**:
- Small databases (<10 repositories): 1-5 minutes
- Medium databases (10-50 repositories): 5-15 minutes
- Large databases (>50 repositories): 15-30 minutes

**Progress Monitoring**:
```bash
# Monitor migration progress (in separate terminal)
tail -f /tmp/codebase-mcp-migration.log
```

**Note**: If the migration script (`alembic/versions/`) does not exist yet, this component will be delivered in Phase 06 (Implementation). For now, document this step as "Migration script TBD in Phase 06".

### Step 4: Update Configuration

Add new v2.0 environment variables to support workflow-mcp integration and multi-project workspace features.

**Required Environment Variables**:

No changes required. All v1.x environment variables remain functional in v2.0.

**Optional Environment Variables**:

Add the following to your `.env` file if you plan to use workflow-mcp integration for automatic project context detection:

```bash
# Add these lines to your .env file
WORKFLOW_MCP_URL=http://localhost:8001  # Optional: workflow-mcp server URL for automatic project detection
WORKFLOW_MCP_TIMEOUT=1.0                # Optional: Timeout for workflow-mcp queries (seconds), default: 1.0
WORKFLOW_MCP_CACHE_TTL=60               # Optional: Cache TTL for workflow-mcp responses (seconds), default: 60
```

**Example Complete .env File**:
```bash
# Required v1.x variables (unchanged)
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost/codebase_mcp
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# Optional v2.0 additions (for workflow-mcp integration)
WORKFLOW_MCP_URL=http://localhost:8001
WORKFLOW_MCP_TIMEOUT=1.0
WORKFLOW_MCP_CACHE_TTL=60
```

**Validation**:
```bash
# Verify new environment variables are present (if added)
grep WORKFLOW_MCP .env
# Expected output (if using workflow-mcp):
# WORKFLOW_MCP_URL=http://localhost:8001
# WORKFLOW_MCP_TIMEOUT=1.0
# WORKFLOW_MCP_CACHE_TTL=60

# Or no output if not using workflow-mcp (this is valid)
```

### Step 5: Restart Server

Start the Codebase MCP Server v2.0 with the updated configuration.

**Systemd Service**:
```bash
sudo systemctl start codebase-mcp.service
```

**Docker Container**:
```bash
docker start codebase-mcp
```

**Direct Process**:
```bash
# Start server in background
codebase-mcp serve &
```

**Validation**:
```bash
# Check server logs for successful startup
journalctl -u codebase-mcp.service -n 50 --no-pager
# Expected output: Should show v2.0 startup messages and no errors

# Or for Docker:
docker logs codebase-mcp --tail 50
# Expected output: Server started successfully on port XXXX

# Or for direct process:
tail -f /var/log/codebase-mcp/server.log
# Expected output: MCP server listening on stdio
```

**Success Indicators**:
- Log message: "Codebase MCP Server v2.0 started successfully"
- No error messages about missing tables or schema issues
- Server accepts connections on configured port

### Step 6: Verify Migration Success

Confirm that v2.0 is operational and all expected functionality is working.

**Verify v2.0 Version**:
```bash
# Check server version via CLI
codebase-mcp --version
# Expected output: codebase-mcp 2.0.0

# Or query server health endpoint (if applicable)
curl http://localhost:8000/health
# Expected output: {"status":"healthy","version":"2.0.0"}
```

**Verify Database Schema**:
```bash
# Check that v1.x project management tables are removed
psql codebase_mcp -c "\dt" | grep -E "projects|entities|work_items"
# Expected output: No matches (tables should be dropped)

# Verify new project_id columns exist
psql codebase_mcp -c "\d repositories" | grep project_id
# Expected output: project_id | character varying(255) | | |

psql codebase_mcp -c "\d file_chunks" | grep project_id
# Expected output: project_id | character varying(255) | | |
```

**Test Core Functionality**:
```bash
# Test index_repository tool (see Post-Migration Validation section below for detailed tests)
# Test search_code tool (see Post-Migration Validation section below for detailed tests)
```

**Optional: Checkpoint Resume**:

If migration supports checkpoint resume (FR-037 SHOULD requirement), the migration script will automatically detect interrupted migrations and resume from the last successful checkpoint. No manual intervention is required.

To verify checkpoint support:
```bash
# Check migration logs for checkpoint messages
grep "checkpoint" /tmp/codebase-mcp-migration.log
# Expected output (if supported): "Checkpoint saved: step_3_complete"
```

**Completion Checklist**:
- [ ] Server starts without errors
- [ ] v2.0 version confirmed via CLI or health endpoint
- [ ] v1.x project management tables are dropped
- [ ] New `project_id` columns exist in `repositories` and `file_chunks` tables
- [ ] No error messages in server logs
- [ ] Ready to proceed to Post-Migration Validation section

---

## Post-Migration Validation

After completing the upgrade procedure, perform comprehensive validation to confirm v2.0 functionality and data preservation.

### Verify v2.0 Functionality

Test the two core v2.0 MCP tools to ensure the server is operational and accepting requests.

#### Test `index_repository` Command

Index a test repository to verify the indexing pipeline is functional.

**Command**:
```bash
# Index a small test repository
codebase-mcp index /path/to/test/repo
```

**Expected Output**:
```
Indexing repository: /path/to/test/repo
Scanning files... 24 files found
Processing chunks... 156 chunks created
Generating embeddings... 156 embeddings generated
Storing in database... complete
Indexing completed in 12.3 seconds
```

**Success Indicators**:
- Process completes without errors
- File count matches expected repository size
- Chunk count is reasonable (typically 5-10 chunks per file)
- Embeddings count equals chunk count
- Duration is within expected range (target: <60s for 10,000 files)

**Validation Query**:
```bash
# Verify repository was indexed
psql codebase_mcp -c "SELECT COUNT(*) FROM repositories WHERE path='/path/to/test/repo';"
# Expected output: 1

# Verify file chunks were created
psql codebase_mcp -c "SELECT COUNT(*) FROM file_chunks WHERE repository_id=(SELECT id FROM repositories WHERE path='/path/to/test/repo' LIMIT 1);"
# Expected output: 156 (or chunk count from indexing output)
```

#### Test `search_code` Command

Execute a semantic code search to verify the search pipeline is functional.

**Command**:
```bash
# Search for a known code pattern
codebase-mcp search "function to parse configuration files"
```

**Expected Output**:
```
Search results for: "function to parse configuration files"

1. config/parser.py:45-67 (similarity: 0.92)
   def parse_config_file(file_path: str) -> Dict[str, Any]:
       """Parse YAML configuration file and return settings dictionary."""
       ...

2. utils/config.py:12-28 (similarity: 0.88)
   class ConfigParser:
       """Configuration file parser with validation support."""
       ...

3. tests/test_config.py:89-105 (similarity: 0.85)
   def test_parse_config_with_defaults():
       """Test configuration parsing with default values."""
       ...

Found 3 results in 0.34 seconds
```

**Success Indicators**:
- Search completes without errors
- Results are semantically relevant to query
- Similarity scores are reasonable (>0.7 for relevant results)
- Response time is within target (<500ms p95 latency)
- File paths and line numbers are correct

**Validation Query**:
```bash
# Verify search used embeddings
psql codebase_mcp -c "SELECT COUNT(*) FROM file_chunks WHERE embedding IS NOT NULL;"
# Expected output: >0 (should match total chunk count from indexing)
```

### Verify Existing Repositories Searchable

Confirm that repositories indexed in v1.x remain searchable after migration and return correct results.

#### Query Previously Indexed Repositories

List all repositories that were indexed before migration and verify they are still accessible.

**Command**:
```bash
# List all indexed repositories
psql codebase_mcp -c "SELECT id, path, indexed_at FROM repositories ORDER BY indexed_at DESC;"
```

**Expected Output**:
```
                  id                  |           path            |         indexed_at
--------------------------------------+---------------------------+----------------------------
 a1b2c3d4-e5f6-7890-abcd-ef1234567890 | /home/user/project-alpha  | 2025-01-10 14:23:45.123456
 b2c3d4e5-f6a7-8901-bcde-f12345678901 | /home/user/project-beta   | 2025-01-09 10:15:32.654321
 c3d4e5f6-a7b8-9012-cdef-123456789012 | /home/user/project-gamma  | 2025-01-08 16:47:19.987654
```

**Validation Steps**:

1. **Confirm repository count matches pre-migration baseline**:
   ```bash
   # Count repositories
   psql codebase_mcp -c "SELECT COUNT(*) FROM repositories;"
   # Expected output: Should match pre-migration count from backup manifest
   ```

2. **Verify embedding counts match pre-migration baseline**:
   ```bash
   # Count total embeddings
   psql codebase_mcp -c "SELECT COUNT(*) FROM file_chunks WHERE embedding IS NOT NULL;"
   # Expected output: Should match pre-migration embedding count
   ```

3. **Test search against pre-migration repositories**:
   ```bash
   # Search in a known repository
   codebase-mcp search "authentication function" --repository-id a1b2c3d4-e5f6-7890-abcd-ef1234567890
   ```

#### Confirm Search Results Return Expected Code

Verify that search results for previously indexed repositories return semantically correct code snippets.

**Test Procedure**:

1. **Select a known code pattern from v1.x**:
   - Identify a specific function or class from a pre-migration repository
   - Record its file path and approximate line numbers

2. **Search for the pattern using v2.0**:
   ```bash
   # Search for known pattern (adjust query based on your codebase)
   codebase-mcp search "user authentication with JWT tokens"
   ```

3. **Compare results with pre-migration baseline**:
   - Verify the known function/class appears in results
   - Confirm file path and line numbers are correct
   - Check similarity score is reasonable (>0.8 for exact matches)

**Success Indicators**:
- All previously indexed repositories are listed
- Repository count matches pre-migration baseline
- Embedding count matches pre-migration baseline
- Search results return expected code snippets
- File paths and line numbers are accurate
- Similarity scores are consistent with v1.x behavior

**Validation Query**:
```bash
# Verify all repositories have embeddings
psql codebase_mcp -c "
  SELECT r.path, COUNT(fc.id) AS chunk_count
  FROM repositories r
  LEFT JOIN file_chunks fc ON r.id = fc.repository_id
  WHERE fc.embedding IS NOT NULL
  GROUP BY r.path
  ORDER BY chunk_count DESC;
"
# Expected output: All repositories should have >0 chunks
```

### Post-Migration Validation Checklist

- [ ] `index_repository` command completes successfully with test repository
- [ ] `search_code` command returns relevant results with acceptable latency
- [ ] All pre-migration repositories are listed in database
- [ ] Repository count matches pre-migration baseline
- [ ] Embedding count matches pre-migration baseline
- [ ] Search results return expected code snippets from v1.x repositories
- [ ] File paths and line numbers are accurate in search results
- [ ] No errors in server logs during validation tests
- [ ] Performance characteristics are acceptable (<60s indexing, <500ms search)

---

## Troubleshooting

This section provides solutions to common migration issues. If you encounter problems during migration, consult these troubleshooting entries before seeking additional support.

### Common Issues

#### 1. Migration Script Fails Midway

**Symptom**:
- Migration script exits with error message before completion
- Partial table modifications visible in database
- Some v1.x tables dropped but v2.0 schema changes incomplete

**Possible Causes**:
- Insufficient PostgreSQL user permissions for schema modifications
- Inadequate disk space for temporary migration operations
- Database connection timeout during long-running operations
- Foreign key constraint violations from unexpected data state

**Solution**:

1. **Check migration logs for specific error**:
   ```bash
   tail -n 50 /tmp/codebase-mcp-migration.log
   ```

2. **Verify prerequisites**:
   ```bash
   # Check database permissions
   psql codebase_mcp -c "\du"
   # User should have SUPERUSER or CREATEDB privileges

   # Check disk space
   df -h /var/lib/postgresql
   # Should have at least 2× database size free

   # Check connection settings
   psql codebase_mcp -c "SHOW max_connections;"
   psql codebase_mcp -c "SELECT count(*) FROM pg_stat_activity;"
   # Active connections should be well below max_connections
   ```

3. **Review diagnostic commands** (see Diagnostic Commands section for validation queries)

4. **Consider rollback and retry**:
   ```bash
   # Rollback to v1.x state
   psql codebase_mcp < backup_20250115_103000.sql

   # Address root cause (permissions, disk space, etc.)

   # Retry migration with resolved issues
   ```

#### 2. Missing Environment Variables

**Symptom**:
- Server fails to start after migration
- Configuration validation errors in server logs
- Error messages referencing undefined environment variables

**Possible Causes**:
- `.env` file missing new v2.0 optional variables
- Environment variable names typo or incorrect format
- Configuration management system not updated with new variables

**Solution**:

1. **Add missing optional variables to `.env` file**:
   ```bash
   # Append v2.0 optional variables with defaults
   cat >> .env <<EOF

   # v2.0 Multi-Project Workspace Integration (Optional)
   # WORKFLOW_MCP_URL=http://localhost:8080
   # WORKFLOW_MCP_TIMEOUT=1.0
   # WORKFLOW_MCP_CACHE_TTL=60
   EOF
   ```

2. **Verify environment variable format**:
   ```bash
   # Check for syntax errors in .env file
   grep -E "^[A-Z_]+=" .env
   # Each line should match KEY=value format

   # Verify no duplicate definitions
   sort .env | uniq -d
   # Should return no results
   ```

3. **Reference FR-013** for complete environment variable specifications:
   - See "Environment Variable Changes" section for default values
   - See "Breaking Changes Summary" section for validation rules
   - All v2.0 optional variables have sensible defaults if omitted

4. **Restart server after configuration changes**:
   ```bash
   # Reload configuration
   sudo systemctl restart codebase-mcp.service

   # Verify startup success
   sudo systemctl status codebase-mcp.service
   journalctl -u codebase-mcp.service -n 50
   ```

#### 3. PostgreSQL Connection Errors

**Symptom**:
- "could not connect to server" errors during or after migration
- "FATAL: too many connections" error messages
- Intermittent connection timeouts

**Possible Causes**:
- `max_connections` limit exceeded by migration process
- Incorrect DATABASE_URL credentials or connection parameters
- PostgreSQL service not running or unreachable
- Connection pool exhaustion from concurrent operations

**Solution**:

1. **Verify PostgreSQL service status**:
   ```bash
   # Check service is running
   sudo systemctl status postgresql

   # Check PostgreSQL is listening
   netstat -an | grep 5432
   # Should show LISTEN state on port 5432
   ```

2. **Check connection pool settings**:
   ```bash
   # Review current connections
   psql codebase_mcp -c "SELECT count(*) FROM pg_stat_activity WHERE datname='codebase_mcp';"

   # Check max_connections setting
   psql -c "SHOW max_connections;"

   # Increase if needed (requires PostgreSQL restart)
   # Edit postgresql.conf: max_connections = 200
   sudo systemctl restart postgresql
   ```

3. **Verify DATABASE_URL format**:
   ```bash
   # Check .env file for correct format
   grep DATABASE_URL .env
   # Should match: postgresql+asyncpg://user:password@host:port/database

   # Test connection manually
   psql "$DATABASE_URL"
   # Should connect successfully
   ```

4. **Adjust connection pool parameters** (if using asyncpg):
   ```python
   # In server configuration, adjust pool settings:
   # min_size=2, max_size=10, max_inactive_connection_lifetime=300
   ```

#### 4. Data Validation Failures

**Symptom**:
- Search queries return no results after migration
- Repository count mismatch between v1.x and v2.0
- Missing or corrupted embeddings in search results
- Validation commands report inconsistencies

**Possible Causes**:
- Incomplete migration due to premature script termination
- Corrupted embeddings during schema modifications
- Foreign key constraint violations during data migration
- Incorrect `project_id` assignments in migrated data

**Solution**:

1. **Run validation commands** (see Post-Migration Validation section):
   ```bash
   # Check repository count
   psql codebase_mcp -c "SELECT COUNT(*) FROM repositories;"

   # Check file_chunks integrity
   psql codebase_mcp -c "SELECT COUNT(*) FROM file_chunks WHERE embedding IS NOT NULL;"

   # Verify project_id consistency
   psql codebase_mcp -c "SELECT DISTINCT project_id FROM repositories;"
   psql codebase_mcp -c "SELECT DISTINCT project_id FROM file_chunks;"
   ```

2. **Compare with pre-migration baseline**:
   ```bash
   # Check pre-migration counts from backup manifest
   cat migration-backup-manifest-*.txt

   # Compare with current counts
   psql codebase_mcp -c "SELECT COUNT(*) FROM repositories;" > post-migration-counts.txt
   diff pre-migration-schema-*.txt post-migration-counts.txt
   ```

3. **Re-run migration with clean backup**:
   ```bash
   # Restore from backup
   psql codebase_mcp < backup_20250115_103000.sql

   # Verify restoration success
   psql codebase_mcp -c "\dt+"
   # Should show v1.x schema

   # Re-run migration script with verbose logging
   ./migrate-v1-to-v2.sh --verbose 2>&1 | tee migration-retry.log
   ```

4. **Re-index repositories if embeddings corrupted**:
   ```bash
   # Get list of repositories
   psql codebase_mcp -c "SELECT id, path FROM repositories;"

   # Re-index each repository using v2.0 API
   codebase-mcp index /path/to/repo1 --force
   codebase-mcp index /path/to/repo2 --force
   ```

### Support Resources

If you continue to experience issues after consulting this troubleshooting guide, the following resources are available:

**GitHub Issues**:
- Report bugs and migration issues: https://github.com/codebase-mcp/codebase-mcp/issues
- Search existing issues before creating new ones
- Include migration logs, error messages, and system information

**Community Discussion**:
- GitHub Discussions: https://github.com/codebase-mcp/codebase-mcp/discussions
- Ask questions and share migration experiences
- Community-contributed troubleshooting solutions

**Documentation**:
- Main documentation: https://github.com/codebase-mcp/codebase-mcp/blob/master/README.md
- Migration specification: `specs/010-v2-documentation/spec.md` (in repository)
- Database operations guide: `docs/operations/DATABASE_RESET.md` (in repository)

**Professional Support**:
- For production environments requiring migration assistance, contact the maintainers via GitHub Issues with the "priority-support" label
- Include detailed environment information, logs, and business impact assessment

---

## FAQ

This section addresses frequently asked questions about the v1.x to v2.0 migration process.

### General Migration Questions

#### What data is lost during migration?

**All v1.x project management data will be permanently lost**, including:

**Discarded Data Types**:
- **Projects and project sessions**: All project workspace metadata, settings, and session history
- **Entity types and entity instances**: Custom entity type definitions and all entity data
- **Work items and dependencies**: Task hierarchies, work item metadata, and dependency graphs
- **Deployments and relationships**: Deployment records and entity/work item relationships

**Preserved Data Types**:
- **Indexed repositories**: All repository metadata (path, name, timestamps) is preserved
- **Code embeddings**: All semantic search vectors remain intact and searchable
- **Search functionality**: Search performance and accuracy characteristics are unchanged

**Rationale**: Project management, entity tracking, and work item features have been extracted to the separate [workflow-mcp](https://github.com/workflow-mcp) server to maintain single-responsibility focus on semantic code search capabilities. This architectural change aligns with the v2.0 constitutional principle of "Simplicity Over Features".

**Migration Path for Project Data**: If you require project management capabilities after migration, install the separate workflow-mcp server and export v1.x data before migration (see "Optional Pre-Migration Steps" for export commands).

#### Can I migrate incrementally?

**No, the migration is an all-or-nothing operation.** Partial migration states are not supported due to breaking schema changes that affect multiple interdependent tables.

**Why All-or-Nothing**:
- v1.x and v2.0 database schemas are incompatible
- Foreign key relationships between dropped and retained tables must be severed atomically
- `project_id` column additions require consistent state across all tables

**Testing Strategy**:
However, you **can and should test migration in a staging environment first** before executing in production:

1. **Clone production database to staging**:
   ```bash
   pg_dump -h prod-host -U postgres codebase_mcp | psql -h staging-host -U postgres codebase_mcp_staging
   ```

2. **Execute full migration in staging**:
   ```bash
   # Run migration against staging database
   DATABASE_URL=postgresql://staging-host/codebase_mcp_staging ./migrate-v1-to-v2.sh
   ```

3. **Validate staging migration**:
   - Run all post-migration validation commands
   - Test search functionality with real queries
   - Verify repository counts and embedding integrity

4. **Test rollback procedure in staging**:
   ```bash
   # Restore staging to v1.x state
   psql codebase_mcp_staging < backup_staging_20250115.sql
   ```

5. **Execute production migration** only after staging validation succeeds

**Downtime Implications**: Plan for 15-90 minutes of continuous downtime during production migration (see "Prerequisites" section for sizing guidance).

#### How long does migration take?

**Migration duration depends on database size and system resources.** Timing guidance is deferred to Phase 06 performance testing (see FR-020 in spec.md for performance requirements).

**General Guidance**:
- **Small installations** (<10 repositories, <100K file chunks): **15-30 minutes**
- **Medium installations** (10-50 repositories, 100K-500K file chunks): **30-45 minutes**
- **Large installations** (>50 repositories, >500K file chunks): **45-90 minutes**

**Factors Affecting Duration**:
1. **Database size**: Larger databases require more time for schema modifications and data migration
2. **Disk I/O performance**: SSD vs HDD significantly impacts migration speed
3. **PostgreSQL configuration**: `shared_buffers`, `work_mem`, and `maintenance_work_mem` settings
4. **System load**: Concurrent database operations may slow migration

**Performance Benchmarks** (from Phase 06 testing - to be added):
- Schema modifications (DROP TABLE operations): <5 minutes for any size
- ALTER TABLE ADD COLUMN operations: ~2-3 minutes per million rows
- Index rebuilds: ~5-10 minutes per million rows with embeddings

**Monitoring Migration Progress**:
```bash
# Watch migration logs in real-time
tail -f /tmp/codebase-mcp-migration.log

# Check PostgreSQL activity
psql codebase_mcp -c "SELECT query, state, wait_event FROM pg_stat_activity WHERE datname='codebase_mcp';"
```

**Planning Downtime Windows**:
- Add 50% buffer to estimated duration (e.g., 30 minutes estimated = 45 minutes planned)
- Schedule migration during low-usage periods
- Communicate expected completion time to users
- Prepare rollback plan if migration exceeds planned window

---

<!--
TODO: Additional sections may be added in future updates:
- Performance optimization tips post-migration
- Workflow-mcp integration examples
- Advanced troubleshooting scenarios
-->
