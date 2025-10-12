# Quickstart: Remove Non-Search MCP Tools Validation

**Feature**: 007-remove-non-search
**Purpose**: Validate 4-phase atomic deletion workflow with intermediate breakage tolerance

## Overview

This quickstart guides validation of removing 14 non-search MCP tools while preserving semantic search functionality. The workflow uses 4 atomic commits with intermediate breakage, validating only at baseline and final states.

## Prerequisites

```bash
# Ensure feature branch
git branch --show-current  # Should show: 007-remove-non-search

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -e ".[dev]"
```

## Validation Workflow

### Phase 1: Pre-Deletion Baseline (REQUIRED FIRST)

**Purpose**: Establish passing test baseline before any deletions

#### Scenario 1.1: Run Search Integration Tests

```bash
pytest tests/integration/test_search.py -v
```

**Expected Output**:
```
tests/integration/test_search.py::test_search_basic PASSED
tests/integration/test_search.py::test_search_with_filters PASSED
tests/integration/test_search.py::test_search_embeddings PASSED
...
============ X passed in Y.YYs ============
```

**Pass Criteria**:
- ✅ All search tests pass
- ✅ Zero test failures
- ✅ Record exact passing test count (use in Phase 5)

#### Scenario 1.2: Record Baseline Metrics

```bash
# Count passing tests
pytest tests/integration/test_search.py -v | grep "passed"

# Example output: "15 passed in 2.34s"
# Record this number for final validation
```

**Pass Criteria**:
- ✅ Record passing test count: _______ (fill in actual number)

#### Scenario 1.3: Verify Current Tool Count

```bash
# Start server in background
python -m src.codebase_mcp.server &
SERVER_PID=$!

# Wait for startup
sleep 2

# Check tool registration in logs
# (or inspect server startup output)

# Cleanup
kill $SERVER_PID
```

**Expected Output**:
```
Registered 16 MCP tools:
- index_repository
- search_code
- get_project_configuration
- update_project_configuration
- query_vendor_status
- update_vendor_status
- create_vendor
- get_task
- list_tasks
- create_task
- update_task
- record_deployment
- create_work_item
- update_work_item
- query_work_item
- list_work_items
```

**Pass Criteria**:
- ✅ Server starts successfully
- ✅ 16 tools registered
- ✅ index_repository and search_code present

**Checkpoint**: Do not proceed until all Phase 1 scenarios pass

---

### Phase 2: Sub-Phase 1 - Delete Tool Files

**Purpose**: Remove tool function files (intermediate breakage acceptable)

#### Scenario 2.1: Delete Tool Files

```bash
# Delete 4 non-search tool files
rm src/codebase_mcp/tools/project_config_tools.py
rm src/codebase_mcp/tools/vendor_tools.py
rm src/codebase_mcp/tools/task_tools.py
rm src/codebase_mcp/tools/work_item_tools.py

# Verify deletions
ls src/codebase_mcp/tools/
```

**Expected Output**:
```
__init__.py
indexing_tools.py
search_tools.py
```

**Pass Criteria**:
- ✅ Only 3 files remain in tools/ directory
- ✅ index_repository and search_code tool files preserved

#### Scenario 2.2: Commit Atomic Change

```bash
git add src/codebase_mcp/tools/
git commit -m "chore(tools): delete 14 non-search MCP tools

Remove project config, vendor, task, and work item tool files.
Server will have import errors (intermediate breakage acceptable).

Related: #007-remove-non-search Sub-Phase 1"
```

**Pass Criteria**:
- ✅ Commit created successfully
- ✅ 4 files deleted in commit

**Note**: Import errors and test failures are EXPECTED and ACCEPTABLE at this stage.

---

### Phase 3: Sub-Phase 2 - Delete Database Operations

**Purpose**: Remove models and service layer code (intermediate breakage acceptable)

#### Scenario 3.1: Delete Model Files

```bash
# Delete non-search model files
rm src/codebase_mcp/models/project_config.py
rm src/codebase_mcp/models/vendor.py
rm src/codebase_mcp/models/task.py
rm src/codebase_mcp/models/work_item.py
rm src/codebase_mcp/models/deployment.py

# Verify remaining models
ls src/codebase_mcp/models/
```

**Expected Output**:
```
__init__.py
repository.py
code_chunk.py
```

**Pass Criteria**:
- ✅ Only repository and code_chunk models remain

#### Scenario 3.2: Delete Service Files

```bash
# Delete non-search service files
rm src/codebase_mcp/services/project_config_service.py
rm src/codebase_mcp/services/vendor_service.py
rm src/codebase_mcp/services/task_service.py
rm src/codebase_mcp/services/work_item_service.py
rm src/codebase_mcp/services/deployment_service.py

# Verify remaining services
ls src/codebase_mcp/services/
```

**Expected Output**:
```
__init__.py
indexing_service.py
search_service.py
embedding_service.py
```

**Pass Criteria**:
- ✅ Only search-related services remain

#### Scenario 3.3: Commit Atomic Change

```bash
git add src/codebase_mcp/models/ src/codebase_mcp/services/
git commit -m "chore(models,services): delete non-search database operations

Remove project config, vendor, task, work item, and deployment models/services.
Server will have import errors (intermediate breakage acceptable).

Related: #007-remove-non-search Sub-Phase 2"
```

**Pass Criteria**:
- ✅ Commit created successfully
- ✅ 10 files deleted in commit (5 models + 5 services)

**Note**: Import errors and test failures are EXPECTED and ACCEPTABLE at this stage.

---

### Phase 4: Sub-Phase 3 - Update Server Registration

**Purpose**: Clean up server.py and verify 2-tool registration (intermediate breakage acceptable)

#### Scenario 4.1: Verify Server Registration Code

```bash
# Inspect server.py tool registration
grep -A 5 "mcp.tool()" src/codebase_mcp/server.py
```

**Expected Output**:
```python
@mcp.tool()
async def index_repository(...):
    ...

@mcp.tool()
async def search_code(...):
    ...
```

**Pass Criteria**:
- ✅ Only index_repository and search_code decorated with @mcp.tool()
- ✅ No decorators for deleted tools

#### Scenario 4.2: Clean Up Imports

```bash
# Review imports in server.py
head -n 30 src/codebase_mcp/server.py | grep "^from\|^import"
```

**Manual Task**:
- Remove imports for deleted tool modules
- Remove imports for deleted model/service modules
- Keep: indexing_tools, search_tools, indexing_service, search_service, embedding_service

**Pass Criteria**:
- ✅ No imports for deleted modules
- ✅ Only search-related imports remain

#### Scenario 4.3: Commit Atomic Change

```bash
git add src/codebase_mcp/server.py
git commit -m "chore(server): verify 2-tool registration and cleanup imports

Remove imports for deleted non-search modules.
Server will have remaining import errors (intermediate breakage acceptable).

Related: #007-remove-non-search Sub-Phase 3"
```

**Pass Criteria**:
- ✅ Commit created successfully
- ✅ server.py updated in commit

**Note**: Import errors and test failures are EXPECTED and ACCEPTABLE at this stage.

---

### Phase 5: Sub-Phase 4 - Delete Tests and Final Validation (REQUIRED LAST)

**Purpose**: Complete deletion and verify all success criteria pass

#### Scenario 5.1: Delete Non-Search Test Files

```bash
# Delete non-search test files
rm tests/integration/test_project_config.py
rm tests/integration/test_vendor.py
rm tests/integration/test_task.py
rm tests/integration/test_work_item.py
rm tests/integration/test_deployment.py

# Delete non-search unit tests (if they exist)
rm -f tests/unit/test_vendor_service.py
rm -f tests/unit/test_task_service.py
rm -f tests/unit/test_work_item_service.py

# Verify remaining tests
ls tests/integration/
```

**Expected Output**:
```
__init__.py
test_search.py
test_indexing.py
```

**Pass Criteria**:
- ✅ Only search/indexing tests remain

#### Scenario 5.2: Run Import Checks

```bash
# Test all module imports
python -c "import src.codebase_mcp.server"
python -c "import src.codebase_mcp.tools.indexing_tools"
python -c "import src.codebase_mcp.tools.search_tools"
python -c "import src.codebase_mcp.services.indexing_service"
python -c "import src.codebase_mcp.services.search_service"
python -c "import src.codebase_mcp.services.embedding_service"
python -c "import src.codebase_mcp.models.repository"
python -c "import src.codebase_mcp.models.code_chunk"
```

**Expected Output**:
```
(no output = success)
```

**Pass Criteria**:
- ✅ All imports succeed with zero errors
- ✅ No ModuleNotFoundError
- ✅ No ImportError

**Failure Example**:
```
Traceback (most recent call last):
  ...
ImportError: cannot import name 'VendorService' from 'src.codebase_mcp.services'
```

**Fix on Failure**: Identify remaining references to deleted modules and remove them.

#### Scenario 5.3: Run Type Checking

```bash
mypy --strict src/
```

**Expected Output**:
```
Success: no issues found in X source files
```

**Pass Criteria**:
- ✅ mypy exits with code 0
- ✅ Zero type errors reported
- ✅ "Success: no issues found" message

**Failure Example**:
```
src/codebase_mcp/server.py:45: error: Module has no attribute "VendorService"
Found 1 error in 1 file (checked 15 source files)
```

**Fix on Failure**: Resolve type errors (likely missing import cleanup).

#### Scenario 5.4: Run Search Integration Tests

```bash
pytest tests/integration/test_search.py -v
```

**Expected Output**:
```
tests/integration/test_search.py::test_search_basic PASSED
tests/integration/test_search.py::test_search_with_filters PASSED
tests/integration/test_search.py::test_search_embeddings PASSED
...
============ X passed in Y.YYs ============
```

**Pass Criteria**:
- ✅ All search tests pass
- ✅ Zero test failures
- ✅ Passing test count MATCHES Phase 1 baseline (Scenario 1.2)

**Failure Example**:
```
tests/integration/test_search.py::test_search_basic FAILED
ImportError: cannot import name 'VendorService'
```

**Fix on Failure**: Resolve import errors before proceeding.

#### Scenario 5.5: Verify Server Startup and Tool Count

```bash
# Start server in background
python -m src.codebase_mcp.server &
SERVER_PID=$!

# Wait for startup
sleep 2

# Check tool registration (inspect logs or server output)
# Expected: 2 tools registered

# Cleanup
kill $SERVER_PID
```

**Expected Output**:
```
Registered 2 MCP tools:
- index_repository
- search_code
```

**Pass Criteria**:
- ✅ Server starts successfully (no exceptions)
- ✅ Exactly 2 tools registered
- ✅ Tools are: index_repository, search_code
- ✅ No deleted tools listed

**Failure Example**:
```
Traceback (most recent call last):
  ...
ImportError: cannot import name 'vendor_tools'
```

**Fix on Failure**: Resolve import errors in server.py.

#### Scenario 5.6: Commit Final State

```bash
git add tests/
git commit -m "chore(tests): delete non-search tests and verify final state

Remove project config, vendor, task, work item, and deployment tests.
All validations pass:
- Import checks: ✅
- Type checking (mypy --strict): ✅
- Search integration tests: ✅ (X/X passing)
- Server startup: ✅
- Tool count: ✅ (2 tools)

Related: #007-remove-non-search Sub-Phase 4"
```

**Pass Criteria**:
- ✅ Commit created successfully
- ✅ All test files deleted in commit

---

## Final Success Criteria Checklist

**ALL criteria must pass before marking feature complete**:

### Import Validation
- [ ] All modules import without errors (Scenario 5.2)
- [ ] No ModuleNotFoundError or ImportError

### Type Safety
- [ ] `mypy --strict src/` passes with 0 errors (Scenario 5.3)
- [ ] "Success: no issues found" message displayed

### Search Functionality
- [ ] All search integration tests pass (Scenario 5.4)
- [ ] Passing test count matches Phase 1 baseline (Scenario 1.2)
- [ ] Search API contracts preserved

### Server Health
- [ ] Server starts successfully (Scenario 5.5)
- [ ] No exceptions during startup
- [ ] Server responds to MCP protocol

### Tool Count
- [ ] Exactly 2 tools registered (Scenario 5.5)
- [ ] Tools are: `index_repository`, `search_code`
- [ ] No deleted tools present

### Git History
- [ ] 4 atomic commits created (one per sub-phase)
- [ ] Commit messages follow Conventional Commits format
- [ ] Each commit references #007-remove-non-search

### Performance Baselines
- [ ] Search test latency unchanged (no regression)
- [ ] Index test latency unchanged (no regression)

## Troubleshooting

### Import Errors After Sub-Phase 3

**Symptom**: `ImportError: cannot import name 'VendorService'`

**Cause**: Incomplete import cleanup in server.py or other modules

**Fix**:
```bash
# Find remaining references
grep -r "VendorService" src/

# Remove import statements
# Edit files to remove deleted module imports
```

### Type Errors in mypy

**Symptom**: `error: Module has no attribute 'vendor_tools'`

**Cause**: Type annotations referencing deleted modules

**Fix**:
```bash
# Find type annotation references
grep -r "vendor_tools" src/

# Remove type hints or update annotations
```

### Search Tests Fail

**Symptom**: Search tests fail with import errors

**Cause**: Test files importing deleted modules

**Fix**:
```bash
# Check test imports
grep -r "from.*vendor" tests/integration/test_search.py

# Remove unnecessary imports from test files
```

### Server Won't Start

**Symptom**: `ImportError` during server startup

**Cause**: server.py still importing deleted modules

**Fix**:
```bash
# Review server.py imports
head -n 50 src/codebase_mcp/server.py

# Remove imports for deleted tools/services/models
```

## Validation Timeline

**Phase 1 (Baseline)**: ~2 minutes
- Run search tests
- Record metrics
- Verify tool count

**Phase 2-4 (Deletions)**: ~5 minutes per phase
- Execute deletions
- Commit atomic changes
- Intermediate breakage acceptable

**Phase 5 (Final Validation)**: ~5 minutes
- Delete tests
- Run all validations
- Commit final state

**Total Estimated Time**: ~25 minutes

## Success Indicators

✅ **Green Light**: All Phase 5 scenarios pass, 4 commits created, ready for PR
⚠️ **Yellow Light**: Import/type errors in Phase 5, need fixes before commit
🔴 **Red Light**: Search tests fail in Phase 5, investigate regression

## Next Steps After Validation

1. Review git log to confirm 4 atomic commits
2. Run full test suite: `pytest tests/`
3. Update documentation to reflect 2-tool scope
4. Create PR with validation results in description
5. Request review from maintainers

---

**Last Updated**: 2025-10-11
**Feature**: 007-remove-non-search
**Validation Strategy**: 4-phase atomic commits with final validation
