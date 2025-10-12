# Git Strategy: Branch and Commit Management

## Overview

The MCP split project follows a disciplined git workflow with micro-commits, Conventional Commits format, and feature-branch development. This strategy ensures traceability, atomic changes, and clean git history.

---

## Branch Strategy

### Branch Naming Convention

**Format:** `###-feature-name`
- **###:** 3-digit zero-padded feature number (e.g., 004, 015, 123)
- **feature-name:** Abbreviated description (max 3-4 words, lowercase, hyphens)

**Examples:**
- ✅ `004-multi-project-search`
- ✅ `005-project-isolation`
- ✅ `006-cache-performance`
- ❌ `multi-project` (missing number)
- ❌ `004_multi_project_search` (use hyphens, not underscores)
- ❌ `004-add-multi-project-support-for-semantic-search` (too long)

### Branch Creation

**Always create from main:**
```bash
# Ensure main is up to date
git checkout main
git pull origin main

# Create feature branch
git checkout -b 004-multi-project-search

# Verify branch created
git branch --show-current
# Output: 004-multi-project-search
```

**Branch lifespan:**
- Created at start of feature development (during `/specify`)
- Maintained throughout `/plan`, `/tasks`, `/implement` workflow
- Deleted after PR merge (squash or preserve commits - see below)

### Branch Protection

**Main branch rules:**
- No direct commits to main
- All changes via pull requests
- Require passing tests before merge
- Require code review (if team workflow)

---

## Commit Strategy

### Micro-Commit Philosophy

**Principle:** One task = one commit

Each task in `tasks.md` maps to exactly one commit. Commits are:
- **Atomic:** Single logical change
- **Working:** All tests pass (or at least don't break existing tests)
- **Focused:** One concern per commit (no mixing unrelated changes)
- **Traceable:** Commit message references task number

**Benefits:**
- Easy to review (small diffs)
- Easy to revert (isolate problematic changes)
- Clear history (each commit has clear purpose)
- Enables git bisect for debugging

### Conventional Commits Format

**Structure:**
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Type:** Describes the nature of the change
- `feat`: New feature or capability
- `fix`: Bug fix
- `refactor`: Code restructure without behavior change
- `test`: Adding or updating tests
- `docs`: Documentation changes
- `perf`: Performance improvements
- `chore`: Build process, dependencies, tooling
- `style`: Formatting, whitespace (no logic change)
- `ci`: CI/CD configuration changes

**Scope:** Component or module affected (optional but recommended)
- `search`: Search-related code
- `indexing`: Indexing functionality
- `cache`: Caching layer
- `schema`: Database schema
- `mcp`: MCP protocol implementation
- `api`: API contracts
- `project`: Project management features

**Description:** Short summary (50 chars max)
- Imperative mood ("add" not "added" or "adds")
- Lowercase first letter
- No period at end

**Examples:**
```bash
# Good
feat(search): add project_id filtering with isolation
fix(cache): handle expired entries correctly
refactor(indexing): extract chunk creation logic
test(mcp): add protocol compliance validation
docs(api): update search_code tool documentation

# Bad
feat: added some features  # Too vague, wrong tense
Fix Cache Bug  # Capitalize only type, missing scope
refactor(search): add project support and fix bugs and update tests  # Too broad
```

### Commit Body (Optional)

Use body for additional context:
```
feat(search): add project_id filtering with isolation

Implements multi-project search by adding project_id parameter
to search_code tool. Falls back to active project if not provided.

Includes:
- Project ID validation (UUID format)
- MCP error handling for invalid/missing projects
- Performance optimizations (composite index)

Performance: <5ms overhead for project filtering
```

**When to use body:**
- Complex changes needing explanation
- Performance implications
- Breaking changes
- Migration notes

### Commit Footer (Optional)

Use footer for metadata:
```
feat(search): add project_id filtering

BREAKING CHANGE: index_repository now requires project_id parameter

Closes #42
Refs #38, #41
```

**Common footers:**
- `BREAKING CHANGE:` - Indicates breaking API change
- `Closes #N` - Links to issue (auto-closes on merge)
- `Refs #N` - References related issues
- `Co-authored-by:` - Multiple authors

---

## Example Commit Sequence

### Feature: Multi-Project Search (004-multi-project-search)

#### Phase 1: Database Schema
```bash
# Task T001: Migration
git add src/database/migrations/008_add_project_support.sql
git commit -m "feat(schema): add project_id columns for multi-project support"

# Task T002: Cache implementation
git add src/cache/project_cache.py tests/test_project_cache.py
git commit -m "feat(cache): add LRU cache with TTL for active project resolution"
```

#### Phase 2: Test-Driven Development
```bash
# Task T003: Integration test (RED)
git add tests/test_multi_project_search.py
git commit -m "test(search): add multi-project isolation integration test"

# Task T004: Validation test (RED)
git add tests/test_search_validation.py
git commit -m "test(search): add project_id validation tests"

# Task T005: Implementation (GREEN)
git add src/tools/search_code.py
git commit -m "feat(search): add project_id filtering with MCP error handling"

# Task T006: Cache test (RED)
git add tests/test_active_project.py
git commit -m "test(project): add active project cache performance test"

# Task T007: Cache usage (GREEN)
git add src/helpers/project_helper.py
git commit -m "feat(project): implement active project caching with <5ms overhead"

# Task T008: Refactor (REFACTOR)
git add src/tools/index_repository.py
git commit -m "refactor(indexing): add required project_id parameter"
```

#### Phase 3: Integration & Edge Cases
```bash
# Task T009: Project switching test
git add tests/test_project_switching.py
git commit -m "test(project): add project switching cache invalidation test"

# Task T010: Edge case test
git add tests/test_edge_cases.py
git commit -m "test(search): add edge case test for missing project context"

# Task T011: Deletion behavior test
git add tests/test_project_lifecycle.py
git commit -m "test(lifecycle): add project deletion soft-delete test"

# Task T012: MCP compliance test
git add tests/test_mcp_compliance.py
git commit -m "test(mcp): add protocol compliance validation for search tool"

# Final: Documentation update
git add docs/api/search-tool.md
git commit -m "docs(api): update search_code documentation for multi-project support"
```

**Total Commits:** 13 (one per task + final docs)

---

## Commit Workflow

### 1. Before Starting a Task

```bash
# Ensure branch is up to date
git status
# Should show: On branch 004-multi-project-search

# Pull any remote changes (if collaborating)
git pull origin 004-multi-project-search
```

### 2. During Task Implementation

**Make changes incrementally:**
```bash
# Edit files
vim src/tools/search_code.py

# Check what changed
git diff

# Stage specific files (not `git add .` unless you're sure)
git add src/tools/search_code.py

# Review staged changes
git diff --staged
```

### 3. Before Committing

**Verify working state:**
```bash
# Run relevant tests
pytest tests/test_search_validation.py -v

# Verify no syntax errors
python -m py_compile src/tools/search_code.py

# Check for unintended changes
git status
```

**If tests fail:**
- Fix the issue before committing
- Each commit should maintain working state
- Exception: RED phase tests (expected to fail)

### 4. Making the Commit

```bash
# Commit with descriptive message
git commit -m "feat(search): add project_id filtering with MCP error handling"

# Or use editor for multi-line message
git commit
# Opens editor for:
# feat(search): add project_id filtering with MCP error handling
#
# Implements multi-project search by adding project_id parameter
# to search_code tool. Falls back to active project if not provided.
```

### 5. After Committing

**Verify commit:**
```bash
# Check last commit
git log -1 --oneline
# Output: abc1234 feat(search): add project_id filtering with MCP error handling

# Verify commit content
git show HEAD

# Check commit message format
git log --oneline -1
# Verify: type(scope): description format
```

**Push to remote:**
```bash
# Push after each commit (or batch multiple)
git push origin 004-multi-project-search

# First push (set upstream)
git push -u origin 004-multi-project-search
```

---

## Handling Mistakes

### Amend Last Commit (Before Push)

**Fix commit message:**
```bash
git commit --amend -m "feat(search): add project_id filtering with isolation"
```

**Add forgotten files:**
```bash
git add tests/test_search.py
git commit --amend --no-edit
```

**Warning:** Only amend if commit not pushed. If pushed, force push required:
```bash
git push origin 004-multi-project-search --force-with-lease
```

### Undo Last Commit (Keep Changes)

```bash
# Undo commit, keep changes staged
git reset --soft HEAD~1

# Undo commit, keep changes unstaged
git reset HEAD~1

# Undo commit, discard changes (DESTRUCTIVE)
git reset --hard HEAD~1
```

### Fix Commit Message After Push

**If commit already pushed to shared branch:**
```bash
# Create new commit fixing the issue
git commit --allow-empty -m "docs: fix previous commit message typo"
```

**Don't rewrite history on shared branches!**

---

## Pull Request Strategy

### When to Create PR

**Feature complete criteria:**
- All tasks in tasks.md marked `[X]`
- All tests passing
- All acceptance criteria met
- Documentation updated
- No temporary/debug code remaining

### PR Title

**Format:** Same as commit message for main feature
```
feat(search): add multi-project support with isolation
```

**Or more descriptive:**
```
Multi-Project Search Support (004-multi-project-search)
```

### PR Description Template

```markdown
## Summary
Brief description of feature (2-3 sentences)

## Related Issue
Closes #42

## Changes
- Added project_id filtering to search_code tool
- Implemented active project caching (<5ms overhead)
- Added multi-project integration tests
- Updated database schema with project_id columns

## Test Plan
- [x] Multi-project isolation test passes
- [x] Active project fallback works correctly
- [x] Edge cases handled (missing project, invalid UUID)
- [x] MCP protocol compliance validated
- [x] Performance targets met (<500ms p95)

## Performance Impact
- Search latency: +5ms (cache hit), +50ms (cache miss)
- Index size: +3% per project
- Database: New indexes created (no migration downtime)

## Breaking Changes
- index_repository now requires project_id parameter

## Deployment Notes
- Run migration 008_add_project_support.sql before deploying
- Requires workflow-mcp v2.0+ for active project integration

## Checklist
- [x] Tests passing
- [x] Documentation updated
- [x] CLAUDE.md updated (if workflow changes)
- [x] No debug/temporary code
- [x] Commit messages follow Conventional Commits
- [x] Constitutional principles complied with
```

### Merge Strategy Options

#### Option 1: Squash Merge
**When to use:** Feature commits are noisy or experimental

**Pros:**
- Clean main branch history (one commit per feature)
- Easy to revert entire feature
- Simplifies git log

**Cons:**
- Loses granular commit history
- Harder to understand implementation evolution
- Git bisect less effective

**Example:**
```bash
# 13 commits on feature branch → 1 commit on main
git checkout main
git merge --squash 004-multi-project-search
git commit -m "feat(search): add multi-project support with isolation (#42)"
```

#### Option 2: Preserve Commits (Recommended)
**When to use:** Commits follow micro-commit strategy and are well-formatted

**Pros:**
- Full traceability (each task visible in history)
- Easier to understand implementation steps
- Better for git bisect debugging
- Shows TDD progression (RED-GREEN-REFACTOR)

**Cons:**
- More commits in main branch history
- Requires disciplined commit messages

**Example:**
```bash
# 13 commits on feature branch → 13 commits on main
git checkout main
git merge --no-ff 004-multi-project-search
# Creates merge commit referencing PR
```

**Recommended for this project:** Preserve commits (due to disciplined workflow)

---

## Git History Best Practices

### Keep Commits Focused

**Good (focused):**
```bash
# Commit 1
feat(cache): add ProjectCache class

# Commit 2
test(cache): add cache expiration tests

# Commit 3
feat(search): integrate ProjectCache into search_code
```

**Bad (unfocused):**
```bash
# Commit 1 (mixing concerns)
feat(cache): add cache, update search, fix bug, add tests
```

### Write Meaningful Commit Messages

**Good:**
```
feat(search): add project_id filtering with isolation

Adds project_id parameter to search_code tool for multi-project
support. Results now filtered by project_id at database level
using composite index for performance.

Performance: <5ms overhead per query
```

**Bad:**
```
update search
```

### Use Imperative Mood

**Good:**
- "add feature"
- "fix bug"
- "refactor code"

**Bad:**
- "added feature"
- "fixing bug"
- "refactors code"

**Rationale:** Git itself uses imperative ("Merge branch", "Revert commit")

---

## Working State Principle

### Every Commit Should Be a Working State

**Definition:** After checking out any commit, the codebase should:
- Compile without errors
- Pass existing tests (or explicitly be RED phase)
- Not break core functionality

**Exceptions:**
- RED phase commits (tests intentionally fail)
- Mark with prefix: `test(search): add failing test for project isolation [RED]`

**Verification:**
```bash
# After each commit
pytest tests/ --maxfail=1  # Stop at first failure
```

**Benefits:**
- Git bisect works reliably
- Easy to revert to known-good state
- Code review easier (each commit reviewable independently)

---

## Example: Full Feature Git Workflow

### Setup Phase
```bash
# Start from clean main
git checkout main
git pull origin main

# Create feature branch
git checkout -b 004-multi-project-search

# Verify starting point
git log -1 --oneline
# abc1234 Previous feature merged
```

### Implementation Phase
```bash
# Task T001
vim src/database/migrations/008_add_project_support.sql
git add src/database/migrations/
git commit -m "feat(schema): add project_id columns for multi-project support"
pytest tests/test_schema.py -v
git push origin 004-multi-project-search

# Task T002
vim src/cache/project_cache.py
vim tests/test_project_cache.py
git add src/cache/ tests/test_project_cache.py
git commit -m "feat(cache): add LRU cache with TTL for active project resolution"
pytest tests/test_project_cache.py -v
git push origin 004-multi-project-search

# ... continue for all tasks ...
```

### Completion Phase
```bash
# Mark all tasks complete in tasks.md
vim specs/004-multi-project-search/tasks.md
git add specs/004-multi-project-search/tasks.md
git commit -m "docs(tasks): mark all tasks complete"

# Update documentation
vim docs/api/search-tool.md
git add docs/api/
git commit -m "docs(api): update search_code documentation for multi-project support"

# Final verification
pytest tests/ --cov=src --cov-report=html
git push origin 004-multi-project-search

# Create PR
gh pr create --title "feat(search): add multi-project support with isolation" \
  --body "$(cat <<EOF
## Summary
Adds multi-project support to semantic code search with database-level isolation.

## Changes
- Added project_id columns to repositories and code_chunks tables
- Implemented active project caching (<5ms overhead)
- Updated search_code and index_repository tools
- Added comprehensive test coverage (MCP compliance + integration)

## Test Plan
- [x] Multi-project isolation validated
- [x] Performance targets met (<500ms p95)
- [x] MCP protocol compliance verified

## Breaking Changes
- index_repository now requires project_id parameter

## Deployment
- Run migration 008 before deploying
- Requires workflow-mcp v2.0+

Closes #42
EOF
)"
```

### Post-Merge Cleanup
```bash
# After PR merged
git checkout main
git pull origin main

# Delete feature branch
git branch -d 004-multi-project-search
git push origin --delete 004-multi-project-search
```

---

## Common Scenarios

### Scenario 1: Multiple Developers on Same Branch

**Not recommended** (use separate branches and integrate)

**If necessary:**
```bash
# Pull before starting each task
git pull origin 004-multi-project-search

# Push immediately after each commit
git commit -m "feat(search): add filtering"
git push origin 004-multi-project-search

# Handle conflicts
git pull --rebase origin 004-multi-project-search
# Resolve conflicts, then:
git rebase --continue
git push origin 004-multi-project-search
```

### Scenario 2: Need to Update from Main During Feature Work

```bash
# Save current work
git stash

# Update from main
git checkout main
git pull origin main

# Rebase feature branch
git checkout 004-multi-project-search
git rebase main

# Restore work
git stash pop

# Test everything still works
pytest tests/ -v
```

### Scenario 3: Discovered Bug During Feature Work

**Option A: Fix in same branch (if related to feature)**
```bash
git add src/tools/search_code.py
git commit -m "fix(search): handle null project_id correctly"
```

**Option B: Fix in separate branch (if unrelated)**
```bash
# Stash feature work
git stash

# Create bugfix branch from main
git checkout main
git checkout -b hotfix-search-null-handling

# Fix bug
git add src/tools/search_code.py
git commit -m "fix(search): handle null project_id in legacy code"
git push origin hotfix-search-null-handling

# Create PR, merge

# Return to feature work
git checkout 004-multi-project-search
git rebase main  # Pick up the fix
git stash pop
```

---

## Git Hygiene Checklist

**Before Each Commit:**
- [ ] Only relevant changes staged (no accidental files)
- [ ] Tests pass (or RED phase explicitly marked)
- [ ] No debug code, print statements, commented code
- [ ] Commit message follows Conventional Commits format
- [ ] Commit is focused (single concern)

**Before Push:**
- [ ] All commits have meaningful messages
- [ ] No merge commits (use rebase if needed)
- [ ] Branch is up to date with remote
- [ ] No sensitive data (credentials, API keys)

**Before PR:**
- [ ] All tests passing
- [ ] All tasks in tasks.md marked complete
- [ ] Documentation updated
- [ ] PR description complete
- [ ] No WIP or temporary commits

---

## Summary

**Key Principles:**
1. **One task = one commit** (micro-commit strategy)
2. **Conventional Commits format** (type(scope): description)
3. **Feature branches** (###-feature-name)
4. **Working state** (each commit is stable)
5. **Preserve commits on merge** (for traceability)

**Typical Feature Workflow:**
```
Create branch → Implement tasks (one commit each) → Push regularly →
Create PR → Review → Merge (preserve commits) → Delete branch
```

**Time Efficiency:**
- Micro-commits: ~1-2 min per commit (quick, focused)
- No need for interactive rebase/squash (preserve as-is)
- Clear history enables fast debugging (git bisect)

**Quality Benefits:**
- Traceability: Each task visible in git history
- Reviewability: Small, focused commits easy to review
- Revertability: Can revert individual tasks if needed
- Debuggability: Git bisect works reliably with working states
