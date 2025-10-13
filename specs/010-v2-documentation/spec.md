# Feature: Documentation Overhaul & Migration Guide for v2.0 Architecture

**Feature Branch**: `010-v2-documentation`
**Created**: 2025-10-13
**Status**: Draft
**Input**: User description: "docs/mcp-split-plan/phases/phase-05-docs-migration/specify-prompt-enhanced.md"

## Original User Description

After completing the codebase-mcp refactoring from 16 tools to 2 tools with multi-project support, all documentation must be updated to reflect the new architecture. Users upgrading from v1.x need clear migration instructions explaining breaking changes, step-by-step upgrade procedures, and rollback options. New users need accurate documentation showing the simplified 2-tool API with multi-project capabilities. All references to the 14 removed tools must be eliminated, and the new connection pooling architecture must be explained.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Existing User Upgrades from v1.x (Priority: P1)

An existing codebase-mcp v1.x user discovers the v2.0 release and needs to upgrade their production system while minimizing risk and downtime. They need clear guidance on breaking changes, step-by-step procedures, data preservation, and rollback options.

**Why this priority**: This is P1 because existing users face breaking changes that could cause production issues without clear migration guidance. Poor upgrade documentation leads to support tickets, failed deployments, and user frustration.

**Independent Test**: Can be fully tested by following migration guide with a v1.x installation and verifying successful upgrade to v2.0 with indexed code repositories preserved and v2.0 functionality working. Delivers value by enabling safe production upgrades.

**Acceptance Scenarios**:

1. **Given** user is running codebase-mcp v1.x, **When** they read README.md, **Then** breaking changes are clearly indicated with link to migration guide
2. **Given** user opens migration guide, **When** they view first section, **Then** all breaking changes are summarized upfront before procedures
3. **Given** user reviews breaking changes, **When** they see removed tools section, **Then** all 14 removed tools are listed by name with descriptions
4. **Given** user prepares for upgrade, **When** they follow backup procedures, **Then** exact commands for database and configuration backup are provided
5. **Given** user executes upgrade steps, **When** they run migration script, **Then** clear execution instructions and expected outputs are documented
6. **Given** user completes upgrade, **When** they run verification commands, **Then** guide provides tests to confirm v2.0 functionality works
7. **Given** upgrade fails or user needs to revert, **When** they follow rollback procedure, **Then** complete restoration to v1.x with v1.x functionality and data intact is achieved
8. **Given** user validates rollback, **When** they run validation commands, **Then** guide confirms v1.x restoration successful

---

### User Story 2 - New User First-Time Installation (Priority: P2)

A developer discovering codebase-mcp for the first time needs to understand what it does, install it correctly, and perform their first indexing and search operations successfully within 15 minutes.

**Why this priority**: This is P2 because new user adoption drives ecosystem growth. Accurate, easy-to-follow documentation accelerates onboarding and builds user confidence in the project.

**Independent Test**: Can be fully tested by following README installation and quick-start sections with no prior codebase-mcp installation, completing first index and search successfully. Delivers value through rapid onboarding.

**Acceptance Scenarios**:

1. **Given** user discovers codebase-mcp repository, **When** they read README overview, **Then** clear description of 2 tools and multi-project support is presented
2. **Given** user reviews requirements, **When** they check installation section, **Then** PostgreSQL version, Python version, and dependencies are listed clearly
3. **Given** user installs codebase-mcp, **When** they execute installation commands, **Then** pip install command and verification steps work correctly
4. **Given** user performs first indexing, **When** they follow example command, **Then** default project behavior is explained and example works
5. **Given** user performs first search, **When** they execute search command, **Then** result format and interpretation guidance is provided
6. **Given** user wants multiple projects, **When** they follow multi-project example, **Then** project_id usage pattern is demonstrated clearly

---

### User Story 3 - Administrator Configures Production Deployment (Priority: P2)

A system administrator preparing a production deployment needs comprehensive configuration guidance to optimize PostgreSQL settings, tune connection pools correctly, and validate the deployment configuration before going live.

**Why this priority**: This is P2 because misconfigured production deployments lead to performance issues, connection exhaustion, and production incidents. Proper configuration documentation prevents these problems.

**Independent Test**: Can be fully tested by following configuration guide to deploy codebase-mcp in staging environment with correct PostgreSQL tuning and connection pool settings validated. Delivers value through optimal production deployments.

**Acceptance Scenarios**:

1. **Given** administrator prepares production deployment, **When** they review configuration guide, **Then** comprehensive environment variable reference table is provided
2. **Given** administrator reviews PostgreSQL requirements, **When** they check connection calculation, **Then** max_connections formula is documented with examples
3. **Given** administrator tunes connection pools, **When** they review MAX_PROJECTS setting, **Then** tradeoffs and PostgreSQL impact are explained clearly
4. **Given** administrator tunes connection pools, **When** they review MAX_CONNECTIONS_PER_POOL, **Then** recommended values for different scenarios are provided
5. **Given** administrator configures monitoring, **When** they review monitoring guidance, **Then** connection pool metrics and health indicators are documented
6. **Given** administrator validates configuration, **When** they use validation checklist, **Then** all critical settings have validation commands

---

### User Story 4 - Developer Integrates workflow-mcp (Priority: P3)

A developer building on top of codebase-mcp wants to integrate workflow-mcp for automatic project detection. They need architecture diagrams, integration examples, and fallback behavior documentation.

**Why this priority**: This is P3 because workflow-mcp integration is optional and serves advanced use cases. Integration examples enable ecosystem development but are not required for basic usage.

**Independent Test**: Can be fully tested by following integration documentation to configure workflow-mcp connection and verify automatic project detection works. Delivers value through simplified multi-project workflows.

**Acceptance Scenarios**:

1. **Given** developer wants automatic project detection, **When** they read README integration section, **Then** workflow-mcp integration is clearly marked optional
2. **Given** developer reviews integration architecture, **When** they view architecture diagram, **Then** integration points and data flow are visualized
3. **Given** developer configures workflow-mcp, **When** they set environment variables, **Then** WORKFLOW_MCP_URL and timeout settings are documented
4. **Given** developer tests integration, **When** they use automatic project detection, **Then** example shows project_id automatically resolved
5. **Given** workflow-mcp is unavailable, **When** integration times out, **Then** fallback behavior to default project is documented

---

### User Story 5 - Maintainer Contributes to Project (Priority: P3)

A new contributor wants to understand the codebase architecture, set up a development environment, and contribute documentation improvements or code changes confidently.

**Why this priority**: This is P3 because maintainer documentation supports long-term sustainability but doesn't block user adoption. Good architecture documentation reduces contributor onboarding time.

**Independent Test**: Can be fully tested by following contributor documentation to set up development environment and understand architecture well enough to make meaningful contributions. Delivers value through sustainable project maintenance.

**Acceptance Scenarios**:

1. **Given** maintainer reviews architecture documentation, **When** they study multi-project design, **Then** connection pool manager and database-per-project strategy are explained
2. **Given** maintainer studies database design, **When** they check naming conventions, **Then** database naming pattern with examples is documented
3. **Given** maintainer understands connection pools, **When** they review pool lifecycle, **Then** LRU eviction and MAX_PROJECTS enforcement are explained
4. **Given** maintainer wants to contribute, **When** they follow development setup, **Then** environment setup and testing procedures are provided

---

### Edge Cases

- **What happens when a new user with no previous codebase-mcp installation reads documentation?** - README provides complete setup from scratch with no mention of migration, ensuring clean onboarding experience
- **What happens when a v2.0 user accidentally follows v1.x documentation?** - Commands fail with clear error messages indicating version mismatch and linking to correct documentation
- **What happens when migration script fails midway through upgrade?** - Migration guide explains how to diagnose failure, provides resume instructions if possible, and documents complete rollback procedure
- **What happens when administrator sets MAX_PROJECTS=20 but PostgreSQL max_connections=100?** - Configuration guide provides calculation formula (20 pools × 20 connections = 400 needed) and warns about insufficient connections
- **What happens when user searches for "upgrade" or "migration" in documentation?** - README prominently links to migration guide in breaking changes section with multiple entry points
- **What happens when v1.x user looks for removed tool (e.g., create_work_item) in API docs?** - API reference clearly states "Removed in v2.0 - see migration guide" with link to explanation
- **What happens when user upgrades without adding new environment variables?** - Server uses documented default values, configuration guide lists all variables with defaults
- **What happens when user searches PostgreSQL for "codebase_mcp" database after indexing project "my-app"?** - Architecture documentation explains database-per-project naming convention: codebase_my-app
- **What happens when workflow-mcp integration is configured but workflow-mcp is unavailable?** - README documents fallback to default project with clear error message and timeout behavior
- **What happens when user executes rollback but is unsure if it succeeded?** - Migration guide provides validation commands to verify v1.x restoration and troubleshooting section for partial rollback

## Requirements *(mandatory)*

### Functional Requirements

#### Documentation Accuracy Requirements

- **FR-001**: README MUST reflect accurate tool count (2 tools: index_repository, search_code)
- **FR-002**: README MUST explain multi-project support capability with use case examples
- **FR-003**: README MUST document workflow-mcp integration as optional feature with standalone usage documented first
- **FR-004**: README MUST provide updated installation instructions matching v2.0 requirements
- **FR-005**: API documentation MUST document index_repository with project_id parameter showing default behavior
- **FR-006**: API documentation MUST document search_code with project_id parameter showing default behavior
- **FR-007**: API documentation MUST remove all references to 14 deleted tools or mark as "Removed in v2.0"
- **FR-008**: Documentation MUST provide list of removed tools with v2.0 removal notation

#### Migration Guide Requirements

- **FR-009**: Migration guide MUST explain breaking changes upfront before procedures
- **FR-010**: Migration guide MUST list all 14 removed tools explicitly by name
- **FR-011**: Migration guide MUST explain database schema changes (9 tables dropped, project_id added)
- **FR-012**: Migration guide MUST document API changes (project_id parameter added to both tools)
- **FR-013**: Migration guide MUST list new environment variables required for v2.0
- **FR-014**: Migration guide MUST provide step-by-step upgrade procedure from backup through validation
- **FR-015**: Migration guide MUST include backup procedures with exact commands before upgrade
- **FR-016**: Migration guide MUST provide complete rollback procedure restoring v1.x functionality and data
- **FR-017**: Migration guide MUST include validation steps to confirm successful upgrade
- **FR-018**: Migration guide MUST document migration script execution procedure
- **FR-019**: Migration guide MUST explain data preservation guarantees (v2.0 preserves only indexed code repositories; all v1.x project management data including work items, entities, deployments, and entity types is discarded during migration)
- **FR-020**: Migration duration estimates are deferred to Phase 06 performance testing; Phase 05 migration guide omits specific timing guidance

#### Configuration Guide Requirements

- **FR-021**: Configuration guide MUST document all environment variables with defaults in table format
- **FR-022**: Configuration guide MUST explain MAX_PROJECTS limit and connection pool implications
- **FR-023**: Configuration guide MUST document MAX_CONNECTIONS_PER_POOL tuning guidance with tradeoffs
- **FR-024**: Configuration guide MUST provide PostgreSQL max_connections calculation formula
- **FR-025**: Configuration guide MUST recommend PostgreSQL tuning parameters for production
- **FR-026**: Configuration guide MUST document workflow-mcp integration environment variables
- **FR-027**: Configuration guide SHOULD provide configuration validation checklist with commands

#### Architecture Documentation Requirements

- **FR-028**: Architecture docs MUST include multi-project architecture diagram showing components
- **FR-029**: Architecture docs MUST explain database-per-project naming strategy with examples
- **FR-030**: Architecture docs MUST document connection pool design and LRU eviction behavior
- **FR-031**: Architecture docs SHOULD explain workflow-mcp integration architecture with diagrams

#### Documentation Quality Requirements

- **FR-032**: All documentation links MUST resolve without 404 errors (manual verification during authoring; automated link checking deferred to Phase 07)
- **FR-033**: All code examples MUST be tested and functional before publication (manual testing during authoring; automated example testing deferred to Phase 07)
- **FR-034**: Documentation MUST use consistent terminology throughout (glossary or style guide)
- **FR-035**: Documentation MUST follow project markdown style guide for formatting consistency

### Key Entities *(include if feature involves data)*

- **Documentation Artifact**: Represents specific documentation files (README, migration guide, configuration guide, architecture docs, API reference) with attributes including artifact type, target audience (new user, upgrading user, administrator, developer, maintainer), status (draft, reviewed, approved, published), and version tied to software version (v2.0 docs)
- **Migration Step**: Represents discrete actions in upgrade procedure with attributes including step number, action description, exact commands, validation criteria, and recovery procedures if step fails
- **Configuration Parameter**: Represents environment variables or settings with attributes including parameter name, default value, description, example value, and related parameters that interact (e.g., MAX_PROJECTS × MAX_CONNECTIONS_PER_POOL calculation)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of documented tool names match actual implementation (exactly 2 tools with correct names)
- **SC-002**: 100% of removed tools (14 total) are documented in migration guide with names
- **SC-003**: 0 broken links in all documentation files (manually verified during authoring)
- **SC-004**: 100% of code examples are tested and execute successfully before publication (manually tested during authoring)
- **SC-005**: 100% of breaking changes are documented with corresponding migration steps
- **SC-006**: 100% of environment variables are documented with default values and descriptions
- **SC-007**: Migration guide provides complete rollback procedure covering all upgrade steps
- **SC-008**: Existing users successfully upgrade from v1.x to v2.0 following guide without requiring support
- **SC-009**: New users complete first indexing and search within 15 minutes of installation
- **SC-010**: System administrators deploy v2.0 to production with correct configuration on first attempt
- **SC-011**: Developers successfully integrate workflow-mcp using provided integration examples
- **SC-012**: New contributors understand architecture and contribute improvements after reading documentation

## Assumptions

- Phase 01-04 implementations are complete and stable (v2.0 refactoring finished)
- Existing v1.x documentation is available for reference and comparison
- PostgreSQL is confirmed as non-negotiable database (per constitution)
- Migration path from v1.x to v2.0 is technically feasible (schema migration tested)
- Rollback procedure is technically possible (data can be restored to v1.x format)
- Default project behavior is well-defined (single "default" project for users not specifying project_id)
- workflow-mcp integration is optional and system functions without it (local-first architecture)
- Documentation will be version-controlled alongside code (same repository)
- Markdown is the documentation format (industry standard for developer tools)
- Users have command-line access for running validation and backup commands

## Dependencies

- **Phase 01 Completion**: Core refactoring to 2 tools must be complete
- **Phase 02 Completion**: Multi-project support implementation must be stable
- **Phase 03 Completion**: Connection pooling architecture must be finalized
- **Phase 04 Completion**: workflow-mcp integration must be implemented and tested
- **Migration Script**: Database migration script must exist and be tested
- **Version Numbering**: v2.0 release version must be confirmed
- **Changelog**: Basic changelog entries for v2.0 must exist (input for migration guide)

## Non-Goals (Explicitly Out of Scope)

**Not Included in This Phase:**
- Performance benchmarking and validation (deferred to Phase 06)
- Migration duration estimates based on database size (deferred to Phase 06 performance testing)
- Automated link checking and example testing scripts/CI integration (deferred to Phase 07)
- Release notes and changelog updates (deferred to Phase 07)
- Production deployment automation scripts (deferred to Phase 07)
- User training materials or video tutorials (future consideration)

**Explicitly NOT Doing:**
- Code changes or bug fixes (Phase 05 is documentation only)
- New feature development or enhancements beyond v2.0 scope
- Performance optimization or database tuning
- Database schema changes or additional migrations
- Test development or test coverage improvements
- Refactoring or code quality improvements

**Future Considerations (Not This Phase):**
- Interactive migration script with guided prompts and validation
- Migration validation tool checking prerequisites automatically
- Automated documentation generation from code annotations
- Documentation versioning with historical archives
- Multi-language documentation translations
- Video tutorials demonstrating upgrade procedures
- Chatbot or FAQ system for common migration questions
- Documentation analytics tracking most-viewed pages and search queries

## Review & Acceptance Checklist

**Content Quality**:
- [X] No implementation details (languages, frameworks, APIs) in user-facing requirements
- [X] Focused on user value and business needs
- [X] Written for appropriate technical level per persona
- [X] All mandatory sections complete
- [X] Terminology consistent throughout

**Requirement Completeness**:
- [X] Maximum 3 [NEEDS CLARIFICATION] markers present (exactly 3: FR-019, FR-020, FR-032)
- [X] All requirements testable and unambiguous
- [X] All personas addressed with relevant documentation
- [X] Edge cases and error scenarios covered (10 specific cases)
- [X] Success criteria measurable and specific (12 quantitative/qualitative measures)
- [X] Each requirement traces to user workflow
- [X] Non-functional requirements captured (accuracy, completeness, quality)

**Scope Clarity**:
- [X] Feature boundaries clearly defined (documentation only, no code changes)
- [X] Out-of-scope items explicitly listed in Non-Goals section
- [X] Dependencies identified (Phases 01-04 completion required)
- [X] Integration documentation requirements specified (workflow-mcp examples)
- [X] Assumptions documented (10 assumptions listed)

**Constitutional Compliance**:
- [X] Aligns with Simplicity Over Features principle (documenting simplified 2-tool design)
- [X] Follows Local-First Architecture (documenting local database setup)
- [X] Respects Protocol Compliance (documenting MCP tool interfaces accurately)
- [X] Adheres to Production Quality (comprehensive migration and configuration docs)
- [X] Compatible with Specification-First Development (this spec before documentation writing)

## Clarifications

### Session 2025-10-13

- Q: During v1.x to v2.0 migration, what happens to existing data (work items, entities, deployments, entity types)? Is all v1.x project-scoped data discarded, or is there a migration path for some/all data? → A: All v1.x project-scoped data is discarded; only indexed code repositories are preserved in v2.0
- Q: Should Phase 05 include actual testing with various database sizes to produce migration duration estimates, or can we provide generic guidance? → A: Defer duration estimates entirely to Phase 06 performance testing; migration guide omits timing guidance
- Q: Should Phase 05 deliver automation scripts/CI integration for link checking and example testing, or is manual validation sufficient? → A: Defer all testing tooling to Phase 07 deployment automation; Phase 05 focuses purely on content
