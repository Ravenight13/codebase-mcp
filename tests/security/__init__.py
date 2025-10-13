"""Security tests for codebase-mcp.

Test modules in this package validate security-critical functionality:
- SQL injection prevention (test_sql_injection.py)
- Identifier validation (test_identifier_validation.py)

Constitutional Compliance:
- Principle V: Production quality (comprehensive security testing)
- Principle VII: TDD (security validation before implementation)
- Principle VIII: Type safety (Pydantic validation integration)
"""

from __future__ import annotations

__all__: list[str] = []
