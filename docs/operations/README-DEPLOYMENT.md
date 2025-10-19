# MCP Server Deployment Documentation - Overview

This directory contains comprehensive deployment and troubleshooting documentation for ensuring the codebase-mcp server runs the correct code version, particularly for the bug fixes on branch `fix/project-resolution-auto-create`.

---

## Problem Summary

**Issue**: workflow-mcp's AI Chat connects to codebase-mcp MCP server, but the server may be running old code that doesn't include recent bug fixes.

**Impact**: Integration tests fail because the fixes for Bug 1, Bug 2, and Bug 3 are not active in the running server.

**Solution**: Proper deployment procedures to ensure the server runs from the correct Git branch with all fixes applied.

---

## Quick Start (TL;DR)

### For Impatient Developers

**1. Verify current state:**
```bash
cd /Users/cliffclarke/Claude_Code/codebase-mcp
./scripts/verify-server-version.sh
```

**2. If issues found, quick fix:**
```bash
pkill -f "codebase-mcp/run_server.py" && sleep 1 && python run_server.py &
```

**3. Verify again:**
```bash
./scripts/verify-server-version.sh
```

**Expected**: "✓ All checks passed! Server is running correct code."

---

## Documentation Structure

### 1. **MCP-SERVER-DEPLOYMENT.md** (Main Guide)
**Path**: `/Users/cliffclarke/Claude_Code/codebase-mcp/docs/operations/MCP-SERVER-DEPLOYMENT.md`

**Purpose**: Comprehensive deployment guide explaining:
- How MCP servers work (3 deployment modes)
- Current configuration investigation results
- 3 deployment options (restart, reinstall, branch-specific)
- Verification procedures
- Troubleshooting common issues
- workflow-mcp integration specifics

**When to use**:
- First time deploying the fix branch
- Understanding MCP server architecture
- Learning about editable installs
- Detailed troubleshooting

**Size**: ~605 lines, 14KB

### 2. **QUICK-RESTART-GUIDE.md** (Quick Reference)
**Path**: `/Users/cliffclarke/Claude_Code/codebase-mcp/docs/operations/QUICK-RESTART-GUIDE.md`

**Purpose**: Fast reference for common restart scenarios:
- One-line quick fix command
- Step-by-step restart procedure
- Verification checklist
- Common issues with solutions
- Testing procedures for each bug fix
- Emergency full reset

**When to use**:
- Daily development workflow
- Quick server restart after code changes
- Testing bug fixes
- Verifying server state

**Size**: ~150 lines, 4.7KB

### 3. **DEPLOYMENT-TROUBLESHOOTING-FLOWCHART.md** (Diagnostic Tool)
**Path**: `/Users/cliffclarke/Claude_Code/codebase-mcp/docs/operations/DEPLOYMENT-TROUBLESHOOTING-FLOWCHART.md`

**Purpose**: Step-by-step troubleshooting flowchart:
- 9 diagnostic sections
- Decision tree format
- Systematic problem isolation
- Section-specific solutions
- Nuclear option (full clean install)
- Debug information collection

**When to use**:
- Tests still fail after basic restart
- Mysterious deployment issues
- Server won't start
- Wrong code still running despite fixes

**Size**: ~11KB

---

## Verification Tool

### **verify-server-version.sh** (Automated Verification)
**Path**: `/Users/cliffclarke/Claude_Code/codebase-mcp/scripts/verify-server-version.sh`

**Purpose**: Automated script that checks:
1. Server is running (process check)
2. Correct Git branch (`fix/project-resolution-auto-create`)
3. Correct commit (`91c24cef`)
4. No uncommitted changes
5. Editable install present
6. Bug 2 fix code present (`config_path=config_path`)
7. Bug 3 fix code present (`result.status`)
8. Server logs exist and recent

**Usage**:
```bash
cd /Users/cliffclarke/Claude_Code/codebase-mcp
./scripts/verify-server-version.sh
```

**Output**:
- Green ✓ for passing checks
- Yellow ⚠ for warnings
- Red ✗ for failures
- Summary with actionable recommendations

**Exit codes**:
- `0`: All checks passed
- `1`: One or more checks failed

---

## Deployment Workflows

### Workflow 1: Daily Development (Most Common)

**Scenario**: You made code changes and want to test them.

**Steps**:
```bash
# 1. Make code changes
# (edit files)

# 2. Restart server (editable install picks up changes automatically)
pkill -f "codebase-mcp/run_server.py"
python run_server.py &

# 3. Verify
./scripts/verify-server-version.sh

# 4. Test your changes
```

**Reference**: `QUICK-RESTART-GUIDE.md` → Step-by-Step section

---

### Workflow 2: First Time Setup

**Scenario**: Setting up development environment for the first time.

**Steps**:
```bash
# 1. Clone repository (if not already done)
cd /Users/cliffclarke/Claude_Code
git clone <repo-url> codebase-mcp

# 2. Checkout fix branch
cd codebase-mcp
git checkout fix/project-resolution-auto-create

# 3. Create virtual environment
python3.13 -m venv .venv
source .venv/bin/activate

# 4. Install in editable mode
uv pip install -e .

# 5. Start server
python run_server.py &

# 6. Verify
./scripts/verify-server-version.sh
```

**Reference**: `MCP-SERVER-DEPLOYMENT.md` → Option 2: Install Editable Package

---

### Workflow 3: Branch Switching

**Scenario**: Switching between Git branches during development.

**Steps**:
```bash
# 1. Stop server
pkill -f "codebase-mcp/run_server.py"

# 2. Switch branch
git checkout <branch-name>

# 3. Update dependencies (if changed)
uv pip install -e .

# 4. Restart server
python run_server.py &

# 5. Verify
./scripts/verify-server-version.sh
```

**Reference**: `MCP-SERVER-DEPLOYMENT.md` → Best Practices → Branch Switching

---

### Workflow 4: Troubleshooting Failed Tests

**Scenario**: Integration tests fail, need to diagnose server deployment.

**Steps**:
```bash
# 1. Run verification
./scripts/verify-server-version.sh

# 2. If failures, follow flowchart
# See: DEPLOYMENT-TROUBLESHOOTING-FLOWCHART.md
# Start at section corresponding to first failure

# 3. Apply recommended fix

# 4. Verify again
./scripts/verify-server-version.sh

# 5. Re-run tests
```

**Reference**: `DEPLOYMENT-TROUBLESHOOTING-FLOWCHART.md` → Start Here

---

### Workflow 5: Integration with workflow-mcp

**Scenario**: Both servers need to run with correct code.

**Steps**:
```bash
# 1. Stop both servers
pkill -f "codebase-mcp/run_server.py"
pkill -f "workflow-mcp/run_server.py"

# 2. Start codebase-mcp first
cd /Users/cliffclarke/Claude_Code/codebase-mcp
python run_server.py &
sleep 3

# 3. Start workflow-mcp
cd /Users/cliffclarke/Claude_Code/workflow-mcp
python run_server.py &

# 4. Verify both
ps aux | grep -E "(codebase|workflow)-mcp/run_server.py" | grep -v grep

# 5. Check logs
tail -f /tmp/codebase-mcp.log
tail -f /tmp/workflow-mcp.log
```

**Reference**: `MCP-SERVER-DEPLOYMENT.md` → For workflow-mcp Integration

---

## Fix-Specific Information

### Bug 1: Foreground Indexing Hang
**Fixed in commit**: `38edf919`
**File changed**: `src/mcp/tools/indexing.py`
**Fix**: Move response formatting inside try block
**Test**: Call `index_repository` via MCP tool, should return without hanging

### Bug 2: Background Auto-Create from Config
**Fixed in commits**: `68ed9fad`, `00ca2314`, `972e08bf`
**Files changed**:
- `src/mcp/tools/background_indexing.py`
- `src/database/auto_create.py`
- `src/services/background_worker.py`
**Fix**: Capture and pass config_path to background worker
**Test**: Call `start_indexing_background` with repo containing `.codebase-mcp/config.json`
**Verification**: `grep "config_path=config_path" src/mcp/tools/background_indexing.py`

### Bug 3: Error Status Handling
**Fixed in commits**: `39d36d28`, `f70791d7`
**File changed**: `src/services/background_worker.py`
**Fix**: Check `IndexResult.status` before marking job completed
**Test**: Call `get_indexing_status` for failed job, should show `status="failed"`
**Verification**: `grep "result.status" src/services/background_worker.py`

---

## Key Files Reference

### Configuration Files
- **Package config**: `/Users/cliffclarke/Claude_Code/codebase-mcp/pyproject.toml`
- **Git config**: `/Users/cliffclarke/Claude_Code/codebase-mcp/.git/config`
- **workflow-mcp config**: `/Users/cliffclarke/Claude_Code/workflow-mcp/.codebase-mcp/config.json`

### Runtime Files
- **Server script**: `/Users/cliffclarke/Claude_Code/codebase-mcp/run_server.py`
- **Main server**: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/mcp/server_fastmcp.py`
- **Server logs**: `/tmp/codebase-mcp.log`
- **Startup logs**: `/tmp/codebase-mcp-startup.log`

### Source Files (Bug Fixes)
- **Indexing tool**: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/mcp/tools/indexing.py`
- **Background tool**: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/mcp/tools/background_indexing.py`
- **Background worker**: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/services/background_worker.py`
- **Auto-create**: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/database/auto_create.py`

### Documentation
- **Main deployment guide**: `docs/operations/MCP-SERVER-DEPLOYMENT.md`
- **Quick restart**: `docs/operations/QUICK-RESTART-GUIDE.md`
- **Troubleshooting flowchart**: `docs/operations/DEPLOYMENT-TROUBLESHOOTING-FLOWCHART.md`
- **Bug fix docs**: `docs/bugs/mcp-indexing-failures/COMPLETION-SUMMARY.md`

### Scripts
- **Verification**: `scripts/verify-server-version.sh`

---

## Common Commands Cheat Sheet

### Server Management
```bash
# Stop server
pkill -f "codebase-mcp/run_server.py"

# Start server (background)
python run_server.py &

# Start server (foreground, for debugging)
python run_server.py

# Check if running
ps aux | grep "codebase-mcp/run_server.py" | grep -v grep

# Restart (one-liner)
pkill -f "codebase-mcp/run_server.py" && sleep 1 && python run_server.py &
```

### Verification
```bash
# Run verification script
./scripts/verify-server-version.sh

# Check Git branch
git branch --show-current

# Check Git commit
git log --oneline -1

# Check package installation
uv pip show codebase-mcp
```

### Logs
```bash
# View server logs (last 50 lines)
tail -50 /tmp/codebase-mcp.log

# Follow server logs (real-time)
tail -f /tmp/codebase-mcp.log

# Search logs for errors
grep -i error /tmp/codebase-mcp.log

# View startup logs
cat /tmp/codebase-mcp-startup.log
```

### Package Management
```bash
# Install editable
uv pip install -e .

# Reinstall
uv pip uninstall codebase-mcp && uv pip install -e .

# Check installation
uv pip list | grep codebase

# Show package details
uv pip show codebase-mcp
```

### Git Operations
```bash
# Check branch
git branch --show-current

# Switch to fix branch
git checkout fix/project-resolution-auto-create

# Pull latest
git pull origin fix/project-resolution-auto-create

# Reset to specific commit
git reset --hard 91c24cef

# Check status
git status
```

---

## Success Criteria

Your deployment is correct when:

### 1. Verification Script Passes
```bash
./scripts/verify-server-version.sh
```
Output: `✓ All checks passed! Server is running correct code.`

### 2. All Checks Green
- ✓ Server is running (PID shown)
- ✓ On correct branch: `fix/project-resolution-auto-create`
- ✓ On correct commit: `91c24cef`
- ✓ No uncommitted changes
- ✓ Editable install detected
- ✓ Bug 2 fix present: config_path parameter
- ✓ Bug 3 fix present: IndexResult.status check
- ✓ Log file exists

### 3. Integration Tests Pass
- **Bug 1**: Foreground indexing completes without hanging
- **Bug 2**: Background indexing auto-creates project from config
- **Bug 3**: Failed jobs show `status="failed"` with error message

---

## Support and Resources

### Getting Help

1. **Start with verification**: Always run `./scripts/verify-server-version.sh` first
2. **Check logs**: `tail -f /tmp/codebase-mcp.log`
3. **Follow flowchart**: See `DEPLOYMENT-TROUBLESHOOTING-FLOWCHART.md`
4. **Collect debug info**: See flowchart Section 9

### Related Documentation

- **Bug fix details**: `docs/bugs/mcp-indexing-failures/COMPLETION-SUMMARY.md`
- **Database operations**: `docs/operations/DATABASE_RESET.md`
- **General troubleshooting**: `docs/operations/troubleshooting.md`
- **Performance monitoring**: `docs/operations/performance-tuning.md`

### External Resources

- **FastMCP documentation**: https://github.com/jlowin/fastmcp
- **MCP protocol spec**: https://modelcontextprotocol.io/
- **PostgreSQL docs**: https://www.postgresql.org/docs/

---

## Document History

- **Created**: 2025-10-18
- **Purpose**: Comprehensive deployment guide for bug fix branch
- **Branch**: `fix/project-resolution-auto-create`
- **Commit**: `91c24cef`
- **Author**: Claude Code (via investigation and documentation request)

---

## Quick Links

| Document | Purpose | When to Use |
|----------|---------|-------------|
| [MCP-SERVER-DEPLOYMENT.md](./MCP-SERVER-DEPLOYMENT.md) | Comprehensive guide | First time, deep dive |
| [QUICK-RESTART-GUIDE.md](./QUICK-RESTART-GUIDE.md) | Fast reference | Daily development |
| [DEPLOYMENT-TROUBLESHOOTING-FLOWCHART.md](./DEPLOYMENT-TROUBLESHOOTING-FLOWCHART.md) | Systematic troubleshooting | When things break |
| [verify-server-version.sh](../../scripts/verify-server-version.sh) | Automated checks | Always before testing |

---

**Pro Tip**: Bookmark this README and the verification script for quick access during development!
