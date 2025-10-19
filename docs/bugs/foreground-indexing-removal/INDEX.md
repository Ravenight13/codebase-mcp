# Foreground Indexing Removal: Documentation Update Plan

**Created**: 2025-10-18
**Status**: Planning Complete
**Total Impact**: 161 markdown files, 1,071+ references

---

## Overview

This directory contains the complete plan for updating all documentation when removing the foreground `index_repository` tool and migrating to background-only indexing.

**What's Changing**:
- ❌ **Removing**: `index_repository` MCP tool (synchronous/blocking)
- ✅ **Keeping**: `start_indexing_background`, `get_indexing_status` (async)
- 📝 **Impact**: 161 documentation files need updates

**Why**: MCP clients have 30-second timeout limits. Large repositories (10,000+ files) require 5-10 minutes to index, causing timeout failures.

---

## 📋 Quick Start

**New to this plan?** Start here:

1. **Read**: `UPDATE-SUMMARY.md` - High-level overview and statistics
2. **Review**: `DOCUMENTATION-UPDATE-PLAN.md` - Complete detailed plan
3. **Track**: `CHECKLIST.md` - Execution checklist with progress tracking
4. **Reference**: `QUICK-REFERENCE.md` - Pattern lookup guide

---

## 📁 Files in This Directory

### 1. DOCUMENTATION-UPDATE-PLAN.md (743 lines) - **THE MASTER PLAN**
Complete, detailed documentation update strategy with file-by-file instructions.

### 2. UPDATE-SUMMARY.md (263 lines) - **QUICK REFERENCE**
High-level statistics, timelines, and change patterns.

### 3. CHECKLIST.md (323 lines) - **EXECUTION TRACKER**
Task-by-task checklist with progress tracking (75 total tasks).

### 4. QUICK-REFERENCE.md (174 lines) - **PATTERN GUIDE**
Side-by-side examples of old vs new patterns for quick lookup.

### 5. DELETION-PLAN.md (534 lines) - **CODE REMOVAL**
Strategy for removing foreground implementation from codebase.

---

## 🎯 Execution Timeline

**Week 1**: Critical user-facing docs (6 files) - MUST HAVE for release
**Week 2**: Operations and architecture (30 files) - SHOULD HAVE
**Week 3**: Archives and code cleanup (39 files + code) - NICE TO HAVE

**Total Effort**: 3 weeks (1 developer)

---

## 📊 Impact by Priority

- 🔴 HIGH (15 files): User-facing documentation
- 🟡 MEDIUM (25 files): Developer/operations documentation  
- ⚪ LOW (121 files): Historical/archived documentation

**Total**: 161 markdown files + 50+ Python files

---

## Next Steps

1. Review all planning documents
2. Approve timeline and priorities
3. Execute Phase 1 (critical docs)
4. Track progress in CHECKLIST.md
5. Validate after each phase

See individual files for details.
