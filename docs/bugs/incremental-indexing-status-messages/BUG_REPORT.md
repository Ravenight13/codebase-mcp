# Bug Report: Missing Status Messages for Incremental Indexing

**Date**: 2025-10-19
**Severity**: MEDIUM (UX Issue)
**Status**: IDENTIFIED
**Branch**: `fix/project-resolution-auto-create`

---

## Summary

When incremental indexing detects no file changes, it returns `files_indexed: 0, chunks_created: 0` without any explanatory message. This appears as an undocumented error to users and AI assistants, when it's actually successful behavior.

---

## User Impact

**Current Behavior**:
```json
{
  "job_id": "1c8c2dd0-2851-4137-8660-71410bbced4b",
  "status": "completed",
  "files_indexed": 0,
  "chunks_created": 0,
  "error_message": null
}
```

**User Interpretation**: "Something failed! Zero files indexed!"
**Reality**: "Success! No changes detected since last index."

---

## Root Cause

**IndexingJob model** (`src/models/indexing_job.py`) has no `status_message` or `completion_message` field to explain the result. Only `error_message` exists for failures.

**Background worker** (`src/services/background_worker.py`) doesn't set descriptive success messages, only updates counters.

---

## Fix Required

### 1. Add `status_message` Field

**Model**: `src/models/indexing_job.py`
```python
class IndexingJob(Base):
    # Existing fields...
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    status_message: Mapped[str | None] = mapped_column(String, nullable=True)  # NEW
```

### 2. Set Descriptive Messages

**Worker**: `src/services/background_worker.py`

**Scenarios**:
- **No changes**: "No file changes detected since last index (351 files already indexed)"
- **Incremental**: "Indexed 23 new/modified files (5 new, 18 updated)"
- **Full index**: "Completed full repository index: 351 files, 2,321 chunks"
- **Force reindex**: "Force reindex completed: 351 files, 2,321 chunks"

### 3. Return Message in MCP Tool

**Tool**: `src/mcp/tools/background_indexing.py`
```python
return {
    "job_id": str(job.id),
    "status": job.status,
    "status_message": job.status_message,  # NEW
    "files_indexed": job.files_indexed,
    # ...
}
```

---

## Expected Behavior

**Incremental (no changes)**:
```json
{
  "status": "completed",
  "files_indexed": 0,
  "chunks_created": 0,
  "status_message": "Repository up to date - no file changes detected since last index (351 files already indexed)"
}
```

**Incremental (some changes)**:
```json
{
  "status": "completed",
  "files_indexed": 23,
  "chunks_created": 156,
  "status_message": "Incremental update completed: 23 files updated (5 new, 18 modified)"
}
```

**Full index**:
```json
{
  "status": "completed",
  "files_indexed": 351,
  "chunks_created": 2321,
  "status_message": "Full repository index completed"
}
```

---

## Implementation Tasks

- [ ] Add `status_message` column to `indexing_jobs` table (migration)
- [ ] Update `IndexingJob` model with new field
- [ ] Update background worker to set messages for all scenarios
- [ ] Update MCP tool to return `status_message`
- [ ] Add tests for status messages
- [ ] Update documentation

---

## Acceptance Criteria

- [ ] Incremental indexing (no changes) has clear success message
- [ ] Incremental indexing (changes) shows what was updated
- [ ] Full indexing has descriptive completion message
- [ ] Error scenarios still use `error_message` field
- [ ] MCP tool returns `status_message` in response
- [ ] Migration runs successfully

---

## Priority

**MEDIUM** - UX improvement, not a functional bug. System works correctly but confuses users.
