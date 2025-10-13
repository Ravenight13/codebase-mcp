# Implementation Plan: Documentation Overhaul & Migration Guide for v2.0 Architecture

**Branch**: `010-v2-documentation` | **Date**: 2025-10-13 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/010-v2-documentation/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Update all codebase-mcp documentation to reflect the v2.0 architecture refactoring (16 tools → 2 tools with multi-project support). Create comprehensive migration guide for v1.x users with breaking changes, upgrade procedures, and rollback instructions. Provide accurate documentation for 5 personas: existing users upgrading, new users installing, administrators configuring production, developers integrating workflow-mcp, and maintainers contributing. All documentation artifacts (README, migration guide, configuration guide, architecture docs, API reference) must be authored, tested, and validated without any code changes (documentation-only phase).

## Technical Context

**Language/Version**: N/A (Documentation only - Markdown format)
**Primary Dependencies**: N/A (No code dependencies - pure documentation authoring)
**Storage**: Version-controlled Markdown files in repository (docs/, README.md, API reference)
**Testing**: Manual testing (link verification, code example execution per FR-032/FR-033)
**Target Platform**: Documentation consumers (web browsers, GitHub rendering, local markdown readers)
**Project Type**: Documentation authoring (not a software build project)
**Performance Goals**: N/A for docs themselves; documented system targets are 60s indexing, 500ms search (Phase 06 validation)
**Constraints**:
- Manual verification only (automated testing deferred to Phase 07 per FR-032/FR-033)
- No code changes permitted (Phase 05 scope boundary per Non-Goals)
- Must complete within documentation authoring timeline (no performance testing)
- All code examples must execute successfully (FR-033)
- All links must resolve without 404 errors (FR-032)
**Scale/Scope**:
- 5 documentation artifacts (README, Migration Guide, Configuration Guide, Architecture Docs, API Reference)
- 5 user personas with distinct needs
- 38 functional requirements to satisfy
- 14 removed tools to document
- 11 edge cases to address

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Phase 0 Validation

| Principle | Status | Assessment |
|-----------|--------|------------|
| **I. Simplicity Over Features** | ✅ PASS | Documentation-only scope explicitly bounded. No feature additions, only documenting existing v2.0 architecture. |
| **II. Local-First Architecture** | ✅ PASS | Documenting local-first system (PostgreSQL, Ollama). No cloud dependencies introduced. |
| **III. Protocol Compliance (MCP)** | ✅ PASS | Documenting accurate MCP tool interfaces (index_repository, search_code). No protocol changes. |
| **IV. Performance Guarantees** | ⚠️ DEFERRED | (Migration duration estimates: see FR-020 in spec.md - deferred to Phase 06) |
| **V. Production Quality Standards** | ✅ PASS | Comprehensive migration guide with backup/rollback procedures (FR-015, FR-016). Quality requirements defined (FR-032 to FR-035, FR-038). |
| **VI. Specification-First Development** | ✅ PASS | Spec completed with 100% checklist pass (91/91 items). All clarifications resolved. Planning follows specification. |
| **VII. Test-Driven Development** | ⚠️ MODIFIED | Manual testing approach for documentation (FR-032, FR-033). Automated testing deferred to Phase 07. TDD not applicable to documentation authoring. |
| **VIII. Pydantic-Based Type Safety** | N/A | No code changes. Type safety not applicable to Markdown documentation. |
| **IX. Orchestrated Subagent Execution** | ✅ APPLICABLE | Implementation phase will use orchestrated subagents for parallel documentation authoring across 5 artifacts. |
| **X. Git Micro-Commit Strategy** | ✅ PASS | Feature branch `010-v2-documentation` created. Micro-commits will follow Conventional Commits format for each documentation artifact. |
| **XI. FastMCP Foundation** | ✅ PASS | Documenting FastMCP-based MCP server accurately. No framework changes. |

**Overall Status**: ✅ **PASS WITH DEFERRALS**

**Justifications**:
- **Principle IV (Performance)**: Timing validation explicitly scoped to Phase 06 per FR-020. Documentation describes targets without performance testing.
- **Principle VII (TDD)**: Manual testing is appropriate and sufficient for documentation artifacts. Code example testing (FR-033) ensures accuracy. Automated link checking (FR-032) deferred to Phase 07 CI integration per explicit scope boundary.

**No constitutional violations requiring Complexity Tracking.**

## Project Structure

### Documentation (this feature)

```
specs/010-v2-documentation/
├── spec.md                  # Feature requirements (completed)
├── plan.md                  # This file (Phase 0-1 output)
├── research.md              # Phase 0: Documentation structure research
├── data-model.md            # Phase 1: Documentation artifact model
├── quickstart.md            # Phase 1: Manual testing scenarios
├── contracts/               # Phase 1: Documentation structure contracts
│   └── documentation-structure.yaml  # Artifact types, audiences, validation rules
├── checklists/              # Requirements quality validation
│   ├── requirements.md      # Original spec validation checklist
│   └── documentation.md     # Comprehensive requirements checklist (100% pass)
└── tasks.md                 # Phase 2: TDD task breakdown (NOT created yet)
```

### Source Code (repository root - **NO CHANGES IN PHASE 05**)

This is a **documentation-only phase**. Per Non-Goals section, the following are explicitly out of scope:
- ❌ Code changes or bug fixes
- ❌ New feature development
- ❌ Performance optimization
- ❌ Database schema changes
- ❌ Test development (beyond documentation validation)
- ❌ Refactoring

Existing repository structure remains unchanged. Documentation updates occur in:

```
/
├── README.md                          # To be updated (v2.0 tool count, installation, multi-project)
├── docs/
│   ├── migration/
│   │   └── v1-to-v2-migration.md     # To be created (breaking changes, upgrade, rollback)
│   ├── configuration/
│   │   └── production-config.md       # To be created (env vars, connection pools, PostgreSQL tuning)
│   ├── architecture/
│   │   └── multi-project-design.md    # To be created (database-per-project, connection pools, LRU eviction)
│   ├── api/
│   │   └── tool-reference.md          # To be updated (2 tools, removed 14 tools notation)
│   └── glossary.md                    # To be created (6 canonical terms per FR-034)
```

**Structure Decision**: Documentation-only project with no source code modifications. All deliverables are Markdown files following project markdown style guide (to be referenced from Assumptions). No compilation, no build artifacts, no runtime dependencies.

## Complexity Tracking

*No constitutional violations requiring justification.*

This feature maintains constitutional compliance without exceptions.

---

## Phase 0: Research & Technical Decisions

✅ **COMPLETED** - See [research.md](./research.md)

**Research Topics Covered**:
1. ✅ Markdown documentation structure best practices - Decision: GitHub-flavored Markdown with hierarchical TOC
2. ✅ Migration guide structure patterns - Decision: Breaking Changes First + Step-by-Step + Rollback
3. ✅ Configuration documentation patterns - Decision: Environment Variable Tables + PostgreSQL Calculations
4. ✅ Architecture documentation patterns - Decision: Mermaid Diagrams + Prose + Code Examples
5. ✅ API reference documentation patterns - Decision: OpenAPI-Inspired + Explicit Deprecation
6. ✅ Documentation validation methodologies - Decision: Manual Checklist + Documented Procedures

**Key Decisions**:
- All documentation uses GitHub-flavored Markdown for maximum compatibility
- Migration guide prioritizes breaking changes upfront (risk communication)
- Configuration guide uses table format for environment variables with calculation examples
- Architecture docs use Mermaid diagrams (embedded in Markdown, no external tools)
- API reference explicitly documents removed tools with "Removed in v2.0" notation
- Manual validation with documented checklists (automated testing deferred to Phase 07)

**No technical unknowns remain** - all documentation patterns established

---

## Phase 1: Design Artifacts

✅ **COMPLETED** - All design artifacts generated

### Design Outputs

1. ✅ **[data-model.md](./data-model.md)**: Documentation artifact entity model (~4,900 lines)
   - Documentation Artifact entity (5 types, 14 fields, state transitions draft→reviewed→approved→published)
   - Migration Step entity (5 phases, 13 fields, relationships to Documentation Artifact)
   - Configuration Parameter entity (4 types, 11 fields, related parameter calculations)
   - Complete Mermaid ER diagram showing 1:N, N:N, and 1:1 optional relationships
   - 38 validation rules mapped from functional requirements
   - Query patterns and usage guidance for documentation authoring workflow

2. ✅ **[contracts/documentation-structure.yaml](./contracts/documentation-structure.yaml)**: Documentation structure specifications (~650 lines)
   - 5 artifact types fully specified (README, Migration Guide, Configuration Guide, Architecture Docs, API Reference)
   - 40+ required sections across all artifacts with content descriptions
   - 30+ validation rules mapping to FR-001 through FR-038
   - 5 audience definitions (new users, existing users, administrators, developers, maintainers)
   - 6 canonical glossary terms with definitions and usage rules (FR-034)
   - 6 success metrics from spec.md (SC-001 to SC-006)

3. ✅ **[quickstart.md](./quickstart.md)**: Manual testing scenarios (~1,350 lines)
   - 5 comprehensive test scenarios with step-by-step procedures:
     * Link Verification (FR-032) - 6 steps, 0 broken links success criteria
     * Code Example Testing (FR-033) - 7 steps, 100% execution success criteria
     * Migration Guide Validation (FR-014 to FR-017, FR-036) - 7 steps, upgrade/rollback/diagnostics validation
     * Configuration Guide Validation (FR-021 to FR-027, FR-038) - 7 steps, env vars/calculations/monitoring validation
     * Cross-Artifact Consistency Check (FR-034, FR-035) - 6 steps, terminology/style consistency validation
   - Master validation checklist with 50+ items covering scenarios, deliverables, quality metrics, FRs, personas
   - Prerequisites, tools, expected results, and pass/fail criteria for each scenario

4. ✅ **Agent context update**: CLAUDE.md updated
   - Added language: N/A (Documentation only - Markdown format)
   - Added framework: N/A (No code dependencies - pure documentation authoring)
   - Added database: Version-controlled Markdown files in repository
   - Incremental update preserves existing manual additions

**Status**: ✅ COMPLETED - Ready for Phase 2 task generation

### Post-Design Constitution Re-evaluation

| Principle | Status | Post-Design Assessment |
|-----------|--------|------------------------|
| **I. Simplicity Over Features** | ✅ PASS | Design maintains documentation-only scope. No complexity introduced. |
| **II. Local-First Architecture** | ✅ PASS | Documentation describes local-first system. No cloud dependencies in design. |
| **III. Protocol Compliance (MCP)** | ✅ PASS | Contracts specify accurate MCP tool documentation. No protocol violations in design. |
| **IV. Performance Guarantees** | ✅ PASS | Design acknowledges timing deferred to Phase 06. No performance testing in documentation phase. |
| **V. Production Quality Standards** | ✅ PASS | Comprehensive validation procedures (quickstart.md). Quality requirements enforced via contracts. |
| **VI. Specification-First Development** | ✅ PASS | Design directly implements spec requirements. All FRs traced to design artifacts. |
| **VII. Test-Driven Development** | ✅ PASS | Validation scenarios (quickstart.md) define testing approach before authoring. Manual testing appropriate for documentation. |
| **VIII. Pydantic-Based Type Safety** | N/A | No code. Type safety not applicable. |
| **IX. Orchestrated Subagent Execution** | ✅ READY | Design enables parallel subagent authoring (5 artifacts can be written concurrently per contracts). |
| **X. Git Micro-Commit Strategy** | ✅ PASS | Feature branch established. Design supports atomic commits per artifact section. |
| **XI. FastMCP Foundation** | ✅ PASS | Contracts document FastMCP MCP server accurately. Design maintains framework compliance. |

**Overall Status**: ✅ **FULL CONSTITUTIONAL COMPLIANCE**

**Confirmation**: All 11 principles remain compliant after design completion. No violations introduced during Phase 0-1.

---

## Phase 2: Task Generation

*NOT INCLUDED IN THIS COMMAND*

Task breakdown will be generated by `/speckit.tasks` command after Phase 0-1 completion. Tasks will follow TDD approach:
1. Validation tasks (link checking, example testing)
2. Authoring tasks (per artifact)
3. Review tasks (cross-artifact consistency)

Expected task count: ~30-40 tasks across 5 documentation artifacts

---

## Notes

**Command Scope**: `/speckit.plan` stops after Phase 1 (design artifacts). Task generation and implementation occur in subsequent commands.

**Phasing Rationale**:
- **Phase 0**: Resolve documentation structure patterns (no code dependencies to research)
- **Phase 1**: Design documentation artifact model and validation procedures
- **Phase 2** (separate command): Generate TDD-ordered task breakdown
- **Implementation** (separate command): Execute tasks with orchestrated subagents

**Next Steps**:
1. Execute Phase 0: Generate research.md
2. Execute Phase 1: Generate data-model.md, contracts/, quickstart.md, update CLAUDE.md
3. User runs `/speckit.tasks` to generate tasks.md
4. User runs `/speckit.implement` to execute documentation authoring
