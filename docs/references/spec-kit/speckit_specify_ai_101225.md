# AI Agent Guide: /specify Command Execution & Review

## Your Mission
Transform user intent into a clear, complete feature specification that captures WHAT users need and WHY it matters—without dictating HOW to build it. You're defining the problem space, not the solution space.

---

## 1. Summary: The /specify Command

**Purpose**: Generate spec.md that serves as the source of truth for feature requirements.

**Core Philosophy**: Radical separation of concerns
- **spec.md contains**: User needs, business value, workflows, success criteria
- **spec.md NEVER contains**: Tech stack, frameworks, databases, code patterns

**Output**: A spec.md file with 8 mandatory sections that:
- Non-technical stakeholders can understand
- Provides clear acceptance criteria
- Identifies ambiguities explicitly
- Serves as basis for technical planning

**Workflow Position**: /constitution → **→ /specify →** /clarify → /plan → /tasks → /implement

**Reference**: For complete methodology, anti-patterns, and examples, see:
- "Spec-Kit Mastery Guide: From Specification to Implementation with AI-Driven Development.md"
- Sections on "Crafting exceptional /specify inputs" and "Complete spec.md structure"

---

## 2. Pre-/specify Focus: Prerequisites & Setup

### MANDATORY PRE-FLIGHT CHECKS

**STOP. Verify before generating spec.md:**

1. **Constitution exists**: `.specify/memory/constitution.md` present with populated principles
2. **Feature scope defined**: This is ONE feature, not an entire product/MVP
3. **User context available**: You know WHO will use this and WHY they need it
4. **Input quality**: User provided problem description with sufficient detail

**If any check fails**: Request missing information. Do NOT proceed with assumptions.

### Understanding Feature Scope

**DO decompose large requests**:
- "Build e-commerce platform" → Split into: 001-product-catalog, 002-shopping-cart, 003-checkout, 004-user-accounts
- "Add social features" → Split into: 001-user-profiles, 002-follow-system, 003-activity-feed

**DO focus on single capability**:
- ✅ "Users can organize photos into date-based albums"
- ❌ "Users can manage photos, share them, edit them, and create slideshows"

### Essential Input Components

Extract or elicit from user:

**User Context** (WHO):
- Persona/role (casual photographers, project managers, developers)
- Technical level (power users vs beginners)
- Scale (10 users vs 10,000 users)

**Problem Statement** (WHY):
- Pain point being solved
- Current workflow that's broken
- Business value delivered

**Core Functionality** (WHAT):
- Primary actions users can perform
- Key workflows start-to-finish
- Constraints and boundaries

**Success Criteria** (HOW MEASURED):
- Quantitative metrics (time saved, error reduction)
- Qualitative outcomes (user satisfaction indicators)

**Scope Boundaries** (WHAT'S OUT):
- Explicitly excluded features
- Future considerations (not this iteration)
- Dependencies on other features

---

## 3. /specify Focus: Generating spec.md

### The Golden Rule

**YOU MUST NOT**:
- Mention programming languages, frameworks, libraries
- Specify databases, APIs, or architectural patterns
- Include code structure, variable names, or algorithms
- Prescribe technical solutions

**YOU MUST**:
- Describe user journeys and interactions
- Define business rules and constraints
- Specify measurable success criteria
- Identify edge cases and error scenarios
- Mark genuine ambiguities with [NEEDS CLARIFICATION]

### spec.md Structure (Follow This Template)

```markdown
# Feature: [Name]

Branch: [###-feature-name] | Date: [YYYY-MM-DD] | Status: [Draft]

## Original User Description
[Paste original request here, preserve context]

---

## User Scenarios & Testing

### Primary Workflow
[Step-by-step user journey - this is MANDATORY, if missing = ERROR]

1. User [action with specific context]
2. System [expected behavior with acceptance criteria]
3. User [decision point or next action]
4. System [response with edge case handling]

### Alternative Paths
[Decision points and branches]

IF [condition]:
  - System [alternative behavior]
ELSE:
  - System [default behavior]

### Edge Cases Covered
[Explicit scenarios - do NOT auto-generate generic ones]

**Empty States**: [What happens with no data]
**Boundary Conditions**: [Limits, maximums, minimums]
**Error Scenarios**: [Network failures, invalid input, timeouts]
**Permission Denials**: [Unauthorized actions]
**Concurrent Operations**: [Multiple users, race conditions]

---

## Functional Requirements

[Use FR-### numbering, start each with MUST/SHOULD/MAY]

**FR-001**: System MUST [specific, testable requirement]
- Acceptance Criteria: [Pass/fail conditions]
- Traces to: [User scenario step]

**FR-002**: System MUST [another requirement]
- Acceptance Criteria: [Measurable criteria]
- Traces to: [User scenario step]

[Use [NEEDS CLARIFICATION: specific question with context] for genuine ambiguities]
[MAXIMUM 3 markers per specification]

**When to mark**:
- Critical decisions with multiple valid interpretations
- Ambiguous scope boundaries affecting feature size
- Unspecified user types/permissions
- Missing constraints that significantly impact approach

**When NOT to mark** (use reasonable defaults):
- Standard performance expectations for domain
- Industry-standard patterns (OAuth for web auth)
- Common UX patterns (error messages, loading states)

---

## Success Criteria

[Measurable, technology-agnostic outcomes]

### Quantitative Metrics
- [Specific number: "Users find photos 3x faster than manual browsing"]
- [Time-based: "Organization tasks complete in under 2 minutes"]
- [Performance: "System responds in under 200ms for 1000 items"]

### Qualitative Measures
- [User satisfaction: "95% complete tasks without help documentation"]
- [Error reduction: "Photo misfiling reduced by 80%"]
- [Adoption: "80% of users actively organize within first week"]

**NO VAGUE ADJECTIVES**: "fast", "good", "scalable", "user-friendly" are banned
**USE SPECIFIC CRITERIA**: Numbers, percentages, time limits, completion rates

---

## Key Entities (if feature involves data)

[Describe WHAT entities represent, not HOW they're stored]

### Entity: [Name]
**Purpose**: [Business meaning - "Represents a collection of related photos"]
**Lifecycle**: [Created when → Updated when → Deleted how]
**Key Attributes**:
- [Attribute]: [Business meaning, constraints, validation rules]
- [Relationship]: [How it relates to other entities]

**Business Invariants**:
- [Rule that must always be true]
- [Constraint that never changes]

**DO**: Describe business meaning and rules
**DON'T**: Specify database schemas, field types, indexes

---

## Edge Cases & Error Handling

[Explicit scenarios with expected user-facing behavior]

### Empty States
**Scenario**: [User has no albums yet]
**Behavior**: [Display welcome message with "Create Album" prompt]
**Recovery**: [Guide to creating first album]

### Boundary Conditions
**Scenario**: [User attempts to upload 10GB photo]
**Behavior**: [Reject with clear message: "Max file size: 50MB"]
**Recovery**: [Suggest compression or alternate method]

### Error Scenarios
**Scenario**: [Network interruption during upload]
**Behavior**: [Progress pauses, "Connection lost" message]
**Recovery**: [Auto-retry 3x, then prompt manual retry]

### Permission Denials
**Scenario**: [User attempts to delete another user's album]
**Behavior**: [Deny with message: "Only album owner can delete"]
**Recovery**: [Suggest requesting ownership transfer]

**CRITICAL**: Think like a tester. What breaks? What's unexpected? What's the user experience when things go wrong?

---

## Review & Acceptance Checklist

**Content Quality**:
- [ ] No implementation details (languages, frameworks, databases)
- [ ] Focused on user value and business needs
- [ ] Written for non-technical stakeholders
- [ ] All mandatory sections complete
- [ ] Terminology consistent throughout

**Requirement Completeness**:
- [ ] No [NEEDS CLARIFICATION] markers remain (or max 3 with valid reason)
- [ ] All requirements testable and unambiguous
- [ ] User types and permissions explicitly defined
- [ ] Edge cases and error scenarios included
- [ ] Success criteria measurable and specific
- [ ] Each requirement traces to user story
- [ ] Non-functional requirements captured (performance, scale, security)

**Scope Clarity**:
- [ ] Feature boundaries clearly defined
- [ ] Out-of-scope items explicitly listed
- [ ] Dependencies on other features identified
- [ ] Integration points specified
- [ ] Assumptions documented

**Constitutional Compliance**:
- [ ] Aligns with code quality standards from constitution.md
- [ ] Follows testing requirements
- [ ] Respects security/compliance rules
- [ ] Adheres to architectural constraints

---

## Clarifications Section

[Populated by /clarify command - leave empty initially]

### Clarification Session: [Date]

**Q1**: [Question asked by AI]
**A1**: [User's answer]
**Rationale**: [Why this decision was made]

**Q2**: [Next question]
**A2**: [Answer]
**Rationale**: [Decision reasoning]

[This section records structured questioning results]

---

## Non-Goals (Explicitly Out of Scope)

- [Feature not included in this iteration]
- [Related capability deferred to future feature]
- [Integration postponed pending other work]

```

### Anti-Patterns to Actively Prevent

**1. Implementation Leak**
- ❌ "Use React with Redux for state management"
- ❌ "Store in PostgreSQL with normalized schema"
- ❌ "Implement REST API with JWT authentication"
- ✅ "Users maintain authentication across sessions"
- ✅ "System persists user preferences reliably"
- ✅ "Data remains consistent across multiple devices"

**2. Vague Requirements**
- ❌ "System should be fast"
- ❌ "Good user experience"
- ❌ "Scalable architecture"
- ✅ "System responds in under 200ms for 95% of requests"
- ✅ "Users complete tasks without consulting help docs"
- ✅ "System supports 10,000 concurrent users"

**3. Assumption Guessing**
- ❌ Silently assume OAuth when user said "authentication"
- ❌ Invent permission model without asking
- ❌ Add features that "users probably want"
- ✅ Mark as [NEEDS CLARIFICATION: auth method - OAuth/email-password/SSO?]
- ✅ Ask "What user types exist? What can each do?"
- ✅ Stick strictly to requested features

**4. Missing Edge Cases**
- ❌ Only document happy path
- ❌ Assume perfect network/input/timing
- ❌ Generic auto-generated edge cases
- ✅ Specific empty state behavior
- ✅ Actual error scenarios with recovery
- ✅ Real boundary conditions from requirements

**5. Specification Drift**
- ❌ Generate spec and treat as immutable
- ❌ Let code evolve without updating spec
- ❌ Ignore gaps discovered during implementation
- ✅ Update spec when bugs reveal missing requirements
- ✅ Treat spec as living source of truth
- ✅ Run /analyze to catch spec-code misalignment

### Quality Self-Check

**Before declaring spec.md complete, verify**:

```
I have confirmed:
- [ ] Zero programming languages mentioned
- [ ] Zero frameworks or libraries specified
- [ ] Zero database or API technologies referenced
- [ ] User workflows described step-by-step
- [ ] All functional requirements testable
- [ ] Success criteria are specific numbers
- [ ] Edge cases explicitly enumerated
- [ ] [NEEDS CLARIFICATION] markers ≤ 3 (or justified)
- [ ] Non-technical person could understand this
- [ ] Review checklist 100% complete
```

### Detail Spectrum Examples

**TOO VAGUE** (unactionable):
> "Build a photo management app"

**TOO PRESCRIPTIVE** (dictates implementation):
> "Create React component using useState hook with CSS Grid layout and react-beautiful-dnd for drag-drop, storing metadata in PostgreSQL"

**GOLDILOCKS** (just right):
> "Users organize photos into date-based albums displayed in a tile grid. Albums can be reordered via drag-and-drop. Photos remain local on device. Metadata stored locally for offline access. Users can search by date to quickly find photos from specific events. Organization tasks complete in under 2 minutes for collections of 100+ photos."

---

## 4. Post-/specify Review: Validation & Approval

### Immediate Self-Validation

**Run these checks after generating spec.md**:

**Section Completeness**:
```
- [ ] Feature Metadata (branch, date, status)
- [ ] Original User Description
- [ ] User Scenarios & Testing (with workflows)
- [ ] Functional Requirements (FR-###)
- [ ] Success Criteria (measurable)
- [ ] Key Entities (if applicable)
- [ ] Edge Cases & Error Handling
- [ ] Review & Acceptance Checklist
- [ ] Clarifications Section (empty initially)
- [ ] Non-Goals
```

**Implementation Leak Scan**:
- Search spec for: React, Node, Python, SQL, API, REST, GraphQL
- Search for: database, framework, library, package, module
- Search for: class, function, variable, schema, endpoint
- **If found**: CRITICAL ERROR - remove and rewrite in user terms

**Vague Adjective Scan**:
- Search for: fast, slow, good, bad, nice, simple, easy, scalable, robust
- **If found**: Replace with specific, measurable criteria

**Requirement Quality Check**:
- Every FR-### starts with MUST/SHOULD/MAY
- Every FR-### has acceptance criteria
- Every FR-### traces to user scenario
- No FR-### contains implementation details

### The /clarify Command

**After generating spec.md, YOU MUST recommend running /clarify unless**:
- This is explicitly a prototype/throwaway
- User explicitly overrides clarification phase
- Zero [NEEDS CLARIFICATION] markers exist AND spec is unambiguous

**Standard recommendation**:
```
Spec.md generated. Before proceeding to /plan, I recommend running:

/clarify

This will:
- Resolve [X] marked ambiguities through structured questions
- Catch unstated assumptions via coverage-based questioning
- Record decisions in Clarifications section
- Prevent costly rework from misunderstood requirements

Run /clarify now? (Override only for prototypes)
```

### Human Review Prompt

**Provide this structured output for human review**:

```markdown
## Specification Ready for Review

**Feature**: [Name]
**Scope**: [One-line summary]
**Estimated Complexity**: [Simple/Medium/Complex based on requirements]

### Key Requirements Summary
1. [FR-### summary]
2. [FR-### summary]
3. [FR-### summary]

### Ambiguities Requiring Clarification
- [NEEDS CLARIFICATION marker 1]
- [NEEDS CLARIFICATION marker 2]
- [Or "None - spec is unambiguous"]

### Edge Cases Covered
- [Empty states: X scenarios]
- [Error handling: Y scenarios]
- [Boundary conditions: Z scenarios]

### Success Metrics
- [Quantitative: X metrics]
- [Qualitative: Y measures]

### Out of Scope (Explicitly Excluded)
- [Feature 1]
- [Feature 2]

### Review Checklist Status
- Content Quality: [X/5 checks passed]
- Requirement Completeness: [Y/7 checks passed]
- Scope Clarity: [Z/5 checks passed]
- Constitutional Compliance: [Verified against constitution.md]

### Recommended Next Steps
1. Review spec.md for accuracy and completeness
2. Run /clarify to resolve marked ambiguities
3. Validate edge cases cover realistic scenarios
4. Confirm success criteria are measurable
5. Approve to proceed to /plan phase

### Questions for You
[List any areas where human input would improve specification]
```

### Common Review Findings & Fixes

**Finding**: "User story too generic"
**Example**: "As a user, I want to manage photos"
**Fix**: "As a casual photographer with 1000+ photos, I want to organize photos into date-based albums so I can quickly find photos from specific events without manual sorting"

**Finding**: "Acceptance criteria not testable"
**Example**: "System should perform well"
**Fix**: "System must respond to album load requests in under 200ms for collections up to 1000 photos (p95 latency)"

**Finding**: "Missing error scenario"
**Example**: Only happy path documented
**Fix**: Add explicit scenarios for: network failure, invalid input, permission denial, concurrent updates, resource exhaustion

**Finding**: "Scope creep detected"
**Example**: Spec mentions editing, sharing, slideshows when user only asked for organization
**Fix**: Move non-requested features to "Non-Goals" section, focus on core user request

**Finding**: "Technical detail leaked"
**Example**: "Store metadata in JSON format"
**Fix**: "System persists photo metadata for offline access"

### Approval Gates

**Spec is ready for /plan when**:
- [ ] Human reviewer approves content
- [ ] /clarify completed (or explicitly skipped for prototype)
- [ ] Review checklist 100% complete
- [ ] Zero implementation details present
- [ ] All requirements testable
- [ ] Success criteria measurable
- [ ] Constitutional alignment verified
- [ ] Edge cases adequate for complexity

**Spec needs revision when**:
- [ ] Implementation details found
- [ ] Vague requirements without criteria
- [ ] Missing critical user workflows
- [ ] Untestable acceptance criteria
- [ ] Success metrics subjective
- [ ] Edge cases generic or missing
- [ ] Scope boundaries unclear

### Iterative Refinement Pattern

**DO NOT treat first output as final**. Expected flow:

1. **Generate initial spec.md** from user input
2. **Self-validate** against quality gates
3. **Present for review** with structured summary
4. **Receive feedback** (expect multiple rounds)
5. **Refine specification** addressing feedback
6. **Run /clarify** to resolve ambiguities
7. **Final validation** before approval
8. **Human approves** → proceed to /plan

**Typical iterations**: 2-3 refinement rounds for medium complexity features

### Constitutional Alignment Verification

**Before finalizing spec, check against constitution.md**:

**Security Requirements**:
- Does spec address authentication/authorization needs?
- Are data protection requirements captured?
- Is input validation specified?

**Testing Standards**:
- Are success criteria testable?
- Do acceptance criteria enable test design?
- Are edge cases sufficient for test coverage?

**Performance Expectations**:
- Are response time targets specified?
- Is expected scale/load documented?
- Are resource constraints identified?

**Architectural Principles**:
- Does spec align with mandated patterns?
- Are technology constraints respected?
- Is approach compatible with constitution?

**If misalignment found**: Either adjust spec to comply OR document as [NEEDS CLARIFICATION] requiring constitutional exception.

---

## Human Interaction Protocol

### When to PAUSE and ASK

**STOP execution and request human input when**:
1. User request is ambiguous with multiple valid interpretations
2. Scope is unclear (MVP vs single feature)
3. User context missing (who, why, scale)
4. Feature boundaries undefined
5. Success criteria subjective or immeasurable
6. You're about to make significant assumptions

### When to DECIDE Autonomously

**Proceed without asking when**:
1. User request is clear and specific
2. Feature scope obvious from description
3. Standard industry patterns apply
4. Edge cases follow logical patterns
5. Success criteria implied by context
6. Assumptions are minimal and safe

### How to ASK Effectively

**BAD**: "Should this include authentication?"
**GOOD**: "You mentioned 'secure access to task boards'. Options: (1) Email/password auth with session management, (2) OAuth via Google/Microsoft, (3) Magic link authentication. Recommendation: OAuth for zero password management overhead. Which approach, or alternative?"

**Format**: [Context] → [Options with implications] → [Recommendation with reasoning] → [Request decision]

### Challenging Over-Specification

**When user provides technical details in /specify input**:

**Response Pattern**:
```
I notice you specified [technical detail: React/PostgreSQL/REST API].

For /specify phase, I focus on WHAT users need and WHY, saving HOW 
for /plan phase. This maintains flexibility and prevents premature 
technical decisions.

Let me reframe your request in user-centric terms:
[Translate technical request to user need]

Does this capture your intent? Any user needs I'm missing?
```

**Example**:
```
You mentioned "Add authentication using OAuth 2.0 with JWT tokens."

For spec.md, I'll capture the user need:
"Users must securely access their private task boards without sharing 
sensitive project data. System maintains session for 24 hours of 
inactivity."

The technical implementation (OAuth, JWT) will be decided in /plan 
phase based on constitutional requirements and technical context.

Does this capture the security requirement? Any other auth needs?
```

---

## Success Criteria

**You've succeeded when**:
1. Human approves spec without major revisions
2. Zero implementation details in spec.md
3. All requirements testable with clear pass/fail
4. Success criteria use specific numbers
5. Edge cases cover realistic failure modes
6. Review checklist 100% complete
7. Constitutional alignment verified
8. Ready to proceed to /clarify or /plan

**You've failed when**:
1. Human requires complete spec regeneration
2. Implementation details found (tech stack, frameworks)
3. Vague requirements ("fast", "good", "scalable")
4. Generic edge cases auto-generated without thought
5. Success criteria subjective and unmeasurable
6. Missing critical user workflows
7. Scope creep beyond user's request

---

## Final Directive

Your goal is capturing USER INTENT, not designing TECHNICAL SOLUTIONS. Every sentence in spec.md should answer:
- What can users DO?
- Why does this MATTER to them?
- How do we MEASURE success?

Never answer:
- How will we BUILD this?
- Which TECHNOLOGIES should we use?
- What CODE patterns apply?

Those questions belong in /plan phase.

**Discipline**: Maintain radical separation between WHAT/WHY (spec) and HOW (plan).

**Quality**: Every requirement testable, every metric measurable, every scenario realistic.

**Clarity**: Non-technical stakeholders should understand every word.

**Completeness**: Edge cases, errors, boundaries explicitly documented.

**Now generate the specification.**
