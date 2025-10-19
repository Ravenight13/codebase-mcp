# Quick Server Restart Guide

**For**: Ensuring codebase-mcp server runs latest code from `fix/project-resolution-auto-create` branch

---

## One-Line Quick Fix

```bash
cd /Users/cliffclarke/Claude_Code/codebase-mcp && pkill -f "codebase-mcp/run_server.py" && sleep 1 && python run_server.py > /tmp/codebase-mcp-startup.log 2>&1 & sleep 2 && tail -20 /tmp/codebase-mcp.log
```

**What it does**:
1. Change to codebase-mcp directory
2. Kill existing server
3. Wait 1 second
4. Start new server in background
5. Wait 2 seconds
6. Show last 20 lines of log

---

## Step-by-Step (Recommended)

### 1. Verify Current State
```bash
cd /Users/cliffclarke/Claude_Code/codebase-mcp
./scripts/verify-server-version.sh
```

### 2. Stop Server
```bash
pkill -f "codebase-mcp/run_server.py"

# Verify stopped
ps aux | grep "codebase-mcp/run_server.py" | grep -v grep
# Should return nothing
```

### 3. Check Git Status
```bash
git branch --show-current
# Should show: fix/project-resolution-auto-create

git status
# Should show: clean working tree
```

### 4. Start Server
```bash
python run_server.py > /tmp/codebase-mcp-startup.log 2>&1 &
```

### 5. Verify Startup
```bash
# Wait 2 seconds
sleep 2

# Check logs
tail -20 /tmp/codebase-mcp.log

# Look for: "FastMCP Server Initialization"
```

### 6. Run Verification Again
```bash
./scripts/verify-server-version.sh
```

**Expected output**: "✓ All checks passed! Server is running correct code."

---

## Verification Checklist

Run verification script: `./scripts/verify-server-version.sh`

Expected results:
- ✓ Server is running
- ✓ On correct branch: `fix/project-resolution-auto-create`
- ✓ On correct commit: `91c24cef`
- ✓ No uncommitted changes
- ✓ Editable install detected
- ✓ Bug 2 fix present: config_path parameter
- ✓ Bug 3 fix present: IndexResult.status check
- ✓ Log file exists

---

## Common Issues

### Server Won't Stop
```bash
# Force kill
pkill -9 -f "codebase-mcp/run_server.py"

# Or find and kill by PID
ps aux | grep "codebase-mcp/run_server.py" | grep -v grep | awk '{print $2}' | xargs kill -9
```

### Wrong Branch
```bash
git checkout fix/project-resolution-auto-create
```

### Old Code Still Running (Cache Issue)
```bash
# Reinstall editable package
uv pip uninstall codebase-mcp
uv pip install -e .

# Restart server
pkill -f "codebase-mcp/run_server.py"
python run_server.py &
```

---

## Testing the Fixes

After server restart, test each bug fix:

### Test Bug 1: Foreground Indexing (No Hang)
```python
# Via MCP tool in workflow-mcp
await index_repository(
    repo_path="/path/to/repo",
    ctx=ctx
)
# Expected: Returns response without hanging
```

### Test Bug 2: Background Auto-Create from Config
```python
# Via MCP tool in workflow-mcp
await start_indexing_background(
    repo_path="/path/to/repo/with/.codebase-mcp/config.json",
    ctx=ctx
)
# Expected: Job starts, project auto-created from config
```

### Test Bug 3: Error Status Handling
```python
# Via MCP tool in workflow-mcp
status = await get_indexing_status(job_id="<failed-job-id>")
# Expected: status["status"] == "failed" with error_message
```

---

## Monitoring

### Real-time Logs
```bash
tail -f /tmp/codebase-mcp.log
```

### Check Server Process
```bash
ps aux | grep "codebase-mcp/run_server.py" | grep -v grep
```

### Check Working Directory of Process
```bash
# Get PID
PID=$(ps aux | grep "codebase-mcp/run_server.py" | grep -v grep | awk '{print $2}' | head -1)

# Check working directory
lsof -p $PID | grep cwd
# Should show: .../codebase-mcp
```

---

## For workflow-mcp Integration

If workflow-mcp also needs updating:

```bash
# Stop workflow-mcp
pkill -f "workflow-mcp/run_server.py"

# Restart codebase-mcp first
cd /Users/cliffclarke/Claude_Code/codebase-mcp
pkill -f "codebase-mcp/run_server.py"
python run_server.py &

# Wait for codebase-mcp to start
sleep 3

# Start workflow-mcp
cd /Users/cliffclarke/Claude_Code/workflow-mcp
python run_server.py &

# Check both running
ps aux | grep -E "(codebase|workflow)-mcp/run_server.py" | grep -v grep
```

---

## Emergency Full Reset

If nothing else works:

```bash
cd /Users/cliffclarke/Claude_Code/codebase-mcp

# Kill everything
pkill -9 -f "codebase-mcp"
pkill -9 -f "workflow-mcp"

# Clean install
uv pip uninstall codebase-mcp
rm -rf .venv
python3.13 -m venv .venv
source .venv/bin/activate
uv pip install -e .

# Verify branch
git checkout fix/project-resolution-auto-create

# Start server
python run_server.py &

# Verify
sleep 2
./scripts/verify-server-version.sh
```

---

## Reference

- **Deployment Guide**: `/Users/cliffclarke/Claude_Code/codebase-mcp/docs/operations/MCP-SERVER-DEPLOYMENT.md`
- **Verification Script**: `/Users/cliffclarke/Claude_Code/codebase-mcp/scripts/verify-server-version.sh`
- **Server Logs**: `/tmp/codebase-mcp.log`
- **Startup Logs**: `/tmp/codebase-mcp-startup.log`
