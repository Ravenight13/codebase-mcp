# Documentation Update Plan: Foreground Indexing Removal

**Date**: 2025-10-18
**Objective**: Update all documentation to reflect background-only indexing pattern
**Context**: Removing foreground `index_repository` tool, keeping only background indexing

---

## Executive Summary

Found **161 markdown files** with references to `index_repository` across the codebase, plus **1,071+ total references** including Python files. This plan prioritizes user-facing documentation first, then developer documentation, then archives.

**Total Impact**:
- High Priority (User-Facing): 15 files
- Medium Priority (Developer Docs): 25 files
- Low Priority (Archive/Historical): 121 files
- Code Files: Separate cleanup task

---

## Standard Background Indexing Pattern

All documentation should use this pattern:

### ❌ OLD PATTERN (Remove)
```python
# Foreground indexing (DEPRECATED)
result = index_repository(repo_path="/path/to/repo")
print(f"Indexed {result['files_indexed']} files")
```

### ✅ NEW PATTERN (Use Everywhere)
```python
# Start background indexing job
job = start_indexing_background(repo_path="/path/to/repo")
job_id = job["job_id"]

# Poll for completion (every 2-5 seconds)
while True:
    status = get_indexing_status(job_id=job_id)
    if status["status"] in ["completed", "failed"]:
        break
    time.sleep(2)

# Check result
if status["status"] == "completed":
    print(f"✅ Indexed {status['files_indexed']} files in {status['duration_seconds']}s")
else:
    print(f"❌ Indexing failed: {status['error_message']}")
```

---

## Files to Update

### 🔴 HIGH PRIORITY - User-Facing Documentation (15 files)

Must be updated before any release. These are the docs users will actually read.

#### 1. `/Users/cliffclarke/Claude_Code/codebase-mcp/README.md`
**Current**: Lines 11, 29-31, 42-44, 142-143
- Shows `index_repository` in features list
- Example code uses foreground pattern
- Tool status table lists `index_repository` as working

**Update Required**:
- Replace all examples with background pattern
- Update tool status table to show `start_indexing_background` and `get_indexing_status`
- Add note about removal of foreground indexing in v2.1+

**Priority**: **CRITICAL** - This is the first file users see

---

#### 2. `/Users/cliffclarke/Claude_Code/codebase-mcp/CLAUDE.md`
**Current**: Lines 12-143 (general context)
- Provides guidance to Claude Code agent
- May reference indexing workflow

**Update Required**:
- Update "Background Indexing" section (lines 115-143)
- Replace foreground examples with background pattern
- Add guidance on when to use background vs foreground (ALWAYS background now)

**Priority**: **CRITICAL** - Agent behavior depends on this

---

#### 3. `/Users/cliffclarke/Claude_Code/codebase-mcp/SESSION_HANDOFF_MCP_TESTING.md`
**Current**: Lines 97-145 - "Phase 2: Index Repository (Foreground)"
- Entire section uses foreground indexing pattern
- Test workflow expects foreground tool

**Update Required**:
- Rename section to "Phase 2: Index Repository (Background)"
- Replace all tool calls with background pattern
- Update expected results to show job status progression
- Add polling loop to test workflow

**Priority**: **CRITICAL** - Active testing documentation

**Lines to Change**:
```markdown
# OLD (Line 97)
### Phase 2: Index Repository (Foreground)

**Tool**: `mcp__codebase-mcp__index_repository`

# NEW
### Phase 2: Index Repository (Background)

**Tool**: `mcp__codebase-mcp__start_indexing_background`

**Action**:
```
start_indexing_background(
    repo_path="/Users/cliffclarke/Claude_Code/codebase-mcp"
)
```

**Expected Result** (immediate return):
```json
{
    "job_id": "uuid",
    "status": "pending",
    "message": "Indexing job started",
    ...
}
```

**Poll for Status**:
```
get_indexing_status(job_id="uuid-from-above")
```
```

---

#### 4. `/Users/cliffclarke/Claude_Code/codebase-mcp/docs/api/tool-reference.md`
**Current**: Lines 1-150 - Entire section documents `index_repository`
- Complete API reference for foreground tool
- Examples all use foreground pattern

**Update Required**:
- **DELETE** entire `index_repository` section (lines 9-150+)
- **ADD** new sections for:
  - `start_indexing_background`
  - `get_indexing_status`
  - `cancel_indexing_background` (if implemented)
- Update breaking change notice at top
- Add migration guide reference

**Priority**: **CRITICAL** - Primary API documentation

**New Structure**:
```markdown
# API Reference

> **Breaking Change**: codebase-mcp v2.1 removes synchronous `index_repository`
> tool in favor of background-only indexing. See Migration Guide below.

## start_indexing_background

Index a code repository asynchronously with job tracking.

### Parameters
...

## get_indexing_status

Query status of a background indexing job.

### Parameters
...

## Migration Guide

### Migrating from index_repository (v2.0) to background indexing (v2.1+)

**Old Pattern (v2.0)**:
```python
result = index_repository(repo_path="/path")
print(result['files_indexed'])
```

**New Pattern (v2.1+)**:
```python
# Start job
job = start_indexing_background(repo_path="/path")

# Poll for completion
while True:
    status = get_indexing_status(job_id=job["job_id"])
    if status["status"] in ["completed", "failed"]:
        break
    time.sleep(2)

print(status['files_indexed'])
```
```

---

#### 5. `/Users/cliffclarke/Claude_Code/codebase-mcp/docs/guides/TOOL_EXAMPLES.md`
**Current**: Lines 1-150 - Shows task management tools, may include indexing
- Practical examples for all tools
- Example code users copy-paste

**Update Required**:
- Remove any `index_repository` examples
- Add comprehensive `start_indexing_background` examples
- Add polling loop examples with error handling
- Show cancellation examples

**Priority**: **CRITICAL** - Users copy code from here

---

#### 6. `/Users/cliffclarke/Claude_Code/codebase-mcp/docs/guides/SETUP_GUIDE.md`
**Current**: References to indexing workflow
- Setup and configuration guide
- May show initial indexing

**Update Required**:
- Update any indexing examples to background pattern
- Add note about indexing duration
- Update expected output examples

**Priority**: **HIGH** - New users follow this

---

#### 7. `/Users/cliffclarke/Claude_Code/codebase-mcp/docs/operations/MCP-SERVER-DEPLOYMENT.md`
**Current**: Deployment documentation
- Operational procedures
- May include indexing examples

**Update Required**:
- Update deployment test procedures
- Update indexing validation steps
- Add monitoring guidance for background jobs

**Priority**: **HIGH** - Operations team uses this

---

#### 8. `/Users/cliffclarke/Claude_Code/codebase-mcp/docs/operations/QUICK-RESTART-GUIDE.md`
**Current**: Quick reference for operators
- Fast troubleshooting guide
- May show indexing commands

**Update Required**:
- Update indexing command examples
- Add job status check commands
- Update troubleshooting for hung jobs

**Priority**: **HIGH** - Used during incidents

---

#### 9. `/Users/cliffclarke/Claude_Code/codebase-mcp/docs/operations/README-DEPLOYMENT.md`
**Current**: Deployment procedures
**Priority**: **HIGH**

---

#### 10. `/Users/cliffclarke/Claude_Code/codebase-mcp/docs/operations/troubleshooting.md`
**Current**: Troubleshooting guide
**Priority**: **HIGH** - Add job troubleshooting section

---

#### 11-15. **Quickstart Guides** (5 files)
- `specs/001-build-a-production/quickstart.md`
- `specs/002-refactor-mcp-server/quickstart.md`
- `specs/007-remove-non-search/quickstart.md`
- `specs/008-multi-project-workspace/quickstart.md`
- `specs/010-v2-documentation/quickstart.md`

**Update Required**: All quickstart guides showing indexing examples must use background pattern

**Priority**: **HIGH** - Users follow these for validation

---

### 🟡 MEDIUM PRIORITY - Developer Documentation (25 files)

Should be updated for correctness, but not user-facing.

#### Architecture & Design Docs (6 files)

1. `/Users/cliffclarke/Claude_Code/codebase-mcp/docs/architecture/ARCHITECTURE.md`
   - Update system architecture diagrams
   - Document background job flow
   - **Lines**: Grep for `index_repository`

2. `/Users/cliffclarke/Claude_Code/codebase-mcp/docs/architecture/AUTO_SWITCH.md`
   - Auto-switching documentation
   - May reference indexing behavior

3. `/Users/cliffclarke/Claude_Code/codebase-mcp/docs/architecture/background-indexing.md`
   - **CRITICAL**: This file should already document background indexing
   - May still reference foreground fallback
   - **Update**: Remove any foreground fallback mentions

4. `/Users/cliffclarke/Claude_Code/codebase-mcp/docs/architecture/multi-project-design.md`
   - Multi-project architecture
   - Indexing per project

5. `/Users/cliffclarke/Claude_Code/codebase-mcp/docs/architecture/api.md`
   - API design documentation

6. `/Users/cliffclarke/Claude_Code/codebase-mcp/docs/architecture/logging.md`
   - May reference indexing logs

---

#### Spec Files - Feature 014 (Background Indexing) (4 files)

**IMPORTANT**: These document the background indexing feature itself. May reference foreground for comparison.

1. `specs/014-add-background-indexing/plan.md`
   - Implementation plan for background indexing
   - **Action**: Update to note foreground removal
   - **Lines**: Search for migration notes

2. `specs/014-add-background-indexing/research.md`
   - Technical research
   - May compare foreground vs background

3. `specs/014-add-background-indexing/tasks.md`
   - Implementation tasks
   - May reference foreground removal task

4. `specs/014-add-background-indexing/data-model.md`
   - Data models for background jobs

---

#### Other Spec Files (15 files)

All spec files in `specs/001-011` that reference indexing:
- Update examples to background pattern
- Add migration notes where relevant
- Lower priority since these are historical

**Files**:
- `specs/001-build-a-production/plan.md`
- `specs/001-build-a-production/research.md`
- `specs/001-build-a-production/tasks.md`
- `specs/002-refactor-mcp-server/plan.md`
- `specs/002-refactor-mcp-server/spec.md`
- `specs/002-refactor-mcp-server/tasks.md`
- `specs/002-refactor-mcp-server/data-model.md`
- `specs/007-remove-non-search/*` (5 files)
- `specs/008-multi-project-workspace/*` (4 files)
- `specs/010-v2-documentation/*` (6 files)
- `specs/011-performance-validation-multi/research.md`

---

### ⚪ LOW PRIORITY - Archive & Historical Docs (121 files)

Historical documentation, session artifacts, old planning docs. Update only if time permits.

#### Bug Investigation Docs (13 files)
- `docs/bugs/mcp-indexing-failures/*.md` (13 files)
  - Historical bug investigation
  - Keep for reference, add deprecation note at top

#### Session Artifacts (20+ files)
- `docs/archive/session-artifacts/2025-10-06/*.md`
- `docs/mcp-split-plan/phases/**/*.md`
  - Historical session notes
  - Add deprecation note, don't update content

#### Planning Archives (50+ files)
- `docs/mcp-split-plan/_archive/**/*.md`
- Old implementation roadmaps
- Refactoring plans
  - Add "ARCHIVED" note at top
  - Don't update content (historical record)

#### Other Specs (30+ files)
- `specs/003-database-backed-project/*`
- `specs/004-as-an-ai/*`
- `specs/005-create-vendor/*`
- `specs/006-database-schema-refactoring/*`
- `specs/009-v2-connection-mgmt/*`
- `specs/013-config-based-project-tracking/*`
  - Update only if actively referenced elsewhere

---

## Migration Guide Content

Create new file: `/Users/cliffclarke/Claude_Code/codebase-mcp/docs/migration/foreground-to-background-indexing.md`

```markdown
# Migration Guide: Foreground to Background Indexing

**Effective**: codebase-mcp v2.1+
**Breaking Change**: Foreground `index_repository` tool removed

## What Changed

**Removed**:
- `index_repository` MCP tool (synchronous indexing)

**Added**:
- `start_indexing_background` - Start async indexing job
- `get_indexing_status` - Query job status and progress

**Why**: MCP clients have 30-second timeout limits. Large repositories
(10,000+ files) take 5-10 minutes to index, causing timeout errors.

## Migration Steps

### Step 1: Update Your Code

**Old Pattern (v2.0)**:
```python
result = index_repository(
    repo_path="/path/to/repo",
    project_id="my-project",
    force_reindex=False
)
print(f"Indexed {result['files_indexed']} files")
```

**New Pattern (v2.1+)**:
```python
# Start background job
job = start_indexing_background(
    repo_path="/path/to/repo",
    project_id="my-project",
    force_reindex=False
)
job_id = job["job_id"]

# Poll for completion (every 2-5 seconds)
import time
while True:
    status = get_indexing_status(job_id=job_id)

    # Check if done
    if status["status"] in ["completed", "failed"]:
        break

    # Show progress
    print(f"Progress: {status['files_indexed']} files, "
          f"{status['chunks_created']} chunks")

    time.sleep(2)

# Handle result
if status["status"] == "completed":
    print(f"✅ Success: {status['files_indexed']} files in "
          f"{status['duration_seconds']}s")
else:
    print(f"❌ Failed: {status['error_message']}")
```

### Step 2: Handle Timeouts Gracefully

Background jobs may take minutes. Add timeout handling:

```python
import time

job = start_indexing_background(repo_path="/path")
job_id = job["job_id"]

# Poll with timeout (5 minutes max)
timeout = 300  # seconds
start_time = time.time()

while True:
    # Check timeout
    if time.time() - start_time > timeout:
        print("⏱️ Indexing still running. Job ID:", job_id)
        print("Check status later with: get_indexing_status(job_id='...')")
        break

    # Poll status
    status = get_indexing_status(job_id=job_id)
    if status["status"] in ["completed", "failed"]:
        break

    time.sleep(2)
```

### Step 3: Add Error Handling

```python
try:
    job = start_indexing_background(repo_path="/path")
    job_id = job["job_id"]
except Exception as e:
    print(f"Failed to start indexing: {e}")
    return

# Poll with error handling
while True:
    try:
        status = get_indexing_status(job_id=job_id)
    except Exception as e:
        print(f"Failed to get status: {e}")
        break

    if status["status"] == "failed":
        print(f"Indexing failed: {status['error_message']}")
        break
    elif status["status"] == "completed":
        print(f"Success: {status['files_indexed']} files")
        break

    time.sleep(2)
```

## Frequently Asked Questions

### Q: Why was foreground indexing removed?

**A**: MCP protocol has 30-second timeout limit. Large repositories take
5-10 minutes to index, causing timeout errors and failed operations.
Background indexing solves this by returning immediately and allowing
clients to poll for progress.

### Q: What if I only have small repositories (<5,000 files)?

**A**: You still must use background indexing. The foreground tool is
completely removed. However, small repositories complete in <60 seconds,
so polling is brief.

### Q: Can I check job status later?

**A**: Yes! Save the `job_id` and call `get_indexing_status(job_id="...")`
anytime, even after server restart. Job status persists in PostgreSQL.

### Q: What happens if the server crashes during indexing?

**A**: Background jobs checkpoint progress every 500 files or 30 seconds.
After restart, check job status - it will show as "failed" with checkpoint
data. Resume is not automatic (future feature).

### Q: How many concurrent jobs can I run?

**A**: Maximum 3 concurrent indexing jobs per server. Additional jobs queue
automatically. Check job status - "pending" means queued, "running" means
active.

### Q: How do I cancel a running job?

**A**: Currently not implemented. Jobs run to completion or failure. Future
release will add `cancel_indexing_background(job_id="...")` tool.

## Troubleshooting

### Job stuck in "pending" status

**Cause**: Maximum concurrent jobs (3) already running.

**Solution**: Wait for other jobs to complete, or check their status:
```python
# List all jobs (implement if available)
all_jobs = list_indexing_jobs()
running = [j for j in all_jobs if j["status"] == "running"]
print(f"{len(running)} jobs currently running")
```

### Job failed with "database error"

**Cause**: PostgreSQL connection issue or permission error.

**Solution**: Check PostgreSQL logs and connection:
```bash
psql -h localhost -d codebase_mcp -c "SELECT 1"
tail -f /tmp/codebase-mcp.log | grep ERROR
```

### Poll loop never completes

**Cause**: Job may be hung or extremely large repository.

**Solution**: Check logs for errors, verify job is progressing:
```python
# Poll with progress check
last_progress = 0
stall_count = 0

while True:
    status = get_indexing_status(job_id=job_id)

    current_progress = status['files_indexed']
    if current_progress == last_progress:
        stall_count += 1
        if stall_count > 10:  # Stalled for 20 seconds
            print("⚠️ Job appears stalled. Check logs.")
            break
    else:
        stall_count = 0

    last_progress = current_progress
    time.sleep(2)
```

## Rollback

If you need to rollback to v2.0 with foreground indexing:

```bash
git checkout tags/v2.0
uv sync
# Restart MCP server
```

**Warning**: Background jobs from v2.1+ will not be accessible in v2.0.

## Support

- **Issues**: https://github.com/codebase-mcp/issues
- **Docs**: `/docs/architecture/background-indexing.md`
- **Spec**: `/specs/014-add-background-indexing/spec.md`
```

---

## Implementation Checklist

### Phase 1: Critical User-Facing Docs (Week 1)
- [ ] Update README.md (examples, tool list, breaking change note)
- [ ] Update CLAUDE.md (agent guidance, indexing workflow)
- [ ] Update SESSION_HANDOFF_MCP_TESTING.md (test procedures)
- [ ] Update docs/api/tool-reference.md (API docs, migration guide)
- [ ] Update docs/guides/TOOL_EXAMPLES.md (code examples)
- [ ] Create docs/migration/foreground-to-background-indexing.md (migration guide)

### Phase 2: High-Priority Operations Docs (Week 1-2)
- [ ] Update docs/guides/SETUP_GUIDE.md
- [ ] Update docs/operations/MCP-SERVER-DEPLOYMENT.md
- [ ] Update docs/operations/QUICK-RESTART-GUIDE.md
- [ ] Update docs/operations/README-DEPLOYMENT.md
- [ ] Update docs/operations/troubleshooting.md
- [ ] Update all quickstart.md files (5 files)

### Phase 3: Medium-Priority Developer Docs (Week 2)
- [ ] Update docs/architecture/ARCHITECTURE.md
- [ ] Update docs/architecture/background-indexing.md (remove foreground fallback)
- [ ] Update docs/architecture/AUTO_SWITCH.md
- [ ] Update docs/architecture/multi-project-design.md
- [ ] Update specs/014-add-background-indexing/*.md (4 files)
- [ ] Update other active spec files (10 files)

### Phase 4: Low-Priority Archives (Week 3 - Optional)
- [ ] Add deprecation notes to bug investigation docs (13 files)
- [ ] Add ARCHIVED notes to session artifacts (20+ files)
- [ ] Add ARCHIVED notes to planning archives (50+ files)
- [ ] Review old spec files for active references (30+ files)

### Phase 5: Code Cleanup (Separate Task)
- [ ] Remove `index_repository` tool implementation
- [ ] Remove foreground indexing tests
- [ ] Update integration tests to background pattern
- [ ] Update type hints and docstrings
- [ ] Run full test suite

### Phase 6: Validation (Week 3)
- [ ] Grep for remaining `index_repository` references
- [ ] Test all code examples in updated docs
- [ ] Validate migration guide with real users
- [ ] Update CHANGELOG.md with breaking change
- [ ] Tag release: v2.1.0-beta

---

## Success Metrics

**Documentation Complete When**:
1. ✅ Zero references to `index_repository` in user-facing docs (HIGH priority)
2. ✅ All code examples use background pattern
3. ✅ Migration guide tested by 3+ users
4. ✅ All quickstart guides validated
5. ✅ Tool reference docs complete for 3 background tools
6. ✅ CLAUDE.md updated for agent guidance

**Code Complete When**:
1. ✅ `index_repository` tool removed from codebase
2. ✅ All tests use background pattern
3. ✅ Integration tests pass
4. ✅ Zero `grep -r "index_repository"` matches in `src/`

---

## Risk Assessment

### High Risk
- **README.md outdated**: First file users see, critical for adoption
- **CLAUDE.md outdated**: Agent will use wrong pattern, cause errors
- **API docs outdated**: Developers will implement wrong pattern

### Medium Risk
- **Quickstart guides outdated**: New users will fail validation
- **Operations guides outdated**: Ops team troubleshooting will be incorrect

### Low Risk
- **Archive docs outdated**: Historical reference, minimal impact
- **Old spec files outdated**: Not actively used

---

## Notes

- **Total files to update**: 40 (15 high + 25 medium priority)
- **Estimated effort**: 2-3 weeks (1 week for critical, 1 week for medium, 1 week for validation)
- **Breaking change**: Requires semver MAJOR version bump (v2.0 → v3.0) or MINOR with deprecation period
- **Recommendation**: Ship as v2.1.0-beta, validate migration guide with users, then v2.1.0 stable

---

## Appendix: Full File List

### Files with `index_repository` references (161 markdown files)

High Priority: 15 files (listed in detail above)

Medium Priority: 25 files
- Architecture docs: 6 files
- Spec 014 files: 4 files
- Other spec files: 15 files

Low Priority: 121 files
- Bug investigation: 13 files
- Session artifacts: 20+ files
- Planning archives: 50+ files
- Old specs: 30+ files
- Misc: 8 files

Total Python files with references: ~50 (separate cleanup task)

---

**END OF PLAN**
