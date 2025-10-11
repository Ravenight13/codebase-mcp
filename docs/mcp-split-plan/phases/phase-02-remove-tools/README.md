# Phase 02: Remove Non-Search Tools

**Phase**: 02 - Remove Tools (Phases 3-6 from FINAL-IMPLEMENTATION-PLAN.md)
**Duration**: 8-12 hours
**Dependencies**: Phase 01 (database schema refactored)
**Status**: Planned

---

## Objective

Remove 14 non-search MCP tools and all supporting code, reducing codebase from ~4,500 to ~1,800 lines.

**Target State**: Only 2 MCP tools remain - `index_repository` and `search_code`

---

## Scope

### Tools to Remove (14 total)

**Work Item Management (6 tools)**:
1. `create_work_item`
2. `update_work_item`
3. `query_work_item`
4. `list_work_items`

**Task Management (4 tools)**:
5. `create_task`
6. `get_task`
7. `list_tasks`
8. `update_task`

**Vendor Management (3 tools)**:
9. `create_vendor`
10. `query_vendor_status`
11. `update_vendor_status`

**Other (1 tool)**:
12. `record_deployment`

**Config Management (2 tools)**:
13. `get_project_configuration`
14. `update_project_configuration`

### Code to Remove

- Tool implementation files (14 files in `src/codebase_mcp/tools/`)
- Database operation modules
- Pydantic models for removed features
- Tests for removed features (~30 test files)
- Server registration code

### Tools to KEEP (2 total)

- `index_repository` - Semantic code indexing
- `search_code` - Semantic code search

---

## Key Deliverables

1. **Cleaned Tool Directory**: Only 2 tool files remain
   - `src/codebase_mcp/tools/index_repository.py`
   - `src/codebase_mcp/tools/search_code.py`

2. **Updated Server**: `src/codebase_mcp/server.py`
   - Only registers 2 tools
   - Imports cleaned up

3. **Cleaned Tests**: `tests/`
   - Only search-related tests remain
   - ~30 test files removed

4. **Updated Dependencies**: `pyproject.toml`
   - Remove unused dependencies (if any)

---

## Acceptance Criteria

- [ ] Only 2 MCP tools registered in server
- [ ] 14 tool implementation files deleted
- [ ] Database operation files for removed features deleted
- [ ] Pydantic models for removed features deleted
- [ ] Tests for removed features deleted
- [ ] Server starts successfully
- [ ] Remaining tests pass (search tests only)
- [ ] `mypy --strict` passes
- [ ] Code reduction: ~4,500 → ~1,800 lines (60% reduction)
- [ ] Git commits: One per removed feature group (work_items, tasks, vendors, etc.)

---

## Execution Strategy

Execute in 4 sub-phases (Phases 3-6 from FINAL-IMPLEMENTATION-PLAN):

### Phase 3: Remove Tool Files
- Delete 14 tool implementation files
- Commit: "refactor(tools): remove non-search tool implementations"

### Phase 4: Remove Database Operations
- Delete database modules for removed features
- Commit: "refactor(database): remove non-search database operations"

### Phase 5: Remove Server Registration
- Update server.py to only register 2 tools
- Remove imports for deleted tools
- Commit: "refactor(server): register only search tools"

### Phase 6: Remove Tests
- Delete tests for removed features
- Verify remaining tests pass
- Commit: "refactor(tests): remove non-search feature tests"

---

## Rollback Procedure

```bash
# Undo all commits from this phase
git checkout 002-refactor-pure-search
git reset --hard <commit-before-phase-02>

# Or restore from backup
git checkout main
dropdb codebase_mcp
createdb codebase_mcp
psql -d codebase_mcp < backups/backup-before-002.sql
```

---

## Verification Commands

```bash
# Count MCP tools registered
grep -r "@mcp.tool" src/codebase_mcp/tools/ | wc -l
# Expected: 2

# Verify server starts
python -m codebase_mcp.server
# Should start without errors

# Run tests
pytest tests/
# All remaining tests should pass

# Type checking
mypy --strict src/
# Should pass with no errors

# Line count (approximate)
find src/ -name "*.py" -exec wc -l {} + | tail -1
# Expected: ~1,800 lines
```

---

## Next Phase

After completing Phase 02:
- Verify codebase reduction (60% fewer lines)
- Verify only 2 tools registered
- Navigate to `../phase-03-multi-project/`
- Clean codebase ready for multi-project feature

---

## Related Documentation

- **Phases 3-6 details**: See `../../_archive/01-codebase-mcp/FINAL-IMPLEMENTATION-PLAN.md` lines 1972-1981
- **Tool architecture**: See `../../_archive/01-codebase-mcp/tech-stack.md`
- **Code structure**: See `../../_archive/01-codebase-mcp/refactoring-plan.md`

---

**Status**: Planned
**Last Updated**: 2025-10-11
**Estimated Time**: 8-12 hours
