# MCP Server Deployment Troubleshooting Flowchart

This flowchart helps diagnose and fix issues when workflow-mcp connects to codebase-mcp running old code.

---

## Start Here

**Question**: Are integration tests failing for Bug 1, Bug 2, or Bug 3?

- **YES** → Continue to Section 1
- **NO** → Tests are passing, no action needed

---

## Section 1: Is the Server Running?

**Check**:
```bash
ps aux | grep "codebase-mcp/run_server.py" | grep -v grep
```

**Result**:
- **Process found** → Continue to Section 2
- **No process** → Go to Section 1A

### Section 1A: Server Not Running

**Action**: Start the server
```bash
cd /Users/cliffclarke/Claude_Code/codebase-mcp
python run_server.py &
sleep 2
./scripts/verify-server-version.sh
```

**Result**:
- **Server started** → Continue to Section 2
- **Server failed to start** → Go to Section 1B

### Section 1B: Server Fails to Start

**Check logs**:
```bash
tail -50 /tmp/codebase-mcp.log
```

**Common errors**:

#### Error: "Port already in use"
```bash
# Kill process using port
lsof -ti:8000 | xargs kill -9
# Restart server
python run_server.py &
```

#### Error: "Database connection failed"
```bash
# Check PostgreSQL
pg_isready
# If not ready, start PostgreSQL
brew services start postgresql@14
# Restart server
python run_server.py &
```

#### Error: "Import error" or "Module not found"
```bash
# Reinstall dependencies
uv pip install -e .
# Restart server
python run_server.py &
```

---

## Section 2: Is Server on Correct Branch?

**Check**:
```bash
cd /Users/cliffclarke/Claude_Code/codebase-mcp
git branch --show-current
```

**Result**:
- **Shows**: `fix/project-resolution-auto-create` → Continue to Section 3
- **Shows**: Different branch → Go to Section 2A

### Section 2A: Wrong Branch

**Action**: Switch to fix branch
```bash
# Stop server
pkill -f "codebase-mcp/run_server.py"

# Switch branch
git checkout fix/project-resolution-auto-create

# Restart server
python run_server.py &

# Verify
./scripts/verify-server-version.sh
```

**Result**:
- **Verification passes** → Problem solved! Test your fixes
- **Verification fails** → Continue to Section 3

---

## Section 3: Is Server on Correct Commit?

**Check**:
```bash
git log --oneline -1
```

**Expected**: `91c24cef docs: comprehensive completion summary for MCP indexing bug fixes`

**Result**:
- **Matches expected** → Continue to Section 4
- **Different commit** → Go to Section 3A

### Section 3A: Wrong Commit

**Action**: Update to latest commit
```bash
# Stop server
pkill -f "codebase-mcp/run_server.py"

# Pull latest changes (if remote exists)
git pull origin fix/project-resolution-auto-create

# Or reset to expected commit
git reset --hard 91c24cef

# Restart server
python run_server.py &

# Verify
./scripts/verify-server-version.sh
```

**Result**:
- **Verification passes** → Problem solved! Test your fixes
- **Verification fails** → Continue to Section 4

---

## Section 4: Is Package Installed in Editable Mode?

**Check**:
```bash
uv pip show codebase-mcp | grep "Editable project location"
```

**Result**:
- **Shows editable location** → Continue to Section 5
- **No editable location shown** → Go to Section 4A

### Section 4A: Not Editable Install

**Action**: Reinstall in editable mode
```bash
# Stop server
pkill -f "codebase-mcp/run_server.py"

# Uninstall
uv pip uninstall codebase-mcp

# Reinstall editable
cd /Users/cliffclarke/Claude_Code/codebase-mcp
uv pip install -e .

# Restart server
python run_server.py &

# Verify
./scripts/verify-server-version.sh
```

**Result**:
- **Verification passes** → Problem solved! Test your fixes
- **Verification fails** → Continue to Section 5

---

## Section 5: Are Fix-Specific Code Changes Present?

**Check**:
```bash
./scripts/verify-server-version.sh
```

Look for these lines:
- `✓ Bug 2 fix present: config_path parameter`
- `✓ Bug 3 fix present: IndexResult.status check`

**Result**:
- **Both fixes present** → Continue to Section 6
- **Fixes missing** → Go to Section 5A

### Section 5A: Fixes Not Present

**Diagnose**: Check source code directly
```bash
# Bug 2 fix
grep -n "config_path=config_path" src/mcp/tools/background_indexing.py

# Bug 3 fix
grep -n "result.status" src/services/background_worker.py
```

**If grep finds nothing**:
- **Wrong branch checked out** → Go back to Section 2A
- **Uncommitted changes** → Go to Section 5B

### Section 5B: Uncommitted Changes or Merge Conflict

**Check**:
```bash
git status
```

**If uncommitted changes**:
```bash
# Stash changes
git stash

# Reset to clean state
git reset --hard 91c24cef

# Restart server
pkill -f "codebase-mcp/run_server.py"
python run_server.py &
```

**If merge conflict**:
```bash
# Abort merge
git merge --abort

# Hard reset
git reset --hard 91c24cef

# Restart server
pkill -f "codebase-mcp/run_server.py"
python run_server.py &
```

---

## Section 6: Multiple Servers Running?

**Check**:
```bash
ps aux | grep "codebase-mcp/run_server.py" | grep -v grep | wc -l
```

**Result**:
- **Shows**: 1 → Continue to Section 7
- **Shows**: >1 → Go to Section 6A

### Section 6A: Multiple Servers

**Action**: Kill all and restart single instance
```bash
# Kill all
pkill -9 -f "codebase-mcp/run_server.py"

# Verify all killed
ps aux | grep "codebase-mcp/run_server.py" | grep -v grep
# Should show nothing

# Start single instance
cd /Users/cliffclarke/Claude_Code/codebase-mcp
python run_server.py &

# Verify single process
ps aux | grep "codebase-mcp/run_server.py" | grep -v grep | wc -l
# Should show: 1
```

**Result**:
- **Single server running** → Continue to Section 7

---

## Section 7: Is Server Using Correct Virtual Environment?

**Check**:
```bash
# Get server PID
PID=$(ps aux | grep "codebase-mcp/run_server.py" | grep -v grep | awk '{print $2}' | head -1)

# Check Python path
lsof -p $PID | grep python

# Should show: .../codebase-mcp/.venv/bin/python
```

**Result**:
- **Correct venv** → Continue to Section 8
- **Wrong venv or system Python** → Go to Section 7A

### Section 7A: Wrong Virtual Environment

**Action**: Restart with correct venv
```bash
# Stop server
pkill -f "codebase-mcp/run_server.py"

# Activate correct venv
cd /Users/cliffclarke/Claude_Code/codebase-mcp
source .venv/bin/activate

# Verify Python
which python
# Should show: /Users/cliffclarke/Claude_Code/codebase-mcp/.venv/bin/python

# Reinstall to be safe
uv pip install -e .

# Start server
python run_server.py &
```

---

## Section 8: Cache or Import Issues?

If all above checks pass but tests still fail, likely Python import cache issue.

**Action**: Hard reset everything
```bash
# Stop all servers
pkill -9 -f "codebase-mcp"
pkill -9 -f "workflow-mcp"

# Clear Python cache
cd /Users/cliffclarke/Claude_Code/codebase-mcp
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete

# Reinstall
uv pip uninstall codebase-mcp
uv pip install -e .

# Restart
python run_server.py &

# Verify
sleep 2
./scripts/verify-server-version.sh
```

**Result**:
- **Verification passes** → Problem solved! Test your fixes
- **Verification still fails** → Go to Section 9

---

## Section 9: Nuclear Option - Full Clean Install

If nothing else works, completely rebuild environment.

### Step 1: Backup Current State
```bash
cd /Users/cliffclarke/Claude_Code/codebase-mcp

# Save current branch
git branch --show-current > /tmp/codebase-mcp-branch.txt

# Check for uncommitted work
git status
# If you have uncommitted changes, stash them:
# git stash save "backup before clean install"
```

### Step 2: Clean Everything
```bash
# Kill all servers
pkill -9 -f codebase-mcp
pkill -9 -f workflow-mcp

# Remove virtual environment
rm -rf .venv

# Clean Python cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete
find . -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

# Clean build artifacts
rm -rf build/ dist/
```

### Step 3: Rebuild
```bash
# Create fresh venv
python3.13 -m venv .venv

# Activate
source .venv/bin/activate

# Upgrade pip/uv
pip install --upgrade pip uv

# Install package in editable mode
uv pip install -e .

# Verify installation
uv pip show codebase-mcp
# Should show: Editable project location: /Users/cliffclarke/Claude_Code/codebase-mcp
```

### Step 4: Verify Git State
```bash
# Check branch
git branch --show-current
# Should show: fix/project-resolution-auto-create

# If wrong branch:
git checkout fix/project-resolution-auto-create

# Verify commit
git log --oneline -1
# Should show: 91c24cef
```

### Step 5: Start Server
```bash
python run_server.py &
sleep 3
```

### Step 6: Full Verification
```bash
./scripts/verify-server-version.sh
```

**Expected output**: All checks pass

---

## Success Criteria

Your deployment is correct when:

1. **Verification script passes**:
   ```bash
   ./scripts/verify-server-version.sh
   ```
   Shows: "✓ All checks passed! Server is running correct code."

2. **Server logs show startup**:
   ```bash
   tail -20 /tmp/codebase-mcp.log
   ```
   Shows: "FastMCP Server Initialization"

3. **Tests pass**:
   - Bug 1: Foreground indexing completes without hanging
   - Bug 2: Background indexing auto-creates project from config
   - Bug 3: Failed jobs show status="failed" with error message

---

## Still Having Issues?

If you've gone through this entire flowchart and issues persist:

### Collect Debug Information
```bash
# Save to file for debugging
cat > /tmp/codebase-mcp-debug.txt <<EOF
=== Git Status ===
$(cd /Users/cliffclarke/Claude_Code/codebase-mcp && git status)

=== Current Branch ===
$(cd /Users/cliffclarke/Claude_Code/codebase-mcp && git branch --show-current)

=== Recent Commits ===
$(cd /Users/cliffclarke/Claude_Code/codebase-mcp && git log --oneline -5)

=== Package Info ===
$(uv pip show codebase-mcp)

=== Running Processes ===
$(ps aux | grep -E "codebase.*mcp" | grep -v grep)

=== Server Logs (last 50 lines) ===
$(tail -50 /tmp/codebase-mcp.log)

=== Verification Script Output ===
$(cd /Users/cliffclarke/Claude_Code/codebase-mcp && ./scripts/verify-server-version.sh)
EOF

cat /tmp/codebase-mcp-debug.txt
```

### Check Related Systems
```bash
# PostgreSQL
pg_isready && echo "PostgreSQL: OK" || echo "PostgreSQL: FAILED"

# Disk space
df -h /tmp

# Python version
python --version
```

---

## Quick Reference: Command Cheat Sheet

```bash
# Stop server
pkill -f "codebase-mcp/run_server.py"

# Start server
cd /Users/cliffclarke/Claude_Code/codebase-mcp && python run_server.py &

# Verify server
./scripts/verify-server-version.sh

# Check logs
tail -f /tmp/codebase-mcp.log

# Reinstall
uv pip uninstall codebase-mcp && uv pip install -e .

# Check branch
git branch --show-current

# Switch to fix branch
git checkout fix/project-resolution-auto-create
```
