# MCP Server Deployment Guide

## Problem Statement

**Symptom**: workflow-mcp's AI Chat connects to a codebase-mcp MCP server, but the server is running old code that doesn't include recent bug fixes on the `fix/project-resolution-auto-create` branch.

**Impact**: Integration tests fail because the MCP server doesn't have the latest fixes for:
- Bug 1: Foreground indexing hanging
- Bug 2: Background indexing auto-creation from config
- Bug 3: Error status handling

**Root Cause**: The MCP server process is running from a different branch or hasn't been restarted after code changes.

---

## How MCP Servers Work

MCP (Model Context Protocol) servers can be deployed in three ways:

### 1. **Installed Package Mode** (Production)
- Package installed via `pip install codebase-mcp` or `uv pip install -e .`
- Server runs from installed code in `.venv/lib/python3.x/site-packages/`
- **Pro**: Clean, production-ready deployment
- **Con**: Requires reinstall after code changes

### 2. **Editable Install Mode** (Development - RECOMMENDED)
- Package installed via `pip install -e .` or `uv pip install -e .`
- Server runs directly from source directory
- **Pro**: Code changes apply immediately (after server restart)
- **Con**: Need to restart server to pick up changes

### 3. **Direct Execution Mode** (Development)
- Server started via `python run_server.py` or `python -m src.mcp.server_fastmcp`
- No installation required
- **Pro**: Maximum flexibility, no install needed
- **Con**: Environment must be managed manually

---

## Current Configuration

Based on investigation of your setup:

```bash
# Installation Status
Package: codebase-mcp 0.1.0
Location: /Users/cliffclarke/Claude_Code/codebase-mcp (editable install)

# Running Processes (example from investigation)
PID: 69459  # codebase-mcp server
PID: 69460  # workflow-mcp server

# Git Status
Current Branch: fix/project-resolution-auto-create
Status: Clean (no uncommitted changes)

# Recent Commits (on fix branch)
91c24cef docs: comprehensive completion summary for MCP indexing bug fixes
972e08bf fix(background): trigger auto-creation from captured config path (Bug 2)
00ca2314 feat(background): capture config path for background worker (Bug 2)
68ed9fad test(background): add failing tests for auto-creation from config (Bug 2)
```

**Key Files Changed in Fix Branch**:
- `src/mcp/tools/indexing.py` - Foreground indexing fixes
- `src/mcp/tools/background_indexing.py` - Background indexing fixes
- `src/services/background_worker.py` - Worker status handling
- `src/database/auto_create.py` - Auto-creation from config
- `src/database/session.py` - Registry sync improvements

---

## Solution: Ensure Correct Code is Used

### Option 1: Restart Server from Fix Branch (FASTEST)

This is the **recommended approach** if you already have an editable install.

#### Step 1: Verify Current Branch
```bash
cd /Users/cliffclarke/Claude_Code/codebase-mcp
git branch --show-current
# Should output: fix/project-resolution-auto-create
```

If on wrong branch:
```bash
git checkout fix/project-resolution-auto-create
```

#### Step 2: Kill Running Server Process
```bash
# Find the codebase-mcp server process
ps aux | grep "codebase-mcp/run_server.py" | grep -v grep

# Kill it (replace PID with actual process ID)
kill <PID>

# Or kill all codebase-mcp servers
pkill -f "codebase-mcp/run_server.py"
```

#### Step 3: Restart Server
```bash
# Start server in background (recommended)
cd /Users/cliffclarke/Claude_Code/codebase-mcp
nohup python run_server.py > /tmp/codebase-mcp-startup.log 2>&1 &

# Or start in foreground (for debugging)
python run_server.py
```

#### Step 4: Verify Server Started
```bash
# Check process is running
ps aux | grep "codebase-mcp/run_server.py" | grep -v grep

# Check logs
tail -f /tmp/codebase-mcp.log
# Look for: "FastMCP Server Initialization"
```

---

### Option 2: Reinstall Editable Package (If Install is Corrupted)

Use this if Option 1 doesn't work or you suspect package issues.

#### Step 1: Uninstall Existing Package
```bash
cd /Users/cliffclarke/Claude_Code/codebase-mcp
uv pip uninstall codebase-mcp
```

#### Step 2: Verify Branch
```bash
git branch --show-current
# Should output: fix/project-resolution-auto-create

git status
# Should show clean working tree
```

#### Step 3: Reinstall in Editable Mode
```bash
# Using uv (recommended)
uv pip install -e .

# Or using pip
pip install -e .
```

#### Step 4: Verify Installation
```bash
uv pip list | grep codebase
# Should show: codebase-mcp  0.1.0  /Users/cliffclarke/Claude_Code/codebase-mcp

# Verify script is available
which codebase-mcp
# Should show: /Users/cliffclarke/Claude_Code/codebase-mcp/.venv/bin/codebase-mcp
```

#### Step 5: Kill Old Server and Restart
```bash
# Kill old server
pkill -f "codebase-mcp/run_server.py"

# Start new server
python run_server.py &
```

---

### Option 3: Run from Specific Branch (Advanced)

Use this for testing multiple branches simultaneously.

#### Step 1: Create Virtual Environment for Branch
```bash
cd /Users/cliffclarke/Claude_Code/codebase-mcp

# Create branch-specific venv
python3.13 -m venv .venv-fix-branch

# Activate it
source .venv-fix-branch/bin/activate

# Install dependencies
uv pip install -e .
```

#### Step 2: Run Server with Branch-Specific Venv
```bash
# Activate branch venv
source .venv-fix-branch/bin/activate

# Verify Python path
which python
# Should show: /Users/cliffclarke/Claude_Code/codebase-mcp/.venv-fix-branch/bin/python

# Start server
python run_server.py
```

---

## Verification Steps

After deploying the server, verify it's using the correct code:

### 1. Check Server Version and Startup
```bash
# Check server logs
tail -50 /tmp/codebase-mcp.log

# Look for:
# - "FastMCP Server Initialization"
# - "Connection pool initialized"
# - "MCP server started successfully"
```

### 2. Verify Git Commit in Running Code
```bash
# Check which directory the server is running from
ps aux | grep "codebase-mcp/run_server.py" | grep -v grep
# Shows working directory

# Verify git commit in that directory
cd /Users/cliffclarke/Claude_Code/codebase-mcp
git log --oneline -1
# Should show: 91c24cef docs: comprehensive completion summary...
```

### 3. Test Fix-Specific Behavior

#### Test Bug 1 Fix (Foreground Indexing)
```bash
# This should complete without hanging
# Use MCP tool: index_repository
# Expected: Response returned with status and file counts
```

#### Test Bug 2 Fix (Background Auto-Create)
```bash
# Check that config-based auto-creation works
# Use MCP tool: start_indexing_background with ctx parameter
# Expected: Job starts with project auto-created from config
```

#### Test Bug 3 Fix (Error Status)
```bash
# Check that errors are properly reported
# Use MCP tool: get_indexing_status for a failed job
# Expected: status="failed" with error_message populated
```

### 4. Check Code Signature
Verify specific fix is present in running code:

```bash
# Bug 2 fix: Check for config path capture
grep -A 5 "config_path_for_worker" /Users/cliffclarke/Claude_Code/codebase-mcp/src/mcp/tools/background_indexing.py

# Bug 3 fix: Check for status validation
grep -A 5 "IndexResult.status" /Users/cliffclarke/Claude_Code/codebase-mcp/src/services/background_worker.py
```

Expected outputs:
- **Bug 2**: Should find `config_path_for_worker` variable in `start_indexing_background` tool
- **Bug 3**: Should find `if result.status == "failed"` condition in background worker

---

## Troubleshooting

### Issue: Server Won't Start

**Symptom**: `python run_server.py` exits immediately

**Check**:
```bash
# Look for errors in log
tail -50 /tmp/codebase-mcp.log

# Check for port conflicts
lsof -i :8000  # Or whatever port MCP uses
```

**Solution**:
```bash
# Kill conflicting process
kill <PID>

# Or use different port (if configurable)
export MCP_PORT=8001
python run_server.py
```

---

### Issue: Old Code Still Running

**Symptom**: Tests fail even after restart

**Check**:
```bash
# Verify process working directory
lsof -p <PID> | grep cwd

# Check Python path
ps -p <PID> -o command=
```

**Solution**:
```bash
# Kill ALL Python processes for certainty
pkill -f "codebase-mcp"

# Verify none running
ps aux | grep codebase-mcp | grep -v grep

# Start fresh
cd /Users/cliffclarke/Claude_Code/codebase-mcp
python run_server.py &
```

---

### Issue: Editable Install Not Reflecting Changes

**Symptom**: Code changes don't appear in running server

**Check**:
```bash
# Verify editable install
pip show codebase-mcp
# Location should point to source directory, not site-packages

# Check for .egg-info
ls -la /Users/cliffclarke/Claude_Code/codebase-mcp/
# Should see: codebase_mcp.egg-info/
```

**Solution**:
```bash
# Reinstall in editable mode
cd /Users/cliffclarke/Claude_Code/codebase-mcp
uv pip uninstall codebase-mcp
uv pip install -e .

# Restart server
pkill -f "codebase-mcp/run_server.py"
python run_server.py &
```

---

### Issue: Wrong Branch Running

**Symptom**: Git shows correct branch, but old code runs

**Check**:
```bash
# Verify no detached HEAD
git status

# Check for uncommitted changes
git diff --stat

# Verify branch commit
git log --oneline -5
```

**Solution**:
```bash
# Ensure on fix branch
git checkout fix/project-resolution-auto-create

# Pull latest changes (if remote exists)
git pull origin fix/project-resolution-auto-create

# Restart server
pkill -f "codebase-mcp/run_server.py"
python run_server.py &
```

---

### Issue: Multiple Servers Running

**Symptom**: Inconsistent behavior, some tests pass/fail randomly

**Check**:
```bash
# Find all codebase-mcp processes
ps aux | grep -E "codebase.*mcp" | grep -v grep

# Check listening ports
lsof -i | grep codebase
```

**Solution**:
```bash
# Kill ALL codebase-mcp servers
pkill -f "codebase-mcp"

# Verify clean slate
ps aux | grep codebase | grep -v grep

# Start single instance
cd /Users/cliffclarke/Claude_Code/codebase-mcp
python run_server.py &

# Verify single process
ps aux | grep "codebase-mcp/run_server.py" | grep -v grep
```

---

## For workflow-mcp Integration

If workflow-mcp needs to connect to the correct codebase-mcp server:

### 1. Check Connection Configuration

workflow-mcp may connect via:
- **Environment variable**: `CODEBASE_MCP_URL`
- **Config file**: `.codebase-mcp/config.json`
- **MCP registry**: System-level MCP server registry

### 2. Verify Server Endpoint

```bash
# Check if codebase-mcp exposes health endpoint
curl http://localhost:8000/health 2>/dev/null || echo "Not HTTP endpoint"

# Check MCP configuration in workflow-mcp
cat /Users/cliffclarke/Claude_Code/workflow-mcp/.codebase-mcp/config.json
```

### 3. Ensure Both Servers Use Same Branch

```bash
# Check codebase-mcp branch
cd /Users/cliffclarke/Claude_Code/codebase-mcp
git branch --show-current

# Check workflow-mcp branch (if applicable)
cd /Users/cliffclarke/Claude_Code/workflow-mcp
git branch --show-current
```

### 4. Restart Both Servers in Correct Order

```bash
# Stop both
pkill -f "codebase-mcp/run_server.py"
pkill -f "workflow-mcp/run_server.py"

# Start codebase-mcp first
cd /Users/cliffclarke/Claude_Code/codebase-mcp
python run_server.py &

# Wait 5 seconds for startup
sleep 5

# Then start workflow-mcp
cd /Users/cliffclarke/Claude_Code/workflow-mcp
python run_server.py &
```

### 5. Test Integration

```bash
# Check both servers running
ps aux | grep -E "(codebase|workflow)-mcp/run_server.py" | grep -v grep

# Check logs for connection
tail -f /tmp/codebase-mcp.log
tail -f /tmp/workflow-mcp.log
```

---

## Quick Reference Commands

### Server Management
```bash
# Kill server
pkill -f "codebase-mcp/run_server.py"

# Start server (background)
cd /Users/cliffclarke/Claude_Code/codebase-mcp && python run_server.py &

# Start server (foreground for debugging)
cd /Users/cliffclarke/Claude_Code/codebase-mcp && python run_server.py

# Check if running
ps aux | grep "codebase-mcp/run_server.py" | grep -v grep

# View logs
tail -f /tmp/codebase-mcp.log
```

### Code Verification
```bash
# Check branch
git branch --show-current

# Check recent commits
git log --oneline -5

# Check for specific fix
grep -n "config_path_for_worker" src/mcp/tools/background_indexing.py
```

### Package Management
```bash
# Reinstall editable
uv pip uninstall codebase-mcp && uv pip install -e .

# Check installation
uv pip show codebase-mcp

# List installed version
uv pip list | grep codebase
```

---

## Best Practices

### 1. Development Workflow
- Always use **editable install** (`uv pip install -e .`) for development
- Keep server running in **tmux** or **screen** for easy monitoring
- Check logs frequently: `tail -f /tmp/codebase-mcp.log`

### 2. Branch Switching
When switching branches:
```bash
# 1. Stop server
pkill -f "codebase-mcp/run_server.py"

# 2. Switch branch
git checkout <branch-name>

# 3. Reinstall (if dependencies changed)
uv pip install -e .

# 4. Restart server
python run_server.py &
```

### 3. Testing New Code
```bash
# 1. Make code changes
# 2. No need to reinstall (editable mode)
# 3. Restart server
pkill -f "codebase-mcp/run_server.py" && python run_server.py &

# 4. Verify in logs
tail -50 /tmp/codebase-mcp.log
```

### 4. Production Deployment
For production, use **non-editable install** from tagged release:
```bash
# Tag release
git tag v0.1.1

# Install from tag
pip install git+https://github.com/user/codebase-mcp.git@v0.1.1

# Run via installed command
codebase-mcp
```

---

## Summary

**The Problem**: Old server code running despite new fixes on branch

**Root Cause**: Server process not restarted after code changes

**Quick Fix**:
1. Verify branch: `git branch --show-current`
2. Kill server: `pkill -f "codebase-mcp/run_server.py"`
3. Restart server: `python run_server.py &`
4. Check logs: `tail -f /tmp/codebase-mcp.log`

**Verification**:
- Server logs show startup message
- Git commit matches expected: `91c24cef`
- Tests pass for Bug 1, 2, and 3

---

## Additional Resources

- **MCP Server Code**: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/mcp/server_fastmcp.py`
- **Server Wrapper**: `/Users/cliffclarke/Claude_Code/codebase-mcp/run_server.py`
- **Server Logs**: `/tmp/codebase-mcp.log`
- **Bug Fix Docs**: `/Users/cliffclarke/Claude_Code/codebase-mcp/docs/bugs/mcp-indexing-failures/`
- **Package Config**: `/Users/cliffclarke/Claude_Code/codebase-mcp/pyproject.toml`
