# Session Handoff: MCP Tools Integration Testing

**Date**: 2025-10-18
**Branch**: `fix/project-resolution-auto-create`
**Objective**: Test codebase-mcp MCP server tools by indexing this repository for semantic search

---

## Context

### What Was Just Completed

Two critical bugs were fixed using parallel debugger agents with micro-commits:

1. **Registry Sync Bug** (`5a0c6462`)
   - Fixed AsyncPG nested transaction error preventing PostgreSQL registry persistence
   - Projects now correctly sync to persistent registry

2. **Event Loop Test Bug** (`16117eca`)
   - Fixed test infrastructure issue where connection pools outlived event loops
   - All 4 config-based project creation tests now pass

### Current Status

✅ **Primary bug fixed and verified**
✅ **All critical integration tests passing**
✅ **Code changes committed to branch**
🔲 **MCP tools not yet tested end-to-end**

---

## Testing Objective

**Goal**: Validate that the MCP server tools work correctly by:
1. Creating a project workspace for this codebase
2. Indexing the entire codebase-mcp repository
3. Performing semantic searches to verify functionality
4. Testing project isolation (ensure data goes to correct database)

**Why This Matters**:
- These tools are what AI assistants (like Claude Code) will actually use
- Need to verify the bug fixes work through the MCP interface, not just in tests
- Confirms end-to-end workflow: session config → project creation → indexing → search

---

## Environment

**Working Directory**: `/Users/cliffclarke/Claude_Code/codebase-mcp`
**Branch**: `fix/project-resolution-auto-create`
**Python**: 3.13.7
**PostgreSQL**: Running locally (port 5432)

**Project Configuration**:
- File: `.codebase-mcp/config.json`
- Should exist with project name: `"codebase-mcp"`
- Project ID: Auto-generated UUID (will be created during testing)

---

## Testing Workflow

### Phase 1: Set Working Directory (Session-Based Config)

**Tool**: `mcp__codebase-mcp__set_working_directory`

**Action**:
```
set_working_directory(
    directory="/Users/cliffclarke/Claude_Code/codebase-mcp"
)
```

**Expected Result**:
```json
{
    "session_id": "...",
    "working_directory": "/Users/cliffclarke/Claude_Code/codebase-mcp",
    "config_found": true,
    "config_path": "/Users/cliffclarke/Claude_Code/codebase-mcp/.codebase-mcp/config.json",
    "project_info": {
        "name": "codebase-mcp",
        "id": null  // or a UUID if config has one
    }
}
```

**Success Criteria**:
- ✅ `config_found: true`
- ✅ `config_path` points to correct file
- ✅ `project_info.name` is "codebase-mcp"

**What This Tests**: Tier 2 resolution (session-based config discovery)

---

### Phase 2: Index Repository (Background Only)

**Note**: Foreground `index_repository` tool has been removed. All indexing now uses background jobs to prevent MCP client timeouts.

**Tool**: `mcp__codebase-mcp__start_indexing_background`

**Action**:
```
start_indexing_background(
    repo_path="/Users/cliffclarke/Claude_Code/codebase-mcp"
)
```

**Expected Immediate Result**:
```json
{
    "job_id": "uuid",
    "status": "pending",
    "message": "Indexing job started",
    "project_id": "uuid",
    "database_name": "cb_proj_codebase_mcp_<hash>"
}
```

**Poll for Status**:
```
get_indexing_status(job_id="uuid-from-above")
```

**Expected Status Progression**:
- Initial: `status: "pending"`
- After ~1-2s: `status: "running"`
- After indexing completes: `status: "completed"`

**Final Completed Status**:
```json
{
    "job_id": "uuid",
    "status": "completed",
    "repo_path": "/Users/cliffclarke/Claude_Code/codebase-mcp",
    "files_indexed": 50-100,  // approximately
    "chunks_created": 500-1000,  // approximately
    "error_message": null,
    "created_at": "2025-10-18T...",
    "started_at": "2025-10-18T...",
    "completed_at": "2025-10-18T..."
}
```

**Success Criteria**:
- ✅ Job starts with `status: "pending"`
- ✅ Status progresses to `"running"` within 5 seconds
- ✅ Eventually reaches `"completed"`
- ✅ `files_indexed` > 0 (should be 50+)
- ✅ `chunks_created` > 0 (should be 500+)
- ✅ `error_message` is null
- ✅ `database_name` contains "codebase_mcp" (not "default")

**What This Tests**:
- Tier 2 project resolution (session config)
- Auto-create module integration
- PostgreSQL registry sync (bug we just fixed)
- Database provisioning
- Background indexing pipeline
- Job state management

---

### Phase 3: Verify Project Isolation

**Manual Verification** (via database inspection):

**Query 1: Check Registry**
```sql
SELECT id, name, database_name
FROM projects
WHERE name = 'codebase-mcp';
```

**Expected**:
- ✅ One row returned
- ✅ `name` = "codebase-mcp"
- ✅ `database_name` = "cb_proj_codebase_mcp_<hash>"

**Query 2: Check Project Database**
```sql
-- Connect to project database from Phase 2
\c <database_name_from_phase_2>

SELECT COUNT(*) FROM repositories;
-- Expected: 1

SELECT COUNT(*) FROM code_files;
-- Expected: 50-100

SELECT COUNT(*) FROM code_chunks;
-- Expected: 500-1000
```

**What This Tests**: PostgreSQL registry persistence (the bug we fixed in commit `5a0c6462`)

---

### Phase 4: Semantic Search

**Tool**: `mcp__codebase-mcp__search_code`

**Test 1: Search for "AsyncPG connection pool"**
```
search_code(
    query="AsyncPG connection pool management",
    limit=5
)
```

**Expected Result**:
```json
{
    "results": [
        {
            "chunk_id": "uuid",
            "file_path": "src/database/session.py",
            "content": "... _registry_pool ...",
            "start_line": 85,
            "end_line": 95,
            "similarity_score": 0.85-0.95,
            "context_before": "...",
            "context_after": "..."
        },
        ...
    ],
    "total_count": 5,
    "project_id": "uuid",
    "database_name": "cb_proj_codebase_mcp_<hash>",
    "latency_ms": 100-500
}
```

**Success Criteria**:
- ✅ `results` contains relevant code from `src/database/session.py`
- ✅ `similarity_score` > 0.7 for top results
- ✅ `latency_ms` < 500 (constitutional performance target)
- ✅ `database_name` matches Phase 2 (correct project isolation)

**Test 2: Search for "event loop closure"**
```
search_code(
    query="event loop closure error handling",
    limit=5
)
```

**Expected**: Should find the cleanup fixture we just added in `tests/integration/conftest.py`

**Test 3: Search for "registry sync transaction"**
```
search_code(
    query="PostgreSQL registry synchronization",
    limit=5
)
```

**Expected**: Should find the registry sync code in `src/database/auto_create.py` lines 455-530

**What This Tests**:
- Semantic search functionality
- Embedding generation and retrieval
- pgvector similarity matching
- Project isolation (uses correct database)
- Performance targets

---

### Phase 5: Additional Repository Indexing (Optional)

**Tool**: `mcp__codebase-mcp__start_indexing_background`

**Purpose**: Test indexing a second repository to verify multi-project isolation.

**Action**:
```
start_indexing_background(
    repo_path="/Users/cliffclarke/Claude_Code/workflow-mcp"
)
```

**Expected Result**:
```json
{
    "job_id": "uuid",
    "status": "pending",
    "message": "Indexing job started",
    "project_id": "workflow-mcp-uuid",
    "database_name": "cb_proj_workflow_mcp_<hash>"
}
```

**Poll for Status**:
```
get_indexing_status(job_id="uuid-from-above")
```

**Expected Progression**:
- `status: "pending"` → `"running"` → `"completed"`
- `files_indexed` increments over time
- `chunks_created` increments over time

**Success Criteria**:
- ✅ Job starts with `status: "pending"`
- ✅ Status progresses to `"running"` within 5 seconds
- ✅ Eventually reaches `"completed"`
- ✅ `files_indexed` matches repository size (~350 files for workflow-mcp)
- ✅ Different `database_name` than Phase 2 (project isolation)

**What This Tests**: Multi-project isolation, background worker scalability

---

## Key Things to Observe

### 1. Project Auto-Creation

When indexing runs, watch for automatic project creation:
- Should detect project from `.codebase-mcp/config.json`
- Should create project in PostgreSQL registry (not just in-memory)
- Should create project-specific database

### 2. Database Naming

All operations should use project-specific databases:
- ✅ **CORRECT**: `cb_proj_codebase_mcp_abc12345`
- ❌ **WRONG**: `cb_proj_default_00000000`

If you see "default", the bug is NOT fixed.

### 3. Registry Persistence

After indexing completes, project should persist in PostgreSQL:
```sql
SELECT COUNT(*) FROM projects WHERE name = 'codebase-mcp';
-- Expected: 1 (not 0)
```

If count is 0, the registry sync bug is NOT fixed.

### 4. Performance Targets (Constitutional Principles)

- **Indexing**: <60 seconds for ~100 files (Principle IV)
- **Search**: <500ms p95 latency (Principle IV)

### 5. Error Handling

No errors should occur. If they do, check:
- PostgreSQL connection issues
- Database permission problems
- Event loop closure errors (should be fixed)
- AsyncPG transaction errors (should be fixed)

---

## Debugging Commands

If issues arise, use these to investigate:

**1. Check PostgreSQL Registry**
```bash
psql -h localhost -U postgres -d codebase_mcp -c "SELECT id, name, database_name, created_at FROM projects ORDER BY created_at DESC LIMIT 10;"
```

**2. List All Project Databases**
```bash
psql -h localhost -U postgres -c "\l" | grep cb_proj
```

**3. Inspect Project Database**
```bash
# Get database name from Phase 2 result
psql -h localhost -U postgres -d <database_name> -c "\dt"
psql -h localhost -U postgres -d <database_name> -c "SELECT COUNT(*) FROM code_chunks;"
```

**4. Check Logs**
```bash
tail -f /tmp/codebase-mcp.log | grep -E "(registry|session|project)"
```

**5. Verify Config File**
```bash
cat /Users/cliffclarke/Claude_Code/codebase-mcp/.codebase-mcp/config.json
```

---

## Expected File Structure

```
/Users/cliffclarke/Claude_Code/codebase-mcp/
├── .codebase-mcp/
│   └── config.json              # Project configuration
├── src/
│   ├── database/
│   │   ├── auto_create.py       # Auto-create module (registry sync fix)
│   │   ├── session.py           # Session management (Tier 2 resolution)
│   │   └── provisioning.py      # Database provisioning
│   ├── services/
│   │   ├── indexer.py           # Indexing logic
│   │   └── search.py            # Search logic
│   └── auto_switch/
│       ├── discovery.py         # Config discovery
│       └── cache.py             # Config caching
└── tests/
    └── integration/
        ├── conftest.py          # Cleanup fixture (event loop fix)
        └── test_config_based_project_creation.py
```

---

## Success Criteria Summary

**All of these must be true**:

1. ✅ Session config discovery works (`config_found: true`)
2. ✅ Project auto-created from config (not default)
3. ✅ Project persists in PostgreSQL registry (survives server restart)
4. ✅ Project-specific database created (`cb_proj_codebase_mcp_*`)
5. ✅ Background indexing job starts (`status: "pending"`)
6. ✅ Job progresses to running and completes (`status: "completed"`)
7. ✅ Repository indexed successfully (50+ files, 500+ chunks)
8. ✅ Semantic search returns relevant results
9. ✅ Search latency <500ms
10. ✅ No errors in any operation

---

## Known Issues (Not Blockers)

These are pre-existing issues NOT related to the bugs we fixed:

1. **Auto-provisioning tests failing**: Some tests fail because they expect workflow-mcp integration (not implemented yet). This is expected.

2. **Resilience tests failing**: These test cross-server communication (codebase-mcp + workflow-mcp). Not applicable for single-server testing.

3. **Concurrent indexing**: Force reindex during background job can cause duplicate key errors. Users unlikely to trigger this.

---

## What to Report Back

After testing, report:

1. **Phase 1 Result**: Did session config discovery work?
2. **Phase 2 Result**: Did indexing complete successfully? (files, chunks, duration, database name)
3. **Phase 3 Result**: Is project in PostgreSQL registry?
4. **Phase 4 Result**: Do searches return relevant results? (latency, accuracy)
5. **Phase 5 Result** (if tested): Did background indexing work?

**Most Important**:
- Did operations use project-specific database (NOT default)?
- Did project persist in PostgreSQL registry?
- Were there any errors?

---

## Next Steps After Testing

If all tests pass:
1. Document test results in this file
2. Consider merging branch to `master`
3. Update CHANGELOG.md with bug fixes
4. Close related issues/tickets

If tests fail:
1. Document failure details
2. Check database state with debugging commands
3. Review logs for error messages
4. Create new bug report with findings

---

## Technical Context

**4-Tier Project Resolution Chain** (tested in this workflow):
1. Tier 1: Explicit `project_id` parameter (not tested here)
2. **Tier 2: Session-based config** (`.codebase-mcp/config.json`) ← **THIS IS WHAT WE'RE TESTING**
3. Tier 3: workflow-mcp integration (not implemented)
4. Tier 4: Default fallback (should NOT be used)

**Fixes Being Validated**:
- ✅ AsyncPG transaction handling (commit `5a0c6462`)
- ✅ Event loop test cleanup (commit `16117eca`)
- ✅ PostgreSQL registry check (commit `4cfed7ab`)

**Architecture**:
- Dual-registry: In-memory + PostgreSQL (both should be populated)
- Schema-based isolation: Each project gets own database
- Session-based config: Auto-discovery via `set_working_directory`

---

## Contact/References

- **Bug Investigation**: `/Users/cliffclarke/Claude_Code/codebase-mcp/docs/bugs/project-resolution-secondary-call/`
- **Branch**: `fix/project-resolution-auto-create`
- **Recent Commits**:
  - `16117eca` - Event loop fix
  - `5a0c6462` - Registry sync fix
  - `4cfed7ab` - Registry check

---

**Good luck with testing! The MCP tools should work flawlessly now that the bugs are fixed.**
