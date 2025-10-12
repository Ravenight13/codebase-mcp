# Documentation Index

This directory contains all documentation for the Codebase MCP Server project, organized by category.

## Directory Structure

### Core Documentation

- **[guides/](guides/)** - User guides and tutorials
  - Integration guide, setup guide, tool examples, quick reference
  - FastMCP implementation guide

- **[architecture/](architecture/)** - System architecture documentation
  - ARCHITECTURE.md - Overall system design
  - api.md - API documentation
  - cache-service.md - Cache service architecture
  - logging.md - Logging infrastructure

- **[operations/](operations/)** - Operations and maintenance guides
  - DATABASE_RESET.md - Database reset procedures
  - ROLLBACK.md - Migration rollback procedures
  - troubleshooting.md - Troubleshooting guide

### Development Documentation

- **[implementation-sessions/](implementation-sessions/)** - Development session summaries
  - Dated session logs (e.g., 2025-10-10-*)
  - Feature implementation handoff documents
  - Task-specific implementation summaries (T019, T041, T042)

- **[task-reports/](task-reports/)** - Individual task implementation reports
  - Detailed reports for specific task completions
  - Task verification and testing documentation

- **[specifications/](specifications/)** - Feature specifications and proposals
  - multi-project-workspace-spec.md - Multi-project workspace design

- **[evaluation/](evaluation/)** - System evaluation reports
  - codebase-mcp-evaluation.md - Comprehensive tool evaluation

### Technical Documentation

- **[migrations/](migrations/)** - Database migration documentation
  - 002-schema-refactoring.md - Schema refactoring migration details

- **[testing/](testing/)** - Testing documentation and procedures
  - Testing guides, test prompts, and testing strategies

- **[releases/](releases/)** - Release notes and breaking change documentation
  - v0.4.0-breaking-change.md

- **[status/](status/)** - Project status tracking
  - MCP_SERVER_STATUS.md - Current server status

### Archive

- **[archive/](archive/)** - Historical artifacts and legacy documentation
  - session-artifacts/ - Old session artifacts
  - Preserved for historical reference

- **[subagent_summaries/](subagent_summaries/)** - Subagent execution summaries
  - Organized by date, specification, and subagent type

- **[mcp-split-plan/](mcp-split-plan/)** - MCP server refactoring plan
  - Historical planning documentation for MCP server split
  - Phase-by-phase implementation details

## Quick Links

### For New Users
- [Setup Guide](guides/SETUP_GUIDE.md)
- [Quick Reference](guides/QUICK_REFERENCE.md)
- [Tool Examples](guides/TOOL_EXAMPLES.md)

### For Developers
- [Architecture Overview](architecture/ARCHITECTURE.md)
- [Integration Guide](guides/INTEGRATION_GUIDE.md)
- [FastMCP Implementation Guide](guides/fastmcp-implementation-guide.md)

### For Operations
- [Database Reset](operations/DATABASE_RESET.md)
- [Rollback Procedures](operations/ROLLBACK.md)
- [Troubleshooting](operations/troubleshooting.md)

### For Contributors
- [Testing Guide](testing/README.md)
- [Migration Documentation](migrations/)
- [Recent Implementation Sessions](implementation-sessions/)

## Documentation Maintenance

When adding new documentation:
1. Place it in the appropriate category folder
2. Update this README if creating a new category
3. Use clear, descriptive filenames
4. Include dates for time-sensitive documents (YYYY-MM-DD prefix)
5. Update related documentation when making significant changes

## Finding Documentation

- **By date**: Check `implementation-sessions/` for dated summaries
- **By feature**: Check `specifications/` or relevant feature's `specs/###-feature/` directory
- **By task**: Check `task-reports/` or `implementation-sessions/`
- **By topic**: Use the category folders above
