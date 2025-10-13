# Glossary Guidance Document

**Purpose**: This document defines canonical terminology forms for the glossary.md file (T002). It resolves capitalization, hyphenation, and formatting inconsistencies identified in the analysis report.

**Target Audience**: Technical writers creating glossary.md

---

## Terminology Standards

### 1. project_id

**Canonical Forms**:
- **Code contexts**: `project_id` (snake_case with code font)
- **Prose contexts**: "project ID" (two words, no code font)
- **Parameter names**: `project_id` (in API documentation, always code font)
- **Database columns**: `project_id` (lowercase snake_case)

**Usage Rules**:
- Use code font when referring to variable names, parameters, or database columns
- Use plain text "project ID" when discussing the concept in prose
- Never capitalize "ID" to "Id" in any context
- Lowercase in examples unless at sentence start

**Correct Examples**:
1. "Each workspace is identified by a unique project ID that isolates data across tenants."
2. "Pass the `project_id` parameter to switch_project() to change the active workspace."
3. "The projects table uses `project_id` as the primary key for workspace isolation."

**Common Errors to Avoid**:
- ❌ `Project-ID` (hyphenated with capitals)
- ❌ `projectId` (camelCase)
- ❌ `project_ID` (mixed case snake_case)
- ❌ `ProjectID` (PascalCase)
- ❌ "Project Id" (capitalizing "Id")

---

### 2. connection pool

**Canonical Forms**:
- **All contexts**: "connection pool" (two words, lowercase, no hyphen)
- **As adjective**: "connection pool" (no hyphen, e.g., "connection pool statistics")
- **Plural**: "connection pools"

**Usage Rules**:
- Always two separate words, never hyphenated
- Lowercase unless at sentence start
- Use "pool" alone only after first reference in same paragraph

**Correct Examples**:
1. "The server maintains separate connection pools for the registry and each active project database."
2. "Connection pool statistics include size, min_size, max_size, and free connections."
3. "Monitor pool health through the health_check tool's connection pool metrics."

**Common Errors to Avoid**:
- ❌ "connection-pool" (hyphenated)
- ❌ "Connection Pool" (unnecessary capitals in prose)
- ❌ "connectionpool" (single word)
- ❌ "conn pool" (abbreviation in formal documentation)

---

### 3. LRU eviction

**Canonical Forms**:
- **First mention**: "LRU (Least Recently Used) eviction"
- **Subsequent mentions**: "LRU eviction"
- **Prose references**: "LRU eviction policy"

**Usage Rules**:
- Always capitalize "LRU" (acronym)
- Always lowercase "eviction" unless at sentence start
- Expand acronym on first use in each major document section
- No hyphen between "LRU" and "eviction"

**Correct Examples**:
1. "The cache implements LRU (Least Recently Used) eviction to manage memory efficiently."
2. "When the cache reaches capacity, LRU eviction removes the least recently accessed entries."
3. "Configure LRU eviction thresholds through the MAX_CACHED_PROJECTS environment variable."

**Common Errors to Avoid**:
- ❌ "lru eviction" (lowercase acronym)
- ❌ "LRU Eviction" (unnecessary capital on "Eviction")
- ❌ "LRU-eviction" (hyphenated)
- ❌ "Lru eviction" (mixed case acronym)

---

### 4. database-per-project

**Canonical Forms**:
- **As compound adjective**: "database-per-project" (hyphenated)
- **In prose description**: "database per project" (no hyphens, separate words)
- **As noun phrase**: "database-per-project architecture"

**Usage Rules**:
- Hyphenate when used as compound adjective before a noun
- No hyphens when used descriptively in prose
- Always lowercase unless at sentence start
- Singular "database" (not "databases-per-project")

**Correct Examples**:
1. "The system uses a database-per-project architecture for workspace isolation."
2. "Each project workspace receives its own database per project for data separation."
3. "The database-per-project pattern ensures tenant isolation at the PostgreSQL level."

**Common Errors to Avoid**:
- ❌ "database per project architecture" (missing hyphens as compound adjective)
- ❌ "Database-Per-Project" (unnecessary capitals)
- ❌ "databases-per-project" (incorrect plural)
- ❌ "db-per-project" (abbreviation in formal documentation)

---

### 5. workflow-mcp integration

**Canonical Forms**:
- **Product name**: "workflow-mcp" (lowercase, hyphenated)
- **Full reference**: "workflow-mcp integration"
- **As code reference**: `workflow-mcp` (code font when referring to package/tool)

**Usage Rules**:
- Always lowercase "workflow-mcp" (product name convention)
- Hyphenate "workflow-mcp" (matches official naming)
- Lowercase "integration" unless at sentence start
- Use code font when referring to the actual server/package

**Correct Examples**:
1. "The codebase-mcp server supports workflow-mcp integration for project context resolution."
2. "Install the `workflow-mcp` server to enable multi-project workspace management."
3. "The workflow-mcp integration provides automatic project_id resolution for operations."

**Common Errors to Avoid**:
- ❌ "Workflow-MCP" (unnecessary capitals)
- ❌ "workflow_mcp" (underscore instead of hyphen)
- ❌ "WorkflowMCP" (PascalCase)
- ❌ "workflow mcp" (missing hyphen)

---

### 6. default project

**Canonical Forms**:
- **All contexts**: "default project" (two words, lowercase)
- **Database name**: `codebase_default` (code font, snake_case)
- **As adjective**: "default project workspace"

**Usage Rules**:
- Always two separate words, no hyphen
- Lowercase unless at sentence start
- Use code font only when referring to actual database name
- Distinguish between conceptual "default project" and database "codebase_default"

**Correct Examples**:
1. "Operations without a project_id use the default project workspace (codebase_default database)."
2. "The server creates a default project automatically during initialization."
3. "Set DEFAULT_PROJECT_NAME to customize the default project database name."

**Common Errors to Avoid**:
- ❌ "Default Project" (unnecessary capitals in prose)
- ❌ "default-project" (hyphenated)
- ❌ "defaultProject" (camelCase)
- ❌ Using "default project" when specifically referring to `codebase_default` database

---

## Cross-Reference Rules

### Code vs. Prose Context

**Code Context** (use code font):
- Parameter names: `project_id`, `pool_size`
- Database names: `codebase_default`, `codebase_my_app`
- Function names: `switch_project()`, `get_active_project()`
- Environment variables: `DEFAULT_PROJECT_NAME`, `MAX_CACHED_PROJECTS`

**Prose Context** (no code font):
- Concepts: "project ID", "connection pool", "default project"
- Architecture patterns: "database-per-project architecture"
- Descriptive phrases: "LRU eviction policy"

### Capitalization at Sentence Start

When terms appear at sentence start, capitalize only the first letter:
- ✅ "Project ID uniquely identifies each workspace."
- ✅ "Connection pools are monitored via health_check."
- ✅ "Database-per-project isolation prevents data leakage."

---

## Glossary Entry Template

Each glossary term should follow this structure:

```markdown
### [Term in Canonical Form]

[1-2 sentence definition]

**Usage**: [Context-specific guidance]

**Examples**:
- [Example 1 showing correct usage]
- [Example 2 in different context]

**Related Terms**: [Cross-references to other glossary entries]
```

---

## Validation Checklist

Before finalizing glossary.md, verify:

- [ ] All 6 terms use canonical forms from this document
- [ ] Code font applied only to code contexts (parameters, databases, functions)
- [ ] Prose contexts use plain text (project ID, connection pool, etc.)
- [ ] Capitalization follows sentence-start rules only
- [ ] Hyphenation matches compound adjective rules (database-per-project)
- [ ] Acronyms expanded on first use (LRU = Least Recently Used)
- [ ] Common errors section included for each high-risk term
- [ ] Cross-references use consistent terminology

---

## Document Metadata

- **Created**: 2025-10-13
- **Purpose**: Resolve T1 terminology inconsistencies
- **Related Tasks**: T002 (Create glossary.md)
- **Severity**: MEDIUM (prevents downstream documentation drift)
