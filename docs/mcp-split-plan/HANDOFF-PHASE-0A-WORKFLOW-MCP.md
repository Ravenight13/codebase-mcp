# Phase 0A: Workflow-MCP Foundation - Handoff Prompt

## Copy-Paste This Into New Chat

```
I'm working on splitting a monolithic MCP into two focused MCPs with multi-project support. All planning is complete. I need to execute Phase 0A: Workflow-MCP Foundation.

**Project Context:**
We're creating a brand new workflow-mcp repository from scratch. This will be an AI project management MCP with multi-project workspace support and a generic entity system.

**What We're Doing:**
Phase 0A builds the complete foundation for workflow-mcp: repository setup, FastMCP server boilerplate, database infrastructure, CI/CD pipeline, and development tools. This is a greenfield project - creating everything from scratch.

**Where We Are:**
- ✅ Planning Complete (10 subagents, all reviews done, all critical issues resolved)
- ✅ Phase 0 Final Plan Ready (includes Phase 0 Review with critical fixes)
- 🚧 Phase 0A: Foundation (Starting Now - Brand New Repository)

**Documentation Location:**
All planning docs are in `/Users/cliffclarke/Claude_Code/codebase-mcp/docs/mcp-split-plan/`
(Yes, planning docs live in codebase-mcp repo, but we're creating workflow-mcp repo)

**Key Files:**
- PHASE-0-FOUNDATION.md - Complete Phase 0 implementation guide
- PHASE-0-REVIEW.md - Critical issues and fixes identified
- IMPLEMENTATION-ROADMAP.md - Overall project roadmap
- 02-workflow-mcp/FINAL-IMPLEMENTATION-PLAN.md - Complete implementation plan
- 02-workflow-mcp/constitution.md - 12 constitutional principles

**Your Task:**
Execute Phase 0A following PHASE-0-FOUNDATION.md section "Phase 0A: workflow-mcp Foundation" (lines 22-877), incorporating critical fixes from PHASE-0-REVIEW.md.

**Deliverables:**
1. Repository initialized with proper structure
2. Python packaging configured (pyproject.toml)
3. FastMCP server boilerplate with health check tool
4. Database setup scripts (PostgreSQL + registry schema)
5. CI/CD pipeline (GitHub Actions)
6. Development tools (Makefile, VSCode settings)
7. Documentation (README, CONTRIBUTING)
8. Test infrastructure (pytest, conftest.py)
9. All dependencies installed and verified

**Success Criteria:**
- ✅ Repository initialized with clean git history
- ✅ FastMCP server starts successfully on port 8002
- ✅ Health check tool responds (via MCP protocol)
- ✅ Database setup scripts execute without errors
- ✅ CI/CD pipeline configured and passes
- ✅ All tests passing (1 test: health_check)
- ✅ Documentation complete and accurate

**Timeline:** 25 hours (3-4 days)

**Next Steps:**
1. Read PHASE-0-FOUNDATION.md section "Phase 0A" (lines 22-877)
2. Read PHASE-0-REVIEW.md for critical fixes (especially issues #1, 3-6, 11-12)
3. Create new workflow-mcp repository
4. Execute Phase 0A steps with git micro-commits
5. Verify with Phase 0A Summary checklist

Ready to begin! Please confirm you understand the context and start by creating the repository at /Users/cliffclarke/Claude_Code/workflow-mcp.
```

---

## Additional Context for Claude

### Repository Information

**Repository Path:** `/Users/cliffclarke/Claude_Code/workflow-mcp` (DOES NOT EXIST YET - WILL CREATE)

**Target State:**
- Brand new MCP server with 1 tool (health_check in Phase 0)
- PostgreSQL project_registry database
- FastMCP-based server at port 8002
- Python 3.11+, FastMCP, asyncpg, Pydantic

**Git State:**
- No existing repository
- Will initialize fresh git repo
- First commit: "chore: initialize workflow-mcp repository"

### Critical Fixes Required

**From PHASE-0-REVIEW.md, these issues MUST be addressed:**

1. **Database Setup Script Syntax** (Issue #1)
   - Use HEREDOC for DO $$ blocks to avoid shell escaping issues
   - Example:
   ```bash
   psql -h localhost -U postgres <<'SQL' 2>/dev/null
       DO \$\$
       BEGIN
           IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mcp_user') THEN
               CREATE ROLE mcp_user WITH LOGIN PASSWORD 'your_password_here';
           END IF;
       END
       \$\$;
   SQL
   ```

2. **CI/CD User Creation** (Issue #3)
   - Add idempotency check when creating mcp_user in GitHub Actions
   - Wrap CREATE ROLE in DO $$ block with IF NOT EXISTS

3. **pgvector Extension** (Issue #4)
   - Add pgvector installation to `setup_database.sh`:
   ```bash
   psql -h localhost -U mcp_user -d project_registry -c "CREATE EXTENSION IF NOT EXISTS vector;"
   ```

4. **Pytest Configuration** (Issue #5)
   - Add to `pyproject.toml`:
   ```toml
   [tool.pytest.ini_options]
   asyncio_mode = "auto"
   asyncio_default_fixture_loop_scope = "function"
   ```

5. **Black Formatter Reference** (Issue #11)
   - Remove black reference from `.vscode/settings.json` (use ruff instead)
   - Or add black to dev dependencies

6. **Schema Initialization** (Issue #12)
   - Add SQL execution to `setup_database.sh`:
   ```bash
   psql -h localhost -U mcp_user -d project_registry -f scripts/init_registry_schema.sql
   ```

### Phase 0A Step-by-Step Checklist

**Section 1: Repository Initialization (2 hours)**
- [ ] Create directory: `mkdir -p /Users/cliffclarke/Claude_Code/workflow-mcp`
- [ ] Initialize git: `git init && git checkout -b main`
- [ ] Create directory structure: `mkdir -p {src/workflow_mcp,tests/{unit,integration,performance},docs,.github/workflows}`
- [ ] Create `README.md` - Project overview
- [ ] Create `.gitignore` - Python, IDE, env files
- [ ] Create `LICENSE` - MIT or Apache 2.0
- [ ] Create `.python-version` - 3.11.9
- [ ] Git commit: "chore: initialize workflow-mcp repository"

**Section 2: Project Configuration (3 hours)**
- [ ] Create `pyproject.toml` with dependencies and tools config (FIX Issue #4 - pytest config)
- [ ] Create `.env.template` with all required variables
- [ ] Git commit: "chore: add project configuration and dependencies"

**Section 3: Base Directory Structure (2 hours)**
- [ ] Create source structure: `src/workflow_mcp/{models,services,tools,utils}`
- [ ] Create `__init__.py` files in all packages
- [ ] Create `tests/conftest.py` with shared fixtures
- [ ] Git commit: "chore: create base directory structure"

**Section 4: FastMCP Server Boilerplate (4 hours)**
- [ ] Create `src/workflow_mcp/server.py` with FastMCP server and health_check tool
- [ ] Create `src/workflow_mcp/config.py` with Pydantic settings
- [ ] Create `tests/unit/test_server.py` with health check test
- [ ] Git commit: "feat(server): add FastMCP server boilerplate"
- [ ] Git commit: "test(server): add health check test"

**Section 5: Database Setup Scripts (4 hours)**
- [ ] Create `scripts/setup_database.sh` (FIX Issue #1 - HEREDOC syntax)
- [ ] Create `scripts/init_registry_schema.sql` with registry schema
- [ ] Create `scripts/verify_database.sh` for validation
- [ ] Make scripts executable: `chmod +x scripts/*.sh`
- [ ] Add schema execution to setup script (FIX Issue #12)
- [ ] Add pgvector extension install (FIX Issue #4)
- [ ] Git commit: "chore(db): add database setup and verification scripts"

**Section 6: CI/CD Pipeline Skeleton (3 hours)**
- [ ] Create `.github/workflows/ci.yml` (FIX Issue #3 - idempotent user creation)
- [ ] Create `.github/workflows/performance.yml` for benchmarks
- [ ] Git commit: "ci: add GitHub Actions workflows for testing and benchmarking"

**Section 7: Development Tools Configuration (2 hours)**
- [ ] Create `.vscode/settings.json` (FIX Issue #11 - remove black reference)
- [ ] Create `Makefile` with common targets
- [ ] Git commit: "chore: add development tools configuration"

**Section 8: Documentation (3 hours)**
- [ ] Update `README.md` with installation, usage, status
- [ ] Create `CONTRIBUTING.md` with workflow and standards
- [ ] Git commit: "docs: add README and contributing guide"

**Section 9: Installation and Verification (2 hours)**
- [ ] Create virtual environment: `python -m venv .venv && source .venv/bin/activate`
- [ ] Install package: `pip install -e ".[dev]"`
- [ ] Run database setup: `make db-setup`
- [ ] Verify database: `make db-verify`
- [ ] Run tests: `make test` (should pass 1 test)
- [ ] Run linting: `make lint` (should pass)
- [ ] Start server: `make run` (manual verification)
- [ ] Git commit: "chore: complete Phase 0 setup and verification"
- [ ] Git tag: `v0.1.0-phase0`

### Common Issues to Watch For

**Issue: PostgreSQL Not Running**
- **Symptom:** `pg_isready` fails in setup script
- **Solution (macOS):** `brew services start postgresql@14`
- **Solution (Linux):** `sudo systemctl start postgresql`

**Issue: Permission Denied Creating Database User**
- **Symptom:** Permission denied when running setup_database.sh
- **Solution:** Use postgres superuser: `psql -U postgres` instead of current user

**Issue: Port 8002 Already in Use**
- **Symptom:** Server fails to start with "address already in use"
- **Solution:** Check `.env` and change `MCP_SERVER_PORT` to different port

**Issue: Python 3.11 Not Available**
- **Symptom:** `python -m venv` uses wrong Python version
- **Solution:** Use pyenv: `pyenv install 3.11.9 && pyenv local 3.11.9`

**Issue: pgvector Extension Fails to Install**
- **Symptom:** CREATE EXTENSION vector fails
- **Solution (macOS):** `brew install pgvector`, restart PostgreSQL
- **Solution (Linux):** Install postgresql-{version}-pgvector package

**Issue: Health Check Verification Fails**
- **Symptom:** Cannot test health check with curl
- **Solution:** FastMCP uses MCP protocol (not REST). Need MCP client like Claude Desktop to test, or wait for integration tests.

**Issue: GitHub Actions CI Fails**
- **Symptom:** CI pipeline fails on first push
- **Solution:** Review logs, common issues are PostgreSQL service startup or missing dependencies

**Issue: Mypy Fails on Config.py**
- **Symptom:** mypy reports missing types for pydantic_settings
- **Solution:** Ensure `pydantic-settings>=2.1.0` installed

### Verification Commands

After completing Phase 0A, run these commands to verify:

```bash
# 1. Verify repository structure
ls -la  # Should show: src/, tests/, scripts/, docs/, .github/
git log --oneline  # Should show Phase 0A commits

# 2. Verify Python environment
python --version  # Should show: 3.11.x
pip list | grep -E 'fastmcp|asyncpg|pydantic'  # Should show installed packages

# 3. Verify database
./scripts/verify_database.sh  # Should show all ✅

# 4. Verify tests
pytest tests/ -v  # Should pass 1 test (test_health_check)

# 5. Verify linting
make lint  # Should pass (no errors)

# 6. Verify Makefile targets
make help  # Should display available targets (if help target added)

# 7. Verify git tags
git tag -l  # Should show: v0.1.0-phase0

# 8. Verify file permissions
ls -l scripts/*.sh  # All should be executable (-rwxr-xr-x)
```

### FastMCP Server Expectations

**Health Check Tool:**
- Name: `health_check`
- Parameters: None
- Returns: `HealthResponse(status="healthy", version="0.1.0", database_connected=False)`
- Note: `database_connected=False` is correct for Phase 0 (will be True in Phase 1)

**Server Startup:**
- Port: 8002 (configurable via MCP_SERVER_PORT)
- Transport: SSE (Server-Sent Events)
- Protocol: MCP (Model Context Protocol)
- Logging: File-based (`/tmp/workflow-mcp.log`)

**Testing Health Check:**
- Cannot use `curl` (not a REST endpoint)
- Use MCP client (Claude Desktop) or wait for Phase 1 integration tests
- Or use MCP protocol inspector tools

### What Comes After Phase 0A

**Immediate Next Steps:**
1. Review Phase 0A outputs with project owner
2. Verify all success criteria met
3. Decision point: Proceed with Phase 1 or pause

**Phase 1: Project Management Core (Weeks 1-3)**
- Duration: 120 hours (3 weeks)
- Deliverables:
  - Registry database with projects table
  - `create_project`, `switch_active_project`, `get_active_project`, `list_projects` tools
  - Minimal entity system (register_entity_type, create_entity, query_entities)
  - Connection pool with LRU eviction
  - Database lifecycle with transactional rollback
- Acceptance criteria:
  - Can create commission project with "vendor" entity type
  - Can create TTRPG project with "game_mechanic" entity type
  - Projects completely isolated (different databases)
  - Connection pools evict after 50 projects

### Emergency Rollback

If critical issues occur during Phase 0A:

**Option 1: Full Rollback (Nuclear)**
```bash
cd /Users/cliffclarke/Claude_Code
rm -rf workflow-mcp
# Re-run Phase 0A from scratch
```

**Option 2: Git Rollback (Surgical)**
```bash
cd workflow-mcp
git log --oneline  # Find commit to rollback to
git reset --hard <commit-hash>
# Or reset to specific tag: git reset --hard v0.1.0-phase0
```

**Option 3: Database Rollback Only**
```bash
# Drop databases and re-run setup
psql -U postgres -c "DROP DATABASE IF EXISTS project_registry;"
psql -U postgres -c "DROP DATABASE IF EXISTS test_workflow_mcp;"
./scripts/setup_database.sh
```

### Prerequisites Validation

Before starting Phase 0A, ensure:

- [ ] PostgreSQL 14+ installed and running
- [ ] Python 3.11+ available (check with `python --version`)
- [ ] Git installed and configured
- [ ] Sufficient disk space (>5GB free)
- [ ] Network connectivity (for pip, git)
- [ ] Write permissions in `/Users/cliffclarke/Claude_Code/`
- [ ] No existing `workflow-mcp` directory

### Final Verification Before Phase 1

Before proceeding to Phase 1, ensure:

- [ ] All Phase 0A checklist items completed
- [ ] Health check test passes
- [ ] Database setup scripts work
- [ ] CI/CD pipeline passes
- [ ] Documentation reviewed
- [ ] All commits follow Conventional Commits format
- [ ] Tag `v0.1.0-phase0` created and pushed
- [ ] No uncommitted changes
- [ ] Virtual environment activated
- [ ] Ready to implement Phase 1 features

### Phase 0A Output Structure

Expected final directory structure:

```
workflow-mcp/
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── performance.yml
├── .vscode/
│   └── settings.json
├── docs/
├── scripts/
│   ├── setup_database.sh
│   ├── verify_database.sh
│   └── init_registry_schema.sql
├── src/
│   └── workflow_mcp/
│       ├── __init__.py
│       ├── server.py
│       ├── config.py
│       ├── models/
│       ├── services/
│       ├── tools/
│       └── utils/
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   │   └── test_server.py
│   ├── integration/
│   └── performance/
├── .env.template
├── .gitignore
├── .python-version
├── CONTRIBUTING.md
├── LICENSE
├── Makefile
├── pyproject.toml
└── README.md
```

---

**Status:** Ready for execution
**Last Updated:** 2025-10-11
**Prepared By:** Claude Code Planning System
