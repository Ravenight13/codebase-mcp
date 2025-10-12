# Constitutional Exception Tracking

This file tracks all approved exceptions to constitutional principles as defined in the Exception Handling Process (constitution.md, Governance section).

## Active Exceptions

*No active exceptions at this time.*

---

## Resolved Exceptions

*No resolved exceptions at this time.*

---

## Exception Template

Use this template when documenting approved exceptions:

```markdown
### Exception [EXC-YYYY-NNN]

**Status**: Active | Resolved
**Principle Affected**: [Principle number and name]
**Requested By**: [GitHub username]
**Request Date**: YYYY-MM-DD
**Approved By**: [Maintainer/Reviewer names]
**Approval Date**: YYYY-MM-DD
**Exception Type**: Temporary (<30 days) | Extended (30-90 days) | Permanent
**Sunset Date**: YYYY-MM-DD (for temporary/extended exceptions)

**Justification Summary**:
[Brief explanation of why the principle cannot be met]

**Alternatives Considered**:
- [Alternative 1 and why it was rejected]
- [Alternative 2 and why it was rejected]

**Impact Analysis**:
- [Quantified impact on system behavior, performance, quality]
- [Risk assessment]

**Mitigation Strategy**:
- [How the violation impact is minimized]
- [Compensating controls or processes]

**Resolution**:
[For resolved exceptions: How it was resolved, date resolved, and outcome]

**GitHub Issue**: [Link to constitution-exception issue]
```

---

## Exception Approval Process

Refer to constitution.md § Governance § Exception Handling Process for the complete workflow:

1. **Create GitHub issue** with label `constitution-exception`
2. **Document** principle(s) requiring exception with detailed justification
3. **Specify** time-bound duration or permanent exception request
4. **Obtain approval**:
   - Temporary (<30 days): Project maintainer
   - Extended (30-90 days): 2 approvals (maintainer + technical reviewer)
   - Permanent: Constitution amendment (MAJOR version bump)
5. **Document** approved exception in this file using template above
6. **Track** sunset dates and review quarterly

---

## Metrics

- **Total Exceptions Requested**: 0
- **Active Exceptions**: 0
- **Resolved Exceptions**: 0
- **Exception Request Rate**: 0% (target: <5% of PRs)
- **Average Exception Duration**: N/A

---

**Last Updated**: 2025-10-12
**Version**: 1.0.0
**Constitution Version**: 3.0.0
