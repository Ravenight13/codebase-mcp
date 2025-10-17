#!/usr/bin/env python3
"""Validation script for resolve_project_id() 4-tier resolution chain update.

This script validates that the resolve_project_id() function has been correctly
updated with:
1. Updated function signature (ctx: Context | None = None parameter added)
2. Priority 2 block for session-based config resolution
3. Correctly renumbered priorities (1-4)
4. Updated docstring with 4-tier resolution order
"""

import re
from pathlib import Path

def validate_resolve_project_id_update():
    """Validate resolve_project_id() implementation matches requirements."""

    session_file = Path("/Users/cliffclarke/Claude_Code/codebase-mcp/src/database/session.py")
    content = session_file.read_text()

    results = []

    # 1. Check function signature
    sig_pattern = r'async def resolve_project_id\(\s*explicit_id: str \| None,\s*settings: Settings \| None = None,\s*ctx: Context \| None = None,\s*\) -> str \| None:'
    if re.search(sig_pattern, content, re.MULTILINE):
        results.append("✅ Function signature updated correctly (ctx parameter added)")
    else:
        results.append("❌ Function signature missing ctx parameter or incorrectly formatted")

    # 2. Check docstring mentions 4-tier resolution
    docstring_pattern = r'Resolution Order.*:\s*1\.\s*\*\*Explicit ID\*\*.*2\.\s*\*\*Session-based config\*\*.*3\.\s*\*\*workflow-mcp Integration\*\*.*4\.\s*\*\*Default Workspace\*\*'
    if re.search(docstring_pattern, content, re.DOTALL):
        results.append("✅ Docstring updated with 4-tier resolution order")
    else:
        results.append("❌ Docstring missing 4-tier resolution description")

    # 3. Check Priority 1 block (explicit_id)
    priority1_pattern = r'# 1\. Explicit ID takes precedence'
    if re.search(priority1_pattern, content):
        results.append("✅ Priority 1 block present (explicit ID)")
    else:
        results.append("❌ Priority 1 block missing or incorrectly numbered")

    # 4. Check Priority 2 block (session-based config)
    priority2_pattern = r'# 2\. Try session-based config resolution \(if Context provided\)'
    if re.search(priority2_pattern, content):
        results.append("✅ Priority 2 block present (session-based config)")
    else:
        results.append("❌ Priority 2 block missing or incorrectly numbered")

    # 5. Check Priority 2 implementation calls _resolve_project_context
    resolve_context_call = r'result = await _resolve_project_context\(ctx\)'
    if re.search(resolve_context_call, content):
        results.append("✅ Priority 2 calls _resolve_project_context(ctx)")
    else:
        results.append("❌ Priority 2 missing _resolve_project_context() call")

    # 6. Check Priority 3 block (workflow-mcp)
    priority3_pattern = r'# 3\. Try workflow-mcp integration'
    if re.search(priority3_pattern, content):
        results.append("✅ Priority 3 block present (workflow-mcp)")
    else:
        results.append("❌ Priority 3 block missing or incorrectly numbered")

    # 7. Check Priority 4 block (default fallback)
    priority4_pattern = r'# 4\. Fallback to default workspace'
    if re.search(priority4_pattern, content):
        results.append("✅ Priority 4 block present (default workspace)")
    else:
        results.append("❌ Priority 4 block missing or incorrectly numbered")

    # 8. Check _resolve_project_context() helper exists
    helper_pattern = r'async def _resolve_project_context\(\s*ctx: Context \| None\s*\) -> tuple\[str, str\] \| None:'
    if re.search(helper_pattern, content):
        results.append("✅ _resolve_project_context() helper function exists")
    else:
        results.append("❌ _resolve_project_context() helper function missing")

    # 9. Check imports for session-based resolution
    imports_pattern = r'from fastmcp import Context'
    if re.search(imports_pattern, content):
        results.append("✅ FastMCP Context import present")
    else:
        results.append("❌ FastMCP Context import missing")

    # 10. Check __all__ exports updated
    all_pattern = r'__all__.*_resolve_project_context'
    if re.search(all_pattern, content, re.DOTALL):
        results.append("✅ _resolve_project_context exported in __all__")
    else:
        results.append("⚠️  _resolve_project_context not in __all__ (optional)")

    return results


def main():
    """Run validation and display results."""
    print("=" * 80)
    print("Validating resolve_project_id() 4-tier resolution chain update")
    print("=" * 80)
    print()

    results = validate_resolve_project_id_update()

    for result in results:
        print(result)

    print()
    print("=" * 80)

    # Count successes and failures
    successes = sum(1 for r in results if r.startswith("✅"))
    failures = sum(1 for r in results if r.startswith("❌"))
    warnings = sum(1 for r in results if r.startswith("⚠️"))

    print(f"Summary: {successes} passed, {failures} failed, {warnings} warnings")
    print("=" * 80)

    if failures == 0:
        print("\n✅ All validations passed! resolve_project_id() update is correct.")
        return 0
    else:
        print(f"\n❌ {failures} validation(s) failed. Please review implementation.")
        return 1


if __name__ == "__main__":
    exit(main())
