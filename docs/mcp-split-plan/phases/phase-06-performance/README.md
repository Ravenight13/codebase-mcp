# Phase 06: Performance Testing

**Phase**: 06 - Performance Testing (Phase 11 from FINAL-IMPLEMENTATION-PLAN.md)
**Duration**: 4-6 hours
**Dependencies**: Phase 05 (documentation complete)
**Status**: Planned

---

## Objective

Validate performance meets targets with NO regression from baseline, and add multi-tenant stress tests.

**Critical**: Performance must match or exceed baseline from Phase 00.

---

## Scope

### What's Included

- **Baseline Comparison**
  - Re-run indexing benchmark (10k files)
  - Re-run search benchmark (100 queries)
  - Compare with Phase 00 baseline
  - Detect any regression

- **Multi-Tenant Stress Tests**
  - Concurrent indexing (3+ projects simultaneously)
  - Concurrent searching (100+ queries across projects)
  - Connection pool stress (MAX_PROJECTS exceeded)
  - Database isolation validation

- **Performance Report**
  - Indexing time comparison (before/after)
  - Search latency comparison (p50/p95/p99)
  - Multi-tenant performance metrics
  - Memory usage analysis
  - Connection pool efficiency

- **Optimization (if needed)**
  - Fix performance regressions
  - Tune connection pool settings
  - Optimize queries

### What's NOT Included

- Feature development (all features complete)
- Documentation updates (already done in Phase 05)

---

## Key Deliverables

1. **Performance Report**: `docs/performance/v2-performance-report.md`
   - Baseline comparison
   - Multi-tenant test results
   - Regression analysis
   - Optimization recommendations

2. **Benchmark Scripts**:
   - `scripts/benchmark_indexing.py` - Measure indexing time
   - `scripts/benchmark_search.py` - Measure search latency
   - `scripts/stress_test_multi_tenant.py` - Multi-tenant stress tests

3. **Test Results**:
   - `docs/performance/indexing-after.json` - Indexing metrics
   - `docs/performance/search-after.json` - Search latency
   - `docs/performance/multi-tenant-stress.json` - Stress test results

---

## Acceptance Criteria

### Performance Targets (From Constitution)

- [ ] **Indexing**: <60 seconds for 10k files (p95)
- [ ] **Search**: <500ms latency (p95)
- [ ] **NO regression**: Within 10% of baseline from Phase 00

### Multi-Tenant Tests

- [ ] Concurrent indexing: 3 projects simultaneously without errors
- [ ] Concurrent searching: 100 queries across projects without errors
- [ ] Connection pool stress: Handles MAX_PROJECTS+5 gracefully
- [ ] Database isolation: No cross-project data leakage
- [ ] LRU eviction: Oldest pools evicted correctly

### Deliverables

- [ ] Performance report created with comparison data
- [ ] All benchmarks run successfully
- [ ] Stress tests pass without errors
- [ ] Any regressions identified and fixed
- [ ] Git commit: "perf: validate performance meets constitutional targets"

---

## Benchmark Procedures

### 1. Indexing Benchmark

```bash
# Generate same test repo as Phase 00 (deterministic seed)
python scripts/generate_test_repo.py \
    --files=10000 \
    --output=/tmp/codebase-benchmark-repo \
    --seed=42

# Benchmark indexing time
time python -m codebase_mcp.tools.search index \
    --project-id=benchmark \
    --repo-path=/tmp/codebase-benchmark-repo

# Expected: <60 seconds (p95)
```

### 2. Search Benchmark

```bash
# Run 100 search queries
python scripts/benchmark_search.py \
    --project-id=benchmark \
    --queries=100 \
    --output=docs/performance/search-after.json

# Expected: p95 <500ms
```

### 3. Multi-Tenant Stress Test

```bash
# Concurrent operations across projects
python scripts/stress_test_multi_tenant.py \
    --projects=15 \
    --concurrent-searches=100 \
    --output=docs/performance/multi-tenant-stress.json

# Should handle gracefully with LRU eviction
```

---

## Performance Report Structure

```markdown
# v2.0 Performance Report

## Executive Summary

- **Indexing**: X seconds (baseline: Y seconds, delta: +/-Z%)
- **Search p95**: X ms (baseline: Y ms, delta: +/-Z%)
- **Multi-tenant**: PASS/FAIL
- **Conclusion**: MEETS/FAILS constitutional targets

## Detailed Results

### Indexing Performance

| Metric | Baseline (Phase 00) | Current (Phase 06) | Delta |
|--------|---------------------|-------------------|-------|
| Mean   | 45.2s               | 46.1s             | +2%   |
| p95    | 52.3s               | 53.8s             | +3%   |
| p99    | 58.1s               | 59.2s             | +2%   |

**Verdict**: PASS (within 10% tolerance)

### Search Performance

| Metric | Baseline (Phase 00) | Current (Phase 06) | Delta |
|--------|---------------------|-------------------|-------|
| p50    | 120ms               | 125ms             | +4%   |
| p95    | 380ms               | 390ms             | +3%   |
| p99    | 480ms               | 495ms             | +3%   |

**Verdict**: PASS (<500ms p95 target met)

### Multi-Tenant Stress Test

- **Concurrent Projects**: 15 (MAX_PROJECTS=10)
- **LRU Evictions**: 5 (expected)
- **Concurrent Searches**: 100 across 15 projects
- **Failures**: 0
- **Isolation Verified**: YES (no cross-contamination)

**Verdict**: PASS

## Optimization Recommendations

1. Consider increasing MAX_CONNECTIONS_PER_POOL for heavy workloads
2. Tune PostgreSQL shared_buffers for better cache hit rate
3. Monitor connection pool hit rate in production

## Conclusion

Performance targets MET. Ready for final validation (Phase 07).
```

---

## Multi-Tenant Isolation Test

```python
async def test_multi_tenant_isolation():
    """Verify no cross-project data leakage under load"""
    # Index different repos in 3 projects
    await asyncio.gather(
        index_repository("project-a", "/tmp/repo-a"),
        index_repository("project-b", "/tmp/repo-b"),
        index_repository("project-c", "/tmp/repo-c"),
    )

    # Search for project-a specific content in project-b
    results_b = await search_code("project-b", "unique-to-project-a")
    assert len(results_b) == 0, "Cross-project data leak detected"

    # Search in correct project
    results_a = await search_code("project-a", "unique-to-project-a")
    assert len(results_a) > 0, "Expected results not found"
```

---

## Connection Pool Stress Test

```python
async def test_connection_pool_stress():
    """Test pool behavior when MAX_PROJECTS exceeded"""
    MAX_PROJECTS = 10
    STRESS_PROJECTS = 15  # Exceed limit by 5

    # Create pools for 15 projects
    pools = []
    for i in range(STRESS_PROJECTS):
        pool = await get_pool(f"project-{i}")
        pools.append(pool)

    # Verify only MAX_PROJECTS active
    stats = await get_pool_stats()
    assert stats["active_pools"] == MAX_PROJECTS
    assert stats["evictions"] == 5  # 5 LRU evictions

    # Verify no errors during eviction
    # All operations should succeed
```

---

## Handling Performance Regressions

### If Regression Detected (>10% slower)

1. **Profile the code**: Use `py-spy` or `cProfile`
   ```bash
   py-spy record -o profile.svg -- python -m codebase_mcp.tools.search index ...
   ```

2. **Check PostgreSQL**: Slow query log
   ```postgresql
   ALTER SYSTEM SET log_min_duration_statement = 500;
   SELECT pg_reload_conf();
   ```

3. **Analyze query plans**: EXPLAIN ANALYZE
   ```postgresql
   EXPLAIN ANALYZE SELECT * FROM code_chunks WHERE ...;
   ```

4. **Optimize**: Based on findings
   - Add missing indexes
   - Tune connection pool settings
   - Adjust PostgreSQL configuration

5. **Re-benchmark**: Verify fix
   ```bash
   python scripts/benchmark_search.py --queries=100
   ```

---

## Rollback Procedure

No rollback needed for testing phase.

If optimization changes cause issues:
```bash
git checkout 002-refactor-pure-search
git reset --hard <commit-before-optimization>
```

---

## Next Phase

After completing Phase 06:
- Verify performance meets all targets
- Document any optimizations made
- Navigate to `../phase-07-final-validation/`
- Ready for final release validation

---

## Related Documentation

- **Phase 11 details**: See `../../_archive/01-codebase-mcp/FINAL-IMPLEMENTATION-PLAN.md` lines 2143-2215
- **Critical Issue C4**: Performance baseline (resolved)
- **Recommendation R4**: Multi-tenant stress tests (implemented)
- **Baseline metrics**: See `../phase-00-preparation/` docs/baseline/

---

**Status**: Planned
**Last Updated**: 2025-10-11
**Estimated Time**: 4-6 hours
