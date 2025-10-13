# Quickstart: Documentation Validation & Testing

**Feature**: 010-v2-documentation
**Version**: v2.0
**Date**: 2025-10-13

## Overview

This document provides manual testing procedures for validating documentation artifacts against specification requirements. All validation is performed manually during Phase 05 documentation authoring. Automated validation (link checking, example testing) is deferred to Phase 07 CI integration per FR-032/FR-033.

**Validation Scope**: 5 documentation artifacts (README, Migration Guide, Configuration Guide, Architecture Docs, API Reference) with 38 functional requirements and 11 edge cases.

**Validation Timeline**: Performed during authoring before PR submission. Validation must complete with 100% pass rate before documentation is marked as reviewed.

---

## Test Scenario 1: Link Verification (FR-032)

**Objective**: Verify all documentation links resolve without 404 errors

**Requirement Traceability**: FR-032 (All documentation links MUST resolve without 404 errors)

**Success Criteria**: SC-003 (0 broken links in all documentation files)

### Prerequisites

- All 5 documentation artifacts authored and saved to repository
- Web browser (Chrome, Firefox, Safari)
- Text editor with grep support
- Spreadsheet software (Excel, Google Sheets) for link inventory

### Procedure

#### Step 1: Extract All Links

Execute the following command from repository root to extract all markdown links:

```bash
grep -rh '\[.*\](.*)'  README.md docs/ | grep -v '.pyc' | grep -v '.git' > /tmp/codebase-mcp-links.txt
```

**Expected Output**: File `/tmp/codebase-mcp-links.txt` containing all markdown links from documentation.

#### Step 2: Create Link Inventory Spreadsheet

Create a spreadsheet with the following columns:

| Source File | Link Text | URL/Path | Link Type | Status | Tested By | Tested Date | Notes |
|-------------|-----------|----------|-----------|--------|-----------|-------------|-------|
| README.md | Migration Guide | docs/migration/v1-to-v2-migration.md | Internal | | | | |
| ... | ... | ... | ... | | | | |

**Link Types**:
- **Internal**: Relative path link (e.g., `docs/migration/v1-to-v2-migration.md`)
- **External**: Absolute URL (e.g., `https://github.com/modelcontextprotocol/specification`)
- **Anchor**: Fragment identifier (e.g., `#breaking-changes-summary`)

**Instructions**:
1. Parse `/tmp/codebase-mcp-links.txt` and extract links
2. Populate spreadsheet with one row per link
3. Categorize by Link Type
4. Group by Source File for easier testing

#### Step 3: Test Internal Links

For each Internal link:

1. **Verify File Exists**: Navigate to repository root and check file existence
   ```bash
   ls -l docs/migration/v1-to-v2-migration.md
   ```
   **Expected**: File exists and is readable

2. **If Anchor Present**: Verify heading exists in target file
   ```bash
   grep -i "## breaking changes summary" docs/migration/v1-to-v2-migration.md
   ```
   **Expected**: Heading found with correct capitalization and formatting

3. **Record Status**: Mark ✅ Pass or ❌ Fail in spreadsheet

#### Step 4: Test External Links

For each External link:

1. **Visit URL in Browser**: Open URL and verify page loads
2. **Check HTTP Status**: Verify 200 OK response (not 404, 403, 500)
3. **Check Redirect**: Note if URL redirects to different domain
4. **Record Status**: Mark ✅ Pass or ❌ Fail with notes

**Common External Links to Verify**:
- MCP Protocol Specification: `https://github.com/modelcontextprotocol/specification`
- workflow-mcp Repository: `https://github.com/workflow-mcp/workflow-mcp`
- PostgreSQL Documentation: `https://www.postgresql.org/docs/14/`
- Python Official Site: `https://www.python.org/`

#### Step 5: Test Anchor Links

For each Anchor link (within same document):

1. **Verify Heading Exists**: Search for heading in source file
   ```bash
   grep -i "## configuration overview" docs/configuration/production-config.md
   ```
   **Expected**: Heading found

2. **Verify GitHub Slug Format**: Check anchor matches GitHub auto-generated slug
   - Lowercase
   - Spaces replaced with hyphens
   - Special characters removed
   - Example: `## Configuration Overview` → `#configuration-overview`

3. **Record Status**: Mark ✅ Pass or ❌ Fail

#### Step 6: Document and Fix Failures

For each ❌ Fail:

1. **Create GitHub Issue**: Document broken link with source file, target, error
2. **Fix Link**: Update documentation with correct path/URL
3. **Re-Test**: Verify fix resolves issue
4. **Update Spreadsheet**: Mark as ✅ Pass after fix verified

### Expected Results

- **Link Inventory Complete**: All links extracted and categorized
- **100% Pass Rate**: All links marked ✅ Pass
- **0 Broken Links**: No 404 errors, all files exist, all anchors valid
- **Spreadsheet Deliverable**: Link inventory spreadsheet with test results

### Pass/Fail Criteria

**PASS**: All links resolve successfully (internal files exist, external URLs return 200, anchors match headings)

**FAIL**: Any broken link (404 error, missing file, invalid anchor, redirect to error page)

**Failure Resolution**: Fix broken links and re-test before proceeding to Scenario 2

---

## Test Scenario 2: Code Example Testing (FR-033)

**Objective**: Verify all code examples execute successfully and produce expected output

**Requirement Traceability**: FR-033 (All code examples MUST be tested and functional before publication)

**Success Criteria**: SC-004 (100% of code examples are tested and execute successfully)

### Prerequisites

- v2.0 codebase-mcp installation (for testing v2.0 examples)
- v1.x codebase-mcp installation (for testing migration guide)
- PostgreSQL 14+ running locally or in staging
- Ollama running with `nomic-embed-text` model available
- Test repository for indexing (e.g., small open-source project)
- Staging environment with PostgreSQL (for configuration guide examples)

### Procedure

#### Step 1: Identify All Code Examples

Search documentation for code blocks:

```bash
grep -rn '```' README.md docs/ | grep -v '.pyc' > /tmp/codebase-mcp-examples.txt
```

**Expected Output**: List of all code blocks with line numbers

**Example Types to Identify**:
- Bash commands (` ```bash `)
- SQL queries (` ```sql `)
- JSON examples (` ```json `)
- Configuration files (` ```ini `, ` ```yaml `)
- Python code (` ```python `)

#### Step 2: Create Code Example Test Log

Create a spreadsheet with the following columns:

| Doc File | Example Type | Example Description | Command/Code | Expected Result | Actual Result | Status | Tested By | Tested Date |
|----------|--------------|---------------------|--------------|-----------------|---------------|--------|-----------|-------------|
| README.md | bash | Install codebase-mcp | pip install codebase-mcp | Package installed | | | | |
| ... | ... | ... | ... | ... | ... | ... | ... | ... |

**Instructions**:
1. Extract each code example from documentation
2. Populate spreadsheet with one row per example
3. Include expected result from documentation (if documented)

#### Step 3: Test Bash Commands

For each bash command example:

1. **Copy Command**: Extract exact command from documentation
2. **Execute in Terminal**:
   ```bash
   # Example from README
   pip install codebase-mcp
   ```
3. **Verify Exit Code**: Check command succeeds (exit code 0)
   ```bash
   echo $?
   # Expected: 0
   ```
4. **Verify Output**: Compare actual output to documented expected output
5. **Record Results**: Document actual result and mark ✅ Pass or ❌ Fail

**Special Cases**:
- **Destructive Commands** (e.g., `DROP DATABASE`): Execute in isolated test environment only
- **Placeholder Values** (e.g., `$DATABASE_URL`): Substitute with actual test values
- **Date Formatting** (e.g., `$(date +%Y%m%d_%H%M%S)`): Verify date format correct, not exact value

#### Step 4: Test SQL Queries

For each SQL query example:

1. **Copy Query**: Extract exact SQL from documentation
2. **Execute Against Test Database**:
   ```bash
   psql postgresql://localhost/codebase_test -c "SHOW max_connections;"
   ```
3. **Verify Result**: Check query executes without error and returns expected result type
4. **Record Results**: Document actual result and mark ✅ Pass or ❌ Fail

**Common SQL Examples to Test**:
- Connection monitoring queries (Configuration Guide)
- Diagnostic queries for migration state (Migration Guide)
- Schema validation queries (Migration Guide)

#### Step 5: Test JSON Examples

For each JSON example:

1. **Copy JSON**: Extract JSON from documentation
2. **Validate Syntax**:
   ```bash
   echo '{"repo_path": "/path/to/repo", "project_id": "my-project"}' | jq .
   ```
   **Expected**: JSON pretty-printed, no syntax errors

3. **Test with MCP Client** (if tool invocation example):
   - Use actual MCP client (Claude, Cursor) to invoke tool with example JSON
   - Verify tool accepts parameters and executes

4. **Record Results**: Mark ✅ Pass or ❌ Fail

**Common JSON Examples to Test**:
- Tool invocation examples (API Reference)
- Return value examples (API Reference)
- Configuration examples (Configuration Guide)

#### Step 6: Test Configuration Examples

For each configuration file example:

1. **Copy Configuration**: Extract configuration from documentation (postgresql.conf, .env)
2. **Apply in Staging Environment**:
   ```bash
   # Example: Test PostgreSQL setting
   psql -c "ALTER SYSTEM SET shared_buffers = '4GB';"
   psql -c "SELECT pg_reload_conf();"
   psql -c "SHOW shared_buffers;"
   # Expected: 4GB
   ```

3. **Verify System Behavior**: Confirm system behaves as documented
4. **Record Results**: Mark ✅ Pass or ❌ Fail

**Configuration Examples to Test**:
- Environment variable examples (Configuration Guide)
- PostgreSQL tuning parameters (Configuration Guide)
- Validation checklist commands (Configuration Guide)

#### Step 7: Document and Fix Failures

For each ❌ Fail:

1. **Diagnose Issue**: Determine if documentation error or environment issue
2. **Fix Documentation**: Update example with correct command/syntax
3. **Re-Test**: Verify fix resolves issue
4. **Update Test Log**: Mark as ✅ Pass after fix verified

### Expected Results

- **Code Example Test Log Complete**: All examples extracted and tested
- **100% Pass Rate**: All examples execute successfully
- **Output Matches Documentation**: Actual results match documented expected results
- **Test Log Deliverable**: Code example test log spreadsheet with results

### Pass/Fail Criteria

**PASS**: All code examples execute successfully with expected output (exit code 0, correct result format)

**FAIL**: Any example fails (non-zero exit code, syntax error, incorrect output, tool invocation fails)

**Failure Resolution**: Fix failing examples and re-test before proceeding to Scenario 3

---

## Test Scenario 3: Migration Guide Validation with v1.x (FR-014, FR-015, FR-016, FR-017)

**Objective**: Validate migration guide by executing complete upgrade and rollback procedures with v1.x environment

**Requirement Traceability**:
- FR-014 (Step-by-step upgrade procedure)
- FR-015 (Backup procedures with exact commands)
- FR-016 (Complete rollback procedure)
- FR-017 (Validation steps to confirm upgrade/rollback)

**Success Criteria**: SC-007 (Migration guide provides complete rollback procedure covering all upgrade steps)

### Prerequisites

- v1.x codebase-mcp installation in isolated test environment (VM, Docker container, or separate machine)
- Test PostgreSQL database with v1.x schema
- Test data: At least one indexed repository in v1.x
- v2.0 codebase-mcp package available for upgrade
- Backup storage with sufficient disk space
- **WARNING**: Do NOT use production environment for this test

### Procedure

#### Step 1: Setup Test Environment

1. **Install v1.x codebase-mcp**:
   ```bash
   pip install codebase-mcp==1.x  # Specific v1.x version
   ```

2. **Initialize v1.x Database**: Create database and run v1.x migrations

3. **Create Test Data**: Index a test repository to verify data preservation
   ```bash
   # Use v1.x tool to index repository
   # Verify repository appears in v1.x database
   ```

4. **Document Baseline State**:
   - Database size: `SELECT pg_size_pretty(pg_database_size('codebase_mcp'));`
   - Table count: `SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';`
   - Indexed repositories: Record count and repository names
   - v1.x version: `pip show codebase-mcp | grep Version`

#### Step 2: Test Backup Procedures (FR-015)

Follow backup procedures from Migration Guide exactly:

1. **Database Backup**:
   ```bash
   pg_dump -h localhost -d codebase_mcp > /tmp/backup_$(date +%Y%m%d_%H%M%S).sql
   ```
   **Verification**:
   - Backup file created: `ls -lh /tmp/backup_*.sql`
   - File size reasonable (>0 bytes): `du -h /tmp/backup_*.sql`
   - Backup contains data: `grep -c "COPY" /tmp/backup_*.sql`

2. **Configuration Backup**:
   ```bash
   cp .env .env.backup_$(date +%Y%m%d_%H%M%S)
   ```
   **Verification**:
   - Backup file created: `ls -l .env.backup_*`
   - File content matches original: `diff .env .env.backup_*`

3. **Record Backup Results**:
   - Backup file paths
   - Backup file sizes
   - Backup completion time
   - Status: ✅ Pass or ❌ Fail

#### Step 3: Test Upgrade Procedure (FR-014, FR-018)

Follow upgrade procedure from Migration Guide step-by-step:

**For each step in upgrade procedure**:

1. **Read Step Instructions**: Understand action, commands, validation
2. **Execute Commands**: Run exact commands from guide
3. **Verify Expected Output**: Compare actual output to documented output
4. **Run Validation**: Execute validation criteria for step
5. **Record Results**:
   - Step number
   - Action description
   - Expected output
   - Actual output
   - Validation result: ✅ Pass or ❌ Fail

**Key Upgrade Steps to Validate**:
- Stop v1.x server (verify process terminated)
- Update dependencies (verify v2.0 package installed)
- Run migration script (verify schema changes applied)
- Update configuration (verify new env vars set)
- Restart server (verify v2.0 server starts)

#### Step 4: Test Post-Migration Validation (FR-017)

Follow post-migration validation procedures from Migration Guide:

1. **Test index_repository with project_id**:
   ```bash
   # Use MCP client or test script to invoke index_repository
   # Verify: Repository indexed successfully, project_id parameter works
   ```

2. **Test search_code with project_id**:
   ```bash
   # Use MCP client or test script to invoke search_code
   # Verify: Search returns results, project_id parameter works
   ```

3. **Verify Existing Repositories Searchable**:
   - Query indexed repositories from v1.x
   - Verify repositories still exist in v2.0
   - Verify search returns results from v1.x repositories

4. **Run Diagnostic Commands** (FR-036):
   ```sql
   -- Check v2.0 schema present
   SELECT table_name FROM information_schema.tables
   WHERE table_schema = 'public'
   ORDER BY table_name;

   -- Verify v1.x tables dropped
   -- (Expect 9 tables missing: projects, project_contexts, entity_types, entities, work_items, etc.)
   ```

5. **Record Validation Results**:
   - Each validation command
   - Expected result
   - Actual result
   - Status: ✅ Pass or ❌ Fail

#### Step 5: Test Rollback Procedure (FR-016)

Follow rollback procedure from Migration Guide step-by-step:

**For each step in rollback procedure**:

1. **Execute Rollback Command**: Run exact command from guide
2. **Verify Expected Output**: Compare to documented output
3. **Run Validation**: Execute validation for rollback step
4. **Record Results**: Document actual results and status

**Key Rollback Steps to Validate**:
- Stop v2.0 server (verify process terminated)
- Restore database backup (verify restoration completes)
- Restore configuration backup (verify .env restored)
- Reinstall v1.x version (verify v1.x package installed)
- Start v1.x server (verify v1.x server starts)

#### Step 6: Test Rollback Validation (FR-017)

Follow rollback validation procedures from Migration Guide:

1. **Verify v1.x Functionality Restored**:
   - Test v1.x tools (create_project, query_entities, etc.)
   - Verify v1.x tools work as expected
   - Verify database contains v1.x schema

2. **Verify Data Restored**:
   - Check indexed repositories from baseline
   - Verify repository count matches baseline
   - Verify repository names match baseline

3. **Run v1.x Validation Commands**:
   ```sql
   -- Check v1.x tables present
   SELECT table_name FROM information_schema.tables
   WHERE table_schema = 'public'
   ORDER BY table_name;

   -- Verify v1.x data intact
   SELECT count(*) FROM repositories;
   ```

4. **Record Validation Results**:
   - Each validation command
   - Expected result (baseline state)
   - Actual result
   - Status: ✅ Pass or ❌ Fail

#### Step 7: Test Diagnostic Commands (FR-036)

Simulate partial migration failure and test diagnostic commands:

1. **Simulate Failure**: Interrupt migration script midway (e.g., stop after schema changes but before data migration)

2. **Run Diagnostic Commands**:
   ```sql
   -- Check which tables exist
   SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';

   -- Check schema version (if migration tracking table exists)
   SELECT version FROM alembic_version;
   ```

3. **Verify Commands Detect State**:
   - Commands execute without error
   - Output indicates partial migration state
   - Guidance provided for recovery

4. **Record Results**: Document diagnostic command effectiveness

### Expected Results

- **Upgrade Procedure Completes**: All upgrade steps execute successfully
- **v2.0 Functionality Works**: Both tools (index_repository, search_code) functional with project_id
- **Repositories Preserved**: v1.x indexed repositories still searchable in v2.0
- **Rollback Procedure Completes**: All rollback steps execute successfully
- **v1.x Functionality Restored**: v1.x tools work after rollback
- **Diagnostic Commands Work**: Partial migration state detectable
- **Migration Guide Validated**: End-to-end procedure tested and verified

### Pass/Fail Criteria

**PASS**:
- Upgrade completes successfully with v2.0 functionality working
- Rollback restores v1.x functionality and data
- Diagnostic commands detect partial migration state
- All validation commands pass

**FAIL**:
- Upgrade procedure fails or produces errors
- v2.0 functionality not working after upgrade
- Rollback fails to restore v1.x functionality
- Data loss detected (repositories not preserved)
- Diagnostic commands fail or provide misleading information

**Failure Resolution**: Update migration guide with corrections, re-test full procedure

---

## Test Scenario 4: Configuration Guide Validation in Staging (FR-021 to FR-027, FR-038)

**Objective**: Validate configuration guide by applying configuration examples in staging environment

**Requirement Traceability**:
- FR-021 (Environment variables documented with defaults)
- FR-022 (MAX_PROJECTS documented with implications)
- FR-023 (MAX_CONNECTIONS_PER_POOL documented with tuning)
- FR-024 (PostgreSQL max_connections calculation formula)
- FR-025 (PostgreSQL tuning parameters)
- FR-026 (workflow-mcp integration variables)
- FR-027 (Configuration validation checklist)
- FR-038 (Connection pool monitoring metrics)

**Success Criteria**: SC-010 (System administrators deploy v2.0 to production with correct configuration on first attempt)

### Prerequisites

- Staging environment (separate from production and test)
- PostgreSQL 14+ with admin access
- Ollama running with embedding model
- workflow-mcp server (optional, for testing integration variables)
- v2.0 codebase-mcp installed in staging

### Procedure

#### Step 1: Test Environment Variable Examples (FR-021)

For each environment variable in Configuration Guide:

1. **Copy Example Value**: Extract example from table
2. **Set Environment Variable**:
   ```bash
   export DATABASE_URL="postgresql://user:pass@localhost/codebase_test"
   export OLLAMA_BASE_URL="http://localhost:11434"
   export MAX_PROJECTS=10
   # ... etc for all variables
   ```

3. **Verify Application Accepts Value**: Start codebase-mcp server, check logs for errors

4. **Record Results**:
   - Variable name
   - Example value
   - Application behavior (accepted/rejected)
   - Status: ✅ Pass or ❌ Fail

**Variables to Test**:
- Core: `DATABASE_URL`, `OLLAMA_BASE_URL`, `EMBEDDING_MODEL`
- Multi-Project: `MAX_PROJECTS`, `MAX_CONNECTIONS_PER_POOL`, `PROJECT_POOL_TIMEOUT`
- Integration: `WORKFLOW_MCP_URL`, `WORKFLOW_MCP_TIMEOUT`

#### Step 2: Test Connection Calculation Examples (FR-024)

For each scenario in calculation table:

1. **Copy Formula**: `Total = MAX_PROJECTS × MAX_CONNECTIONS_PER_POOL`

2. **Plug in Scenario Values**:
   ```
   Scenario: Small Deployment
   MAX_PROJECTS=5, MAX_CONNECTIONS_PER_POOL=10
   Calculated: 5 × 10 = 50
   Table Value: 50
   ```

3. **Verify Calculation Matches Table**: Compare calculated result to table value

4. **Record Results**:
   - Scenario name
   - Formula
   - Calculated result
   - Table result
   - Status: ✅ Pass (match) or ❌ Fail (mismatch)

**Scenarios to Test**:
- Small Deployment (5 projects, 10 connections per pool)
- Medium Deployment (10 projects, 20 connections per pool)
- Large Deployment (20 projects, 25 connections per pool)

#### Step 3: Test PostgreSQL Tuning Examples (FR-025)

For each PostgreSQL setting in Configuration Guide:

1. **Copy Setting from Guide**:
   ```ini
   shared_buffers = 4GB
   effective_cache_size = 12GB
   work_mem = 64MB
   ```

2. **Apply in Staging Database**:
   ```bash
   # Edit postgresql.conf or use ALTER SYSTEM
   psql -c "ALTER SYSTEM SET shared_buffers = '4GB';"
   psql -c "SELECT pg_reload_conf();"
   ```

3. **Verify Setting Applied**:
   ```bash
   psql -c "SHOW shared_buffers;"
   # Expected: 4GB
   ```

4. **Record Results**:
   - Setting name
   - Documented value
   - Actual value after application
   - Status: ✅ Pass (applied) or ❌ Fail (not applied or error)

**Settings to Test**:
- `max_connections` (calculate based on MAX_PROJECTS formula)
- `shared_buffers`
- `effective_cache_size`
- `maintenance_work_mem`
- `work_mem`
- `random_page_cost`

#### Step 4: Test Validation Checklist Commands (FR-027)

Follow validation checklist from Configuration Guide:

**For each checklist item**:

1. **Execute Command**: Run exact command from checklist
   ```bash
   # Example: Test DATABASE_URL connection
   psql $DATABASE_URL -c "SELECT 1;"
   # Expected: (1 row)
   ```

2. **Verify Expected Result**: Compare to documented expected result

3. **Record Results**:
   - Checklist item description
   - Command
   - Expected result
   - Actual result
   - Status: ✅ Pass or ❌ Fail

**Checklist Items to Test**:
- [ ] DATABASE_URL connects successfully
- [ ] OLLAMA_BASE_URL responds
- [ ] Embedding model available
- [ ] PostgreSQL max_connections sufficient (calculation verification)
- [ ] workflow-mcp reachable (if configured)
- [ ] Test indexing (small repository)
- [ ] Test search (query test repository)
- [ ] Verify project isolation (index two projects, confirm separate databases)

#### Step 5: Test Monitoring Queries (FR-038)

For each monitoring SQL query in Configuration Guide:

1. **Copy Query**: Extract SQL from Monitoring section

2. **Execute Against Staging**:
   ```sql
   -- Check active databases
   SELECT datname FROM pg_database WHERE datname LIKE 'codebase_%';

   -- Check connection count per database
   SELECT datname, count(*)
   FROM pg_stat_activity
   WHERE datname LIKE 'codebase_%'
   GROUP BY datname;

   -- Check total connections
   SELECT count(*) FROM pg_stat_activity;
   ```

3. **Verify Query Executes**: Check for errors, verify result format

4. **Record Results**:
   - Query description
   - Expected columns
   - Actual result (format and data)
   - Status: ✅ Pass or ❌ Fail

**Monitoring Queries to Test**:
- Active project databases query
- Connection count per database query
- Total connections query
- Pool eviction detection (check logs if available)

#### Step 6: Test Tradeoff Documentation (FR-022, FR-023)

Validate tradeoff documentation accuracy:

1. **Review Higher Value Tradeoffs**: Read pros/cons for increasing MAX_PROJECTS
2. **Review Lower Value Tradeoffs**: Read pros/cons for decreasing MAX_PROJECTS
3. **Test with Actual Configuration**: Set MAX_PROJECTS to high value (e.g., 50)
4. **Observe Behavior**: Monitor PostgreSQL connection count, memory usage
5. **Verify Tradeoffs Match Reality**: Confirm documented tradeoffs (more connections, more memory) are accurate

**Record Observations**:
- Documented tradeoff
- Observed behavior in staging
- Status: ✅ Accurate or ❌ Inaccurate

#### Step 7: Document Configuration Issues

For any ❌ Fail:

1. **Diagnose Issue**: Determine if documentation error or staging environment issue
2. **Fix Documentation**: Update configuration guide with corrections
3. **Re-Test**: Verify fix resolves issue
4. **Update Test Log**: Mark as ✅ Pass after fix verified

### Expected Results

- **All Environment Variable Examples Valid**: Examples accepted by application
- **All Calculations Correct**: Formula matches table scenarios
- **All PostgreSQL Settings Apply**: Settings accepted by PostgreSQL
- **Validation Checklist Commands Work**: All checklist items pass
- **Monitoring Queries Execute**: Queries return expected data format
- **Tradeoffs Accurate**: Documented tradeoffs match observed behavior
- **Configuration Guide Validated**: All examples tested in staging

### Pass/Fail Criteria

**PASS**:
- All environment variable examples valid
- All calculations match table values
- All PostgreSQL settings apply successfully
- All validation checklist commands pass
- All monitoring queries execute and return sensible data
- Documented tradeoffs match observed behavior

**FAIL**:
- Environment variable example rejected by application
- Calculation mismatch
- PostgreSQL setting fails to apply
- Validation checklist command fails
- Monitoring query fails or returns unexpected format
- Documented tradeoffs inaccurate

**Failure Resolution**: Fix configuration guide errors, re-test in staging

---

## Test Scenario 5: Cross-Artifact Consistency Check (FR-034, FR-035)

**Objective**: Verify terminology consistency and formatting across all 5 documentation artifacts

**Requirement Traceability**:
- FR-034 (Consistent terminology using glossary.md)
- FR-035 (Markdown style guide formatting)

**Success Criteria**: SC-001 to SC-006 (various consistency and completeness metrics)

### Prerequisites

- All 5 documentation artifacts authored and saved
- Glossary file (docs/glossary.md) created with canonical terms
- Project markdown style guide available
- Text editor with search/replace capability

### Procedure

#### Step 1: Terminology Consistency Check (FR-034)

For each canonical term in glossary:

1. **Extract Term from Glossary**: Read term, definition, usage rule

2. **Search All Documentation**:
   ```bash
   grep -rn "project_id\|project ID\|projectId" README.md docs/
   ```

3. **Verify Consistent Usage**: Check all occurrences follow usage rule

4. **Record Inconsistencies**:
   - File name
   - Line number
   - Incorrect usage
   - Correct usage (from glossary)

**Terms to Check**:
- `project_id` (not "project ID", "projectId")
- `connection pool` (not "conn pool", "connection-pool")
- `LRU eviction` (spelled out on first use, then "LRU eviction")
- `database-per-project` (hyphenated, not "database per project")
- `workflow-mcp integration` (lowercase 'w', not "Workflow-MCP")
- `default project` (not "default-project")

**Additional Checks**:
- Technical terms: "PostgreSQL" (not "Postgres", "postgres")
- Technical terms: "FastMCP" (not "Fast MCP", "fastmcp")
- Tool names: "index_repository" (not "indexRepository", "index-repository")
- Tool names: "search_code" (not "searchCode", "search-code")

#### Step 2: Abbreviation Check (FR-034)

Search for common abbreviations:

1. **Find First Use of Abbreviation**:
   ```bash
   grep -n "LRU" README.md docs/
   ```

2. **Verify Spelled Out on First Use**: Check first occurrence includes full term
   - Example: "LRU (Least Recently Used) eviction"

3. **Record Violations**: Document any abbreviation used without first spelling out

**Abbreviations to Check**:
- LRU (Least Recently Used)
- MCP (Model Context Protocol)
- SSE (Server-Sent Events)
- SQL (Structured Query Language) - typically not spelled out, verify usage

#### Step 3: Markdown Style Guide Check (FR-035)

For each style rule:

1. **Code Blocks Have Language Specifiers**:
   ```bash
   # Find code blocks without language
   grep -n '```$' README.md docs/
   # Expected: No matches (all code blocks should have language: ```bash, ```sql, etc.)
   ```

2. **Heading Hierarchy Check**:
   - Verify no skipped levels (H1 → H2 → H3, not H1 → H3)
   - Verify single H1 per document
   ```bash
   grep -n '^#' README.md  # Extract all headings, visually verify hierarchy
   ```

3. **Table Formatting Check**:
   - Verify pipes aligned
   - Verify header row separator (|---|---|)
   - Example:
     ```
     | Column 1 | Column 2 |
     |----------|----------|
     | Value 1  | Value 2  |
     ```

4. **File Naming Check**:
   - Verify lowercase-with-hyphens.md format
   - Verify no spaces or underscores in file names
   ```bash
   find docs/ -name '*.md' | grep -v '^[a-z0-9-/]*\.md$'
   # Expected: No matches (all files follow convention)
   ```

5. **Record Violations**: Document any style guide deviations

**Style Rules to Validate**:
- Code blocks with language specifiers
- Heading hierarchy (no skipped levels)
- Single H1 per document
- Table formatting consistency
- File naming convention
- Consistent list formatting (ordered vs unordered)

#### Step 4: Cross-Reference Consistency Check

Verify consistent information across artifacts:

1. **Tool Count Consistency** (FR-001):
   - README Features section: 2 tools
   - API Reference Overview: 2 tools
   - Architecture Docs Component Diagram: 2 tools
   - Verify all mentions consistent

2. **Removed Tools List Consistency** (FR-010):
   - Migration Guide: 14 tools listed
   - API Reference Removed Tools: 14 tools listed
   - Verify lists match exactly

3. **Environment Variable Consistency**:
   - Configuration Guide table: All env vars with defaults
   - Migration Guide new env vars: Subset of config guide
   - Verify no conflicting defaults

4. **project_id Behavior Consistency**:
   - README Quick Start: Default project behavior
   - API Reference index_repository: Default project behavior
   - API Reference search_code: Default project behavior
   - Configuration Guide: Default project mentioned
   - Verify all descriptions match

5. **Record Inconsistencies**: Document any conflicting information across artifacts

#### Step 5: Link Cross-Reference Check

Verify cross-references between artifacts are bidirectional:

1. **README Links to Specialized Guides**:
   - Verify README links to migration, configuration, architecture, API reference
   - Verify each guide links back to README

2. **Migration Guide Links**:
   - Verify links to configuration guide (for env vars)
   - Verify links to API reference (for removed tools)

3. **Configuration Guide Links**:
   - Verify links to architecture docs (for design explanation)
   - Verify links to migration guide (for upgrade context)

4. **Record Missing Cross-References**: Document any one-way references that should be bidirectional

#### Step 6: Document and Fix Inconsistencies

For each inconsistency found:

1. **Determine Correct Version**: Reference spec.md, glossary.md, or implementation
2. **Fix All Occurrences**: Update documentation with correct terminology/formatting
3. **Re-Test**: Verify fix applied consistently
4. **Update Test Log**: Mark as ✅ Pass after fix verified

### Expected Results

- **Terminology 100% Consistent**: All glossary terms used correctly across artifacts
- **Abbreviations Spelled Out**: All first uses include full term
- **Markdown Style Consistent**: All artifacts follow style guide
- **Cross-References Consistent**: Information matches across artifacts
- **Links Bidirectional**: Cross-references are bidirectional where appropriate
- **Consistency Validated**: All 5 artifacts consistent with each other

### Pass/Fail Criteria

**PASS**:
- All terminology matches glossary usage rules
- All abbreviations spelled out on first use
- All markdown formatting follows style guide
- No conflicting information across artifacts
- All cross-references correct and bidirectional

**FAIL**:
- Terminology inconsistencies found
- Abbreviations not spelled out
- Markdown style violations
- Conflicting information across artifacts
- Missing or broken cross-references

**Failure Resolution**: Fix inconsistencies and re-test

---

## Validation Checklist (Master Checklist)

Complete all scenarios before PR submission:

### Scenario Completion
- [ ] Test Scenario 1: Link Verification (FR-032) - PASSED
- [ ] Test Scenario 2: Code Example Testing (FR-033) - PASSED
- [ ] Test Scenario 3: Migration Guide Validation (FR-014 to FR-017) - PASSED
- [ ] Test Scenario 4: Configuration Guide Validation (FR-021 to FR-027) - PASSED
- [ ] Test Scenario 5: Cross-Artifact Consistency Check (FR-034, FR-035) - PASSED

### Deliverables
- [ ] Link inventory spreadsheet complete with 100% pass rate
- [ ] Code example test log complete with 100% pass rate
- [ ] Migration guide test report with upgrade and rollback validation
- [ ] Configuration guide test report with staging validation
- [ ] Consistency check report with no violations

### Quality Metrics (Success Criteria)
- [ ] SC-001: 100% tool names match (2 tools documented accurately)
- [ ] SC-002: 100% removed tools documented (14 tools listed by name)
- [ ] SC-003: 0 broken links (link inventory 100% pass)
- [ ] SC-004: 100% code examples tested (test log 100% pass)
- [ ] SC-005: 100% breaking changes mapped to migration steps
- [ ] SC-006: 100% environment variables documented with defaults

### Functional Requirements Coverage
- [ ] FR-001 to FR-008: Documentation Accuracy Requirements validated
- [ ] FR-009 to FR-020, FR-036, FR-037: Migration Guide Requirements validated
- [ ] FR-021 to FR-027, FR-038: Configuration Guide Requirements validated
- [ ] FR-028 to FR-031: Architecture Documentation Requirements validated
- [ ] FR-032: Link validation complete (0 broken links)
- [ ] FR-033: Code example testing complete (100% pass)
- [ ] FR-034: Terminology consistency validated
- [ ] FR-035: Formatting consistency validated

### Persona Coverage
- [ ] New user can complete first installation and search (User Story 2)
- [ ] Existing user can upgrade safely (User Story 1)
- [ ] Administrator can configure production (User Story 3)
- [ ] Developer can integrate workflow-mcp (User Story 4)
- [ ] Maintainer understands architecture (User Story 5)

### Review and Approval
- [ ] Author validation complete (all scenarios passed)
- [ ] Peer review requested (separate reviewer assigned)
- [ ] Reviewer confirms link validation (spot-check 20%)
- [ ] Reviewer confirms code example validation (spot-check 20%)
- [ ] Reviewer confirms migration guide validation (full test in their environment)
- [ ] Both author and reviewer sign off on checklist

---

## Notes

**Manual Validation Rationale**: Phase 05 scope uses manual validation with structured procedures. Automated validation (CI integration, link checking tools, example testing frameworks) is explicitly deferred to Phase 07 per FR-032/FR-033 and Non-Goals section of spec.md.

**Staging Environment**: All configuration and migration testing MUST occur in non-production staging environment. Never test destructive procedures (database migrations, configuration changes) in production.

**Test Data**: Use small test repositories (<100 files) for indexing tests to reduce test execution time. Larger repository testing deferred to Phase 06 performance validation.

**Version Control**: Commit test logs and validation reports to repository alongside documentation artifacts for traceability and audit trail.

**Failure Handling**: Any test failure requires fixing documentation and re-running full test suite. Do not proceed to PR submission with failing tests.

**Peer Review**: Separate reviewer (not author) must independently verify validation procedures completed. Reviewer should spot-check 20% of links and code examples, and run full migration guide test in their own environment.
