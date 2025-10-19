# Bug #015: Project Resolution Tier Fallthrough

**Status**: Identified
**Severity**: CRITICAL
**Date Reported**: 2025-10-19
**Branch**: `015-fix-project-resolution`

## Summary

Multiple critical bugs in the project resolution system cause:
- Wrong databases to be used for projects
- Config changes to be ignored
- Persistent stale project mappings
- Cross-contamination between codebase-mcp and workflow-mcp projects

## User Impact

Users report:
1. Database "does not exist" errors despite valid config
2. Config changes (project.id) being completely ignored
3. Projects mapping to wrong databases (workflow-mcp databases instead of codebase-mcp)
4. Mappings persisting across config changes and `set_working_directory()` calls

## Root Causes Identified

1. **Uncontrolled Fallthrough to workflow-mcp (Tier 3)**: System falls through to workflow-mcp even when config specifies a project
2. **Explicit ID Fallthrough (Tier 1)**: Continues searching instead of creating project when ID not found
3. **PostgreSQL Registry Not Updated**: Old project entries persist when config changes
4. **In-Memory Registry Caching**: Stale projects cached without invalidation
5. **Database Existence Not Validated**: No verification after provisioning attempt

## Evidence

Database name reported: `cb_proj_workflow_mcp_0d1eea82`
- Expected: `cb_proj_commission_processing_ve_<hash>`
- Actual: Contains "workflow_mcp" proving wrong project returned

## Files

- `analysis.md` - Detailed root cause analysis with code references
- `test-cases.md` - Test cases to verify fixes (TBD)
- `implementation-plan.md` - Fix implementation plan (TBD)

## Affected Components

- `src/database/session.py` - resolve_project_id() function
- `src/database/auto_create.py` - get_or_create_project_from_config()
- `src/database/provisioning.py` - create_project_database()
- `src/auto_switch/cache.py` - ConfigCache (working correctly)
- `src/mcp/tools/background_indexing.py` - start_indexing_background()

## Priority

**CRITICAL** - Causes data corruption and silent failures
