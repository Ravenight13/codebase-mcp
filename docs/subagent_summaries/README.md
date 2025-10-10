# Subagent Summaries Documentation

This directory contains comprehensive documentation of subagent interactions during orchestrated implementation sessions. The documentation captures complete input/output exchanges, technical achievements, and handoff context for project continuity.

## Directory Structure

```
subagent_summaries/
├── README.md                    # This file
├── by_date/                     # Primary storage (chronological)
│   └── YYYY-MM-DD_subagent-type_context-id.md
├── by_specification/            # Cross-references by feature
│   └── ###-feature-name/
│       └── YYYY-MM-DD_subagent-type_task-range.md -> ../../by_date/...
├── by_subagent/                 # Cross-references by subagent type
│   └── subagent-type/
│       └── YYYY-MM-DD_context-id.md -> ../../by_date/...
└── by_project/                  # Cross-references by project (if applicable)
    └── project-name/
        └── YYYY-MM-DD_subagent-type_context-id.md -> ../../by_date/...
```

## File Naming Conventions

### Primary Files (by_date/)

Format: `YYYY-MM-DD_subagent-type_context-id.md`

Examples:
- `2025-10-10_orchestrator_003-database-backed-project.md`
- `2025-10-10_test-automator_T001.md`
- `2025-10-10_python-wizard_T019.md`

### Cross-Reference Symlinks

**by_specification/**: `YYYY-MM-DD_subagent-type_task-range.md`
- Example: `2025-10-10_orchestrator_T001-T036.md`

**by_subagent/**: `YYYY-MM-DD_context-id.md`
- Example: `2025-10-10_003-database-backed-project.md`

**by_project/**: `YYYY-MM-DD_subagent-type_context-id.md`
- Example: `2025-10-10_orchestrator_003-database-backed-project.md`

## Document Structure

Each subagent summary document follows this template:

```markdown
---
subagent_type: "[detected_type]"
specification_id: "[if_found]"
task_id: "[if_found]"
date: "YYYY-MM-DD"
context: "[brief_description]"
---

# [Subagent Type]: [Context Description]

## Original Prompt
[exact_subagent_prompt]

## Complete Response
[full_subagent_response_with_formatting]

## Analysis Summary
- **Technical Scope**: [what_was_accomplished]
- **Files Modified**: [list_if_any]
- **Key Achievements**: [bullet_points]
- **Performance Impact**: [if_measurable]

## Cross-References
- Primary: by_date/[filename]
- Specification: by_specification/[spec_id]/
- Subagent: by_subagent/[type]/
```

## Subagent Types

### Recognized Subagent Types

1. **orchestrator**: Main coordination sessions managing parallel/sequential execution
2. **test-automator**: Contract test and integration test creation
3. **python-wizard**: Python implementation (models, services, utilities)
4. **fastapi-pro**: FastAPI/FastMCP tool implementation
5. **code-specialist**: General code implementation and debugging
6. **testing-specialist**: Test creation and validation
7. **documentation-specialist**: Documentation generation
8. **architecture-specialist**: Architecture design and refactoring
9. **security-auditor**: Security analysis and hardening
10. **database-optimizer**: Database schema and query optimization
11. **performance-analyzer**: Performance profiling and optimization
12. **general-specialist**: Unclassified or multi-domain work

### Type Detection Patterns

- **orchestrator**: Multi-task coordination, parallel execution, phase management
- **test-automator**: pytest, contract tests, integration tests, MCP protocol validation
- **python-wizard**: SQLAlchemy models, async services, Pydantic validation
- **fastapi-pro**: FastMCP decorators, MCP tools, API endpoints
- **code-specialist**: Implementation focus, debugging, refactoring
- **testing-specialist**: Test strategy, coverage analysis, test frameworks

## Usage Examples

### Finding Documentation

**By Date**:
```bash
ls -l docs/subagent_summaries/by_date/2025-10-10*
```

**By Specification**:
```bash
ls -l docs/subagent_summaries/by_specification/003-database-backed-project/
```

**By Subagent Type**:
```bash
ls -l docs/subagent_summaries/by_subagent/orchestrator/
ls -l docs/subagent_summaries/by_subagent/python-wizard/
```

### Reading Full Context

```bash
# Read primary documentation
cat docs/subagent_summaries/by_date/2025-10-10_orchestrator_003-database-backed-project.md

# Or use cross-reference
cat docs/subagent_summaries/by_specification/003-database-backed-project/2025-10-10_orchestrator_T001-T036.md
```

### Searching Across Sessions

```bash
# Find all orchestrator sessions
grep -r "subagent_type: \"orchestrator\"" docs/subagent_summaries/by_date/

# Find sessions for specific specification
grep -r "specification_id: \"003-database-backed-project\"" docs/subagent_summaries/by_date/

# Find sessions by task range
grep -r "T001-T036" docs/subagent_summaries/by_specification/
```

## Documentation Workflow

### 1. Automatic Documentation Capture

When a subagent interaction is documented, the system:
1. Analyzes conversation context for identifiers (spec ID, task ID, subagent type)
2. Selects appropriate template (subagent_summary, project_summary, phase_summary)
3. Generates primary documentation file in `by_date/`
4. Creates cross-reference symlinks in `by_specification/`, `by_subagent/`, `by_project/`
5. Preserves exact prompt and response with original formatting

### 2. Manual Documentation Creation

To document a subagent interaction manually:

```bash
# 1. Create primary file
vim docs/subagent_summaries/by_date/YYYY-MM-DD_subagent-type_context-id.md

# 2. Add frontmatter metadata
# 3. Document prompt, response, analysis

# 4. Create cross-references
cd docs/subagent_summaries
ln -sf ../../by_date/[filename] by_specification/[spec-id]/[filename]
ln -sf ../../by_date/[filename] by_subagent/[type]/[filename]
```

### 3. Session Handoff Process

For multi-session implementations:

1. **Document Current Session**: Create comprehensive summary with:
   - Complete implementation scope
   - File inventory with line counts
   - Remaining work breakdown
   - Known issues and recommendations
   - Next session initialization commands

2. **Create Handoff Checklist**: Include:
   - Context documents to read
   - Validation commands to run
   - Key files to review
   - Orchestrator prompt template

3. **Cross-Reference All Artifacts**: Link to:
   - Specification files (spec.md, plan.md, tasks.md)
   - Implementation files (models, services, tools, tests)
   - Related documentation (implementation summaries, phase reports)

## Existing Documentation

### Orchestrator Sessions

- **2025-10-10**: Database-Backed Project Tracking Implementation (003-database-backed-project)
  - Tasks: T001-T036 (36/52 completed, 69%)
  - Phases: 3.1-3.4 (Contract Tests, Models, Services, MCP Tools)
  - Subagents: test-automator (8), python-wizard (14), fastapi-pro (3)
  - Code: ~21,458 lines, 312 tests, 100% type-safe
  - File: `by_date/2025-10-10_orchestrator_003-database-backed-project.md`

## Best Practices

### For Documentation Creators

1. **Preserve Exact Content**: Never summarize or paraphrase original prompts/responses
2. **Include All Metadata**: Date, specification ID, task ID, subagent type, context
3. **Cross-Reference Thoroughly**: Create all applicable symlinks
4. **Document Achievements**: Technical scope, files modified, key achievements
5. **Capture Handoff Context**: Commands, checklists, next steps for continuity

### For Documentation Consumers

1. **Start with Primary File**: Always read `by_date/` file first (most complete)
2. **Follow Cross-References**: Use symlinks to navigate related sessions
3. **Verify Context**: Check metadata for specification ID, task range, date
4. **Run Validation Commands**: Execute provided commands to verify state
5. **Read Related Artifacts**: Specifications, implementation summaries, task breakdowns

## Maintenance

### Directory Cleanup

Periodically review and archive old documentation:

```bash
# Archive sessions older than 6 months
find docs/subagent_summaries/by_date/ -name "*.md" -mtime +180 -exec mv {} docs/subagent_summaries/archive/ \;

# Update broken symlinks
find docs/subagent_summaries/ -type l ! -exec test -e {} \; -delete
```

### Quality Checks

Run these checks to ensure documentation quality:

```bash
# Verify all primary files have frontmatter
grep -L "^---$" docs/subagent_summaries/by_date/*.md

# Check for missing cross-references
find docs/subagent_summaries/by_date/ -name "*.md" | while read file; do
    basename=$(basename "$file")
    spec_id=$(grep "specification_id:" "$file" | cut -d'"' -f2)
    if [ -n "$spec_id" ]; then
        if [ ! -L "docs/subagent_summaries/by_specification/$spec_id/"* ]; then
            echo "Missing spec cross-ref: $basename"
        fi
    fi
done

# Validate symlinks
find docs/subagent_summaries/ -type l ! -exec test -e {} \; -print
```

---

## Contact & Contribution

This documentation system is designed to capture AI-assisted development sessions for project continuity. For questions or improvements, consult the project constitutional principles and workflow documentation.

**Related Documentation**:
- Project Constitution: `.specify/memory/constitution.md`
- Workflow Guide: `CLAUDE.md`
- Specification Templates: `.specify/templates/`
- Slash Commands: `.claude/commands/`

**Document Version**: 1.0
**Last Updated**: 2025-10-10
**Maintained By**: Documentation Automator Agent
