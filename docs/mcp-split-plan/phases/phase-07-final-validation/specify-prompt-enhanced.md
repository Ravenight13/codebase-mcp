# Feature: Phase 07 - Production Release Validation

Branch: `007-production-release-validation` | Date: 2025-10-12 | Status: Draft

## Original User Description

**Context**: This is Phase 07 of the multi-phase codebase-mcp refactoring plan. By this point, all previous phases (01-06) have been completed, including the core refactoring from 16 tools to 2 tools, multi-project support implementation, optional workflow-mcp integration, comprehensive testing, migration tooling, and performance validation.

**User Request**: "Create the final production release validation phase that ensures the codebase-mcp v2.0 release meets all quality, security, compliance, and operational readiness criteria before deployment."

**What needs to happen**:
1. Validate MCP protocol compliance using official tooling (mcp-inspector)
2. Conduct comprehensive security audit (SQL injection, input validation, dependency vulnerabilities)
3. Verify type safety compliance (mypy --strict with zero errors)
4. Validate test coverage targets (>80% overall, 100% critical paths)
5. Complete release readiness checklist (version bumps, changelog, migration guide)
6. Generate validation reports for all quality gates
7. Create release artifacts (tags, notes, documentation)

**Dependencies**: All phases 01-06 must be completed and merged. This is the final gate before v2.0.0 release.

---

## Execution Flow (main)
```
1. Parse validation requirements from user description
   → Identify: MCP compliance, security, type safety, coverage, release tasks
2. Validate prerequisites (phases 01-06 complete)
   → If incomplete: ERROR "Prior phases must complete first"
3. For each validation category:
   → Define testable acceptance criteria
   → Specify validation tooling and procedures
4. Map validation outputs to quality gates
   → Each gate must pass before release
5. Define rollback procedure for validation failures
6. Generate comprehensive checklist
7. Run Review Checklist
   → If any validation undefined: ERROR "Missing quality gate"
   → If no rollback plan: ERROR "Must define failure handling"
8. Return: SUCCESS (validation spec ready for planning)
```

---

## ⚡ Quick Guidelines
- ✅ Focus on WHAT must be validated and WHY (quality assurance)
- ✅ Define measurable acceptance criteria for each validation category
- ❌ Avoid HOW to implement validation scripts (that's for planning phase)
- 👥 Written for release managers and quality assurance stakeholders

### Section Requirements
- **Mandatory sections**: User Scenarios, Functional Requirements, Success Criteria, Edge Cases
- **Optional sections**: Key Entities (not applicable for validation phase)
- When a section doesn't apply, note it as "N/A for validation phase"

---

## User Scenarios & Testing

### Primary User Story

**As a** Release Manager
**I want** comprehensive validation of the codebase-mcp v2.0 release
**So that** I can confidently deploy to production knowing all quality, security, and compliance gates have passed

**User Journey**:
1. Release manager initiates Phase 07 validation after Phase 06 completion
2. System executes automated validation suite across 5 categories:
   - MCP Protocol Compliance
   - Security Audit
   - Type Safety Verification
   - Test Coverage Analysis
   - Release Readiness Checklist
3. System generates detailed validation reports for each category
4. Release manager reviews all reports and verifies pass/fail status
5. If all gates pass: System creates release artifacts (tags, changelog, notes)
6. If any gate fails: System provides rollback procedure and remediation guidance

### Acceptance Scenarios

#### Scenario 1: Complete Validation Success Path
1. **Given** all phases 01-06 are completed and merged
2. **And** the codebase is on branch `002-refactor-pure-search`
3. **When** Phase 07 validation is initiated
4. **Then** the system runs MCP protocol compliance tests
5. **And** all MCP inspector checks pass (tool discovery, schemas, SSE transport, error handling)
6. **And** the system runs security audit tests
7. **And** all security checks pass (SQL injection blocked, input validation enforced, 0 critical vulnerabilities)
8. **And** the system runs type safety verification
9. **And** mypy --strict passes with 0 errors
10. **And** the system runs test coverage analysis
11. **And** coverage exceeds 80% overall with 100% critical path coverage
12. **And** the system validates release readiness checklist
13. **And** all pre-release tasks are completed (version bump, changelog, migration guide)
14. **And** the system generates comprehensive validation report
15. **Then** release manager receives GREEN status for all 5 categories
16. **And** system creates git tag `v2.0.0`
17. **And** system generates release notes document
18. **And** Phase 07 is marked as COMPLETE

#### Scenario 2: MCP Compliance Failure Path
1. **Given** Phase 07 validation is initiated
2. **When** mcp-inspector detects tool schema violations
3. **Then** system generates detailed MCP compliance report showing failures
4. **And** system provides specific error details (e.g., "Tool 'search_code' missing required 'query' parameter description")
5. **And** system marks MCP Compliance gate as FAILED
6. **And** system halts validation (does not proceed to security audit)
7. **And** release manager is notified of validation failure
8. **And** system provides rollback instructions
9. **And** system links to MCP specification documentation for remediation
10. **Then** v2.0.0 release is blocked until compliance issues are resolved

#### Scenario 3: Security Audit Failure Path
1. **Given** MCP compliance checks have passed
2. **When** security audit detects SQL injection vulnerability
3. **Then** system generates detailed security audit report
4. **And** report identifies vulnerable code location and attack vector
5. **And** system marks Security gate as FAILED
6. **And** system continues with remaining validations (type safety, coverage)
7. **And** release manager receives final report with Security FAILED, other gates pending
8. **And** system provides remediation guidance (e.g., "Add input validation in project_id parameter")
9. **Then** v2.0.0 release is blocked until security issues are resolved

#### Scenario 4: Test Coverage Insufficient Path
1. **Given** MCP compliance and security audit have passed
2. **When** test coverage analysis shows only 75% overall coverage
3. **Then** system generates coverage report with uncovered line details
4. **And** system identifies critical paths with <100% coverage
5. **And** system marks Coverage gate as FAILED
6. **And** report shows exactly which files/functions need additional tests
7. **And** release manager receives actionable test coverage improvement plan
8. **Then** v2.0.0 release is blocked until coverage targets are met

### Edge Cases & Alternative Paths

**Edge Case 1: Partial Validation Pass**
- **Scenario**: 4 out of 5 validation categories pass, but type safety fails due to 2 unaddressed mypy errors
- **Expected Behavior**: System generates complete report showing 4 PASS, 1 FAIL; provides mypy error details; blocks release; provides remediation steps

**Edge Case 2: Dependency Vulnerability False Positive**
- **Scenario**: Security audit flags a dependency vulnerability that has been independently verified as false positive
- **Expected Behavior**: System allows manual override with justification; requires release manager approval; logs override decision; documents in security audit report

**Edge Case 3: Release Checklist Incomplete**
- **Scenario**: All automated validations pass, but CHANGELOG.md is missing v2.0.0 entry
- **Expected Behavior**: System marks Release Readiness gate as FAILED; identifies specific missing item; blocks tag creation; provides checklist template

**Edge Case 4: Migration Guide Not Tested**
- **Scenario**: Migration guide exists but hasn't been validated against a real v1.x database
- **Expected Behavior**: System flags untested migration as warning (not blocker); requires manual testing confirmation; documents testing status in validation report

**Edge Case 5: Performance Regression Detected Post-Phase 06**
- **Scenario**: Phase 06 performance validation passed, but subsequent changes introduce regression
- **Expected Behavior**: System re-runs performance benchmark as part of validation; detects regression; marks Performance gate as FAILED (new category); blocks release; requires return to Phase 06

---

## Requirements

### Functional Requirements

#### MCP Protocol Compliance Validation (FR-001 to FR-006)

- **FR-001**: System MUST validate MCP protocol compliance using the official `@modelcontextprotocol/inspector` tool
  - Validation target: HTTP endpoint responding at correct path
  - Expected outcome: Inspector reports "Server responding" status

- **FR-002**: System MUST verify that both MCP tools (`index_repository`, `search_code`) are discoverable via the MCP tool discovery mechanism
  - Validation target: Tool list returned by server
  - Expected outcome: Both tools present with correct names and descriptions

- **FR-003**: System MUST validate tool schemas against MCP specification requirements
  - Validation target: JSON schema for `index_repository` and `search_code`
  - Schema requirements:
    - `index_repository`: `repo_path` (required), `project_id` (optional, default "default", pattern `^[a-z0-9-]{1,50}$`)
    - `search_code`: `query` (required), `project_id` (optional, default "default", pattern `^[a-z0-9-]{1,50}$`), `limit` (optional, integer, default 10)
  - Expected outcome: All schema validations pass, no missing/incorrect types

- **FR-004**: System MUST verify SSE (Server-Sent Events) transport layer is functioning correctly
  - Validation target: SSE connection establishment and message streaming
  - Expected outcome: Inspector confirms SSE transport working

- **FR-005**: System MUST validate that error responses follow MCP error response specification
  - Validation target: Error response format for invalid inputs
  - Expected outcome: Errors include proper error codes, messages, and follow MCP error schema

- **FR-006**: System MUST generate an MCP Protocol Compliance Report documenting all validation results
  - Report location: `docs/validation/mcp-inspector-report.md`
  - Report contents: Pass/fail status for each compliance check, detailed error messages for failures, inspector version and timestamp

#### Security Audit Validation (FR-007 to FR-015)

- **FR-007**: System MUST execute SQL injection attack tests against both MCP tools to verify injection prevention
  - Test cases: Minimum 10 malicious inputs including:
    - SQL comment injection: `project'; DROP TABLE repositories; --`
    - Boolean condition injection: `project' OR '1'='1`
    - Path traversal: `../../../etc/passwd`
    - Null byte injection: `project\x00null`
  - Expected outcome: All malicious inputs rejected with `ValueError: Invalid project_id`

- **FR-008**: System MUST validate input validation enforcement for all tool parameters
  - Parameters to validate:
    - `project_id`: Must match pattern `^[a-z0-9-]{1,50}$`
    - `repo_path`: Must be valid absolute path, no path traversal allowed
    - `query`: Must be non-empty string
    - `limit`: Must be positive integer between 1 and 100
  - Expected outcome: Invalid inputs rejected with descriptive validation errors

- **FR-009**: System MUST scan the codebase for hardcoded secrets (API keys, passwords, tokens)
  - Scanning tool: `detect-secrets` or equivalent
  - Scan scope: All Python source files, configuration files, documentation
  - Expected outcome: Zero hardcoded secrets found

- **FR-010**: System MUST perform dependency vulnerability scan using `safety` or equivalent tool
  - Scan scope: All dependencies in `requirements.txt` and `pyproject.toml`
  - Vulnerability severity levels: Critical, High, Medium, Low
  - Expected outcome: Zero critical vulnerabilities, zero high vulnerabilities

- **FR-011**: System MUST execute static security analysis using `bandit` security linter
  - Scan scope: All Python source code in `src/` directory
  - Severity levels: High, Medium, Low
  - Expected outcome: Zero high severity issues

- **FR-012**: System MUST validate that no sensitive data (database credentials, API keys) is logged or exposed in error messages
  - Test cases: Trigger various error conditions and inspect logs
  - Expected outcome: No credentials or sensitive data in log output

- **FR-013**: System MUST verify that connection strings and database passwords are loaded from environment variables, not hardcoded
  - Code review target: Database connection initialization code
  - Expected outcome: All credentials loaded from `DATABASE_URL` environment variable

- **FR-014**: System MUST validate CORS (Cross-Origin Resource Sharing) configuration if HTTP endpoints are exposed
  - Validation target: HTTP server CORS headers
  - Expected outcome: CORS properly configured or N/A if not applicable

- **FR-015**: System MUST generate a comprehensive Security Audit Report
  - Report location: `docs/validation/security-audit.md`
  - Report sections:
    - SQL Injection Test Results (pass/fail for each test case)
    - Input Validation Test Results
    - Secrets Detection Results
    - Dependency Vulnerability Scan Results (with CVE details if any)
    - Bandit Static Analysis Results
    - Security Findings Summary (total issues by severity)
    - Remediation Recommendations (if any failures)

#### Type Safety Verification (FR-016 to FR-019)

- **FR-016**: System MUST validate that `mypy --strict` type checking passes with zero errors
  - Type checking scope: All source code in `src/` directory
  - Strict mode requirements: No untyped definitions, no implicit `Any`, strict function signatures
  - Expected outcome: `Success: no issues found in N source files`

- **FR-017**: System MUST verify that no `type: ignore` comments exist in the codebase unless explicitly justified
  - Code review target: All Python files for `# type: ignore` comments
  - If any exist: Must have inline justification comment explaining why
  - Expected outcome: Zero unjustified type: ignore comments

- **FR-018**: System MUST validate that all Pydantic models have proper validation rules
  - Validation target: All Pydantic model definitions in codebase
  - Requirements:
    - All fields have explicit types
    - Constraints defined where applicable (min_length, max_length, regex patterns)
    - Custom validators for complex validation logic
  - Expected outcome: All models pass Pydantic validation instantiation tests

- **FR-019**: System MUST generate a Type Safety Report
  - Report location: `docs/validation/mypy-report.txt`
  - Report contents: Mypy version, strict mode confirmation, total files checked, pass/fail status, error details if any

#### Test Coverage Analysis (FR-020 to FR-024)

- **FR-020**: System MUST execute test suite with coverage measurement enabled
  - Test runner: `pytest --cov=src --cov-report=html --cov-report=term`
  - Coverage scope: All source code in `src/` directory
  - Coverage types: Statement coverage (line coverage)

- **FR-021**: System MUST validate that overall test coverage exceeds 80%
  - Measurement: Total lines covered / total lines * 100
  - Expected outcome: Coverage ≥ 80%
  - If coverage < 80%: Validation fails, report identifies uncovered modules

- **FR-022**: System MUST validate that critical paths have 100% test coverage
  - Critical paths definition:
    - `index_repository` tool: Repository scanning, chunking, embedding generation, database insertion
    - `search_code` tool: Query embedding, similarity search, result ranking, context retrieval
    - Connection pooling: Pool initialization, connection acquisition, connection release, pool eviction
    - Multi-project support: Project database lookup, isolation verification
  - Expected outcome: All critical path lines covered by tests

- **FR-023**: System MUST identify and report all uncovered lines with file paths and line numbers
  - Report format: File path, line range, uncovered code snippet
  - Prioritization: Critical path uncovered lines flagged as high priority

- **FR-024**: System MUST generate comprehensive Test Coverage Report
  - Report locations:
    - HTML report: `docs/validation/coverage-report.html`
    - Terminal summary: Included in validation output
  - Report contents:
    - Overall coverage percentage
    - Per-module coverage breakdown
    - Uncovered lines detail (file, line numbers)
    - Critical path coverage analysis
    - Coverage trend (if historical data available)

#### Release Readiness Validation (FR-025 to FR-029)

- **FR-025**: System MUST validate that version number has been updated to `2.0.0` in all required locations
  - Files to check:
    - `pyproject.toml`: `version = "2.0.0"`
    - `src/codebase_mcp/__init__.py`: `__version__ = "2.0.0"`
  - Expected outcome: Both files contain correct version string

- **FR-026**: System MUST validate that `CHANGELOG.md` contains a complete entry for v2.0.0
  - Changelog requirements:
    - Version number and release date
    - Major changes section (breaking changes)
    - Features section (new capabilities)
    - Performance section (improvements)
    - Security section (fixes)
    - Documentation section (updates)
    - Migration section (link to migration guide)
    - Breaking changes section (detailed list)
  - Expected outcome: All required sections present and non-empty

- **FR-027**: System MUST validate that migration guide has been tested against a real v1.x database
  - Validation method: Check for testing confirmation file or manual sign-off
  - Migration guide location: `docs/migration/v1-to-v2.md`
  - Expected outcome: Migration guide marked as tested with documented test date

- **FR-028**: System MUST validate that all documentation files are accurate and complete
  - Documentation files to review:
    - `README.md`: Installation, usage, configuration instructions
    - `docs/architecture.md`: Multi-project architecture description
    - `docs/configuration.md`: Environment variables, database setup
    - `docs/migration/v1-to-v2.md`: Step-by-step migration instructions
  - Expected outcome: No placeholder text, no outdated information, all examples work

- **FR-029**: System MUST generate a complete Release Readiness Checklist Report
  - Report location: `docs/validation/release-checklist.md`
  - Checklist items:
    - Version bumped: YES/NO
    - Changelog complete: YES/NO
    - Migration guide tested: YES/NO
    - Documentation reviewed: YES/NO
    - All tests passing: YES/NO
    - Performance validated: YES/NO (reference Phase 06)
    - MCP compliance verified: YES/NO
    - Security audit passed: YES/NO
    - Type safety confirmed: YES/NO
    - Coverage target met: YES/NO
    - Release notes drafted: YES/NO
    - Git tag ready: YES/NO

### Success Criteria

#### Quantitative Metrics

1. **MCP Protocol Compliance**: 100% of inspector checks pass
2. **Security Audit**: 0 critical vulnerabilities, 0 high vulnerabilities, 0 SQL injection attacks succeed
3. **Type Safety**: 0 mypy strict errors, 0 unjustified type: ignore comments
4. **Test Coverage**: ≥80% overall coverage, 100% critical path coverage
5. **Release Readiness**: 12/12 checklist items complete

#### Qualitative Criteria

1. **Validation Reports**: All 5 reports generated with complete, actionable information
2. **Remediation Guidance**: Any failures include clear steps to resolve
3. **Audit Trail**: All validation steps documented with timestamps and tooling versions
4. **Release Confidence**: Release manager can confidently approve v2.0.0 deployment based on validation results

#### Gate Conditions

- **Green Gate**: ALL 5 categories pass → v2.0.0 release approved
- **Yellow Gate**: 1-2 non-critical failures with approved overrides → conditional release approval required
- **Red Gate**: Any critical failure (MCP non-compliance, critical security vulnerability, <70% coverage) → release BLOCKED until resolved

### Key Entities

**N/A for validation phase** - This phase validates existing code and artifacts. No new data entities are created or modified.

---

## Edge Cases & Error Handling

### Validation Failure Scenarios

**Edge Case 1: MCP Inspector Not Installed**
- **Trigger**: System attempts to run `mcp-inspector` but npm package not found
- **Expected Behavior**: Validation fails with clear error: "mcp-inspector not installed. Run: npm install -g @modelcontextprotocol/inspector"
- **Recovery**: Provide installation instructions, allow retry after installation

**Edge Case 2: Database Unavailable During Security Tests**
- **Trigger**: PostgreSQL service down when running SQL injection tests
- **Expected Behavior**: Security validation reports database connection error; suggests checking database status; does not mark security tests as passed
- **Recovery**: Provide database health check commands; allow retry after database restored

**Edge Case 3: Mypy Version Mismatch**
- **Trigger**: Different mypy version produces different errors than development environment
- **Expected Behavior**: Report includes mypy version used; flags version mismatch; provides instructions to install correct mypy version
- **Recovery**: Document required mypy version; provide installation command

**Edge Case 4: Test Coverage Below 80% After Phases 01-06**
- **Trigger**: Coverage analysis shows 75% overall coverage despite Phase 06 completion
- **Expected Behavior**: Validation fails; report identifies newly uncovered code; provides specific test recommendations; suggests returning to Phase 06
- **Recovery**: Generate test stubs for uncovered code; re-run coverage after adding tests

**Edge Case 5: Changelog Missing Breaking Changes Detail**
- **Trigger**: CHANGELOG.md exists but doesn't adequately document 14 removed MCP tools
- **Expected Behavior**: Release readiness validation flags incomplete changelog; provides template for breaking changes section
- **Recovery**: Provide checklist of all breaking changes; require complete documentation before re-validation

### Concurrent Validation Execution

**Edge Case 6: Multiple Validations Running Simultaneously**
- **Trigger**: Security audit and coverage analysis both access database concurrently
- **Expected Behavior**: System serializes database-dependent validations; parallel validations for independent checks (mypy, changelog review)
- **Recovery**: N/A (handled by validation orchestration)

### Report Generation Failures

**Edge Case 7: Unable to Write Validation Report**
- **Trigger**: Insufficient file permissions for `docs/validation/` directory
- **Expected Behavior**: Validation completes but report writing fails; error message indicates permission issue; suggests creating directory with correct permissions
- **Recovery**: Provide directory creation command: `mkdir -p docs/validation && chmod 755 docs/validation`

**Edge Case 8: HTML Coverage Report Too Large**
- **Trigger**: Coverage HTML report exceeds reasonable size (>100MB) due to large codebase
- **Expected Behavior**: System generates terminal summary report; logs warning about HTML report size; provides instructions to open HTML report externally
- **Recovery**: Suggest using terminal report for quick review; HTML report available for detailed analysis

### Git Tag Conflicts

**Edge Case 9: v2.0.0 Tag Already Exists**
- **Trigger**: Validation passes and attempts to create `v2.0.0` tag, but tag already exists from previous failed release attempt
- **Expected Behavior**: Tag creation fails with error: "Tag v2.0.0 already exists"; provides instructions to delete old tag if safe; requires manual confirmation
- **Recovery**: `git tag -d v2.0.0 && git push origin :refs/tags/v2.0.0` (after confirming old tag should be removed)

**Edge Case 10: Not on Expected Branch**
- **Trigger**: Validation initiated but current git branch is not `002-refactor-pure-search`
- **Expected Behavior**: Validation halts immediately; error message: "Phase 07 must run on branch 002-refactor-pure-search. Current branch: <branch_name>"
- **Recovery**: `git checkout 002-refactor-pure-search` and retry validation

### Dependency Issues

**Edge Case 11: Conflicting Dependency Versions**
- **Trigger**: Development environment has different dependency versions than `requirements.txt`
- **Expected Behavior**: Security vulnerability scan shows different results than expected; validation flags version mismatch; recommends clean virtual environment
- **Recovery**: `python -m venv venv && source venv/bin/activate && pip install -r requirements.txt` and re-run validation

**Edge Case 12: Ollama Service Not Running for Embedding Tests**
- **Trigger**: Integration tests require Ollama for embeddings but service is down
- **Expected Behavior**: Test execution fails; coverage report marks embedding-related code as untested; validation fails
- **Recovery**: Start Ollama service: `ollama serve` (in background); re-run tests

### Performance Regression Detection

**Edge Case 13: Post-Phase 06 Code Changes Introduce Performance Regression**
- **Trigger**: Bug fix or documentation update after Phase 06 inadvertently impacts performance
- **Expected Behavior**: Validation includes performance smoke test; detects regression; flags as critical failure; requires return to Phase 06 for performance re-validation
- **Recovery**: Revert problematic changes; re-run Phase 06 performance tests; proceed with Phase 07 after performance validated

---

## Review & Acceptance Checklist

### Content Quality
- [x] No implementation details (focuses on WHAT to validate, not HOW)
- [x] Focused on quality assurance value and release confidence
- [x] Written for release managers and QA stakeholders
- [x] All mandatory sections completed

### Requirement Completeness
- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous (each has clear pass/fail criteria)
- [x] Success criteria are measurable (quantitative metrics defined)
- [x] Scope is clearly bounded (validation only, no new features)
- [x] Dependencies identified (phases 01-06 completion)
- [x] Rollback procedure defined (return to Phase 06 if validation fails)

### Validation Coverage
- [x] MCP protocol compliance fully specified
- [x] Security audit requirements comprehensive
- [x] Type safety verification complete
- [x] Test coverage targets defined
- [x] Release readiness checklist exhaustive

### Edge Case Handling
- [x] Tool installation failures addressed
- [x] Database connectivity issues handled
- [x] Version mismatch scenarios covered
- [x] Git tag conflicts resolved
- [x] Performance regression detection included

---

## Clarifications Section

**No clarifications needed.** All validation requirements are fully specified with:
- Clear acceptance criteria for each validation category
- Specific tooling requirements (mcp-inspector, safety, bandit, mypy, pytest)
- Quantitative pass/fail thresholds (0 critical vulnerabilities, >80% coverage, etc.)
- Comprehensive edge case handling
- Defined rollback procedures

---

## Non-Goals

**Explicitly OUT OF SCOPE for Phase 07:**

1. **New Feature Development**: Phase 07 is validation only. No new MCP tools, no additional functionality.

2. **Performance Optimization**: Performance validation refers to Phase 06 results. No new performance tuning in this phase.

3. **Code Refactoring**: No code changes except critical bug fixes discovered during validation. Refactoring belongs in earlier phases.

4. **Documentation Rewriting**: Documentation review validates accuracy and completeness. Major documentation rewrites should have been done in Phase 06 or earlier.

5. **Migration Guide Testing Against All Possible v1.x Configurations**: Migration guide testing validates the happy path. Exhaustive testing of all edge cases is out of scope.

6. **Production Deployment**: Phase 07 validates readiness for release. Actual deployment to production environments is a separate post-release activity.

7. **User Acceptance Testing (UAT)**: Validation is technical QA. UAT with end users is a separate activity.

8. **Backward Compatibility**: v2.0.0 is a breaking change release. No effort to maintain v1.x API compatibility.

9. **Hotfix for Issues Discovered in Validation**: If validation discovers critical issues, Phase 07 documents them but does NOT fix them. Fixes require returning to appropriate prior phase (e.g., Phase 03 for test issues, Phase 06 for performance issues).

10. **Release Announcement and Marketing**: Phase 07 drafts release notes. Actual announcement, blog posts, and marketing activities are post-release.

---

## Execution Status

*Updated during validation execution:*

- [ ] Prerequisites validated (phases 01-06 complete)
- [ ] MCP protocol compliance tests executed
- [ ] Security audit completed
- [ ] Type safety verification performed
- [ ] Test coverage analysis finished
- [ ] Release readiness checklist reviewed
- [ ] All validation reports generated
- [ ] Quality gates evaluated (all pass)
- [ ] Release artifacts created (tag, notes)
- [ ] Phase 07 marked COMPLETE

---

## Validation Report Structure

Each of the 5 validation categories produces a standardized report with the following structure:

### Report Template

```markdown
# [Validation Category] Report

**Phase**: 07 - Production Release Validation
**Date**: YYYY-MM-DD HH:MM:SS UTC
**Branch**: 002-refactor-pure-search
**Commit**: <git commit SHA>

---

## Executive Summary

**Overall Status**: PASS / FAIL / WARNING
**Critical Issues**: N
**High Issues**: N
**Medium Issues**: N
**Low Issues**: N

---

## Validation Results

### [Test Category 1]
- **Status**: PASS / FAIL
- **Details**: [Specific results]
- **Evidence**: [Tool output, logs, screenshots]

### [Test Category 2]
...

---

## Issues Identified

### Critical Issues
1. **Issue**: [Description]
   - **Severity**: CRITICAL
   - **Location**: [File/function]
   - **Remediation**: [Steps to fix]

### High Issues
...

---

## Recommendations

1. [Action item based on findings]
2. [Action item based on findings]

---

## Tooling Details

- **Tool Name**: [Version]
- **Configuration**: [Relevant settings]
- **Execution Environment**: [Python version, OS, etc.]

---

## Appendix

[Detailed logs, full tool output, etc.]
```

---

## Dependencies and Assumptions

### Dependencies (MUST be complete before Phase 07)

1. **Phase 01**: Core refactoring from 16 tools to 2 tools complete
2. **Phase 02**: Multi-project support implemented and tested
3. **Phase 03**: Optional workflow-mcp integration functional
4. **Phase 04**: Comprehensive test suite passing (unit, integration, E2E)
5. **Phase 05**: Migration tooling and documentation complete
6. **Phase 06**: Performance validation passed (60s indexing, 500ms search targets met)

### Assumptions

1. **Development Environment**: All validation runs on a clean development environment with all dependencies installed per `requirements.txt`
2. **Database Availability**: PostgreSQL service is running and accessible for tests requiring database access
3. **Ollama Service**: Ollama is running and accessible for tests requiring embedding generation
4. **Network Access**: npm registry accessible for installing `mcp-inspector` (if not already installed)
5. **Git State**: All phases 01-06 changes committed and branch is clean (no uncommitted changes)
6. **Tool Availability**: Python 3.11+, pip, npm, git, pytest, mypy, bandit, safety, detect-secrets available in PATH

### External Dependencies

- **@modelcontextprotocol/inspector**: Official MCP protocol validation tool (npm package)
- **safety**: Python dependency vulnerability scanner (pip package)
- **bandit**: Python security linter (pip package)
- **detect-secrets**: Secret detection tool (pip package)
- **mypy**: Python static type checker (pip package)
- **pytest**: Python test framework with coverage plugin (pip package)

---

## Rollback and Recovery Procedures

### When Validation Fails

**General Principle**: Phase 07 validation failures indicate issues that should have been caught in earlier phases. Rollback to the appropriate phase based on failure category.

#### MCP Compliance Failure → Return to Phase 01
- **Why**: MCP tool schema issues indicate core refactoring problems
- **Procedure**:
  1. Document compliance failures in Phase 01 tracking document
  2. Checkout Phase 01 branch: `git checkout 001-core-refactoring`
  3. Fix MCP tool definitions
  4. Re-run Phase 01 tests
  5. Merge fix to `002-refactor-pure-search`
  6. Re-run Phase 07 validation

#### Security Audit Failure → Return to Phase 02 or 03
- **Why**: SQL injection or input validation failures relate to multi-project or integration code
- **Procedure**:
  1. Identify failure location (database access layer, MCP tool parameter handling)
  2. If multi-project database isolation issue: Return to Phase 02
  3. If workflow-mcp integration issue: Return to Phase 03
  4. Fix security vulnerability
  5. Add security test to prevent regression
  6. Re-run Phase 04 tests (comprehensive suite)
  7. Re-run Phase 07 validation

#### Type Safety Failure → Return to Phase 01-03 (depending on location)
- **Why**: Type errors should have been caught during development
- **Procedure**:
  1. Review mypy errors and identify affected code
  2. Return to phase where code was introduced
  3. Add type annotations
  4. Verify mypy --strict passes
  5. Re-run affected phase tests
  6. Re-run Phase 07 validation

#### Coverage Failure → Return to Phase 04
- **Why**: Test coverage issues indicate missing tests
- **Procedure**:
  1. Review uncovered lines report
  2. Checkout Phase 04 branch: `git checkout 004-comprehensive-testing`
  3. Add missing tests for uncovered code
  4. Verify coverage >80% and critical paths 100%
  5. Merge tests to `002-refactor-pure-search`
  6. Re-run Phase 07 validation

#### Release Readiness Failure → Fix in Place (Phase 07)
- **Why**: Documentation and release artifact issues can be fixed without code changes
- **Procedure**:
  1. Update CHANGELOG.md, version numbers, or documentation as needed
  2. Commit changes: `git commit -m "docs: complete release readiness for v2.0.0"`
  3. Re-run Phase 07 validation

### When All Validations Pass

**Success Path**:
1. All 5 validation reports show PASS status
2. Create git tag: `git tag -a v2.0.0 -m "Release v2.0.0: Pure semantic search with multi-project support"`
3. Generate release notes from CHANGELOG.md and validation reports
4. Merge branch to main: `git checkout main && git merge 002-refactor-pure-search`
5. Push tag: `git push origin v2.0.0`
6. Create GitHub release with notes and artifacts
7. Mark Phase 07 COMPLETE
8. Announce v2.0.0 release

---

## Performance Smoke Test

**Rationale**: While Phase 06 conducted comprehensive performance validation, Phase 07 includes a quick smoke test to catch any performance regressions introduced by post-Phase 06 changes (e.g., documentation updates, minor bug fixes).

### Smoke Test Criteria

1. **Indexing Performance**: Index a 1,000-file repository in <10 seconds (vs. Phase 06 target of <60s for 10,000 files)
2. **Search Performance**: Execute 10 semantic searches with p95 latency <100ms (vs. Phase 06 target of <500ms)
3. **Connection Pool**: Verify connection acquisition <10ms for 3 concurrent projects

### If Smoke Test Fails

- **Action**: BLOCK release, return to Phase 06 for full performance re-validation
- **Rationale**: Performance regression indicates a critical issue that must be resolved before v2.0.0 release

---

## Compliance and Audit Trail

### Validation Artifact Retention

All validation reports and supporting artifacts must be retained for audit purposes:

- **Location**: `docs/validation/`
- **Retention Period**: Indefinite (committed to git repository)
- **Artifacts**:
  - `mcp-inspector-report.md`
  - `security-audit.md`
  - `mypy-report.txt`
  - `coverage-report.html`
  - `release-checklist.md`
  - `bandit-report.json`
  - `safety-report.json`

### Audit Trail Requirements

Each validation report must include:
1. **Timestamp**: UTC timestamp of validation execution
2. **Environment**: OS, Python version, tool versions
3. **Git State**: Branch, commit SHA, clean/dirty working directory
4. **Executor**: Who initiated the validation (for manual reviews)
5. **Results**: Pass/fail status with detailed evidence

---

## Phase 07 Success Definition

**Phase 07 is considered COMPLETE when:**

1. ✅ All 5 validation categories report PASS status
2. ✅ All validation reports committed to `docs/validation/`
3. ✅ Git tag `v2.0.0` created and pushed
4. ✅ Release notes document generated and reviewed
5. ✅ No CRITICAL or HIGH severity issues unresolved
6. ✅ Performance smoke test passes
7. ✅ Release manager approves v2.0.0 deployment

**Post-Phase 07:**
- Merge `002-refactor-pure-search` to `main`
- Create GitHub release with artifacts
- Update production deployment configurations
- Announce v2.0.0 availability

---

**🎉 Phase 07 represents the final quality gate before codebase-mcp v2.0.0 is released to production. Comprehensive validation ensures confidence in the release and provides a documented audit trail of all quality assurance activities.**
