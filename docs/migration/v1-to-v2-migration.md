# Migration Guide: v1.x to v2.0

## Overview

This guide provides step-by-step instructions for safely upgrading an existing Codebase MCP Server v1.x installation to v2.0. The v2.0 release represents a major architectural change focused on semantic code search capabilities, with significant breaking changes.

**Purpose**: Enable existing v1.x users to migrate to v2.0 with minimal downtime and data preservation where applicable.

**Scope**: This guide covers database-per-project migration, tool API changes, and environment variable updates for production installations.

**Target Audience**: System administrators, DevOps engineers, and development teams managing v1.x installations.

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
| `WORKFLOW_MCP_URL` | Optional | *(none)* | Optional workflow-mcp server URL for automatic project detection. Enables automatic `project_id` resolution from Git repository context. |
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

<!--
TODO: Sections to be added in subsequent tasks:
- Breaking Changes Summary (T009)
- Removed Tools List (T010)
- Upgrade Procedure (T014)
- Post-Migration Validation (T015)
- Diagnostic Commands (T016)
- Rollback Procedure (T017)
- Troubleshooting (T018)
- FAQ (T019)
-->
