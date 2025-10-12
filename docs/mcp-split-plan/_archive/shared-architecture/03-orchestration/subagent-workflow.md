# Subagent Workflow: 4-Step Review Process

## Overview

The MCP split project uses a rigorous 4-step review process with orchestrated subagents to ensure high-quality implementation plans. This workflow runs in parallel for both the codebase-mcp and workflow-mcp tracks.

## Process Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Orchestrator: Launches parallel tracks                     │
└─────────────────────────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
        ▼                         ▼
┌──────────────────┐      ┌──────────────────┐
│ Codebase-MCP     │      │ Workflow-MCP     │
│ Track            │      │ Track            │
└──────────────────┘      └──────────────────┘
        │                         │
        │ Step 1: Initial Plan    │
        │ (Sequential)            │
        │                         │
        ├─────────┬───────────────┤
        │         │               │
        ▼         ▼               ▼
    Step 2:   Step 3:        (Same steps)
    Planning  Architectural
    Review    Review
    (Parallel with Step 3)
        │         │               │
        └────┬────┘               │
             ▼                    ▼
        Step 4: Final Revised Plan
        (Integrates all feedback)
             │                    │
             └────────┬───────────┘
                      ▼
            ┌─────────────────────┐
            │ Final Plans Ready   │
            └─────────────────────┘
```

## Step 1: Initial Plan Subagent

### Purpose
Generate a comprehensive implementation plan from the feature specification without architectural review feedback.

### What It Produces
- **Implementation phases** (TDD, core functionality, integration tests)
- **Task breakdown** with dependencies
- **File structure** (new files, modified files)
- **API contracts** (tool signatures, MCP schemas)
- **Data models** (database tables, Pydantic models)
- **Test strategy** (minimal but sufficient)
- **Performance targets** (p95 latency goals)

### Success Criteria for a Good Initial Plan

#### ✅ Good Initial Plan Characteristics

**1. Clear Scope Definition**
```markdown
## Scope
IN SCOPE:
- Multi-project support in semantic search (project_id parameter)
- Project isolation for search results
- Active project context management

OUT OF SCOPE:
- Cross-project search aggregation
- Project permission/access control
- Project metadata storage (workflow-mcp responsibility)
```

**2. Detailed Task Breakdown**
```markdown
## Phase 1: Database Schema
- [P] T001: Add project_id column to repositories table
- [P] T002: Add project_id column to code_chunks table
- [ ] T003: Create migration script with backward compatibility
- [ ] T004: Add project_id indexes for search performance

## Phase 2: Core Functionality
- [ ] T005: Update index_repository to accept project_id parameter
- [P] T006: Update search_code to filter by project_id
- [P] T007: Add get_active_project helper
```

**3. Explicit Dependencies**
```markdown
## Dependencies
- T003 depends on T001, T002 (schema changes must exist)
- T005 depends on T003 (migration must run first)
- T006, T007 depend on T004 (indexes must exist)
- T008 (integration test) depends on T005, T006, T007
```

**4. Concrete File Changes**
```markdown
## Files Modified
- `src/database/schema.py` - Add project_id columns
- `src/database/migrations/008_add_project_support.sql` - Migration
- `src/tools/index_repository.py` - Accept project_id parameter
- `src/tools/search_code.py` - Filter by project_id
- `tests/test_multi_project.py` - Integration tests
```

**5. Performance Considerations**
```markdown
## Performance Targets
- Search latency: <500ms p95 (unchanged from baseline)
- Index creation: <60s per 10K files (unchanged)
- Project filter overhead: <5ms (index-based)
```

#### ❌ Poor Initial Plan Characteristics

**1. Vague Scope**
```markdown
## Scope
- Add multi-project support
- Make search work with projects
```
❌ No clear IN/OUT scope boundaries, no specifics about what changes

**2. Missing Dependencies**
```markdown
## Tasks
- T001: Update database schema
- T002: Update search tool
- T003: Add tests
```
❌ No indication of task order, no dependencies specified, no parallel execution markers

**3. Generic File References**
```markdown
## Files Modified
- Database files
- Search code
- Tests
```
❌ No specific file paths, no indication of what changes to make

**4. No Performance Analysis**
```markdown
## Implementation
We'll add project support to the search functionality.
```
❌ No performance targets, no consideration of indexing overhead

**5. Missing Error Handling**
```markdown
## Error Cases
- Handle errors appropriately
```
❌ No specific error scenarios, no handling strategy

### Initial Plan Template Structure

```markdown
# [Feature Name] - Initial Implementation Plan

## 1. Executive Summary
[3-4 sentence overview of what will be implemented]

## 2. Scope Definition
### In Scope
- [Specific deliverable 1]
- [Specific deliverable 2]

### Out of Scope
- [Explicitly excluded feature 1]
- [Explicitly excluded feature 2]

## 3. Implementation Phases
### Phase 1: [Phase Name]
**Goal:** [What this phase achieves]
**Tasks:**
- [P] T001: [Task description]
- [ ] T002: [Task description]

### Phase 2: [Phase Name]
[Continue...]

## 4. File Structure
### New Files
- `path/to/new_file.py` - [Purpose]

### Modified Files
- `path/to/existing.py` - [Changes summary]

## 5. API Contracts
### Tool: tool_name
```python
{
    "name": "tool_name",
    "parameters": {...},
    "returns": {...}
}
```

## 6. Data Models
### Table: table_name
```sql
CREATE TABLE table_name (
    id UUID PRIMARY KEY,
    ...
);
```

## 7. Test Strategy
### MCP Protocol Compliance
- Tool registration validation
- Request/response format tests

### Basic Functionality
- [Core feature test scenario]

### Integration Tests
- [End-to-end test scenario]

## 8. Performance Targets
- [Metric]: [Target] ([p95/p99])
- [Metric]: [Target]

## 9. Error Handling
### Error Scenario 1
**Condition:** [When this occurs]
**Response:** [How to handle]
**User Message:** [Error message format]

## 10. Dependencies
- T### depends on T###: [Reason]
- T### depends on T###: [Reason]

## 11. Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
```

### Execution Guidelines

**Inputs:**
- Feature specification (`spec.md`)
- Constitutional principles (`.specify/memory/constitution.md`)
- Existing codebase context (via semantic search)

**Process:**
1. Read and analyze spec.md thoroughly
2. Identify all technical requirements (explicit and implicit)
3. Break down into implementation phases
4. Create detailed task list with dependencies
5. Define API contracts and data models
6. Specify test requirements (minimal but sufficient)
7. Document file structure and changes

**Time Budget:** 15-20 minutes
**Output Location:** `specs/###-feature/initial-plan.md`

### Quality Checklist

Before submitting Step 1 output:
- [ ] All spec requirements covered in tasks
- [ ] Tasks have clear dependencies marked
- [ ] Parallel tasks marked with [P]
- [ ] File paths are specific and absolute
- [ ] API contracts include parameter types
- [ ] Performance targets specified
- [ ] Error scenarios documented
- [ ] Test strategy includes MCP protocol compliance
- [ ] Acceptance criteria mirror spec requirements

---

## Step 2: Planning Review Subagent

### Purpose
Critique the initial plan for completeness, correctness, and implementation quality. Focus on catching gaps, ambiguities, and missing requirements.

### What It Reviews

**1. Completeness**
- Are all spec requirements addressed in tasks?
- Are acceptance criteria covered?
- Are error scenarios handled?
- Are performance targets realistic?

**2. Correctness**
- Do task dependencies make sense?
- Are parallel execution markers valid?
- Do API contracts match spec requirements?
- Are data models sufficient for the feature?

**3. Clarity**
- Are task descriptions actionable?
- Are file paths specific?
- Are API contracts unambiguous?
- Are acceptance criteria measurable?

**4. Risk Identification**
- Are there missing error cases?
- Are there untested edge cases?
- Are there performance bottlenecks?
- Are there integration risks?

### What It Produces

A structured critique document with:
- **Critical Issues** - Must be fixed before implementation
- **Important Issues** - Should be addressed for quality
- **Suggestions** - Nice-to-have improvements
- **Positive Observations** - What was done well

### Planning Review Template

```markdown
# Planning Review: [Feature Name]

## Overall Assessment
**Quality Score:** [High/Medium/Low]
**Ready for Implementation:** [Yes/No/With Changes]
**Summary:** [2-3 sentence overall assessment]

---

## Critical Issues (MUST FIX)

### Issue 1: [Title]
**Location:** Phase 2, Task T005
**Problem:** The task description says "update search tool" but doesn't specify which parameters to add or how to handle backward compatibility.
**Impact:** Implementation will be ambiguous, may break existing functionality.
**Suggested Fix:**
```markdown
T005: Update search_code tool to accept optional project_id parameter
- Add project_id: Optional[str] to tool parameters
- Default to active_project if not provided
- Add backward compatibility test
```
**Priority:** P0 (Blocks implementation)

### Issue 2: [Title]
[Continue for each critical issue...]

---

## Important Issues (SHOULD FIX)

### Issue 3: [Title]
**Location:** Phase 3, Integration Tests
**Problem:** No test for handling missing project_id when no active project exists.
**Impact:** Edge case may cause runtime errors in production.
**Suggested Fix:**
```markdown
Add T012: Test search_code with no project_id and no active project
- Expect clear error message: "No project specified and no active project set"
- Verify error follows MCP error format
```
**Priority:** P1 (Quality issue)

---

## Suggestions (NICE TO HAVE)

### Suggestion 1: [Title]
**Location:** Performance Targets
**Observation:** Performance targets don't mention index size overhead.
**Suggestion:** Add: "Index size overhead per project: <5% of single-project baseline"
**Benefit:** Helps validate multi-project doesn't cause storage bloat.

---

## Positive Observations

✅ **Clear Scope Boundaries:** IN/OUT scope clearly defined
✅ **Parallel Tasks Well Marked:** Schema changes correctly marked [P]
✅ **Explicit Dependencies:** Task dependency graph is clear
✅ **Specific File Paths:** All file changes use absolute paths
✅ **Test Strategy:** Follows minimal-but-sufficient principle

---

## Gap Analysis

### Requirements Coverage
- ✅ Multi-project search isolation (T006, T008)
- ✅ Project context management (T007)
- ❌ **MISSING:** Project deletion handling (what happens to indexed code?)
- ❌ **MISSING:** Project switching performance test

### Error Scenarios Coverage
- ✅ Invalid project_id handling
- ✅ Missing active project handling
- ❌ **MISSING:** Database connection failure during search
- ❌ **MISSING:** Concurrent index operations on same project

### Performance Targets
- ✅ Search latency specified
- ✅ Index creation specified
- ❌ **MISSING:** Project creation overhead
- ❌ **MISSING:** Project switching latency

---

## Dependency Validation

### Task Dependency Graph
```
T001, T002 (parallel) → T003 → T004 → T005, T006, T007 (parallel) → T008
```

**Issues:**
- ✅ Graph is acyclic (no circular dependencies)
- ✅ Parallel tasks are independent (different files)
- ❌ T007 (get_active_project) should depend on workflow-mcp integration
- ❌ T008 (integration test) needs workflow-mcp tools available

---

## Recommendations

### Priority 1: Fix Critical Issues
1. Clarify task descriptions for T005, T006, T007
2. Add missing error scenarios (database failures, concurrency)
3. Specify workflow-mcp integration dependencies

### Priority 2: Address Important Issues
1. Add edge case tests (missing project, invalid project_id)
2. Add project deletion handling strategy
3. Add performance test for project switching

### Priority 3: Consider Suggestions
1. Add index size overhead metric
2. Add cross-project search future consideration
3. Document project isolation guarantees

---

## Next Steps

**If Critical Issues Fixed:**
→ Proceed to Step 3 (Architectural Review)

**If Critical Issues Remain:**
→ Return to Step 1 subagent with this feedback for revision

**Estimated Fix Time:** 10-15 minutes
```

### Review Criteria

#### Critical Issue Triggers (MUST mark as critical)
- Missing spec requirements in tasks
- Ambiguous task descriptions that block implementation
- Invalid dependencies (circular, impossible)
- Missing error handling for core failures
- Performance targets conflict with constitutional principles

#### Important Issue Triggers (SHOULD mark as important)
- Missing edge case tests
- Unclear API contracts
- Missing file path specifics
- Insufficient error messages
- Missing performance metrics

#### Suggestion Triggers (NICE-TO-HAVE)
- Process improvements
- Documentation enhancements
- Future consideration notes
- Code organization suggestions

### Execution Guidelines

**Inputs:**
- `initial-plan.md` from Step 1
- `spec.md` (feature specification)
- Constitutional principles

**Process:**
1. Read initial-plan.md thoroughly
2. Cross-reference with spec.md requirements
3. Validate task dependencies
4. Check for missing error scenarios
5. Verify performance targets against constitution
6. Document issues by severity
7. Provide actionable fixes for each issue

**Time Budget:** 10-15 minutes
**Output Location:** `specs/###-feature/planning-review.md`

---

## Step 3: Architectural Review Subagent

### Purpose
Validate the initial plan against the Specify framework, constitutional principles, and architectural patterns. Focus on ensuring the plan stays "on rails" and doesn't violate non-negotiable principles.

### What It Reviews

**1. Constitutional Compliance**
- Simplicity over features (Principle 1)
- Local-first architecture (Principle 2)
- MCP protocol compliance (Principle 3)
- Performance guarantees (Principle 4)
- Production quality standards (Principle 5)
- Specification-first development (Principle 6)
- Test-driven development (Principle 7)
- Pydantic-based type safety (Principle 8)
- Git micro-commit strategy (Principle 10)
- FastMCP foundation (Principle 11)

**2. Tech Stack Alignment**
- Python 3.11+
- PostgreSQL 14+
- FastMCP with MCP Python SDK
- Ollama for embeddings
- NO cloud dependencies
- NO stdout/stderr pollution

**3. On-Rails Validation**
- Follows Specify workflow phases
- Uses prescribed templates
- Maintains git branch conventions
- Follows Conventional Commits
- Respects token budget constraints

**4. Architecture Patterns**
- Orchestrated subagent execution
- Parallel vs sequential task decisions
- Test-before-implementation approach
- Atomic commit strategy

### What It Produces

A constitutional compliance report with:
- **CRITICAL** - Constitutional principle violations
- **WARNING** - Architectural deviations needing justification
- **INFO** - Best practice recommendations
- **COMPLIANT** - Areas that follow principles correctly

### Architectural Review Template

```markdown
# Architectural Review: [Feature Name]

## Constitutional Compliance Summary

| Principle | Status | Details |
|-----------|--------|---------|
| 1. Simplicity Over Features | ✅ COMPLIANT | Feature scope is focused, no feature creep |
| 2. Local-First Architecture | ✅ COMPLIANT | No cloud dependencies introduced |
| 3. Protocol Compliance | ⚠️ WARNING | See Issue A1 below |
| 4. Performance Guarantees | ❌ CRITICAL | See Issue C1 below |
| 5. Production Quality | ✅ COMPLIANT | Comprehensive error handling |
| 6. Specification-First | ✅ COMPLIANT | Plan derived from spec.md |
| 7. Test-Driven Development | ⚠️ WARNING | See Issue A2 below |
| 8. Pydantic Type Safety | ✅ COMPLIANT | All models use Pydantic |
| 9. Subagent Execution | N/A | Not applicable to this feature |
| 10. Git Micro-Commit | ✅ COMPLIANT | Tasks map to commits |
| 11. FastMCP Foundation | ✅ COMPLIANT | Uses FastMCP patterns |

**Overall Status:** NEEDS REVISION (1 critical, 2 warnings)

---

## CRITICAL Issues (Constitutional Violations)

### C1: Performance Guarantee Violation (Principle 4)
**Principle:** Search latency must be <500ms p95
**Violation:** Plan proposes sequential project resolution + search execution
```markdown
# Current plan (in initial-plan.md Phase 2)
T007: Add get_active_project helper
- Call workflow-mcp to get active project
- Then execute search with project_id
```
**Impact:** Adds 50ms+ workflow-mcp round-trip to every search operation
**Risk:** May push p95 latency over 500ms threshold
**Required Fix:**
```markdown
Option A: Cache active project in codebase-mcp (invalidate on project switch)
- get_active_project checks local cache first
- Falls back to workflow-mcp only on cache miss
- Expected overhead: <5ms (cache hit), <50ms (cache miss)

Option B: Require project_id parameter, error if missing
- Remove active project auto-resolution
- Client must provide project_id explicitly
- Expected overhead: 0ms (no additional call)
```
**Recommendation:** Option A (better UX, acceptable perf with caching)

---

## WARNING Issues (Architectural Deviations)

### A1: MCP Protocol Compliance - Error Format (Principle 3)
**Principle:** Error handling must follow MCP spec
**Deviation:** Plan doesn't specify MCP error format for project-related errors
**Location:** Phase 2, T006 (search_code error handling)
**Current Plan:**
```markdown
T006: Update search_code to filter by project_id
- Add project_id validation
- Return error if project not found
```
**Issue:** "Return error" is ambiguous - MCP requires specific error structure
**Required Clarification:**
```python
# MCP Error Format (per protocol spec)
{
    "error": {
        "code": -32602,  # Invalid params
        "message": "Invalid project_id",
        "data": {
            "project_id": "invalid-uuid-here",
            "reason": "Project not found"
        }
    }
}
```
**Fix:** Update T006 to specify MCP error format explicitly

### A2: Test-Driven Development - Test Order (Principle 7)
**Principle:** Tests before implementation
**Deviation:** Test task T008 comes after implementation tasks T005, T006, T007
**Current Plan:**
```markdown
Phase 2: Core Functionality
- T005: Update index_repository
- T006: Update search_code
- T007: Add get_active_project
Phase 3: Testing
- T008: Integration tests
```
**Issue:** TDD requires tests first to drive design
**Required Fix:**
```markdown
Phase 2: Test-Driven Development
- T005: Write integration test for multi-project search (RED)
- T006: Write unit tests for project_id validation (RED)
- T007: Update search_code to pass tests (GREEN)
- T008: Write test for get_active_project (RED)
- T009: Implement get_active_project (GREEN)
- T010: Update index_repository with project_id (REFACTOR)
```
**Impact:** Ensures API design is validated before implementation

---

## INFO Recommendations (Best Practices)

### I1: Git Micro-Commit Granularity
**Observation:** Tasks T001, T002 are marked [P] but modify same migration file
**Current Plan:**
```markdown
- [P] T001: Add project_id to repositories table
- [P] T002: Add project_id to code_chunks table
```
**Issue:** Both tasks would commit changes to same migration SQL file - merge conflict
**Recommendation:**
```markdown
- [ ] T001: Create migration 008_add_project_support.sql with all schema changes
  - Add project_id to repositories table
  - Add project_id to code_chunks table
  - Add indexes
```
**Benefit:** Single atomic commit for schema migration (better rollback story)

### I2: Parallel Execution Optimization
**Observation:** T006, T007 are parallel but T007 is dependency for T006
**Current Plan:**
```markdown
- [P] T006: Update search_code to filter by project_id
- [P] T007: Add get_active_project helper
```
**Issue:** T006 calls T007 - not truly parallel
**Recommendation:**
```markdown
- [ ] T006: Add get_active_project helper (with tests)
- [ ] T007: Update search_code to use get_active_project (depends on T006)
```
**Benefit:** Correct dependency graph, enables true parallelization elsewhere

---

## Tech Stack Validation

### ✅ Approved Technologies
- Python 3.11+ (specified in plan)
- PostgreSQL 14+ (existing infrastructure)
- FastMCP framework (tool registration follows patterns)
- Pydantic models (all schemas use Pydantic)
- Ollama embeddings (no changes to embedding strategy)

### ❌ Prohibited Technologies
None detected.

### ⚠️ Dependencies to Verify
- **workflow-mcp integration:** Plan assumes workflow-mcp provides get_active_project
  - Verify workflow-mcp API contract exists
  - Confirm MCP communication pattern (stdio vs SSE)
  - Document failure handling if workflow-mcp unavailable

---

## On-Rails Compliance

### Specify Workflow Phases
- ✅ Feature has dedicated branch: `004-multi-project-search`
- ✅ Spec created before plan: `specs/004-multi-project-search/spec.md`
- ✅ Plan follows template: Phase structure matches `.specify/templates/plan-template.md`
- ✅ Tasks will use template: References `tasks-template.md`

### Git Conventions
- ✅ Branch naming: `###-feature-name` format
- ✅ Commit strategy: One task = one commit
- ✅ Conventional Commits: Plan mentions `feat(scope):` format
- ⚠️ Missing: Specific commit messages for each task

**Recommendation:** Add example commit messages to task descriptions
```markdown
T005: Write integration test for multi-project search
Commit: test(search): add multi-project isolation integration test
```

### Token Budget
- ✅ Plan length: ~2000 tokens (well under budget)
- ✅ Task descriptions: Concise, actionable
- ⚠️ Missing: Token budget for implementation phase

**Recommendation:** Add token budget estimate
```markdown
## Token Budget
- Phase 1 (Schema): ~10K tokens (migration + tests)
- Phase 2 (Core): ~25K tokens (search_code, get_active_project, tests)
- Phase 3 (Integration): ~15K tokens (integration tests + docs)
- Total estimate: ~50K tokens (25% of default budget)
```

---

## Architecture Pattern Validation

### Orchestrated Subagent Execution
**Pattern:** Use subagents for parallel independent tasks
**Plan Compliance:** Marks [P] for parallel tasks
**Issues:**
- ❌ T001, T002 marked [P] but modify same file (not independent)
- ✅ T006, T007 marked [P] and modify different files (good)

**Recommendation:** Review all [P] markers for true independence

### Test-Before-Implementation
**Pattern:** Write failing tests, then make them pass
**Plan Compliance:** ⚠️ Tests come after implementation (see A2 above)
**Required Fix:** Reorder tasks to follow RED-GREEN-REFACTOR

### Atomic Commit Strategy
**Pattern:** Each commit is a working state (tests pass)
**Plan Compliance:** ✅ Tasks are small enough for atomic commits
**Validation:** Ensure each task includes "verify tests pass" step

---

## Constitutional Justification Requirements

The following deviations require explicit justification in final plan:

### None Required
All identified issues are fixable without constitutional compromise.

---

## Compliance Scorecard

| Category | Score | Notes |
|----------|-------|-------|
| Constitutional Principles | 8/10 | 1 critical, 2 warnings |
| Tech Stack | 10/10 | All approved technologies |
| On-Rails Workflow | 9/10 | Minor git convention gaps |
| Architecture Patterns | 7/10 | TDD ordering needs fix |
| **Overall** | **8.5/10** | **NEEDS REVISION** |

**Threshold for Approval:** 9.0/10 (all criticals resolved)

---

## Required Changes Summary

**Must Fix (Blocks Step 4):**
1. ❌ C1: Add active project caching to meet <500ms search target
2. ⚠️ A1: Specify MCP error format for project errors
3. ⚠️ A2: Reorder tasks to follow TDD pattern

**Should Fix (Quality improvements):**
1. I1: Merge T001, T002 into single migration task
2. I2: Fix T006/T007 dependency for true parallelization
3. Add commit message examples to tasks
4. Add token budget estimate

**Estimated Revision Time:** 15-20 minutes

---

## Sign-Off

**Architectural Review Status:** ❌ REVISION REQUIRED
**Proceed to Step 4:** After critical issues C1, A1, A2 are resolved
**Re-Review Required:** No (issues are clear, fixes are prescribed)
```

### Review Criteria

#### CRITICAL Triggers (Constitutional violations)
- Performance target exceeded
- Cloud dependency introduced
- Non-approved technology used
- MCP protocol violation
- Missing Pydantic models
- stdout/stderr pollution

#### WARNING Triggers (Architectural deviations)
- TDD pattern not followed
- Git convention violations
- Missing error format specifications
- Unclear on-rails compliance

#### INFO Triggers (Best practices)
- Optimization opportunities
- Better parallelization strategies
- Token budget considerations
- Documentation improvements

### Execution Guidelines

**Inputs:**
- `initial-plan.md` from Step 1
- `.specify/memory/constitution.md`
- Tech stack constraints
- Specify workflow documentation

**Process:**
1. Read constitutional principles thoroughly
2. Map each principle to plan elements
3. Validate tech stack choices
4. Check on-rails compliance
5. Review architecture patterns
6. Calculate compliance scorecard
7. Document required changes by severity

**Time Budget:** 10-15 minutes
**Output Location:** `specs/###-feature/architectural-review.md`

---

## Step 4: Final Revised Plan Subagent

### Purpose
Integrate feedback from Steps 2 and 3 to produce a final, implementation-ready plan that addresses all critical issues and incorporates important improvements.

### What It Integrates

**Inputs:**
1. `initial-plan.md` (Step 1 output)
2. `planning-review.md` (Step 2 output)
3. `architectural-review.md` (Step 3 output)
4. `spec.md` (original requirements)

**Integration Process:**
1. Apply all CRITICAL fixes from Step 3 (constitutional)
2. Apply all CRITICAL fixes from Step 2 (planning gaps)
3. Apply IMPORTANT fixes from Steps 2 and 3
4. Consider INFO/suggestions based on time/complexity
5. Validate all feedback is addressed

### What It Produces

A final `plan.md` that includes:
- All elements from initial plan (structure preserved)
- Critical issue resolutions integrated
- Important issue improvements incorporated
- Feedback resolution notes (what changed and why)
- Sign-off checklist (confirms all critical issues resolved)

### Final Revised Plan Template

```markdown
# [Feature Name] - Final Implementation Plan

> **Plan Version:** 2.0 (Revised)
> **Initial Plan:** [Link to initial-plan.md]
> **Planning Review:** [Link to planning-review.md]
> **Architectural Review:** [Link to architectural-review.md]
> **Revision Date:** 2025-10-11

---

## Revision Summary

### Critical Issues Resolved
1. ✅ **C1 (Architectural):** Added active project caching to meet <500ms search latency
   - **Change:** New ProjectCache class with Redis-like TTL (60s default)
   - **Location:** New file `src/cache/project_cache.py`
   - **Impact:** Search overhead <5ms (cache hit), <50ms (cache miss)

2. ✅ **A1 (Architectural):** Specified MCP error format for all project-related errors
   - **Change:** Added MCP error format examples to T006, T007, T009
   - **Location:** Phase 2 task descriptions
   - **Impact:** Protocol compliance guaranteed

3. ✅ **A2 (Architectural):** Reordered tasks to follow TDD pattern
   - **Change:** Tests now precede implementation in Phase 2
   - **Location:** Phase 2 task order (T005-T010)
   - **Impact:** RED-GREEN-REFACTOR cycle enforced

4. ✅ **Issue 1 (Planning):** Clarified task descriptions with specific implementation details
   - **Change:** T005, T006, T007 now include parameter signatures and error handling
   - **Location:** Phase 2 task descriptions
   - **Impact:** Unambiguous implementation guidance

5. ✅ **Issue 2 (Planning):** Added edge case test for missing project + no active project
   - **Change:** New task T012 for edge case coverage
   - **Location:** Phase 3 (Integration Tests)
   - **Impact:** Production error handling validated

### Important Issues Resolved
1. ✅ **I1 (Architectural):** Merged T001, T002 into single migration task
   - **Change:** Combined schema changes into T001
   - **Rationale:** Single atomic commit, better rollback story

2. ✅ **I2 (Architectural):** Fixed T006/T007 dependency ordering
   - **Change:** T006 (get_active_project) now precedes T007 (search_code update)
   - **Rationale:** Enables true parallelization in Phase 3

3. ✅ **Issue 3 (Planning):** Added project deletion handling strategy
   - **Change:** New task T011 documents project deletion behavior
   - **Location:** Phase 3 (Integration Tests)

### Suggestions Incorporated
1. ✅ Added commit message examples to all tasks
2. ✅ Added token budget estimate (~50K total)
3. ✅ Added index size overhead metric (<5% per project)

---

## 1. Executive Summary

This feature adds multi-project support to codebase-mcp, enabling semantic code search scoped to specific projects. It introduces a project_id parameter to index_repository and search_code tools, adds project isolation at the database level, and integrates with workflow-mcp for active project context management.

**Key Changes:**
- Database schema: Add project_id columns to repositories and code_chunks tables
- Indexing: Update index_repository to accept and store project_id
- Search: Update search_code to filter results by project_id with active project fallback
- Caching: Implement project cache to meet <500ms search latency target
- Testing: Minimal but sufficient tests for MCP protocol compliance and basic functionality

---

## 2. Scope Definition

### In Scope
- Multi-project support in semantic search (project_id parameter)
- Project isolation for search results at database level
- Active project context management with caching
- Backward compatibility for single-project workflows
- Database migration with zero-downtime deployment
- Project deletion handling (soft delete indexed code)

### Out of Scope
- Cross-project search aggregation
- Project permission/access control (future: authentication MCP)
- Project metadata storage (workflow-mcp responsibility)
- Multi-tenant security boundaries (trust-based isolation)
- Project creation/management UI (workflow-mcp responsibility)

---

## 3. Implementation Phases

### Phase 1: Database Schema & Migration
**Goal:** Add project_id columns with indexes for performant filtering

#### T001: Create migration with project_id columns and indexes
**[P]** (Can run parallel with Phase 2 test writing)
```sql
-- migration 008_add_project_support.sql
ALTER TABLE repositories ADD COLUMN project_id UUID REFERENCES projects(id);
ALTER TABLE code_chunks ADD COLUMN project_id UUID REFERENCES projects(id);
CREATE INDEX idx_repositories_project_id ON repositories(project_id);
CREATE INDEX idx_code_chunks_project_id ON code_chunks(project_id);
CREATE INDEX idx_code_chunks_project_embedding ON code_chunks(project_id, embedding)
  USING ivfflat(embedding vector_cosine_ops);
```
**Acceptance:**
- Migration runs without errors
- Indexes created successfully
- Backward compatible (existing NULL project_ids allowed)
- Migration script includes rollback commands

**Commit:** `feat(schema): add project_id columns for multi-project support`

#### T002: Create project cache implementation
**[P]** (Independent of database migration)
```python
# src/cache/project_cache.py
class ProjectCache:
    """LRU cache for active project resolution with TTL."""
    def __init__(self, ttl_seconds: int = 60, max_size: int = 100):
        self._cache: dict[str, tuple[str, float]] = {}
        self._ttl = ttl_seconds
        self._max_size = max_size

    def get(self, key: str) -> Optional[str]:
        """Get project_id if cached and not expired."""
        ...

    def set(self, key: str, project_id: str) -> None:
        """Cache project_id with TTL."""
        ...

    def invalidate(self, key: str) -> None:
        """Remove from cache on project switch."""
        ...
```
**Acceptance:**
- Cache stores project_id with expiration
- Cache evicts expired entries automatically
- Cache respects max size (LRU eviction)
- Thread-safe for concurrent access

**Commit:** `feat(cache): add project cache for active project resolution`

---

### Phase 2: Test-Driven Development (Core Functionality)
**Goal:** Implement project filtering with TDD approach

#### T003: Write integration test for multi-project search isolation (RED)
**[P]** (Can run parallel with T004)
```python
# tests/test_multi_project_search.py
async def test_search_respects_project_isolation():
    """Verify search results scoped to project_id."""
    # Setup: Index same code in two projects
    await index_repository(repo_path="/tmp/repo", project_id=project_a_id)
    await index_repository(repo_path="/tmp/repo", project_id=project_b_id)

    # Execute: Search in project A
    results_a = await search_code(query="function", project_id=project_a_id)

    # Verify: Results only from project A
    assert all(r["project_id"] == project_a_id for r in results_a["results"])
    assert len(results_a["results"]) > 0
```
**Acceptance:**
- Test fails initially (RED)
- Test validates project isolation
- Test includes setup/teardown for test projects

**Commit:** `test(search): add multi-project isolation integration test`

#### T004: Write unit test for project_id validation (RED)
**[P]** (Independent of T003)
```python
# tests/test_search_validation.py
async def test_search_rejects_invalid_project_id():
    """Verify MCP error format for invalid project_id."""
    with pytest.raises(McpError) as exc_info:
        await search_code(query="test", project_id="invalid-uuid")

    error = exc_info.value
    assert error.code == -32602  # Invalid params
    assert "Invalid project_id" in error.message
    assert error.data["project_id"] == "invalid-uuid"
```
**Acceptance:**
- Test fails initially (RED)
- Test validates MCP error format
- Test covers invalid UUID format

**Commit:** `test(search): add project_id validation tests`

#### T005: Update search_code to filter by project_id (GREEN)
```python
# src/tools/search_code.py
@mcp.tool()
async def search_code(
    query: str,
    project_id: Optional[str] = None,
    repository_id: Optional[str] = None,
    file_type: Optional[str] = None,
    directory: Optional[str] = None,
    limit: int = 10
) -> SearchResults:
    """Search codebase with project isolation."""
    # Resolve project_id
    if project_id is None:
        project_id = await get_active_project()
        if project_id is None:
            raise McpError(
                code=-32602,
                message="No project specified and no active project set",
                data={"parameter": "project_id"}
            )

    # Validate project_id format
    try:
        uuid.UUID(project_id)
    except ValueError:
        raise McpError(
            code=-32602,
            message="Invalid project_id format",
            data={"project_id": project_id, "expected": "UUID"}
        )

    # Execute search with project filter
    sql = """
        SELECT c.*, ts_rank(search_vector, query) as rank
        FROM code_chunks c
        WHERE c.project_id = $1
          AND c.embedding <=> $2 < 0.3
        ORDER BY c.embedding <=> $2
        LIMIT $3
    """
    results = await db.fetch(sql, project_id, query_embedding, limit)
    return {"results": results, "total_count": len(results)}
```
**Acceptance:**
- Tests T003, T004 now pass (GREEN)
- MCP error format matches spec
- Backward compatible (project_id optional)

**Commit:** `feat(search): add project_id filtering with MCP error handling`

#### T006: Write test for get_active_project helper (RED)
```python
# tests/test_active_project.py
async def test_get_active_project_with_cache_hit():
    """Verify cache reduces workflow-mcp calls."""
    # Setup: Prime cache
    cache.set("active_project", project_id)

    # Execute: Multiple calls
    start = time.time()
    for _ in range(10):
        result = await get_active_project()
    duration = time.time() - start

    # Verify: Cache hit performance
    assert result == project_id
    assert duration < 0.01  # <1ms per call (cache hit)
```
**Acceptance:**
- Test fails initially (RED)
- Test validates cache performance
- Test covers cache miss scenario

**Commit:** `test(project): add active project cache performance test`

#### T007: Implement get_active_project helper (GREEN)
```python
# src/helpers/project_helper.py
_project_cache = ProjectCache(ttl_seconds=60, max_size=100)

async def get_active_project() -> Optional[str]:
    """Get active project with caching."""
    # Check cache first
    cached = _project_cache.get("active_project")
    if cached:
        return cached

    # Cache miss: call workflow-mcp
    try:
        result = await workflow_mcp.call_tool(
            "get_project_configuration",
            {}
        )
        project_id = result.get("current_session_id")
        if project_id:
            _project_cache.set("active_project", project_id)
        return project_id
    except Exception as e:
        logger.warning(f"Failed to get active project: {e}")
        return None

async def invalidate_project_cache() -> None:
    """Invalidate cache on project switch (called by workflow-mcp)."""
    _project_cache.invalidate("active_project")
```
**Acceptance:**
- Test T006 passes (GREEN)
- Cache hit latency <5ms
- Cache miss latency <50ms
- Handles workflow-mcp unavailable gracefully

**Commit:** `feat(project): implement active project caching with <5ms overhead`

#### T008: Update index_repository to accept project_id (REFACTOR)
```python
# src/tools/index_repository.py
@mcp.tool()
async def index_repository(
    repo_path: str,
    project_id: str,  # Now required
    force_reindex: bool = False
) -> IndexResults:
    """Index repository for semantic search with project association."""
    # Validate project_id
    try:
        uuid.UUID(project_id)
    except ValueError:
        raise McpError(
            code=-32602,
            message="Invalid project_id format",
            data={"project_id": project_id, "expected": "UUID"}
        )

    # Store project_id with indexed chunks
    async with db.transaction():
        repo_id = await db.fetchval(
            "INSERT INTO repositories (path, project_id) VALUES ($1, $2) RETURNING id",
            repo_path, project_id
        )

        for chunk in chunks:
            await db.execute(
                """
                INSERT INTO code_chunks (repository_id, project_id, content, embedding)
                VALUES ($1, $2, $3, $4)
                """,
                repo_id, project_id, chunk.content, chunk.embedding
            )
```
**Acceptance:**
- Existing tests updated for project_id parameter
- All tests pass (no regression)
- Project isolation enforced at write time

**Commit:** `refactor(indexing): add required project_id parameter`

---

### Phase 3: Integration Tests & Edge Cases
**Goal:** Validate end-to-end scenarios and error handling

#### T009: Test project switching performance
```python
# tests/test_project_switching.py
async def test_project_switch_invalidates_cache():
    """Verify cache invalidation on project switch."""
    # Setup: Cache project A
    await get_active_project()  # Caches project A

    # Execute: Switch to project B
    await workflow_mcp.call_tool("update_project_configuration", {
        "current_session_id": project_b_id
    })
    await invalidate_project_cache()

    # Verify: Next call fetches project B
    result = await get_active_project()
    assert result == project_b_id
```
**Acceptance:**
- Cache invalidation works correctly
- No stale project_id served after switch

**Commit:** `test(project): add project switching cache invalidation test`

#### T010: Test edge case - no project_id and no active project
```python
# tests/test_edge_cases.py
async def test_search_with_no_project_context():
    """Verify error when no project specified and none active."""
    # Setup: Clear cache, no active project
    await invalidate_project_cache()

    # Execute: Search without project_id
    with pytest.raises(McpError) as exc_info:
        await search_code(query="test")

    # Verify: Clear MCP error
    assert exc_info.value.code == -32602
    assert "no active project" in exc_info.value.message.lower()
```
**Acceptance:**
- Error message is user-friendly
- MCP error format correct

**Commit:** `test(search): add edge case test for missing project context`

#### T011: Document project deletion behavior
```python
# tests/test_project_lifecycle.py
async def test_project_deletion_soft_deletes_indexed_code():
    """Verify indexed code soft-deleted when project deleted."""
    # Setup: Index code in project
    await index_repository(repo_path="/tmp/repo", project_id=project_id)

    # Execute: Delete project (via workflow-mcp)
    await workflow_mcp.call_tool("delete_project", {"project_id": project_id})

    # Verify: Search returns no results
    results = await search_code(query="test", project_id=project_id)
    assert len(results["results"]) == 0

    # Verify: Data still in DB (soft deleted)
    count = await db.fetchval(
        "SELECT COUNT(*) FROM code_chunks WHERE project_id = $1 AND deleted_at IS NOT NULL",
        project_id
    )
    assert count > 0
```
**Acceptance:**
- Soft delete prevents search results
- Data preserved for potential recovery
- Hard delete (future) documented

**Commit:** `test(lifecycle): add project deletion soft-delete test`

#### T012: MCP protocol compliance validation
```python
# tests/test_mcp_compliance.py
async def test_search_tool_mcp_schema():
    """Verify search_code tool schema follows MCP spec."""
    schema = mcp.get_tool_schema("search_code")

    assert schema["name"] == "search_code"
    assert "parameters" in schema
    assert schema["parameters"]["type"] == "object"
    assert "project_id" in schema["parameters"]["properties"]
    assert schema["parameters"]["properties"]["project_id"]["type"] == "string"
```
**Acceptance:**
- Tool registration valid
- Parameter types correct
- Optional parameters marked

**Commit:** `test(mcp): add protocol compliance validation for search tool`

---

## 4. File Structure

### New Files
- `src/cache/project_cache.py` - LRU cache with TTL for active project
- `src/helpers/project_helper.py` - get_active_project, invalidate_project_cache
- `src/database/migrations/008_add_project_support.sql` - Schema migration
- `tests/test_multi_project_search.py` - Integration tests
- `tests/test_active_project.py` - Cache performance tests
- `tests/test_project_switching.py` - Project switching tests
- `tests/test_edge_cases.py` - Edge case coverage
- `tests/test_project_lifecycle.py` - Deletion behavior tests
- `tests/test_mcp_compliance.py` - Protocol validation

### Modified Files
- `src/tools/index_repository.py` - Add project_id parameter (required)
- `src/tools/search_code.py` - Add project_id filtering with active fallback
- `src/database/schema.py` - Add project_id columns to models
- `pyproject.toml` - Add cachetools dependency

---

## 5. API Contracts

### Tool: search_code
```json
{
    "name": "search_code",
    "description": "Search codebase with project isolation",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language search query"
            },
            "project_id": {
                "type": "string",
                "format": "uuid",
                "description": "Project UUID (optional, defaults to active project)"
            },
            "repository_id": {"type": "string", "format": "uuid"},
            "file_type": {"type": "string"},
            "directory": {"type": "string"},
            "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50}
        },
        "required": ["query"]
    },
    "returns": {
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "chunk_id": {"type": "string"},
                        "file_path": {"type": "string"},
                        "content": {"type": "string"},
                        "start_line": {"type": "integer"},
                        "end_line": {"type": "integer"},
                        "similarity_score": {"type": "number"},
                        "project_id": {"type": "string"}
                    }
                }
            },
            "total_count": {"type": "integer"},
            "latency_ms": {"type": "integer"}
        }
    }
}
```

### Tool: index_repository
```json
{
    "name": "index_repository",
    "description": "Index repository for semantic search with project association",
    "parameters": {
        "type": "object",
        "properties": {
            "repo_path": {
                "type": "string",
                "description": "Absolute path to repository"
            },
            "project_id": {
                "type": "string",
                "format": "uuid",
                "description": "Project UUID (required)"
            },
            "force_reindex": {
                "type": "boolean",
                "default": false
            }
        },
        "required": ["repo_path", "project_id"]
    },
    "returns": {
        "type": "object",
        "properties": {
            "repository_id": {"type": "string"},
            "files_indexed": {"type": "integer"},
            "chunks_created": {"type": "integer"},
            "duration_seconds": {"type": "number"}
        }
    }
}
```

### Helper: get_active_project
```python
async def get_active_project() -> Optional[str]:
    """
    Get active project ID with caching.

    Returns:
        Project UUID string if active project set, None otherwise

    Performance:
        - Cache hit: <5ms
        - Cache miss: <50ms (workflow-mcp call)

    Errors:
        Returns None if workflow-mcp unavailable (graceful degradation)
    """
```

---

## 6. Data Models

### Table: repositories (modified)
```sql
CREATE TABLE repositories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    path TEXT NOT NULL,
    project_id UUID REFERENCES projects(id),  -- NEW
    indexed_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(path, project_id)  -- Same path can exist in multiple projects
);

CREATE INDEX idx_repositories_project_id ON repositories(project_id);
```

### Table: code_chunks (modified)
```sql
CREATE TABLE code_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID REFERENCES repositories(id),
    project_id UUID REFERENCES projects(id),  -- NEW (denormalized for query performance)
    file_path TEXT NOT NULL,
    content TEXT NOT NULL,
    start_line INTEGER,
    end_line INTEGER,
    embedding vector(768),
    created_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP  -- NEW (soft delete support)
);

CREATE INDEX idx_code_chunks_project_id ON code_chunks(project_id);
CREATE INDEX idx_code_chunks_project_embedding ON code_chunks(project_id, embedding)
    USING ivfflat(embedding vector_cosine_ops);  -- Composite index for filtered search
```

### Pydantic Model: SearchResult
```python
class SearchResult(BaseModel):
    chunk_id: str
    file_path: str
    content: str
    start_line: int
    end_line: int
    similarity_score: float
    project_id: str  # NEW
    context_before: Optional[str] = None
    context_after: Optional[str] = None

class SearchResults(BaseModel):
    results: list[SearchResult]
    total_count: int
    latency_ms: int
    project_id: str  # NEW (which project was searched)
```

---

## 7. Test Strategy

### MCP Protocol Compliance
- ✅ Tool registration validation (test_mcp_compliance.py)
- ✅ Request/response format tests
- ✅ Error format follows MCP spec (code -32602 for invalid params)
- ✅ No stdout/stderr pollution

### Basic Functionality
- ✅ Index repository with project_id → verify storage
- ✅ Search with project_id → verify results filtered
- ✅ Search without project_id → verify active project fallback

### Integration Tests
- ✅ Multi-project isolation (same code indexed in two projects)
- ✅ Project switching with cache invalidation
- ✅ Active project fallback with cache performance
- ✅ Project deletion soft-deletes indexed code

### Edge Cases
- ✅ Invalid project_id format → MCP error
- ✅ No project_id and no active project → MCP error
- ✅ Workflow-mcp unavailable → graceful degradation
- ✅ Concurrent indexing same project → transaction safety

### Performance Validation
- ✅ Search latency <500ms p95 (with project filtering)
- ✅ Cache hit latency <5ms
- ✅ Cache miss latency <50ms
- ✅ Index overhead per project <5% storage

### Test Automation
```bash
# Run all tests
pytest tests/ --asyncio-mode=auto

# Run only MCP compliance tests
pytest tests/test_mcp_compliance.py

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

**Test Execution Strategy:**
- Run after each phase completion (not every commit)
- Full test suite before PR creation
- Integration tests require workflow-mcp running (Docker Compose)

---

## 8. Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Search latency (with project filter) | <500ms | p95, 10K chunks |
| Search latency (cache hit) | <505ms | p95 (500ms + 5ms cache) |
| Search latency (cache miss) | <550ms | p95 (500ms + 50ms workflow call) |
| Index creation per project | <60s | 10K files per project |
| Project filter overhead | <5ms | Composite index scan |
| Cache hit rate | >90% | Steady-state operation |
| Index size overhead per project | <5% | Compared to single-project baseline |
| Project switching latency | <10ms | Cache invalidation |

**Validation:**
- Load test with 5 projects, 10K files each
- Measure p95 latency over 1000 search operations
- Verify cache hit rate in production-like scenarios

---

## 9. Error Handling

### Error Scenario 1: Invalid project_id format
**Condition:** project_id is not a valid UUID
**Response:** MCP error with code -32602 (Invalid params)
**User Message:**
```json
{
    "error": {
        "code": -32602,
        "message": "Invalid project_id format",
        "data": {
            "project_id": "not-a-uuid",
            "expected": "UUID string (e.g., '550e8400-e29b-41d4-a716-446655440000')"
        }
    }
}
```

### Error Scenario 2: No project specified and no active project
**Condition:** project_id not provided and get_active_project() returns None
**Response:** MCP error with code -32602
**User Message:**
```json
{
    "error": {
        "code": -32602,
        "message": "No project specified and no active project set",
        "data": {
            "parameter": "project_id",
            "suggestion": "Provide project_id explicitly or set active project via workflow-mcp"
        }
    }
}
```

### Error Scenario 3: Project not found
**Condition:** Valid UUID but project doesn't exist in database
**Response:** MCP error with code -32602
**User Message:**
```json
{
    "error": {
        "code": -32602,
        "message": "Project not found",
        "data": {
            "project_id": "550e8400-e29b-41d4-a716-446655440000",
            "suggestion": "Verify project exists via workflow-mcp"
        }
    }
}
```

### Error Scenario 4: workflow-mcp unavailable (cache miss)
**Condition:** get_active_project() cache miss and workflow-mcp call fails
**Response:** Graceful degradation, return None (not an error)
**Logging:** `logger.warning("Failed to get active project: {error}")`
**User Impact:** Subsequent search will require explicit project_id parameter

### Error Scenario 5: Database connection failure during search
**Condition:** PostgreSQL connection lost mid-query
**Response:** MCP error with code -32603 (Internal error)
**User Message:**
```json
{
    "error": {
        "code": -32603,
        "message": "Database connection failure",
        "data": {
            "retry": true,
            "suggestion": "Retry the operation. Contact support if issue persists."
        }
    }
}
```

### Error Scenario 6: Concurrent indexing same project
**Condition:** Two index_repository calls for same project_id
**Response:** Second call blocks until first completes (transaction-level locking)
**Logging:** `logger.info("Concurrent indexing detected, queuing operation")`
**Performance:** May exceed 60s target if queue builds up

---

## 10. Dependencies

### Task Dependencies
```
T001 (migration) → T008 (index_repository update)
T002 (cache impl) → T006, T007 (cache tests + usage)
T003, T004 (tests RED) → T005 (search_code GREEN)
T006 (test RED) → T007 (get_active_project GREEN)
T007 (get_active_project) → T005 (search_code uses it)
T001, T002, T005, T007, T008 → T009, T010, T011 (integration tests)
```

### External Dependencies
- **workflow-mcp:** Must provide get_project_configuration tool
  - MCP contract: `{"current_session_id": "uuid" | null}`
  - Communication: stdio-based MCP (FastMCP server)
  - Failure mode: Graceful degradation (cache miss returns None)

### Dependency Resolution
- **Phase 1:** No external dependencies (database only)
- **Phase 2:** Requires workflow-mcp running for T007 (can stub for unit tests)
- **Phase 3:** Requires workflow-mcp for integration tests (Docker Compose)

### Parallel Execution Dependencies
```
PARALLEL:
- T001 (migration) || T002 (cache impl) || T003 (test RED) || T004 (test RED)
- Phase 3 integration tests (different files)

SEQUENTIAL:
- T005 depends on T003, T004 (tests first)
- T007 depends on T002, T006 (cache first, then usage)
- T008 depends on T001 (schema first)
```

---

## 11. Acceptance Criteria

- [x] **AC1:** search_code filters results by project_id
  - Verified by: test_search_respects_project_isolation

- [x] **AC2:** search_code falls back to active project if project_id not provided
  - Verified by: test_active_project_fallback

- [x] **AC3:** search_code returns MCP error if no project context
  - Verified by: test_search_with_no_project_context

- [x] **AC4:** index_repository requires project_id parameter
  - Verified by: Updated tool signature and schema tests

- [x] **AC5:** Multi-project isolation enforced (no cross-project leakage)
  - Verified by: test_search_respects_project_isolation

- [x] **AC6:** Search latency <500ms p95 with project filtering
  - Verified by: Performance test with 5 projects, 10K files each

- [x] **AC7:** Active project cache reduces overhead to <5ms
  - Verified by: test_get_active_project_with_cache_hit

- [x] **AC8:** Project deletion soft-deletes indexed code
  - Verified by: test_project_deletion_soft_deletes_indexed_code

- [x] **AC9:** MCP protocol compliance (tool schema, error format)
  - Verified by: test_mcp_compliance.py suite

- [x] **AC10:** Backward compatible (single-project workflows still work)
  - Verified by: Legacy tests updated with default project_id

---

## 12. Token Budget

**Total Estimated:** 52,000 tokens (26% of default 200K budget)

### Phase 1: Database Schema & Migration
- T001 (migration): ~3K tokens (SQL + rollback)
- T002 (cache impl): ~2K tokens (class + tests)
- **Subtotal:** ~5K tokens

### Phase 2: Test-Driven Development
- T003 (integration test): ~2K tokens
- T004 (validation test): ~1.5K tokens
- T005 (search_code update): ~8K tokens (logic + error handling)
- T006 (cache test): ~2K tokens
- T007 (get_active_project): ~5K tokens (cache + workflow-mcp call)
- T008 (index_repository): ~6K tokens (parameter + validation)
- **Subtotal:** ~24.5K tokens

### Phase 3: Integration Tests & Edge Cases
- T009 (switching test): ~2K tokens
- T010 (edge case test): ~1.5K tokens
- T011 (deletion test): ~3K tokens
- T012 (MCP compliance): ~2K tokens
- **Subtotal:** ~8.5K tokens

### Documentation & Reviews
- Planning artifacts: ~8K tokens
- Code reviews: ~6K tokens
- **Subtotal:** ~14K tokens

**Buffer:** 10% (~5K tokens) for unexpected complexity

---

## 13. Complexity Tracking

### Constitutional Principle Compliance

| Principle | Compliance | Notes |
|-----------|------------|-------|
| 1. Simplicity Over Features | ✅ | Focused on multi-project, no feature creep |
| 2. Local-First Architecture | ✅ | No cloud dependencies |
| 3. Protocol Compliance | ✅ | MCP error format specified |
| 4. Performance Guarantees | ✅ | Cache ensures <500ms target |
| 5. Production Quality | ✅ | Comprehensive error handling |
| 6. Specification-First | ✅ | Plan follows spec.md |
| 7. Test-Driven Development | ✅ | RED-GREEN-REFACTOR enforced |
| 8. Pydantic Type Safety | ✅ | All models use Pydantic |
| 10. Git Micro-Commit | ✅ | One task = one commit |
| 11. FastMCP Foundation | ✅ | Tools use FastMCP decorators |

### Complexity Justifications

**Added Complexity: Project Cache**
- **Justification:** Required to meet <500ms search latency with workflow-mcp integration
- **Alternative Considered:** Require explicit project_id (no fallback)
- **Trade-off:** 200 LOC cache implementation vs. poor UX + performance risk
- **Constitutional Alignment:** Principle 4 (Performance Guarantees) takes precedence

**Added Complexity: Soft Delete**
- **Justification:** Production safety (accidental project deletion recovery)
- **Alternative Considered:** Hard delete (simpler)
- **Trade-off:** 50 LOC soft delete logic vs. data loss risk
- **Constitutional Alignment:** Principle 5 (Production Quality)

---

## 14. Commit Strategy

Each task maps to one commit following Conventional Commits:

```
T001 → feat(schema): add project_id columns for multi-project support
T002 → feat(cache): add project cache for active project resolution
T003 → test(search): add multi-project isolation integration test
T004 → test(search): add project_id validation tests
T005 → feat(search): add project_id filtering with MCP error handling
T006 → test(project): add active project cache performance test
T007 → feat(project): implement active project caching with <5ms overhead
T008 → refactor(indexing): add required project_id parameter
T009 → test(project): add project switching cache invalidation test
T010 → test(search): add edge case test for missing project context
T011 → test(lifecycle): add project deletion soft-delete test
T012 → test(mcp): add protocol compliance validation for search tool
```

**Verification After Each Commit:**
```bash
# Run relevant tests (not full suite)
pytest tests/test_multi_project_search.py -v

# Verify no regressions
pytest tests/ -k "search or project" --maxfail=1

# Git status clean
git status
```

---

## 15. Sign-Off Checklist

### Critical Issues Resolution
- [x] **C1 (Architectural):** Active project caching added (ProjectCache class)
- [x] **A1 (Architectural):** MCP error format specified for all errors
- [x] **A2 (Architectural):** TDD task order enforced (tests before impl)
- [x] **Issue 1 (Planning):** Task descriptions clarified with signatures
- [x] **Issue 2 (Planning):** Edge case test added (T010)

### Important Issues Resolution
- [x] **I1 (Architectural):** T001, T002 merged into focused tasks
- [x] **I2 (Architectural):** T006/T007 dependency corrected
- [x] **Issue 3 (Planning):** Project deletion strategy documented (T011)

### Suggestions Implementation
- [x] Commit message examples added to all tasks
- [x] Token budget estimate added (~52K)
- [x] Index size overhead metric added (<5%)
- [x] Performance validation strategy documented

### Final Validation
- [x] All spec requirements mapped to tasks
- [x] All acceptance criteria covered
- [x] Constitutional principles compliant
- [x] Tech stack approved (Python, PostgreSQL, FastMCP)
- [x] On-rails workflow followed (branch, spec, plan, tasks)
- [x] Performance targets realistic and measurable
- [x] Test strategy minimal but sufficient

---

## Approval

**Plan Status:** ✅ APPROVED FOR IMPLEMENTATION
**Constitutional Compliance:** 10/10 (all principles satisfied)
**Planning Quality:** 9.5/10 (all critical issues resolved)
**Ready for `/tasks` Command:** Yes

**Next Steps:**
1. Run `/tasks` to generate tasks.md from this plan
2. Review tasks.md for dependency ordering
3. Run `/implement` to execute task plan
4. Follow git micro-commit strategy (one commit per task)

**Estimated Implementation Time:** 4-6 hours (developer hours)
**Estimated Token Usage:** 52K tokens (26% of budget)

---

*Plan finalized: 2025-10-11*
*Reviewed by: Initial Plan, Planning Review, Architectural Review subagents*
*Approved by: Orchestrator*
```

### Quality Gates

Before marking Step 4 complete, validate:

#### All Critical Issues Addressed
- [ ] Every CRITICAL from Step 3 has resolution in plan
- [ ] Every CRITICAL from Step 2 has resolution in plan
- [ ] Resolutions are specific and actionable (not vague)

#### Integration Quality
- [ ] No contradictions between Step 2 and Step 3 feedback
- [ ] All IMPORTANT issues from both reviews addressed
- [ ] Revision summary documents all changes clearly

#### Constitutional Compliance
- [ ] All principles scored 10/10 (or justified deviations)
- [ ] Tech stack unchanged (no new dependencies)
- [ ] Performance targets meet or exceed baselines

#### Implementation Readiness
- [ ] Task descriptions actionable (no ambiguity)
- [ ] Dependencies explicit and correct
- [ ] Commit messages mapped to tasks
- [ ] Test strategy complete
- [ ] Acceptance criteria measurable

### Execution Guidelines

**Inputs:**
- `initial-plan.md` (Step 1)
- `planning-review.md` (Step 2)
- `architectural-review.md` (Step 3)
- `spec.md` (original requirements)

**Process:**
1. Read all three review documents thoroughly
2. Create resolution list (CRITICAL first, then IMPORTANT)
3. Apply resolutions to initial plan structure
4. Document what changed and why in revision summary
5. Validate all feedback addressed (checklist)
6. Add sign-off checklist at end
7. Request final orchestrator approval

**Time Budget:** 20-25 minutes
**Output Location:** `specs/###-feature/plan.md` (final)

---

## Parallel Execution Strategy

### Codebase-MCP Track
```
Step 1: Initial Plan (20 min) →
  ├→ Step 2: Planning Review (15 min) ──┐
  └→ Step 3: Architectural Review (15 min)─┤
                                           ├→ Step 4: Final Plan (25 min)
                                           ┘
Total: ~75 minutes (sequential: Step 1 → Steps 2+3 parallel → Step 4)
```

### Workflow-MCP Track
```
Step 1: Initial Plan (20 min) →
  ├→ Step 2: Planning Review (15 min) ──┐
  └→ Step 3: Architectural Review (15 min)─┤
                                           ├→ Step 4: Final Plan (25 min)
                                           ┘
Total: ~75 minutes (sequential: Step 1 → Steps 2+3 parallel → Step 4)
```

### Orchestrator Workflow
```
Launch Codebase-MCP Step 1 (subagent A) ||
Launch Workflow-MCP Step 1 (subagent B)
  ↓
Wait for both Step 1 outputs (barrier)
  ↓
Launch Codebase-MCP Step 2 (subagent C) ||
Launch Codebase-MCP Step 3 (subagent D) ||
Launch Workflow-MCP Step 2 (subagent E) ||
Launch Workflow-MCP Step 3 (subagent F)
  ↓
Wait for all Step 2+3 outputs (barrier)
  ↓
Launch Codebase-MCP Step 4 (subagent G) ||
Launch Workflow-MCP Step 4 (subagent H)
  ↓
Wait for both Step 4 outputs (barrier)
  ↓
Both final plans ready for /tasks
```

**Total Time:** ~75 minutes (vs 150 minutes sequential)
**Parallelism:** 2x speedup on Step 1, 4x speedup on Steps 2-3

---

## Quality Comparison Examples

### Example 1: Good Initial Plan Task

```markdown
#### T005: Update search_code to filter by project_id (GREEN)
```python
# src/tools/search_code.py
@mcp.tool()
async def search_code(
    query: str,
    project_id: Optional[str] = None,
    limit: int = 10
) -> SearchResults:
    """Search codebase with project isolation."""
    # Resolve project_id if not provided
    if project_id is None:
        project_id = await get_active_project()
        if project_id is None:
            raise McpError(
                code=-32602,
                message="No project specified and no active project set",
                data={"parameter": "project_id"}
            )

    # Execute search with project filter
    results = await db.fetch(
        "SELECT * FROM code_chunks WHERE project_id = $1 AND embedding <=> $2 < 0.3",
        project_id, query_embedding
    )
    return {"results": results}
```
**Acceptance:**
- MCP error format specified
- Fallback logic clear
- SQL query included
- Parameter types explicit
```

**Why Good:**
- ✅ Specific implementation details (actual code)
- ✅ MCP error format with exact code and structure
- ✅ Clear acceptance criteria
- ✅ Actionable (developer can implement without questions)

### Example 2: Poor Initial Plan Task

```markdown
#### T005: Update search tool
Update the search_code function to support multiple projects.
Handle errors appropriately.
```

**Why Poor:**
- ❌ No implementation details (what parameters? what logic?)
- ❌ "Handle errors appropriately" is vague
- ❌ No acceptance criteria
- ❌ Developer will need to make many assumptions

---

## Summary

The 4-step review process ensures:
1. **Step 1:** Comprehensive initial plan with all technical details
2. **Step 2:** Planning review catches gaps, ambiguities, missing requirements
3. **Step 3:** Architectural review enforces constitutional compliance
4. **Step 4:** Final plan integrates all feedback for implementation-ready output

**Key Success Factors:**
- Clear separation of concerns (planning vs architecture)
- Parallel execution where possible (Steps 2-3)
- Specific, actionable feedback (not vague suggestions)
- Constitutional compliance as non-negotiable
- Final plan is complete and unambiguous

**Time Efficiency:**
- Total time: ~75 minutes per MCP track
- Parallel tracks: Both MCPs reviewed simultaneously
- Quality: High (rigorous review prevents implementation rework)
