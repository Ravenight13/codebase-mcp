#!/bin/bash
set -e

echo ""
echo "=========================================="
echo "⚠️  EMERGENCY ROLLBACK TO PRE-REFACTOR"
echo "=========================================="
echo ""
echo "This script will:"
echo "  1. Stash any uncommitted changes"
echo "  2. Switch to main branch"
echo "  3. Reset to backup-before-refactor tag"
echo ""
echo "⚠️  WARNING: This will discard all refactor work!"
echo ""

# Require confirmation
read -p "Are you sure you want to proceed? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "❌ Rollback cancelled"
    exit 1
fi

echo ""
echo "🔍 Running pre-flight checks..."

# Verify backup tag exists
if ! git rev-parse backup-before-refactor >/dev/null 2>&1; then
    echo "❌ ERROR: backup-before-refactor tag not found"
    echo "   Cannot proceed with rollback without backup tag"
    exit 1
fi

BACKUP_COMMIT=$(git rev-parse backup-before-refactor)
echo "✅ Backup tag found at commit: $BACKUP_COMMIT"
git log -1 --oneline backup-before-refactor
echo ""

# Stash uncommitted changes
echo "💾 Stashing uncommitted changes..."
if git stash push -m "Emergency rollback stash $(date +%Y-%m-%d_%H:%M:%S)"; then
    echo "✅ Changes stashed"
else
    echo "✅ No changes to stash"
fi
echo ""

# Checkout main
echo "🔄 Switching to main branch..."
git checkout main
echo "✅ On main branch"
echo ""

# Reset to backup tag
echo "⏮️  Resetting to backup-before-refactor..."
git reset --hard backup-before-refactor
echo "✅ Reset complete"
echo ""

echo "=========================================="
echo "✅ EMERGENCY ROLLBACK COMPLETE"
echo "=========================================="
echo ""
echo "Current commit:"
git log -1 --oneline
echo ""
echo "Your repository has been restored to pre-refactor state."
echo "Stashed changes can be recovered with: git stash list"
