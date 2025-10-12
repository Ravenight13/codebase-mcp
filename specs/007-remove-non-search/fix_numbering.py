#!/usr/bin/env python3
"""Fix the task numbering - T034 should not have been renamed."""

import re

# Read the current (incorrectly numbered) file
with open('tasks.md', 'r') as f:
    content = f.read()

# T035-T037 should be T034-T036, but T038-T085 stay as is
# So we need to:
# 1. T035 -> T034 (database README)
# 2. T036 -> T035 (model init)
# 3. T037 -> T036 (service init)
# 4. T038 -> T037 (git commit)
# 5. T039-T085 -> T038-T084

# Do this in reverse order to avoid double-replacements
replacements = [
    # From T085 down to T039, shift down by 1
    *[(f"T{i:03d}", f"T{i-1:03d}") for i in range(85, 38, -1)],
    # T038 -> T037
    ("T038", "T037"),
    # T037 -> T036
    ("T037", "T036"),
    # T036 -> T035
    ("T036", "T035"),
    # T035 -> T034
    ("T035", "T034"),
]

# Apply replacements
for old, new in replacements:
    # Replace task headers
    content = re.sub(rf'\*\*{old}\*\*', f'**{new}**', content)
    # Replace task references (but be careful not to replace partial matches)
    content = re.sub(rf'\b{old}\b', new, content)

# Update task counts back to 84
content = re.sub(r'\*\*Task Count\*\*: 85 tasks', '**Task Count**: 84 tasks', content)
content = re.sub(
    r'85 tasks \(3 baseline \+ 6 sub-phase 1 \+ 23 sub-phase 2 \+ 6 sub-phase 3 \+ 47 sub-phase 4\)',
    '84 tasks (3 baseline + 6 sub-phase 1 + 23 sub-phase 2 + 6 sub-phase 3 + 46 sub-phase 4)',
    content
)
content = re.sub(r'\*\*Total Tasks\*\*: 85 tasks', '**Total Tasks**: 84 tasks', content)
content = re.sub(r'- Phase 3\.4 \(Sub-Phase 3\): 6 tasks', '- Phase 3.4 (Sub-Phase 3): 6 tasks', content)
content = re.sub(r'- Phase 3\.5 \(Sub-Phase 4\): 47 tasks', '- Phase 3.5 (Sub-Phase 4): 46 tasks', content)

# Write the corrected content
with open('tasks.md', 'w') as f:
    f.write(content)

print("Fixed task numbering!")
print("- T034 is now database README (was incorrectly T035)")
print("- T035 is now model init (was incorrectly T036)")
print("- T036 is now service init (was incorrectly T037)")
print("- T037 is now git commit (was incorrectly T038)")
print("- T038-T084 are test deletions and validations (was T039-T085)")
