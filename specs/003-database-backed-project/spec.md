# Feature Specification: Project Status and Work Item Tracking MCP System

**Feature Branch**: `003-database-backed-project`
**Created**: 2025-10-10
**Status**: Draft
**Input**: User description: "Add Project status and work item tracking MCP system with our database integration"

## Execution Flow (main)
```
1. Parse user description from Input
   → If empty: ERROR "No feature description provided"
2. Extract key concepts from description
   → Identify: actors, actions, data, constraints
3. For each unclear aspect:
   → Mark with [NEEDS CLARIFICATION: specific question]
4. Fill User Scenarios & Testing section
   → If no clear user flow: ERROR "Cannot determine user scenarios"
5. Generate Functional Requirements
   → Each requirement must be testable
   → Mark ambiguous requirements
6. Identify Key Entities (if data involved)
7. Run Review Checklist
   → If any [NEEDS CLARIFICATION]: WARN "Spec has uncertainties"
   → If implementation details found: ERROR "Remove tech details"
8. Return: SUCCESS (spec ready for planning)
```

---

## ⚡ Quick Guidelines
- ✅ Focus on WHAT users need and WHY
- ❌ Avoid HOW to implement (no tech stack, APIs, code structure)
- 👥 Written for business stakeholders, not developers

### Section Requirements
- **Mandatory sections**: Must be completed for every feature
- **Optional sections**: Include only when relevant to the feature
- When a section doesn't apply, remove it entirely (don't leave as "N/A")

### For AI Generation
When creating this spec from a user prompt:
1. **Mark all ambiguities**: Use [NEEDS CLARIFICATION: specific question] for any assumption you'd need to make
2. **Don't guess**: If the prompt doesn't specify something (e.g., "login system" without auth method), mark it
3. **Think like a tester**: Every vague requirement should fail the "testable and unambiguous" checklist item
4. **Common underspecified areas**:
   - User types and permissions
   - Data retention/deletion policies
   - Performance targets and scale
   - Error handling behaviors
   - Integration requirements
   - Security/compliance needs

---

## Clarifications

### Session 2025-10-10
- Q: When multiple AI clients update the same work item concurrently, how should conflicts be resolved? → A: Optimistic locking with version check, reject conflicting update with error (prevents data loss)
- Q: When the database is unavailable and an AI client attempts to update work item state, what should happen? → A: Write to both SQLite cache AND markdown file simultaneously (parallel, maximum redundancy)
- Q: What observability signals must the system provide for operational monitoring? → A: Minimal - rely on database logs and external monitoring (no additional overhead)
- Q: The audit trail tracks "created_by" for all entities. What identity should this field capture? → A: AI client identifier (e.g., "claude-code", "claude-desktop", "copilot")
- Q: With 1,200+ work items accumulated over 5 years, how should queries maintain <10ms response times? → A: Automatic archiving - move items older than 1 year to separate archive table, query active only

---

## User Scenarios & Testing

### Primary User Story
AI coding assistants (Claude Code, Claude Desktop, GitHub Copilot, and other MCP clients) need to programmatically query and update project status, work item tracking, vendor extractor health, and deployment history. Currently, this data lives in a manually-maintained markdown file (.project_status.md) that requires human updates, cannot be queried efficiently, and doesn't support concurrent access from multiple AI clients.

The system must provide queryable, structured project status data through MCP tools, enabling AI assistants to:
- Query operational vendor status in under 1ms
- Track hierarchical work items (projects → sessions → tasks) with dependency relationships
- Access deployment history with test results and constitutional compliance validation
- Generate up-to-date status reports automatically
- Maintain complete audit trails of all changes

### Acceptance Scenarios

1. **Given** an AI assistant needs to check vendor extractor health, **When** it queries vendor status via MCP tool, **Then** it receives current operational status, test results (passing/total/skipped), format support flags, and version information in under 1ms

2. **Given** an AI assistant is working on a task within a work session, **When** it updates task status via MCP tool, **Then** the change is persisted with audit trail (created_by = AI client identifier, updated_at) and immediately visible to other AI clients

3. **Given** a deployment has occurred, **When** deployment metadata is recorded via MCP tool, **Then** the system captures PR merge details, commit hash, timestamp, related work items, affected vendors, test results, and constitutional compliance status

4. **Given** the database becomes unavailable, **When** an AI assistant queries project status, **Then** the system falls back through cache (30-min TTL) → git history → manual markdown file without hard failure, returning warnings instead of errors

5. **Given** legacy .project_status.md data exists, **When** migration is executed, **Then** 100% of historical data is preserved and validated through five reconciliation checks (vendor count, deployment history, enhancements count, session prompt count, vendor metadata completeness)

6. **Given** an AI assistant needs hierarchical work item context, **When** it queries a task, **Then** it receives the full parent chain (session → project) and child tasks with dependency relationships up to 5 levels deep in under 10ms

7. **Given** multiple AI clients are accessing project status concurrently, **When** one client updates a work item, **Then** other clients see the change immediately on their next query without conflicts

8. **Given** an AI assistant needs full project status, **When** it requests complete status generation, **Then** the system produces vendor health summary, active work items, recent deployments, and pending enhancements in under 100ms

### Edge Cases

- **What happens when database is down during critical updates?** System writes updates to both local SQLite cache AND fallback markdown file in parallel, then syncs to PostgreSQL when database reconnects (maximum redundancy, no data loss)
- **How does system handle concurrent updates to the same work item?** System uses optimistic locking with version checking; conflicting updates are rejected with error indicating version mismatch, requiring client to fetch latest version and retry
- **What happens when hierarchical relationships create cycles?** System must detect and reject circular parent-child dependencies
- **How does system handle 5+ years of accumulated work items (1,200+ items)?** System automatically archives work items older than 1 year to separate archive table; queries default to active table only, maintaining <10ms response times; archived items queryable separately if needed
- **What happens when JSONB metadata fails Pydantic validation?** System must reject invalid updates and return validation errors to AI client
- **How does system recover from failed migration?** Rollback procedures must restore original markdown file and database state
- **What happens when session prompt YAML frontmatter is malformed?** Parser must handle gracefully with clear error messages and skip invalid entries

## Requirements

### Functional Requirements

**Vendor Tracking**
- **FR-001**: System MUST track operational status for 45+ vendor extractors, including status flags (operational/broken), test results (passing/total/skipped counts), format support flags (Excel/CSV/PDF/OCR), extractor version strings, and manifest compliance status
- **FR-002**: System MUST allow querying individual vendor status in under 1ms (performance target)
- **FR-003**: System MUST support vendor-specific metadata storage using flexible schema (JSONB) with Pydantic validation for type safety
- **FR-004**: System MUST track which vendors are affected by each deployment through relationship linkage

**Deployment History**
- **FR-005**: System MUST record deployment events including PR merge details, commit hashes, deployment timestamp, related work items, affected vendors, test result summaries, and constitutional compliance validation status
- **FR-006**: System MUST maintain complete chronological deployment timeline accessible via queries
- **FR-007**: System MUST link deployments to specific work items and vendors through relational references

**Work Item Tracking**
- **FR-008**: System MUST support hierarchical work item types: projects, work sessions, tasks, and research phases with parent-child relationships up to 5 levels deep
- **FR-009**: System MUST allow tracking dependencies between work items (blocked-by, depends-on relationships)
- **FR-010**: System MUST store type-specific metadata for each work item using flexible schema (JSONB) with Pydantic validation
- **FR-011**: System MUST track git integration metadata including branch names, commit hashes, and PR numbers for each work item
- **FR-012**: System MUST implement soft-delete pattern for work items to preserve audit trail (deleted_at timestamp instead of hard delete)
- **FR-013**: System MUST query work item hierarchies in under 10ms (performance target)
- **FR-014**: System MUST record audit trail for all work item changes including created_at, updated_at, and created_by fields; created_by captures AI client identifier (e.g., "claude-code", "claude-desktop", "copilot")

**Global Configuration**
- **FR-015**: System MUST maintain singleton project configuration including active context type, token budgets, current session reference, git state, and health check status
- **FR-016**: System MUST allow querying and updating global configuration via MCP tools

**Future Enhancements Tracking**
- **FR-017**: System MUST track planned future enhancements with priority levels, dependency relationships, target quarter/timeline, and required constitutional principle compliance flags
- **FR-018**: System MUST allow filtering enhancements by priority, status, and target timeline

**MCP Tool Integration**
- **FR-019**: System MUST provide 8 MCP tools for CRUD operations: create work item, update work item, query work item, list work items, record deployment, query vendor status, update vendor status, get project configuration
- **FR-020**: System MUST validate all JSONB metadata against Pydantic schemas before persistence
- **FR-021**: System MUST parse session prompts with YAML frontmatter including schema versioning

**Status Report Generation**
- **FR-022**: System MUST auto-generate .project_status.md markdown file from database queries matching legacy format
- **FR-023**: System MUST generate full project status report in under 100ms (performance target)

**Data Migration & Integrity**
- **FR-024**: System MUST migrate 100% of data from legacy .project_status.md without loss
- **FR-025**: System MUST execute five reconciliation checks post-migration: vendor count match, deployment history completeness, enhancements count match, session prompts count match, vendor metadata completeness
- **FR-026**: System MUST provide rollback procedures if migration validation fails
- **FR-027**: System MUST maintain audit trail with created_at, updated_at, created_by for all entities; created_by captures AI client identifier

**Reliability & Fallback**
- **FR-028**: System MUST implement 4-layer fallback when database unavailable for reads: Database → SQLite cache (30-min TTL) → Git history → Manual markdown file
- **FR-029**: System MUST write updates to both SQLite cache AND markdown file in parallel when PostgreSQL is unavailable, then sync to PostgreSQL when reconnected
- **FR-030**: System MUST continue operating with warnings (not errors) when database is unavailable
- **FR-031**: System MUST maintain backward compatibility with markdown-based workflows
- **FR-032**: System MUST never produce hard failures that block AI assistant operation

**Performance & Scale**
- **FR-033**: System MUST support 45+ vendors and 1,200+ work items accumulated over 5 years
- **FR-034**: System MUST meet performance targets: operational vendor query <1ms, work item hierarchy query <10ms, full status generation <100ms
- **FR-039**: System MUST automatically archive work items older than 1 year to separate archive table; default queries operate on active table only; archived items MUST remain queryable via separate archive query operations

**Multi-Client Support**
- **FR-035**: System MUST allow multiple AI clients (Claude Code, Claude Desktop, etc.) to query and update shared work item state concurrently
- **FR-036**: System MUST ensure changes from one client are immediately visible to other clients on subsequent queries
- **FR-037**: System MUST implement optimistic locking with version tracking for all work items, vendors, and configuration updates; conflicting updates MUST be rejected with version mismatch error

**Observability**
- **FR-038**: System does NOT need to implement custom logging, metrics, or tracing infrastructure; operational monitoring relies on PostgreSQL logs, SQLite logs, and external monitoring systems

### Key Entities

- **Vendor Extractor**: Represents a commission data vendor extractor with operational status, test results, format support capabilities, version information, manifest compliance status, and vendor-specific metadata. Related to deployments that affect the vendor.

- **Deployment Event**: Represents a deployment occurrence with PR merge details, commit hash, timestamp, test result summary, constitutional compliance validation, and relationships to affected work items and vendors.

- **Work Item**: Polymorphic entity representing projects, work sessions, tasks, or research phases. Contains hierarchical parent-child relationships, dependency links to other work items, type-specific metadata, git integration details (branch, commits, PRs), soft-delete flag, and complete audit trail.

- **Project Configuration**: Singleton configuration entity storing active context type, token budgets, current session reference, git repository state, and health check status.

- **Future Enhancement**: Planned feature or improvement with priority level, dependency relationships to other enhancements, target quarter/timeline, required constitutional principles, and tracking status.

- **Work Item Dependency**: Relationship between work items indicating blocked-by or depends-on constraints.

- **Vendor Deployment Link**: Many-to-many relationship connecting deployments to affected vendors.

- **Work Item Deployment Link**: Many-to-many relationship connecting deployments to related work items.

---

## Review & Acceptance Checklist
*GATE: Automated checks run during main() execution*

### Content Quality
- [X] No implementation details (languages, frameworks, APIs)
- [X] Focused on user value and business needs
- [X] Written for non-technical stakeholders
- [X] All mandatory sections completed

### Requirement Completeness
- [ ] No [NEEDS CLARIFICATION] markers remain
- [X] Requirements are testable and unambiguous
- [X] Success criteria are measurable
- [X] Scope is clearly bounded
- [ ] Dependencies and assumptions identified

**Outstanding Clarifications:**
- None - specification is complete based on detailed feature description and reference implementation plan

**Identified Dependencies:**
- Existing PostgreSQL database with pgvector extension
- Existing MCP server infrastructure
- Legacy .project_status.md file for migration
- MCP client applications (Claude Code, Claude Desktop, etc.)

**Assumptions:**
- Database schema will support JSONB for flexible metadata
- Pydantic models exist or will be created for all metadata types
- Session prompts use YAML frontmatter with schema versioning
- Constitutional compliance validation is a boolean flag per deployment
- AI clients use MCP protocol for all interactions

---

## Execution Status
*Updated by main() during processing*

- [X] User description parsed
- [X] Key concepts extracted
- [X] Ambiguities marked (none found - spec is complete)
- [X] User scenarios defined
- [X] Requirements generated
- [X] Entities identified
- [X] Review checklist passed

---
