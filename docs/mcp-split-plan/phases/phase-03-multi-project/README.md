# Phase 03: Multi-Project Support

**Phase**: 03 - Multi-Project Support (Phase 7 from FINAL-IMPLEMENTATION-PLAN.md)
**Duration**: 6-8 hours
**Dependencies**: Phase 02 (tools removed, clean codebase)
**Status**: Planned

---

## Objective

Add `project_id` parameter to search and indexing tools, enabling multi-project workspace support with complete isolation.

**Key Feature**: Each project gets its own database (`codebase_<project_id>`)

---

## Scope

### What's Included

- **Tool Parameter Updates**
  - Add `project_id: str` parameter to `index_repository`
  - Add `project_id: str` parameter to `search_code`
  - Default value: `"default"` (backward compatibility)
  - Validation: Pydantic model with regex `^[a-z0-9-]{1,50}$`

- **workflow-mcp Integration** (Optional)
  - Query workflow-mcp for active project
  - Use active project if no project_id provided
  - Graceful degradation if workflow-mcp unavailable

- **Database Per Project**
  - Create database `codebase_<project_id>` if not exists
  - Validate CREATEDB permission
  - Clear error messages for permission issues

- **Integration Tests**
  - Test multi-project isolation (no cross-contamination)
  - Test workflow-mcp integration (optional)
  - Test database creation with various project_ids

### What's NOT Included

- Connection pooling (that's Phase 04)
- Performance optimization (that's Phase 06)
- Production documentation (that's Phase 05)

---

## Key Deliverables

1. **Updated Tools**:
   - `src/codebase_mcp/tools/index_repository.py` - Added project_id parameter
   - `src/codebase_mcp/tools/search_code.py` - Added project_id parameter

2. **Project ID Validation**:
   - `src/codebase_mcp/models/project.py` - Pydantic model with validation

3. **workflow-mcp Integration**:
   - `src/codebase_mcp/integrations/workflow_mcp.py` - Optional integration
   - Error categorization (unavailable, timeout, invalid response)
   - Caching (1-minute TTL)

4. **Integration Tests**:
   - `tests/integration/test_multi_project.py` - Isolation tests
   - `tests/integration/test_workflow_integration.py` - workflow-mcp tests

---

## Acceptance Criteria

- [ ] `index_repository` accepts `project_id` parameter
- [ ] `search_code` accepts `project_id` parameter
- [ ] project_id validated: `^[a-z0-9-]{1,50}$` pattern
- [ ] Invalid project_ids rejected with clear error message
- [ ] Database created automatically: `codebase_<project_id>`
- [ ] CREATEDB permission validated with helpful error
- [ ] workflow-mcp integration working (optional)
- [ ] Graceful degradation if workflow-mcp unavailable
- [ ] Multi-project isolation test passes (no cross-contamination)
- [ ] SQL injection attempts blocked (test cases pass)
- [ ] All tests passing (including new integration tests)
- [ ] Git commit: "feat(multi-project): add project_id parameter to tools"

---

## Project ID Validation

### Validation Rules

```python
class ProjectID(BaseModel):
    value: str = Field(
        pattern=r'^[a-z0-9-]{1,50}$',
        description="Lowercase alphanumeric with hyphens, max 50 chars"
    )

    @validator('value')
    def validate_safe_project_id(cls, v):
        if v.startswith('-') or v.endswith('-'):
            raise ValueError("project_id cannot start or end with hyphen")
        if '--' in v:
            raise ValueError("project_id cannot contain consecutive hyphens")
        return v
```

### Valid Examples

- `default`
- `my-app`
- `commission-extraction`
- `project-2024`

### Invalid Examples

- `My-App` (uppercase)
- `my_app` (underscore)
- `my app` (space)
- `-myapp` (starts with hyphen)
- `my--app` (consecutive hyphens)
- `a` (too short? - actually valid, min is 1 char)

---

## workflow-mcp Integration

### Optional Integration Flow

1. Check if `project_id` parameter provided
2. If not provided, query workflow-mcp: `GET /active-project`
3. If workflow-mcp returns project, use that project_id
4. If workflow-mcp unavailable, use `"default"`
5. If workflow-mcp errors, log and use `"default"`

### Error Handling

```python
class WorkflowMCPStatus(Enum):
    SUCCESS = "success"
    NO_ACTIVE_PROJECT = "no_active_project"
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    INVALID_RESPONSE = "invalid_response"
```

### Caching

- Cache active project for 1 minute (reduce HTTP calls)
- Invalidate cache on error
- TTL configurable via environment variable

---

## Multi-Project Isolation Test

```python
async def test_multi_project_isolation():
    """Verify projects cannot see each other's data"""
    # Index repo in project-a
    await index_repository(
        project_id="project-a",
        repo_path="/tmp/test-repo"
    )

    # Search in project-b (different database)
    results = await search_code(
        project_id="project-b",
        query="function test"
    )

    # Should return no results (different database)
    assert len(results) == 0
```

---

## Rollback Procedure

```bash
# Undo multi-project changes
git checkout 002-refactor-pure-search
git reset --hard <commit-before-phase-03>

# Drop created databases (optional)
psql -c "SELECT datname FROM pg_database WHERE datname LIKE 'codebase_%';"
# Manually drop unwanted test databases
```

---

## Next Phase

After completing Phase 03:
- Verify multi-project isolation
- Verify workflow-mcp integration (optional)
- Navigate to `../phase-04-connection-mgmt/`
- Ready for production-grade connection pooling

---

## Related Documentation

- **Phase 7 details**: See `../../_archive/01-codebase-mcp/FINAL-IMPLEMENTATION-PLAN.md` lines 1982-2080
- **Critical Issue C1**: Database naming (resolved)
- **Critical Issue C2**: workflow-mcp error handling (resolved)
- **Integration architecture**: See `../../_archive/shared-architecture/00-architecture/connection-management.md`

---

**Status**: Planned
**Last Updated**: 2025-10-11
**Estimated Time**: 6-8 hours
