# /specify Prompt: Phase 03 - Multi-Project Support

## AI Agent Instructions

You are generating a feature specification (spec.md) for **multi-project workspace support** in the codebase-mcp server. This specification must capture WHAT users need and WHY it matters, without dictating HOW to implement it.

### Pre-Flight Validation

Before generating spec.md, verify:

1. **Constitution exists**: `.specify/memory/constitution.md` contains project principles
2. **Feature scope confirmed**: This is ONE feature (multi-project isolation), not multiple features
3. **User context clear**: Multiple personas with distinct multi-project needs identified
4. **Phase context understood**: This is Phase 03 of a larger refactoring initiative

If any validation fails, request clarification before proceeding.

---

## Feature Context

### Original User Request

Users working on multiple codebases need to keep them isolated - searching one project should never return results from another project. Currently, the codebase-mcp server can only index and search a single codebase. Users need the ability to maintain multiple projects simultaneously without data contamination or complex manual database management.

### User Personas

**Persona 1: Full-Stack Developer (Primary)**
- Manages 3-5 codebases simultaneously (frontend, backend, shared libraries)
- Switches between projects multiple times daily
- Needs instant context switching without cross-contamination
- Technical proficiency: High

**Persona 2: Consultant with Multiple Clients**
- Maintains 5-10 client projects simultaneously
- Requires strict isolation for confidentiality
- Needs quick project switching during client calls
- Technical proficiency: Medium-High

**Persona 3: Engineering Manager**
- Oversees multiple team projects
- Reviews code across different repositories
- Concerned with infrastructure costs and team efficiency
- Technical proficiency: Medium

**Persona 4: Workflow Automation User**
- Uses workflow-mcp for project management
- Expects automatic project detection
- Values seamless integration between tools
- Technical proficiency: Medium

### Business Value

- **Enables Multi-Tenant Usage**: Multiple users/teams share infrastructure without conflicts
- **Reduces Infrastructure Costs**: Single server instance supports multiple projects
- **Simplifies User Workflow**: No manual database management or complex configuration
- **Supports Modern Development**: Context switching for multi-repo workflows
- **Foundation for Future Features**: Enables project-specific settings, analytics, collaboration

---

## Required spec.md Structure

Generate a complete spec.md file with these EIGHT MANDATORY SECTIONS:

### 1. Feature Metadata

```markdown
# Feature: Multi-Project Workspace Support

Branch: 003-multi-project-support | Date: [YYYY-MM-DD] | Status: Draft

## Original User Description
[Paste the original user request verbatim from Feature Context above]
```

### 2. User Scenarios & Testing

**THIS IS MANDATORY** - Document concrete user workflows step-by-step.

#### Primary Workflow: Multi-Project Development

```
1. Developer starts work on client-a project
2. System [provides isolated workspace for client-a]
3. Developer indexes client-a codebase
4. System [stores client-a code in isolated workspace]
5. Developer searches for "authentication logic" in client-a
6. System [returns only client-a results, zero cross-contamination]
7. Developer switches to client-b project
8. System [switches to client-b isolated workspace]
9. Developer searches for "authentication logic" in client-b
10. System [returns only client-b results, different from client-a]
11. Developer verifies no cross-contamination between projects
12. System [confirms complete isolation via testing]
```

#### Alternative Path: Workflow Automation Integration

```
IF workflow-mcp is available:
  1. Developer does not specify project identifier
  2. System queries workflow-mcp for active project
  3. System uses active project context automatically
  4. Developer continues without manual project specification
ELSE:
  1. System uses default project workspace
  2. Developer continues with backward-compatible behavior
```

#### Alternative Path: New Project Creation

```
1. Developer specifies new project identifier for first time
2. System detects project workspace does not exist
3. System validates appropriate permissions exist
4. System creates isolated workspace automatically
5. Developer indexes first repository into new project
6. System confirms workspace ready for use
```

#### Edge Case Workflows

Document how system behaves in these scenarios:

**Empty State - No Projects Yet**
- Scenario: First-time user with no existing projects
- Behavior: System uses default project workspace automatically
- Recovery: Developer can create additional projects as needed

**Boundary Condition - Maximum Project Identifier Length**
- Scenario: Developer provides 50-character project identifier (maximum)
- Behavior: System accepts and creates workspace successfully
- Recovery: N/A (valid input)

**Boundary Condition - Exceeds Maximum Length**
- Scenario: Developer provides 51+ character project identifier
- Behavior: System rejects with clear message: "Project identifier must be 50 characters or less"
- Recovery: Developer shortens identifier and retries

**Error Scenario - Invalid Characters in Identifier**
- Scenario: Developer provides "My_Project" (uppercase and underscore)
- Behavior: System rejects with message: "Project identifiers must be lowercase alphanumeric with hyphens only"
- Recovery: Developer corrects to "my-project" format

**Error Scenario - Permission Denied**
- Scenario: System lacks permission to create new project workspace
- Behavior: System displays error: "Cannot create project workspace - insufficient permissions. Contact administrator."
- Recovery: Administrator grants required permissions, developer retries

**Error Scenario - Workflow Integration Timeout**
- Scenario: workflow-mcp query exceeds timeout threshold
- Behavior: System logs timeout, falls back to default project workspace
- Recovery: Developer continues with default workspace, can manually specify project

**Error Scenario - Workflow Integration Unavailable**
- Scenario: workflow-mcp server not accessible
- Behavior: System detects unavailability, falls back to default project workspace
- Recovery: Developer continues with default workspace or manual specification

**Concurrent Operation - Simultaneous Project Creation**
- Scenario: Two developers create same project identifier simultaneously
- Behavior: System handles race condition gracefully (first succeeds, second reuses)
- Recovery: Both developers use same project workspace (intended behavior)

**Security Scenario - SQL Injection Attempt**
- Scenario: Developer provides malicious project identifier: `"project'; DROP TABLE--"`
- Behavior: System validation rejects before any database operations
- Recovery: System logs security event, developer must use valid identifier

### 3. Functional Requirements

Number each requirement (FR-001, FR-002...). Use MUST/SHOULD/MAY modal verbs. Keep technology-agnostic.

**FR-001**: System MUST accept optional project identifier parameter for indexing operations
- Acceptance Criteria: Indexing operation accepts project identifier without error
- Traces to: Primary Workflow step 3

**FR-002**: System MUST accept optional project identifier parameter for search operations
- Acceptance Criteria: Search operation accepts project identifier without error
- Traces to: Primary Workflow step 5

**FR-003**: System MUST provide default project workspace when no identifier specified
- Acceptance Criteria: Operations without project identifier use consistent default workspace
- Traces to: Alternative Path (workflow integration ELSE clause)

**FR-004**: System MUST validate project identifiers before use
- Acceptance Criteria: Invalid identifiers rejected with clear error messages
- Traces to: Edge Case (invalid characters)

**FR-005**: System MUST enforce lowercase alphanumeric with hyphen format for identifiers
- Acceptance Criteria: Uppercase, underscore, spaces, special characters rejected
- Traces to: Edge Case (invalid characters scenario)

**FR-006**: System MUST enforce maximum 50-character length for identifiers
- Acceptance Criteria: Identifiers of 51+ characters rejected with helpful error
- Traces to: Edge Case (exceeds maximum length)

**FR-007**: System MUST prevent identifiers starting or ending with hyphens
- Acceptance Criteria: "-project" and "project-" rejected, "my-project" accepted
- Traces to: Validation rules

**FR-008**: System MUST prevent consecutive hyphens in identifiers
- Acceptance Criteria: "my--project" rejected, "my-project" accepted
- Traces to: Validation rules

**FR-009**: System MUST create isolated workspace for each unique project identifier
- Acceptance Criteria: Data indexed in project-a never appears in project-b searches
- Traces to: Primary Workflow steps 4, 6, 10

**FR-010**: System MUST automatically provision workspace on first use
- Acceptance Criteria: New project identifier triggers workspace creation without manual steps
- Traces to: Alternative Path (new project creation)

**FR-011**: System MUST validate required permissions before workspace creation
- Acceptance Criteria: Permission check occurs before creation attempt, clear error if insufficient
- Traces to: Edge Case (permission denied)

**FR-012**: System SHOULD query workflow-mcp for active project when available
- Acceptance Criteria: If workflow-mcp accessible, system retrieves active project context
- Traces to: Alternative Path (workflow automation integration)
- [NEEDS CLARIFICATION: Should workflow-mcp integration be mandatory or optional? Optional enables standalone operation but reduces automation for users who have workflow-mcp. Recommendation: Optional for maximum flexibility.]

**FR-013**: System MUST gracefully handle workflow-mcp unavailability
- Acceptance Criteria: Workflow-mcp timeout/unavailability falls back to default workspace without errors
- Traces to: Edge Cases (timeout, unavailable)

**FR-014**: System MUST categorize workflow-mcp integration failures
- Acceptance Criteria: Distinct error types (unavailable, timeout, invalid response) logged for troubleshooting
- Traces to: Alternative Path (workflow integration ELSE clause)

**FR-015**: System SHOULD cache workflow-mcp responses temporarily
- Acceptance Criteria: Repeated queries within short time window reuse cached result
- Traces to: Persona 4 (workflow automation user) efficiency needs
- [NEEDS CLARIFICATION: What cache duration balances freshness vs. efficiency? Recommendation: 1 minute based on typical context-switching patterns.]

**FR-016**: System MUST prevent security vulnerabilities via identifier validation
- Acceptance Criteria: SQL injection attempts blocked, malicious identifiers rejected
- Traces to: Edge Case (SQL injection attempt)

**FR-017**: System MUST maintain complete data isolation between projects
- Acceptance Criteria: Integration test confirms zero cross-project data leakage
- Traces to: Primary Workflow step 11, Persona 2 (consultant confidentiality)

**FR-018**: System MUST support backward compatibility for existing users
- Acceptance Criteria: Existing usage without project identifiers continues working unchanged
- Traces to: FR-003 (default workspace), business value (no breaking changes)

### 4. Success Criteria

Define measurable, technology-agnostic outcomes.

#### Quantitative Metrics

- **Isolation Guarantee**: 100% of cross-project searches return zero results from other projects (verified via integration tests)
- **Validation Effectiveness**: 100% of invalid project identifiers rejected before operations
- **Permission Detection**: System detects insufficient permissions before failed operations in 100% of cases
- **Workflow Integration Success Rate**: When workflow-mcp available, system retrieves active project in 100% of attempts (excluding timeouts)
- **Fallback Reliability**: System falls back to default workspace in 100% of workflow-mcp failure scenarios
- **Security Coverage**: 100% of SQL injection test cases blocked by validation

#### Qualitative Measures

- **User Workflow Simplification**: Full-stack developers complete project switches without manual database operations
- **Consultant Confidence**: Consultants trust complete isolation for client confidentiality
- **Manager Satisfaction**: Engineering managers achieve multi-team support with single infrastructure instance
- **Automation Seamlessness**: Workflow-mcp users experience automatic project detection when available
- **Error Clarity**: Users understand validation errors and can correct identifiers without support tickets

### 5. Key Entities

**Entity: Project Workspace**

- **Purpose**: Represents an isolated environment for a single codebase or logical project grouping
- **Lifecycle**:
  - Created: Automatically on first use of a new project identifier
  - Updated: Implicitly when repositories indexed or searches performed
  - Deleted: [NEEDS CLARIFICATION: How should users remove old project workspaces? Manual cleanup, automatic archival after inactivity period, or explicit deletion API? Recommendation: Out of scope for this phase, address in future management features.]
- **Key Attributes**:
  - **Identifier**: Unique string identifying the workspace (lowercase alphanumeric with hyphens, max 50 chars)
  - **Isolation Boundary**: Workspace stores all indexed repositories and search indices independently
  - **Creation Timestamp**: When workspace first created (for future archival features)
- **Business Invariants**:
  - Identifier must remain immutable after creation (no renaming)
  - Complete isolation guarantee: no data sharing between workspaces
  - Default workspace always available for backward compatibility

**Entity: Project Identifier**

- **Purpose**: Validated string that uniquely names a project workspace
- **Lifecycle**:
  - Created: User provides identifier in indexing or search operation
  - Updated: Never (immutable)
  - Deleted: N/A (identifiers persist with workspaces)
- **Key Attributes**:
  - **Format**: Lowercase alphanumeric characters with hyphens only
  - **Length**: 1-50 characters inclusive
  - **Constraints**: Cannot start/end with hyphen, no consecutive hyphens
- **Business Invariants**:
  - Must pass validation before any operations
  - Same identifier always resolves to same workspace
  - Validation prevents security vulnerabilities

**Entity: Workflow Integration Context** (Optional)

- **Purpose**: Represents active project context from workflow-mcp when available
- **Lifecycle**:
  - Created: Queried from workflow-mcp on demand
  - Updated: Cached temporarily (recommended 1 minute)
  - Deleted: Cache expires after TTL
- **Key Attributes**:
  - **Active Project**: Current project identifier from workflow-mcp
  - **Cache Timestamp**: When value retrieved (for expiration calculation)
  - **Status**: Success, unavailable, timeout, invalid response
- **Business Invariants**:
  - Graceful degradation required (system works without workflow-mcp)
  - Cache must not serve stale values beyond TTL
  - Errors must not block user operations

### 6. Edge Cases & Error Handling

[Already documented in Section 2 workflows - cross-reference those scenarios here with user-facing behaviors]

**Empty States**
- See "Edge Case Workflows: Empty State - No Projects Yet"
- Behavior: System uses default workspace, enables immediate productivity

**Boundary Conditions**
- See "Edge Case Workflows: Maximum Project Identifier Length"
- See "Edge Case Workflows: Exceeds Maximum Length"
- Behavior: Clear validation messages guide users to valid formats

**Error Scenarios**
- See "Edge Case Workflows: Invalid Characters in Identifier"
- See "Edge Case Workflows: Permission Denied"
- See "Edge Case Workflows: Workflow Integration Timeout"
- See "Edge Case Workflows: Workflow Integration Unavailable"
- Behavior: Specific error messages with recovery guidance

**Permission Denials**
- See "Edge Case Workflows: Permission Denied"
- Behavior: Early detection with administrator escalation guidance

**Concurrent Operations**
- See "Edge Case Workflows: Simultaneous Project Creation"
- Behavior: Graceful race condition handling, idempotent operations

**Security Scenarios**
- See "Edge Case Workflows: SQL Injection Attempt"
- Behavior: Validation blocks attacks before database operations, security logging

### 7. Review & Acceptance Checklist

**Content Quality**:
- [ ] No implementation details (languages, frameworks, databases)
- [ ] Focused on user value and business needs
- [ ] Written for non-technical stakeholders
- [ ] All mandatory sections complete
- [ ] Terminology consistent throughout

**Requirement Completeness**:
- [ ] Maximum 3 [NEEDS CLARIFICATION] markers (or justified excess)
- [ ] All requirements testable and unambiguous
- [ ] User types and permissions explicitly defined
- [ ] Edge cases and error scenarios included
- [ ] Success criteria measurable and specific
- [ ] Each requirement traces to user story
- [ ] Non-functional requirements captured (isolation, security)

**Scope Clarity**:
- [ ] Feature boundaries clearly defined
- [ ] Out-of-scope items explicitly listed (see Non-Goals section)
- [ ] Dependencies identified (Phase 02 completion)
- [ ] Integration points specified (workflow-mcp optional)
- [ ] Assumptions documented

**Constitutional Compliance**:
- [ ] Aligns with Simplicity Over Features principle (focused on multi-project only)
- [ ] Follows Local-First Architecture (no cloud dependencies introduced)
- [ ] Respects Protocol Compliance (MCP tool parameter additions only)
- [ ] Adheres to Production Quality (comprehensive error handling specified)
- [ ] Compatible with Test-Driven Development (testable requirements)

### 8. Clarifications Section

[Leave empty initially - populated by /clarify command]

### 9. Non-Goals (Explicitly Out of Scope)

**Not Included in This Phase:**
- Connection pooling optimization (deferred to Phase 04)
- Performance tuning and benchmarking (deferred to Phase 06)
- Documentation updates and migration guides (deferred to Phase 05)
- Production deployment procedures (deferred to Phase 07)

**Explicitly NOT Doing:**
- Cross-project search (searching multiple projects simultaneously)
- Project management UI or CLI commands
- Project deletion, archival, or lifecycle management features
- Project configuration storage or metadata
- Project-specific settings or preferences
- Project sharing or permissions between users
- Project import/export capabilities
- Project statistics or analytics
- Historical project data or versioning
- Automatic project detection from Git repository names
- Project templates or initialization wizards

**Future Considerations** (Not This Phase):
- Project workspace cleanup and archival policies
- Cross-project analytics and reporting
- Team collaboration features (shared projects)
- Project-specific search configuration
- Project metadata storage (description, tags, owner)
- Project access control and permissions

---

## Specification Generation Guidelines

### The Golden Rule: WHAT/WHY vs. HOW

**YOU MUST NOT INCLUDE:**
- Programming languages, frameworks, or libraries
- Database schemas, table designs, or query patterns
- API implementation details (REST/GraphQL specifics)
- Code structure, class names, or algorithms
- File paths or directory structures
- Specific technology names (PostgreSQL, FastMCP, etc.)

**YOU MUST INCLUDE:**
- User interactions and workflows (step-by-step)
- Business rules and constraints (validation rules)
- Measurable success criteria (numbers, percentages)
- Error scenarios and recovery paths (user experience)
- Edge cases with user-facing behaviors
- Data entities and relationships (business meaning)

### Abstraction Examples

**Implementation Leak** (WRONG):
> "Database created with name codebase_<project_id> using PostgreSQL CREATE DATABASE command with asyncpg driver"

**Proper Abstraction** (CORRECT):
> "System automatically provisions isolated workspace for each project identifier on first use"

**Implementation Leak** (WRONG):
> "Add project_id parameter to index_repository() function in src/codebase_mcp/tools/index_repository.py"

**Proper Abstraction** (CORRECT):
> "System accepts optional project identifier when indexing repositories to direct storage to appropriate workspace"

**Implementation Leak** (WRONG):
> "Cache workflow-mcp response in TTLCache with 60-second expiration using cachetools library"

**Proper Abstraction** (CORRECT):
> "System temporarily remembers workflow integration context to reduce redundant lookups during active development sessions"

### Quality Self-Check

Before finalizing spec.md, verify:

```
- [ ] Zero programming languages mentioned
- [ ] Zero frameworks or libraries specified
- [ ] Zero database technologies referenced
- [ ] Zero file paths or code structure described
- [ ] User workflows described step-by-step with decision points
- [ ] All functional requirements testable with pass/fail criteria
- [ ] Success criteria use specific numbers and percentages
- [ ] Edge cases explicitly enumerated with user-facing behaviors
- [ ] [NEEDS CLARIFICATION] markers ≤ 3 (with valid justification)
- [ ] Non-technical stakeholder could understand every section
- [ ] Review checklist 100% addressable
- [ ] Constitutional principles respected throughout
```

---

## Post-Generation Actions

After generating spec.md:

1. **Self-validate** against quality checklist above
2. **Scan for leaks**: Search for tech terms (PostgreSQL, Python, FastMCP, asyncpg)
3. **Present summary** to user for review:
   ```
   Spec.md generated for Phase 03: Multi-Project Support

   - 18 functional requirements defined
   - 4 user personas documented
   - 10 edge case scenarios covered
   - 3 clarification markers for ambiguities
   - Complete isolation guaranteed for multi-tenant usage

   Recommend running /clarify to resolve marked ambiguities before /plan phase.
   ```
4. **Request approval** before proceeding to /plan
5. **Update status** to "Approved" once human validates

---

## Success Indicators

**This specification succeeds when:**
- Human reviewer approves without requesting major revisions
- Zero implementation details found during leak scan
- All requirements testable with clear pass/fail criteria
- Success criteria use specific, measurable numbers
- Edge cases cover realistic failure modes comprehensively
- Review checklist 100% complete and validated
- Constitutional compliance verified (all principles respected)
- User workflows enable test scenario design
- Clarification markers identify genuine ambiguities only
- Non-technical stakeholders understand user value

**This specification fails when:**
- Human requires complete regeneration
- Implementation details discovered (tech stack mentions)
- Vague requirements found ("fast", "good", "scalable")
- Generic edge cases auto-generated without context
- Success criteria subjective and unmeasurable
- Missing critical user workflows or scenarios
- Scope creep beyond multi-project isolation
- Technical jargon prevents non-technical understanding

---

## Constitutional Alignment Notes

This feature aligns with project constitution principles:

1. **Simplicity Over Features**: Focused exclusively on multi-project isolation, no feature creep
2. **Local-First Architecture**: No cloud dependencies introduced, local database per project
3. **Protocol Compliance**: Extends MCP tool interfaces without breaking protocol
4. **Performance Guarantees**: Design enables future optimization (Phase 06) without blocking this phase
5. **Production Quality**: Comprehensive error handling and validation specified throughout
6. **Specification-First Development**: This spec defines requirements before technical planning
7. **Test-Driven Development**: All requirements testable, enables test-first implementation

---

**END OF PROMPT**

Generate spec.md following this structure exactly. Maintain radical separation between WHAT users need (specification) and HOW to build it (implementation planning).
