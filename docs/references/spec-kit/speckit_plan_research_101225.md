# GitHub Spec-Kit /plan Command: Complete Implementation Guide

The /plan command transforms functional specifications into executable technical blueprints through a structured, phase-gated workflow that generates multiple artifacts—research documentation, data models, API contracts, and quickstart guides—while enforcing constitutional principles and preventing over-engineering. This methodology achieves what traditional planning often fails at: **maintaining implementation flexibility while providing just enough structure to guide AI agents toward consistent, maintainable solutions**.

GitHub released Spec-Kit in September 2024 to address a fundamental problem with AI coding: agents excel at pattern completion but fail at mind-reading. The /plan command sits at the critical transition point between "what to build" (specification) and "how to build it" (implementation), serving as the bridge where product requirements transform into architectural decisions. This guide synthesizes insights from official documentation, community implementations, and real-world usage patterns to provide actionable guidance for creating effective technical plans.

## The /plan command solves three critical problems in AI-assisted development

Traditional development treats specifications as disposable scaffolding discarded once coding begins. Spec-Kit inverts this: specifications become executable artifacts that directly generate implementations. The /plan command specifically addresses the "translation gap"—the space where vague product requirements must transform into precise technical decisions without losing flexibility or enabling over-engineering.

**The first problem is premature specificity.** When developers provide high-level requirements directly to AI coding agents, the agents must guess at technology choices, architectural patterns, and integration approaches. These guesses often reflect popular patterns rather than project needs, leading to over-engineered solutions using trendy frameworks for simple problems. The /plan command forces explicit technical decisions upfront while maintaining appropriate abstraction levels.

**The second problem is ambiguity accumulation.** Unclear requirements compound through the development process. A vague adjective like "fast" in a specification might mean sub-100ms latency to one stakeholder and under-5-second page loads to another. By the time this ambiguity surfaces during implementation, fixing it requires expensive rework. The /plan workflow includes a mandatory /clarify gate that catches and resolves ambiguities before technical planning begins.

**The third problem is architectural drift.** Without constitutional governance, each feature makes independent technical decisions, creating inconsistent patterns across a codebase. One feature might use REST APIs while another chooses GraphQL; security implementations vary; testing strategies diverge. The /plan command enforces alignment with project-wide principles defined in constitution.md, ensuring architectural consistency across all features.

## How /plan fits into the spec-driven development workflow

The complete workflow follows strict sequencing with validation gates: **/constitution → /specify → /clarify → /plan → /tasks → /analyze → /implement**. Each phase has explicit entry and exit criteria, with the /plan command serving as the architectural decision point.

**Phase 0 establishes governance.** The /constitution command creates the project's architectural DNA—non-negotiable principles that override individual preferences. This includes security standards, testing mandates, technology constraints, and coding patterns. Organizations can create "opinionated stacks" encoding their standards into reusable constitutions (Angular projects always use DDD principles and Angular Material; Python projects mandate type hints and pytest patterns). The constitution serves as permanent context for all AI agents, ensuring they respect organizational standards automatically.

**Phase 1 captures intent.** The /specify command generates high-level descriptions of features focusing exclusively on user journeys, experiences, and success criteria. This phase deliberately excludes technical details—no frameworks, no databases, no API designs. A good specification answers "what should users be able to do?" and "why does this matter?" without constraining "how will we build it?" The Taskify example demonstrates this well: "Users create projects, add team members, assign tasks, comment, and move tasks between Kanban boards" with explicit constraints like "5 predefined users initially, 3 sample projects, standard Kanban columns."

**Phase 1.5 eliminates ambiguity.** The /clarify command runs structured questioning to resolve unclear requirements before technical planning. The AI performs sequential, coverage-based questioning, recording answers in a Clarifications section of spec.md. This gate identifies underspecified requirements, vague adjectives, unresolved critical choices, and missing constraints. The /plan template explicitly checks for this section and pauses execution if ambiguities remain, forcing resolution when fixing is cheap rather than expensive.

**Phase 2 transforms intent into architecture.** The /plan command accepts user-provided technical constraints (tech stack, frameworks, performance targets, integration requirements) and generates comprehensive technical artifacts. This isn't just documentation—it's an executable template that orchestrates artifact generation through a structured 9-step workflow with explicit quality gates. The command produces plan.md (core implementation strategy), research.md (technology validation), data-model.md (entity definitions), contracts/ (API specifications), and quickstart.md (development setup).

**Phase 3 creates actionable tasks.** After human review and approval of the technical plan, the /tasks command breaks the plan into small, reviewable implementation chunks. Each task is isolated, testable, and references specific plan sections. Tasks follow test-driven development ordering: contract definitions come before contract tests, which come before implementation. This granular breakdown enables focused code reviews rather than overwhelming thousand-line diffs.

**Phase 3.5 validates alignment.** The /analyze command performs cross-artifact validation before implementation begins, checking spec-to-plan alignment, plan-to-constitution compliance, requirements completeness, and quality checklist items. Constitutional violations are flagged as CRITICAL findings that block the /implement command until resolved. This final checkpoint ensures the entire specification-to-implementation chain maintains consistency.

**Phase 4 executes the plan.** The /implement command follows the task breakdown using TDD principles, with AI agents writing actual code while developers review focused changes. Because tasks are granular and well-specified, reviews focus on "does this correctly solve the stated problem?" rather than "what is this trying to do?"

## Creating effective technical plans through structured documentation

The plan.md file structure reflects a philosophy of progressive disclosure: high-level architectural decisions appear first, with detailed technical information extracted to separate artifacts. This keeps plans scannable and maintainable while providing necessary depth through cross-referenced documents.

**Technical Context establishes the decision foundation.** Every plan begins with a metadata header linking to the source specification and feature branch, followed by a Technical Context section capturing core architectural choices. This includes language and version (Python 3.11, Swift 5.9), primary dependencies (FastAPI, UIKit), storage approach (PostgreSQL, CoreData, files, or N/A), testing framework (pytest, XCTest), target platform (Linux server, iOS 15+), and project type determining source structure.

The Technical Context uses an explicit clarity pattern: each element must contain a specific value or the marker "NEEDS CLARIFICATION." This forces decisions to be made rather than assumed. Performance goals must be domain-specific and measurable: "1000 req/s for API," "10k lines/sec for parser," "60 fps for UI" rather than vague adjectives like "fast" or "scalable." This section serves as a quality gate—all NEEDS CLARIFICATION markers must be resolved before Phase 0 research begins.

**Project structure selection determines code organization.** Based on detected requirements, the template offers three standard patterns. Single project architecture uses src/ (with models/, services/, cli/, lib/) and tests/ (with contract/, integration/, unit/) for standalone applications and libraries. Web application architecture separates backend/src/ (models/, services/, api/) and frontend/src/ (components/, pages/, services/) when frontend and backend are explicitly mentioned. Mobile + API architecture divides api/ and ios/android/ directories with platform-specific feature modules when iOS or Android appears in requirements. The AI must select one structure, justify the choice, and remove unused options from the final plan.

**Constitution checks validate architectural alignment.** Before and after design generation, the plan evaluates proposed architecture against constitutional requirements. This section documents any principle violations with explicit justifications. If violations cannot be justified, the implementation approach must be simplified. This double-gate pattern (pre-design and post-design) catches both initial misalignments and complications introduced during detailed planning.

**Phase-based artifact generation separates concerns.** Phase 0 generates research.md containing technology investigations, library compatibility analysis, performance benchmarks, security implications, and architectural decisions with documented rationale. For rapidly changing technologies like .NET Aspire or modern JavaScript frameworks, this research phase validates version-specific approaches and documents known issues. Phase 1 generates data-model.md (entity definitions, relationships, schemas), contracts/ (API specifications, interface definitions), quickstart.md (development setup and validation scenarios), and agent-specific context files (updates to CLAUDE.md, .github/copilot-instructions.md, or GEMINI.md with project context).

The artifact directory structure makes relationships explicit. Each feature gets a specs/###-feature-name/ directory containing spec.md (from /specify), plan.md (from /plan), research.md (Phase 0 output), data-model.md (Phase 1 output), contracts/ (Phase 1 output), quickstart.md (Phase 1 output), and tasks.md (from separate /tasks command). This structure enables clear traceability: when reviewing implementation, developers can trace decisions back through tasks → plan → spec to understand not just what was built but why.

**Progress tracking provides execution transparency.** The plan includes a Progress Tracking section updated incrementally as the /plan command executes, showing completion status of Initial Constitution Check, Phase 0 research, Phase 1 design, and Post-Design Constitution Check. Any ERROR or WARN states are documented here, providing visibility into what's complete versus pending and blocking issues requiring resolution.

## Architecture Decision Records integrate directly into planning artifacts

Unlike traditional ADR systems that maintain separate decision documents, Spec-Kit embeds architectural decisions directly into plan.md and research.md. This reflects the "executable specifications" philosophy where documentation evolves alongside implementation rather than existing as static records.

**Inline decisions in plan.md capture high-level choices.** Technology stack selections, architectural patterns, performance targets, testing strategies, and integration patterns appear directly in the Technical Context and implementation approach sections. These decisions are concise (often single-line entries) but link to detailed analysis in research.md. For example: "Language: Python 3.11 chosen for async support and type hints. See research.md for FastAPI vs Flask vs Django comparison."

**Detailed analysis in research.md documents alternatives.** When architectural decisions require justification, research.md provides the "why X over Y" analysis. This includes options evaluated (listing alternatives considered), decision rationale (performance benchmarks, ecosystem maturity, team expertise), trade-offs accepted (known limitations or compromises), and consequences (how this choice affects other decisions). The format follows a pattern: state the choice clearly, explain why it was made, enumerate alternatives that were rejected with reasons, and acknowledge trade-offs.

**Decision documentation pattern maintains clarity.** Good architectural decision documentation includes these elements: context explaining what problem this solves, the specific decision made, alternatives considered with elimination rationale, consequences both positive and negative, constitutional alignment showing how this respects project principles, and version specificity for rapidly changing technologies. For database selection, this might document: "Context: Real-time collaboration requirement with 50+ concurrent users. Options: PostgreSQL + LISTEN/NOTIFY (200ms latency), Redis + Pub/Sub (5ms latency), Postgres + Redis hybrid (15ms latency). Decision: Hybrid approach. Rationale: Meets real-time requirement (<50ms) while maintaining ACID guarantees. Trade-off: Added complexity justified by critical UX requirement."

**Decisions evolve through append-only updates.** Rather than creating new ADR files, Spec-Kit updates existing plan.md and research.md with new information. Updates include date stamps: "Updated 2025-10-15: Added .NET Aspire 8.0.1 specific integration patterns." Deprecated decisions are marked with strikethrough: "~~Original choice: Monolithic architecture~~ Superseded by microservices (see research.md section 3.2)." This maintains decision history inline rather than scattering it across multiple ADR files.

**Constitutional linking provides governance.** Every architectural decision must reference how it aligns with project principles defined in constitution.md. Nine common constitutional articles include: Feature as Library (every feature begins as standalone component), Observability Over Opacity (everything inspectable through CLI), Simplicity Over Cleverness (start simple, add complexity only when proven necessary), Integration Over Isolation (test in real environments), Modularity Over Monoliths (clear boundaries between features), TDD Mandate (contract → integration → e2e → unit test ordering), Real Dependencies (no mocks in integration tests), Performance as Feature (measurable performance goals required), and Documentation as Code (all decisions captured in markdown).

**Version-specific evolution handles rapid change.** For fast-moving technologies, research.md should document the specific version being used (e.g., ".NET Aspire 8.0.1"), known issues or limitations in that version, upgrade paths and compatibility concerns, and API changes from previous versions. This allows future updates to compare new versions against documented constraints. The iterative refinement prompt demonstrates this: "Go through the implementation plan looking for areas that could benefit from additional research as .NET Aspire is rapidly changing. Update the research document with specific versions and spawn parallel research tasks to clarify details."

## Technology stack selection balances specificity with flexibility

The plan command requires explicit technology decisions while maintaining appropriate flexibility for implementation details. This balance prevents both over-specification (removing developer creativity) and under-specification (forcing AI agents to guess).

**Three-level specificity model guides decisions.** Must-specify elements include primary language and major framework, database technology, core architectural patterns (monolith/microservices/serverless), API design approach (REST/GraphQL/gRPC), and authentication/authorization mechanism. These choices fundamentally shape the system and require early commitment. Should-specify elements include major libraries for core functionality, testing frameworks and approaches, build and deployment tooling, package manager choices, and state management approach. These affect developer experience and system maintainability but allow some variation. Can-defer elements include minor utility libraries, CSS frameworks (unless design system mandated), logging libraries, development tools, and code formatting standards. These have minimal architectural impact and can be decided during implementation.

**Lock-in criteria determine commitment timing.** Lock in technology choices when organizational constraints exist (company-mandated stacks like .NET Aspire and PostgreSQL), compliance requirements dictate specific technologies, legacy system integration requires matching existing tech, team expertise is critical and deadlines are tight, or performance requirements demand specific technologies with proven benchmarks. Keep flexibility when technology is rapidly evolving (mark with research tasks to investigate latest versions), exploring implementation variants (Spec-Kit supports generating multiple implementations from one spec), building libraries or modules (abstract interfaces allow swapping implementations), or early prototyping (defer some decisions until after validation).

**Justification patterns document rationale.** For each major technology choice, document the choice itself, why it was selected (performance data, ecosystem maturity, team expertise, organizational standards), alternatives that were considered (with elimination reasons), trade-offs accepted (known limitations or compromises), and version constraints (specific version requirements and compatibility needs). This documentation prevents future questions about "why did we choose X?" and enables informed evolution of technology choices as better options emerge.

**Constitutional constraints flow into planning.** The constitution.md file should establish technology constraints before feature planning begins. This includes mandated frameworks ("All projects use React with TypeScript"), approved cloud providers and deployment platforms, required security tools and libraries (specified encryption libraries, secrets management approach), testing frameworks and coverage requirements, and organizational design systems. When constitutional constraints exist, AI agents automatically respect them during plan generation, ensuring consistency across features.

**Handling rapidly changing technologies requires research-driven approaches.** For frameworks like .NET Aspire, modern JavaScript libraries, or rapidly evolving cloud services, create targeted research tasks investigating specific integration points rather than generic research. Document specific versions in research.md with exact version numbers and release dates. Include version constraints in plan.md tied to validated approaches. Update quickstart.md with exact installation commands matching researched versions. Plan for evolution by documenting upgrade considerations and known migration paths.

## Data model design enables future evolution while providing current structure

The separate data-model.md artifact keeps entity design distinct from implementation details, allowing schema iteration without touching code. This separation enables clear contracts for front-end and back-end coordination while maintaining flexibility for refinement.

**Entity documentation follows progressive elaboration.** Each entity includes a clear purpose statement explaining what it represents, lifecycle description covering creation, updates, and deletion logic, fields table with name, type, constraints, and business rules, relationships section documenting belongs-to, has-many, and reference associations, and business invariants listing rules that must always be true and cross-field validations. For example: "Entity: Task. Purpose: Represents a unit of work within a project. Lifecycle: Created by users, updated through drag-drop, soft-deleted to preserve history. Fields: id (UUID, PK, immutable), project_id (UUID, FK, NOT NULL, indexed), title (VARCHAR(255), NOT NULL), status (ENUM: todo|in_progress|in_review|done). Relationships: Belongs to Project, Has many Comments. Business Invariants: Task must belong to exactly one project, Status transitions are unidirectional (todo → in_progress → in_review → done), Completed tasks cannot be reassigned."

**Schema design principles prioritize adaptability.** Start simple and add complexity only when proven necessary—begin with minimal viable schema, add indexes and optimizations in refinement phase, mark premature optimizations with [FUTURE OPTIMIZATION] tags. Document business invariants explicitly, not just database constraints: capture business rules like "A task can only be in one project," state transitions like "Tasks in Done status cannot be edited," and capacity constraints like "Maximum 15 tasks per Kanban column." Balance normalization with practical needs by applying normalization for data integrity, denormalizing intentionally for performance with documented rationale, using views or computed fields over storing derived data, and documenting trade-offs in data-model.md.

**Timing decisions for implementation details follows phase gates.** Phase 1 conceptual schema (in data-model.md) documents entities and relationships, key fields and types, business rules and constraints, and cardinality with validation rules. Phase 2 logical schema (in contracts/) specifies actual table definitions, indexes on frequently queried fields, foreign key relationships, and check constraints. Phase 3 physical tuning (in tasks.md) addresses performance indexes, partitioning strategies, migration scripts, and seed data requirements. This phased approach prevents premature optimization while ensuring necessary structure exists before implementation begins.

**Relationship documentation patterns maintain clarity.** For each entity relationship, document the relationship type and cardinality (one-to-many, many-to-many), cascade behavior (what happens when parent is deleted), orphan prevention (constraints preventing dangling references), and query optimization (indexes supporting common queries). Junction tables for many-to-many relationships should include the junction table name, additional attributes beyond foreign keys (like role or joined_at), and constraints (like "at least one owner per project").

**State management and data flow receive explicit documentation.** Specify application state (where it's stored: Redux/Context/MobX, what it contains: user session/UI state/transient data, persistence approach: session storage versus database). Define server state (database storage, core business data, caching strategy using Redis or in-memory approaches). Document data flow from user action through API request, validation, business logic, database transaction, response, state update, to UI refresh. Establish synchronization patterns including when to use optimistic updates, real-time update mechanisms (WebSocket/SSE), and conflict resolution strategies (last-write-wins/CRDT).

**Schema evolution guidelines prepare for change.** Classify changes by risk level: additive changes (new optional fields, new tables, new indexes) require migration but no data backfill; modification changes (field type changes, constraint additions) require migration plus data transformation; breaking changes (field removal, table removal) require deprecation path and migration strategy. Document the migration tool (Flyway, Liquibase, Alembic), migration file location (/migrations), rollback strategy (defined for each migration), and version compatibility (maintaining backward compatibility during transitions).

## API contracts define interfaces before implementation

The contracts/ directory contains machine-readable specifications (OpenAPI/Swagger for REST, GraphQL schemas, SignalR/WebSocket specifications) that enable contract-first development. These specifications serve as both documentation and executable contracts for testing.

**OpenAPI specifications capture REST API design.** Each endpoint includes the HTTP method and path, summary describing the operation, request parameters (path, query, header, with types and constraints), request body schema (for POST/PUT/PATCH operations with validation rules), response schemas for each status code (200, 201, 400, 404, 500), error response formats (consistent structure across all endpoints), and authentication requirements (security schemes applied to operations).

**Request and response documentation provides complete interface contracts.** Schemas use JSON Schema format with type definitions (string, number, boolean, object, array), validation constraints (required fields, min/max length, patterns, enums), format specifications (date-time, email, uuid), nested object structures, and example values demonstrating typical usage. Components section defines reusable schemas referenced across multiple endpoints, reducing duplication and ensuring consistency.

**Error handling follows standard conventions.** Success responses use appropriate status codes: 200 OK for successful GET requests, 201 Created for successful POST creating resources, 204 No Content for successful DELETE. Client error responses include: 400 Bad Request for invalid format or validation failure, 401 Unauthorized for missing or invalid authentication, 403 Forbidden for insufficient permissions, 404 Not Found for non-existent resources, and 409 Conflict for resource state conflicts. Server error responses use 500 Internal Server Error for unexpected errors and 503 Service Unavailable for temporary unavailability. Error response bodies follow consistent structure with error code (machine-readable identifier), message (human-readable description), field (identifying problematic field for validation errors), and details object for additional context.

**Authentication and authorization specifications establish security boundaries.** Document authentication methods (OAuth 2.0/OpenID Connect specifications, JWT token structure and expiration, API key management approaches, session-based authentication patterns). Define authorization patterns (Role-Based Access Control with role definitions, permission matrices documented in data-model.md, resource-level access controls, scope definitions for OAuth). Specify implementation details like token lifetime (access token: 1 hour, refresh token: 30 days), header format (Authorization: Bearer <token>), refresh endpoint (POST /api/auth/refresh), and token validation approach (signature verification, expiration checking, scope validation).

**API versioning strategy prevents breaking changes.** URL versioning provides explicit version in path (/api/v1/resource, /api/v2/resource), making routing and caching straightforward. Header versioning uses custom headers (X-API-Version: 2) or content negotiation (Accept header). Version management tracks major version for breaking changes, minor version for backward-compatible additions, and patch version for bug fixes. Breaking change protocol includes announcing deprecation (6 months notice), deploying new version with compatibility layer, monitoring usage of deprecated endpoints, communicating with consumers, and removing old version after sunset period.

**Contract evolution follows analyze-before-extend pattern.** First feature creates initial OpenAPI specification. Subsequent features analyze existing contracts for reusability—can existing endpoints be used? Can query parameters be added? Is a new endpoint truly necessary? Extensions occur only when existing operations are insufficient. This pattern prevents API bloat through intelligent contract analysis. Contract testing with tools like Specmatic MCP validates backend implementations against specifications, provides mock servers for parallel frontend development, generates contract tests from specifications, and runs resiliency tests for boundary conditions.

## Integration management anticipates failure modes

Technical plans must document external dependencies and specify how to handle inevitable integration failures. This transforms integration from a hopeful best-case scenario to a managed risk with explicit degradation strategies.

**Dependency catalog documents external services.** For each external service, capture provider name and version (Stripe API v2, SendGrid v3), endpoint URLs and environments (staging, production), authentication mechanisms (API key, Bearer token, OAuth), rate limits and quotas (100 req/sec, 10k/month), SLA commitments (99.9% uptime), fallback services (primary and secondary providers), timeout configurations (connection and read timeouts), and monitoring requirements (health checks, alert thresholds).

**Service wrapper patterns abstract integration complexity.** Define abstract interfaces for each external service type (payment, email, SMS, analytics), adapter implementations for vendor-specific details, configuration management for endpoints and credentials, logging and monitoring at integration boundaries, and error translation from service-specific errors to application errors. This pattern allows swapping providers without changing application code and enables testing with mock services during development.

**Circuit breaker patterns prevent cascade failures.** Circuit breakers maintain three states: closed (normal operation, requests pass through), open (too many failures, reject requests immediately), and half-open (testing if service recovered, allow single probe request). Configuration includes failure threshold (consecutive failures before opening, e.g., 5), timeout duration (how long to stay open before half-open test, e.g., 30 seconds), reset timeout (how long in half-open before closing, e.g., 60 seconds), and success threshold (consecutive successes needed in half-open to close circuit).

**Graceful degradation modes maintain partial functionality.** Define fallback behaviors for each external service: payment service down → queue orders for later processing with "pending" status, email service down → store emails in database queue for retry, search service down → fall back to database queries with reduced features, cache failure → direct database access with performance impact. Document user communication strategy including notification patterns (banner indicating degraded mode), feature availability messaging (which features still work), and estimated recovery time display.

**Retry policies balance recovery with overload prevention.** Configuration includes maximum attempts (typically 3 retries), initial delay (100ms for first retry), backoff multiplier (exponential: 100ms, 200ms, 400ms), maximum delay ceiling (5000ms to prevent excessive waiting), retry conditions (which status codes trigger retry: 500, 502, 503, 504), and no-retry conditions (client errors don't benefit from retry: 400, 401, 403, 404, 409). Implement idempotency keys for POST requests to prevent duplicate operations during retries. GET, PUT, and DELETE operations have natural idempotency, but POST operations require explicit idempotency handling.

**Integration testing approach validates reliability.** Contract testing ensures API compliance against OpenAPI specifications. Integration testing validates service interactions with real dependencies or high-fidelity mocks. Resiliency testing simulates failure modes (service timeout, network error, rate limit exceeded) to verify fallback behaviors work correctly. Parallel development uses Specmatic mock servers running on standardized ports, enabling frontend development against contracts while backend implements features against failing contract tests following TDD.

## Performance and scalability planning translates requirements into constraints

Vague performance goals like "fast" or "scalable" have no place in technical plans. Effective plans translate spec requirements into measurable constraints with monitoring strategies to validate achievement.

**Performance goals must be quantifiable and domain-specific.** For web APIs, specify request throughput (1000 req/s sustained), response latency (p50, p95, p99 targets: <200ms p95), error rate acceptable threshold (<0.1%), and concurrent user capacity (10k active sessions). For batch processing, define throughput (10k lines/sec processing), job completion time (max duration for typical workload), resource utilization limits (<70% CPU average), and concurrency (number of parallel jobs). For user interfaces, establish frame rate (60fps for animations), interaction responsiveness (<100ms for all interactions), page load time (<2 seconds perceived load), and time to interactive (<5 seconds on 3G network).

**Resource constraints establish operational boundaries.** Memory limits per instance (<512MB for containerized services), CPU utilization targets (<70% average to maintain responsiveness), database connection pool sizing (min 5, max 20 connections per instance), storage growth projections (<10GB first year, <50GB at 3 years), and network bandwidth requirements (typical and peak). These constraints inform infrastructure sizing and scaling strategies.

**Caching strategy follows multi-layer approach.** CDN layer caches static assets (images, CSS, JavaScript) with long TTL (24 hours), serves content from edge locations near users, and reduces origin server load. Application cache (Redis/Memcached) stores user sessions (30-minute TTL), API responses (5-minute TTL for frequently accessed data), and database query results (15-minute TTL for expensive queries). Database query cache uses built-in mechanisms (MySQL query cache, PostgreSQL shared buffers) and materialized views refreshed hourly for complex aggregations. Cache invalidation strategies include write-through (update cache on data modification), time-based expiration (TTL), event-based invalidation (clear cache on entity updates), and tag-based grouping (invalidate related items together).

**Database optimization starts with indexing strategy.** Document indexes on fields used for lookups (users.email for login queries), filtering (products.category for browsing), and sorting (orders.created_at for history). Create composite indexes for common query patterns (orders.user_id + orders.created_at for user order history). Add full-text indexes for search functionality (products.name, products.description). Consider index trade-offs: faster reads versus slower writes, storage overhead, and maintenance cost. Query optimization patterns include selecting only required columns (avoid SELECT *), implementing pagination (LIMIT/OFFSET or cursor-based for large result sets), preventing N+1 queries (eager loading, join optimization), enforcing query timeouts (5 seconds maximum), and configuring connection pooling (min 5, max 20 connections).

**Horizontal scaling enables capacity growth.** Load balancer configuration uses algorithms like round-robin with health checks, least connections for uneven workload distribution, or IP hash for session affinity. Auto-scaling triggers scale up when CPU exceeds 70% for 5 minutes, memory exceeds 80%, or request queue depth grows. Scale down when CPU drops below 30% for 15 minutes, maintaining minimum instances (typically 2 for high availability) and maximum instances (budget-based limit). Stateless design requirements include external session storage (Redis for session data), object storage for files (S3, Azure Blob), no local file system dependencies, and shared-nothing architecture enabling any instance to serve any request.

**Capacity planning calculates resource needs.** Start with expected load: 10k concurrent users generating 100 requests per user per hour equals 1M requests per hour equals 278 req/s average. Single instance capacity determines baseline: if one instance handles 100 req/s, you need 278/100 = 3 instances. Apply multipliers for reality: 2x for high availability (active-active pair), 3x for peak load handling (Black Friday, product launches), resulting in 3 * 2 * 3 = 18 instances at peak. Database sizing follows similar patterns: average query time (10ms), queries per request (5), total query load (278 req/s * 5 = 1,390 queries/s), single database capacity (5,000 queries/s), instance count (1 primary plus 2 read replicas for scale). Document growth projections: Year 1 baseline, Year 2 growth rate (50k users = 5x multiplier), Year 3 at-scale considerations (sharding, data partitioning).

**Monitoring and observability make performance measurable.** Key Performance Indicators include request rate (req/s), response latency percentiles (p50, p95, p99), error rate percentage, resource utilization (CPU, memory, disk I/O), database query performance (slow query log, execution plans), cache hit rate (effectiveness of caching strategy), and business metrics (conversion rate, user engagement). Observability stack components include metrics collection (Prometheus, Grafana, DataDog), logging with structured JSON format (ELK Stack, Loki), distributed tracing (OpenTelemetry, Jaeger for request flow across services), and application performance monitoring (APM tools for bottleneck identification). Health check endpoints expose service status, version information, dependency health, and degraded mode indicators.

## Security and compliance architecture embeds protection from day one

Rather than treating security as a post-development concern, effective plans embed security requirements into architectural decisions through constitutional governance and phase-specific security research.

**Constitutional security principles establish non-negotiables.** Authentication architecture specifies mechanisms (OAuth 2.0 with JWT tokens, RS256 signing algorithm), session management (30-minute inactivity timeout, 8-hour absolute timeout, refresh token rotation), and credential handling (no hardcoded secrets, zero exceptions). Authorization patterns define Role-Based Access Control with documented roles, principle of least privilege, and permissions checked at service layer AND API gateway for defense in depth. Data protection mandates encryption standards (AES-256-GCM for data at rest, TLS 1.3 for all network communication) and PII handling (encrypted storage, access logging, data classification). Secrets management specifies production approach (HashiCorp Vault), container credentials (Kubernetes secrets), and development secrets (environment variables, never committed to source control).

**Phase 0 security research validates approach.** During research phase, investigate authentication libraries for chosen stack with security track record, verify OWASP Top 10 mitigation patterns for common vulnerabilities, review encryption library options comparing libsodium versus language-native implementations, validate secrets management SDK compatibility with chosen stack, and research compliance requirements specific to industry (GDPR for EU users, HIPAA for healthcare, PCI-DSS for payment processing, SOC 2 for B2B SaaS).

**Threat modeling identifies attack surfaces.** Document trust boundaries where data crosses security domains (client to API gateway, API gateway to services, services to database), authentication flows showing token generation and validation paths, data flows with sensitivity classification (public, internal, confidential, PII), attack surface areas (public endpoints, file uploads, search functionality), and mitigation strategies for identified threats (input validation, output encoding, rate limiting, audit logging).

**Compliance requirements translate into implementation constraints.** GDPR compliance requires data portability (export user data in machine-readable format), right to erasure (complete data deletion within 30 days), consent management (explicit opt-in for processing, easy withdrawal), and data processing records (documented purposes and legal basis). HIPAA compliance mandates PHI handling (Protected Health Information identified and encrypted), audit logging (access to PHI tracked with tamper-proof logs), access controls (role-based, need-to-know principle), and incident response (breach notification within 60 days). Document compliance validation approach including periodic audits, automated compliance scanning, and evidence collection for attestation.

## Testing strategy enforces quality through constitutional mandate

Spec-Kit treats Test-Driven Development as non-negotiable, architecturally enforcing test-first approaches through file creation ordering and task sequencing rather than relying on developer discipline.

**TDD mandate establishes iron-clad process.** Constitutional principle: "All implementation MUST follow strict Test-Driven Development. No implementation code shall be written before: (1) unit tests are written, (2) tests are validated and approved by the user, (3) tests pass proving the feature works." File creation order enforces this: create contracts/ with API specifications, create test files in order (contract → integration → e2e → unit), then create source files to make tests pass. This ordering constraint ensures AI agents think about testability and contracts before implementation.

**Testing pyramid provides structure.** Contract tests form the foundation, specifying all external interfaces (API specs in OpenAPI format, SignalR/WebSocket specifications) with contract tests validating boundaries before implementation. Integration tests verify component interactions, focus on critical user paths from spec.md, use real dependencies rather than mocks (constitutional mandate), and create test-dataset snapshots for repeatability. End-to-end tests validate complete user journeys mapping to acceptance criteria in spec.md and test in production-like environments. Unit tests cover individual functions in isolation, focus on business logic, achieve high coverage (>80% of business logic), and mock external dependencies. This structure prevents both under-testing (missing critical paths) and over-testing (fragile tests for implementation details).

**Coverage targets balance thoroughness with pragmatism.** Contract test coverage requires 100% of external interfaces because these define system boundaries. Integration test coverage focuses on critical paths rather than comprehensive combinations—test the happy path for each user story, test one error case per category (network failure, invalid input, authorization failure), and validate state transitions for workflows. Unit test coverage targets exceed 80% of business logic while excluding trivial code (getters/setters, data transfer objects). End-to-end test coverage validates top 5 user journeys from specification, capturing the most important user experiences without attempting exhaustive scenario coverage.

**Test data management ensures repeatability.** Create test datasets with known inputs and expected outputs stored as fixtures. Generate snapshot tests capturing expected system state at specific points. Ensure deterministic test execution by avoiding time-based dependencies (mock dates, freeze time), random data (use seeded random generators), and external state (isolate tests from each other). Separate test data from production data with dedicated test databases, synthetic data generation, and data masking for production-like scenarios. Document test data setup in quickstart.md including database seeding scripts, fixture loading commands, and test environment configuration.

**CI/CD integration automates quality gates.** Pre-commit hooks run linting and formatting, validate no NEEDS CLARIFICATION markers remain in specs, execute fast unit tests, and check constitutional compliance. Continuous integration pipeline validates specifications against templates, runs complete test suite (contract, integration, e2e, unit), performs security scanning (dependency vulnerabilities, code analysis), checks test coverage thresholds, and validates that plan, spec, and constitution align using /analyze command. Deployment gates require all tests passing (zero tolerance for failing tests), security scan approval (no high-severity findings), performance benchmark validation (meets documented targets), and manual approval for production (human review of changes).

## Quality gates prevent premature progression

The spec-kit methodology includes explicit validation checkpoints that block progression until quality criteria are met. These gates catch issues when fixing is cheap rather than expensive.

**Pre-plan gates validate foundation.** Constitution.md must exist and be populated with security principles, testing standards, architecture patterns, technology constraints, and compliance requirements. Specification must be complete with goals and non-goals clearly defined, user stories with acceptance criteria, edge cases explicitly documented (not auto-generated), Review & Acceptance Checklist fully completed, and Clarifications section populated via /clarify. The /clarify command must have run unless explicitly overridden—this structured questioning reduces downstream rework by resolving ambiguities before technical planning begins.

**Plan completeness checklist ensures artifact quality.** Verify Tech Stack Summary documents language, dependencies, storage, and testing approach. Performance Goals and Constraints must be specific and measurable, not vague adjectives. Scale/Scope parameters specify expected users, data volume, and growth projections. Project structure choice (single/web/mobile) must be explicitly selected and justified with unused options removed. Phase 0 completion requires research.md exists and validates technology choices. Phase 1 completion requires data-model.md documents entities, contracts/ contains API specifications, and quickstart.md provides setup instructions. All NEEDS CLARIFICATION markers must be resolved—no exceptions.

**Traceability validation connects artifacts.** Every technology choice must have documented rationale in research.md. Every architectural decision must trace to spec requirements showing why this approach serves user needs. Implementation details must reference spec sections establishing clear lineage. Tasks must reference appropriate detail documents (data-model.md for entities, contracts/ for APIs) enabling developers to find context quickly.

**The /analyze command performs cross-artifact validation.** Running before /tasks generation, /analyze checks cross-artifact consistency (do plan and spec agree?), coverage analysis (are all requirements addressed?), constitutional compliance (do decisions respect principles?), requirements completeness (any gaps or ambiguities?), and custom quality checklists. Findings are categorized by severity: CRITICAL findings indicate constitutional violations and block /implement until resolved, WARNING findings suggest potential issues requiring review but don't block progression, INFO findings offer improvement suggestions. This final pre-implementation checkpoint ensures the entire specification-to-plan chain maintains consistency.

**Over-engineering detection prevents unnecessary complexity.** At specification level, verify no speculative "might need" features exist, all features trace to concrete user stories, no "nice to have" items without clear acceptance criteria, and all phases have clear prerequisites and deliverables. At plan level, ensure tech stack appropriately sized for requirements (not over-architected), no unnecessary complexity or "clever" solutions, adherence to "start simple, add complexity only when proven" principle, and no premature optimizations. At task level, confirm tasks are appropriately sized (not over-granular), dependencies are real not assumed, and no tasks exist for features not in specification. Human validation prompt before implementation: "Cross-check the details to see if there are any over-engineered pieces. If over-engineered components exist, resolve them. Ensure alignment with constitution."

## Common anti-patterns and effective countermeasures

Understanding failure modes enables preemptive protection. These patterns emerge consistently across implementations and have proven solutions.

**The God Plan anti-pattern creates unreadable documentation.** Plans exceeding 1000 lines for simple features indicate over-specification. Symptoms include code samples instead of architectural decisions, implementation details down to variable names, and decision rationale buried in implementation minutiae. This makes plans unreadable and defeats their purpose as navigable technical blueprints. The solution uses progressive disclosure: keep plan.md high-level (architecture, stack, patterns), move detailed specifications to implementation-details/ subfolder (per-feature detailed docs), extract API details to contracts/ (OpenAPI specs, GraphQL schemas), and place entity definitions in data-model.md (schemas, relationships, constraints). Quote from methodology: "This implementation plan should remain high-level and readable. Any code samples must be placed in the appropriate implementation-details/ file."

**Premature library selection reflects AI over-eagerness.** AI agents often select trendy or complex libraries without justification. The README explicitly warns: "Claude Code might be over-eager and add components that you did not ask for." This manifests as unnecessary frameworks for simple projects, dependency injection in 3-file applications, abstract factory patterns for basic CRUD operations, and microservices for features that could be functions. Prevention requires explicitly stating simplicity preferences in /plan prompt ("use vanilla HTML, CSS, JavaScript as much as possible"), asking AI to clarify rationale for each technology choice, and adding complexity gates to constitution.md requiring explicit justification for abstractions.

**Vague adjectives force AI guessing.** Imprecise language like "fast response," "user-friendly," "scalable," or "modern UI" requires AI to invent specific meanings. The plan.md command explicitly checks for this: "If clearly ambiguous areas remain (vague adjectives, unresolved critical choices), PAUSE and instruct the user to run /clarify first." Real example: "notification preferences" interpreted differently by PM (per-channel toggles), backend (single on/off switch), frontend (OS integration), and designer (complete user service rebuild). Solution uses the /clarify command to convert adjectives to measurable criteria: "fast" becomes "response <200ms p95 latency," "user-friendly" becomes "max 3 clicks to any feature," "scalable" becomes "support 10k concurrent users with <$5k/month infrastructure cost."

**Missing error state handling creates fragile systems.** Specifications describing only happy paths lead to optimistic code that crashes on edge cases. Plans must explicitly enumerate empty states (no data, no search results, new user experience), error conditions (network failure, invalid input, timeout, service unavailable), rate limits and capacity constraints (API limits, database connection exhaustion), and edge cases (concurrent updates, partial failures, data inconsistencies). The /clarify command should specifically ask: "What should happen when...?" for each major operation.

**Wrong command sequence causes rework.** GitHub Issue #295 documents confusion about /specify, /plan, /tasks ordering. Common mistake: running /plan before /clarify leads to plans built on ambiguous requirements requiring regeneration. Correct sequence: /constitution → /specify → /clarify → /plan → /tasks → /analyze → /implement. Each command assumes previous phases are complete—skipping steps breaks assumptions and forces backtracking.

**Treating first output as final wastes improvement opportunities.** README explicitly states: "It's important to use interaction with Claude Code as an opportunity to clarify and ask questions around the specification - do not treat its first attempt as final." Plan audit prompt enables iteration: "Audit the implementation plan for sequence of tasks with clear dependencies, references to spec sections for each task, over-engineered components, and missing implementation details." If audit reveals issues, regenerate plan with corrections rather than trying to patch problems.

**Context window overload degrades AI performance.** As features grow, AI loses track of earlier decisions. Technical Design Spec Pattern article notes: "Current-generation LLM performance degrades noticeably as context window gets full." Solution: start new chat sessions after task completion, use plan.md as "long term memory" the AI references, aggressively cull completed tasks from context, and update specs at session boundaries to capture learnings.

**No research validation for evolving tech creates outdated plans.** Skipping research.md review for fast-changing frameworks (React, Next.js, .NET Aspire, Kubernetes) risks using outdated patterns or deprecated APIs. Solution prompt: "Go through implementation plan looking for areas that could benefit from additional research as [Framework] is rapidly changing. Update research document with specific versions and spawn parallel research tasks to clarify details." Version-pin dependencies with exact versions, document known issues for that version, and note upgrade paths.

## AI collaboration patterns for effective planning

Successful spec-kit usage treats AI agents as literal-minded collaborators requiring explicit instructions rather than mind-reading search engines.

**Question-driven process surfaces assumptions.** End each prompt with "What questions do you have?" forcing AI to articulate uncertainties rather than guessing. Example: "Generate implementation plan based on spec.md and constitution.md. What questions do you have about technology choices, performance requirements, or integration approaches?" This simple addition shifts AI from presumptive answering to collaborative problem-solving.

**Targeted research prevents broad inefficiency.** Anti-pattern: "Research .NET Aspire in general" produces overwhelming unfocused information. Effective pattern: "Research Aspire's service discovery patterns for our multi-tenant architecture with PostgreSQL database" generates actionable findings. Break research into parallel specific tasks rather than sequential generic investigation. Quote from README: "The research needs to help you solve a specific targeted question."

**Three-pass refinement builds quality incrementally.** Pass 1 baseline generates initial spec from high-level prompt establishing structure and capturing obvious requirements. Pass 2 clarification runs /clarify for structured Q&A, records answers in spec.md Clarifications section, and resolves ambiguities. Pass 3 validation audits against acceptance checklist, verifies traceability, and confirms readiness for /plan. Each pass adds precision without overwhelming initial effort. This iterative approach prevents both rushed incomplete specs and analysis paralysis.

**Constitutional prompting ensures alignment.** Reference constitution.md in every prompt to maintain consistency. Example: "Read constitution.md ensuring this plan follows our SOLID principles, TDD mandate, and security requirements. Document any deviations with explicit justification." From spec-driven.md: "Constitution acts as the architectural DNA of the system" providing continuous governance across all phases.

**Checklist validation provides objective quality gates.** After each phase, run checklist audit preventing premature progression. Example prompt: "Read review and acceptance checklist, check off each item if feature spec meets criteria, leave empty if not. For unchecked items, explain gap and recommend correction." This prevents subjective "looks good enough" assessments with objective criteria.

**Plan audit loop catches issues early.** After /plan generation, audit prompt: "Audit implementation plan for: sequence of tasks with clear dependencies, references to spec sections for each task, over-engineered components, missing implementation details. Propose specific improvements." If audit reveals issues, regenerate plan with corrections rather than patching. Fix at design stage costs minutes; fix during implementation costs hours.

**Parallel task spawning reduces sequential bottlenecks.** For complex research: "Identify list of questions requiring research. For each question, create separate research task so we research all specific questions in parallel." This leverages AI's ability to maintain multiple concurrent investigations without getting confused by breadth. Example: researching authentication library, database migration tool, deployment platform, and monitoring solution simultaneously rather than sequentially.

**Scoped context windows maintain focus.** Start new chat sessions at task boundaries to prevent context overload. Update spec.md at session boundaries capturing learnings and decisions. Use plan.md as external memory the AI reads for context rather than maintaining everything in conversation history. This enables working on large projects without AI performance degradation.

**Complexity detection prevents over-engineering.** Before /implement, prompt: "Review plan for unnecessary complexity. Propose simplifications maintaining functionality while reducing: number of dependencies, abstraction layers, infrastructure components. Justify any complexity you recommend keeping." Constitutional support: add "Simplicity Over Cleverness" principle mandating explicit justification for abstractions.

## Practical templates and quick reference

These copy-paste templates provide starting points for common planning scenarios.

**Minimal Web Application Plan Structure:**

```markdown
Branch: 001-feature-name | Date: 2025-10-12 | Spec: specs/001-feature-name/spec.md

## Technical Context

Primary requirement: [One sentence from spec]
Technical approach: [High-level strategy]

Language/Version: JavaScript ES6+ with Node.js 20
Primary Dependencies: Express 4.18, React 18
Storage: PostgreSQL 15
Testing: Jest, React Testing Library
Target Platform: Modern web browsers, Docker containers
Project Type: web
Performance Goals: <200ms API response p95, <2s page load
Constraints: Must work offline, <512MB memory per container
Scale/Scope: 1000 concurrent users initially, 10k within year 1

## Constitution Check
[Review against constitution.md principles]
- Complies with security requirements: Yes - JWT auth, TLS 1.3
- Follows TDD mandate: Yes - contract tests before implementation
- Respects architectural patterns: Yes - library-first development

## Source Tree Structure
backend/
├── src/
│   ├── models/          # Data entities
│   ├── services/        # Business logic
│   └── api/            # Express routes
└── tests/
    ├── contract/        # API contract tests
    ├── integration/     # Service integration
    └── unit/           # Component tests

frontend/
├── src/
│   ├── components/      # Reusable UI
│   ├── pages/          # Route pages
│   └── services/       # API clients
└── tests/

## Execution Flow
1. ✅ Load spec from specs/001-feature-name/spec.md
2. ✅ Technical Context completed, Project Type: web
3. ✅ Constitution Check: No violations
4. [Phase 0] Generate research.md
5. [Phase 1] Generate data-model.md, contracts/, quickstart.md
6. [Phase 1] Update .github/copilot-instructions.md
7. Re-evaluate Constitution Check
8. Generate Progress Tracking
9. Validate completeness

## Progress Tracking
- Initial Constitution Check: ✅ Complete
- Phase 0 (Research): 🔄 In Progress
- Phase 1 (Design): ⏸️ Pending
- Post-Design Constitution Check: ⏸️ Pending
```

**Data Model Entity Template:**

```markdown
## Entity: [EntityName]

**Purpose**: [What this entity represents in business domain]
**Lifecycle**: [Creation trigger] → [Update conditions] → [Deletion approach]

**Fields:**
| Field | Type | Constraints | Business Rules |
|-------|------|-------------|----------------|
| id | UUID | PK, immutable | Auto-generated |
| name | VARCHAR(255) | NOT NULL, 1-255 chars | User-facing identifier |
| status | ENUM | Required | Values: draft, active, archived |
| created_at | TIMESTAMP | NOT NULL, auto | Immutable after creation |
| updated_at | TIMESTAMP | NOT NULL, auto | Modified on every update |

**Relationships:**
- Belongs to: [ParentEntity] via parent_id
- Has many: [ChildEntity] (cascade delete)
- References: [OtherEntity] (nullify on delete)

**Business Invariants:**
- [Rule that must always be true]
- [Cross-field validation]
- [State transition constraint]

**Indexes:**
- (field_name) BTREE - for [specific query pattern]
- (field1, field2) COMPOSITE - for [join optimization]
```

**API Endpoint Specification Template:**

```yaml
paths:
  /api/v1/resource:
    get:
      summary: List resources with filtering and pagination
      parameters:
        - name: status
          in: query
          schema:
            type: string
            enum: [draft, active, archived]
        - name: page
          in: query
          schema:
            type: integer
            default: 1
            minimum: 1
        - name: limit
          in: query
          schema:
            type: integer
            default: 20
            maximum: 100
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/Resource'
                  pagination:
                    $ref: '#/components/schemas/Pagination'
        '400':
          description: Invalid parameters
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'
        '401':
          description: Unauthorized
      security:
        - bearerAuth: []

components:
  schemas:
    Resource:
      type: object
      required: [id, name, status]
      properties:
        id:
          type: string
          format: uuid
        name:
          type: string
          minLength: 1
          maxLength: 255
        status:
          type: string
          enum: [draft, active, archived]
```

**Performance Specification Template:**

```markdown
## Performance Requirements

### Response Time Targets
- API endpoints: <200ms p95, <500ms p99
- Database queries: <50ms p95
- External API calls: 5s timeout, 3 retries
- Page load (perceived): <2 seconds
- Time to interactive: <5 seconds on 3G

### Throughput Requirements
- Peak traffic: [X] requests/second
- Sustained load: [Y] requests/second
- Batch processing: [Z] items/second
- Background jobs: [N] per hour

### Resource Constraints
- Memory per instance: <512MB
- CPU utilization: <70% average, <90% peak
- Database connections: <50 per instance
- Storage growth: <[X]GB per year

### Caching Strategy
- CDN: Static assets, 24h TTL
- Application: User sessions (30min), API responses (5min)
- Database: Materialized views (hourly refresh)
- Invalidation: Write-through on updates, event-based on critical paths

### Monitoring
- Metrics: Request rate, latency percentiles, error rate, resource utilization
- Alerts: p95 latency >300ms, error rate >1%, CPU >85% for 5min
- APM: [Tool name] with distributed tracing
```

**Pre-Implementation Quality Gate Checklist:**

```markdown
## Specification Validation
- [ ] Review & Acceptance Checklist 100% complete
- [ ] Clarifications documented with session timestamps
- [ ] Edge cases explicitly defined (not auto-generated)
- [ ] No placeholder content or TODO markers
- [ ] User stories have clear acceptance criteria
- [ ] Non-goals explicitly stated

## Plan Validation
- [ ] research.md validates tech stack for specific versions
- [ ] data-model.md defines all entities with relationships
- [ ] contracts/ directory contains all interface specs
- [ ] quickstart.md provides executable setup instructions
- [ ] All implementation details reference spec sections
- [ ] No NEEDS CLARIFICATION markers remain
- [ ] Over-engineering audit completed and passed

## Constitutional Validation
- [ ] Plan aligns with all constitutional principles
- [ ] Security requirements embedded in architecture
- [ ] Testing approach follows TDD mandate
- [ ] Technology choices comply with organizational constraints
- [ ] Deviations documented with explicit justification

## Cross-Artifact Validation
- [ ] /analyze command executed successfully
- [ ] All CRITICAL findings resolved
- [ ] WARNING findings reviewed and accepted
- [ ] Traceability verified: spec → plan → constitution
- [ ] Completeness coverage confirmed

## Approval Gates
- [ ] Stakeholder review of spec.md completed
- [ ] Technical review of plan.md completed
- [ ] Security review of architecture completed
- [ ] Performance targets validated as achievable
- [ ] Ready to generate tasks with /tasks command
```

## Quick reference card for rapid consultation

**Command Sequence:** /constitution → /specify → /clarify → /plan → /tasks → /analyze → /implement

**Plan.md Must Contain:** Technical Context (tech stack, performance goals, constraints), Constitution Check (alignment validation), Source Tree Structure (chosen pattern, unused options removed), Execution Flow (9-step phase sequence), Progress Tracking (phase completion status)

**Phase 0 Output:** research.md (technology validation, version decisions, alternative analysis, security implications)

**Phase 1 Outputs:** data-model.md (entities, relationships, constraints), contracts/ (OpenAPI specs, GraphQL schemas), quickstart.md (setup instructions, validation scenarios), agent context updates (CLAUDE.md, copilot-instructions.md)

**Three Specificity Levels:** Must specify (language, framework, database, API approach, auth mechanism), Should specify (major libraries, testing tools, build systems, state management), Can defer (utility libraries, formatting tools, minor dependencies)

**Lock-in Triggers:** Organizational mandates, compliance requirements, legacy integration, team expertise with deadlines, proven performance requirements

**Keep Flexible When:** Technology rapidly evolving, exploring implementation variants, building libraries, early prototyping

**Critical Anti-Patterns:** God Plan (unreadable 1000+ line plans), premature library selection (unnecessary complexity), vague adjectives (forcing AI guessing), missing error states (fragile happy-path-only code), wrong command sequence (rework from skipped gates)

**Quality Gates:** Pre-plan (constitution exists, spec complete, /clarify run), Post-plan (all artifacts generated, NEEDS CLARIFICATION resolved, over-engineering audit passed), Pre-implement (/analyze run, CRITICAL findings resolved, traceability validated)

**AI Collaboration Patterns:** Question-driven process (end prompts with "What questions?"), targeted research (specific questions, not broad topics), three-pass refinement (baseline → clarify → validate), constitutional prompting (reference principles explicitly), parallel task spawning (concurrent research on independent questions)

**Over-Engineering Detection:** Specification level (no speculative features), Plan level (tech appropriate for scale), Task level (appropriately sized), Human validation (audit before implementation)

**Test Ordering:** Contract definitions → Contract tests → Integration tests → Implementation → Unit tests (TDD mandate enforced through task sequencing)

**Documentation Principles:** Plans stay high-level (architectural decisions only), Details move to separate files (implementation-details/, contracts/, data-model.md), Cross-references maintain navigation (link related documents explicitly), Progress tracking shows status (completed, in-progress, blocked)

## Beyond templates: cultivating planning judgment

The true value of spec-kit's /plan methodology extends beyond templates and checklists to cultivating better planning judgment. Organizations adopting this approach report shifting from reactive "fix it in code review" culture to proactive "get it right in planning" discipline.

**Constitutional governance transforms consistency from aspiration to enforcement.** Rather than hoping developers remember architectural principles, constitutions encode them as AI guardrails. The /analyze command's constitutional compliance checking makes violations visible before implementation begins, when fixing costs minutes rather than sprints. Teams report this shifts architecture conversations from "why didn't you follow our patterns?" after code is written to "how should we encode this pattern?" when establishing principles.

**Explicit ambiguity handling through NEEDS CLARIFICATION markers creates cultural honesty about uncertainty.** Traditional planning often masks uncertainty with vague language or assumptions. Spec-kit's approach makes uncertainty visible and addressable. When AI agents mark unclear requirements explicitly, it removes the stigma from saying "I don't know" and replaces it with systematic resolution. One practitioner noted: "The [NEEDS CLARIFICATION] pattern saved us from entire sprints of rework by catching a different interpretation of 'notification preferences' across PM, backend, frontend, and design."

**Test-driven planning, not just test-driven development, emerges from enforced contract-first approaches.** By requiring contract definitions before implementation files, the methodology forces thinking about interfaces and testability during design rather than as implementation afterthoughts. This shifts quality from "did we test enough?" to "can this design be tested effectively?" The contract tests that must fail before implementation provide objective validation that plans correctly capture requirements.

**Appropriate abstraction levels come from progressive disclosure patterns.** Keeping plan.md high-level while extracting details to separate artifacts creates sustainable documentation that remains navigable as complexity grows. Teams report that this structure makes onboarding new developers faster because they can start with architectural overview in plan.md and drill into specific details only when needed, rather than confronting overwhelming monolithic documents.

**The methodology's greatest strength is making implicit assumptions explicit.** Every aspect—from constitutional principles to performance targets to error handling strategies—must be articulated clearly enough for AI agents to follow. This requirement for explicitness benefits human collaborators as much as AI agents. Architectural decisions that "everyone just knows" become documented rationale that new team members can read. Trade-offs that lived in senior developers' heads become analyzed comparisons in research.md that the entire team can evaluate.

The future of software planning increasingly involves AI collaboration, and Spec-Kit provides a proven framework for that collaboration. By treating specifications as executable source code, plans as structured artifacts that generate implementations, and quality gates as non-negotiable checkpoints, the methodology transforms planning from artistic intuition to engineered discipline. The templates and checklists in this guide provide starting points, but cultivating judgment about when to lock decisions versus maintain flexibility, when plans contain enough detail versus too much, and when to refine specifications versus proceed to implementation—that judgment comes from deliberate practice with the methodology's principles.