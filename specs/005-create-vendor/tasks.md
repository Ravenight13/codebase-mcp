# Tasks: Create Vendor MCP Function

**Feature**: 005-create-vendor
**Input**: Design documents from `/specs/005-create-vendor/`
**Prerequisites**: plan.md, research.md, data-model.md, contracts/create_vendor.yml

## Execution Overview

This task breakdown implements the `create_vendor()` MCP tool following TDD principles. The implementation adds:
- Database migration for case-insensitive uniqueness (functional unique index)
- New service function `create_vendor()` with enhanced exception handling
- New MCP tool `create_vendor()` with FastMCP decorator
- Comprehensive validation for vendor names and metadata
- Integration with existing vendor tracking workflow

**Tech Stack**: Python 3.11+, PostgreSQL 14+, FastMCP, SQLAlchemy 2.0, Pydantic
**Performance Target**: <100ms p95 latency

## Phase 3.1: Setup and Database Migration

- [ ] T001 Create database migration for case-insensitive vendor name uniqueness in `alembic/versions/005_case_insensitive_vendor_name.py`
  - Drop existing `vendor_extractors_name_key` unique constraint
  - Create functional unique index `idx_vendor_name_lower` on `LOWER(name)`
  - Add migration test to verify index enforcement
  - **Dependencies**: None
  - **Notes**: Critical for FR-012 case-insensitive uniqueness requirement

- [ ] T002 Run database migration and verify functional unique index
  - Execute `alembic upgrade head`
  - Verify index exists: `SELECT indexname FROM pg_indexes WHERE tablename='vendor_extractors'`
  - Test case-insensitive uniqueness with manual INSERT attempts
  - **Dependencies**: T001
  - **Notes**: Must complete before any other tasks can test duplicate detection

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3

**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

- [ ] T003 [P] Contract test for create_vendor MCP tool input/output schema in `tests/contract/test_create_vendor_contract.py`
  - Test valid CreateVendorRequest validation (name, initial_metadata, created_by)
  - Test invalid name formats (empty, too long, invalid characters)
  - Test invalid metadata types (scaffolder_version as int, invalid created_at ISO 8601)
  - Test CreateVendorResponse schema validation (all required fields, correct types)
  - Validate status always "broken", version always 1, extractor_version "0.0.0"
  - **Dependencies**: None (can run in parallel)
  - **Expected**: Tests FAIL (Pydantic models not yet created)

- [ ] T004 [P] Integration test for create_vendor success scenarios in `tests/integration/test_create_vendor_integration.py`
  - Scenario 1: Create vendor with full metadata (scaffolder_version, created_at, custom_field)
  - Scenario 2: Create vendor with partial metadata (scaffolder_version only)
  - Scenario 3: Create vendor with no metadata (empty dict)
  - Scenario 6: Immediate query after creation (verify queryable)
  - **Dependencies**: None (can run in parallel with T003, T005)
  - **Expected**: Tests FAIL (create_vendor() tool not implemented)

- [ ] T005 [P] Integration test for create_vendor error scenarios in `tests/integration/test_create_vendor_integration.py`
  - Scenario 4: Duplicate vendor error (exact name match)
  - Scenario 5: Duplicate vendor error (case-insensitive match: "newcorp" vs "NewCorp")
  - Scenario 7: Invalid name validation (empty string)
  - Scenario 8: Invalid name validation (too long >100 chars)
  - Scenario 9: Invalid name validation (invalid characters: @, !, #, $, %)
  - Scenario 10: Invalid metadata type (scaffolder_version as integer)
  - Scenario 11: Invalid metadata format (created_at not ISO 8601)
  - Scenario 12: Concurrent creation attempts (verify only one succeeds)
  - **Dependencies**: None (can run in parallel with T003, T004)
  - **Expected**: Tests FAIL (validation logic not implemented)

- [ ] T006 [P] Performance test for create_vendor latency in `tests/integration/test_create_vendor_performance.py`
  - Create 100 vendors with unique names
  - Measure latency for each operation
  - Calculate p50, p95, p99 percentiles
  - Assert p95 < 100ms (FR-015 requirement)
  - **Dependencies**: None (can run in parallel with T003-T005)
  - **Expected**: Tests FAIL (create_vendor() tool not implemented)

- [ ] T007 [P] End-to-end vendor workflow integration test in `tests/integration/test_vendor_workflow_integration.py`
  - Full lifecycle: create (broken) → query → update (operational) → query
  - Verify version increments from 1 to 2 on update
  - Verify metadata persistence across operations
  - Verify status transition from "broken" to "operational"
  - **Dependencies**: None (can run in parallel with T003-T006)
  - **Expected**: Tests FAIL (create_vendor() tool not implemented)

## Phase 3.3: Core Implementation (ONLY after tests are failing)

**Prerequisites**: All tests in Phase 3.2 must be written and failing

- [ ] T008 [P] Create VendorAlreadyExistsError exception class in `src/services/vendor.py`
  - Add `vendor_name` and `existing_name` fields
  - Implement enhanced error message: "Vendor already exists: {vendor_name} (conflicts with existing '{existing_name}')"
  - Implement `to_dict()` method with HTTP 409 status
  - **Dependencies**: T001-T007 (tests must be written first)
  - **Notes**: Exception used by create_vendor() service function

- [ ] T009 [P] Create vendor name validation function in `src/services/validation.py`
  - Implement `validate_vendor_name(name: str) -> None`
  - Validate not empty or whitespace-only
  - Validate length 1-100 characters
  - Validate regex pattern: `^[a-zA-Z0-9 \-_]+$`
  - Raise ValueError with descriptive messages
  - **Dependencies**: T001-T007 (tests must be written first)
  - **Notes**: Used by create_vendor() tool before service call

- [ ] T010 [P] Create vendor metadata validation function in `src/services/validation.py`
  - Implement `validate_create_vendor_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]`
  - Validate scaffolder_version is string if present
  - Validate created_at is ISO 8601 string if present (use `datetime.fromisoformat()`)
  - Pass through unknown fields without validation (flexible schema)
  - Return validated/merged metadata dict
  - **Dependencies**: T001-T007 (tests must be written first)
  - **Notes**: Flexible schema per clarification session requirements

- [ ] T011 Implement create_vendor() service function in `src/services/vendor.py`
  - Signature: `async def create_vendor(name: str, initial_metadata: dict[str, Any] | None, created_by: str, session: AsyncSession) -> VendorExtractor`
  - Create VendorExtractor instance with initial values (status="broken", version=1, extractor_version="0.0.0")
  - Add to session and flush to trigger functional unique index check
  - Catch IntegrityError → Query existing vendor name → Raise VendorAlreadyExistsError with existing_name
  - Return created VendorExtractor instance
  - **Dependencies**: T008, T009, T010 (exception and validation functions)
  - **Notes**: Core service logic with enhanced duplicate detection

- [ ] T012 Implement create_vendor() MCP tool function in `src/mcp/tools/tracking.py`
  - Add `@mcp.tool()` decorator with docstring matching contract
  - Signature: `async def create_vendor(name: str, initial_metadata: dict[str, Any] | None = None, created_by: str = "claude-code", ctx: Context | None = None) -> dict[str, Any]`
  - Call `validate_vendor_name(name)` first (fail-fast)
  - Call `validate_create_vendor_metadata(initial_metadata)` if provided
  - Invoke `create_vendor()` service function within database session
  - Convert VendorAlreadyExistsError to ValueError for MCP protocol compliance
  - Dual logging: `ctx.info()` for MCP client + `logger.info()` for file logs
  - Return response dict matching CreateVendorResponse schema
  - **Dependencies**: T011 (service function must be implemented)
  - **Notes**: FastMCP decorator pattern per existing tools

## Phase 3.4: Integration and Error Handling

- [ ] T013 Add structured logging for create_vendor operations in `src/mcp/tools/tracking.py`
  - Log vendor creation attempts with `logger.info("Creating vendor", extra={"vendor_name": name, "created_by": created_by})`
  - Log successful creations with vendor ID and metadata summary
  - Log validation errors with specific validation failure details
  - Log duplicate detection with both attempted and existing vendor names
  - **Dependencies**: T012 (tool implementation)
  - **Notes**: Supports debugging and audit trail

- [ ] T014 Update MCP tool registration to include create_vendor in `src/mcp/server.py`
  - Verify FastMCP auto-discovers `@mcp.tool()` decorated function
  - Test tool visibility via MCP client `tools/list` request
  - Validate tool schema matches contract/create_vendor.yml
  - **Dependencies**: T012 (tool implementation)
  - **Notes**: FastMCP should auto-register, just verify

## Phase 3.5: Polish and Documentation

- [ ] T015 [P] Add unit tests for vendor name validation in `tests/unit/test_vendor_validation.py`
  - Test empty string raises ValueError
  - Test whitespace-only string raises ValueError
  - Test name too short (0 chars) raises ValueError
  - Test name too long (101 chars) raises ValueError
  - Test valid characters (alphanumeric, spaces, hyphens, underscores) pass
  - Test invalid characters (@, !, #, $, %, etc.) raise ValueError
  - **Dependencies**: T009 (validation function implemented)
  - **Notes**: Comprehensive edge case coverage

- [ ] T016 [P] Add unit tests for vendor metadata validation in `tests/unit/test_vendor_validation.py`
  - Test None input returns empty dict
  - Test empty dict input returns empty dict
  - Test valid scaffolder_version passes through
  - Test invalid scaffolder_version type (int) raises ValueError
  - Test valid created_at ISO 8601 passes through
  - Test invalid created_at format raises ValueError
  - Test unknown fields pass through without validation
  - Test mixed known and unknown fields
  - **Dependencies**: T010 (validation function implemented)
  - **Notes**: Flexible schema validation coverage

- [ ] T017 [P] Update CHANGELOG.md with Feature 005 summary
  - Add entry under "## [Unreleased]" section
  - Document new create_vendor() MCP tool
  - Document database migration for case-insensitive uniqueness
  - Document new VendorAlreadyExistsError exception
  - Note performance characteristics (<100ms p95)
  - **Dependencies**: T001-T016 (implementation complete)
  - **Notes**: User-facing feature announcement

- [ ] T018 Run full test suite and verify all tests pass
  - Execute `pytest tests/contract/test_create_vendor_contract.py -v`
  - Execute `pytest tests/integration/test_create_vendor_integration.py -v`
  - Execute `pytest tests/integration/test_create_vendor_performance.py -v`
  - Execute `pytest tests/integration/test_vendor_workflow_integration.py -v`
  - Execute `pytest tests/unit/test_vendor_validation.py -v`
  - Verify all 12 integration scenarios pass
  - Verify p95 latency < 100ms
  - **Dependencies**: T001-T017 (all implementation complete)
  - **Notes**: Final validation gate before feature completion

- [ ] T019 Run mypy type checking with --strict mode
  - Execute `mypy src/services/vendor.py src/services/validation.py src/mcp/tools/tracking.py --strict`
  - Fix any type errors (should be zero with proper annotations)
  - Verify return types match Pydantic schemas
  - **Dependencies**: T001-T018 (implementation complete)
  - **Notes**: Principle VIII compliance (Pydantic-Based Type Safety)

## Dependencies Graph

```
T001 (Migration)
  ↓
T002 (Run Migration)
  ↓
T003-T007 (Tests - Parallel) ← Must FAIL before implementation
  ↓
T008-T010 (Exceptions + Validation - Parallel)
  ↓
T011 (Service Function)
  ↓
T012 (MCP Tool)
  ↓
T013-T014 (Integration + Registration)
  ↓
T015-T019 (Polish - Parallel where applicable)
```

## Parallel Execution Examples

### Phase 3.2 (Tests First)
```bash
# Launch T003-T007 together (all independent, different files):
pytest tests/contract/test_create_vendor_contract.py -v &
pytest tests/integration/test_create_vendor_integration.py::test_create_vendor_success -v &
pytest tests/integration/test_create_vendor_integration.py::test_create_vendor_errors -v &
pytest tests/integration/test_create_vendor_performance.py -v &
pytest tests/integration/test_vendor_workflow_integration.py -v &
wait
# Expected: All tests FAIL (implementation not yet done)
```

### Phase 3.3 (Core Implementation - Parallel Setup)
```bash
# Launch T008-T010 together (all independent, different functions):
# Task: "Create VendorAlreadyExistsError in src/services/vendor.py"
# Task: "Create validate_vendor_name in src/services/validation.py"
# Task: "Create validate_create_vendor_metadata in src/services/validation.py"
# Note: T009 and T010 are same file, so NOT truly parallel - T010 waits for T009
```

### Phase 3.5 (Polish - Parallel Documentation)
```bash
# Launch T015-T017 together (all independent):
pytest tests/unit/test_vendor_validation.py::test_name_validation -v &
pytest tests/unit/test_vendor_validation.py::test_metadata_validation -v &
# Edit CHANGELOG.md (T017) while tests run
```

## Task Completion Checklist

After completing all tasks, verify:

- [x] Database migration applied (functional unique index on LOWER(name))
- [x] All 12 quickstart scenarios pass
- [x] Contract tests validate Pydantic schemas
- [x] Integration tests cover success and error paths
- [x] Performance tests show p95 < 100ms
- [x] Unit tests cover validation edge cases
- [x] mypy --strict passes with zero errors
- [x] Structured logging in place for all operations
- [x] Error messages include case-sensitivity conflict details
- [x] create_vendor() tool visible in MCP tools/list
- [x] CHANGELOG.md updated with feature summary

## Notes

- **TDD Approach**: Tests (T003-T007) MUST be written and failing before implementation (T008-T012)
- **Migration First**: T001-T002 are critical prerequisites for duplicate detection tests
- **Parallel Constraints**: T009 and T010 are same file (`validation.py`), so T010 must wait for T009 despite [P] marking
- **Performance Validation**: T006 and T018 verify <100ms p95 latency requirement (FR-015)
- **Constitutional Compliance**:
  - Principle III: FastMCP @mcp.tool() decorator (no stdout/stderr pollution)
  - Principle V: Comprehensive validation, error handling, structured logging
  - Principle VIII: Pydantic models for request/response, mypy --strict
  - Principle X: Micro-commits after each task (T001, T002, T003-T007, T008, etc.)
- **Git Workflow**: Commit after each completed task with conventional commit messages
  - Example: `feat(vendor): add database migration for case-insensitive vendor names`
  - Example: `test(vendor): add contract tests for create_vendor MCP tool`
  - Example: `feat(vendor): implement create_vendor service function`

## Validation Rules (Per Template)

- [x] All contracts have corresponding tests (T003 covers create_vendor.yml)
- [x] All entities have model tasks (VendorExtractor already exists, T008 adds exception)
- [x] All tests come before implementation (T003-T007 before T008-T012)
- [x] Parallel tasks truly independent (T003-T007 all different files; T015-T017 independent)
- [x] Each task specifies exact file path (all tasks include file paths)
- [x] No task modifies same file as another [P] task (T009/T010 conflict noted in dependencies)
