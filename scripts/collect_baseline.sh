#!/bin/bash
set -e

echo "📊 Starting baseline performance collection..."
echo ""

# Check if baseline repo exists
BASELINE_DIR="test_repos/baseline_repo"
if [ ! -d "$BASELINE_DIR" ]; then
    echo "📁 Baseline repository not found. Generating test repository..."
    python scripts/generate_test_repo.py --files 10000 --output "$BASELINE_DIR"
    echo "✅ Test repository generated"
else
    echo "✅ Baseline repository already exists at $BASELINE_DIR"
fi

echo ""
echo "🧪 Running performance benchmarks..."
pytest tests/performance/test_baseline.py --benchmark-only --benchmark-json=baseline-results.json -v

echo ""
echo "📈 Parsing and displaying results..."
python scripts/parse_baseline.py baseline-results.json

echo ""
echo "✅ Baseline collection complete! Results saved to baseline-results.json"
