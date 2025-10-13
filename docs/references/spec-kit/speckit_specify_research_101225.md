# Spec-Kit Mastery Guide: From /specify to Implementation

**GitHub's spec-kit transforms AI coding from "vibe coding" into disciplined, repeatable Spec-Driven Development.** This guide provides actionable practices for crafting stellar /specify inputs, generating quality spec.md files, and establishing rigorous review processes that work in production.

## Understanding the spec-kit paradigm shift

For decades, code reigned supreme while specifications served as disposable scaffolding. Spec-kit inverts this: **specifications become executable artifacts that directly generate working implementations.** The toolkit structures AI collaboration through seven disciplined phases where separation of concerns—WHAT/WHY versus HOW—prevents the premature technical decisions that plague traditional development.

The workflow begins with **constitution** (non-negotiable project principles), flows through **specify** (user needs without technical constraints), continues to **clarify** (resolve ambiguities systematically), advances to **plan** (technical architecture), breaks down into **tasks** (atomic work units), validates via **analyze** (cross-artifact consistency), and culminates in **implement** (AI-driven execution). Each phase builds upon validated foundations, eliminating the specification-implementation gap that causes costly rework.

Spec-kit's power emerges from constraint: templates act as sophisticated prompts that force proper abstraction levels, prevent premature optimization, and guide AI toward specifications that remain stable even as technology evolves. Real-world implementations show 100% build success rates and zero regressions when quality gates are enforced, but only 25% workflow coverage in vanilla spec-kit—extensions for bugfix, modify, refactor, hotfix, and deprecate workflows complete the methodology.

## Crafting exceptional /specify inputs

The golden rule: **describe user needs and business value, never implementation details.** Your /specify input should paint a complete picture of user interactions, workflows, and outcomes while leaving technical decisions for the /plan phase.

### Essential components framework

Every /specify input must include five core elements. **User context** identifies personas, roles, and who benefits from the feature—"casual photographers managing 1000+ personal photos" beats generic "users." **Problem statement** articulates the pain point being solved with specificity. **Core functionality** describes actions users can perform in concrete, testable terms. **Success outcomes** define measurable criteria for user satisfaction. **Scope boundaries** explicitly state what's IN and OUT of scope to prevent feature creep.

**Exemplar input pattern:**

```
/specify Build an application that helps me organize photos in separate albums. 
Albums are grouped by date and can be reorganized by dragging and dropping on 
the main page. Albums are never nested within other albums. Within each album, 
photos preview in a tile-like interface. Photos remain local and are not uploaded 
anywhere. Metadata is stored locally.

User context: Casual photographers with 500-2000 photos wanting quick date-based 
retrieval without manual sorting.

Success means: Users can find photos from specific events 3x faster than manual 
browsing, with organization tasks taking under 2 minutes for 100+ photos.

Out of scope: Cloud sync, sharing features, editing tools (separate features).
```

This works because it specifies user journeys, constraints, and non-features without mentioning React, databases, or APIs. Compare to the anti-pattern: "/specify Build photo management using React, Node.js backend, PostgreSQL database with Redux state management"—this dictates implementation, provides no user context, and belongs entirely in the /plan phase.

### The detail spectrum sweet spot

Finding the right detail level is critical. **Too vague** produces generic solutions: "/specify Build a photo management app" gives AI nothing actionable. **Too prescriptive** eliminates AI's value: "/specify Create React component using useState hook with CSS Grid layout and react-beautiful-dnd" belongs in implementation, not specification.

The sweet spot balances concrete user interactions with implementation freedom. Detail about **user needs** (extensive), **permissions and business rules** (explicit), **scope and boundaries** (crystal clear), but avoid detail about **technical stack** (none), **code structure** (forbidden), or **libraries and frameworks** (belongs in /plan).

Feature scope matters: each /specify should target ONE feature, not entire MVPs. Break large projects into 3-7 distinct features with sequential numbering. Instead of "/specify Build complete e-commerce platform," decompose into Feature 001: Product catalog with search, Feature 002: Shopping cart, Feature 003: Checkout and payment, Feature 004: User accounts. This enables focused specifications, manageable reviews, and proper Git workflow.

### Framing user problems effectively

Use the Problem → User → Action → Outcome framework. Start with problem context ("Users struggle to organize large photo collections by date"), identify user persona ("Casual photographers managing 1000+ personal photos"), specify key actions ("Create albums, drag-drop to reorganize, preview in tiles"), and define success metrics ("Quickly find photos by date, simple reorganization").

Transform technical requests into user-centric specifications. Don't say "We need authentication"—instead say "Users need secure access to their private task boards without sharing sensitive project data." Don't say "Add a dashboard"—say "Project managers need visibility into team progress at a glance to identify bottlenecks and redistribute work." Don't say "Use microservices"—say "System must handle 10,000 concurrent users with response times under 100ms during peak usage."

## Critical anti-patterns that sabotage specifications

**Implementation leak** destroys the what/why separation. Including tech stack, libraries, or frameworks in /specify forces premature technical decisions and reduces flexibility. Save ALL technical details for /plan.

**Assumption guessing** occurs when AI fills missing details with plausible assumptions rather than marking ambiguities. This generates specs that diverge from true intent. AI should use [NEEDS CLARIFICATION: specific question] markers instead of hallucinating requirements.

**Over-eager AI feature addition** introduces scope creep through "helpful" components nobody requested. Challenge AI: "Why did you add this? Where in my input was this requested?" before accepting additions.

**Vague requirements** like "System should be fast" or "Good user experience" are untestable and subjective. Specify concrete criteria: "Load time under 2 seconds for 1000 items" or "95% of users complete organization tasks without help documentation."

**Missing boundary conditions** creates incomplete implementations. Include "what happens when..." scenarios: empty states, error conditions, exceeded limits, permission denials, network failures. Edge cases aren't optional—they're where bugs hide.

**Specification drift** happens when code evolves but specs stagnate. When bugs reveal spec gaps, UPDATE SPEC FIRST, then fix code. Production issues become new non-functional requirements. Use /analyze to validate spec-code alignment.

## The [NEEDS CLARIFICATION] marker system

This disciplined constraint prevents AI from making plausible but incorrect assumptions. The marker forces explicit decisions on ambiguous points before planning begins.

**Usage rules are strict:** Limit to maximum 3 markers per specification. Use only for critical decisions that significantly impact feature scope, have multiple reasonable interpretations with different implications, or cannot be resolved with industry-standard defaults. Format as [NEEDS CLARIFICATION: specific question with context].

**Mark these ambiguities:** Authentication methods (email/password, SSO, OAuth?), data retention policies (how long? deletion rules?), user permissions and roles (who can do what?), feature scope boundaries (included/excluded functionality?), performance requirements (response time? concurrent users?), security and compliance needs (legally or financially significant?).

**Don't mark these—use reasonable defaults:** Standard web app performance expectations, industry-standard data retention for the domain, user-friendly error messages with fallbacks, standard session-based or OAuth2 for web apps.

**Exemplar clarity markers:**

```markdown
FR-006: System MUST authenticate users via [NEEDS CLARIFICATION: auth method not 
specified - email/password, SSO, OAuth? Consider that OAuth eliminates password 
management but creates 3rd party dependency]

FR-007: System MUST retain user data for [NEEDS CLARIFICATION: retention period not 
specified - 30 days, 1 year, indefinitely? Legal compliance may dictate minimum/maximum]

FR-008: Users with [NEEDS CLARIFICATION: which user types? all authenticated users, 
only project owners, or admins only?] can delete projects
```

After spec generation, run `/clarify` for structured questioning. AI presents multiple-choice options with implications, records answers in a "Clarifications" section within spec.md, and reduces downstream rework. The preferred sequence: /clarify (structured, sequential, coverage-based), then ad-hoc refinement if needed, with explicit statement if skipping clarification for prototypes only.

## Complete spec.md structure and standards

A quality spec.md contains eight mandatory sections following strict separation of WHAT/WHY from HOW.

**Feature Metadata** includes feature branch name (001-feature-name), creation date, status (Draft/Review/Approved), and original user description. **User Scenarios & Testing** documents concrete workflows with step-by-step interactions, expected behaviors, alternative paths, and decision points—missing clear user flow triggers ERROR. **Functional Requirements** use numbered format (FR-001, FR-002) with testable, unambiguous statements using MUST/SHOULD/MAY modal verbs. Each requirement traces to user stories, focuses on user value not implementation, and marks ambiguities.

**Success Criteria** define measurable, technology-agnostic outcomes mixing quantitative metrics (time, performance, volume) and qualitative measures (user satisfaction, task completion). All criteria must be verifiable post-release without implementation details. **Key Entities** (when feature involves data) describe what each entity represents, key attributes without database schemas, and relationships to other entities. **Edge Cases** cover empty states, boundary conditions, error scenarios with user-facing behaviors and recovery paths for each.

**Review & Acceptance Checklist** provides auto-generated validation covering content quality (no implementation details, focused on user value, written for non-technical stakeholders), requirement completeness (no [NEEDS CLARIFICATION] markers remain, requirements testable and unambiguous, success criteria measurable), and feature readiness (all functional requirements have acceptance criteria, user scenarios cover primary flows). **Clarifications Section** (populated by /clarify) records answers to [NEEDS CLARIFICATION] markers with rationale for design decisions and assumptions stated explicitly.

### User stories format and excellence

Stories follow standard structure but emphasize user value: "As a [persona], I want to [action], so that [benefit]." Focus on user perspective not system features, emphasize the "why" (business value), keep stories independent and testable, include context about user motivation.

**Contrast quality levels:**

```
❌ BAD: "As a user, I want photo management"
Vague actor, no specific action, missing value proposition

✓ GOOD: "As a content creator, I want to organize photos into date-based albums 
so that I can quickly find photos from specific events without manual sorting"
Clear role, specific need, concrete benefit, testable outcome
```

Write for non-technical stakeholders. Product managers should understand it immediately. Avoid databases, APIs, frameworks, and technical jargon.

### Acceptance criteria patterns

Each criterion must be **testable** with pass/fail results: "System MUST respond to health check within 100ms" beats "System should be fast." Make criteria **specific** using concrete, measurable terms: "User MUST be able to upload files up to 10MB" beats "User can upload reasonably sized files." Ensure **completeness** covering all requirement aspects: authentication method, supported providers, post-authentication redirect, and error handling—not just "System needs authentication."

**Format requirements rigorously:** Use modal verbs (MUST for mandatory, SHOULD for recommended, MAY for optional). Stay technology-agnostic: "System MUST store user preferences persistently" not "System MUST store preferences in PostgreSQL database." Include all scenarios: happy path, error conditions, edge cases, and boundary conditions.

**Production-quality example:**

```markdown
### Functional Requirements

FR-001: System MUST provide health check endpoint accessible via GET request to /health

FR-002: System MUST return operational status information in JSON format

FR-003: System MUST return HTTP status code 200 for healthy service

FR-004: System MUST bypass heavy operations (database connections, file I/O) to 
ensure rapid response

FR-005: System MUST respond within 100ms under normal load

FR-006: System MUST include service name, version, and timestamp in response

FR-007: System MUST return HTTP 503 with "degraded" status when experiencing issues

FR-008: System MUST handle up to 10,000 requests per second without performance impact
```

### Documenting workflows, edge cases, and errors

**User flow documentation** uses step-by-step workflows with decision points and alternative paths. Primary workflows show normal operation: "1. User selects photos from device, 2. System validates file types, 3. Photos upload with progress indication, 4. System extracts metadata, 5. Photos auto-sort into date albums, 6. User reviews and adjusts via drag-drop, 7. User saves final organization."

**Conditional workflows** document decision points: "1. User enters search term, 2. System displays results, 3. IF results > 100: System prompts for filters, 4. User optionally applies date/category filters, 5. System updates in real-time, 6. User selects photo for detail view."

**Edge case documentation** covers empty states ("User has not created albums yet → System displays welcome message with tutorial link"), boundary conditions ("User attempts file exceeding 10MB → System prevents upload, displays size limit message"), and data validation ("Photo has no date metadata → System places in 'Unsorted' album, user can manually assign").

**Error scenarios** define user-facing errors with clear recovery paths. For upload failure: "Network interruption during upload → Progress bar pauses, 'Connection lost' message displays → System auto-retries 3 times → Prompts user to retry manually → User clicks 'Retry Upload' button." For invalid file type: "User attempts non-image file → File rejected with message: 'Only image files (JPG, PNG, GIF) supported' → User selects different file."

Think like a tester: What happens at boundaries (0, 1, max values)? What if data is missing or invalid? What if operations fail or timing is unexpected? What about concurrent operations, network failures, or permission denials? Define user-friendly behavior with clear error messages, graceful degradation, recovery paths, and helpful suggestions.

## Post-generation review process

Validation occurs in four progressive quality gates. **Gate 1 (Spec Generation)** verifies all mandatory sections present, warns if [NEEDS CLARIFICATION] markers remain, errors if implementation details found, and errors if no clear user scenarios. **Gate 2 (Before /plan)** requires checklist fully reviewed and checked, all clarifications addressed, constitutional compliance verified, and human approval granted.

### Completeness verification checklist

Run this systematic validation after spec generation:

**Content Quality:**
- [ ] No implementation details (languages, frameworks, APIs)
- [ ] Focused on user value and business needs
- [ ] Written for non-technical stakeholders (product managers can understand)
- [ ] All mandatory sections completed
- [ ] Terminology used consistently throughout

**Requirement Completeness:**
- [ ] No [NEEDS CLARIFICATION] markers remain
- [ ] Requirements are testable and unambiguous
- [ ] All user types and permissions defined explicitly
- [ ] Edge cases and error scenarios included
- [ ] Success criteria clearly specified and measurable
- [ ] Each requirement maps to user story
- [ ] Non-functional requirements captured (performance, scale, security)

**Scope Clarity:**
- [ ] Feature boundaries clearly defined
- [ ] Out-of-scope items explicitly listed
- [ ] Dependencies on other features/systems identified
- [ ] Integration points specified
- [ ] Assumptions documented

**Constitutional Compliance:**
- [ ] Aligns with code quality standards from constitution.md
- [ ] Follows testing requirements
- [ ] Respects security/compliance rules
- [ ] Adheres to architectural constraints

### Quality assessment by section

**User Stories Section:** Each story follows "As a... I want... so that..." format, stories are user-centric not system-centric, clear value proposition in each story. Red flags: Technical implementation mentioned, vague benefits like "better experience."

**Functional Requirements Section:** Requirements are atomic and testable, each starts with "System MUST/SHALL/SHOULD," clear pass/fail criteria, no overlapping or duplicate requirements. Red flags: Subjective terms (fast, good, nice), combined requirements that should be split.

**Scenarios Section:** Step-by-step user workflows, expected system responses defined, error cases included, decision points documented. Red flags: Missing error/edge cases, assumes technical knowledge.

### Cross-cutting validation prompts

Use these AI prompts to validate specifications:

**Check checklist completion:**
```
Read the review and acceptance checklist, and check off each item if the feature 
spec meets the criteria. Leave it empty if it does not. For any unchecked items, 
explain what's missing and how to address it.
```

**Audit for missing context:**
```
Audit the specification to determine whether there's a sequence of user actions 
that are obvious from reading this. Identify gaps where user workflows are unclear 
or missing critical steps.
```

**Check for over-engineering:**
```
Before moving to /plan, identify any aspects of this specification that seem 
over-engineered or include components that were not requested. Ask for clarification 
on the rationale and source for each addition.
```

**Verify constitutional alignment:**
```
Read constitution.md and verify this specification aligns with:
- Code quality standards
- Testing requirements  
- Security/compliance rules
- Architectural constraints

Flag any conflicts or violations.
```

**Gap detection prompt:**
```
I think we need to break this down into a series of steps. First, identify areas 
in the specification that could benefit from additional detail. List those areas. 
Then for each one, ask me specific questions to fill those gaps.
```

### The /analyze command for validation

Run `/analyze` after `/tasks`, before `/implement` to validate cross-artifact consistency. This checks spec-plan alignment, plan-tasks alignment, constitutional compliance, coverage gaps, and consistency issues. Severity levels: **CRITICAL** blocks /implement (must fix), **WARNING** should address but not blocking, **INFO** provides suggestions for improvement.

Analyze validates that requirements from spec.md are addressed in plan.md, tasks in tasks.md trace to plan requirements, constitution principles are followed throughout, and no critical findings exist before proceeding to implementation.

## Templates and copy-paste resources

### Constitution template

```markdown
# Project Constitution

## Article I: Code Quality Standards
- Minimum 80% test coverage for all business logic
- SOLID principles applied to all classes and modules
- Code reviews required before merging to main
- No commented-out code in production branches

## Article II: Testing Requirements
- Unit tests for all business logic
- Integration tests for all API endpoints
- End-to-end tests for critical user workflows
- Tests must pass before merge

## Article III: Security Standards
- Input validation on all user-provided data
- Authentication required for all protected endpoints
- Secrets stored in environment variables, never in code
- HTTPS enforced in production

## Article IV: Performance Requirements
- API response times under 200ms for standard queries
- Frontend initial load under 2 seconds
- Database queries optimized with proper indexing
- Caching implemented for frequently accessed data

## Article V: [Your Domain-Specific Principle]
[Add principles specific to your project type]
```

### /specify input template

```markdown
/specify [Feature Name]

USER CONTEXT:
[Who will use this? What roles/personas? What's their technical level?]

PROBLEM STATEMENT:
[What problem does this solve? What pain point are users experiencing?]

CORE FUNCTIONALITY:
[What actions can users perform? Be specific and concrete.]
- [Primary action 1]
- [Primary action 2]  
- [Primary action 3]

USER WORKFLOWS:
[Describe step-by-step what users do]
1. [Step 1]
2. [Step 2]
3. [Step 3]

CONSTRAINTS:
[What are the boundaries and rules?]
- [Constraint 1]
- [Constraint 2]

SUCCESS OUTCOMES:
[How do we know this succeeded for users?]
- [Measurable outcome 1]
- [Measurable outcome 2]

OUT OF SCOPE:
[What explicitly is NOT included?]
- [Excluded feature 1]
- [Excluded feature 2]
```

### Spec.md review template

```markdown
# Specification Review: [Feature Name]

## Reviewer: [Your Name]
## Date: [Review Date]
## Status: [Draft / Needs Revision / Approved]

### Content Quality Review
- [ ] No implementation details present
- [ ] Focused on user value
- [ ] Non-technical stakeholders can understand
- [ ] All mandatory sections complete

**Issues Found:**
[List any violations]

### Requirement Quality Review
- [ ] All requirements testable
- [ ] No [NEEDS CLARIFICATION] markers remain
- [ ] Edge cases covered
- [ ] Success criteria measurable

**Issues Found:**
[List any gaps or unclear requirements]

### Constitutional Compliance Review
- [ ] Aligns with testing standards
- [ ] Follows security requirements
- [ ] Respects architectural principles
- [ ] Meets performance expectations

**Issues Found:**
[List any conflicts with constitution]

### Gap Analysis
**Missing Elements:**
1. [Gap 1]
2. [Gap 2]

**Recommendations:**
1. [Recommendation 1]
2. [Recommendation 2]

### Approval Decision
[ ] APPROVED - Ready for /plan phase
[ ] NEEDS REVISION - Address issues above before proceeding
[ ] REJECTED - Fundamental problems, restart /specify

**Rationale:**
[Explain decision]
```

## AI collaboration patterns for spec-kit

### Pattern 1: Constitutional enforcement

AI validates against constitution at each phase using gate checks embedded in templates. Before planning, verify: Using ≤3 projects? (Simplicity Gate), Using framework features directly? (Framework Trust), Contract tests before implementation? (Test-Driven Quality). This prevents common mistakes early when they're cheapest to fix.

### Pattern 2: Iterative spec refinement

Generate spec, review it, refine it, and repeat until quality gates pass. Treat AI's first attempt as draft, never final. Use /clarify for structured questioning. Validate acceptance checklist after each iteration. This pattern produces specifications that withstand implementation challenges.

### Pattern 3: Research-driven planning

For rapidly evolving technology stacks, explicitly ask AI to research current best practices. Example: "Go through the implementation plan and identify areas that would benefit from research on .NET Aspire. Update research.md with specific version details and spawn parallel research tasks." This ensures specs use current patterns, not outdated training data.

### Pattern 4: Implementation plan auditing

Never go directly from /plan to /implement. Audit for completeness: "Audit the implementation plan to determine if there's a clear sequence of tasks. Reference specific sections in implementation details where needed. Check for gaps where prerequisites are missing or dependencies are unclear."

### Pattern 5: Agent-specific workflows with portable specs

Spec-kit supports 11+ AI agents (Claude Code, GitHub Copilot, Gemini CLI, Cursor, Windsurf, Qwen Code, others) with agent-specific directories (.claude/commands/, .github/prompts/, .gemini/commands/). The key insight: same spec.md works across all agents because specifications are decoupled from code. You can generate implementations in multiple languages or frameworks from a single spec, enabling parallel exploration of technical approaches.

### Pattern 6: Cross-artifact validation

Use /analyze after /tasks, before /implement to validate consistency across spec, plan, and tasks. Constitutional violations are treated as CRITICAL findings that block implementation. This systematic validation prevents costly rework discovered during coding.

## Real-world examples and case studies

### Production success: Tweeter clone at scale

Developer MartyBonacci built a Twitter clone using spec-kit across 14 complete features with React Router v7. Results over 6 months: zero regressions, zero breaking changes, 100% build success rate. The secret: extending vanilla spec-kit (which only covered 25% of work—new features) with five additional workflows.

**/bugfix workflow** (20-30% of dev time) enforces regression test BEFORE fix. Example: Profile form crash fixed in 1 hour with test coverage preventing recurrence.

**/modify workflow** (30-40% of dev time) requires impact analysis before changes. Example: Making profile fields optional triggered automatic dependency detection across 8 affected files.

**/refactor workflow** (10-15% of dev time) captures baseline metrics before changes. Example: Extracting reusable avatar component completed with zero behavior changes verified by tests.

**/hotfix workflow** (5-10% of dev time) is the exception—tests AFTER fix for speed, but mandatory post-mortem within 48 hours documents the issue.

**/deprecate workflow** (5-10% of dev time) uses 3-phase sunset: Warnings, Disabled, Removed. Dependency analysis prevents breaking changes.

**Key lesson:** Quality gates prevent mistakes that cause regressions. When extended to complete software lifecycle, spec-kit becomes a full development methodology covering 100% of engineering work, not just 25%.

### API-first development: Specmatic integration

The specmatic-mcp-sample-with-spec-kit project demonstrates organic OpenAPI evolution. Feature 1 creates initial API with GET /products. Feature 2 analyzes existing spec before adding POST /products. Feature 3 reuses existing GET /products instead of creating duplicate endpoint. This prevents API bloat through reuse analysis, with contract serving as agreement between frontend and backend teams.

### Markdown as programming: GitHub Brain

GitHub employee wham built github-brain MCP server where entire app is "written" in Markdown (main.md), GitHub Copilot "compiles" it into Go code (main.go), and development rarely touches Go directly—iterations happen in the spec. This pattern succeeds for command-line tools and well-defined domain logic, particularly in greenfield projects.

## Anti-patterns and gotchas from production use

**Generic constitutions** provide no value. Using default constitution without customization means AI doesn't enforce project-specific conventions. Solution: Spend time crafting constitution tailored to your domain, update iteratively as patterns emerge.

**Skipping clarification phase** causes expensive rework. Going directly from /specify to /plan compounds ambiguities through planning, tasks, and implementation. Solution: Always run /clarify unless explicitly choosing exploratory prototype mode.

**Context isolation confusion** occurs when mixing AI agents (Claude Code + Cursor simultaneously). This causes outdated specs to load and conflicting implementations. Solution: Use one AI agent per feature/branch, archive completed specs.

**File path confusion** happens when AI reads /memory/constitution.md from wrong directory, causing constitution to not apply to planning. Solution: Use absolute paths in scripts.

**Over-eager AI additions** introduce scope creep through "helpful" components nobody requested. Solution: Ask AI to clarify rationale and source of EVERY change not explicitly in the spec.

**Incomplete implementations** follow excellent specs when task breakdown is too large or AI loses context. Solution: Small, focused tasks like "Create email validation endpoint" instead of "Build authentication."

**Using spec-kit on large existing codebases** struggles because spec-kit assumes greenfield development. Workarounds: Generate constitution from existing patterns, start with new features not refactors, use /modify workflows for changes.

## Success criteria at each workflow stage

**Constitution phase success:** Principles are specific to your project domain, not generic platitudes. Standards are enforceable through validation. Examples clarify each principle. Team consensus exists on all articles.

**Specify phase success:** All mandatory sections present. No implementation details leaked. User scenarios describe concrete workflows. Requirements testable with pass/fail criteria. Maximum 3 [NEEDS CLARIFICATION] markers for truly ambiguous decisions. Scope boundaries explicit. Success metrics measurable.

**Clarify phase success:** All [NEEDS CLARIFICATION] markers resolved. Answers recorded in Clarifications section. Rationale documented for design decisions. Assumptions explicitly stated. No remaining ambiguities that would block planning.

**Pre-plan approval success:** Review checklist fully validated. Constitutional compliance verified. Human stakeholder approval granted. No critical gaps in user stories or acceptance criteria. Edge cases and error scenarios covered. Team consensus on proceeding to technical planning.

**Plan phase success:** Technical approach addresses all functional requirements. Architecture aligns with constitutional principles. Research.md documents stack decisions with rationale. Data model captures entities and relationships. API contracts or integration points specified. Quickstart.md enables validation. No over-engineering beyond requirements.

**Tasks phase success:** Tasks are atomic and independently testable. Dependencies clearly marked. Parallel execution opportunities identified. Each task traces to plan and spec. TDD approach possible for each task. Estimated effort reasonable for review cycles.

**Analyze phase success:** No CRITICAL findings (blocks proceed). Warnings addressed or explicitly accepted. Spec-plan-tasks alignment validated. Constitutional compliance confirmed. Coverage gaps identified and resolved.

**Implementation phase success:** All tasks completed with tests passing. Specifications fully realized in code. No undocumented deviations from plan. Constitutional principles followed. Human review confirms quality. Feature ready for production deployment.

## Quick reference card

**Golden Rules:**
1. Separate WHAT/WHY (spec) from HOW (plan)—never mix
2. Clarify ambiguities explicitly—never let AI guess
3. One feature per spec—break MVPs into 3-7 distinct features
4. Constitution first—establish principles before specifications
5. Quality gates matter—don't skip checklists or rush to implement

**Red Flags in /specify Input:**
- Tech stack mentioned (React, PostgreSQL, etc.)
- Subjective terms ("fast", "good", "nice")
- Missing error scenarios or edge cases
- Undefined user roles or permissions
- Vague requirements without concrete criteria

**Mandatory Spec.md Sections:**
1. Feature Metadata (branch, date, status)
2. User Scenarios & Testing (workflows)
3. Functional Requirements (FR-001, FR-002...)
4. Success Criteria (measurable outcomes)
5. Key Entities (if data involved)
6. Edge Cases (empty states, errors, boundaries)
7. Review & Acceptance Checklist
8. Clarifications (from /clarify command)

**Review Process:**
1. Generate spec with /specify
2. Run /clarify for structured questioning
3. Validate each section against standards
4. Check for implementation leaks
5. Verify constitutional compliance
6. Challenge vague or subjective terms
7. Get human approval before /plan
8. Run /analyze before /implement

**When Spec-Kit Works Best:**
- Greenfield projects with clear intent
- Well-defined domain logic
- Command-line tools and APIs
- Features with concrete user workflows
- Teams committed to quality gates

**When Spec-Kit Struggles:**
- Large existing codebases (use /modify workflows)
- Legacy modernization (generate constitution from code first)
- Exploratory prototypes (explicitly skip clarification)
- Rapidly changing requirements (embrace iterative refinement)

This methodology transforms AI coding from unpredictable "vibe coding" into systematic, repeatable Spec-Driven Development. The specifications you craft become executable artifacts that generate implementations matching true intent, with quality gates preventing the common mistakes that cause regressions and technical debt. Success requires discipline: follow the workflow, enforce constitutional principles, validate at every gate, and never skip clarification for production features.