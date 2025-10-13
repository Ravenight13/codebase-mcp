# Research: Documentation Structure & Best Practices

## Decision Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Markdown Documentation Structure** | GitHub-flavored Markdown with hierarchical TOC navigation | GitHub native rendering, ubiquitous tooling, accessibility friendly, version control friendly |
| **Migration Guide Structure** | Breaking Changes First + Step-by-Step + Rollback pattern | Risk communication upfront, procedural clarity, safety-first approach matches production quality principle |
| **Configuration Documentation** | Environment Variable Tables + PostgreSQL Calculation Examples | Scannable reference format, explicit defaults, concrete calculation examples prevent misconfiguration |
| **Architecture Documentation** | Mermaid Diagrams + Prose + Code Examples | Native GitHub rendering, maintainable text-based diagrams, visual-textual balance |
| **API Reference Documentation** | OpenAPI-Inspired Structure + Explicit Deprecation Notices | Industry-standard parameter documentation, clear migration path for removed tools |
| **Documentation Validation** | Manual Checklist + Documented Procedures | Appropriate for Phase 05 scope, defers automation to Phase 07, ensures accuracy through structured process |

---

## 1. Markdown Documentation Structure

### Decision

Use **GitHub-flavored Markdown (GFM)** with the following structure pattern for all documentation artifacts:

**Standard Structure Template**:
```markdown
# Title (H1 - single per document)

> Brief description (1-2 sentences explaining purpose)

## Table of Contents (H2 - for documents >500 lines)
- [Section 1](#section-1)
- [Section 2](#section-2)

## Overview (H2)
High-level introduction to the content

## Core Content Sections (H2)
Detailed content organized hierarchically

### Subsections (H3)
Specific topics within sections

#### Details (H4 - sparingly)
Fine-grained details when necessary

## Examples (H2)
Practical usage examples with code blocks

## Troubleshooting (H2 - where applicable)
Common issues and solutions

## Related Resources (H2)
Links to other relevant documentation
```

**Typography Conventions**:
- **Bold** for emphasis on key terms first mention
- `Code font` for all technical terms (tool names, parameters, file paths, commands)
- *Italic* for document references and annotations
- > Blockquotes for warnings, important notes, and callouts
- Tables for structured data (configuration variables, parameter lists)
- Ordered lists for sequential procedures
- Unordered lists for non-sequential information

**Navigation Patterns**:
- README.md acts as the entry point with links to specialized guides
- Each guide starts with a brief description and links back to README
- Cross-references use relative paths: `[Migration Guide](docs/migration/v1-to-v2-migration.md)`
- Anchor links for intra-document navigation: `[Configuration](#configuration)`

### Rationale

GitHub-flavored Markdown is the de facto standard for developer documentation because:

1. **Native Rendering**: GitHub/GitLab render GFM without tooling, making docs immediately accessible
2. **Version Control Friendly**: Plain text format enables meaningful diffs, conflict resolution, and attribution
3. **Accessibility**: Screen readers handle Markdown well, semantic HTML output supports WCAG compliance
4. **Universal Tooling**: Every code editor, IDE, and static site generator supports Markdown
5. **Low Friction**: No build step, no special tooling, immediate editing and preview
6. **Search Friendly**: Plain text enables grep, IDE search, and GitHub's code search

The hierarchical structure with explicit TOC navigation addresses the documented scale (5 artifacts, 38 functional requirements) by providing:
- Quick orientation (overview sections)
- Direct navigation to relevant sections (TOC)
- Scannable structure (H2-H4 hierarchy)
- Progressive disclosure (high-level → detailed)

### Alternatives Considered

- **Alternative 1: Sphinx/reStructuredText** - Rejected because it requires Python tooling, build step, and specialized markup. Adds complexity for marginal benefit (better cross-referencing). Violates "simplicity over features" principle.
- **Alternative 2: AsciiDoc** - Rejected because GitHub rendering support is limited, tooling less universal than Markdown. Better semantic markup doesn't justify adoption barrier for contributors.
- **Alternative 3: Static Site Generator (Docusaurus, MkDocs)** - Rejected for Phase 05 because it requires build infrastructure, deployment process, and maintenance overhead. Documentation-only phase should not introduce new tooling dependencies. Future consideration for Phase 07.
- **Alternative 4: Wiki-style documentation** - Rejected because version control is weaker (separate wiki repo), no PR workflow for changes, harder to keep in sync with code.

### Implementation Guidance

**For this project, apply these specific patterns**:

1. **README.md Structure**:
   ```markdown
   # Codebase MCP Server
   > Brief description

   ## What's New in v2.0
   [Breaking Changes Summary] → link to migration guide

   ## Features
   - 2 tools: index_repository, search_code
   - Multi-project support with project_id parameter
   - workflow-mcp integration (optional)

   ## Installation
   Prerequisites → Installation → Verification

   ## Quick Start
   Basic usage → Multi-project usage

   ## Documentation
   Links to 4 specialized guides

   ## Contributing
   Link to architecture docs
   ```

2. **File Naming Convention**:
   - Use lowercase with hyphens: `v1-to-v2-migration.md`
   - Use descriptive names: `production-config.md` not `config.md`
   - Version-specific files include version: `v1-to-v2-migration.md`

3. **Code Block Standards**:
   - Always specify language: ` ```bash `, ` ```python `, ` ```yaml `
   - Include comments explaining non-obvious commands
   - Show expected output where helpful:
     ```bash
     # Command
     $ pg_dump -h localhost -d codebase_mcp > backup.sql

     # Expected output
     pg_dump: dumping contents of table "repositories"
     pg_dump: dumping contents of table "code_chunks"
     ```

4. **Link Validation**:
   - Use relative paths for internal links: `docs/migration/v1-to-v2-migration.md`
   - Use absolute URLs for external links: `https://github.com/modelcontextprotocol/specification`
   - Maintain a link inventory during authoring (spreadsheet or checklist)
   - Test all links manually before PR submission (FR-032)

5. **Cross-Reference Pattern**:
   - First mention of another guide: full link + brief description
   - Subsequent mentions: inline link only
   - Example: "See the [Configuration Guide](docs/configuration/production-config.md) for PostgreSQL tuning details."

---

## 2. Migration Guide Structure

### Decision

Use **Breaking Changes First + Step-by-Step Procedures + Rollback** pattern:

```markdown
# Migration Guide: Upgrading from v1.x to v2.0

> This guide walks through upgrading codebase-mcp from v1.x to v2.0, including breaking changes, data preservation, and rollback procedures.

## Overview
- Who should use this guide
- Migration scope (what's preserved, what's discarded)
- Estimated time (deferred to Phase 06 per FR-020)

## Breaking Changes Summary
[Upfront, before any procedures - FR-009]

### Tool API Changes
- 14 tools removed (explicit list - FR-010)
- 2 tools retained with project_id parameter added (FR-012)

### Database Schema Changes
- 9 tables dropped (FR-011)
- project_id column added to repositories, code_chunks

### Environment Variable Changes
- New required variables (FR-013)
- Changed defaults

### Data Preservation Policy
- ✅ Preserved: Indexed code repositories
- ❌ Discarded: All v1.x project management data (FR-019)

## Prerequisites
- v1.x installation running
- PostgreSQL access for backup
- Disk space for backups
- Downtime window (production systems)

## Pre-Migration Checklist
- [ ] Review breaking changes section
- [ ] Verify PostgreSQL version (14+)
- [ ] Verify Python version (3.11+)
- [ ] Test rollback procedure in non-production environment
- [ ] Schedule maintenance window

## Backup Procedures (FR-015)
Exact commands with explanations

### Database Backup
```bash
# Command with parameters
pg_dump -h localhost -d codebase_mcp > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Configuration Backup
```bash
cp .env .env.backup
```

## Upgrade Procedure (FR-014, FR-018)

### Step 1: Stop v1.x Server
[Command, validation]

### Step 2: Update Dependencies
[Command, validation]

### Step 3: Run Migration Script
[Command, expected output, duration guidance]

### Step 4: Update Configuration
[New environment variables, changed defaults]

### Step 5: Restart Server
[Command, validation]

### Step 6: Verify Migration Success
[Validation commands - FR-017]

## Post-Migration Validation (FR-017)

### Verify v2.0 Functionality
- Test index_repository with project_id
- Test search_code with project_id
- Verify existing repositories still searchable

### Diagnostic Commands (FR-036)
Commands to detect partial migration state

## Rollback Procedure (FR-016)

### When to Roll Back
- Migration script fails
- v2.0 functionality not working
- Unacceptable data loss discovered

### Rollback Steps
1. Stop v2.0 server
2. Restore database backup
3. Restore configuration backup
4. Reinstall v1.x version
5. Start v1.x server
6. Verify v1.x functionality restored

### Rollback Validation (FR-017)
Commands to confirm v1.x restoration

## Troubleshooting

### Common Issues
- Migration script fails midway (FR-036)
- Missing environment variables
- PostgreSQL connection errors
- Data validation failures

### Support Resources
- GitHub Issues
- Discussion forum link

## Frequently Asked Questions

### What data is lost during migration?
[Explicit answer from FR-019]

### Can I migrate incrementally?
[Answer: no, explain why]

### How long does migration take?
[Deferred to Phase 06 per FR-020]
```

### Rationale

This structure addresses the documented user persona needs:

1. **Breaking Changes First (FR-009)**: Risk communication upfront allows users to make informed go/no-go decisions before investing time in procedures. Matches "production quality standards" constitutional principle by prioritizing safety.

2. **Step-by-Step Procedures (FR-014)**: Sequential numbered steps reduce cognitive load, enable checkpoint validation, and support partial completion. Each step has:
   - Action description
   - Exact command
   - Expected output
   - Validation criteria
   - Recovery procedure if step fails

3. **Rollback Procedure (FR-016)**: Complete restoration path provides safety net for production upgrades. Reduces risk perception and increases confidence in attempting migration.

4. **Validation Commands (FR-017)**: Explicit validation steps throughout (pre-migration, post-step, post-migration, post-rollback) enable users to detect problems early and confirm success.

5. **Troubleshooting Section**: Addresses edge cases from spec (11 documented edge cases) with diagnostic procedures and solutions.

### Alternatives Considered

- **Alternative 1: Procedures First, Breaking Changes Later** - Rejected because users need to understand impact before committing to procedures. Burying breaking changes deep in docs violates production quality principle.
- **Alternative 2: Automated Migration Script Only** - Rejected because interactive scripts require Phase 07 tooling development. Manual procedures with validation commands are appropriate for Phase 05 documentation-only scope.
- **Alternative 3: FAQ-Style Migration Guide** - Rejected because sequential procedures require ordered presentation. FAQs work for reference but not for procedural workflows.
- **Alternative 4: Rollback as Separate Document** - Rejected because users need rollback context during upgrade planning. Separating it increases risk of users missing critical safety information.

### Implementation Guidance

**For this project, apply these specific patterns**:

1. **Breaking Changes Section**:
   - Lead with highest-impact changes (tool removals)
   - Use tables for comparison (v1.x vs v2.0)
   - Explicit data preservation policy callout box
   - Link to detailed API changes in API reference doc

2. **Command Documentation**:
   - Always include comments explaining what command does
   - Show expected output for validation
   - Provide error recovery instructions
   - Use consistent prompt notation (`$` for user commands)

3. **Validation Commands**:
   - Provide SQL queries to check schema state
   - Provide Python scripts to verify tool functionality
   - Provide PostgreSQL commands to check database existence
   - Include success criteria for each validation

4. **Rollback Procedure**:
   - Mirror upgrade procedure structure (same step count)
   - Reference backup locations from backup section
   - Include validation for each rollback step
   - Provide troubleshooting for partial rollback scenarios

5. **Data Preservation Communication**:
   - Use visual indicators (✅ ❌) for scannable lists
   - Be explicit about what's discarded (FR-019)
   - Explain why data is not migrated (architectural decision)
   - Provide export options if users need v1.x data archived

---

## 3. Configuration Documentation

### Decision

Use **Environment Variable Reference Tables + PostgreSQL Calculation Examples + Production Tuning Guidance** pattern:

```markdown
# Configuration Guide: Production Deployment

> Comprehensive configuration reference for production deployments of codebase-mcp v2.0, covering environment variables, connection pool tuning, and PostgreSQL optimization.

## Configuration Overview

Quick links to sections:
- [Environment Variables Reference](#environment-variables-reference)
- [Connection Pool Tuning](#connection-pool-tuning)
- [PostgreSQL Configuration](#postgresql-configuration)
- [workflow-mcp Integration](#workflow-mcp-integration)
- [Monitoring & Health Checks](#monitoring--health-checks)

## Environment Variables Reference (FR-021)

### Core Configuration

| Variable | Required | Default | Description | Example |
|----------|----------|---------|-------------|---------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection string | `postgresql://user:pass@localhost/codebase_mcp` |
| `OLLAMA_BASE_URL` | Yes | `http://localhost:11434` | Ollama API endpoint | `http://ollama:11434` |
| `EMBEDDING_MODEL` | No | `nomic-embed-text` | Ollama embedding model | `all-minilm` |

### Multi-Project Configuration (FR-022, FR-023)

| Variable | Required | Default | Description | Impact |
|----------|----------|---------|-------------|--------|
| `MAX_PROJECTS` | No | `10` | Maximum concurrent project connection pools | 1 pool = MAX_CONNECTIONS_PER_POOL connections |
| `MAX_CONNECTIONS_PER_POOL` | No | `20` | PostgreSQL connections per project pool | Total = MAX_PROJECTS × MAX_CONNECTIONS_PER_POOL |
| `PROJECT_POOL_TIMEOUT` | No | `300` | Pool idle timeout (seconds) before LRU eviction | Higher = less churn, more memory |

### workflow-mcp Integration (FR-026)

| Variable | Required | Default | Description | Example |
|----------|----------|---------|-------------|---------|
| `WORKFLOW_MCP_URL` | No | - | workflow-mcp SSE endpoint for project detection | `http://localhost:8080/sse` |
| `WORKFLOW_MCP_TIMEOUT` | No | `5` | Request timeout (seconds) | `10` |

## Connection Pool Tuning (FR-022, FR-023)

### Understanding the Calculation (FR-024)

Total PostgreSQL connections consumed:
```
Total Connections = MAX_PROJECTS × MAX_CONNECTIONS_PER_POOL
```

**Example Scenarios**:

| Scenario | MAX_PROJECTS | MAX_CONNECTIONS_PER_POOL | Total Connections | Use Case |
|----------|--------------|---------------------------|-------------------|----------|
| Small Deployment | 5 | 10 | 50 | Single-user development |
| Medium Deployment | 10 | 20 | 200 | Small team (default) |
| Large Deployment | 20 | 25 | 500 | Multi-tenant production |

### PostgreSQL max_connections Requirement (FR-024)

Your PostgreSQL `max_connections` setting MUST exceed total connection pool consumption plus overhead:

```
PostgreSQL max_connections ≥ (MAX_PROJECTS × MAX_CONNECTIONS_PER_POOL) + 10
```

The +10 buffer accounts for:
- Administrative connections (pg_dump, psql)
- Monitoring tools
- Connection pool initialization spikes

**Configuration Validation**:
```bash
# Check current PostgreSQL max_connections
psql -h localhost -c "SHOW max_connections;"

# Expected: Value ≥ (MAX_PROJECTS × MAX_CONNECTIONS_PER_POOL + 10)
```

### Tuning MAX_PROJECTS (FR-022)

**Tradeoffs**:
- ✅ Higher value: More concurrent projects, less LRU eviction churn
- ❌ Higher value: More PostgreSQL connections, more memory usage
- ✅ Lower value: Less resource consumption, more predictable performance
- ❌ Lower value: More frequent pool eviction, connection overhead

**Recommendations**:
- Development: 5 projects (minimal overhead)
- Production (single-team): 10 projects (default, balanced)
- Production (multi-tenant): 20-50 projects (requires PostgreSQL tuning)

### Tuning MAX_CONNECTIONS_PER_POOL (FR-023)

**Tradeoffs**:
- ✅ Higher value: More concurrent queries per project, better throughput
- ❌ Higher value: More total connections, PostgreSQL overhead
- ✅ Lower value: Fewer total connections, less memory
- ❌ Lower value: Query queueing under load, slower response times

**Recommendations**:
- Development: 5 connections (low concurrency expected)
- Production (small repos): 10-15 connections (moderate concurrency)
- Production (large repos): 20-30 connections (high concurrency, large indexing jobs)

## PostgreSQL Configuration (FR-025)

### Production Tuning Parameters (FR-025)

```ini
# postgresql.conf

# Connection limits (adjust based on MAX_PROJECTS calculation)
max_connections = 300

# Memory settings (tune based on available RAM)
shared_buffers = 4GB
effective_cache_size = 12GB
maintenance_work_mem = 1GB
work_mem = 64MB

# Query performance
random_page_cost = 1.1  # For SSD storage
effective_io_concurrency = 200

# Write performance
wal_buffers = 16MB
checkpoint_completion_target = 0.9

# Logging (for production monitoring)
log_min_duration_statement = 1000  # Log queries >1s
log_line_prefix = '%m [%p] %q%u@%d '
```

**Rationale for Settings**:
- `shared_buffers = 4GB`: codebase-mcp performs frequent GIN index lookups on JSONB columns; larger buffer cache reduces disk I/O
- `effective_cache_size = 12GB`: Hints query planner about available OS cache for embedding vector similarity queries
- `work_mem = 64MB`: Embedding searches may require sorting; adequate work_mem prevents disk-based sorts

## Monitoring & Health Checks (FR-038)

### Connection Pool Metrics (FR-038)

**Key Indicators**:
1. Active pool count (should not exceed MAX_PROJECTS)
2. Connections per pool (should not exceed MAX_CONNECTIONS_PER_POOL)
3. Pool eviction frequency (high frequency indicates MAX_PROJECTS too low)
4. Query latency (increasing latency may indicate connection exhaustion)

**Monitoring Queries**:
```sql
-- Check active databases (one per project)
SELECT datname FROM pg_database WHERE datname LIKE 'codebase_%';

-- Check connection count per database
SELECT datname, count(*)
FROM pg_stat_activity
WHERE datname LIKE 'codebase_%'
GROUP BY datname;

-- Check total connections
SELECT count(*) FROM pg_stat_activity;
```

### Health Check Endpoints

[Document any health check endpoints if they exist in v2.0]

## Configuration Validation Checklist (FR-027)

Before deploying to production:

- [ ] `DATABASE_URL` connects successfully: `psql $DATABASE_URL -c "SELECT 1;"`
- [ ] `OLLAMA_BASE_URL` responds: `curl $OLLAMA_BASE_URL/api/version`
- [ ] Embedding model available: `curl $OLLAMA_BASE_URL/api/show -d '{"name":"nomic-embed-text"}'`
- [ ] PostgreSQL `max_connections` sufficient: Use calculation formula
- [ ] workflow-mcp reachable (if configured): `curl $WORKFLOW_MCP_URL`
- [ ] Test indexing: Index small test repository
- [ ] Test search: Perform test search query
- [ ] Verify project isolation: Index two projects, confirm separate databases

## Troubleshooting

### "Too many connections" error
- Symptom: PostgreSQL rejects connections
- Cause: `max_connections` too low or connection leak
- Solution: Increase PostgreSQL `max_connections` or reduce `MAX_PROJECTS × MAX_CONNECTIONS_PER_POOL`

### Slow query performance
- Symptom: Search queries >1s response time
- Cause: Insufficient PostgreSQL memory or disk I/O bottleneck
- Solution: Increase `shared_buffers` and `effective_cache_size`, use SSD storage

### Frequent pool evictions
- Symptom: Logs show "Evicting project pool X"
- Cause: `MAX_PROJECTS` too low for working set
- Solution: Increase `MAX_PROJECTS` (and PostgreSQL `max_connections`)
```

### Rationale

This structure addresses administrator persona needs (User Story 3) with:

1. **Reference Tables (FR-021)**: Scannable format for quick lookup during configuration. Columns include defaults to support "what happens when user doesn't set variable" edge case.

2. **Calculation Examples (FR-024)**: Concrete scenarios prevent misconfiguration. Formula + examples + validation commands enable administrators to verify their configuration before deployment.

3. **Tradeoff Documentation (FR-022, FR-023)**: Explicit pros/cons for tuning decisions help administrators make informed choices based on their deployment context (small team vs multi-tenant).

4. **Production Tuning Guidance (FR-025)**: PostgreSQL-specific recommendations address database performance requirements. Rationale column explains why settings matter for codebase-mcp workload.

5. **Monitoring Metrics (FR-038)**: SQL queries for connection pool monitoring enable administrators to validate deployment health and diagnose issues.

6. **Validation Checklist (FR-027)**: Pre-deployment checklist with commands prevents common configuration errors. Addresses "administrator deploys correctly on first attempt" success criterion (SC-010).

### Alternatives Considered

- **Alternative 1: Prose-Only Configuration Docs** - Rejected because administrators need reference format, not narrative. Tables enable quick scanning during configuration.
- **Alternative 2: Auto-Generated Config Docs from Schema** - Rejected because Phase 05 is documentation-only. Auto-generation requires Phase 07 tooling.
- **Alternative 3: Separate Configuration File with Comments** - Rejected because environment variables are the configuration mechanism (12-factor app pattern). Documentation explains the variables, not replaces them.
- **Alternative 4: Configuration Wizard/Script** - Rejected because interactive tooling requires Phase 07 development. Manual configuration with validation checklist is appropriate for Phase 05.

### Implementation Guidance

**For this project, apply these specific patterns**:

1. **Environment Variable Tables**:
   - Group related variables (Core, Multi-Project, Integration)
   - Required column distinguishes mandatory from optional
   - Default column shows behavior when unset
   - Example column provides concrete value format

2. **Calculation Examples**:
   - Lead with formula
   - Provide 3-5 concrete scenarios
   - Include validation commands
   - Explain buffer/overhead calculations

3. **Tradeoff Documentation**:
   - Use ✅ ❌ symbols for scannable pros/cons
   - Provide context-specific recommendations
   - Link to monitoring section for validation

4. **PostgreSQL Tuning**:
   - Use actual configuration file syntax (postgresql.conf)
   - Include comments explaining rationale
   - Provide ranges, not single values
   - Link to PostgreSQL official docs for deeper tuning

5. **Validation Checklist**:
   - Checkbox format for copy-paste workflow
   - Include exact validation commands
   - Show expected output where helpful
   - Order by dependency (database before application)

---

## 4. Architecture Documentation

### Decision

Use **Mermaid Diagrams + Component Prose + Code Examples** pattern:

```markdown
# Architecture: Multi-Project Design

> Technical overview of codebase-mcp v2.0 architecture, covering database-per-project strategy, connection pool management, and workflow-mcp integration.

## Architecture Overview

High-level description of system components and design philosophy.

## Multi-Project Architecture Diagram (FR-028)

```mermaid
graph TB
    Client[MCP Client<br/>Claude/Cursor/etc]
    Server[codebase-mcp Server<br/>FastMCP + Python SDK]
    PoolMgr[Connection Pool Manager<br/>LRU Cache]
    WorkflowMCP[workflow-mcp Server<br/>Optional]

    DB_Default[(PostgreSQL<br/>codebase_default)]
    DB_Proj1[(PostgreSQL<br/>codebase_proj1)]
    DB_Proj2[(PostgreSQL<br/>codebase_proj2)]

    Client -->|SSE| Server
    Server -->|index_repository<br/>search_code| PoolMgr
    Server -.->|get_active_project<br/>Optional| WorkflowMCP

    PoolMgr -->|Project: default| DB_Default
    PoolMgr -->|Project: proj1| DB_Proj1
    PoolMgr -->|Project: proj2| DB_Proj2

    PoolMgr -.->|LRU Eviction<br/>when MAX_PROJECTS exceeded| DB_Proj2

    style Server fill:#e1f5ff
    style PoolMgr fill:#fff4e1
    style WorkflowMCP fill:#f0f0f0,stroke-dasharray: 5 5
```

**Component Responsibilities**:
- **MCP Client**: AI coding assistant (Claude, Cursor) invoking tools via SSE
- **codebase-mcp Server**: FastMCP-based server exposing 2 tools with multi-project routing
- **Connection Pool Manager**: Maintains up to MAX_PROJECTS pools, LRU eviction policy
- **workflow-mcp Server**: Optional automatic project detection via get_active_project
- **PostgreSQL Databases**: One database per project for schema isolation

## Database-Per-Project Strategy (FR-029)

### Design Decision

Each project gets an isolated PostgreSQL database with naming convention:
```
codebase_{sanitized_project_id}
```

**Examples**:
| project_id | Database Name | Notes |
|------------|---------------|-------|
| `default` | `codebase_default` | Used when no project_id specified |
| `my-app` | `codebase_my_app` | Hyphens converted to underscores |
| `frontend.ui` | `codebase_frontend_ui` | Dots converted to underscores |
| `client_a` | `codebase_client_a` | Underscores preserved |

**Sanitization Rules**:
- Convert non-alphanumeric characters to underscores
- Lowercase all characters
- Preserve underscores
- Max length: 63 characters (PostgreSQL limit) minus `codebase_` prefix (9 chars) = 54 chars for project_id

### Rationale

Database-per-project isolation provides:

1. **Schema Independence**: Each project has identical schema (repositories, code_chunks, embeddings tables) without cross-project contamination
2. **Query Performance**: No project_id filtering needed in queries; PostgreSQL query planner optimizes per-database
3. **Data Locality**: Related code chunks physically co-located, improving cache efficiency
4. **Backup Granularity**: Drop/backup/restore projects independently
5. **Multi-Tenancy**: Natural tenant isolation for SaaS deployments
6. **Resource Limits**: PostgreSQL database-level resource limits if needed

**Tradeoffs**:
- ❌ More PostgreSQL databases to manage (monitoring, backups)
- ❌ More connections consumed (MAX_PROJECTS × MAX_CONNECTIONS_PER_POOL)
- ✅ Better isolation, performance, and operational flexibility

### Schema Structure

Each project database contains identical schema:

```sql
-- Simplified schema (see full schema in migrations/)

CREATE TABLE repositories (
    id UUID PRIMARY KEY,
    repo_path TEXT NOT NULL,
    indexed_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE code_chunks (
    id UUID PRIMARY KEY,
    repository_id UUID REFERENCES repositories(id),
    file_path TEXT NOT NULL,
    content TEXT NOT NULL,
    start_line INT,
    end_line INT,
    embedding vector(768)  -- pgvector type
);

CREATE INDEX idx_embedding ON code_chunks USING ivfflat (embedding vector_cosine_ops);
```

## Connection Pool Design (FR-030)

### Pool Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Uninitialized
    Uninitialized --> Creating: First query for project
    Creating --> Active: Pool created
    Active --> Active: Queries served
    Active --> Idle: No queries for PROJECT_POOL_TIMEOUT
    Idle --> Active: New query received
    Idle --> Evicted: LRU eviction (MAX_PROJECTS limit)
    Active --> Evicted: LRU eviction (MAX_PROJECTS limit)
    Evicted --> [*]
    Evicted --> Creating: Query after eviction (recreates pool)
```

**State Descriptions**:
- **Uninitialized**: No pool exists for project yet
- **Creating**: Pool initialization in progress (database creation, connection opening)
- **Active**: Pool serving queries, connections open
- **Idle**: No active queries, connections kept warm for PROJECT_POOL_TIMEOUT seconds
- **Evicted**: Pool closed due to LRU eviction when MAX_PROJECTS limit exceeded

### LRU Eviction Policy (FR-030)

When a query arrives for project N+1 and MAX_PROJECTS pools already exist:

1. Identify least-recently-used pool (oldest last query timestamp)
2. Close all connections in LRU pool
3. Remove pool from cache
4. Create new pool for project N+1
5. Serve query

**Example Timeline**:
```
MAX_PROJECTS=3
t0: Query project A → Pool A created (Pools: A)
t1: Query project B → Pool B created (Pools: A, B)
t2: Query project C → Pool C created (Pools: A, B, C)
t3: Query project A → Pool A reused (Pools: A, B, C; LRU order: B, C, A)
t4: Query project D → Pool B evicted (least recently used), Pool D created (Pools: A, C, D)
```

**Performance Implications**:
- Pool creation: ~100-500ms (database creation, schema initialization)
- Pool eviction: ~50-100ms (connection cleanup)
- Frequent eviction indicates MAX_PROJECTS too low for working set

### Connection Pool Configuration

Each pool maintains:
- **Min connections**: 2 (kept warm)
- **Max connections**: MAX_CONNECTIONS_PER_POOL (default 20)
- **Timeout**: 30 seconds for acquiring connection
- **Idle timeout**: PROJECT_POOL_TIMEOUT (default 300s)

**Concurrency Example**:
```
MAX_CONNECTIONS_PER_POOL=20
- 5 concurrent indexing operations (5 connections)
- 15 concurrent search queries (15 connections)
Total: 20 connections in use
21st query waits for available connection (up to 30s timeout)
```

## workflow-mcp Integration Architecture (FR-031)

```mermaid
sequenceDiagram
    participant Client as MCP Client
    participant CBServer as codebase-mcp
    participant WFServer as workflow-mcp
    participant DB as PostgreSQL

    Client->>CBServer: search_code(query, project_id=None)
    CBServer->>WFServer: get_active_project() [timeout=5s]

    alt workflow-mcp responds
        WFServer-->>CBServer: {"active_project": "frontend-ui"}
        CBServer->>DB: Query codebase_frontend_ui
        DB-->>CBServer: Search results
    else workflow-mcp timeout
        CBServer->>DB: Query codebase_default (fallback)
        DB-->>CBServer: Search results
    end

    CBServer-->>Client: Search results
```

**Integration Behavior**:
1. If `project_id` parameter provided: Use specified project (no workflow-mcp call)
2. If `project_id=None` and `WORKFLOW_MCP_URL` set: Call `get_active_project()` with timeout
3. If workflow-mcp responds: Use returned project_id
4. If workflow-mcp timeout/error: Fallback to "default" project
5. If `WORKFLOW_MCP_URL` not set: Use "default" project directly

**Fallback Rationale**:
- Local-first architecture principle (Principle II)
- System must function without external dependencies
- Graceful degradation under network issues

## Component Interactions

### Indexing Flow

```
Client → index_repository(repo_path, project_id)
  ↓
Pool Manager → Get/create pool for project_id
  ↓
Database Creation → Create codebase_{project_id} if not exists
  ↓
Repository Scanning → Tree-sitter AST parsing
  ↓
Chunking → Extract code chunks with context
  ↓
Embedding Generation → Ollama API call (nomic-embed-text)
  ↓
Storage → Insert into code_chunks table with vector
  ↓
Response → {files_indexed, chunks_created, duration}
```

### Search Flow

```
Client → search_code(query, project_id)
  ↓
Project Resolution → project_id or workflow-mcp or default
  ↓
Pool Manager → Get pool for resolved project_id
  ↓
Query Embedding → Ollama API call for query vector
  ↓
Vector Search → pgvector cosine similarity query
  ↓
Result Ranking → Top-k results with scores
  ↓
Context Retrieval → Fetch surrounding lines
  ↓
Response → {results, similarity_scores, context}
```

## Design Rationale Summary

**Why Multi-Project Architecture?**
- Enables SaaS/multi-tenant deployments
- Supports workflow-mcp ecosystem integration
- Maintains simplicity (single codebase, generic tools)

**Why Database-Per-Project?**
- Better isolation, performance, and operational flexibility
- Aligns with PostgreSQL strengths (per-database optimization)
- Simplifies schema management (no discriminator columns)

**Why Connection Pool Manager?**
- Amortizes connection overhead across queries
- LRU eviction balances resource usage and performance
- Configurable limits adapt to deployment size

**Why Optional workflow-mcp?**
- Local-first architecture (works standalone)
- Graceful degradation (fallback to default project)
- Enables advanced workflows without coupling
```

### Rationale

This structure addresses maintainer persona needs (User Story 5) with:

1. **Mermaid Diagrams (FR-028, FR-031)**: Visual representation of architecture aids comprehension. GitHub renders Mermaid natively (no build tooling). Text-based format enables version control diffs and review.

2. **Component Prose**: Explains design decisions with rationale. Answers "why this design?" for contributors evaluating alternatives or debugging issues.

3. **Code Examples**: Concrete SQL, naming examples, and flow diagrams make abstract concepts tangible. Supports "maintainer understands architecture well enough to contribute" (SC-012).

4. **Database Naming Convention (FR-029)**: Explicit sanitization rules with examples prevent confusion. Documents implementation detail critical for debugging database connection issues.

5. **LRU Eviction Explanation (FR-030)**: Timeline example clarifies lifecycle. Performance implications guide tuning decisions and troubleshooting.

### Alternatives Considered

- **Alternative 1: PlantUML Diagrams** - Rejected because GitHub doesn't render PlantUML natively (requires external tool or embedded images). Mermaid provides native GitHub support.
- **Alternative 2: ASCII Diagrams** - Rejected because complexity of multi-project architecture exceeds ASCII diagram readability. Mermaid provides better visual clarity.
- **Alternative 3: External Diagramming Tool (Lucidchart, Draw.io)** - Rejected because external tools create binary artifacts not version-controllable as text. Updates require manual export/import workflow.
- **Alternative 4: Architecture Decision Records (ADRs)** - Considered complementary but not replacement. ADRs document decisions over time; architecture guide documents current state. Future consideration for Phase 07.

### Implementation Guidance

**For this project, apply these specific patterns**:

1. **Mermaid Diagram Standards**:
   - Use `graph TB` (top-bottom) for component diagrams
   - Use `sequenceDiagram` for interaction flows
   - Use `stateDiagram-v2` for lifecycle diagrams
   - Include legend/annotations for symbol meanings
   - Keep diagrams focused (one concept per diagram)

2. **Database Naming Examples**:
   - Provide table with 5-10 examples
   - Cover edge cases (special characters, length limits)
   - Show sanitization rules explicitly
   - Link to code implementing sanitization

3. **Component Descriptions**:
   - Start with overview (what it does)
   - Explain responsibilities (what it's responsible for)
   - Provide rationale (why this design)
   - Show interactions (how it connects to other components)

4. **Flow Diagrams**:
   - Use indented ASCII for simple flows
   - Use Mermaid sequence diagrams for complex flows
   - Include failure paths, not just happy path
   - Annotate with timing/performance notes

5. **Design Rationale**:
   - Summarize key decisions at end
   - Link decisions to constitutional principles
   - Explain tradeoffs explicitly
   - Provide "Why X?" subsections for major choices

---

## 5. API Reference Documentation

### Decision

Use **OpenAPI-Inspired Structure + Explicit Deprecation Notices** pattern:

```markdown
# API Reference: MCP Tools

> Complete reference for codebase-mcp v2.0 MCP tools, including parameters, return values, and examples.

## Overview

codebase-mcp v2.0 provides **2 MCP tools** for semantic code search:
1. `index_repository` - Index a code repository for semantic search
2. `search_code` - Search indexed repositories using natural language

**Breaking Changes from v1.x**: See [Removed Tools](#removed-tools) section below.

## index_repository

Indexes a code repository into PostgreSQL with semantic embeddings for natural language search.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `repo_path` | string | Yes | - | Absolute path to repository directory to index |
| `project_id` | string | No | `"default"` | Project identifier for multi-project isolation. Defaults to "default" for standalone usage. |
| `force_reindex` | boolean | No | `false` | Force full re-index even if already indexed |

**Parameter Details**:

**`repo_path`** (string, required)
- Must be absolute path, not relative
- Directory must exist and be readable
- Supports git repositories (respects .gitignore) and plain directories
- Example: `/Users/alice/projects/myapp`

**`project_id`** (string, optional)
- Identifies project for database isolation
- Sanitized for PostgreSQL database name: lowercase, non-alphanumeric → underscore
- Max length: 54 characters (PostgreSQL limit - `codebase_` prefix)
- Example: `"frontend-ui"` → database `codebase_frontend_ui`
- If omitted: Uses "default" project (database `codebase_default`)
- If `WORKFLOW_MCP_URL` set and `project_id` omitted: Automatically resolved via `get_active_project()`

**`force_reindex`** (boolean, optional)
- `false` (default): Skip indexing if repository already indexed (checks by repo_path)
- `true`: Delete existing index and re-index from scratch
- Use case: Code changes since last index, corrupted index

### Return Value

```json
{
  "repository_id": "uuid",
  "files_indexed": 1234,
  "chunks_created": 5678,
  "duration_seconds": 45.2,
  "project_id": "frontend-ui",
  "schema_name": "codebase_frontend_ui",
  "status": "success"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `repository_id` | string (UUID) | Unique identifier for indexed repository |
| `files_indexed` | integer | Count of files successfully indexed |
| `chunks_created` | integer | Count of code chunks extracted and embedded |
| `duration_seconds` | float | Time taken for indexing operation |
| `project_id` | string | Project identifier used (resolved or provided) |
| `schema_name` | string | PostgreSQL database name used |
| `status` | string | Operation status: "success", "partial", "failed" |

### Examples

**Basic Usage (Default Project)**:
```json
{
  "repo_path": "/Users/alice/projects/myapp"
}
```

**Multi-Project Usage**:
```json
{
  "repo_path": "/Users/alice/clients/acme-corp/backend",
  "project_id": "acme-backend"
}
```

**Force Re-Index**:
```json
{
  "repo_path": "/Users/alice/projects/myapp",
  "force_reindex": true
}
```

### Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `ValueError: repo_path must be absolute` | Relative path provided | Provide absolute path starting with `/` |
| `ValueError: Directory does not exist` | Invalid repo_path | Verify directory exists and is readable |
| `RuntimeError: Database connection failed` | PostgreSQL unreachable | Check `DATABASE_URL` configuration |
| `RuntimeError: Ollama API unavailable` | Ollama not running | Start Ollama server, verify `OLLAMA_BASE_URL` |

---

## search_code

Searches indexed code repositories using natural language queries with semantic similarity matching.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Natural language search query |
| `project_id` | string | No | `"default"` | Project identifier for multi-project isolation |
| `repository_id` | string (UUID) | No | - | Filter by specific repository |
| `file_type` | string | No | - | Filter by file extension (e.g., "py", "js") |
| `directory` | string | No | - | Filter by directory path (supports wildcards) |
| `limit` | integer | No | `10` | Maximum results to return (1-50) |

**Parameter Details**:

**`query`** (string, required)
- Natural language description of code to find
- Examples: "authentication middleware", "database connection pooling", "error handling in API routes"
- Minimum length: 2 characters

**`project_id`** (string, optional)
- Same behavior as `index_repository`: defaults to "default", auto-resolved if workflow-mcp configured

**`repository_id`** (string, optional)
- UUID returned from `index_repository`
- Filters results to single repository
- Useful when multiple repositories indexed in same project

**`file_type`** (string, optional)
- File extension without dot: "py", "js", "go", "rs"
- Case-insensitive
- Filters results to matching file types

**`directory`** (string, optional)
- Relative path within repository: "src/api", "tests"
- Supports wildcards: "src/*/handlers"
- Case-sensitive

**`limit`** (integer, optional)
- Range: 1-50
- Default: 10
- Returns top-k results by similarity score

### Return Value

```json
{
  "results": [
    {
      "chunk_id": "uuid",
      "file_path": "src/api/auth.py",
      "content": "def authenticate_user(username, password):\n    ...",
      "start_line": 15,
      "end_line": 25,
      "similarity_score": 0.92,
      "context_before": "# Authentication module\n",
      "context_after": "\n# Password hashing utilities"
    }
  ],
  "total_count": 42,
  "project_id": "acme-backend",
  "schema_name": "codebase_acme_backend",
  "latency_ms": 250
}
```

| Field | Type | Description |
|-------|------|-------------|
| `results` | array | List of matching code chunks (see Result Object below) |
| `total_count` | integer | Total matches before limit applied |
| `project_id` | string | Project identifier used |
| `schema_name` | string | PostgreSQL database queried |
| `latency_ms` | float | Query execution time (milliseconds) |

**Result Object**:

| Field | Type | Description |
|-------|------|-------------|
| `chunk_id` | string (UUID) | Unique identifier for code chunk |
| `file_path` | string | Relative path to file within repository |
| `content` | string | Code chunk content |
| `start_line` | integer | Starting line number in file |
| `end_line` | integer | Ending line number in file |
| `similarity_score` | float | Cosine similarity score (0.0-1.0, higher is better) |
| `context_before` | string | Lines before chunk (for context) |
| `context_after` | string | Lines after chunk (for context) |

### Examples

**Basic Search**:
```json
{
  "query": "database connection pooling"
}
```

**Multi-Project Search**:
```json
{
  "query": "authentication middleware",
  "project_id": "acme-backend"
}
```

**Filtered Search**:
```json
{
  "query": "error handling",
  "file_type": "py",
  "directory": "src/api",
  "limit": 20
}
```

### Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `ValueError: query too short` | Query <2 characters | Provide longer query |
| `ValueError: limit out of range` | Limit <1 or >50 | Use limit between 1-50 |
| `ValueError: project not found` | project_id has no database | Index repository first |
| `RuntimeError: Ollama API unavailable` | Ollama not running | Start Ollama server |

---

## Removed Tools (v2.0)

The following **14 tools** were removed in v2.0 as part of the architecture refactoring to focus exclusively on semantic code search. Users needing project management functionality should use the separate [workflow-mcp server](https://github.com/workflow-mcp/workflow-mcp).

### Removed Project Management Tools

- ❌ **`create_project`** - Removed in v2.0. Use workflow-mcp for project management.
- ❌ **`switch_project`** - Removed in v2.0. Use `project_id` parameter instead.
- ❌ **`get_active_project`** - Removed in v2.0. Use workflow-mcp integration or explicit `project_id`.
- ❌ **`list_projects`** - Removed in v2.0. Use workflow-mcp for project management.

### Removed Entity Management Tools

- ❌ **`register_entity_type`** - Removed in v2.0. Use workflow-mcp for entity management.
- ❌ **`create_entity`** - Removed in v2.0. Use workflow-mcp for entity management.
- ❌ **`query_entities`** - Removed in v2.0. Use workflow-mcp for entity management.
- ❌ **`update_entity`** - Removed in v2.0. Use workflow-mcp for entity management.
- ❌ **`delete_entity`** - Removed in v2.0. Use workflow-mcp for entity management.
- ❌ **`update_entity_type_schema`** - Removed in v2.0. Use workflow-mcp for entity management.

### Removed Work Item Management Tools

- ❌ **`create_work_item`** - Removed in v2.0. Use workflow-mcp for work item management.
- ❌ **`update_work_item`** - Removed in v2.0. Use workflow-mcp for work item management.
- ❌ **`query_work_items`** - Removed in v2.0. Use workflow-mcp for work item management.
- ❌ **`get_work_item_hierarchy`** - Removed in v2.0. Use workflow-mcp for work item management.

**Migration Path**: See [v1-to-v2 Migration Guide](../migration/v1-to-v2-migration.md) for upgrade instructions.

---

## Tool Discovery

MCP clients discover tools via SSE (Server-Sent Events) `tools/list` request. codebase-mcp v2.0 returns:

```json
{
  "tools": [
    {
      "name": "index_repository",
      "description": "Index a code repository for semantic search",
      "inputSchema": { ... }
    },
    {
      "name": "search_code",
      "description": "Search indexed code using natural language",
      "inputSchema": { ... }
    }
  ]
}
```

**JSON Schema Validation**: MCP clients validate parameters against `inputSchema` before tool invocation. See [MCP Protocol Specification](https://github.com/modelcontextprotocol/specification) for details.
```

### Rationale

This structure addresses multiple personas:

1. **OpenAPI-Inspired Structure**: Familiar format for developers accustomed to REST API documentation. Clear sections (Parameters, Return Value, Examples, Errors) provide complete reference.

2. **Explicit Deprecation Notices (FR-007, FR-008)**: Removed tools section prominently displays 14 removed tools by name with v2.0 notation. Includes migration path link. Addresses "v1.x user looks for removed tool" edge case.

3. **Parameter Documentation**: Table format for scannable reference. Detailed subsections explain behavior, validation, examples. Addresses `project_id` parameter default behavior (FR-005, FR-006).

4. **Return Value Documentation**: JSON schema + table description. Shows actual response structure, not prose description.

5. **Error Handling**: Table of common errors with causes and resolutions. Enables users to troubleshoot independently.

6. **Examples**: Multiple examples per tool showing common use cases. Addresses "new user completes first indexing/search" (User Story 2).

### Alternatives Considered

- **Alternative 1: Pure OpenAPI YAML** - Rejected because OpenAPI is REST-focused, not MCP-focused. MCP uses JSON-RPC over SSE, not HTTP. OpenAPI structure inspires documentation but full spec doesn't apply.
- **Alternative 2: Swagger UI Generation** - Rejected because it requires build tooling and doesn't match MCP protocol. Manual Markdown is more appropriate for Phase 05 documentation-only scope.
- **Alternative 3: JSDoc/Pydantic Schema Generation** - Rejected because Phase 05 is documentation-only (no code changes). Auto-generation deferred to Phase 07.
- **Alternative 4: Separate Page Per Tool** - Rejected because 2 tools don't justify multi-page structure. Single page with anchor links provides better UX for small API surface.

### Implementation Guidance

**For this project, apply these specific patterns**:

1. **Tool Documentation Structure**:
   - Lead with overview (brief description)
   - Parameters section: table + detailed subsections
   - Return value section: JSON example + table description
   - Examples section: 3-5 common use cases
   - Error handling section: table of errors

2. **Parameter Tables**:
   - Columns: Parameter, Type, Required, Default, Description
   - Follow with detailed subsections for complex parameters
   - Show validation rules explicitly
   - Link to related configuration (e.g., workflow-mcp integration)

3. **Return Value Documentation**:
   - Show actual JSON structure (copy from implementation)
   - Table describing each field
   - Explain field semantics (not just types)

4. **Examples**:
   - Use JSON format (MCP tool parameters are JSON)
   - Progress from simple to complex
   - Cover multi-project usage
   - Show filters and advanced parameters

5. **Removed Tools Section**:
   - List all 14 tools by name (FR-010)
   - Use ❌ symbol for visual indicator
   - Group by category (Project, Entity, Work Item)
   - Link to migration guide
   - Link to workflow-mcp as alternative

---

## 6. Documentation Validation

### Decision

Use **Manual Validation Checklist + Documented Procedures** pattern:

```markdown
# Documentation Validation Procedures

> Manual validation procedures for ensuring documentation accuracy, completeness, and correctness before publication.

## Validation Overview

This document defines manual validation procedures for Phase 05 documentation artifacts. Automated validation (link checking, example testing) is deferred to Phase 07 CI integration per FR-032/FR-033.

## Validation Checklist

Complete before PR submission:

### Completeness Validation
- [ ] All 38 functional requirements addressed in documentation
- [ ] All 5 user personas served (README, migration, config, architecture, API reference)
- [ ] All 11 edge cases addressed in relevant docs
- [ ] All 14 removed tools documented by name
- [ ] All environment variables documented with defaults
- [ ] All constitutional principles reflected accurately

### Accuracy Validation
- [ ] Tool count is 2 (index_repository, search_code) - no other tools mentioned
- [ ] Multi-project support explained with project_id parameter
- [ ] workflow-mcp integration marked optional with standalone usage documented first
- [ ] Database-per-project naming convention examples correct
- [ ] Connection pool calculation formula correct
- [ ] PostgreSQL version requirements accurate (14+)
- [ ] Python version requirements accurate (3.11+)

### Link Validation (FR-032)
- [ ] All internal links tested (relative paths resolve)
- [ ] All external links tested (URLs return 200)
- [ ] All anchor links tested (heading anchors exist)
- [ ] Link inventory spreadsheet complete

### Code Example Validation (FR-033)
- [ ] All bash commands tested and execute successfully
- [ ] All SQL queries tested against actual database
- [ ] All JSON examples validate against schemas
- [ ] All configuration examples tested in staging environment

### Terminology Consistency (FR-034)
- [ ] Glossary terms used consistently across all docs
- [ ] Technical terms match implementation (codebase, not codebase-mcp)
- [ ] Capitalization consistent (PostgreSQL, not Postgres)
- [ ] Abbreviations defined on first use

### Formatting Consistency (FR-035)
- [ ] Markdown style guide followed
- [ ] Code blocks have language specifiers
- [ ] Tables formatted consistently
- [ ] Heading hierarchy correct (no skipped levels)
- [ ] File names follow convention (lowercase-with-hyphens.md)

## Link Validation Procedure

### Tools Required
- Web browser
- Text editor
- Spreadsheet for link inventory

### Procedure

1. **Extract All Links**:
   ```bash
   # Find all markdown links in docs/
   grep -r '\[.*\](.*)' docs/ README.md | grep -v '.pyc' > links.txt
   ```

2. **Create Link Inventory**:
   - Spreadsheet columns: Source File, Link Text, URL/Path, Status, Notes
   - Categorize: Internal (relative), External (absolute), Anchor (fragment)

3. **Test Internal Links**:
   - For each relative path link:
     - Verify target file exists at path
     - If anchor: verify heading exists in target
     - Record status: ✅ Pass / ❌ Fail

4. **Test External Links**:
   - For each absolute URL:
     - Visit URL in browser
     - Verify returns 200 (not 404, 403, etc.)
     - Record status and note if redirect occurred

5. **Test Anchor Links**:
   - For each fragment identifier (#heading):
     - Verify heading exists in same document
     - Verify anchor matches GitHub slug format (lowercase, hyphens)
     - Record status

6. **Document Failures**:
   - Create GitHub issue for each broken link
   - Fix before PR submission
   - Re-test after fix

### Expected Outcome
- 0 broken links (SC-003)
- Link inventory spreadsheet complete
- All links marked ✅ Pass

## Code Example Validation Procedure

### Tools Required
- v2.0 codebase-mcp installation
- PostgreSQL 14+
- Test repository for indexing
- Staging environment (for production config examples)

### Procedure

1. **Identify All Code Examples**:
   - Bash commands (` ```bash `)
   - SQL queries (` ```sql `)
   - JSON examples (` ```json `)
   - Configuration files (` ```ini `, ` ```yaml `)

2. **Test Bash Commands**:
   - Copy command from documentation
   - Execute in terminal
   - Verify exit code 0 (success)
   - Verify expected output matches documentation
   - Record: Command, Expected Output, Actual Output, Status

3. **Test SQL Queries**:
   - Copy query from documentation
   - Execute against test database: `psql $DATABASE_URL -c "QUERY"`
   - Verify result matches documentation
   - Record: Query, Expected Result, Actual Result, Status

4. **Test JSON Examples**:
   - Copy JSON from documentation
   - Validate syntax: `echo 'JSON' | jq .`
   - Verify against schema (if applicable)
   - Test with actual MCP client (if tool invocation example)
   - Record: Example, Validation Result, Status

5. **Test Configuration Examples**:
   - Copy configuration to staging environment
   - Apply configuration (environment variables, postgresql.conf)
   - Verify system behavior matches documentation
   - Record: Config, Expected Behavior, Actual Behavior, Status

6. **Document Failures**:
   - Create GitHub issue for each failed example
   - Fix documentation or note caveats
   - Re-test after fix

### Expected Outcome
- 100% of code examples execute successfully (SC-004)
- Code example test log complete
- All examples marked ✅ Pass

## Migration Guide Validation Procedure

### Tools Required
- v1.x codebase-mcp installation
- v2.0 codebase-mcp installation
- Test PostgreSQL database
- Backup storage

### Procedure

1. **Setup Test Environment**:
   - Install v1.x in isolated environment
   - Create test data (indexed repositories)
   - Document baseline state

2. **Test Backup Procedures**:
   - Follow backup procedures from migration guide exactly
   - Verify backup files created
   - Verify backup files restorable
   - Record: Backup Step, Command, Result

3. **Test Upgrade Procedure**:
   - Follow upgrade procedure from migration guide step-by-step
   - Execute each command exactly as documented
   - Verify expected output at each step
   - Record: Upgrade Step, Expected Output, Actual Output

4. **Test Validation Commands**:
   - Run all validation commands from guide
   - Verify v2.0 functionality works
   - Record: Validation Command, Expected Result, Actual Result

5. **Test Rollback Procedure**:
   - Follow rollback procedure from migration guide step-by-step
   - Restore backups
   - Verify v1.x functionality restored
   - Record: Rollback Step, Expected Output, Actual Output

6. **Test Diagnostic Commands**:
   - Simulate partial migration failure
   - Run diagnostic commands (FR-036)
   - Verify commands detect state correctly
   - Record: Diagnostic Command, Scenario, Result

7. **Document Issues**:
   - Note any steps that fail or produce unexpected output
   - Update migration guide with corrections
   - Re-test full procedure after updates

### Expected Outcome
- Upgrade procedure completes successfully
- Rollback procedure restores v1.x functionality
- Diagnostic commands detect migration state
- Migration guide validated end-to-end

## Configuration Guide Validation Procedure

### Tools Required
- Staging environment (not production)
- PostgreSQL 14+
- Monitoring tools (psql, connection count queries)

### Procedure

1. **Test Environment Variable Examples**:
   - Copy each example value from table
   - Set environment variable
   - Verify application accepts value
   - Record: Variable, Example Value, Status

2. **Test Connection Calculation Examples**:
   - Copy calculation formula
   - Plug in example scenario values
   - Verify calculation result matches table
   - Record: Scenario, Formula, Calculated Result, Table Result

3. **Test PostgreSQL Tuning Examples**:
   - Apply postgresql.conf settings to staging database
   - Restart PostgreSQL
   - Verify settings applied: `SHOW setting_name;`
   - Record: Setting, Documented Value, Actual Value

4. **Test Validation Checklist**:
   - Follow validation checklist commands
   - Verify each command produces expected result
   - Record: Checklist Item, Command, Expected Result, Actual Result

5. **Test Monitoring Queries**:
   - Run connection pool monitoring SQL queries
   - Verify queries execute and return sensible data
   - Record: Query, Expected Columns, Actual Result

6. **Document Issues**:
   - Note any configuration that doesn't work as documented
   - Update configuration guide with corrections
   - Re-test after updates

### Expected Outcome
- All environment variable examples valid
- All calculations correct
- All PostgreSQL settings apply successfully
- Validation checklist commands work

## Review Checklist

Final review before PR submission:

### Content Review
- [ ] All validation procedures completed
- [ ] All failures documented and fixed
- [ ] Cross-reference consistency (no conflicting information)
- [ ] Tone consistent (technical but approachable)
- [ ] No placeholder text (`TODO`, `[FILL IN]`, etc.)

### Persona Coverage
- [ ] New user can complete first installation and search (User Story 2)
- [ ] Existing user can upgrade safely (User Story 1)
- [ ] Administrator can configure production (User Story 3)
- [ ] Developer can integrate workflow-mcp (User Story 4)
- [ ] Maintainer understands architecture (User Story 5)

### Quality Metrics
- [ ] 0 broken links (SC-003)
- [ ] 100% code examples tested (SC-004)
- [ ] 100% functional requirements addressed
- [ ] 100% removed tools documented (SC-002)

### Approval
- [ ] Author validation complete
- [ ] Peer review completed (separate reviewer)
- [ ] Reviewer confirms link validation
- [ ] Reviewer confirms code example validation
```

### Rationale

This approach addresses Phase 05 scope constraints:

1. **Manual Validation (FR-032, FR-033)**: Appropriate for documentation-only phase. Automated testing deferred to Phase 07 CI integration per explicit scope boundary. Manual validation ensures accuracy without introducing new tooling dependencies.

2. **Documented Procedures**: Checklists and step-by-step procedures enable consistent validation across contributors. Reduces subjectivity in "documentation quality" assessment.

3. **Spreadsheet-Based Tracking**: Simple tool (Excel/Google Sheets) for link inventory and test logs. No custom tooling required. Enables progress tracking and issue identification.

4. **Staging Environment Testing**: Configuration and migration guides tested in non-production environment. Prevents documentation errors from impacting production systems.

5. **Peer Review Requirement**: Separate reviewer confirms validation completed. Catches author blind spots and ensures compliance with checklist.

### Alternatives Considered

- **Alternative 1: Automated Link Checking (markdownlint, linkchecker)** - Rejected for Phase 05 because automation requires CI integration. Explicitly scoped to Phase 07. Manual validation sufficient for initial publication.
- **Alternative 2: Automated Example Testing (doctest-style)** - Rejected for Phase 05 because it requires code annotations and test runner. Deferred to Phase 07 along with other automation.
- **Alternative 3: Documentation Linter (Vale, write-good)** - Rejected because it requires tooling installation and configuration. Style consistency achieved through markdown style guide and manual review.
- **Alternative 4: Third-Party Review Service** - Rejected because it introduces external dependency and cost. Peer review within team is sufficient for technical documentation.

### Implementation Guidance

**For this project, apply these specific patterns**:

1. **Link Inventory Spreadsheet Structure**:
   - Columns: Source File, Link Text, URL/Path, Type (Internal/External/Anchor), Status, Tested By, Tested Date, Notes
   - Sort by source file for easier cross-referencing
   - Filter by status to identify failures quickly

2. **Code Example Test Log Structure**:
   - Columns: Doc File, Example Type (Bash/SQL/JSON/Config), Example Description, Command/Code, Expected Result, Actual Result, Status, Tested By, Tested Date
   - One row per example
   - Include screenshots for complex examples if helpful

3. **Validation Checklist Usage**:
   - Copy checklist to PR description
   - Check boxes as completed
   - Link to evidence (link inventory spreadsheet, test log)
   - Reviewer re-verifies critical items

4. **Migration Guide Testing**:
   - Use disposable VM or Docker container for test environment
   - Document exact steps taken (enables reproducibility)
   - Take database dumps at checkpoints (enables rollback testing)
   - Include timing information (informs duration guidance in future)

5. **Configuration Guide Testing**:
   - Use staging database separate from test/dev databases
   - Test both minimal and maximal configurations
   - Verify monitoring queries with actual data
   - Document any platform-specific issues (Linux vs macOS vs Docker)

6. **Review Process**:
   - Author completes validation, creates PR
   - Reviewer spot-checks 20% of links and examples
   - Reviewer runs migration guide in their own environment
   - Both author and reviewer sign off on checklist

---

## Key Takeaways

1. **GitHub-Flavored Markdown with Hierarchical Navigation**: Use GFM for universal compatibility. Structure docs with H1 title, H2 sections, TOC for long docs. Cross-reference with relative paths. Enables version control, accessibility, and no-build-tooling simplicity.

2. **Breaking Changes First + Step-by-Step + Rollback Pattern**: Migration guides must communicate risk upfront before procedures. Sequential steps with validation at each checkpoint. Complete rollback procedure provides safety net for production upgrades.

3. **Environment Variable Tables + Calculation Examples**: Configuration docs need scannable reference format (tables) with concrete examples. PostgreSQL connection calculation formula + scenarios prevent misconfiguration. Validation checklist enables pre-deployment verification.

4. **Mermaid Diagrams + Component Prose + Code Examples**: Architecture docs balance visual (Mermaid) and textual (prose) explanation. Text-based diagrams enable version control. Database naming examples with sanitization rules address implementation details critical for debugging.

5. **OpenAPI-Inspired Structure + Explicit Deprecation Notices**: API reference uses familiar structure (Parameters, Return Value, Examples, Errors) from REST API documentation. Removed tools section prominently lists 14 tools by name with migration path link.

6. **Manual Validation Checklist + Documented Procedures**: Phase 05 scope uses manual validation (link checking, example testing) with structured procedures. Automation deferred to Phase 07. Spreadsheet-based tracking and peer review ensure quality without new tooling dependencies.

7. **Multi-Persona Documentation Strategy**: 5 artifacts serve 5 distinct personas: README (new users), Migration Guide (upgrading users), Configuration Guide (administrators), Architecture Docs (maintainers), API Reference (developers). Each artifact has persona-specific content focus and technical depth.

8. **Production Quality Through Validation**: Manual validation procedures (link checking, example testing, migration testing, configuration testing) ensure documentation accuracy before publication. Validation checklists in PR process enforce quality standards.

9. **Progressive Disclosure Pattern**: Documentation structure moves from high-level (overview, quick start) to detailed (specific sections, troubleshooting). TOC and cross-references enable readers to drill down to relevant details without overwhelming initial presentation.

10. **Concrete Examples Over Abstract Descriptions**: Every concept illustrated with concrete example: database naming rules → example table; connection calculations → scenario table; migration procedure → exact commands with expected output. Reduces ambiguity and enables direct application.
