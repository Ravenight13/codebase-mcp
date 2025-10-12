# /specify Prompt: Phase 05 - Documentation Overhaul & Migration Guide

## AI Agent Instructions

You are generating a feature specification (spec.md) for **documentation overhaul and migration guide creation** for the codebase-mcp server v2.0 refactoring. This specification must capture WHAT users need and WHY it matters, without dictating HOW to implement it.

### Pre-Flight Validation

Before generating spec.md, verify:

1. **Constitution exists**: `.specify/memory/constitution.md` contains project principles
2. **Feature scope confirmed**: This is ONE feature (documentation update for v2.0), not multiple features
3. **User context clear**: Multiple personas with distinct documentation needs identified
4. **Phase context understood**: This is Phase 05 of a larger refactoring initiative (depends on Phases 01-04)

If any validation fails, request clarification before proceeding.

---

## Feature Context

### Original User Request

After completing the codebase-mcp refactoring from 16 tools to 2 tools with multi-project support, all documentation must be updated to reflect the new architecture. Users upgrading from v1.x need clear migration instructions explaining breaking changes, step-by-step upgrade procedures, and rollback options. New users need accurate documentation showing the simplified 2-tool API with multi-project capabilities. All references to the 14 removed tools must be eliminated, and the new connection pooling architecture must be explained.

### User Personas

**Persona 1: Existing User Upgrading from v1.x (Primary)**
- Currently using codebase-mcp v1.x with 16 tools
- Needs to understand breaking changes and migration path
- Concerned about data preservation and rollback options
- Technical proficiency: Medium-High
- Pain Point: Breaking changes without clear migration guidance cause production issues

**Persona 2: New User Adopting v2.0**
- Discovering codebase-mcp for the first time
- Needs clear installation and quick-start instructions
- Expects accurate API documentation matching actual implementation
- Technical proficiency: Medium
- Pain Point: Outdated documentation creates confusion and delays adoption

**Persona 3: System Administrator Deploying v2.0**
- Responsible for production deployments and configuration
- Needs PostgreSQL configuration guidance for connection pooling
- Requires environment variable reference and tuning recommendations
- Technical proficiency: High
- Pain Point: Missing configuration guidance leads to suboptimal deployments

**Persona 4: Developer Integrating with workflow-mcp**
- Building on top of codebase-mcp with workflow-mcp integration
- Needs architecture diagrams explaining multi-project design
- Wants example usage patterns for both standalone and integrated modes
- Technical proficiency: High
- Pain Point: Lack of integration examples slows development

**Persona 5: Maintainer Contributing to Project**
- Contributing code or documentation improvements
- Needs architecture documentation to understand system design
- Requires development setup and testing procedures
- Technical proficiency: Very High
- Pain Point: Missing architecture docs increase onboarding time

### Business Value

- **Reduces Support Burden**: Clear migration guide prevents upgrade issues and support tickets
- **Accelerates Adoption**: Accurate documentation enables faster new user onboarding
- **Improves Production Deployments**: Configuration guidance prevents performance issues
- **Enables Ecosystem Growth**: Integration examples help developers build on top of codebase-mcp
- **Lowers Maintenance Costs**: Updated docs reduce contributor onboarding time
- **Builds User Trust**: Professional documentation signals production-ready software

---

## Required spec.md Structure

Generate a complete spec.md file with these EIGHT MANDATORY SECTIONS:

### 1. Feature Metadata

```markdown
# Feature: Documentation Overhaul & Migration Guide for v2.0 Architecture

Branch: phase-05-docs-migration | Date: [YYYY-MM-DD] | Status: Draft

## Original User Description
[Paste the original user request verbatim from Feature Context above]
```

### 2. User Scenarios & Testing

**THIS IS MANDATORY** - Document concrete user workflows step-by-step.

#### Primary Workflow: Existing User Upgrades from v1.x

```
1. User reads README.md mentioning v2.0 release
2. System [provides clear indication of breaking changes]
3. User navigates to migration guide
4. System [presents breaking changes summary upfront]
5. User evaluates impact on existing setup
6. System [lists specific removed tools and schema changes]
7. User performs backup procedures
8. System [provides exact backup commands for database and config]
9. User executes upgrade steps sequentially
10. System [guides through version update, migration script, config changes]
11. User tests multi-project functionality
12. System [provides verification commands to confirm upgrade success]
13. User encounters issue and needs rollback
14. System [provides complete rollback procedure with data restoration]
```

#### Alternative Workflow: New User First-Time Installation

```
1. User discovers codebase-mcp project
2. System [presents clear overview in README.md: 2 tools, multi-project support]
3. User reviews installation requirements
4. System [lists PostgreSQL version, Python version, dependencies]
5. User executes installation steps
6. System [provides pip install command and verification]
7. User runs first indexing operation
8. System [shows example with default project_id]
9. User performs first search
10. System [shows example search with result interpretation]
11. User wants to create second project
12. System [demonstrates multi-project usage pattern]
```

#### Alternative Workflow: Administrator Configures Production Deployment

```
1. Administrator prepares production deployment
2. System [provides environment variable reference table]
3. Administrator reviews PostgreSQL requirements
4. System [specifies max_connections calculation formula]
5. Administrator tunes connection pool settings
6. System [explains MAX_PROJECTS and MAX_CONNECTIONS_PER_POOL tradeoffs]
7. Administrator configures monitoring
8. System [documents connection pool metrics and health indicators]
9. Administrator validates configuration
10. System [provides configuration validation checklist]
```

#### Alternative Workflow: Developer Integrates workflow-mcp

```
1. Developer wants automatic project detection
2. System [explains workflow-mcp integration in README.md]
3. Developer reviews integration architecture
4. System [provides architecture diagram showing integration]
5. Developer configures workflow-mcp connection
6. System [documents WORKFLOW_MCP_URL environment variable]
7. Developer tests automatic project context
8. System [shows example where project_id automatically detected]
9. Developer handles integration unavailability
10. System [documents fallback behavior to default project]
```

#### Edge Case Workflows

Document how system behaves in these scenarios:

**Empty State - Fresh v2.0 Installation**
- Scenario: New user with no previous codebase-mcp installation
- Behavior: README.md provides complete setup from scratch, no migration guide needed
- Recovery: N/A (standard installation flow)

**Version Detection - User on v1.x Tries v1.x Instructions**
- Scenario: User on v2.0 accidentally follows v1.x documentation
- Behavior: Commands fail with clear error indicating version mismatch
- Recovery: Documentation links to migration guide from error context

**Migration Interruption - Upgrade Fails Midway**
- Scenario: Migration script fails during execution (e.g., permission issue)
- Behavior: Migration guide explains how to diagnose failure and resume
- Recovery: Rollback procedure restores to v1.x, user fixes issue and retries

**Configuration Mismatch - Insufficient PostgreSQL Connections**
- Scenario: Administrator sets MAX_PROJECTS=20 but PostgreSQL max_connections=100
- Behavior: Configuration guide warns about calculation: 20 pools × 20 connections = 400 needed
- Recovery: Documentation provides formula and tuning guidance

**Documentation Discovery - User Can't Find Migration Guide**
- Scenario: User searches for "upgrade" or "migration" in documentation
- Behavior: README.md prominently links to migration guide in Breaking Changes section
- Recovery: Multiple entry points (README, CHANGELOG, release notes) point to guide

**API Reference Confusion - User Expects Removed Tool**
- Scenario: v1.x user looks for create_work_item in API docs
- Behavior: API reference clearly states "Removed in v2.0 - see migration guide"
- Recovery: Migration guide explains removal rationale and workflow-mcp alternative

**Environment Variable Error - User Forgets New Required Variable**
- Scenario: User upgrades without adding MAX_PROJECTS to .env
- Behavior: Server uses default value (10), documented clearly in config guide
- Recovery: Configuration guide lists all variables with defaults and descriptions

**Architecture Misunderstanding - User Expects Single Database**
- Scenario: User searches PostgreSQL for "codebase_mcp" database after indexing project "my-app"
- Behavior: Architecture documentation explains database-per-project naming: codebase_my-app
- Recovery: Documentation provides database naming convention and discovery commands

**Integration Timeout - workflow-mcp Unavailable**
- Scenario: User expects automatic project detection but workflow-mcp down
- Behavior: README.md documents fallback to default project with clear error message
- Recovery: Configuration guide explains timeout settings and fallback behavior

**Rollback Validation - User Unsure if Rollback Successful**
- Scenario: User executed rollback procedure but uncertain about success
- Behavior: Migration guide provides validation commands to verify v1.x restoration
- Recovery: Guide includes troubleshooting section for partial rollback scenarios

### 3. Functional Requirements

Number each requirement (FR-001, FR-002...). Use MUST/SHOULD/MAY modal verbs. Keep technology-agnostic.

#### Documentation Accuracy Requirements

**FR-001**: README.md MUST reflect accurate tool count (2 tools: index_repository, search_code)
- Acceptance Criteria: README lists exactly 2 tools with no references to removed tools
- Traces to: Persona 2 (new user) needs accurate quick-start

**FR-002**: README.md MUST explain multi-project support capability
- Acceptance Criteria: Overview section describes multi-project isolation and use cases
- Traces to: Alternative Workflow (new user creates second project)

**FR-003**: README.md MUST document workflow-mcp integration as optional feature
- Acceptance Criteria: Integration section clearly marked optional with standalone usage documented first
- Traces to: Alternative Workflow (developer integrates workflow-mcp)

**FR-004**: README.md MUST provide updated installation instructions matching v2.0 requirements
- Acceptance Criteria: Installation steps reference correct PostgreSQL configuration and Python dependencies
- Traces to: Alternative Workflow (new user first-time installation)

**FR-005**: API documentation MUST document index_repository with project_id parameter
- Acceptance Criteria: Tool signature shows project_id as optional parameter with default behavior explained
- Traces to: Persona 2 (new user) needs accurate API reference

**FR-006**: API documentation MUST document search_code with project_id parameter
- Acceptance Criteria: Tool signature shows project_id as optional parameter with default behavior explained
- Traces to: Persona 2 (new user) needs accurate API reference

**FR-007**: API documentation MUST remove all references to 14 deleted tools
- Acceptance Criteria: Zero mentions of removed tools in API docs (or marked as "Removed in v2.0")
- Traces to: Edge Case (user expects removed tool)

**FR-008**: Documentation MUST provide list of removed tools with v2.0 removal noted
- Acceptance Criteria: Migration guide lists all 14 removed tools by name
- Traces to: Persona 1 (upgrading user) needs breaking changes clarity

#### Migration Guide Requirements

**FR-009**: Migration guide MUST explain breaking changes upfront before procedures
- Acceptance Criteria: First section lists all breaking changes with impact summary
- Traces to: Primary Workflow step 4 (breaking changes summary)

**FR-010**: Migration guide MUST list all 14 removed tools explicitly
- Acceptance Criteria: Complete list with tool names and brief purpose descriptions
- Traces to: Primary Workflow step 6 (specific removed tools listed)

**FR-011**: Migration guide MUST explain database schema changes (9 tables dropped, project_id added)
- Acceptance Criteria: Schema changes documented with before/after table lists
- Traces to: Primary Workflow step 6 (schema changes listed)

**FR-012**: Migration guide MUST document API changes (project_id parameter added to both tools)
- Acceptance Criteria: API changes section shows parameter additions with examples
- Traces to: Persona 1 (upgrading user) needs API change awareness

**FR-013**: Migration guide MUST list new environment variables required for v2.0
- Acceptance Criteria: Environment variable changes documented with defaults
- Traces to: Edge Case (user forgets new required variable)

**FR-014**: Migration guide MUST provide step-by-step upgrade procedure
- Acceptance Criteria: Sequential numbered steps from backup through validation
- Traces to: Primary Workflow steps 7-12 (upgrade procedure)

**FR-015**: Migration guide MUST include backup procedures before upgrade
- Acceptance Criteria: Exact commands for database backup and configuration backup provided
- Traces to: Primary Workflow step 8 (backup commands)

**FR-016**: Migration guide MUST provide complete rollback procedure
- Acceptance Criteria: Rollback steps restore v1.x with data and configuration
- Traces to: Primary Workflow step 14 (rollback procedure)

**FR-017**: Migration guide MUST include validation steps to confirm successful upgrade
- Acceptance Criteria: Test commands provided to verify v2.0 functionality
- Traces to: Primary Workflow step 12 (verification commands)

**FR-018**: Migration guide MUST document migration script execution procedure
- Acceptance Criteria: Alembic migration commands or SQL scripts provided with execution instructions
- Traces to: Primary Workflow step 10 (migration script guidance)

**FR-019**: Migration guide MUST explain data preservation guarantees
- Acceptance Criteria: Clear statement about what data preserved vs. what data lost
- Traces to: Persona 1 (upgrading user) concerned about data preservation

**FR-020**: Migration guide SHOULD provide estimated migration duration
- Acceptance Criteria: Time estimate provided based on database size and operations
- Traces to: Persona 1 (upgrading user) planning upgrade window

#### Configuration Guide Requirements

**FR-021**: Configuration guide MUST document all environment variables with defaults
- Acceptance Criteria: Table format with variable name, default value, description, example
- Traces to: Alternative Workflow (administrator configures production)

**FR-022**: Configuration guide MUST explain MAX_PROJECTS limit and implications
- Acceptance Criteria: Connection pool count calculation and PostgreSQL impact documented
- Traces to: Edge Case (configuration mismatch)

**FR-023**: Configuration guide MUST document MAX_CONNECTIONS_PER_POOL tuning guidance
- Acceptance Criteria: Tradeoffs explained with recommended values for different scenarios
- Traces to: Alternative Workflow (administrator tunes connection pool settings)

**FR-024**: Configuration guide MUST provide PostgreSQL max_connections calculation formula
- Acceptance Criteria: Formula documented: max_connections >= MAX_PROJECTS × MAX_CONNECTIONS_PER_POOL
- Traces to: Edge Case (insufficient PostgreSQL connections)

**FR-025**: Configuration guide MUST recommend PostgreSQL tuning parameters for production
- Acceptance Criteria: Recommended values for shared_buffers, effective_cache_size, work_mem provided
- Traces to: Alternative Workflow (administrator validates configuration)

**FR-026**: Configuration guide MUST document workflow-mcp integration variables
- Acceptance Criteria: WORKFLOW_MCP_URL and WORKFLOW_MCP_TIMEOUT documented with examples
- Traces to: Alternative Workflow (developer configures workflow-mcp connection)

**FR-027**: Configuration guide SHOULD provide configuration validation checklist
- Acceptance Criteria: Checklist covers all critical settings with validation commands
- Traces to: Alternative Workflow step 10 (configuration validation checklist)

#### Architecture Documentation Requirements

**FR-028**: Architecture docs MUST include multi-project architecture diagram
- Acceptance Criteria: Diagram shows connection pool manager, multiple databases, tool layer
- Traces to: Persona 4 (developer) needs architecture understanding

**FR-029**: Architecture docs MUST explain database-per-project naming strategy
- Acceptance Criteria: Naming convention documented with examples (codebase_default, codebase_my-app)
- Traces to: Edge Case (user expects single database)

**FR-030**: Architecture docs MUST document connection pool design and LRU eviction
- Acceptance Criteria: Pool lifecycle, MAX_PROJECTS enforcement, eviction behavior explained
- Traces to: Persona 5 (maintainer) needs implementation understanding

**FR-031**: Architecture docs SHOULD explain workflow-mcp integration architecture
- Acceptance Criteria: Diagram or description showing optional integration points
- Traces to: Alternative Workflow (developer reviews integration architecture)

#### Documentation Quality Requirements

**FR-032**: All documentation links MUST resolve without 404 errors
- Acceptance Criteria: Automated link checking passes for all internal and external links
- Traces to: Documentation quality standard

**FR-033**: All code examples MUST be tested and functional
- Acceptance Criteria: Example commands and code snippets verified working
- Traces to: Persona 2 (new user) frustrated by broken examples

**FR-034**: Documentation MUST use consistent terminology throughout
- Acceptance Criteria: Glossary or consistent term usage (e.g., "project" vs "workspace")
- Traces to: Documentation quality standard

**FR-035**: Documentation MUST follow project style guide if defined
- Acceptance Criteria: Markdown formatting, heading hierarchy, code block syntax consistent
- Traces to: Persona 5 (maintainer) contributing documentation improvements

### 4. Success Criteria

Define measurable, technology-agnostic outcomes.

#### Quantitative Metrics

- **Accuracy Guarantee**: 100% of documented tool names match actual implementation (2 tools only)
- **Completeness**: 100% of removed tools (14 total) documented in migration guide
- **Link Validity**: 0 broken links in all documentation files
- **Example Verification**: 100% of code examples tested and functional
- **Migration Coverage**: 100% of breaking changes documented with migration steps
- **Configuration Coverage**: 100% of environment variables documented with defaults
- **Rollback Reliability**: Migration guide provides complete rollback procedure (not partial)

#### Qualitative Measures

- **User Upgrade Success**: Existing users successfully upgrade from v1.x to v2.0 following guide without support tickets
- **New User Onboarding**: New users complete first indexing and search within 15 minutes of installation
- **Administrator Confidence**: System administrators deploy v2.0 to production with correct configuration on first attempt
- **Developer Integration**: Developers integrate workflow-mcp successfully using provided examples
- **Maintainer Contribution**: New contributors understand architecture and contribute improvements after reading docs
- **Documentation Professionalism**: Documentation perceived as production-ready by enterprise users

### 5. Key Entities

**Entity: Documentation Artifact**

- **Purpose**: Represents a specific documentation file or section that must be created or updated
- **Lifecycle**:
  - Created: When documentation written during Phase 05
  - Updated: When content revised for accuracy or completeness
  - Deleted: N/A (documentation persists)
- **Key Attributes**:
  - **Artifact Type**: README, migration guide, configuration guide, architecture doc, API reference
  - **Status**: Draft, reviewed, approved, published
  - **Version**: Documentation version tied to software version (v2.0 docs)
  - **Target Audience**: New user, upgrading user, administrator, developer, maintainer
- **Business Invariants**:
  - Must match actual implementation (no outdated content)
  - Must be validated before approval (link checking, example testing)
  - Must trace to user persona needs

**Entity: Migration Step**

- **Purpose**: Represents a discrete action in the upgrade procedure from v1.x to v2.0
- **Lifecycle**:
  - Created: When migration guide authored
  - Updated: When procedure refined based on testing
  - Deleted: N/A (steps remain in guide)
- **Key Attributes**:
  - **Step Number**: Sequential ordering (Step 1, Step 2, ...)
  - **Action Description**: What user must do (backup database, run migration script, etc.)
  - **Commands**: Exact commands to execute (for terminal steps)
  - **Validation**: How to confirm step succeeded
  - **Recovery**: What to do if step fails
- **Business Invariants**:
  - Steps must be sequential and complete (no missing steps)
  - Each step must be testable (validation criteria)
  - Rollback must reverse all steps (data preservation)

**Entity: Configuration Parameter**

- **Purpose**: Represents an environment variable or configuration setting users must understand
- **Lifecycle**:
  - Created: When parameter introduced in v2.0
  - Updated: When default value or behavior changes
  - Deleted: When parameter deprecated (not in v2.0)
- **Key Attributes**:
  - **Parameter Name**: Environment variable name (e.g., MAX_PROJECTS)
  - **Default Value**: Value used if not specified
  - **Description**: Purpose and impact of parameter
  - **Example Value**: Recommended value for common scenarios
  - **Related Parameters**: Other settings that interact (MAX_PROJECTS × MAX_CONNECTIONS_PER_POOL)
- **Business Invariants**:
  - Must match actual code implementation (accurate defaults)
  - Must explain consequences of changing (performance, resource usage)
  - Must provide formula for calculated settings (PostgreSQL max_connections)

### 6. Edge Cases & Error Handling

[Already documented in Section 2 workflows - cross-reference those scenarios here with user-facing behaviors]

**Empty States**
- See "Edge Case Workflows: Empty State - Fresh v2.0 Installation"
- Behavior: README provides complete setup, no migration complexity

**Version Mismatches**
- See "Edge Case Workflows: Version Detection - User on v1.x Tries v1.x Instructions"
- Behavior: Clear error messages guide to correct version documentation

**Migration Failures**
- See "Edge Case Workflows: Migration Interruption - Upgrade Fails Midway"
- Behavior: Guide explains diagnosis and resume/rollback options

**Configuration Errors**
- See "Edge Case Workflows: Configuration Mismatch - Insufficient PostgreSQL Connections"
- See "Edge Case Workflows: Environment Variable Error - User Forgets New Required Variable"
- Behavior: Configuration guide provides validation formulas and defaults

**Documentation Discovery Issues**
- See "Edge Case Workflows: Documentation Discovery - User Can't Find Migration Guide"
- See "Edge Case Workflows: API Reference Confusion - User Expects Removed Tool"
- Behavior: Multiple entry points and clear removal notices

**Architecture Misunderstandings**
- See "Edge Case Workflows: Architecture Misunderstanding - User Expects Single Database"
- Behavior: Architecture docs explain multi-database design clearly

**Integration Problems**
- See "Edge Case Workflows: Integration Timeout - workflow-mcp Unavailable"
- Behavior: Documentation covers fallback behavior and timeout configuration

**Rollback Uncertainties**
- See "Edge Case Workflows: Rollback Validation - User Unsure if Rollback Successful"
- Behavior: Guide provides validation commands for rollback verification

### 7. Review & Acceptance Checklist

**Content Quality**:
- [ ] No implementation details (languages, frameworks, databases) in user-facing documentation
- [ ] Focused on user value and practical procedures
- [ ] Written for appropriate technical level per persona
- [ ] All mandatory sections complete
- [ ] Terminology consistent throughout

**Requirement Completeness**:
- [ ] Maximum 3 [NEEDS CLARIFICATION] markers (or justified excess)
- [ ] All requirements testable and unambiguous
- [ ] All personas addressed with relevant documentation
- [ ] Edge cases and error scenarios covered
- [ ] Success criteria measurable and specific
- [ ] Each requirement traces to user workflow
- [ ] Non-functional requirements captured (accuracy, completeness, quality)

**Scope Clarity**:
- [ ] Feature boundaries clearly defined (documentation only, no code changes)
- [ ] Out-of-scope items explicitly listed (see Non-Goals section)
- [ ] Dependencies identified (Phases 01-04 completion required)
- [ ] Integration documentation requirements specified (workflow-mcp examples)
- [ ] Assumptions documented

**Constitutional Compliance**:
- [ ] Aligns with Simplicity Over Features principle (documenting simplified 2-tool design)
- [ ] Follows Local-First Architecture (documenting local database setup)
- [ ] Respects Protocol Compliance (documenting MCP tool interfaces accurately)
- [ ] Adheres to Production Quality (comprehensive migration and configuration docs)
- [ ] Compatible with Specification-First Development (this spec before documentation writing)

### 8. Clarifications Section

[Leave empty initially - populated by /clarify command]

### 9. Non-Goals (Explicitly Out of Scope)

**Not Included in This Phase:**
- Performance benchmarking and validation (deferred to Phase 06)
- Release notes and changelog updates (deferred to Phase 07)
- Production deployment automation (deferred to Phase 07)
- User training materials or video tutorials (future consideration)

**Explicitly NOT Doing:**
- Code changes or bug fixes (Phase 05 is documentation only)
- New feature development or enhancements
- Performance optimization or tuning
- Database schema changes or migrations
- Test development or test coverage improvements

**Future Considerations** (Not This Phase):
- Interactive migration script with guided prompts
- Migration validation tool that checks prerequisites
- Automated documentation generation from code
- Documentation versioning and historical archives
- Multi-language documentation translations
- Video tutorials for upgrade procedures
- Chatbot or FAQ system for common questions
- Documentation analytics (most-viewed pages, search queries)

---

## Specification Generation Guidelines

### The Golden Rule: WHAT/WHY vs. HOW

**YOU MUST NOT INCLUDE:**
- Programming languages, frameworks, or libraries
- File paths or directory structures (except when documenting user-facing locations)
- Code implementation details or algorithms
- Database schemas or query patterns
- Specific technology names in requirements (acceptable in examples when documenting actual implementation)

**YOU MUST INCLUDE:**
- User workflows for each persona (step-by-step)
- Documentation requirements and completeness criteria
- Migration procedures with validation steps
- Configuration guidance with validation formulas
- Error scenarios and recovery procedures
- Measurable success criteria for documentation quality

### Abstraction Examples

**Implementation Leak** (WRONG):
> "Update README.md file at root of repository by editing markdown and committing to Git"

**Proper Abstraction** (CORRECT):
> "README must reflect accurate tool count and provide updated installation instructions matching v2.0 requirements"

**Implementation Leak** (WRONG):
> "Create docs/migration/v1-to-v2.md with markdown sections containing bash code blocks"

**Proper Abstraction** (CORRECT):
> "Migration guide must provide step-by-step upgrade procedure with backup commands, migration script execution, and rollback instructions"

**Implementation Leak** (WRONG):
> "Document asyncpg connection pool implementation details in architecture docs"

**Proper Abstraction** (CORRECT):
> "Architecture documentation must explain connection pool design, LRU eviction behavior, and MAX_PROJECTS enforcement"

### Quality Self-Check

Before finalizing spec.md, verify:

```
- [ ] Zero programming languages mentioned in requirements
- [ ] Zero frameworks or libraries specified
- [ ] File paths only mentioned for user-facing documentation locations
- [ ] User workflows described step-by-step for all personas
- [ ] All functional requirements testable with pass/fail criteria
- [ ] Success criteria use specific numbers and percentages
- [ ] Edge cases explicitly enumerated with user-facing behaviors
- [ ] [NEEDS CLARIFICATION] markers ≤ 3 (with valid justification)
- [ ] Technical writers or users could understand every requirement
- [ ] Review checklist 100% addressable
- [ ] Constitutional principles respected throughout
```

---

## Post-Generation Actions

After generating spec.md:

1. **Self-validate** against quality checklist above
2. **Scan for leaks**: Search for tech terms that shouldn't be in requirements
3. **Present summary** to user for review:
   ```
   Spec.md generated for Phase 05: Documentation Overhaul & Migration Guide

   - 35 functional requirements defined
   - 5 user personas documented
   - 10 edge case scenarios covered
   - 0 clarification markers (or list them if any)
   - Complete migration guide structure defined

   Recommend running /clarify if needed before /plan phase.
   ```
4. **Request approval** before proceeding to /plan
5. **Update status** to "Approved" once human validates

---

## Success Indicators

**This specification succeeds when:**
- Human reviewer approves without requesting major revisions
- Minimal implementation details found (acceptable in examples documenting real interfaces)
- All requirements testable with clear pass/fail criteria
- Success criteria use specific, measurable numbers
- Edge cases cover realistic documentation and migration scenarios
- Review checklist 100% complete and validated
- Constitutional compliance verified (all principles respected)
- User workflows enable documentation testing (example verification, link checking)
- All personas have relevant documentation requirements addressed
- Non-technical stakeholders understand migration value

**This specification fails when:**
- Human requires complete regeneration
- Requirements too vague ("good documentation", "clear migration")
- Generic edge cases auto-generated without context
- Success criteria subjective and unmeasurable
- Missing critical user workflows or personas
- Scope creep beyond documentation (includes code changes)
- Technical jargon prevents user comprehension

---

## Constitutional Alignment Notes

This feature aligns with project constitution principles:

1. **Simplicity Over Features**: Documents simplified 2-tool design without feature creep
2. **Local-First Architecture**: Documents local PostgreSQL setup and database-per-project design
3. **Protocol Compliance**: Accurately documents MCP tool interfaces
4. **Performance Guarantees**: Documents configuration tuning for optimal performance
5. **Production Quality**: Provides comprehensive migration and configuration guidance for production deployments
6. **Specification-First Development**: This spec defines documentation requirements before writing docs
7. **Test-Driven Development**: Documentation requirements testable (link checking, example verification)

---

**END OF PROMPT**

Generate spec.md following this structure exactly. Maintain radical separation between WHAT users need (specification) and HOW to build it (implementation planning).
