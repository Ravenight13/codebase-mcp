#!/usr/bin/env python3
"""Correctly insert T033b and renumber all subsequent tasks."""

import re

# Read the original file
with open('tasks.md', 'r') as f:
    content = f.read()

# First, renumber all tasks from T034 onwards to make room for T033b
# We need to renumber T034->T035, T035->T036, ..., T084->T085
# Do this in REVERSE order to avoid double-replacements
for old_num in range(84, 33, -1):  # From T084 down to T034
    new_num = old_num + 1
    old_id = f"T{old_num:03d}"
    new_id = f"T{new_num:03d}"

    # Replace task headers: **T034**
    content = re.sub(rf'(\*\*){old_id}(\*\*)', rf'\1{new_id}\2', content)

    # Replace task references in text (dependencies, blockers, etc.)
    # Be very careful to match word boundaries
    content = re.sub(rf'\b{old_id}\b', new_id, content)

# Now insert T033b after T033
t033b_text = """
- [ ] **T033b** [UPDATE] Fix pyproject.toml entry point
  - File: `pyproject.toml`
  - Action: Change entry point from `codebase-mcp = "src.main:main"` to `codebase-mcp = "src.mcp.server_fastmcp:main"`
  - Rationale: Current entry point references non-existent src/main.py file
  - Dependencies: T032 commit complete
"""

# Find T033 and insert T033b after it
t033_pattern = r'(- \[ \] \*\*T033\*\* \[UPDATE\] Remove deleted tool imports from server\.py.*?Dependencies: T032 commit complete\n)'
match = re.search(t033_pattern, content, re.DOTALL)

if match:
    insert_pos = match.end()
    content = content[:insert_pos] + t033b_text + content[insert_pos:]
else:
    print("ERROR: Could not find T033 in the file!")
    exit(1)

# Update T038 git commit command to include pyproject.toml and update file count
# T037 became T038 after renumbering
content = re.sub(
    r'(- \[ \] \*\*T038\*\* \[GIT\] Commit Sub-Phase 3 cleanup\n.*?Command: `git add src/mcp/server_fastmcp\.py )',
    r'\1pyproject.toml ',
    content,
    flags=re.DOTALL
)

# Update files count in T038
content = re.sub(
    r'(- \[ \] \*\*T038\*\* \[GIT\] Commit Sub-Phase 3 cleanup.*?Files: )4 updates \(server\.py, README\.md, 2 __init__\.py files\)',
    r'\g<1>5 updates (server.py, pyproject.toml, README.md, 2 __init__.py files)',
    content,
    flags=re.DOTALL
)

# Update dependencies in T038 to include T033b
content = re.sub(
    r'(- \[ \] \*\*T038\*\* \[GIT\] Commit Sub-Phase 3 cleanup.*?Dependencies: T033-)T037 complete',
    r'\g<1>T037 complete',
    content,
    flags=re.DOTALL
)

# Update task count at the end
content = re.sub(
    r'\*\*Task Count\*\*: 84 tasks',
    '**Task Count**: 85 tasks',
    content
)

content = re.sub(
    r'84 tasks \(3 baseline \+ 6 sub-phase 1 \+ 23 sub-phase 2 \+ 5 sub-phase 3 \+ 47 sub-phase 4\)',
    '85 tasks (3 baseline + 6 sub-phase 1 + 23 sub-phase 2 + 6 sub-phase 3 + 47 sub-phase 4)',
    content
)

# Update total tasks count
content = re.sub(
    r'\*\*Total Tasks\*\*: 84 tasks',
    '**Total Tasks**: 85 tasks',
    content
)

# Update Phase 3.4 task count
content = re.sub(
    r'- Phase 3\.4 \(Sub-Phase 3\): 5 tasks',
    '- Phase 3.4 (Sub-Phase 3): 6 tasks',
    content
)

# Update deletion scope file count
content = re.sub(
    r'4 files updated',
    '5 files updated',
    content
)

# Update dependencies graph
content = re.sub(
    r'T032 → T033,T035,T036,T037 \(cleanup imports\) → T038 \(commit\)',
    'T032 → T033,T033b,T035,T036,T037 (cleanup imports) → T038 (commit)',
    content
)

# Write the updated content
with open('tasks.md', 'w') as f:
    f.write(content)

print("Successfully inserted T033b and renumbered all subsequent tasks!")
print("Changes:")
print("- Inserted T033b after T033")
print("- Renumbered T034->T035, T035->T036, ..., T084->T085")
print("- Updated T038 git command to include pyproject.toml")
print("- Updated T038 file count from 4 to 5")
print("- Updated task counts (84 -> 85 total, Sub-Phase 3: 5 -> 6)")
print("- Updated dependencies graph")
