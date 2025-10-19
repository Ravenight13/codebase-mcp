#!/bin/bash
# Verification script to check if codebase-mcp server is running the correct code
# Usage: ./scripts/verify-server-version.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Expected values for fix branch
EXPECTED_BRANCH="fix/project-resolution-auto-create"
EXPECTED_COMMIT="91c24cef"  # First 8 chars of commit hash
REPO_ROOT="/Users/cliffclarke/Claude_Code/codebase-mcp"

echo "=========================================="
echo "Codebase MCP Server Version Verification"
echo "=========================================="
echo ""

# 1. Check if server is running
echo "1. Checking if server is running..."
if ps aux | grep -v grep | grep "codebase-mcp/run_server.py" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Server is running${NC}"
    SERVER_PID=$(ps aux | grep -v grep | grep "codebase-mcp/run_server.py" | awk '{print $2}' | head -1)
    echo "  PID: $SERVER_PID"
else
    echo -e "${RED}✗ Server is NOT running${NC}"
    echo "  Run: python run_server.py &"
    exit 1
fi
echo ""

# 2. Check current branch
echo "2. Checking Git branch..."
cd "$REPO_ROOT"
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" = "$EXPECTED_BRANCH" ]; then
    echo -e "${GREEN}✓ On correct branch: $CURRENT_BRANCH${NC}"
else
    echo -e "${YELLOW}⚠ On branch: $CURRENT_BRANCH (expected: $EXPECTED_BRANCH)${NC}"
fi
echo ""

# 3. Check current commit
echo "3. Checking Git commit..."
CURRENT_COMMIT=$(git log --oneline -1 | awk '{print $1}')
if [ "$CURRENT_COMMIT" = "$EXPECTED_COMMIT" ]; then
    echo -e "${GREEN}✓ On correct commit: $CURRENT_COMMIT${NC}"
else
    echo -e "${YELLOW}⚠ On commit: $CURRENT_COMMIT (expected: $EXPECTED_COMMIT)${NC}"
fi
git log --oneline -1
echo ""

# 4. Check for uncommitted changes
echo "4. Checking for uncommitted changes..."
if git diff-index --quiet HEAD --; then
    echo -e "${GREEN}✓ No uncommitted changes${NC}"
else
    echo -e "${YELLOW}⚠ Uncommitted changes detected${NC}"
    git status --short
fi
echo ""

# 5. Check editable install
echo "5. Checking package installation..."
if uv pip show codebase-mcp > /dev/null 2>&1; then
    # Check if it's an editable install
    if uv pip show codebase-mcp | grep -q "Editable project location:"; then
        EDITABLE_LOC=$(uv pip show codebase-mcp | grep "Editable project location:" | cut -d: -f2- | xargs)
        echo -e "${GREEN}✓ Editable install detected${NC}"
        echo "  Location: $EDITABLE_LOC"
    else
        INSTALL_LOC=$(uv pip show codebase-mcp | grep "Location:" | awk '{print $2}')
        echo -e "${YELLOW}⚠ Non-editable install from: $INSTALL_LOC${NC}"
        echo "  Recommended: uv pip install -e ."
    fi
else
    echo -e "${RED}✗ codebase-mcp package not found${NC}"
    echo "  Run: uv pip install -e ."
fi
echo ""

# 6. Check for fix-specific code
echo "6. Verifying fix-specific code is present..."

# Bug 2 fix: config_path parameter
if grep -q "config_path=config_path" "$REPO_ROOT/src/mcp/tools/background_indexing.py"; then
    echo -e "${GREEN}✓ Bug 2 fix present: config_path parameter${NC}"
else
    echo -e "${RED}✗ Bug 2 fix MISSING: config_path parameter not found${NC}"
fi

# Bug 3 fix: IndexResult.status check
if grep -q "result.status" "$REPO_ROOT/src/services/background_worker.py"; then
    echo -e "${GREEN}✓ Bug 3 fix present: IndexResult.status check${NC}"
else
    echo -e "${RED}✗ Bug 3 fix MISSING: IndexResult.status check not found${NC}"
fi
echo ""

# 7. Check server logs
echo "7. Checking server logs..."
if [ -f "/tmp/codebase-mcp.log" ]; then
    echo -e "${GREEN}✓ Log file exists: /tmp/codebase-mcp.log${NC}"

    # Check for recent startup
    if grep -q "FastMCP Server Initialization" /tmp/codebase-mcp.log; then
        LAST_STARTUP=$(grep "FastMCP Server Initialization" /tmp/codebase-mcp.log | tail -1)
        echo "  Last startup: $(echo "$LAST_STARTUP" | awk '{print $1, $2}')"
    fi
else
    echo -e "${YELLOW}⚠ Log file not found: /tmp/codebase-mcp.log${NC}"
fi
echo ""

# 8. Summary
echo "=========================================="
echo "Summary"
echo "=========================================="

ISSUES=0

if ! ps aux | grep -v grep | grep "codebase-mcp/run_server.py" > /dev/null 2>&1; then
    ISSUES=$((ISSUES + 1))
    echo -e "${RED}✗ Server not running${NC}"
fi

if [ "$CURRENT_BRANCH" != "$EXPECTED_BRANCH" ]; then
    ISSUES=$((ISSUES + 1))
    echo -e "${YELLOW}⚠ Wrong branch${NC}"
fi

if [ "$CURRENT_COMMIT" != "$EXPECTED_COMMIT" ]; then
    ISSUES=$((ISSUES + 1))
    echo -e "${YELLOW}⚠ Different commit${NC}"
fi

if ! git diff-index --quiet HEAD --; then
    ISSUES=$((ISSUES + 1))
    echo -e "${YELLOW}⚠ Uncommitted changes${NC}"
fi

if ! grep -q "config_path=config_path" "$REPO_ROOT/src/mcp/tools/background_indexing.py"; then
    ISSUES=$((ISSUES + 1))
    echo -e "${RED}✗ Bug 2 fix missing${NC}"
fi

if ! grep -q "result.status" "$REPO_ROOT/src/services/background_worker.py"; then
    ISSUES=$((ISSUES + 1))
    echo -e "${RED}✗ Bug 3 fix missing${NC}"
fi

echo ""
if [ $ISSUES -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed! Server is running correct code.${NC}"
    echo ""
    echo "Next steps:"
    echo "  - Run integration tests to verify fixes"
    echo "  - Monitor logs: tail -f /tmp/codebase-mcp.log"
    exit 0
else
    echo -e "${RED}✗ $ISSUES issue(s) detected${NC}"
    echo ""
    echo "Recommended actions:"
    echo "  1. Kill server: pkill -f 'codebase-mcp/run_server.py'"
    echo "  2. Checkout fix branch: git checkout fix/project-resolution-auto-create"
    echo "  3. Restart server: python run_server.py &"
    echo "  4. Re-run this script: ./scripts/verify-server-version.sh"
    exit 1
fi
