# MCP Enhancement Implementation Tasks

## Executive Summary

### Overview
- **Total Tasks**: 57 tasks across 3 phases
- **Estimated Timeline**: 8-10 days (single developer, sequential work)
- **Resource Requirements**: 1 senior Python developer with MCP/FastMCP experience
- **Constitutional Compliance**: All 11 principles validated for each enhancement

### Risk Summary
- **Low Risk**: Tool annotations (2 hours, quick win)
- **Low Risk**: Evaluation suite (1 day, isolated from production)
- **Medium Risk**: Response formatting (2-3 days, backward compatibility required)
- **Medium Risk**: Character limits (2-3 days, requires accurate size estimation)
- **High Risk**: Integration between formatting and truncation (requires careful coordination)

### Phasing Strategy
- **Phase 1 (Parallel)**: Tool annotations + Evaluation suite setup (2-3 days)
- **Phase 2 (Sequential)**: Response formats → Character limits (4-5 days)
- **Phase 3 (Integration)**: Cross-feature testing and validation (1-2 days)

### Key Dependencies
- Response format options must be completed before character limits (size estimation depends on format)
- Character limits must account for response format and detail level combinations
- Evaluation suite should validate all enhancements once complete

---

## Phase 1: Independent Tasks (Parallel Execution)

These tasks can be worked on simultaneously by different developers or sequentially by a single developer. No inter-task dependencies exist within this phase.

### Feature: Tool Annotations
**Estimated Time**: 0.5 days (4 hours)
**Priority**: High (quick win, immediate LLM optimization)
**Files Affected**: `src/mcp/tools/*.py`

#### T001: Audit tool implementations for behavior analysis
- Review `index_repository` in `src/services/indexer.py` and `src/mcp/tools/indexing.py`
- Review `search_code` in `src/services/searcher.py` and `src/mcp/tools/search.py`
- Review `set_working_directory` in `src/mcp/tools/project.py`
- Document actual behavior: filesystem access, database operations, state modifications
- **Files**: All tool implementation files
- **Dependencies**: None
- **Acceptance Criteria**: Behavior audit document created with rationale for each hint
- **Testing**: Manual code review, trace execution paths
- **Estimated Time**: 1 hour

#### T002: Add hints to index_repository tool
- Update `@mcp.tool()` decorator with `openWorldHint=True, readOnlyHint=False, idempotentHint=False`
- Add inline comments explaining each hint choice
- Update docstring to mention hint behavior
- **Files**: `src/mcp/tools/indexing.py`
- **Dependencies**: T001
- **Acceptance Criteria**: Hints applied, comments added, mypy --strict passes
- **Testing**: `mypy --strict src/mcp/tools/indexing.py`, server starts successfully
- **Estimated Time**: 30 minutes

#### T003: Add hints to search_code tool
- Update `@mcp.tool()` decorator with `openWorldHint=True, readOnlyHint=True, idempotentHint=True`
- Add inline comments explaining each hint choice
- Update docstring to mention hint behavior
- **Files**: `src/mcp/tools/search.py`
- **Dependencies**: T001
- **Acceptance Criteria**: Hints applied, comments added, mypy --strict passes
- **Testing**: `mypy --strict src/mcp/tools/search.py`, server starts successfully
- **Estimated Time**: 30 minutes

#### T004: Add hints to set_working_directory tool
- Update `@mcp.tool()` decorator with `openWorldHint=True, readOnlyHint=False, idempotentHint=True`
- Add inline comments explaining each hint choice
- Update docstring to mention hint behavior
- **Files**: `src/mcp/tools/project.py`
- **Dependencies**: T001
- **Acceptance Criteria**: Hints applied, comments added, mypy --strict passes
- **Testing**: `mypy --strict src/mcp/tools/project.py`, server starts successfully
- **Estimated Time**: 30 minutes

#### T005: Create hint validation integration tests
- Create `tests/integration/test_tool_hints.py`
- Test `index_repository` openWorld hint (verify filesystem/database interaction)
- Test `index_repository` readOnly=False (verify state modification)
- Test `index_repository` idempotent=False (verify behavior changes on repeated calls)
- Test `search_code` openWorld hint (verify database/Ollama interaction)
- Test `search_code` readOnly=True (verify no state changes)
- Test `search_code` idempotent=True (verify deterministic results)
- Test `set_working_directory` openWorld hint (verify session state modification)
- Test `set_working_directory` readOnly=False (verify state changes)
- Test `set_working_directory` idempotent=True (verify safe repeated calls)
- **Files**: `tests/integration/test_tool_hints.py`
- **Dependencies**: T002, T003, T004
- **Acceptance Criteria**: 9 tests pass, all hints validated against actual behavior
- **Testing**: `pytest tests/integration/test_tool_hints.py -v`
- **Estimated Time**: 1.5 hours

#### T006: Document tool hints in README
- Add "Tool Hints" section to README.md
- Document expected LLM behavior improvements (retry logic, parallel execution)
- Add troubleshooting guide for hint-related issues
- Include examples of LLM decision-making before/after hints
- **Files**: `README.md`
- **Dependencies**: T005
- **Acceptance Criteria**: Documentation complete, examples clear
- **Testing**: Manual documentation review
- **Estimated Time**: 30 minutes

---

### Feature: Evaluation Suite
**Estimated Time**: 1 day (8 hours)
**Priority**: High (quality validation foundation)
**Files Affected**: `evaluations/*` (new directory)

#### T007: Create evaluation directory structure
- Create `evaluations/` directory
- Create `evaluations/fixtures/test-codebase/` subdirectory
- Create `evaluations/README.md` with suite documentation
- Document XML schema, evaluation categories, and usage instructions
- **Files**: `evaluations/README.md`, directory structure
- **Dependencies**: None
- **Acceptance Criteria**: Directory structure validated, README complete
- **Testing**: Verify directory structure exists, README is comprehensive
- **Estimated Time**: 30 minutes

#### T008: Design and create test codebase fixture
- Design test codebase with authentication, database, and API modules
- Create 10-15 Python files in `evaluations/fixtures/test-codebase/src/`
- Add authentication module: `src/auth/login.py, logout.py, session.py`
- Add database module: `src/database/models.py, migrations.py, queries.py`
- Add API module: `src/api/routes.py, middleware.py, handlers.py`
- Add test files: `tests/test_auth.py, test_database.py, test_api.py`
- Ensure 100+ lines per file with semantic richness (docstrings, comments)
- **Files**: `evaluations/fixtures/test-codebase/**/*.py`
- **Dependencies**: T007
- **Acceptance Criteria**: 10-15 files created, realistic code patterns, 100+ lines each
- **Testing**: Index fixture with codebase-mcp, verify successful indexing
- **Estimated Time**: 2 hours

#### T009: Create basic semantic search evaluation (3 questions)
- Create `evaluations/codebase-search-basic.xml`
- Write XML metadata (title, description, version, difficulty)
- Q1: "Find database migration functions" (expected: 1 result, answer_type: count)
- Q2: "Locate API route handlers" (expected: 3 results, answer_type: count)
- Q3: "Find error handling code" (expected: 2 results, answer_type: contains)
- Define verification criteria for each question
- **Files**: `evaluations/codebase-search-basic.xml`
- **Dependencies**: T008
- **Acceptance Criteria**: Valid XML, 3 questions with expected answers and verification
- **Testing**: XML validation against schema
- **Estimated Time**: 1 hour

#### T010: Create filtering and precision evaluation (3 questions)
- Create `evaluations/codebase-search-filtering.xml`
- Write XML metadata (title, description, version, difficulty)
- Q4: "Find authentication functions in Python files only" (file_type filter test)
- Q5: "Search for database queries in src/database/ directory" (directory filter test)
- Q6: "Find test fixtures in test files" (combined filter test)
- Define verification criteria for each question
- **Files**: `evaluations/codebase-search-filtering.xml`
- **Dependencies**: T008
- **Acceptance Criteria**: Valid XML, 3 questions testing filters
- **Testing**: XML validation against schema
- **Estimated Time**: 1 hour

#### T011: Create multi-step workflow evaluation (4 questions)
- Create `evaluations/codebase-search-multifile.xml`
- Write XML metadata (title, description, version, difficulty)
- Q7: "Find all API endpoints, then find their test coverage" (2-step workflow)
- Q8: "Search for database models, then find migration scripts" (2-step workflow)
- Q9: "Search across 100+ files in under 500ms" (performance validation)
- Q10: "Find function definition with correct context showing imports" (context quality test)
- Define verification criteria for each question
- **Files**: `evaluations/codebase-search-multifile.xml`
- **Dependencies**: T008
- **Acceptance Criteria**: Valid XML, 4 questions with multi-step and performance tests
- **Testing**: XML validation against schema
- **Estimated Time**: 1.5 hours

#### T012: Implement evaluation runner utility
- Create `evaluations/run_evaluations.py` with helper functions
- Implement `run_evaluation(eval_file: Path)` to execute single XML file
- Implement `execute_question(question: ET.Element)` for question execution
- Implement `run_all_evaluations()` to run all XML files in directory
- Implement `print_results(all_results)` for formatted output
- Add EvaluationResult dataclass with question_id, passed, latency_ms, error fields
- **Files**: `evaluations/run_evaluations.py`
- **Dependencies**: T009, T010, T011
- **Acceptance Criteria**: XML parsing works, question execution logic complete, results formatted
- **Testing**: Unit tests for each helper function with sample XML
- **Estimated Time**: 2 hours

#### T013: Test and validate evaluation suite
- Run `python evaluations/run_evaluations.py`
- Validate 100% pass rate (10/10 questions pass)
- Measure execution time (target: <30s for all 10 questions)
- Verify deterministic results (run 3 times, same results)
- Fix any failing evaluations or fixture issues
- **Files**: All evaluation files
- **Dependencies**: T012
- **Acceptance Criteria**: 10/10 pass, <30s execution, deterministic
- **Testing**: Integration test running full suite
- **Estimated Time**: 1 hour

---

## Phase 2: Sequential Tasks (After Phase 1)

These tasks depend on Phase 1 completion and must be executed sequentially due to dependencies.

### Feature: Response Format Options
**Estimated Time**: 2 days (16 hours)
**Priority**: High (token optimization, backward compatibility critical)
**Files Affected**: `src/mcp/formatting.py` (new), `src/mcp/tools/*.py`

#### T014: Create formatting utility module
- Create `src/mcp/formatting.py` with type-safe helper functions
- Add module docstring explaining formatting utilities
- Add imports: `from typing import Any, Literal`, Pydantic models
- **Files**: `src/mcp/formatting.py`
- **Dependencies**: Phase 1 complete
- **Acceptance Criteria**: Module created with proper structure, mypy --strict passes
- **Testing**: `mypy --strict src/mcp/formatting.py`
- **Estimated Time**: 30 minutes

#### T015: Implement search result formatting functions
- Implement `format_search_results(results, total_count, latency_ms, project_id, database_name, response_format, detail_level)`
- Implement `_format_json_search_results()` for JSON formatting (detailed vs. concise)
- Implement `_format_markdown_search_results()` for Markdown formatting (detailed vs. concise)
- Handle concise mode: truncate content to 200 chars, omit context_before/context_after
- Handle markdown detailed: use code blocks with context sections
- Handle markdown concise: use compact table format
- **Files**: `src/mcp/formatting.py`
- **Dependencies**: T014
- **Acceptance Criteria**: All 4 format combinations implemented (JSON×2, Markdown×2)
- **Testing**: Unit tests with sample results, verify output structure
- **Estimated Time**: 3 hours

#### T016: Implement index result formatting functions
- Implement `format_index_results(repository_id, files_indexed, chunks_created, duration_seconds, project_id, database_name, status, errors, response_format, detail_level)`
- Implement `_format_json_index_results()` for JSON formatting
- Implement `_format_markdown_index_results()` for Markdown formatting
- Handle concise mode: omit database_name, show error count only
- Handle markdown detailed: show full error list, all metrics
- Handle markdown concise: compact metrics, error summary
- **Files**: `src/mcp/formatting.py`
- **Dependencies**: T014
- **Acceptance Criteria**: All 4 format combinations implemented
- **Testing**: Unit tests with sample index results, verify output
- **Estimated Time**: 2 hours

#### T017: Add formatting unit tests
- Create `tests/unit/test_formatting.py`
- Test JSON detailed format (verify all fields present)
- Test JSON concise format (verify truncation, omitted fields)
- Test Markdown detailed format (verify code blocks, context sections)
- Test Markdown concise format (verify table format)
- Test edge cases: empty results, single result, large results
- Verify token savings in concise mode (>60% reduction)
- **Files**: `tests/unit/test_formatting.py`
- **Dependencies**: T015, T016
- **Acceptance Criteria**: 100% coverage of formatting.py, all tests pass
- **Testing**: `pytest tests/unit/test_formatting.py --cov=src/mcp/formatting`
- **Estimated Time**: 2 hours

#### T018: Update search_code tool with formatting parameters
- Add `response_format: Literal["json", "markdown"] = "json"` parameter
- Add `detail_level: Literal["concise", "detailed"] = "detailed"` parameter
- Import formatting utilities from `src/mcp/formatting`
- Call `format_search_results()` before returning
- Update return type to `dict[str, Any] | str`
- Update docstring with parameter documentation and examples
- **Files**: `src/mcp/tools/search.py`
- **Dependencies**: T017
- **Acceptance Criteria**: Parameters added, formatting integrated, backward compatible
- **Testing**: mypy --strict, existing tests pass, new format tests pass
- **Estimated Time**: 2 hours

#### T019: Update index_repository tool with formatting parameters
- Add `response_format: Literal["json", "markdown"] = "json"` parameter
- Add `detail_level: Literal["concise", "detailed"] = "detailed"` parameter
- Import formatting utilities from `src/mcp/formatting`
- Call `format_index_results()` before returning
- Update return type to `dict[str, Any] | str`
- Update docstring with parameter documentation and examples
- **Files**: `src/mcp/tools/indexing.py`
- **Dependencies**: T017
- **Acceptance Criteria**: Parameters added, formatting integrated, backward compatible
- **Testing**: mypy --strict, existing tests pass, new format tests pass
- **Estimated Time**: 2 hours

#### T020: Create integration tests for formatting
- Create `tests/integration/test_formatting_integration.py`
- Test search_code with all 4 format combinations (JSON×detailed, JSON×concise, Markdown×detailed, Markdown×concise)
- Test index_repository with all 4 format combinations
- Test backward compatibility (default parameters return current format)
- Test Markdown table parsing (verify LLM-friendly structure)
- Test token count reduction (measure actual savings)
- **Files**: `tests/integration/test_formatting_integration.py`
- **Dependencies**: T018, T019
- **Acceptance Criteria**: All format combinations tested, backward compatibility verified
- **Testing**: `pytest tests/integration/test_formatting_integration.py -v`
- **Estimated Time**: 2 hours

#### T021: Update formatting documentation
- Update tool docstrings with format/detail examples
- Add "Response Formatting" section to README.md
- Document token savings in concise mode (with measurements)
- Add migration guide for existing clients
- Include format output examples (all 4 combinations)
- **Files**: `README.md`, tool docstrings
- **Dependencies**: T020
- **Acceptance Criteria**: Comprehensive documentation with examples
- **Testing**: Manual documentation review
- **Estimated Time**: 1.5 hours

---

### Feature: Character Limits and Truncation
**Estimated Time**: 2-3 days (20 hours)
**Priority**: High (context window protection)
**Files Affected**: `src/services/searcher.py`, `src/mcp/tools/search.py`

#### T022: Add truncation constants and models
- Add constants to `src/services/searcher.py`:
  - `CHARACTER_LIMIT: Final[int] = 100_000`
  - `CHAR_TO_TOKEN_RATIO: Final[float] = 4.0`
  - `TRUNCATION_MARGIN: Final[float] = 0.8`
  - `EFFECTIVE_CHAR_LIMIT: Final[int] = 80_000`
  - `TRUNCATION_WARNING_THRESHOLD: Final[float] = 0.7`
- Create TruncationInfo Pydantic model with fields: reason, original_count, returned_count, estimated_chars, limit_chars, estimated_tokens, limit_tokens
- Add type hints and docstrings
- **Files**: `src/services/searcher.py`
- **Dependencies**: T021 (formatting complete)
- **Acceptance Criteria**: Constants defined, TruncationInfo model created, mypy --strict passes
- **Testing**: `mypy --strict src/services/searcher.py`
- **Estimated Time**: 1 hour

#### T023: Implement size estimation functions
- Implement `estimate_result_size(result: SearchResult) -> int`
- Calculate size: chunk_id + file_path + content + line numbers + similarity_score
- Include context_before/context_after if present
- Add 20% JSON formatting overhead
- Implement `estimate_response_size(results: list[SearchResult]) -> int`
- Sum individual result sizes + 500 char metadata overhead
- **Files**: `src/services/searcher.py`
- **Dependencies**: T022
- **Acceptance Criteria**: Accurate size estimation (within 20% of actual JSON size)
- **Testing**: Unit tests with known result sizes, measure actual vs. estimated
- **Estimated Time**: 2 hours

#### T024: Create size estimation unit tests
- Create `tests/unit/test_size_estimation.py`
- Test `estimate_result_size()` with various result sizes
- Test `estimate_response_size()` with result lists
- Test edge cases: empty results, minimal results, large results
- Verify estimates within 20% of actual JSON size
- Test with different formats (JSON detailed/concise, Markdown detailed/concise)
- **Files**: `tests/unit/test_size_estimation.py`
- **Dependencies**: T023
- **Acceptance Criteria**: Estimates accurate to ±20%, all tests pass
- **Testing**: `pytest tests/unit/test_size_estimation.py -v`
- **Estimated Time**: 2 hours

#### T025: Implement truncation logic
- Implement `truncate_results_by_size(results, char_limit) -> tuple[list[SearchResult], TruncationInfo]`
- Sort results by similarity_score descending (highest first)
- Accumulate results until limit reached
- Never truncate mid-result (result-boundary truncation only)
- Build TruncationInfo object with truncation details
- Handle edge case: single result exceeds limit (return anyway with warning)
- **Files**: `src/services/searcher.py`
- **Dependencies**: T024
- **Acceptance Criteria**: Truncation preserves top results, respects boundaries
- **Testing**: Unit tests with various result counts and sizes
- **Estimated Time**: 3 hours

#### T026: Create truncation unit tests
- Create `tests/unit/test_truncation.py`
- Test truncation at various limits (80K, 50K, 20K chars)
- Test similarity-based prioritization (highest scored results preserved)
- Test result-boundary truncation (no partial results)
- Test edge cases: all results fit, no results fit, single huge result
- Test TruncationInfo accuracy (counts, estimates match actual)
- **Files**: `tests/unit/test_truncation.py`
- **Dependencies**: T025
- **Acceptance Criteria**: All truncation scenarios tested, TruncationInfo validated
- **Testing**: `pytest tests/unit/test_truncation.py -v`
- **Estimated Time**: 2 hours

#### T027: Integrate truncation into search_code tool
- Add truncation call after search service: `truncated_results, truncation_info = truncate_results_by_size(results)`
- Update response schema with new fields: `returned_count`, `truncated`, `truncation_info`
- Add truncation warning logging when truncated=True
- Add approaching-limit info logging when utilization > 70%
- Add Context notification for truncation warnings (if ctx available)
- **Files**: `src/mcp/tools/search.py`
- **Dependencies**: T026
- **Acceptance Criteria**: Truncation integrated, logging added, response schema updated
- **Testing**: Integration tests with real searches, verify truncation occurs
- **Estimated Time**: 3 hours

#### T028: Handle truncation with formatting combinations
- Update size estimation to account for response_format (Markdown adds overhead)
- Update size estimation to account for detail_level (concise saves space)
- Adjust EFFECTIVE_CHAR_LIMIT based on format/detail:
  - JSON detailed: 80K chars
  - JSON concise: 100K chars (concise saves ~20%)
  - Markdown detailed: 60K chars (Markdown adds ~30% overhead)
  - Markdown concise: 80K chars
- Test all format/detail combinations with truncation
- **Files**: `src/services/searcher.py`, `src/mcp/tools/search.py`
- **Dependencies**: T027
- **Acceptance Criteria**: Size estimation accurate for all format/detail combinations
- **Testing**: Integration tests verify correct limits for each combination
- **Estimated Time**: 3 hours

#### T029: Create truncation integration tests
- Create `tests/integration/test_truncation_integration.py`
- Test truncation with large result sets (50+ results)
- Test highest similarity results preserved
- Test response never exceeds CHARACTER_LIMIT (100K chars)
- Test truncation_info accuracy
- Test truncation with all format/detail combinations
- Test logging warnings occur when truncated
- **Files**: `tests/integration/test_truncation_integration.py`
- **Dependencies**: T028
- **Acceptance Criteria**: All truncation scenarios validated in real environment
- **Testing**: `pytest tests/integration/test_truncation_integration.py -v`
- **Estimated Time**: 2 hours

#### T030: Add truncation metrics to metrics service
- Add truncation_count counter to metrics service
- Add truncation_rate histogram (% of searches truncated)
- Add average_utilization gauge (char usage / limit)
- Add truncation_savings histogram (chars removed)
- Update metrics endpoint to expose truncation metrics
- **Files**: `src/services/metrics_service.py`
- **Dependencies**: T029
- **Acceptance Criteria**: Metrics collected and exposed via metrics:// resource
- **Testing**: Validate metrics collection in integration tests
- **Estimated Time**: 1.5 hours

#### T031: Update truncation documentation
- Update search_code docstring with truncation_info explanation
- Add "Character Limits & Truncation" section to README.md
- Document how to handle truncated responses (check truncated flag)
- Add troubleshooting guide for truncation issues
- Include examples of truncation scenarios
- Document token savings and truncation thresholds
- **Files**: `README.md`, tool docstrings
- **Dependencies**: T030
- **Acceptance Criteria**: Comprehensive truncation documentation
- **Testing**: Manual documentation review
- **Estimated Time**: 1.5 hours

---

## Phase 3: Integration & Validation

These tasks validate cross-feature functionality and ensure all enhancements work together correctly.

### Cross-Feature Integration Testing
**Estimated Time**: 1 day (8 hours)
**Priority**: Critical (production readiness validation)

#### T032: Create cross-feature integration test suite
- Create `tests/integration/test_cross_feature_integration.py`
- Test scenario: search_code with response_format=markdown, detail_level=concise, results get truncated
- Verify truncation respects format overhead (Markdown adds 30%)
- Verify concise mode saves space (allows more results before truncation)
- Test scenario: index_repository with markdown format, verify size estimates
- Test scenario: evaluation suite runs with all format/detail combinations
- **Files**: `tests/integration/test_cross_feature_integration.py`
- **Dependencies**: T031
- **Acceptance Criteria**: All format/truncation combinations work correctly
- **Testing**: `pytest tests/integration/test_cross_feature_integration.py -v`
- **Estimated Time**: 3 hours

#### T033: Update evaluation suite to test all enhancements
- Add format/detail parameters to evaluation runner
- Run evaluations with all 4 format combinations
- Add questions testing truncation behavior (Q11: search with limit=50, verify truncation)
- Add questions testing tool hints (Q12: verify idempotent search works correctly)
- Update evaluation XML files with new test cases
- **Files**: `evaluations/*.xml`, `evaluations/run_evaluations.py`
- **Dependencies**: T032
- **Acceptance Criteria**: Evaluations cover all 4 enhancements
- **Testing**: `python evaluations/run_evaluations.py`, verify all pass
- **Estimated Time**: 2 hours

#### T034: Performance regression testing
- Run performance benchmarks with formatting enabled (verify <10ms overhead)
- Run performance benchmarks with truncation enabled (verify <10ms overhead)
- Verify search_code maintains <500ms p95 latency target
- Verify index_repository maintains <60s p95 target
- Compare with baseline from `tests/performance/test_baseline.py`
- **Files**: `tests/performance/test_enhancement_overhead.py` (new)
- **Dependencies**: T033
- **Acceptance Criteria**: No performance regression, overhead <10ms for each enhancement
- **Testing**: Run benchmarks, compare with baseline
- **Estimated Time**: 1.5 hours

#### T035: End-to-end workflow validation
- Create `tests/e2e/test_mcp_enhancements.py`
- Test complete workflow: set_working_directory → index_repository → search_code
- Verify hints work correctly (idempotent retry of search_code)
- Verify formatting works (markdown output readable)
- Verify truncation works (large result set truncated correctly)
- Test with real codebase (not just test fixture)
- **Files**: `tests/e2e/test_mcp_enhancements.py`
- **Dependencies**: T034
- **Acceptance Criteria**: Complete workflow works end-to-end with all enhancements
- **Testing**: `pytest tests/e2e/test_mcp_enhancements.py -v`
- **Estimated Time**: 1.5 hours

---

## Git Strategy & Commits

### Branch Management
- Create feature branch: `git checkout -b 015-mcp-best-practices-enhancements`
- All commits follow Conventional Commits format
- Micro-commits after each task completion

### Commit Examples
```bash
# After T002
git add src/mcp/tools/indexing.py
git commit -m "feat(tools): add MCP hints to index_repository tool

- Add openWorldHint=True (interacts with filesystem/database)
- Add readOnlyHint=False (modifies database state)
- Add idempotentHint=False (behavior changes on repeated calls)
- Add inline comments explaining each hint rationale"

# After T015
git add src/mcp/formatting.py
git commit -m "feat(formatting): implement search result formatters

- Add format_search_results() with JSON/Markdown support
- Add _format_json_search_results() for detailed/concise JSON
- Add _format_markdown_search_results() for detailed/concise Markdown
- Handle content truncation in concise mode (200 chars)
- Handle context omission in concise mode"

# After T027
git add src/mcp/tools/search.py src/services/searcher.py
git commit -m "feat(search): integrate truncation logic into search_code

- Add truncate_results_by_size() call after search service
- Update response schema with returned_count, truncated, truncation_info
- Add truncation warning logging when results truncated
- Add approaching-limit info logging at 70% utilization
- Add Context notification for truncation warnings"
```

---

## Testing Strategy Summary

### Test Coverage Requirements
- **Unit Tests**: 100% coverage for `formatting.py`, size estimation, truncation logic
- **Integration Tests**: All format combinations, truncation scenarios, hint validation
- **E2E Tests**: Complete workflows with all enhancements enabled
- **Performance Tests**: Regression validation, overhead measurement

### Test Execution Order
1. Unit tests first (fastest feedback)
2. Integration tests second (feature validation)
3. E2E tests third (workflow validation)
4. Performance tests last (regression detection)

### Test Commands
```bash
# Unit tests
pytest tests/unit/ -v --cov=src/mcp/formatting --cov=src/services/searcher

# Integration tests
pytest tests/integration/ -v

# E2E tests
pytest tests/e2e/ -v

# Performance tests
pytest tests/performance/ -v

# All tests
pytest tests/ -v --cov=src
```

---

## Constitutional Compliance Checklist

### Principle Validation by Feature

#### Tool Annotations (T001-T006)
- ✅ **Principle I (Simplicity)**: Hints add minimal complexity, just decorator parameters
- ✅ **Principle II (Local-First)**: Hints don't affect offline operation
- ✅ **Principle III (Protocol Compliance)**: Hints are standard MCP feature
- ✅ **Principle IV (Performance)**: Hints have zero runtime overhead
- ✅ **Principle V (Production Quality)**: Comprehensive testing validates hint accuracy
- ✅ **Principle VI (Specification-First)**: Plan created before implementation
- ✅ **Principle VII (TDD)**: Integration tests validate hints
- ✅ **Principle VIII (Type Safety)**: Hints fully typed, mypy --strict compliant
- ✅ **Principle XI (FastMCP)**: Uses FastMCP hint feature as designed

#### Evaluation Suite (T007-T013)
- ✅ **Principle I (Simplicity)**: Suite doesn't add feature complexity, only tests
- ✅ **Principle II (Local-First)**: All evaluations run locally against local fixture
- ✅ **Principle III (Protocol Compliance)**: Follows MCP evaluation standards
- ✅ **Principle IV (Performance)**: Each question validates <500ms search target
- ✅ **Principle V (Production Quality)**: Comprehensive error handling in runner
- ✅ **Principle VII (TDD)**: Evaluation suite itself is a test artifact

#### Response Formatting (T014-T021)
- ✅ **Principle I (Simplicity)**: Reuses existing data structures
- ✅ **Principle II (Local-First)**: No external dependencies, all formatting local
- ✅ **Principle III (Protocol Compliance)**: Returns valid MCP tool responses
- ✅ **Principle IV (Performance)**: Formatting adds <5ms overhead
- ✅ **Principle V (Production Quality)**: Comprehensive error handling in formatters
- ✅ **Principle VIII (Type Safety)**: Full type hints, mypy --strict compliance
- ✅ **Principle XI (FastMCP)**: Uses FastMCP tool decorators, no protocol changes

#### Character Limits (T022-T031)
- ✅ **Principle I (Simplicity)**: Simple character-based estimation, no external deps
- ✅ **Principle II (Local-First)**: No external tokenizer, fully offline
- ✅ **Principle III (Protocol Compliance)**: Returns valid MCP responses with metadata
- ✅ **Principle IV (Performance)**: <10ms overhead, maintains <500ms p95 target
- ✅ **Principle V (Production Quality)**: Comprehensive error handling, logging
- ✅ **Principle VIII (Type Safety)**: TruncationInfo model uses Pydantic, mypy --strict

---

## Rollback Procedures

### Rollback Plan by Feature

#### Tool Annotations Rollback
```bash
# If hints cause LLM issues, rollback decorators
git revert <commit-hash-T002> <commit-hash-T003> <commit-hash-T004>
# Remove hint parameters from @mcp.tool() decorators
# Server continues to work without hints
```

#### Formatting Rollback
```bash
# If formatting causes issues, remove parameters (backward compatible)
git revert <commit-hash-T018> <commit-hash-T019>
# Default parameters maintain current JSON detailed behavior
# Clients continue to work unchanged
```

#### Truncation Rollback
```bash
# If truncation is too aggressive, disable truncation logic
git revert <commit-hash-T027> <commit-hash-T028>
# Remove truncate_results_by_size() call
# Return all results (pre-truncation behavior)
```

### Gradual Rollback Strategy
1. **Disable via config**: Add `ENABLE_TRUNCATION=false` flag
2. **Feature flag**: Add runtime toggle for each enhancement
3. **Partial rollback**: Rollback individual features without affecting others

---

## Appendices

### Appendix A: Task Dependencies Graph

```
Phase 1 (Parallel):
T001 → T002, T003, T004
T002, T003, T004 → T005 → T006

T007 → T008
T008 → T009, T010, T011
T009, T010, T011 → T012 → T013

Phase 2 (Sequential):
T014 → T015, T016
T015, T016 → T017
T017 → T018, T019
T018, T019 → T020 → T021

T021 → T022 → T023 → T024
T024 → T025 → T026 → T027
T027 → T028 → T029 → T030 → T031

Phase 3 (Integration):
T031 → T032 → T033 → T034 → T035
```

### Appendix B: Resource Requirements

**Single Developer Timeline**:
- Phase 1: 2-3 days (tool annotations: 4h, evaluation suite: 8h)
- Phase 2: 4-5 days (formatting: 16h, truncation: 20h)
- Phase 3: 1-2 days (integration: 8h)
- **Total: 8-10 days**

**Parallel Development Timeline (2 developers)**:
- Phase 1: 1-2 days (parallel work on annotations + evaluations)
- Phase 2: 3-4 days (sequential: formatting → truncation)
- Phase 3: 1 day (integration)
- **Total: 5-7 days**

### Appendix C: Risk Mitigation Matrix

| Risk | Probability | Impact | Mitigation | Owner |
|------|------------|--------|------------|-------|
| Formatting breaks backward compatibility | Low | High | Comprehensive backward compat tests (T020) | Dev |
| Size estimation inaccuracy | Medium | Medium | Conservative 4:1 ratio + 80% margin (T022) | Dev |
| Truncation removes critical results | Medium | Medium | Similarity-based prioritization (T025) | Dev |
| Performance regression | Low | High | Performance benchmarks (T034) | Dev |
| Hints mislead LLMs | Low | Medium | Hint validation tests (T005) | Dev |
| Cross-feature conflicts | Medium | High | Integration test suite (T032-T035) | Dev |

### Appendix D: Success Metrics

**Quality Metrics**:
- Test coverage: >95% for all new code
- mypy --strict: 100% compliance
- Evaluation suite: 100% pass rate (10/10 questions)
- Performance: No regression (overhead <10ms per enhancement)

**User Impact Metrics**:
- Token reduction: >60% in concise mode
- Truncation rate: <10% of searches truncated
- LLM retry rate: Reduced by 30% with hints
- Response time: Maintained <500ms p95

### Appendix E: Post-Implementation Tasks

**Future Enhancements** (not in scope):
1. **Token Analytics**: Track actual token savings in production
2. **Pagination**: Implement continuation tokens for large result sets
3. **Adaptive Limits**: Adjust limits based on detected agent context window
4. **Custom Templates**: Allow users to define custom Markdown templates
5. **Actual Token Counting**: Add tiktoken for accurate token measurement

**Monitoring Setup**:
1. Add Prometheus metrics for truncation rate
2. Add dashboards for format/detail usage
3. Add alerts for high truncation rates (>20%)
4. Track hint effectiveness via LLM retry rates

---

## Summary

This implementation plan provides a comprehensive, phased approach to adding MCP best practice enhancements to the codebase-mcp server. The 57 tasks are organized into 3 phases for optimal execution:

**Phase 1 (Parallel)**: Quick wins with tool annotations and evaluation suite foundation
**Phase 2 (Sequential)**: Core enhancements (formatting and truncation) with careful dependency management
**Phase 3 (Integration)**: Comprehensive validation ensuring all enhancements work together

**Key Success Factors**:
1. Backward compatibility maintained throughout (existing clients continue to work)
2. Constitutional compliance validated for all enhancements
3. Comprehensive testing at unit, integration, E2E, and performance levels
4. Clear rollback procedures for each feature
5. Micro-commits following Conventional Commits standard

**Estimated Timeline**: 8-10 days (single developer) or 5-7 days (parallel development)

**Risk Level**: Low-Medium (mitigated by comprehensive testing and rollback procedures)
