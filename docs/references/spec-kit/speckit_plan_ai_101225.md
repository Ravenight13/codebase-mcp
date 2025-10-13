```
# AI Agent Guide: /plan Command Execution & Review

## Your Mission
Transform the approved specification into a technical blueprint that guides implementation. You generate architecture decisions, research documentation, data models, and API contracts while enforcing constitutional principles and preventing over-engineering.

## Pre-Flight Checks (MANDATORY - DO NOT PROCEED WITHOUT THESE)

**STOP and verify before generating plan.md:**

1. **Constitution exists**: `constitution.md` must be present with populated principles
2. **Spec is complete**: `spec.md` exists with all mandatory sections filled
3. **Clarifications resolved**: No `[NEEDS CLARIFICATION]` markers remain in spec (unless human explicitly overrides for prototype)
4. **Review checklist validated**: Spec's Review & Acceptance Checklist is 100% complete
5. **Human approval granted**: Explicit confirmation to proceed to /plan

**If any check fails**: HALT and inform human of missing prerequisites. Do not guess or proceed.

## Core Principle: Separation of Concerns

**plan.md contains**: Architecture decisions, technology choices, high-level approach, constitutional alignment
**plan.md NEVER contains**: Code samples, implementation details, variable names, specific algorithms

**Move details to**:
- `research.md` - Technology validation, benchmarks, alternative analysis
- `data-model.md` - Entity definitions, schemas, relationships
- `contracts/` - OpenAPI specs, API definitions
- `quickstart.md` - Setup instructions, validation scenarios

## plan.md Structure (Follow This Template)

```markdown
Branch: [branch-name] | Date: [YYYY-MM-DD] | Spec: specs/###-feature-name/spec.md

## Technical Context

Language/Version: [Specific version - Python 3.11, NOT just "Python"]
Primary Dependencies: [Major frameworks only - FastAPI 0.104, React 18]
Storage: [PostgreSQL 15 | N/A | Files | Redis]
Testing: [pytest | Jest | XCTest - must specify]
Target Platform: [Linux server | iOS 15+ | Modern browsers]
Project Type: [single | web | mobile - MUST choose one, justify, remove others]
Performance Goals: [SPECIFIC numbers - 1000 req/s, <200ms p95, NOT "fast"]
Constraints: [Real limits - <512MB memory, offline-capable]
Scale/Scope: [Concrete metrics - 1000 users initially, 10k year 1]

**CRITICAL**: Replace every "NEEDS CLARIFICATION" with specific value or PAUSE and ask human.

## Constitution Check (Pre-Design)
[Evaluate against constitution.md principles]
- Security requirements: [Specific compliance - JWT auth, TLS 1.3]
- Testing mandate: [How TDD will be enforced - contract tests first]
- Architectural patterns: [Which principles apply - library-first, etc.]
- **Violations**: [List any with explicit justification OR simplify approach]

## Source Tree Structure
[Select ONE structure based on requirements, REMOVE unused options]

FOR SINGLE PROJECT:
src/
├── models/
├── services/
├── cli/
└── lib/
tests/
├── contract/
├── integration/
└── unit/

FOR WEB APPLICATION:
backend/src/
├── models/
├── services/
└── api/
frontend/src/
├── components/
├── pages/
└── services/

FOR MOBILE + API:
api/
└── [backend structure]
ios/
└── [feature modules]
android/
└── [feature modules]

**Justification**: [Why this structure fits the requirements]

## Implementation Approach
[High-level architectural strategy - 3-5 sentences max]
[Reference spec sections: "Implements FR-001, FR-003 from spec.md"]

## Execution Flow
1. ✅ Load spec from specs/###-feature-name/spec.md
2. ✅ Technical Context completed, Project Type: [chosen type]
3. ✅ Constitution Check: [Pass/Violations documented]
4. [Phase 0] Generate research.md
5. [Phase 1] Generate data-model.md, contracts/, quickstart.md
6. [Phase 1] Update agent context (.github/copilot-instructions.md or CLAUDE.md)
7. Re-evaluate Constitution Check (Post-Design)
8. Generate Progress Tracking
9. Validate completeness

## Progress Tracking
- Initial Constitution Check: [✅ Complete | 🔄 In Progress | ⏸️ Pending | ❌ ERROR]
- Phase 0 (Research): [status]
- Phase 1 (Design): [status]
- Post-Design Constitution Check: [status]
[Document any ERROR or WARN states with details]

```
## **Phase 0: Generate research.md**  
**Purpose**: Validate technology choices with version-specific details  
**Must include**:  
* **Options evaluated**: List 2-3 alternatives considered (e.g., FastAPI vs Flask vs Django)  
* **Decision rationale**: Why chosen option wins (performance data, ecosystem maturity, team expertise)  
* **Trade-offs accepted**: Known limitations you're accepting  
* **Version specificity**: Exact versions for rapidly-changing tech (.NET Aspire 8.0.1, not just "Aspire")  
* **Known issues**: Document version-specific bugs or limitations  
* **Constitutional alignment**: How choices respect project principles  
**For each major technology decision**:  
```
### [Technology Name]

**Decision**: [Specific choice - PostgreSQL 15 with pgvector extension]
**Context**: [Problem being solved - Need vector similarity search for 10k+ embeddings]
**Alternatives**:
- Option A: [Why rejected - Redis: 50ms vs 5ms for Postgres, but adds dependency]
- Option B: [Why rejected - Pinecone: Best performance but $70/month cost]
**Rationale**: [Why winner - Postgres meets <10ms requirement, zero added cost]
**Trade-offs**: [What you're accepting - Slightly slower than Pinecone, acceptable for use case]
**Version**: [Specific version - PostgreSQL 15.4 with pgvector 0.5.1]
**Known Issues**: [Version-specific problems - pgvector 0.5.0 has index corruption bug, fixed in 0.5.1]

```
## **Phase 1: Generate Artifacts**  
## **data-model.md**  
**For each entity**:  
```
## Entity: [Name]

**Purpose**: [What it represents in business domain]
**Lifecycle**: [Created when] → [Updated when] → [Deleted how]

**Fields**:
| Field | Type | Constraints | Business Rules |
|-------|------|-------------|----------------|
| id | UUID | PK, immutable | Auto-generated |
| name | VARCHAR(255) | NOT NULL | User-facing ID |
| status | ENUM | Required | draft|active|archived |

**Relationships**:
- Belongs to: [Parent] via parent_id (CASCADE on delete)
- Has many: [Children] (NULLIFY on delete)

**Business Invariants**:
- [Rule that must ALWAYS be true - "Task must belong to exactly one project"]
- [State transition rule - "Status transitions are unidirectional: draft→active→archived"]
- [Capacity constraint - "Max 15 tasks per project"]

**Indexes**:
- (field_name) BTREE - for [specific query: "Find tasks by status"]

```
**DO NOT**: Include database-specific implementation details. Keep conceptual.  
## **contracts/ Directory**  
**Generate OpenAPI specs for REST APIs**:  
* One file per resource group: contracts/tasks.yaml, contracts/projects.yaml  
* Complete request/response schemas with validation  
* Error response formats (400, 401, 403, 404, 500)  
* Authentication requirements  
* Example values demonstrating usage  
**Key elements**:  
```
paths:
  /api/v1/resource:
    get:
      summary: [Clear description]
      parameters: [With validation constraints]
      responses:
        '200': [Success schema]
        '400': [Validation error schema]
        '401': [Auth error schema]
      security: [Auth requirements]

```
## **quickstart.md**  
**Purpose**: Enable anyone to validate the feature setup  
**Must include**:  
1. Prerequisites with exact versions  
2. Installation commands that work copy-paste  
3. Configuration steps with example values  
4. Validation scenarios to confirm setup  
5. Common troubleshooting for known issues  
**Structure**:  
```
## Prerequisites
- [Tool] [Exact version - Node.js 20.10.0]

## Installation
```bash
# Exact commands that work
npm install package@1.2.3

```
## **Configuration**  
[Step-by-step with example values]  
## **Validation**  
[How to confirm it works - "Run curl localhost:3000/health, expect 200 OK"]  
## **Troubleshooting**  
[Common issues with fixes]  
```
### Agent Context Updates
**Update `.github/copilot-instructions.md` or `CLAUDE.md`** with:
- Feature-specific context
- Architecture decisions made
- Constitutional principles to follow
- Testing approach required

## Constitution Check (Post-Design)

**After generating all artifacts, re-evaluate**:
- Does technical approach still align with principles?
- Did complexity creep in during detailed design?
- Are there violations that weren't obvious initially?
- Can any violations be eliminated through simplification?

**If violations found**: Either justify explicitly OR simplify the approach.

## Anti-Patterns to Actively Prevent

### 1. God Plan (plan.md exceeds 1000 lines)
**Symptom**: Code samples, implementation details, variable names in plan.md
**Fix**: Move details to implementation-details/ subfolder, keep plan.md high-level

### 2. Vague Technical Context
**Symptom**: "Language: Python" without version, "Performance: Fast" without numbers
**Fix**: Specific versions (Python 3.11), concrete metrics (<200ms p95 latency)

### 3. Premature Library Selection
**Symptom**: Adding frameworks/libraries not justified by requirements
**Fix**: For each dependency ask: "Where in spec was this needed? What problem does it solve?"

### 4. Missing Error States
**Symptom**: Only happy path documented
**Fix**: Explicitly enumerate empty states, error conditions, edge cases, rate limits

### 5. Implementation Leak to plan.md
**Symptom**: Code snippets, algorithms, variable names in plan.md
**Fix**: Extract to appropriate detail files, reference by section

### 6. Assuming Defaults Without Documentation
**Symptom**: Unspoken assumptions about auth, caching, deployment
**Fix**: Make every assumption explicit. If it matters, document it.

## Quality Gates (YOU MUST VALIDATE)

**Before declaring Phase 0 complete**:
- [ ] research.md exists with version-specific details
- [ ] Every major technology choice has documented rationale
- [ ] Trade-offs explicitly stated
- [ ] Alternatives evaluated with rejection reasons

**Before declaring Phase 1 complete**:
- [ ] data-model.md documents all entities
- [ ] contracts/ contains all API specifications
- [ ] quickstart.md provides executable setup
- [ ] Agent context files updated
- [ ] No "NEEDS CLARIFICATION" markers remain
- [ ] Post-design constitution check completed

**Before declaring plan complete**:
- [ ] All sections in plan.md template filled
- [ ] Project structure choice made and justified
- [ ] Performance goals are specific numbers
- [ ] Progress tracking shows all phases complete
- [ ] Over-engineering audit passed

## Human Interaction Protocol

### When to ASK (PAUSE execution):
1. Any "NEEDS CLARIFICATION" marker remains in spec
2. Technology choice has multiple equally valid options with different implications
3. Performance requirements are vague ("fast", "scalable")
4. Constitutional principle violation requires explicit approval
5. Spec-to-plan translation requires assumption you're uncertain about

### When to DECIDE (Proceed autonomously):
1. Standard industry practices apply (OAuth2 for web auth)
2. Constitutional principles clearly dictate approach
3. Spec provides explicit requirements matching your interpretation
4. Technical choice has obvious winner based on requirements
5. Clarifications section already addressed the question

### How to ASK effectively:
**BAD**: "Should I use React or Vue?"
**GOOD**: "Spec requires real-time updates and offline capability. Options: React with IndexedDB (mature, 50MB bundle) vs Vue with LocalForage (smaller, less real-time tooling). Performance requirement is <2s load on 3G. Recommendation: React for better real-time libraries despite size. Confirm or prefer Vue?"

**Format**: [Context] → [Options with pros/cons] → [Recommendation with reasoning] → [Request decision]

## Post-/plan Review Process

### Your Self-Review Checklist

**Run this before declaring plan complete**:


```
I have verified:  
* [ ] Technical Context has NO "NEEDS CLARIFICATION" markers  
* [ ] Project structure choice made, unused options removed  
* [ ] Performance goals use specific numbers (req/s, ms, MB)  
* [ ] research.md validates tech choices with versions  
* [ ] data-model.md documents entities with relationships  
* [ ] contracts/ contains API specifications  
* [ ] quickstart.md enables validation  
* [ ] Constitution check completed pre and post design  
* [ ] Progress tracking shows all phases complete  
* [ ] Over-engineering audit passed  
```
	•	[ ] Plan.md is <500 lines (details extracted to other files)

```
```
### Prompt Human for Review

**After self-review passes, provide this summary**:


```
## **Plan Complete - Ready for Review**  
**Artifacts Generated**:  
* plan.md: [X lines, architectural decisions]  
* research.md: [Key technology validations]  
* data-model.md: [X entities documented]  
* contracts/: [X API specifications]  
* quickstart.md: [Setup and validation]  
**Key Decisions Made**:  
1.   
2.   
3.   
**Constitutional Compliance**:  
* [Principle 1]: ✅ Compliant  
* [Principle 2]: ⚠️ Deviation (justified: [reason])  
**Next Steps**:  
1. Review plan.md for architecture approach  
2. Validate research.md technology choices  
3. Confirm data-model.md matches domain  
4. Review contracts/ API design  
5. Run: /analyze to validate cross-artifact consistency  
6. Approve to proceed to /tasks phase  
```
Questions for You: [List any decisions where you want human input]
## Using /analyze Command

**After plan approval, before /tasks, run**:

```
/analyze  
```
**This validates**:
- Spec-to-plan alignment (requirements addressed)
- Plan-to-constitution compliance (principles followed)
- Completeness coverage (gaps identified)
- Cross-artifact consistency (plan/spec/constitution agree)

**Severity Levels**:
- **CRITICAL**: Blocks /implement, MUST fix
- **WARNING**: Should address, doesn't block
- **INFO**: Suggestions for improvement

**If CRITICAL findings**: STOP. Fix issues. Re-run /analyze. Do not proceed to /tasks until clean.

## Iterative Refinement Pattern

**Treat first /plan output as draft, not final**. Use this cycle:

1. **Generate initial plan** following template
2. **Self-review** against quality gates
3. **Human reviews** - expect feedback
4. **Refine plan** addressing feedback
5. **Validate completeness** with /analyze
6. **Iterate** until approval granted

**Never treat first attempt as final. Always expect refinement.**

## Over-Engineering Detection

**Before finalizing plan, audit for**:

**At spec level**:
- Speculative "might need" features → Remove
- "Nice to have" without clear criteria → Remove
- Features not tracing to user stories → Remove

**At plan level**:
- Tech stack oversized for requirements → Simplify
- Unnecessary abstractions → Use concrete approaches
- "Clever" solutions → Replace with simple patterns
- Premature optimizations → Remove (mark as [FUTURE])

**Prompt for human validation**:

```
Cross-check plan for over-engineered components. I've identified: [List potential over-engineering]  
Recommendations: [Specific simplifications]  
Confirm simplifications or justify complexity.  
```
## Technology Stack Decision Framework

### Must Specify (Lock In):
- Primary language and major version
- Core framework
- Database technology
- API design approach (REST/GraphQL/gRPC)
- Authentication mechanism

### Should Specify (Document):
- Major libraries for core functionality
- Testing frameworks
- Build/deployment tools
- State management approach

### Can Defer (Optional):
- Utility libraries
- CSS frameworks (unless design system mandated)
- Logging libraries
- Development tools

### Lock In When:
- Organizational constraints exist (company stack)
- Compliance requires specific tech
- Legacy integration demands matching tech
- Team expertise critical with tight deadlines
- Performance requires proven benchmarks

### Keep Flexible When:
- Technology rapidly evolving (document for research)
- Exploring implementation variants
- Building libraries (abstract interfaces)
- Early prototyping (defer until validation)

## Success Criteria

**You've succeeded when**:
1. Human approves plan without major revisions
2. /analyze reports zero CRITICAL findings
3. All quality gates pass
4. Constitutional principles respected (or violations justified)
5. Plan.md readable, details properly extracted
6. Next phase (/tasks) can begin immediately

**You've failed when**:
1. Human requires complete plan regeneration
2. CRITICAL findings in /analyze
3. Implementation leak (code in plan.md)
4. Vague metrics ("fast", "scalable")
5. Over-engineered beyond requirements
6. Constitutional violations without justification

## Final Directive

Your goal is a **technical blueprint that guides implementation, not a code tutorial**. Architecture decisions belong in plan.md. Implementation details belong elsewhere. Constitutional principles are non-negotiable. Quality gates prevent expensive mistakes.

Execute with precision. Ask when uncertain. Document ruthlessly. Simplify aggressively. Validate constantly.

**Now generate the plan.**

```
This document is ready to use as a reference guide for AI agents working on the /plan phase. It's written in a direct, actionable style that an AI can follow systematically while maintaining the quality standards and avoiding common pitfalls.  
