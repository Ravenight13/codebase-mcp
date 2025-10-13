# Glossary

This glossary defines canonical terminology used throughout the codebase-mcp documentation. These terms follow consistent capitalization, hyphenation, and formatting rules to ensure clarity and reduce ambiguity across API documentation, user guides, and technical specifications.

**Purpose**: Establish standard vocabulary for multi-project workspace architecture, database isolation patterns, and system integration concepts.

**Audience**: Developers, technical writers, and users working with the codebase-mcp server.

---

## Terms

### project_id

A unique identifier that isolates workspace data across tenants in the multi-project architecture. Each workspace is assigned a project ID that determines which isolated database handles operations, enabling multiple independent projects to coexist within a single codebase-mcp server instance.

**Usage**:
- In code contexts (parameters, database columns), use `project_id` with code font and snake_case formatting
- In prose, use "project ID" (two words, no code font) when discussing the concept
- Never capitalize "ID" to "Id" or use camelCase variants

**Examples**:
- "Each workspace is identified by a unique project ID that isolates data across tenants."
- "Pass the `project_id` parameter to `switch_project()` to change the active workspace."
- "The projects table uses `project_id` as the primary key for workspace isolation."

**Related Terms**: [default project](#default-project), [database-per-project](#database-per-project), [workflow-mcp integration](#workflow-mcp-integration)

---

### connection pool

A pool of reusable database connections maintained by the server to optimize performance and resource utilization. The codebase-mcp server maintains separate connection pools for the registry database and each active project database, with configurable size limits and automatic lifecycle management.

**Usage**:
- Always write as two separate words without hyphenation
- Lowercase in prose unless at sentence start
- Can abbreviate to "pool" after first reference in the same paragraph

**Examples**:
- "The server maintains separate connection pools for the registry and each active project database."
- "Connection pool statistics include size, min_size, max_size, and free connections."
- "Monitor pool health through the `health_check` tool's connection pool metrics."

**Related Terms**: [LRU eviction](#lru-eviction), [database-per-project](#database-per-project)

---

### LRU eviction

LRU (Least Recently Used) eviction is a cache management policy that removes the least recently accessed entries when the cache reaches capacity. The codebase-mcp server uses LRU eviction to manage project database connection pools, ensuring frequently accessed projects remain cached while inactive projects are evicted to free resources.

**Usage**:
- Always capitalize "LRU" as an acronym
- Expand to "Least Recently Used" on first mention in each major document section
- Keep "eviction" lowercase unless at sentence start
- No hyphen between "LRU" and "eviction"

**Examples**:
- "The cache implements LRU (Least Recently Used) eviction to manage memory efficiently."
- "When the cache reaches capacity, LRU eviction removes the least recently accessed entries."
- "Configure LRU eviction thresholds through the `MAX_CACHED_PROJECTS` environment variable."

**Related Terms**: [connection pool](#connection-pool), [project_id](#project_id)

---

### database-per-project

An architectural pattern where each project workspace receives its own isolated PostgreSQL database for complete data separation and tenant isolation. This approach provides security, performance, and operational independence by preventing cross-tenant data leakage and enabling per-project backup, migration, and schema customization.

**Usage**:
- Hyphenate when used as a compound adjective before a noun (e.g., "database-per-project architecture")
- Use separate words without hyphens in descriptive prose (e.g., "each project gets a database per project")
- Always lowercase unless at sentence start
- Singular "database" (not "databases-per-project")

**Examples**:
- "The system uses a database-per-project architecture for workspace isolation."
- "Each project workspace receives its own database per project for data separation."
- "The database-per-project pattern ensures tenant isolation at the PostgreSQL level."

**Related Terms**: [project_id](#project_id), [connection pool](#connection-pool), [default project](#default-project)

---

### workflow-mcp integration

Integration with the workflow-mcp server that provides automatic project context resolution and workspace management. When both servers are configured together, codebase-mcp can automatically resolve the active `project_id` from workflow-mcp, enabling seamless multi-project operations without manual context switching.

**Usage**:
- Always lowercase "workflow-mcp" (follows product naming convention)
- Hyphenate "workflow-mcp" (matches official package name)
- Use code font when referring to the server/package implementation
- Keep "integration" lowercase unless at sentence start

**Examples**:
- "The codebase-mcp server supports workflow-mcp integration for project context resolution."
- "Install the `workflow-mcp` server to enable multi-project workspace management."
- "The workflow-mcp integration provides automatic `project_id` resolution for operations."

**Related Terms**: [project_id](#project_id), [default project](#default-project)

---

### default project

The fallback workspace used when operations do not specify a `project_id`. The default project uses the `codebase_default` database and is automatically created during server initialization. All operations without explicit project context are routed to this workspace.

**Usage**:
- Always write as two separate words without hyphenation
- Lowercase in prose unless at sentence start
- Use code font only when referring to the actual database name (`codebase_default`)
- Distinguish between the conceptual "default project" and the database implementation

**Examples**:
- "Operations without a `project_id` use the default project workspace (`codebase_default` database)."
- "The server creates a default project automatically during initialization."
- "Set `DEFAULT_PROJECT_NAME` to customize the default project database name."

**Related Terms**: [project_id](#project_id), [database-per-project](#database-per-project), [workflow-mcp integration](#workflow-mcp-integration)

---

## Usage Guidelines

### Code vs. Prose Contexts

**Code contexts** (use code font with backticks):
- Parameter names: `project_id`, `pool_size`
- Database names: `codebase_default`, `codebase_my_app`
- Function names: `switch_project()`, `get_active_project()`
- Environment variables: `DEFAULT_PROJECT_NAME`, `MAX_CACHED_PROJECTS`

**Prose contexts** (no code font):
- Concepts: "project ID", "connection pool", "default project"
- Architecture patterns: "database-per-project architecture"
- Descriptive phrases: "LRU eviction policy"

### Capitalization Rules

- Capitalize only at sentence start: "Project ID uniquely identifies each workspace."
- Keep acronyms uppercase: "LRU eviction", not "lru eviction"
- Lowercase product names: "workflow-mcp integration", not "Workflow-MCP Integration"

---

## Validation

This glossary was created following the terminology standards in `specs/010-v2-documentation/glossary-guidance.md`. All terms use canonical forms with consistent:
- Hyphenation (database-per-project, workflow-mcp)
- Capitalization (LRU, project ID)
- Code font application (parameters vs. concepts)
- Cross-references to related terms

For questions or suggested additions, refer to the glossary guidance document or open an issue.
