# Feature Specification: FastMCP Framework Migration

**Feature Branch**: `002-refactor-mcp-server`
**Created**: 2025-10-06
**Status**: Draft
**Input**: User description: "Refactor MCP server to use FastMCP framework and Python SDK for protocol compliance"

## User Scenarios & Testing

### Primary User Story

As an **AI coding assistant** (Claude Desktop, Cursor, etc.), I need the MCP server to maintain protocol compliance and reliability while reducing implementation complexity. The server should use established frameworks (FastMCP and Python SDK) rather than custom protocol handling, ensuring robust integration without breaking existing functionality.

### Acceptance Scenarios

1. **Given** the MCP server is running with FastMCP framework, **When** an AI assistant connects via stdio transport, **Then** all 6 MCP tools (search_code, index_repository, create_task, get_task, list_tasks, update_task) respond correctly with protocol-compliant messages

2. **Given** the FastMCP server is integrated with Claude Desktop, **When** a user requests "search for authentication code", **Then** the search returns semantic results in under 500ms with properly formatted MCP responses

3. **Given** the refactored server uses FastMCP decorators, **When** a tool is invoked with invalid parameters, **Then** Pydantic validation catches the error and returns a clear, field-level error message to the client

4. **Given** the server uses automatic schema generation from type hints, **When** the server starts, **Then** tool schemas are automatically generated and match the expected MCP protocol format

5. **Given** the migration is complete, **When** running the existing test suite, **Then** all protocol compliance tests, integration tests, and performance tests pass without modification

### Edge Cases

- What happens when FastMCP's context injection is used for logging and a log file becomes unavailable?
- How does the system handle transport-level errors when switching between stdio and SSE transports?
- If FastMCP's automatic schema generation conflicts with existing Pydantic models, use FastMCP's schema override mechanisms to manually define conflicting schemas
- When FastMCP's decorator registration fails due to type hint issues, the server refuses to start and logs the error with fix instructions (fail-fast strategy)

## Clarifications

### Session 2025-10-06

- Q: What is the preferred migration strategy? → A: Full cutover (migrate all tools, deploy complete refactored server)
- Q: What is the rollback strategy if the migration fails in production? → A: Revert to previous version (maintain old implementation in parallel during transition)
- Q: What should happen when FastMCP decorator registration fails at server startup? → A: Fail fast (server refuses to start, logs error with fix instructions)
- Q: What should happen if FastMCP's automatic schema generation conflicts with existing Pydantic models? → A: Override with FastMCP
- Q: How long should the previous implementation be maintained for potential rollback? → A: Don't keep it active, kill immediately to upgrade (rollback via deployment reversion, not parallel instances)

## Requirements

### Functional Requirements

- **FR-001**: System MUST migrate all MCP tool handlers to use FastMCP's @mcp.tool() decorator pattern
- **FR-002**: System MUST use official MCP Python SDK for protocol compliance validation
- **FR-003**: System MUST leverage FastMCP's automatic schema generation from type hints and docstrings
- **FR-004**: System MUST use FastMCP's context injection for logging, progress reporting, and resource access
- **FR-005**: System MUST maintain backward compatibility with existing Claude Desktop configuration
- **FR-006**: System MUST preserve all 6 existing MCP tools without breaking their functionality
- **FR-007**: System MUST continue logging to `/tmp/codebase-mcp.log` without stdout/stderr pollution
- **FR-008**: System MUST pass all existing protocol compliance, integration, and performance tests
- **FR-009**: System MUST support both stdio and SSE transports via FastMCP's transport abstraction
- **FR-010**: System MUST eliminate custom protocol handling code in favor of FastMCP's high-level API
- **FR-011**: Migration MUST complete all tool refactoring before deployment (full cutover strategy, no partial deployments)
- **FR-012**: System MUST support rollback via deployment reversion (version control), not parallel running instances
- **FR-013**: Old server instance MUST be terminated immediately during upgrade (no parallel operation)
- **FR-014**: System MUST fail fast at startup if FastMCP decorator registration fails, refusing to start and logging actionable error messages with fix instructions
- **FR-015**: System MUST use FastMCP's schema override mechanisms to manually define schemas where automatic generation conflicts with existing Pydantic models

### Non-Functional Requirements

- **NFR-001**: Performance MUST remain unchanged (60s indexing for 10k files, 500ms p95 search latency)
- **NFR-002**: Type safety MUST be maintained with mypy --strict compliance
- **NFR-003**: Error handling MUST continue to provide specific, actionable error messages
- **NFR-004**: Migration MUST not introduce new dependencies beyond FastMCP and official Python SDK
- **NFR-005**: Code complexity MUST be reduced through framework abstractions

### Key Entities

- **MCP Server**: The refactored server instance using FastMCP framework as the foundation
- **Tool Handler**: Functions decorated with @mcp.tool() that implement MCP tool logic
- **Transport Layer**: FastMCP's abstraction handling stdio/SSE protocol communication
- **Context Object**: FastMCP's built-in context providing logging, sampling, and resource access
- **Schema Definition**: Automatically generated from type hints and docstrings

## Success Metrics

- **Zero** protocol violations in integration tests after migration
- **All** 6 MCP tools function identically to pre-migration behavior
- **100%** of existing tests pass without modification
- **Reduced** lines of protocol handling code by eliminating custom implementations
- **Maintained** performance guarantees (60s/500ms targets)

## Dependencies & Assumptions

### Dependencies
- FastMCP framework (https://github.com/jlowin/fastmcp) must be installed and compatible with Python 3.11+
- Official MCP Python SDK (https://github.com/modelcontextprotocol/python-sdk) must be compatible with FastMCP
- Existing Pydantic models must work with FastMCP's automatic schema generation
- Current PostgreSQL/Ollama infrastructure remains unchanged

### Assumptions
- FastMCP supports async operations required for database and embedding calls
- FastMCP's transport abstraction is compatible with current Claude Desktop configuration
- Migration will use full cutover strategy: all tools refactored in codebase before deployment
- FastMCP's logging context can integrate with existing structured logging to `/tmp/codebase-mcp.log`
- Rollback capability relies on version control/deployment tooling, not parallel server instances
- Old server instance is terminated immediately during upgrade (no graceful transition period)

## Out of Scope

- Adding new MCP tools or features (focus is refactoring existing implementation)
- Changing database schema or data models
- Modifying Ollama embedding integration
- Altering performance targets or guarantees
- Changing Claude Desktop configuration format (must remain backward compatible)

## Review & Acceptance Checklist

### Content Quality
- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

### Requirement Completeness
- [ ] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Execution Status

- [x] User description parsed
- [x] Key concepts extracted (framework migration, protocol compliance, backward compatibility)
- [x] Ambiguities marked (migration strategy)
- [x] User scenarios defined
- [x] Requirements generated
- [x] Entities identified
- [x] Review checklist passed (1 clarification pending)
