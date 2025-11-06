# Feature Specification: Docker Support for Codebase MCP Server

**Feature Branch**: `015-add-support-docker`
**Created**: 2025-11-06
**Status**: Draft
**Input**: User description: "Add support for docker, the entire server should be able to run from a docker container"

## User Scenarios & Testing

### User Story 1 - Developer Sets Up Local Environment with Docker Compose (Priority: P1)

A developer clones the repository and wants to start the entire Codebase MCP Server stack (PostgreSQL, Ollama, and the MCP server) with a single command, without needing to install PostgreSQL or Ollama locally.

**Why this priority**: This is the most critical use case. Developers need frictionless local setup to contribute code and run tests. A working docker-compose.yml removes installation complexity and eliminates "works on my machine" problems.

**Independent Test**: Can be fully tested by running `docker-compose up` from the repository root and verifying that all services (PostgreSQL, Ollama, MCP server) start successfully, health checks pass, and the MCP server is ready to accept connections.

**Acceptance Scenarios**:

1. **Given** a fresh clone of the repository, **When** a developer runs `docker-compose up` from the repository root, **Then** all services start in correct dependency order (PostgreSQL first, then Ollama, then MCP server), database migrations run automatically, and the system is ready for testing within 120 seconds.

2. **Given** the docker-compose stack is running, **When** a developer runs the integration test suite, **Then** all tests pass without requiring additional setup steps.

3. **Given** the docker-compose stack is running, **When** a developer makes code changes to the source directory, **Then** the changes are immediately reflected in the running container (hot reload via volume mount).

4. **Given** a developer wants to reset the environment, **When** they run `docker-compose down -v`, **Then** all containers stop and all persistent data (databases, volumes) are removed, allowing a clean restart.

---

### User Story 2 - DevOps Engineer Deploys to Production with Docker (Priority: P2)

A DevOps engineer has production servers and wants to deploy the Codebase MCP Server using Docker containers. They need a production-ready Dockerfile, multi-stage builds for optimization, and deployment documentation.

**Why this priority**: This enables production deployment and is necessary for organizations that use containerized infrastructure. It's secondary to local development but critical for operational use.

**Independent Test**: Can be fully tested by building a production Docker image, running it with environment variables configured, verifying that the server starts, health checks pass, and it can successfully index a small repository and respond to search queries.

**Acceptance Scenarios**:

1. **Given** a production server with Docker installed, **When** a DevOps engineer builds the Docker image using `docker build -t codebase-mcp:latest .` and runs it with required environment variables (REGISTRY_DATABASE_URL, OLLAMA_BASE_URL), **Then** the server starts successfully and is ready to accept indexing and search requests.

2. **Given** the production container is running, **When** a Docker health check script queries the `health://status` MCP resource, **Then** the container reports healthy status within 5 seconds.

3. **Given** the container is running indexing operations, **When** the container receives a SIGTERM signal, **Then** it gracefully shuts down, waiting for in-flight operations to complete (with a timeout) before exiting.

4. **Given** multiple instances of the server are running behind a load balancer, **When** they share the same PostgreSQL and Ollama services, **Then** they work correctly without conflicts or race conditions.

---

### User Story 3 - CI/CD Pipeline Runs Tests in Docker (Priority: P3)

A CI/CD system (GitHub Actions, GitLab CI, etc.) needs to run automated tests without installing system dependencies. Test environments should be isolated and reproducible.

**Why this priority**: This automates testing and validation but is less critical than development and production use cases. It can be implemented after core containerization.

**Independent Test**: Can be fully tested by running a CI pipeline that uses Docker to build the image and execute the test suite, verifying that all tests pass in the containerized environment.

**Acceptance Scenarios**:

1. **Given** a CI/CD pipeline configuration, **When** the pipeline builds the Docker image and runs `docker run ... pytest`, **Then** all unit and integration tests pass consistently.

2. **Given** a Dockerfile, **When** multiple consecutive builds are performed with the same source code, **Then** build time is deterministic and layer caching is efficient (changes to Python code don't require reinstalling dependencies).

---

### Edge Cases

- What happens when PostgreSQL is unavailable during container startup? (Should retry with exponential backoff)
- How does the system handle volume mount permissions on different operating systems (Linux, macOS, Windows with WSL)?
- What happens when Ollama service becomes unavailable after the server has started? (Should handle gracefully with appropriate error messages)
- How are secrets (database passwords) managed in Docker environments? (Should support both environment variables and secret files)
- What is the behavior when the container's `/tmp` space is exhausted during indexing?

## Requirements

### Functional Requirements

- **FR-001**: System MUST provide a Dockerfile that builds a production-ready Docker image containing the MCP server application and all required Python dependencies.

- **FR-002**: Dockerfile MUST use a multi-stage build to optimize image size (final image should be <500 MB).

- **FR-003**: System MUST provide a docker-compose.yml file that orchestrates PostgreSQL 14+, Ollama service, and the MCP server with correct startup order and health checks.

- **FR-004**: docker-compose.yml MUST include volume mounts for PostgreSQL data persistence and source code (for development).

- **FR-005**: System MUST automatically run database migrations (alembic upgrade head) when the container starts, ensuring the schema is always current.

- **FR-006**: Dockerfile MUST expose the server on the expected stdio/MCP transport and include proper signal handling for graceful shutdown (SIGTERM).

- **FR-007**: System MUST support configuration via environment variables (REGISTRY_DATABASE_URL, OLLAMA_BASE_URL, etc.) for both development and production environments.

- **FR-008**: docker-compose.yml MUST include a .env.example file documenting all required and optional environment variables with sensible defaults.

- **FR-009**: System MUST implement health checks for all services (PostgreSQL, Ollama, MCP server) with appropriate timeouts and retry logic. MCP server health checks MUST use the existing `health://status` MCP resource accessed via a custom health check script.

- **FR-010**: Dockerfile MUST use Python 3.12 as the base Python version. Multi-version support (3.11, 3.13) deferred to future enhancements.

- **FR-011**: System MUST provide comprehensive deployment documentation including: setup instructions, configuration guide, troubleshooting, and example deployment scenarios (local, staging, production).

- **FR-012**: System MUST support running tests in Docker using `docker-compose -f docker-compose.test.yml up` without requiring additional setup.

- **FR-013**: Logging MUST use the existing application logging configuration. Container logs are captured via `docker logs` command. No changes to logging format or structure required for this feature.

### Key Entities

- **Docker Image**: A built container image containing the MCP server code and dependencies, tagged with version information.
- **Service Container**: A running instance of the Docker image, isolated with its own filesystem, network namespace, and resource constraints.
- **Compose Network**: A Docker network created by docker-compose connecting PostgreSQL, Ollama, and MCP server services.
- **Volume**: Persistent storage for PostgreSQL data and configuration, allowing data to survive container restarts.
- **Environment Configuration**: Set of variables (REGISTRY_DATABASE_URL, OLLAMA_BASE_URL, etc.) used to customize container behavior without rebuilding.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Developers can start the entire local development stack with `docker-compose up` and have all services running and ready within 120 seconds (includes container startup, database migrations, and health checks).

- **SC-002**: The production Docker image builds successfully and is smaller than 500 MB, demonstrating efficient multi-stage build optimization.

- **SC-003**: A production container starts successfully with only environment variables configured (no additional setup), and health checks pass within 30 seconds.

- **SC-004**: Database migrations run automatically during container startup, and the server is ready to index and search without manual migration steps.

- **SC-005**: The container gracefully shuts down within 10 seconds of receiving SIGTERM, completing in-flight operations where possible.

- **SC-006**: The system works correctly on multiple operating systems and Docker Desktop versions (Linux, macOS, Windows with WSL).

- **SC-007**: CI/CD pipelines can successfully build and test the Docker image as part of automated workflows, with consistent and reproducible results.

- **SC-008**: Developers report reduced setup time by at least 80% compared to manual installation (measured by time-to-ready metric from clone to first test run).

- **SC-009**: The docker-compose configuration supports scaling (e.g., multiple MCP server instances sharing a single PostgreSQL + Ollama stack).

- **SC-010**: All existing functionality (indexing, searching, health checks, metrics) works identically in containerized and non-containerized deployments.

## Clarifications

### Session 2025-11-06

- Q1: Health check mechanism for Docker? → A: Use MCP resources only (`health://status` MCP resource). Docker health checks via custom script that queries the resource. No HTTP endpoint required.
- Q2: Python version strategy? → A: Use Python 3.12 only for initial implementation. Multi-version support deferred to future feature.
- Q3: Observability and logging? → A: Use existing application logging as-is. Container logs captured via `docker logs`. Structured logging and metrics endpoints deferred to future observability feature.

## Assumptions

- Docker and Docker Compose are installed on the user's machine.
- PostgreSQL 14+ and Ollama services are either containerized as part of the docker-compose stack OR available as external services via environment variables.
- The MCP server uses Python 3.12 for container image (existing support for 3.11, 3.12, 3.13 maintained in codebase for non-containerized deployments).
- Signal handling (SIGTERM) for graceful shutdown is implemented or can be added without breaking existing functionality.
- Developers are familiar with basic Docker and docker-compose concepts.
- The project uses environment variables for configuration (already the case with Pydantic BaseSettings).
- Docker health checks access the MCP server via the existing `health://status` resource (not via HTTP endpoint).

## Scope & Boundaries

### In Scope

- Production Dockerfile with multi-stage builds and optimization
- docker-compose.yml for local development (PostgreSQL + Ollama + MCP server)
- Environment variable configuration and .env.example
- Automatic database migration on startup
- Health checks for all services
- Deployment documentation
- Support for Python 3.11, 3.12, 3.13
- Graceful shutdown handling

### Out of Scope

- Kubernetes orchestration (YAML manifests, Helm charts) - future feature
- Container registry setup or image push pipelines - organizational decision
- Production secret management (e.g., HashiCorp Vault integration) - beyond containerization scope
- Reverse proxy configuration (nginx, Traefik) - deployment-specific
- Container runtime security scanning - organizational policy
- Multi-region or geo-distributed deployment - future feature

## Dependencies & Risks

### External Dependencies

- Docker Engine 20.10+
- Docker Compose 2.0+
- PostgreSQL Docker image (official postgres:14+ image from Docker Hub)
- Ollama Docker image (existing ollama/ollama image)

### Technical Risks

- **Platform compatibility**: Docker networking and volume mounting behave differently on Windows (WSL2), macOS (Docker Desktop), and Linux. Risk: Mitigation through testing on all platforms.

- **Database port conflicts**: PostgreSQL container defaults to port 5432. Risk: If users have local PostgreSQL running, port conflicts occur. Mitigation: Document how to change ports in docker-compose.yml.

- **Performance overhead**: Docker containerization adds minimal overhead (~2-5%), but startup time increases due to container initialization. Risk: May exceed 120-second target. Mitigation: Optimize layer caching and parallel service startup.

- **Development volume mount performance**: On macOS, Docker Desktop volume mounts are slower than native filesystem. Risk: Development experience may be degraded. Mitigation: Document optimization techniques (named volumes, docker-sync).

### Project Dependencies

- Alembic migrations must work correctly from container startup scripts.
- Pydantic settings must properly parse environment variables in containerized environment.
- The MCP server must handle SIGTERM gracefully (if not already implemented).
- Health check endpoints must be accessible from Docker health check probes.
