# Spec 013: Config-Based Project Tracking

**Status**: Ready for Implementation
**Version**: 2.0 (Revised)
**Branch**: `013-config-based-project-tracking`
**Estimated Timeline**: 14-20 hours

---

## Overview

Convert codebase-mcp's multi-project tracking from a stateless per-request model to workflow-mcp's proven config-based session architecture using `.codebase-mcp/config.json` files.

---

## Goals

### Primary Goals
1. Enable session-based project tracking with zero cross-contamination
2. Support `.codebase-mcp/config.json` files for local project configuration
3. Provide 50-100x performance improvement for cached config resolution
4. Maintain 100% backward compatibility with explicit `project_id` parameters
5. Support multi-session workflows (multiple Claude Code windows)

### Non-Goals
- Migrating existing projects (no data migration needed - no ingested projects exist)
- Changing database architecture (keeping shared pool + schema isolation)
- Changing per-project database pools (keeping single shared pool)

---

## What & Why

### Current State: Stateless Per-Request
- No session persistence (every call re-resolves project)
- No local config file support
- Dependency on external workflow-mcp server
- 3-tier resolution: explicit param → workflow-mcp → default

**Problem**:
- Users must specify `project_id` on every call or configure workflow-mcp
- No support for local project configuration
- Performance overhead from repeated resolution

### Target State: Config-Based Sessions
- Session persistence with config file caching
- Local `.codebase-mcp/config.json` support
- Optional workflow-mcp integration
- 4-tier resolution: explicit → session config → workflow-mcp → default

**Benefits**:
- Automatic project resolution from working directory
- <1ms cached config lookups (vs 50-100ms workflow-mcp queries)
- Zero cross-contamination between sessions
- Backward compatible (explicit `project_id` still works)

---

## Success Criteria

### Functional
- [ ] `set_working_directory()` tool works with FastMCP Context
- [ ] Config discovery finds `.codebase-mcp/config.json` (up to 20 levels)
- [ ] `index_repository()` and `search_code()` auto-resolve project
- [ ] Multi-session isolation (zero cross-contamination)
- [ ] Graceful fallback when config missing
- [ ] Backward compatible (explicit `project_id` works)

### Performance
- [ ] Config resolution <60ms p95 (uncached)
- [ ] Config resolution <1ms p95 (cached)
- [ ] No regression in indexing/search performance
- [ ] Background cleanup <1s overhead

### Quality
- [ ] 16+ tests passing (integration, performance, edge cases)
- [ ] Async-safe (asyncio.Lock everywhere, no thread-local)
- [ ] Session manager lifecycle (start/stop/cleanup)
- [ ] Documentation (README, ARCHITECTURE.md)

---

## Architecture

### Core Components

1. **SessionContextManager** (`session_context.py`)
   - Store per-session working directories
   - Background cleanup (>24h inactive sessions)
   - FastMCP lifespan integration

2. **Config Discovery** (`discovery.py`)
   - Upward directory search (20 levels max)
   - Edge case handling (symlinks, permissions, deletions)

3. **Config Cache** (`cache.py`)
   - LRU cache with mtime-based invalidation
   - Async-safe (asyncio.Lock)
   - 100-entry capacity

4. **Project Resolution** (`connection.py`)
   - 4-tier resolution chain
   - Graceful fallback (no exceptions)
   - FastMCP Context parameter threading

### Resolution Chain

```
1. Explicit project_id parameter (highest priority)
   ↓ (if None)
2. Session config file (_resolve_project_context)
   ↓ (if None)
3. Query workflow-mcp via MCP client
   ↓ (if fails)
4. Default workspace "default" (always succeeds)
```

---

## Technical Decisions

### Decision 1: Use FastMCP Context (Not Thread-Local) ✅
**Rationale**: FastMCP provides explicit `session_id` via Context, async-safe
**Impact**: Correct session isolation in async context

### Decision 2: All Locks Use asyncio.Lock ✅
**Rationale**: Consistent concurrency primitive, no mixing async/sync
**Impact**: Deadlock-free concurrency

### Decision 3: Explicit Lifecycle Management ✅
**Rationale**: FastMCP lifespan provides startup/shutdown hooks
**Impact**: Production-ready lifecycle, prevents memory leaks

### Decision 4: Graceful Fallback on Session Failure ✅
**Rationale**: Missing config → try workflow-mcp → default
**Impact**: Robust multi-tier resolution, backward compatible

### Decision 5: Keep Shared Connection Pool ✅
**Rationale**: Schema isolation (SET search_path) sufficient
**Impact**: Minimal database layer changes, simpler architecture

---

## Implementation Phases

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| 1. Config Infrastructure | 3-4h | auto_switch module (5 files, ~730 lines) |
| 2. Database Resolution | 3-4h | _resolve_project_context(), updated resolve_project_id() |
| 3. Lifecycle Management | 1-2h | FastMCP lifespan integration |
| 4. MCP Tool | 1h | set_working_directory tool |
| 5. Update MCP Tools | 1h | Thread Context to tools |
| 6. Testing | 4-5h | 16 tests (integration, performance, edge cases) |
| 7. Documentation | 1-2h | README, ARCHITECTURE.md |
| **Total** | **14-20h** | **Production-ready implementation** |

---

## Testing Strategy

### Integration Tests (8 tests)
- End-to-end config resolution workflow
- Multi-session isolation (zero cross-contamination) ← CRITICAL
- Session manager lifecycle
- Concurrent config access (thread-safety)
- Config file deleted during operation
- Symlink resolution failure
- Cache LRU eviction
- Backward compatibility (explicit project_id)

### Performance Tests (4 tests)
- Uncached resolution <60ms p95
- Cached resolution <1ms p95
- Deep directory traversal (20 levels)
- Concurrent resolution (100 clients)

---

## Risk Analysis

All critical risks have been mitigated:
- ✅ Thread-local vs async mismatch → Use FastMCP Context
- ✅ Deadlock from mixed locks → asyncio.Lock consistently
- ✅ Session manager never started → FastMCP lifespan
- ✅ Memory leak → Background cleanup task
- ✅ Context not threaded → Explicit parameter
- ✅ Backward compat break → Graceful fallback

**Overall Risk**: **VERY LOW**

---

## Documentation

### Files Created
1. `specs/013-config-based-project-tracking/spec.md` (this file)
2. `specs/013-config-based-project-tracking/CONVERSION_PLAN.md` (v1.0 - original)
3. `specs/013-config-based-project-tracking/CONVERSION_PLAN_REVISED.md` (v2.0 - approved)

### Files Updated
- `README.md` - Multi-project config workflow
- `ARCHITECTURE.md` - Session isolation architecture (new file)
- Tool docstrings - Updated with resolution chain

---

## Approval Status

**Architectural Review**: ✅ APPROVED (2025-10-16)
- All 7 critical issues resolved
- Async patterns correct
- Lifecycle management production-ready
- Test coverage comprehensive

**Status**: **READY FOR IMPLEMENTATION**

---

## References

- **Implementation Guide**: `specs/013-config-based-project-tracking/CONVERSION_PLAN_REVISED.md`
- **Original Plan**: `specs/013-config-based-project-tracking/CONVERSION_PLAN.md`
- **workflow-mcp Source**: Commit b8f8085 (master branch)
- **workflow-mcp Guide**: `/Users/cliffclarke/Claude_Code/workflow-mcp/CODEBASE_MCP_IMPLEMENTATION_GUIDE.md`

---

## Next Steps

1. Create feature branch: `013-config-based-project-tracking`
2. Implement Phase 1: Config Infrastructure (3-4h)
3. Implement Phase 2: Database Resolution (3-4h)
4. Continue through phases 3-7
5. Validate all 16 tests pass
6. Merge to master

**Start Date**: TBD
**Target Completion**: TBD + 14-20 hours
