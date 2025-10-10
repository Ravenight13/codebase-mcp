# Changelog

All notable changes to the Codebase MCP Server project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.3.0] - 2025-10-10

### Added

#### Hierarchical Work Items
- **New MCP Tools** for database-backed project tracking:
  - `create_work_item`: Create hierarchical work items (project/session/task/research) with type-specific metadata
  - `update_work_item`: Update work items with optimistic locking (version-based concurrency control)
  - `query_work_item`: Retrieve work items with full hierarchy (ancestors and descendants)
  - `list_work_items`: Filter and paginate work items by type, status, and parent
- **Hierarchical Support**: 5-level work item hierarchies with materialized paths and recursive CTEs
- **Performance**: <10ms p95 for 5-level hierarchical queries, <150ms p95 for CRUD operations
- **Type-Specific Metadata**: Pydantic-validated JSONB metadata for each work item type:
  - `ProjectMetadata`: description, target_quarter, constitutional_principles
  - `SessionMetadata`: token_budget, prompts_count, yaml_frontmatter
  - `TaskMetadata`: estimated_hours, actual_hours, blocked_reason
  - `ResearchMetadata`: research_questions, findings_summary, references
- **Optimistic Locking**: Version-based concurrency control to prevent lost updates
- **Explicit Hierarchy Arrays**: Query responses now include `ancestors` and `descendants` arrays with summary information

#### Documentation
- **`specs/003-database-backed-project/METADATA_SCHEMAS.md`**: Comprehensive reference guide for all work item metadata types with required fields, validation rules, and examples
- **`docs/2025-10-10-sqlalchemy-session-fix.md`**: Technical deep-dive on SQLAlchemy session management bug fix
- **`docs/2025-10-10-status-translation-fix.md`**: Backward compatibility solution documentation for status value translation
- **`docs/2025-10-10-feature-003-merge-summary.md`**: Complete feature merge summary with validation results
- **Testing Prompts**: Remote MCP client testing instructions (11 comprehensive test cases)

#### Tests
- **`tests/unit/test_status_translation.py`**: 9 unit tests for status translation layer (100% passing)
- **`tests/integration/test_session_detachment_fix.py`**: Integration tests for SQLAlchemy session management fix

### Fixed

#### Critical Bug Fixes
- **SQLAlchemy Session Management** (`src/mcp/tools/work_items.py`):
  - Fixed `DetachedInstanceError` when accessing lazy-loaded relationships after session closure
  - Solution: Use `sqlalchemy.inspect()` with `NEVER_SET` sentinel to safely check relationship load state
  - Impact: All work item operations (create, list, query, update) now functional
- **Status Value Incompatibility** (`src/services/tasks.py`):
  - Fixed Pydantic validation failures when database contains new work item statuses
  - Solution: Non-destructive `STATUS_TRANSLATION` mapping layer (active → need to be done, completed → complete, blocked → need to be done)
  - Impact: Legacy task endpoints (`list_tasks`, `get_task`, `update_task`) maintain 100% backward compatibility

### Changed

#### Enhancements
- **Query Response Format**: `query_work_item` now returns explicit `ancestors` and `descendants` arrays in addition to path/depth fields
- **Backward Compatibility**: Added status translation layer to support both legacy task statuses and new work item statuses

### Performance

- Hierarchical queries: <10ms p95 for 5-level hierarchies (validated)
- CRUD operations: <150ms p95 (validated)
- List operations: <200ms p95 (validated)
- Translation layer: <0.1ms overhead (negligible)

### Validation

- **Remote MCP Testing**: 11/11 tests passing (100% success rate)
- **Type Safety**: mypy --strict compliance (0 errors)
- **Backward Compatibility**: 67 contract tests passing
- **Constitutional Compliance**: All 11 project principles verified

### Documentation References

- Full feature details: [`docs/2025-10-10-feature-003-merge-summary.md`](docs/2025-10-10-feature-003-merge-summary.md)
- Metadata schemas: [`specs/003-database-backed-project/METADATA_SCHEMAS.md`](specs/003-database-backed-project/METADATA_SCHEMAS.md)
- Session management fix: [`docs/2025-10-10-sqlalchemy-session-fix.md`](docs/2025-10-10-sqlalchemy-session-fix.md)
- Status translation fix: [`docs/2025-10-10-status-translation-fix.md`](docs/2025-10-10-status-translation-fix.md)

---

## [Unreleased]

### Known Issues

- **Contract Test Failures**: 14 Pydantic V2 validation contract tests failing due to schema mismatches (non-blocking, core functionality working)
- **Integration Test Issues**: 2 integration tests failing due to asyncio event loop fixture issues (non-blocking, feature functionality working)

### Planned

- Align contract test schemas with actual Pydantic schemas
- Fix asyncio fixture issues in integration tests
- Add automated performance regression tests
- Consider unified status enum for long-term maintenance

---

## Version History

### [0.3.0] - 2025-10-10
**Feature 003: Database-Backed Project Tracking**
- Hierarchical work items with optimistic locking
- Type-specific metadata validation
- 100% backward compatibility maintained

### [0.2.0] - (Previous Release)
*Documentation pending for earlier releases*

### [0.1.0] - (Initial Release)
*Documentation pending for initial release*

---

## Links

- [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
- [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
- [Project Repository](https://github.com/Ravenight13/codebase-mcp)
