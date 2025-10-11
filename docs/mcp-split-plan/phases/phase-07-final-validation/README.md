# Phase 07: Final Validation

**Phase**: 07 - Final Validation (Phase 12 from FINAL-IMPLEMENTATION-PLAN.md)
**Duration**: 2-3 hours
**Dependencies**: Phase 06 (performance validated)
**Status**: Planned

---

## Objective

Comprehensive validation before release: MCP protocol compliance, security audit, and release checklist.

**Final Gate**: All criteria must pass before v2.0 release.

---

## Scope

### What's Included

- **MCP Protocol Compliance**
  - Test with `mcp-inspector`
  - Verify tool schemas
  - Validate SSE transport
  - Check error handling

- **Security Audit**
  - SQL injection tests
  - Input validation tests
  - Dependency vulnerability scan
  - Secrets detection

- **Type Safety**
  - `mypy --strict` passes
  - No type: ignore comments
  - Pydantic models validated

- **Test Coverage**
  - >80% code coverage
  - All critical paths tested
  - Integration tests pass

- **Release Checklist**
  - Version bumped to 2.0.0
  - Changelog updated
  - Migration guide reviewed
  - Git tags created

### What's NOT Included

- New features (all features complete)
- Performance optimization (done in Phase 06)

---

## Key Deliverables

1. **MCP Inspector Report**: `docs/validation/mcp-inspector-report.md`
   - Protocol compliance results
   - Tool schema validation
   - Transport verification

2. **Security Audit Report**: `docs/validation/security-audit.md`
   - Vulnerability scan results
   - Input validation tests
   - SQL injection test results

3. **Coverage Report**: `docs/validation/coverage-report.html`
   - Code coverage metrics
   - Uncovered lines analysis

4. **Release Checklist**: `docs/validation/release-checklist.md`
   - All pre-release tasks checked

---

## Acceptance Criteria

### MCP Protocol Compliance

- [ ] `mcp-inspector` passes all tests
- [ ] Tool schemas valid (index_repository, search_code)
- [ ] SSE transport working correctly
- [ ] Error responses follow MCP spec
- [ ] Tool discovery working

### Security

- [ ] SQL injection tests pass (10+ test cases)
- [ ] Input validation enforced (project_id, repo_path)
- [ ] No hardcoded secrets in codebase
- [ ] Dependency vulnerabilities: 0 critical, 0 high
- [ ] `bandit` security linter passes

### Type Safety

- [ ] `mypy --strict src/` passes with 0 errors
- [ ] No `type: ignore` comments (or justified)
- [ ] All Pydantic models validated

### Test Coverage

- [ ] Overall coverage >80%
- [ ] Critical paths 100% covered (search, index)
- [ ] Integration tests pass (multi-project, workflow-mcp)
- [ ] All tests green in CI/CD

### Release Readiness

- [ ] Version bumped to 2.0.0 in pyproject.toml
- [ ] CHANGELOG.md updated with all changes
- [ ] Migration guide reviewed and tested
- [ ] README.md accurate
- [ ] Git tag created: `v2.0.0`
- [ ] Release notes drafted

---

## MCP Inspector Validation

### Install mcp-inspector

```bash
npm install -g @modelcontextprotocol/inspector
```

### Run Inspector

```bash
# Start codebase-mcp server
python -m codebase_mcp.server &
SERVER_PID=$!

# Run inspector
mcp-inspector http://localhost:3000/mcp/codebase-mcp

# Expected output:
# ✓ Server responding
# ✓ Tool discovery working
# ✓ Tool schemas valid
# ✓ SSE transport working
# ✓ Error handling compliant

# Stop server
kill $SERVER_PID
```

### Expected Tool Schemas

```json
{
  "tools": [
    {
      "name": "index_repository",
      "description": "Index a code repository for semantic search",
      "inputSchema": {
        "type": "object",
        "properties": {
          "project_id": {
            "type": "string",
            "pattern": "^[a-z0-9-]{1,50}$",
            "default": "default"
          },
          "repo_path": {
            "type": "string"
          }
        },
        "required": ["repo_path"]
      }
    },
    {
      "name": "search_code",
      "description": "Search code using semantic similarity",
      "inputSchema": {
        "type": "object",
        "properties": {
          "project_id": {
            "type": "string",
            "pattern": "^[a-z0-9-]{1,50}$",
            "default": "default"
          },
          "query": {
            "type": "string"
          },
          "limit": {
            "type": "integer",
            "default": 10
          }
        },
        "required": ["query"]
      }
    }
  ]
}
```

---

## Security Audit

### SQL Injection Tests

```python
# Test malicious project_ids
@pytest.mark.parametrize("malicious_id", [
    "project'; DROP TABLE repositories; --",
    "project\"; DELETE FROM code_chunks; --",
    "project' OR '1'='1",
    "../../../etc/passwd",
    "project\x00null",
])
async def test_sql_injection_blocked(malicious_id):
    """Verify SQL injection attempts rejected"""
    with pytest.raises(ValueError, match="Invalid project_id"):
        await index_repository(project_id=malicious_id, repo_path="/tmp/test")
```

### Input Validation Tests

```python
async def test_project_id_validation():
    """Test project_id validation rules"""
    # Valid IDs
    assert ProjectID(value="default")
    assert ProjectID(value="my-project")
    assert ProjectID(value="a")

    # Invalid IDs
    with pytest.raises(ValidationError):
        ProjectID(value="My-Project")  # uppercase
    with pytest.raises(ValidationError):
        ProjectID(value="my_project")  # underscore
    with pytest.raises(ValidationError):
        ProjectID(value="-myproject")  # starts with hyphen
```

### Dependency Vulnerability Scan

```bash
# Scan dependencies
pip install safety
safety check --json > docs/validation/safety-report.json

# Expected: 0 critical, 0 high vulnerabilities
```

### Secrets Detection

```bash
# Scan for hardcoded secrets
pip install detect-secrets
detect-secrets scan > .secrets.baseline

# Review any findings
detect-secrets audit .secrets.baseline
```

### Bandit Security Linter

```bash
# Run Bandit
bandit -r src/ -f json -o docs/validation/bandit-report.json

# Expected: 0 high severity issues
```

---

## Type Safety Validation

```bash
# Run mypy with strict mode
mypy --strict src/ > docs/validation/mypy-report.txt

# Expected: Success: no issues found in N source files
```

---

## Test Coverage

```bash
# Run tests with coverage
pytest --cov=src --cov-report=html --cov-report=term

# Expected output:
# Name                                    Stmts   Miss  Cover
# -----------------------------------------------------------
# src/codebase_mcp/__init__.py                5      0   100%
# src/codebase_mcp/server.py                 50      2    96%
# src/codebase_mcp/tools/index.py           120      8    93%
# src/codebase_mcp/tools/search.py          110      5    95%
# src/codebase_mcp/database/pool.py          80      3    96%
# -----------------------------------------------------------
# TOTAL                                    1800    150    92%

# Open HTML report
open htmlcov/index.html
```

---

## Release Checklist

### Pre-Release Tasks

- [ ] All tests passing (unit, integration, e2e)
- [ ] Performance targets met (Phase 06)
- [ ] MCP protocol compliance (mcp-inspector)
- [ ] Security audit complete (0 critical vulnerabilities)
- [ ] Type safety verified (mypy --strict)
- [ ] Coverage >80%
- [ ] Documentation complete and accurate
- [ ] Migration guide tested

### Version Management

- [ ] Update `pyproject.toml`: version = "2.0.0"
- [ ] Update `src/codebase_mcp/__init__.py`: __version__ = "2.0.0"
- [ ] Create CHANGELOG.md entry for v2.0.0

### Git Tagging

```bash
# Create annotated tag
git tag -a v2.0.0 -m "Release v2.0.0: Pure semantic search with multi-project support"

# Push tag
git push origin v2.0.0
```

### Release Notes

Draft release notes:
- Summary of changes (16 → 2 tools, multi-project support)
- Breaking changes (migration guide link)
- Performance improvements
- Bug fixes
- Known issues (if any)

---

## CHANGELOG.md Entry

```markdown
## [2.0.0] - 2025-10-11

### 🚀 Major Changes

- **BREAKING**: Reduced from 16 MCP tools to 2 (semantic search only)
- **BREAKING**: Removed work item, task, vendor, deployment management
- **NEW**: Multi-project support with database-per-project architecture
- **NEW**: Optional workflow-mcp integration for active project detection

### 🎯 Features

- Added `project_id` parameter to `index_repository` and `search_code`
- Implemented per-project connection pooling with LRU eviction
- Added database-per-project isolation (format: `codebase_<project_id>`)
- Added project_id validation (`^[a-z0-9-]{1,50}$`)

### ⚡ Performance

- Maintained performance targets: <60s indexing, <500ms search (p95)
- Added multi-tenant stress testing
- Connection pool optimization

### 🔒 Security

- SQL injection prevention via project_id validation
- Input sanitization for all parameters
- Dependency vulnerability scan: 0 critical

### 📚 Documentation

- Complete migration guide (v1.x → v2.0)
- Multi-project architecture documentation
- Configuration guide for production deployments

### 🔧 Internal

- 60% code reduction (~4,500 → ~1,800 lines)
- Database schema refactored (9 tables removed)
- Comprehensive test suite (>80% coverage)
- mypy --strict compliance

### 📦 Migration

See [Migration Guide](docs/migration/v1-to-v2.md) for upgrade instructions.

### ⚠️ Breaking Changes

- 14 MCP tools removed (work items, tasks, vendors, deployments)
- Database schema change (9 tables dropped, project_id added)
- API change (project_id parameter added to tools)
```

---

## Rollback Procedure

If final validation fails:
```bash
# Do NOT create v2.0.0 tag
# Return to Phase 06 to fix issues
git checkout 002-refactor-pure-search

# Fix identified issues
# Re-run validation
```

---

## Next Steps

After Phase 07 completion:
- **Merge to main**: `git checkout main && git merge 002-refactor-pure-search`
- **Push tags**: `git push origin main v2.0.0`
- **Publish release**: Create GitHub release with notes
- **Deploy**: Update production deployments
- **Announce**: Notify users of v2.0 release

---

## Related Documentation

- **Phase 12 details**: See `../../_archive/01-codebase-mcp/FINAL-IMPLEMENTATION-PLAN.md` lines 2216-2651
- **Release strategy**: See `../../_archive/shared-architecture/03-orchestration/git-strategy.md`
- **Testing strategy**: See `../../_archive/shared-architecture/03-orchestration/testing-strategy.md`

---

**Status**: Planned
**Last Updated**: 2025-10-11
**Estimated Time**: 2-3 hours

---

**🎉 After Phase 07: Refactoring COMPLETE! Ready for v2.0 release! 🚀**
