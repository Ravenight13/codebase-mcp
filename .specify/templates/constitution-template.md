# [PROJECT_NAME] Constitution

## Project Identity

**Purpose**: [Brief 1-2 sentence description of what this project does and its core value proposition]

**Scope**: [Define clear boundaries - what this project IS and what it is NOT. Be explicit about focus areas.]

## Preamble

This constitution defines the non-negotiable architectural and quality principles for [PROJECT_NAME]. All feature specifications, implementation plans, and code contributions MUST comply with these standards. The `/analyze` command validates compliance before implementation begins. Constitutional violations flagged as CRITICAL block feature progression.

This document serves as the authoritative governance framework for all development decisions. When in doubt, defer to constitutional principles. When principles conflict, follow the priority order defined in the Governance section.

**Version**: 1.0.0 | **Ratified**: [YYYY-MM-DD] | **Last Amended**: [YYYY-MM-DD]

---

## Core Principles

### I. Code Quality Standards

**Principle**: Code must be readable, maintainable, and follow established patterns. Complexity must be justified against measurable user value.

**Requirements**:
1. **Complexity Limits**
   - Maximum cyclomatic complexity: [NUMBER] per function
   - Maximum file length: [NUMBER] lines
   - Maximum function/method length: [NUMBER] lines
   - Functions exceeding limits require documented justification

2. **SOLID Principles Application**
   - Single Responsibility: Classes/modules have one reason to change
   - Open/Closed: Extend behavior without modifying existing code
   - Liskov Substitution: Subtypes substitutable for base types
   - Interface Segregation: Many specific interfaces over one general
   - Dependency Inversion: Depend on abstractions, not concretions

3. **Code Review**
   - All changes require [NUMBER]+ approval(s)
   - Maximum [NUMBER] lines per PR for effective review
   - Reviewers check: correctness, readability, constitutional compliance
   - Review response time: [NUMBER] hours target, [NUMBER] hours maximum

4. **Documentation**
   - All public APIs require documentation with examples
   - Complex algorithms require inline comments explaining "why"
   - README.md for each major module/package
   - Architecture Decision Records (ADRs) for significant choices

**Rationale**: Readable code reduces maintenance costs and onboarding time. SOLID principles enable sustainable growth. Small PRs enable thorough review.

**Verification**:
- Automated: [Linters/tools] enforce complexity limits and style in CI pipeline, code coverage tools validate documentation presence
- Manual: Code review validates SOLID principles, PR size limits enforced by reviewers
- Tooling: [Static analysis tools], complexity metrics tracked in [dashboard/tool]

---

### II. Testing Requirements (NON-NEGOTIABLE)

**Principle**: Comprehensive testing prevents regressions and enables confident refactoring. Tests define correct behavior before implementation.

**Requirements**:
1. **Coverage Standards**
   - Minimum [PERCENTAGE]% line coverage for new code
   - Critical paths require [PERCENTAGE]% coverage
   - PR cannot merge if coverage decreases below threshold
   - Coverage exemptions require explicit justification

2. **Test Types Required**
   - **Unit Tests**: All business logic, edge cases, error conditions
   - **Integration Tests**: All [API endpoints/component interactions/database operations]
   - **End-to-End Tests**: Critical user journeys (happy paths minimum)
   - **Performance Tests**: [Load testing for high-traffic features/benchmarks for critical operations]

3. **Test Quality Standards**
   - Tests must be deterministic (no flaky tests)
   - Use test fixtures/factories, not hard-coded data
   - Tests run in <[NUMBER] minutes locally
   - Test naming: `[should_expectedBehavior_when_condition / test_feature_scenario / describe-it pattern]`

4. **Test Data Management**
   - Test datasets version controlled in [/fixtures / /testdata / tests/data]
   - [Snapshots for UI components / Database seeding scripts / Mock data generators]
   - No production data in tests
   - Sensitive data anonymized/synthetic

**Rationale**: [Test-Driven Development / Early bug detection / Confident refactoring] requires comprehensive testing. Protocol/contract compliance testing prevents integration breakage. Performance tests prevent regression.

**Verification**:
- Automated: [pytest-cov / Jest / coverage.py] enforces [PERCENTAGE]% coverage gate in CI, tests must pass before merge
- Manual: Code review validates tests written before implementation, test scenarios match acceptance criteria
- Tooling: [Test framework], CI pipeline blocks merge on test failures, coverage reports in PR comments

---

### III. Security Standards (NON-NEGOTIABLE)

**Principle**: Security is not optional. Protect user data, system integrity, and maintain trust through defense-in-depth.

**Requirements**:
1. **Authentication & Authorization**
   - All [API endpoints / routes / operations] require authentication (except explicitly public)
   - [OAuth 2.0 + JWT / API keys / Session-based] authentication required
   - [Role-Based Access Control (RBAC) / Attribute-Based Access Control (ABAC)] for all resources
   - Session timeouts: [NUMBER] minutes inactivity, [NUMBER] hours maximum
   - Multi-factor authentication (MFA) for [admin operations / sensitive data access]

2. **Data Protection**
   - All [PII / sensitive data / credentials] encrypted at rest ([AES-256 / encryption standard])
   - [TLS 1.3 / TLS 1.2+] for all network traffic
   - Passwords: [bcrypt with 12+ rounds / Argon2 / scrypt]
   - No credentials in source code (use environment variables or secret management)
   - Secrets management via [HashiCorp Vault / AWS Secrets Manager / Azure Key Vault / environment variables]

3. **Input Validation**
   - Validate all user inputs against schemas
   - Parameterized queries only (no string concatenation for SQL)
   - [Content Security Policy (CSP) headers / CORS policies strictly defined]
   - Rate limiting on [public endpoints / API routes]: [NUMBER] requests per [time period]

4. **Dependency Security**
   - Automated security scanning ([Snyk / Dependabot / OWASP Dependency-Check])
   - **Critical vulnerabilities**: Patch within [NUMBER] hours
   - **High severity**: Patch within [NUMBER] days
   - **Medium/Low severity**: Review and plan remediation within [NUMBER] days
   - No dependencies with known critical CVEs

5. **[OPTIONAL] Compliance Frameworks**
   - [GDPR: Data subject rights, consent management, breach notification]
   - [SOC 2: Access controls, logging, change management]
   - [HIPAA: PHI encryption, audit logs, Business Associate Agreements]
   - [PCI DSS: Cardholder data protection, network security]

**Rationale**: Security breaches destroy user trust and create legal liability. Defense-in-depth prevents single point of failure. Automated scanning catches vulnerabilities before production.

**Verification**:
- Automated: [SAST tools (SonarQube, Checkmarx) / DAST tools / dependency scanning] run in CI, security tests in test suite
- Manual: Security review required for PRs touching auth/data layers, quarterly security audits
- Tooling: [Security scanning tools], vulnerability dashboard, penetration testing [quarterly/annually]

---

### IV. Performance Standards

**Principle**: Performance is a feature. Optimize for user experience and resource efficiency.

**Requirements**:
1. **Response Time Targets**
   - [API endpoints / Backend services]: p95 <[NUMBER]ms, p99 <[NUMBER]ms
   - [Database queries]: p95 <[NUMBER]ms
   - [Page load / Initial render]: p95 <[NUMBER] seconds
   - [Time to Interactive (TTI)]: <[NUMBER] seconds

2. **Optimization Standards**
   - Database: All queries must use indexes (explain plan validation required)
   - [Frontend: Code splitting for routes >[NUMBER]KB / Asset optimization]
   - [Images: Compressed (WebP/AVIF), lazy-loaded, responsive sizing]
   - [API: Response caching with appropriate TTLs (ETag, Cache-Control)]
   - [Static assets served via CDN]

3. **Resource Limits**
   - [Memory: Services <[NUMBER]MB baseline, <[NUMBER]GB under load]
   - [CPU: <[PERCENTAGE]% average utilization]
   - [Database connections: Pooling with max [NUMBER] connections]
   - [Concurrent requests: [NUMBER] per instance]

4. **Monitoring & Observability**
   - [APM tools (Datadog, New Relic, OpenTelemetry)] in production
   - [Performance budgets in CI (Lighthouse, WebPageTest)]
   - Alerts for p95 exceeding thresholds
   - [Real User Monitoring (RUM) for frontend]

**Rationale**: Slow tools break developer/user flow. Quantified targets enable objective measurement. Monitoring enables proactive problem detection.

**Verification**:
- Automated: [Performance tests / benchmark suite] validates targets in CI, load testing before releases
- Manual: Performance review for complex features, profiling during code review
- Tooling: [Benchmarking tool], [monitoring platform], performance regression detection

---

### V. Git Workflow & Version Control (NON-NEGOTIABLE)

**Principle**: Disciplined version control enables collaboration, debugging, and rollback. Clear history tells the story of the codebase.

**Requirements**:
1. **Branching Strategy**
   - `[main/master]`: Production-ready code only
   - `[develop]`: [Integration branch for features - OPTIONAL for trunk-based development]
   - `[feature/[ticket]-[description]]`: Feature development
   - `[hotfix/[ticket]-[description]]`: Urgent production fixes
   - No direct commits to [main/master] (enforced via branch protection)

2. **Commit Strategy**
   - **Format**: [Conventional Commits: `type(scope): description` / Ticket-first: `[TICKET-123] description`]
   - **Types**: [feat, fix, docs, refactor, test, chore, perf]
   - **Frequency**: [Atomic commits after each logical unit / After each completed task]
   - **Quality**: One logical change per commit, tests pass per commit
   - **Messages**:
     - First line: <[NUMBER] characters summary
     - Body: Why (not what), reference ticket/issue

3. **Pull Request Requirements**
   - **Reviews**: [NUMBER]+ approval(s) for most changes
   - **Additional approvals**: [2+ for shared libraries/infrastructure / CODEOWNERS defines required reviewers]
   - **CI Checks Must Pass**:
     - All tests pass
     - Code coverage ≥[PERCENTAGE]%
     - No linting errors
     - [Security scan passes / Performance benchmarks met]
   - **Description Requirements**:
     - Summary of changes
     - Testing performed
     - [Screenshots for UI changes]
     - [Migration notes if breaking changes]
   - **Size Limits**: <[NUMBER] lines preferred for effective review

4. **Versioning**
   - [Semantic versioning (MAJOR.MINOR.PATCH)]
   - [Tag releases: `v[VERSION]` / Git tags for production deployments]
   - [Changelog auto-generated from commit messages / Manual changelog maintained]

**Rationale**: [Trunk-based development / GitFlow / GitHub Flow] enables [continuous integration / release management / parallel development]. Conventional Commits enable automated changelog generation. Branch protection prevents accidental main branch corruption.

**Verification**:
- Automated: [commitlint / pre-commit hooks] validate commit format, branch protection enforced in [GitHub/GitLab], CI runs per commit
- Manual: PR review validates commit atomicity, all checks pass before merge approval
- Tooling: [Git hooks], [semantic-release for versioning], CI/CD pipeline integration

---

### VI. Documentation Standards

**Principle**: Documentation is not an afterthought. Clear documentation reduces onboarding time and prevents tribal knowledge.

**Requirements**:
1. **Code-Level Documentation**
   - All public APIs require [docstrings / JSDoc / XML comments] with:
     - Purpose description
     - Parameter descriptions
     - Return value description
     - Usage examples
     - [Exception/error documentation]
   - Complex algorithms require inline comments explaining "why" (not "what")

2. **Project Documentation**
   - **README.md** must include:
     - Project purpose and scope
     - Installation/setup instructions
     - Configuration options (required vs optional)
     - Usage examples
     - [Contribution guidelines / Development setup]
   - **[ARCHITECTURE.md / docs/architecture/]**: High-level system design
   - **[API.md / OpenAPI/Swagger specs]**: API contracts with examples
   - **[TROUBLESHOOTING.md]**: Common errors and solutions

3. **Decision Documentation**
   - Architecture Decision Records (ADRs) for significant choices in [docs/adr / .adr]
   - ADR template:
     - Context: Why this decision is needed
     - Decision: What was decided
     - Alternatives: What else was considered
     - Consequences: Implications and tradeoffs

4. **[OPTIONAL] User Documentation**
   - [User guides for end-user features]
   - [Tutorials for common workflows]
   - [FAQ for common questions]

**Rationale**: Documentation reduces support burden and enables self-service. ADRs capture the "why" behind decisions. API documentation prevents integration errors.

**Verification**:
- Automated: [Linters check docstring presence / Documentation coverage tools / Link checkers]
- Manual: PR template requires documentation updates, code review validates documentation quality
- Tooling: [Sphinx / JSDoc / Doxygen / MkDocs for generation], documentation deployed to [GitHub Pages / Read the Docs]

---

### VII. Architectural Standards

**Principle**: [Modular, loosely coupled, highly cohesive systems / Clean Architecture / Domain-Driven Design] enables sustainable growth.

**Requirements**:
1. **Architecture Pattern**
   - [Microservices: Each service has single responsibility]
   - [Layered Architecture: Presentation → Business Logic → Data Access]
   - [Event-Driven: Services communicate via events/message queues]
   - [Modular Monolith: Clear module boundaries with enforced dependencies]
   - Communication: [REST APIs / GraphQL / gRPC / Message queues]

2. **Design Patterns** (Preferred)
   - [Repository Pattern for data access]
   - [Factory Pattern for object creation]
   - [Strategy Pattern for algorithmic variation]
   - [Observer Pattern for event handling]
   - [Decorator Pattern for functionality extension]

3. **Anti-Patterns to Avoid**
   - God Objects (classes doing too much)
   - Tight Coupling (hard dependencies between modules)
   - Circular Dependencies
   - Spaghetti Code (tangled control flow)
   - [Golden Hammer (same solution for all problems)]

4. **Dependency Management**
   - Dependency inversion: Depend on abstractions, not concretions
   - No circular dependencies (detected via [tooling])
   - Shared code: [Published packages / Shared libraries], not copy-paste
   - [Dependency injection for testability]

5. **Data Architecture**
   - [Database per service pattern / Shared database with clear ownership]
   - [Event sourcing for audit trails / Change data capture]
   - [CQRS for complex read/write patterns - OPTIONAL]
   - Schema migrations version controlled ([Flyway / Liquibase / Alembic / Prisma])

**Rationale**: [Architectural pattern] prevents [specific problems]. Design patterns provide proven solutions. Anti-pattern awareness prevents common pitfalls.

**Verification**:
- Automated: [Dependency graph analysis / Architecture tests / Import linters]
- Manual: Architecture review for new services/modules, ADRs for significant architectural changes
- Tooling: [Dependency analyzers], quarterly architecture review meetings

---

### VIII. Error Handling & Observability

**Principle**: Systems fail gracefully. Comprehensive error handling and observability enable rapid problem diagnosis and resolution.

**Requirements**:
1. **Error Handling Standards**
   - All exceptions must be caught and logged with context
   - Structured error responses: [status code, error message, details, correlation ID]
   - User-facing errors must be actionable (what went wrong, suggested action)
   - Never expose internal details (stack traces, database errors) to users
   - Error boundaries for [frontend components / service boundaries]

2. **Logging Requirements**
   - **Structured logging**: [JSON format / Key-value pairs]
   - **Log levels**:
     - ERROR: Actionable problems requiring immediate attention
     - WARN: Potentially problematic situations worth monitoring
     - INFO: Significant events (audit trail, state changes)
     - DEBUG: Detailed diagnostic information (development only)
   - **Required fields**: timestamp, level, message, [correlation ID, service name, user ID (if applicable)]
   - [Logs to file/stdout, NEVER to stderr for protocol messages]

3. **Monitoring & Alerting**
   - **Three Pillars of Observability**:
     - **Logs**: Event records with context
     - **Metrics**: Numeric values tracked over time (latency, throughput, error rates)
     - **Traces**: Request flow across services (distributed tracing)
   - [APM tools: Datadog, New Relic, OpenTelemetry]
   - Alerts for:
     - Error rate exceeds [PERCENTAGE]%
     - p95 latency exceeds [NUMBER]ms
     - [Resource utilization exceeds [PERCENTAGE]%]

4. **Resilience Patterns**
   - [Circuit breakers on external dependencies]
   - [Retry logic with exponential backoff]
   - [Graceful degradation for non-critical features]
   - [Timeout configuration for all network calls]

**Rationale**: Graceful failures maintain user trust. Structured logging enables debugging. Observability enables proactive problem detection. Resilience patterns prevent cascading failures.

**Verification**:
- Automated: [Linters validate error handling patterns / Log format validation / Health check endpoints]
- Manual: Code review validates error messages and logging context
- Tooling: [Logging framework], [monitoring platform], [distributed tracing tool]

---

### IX. [OPTIONAL] Accessibility Standards

**When to Apply**: For user-facing applications with web/mobile interfaces, especially public-facing products or those requiring regulatory compliance (government, education, healthcare).

**Principle**: Accessible software serves all users, regardless of ability. Accessibility is a quality attribute, not a feature.

**Requirements**:
1. **WCAG Compliance**
   - [WCAG 2.1 / WCAG 2.2] Level [AA / AAA] compliance required
   - All interactive elements keyboard accessible (no mouse-only operations)
   - Screen reader compatible (proper semantic HTML, ARIA labels)
   - Color contrast ratios: [4.5:1 for normal text, 3:1 for large text]

2. **Testing Requirements**
   - Automated accessibility testing in CI ([axe-core / Pa11y / Lighthouse accessibility score])
   - Manual testing with screen readers ([NVDA / JAWS / VoiceOver])
   - Keyboard-only navigation testing

**Rationale**: Accessibility expands user base and prevents legal liability. Many accessibility improvements benefit all users (keyboard navigation, clear labels).

**Verification**:
- Automated: [Accessibility linters] in CI, Lighthouse accessibility score ≥[NUMBER]
- Manual: Quarterly accessibility audits, user testing with assistive technologies

---

### X. [OPTIONAL] Performance Budgets (Frontend)

**When to Apply**: For web applications, mobile apps, or any user-facing frontend with performance-sensitive interfaces.

**Principle**: Performance is a feature. Budget constraints prevent performance regression.

**Requirements**:
1. **Asset Size Budgets**
   - JavaScript bundles: <[NUMBER]KB per route
   - CSS: <[NUMBER]KB total
   - Images: Optimized ([WebP/AVIF]), lazy-loaded, max [NUMBER]KB per image
   - Fonts: [Web fonts subset, max [NUMBER] font families]

2. **Lighthouse Scores** (Minimum)
   - Performance: ≥[NUMBER (e.g., 90)]
   - Accessibility: ≥[NUMBER (e.g., 90)]
   - Best Practices: ≥[NUMBER (e.g., 90)]
   - SEO: ≥[NUMBER (e.g., 90)]

3. **Core Web Vitals**
   - Largest Contentful Paint (LCP): <[NUMBER (e.g., 2.5)]s
   - First Input Delay (FID): <[NUMBER (e.g., 100)]ms
   - Cumulative Layout Shift (CLS): <[NUMBER (e.g., 0.1)]

**Rationale**: Performance budgets prevent regression. Quantified targets enable objective measurement.

**Verification**:
- Automated: Lighthouse CI in pipeline, bundle size tracking, Core Web Vitals monitoring
- Manual: Performance review for frontend changes

---

### XI. [OPTIONAL] Deployment & Release Standards

**When to Apply**: For production systems requiring controlled releases, rollback capabilities, or multi-environment deployments.

**Principle**: Deployments should be safe, repeatable, and reversible. Release automation reduces human error.

**Requirements**:
1. **Environment Strategy**
   - [Development → Staging → Production pipeline]
   - [Feature flags for gradual rollouts]
   - [Blue-green / Canary deployment for zero-downtime]

2. **CI/CD Pipeline**
   - **Pre-merge**: Linting, tests, security scans, coverage reports
   - **Post-merge**: Build artifacts, deploy to staging, smoke tests
   - **Production**: Manual approval required, [blue-green deployment / rolling updates]

3. **Rollback Procedures**
   - Automated rollback on errors ([health check failures / error rate spike])
   - Rollback SLA: <[NUMBER] minutes to previous version
   - Database migrations must be reversible

4. **Release Process**
   - [Semantic versioning for releases]
   - [Changelog auto-generated / manually maintained]
   - [Release notes for major/minor versions]
   - [Post-deployment verification / smoke tests]

**Rationale**: Automated deployments reduce human error. Rollback capabilities enable safe experimentation. Multi-environment testing catches issues before production.

**Verification**:
- Automated: CI/CD pipeline enforces gates, health checks validate deployments
- Manual: Release approval process, post-deployment verification

---

## Technical Constraints

### Required Technology Stack

**[Lock in core technologies with versions and rationale]**

- **Runtime/Language**: [Technology] [VERSION]+ (Rationale: [why this choice])
- **Framework**: [Technology] [VERSION]+ (Rationale: [why this choice])
- **Database**: [Technology] [VERSION]+ (Rationale: [why this choice])
- **[Additional Core Tech]**: [Technology] [VERSION]+ (Rationale: [why this choice])

### Prohibited Technologies

**[Explicitly document what NOT to use and why]**

- **[Technology Name]**: Decision date [YYYY-MM-DD], Reason: [why prohibited]
- **[Technology Name]**: Decision date [YYYY-MM-DD], Reason: [why prohibited]

### Version Compatibility Policy

- [Runtime/Language]: [Version policy - e.g., "Latest LTS only", "Within 2 major versions"]
- Dependencies: [Policy - e.g., "Major versions within 12 months of latest"]
- Security patches: Apply within [NUMBER] [hours/days] of release
- Breaking changes: [Migration plan required / Grace period of [NUMBER] sprints]

### Evaluation Criteria for New Technologies

Before adopting new technology, validate:
1. **Maintenance**: Active development (commit within [NUMBER] months)
2. **Adoption**: [Maturity signal - e.g., ">1000 GitHub stars OR major company using"]
3. **Security**: No critical CVEs, responsible disclosure process
4. **License**: Compatible license ([MIT, Apache 2.0, BSD, etc.])
5. **Team Fit**: Team expertise OR justified learning investment

**Exception Process**: Propose via ADR → [Approval requirements] → Pilot in non-critical feature → Document evaluation

---

## Enforcement Matrix

This matrix documents which constitutional principles have automated enforcement and which require manual validation. **Target: >50% automation coverage.**

| Principle | Enforcement Type | Tool/Process | CI Stage |
|-----------|------------------|--------------|----------|
| I. Code Quality | [Automated/Manual/Mixed] | [Linters, complexity tools, review] | [Pre-commit, CI] |
| II. Testing | Automated | [Test framework, coverage tool] | CI |
| III. Security | Automated | [Security scanners, dependency check] | Pre-commit, CI |
| IV. Performance | [Automated/Mixed] | [Benchmark tools, load tests] | CI |
| V. Git Workflow | Automated | [Commitlint, branch protection] | Pre-push, CI |
| VI. Documentation | Mixed | [Doc linters, review checklist] | CI, manual review |
| VII. Architecture | Manual | [Architecture review, dep analysis] | Planning, quarterly |
| VIII. Error Handling & Observability | Mixed | [Log validation, monitoring setup] | CI, runtime |
| [IX. Accessibility] | [Automated if applicable] | [Accessibility linters] | [CI] |
| [X. Performance Budgets] | [Automated if applicable] | [Lighthouse CI, bundle analysis] | [CI] |
| [XI. Deployment] | [Automated if applicable] | [CI/CD pipeline, health checks] | [Deployment] |

**Automation Coverage**: [X]/[Y] ([PERCENTAGE]%) - [meets/exceeds/below] >50% threshold

**Notes**:
- **Automated**: Enforcement via CI/CD pipelines, pre-commit hooks, or runtime validation
- **Manual**: Human review required (spec validation, architecture review)
- **Mixed**: Combination of automated metrics + human judgment

---

## Success Criteria

This project is production-ready when:

1. ✅ [Specific measurable criterion - e.g., "Indexes 10k LOC in <60s"]
2. ✅ [Specific measurable criterion - e.g., "Search returns in <500ms (p95)"]
3. ✅ [Specific measurable criterion - e.g., "All tests pass with 80%+ coverage"]
4. ✅ [Specific measurable criterion - e.g., "Zero critical security vulnerabilities"]
5. ✅ [Specific measurable criterion - e.g., "All mypy --strict checks pass"]
6. ✅ [Specific measurable criterion - e.g., "Documentation complete for all public APIs"]
7. ✅ [Specific measurable criterion - e.g., "CI/CD pipeline fully automated"]
8. ✅ [Specific measurable criterion - e.g., "Performance targets met under load"]

---

## Non-Goals

Explicitly OUT OF SCOPE to prevent feature creep:

- [Feature category that's explicitly excluded - e.g., "Generic knowledge base functionality"]
- [Feature category that's explicitly excluded - e.g., "Real-time collaboration features"]
- [Feature category that's explicitly excluded - e.g., "Mobile app development"]
- [Technology/approach that's explicitly excluded - e.g., "Cloud-based SaaS deployment"]

**Rationale**: Scope creep prevention requires explicit boundaries. These features belong in other tools or violate core principles.

---

## Development Workflow

### Specification Phase (`/specify`)

- Create feature specifications focusing on user requirements (WHAT/WHY)
- Define acceptance criteria and test scenarios
- Mark ambiguities with `[NEEDS CLARIFICATION: question]`
- Avoid implementation details (HOW)

### Clarification Phase (`/clarify`)

- Interactive Q&A to resolve ambiguities in spec
- Maximum 5 targeted questions per iteration
- Answers encoded back into spec.md
- Run before `/plan` to ensure clarity

### Planning Phase (`/plan`)

- Generate implementation plan from specification
- Research technical approaches
- Design data models and API contracts
- Validate against constitutional principles (Phases 0 and 1)

### Task Generation (`/tasks`)

- Generate TDD-ordered task breakdown from plan
- Mark independent tasks with `[P]` for parallel execution
- Ensure test tasks precede implementation tasks

### Analysis Phase (`/analyze`)

- Cross-artifact consistency validation (spec → plan → tasks)
- Constitutional compliance check
- CRITICAL violations block implementation
- Must resolve all CRITICAL issues before `/implement`

### Implementation Phase (`/implement`)

- Execute tasks sequentially by phase
- [Use orchestrated subagents for parallel tasks - if applicable]
- Commit after each completed task: `[type(scope): description]`
- Each commit must pass tests (working state requirement)
- Mark completed tasks as `[X]` in tasks.md

---

## Governance

### Amendment Process

Constitution changes require:
1. **Version increment** following semantic versioning:
   - **MAJOR**: Scope change, principle removal, architectural pivot
   - **MINOR**: New principle added, expanded quality standards
   - **PATCH**: Clarifications, wording improvements, non-semantic refinements
2. **Sync Impact Report** documenting:
   - Version change (old → new)
   - Principles added/modified/removed
   - Sections added/modified/removed
   - Templates requiring updates
   - Follow-up TODOs
3. **Validation**: Changes don't violate core principles
4. **Documentation**: Update with clear rationale and date

### Principle Priority

In conflicts, principles are prioritized as follows (highest to lowest):

1. **[Principle Name from your NON-NEGOTIABLE principles]** ([why it's highest priority])
2. **[Next principle]** ([why it's next])
3. **[Next principle]** ([why it's next])
4. [Continue numbering based on your project priorities]

### Complexity Justification

When implementation requires complexity:
- Document the tradeoff explicitly in ADR
- Explain why simpler alternatives are insufficient
- Ensure complexity serves a constitutional principle
- Get approval before implementation begins
- Track complexity debt with sunset dates for simplification

### Exception Handling Process

When a constitutional principle cannot be met, an exception may be requested:

**Request Process**:
1. Create [GitHub issue / Jira ticket / documentation entry] with label `constitution-exception`
2. Document specific principle(s) requiring exception
3. Provide detailed justification:
   - Why the principle cannot be met
   - What alternatives were considered
   - Quantified impact analysis
   - Proposed mitigation strategy
4. Specify time-bound duration (temporary) or permanent exception

**Approval Requirements**:
- **Temporary Exceptions** (<[NUMBER] days): [Role - e.g., "Project maintainer"] approval + documented in `exceptions.md`
- **Extended Exceptions** ([NUMBER]-[NUMBER] days): [NUMBER] approvals ([roles - e.g., "maintainer + technical reviewer"])
- **Permanent Exceptions**: Constitution amendment required (MAJOR version bump)

**Tracking**:
- All exceptions logged in `.specify/memory/exceptions.md` with:
  - Exception ID
  - Principle affected
  - Justification summary
  - Approval date and approvers
  - Sunset date (for temporary exceptions)
  - Resolution status

**Grace Periods**:
- New principles have [NUMBER]-day grace period for existing code
- Breaking changes require migration plan before enforcement
- [Performance targets / New tool adoption] enforceable only after [tooling setup / training] complete

### Compliance Tracking

Constitutional compliance is monitored through:

**Automated Monitoring**:
- CI/CD pipeline runs enforcement checks (see Enforcement Matrix)
- Pre-commit hooks block common violations
- `/analyze` command validates specifications against principles

**Manual Review**:
- [Quarterly/Monthly] constitution audit reviewing:
  - Active exceptions (review sunset dates)
  - Principle violation trends
  - Enforcement effectiveness
  - Potential principle updates
- Spec review process validates feature requests against scope
- Implementation review validates [code quality / orchestration / architectural alignment]

**Violation Response**:
1. **CRITICAL violations**: Block merge, require fix before proceeding
2. **WARNING violations**: Document in PR, require justification or fix
3. **INFO violations**: Advisory only, tracked for trends

**Metrics**:
- Track exception request rate (target: <[PERCENTAGE]% of PRs)
- Track CRITICAL violation block rate
- Track automation coverage percentage (maintain >[PERCENTAGE]%)
- Track time-to-resolution for violations

---

## Usage Notes for AI Agents

### When Creating Project-Specific Constitutions

1. **Replace all placeholders** in `[BRACKETS]` with project-specific values
2. **Remove OPTIONAL sections** that don't apply to your project
3. **Customize enforcement** tools/processes to match your tech stack
4. **Quantify everything**: Replace vague terms with numbers
5. **Justify choices**: Add rationale for non-obvious decisions
6. **Validate completeness**: Ensure all placeholders are filled

### Placeholder Guide

- `[PROJECT_NAME]`: Your project's name
- `[NUMBER]`: Quantified threshold (e.g., 80, 200, 500)
- `[PERCENTAGE]`: Coverage/utilization target (e.g., 80%, 90%)
- `[YYYY-MM-DD]`: Specific dates for tracking
- `[TECHNOLOGY]`: Specific tool/framework/language name
- `[VERSION]`: Specific version number or constraint
- `[Tool/Framework]`: Specific tool names based on your stack
- `[Role]`: Approval role (e.g., "Tech Lead", "Security Lead")

### Customization Priorities

1. **MUST customize**: Technology Stack, Success Criteria, Non-Goals
2. **SHOULD customize**: Testing percentages, Performance targets, Review requirements
3. **CAN customize**: Principle wording (keep structure), Documentation format

### Quality Checklist

Before finalizing, verify:
- [ ] Zero placeholders remain (search for `[` and `]`)
- [ ] All NON-NEGOTIABLE principles identified
- [ ] Enforcement Matrix shows >50% automation
- [ ] Technology stack fully specified with versions
- [ ] Success Criteria are measurable
- [ ] Non-Goals prevent scope creep
- [ ] Principle priorities ordered
- [ ] Version and dates filled in

---

## Technology Domain Addenda

This section contains technology-specific optional principles that apply conditionally based on your project's technology stack. These principles complement the core constitution with domain-specific best practices, enforcement mechanisms, and measurable standards.

### How to Use This Addenda

1. **Review Applicability**: Read the "Applies When" criteria for each principle
2. **Adopt Selectively**: Copy relevant sections into your project constitution
3. **Customize Values**: Replace placeholders with project-specific thresholds
4. **Enforce Consistently**: Integrate verification mechanisms into your CI/CD pipeline
5. **Track Adoption**: Document which principles you've adopted in your constitution version history

**Note**: These principles are research-informed (2024-2025 best practices) and production-tested. Choose based on your technology stack, not what seems interesting.

---

### Type Safety & Validation

#### [OPTIONAL] Type Safety Standards (Static + Runtime)

**Priority**: RECOMMENDED
**Applies When**: IF project uses Python 3.8+ OR TypeScript 4+ OR other statically-typed languages

**Example Conditions:**
- IF project uses **Python with type hints** THEN enforce `mypy --strict`
- IF project uses **Pydantic** THEN enforce `BaseModel` inheritance for all DTOs
- IF project uses **TypeScript** THEN enforce `strict: true` in tsconfig.json
- IF project uses **validation libraries** (Pydantic, Zod, Joi) THEN validate at system boundaries

**Principle Description:**

Type safety prevents entire classes of bugs before runtime. Static type checking (mypy, TypeScript compiler) catches type mismatches during development. Runtime validation (Pydantic, Zod) prevents invalid data from propagating through the system. Combined, they provide defense-in-depth against type-related errors.

**Requirements:**

1. **Static Type Checking**
   - Python: `mypy --strict` with zero type errors blocking CI
   - TypeScript: `"strict": true, "noImplicitAny": true` in tsconfig.json
   - Gradual adoption: Start with `--disallow-untyped-defs` for new code
   - Configuration: Commit mypy.ini or tsconfig.json to version control

2. **Runtime Validation**
   - Python: All data models inherit from `pydantic.BaseModel`
   - Python: Configuration uses `pydantic_settings.BaseSettings`
   - TypeScript: API boundaries validated with Zod or Joi schemas
   - Validation errors caught at system boundaries with field-level messages

3. **Enforcement Standards**
   - Type hints required for all public functions/methods
   - Generic types fully specified (no bare `List`, use `List[str]`)
   - `Any` type prohibited except with documented justification
   - Third-party libraries: Use type stubs (typeshed) or create custom stubs

**Enforcement Mechanisms:**

- **Verification - Automated**:
  - CI pipeline runs `mypy --strict` or `tsc --noEmit`
  - Pre-commit hooks block commits with type errors
  - Pydantic validators execute at model instantiation
  - Type coverage tools ensure >95% of codebase has type annotations

- **Verification - Manual**:
  - Code review validates `BaseModel` inheritance for DTOs
  - Review checks for `# type: ignore` comments (require justification)

- **Tooling**:
  - mypy with strict mode, Pydantic v2, TypeScript strict compiler, Ruff/Pylint

**Why This Matters:**

Research shows mypy catches 38% of bugs at compile time. Runtime validation with Pydantic prevents invalid data from causing downstream errors. Combined enforcement creates a "pit of success" where type errors are caught before production.

**Anti-Patterns:**
- Using `Any` type liberally (defeats purpose)
- Silencing type errors with `# type: ignore` without justification
- Skipping validation at API/database boundaries

---

#### [OPTIONAL] Schema Validation Standards

**Priority**: RECOMMENDED
**Applies When**: IF project uses JSON Schema OR database schemas OR API contracts

**Example Conditions:**
- IF project uses **PostgreSQL JSONB** THEN enforce JSON Schema validation
- IF project uses **API contracts** THEN maintain OpenAPI/GraphQL schemas
- IF project uses **message queues** THEN validate message schemas

**Principle Description:**

Schema validation ensures data integrity across system boundaries. JSON Schema provides runtime validation for flexible JSON storage. API schemas (OpenAPI, GraphQL) enable contract testing and prevent integration breakage.

**Requirements:**

1. **Schema Definition**
   - All JSONB columns have associated JSON Schema (Draft 7+)
   - API contracts maintained as OpenAPI 3.0+ or GraphQL SDL
   - Schemas version-controlled alongside code

2. **Schema Evolution Governance**
   - Backward compatibility validation for schema changes
   - Expand → Migrate → Contract pattern for migrations
   - Version tracking: Schema version field in all documents

**Enforcement Mechanisms:**

- **Verification - Automated**: JSON Schema validators, OpenAPI validators, schema diff tools
- **Verification - Manual**: Schema review for backward compatibility
- **Tooling**: jsonschema library, ajv, Confluent Schema Registry

**Why This Matters:**

Schema evolution without governance causes production data corruption. API schema violations break integrations. Proactive schema governance prevents these issues.

**Anti-Patterns:**
- Schema-less JSON storage
- Breaking schema changes without migration plan

---

### Database & Persistence

#### [OPTIONAL] Database Migration Governance

**Priority**: CRITICAL
**Applies When**: IF project uses relational databases (PostgreSQL, MySQL, SQLite) OR schema management tools

**Example Conditions:**
- IF project uses **Alembic/Flyway** THEN enforce migration script review and rollback testing
- IF project has **zero-downtime requirements** THEN enforce expand-migrate-contract pattern

**Principle Description:**

Database migrations are high-risk operations that can cause production outages, data loss, or application breakage. Migration governance establishes safety protocols: backward compatibility validation, rollback testing, staged deployment, and operation-specific review requirements.

**Requirements:**

1. **Migration Safety Standards**
   - Backward Compatible by Default: Old code continues working during migration
   - Expand-Migrate-Contract Pattern for schema changes
   - Rollback Testing: Every migration has tested downgrade path
   - Lock Analysis: Long-running operations (>30s) broken into stages

2. **Backward Compatibility Rules**
   - ✅ ALLOWED: Add nullable columns, create indexes concurrently
   - ❌ PROHIBITED: Add NOT NULL columns without default, drop columns in use

3. **Migration Review Process**
   - Automated linter checks for anti-patterns
   - Manual review for migrations affecting >1M rows
   - Dry-run in staging before production

**Enforcement Mechanisms:**

- **Verification - Automated**: Migration linting, integration tests, performance tests
- **Verification - Manual**: DBA review, staging validation, post-deployment monitoring
- **Tooling**: Alembic, Flyway, pytest-alembic, database backup automation

**Why This Matters:**

Database migrations are a leading cause of production outages. Backward-incompatible migrations break running applications. Migration governance reduces these risks by 50%+.

**Anti-Patterns:**
- No rollback strategy
- Dropping columns still referenced in old code
- Running heavy operations during peak traffic

---

#### [OPTIONAL] Connection Pooling Standards

**Priority**: RECOMMENDED
**Applies When**: IF project uses databases AND handles concurrent requests

**Example Conditions:**
- IF project uses **PostgreSQL with asyncpg** THEN configure connection pooling
- IF project uses **async frameworks** (FastAPI, asyncio) THEN use async connection pools

**Principle Description:**

Establishing database connections is expensive (50-200ms per connection). Connection pools maintain open connections and lease them to requests, providing 6.7x performance improvement.

**Requirements:**

1. **Pool Configuration**
   - Min Size: 2-5 connections, Max Size: 10-20 connections per instance
   - Connection Lifetime: 5-15 minutes max
   - Idle Timeout: 60-300 seconds

2. **Async Pool Management**
   - Use `asyncpg.create_pool()` for PostgreSQL async operations
   - Pool as context manager: Auto-return connections after use

3. **Monitoring**
   - Track pool utilization (active/idle/total connections)
   - Alert on pool exhaustion (>90% utilization sustained)

**Enforcement Mechanisms:**

- **Verification - Automated**: Integration tests, load tests, health check metrics
- **Verification - Manual**: Code review, performance profiling
- **Tooling**: asyncpg, SQLAlchemy QueuePool, APM tools

**Why This Matters:**

Connection pooling provides 6.7x performance improvement. Prevents connection exhaustion under load.

**Anti-Patterns:**
- Creating connections per request
- No max connection limit
- Leaking connections

---

### API Protocols

#### [OPTIONAL] API Protocol Compliance Standards

**Priority**: CRITICAL
**Applies When**: IF project implements network protocols (MCP, REST, GraphQL, gRPC)

**Example Conditions:**
- IF project implements **MCP protocol** THEN use FastMCP framework with SSE transport
- IF project implements **REST APIs** THEN follow OpenAPI specification
- IF project implements **GraphQL** THEN enforce schema-first development

**Principle Description:**

Protocol violations break integrations, cause parsing failures, and prevent interoperability. MCP protocol requires SSE transport with no stdout/stderr pollution. REST APIs benefit from OpenAPI contracts.

**Requirements:**

1. **MCP Protocol Compliance** (if applicable)
   - Transport: SSE (Server-Sent Events) only
   - Logging: File-based structured logging, never stdout/stderr
   - Framework: FastMCP with automatic schema generation

2. **REST API Standards** (if applicable)
   - Specification: OpenAPI 3.0+ maintained alongside code
   - Versioning: Semantic versioning with `/v1/` prefix
   - Contract Testing: Request/response validation

3. **General Protocol Requirements**
   - Error Format: Structured responses (status code, message, details, correlation ID)
   - Rate Limiting: Documented limits with 429 responses

**Enforcement Mechanisms:**

- **Verification - Automated**: Protocol compliance tests, OpenAPI validators, contract tests
- **Verification - Manual**: Integration testing with protocol clients
- **Tooling**: FastMCP, OpenAPI generators, GraphQL schema linters

**Why This Matters:**

MCP protocol violations prevent AI assistant integrations. REST API schema drift breaks client applications.

**Anti-Patterns:**
- MCP: Logging to stdout/stderr (breaks protocol)
- REST: No API versioning
- All: Inconsistent error format

---

### Async & Concurrency

#### [OPTIONAL] Async/Await Standards

**Priority**: RECOMMENDED
**Applies When**: IF project uses async frameworks (asyncio, FastAPI, Node.js async)

**Example Conditions:**
- IF project uses **FastAPI** THEN all I/O operations must be async
- IF project uses **asyncio** THEN enforce proper event loop management

**Principle Description:**

Async operations enable high concurrency without thread overhead. Blocking operations in async code destroy performance. Proper event loop management prevents resource leaks.

**Requirements:**

1. **Async I/O Enforcement**
   - Database: Use async drivers (asyncpg, Motor)
   - HTTP Clients: Use httpx or aiohttp (not requests)
   - External Services: Use async libraries or run_in_executor

2. **Event Loop Management**
   - Single Event Loop: One loop per process
   - No Blocking: Prohibit time.sleep, blocking I/O in async functions

3. **Error Handling**
   - Handle asyncio.CancelledError properly
   - All async operations have timeouts

**Enforcement Mechanisms:**

- **Verification - Automated**: Linters detect blocking I/O, performance tests
- **Verification - Manual**: Code review, profiling
- **Tooling**: Ruff with async rules, pytest-asyncio

**Why This Matters:**

Async code provides 10-100x concurrency improvement. Blocking operations destroy this benefit.

**Anti-Patterns:**
- Mixing sync and async code without executors
- Using blocking libraries in async code
- No timeouts on async operations

---

### Framework-Specific

#### [OPTIONAL] FastAPI Best Practices

**Priority**: RECOMMENDED
**Applies When**: IF project uses FastAPI framework

**Principle Description:**

FastAPI provides automatic validation, dependency injection, and OpenAPI generation. Proper usage maximizes these benefits.

**Requirements:**

1. **Dependency Injection**
   - Use `Depends()` for database sessions, authentication
   - Testing: Override dependencies with test doubles

2. **Pydantic Integration**
   - Request bodies: Pydantic models with validation
   - Response models: `response_model` parameter

3. **Async Patterns**
   - All I/O operations: async functions
   - Background tasks: Use BackgroundTasks

**Enforcement Mechanisms:**

- **Verification - Automated**: Tests validate dependency injection
- **Tooling**: FastAPI with TestClient

**Why This Matters:**

FastAPI patterns enable clean, testable, documented APIs.

**Anti-Patterns:**
- Global database sessions
- Blocking I/O in async endpoints

---

#### [OPTIONAL] FastMCP Framework Standards

**Priority**: CRITICAL
**Applies When**: IF project implements MCP servers

**Principle Description:**

FastMCP provides the shortest path from implementation to production MCP servers. Automatic schema generation from type hints ensures contract correctness.

**Requirements:**

1. **Framework Usage**
   - Use `@mcp.tool()` decorator for tool registration
   - Type hints on all decorated functions
   - Docstrings for function descriptions

2. **Protocol Compliance**
   - File-based logging only (no stdout/stderr)
   - SSE transport (FastMCP handles this)

**Enforcement Mechanisms:**

- **Verification - Automated**: Protocol compliance tests, log analysis
- **Tooling**: FastMCP framework, MCP Python SDK

**Why This Matters:**

FastMCP eliminates 90% of boilerplate for MCP servers.

**Anti-Patterns:**
- Direct protocol handling
- Logging to stdout/stderr

---

### Infrastructure

#### [OPTIONAL] Docker Best Practices

**Priority**: RECOMMENDED
**Applies When**: IF project uses Docker for deployment OR local development

**Principle Description:**

Docker provides consistent environments but introduces security and size concerns. Multi-stage builds reduce image size by 70%+.

**Requirements:**

1. **Image Security**
   - Run as non-root user
   - Minimal base images (alpine, distroless)
   - Scan images for vulnerabilities

2. **Image Optimization**
   - Multi-stage builds
   - .dockerignore to exclude unnecessary files
   - Target image size: <500MB for apps

3. **Health Checks**
   - HEALTHCHECK instruction in Dockerfile

**Enforcement Mechanisms:**

- **Verification - Automated**: Trivy/Snyk scans, image size checks
- **Tooling**: Trivy, Hadolint, Docker Scout

**Why This Matters:**

Multi-stage builds reduce image size by 70%+. Non-root execution prevents privilege escalation.

**Anti-Patterns:**
- Running as root
- No .dockerignore
- Secrets in images

---

#### [OPTIONAL] Environment Configuration Standards

**Priority**: RECOMMENDED
**Applies When**: IF project requires environment-specific configuration

**Principle Description:**

Configuration management prevents production incidents caused by misconfiguration. Environment variables provide 12-factor app compliance.

**Requirements:**

1. **Configuration Structure**
   - Python: `pydantic_settings.BaseSettings` with validation
   - Node.js: dotenv with validation

2. **Environment Files**
   - `.env.example`: Template (committed)
   - `.env`: Actual values (gitignored)

3. **Secret Management**
   - Secrets not in .env files (use secret manager)
   - Local development: Use .env with dummy secrets

**Enforcement Mechanisms:**

- **Verification - Automated**: Configuration validation tests, secret scanning
- **Tooling**: pydantic-settings, Vault/AWS Secrets Manager

**Why This Matters:**

Misconfiguration causes 80% of production incidents. Validation at startup prevents silent failures.

**Anti-Patterns:**
- Secrets committed to version control
- No validation
- Hard-coded configuration

---

### Quality & Process

#### [OPTIONAL] Static Analysis Standards

**Priority**: RECOMMENDED
**Applies When**: IF project uses linters/static analysis tools

**Principle Description:**

Static analysis catches bugs, security issues, and style violations before code review. Automated formatting eliminates style debates.

**Requirements:**

1. **Linting Configuration**
   - Python: Ruff with strict configuration
   - TypeScript: ESLint with strict rules

2. **Security Linting**
   - Python: Bandit for security issues
   - Detect: SQL injection, XSS, hardcoded secrets

3. **Complexity Metrics**
   - Cyclomatic complexity: Max 10-15 per function

**Enforcement Mechanisms:**

- **Verification - Automated**: Pre-commit hooks, CI pipeline blocks
- **Tooling**: Ruff, ESLint, Bandit, SonarQube

**Why This Matters:**

Static analysis catches 40-60% of bugs before runtime.

**Anti-Patterns:**
- Disabling linter rules without justification
- Ignoring complexity warnings

---

### Web Application Principles

#### [OPTIONAL] Core Web Vitals Performance Standards

**Priority**: CRITICAL
**Applies When**: IF project is user-facing web application

**Principle Description:**

Core Web Vitals are Google's essential metrics for measuring user experience quality. As of March 2024, INP (Interaction to Next Paint) replaced FID as the official responsiveness metric. These metrics directly impact SEO rankings, user engagement, and conversion rates.

**Requirements:**

1. **Largest Contentful Paint (LCP)**
   - MUST achieve LCP < 2.5 seconds for "Good" rating
   - Measure LCP in production with Real User Monitoring

2. **Interaction to Next Paint (INP)**
   - MUST achieve INP < 200 milliseconds for "Good" rating
   - Optimize JavaScript execution to avoid long tasks (> 50ms)

3. **Cumulative Layout Shift (CLS)**
   - MUST achieve CLS < 0.1 for "Good" rating
   - Set explicit width and height for images and videos

**Enforcement Mechanisms:**

- **Verification - Automated**: Lighthouse CI, PageSpeed Insights API, RUM alerts
- **Tooling**: Lighthouse CI, Web Vitals JS library, Sentry Performance

**Why This Matters:**

Google uses Core Web Vitals as a ranking factor. 53% of mobile users abandon sites taking >3 seconds. Amazon reported every 100ms of latency costs 1% in sales.

**Anti-Patterns:**
- Lazy loading images in initial viewport
- Heavy JavaScript on initial load
- Not setting dimensions for images

---

#### [OPTIONAL] WCAG 2.2 Web Accessibility Standards

**Priority**: CRITICAL
**Applies When**: IF project serves public users OR government entity OR accessibility requirements specified

**Principle Description:**

WCAG 2.2 (October 2023) defines how to make web content accessible. The U.S. Department of Justice's final rule requires state/local governments to meet WCAG 2.1 Level AA by April 2026-2027. Beyond legal compliance, accessibility is a moral imperative—15% of the global population lives with some form of disability.

**Requirements:**

1. **WCAG 2.2 Level AA Compliance**
   - All functionality MUST be keyboard accessible
   - Color contrast MUST meet 4.5:1 for normal text
   - All images MUST have meaningful alt text

2. **Semantic HTML & ARIA**
   - Use semantic HTML5 elements
   - ARIA attributes only when semantic HTML insufficient

3. **Screen Reader Support**
   - Test with NVDA, JAWS, VoiceOver
   - Dynamic content updates use ARIA live regions

**Enforcement Mechanisms:**

- **Verification - Automated**: axe-core in CI, Lighthouse accessibility audit
- **Verification - Manual**: Monthly screen reader testing
- **Tooling**: axe DevTools, WAVE, Cypress + cypress-axe

**Why This Matters:**

Legal compliance with ADA Title II rule. Disability market represents $13 trillion in global disposable income. Companies face lawsuits costing millions for accessibility failures.

**Anti-Patterns:**
- Using div/span for buttons
- Missing alt text
- Insufficient color contrast
- Keyboard traps

---

#### [OPTIONAL] Frontend Security Standards (CSP, CORS, XSS)

**Priority**: CRITICAL
**Applies When**: IF web application handles user data OR authentication OR user-generated content

**Principle Description:**

Modern web applications face sophisticated threats including XSS, CSRF, and clickjacking. Content Security Policy (CSP) is the leading defense-in-depth technique against XSS attacks. A strict CSP using nonces or hashes can prevent execution of malicious scripts.

**Requirements:**

1. **Content Security Policy - Strict Configuration**
   - MUST implement nonce-based or hash-based CSP
   - MUST avoid `unsafe-inline` and `unsafe-eval`
   - Deploy in report-only mode first, monitor violations

2. **XSS Prevention**
   - MUST sanitize all user input on arrival
   - MUST encode output data based on context
   - Use DOMPurify for sanitizing HTML

3. **Secure Cookie Handling**
   - MUST set `Secure`, `HttpOnly`, `SameSite` flags

**Enforcement Mechanisms:**

- **Verification - Automated**: CSP validator, security headers scanner, OWASP ZAP
- **Verification - Manual**: Quarterly penetration testing
- **Tooling**: CSP Evaluator, Mozilla Observatory, DOMPurify

**Why This Matters:**

XSS is ranked #3 in OWASP Top 10. 94% of web applications have at least one serious vulnerability. Average data breach cost: $4.45 million. CSP reduces XSS exploit success by 95%.

**Anti-Patterns:**
- Using `script-src 'unsafe-inline'`
- CORS `*` with credentials
- Trusting client-side validation alone

---

#### [OPTIONAL] Modern Image Optimization Standards

**Priority**: RECOMMENDED
**Applies When**: IF web application displays images OR requires fast LCP

**Principle Description:**

Poorly optimized images are the leading cause of slow page loads and poor LCP scores. AVIF offers 60-70% smaller file sizes than JPG. Modern responsive image techniques using `<picture>`, `srcset`, and lazy loading are essential.

**Requirements:**

1. **Modern Format Adoption**
   - MUST serve AVIF with WebP and JPG/PNG fallbacks
   - Use `<picture>` element for format negotiation

2. **Responsive Images**
   - MUST use `srcset` attribute for multiple resolutions
   - MUST set explicit `width` and `height` attributes

3. **LCP Image Optimization**
   - MUST use `fetchpriority="high"` on LCP image
   - MUST NOT lazy-load LCP images

**Enforcement Mechanisms:**

- **Verification - Automated**: Lighthouse audit, bundle size checks
- **Tooling**: Sharp, Squoosh, imagemin, CDNs (Cloudinary, Cloudflare)

**Why This Matters:**

AVIF reduces image size by 60-70%. 1-second delay reduces conversions by 7%. Sites with LCP > 2.5s experience 50% higher bounce rates.

**Anti-Patterns:**
- Serving full-resolution to mobile
- Lazy loading hero images
- Not setting width/height

---

#### [OPTIONAL] SEO & Discoverability Standards

**Priority**: CRITICAL
**Applies When**: IF public-facing website OR requires search engine visibility

**Principle Description:**

Modern SEO requires structured data (JSON-LD), comprehensive meta tags, and Server-Side Rendering (SSR) or Static Site Generation (SSG) for critical pages. Structured data enables rich snippets in search results, increasing click-through rates by 20-30%.

**Requirements:**

1. **Structured Data Implementation (JSON-LD)**
   - MUST implement Schema.org vocabulary via JSON-LD
   - MUST validate with Google Rich Results Test

2. **Meta Tags Optimization**
   - MUST include unique `<title>` and `<meta name="description">`
   - MUST implement Open Graph and Twitter Card tags

3. **Server-Side Rendering (SSR) or Static Site Generation (SSG)**
   - MUST use SSR/SSG for important pages
   - MUST deliver pre-rendered HTML to crawlers

**Enforcement Mechanisms:**

- **Verification - Automated**: Google Rich Results Test, Lighthouse SEO audit
- **Verification - Manual**: Monthly Google Search Console review
- **Tooling**: Schema.org validator, next-seo, vue-meta

**Why This Matters:**

Organic search drives 53% of all website traffic. Sites with structured data see 20-30% higher CTR. 75% of users never scroll past first page.

**Anti-Patterns:**
- Client-side rendering only for public pages
- Missing or duplicate meta descriptions
- No structured data

---

#### [OPTIONAL] Progressive Web App (PWA) Standards

**Priority**: RECOMMENDED
**Applies When**: IF application benefits from offline support OR installability

**Principle Description:**

PWAs combine web reach with native app capabilities—offline functionality, push notifications, home screen installation. Service workers enable caching strategies. Installed PWAs have 2-3x higher engagement rates.

**Requirements:**

1. **Service Worker Implementation**
   - MUST register service worker
   - MUST cache critical assets during `install` event
   - MUST provide custom offline page (minimum)

2. **Web App Manifest**
   - MUST create `manifest.json` with required fields
   - MUST provide icons: 192x192px, 512x512px, maskable icon

3. **HTTPS Requirement**
   - MUST serve entire site over HTTPS

**Enforcement Mechanisms:**

- **Verification - Automated**: Lighthouse PWA audit
- **Verification - Manual**: Monthly offline functionality testing
- **Tooling**: Workbox, PWA Builder

**Why This Matters:**

Installed PWAs have 2-3x higher engagement. Twitter Lite saw 65% increase in pages per session. Starbucks PWA is 99.84% smaller than iOS app.

**Anti-Patterns:**
- Not implementing offline page
- Caching too aggressively
- Not handling service worker updates

---

#### [OPTIONAL] Frontend Testing Standards

**Priority**: CRITICAL
**Applies When**: IF web application requires quality assurance OR regression prevention

**Principle Description:**

Comprehensive frontend testing prevents regressions. Playwright has emerged as the leading E2E framework for superior cross-browser support. Visual regression testing detects unintended UI changes.

**Requirements:**

1. **End-to-End (E2E) Testing**
   - MUST implement E2E tests for critical user flows
   - SHOULD use Playwright or Cypress
   - MUST test across browsers: Chromium, Firefox, WebKit
   - Target E2E test execution time: <10 minutes in CI

2. **Accessibility Testing**
   - MUST integrate axe-core accessibility tests
   - Target 0 WCAG violations on critical pages

3. **Visual Regression Testing**
   - SHOULD implement visual regression tests
   - MUST review visual diffs during code review

**Enforcement Mechanisms:**

- **Verification - Automated**: CI/CD pipeline runs all tests
- **Tooling**: Playwright, Cypress, axe-core, Percy/Chromatic

**Why This Matters:**

E2E tests catch 70% of integration bugs. Visual regression prevents unintended UI changes. Automated testing reduces manual QA costs by 50-70%.

**Anti-Patterns:**
- Using CSS classes for test selectors
- Flaky tests
- Not running tests in CI/CD

---

#### [OPTIONAL] Frontend Bundle Optimization Standards

**Priority**: RECOMMENDED
**Applies When**: IF web application serves JavaScript bundles OR requires fast TTI

**Principle Description:**

JavaScript bundle size directly impacts Time to Interactive. Every 100KB adds ~250ms to TTI on mid-range mobile. Code splitting, tree shaking, and lazy loading can reduce initial bundle by 50-70%.

**Requirements:**

1. **Bundle Size Targets**
   - MUST keep initial JavaScript bundle < 200KB (gzipped)
   - MUST monitor bundle size in CI/CD

2. **Code Splitting**
   - MUST implement route-based code splitting
   - SHOULD implement component-based code splitting

3. **Tree Shaking**
   - MUST enable tree shaking (production mode)
   - MUST use ES6 modules (not CommonJS)

**Enforcement Mechanisms:**

- **Verification - Automated**: bundlesize/size-limit in CI, Lighthouse budgets
- **Verification - Manual**: Monthly bundle analysis
- **Tooling**: webpack-bundle-analyzer, vite-bundle-visualizer

**Why This Matters:**

Large bundles cause slow page loads. 1-second delay reduces conversions by 7%. Optimized bundles reduce bandwidth costs and improve Core Web Vitals.

**Anti-Patterns:**
- Importing entire libraries
- Using barrel exports
- Not lazy-loading routes

---

#### [OPTIONAL] State Management Architecture Standards

**Priority**: RECOMMENDED
**Applies When**: IF React/Vue/Angular application with complex state

**Principle Description:**

As of 2024, state management has shifted from Redux-dominated to nuanced approach: Zustand for client state, React Query for server state. The key is separating client state from server state.

**Requirements:**

1. **State Management Decision Framework**
   - IF simple prop-drilling THEN use Context API
   - IF medium to large app THEN use Zustand
   - IF large enterprise app THEN use Redux Toolkit
   - IF heavy server data THEN use React Query

2. **Server State Management (React Query)**
   - MUST use React Query for data fetching
   - MUST NOT store server state in Redux/Zustand

3. **Performance Optimization**
   - MUST prevent unnecessary re-renders
   - Target: <16ms render time (60fps)

**Enforcement Mechanisms:**

- **Verification - Automated**: ESLint rules, bundle size checks
- **Verification - Manual**: Monthly performance profiling
- **Tooling**: Redux DevTools, React Query DevTools, Zustand DevTools

**Why This Matters:**

State management impacts productivity, performance, maintainability. Zustand (3KB) vs Redux (40KB) impacts load time. React Query eliminates 90% of server state boilerplate.

**Anti-Patterns:**
- Context API for frequently changing state
- Storing server state in Redux/Zustand
- Not using selectors

---

#### [OPTIONAL] Frontend Monitoring & Observability Standards

**Priority**: CRITICAL
**Applies When**: IF production web application OR requires error tracking

**Principle Description:**

Frontend monitoring is essential for understanding real user experience. Modern observability combines error tracking, Real User Monitoring (RUM), session replay, and analytics. Without monitoring, teams operate blind.

**Requirements:**

1. **Error Tracking & Reporting**
   - MUST implement error tracking service (Sentry, Rollbar)
   - MUST capture JavaScript errors, unhandled promise rejections
   - MUST enrich errors with context (user ID, session ID, environment)
   - Target error rate: <0.1% of sessions

2. **Real User Monitoring (RUM)**
   - SHOULD implement RUM for production performance data
   - MUST track Core Web Vitals (LCP, INP, CLS) from real users

3. **Analytics Integration**
   - SHOULD implement analytics (GA4, Mixpanel, Amplitude)
   - MUST track key user actions

4. **Privacy & Compliance**
   - MUST comply with GDPR, CCPA
   - MUST anonymize PII in error logs

**Enforcement Mechanisms:**

- **Verification - Automated**: Error tracking integration tests
- **Verification - Manual**: Weekly error dashboard review
- **Tooling**: Sentry, Datadog RUM, GA4, LogRocket

**Why This Matters:**

Sentry detects errors 10x faster. RUM shows 53% of users abandon slow sites. Session replay reduces debugging time by 50-70%. Average 1-hour downtime costs $300k for e-commerce.

**Anti-Patterns:**
- Not implementing error tracking
- Missing source maps
- Not filtering low-severity errors
- Not anonymizing PII

---

**Last Updated**: [YYYY-MM-DD]
**Next Review**: [YYYY-MM-DD] ([Quarterly/Semi-annually/Annually])
