# Next Task: MCP Best Practices Enhancements

**Priority**: High
**Status**: Planned (after background indexing completes)
**Estimated Time**: 2.5-3 days
**Branch**: `015-mcp-best-practices-simplified`

## Overview

Implement 4 MCP best practice enhancements based on comprehensive mcp-builder skill evaluation.

- **23 tasks** (down from 57 in original plan)
- **~800 LOC** (down from ~2000 LOC)
- **60% code reduction** with full functionality maintained
- **All 11 constitutional principles** validated

## Key Enhancements

### 1. Tool Annotations (2 hours)
- Add MCP hints to all 3 tools for LLM optimization
- `readOnlyHint`, `idempotentHint`, `openWorldHint`
- Immediate benefit: Better LLM tool selection

### 2. Concise Mode (8 hours)
- Add `detail_level` parameter ("detailed" | "concise")
- 50-80% token reduction in concise mode
- Simple dictionary unpacking implementation

### 3. Character Limits (4 hours)
- 100K character limit (~25K tokens)
- Direct measurement: `len(json.dumps(response))`
- Simple truncation with `truncated` flag

### 4. Evaluation Suite (4 hours)
- 5 pytest questions using actual codebase
- Validates all tool capabilities
- Standard pytest (no custom runner)

## Documentation Created

All documentation is in `/docs/plans/`:

- ✅ `evaluation-suite.md` - 10-question evaluation plan (18KB)
- ✅ `response-format-options.md` - JSON/Markdown formatting plan (24KB)
- ✅ `character-limits-truncation.md` - Truncation strategy (21KB)
- ✅ `tool-annotations.md` - MCP hints plan (20KB)
- ✅ `implementation-tasks.md` - Original 57-task list
- ✅ `implementation-tasks-simplified.md` - **23-task simplified list** ⭐
- ✅ `architecture-review.md` - 60% simplification rationale

## Implementation Order

### Phase 1: Quick Wins (0.5 days, parallel)
- T001-T003: Tool annotations

### Phase 2: Core Features (1.5 days, sequential)
- T004-T008: Concise mode formatting
- T009-T012: Character limits & truncation

### Phase 3: Validation (0.5 days, can parallel with Phase 2)
- T013-T015: Evaluation suite (5 pytest tests)

### Phase 4: Integration (0.5 days, sequential)
- T016-T018: Integration testing
- T019-T023: Documentation & git

## Success Criteria

- ✅ All 23 tasks complete
- ✅ Test coverage >95%
- ✅ mypy --strict 100% compliance
- ✅ Evaluation suite 5/5 pass rate
- ✅ Performance overhead <10ms
- ✅ No regressions
- ✅ Zero constitutional violations

## Why Simplified?

The architecture review identified 60% code reduction opportunity:

1. **No formatting module** - Use Pydantic + dictionary unpacking (100 LOC vs 800)
2. **Direct measurement** - Use `json.dumps()` length (150 LOC vs 600)
3. **Standard pytest** - No custom XML runner (200 LOC vs 600)

**Result**: Same functionality, 60% less code, 65% faster implementation.

## Quick Start

When ready to implement:

```bash
# Create feature branch
git checkout -b 015-mcp-best-practices-simplified

# Start with Phase 1 (2 hours)
# See /docs/plans/implementation-tasks-simplified.md for full task list

# Follow micro-commit strategy
# Commit after each task completion
```

## References

- **MCP Evaluation Report**: In conversation history (8.1/10 score)
- **Task List**: `/docs/plans/implementation-tasks-simplified.md`
- **Architecture Review**: `/docs/plans/architecture-review.md`
- **Original Plans**: All 4 feature plans in `/docs/plans/`

---

*Created after MCP best practices evaluation and architectural review*
*Ready to start immediately after background indexing work completes*
