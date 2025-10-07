# Rollback Procedure: FastMCP Migration

## Overview

This document provides a tested rollback procedure to revert from the FastMCP-based MCP server (v4.x) to the legacy Python SDK-based server (v3.x) if critical issues are encountered in production.

**Key Characteristics**:
- **Rollback Time**: <5 minutes (tested)
- **Data Safety**: No PostgreSQL data loss during rollback
- **Strategy**: Version control reversion (no parallel instances)
- **Validation**: All 6 tools must function correctly post-rollback

---

## When to Rollback

Execute this rollback procedure immediately if ANY of the following conditions occur:

### Critical Rollback Triggers

1. **Test Failures**: Integration test pass rate drops below 100%
2. **Performance Regression**: Search p95 latency exceeds 500ms
3. **Indexing Degradation**: Indexing time exceeds 70s for 10,000 files (>16% regression)
4. **Protocol Violations**: MCP protocol compliance violations detected by clients
5. **Connection Failures**: Claude Desktop unable to connect or tools fail to register
6. **Data Integrity**: Data corruption or loss detected in PostgreSQL
7. **Critical Bugs**: Production-blocking bugs discovered in FastMCP implementation

**Decision Rule**: If any single trigger condition is met, initiate rollback immediately. Do not wait for multiple conditions.

---

## Prerequisites

Before executing rollback, ensure:

- [ ] Git repository access with commit history
- [ ] Write access to Claude Desktop configuration file
- [ ] Ability to restart Claude Desktop application
- [ ] Access to `/tmp/codebase-mcp.log` for verification

**Required Versions**:
- Previous version tagged as `v3.0.0-mcp-sdk` or similar
- FastMCP version tagged as `v4.0.0-fastmcp` or similar

---

## Rollback Steps

### Step 1: Identify Rollback Target

```bash
# Navigate to project directory
cd /Users/cliffclarke/Claude_Code/codebase-mcp

# List available git tags to find v3.x version
git tag -l | grep "v3"

# Expected output:
# v3.0.0-mcp-sdk

# Verify tag commit details
git show v3.0.0-mcp-sdk --stat
```

**Expected Output**:
```
tag v3.0.0-mcp-sdk
Tagger: ...
Date:   ...

MCP Server (Python SDK v3) - Stable Release

commit abc123def456...
```

### Step 2: Checkout Previous Version

```bash
# Checkout the v3 server tag
git checkout v3.0.0-mcp-sdk

# Verify correct version checked out
git log -1 --oneline

# Expected output:
# abc123d MCP server with Python SDK v3 implementation
```

**Time Estimate**: 30 seconds

### Step 3: Update Claude Desktop Configuration

```bash
# Backup current configuration (optional)
cp ~/Library/Application\ Support/Claude/claude_desktop_config.json \
   ~/Library/Application\ Support/Claude/claude_desktop_config.json.backup

# Update configuration for v3 server
cat > ~/Library/Application\ Support/Claude/claude_desktop_config.json <<'EOF'
{
  "mcpServers": {
    "codebase-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/cliffclarke/Claude_Code/codebase-mcp",
        "run",
        "python",
        "-m",
        "src.mcp.server"
      ]
    }
  }
}
EOF

# Verify configuration file
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json | jq .
```

**Expected Output**:
```json
{
  "mcpServers": {
    "codebase-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/cliffclarke/Claude_Code/codebase-mcp",
        "run",
        "python",
        "-m",
        "src.mcp.server"
      ]
    }
  }
}
```

**Time Estimate**: 1 minute

### Step 4: Restart Claude Desktop

```bash
# On macOS, quit Claude Desktop
osascript -e 'quit app "Claude"'

# Wait 5 seconds for graceful shutdown
sleep 5

# Relaunch Claude Desktop
open -a "Claude"
```

**Alternative Manual Steps**:
1. Click "Claude" in menu bar
2. Select "Quit Claude"
3. Wait 5 seconds
4. Open Claude from Applications folder

**Time Estimate**: 1 minute

### Step 5: Validate V3 Server Functionality

```bash
# Monitor server startup in logs
tail -f /tmp/codebase-mcp.log

# Expected log output (v3 server):
# 2025-10-06 10:05:00 - INFO - Starting MCP server (Python SDK v3)
# 2025-10-06 10:05:00 - INFO - Registered tool: search_code
# 2025-10-06 10:05:00 - INFO - Registered tool: index_repository
# 2025-10-06 10:05:00 - INFO - Registered tool: create_task
# 2025-10-06 10:05:00 - INFO - Registered tool: get_task
# 2025-10-06 10:05:00 - INFO - Registered tool: list_tasks
# 2025-10-06 10:05:00 - INFO - Registered tool: update_task
# 2025-10-06 10:05:00 - INFO - Server listening on SSE transport
```

**Time Estimate**: 2 minutes

---

## Validation Tests

After rollback, verify each tool functions correctly:

### Test 1: Search Code Tool

**In Claude Desktop conversation**:
```
User: "Search for database connection code"
```

**Expected Behavior**:
- Claude invokes `search_code` tool
- Results return within 500ms
- Search results display file paths and code snippets
- No errors in `/tmp/codebase-mcp.log`

**Success Criteria**: Search results appear with semantic matches

### Test 2: Index Repository Tool

**In Claude Desktop conversation**:
```
User: "Index the repository at /tmp/test-repo"
```

**Expected Behavior**:
- Claude invokes `index_repository` tool
- Progress logs appear in `/tmp/codebase-mcp.log`
- Indexing completes without errors
- Success message confirms files indexed

**Success Criteria**: Repository indexed successfully

### Test 3: Task Management Tools

**In Claude Desktop conversation**:
```
User: "Create a task titled 'Test rollback' with description 'Verify v3 server works'"
User: "List all tasks"
User: "Update the test rollback task to completed status"
User: "Get the details of the test rollback task"
```

**Expected Behavior**:
- All 4 task tools function correctly
- Task data persists in PostgreSQL
- No protocol errors

**Success Criteria**: All task operations complete successfully

### Test 4: Log File Verification

```bash
# Check log file for v3 server messages (not FastMCP)
grep "Python SDK v3" /tmp/codebase-mcp.log

# Should see v3 startup messages
# Should NOT see "FastMCP" messages

# Check for errors
grep -i "error\|exception\|failed" /tmp/codebase-mcp.log | tail -20
```

**Success Criteria**: Logs show v3 server, no critical errors

---

## Data Considerations

### PostgreSQL Database

**Important**: The PostgreSQL database is NOT affected by rollback:

- **Indexed repositories**: Remain indexed after rollback
- **Task data**: All tasks persist unchanged
- **Embeddings**: Vector embeddings remain valid
- **Schema**: No schema changes between v3 and v4

**No Action Required**: Database continues working with v3 server.

### Configuration Files

**Files Modified During Rollback**:
- `~/Library/Application Support/Claude/claude_desktop_config.json` (reverted to v3 config)

**Files NOT Modified**:
- `.env` (unchanged)
- `pyproject.toml` (checked out to v3 version)
- PostgreSQL database (unchanged)
- `/tmp/codebase-mcp.log` (appended to, not deleted)

---

## Rollback Validation Checklist

After completing rollback steps, verify:

- [ ] Git repository on v3.0.0-mcp-sdk tag (run `git describe --tags`)
- [ ] Claude Desktop config points to `src.mcp.server` (not `fastmcp_server.py`)
- [ ] Claude Desktop restarted successfully
- [ ] Logs show "Python SDK v3" messages (run `grep "v3" /tmp/codebase-mcp.log`)
- [ ] Search tool returns results (<500ms)
- [ ] Index tool works on test repository
- [ ] Task creation/retrieval/update/list all functional
- [ ] No protocol errors in logs
- [ ] Total rollback time <5 minutes

**Sign-Off**: If all items checked, rollback is successful.

---

## Re-Deployment After Fix

If the FastMCP issue is resolved and you want to re-deploy v4:

```bash
# 1. Return to feature branch
git checkout 002-refactor-mcp-server

# 2. Apply fixes (if needed)
# ... make code changes ...

# 3. Run full test suite
pytest tests/integration/ -v

# 4. Tag new fixed version
git tag v4.0.1-fastmcp-fixed
git push origin v4.0.1-fastmcp-fixed

# 5. Update Claude Desktop config (back to FastMCP)
cat > ~/Library/Application\ Support/Claude/claude_desktop_config.json <<'EOF'
{
  "mcpServers": {
    "codebase-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/cliffclarke/Claude_Code/codebase-mcp",
        "run",
        "mcp",
        "run",
        "src/mcp/fastmcp_server.py"
      ]
    }
  }
}
EOF

# 6. Restart Claude Desktop
osascript -e 'quit app "Claude"'
sleep 5
open -a "Claude"

# 7. Verify FastMCP server starts
tail -f /tmp/codebase-mcp.log
```

**Re-validation Required**: Run all validation tests from this document before considering re-deployment complete.

---

## Troubleshooting

### Issue: Git checkout fails with uncommitted changes

**Error**:
```
error: Your local changes to the following files would be overwritten by checkout
```

**Solution**:
```bash
# Stash current changes
git stash save "Stashing FastMCP changes before rollback"

# Retry checkout
git checkout v3.0.0-mcp-sdk

# If needed later, recover changes
git stash pop
```

### Issue: Claude Desktop config file not found

**Error**:
```
cat: ~/Library/Application Support/Claude/claude_desktop_config.json: No such file or directory
```

**Solution**:
```bash
# Create directory if missing
mkdir -p ~/Library/Application\ Support/Claude

# Create new config file
cat > ~/Library/Application\ Support/Claude/claude_desktop_config.json <<'EOF'
{
  "mcpServers": {
    "codebase-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/cliffclarke/Claude_Code/codebase-mcp",
        "run",
        "python",
        "-m",
        "src.mcp.server"
      ]
    }
  }
}
EOF
```

### Issue: V3 server not starting after rollback

**Symptoms**: No logs in `/tmp/codebase-mcp.log` after Claude Desktop restart

**Debugging Steps**:
```bash
# 1. Verify correct Python module exists
ls src/mcp/server.py
# Should exist for v3 server

# 2. Test server manually
cd /Users/cliffclarke/Claude_Code/codebase-mcp
uv run python -m src.mcp.server

# 3. Check for dependency issues
uv pip list | grep mcp

# 4. Review Claude Desktop logs
tail -f ~/Library/Logs/Claude/mcp*.log
```

**Solution**: If server.py missing, wrong git tag was checked out. Verify with `git describe --tags` and checkout correct v3 tag.

### Issue: Tools registered but not working

**Symptoms**: Server starts, tools appear in Claude Desktop, but searches return errors

**Debugging Steps**:
```bash
# Check PostgreSQL connection
psql -d codebase_mcp -c "SELECT COUNT(*) FROM code_files;"

# Check Ollama availability
curl http://localhost:11434/api/tags

# Review error logs
grep -i "error" /tmp/codebase-mcp.log | tail -20
```

**Solution**: Verify PostgreSQL and Ollama services running. Restart if needed.

---

## Performance Comparison

After rollback, performance should match v3 baseline:

| Metric | V3 Server (Expected) | Validation Command |
|--------|---------------------|-------------------|
| Indexing (10K files) | 50-60 seconds | `time uv run python -m src.mcp.server index /path/to/repo` |
| Search p95 latency | <500ms | Use hyperfine benchmark (see quickstart.md) |
| Search mean latency | 300-400ms | Use hyperfine benchmark |
| Server startup | <5 seconds | Monitor `/tmp/codebase-mcp.log` |

**If performance differs**: Check PostgreSQL query performance, Ollama model availability, or system resource contention.

---

## Rollback Success Metrics

**Rollback is considered successful when**:
- ✅ All 6 MCP tools functional in Claude Desktop
- ✅ Search results return in <500ms (p95)
- ✅ No protocol errors in logs
- ✅ PostgreSQL data intact (run `SELECT COUNT(*) FROM code_files`)
- ✅ Rollback completed in <5 minutes
- ✅ V3 server logs visible in `/tmp/codebase-mcp.log`

**Rollback Sign-Off**: Document completion time and validation results for post-mortem analysis.

---

## Support & Escalation

If rollback fails or v3 server does not function correctly:

1. **Check Prerequisites**: Verify PostgreSQL and Ollama running
2. **Review Logs**: Analyze `/tmp/codebase-mcp.log` for errors
3. **Test Database**: Run `psql -d codebase_mcp -c "SELECT version();"` to confirm DB access
4. **Escalate**: Contact repository maintainer with:
   - Rollback steps executed
   - Error messages from logs
   - Git tag/commit checked out
   - Claude Desktop version

**Emergency Contact**: See repository CONTRIBUTING.md for maintainer contact information.

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| v1.0 | 2025-10-06 | Initial rollback procedure for FastMCP migration |

**Document Maintenance**: Update this document after each successful rollback with lessons learned and any procedure improvements.
