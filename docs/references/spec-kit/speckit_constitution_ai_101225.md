# AI Agent Guide: /constitution Command Execution & Review

## Section 1: Constitution Overview

**Bottom Line**: The constitution is your project's "architectural DNA"—a set of non-negotiable principles that AI agents (including you) reference at EVERY workflow phase to maintain consistency, quality, and alignment.

**Purpose**: Codify organizational wisdom that typically lives in tribal knowledge: testing approaches, architectural patterns, technology constraints, design requirements, compliance mandates, and performance budgets.

**Critical Distinction**: 
- **Constitutional Principles** = The "WHY" and "WHAT MATTERS" (testing philosophy, security requirements, architectural patterns)
- **Coding Standards** = The "HOW IT LOOKS" (bracket placement, naming conventions, tabs vs spaces)

**You enforce constitutional principles. Linters enforce coding standards.**

**Full Reference**: For comprehensive examples, domain-specific patterns, enforcement mechanisms, and governance frameworks, see "GitHub Spec-Kit Constitution: Comprehensive Guide to AI-Governed Project Development and Architectural Governance.md"

**Your Role**: You will reference the constitution during `/specify`, `/plan`, `/tasks`, and before `/implement`. The `/analyze` command validates constitutional compliance and blocks implementation if CRITICAL violations exist.

---

## Section 2: Pre-/constitution Focus

### Pre-Flight Assessment (MANDATORY)

**Before generating constitution, assess**:

1. **Project Type Identification**
   - [ ] Greenfield new project
   - [ ] Existing codebase needing governance
   - [ ] Multi-project organization seeking consistency
   - [ ] Team with tribal knowledge needing documentation

2. **Pain Point Discovery**
   - Ask: "What development problems cause the most rework?"
   - Ask: "What architectural decisions are most contentious?"
   - Ask: "What quality issues appear repeatedly in postmortems?"
   - Ask: "What standards do new team members struggle to learn?"

3. **Scope Determination**
   - [ ] Single project constitution
   - [ ] Team-wide standards
   - [ ] Organization-level governance
   - [ ] Domain-specific constraints (web app, API, CLI, mobile)

4. **Constraint Gathering**
   - Mandatory technologies (company stack)
   - Compliance requirements (GDPR, HIPAA, SOC2)
   - Performance budgets (response times, resource limits)
   - Security standards (authentication, encryption)
   - Existing architectural patterns to maintain

5. **Stakeholder Input**
   - Tech lead priorities
   - Security team requirements
   - Product team constraints
   - Team consensus on negotiables vs non-negotiables

**Output Required**: Documented answers to use as constitutional input

### What You Need From Human

**Essential Information**:
- Project domain (web app, API, CLI, mobile, microservices)
- 3-5 biggest pain points causing rework/incidents
- Technology stack constraints (mandated or prohibited)
- Security/compliance requirements
- Testing philosophy (coverage targets, TDD mandate)
- Performance expectations (quantified)
- Team size and expertise level

**Ask Explicitly**:
```
Before creating constitution, I need:

1. **Top 3-5 Development Pain Points**: What causes most rework/bugs?
2. **Technology Constraints**: Any mandated or prohibited frameworks/tools?
3. **Security Requirements**: Authentication, encryption, compliance needs?
4. **Testing Standards**: Coverage targets? TDD required? Test types?
5. **Performance Budgets**: Response times? Resource limits? Scale expectations?
6. **Non-Negotiables**: What principles cannot be bent under any circumstances?

This focuses the constitution on solving real problems vs generic guidelines.
```

### Starting Point Strategy

**For Greenfield Projects**:
- Start with 3-5 core principles
- Focus on highest-impact, most enforceable rules
- Target 1 page maximum initially
- Expand iteratively based on needs

**For Existing Codebases**:
- Extract patterns from current code
- Document decisions already being made
- Identify inconsistencies to standardize
- Capture implicit tribal knowledge

**For Organizations**:
- Three-tier architecture:
  - Tier 1: Organizational (security, compliance, legal)
  - Tier 2: Domain/Team (tech choices within guardrails)
  - Tier 3: Project-Specific (tool choices, workflows)

---

## Section 3: /constitution Command Execution

### Core Principle: Specific, Measurable, Enforceable

**Every constitutional principle must be**:
- **Specific**: "Functions >50 lines require justification" NOT "code should be maintainable"
- **Measurable**: "p95 response <200ms" NOT "should be performant"
- **Enforceable**: "CI blocks merge if coverage <80%" NOT "maintain good coverage"
- **Contextual**: Include exceptions/rationale for bending rules

### Mandatory Constitution Structure

```markdown
# Project Constitution v1.0

**Last Updated**: [YYYY-MM-DD]
**Governance**: [Amendment process - e.g., "2/3 team consensus"]

## Preamble

This constitution defines non-negotiable principles for [Project Name]. 
All specifications, plans, and implementations must comply.

## Article I: Code Quality Standards

**Principle**: [High-level value - "Code must be readable, maintainable, tested"]

**Requirements**:
- [Specific rule - "Maximum cyclomatic complexity: 10 per function"]
- [Specific rule - "Code review required: 1+ approval for changes"]
- [Specific rule - "Documentation required for all public APIs"]
- [Specific rule - "Linting enforced in CI pipeline"]

**Verification**: [How enforced - "Automated in CI via SonarQube"]

## Article II: Testing Requirements (NON-NEGOTIABLE)

**Principle**: [Testing philosophy]

**Requirements**:
- [Coverage target - "80%+ line coverage for new code"]
- [Test types - "Integration tests for all API endpoints"]
- [Test types - "E2E tests for critical user journeys"]
- [Quality gate - "Tests must pass before merge"]

**Verification**: [Enforcement - "Coverage gate in CI, blocks <80%"]

## Article III: Security Standards (NON-NEGOTIABLE)

**Principle**: [Security philosophy - "Security by default"]

**Requirements**:
- [Auth requirement - "Authentication required on all endpoints except explicit public"]
- [Secrets management - "No secrets in code, use environment variables"]
- [Scanning - "Dependency scanning enabled, critical CVEs <24hr patch"]
- [Input validation - "All user inputs validated against schemas"]

**Verification**: [Enforcement - "Security scan in CI, Snyk/Dependabot"]

## Article IV: Performance Requirements

**Principle**: [Performance philosophy]

**Requirements**:
- [Specific metric - "API p95 latency <200ms"]
- [Specific metric - "Frontend Lighthouse score >90"]
- [Optimization - "Database queries must use indexes"]
- [Testing - "Performance tests for critical paths"]

**Verification**: [Enforcement - "Performance testing in CI"]

## Article V: Architectural Standards

**Principle**: [Architecture philosophy - "Modular, loosely coupled"]

**Requirements**:
- [Pattern - "Clear service boundaries, no God objects"]
- [Dependencies - "Dependency injection for testability"]
- [Communication - "No circular dependencies"]
- [Documentation - "ADRs for significant architectural decisions"]

**Technology Stack**:
- Language: [Specific version - "Python 3.11"]
- Framework: [Specific version - "FastAPI 0.104"]
- Database: [Specific version - "PostgreSQL 15"]
- Testing: [Specific framework - "pytest 7.4"]

**Prohibited**:
- [What NOT to use - "MongoDB (use PostgreSQL), Moment.js (use date-fns)"]

## Governance

**Amendment Process**:
1. Propose via RFC (2-week discussion period)
2. Require [approval threshold - "2/3 majority"]
3. Update constitution.md + templates
4. Grace period: [timeline - "2 sprints for adoption"]

**Exceptions**:
- Require [approval - "2+ approvals: engineer + tech lead"]
- Must document justification
- Time-bound with sunset date
- Tracked in exceptions.md

**Compliance**:
- /analyze validates before implementation
- Quarterly constitutional health review
- Violations tracked in dashboard
```

### Article Template Pattern

**For each constitutional article, use this structure**:

```markdown
## Article [N]: [Domain Name] [(NON-NEGOTIABLE if applicable)]

**Principle**: [One sentence high-level value statement]

**Requirements**:
1. **[Category]**
   - [Specific, measurable rule with exact thresholds]
   - [Specific, measurable rule with exact thresholds]
   
2. **[Category]**
   - [Specific, measurable rule with exact thresholds]

**Verification**: 
- [How this is enforced - "CI pipeline", "Manual review", "Automated scanning"]
- [What tool/process - "SonarQube quality gate", "Code review checklist"]
```

### Standard Article Types by Domain

**Web Application**:
- Article I: Code Quality (SOLID, complexity limits, review)
- Article II: Testing (coverage, types, quality)
- Article III: Security (auth, encryption, validation)
- Article IV: Performance (response times, bundle sizes, caching)
- Article V: Accessibility (WCAG 2.1 AA, keyboard nav, screen readers)

**API/Backend Service**:
- Article I: Code Quality
- Article II: Testing
- Article III: Security
- Article IV: Performance (latency, throughput, resource limits)
- Article V: Reliability (circuit breakers, retries, observability)

**CLI Tool**:
- Article I: Code Quality
- Article II: Testing
- Article III: Installation (single binary, zero dependencies)
- Article IV: UX Standards (help text, exit codes, progress indicators)
- Article V: Offline Operation (no network requirements for core features)

**Mobile App**:
- Article I: Code Quality
- Article II: Testing
- Article III: Security
- Article IV: Performance (launch time, battery usage, memory)
- Article V: Platform Standards (iOS HIG, Material Design)

### Technology Stack Specification

**Must Specify** (Lock in decisions):
- Primary language with exact version
- Core framework with exact version
- Database technology with version
- API design approach (REST/GraphQL/gRPC)
- Authentication mechanism (OAuth2, JWT, etc.)

**Should Specify** (Document choices):
- Major libraries for core functionality
- Testing frameworks and tools
- Build and deployment tooling
- State management approach
- Package manager

**Can Defer** (Optional, decide later):
- Utility libraries
- CSS frameworks (unless design system mandated)
- Logging libraries
- Development tools

**Format**:
```markdown
**Technology Stack**:
- **Runtime**: [Exact version - "Node.js 20.10 LTS (EOL: 2026-04)"]
- **Language**: [Version + constraints - "TypeScript 5+ (strict mode)"]
- **Framework**: [Version + rationale - "Next.js 14+ (server components, optimization)"]
- **Database**: [Version + use case - "PostgreSQL 15+ (ACID, JSON support)"]
- **Testing**: [Frameworks - "Jest 29+, Playwright for E2E"]

**Rationale**:
- [Why this stack - "TypeScript catches 38% bugs at compile time"]
- [Why this stack - "Next.js: server components reduce bundle 40%"]

**Prohibited**:
- [What NOT to use + reason - "MongoDB: Decision 2024-03-15, consistency with existing systems"]
- [What NOT to use + reason - "Moment.js: Use date-fns (80% smaller bundle)"]

**Version Policy**:
- Node.js: Latest LTS only
- Dependencies: Major versions within 12 months of latest
- Security patches: Apply within 1 week

**Evaluation Criteria for New Technologies**:
1. Active maintenance (commit within 3 months)
2. Production adoption (>1000 stars OR major company using)
3. Security track record (no critical CVEs)
4. License compatibility (MIT, Apache 2.0, BSD)
5. Team expertise OR justified learning investment
```

### Writing Effective Principles

**GOOD Constitutional Principles**:
```markdown
✅ "All API endpoints require authentication except explicitly public routes"
✅ "Code coverage must be ≥80% for new features, enforced via CI gate"
✅ "Database queries must use indexes, validated via EXPLAIN analysis in review"
✅ "p95 API response time <200ms, p99 <500ms, monitored in production"
✅ "Breaking changes to shared libraries require 2-sprint notice + migration guide"
✅ "All PII must be encrypted at rest using AES-256, audited quarterly"
```

**BAD Constitutional Principles** (too generic):
```markdown
❌ "We value quality"
❌ "Code should be maintainable"
❌ "Performance matters"
❌ "Follow best practices"
❌ "Security is important"
❌ "Test your code"
```

**Transform Generic to Specific**:
- "Be secure" → "All endpoints require authentication (OAuth2+JWT), secrets via Vault, TLS 1.3 only"
- "Write tests" → "80%+ coverage, integration tests for APIs, E2E for critical paths, CI blocks <80%"
- "Make it fast" → "p95 <200ms API, p99 <500ms, Lighthouse >90 frontend, database queries use indexes"
- "Document code" → "Public APIs require JSDoc with examples, ADRs for arch decisions, README per module"

### Anti-Patterns to AVOID

**1. Wallpaper Constitution** (generic platitudes):
❌ "Communication is important"
❌ "We value quality"
❌ "Follow best practices"

**Solution**: Every principle must be specific, measurable, enforceable.

**2. Zombie Constitution** (unenforced):
❌ Last updated 18 months ago
❌ No one references it
❌ No measurement/tracking
❌ Not integrated into workflow

**Solution**: Automate enforcement, track metrics, integrate into CI/CD.

**3. Paradox Constitution** (contradictory):
❌ "Move fast and break things" + "Zero defects"
❌ "Autonomous teams" + "Standardized everything"

**Solution**: Resolve conflicts explicitly, define when each applies.

**4. Bureaucratic Constitution** (over-specified):
❌ Dictating exact tools vs capabilities
❌ Covering every edge case
❌ No flexibility for exceptions

**Solution**: Specify outcomes, not implementations. Allow exceptions with justification.

**5. Copy-Paste Constitution** (adopted without customization):
❌ Using Google's standards without Google's scale
❌ Generic templates without project context

**Solution**: Start from YOUR problems, pilot before codifying, iterate based on feedback.

### Quality Gates (Self-Validation)

**Before declaring constitution complete, verify**:

**Specificity Check**:
- [ ] Every principle has measurable criteria (numbers, not adjectives)
- [ ] No vague terms ("fast", "good", "maintainable") without quantification
- [ ] Technology choices include exact versions
- [ ] Performance requirements use concrete metrics

**Enforceability Check**:
- [ ] >50% of principles have automated enforcement (CI/CD)
- [ ] Each principle has documented verification method
- [ ] Non-automatable principles have manual review process
- [ ] Exception process clearly defined

**Completeness Check**:
- [ ] 3-5 core articles minimum (Code Quality, Testing, Security mandatory)
- [ ] Technology stack fully specified
- [ ] Governance section present (amendments, exceptions)
- [ ] NON-NEGOTIABLE markers on critical principles

**Clarity Check**:
- [ ] Non-technical stakeholders can understand principles
- [ ] Each principle has clear business rationale
- [ ] Examples provided for ambiguous rules
- [ ] Consistent terminology throughout

**Practicality Check**:
- [ ] Principles are achievable with current team/resources
- [ ] No contradictory principles
- [ ] Grace periods defined for adoption
- [ ] Exception process doesn't block all work

### Human Interaction Protocol

**When to ASK** (pause execution):
1. Pain points unclear or contradictory
2. Technology constraints have multiple valid approaches
3. Testing philosophy unclear (TDD required? Coverage target?)
4. Security requirements vague ("be secure")
5. Performance targets missing numbers
6. Team consensus needed on non-negotiables

**When to DECIDE** (proceed autonomously):
1. Standard industry practices apply (OAuth2 for auth)
2. Human provided clear quantified requirements
3. Domain best practices obvious (WCAG for accessibility)
4. Technology stack explicitly specified
5. Prior examples/patterns established

**How to ASK effectively**:

**BAD**: "What should the constitution say?"

**GOOD**: 
```
I need clarification on constitutional scope:

1. **Testing Requirements**: 
   - Option A: 80% coverage + TDD mandate + contract-first
   - Option B: 60% coverage + flexible approach
   - Recommendation: Option A for quality, but requires discipline
   
2. **Security Standards**:
   - Option A: OAuth2+JWT with RBAC
   - Option B: Simple API key auth
   - Current spec implies multi-user (suggests Option A)
   
3. **Performance Targets**:
   - Current: "Fast response times" (too vague)
   - Need: Specific numbers (suggest <200ms p95 API, <2s page load)

Confirm recommendations or specify alternatives.
```

**Format**: [Category] → [Options with tradeoffs] → [Recommendation with reasoning] → [Request decision]

---

## Section 4: Post-/constitution Review

### Your Self-Review Checklist

**Run this before declaring constitution complete**:

**Structure Validation**:
- [ ] Preamble states purpose and scope
- [ ] 3-5 core articles present (minimum)
- [ ] Each article has Principle + Requirements + Verification
- [ ] Governance section includes amendments and exceptions
- [ ] Technology stack fully specified with versions
- [ ] NON-NEGOTIABLE markers on critical principles

**Content Quality**:
- [ ] Zero vague principles ("be good", "high quality")
- [ ] Every requirement has measurable criteria
- [ ] Performance metrics include numbers (not "fast")
- [ ] Technology versions specified (not "latest")
- [ ] Prohibited technologies listed with rationale
- [ ] Each principle traces to real problem/pain point

**Enforceability**:
- [ ] >50% principles have automated enforcement path
- [ ] Verification method documented per article
- [ ] CI/CD integration points identified
- [ ] Manual review processes defined
- [ ] Exception handling workflow clear

**Practicality**:
- [ ] No contradictory principles
- [ ] Achievable with current team/resources
- [ ] Grace periods for adoption defined
- [ ] Examples provided for complex principles
- [ ] Business rationale clear for each principle

**Length Appropriateness**:
- [ ] Greenfield: 1-2 pages maximum
- [ ] Mature project: 2-3 pages maximum
- [ ] No unnecessary duplication
- [ ] Focused on high-impact principles

### Provide Human Summary

**After self-review passes, generate this summary**:

```markdown
## Constitution Complete - Ready for Review

**Scope**: [Single project | Team-wide | Organization-level]

**Articles Generated**:
1. **Code Quality**: [Key requirements - complexity <10, reviews required]
2. **Testing** (NON-NEGOTIABLE): [Coverage 80%+, integration tests required]
3. **Security** (NON-NEGOTIABLE): [Auth on all endpoints, secrets via env vars]
4. **Performance**: [p95 <200ms, Lighthouse >90]
5. **Architecture**: [Modular design, no circular deps]

**Technology Stack Locked**:
- Language: [e.g., Python 3.11]
- Framework: [e.g., FastAPI 0.104]
- Database: [e.g., PostgreSQL 15]
- Testing: [e.g., pytest 7.4]

**Enforcement Plan**:
- Automated: [X% of principles - "60% via CI/CD gates"]
- Manual: [Process - "Code review checklist, ADR requirement"]
- Monitoring: [Approach - "SonarQube dashboard, weekly metrics"]

**NON-NEGOTIABLE Principles** (cannot be bent):
1. [Principle from Article with critical marker]
2. [Principle from Article with critical marker]
3. [Principle from Article with critical marker]

**Next Steps**:
1. **Review constitution.md**: Validate principles match team consensus
2. **Verify enforcement**: Confirm CI/CD integration points
3. **Approve for use**: Give explicit approval to proceed
4. **Integration**: Constitution will auto-inject into spec/plan/task templates

**Questions for You**:
[List any decisions requiring human input or clarification]
```

### Common Human Feedback Patterns

**"Too strict/bureaucratic"**:
- **Action**: Reduce principle count to 3-5 most critical
- **Action**: Convert MUST to SHOULD for non-critical items
- **Action**: Add exception process with clear approval path

**"Too vague/generic"**:
- **Action**: Replace adjectives with numbers
- **Action**: Add specific examples to each principle
- **Action**: Convert principles to testable criteria

**"Missing critical area"**:
- **Action**: Add new article addressing gap
- **Action**: Maintain focus (don't bloat unnecessarily)
- **Action**: Prioritize enforceable principles

**"Technology stack too restrictive"**:
- **Action**: Specify capabilities instead of tools
- **Action**: Create evaluation criteria for alternatives
- **Action**: Document rationale for mandated choices

**"Unenforceable principles"**:
- **Action**: Identify automation opportunities
- **Action**: Define manual review process
- **Action**: Remove if truly unverifiable

### Constitution Validation Commands

**After human approval, run these validations**:

1. **Template Integration Test**:
```bash
# Verify constitution propagates to templates
/specify [test feature]
# Check: spec-template.md includes constitutional references
```

2. **Enforcement Verification**:
```bash
# Verify CI integration
git add constitution.md
git commit -m "Add project constitution"
git push
# Check: CI pipeline includes constitutional validation
```

3. **AI Agent Context Test**:
```bash
# Verify AI agents receive constitutional context
/plan [test feature]
# Check: Plan references constitutional principles
# Check: Technical Context section validates against constitution
```

### Iterative Refinement Protocol

**Treat first constitution as v1.0, not final**. Use this cycle:

1. **Generate initial constitution** following template
2. **Self-review** against quality gates
3. **Human reviews** - expect feedback
4. **Refine constitution** addressing concerns
5. **Pilot with willing team** (1-2 sprints)
6. **Measure impact** (violation rates, reference frequency)
7. **Iterate** based on usage data

**Update triggers**:
- Quarterly review cycle (scheduled)
- Postmortem identifies constitutional gap (reactive)
- New compliance requirement (mandate)
- Technology evolution (proactive)
- Team consensus on amendment (democratic)

**Version control**:
```markdown
# Project Constitution v2.1

**Last Updated**: 2025-10-15
**Previous Version**: v2.0 (2025-07-10)

**Changelog**:
- v2.1: Added Article VI: Deployment Standards (incident postmortem)
- v2.0: Updated Article III: Security (GDPR compliance requirement)
- v1.1: Clarified Article II: Testing (added E2E requirement)
- v1.0: Initial constitution (2025-01-15)
```

### Success Criteria

**You've succeeded when**:
1. Human approves constitution without major revisions
2. All quality gates pass
3. Every principle is specific, measurable, enforceable
4. Technology stack fully specified with versions
5. >50% principles have automated enforcement
6. Team consensus on non-negotiables achieved
7. Constitution ready for /specify phase

**You've failed when**:
1. Human requires complete regeneration
2. Vague principles without measurable criteria
3. Contradictory principles exist
4. Technology stack has "NEEDS CLARIFICATION" markers
5. No enforcement mechanisms defined
6. Generic copy-paste without project context

### Post-Approval Actions

**After human approval, execute**:

1. **Save constitution.md**:
```bash
.specify/memory/constitution.md
```

2. **Update project README**:
```markdown
## Project Governance

This project follows constitutional principles defined in `.specify/memory/constitution.md`.

All specifications, plans, and implementations must comply with these non-negotiable standards.
```

3. **Integrate into CI/CD**:
- Add constitutional validation to pipeline
- Configure quality gates (coverage, complexity, security)
- Set up monitoring dashboard

4. **Prepare for /specify**:
- Constitution ready to inject into spec-template.md
- AI agents will reference during specification
- Quality gates ready to validate compliance

5. **Document for team**:
- Share constitution in team workspace
- Add to onboarding materials
- Schedule quarterly review

### Final Directive

**Your goal**: Create a **living governance document** that encodes project wisdom into enforceable principles that AI agents (including you) reference throughout the development lifecycle.

**Key principles**:
- Specific beats generic
- Measurable beats aspirational
- Enforceable beats hopeful
- Practical beats perfect
- Iterative beats comprehensive

**Now generate the constitution.**

---

## Quick Reference Card

**Constitutional Principles Must Be**:
- ✅ Specific: "Complexity <10" NOT "maintainable"
- ✅ Measurable: "p95 <200ms" NOT "fast"
- ✅ Enforceable: "CI blocks <80% coverage" NOT "test well"

**Mandatory Articles** (minimum):
1. Code Quality (SOLID, complexity, reviews)
2. Testing (coverage, types, TDD)
3. Security (auth, encryption, scanning)

**Optional Articles** (add as needed):
4. Performance (latency, resources)
5. Architecture (patterns, dependencies)
6. Domain-specific (accessibility, offline, deployment)

**Anti-Patterns**:
- ❌ "We value quality" (wallpaper)
- ❌ Last updated 18mo ago (zombie)
- ❌ "Move fast" + "Zero bugs" (paradox)
- ❌ Specifies every tool (bureaucracy)
- ❌ Copied from Google (not contextualized)

**Quality Gates**:
- [ ] 3-5 core articles
- [ ] Every principle measurable
- [ ] >50% automated enforcement
- [ ] Tech stack with versions
- [ ] NON-NEGOTIABLE marked
- [ ] 1-3 pages max (greenfield)
- [ ] Zero vague principles

**Success Metrics**:
- Referenced weekly in PRs/decisions
- Updated within last 90 days
- New hires learn Week 1
- >50% automated enforcement
- <10% exception rate
- Improves DORA metrics

**Failure Signals**:
- No one references it
- Generic principles provide no guidance
- Contradictions cause paralysis
- Exceptions exceed 10%
- Complete regeneration required
