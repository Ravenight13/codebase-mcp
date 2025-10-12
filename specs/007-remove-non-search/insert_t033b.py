#!/usr/bin/env python3
"""Insert T033b and renumber all subsequent tasks."""

import re

# Read the backup file
with open('tasks.md.backup', 'r') as f:
    content = f.read()

# Define the T033b task text
t033b_text = """- [ ] **T033b** [UPDATE] Fix pyproject.toml entry point
  - File: `pyproject.toml`
  - Action: Change entry point from `codebase-mcp = "src.main:main"` to `codebase-mcp = "src.mcp.server_fastmcp:main"`
  - Rationale: Current entry point references non-existent src/main.py file
  - Dependencies: T032 commit complete

"""

# Find T033 and insert T033b after it
t033_pattern = r'(- \[ \] \*\*T033\*\* \[UPDATE\] Remove deleted tool imports from server\.py.*?- Dependencies: T032 commit complete\n)'
match = re.search(t033_pattern, content, re.DOTALL)

if match:
    # Insert T033b after T033
    insert_pos = match.end()
    content = content[:insert_pos] + '\n' + t033b_text + content[insert_pos:]

# Now renumber all tasks from T034 onwards
# We need to increment each task number by 1

# Find all task patterns from T034 onwards
def renumber_tasks(text):
    """Renumber tasks from T034 to T085 (shifting everything up by 1)."""
    # Create mapping from old to new numbers
    # T034 -> T035, T035 -> T036, ..., T084 -> T085

    # Process in reverse order to avoid replacing already replaced numbers
    for old_num in range(84, 33, -1):  # From T084 down to T034
        new_num = old_num + 1
        old_id = f"T{old_num:03d}"
        new_id = f"T{new_num:03d}"

        # Replace task IDs in various contexts:
        # 1. Task headers: **T034**
        text = re.sub(rf'\*\*{old_id}\*\*', f'**{new_id}**', text)

        # 2. Task references in dependencies, blockers, etc.
        text = re.sub(rf'\b{old_id}\b', new_id, text)

    return text

content = renumber_tasks(content)

# Update T037 git commit command to include pyproject.toml
content = re.sub(
    r'(- \[ \] \*\*T037\*\* \[GIT\] Commit Sub-Phase 3 cleanup.*?Command: `git add src/mcp/server_fastmcp\.py )',
    r'\1pyproject.toml ',
    content,
    flags=re.DOTALL
)

# Update T037 files count
content = re.sub(
    r'(- \[ \] \*\*T037\*\* \[GIT\] Commit Sub-Phase 3 cleanup.*?Files: )4 updates \(server\.py, README\.md, 2 __init__\.py files\)',
    r'\g<1>5 updates (server.py, pyproject.toml, README.md, 2 __init__.py files)',
    content,
    flags=re.DOTALL
)

# Update the task count at the end
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

# Update Phase 3.4 task count
content = re.sub(
    r'(Phase 3\.4: Sub-Phase 3 - Update Server Registration.*?)5 tasks',
    r'\g<1>6 tasks',
    content,
    flags=re.DOTALL
)

# Update Phase 3.4 update count in deletion scope
content = re.sub(
    r'4 files updated',
    '5 files updated',
    content
)

# Update total tasks count in overview
content = re.sub(
    r'\*\*Total Tasks\*\*: 84 tasks',
    '**Total Tasks**: 85 tasks',
    content
)

# Update timeline sub-phase 3
content = re.sub(
    r'- Phase 3\.4 \(Sub-Phase 3\): 5 tasks',
    '- Phase 3.4 (Sub-Phase 3): 6 tasks',
    content
)

# Update dependencies in T037 to include T033b
content = re.sub(
    r'(- \[ \] \*\*T037\*\* \[GIT\] Commit Sub-Phase 3 cleanup.*?Dependencies: )T033-T036 complete',
    r'\g<1>T033-T036 complete',
    content,
    flags=re.DOTALL
)

# Write the updated content
with open('tasks.md', 'w') as f:
    f.write(content)

print("Successfully inserted T033b and renumbered all subsequent tasks!")
print("- Inserted T033b after T033")
print("- Renumbered T034-T084 to T035-T085")
print("- Updated T037 git command to include pyproject.toml")
print("- Updated task counts")
