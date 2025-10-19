# Feature Request: Add force_reindex Parameter to MCP Indexing Tool

**Request ID**: FR-001
**Date**: 2025-10-19
**Status**: PROPOSED
**Priority**: MEDIUM
**Requested By**: User feedback during testing

---

## Summary

Add an optional `force_reindex` parameter to the `start_indexing_background()` MCP tool, allowing users to force a complete re-index of a repository even when no file changes are detected.

---

## Current Behavior

**Incremental Indexing Only**:
- The MCP tool always performs incremental indexing
- Checks file modification times against `last_indexed_at`
- Skips unchanged files (efficient but inflexible)
- No way to force a full re-index via MCP tool

**User Experience**:
```python
# This ALWAYS does incremental indexing
await start_indexing_background("/path/to/repo")

# If no changes: 0 files indexed (efficient but sometimes not desired)
```

**Workarounds Required**:
```sql
-- Option 1: Manual database deletion
DELETE FROM repositories WHERE path = '/path/to/repo';
```

```bash
# Option 2: Touch files to trigger incremental update
find /path/to/repo -name "*.py" -exec touch {} \;
```

```python
# Option 3: Direct service call (bypasses MCP)
from src.services.indexer import index_repository
await index_repository(repo_path, force_reindex=True)  # Not exposed via MCP
```

---

## Proposed Behavior

**Add Optional Parameter**:
```python
await start_indexing_background(
    repo_path="/path/to/repo",
    force_reindex=True  # NEW: Force full re-index
)
```

**Default**: `force_reindex=False` (maintains current incremental behavior)

**When True**:
- Ignores `last_indexed_at` timestamp
- Re-indexes ALL files regardless of modification time
- Generates fresh embeddings for all chunks
- Updates status_message: "Force reindex completed: N files, M chunks"

---

## Use Cases

### 1. Embedding Model Changed
**Scenario**: User switches from one Ollama model to another
```python
# After changing from nomic-embed-text to mxbai-embed-large
await start_indexing_background("/path/to/repo", force_reindex=True)
```
**Reason**: Old embeddings are incompatible with new model

### 2. Index Corruption Suspected
**Scenario**: Search returns poor results, suspect database corruption
```python
# Re-index everything to rebuild from scratch
await start_indexing_background("/path/to/repo", force_reindex=True)
```
**Reason**: Clean slate without manual database manipulation

### 3. Chunking Strategy Updated
**Scenario**: Changed AST parsing logic or chunk size configuration
```python
# Re-chunk all files with new strategy
await start_indexing_background("/path/to/repo", force_reindex=True)
```
**Reason**: Existing chunks don't reflect new chunking logic

### 4. Testing and Benchmarking
**Scenario**: Performance testing or benchmark validation
```python
# Ensure consistent full-index benchmarks
for model in ["nomic-embed-text", "mxbai-embed-large"]:
    configure_embedding_model(model)
    result = await start_indexing_background("/path/to/repo", force_reindex=True)
    measure_performance(result)
```
**Reason**: Need reproducible full-index operations

### 5. Migration Scenarios
**Scenario**: Upgrading codebase-mcp version with schema changes
```python
# After database schema migration
await start_indexing_background("/path/to/repo", force_reindex=True)
```
**Reason**: Ensure all data matches new schema format

---

## Implementation Plan

### 1. Update MCP Tool Signature

**File**: `src/mcp/tools/background_indexing.py`

```python
@mcp.tool()
async def start_indexing_background(
    repo_path: str,
    project_id: str | None = None,
    force_reindex: bool = False,  # NEW PARAMETER
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Start repository indexing in the background (non-blocking).

    Args:
        repo_path: Absolute path to repository (validated for path traversal)
        project_id: Optional project identifier (resolved via 4-tier chain)
        force_reindex: If True, re-index all files regardless of changes (default: False)
        ctx: FastMCP Context for session-based project resolution

    Returns:
        {
            "job_id": "uuid",
            "status": "pending",
            "message": "Indexing job started",
            "force_reindex": true,  # NEW: indicates mode
            "project_id": "resolved_project_id",
            "database_name": "cb_proj_xxx"
        }
    """
```

### 2. Update IndexingJob Model

**File**: `src/models/indexing_job.py`

```python
class IndexingJob(Base):
    # Existing fields...
    force_reindex: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)  # NEW
```

**Migration**: Add `force_reindex` column to `indexing_jobs` table

### 3. Pass Parameter to Worker

**File**: `src/mcp/tools/background_indexing.py`

```python
# Create job record with force_reindex flag
job = IndexingJob(
    repo_path=job_input.repo_path,
    project_id=resolved_id,
    status="pending",
    force_reindex=force_reindex,  # NEW: store flag in job
)

# Pass to worker
asyncio.create_task(
    _background_indexing_worker(
        job_id=job_id,
        repo_path=job_input.repo_path,
        project_id=resolved_id,
        config_path=config_path,
        force_reindex=force_reindex,  # NEW: pass to worker
    )
)
```

### 4. Update Background Worker

**File**: `src/services/background_worker.py`

```python
async def _background_indexing_worker(
    job_id: UUID,
    repo_path: str,
    project_id: str,
    config_path: Path | None,
    force_reindex: bool = False,  # NEW PARAMETER
) -> None:
    # ...
    result = await index_repository(
        repo_path=repo_path,
        database=database,
        force_reindex=force_reindex,  # NEW: pass through
    )

    # Update status_message based on force_reindex flag
    if force_reindex:
        status_message = f"Force reindex completed: {files_indexed} files, {chunks_created} chunks"
    elif files_indexed == 0:
        status_message = f"Repository up to date - no file changes detected..."
    # ... rest of logic
```

### 5. Update Status Messages

**New Message**: "Force reindex completed: N files, M chunks"

**Distinguish From**:
- "Full repository index completed: N files, M chunks" (new repo, first index)
- "Repository up to date - no file changes detected..." (incremental, no changes)
- "Incremental update completed: N files updated" (incremental, some changes)

---

## API Design

### MCP Tool Usage

**Default (incremental)**:
```python
result = await start_indexing_background("/path/to/repo")
# Uses incremental indexing (existing behavior)
```

**Force reindex**:
```python
result = await start_indexing_background(
    repo_path="/path/to/repo",
    force_reindex=True
)
# Forces complete re-index of all files
```

**Return Value**:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Indexing job started",
  "force_reindex": true,
  "project_id": "0d1eea82-e60f-4c96-9b69-b677c1f3686a",
  "database_name": "cb_proj_workflow_mcp_0d1eea82"
}
```

**Status After Completion**:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "status_message": "Force reindex completed: 351 files, 2321 chunks",
  "files_indexed": 351,
  "chunks_created": 2321,
  "force_reindex": true
}
```

---

## Performance Considerations

### Impact of Force Reindex

**Small Repository** (<100 files):
- Incremental: 1-5 seconds
- Force reindex: 10-30 seconds
- Impact: 5-10x slower (acceptable)

**Medium Repository** (100-1,000 files):
- Incremental: 5-30 seconds
- Force reindex: 1-5 minutes
- Impact: 5-10x slower (acceptable)

**Large Repository** (1,000-10,000 files):
- Incremental: 30-120 seconds
- Force reindex: 5-20 minutes
- Impact: 5-10x slower (acceptable with warning)

### Optimization Opportunities

1. **Parallel Processing**: Re-index files in parallel (already implemented)
2. **Batch Embeddings**: Send chunks in batches to Ollama (already implemented)
3. **Connection Pooling**: Reuse database connections (already implemented)
4. **Progress Reporting**: Real-time progress updates via `files_indexed` counter

### Warning for Large Repos

```python
# Before force reindex on large repo
if file_count > 1000 and force_reindex:
    logger.warning(
        f"Force reindex requested for large repository ({file_count} files). "
        f"This may take 10-20 minutes. Consider incremental indexing if only "
        f"some files changed."
    )
```

---

## Testing Strategy

### Unit Tests

```python
async def test_force_reindex_flag_stored():
    """Test that force_reindex flag is stored in job."""
    job = await start_indexing_background(
        repo_path="/path/to/repo",
        force_reindex=True
    )
    assert job["force_reindex"] is True

async def test_force_reindex_default_false():
    """Test that force_reindex defaults to False."""
    job = await start_indexing_background("/path/to/repo")
    assert job["force_reindex"] is False
```

### Integration Tests

```python
async def test_force_reindex_ignores_timestamps():
    """Test that force_reindex re-indexes all files."""
    # Initial index
    await index_repository(repo_path)

    # Force reindex (no file changes)
    result = await index_repository(repo_path, force_reindex=True)

    # Should re-index all files, not 0
    assert result.files_indexed > 0
    assert result.chunks_created > 0
```

### Performance Tests

```python
@pytest.mark.benchmark
async def test_force_reindex_performance():
    """Benchmark force reindex vs incremental."""
    # Measure force reindex
    start = time.time()
    await index_repository(repo_path, force_reindex=True)
    force_duration = time.time() - start

    # Measure incremental (no changes)
    start = time.time()
    await index_repository(repo_path, force_reindex=False)
    incremental_duration = time.time() - start

    # Force reindex should be slower but not excessively
    assert force_duration > incremental_duration
    assert force_duration / incremental_duration < 20  # <20x slower
```

---

## Migration Path

### Database Migration

```python
# migrations/versions/XXX_add_force_reindex_to_indexing_jobs.py

def upgrade():
    op.add_column(
        'indexing_jobs',
        sa.Column('force_reindex', sa.Boolean(), nullable=False, server_default='false')
    )

def downgrade():
    op.drop_column('indexing_jobs', 'force_reindex')
```

### Backward Compatibility

**Existing Jobs**: Jobs created before this feature will have `force_reindex=False` (default)

**Existing Callers**: Callers not passing `force_reindex` get incremental indexing (current behavior)

**API Compatibility**: Fully backward compatible - new optional parameter

---

## Documentation Updates

### 1. MCP Tool Docstring

Update `start_indexing_background()` docstring with:
- New `force_reindex` parameter description
- Use cases and examples
- Performance warnings for large repos

### 2. User Documentation

Add section to `docs/guides/indexing.md`:
```markdown
## Force Re-indexing

When to use force re-index:
- Changed embedding model
- Suspect index corruption
- Updated chunking strategy
- After database migration

Example:
```python
await start_indexing_background(
    repo_path="/path/to/repo",
    force_reindex=True
)
```

**Note**: Force re-index is slower than incremental. Only use when necessary.
```

### 3. CLAUDE.md Update

Add to background indexing section:
```markdown
### Force Re-indexing

Use `force_reindex=True` to re-index all files:
- Ignores modification timestamps
- Regenerates all embeddings
- Slower but ensures fresh index
```

---

## Constitutional Compliance

### Principle I: Simplicity Over Features
✅ **PASS** - Simple boolean flag, no complex configuration

### Principle IV: Performance Guarantees
✅ **PASS** - Documents performance impact, warns for large repos

### Principle V: Production Quality Standards
✅ **PASS** - Comprehensive error handling, logging, warnings

### Principle VII: Test-Driven Development
✅ **PASS** - Test strategy defined (unit, integration, performance)

### Principle VIII: Pydantic-Based Type Safety
✅ **PASS** - All new code uses type hints and Pydantic models

---

## Acceptance Criteria

- [ ] `force_reindex` parameter added to `start_indexing_background()`
- [ ] Default value is `False` (maintains current behavior)
- [ ] Parameter stored in `indexing_jobs` table
- [ ] Worker passes flag to `index_repository()`
- [ ] Status message distinguishes force reindex from full index
- [ ] Unit tests cover parameter handling
- [ ] Integration tests verify all files re-indexed
- [ ] Performance tests measure overhead
- [ ] Documentation updated (docstrings, guides, CLAUDE.md)
- [ ] Migration runs successfully
- [ ] Backward compatibility maintained

---

## Estimated Effort

**Implementation**: 2-3 hours
- Model changes: 30 minutes
- Migration: 15 minutes
- MCP tool: 30 minutes
- Worker: 30 minutes
- Status messages: 15 minutes
- Testing: 45 minutes
- Documentation: 30 minutes

**Testing**: 1 hour
- Unit tests: 20 minutes
- Integration tests: 30 minutes
- Manual verification: 10 minutes

**Total**: 3-4 hours

---

## Alternative Approaches Considered

### Alternative 1: Separate MCP Tool

Create `force_reindex_repository()` instead of adding parameter:
```python
await force_reindex_repository("/path/to/repo")
```

**Pros**: Clear intent, separate operation
**Cons**: Code duplication, two tools doing similar things
**Decision**: REJECTED - Parameter is simpler

### Alternative 2: Auto-detect Scenarios

Automatically detect when force reindex needed (model change, etc.):
```python
# Auto-detect and force reindex if needed
await start_indexing_background("/path/to/repo")
```

**Pros**: No user decision required
**Cons**: Complex detection logic, unpredictable behavior
**Decision**: REJECTED - Too much magic

### Alternative 3: Config File Setting

Add force reindex setting to `.codebase-mcp/config.json`:
```json
{
  "force_reindex": true
}
```

**Pros**: Persistent setting
**Cons**: Not per-operation, requires file edits
**Decision**: REJECTED - Less flexible than parameter

---

## Risk Assessment

### Low Risk
- Simple boolean parameter
- Existing `force_reindex` already implemented in service layer
- Backward compatible (optional parameter)
- Well-defined use cases

### Mitigation
- Comprehensive testing (unit, integration, performance)
- Clear documentation and warnings
- Default to `False` for safety

---

## Related Work

- **Bug Fix**: Status messages (just completed)
- **Existing Code**: `force_reindex` parameter already exists in `index_repository()` service
- **Related Feature**: Incremental indexing (current behavior)

---

## References

- **Service Implementation**: `src/services/indexer.py:498-653` (force_reindex logic)
- **MCP Tool**: `src/mcp/tools/background_indexing.py`
- **Background Worker**: `src/services/background_worker.py`
- **Constitutional Principles**: `.specify/memory/constitution.md`
