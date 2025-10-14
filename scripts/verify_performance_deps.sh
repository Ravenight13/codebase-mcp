#!/bin/bash
# scripts/verify_performance_deps.sh
# Verify all performance testing dependencies are installed

set -e

echo "=================================================="
echo "Performance Testing Dependencies Verification"
echo "=================================================="
echo ""

# Track failures
FAILED=0

echo "Checking Python dependencies..."
echo "-----------------------------------"

# pytest-benchmark
if python -c "import pytest_benchmark; print(f'✓ pytest-benchmark {pytest_benchmark.__version__}')" 2>/dev/null; then
    true
else
    echo "✗ pytest-benchmark missing"
    FAILED=$((FAILED + 1))
fi

# pytest-asyncio
if python -c "import pytest_asyncio; print(f'✓ pytest-asyncio {pytest_asyncio.__version__}')" 2>/dev/null; then
    true
else
    echo "✗ pytest-asyncio missing"
    FAILED=$((FAILED + 1))
fi

# httpx
if python -c "import httpx; print(f'✓ httpx {httpx.__version__}')" 2>/dev/null; then
    true
else
    echo "✗ httpx missing"
    FAILED=$((FAILED + 1))
fi

# tiktoken (optional)
if python -c "import tiktoken; print(f'✓ tiktoken {tiktoken.__version__}')" 2>/dev/null; then
    true
else
    echo "⚠ tiktoken missing (optional)"
fi

# py-spy (optional)
if python -c "import py_spy; print(f'✓ py-spy available')" 2>/dev/null; then
    true
else
    if command -v py-spy &> /dev/null; then
        echo "✓ py-spy $(py-spy --version 2>&1 | head -1)"
    else
        echo "⚠ py-spy missing (optional)"
    fi
fi

echo ""
echo "Checking external dependencies..."
echo "-----------------------------------"

# k6
if command -v k6 &> /dev/null; then
    K6_VERSION=$(k6 version --quiet 2>&1 | head -1 | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+' || echo "unknown")
    echo "✓ k6 $K6_VERSION"
else
    echo "✗ k6 not installed"
    echo "  Install: brew install k6 (macOS) or see docs/performance/DEPENDENCIES.md"
    FAILED=$((FAILED + 1))
fi

echo ""
echo "Checking directory structure..."
echo "-----------------------------------"

# Check required directories
if [ -d "performance_baselines" ]; then
    echo "✓ performance_baselines/ exists"
else
    echo "✗ performance_baselines/ missing"
    FAILED=$((FAILED + 1))
fi

if [ -d "docs/performance" ]; then
    echo "✓ docs/performance/ exists"
else
    echo "✗ docs/performance/ missing"
    FAILED=$((FAILED + 1))
fi

if [ -d "tests/load/results" ]; then
    echo "✓ tests/load/results/ exists"
else
    echo "✗ tests/load/results/ missing"
    FAILED=$((FAILED + 1))
fi

echo ""
echo "=================================================="
if [ $FAILED -eq 0 ]; then
    echo "✓ All critical dependencies verified"
    echo "=================================================="
    exit 0
else
    echo "✗ $FAILED critical dependencies missing"
    echo "=================================================="
    echo ""
    echo "To install missing Python dependencies:"
    echo "  pip install -e '.[dev]'"
    echo ""
    echo "To install k6 (macOS):"
    echo "  brew install k6"
    echo ""
    echo "See docs/performance/DEPENDENCIES.md for details."
    exit 1
fi
