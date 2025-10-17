# Evaluation Suite Implementation Plan

## Overview

**Purpose**: Create a comprehensive evaluation suite with 10 complex questions to validate the codebase-mcp server's semantic search capabilities, following MCP best practices for evaluation-driven development.

**MCP Best Practice Alignment**: This aligns with Phase 4 of the mcp-builder skill - "Evaluation-driven development". High-quality evaluations ensure the server meets real-world use cases and provides a quantitative metric for quality improvements.

**Expected Benefits**:
- Quantitative quality metrics for semantic search accuracy
- Regression detection during development
- Validation of multi-step tool workflows
- Documentation of realistic use cases
- Baseline for future improvements

## Current State Analysis

### What Exists Today
- Performance benchmarks in `tests/performance/test_baseline.py`
- Integration tests in `tests/integration/`
- Manual testing documentation in `specs/*/quickstart.md`
- Protocol compliance tests in `tests/contract/`

### Gaps/Limitations
- No structured evaluation suite following MCP standards
- No complex, multi-step workflow testing
- No verifiable single-answer questions
- No XML evaluation format support
- No automated evaluation execution framework

## Proposed Solution

### High-Level Approach
Create an `evaluations/` directory with XML-formatted evaluation files following MCP evaluation guidelines. Each evaluation contains:
1. A realistic, complex question requiring multiple tool calls
2. A single, verifiable correct answer
3. Read-only operations (no state modifications)
4. Contextual information for the question

The evaluation suite will test:
- **Multi-step workflows**: Questions requiring multiple search queries
- **Filtering capabilities**: Questions testing repository_id, file_type, directory filters
- **Cross-repository search**: Questions spanning multiple indexed repositories
- **Performance validation**: Questions verifying search latency targets
- **Context extraction**: Questions validating context_before/context_after quality

### Key Design Decisions

**Decision 1: XML Format over JSON**
- **Choice**: Use XML format as specified in MCP evaluation guidelines
- **Rationale**: XML is the MCP standard format, enables better tooling integration
- **Trade-off**: Slightly more verbose than JSON, but more standardized

**Decision 2: Read-Only Questions**
- **Choice**: All evaluation questions use only search_code and index_repository (read operations)
- **Rationale**: Evaluations should be repeatable without side effects
- **Trade-off**: Cannot test write operations, but aligns with our read-heavy use case

**Decision 3: Single-Answer Questions**
- **Choice**: Each question has exactly one correct, verifiable answer
- **Rationale**: Enables automated grading and regression detection
- **Trade-off**: May oversimplify complex scenarios, but ensures testability

**Decision 4: Realistic Codebase Fixture**
- **Choice**: Create a dedicated test repository with known patterns
- **Rationale**: Ensures reproducible, predictable evaluation results
- **Trade-off**: Requires maintenance of test fixture, but eliminates flakiness

### Trade-offs Considered

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| 10 simple questions | Easy to verify | Doesn't test complexity | ❌ Rejected |
| 10 complex questions | Tests real workflows | Harder to verify | ✅ **Selected** |
| JSON format | Familiar, concise | Non-standard | ❌ Rejected |
| XML format | MCP standard | More verbose | ✅ **Selected** |
| Real codebases | Realistic | Flaky, unreliable | ❌ Rejected |
| Test fixture | Predictable | Requires maintenance | ✅ **Selected** |

## Technical Design

### Directory Structure

```
evaluations/
├── README.md                     # Evaluation suite documentation
├── codebase-search-basic.xml    # Basic semantic search evaluation
├── codebase-search-filtering.xml # Filter capability evaluation
├── codebase-search-multifile.xml # Cross-file search evaluation
└── fixtures/
    └── test-codebase/           # Test repository for evaluations
        ├── README.md
        ├── src/
        │   ├── auth/
        │   │   ├── login.py
        │   │   ├── logout.py
        │   │   └── session.py
        │   ├── database/
        │   │   ├── models.py
        │   │   ├── migrations.py
        │   │   └── queries.py
        │   └── api/
        │       ├── routes.py
        │       ├── middleware.py
        │       └── handlers.py
        └── tests/
            ├── test_auth.py
            ├── test_database.py
            └── test_api.py
```

### XML Evaluation Format

Each evaluation file follows this structure:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<evaluation>
    <metadata>
        <title>Basic Semantic Search Evaluation</title>
        <description>Tests basic semantic search capabilities with simple queries</description>
        <version>1.0</version>
        <difficulty>easy</difficulty>
    </metadata>

    <question id="1">
        <text>Find all functions that handle user authentication</text>
        <context>
            The test codebase has authentication logic spread across multiple files
            in the src/auth/ directory. We want to find all functions involved in
            authenticating users.
        </context>
        <expected_answer>3</expected_answer>
        <answer_type>count</answer_type>
        <verification>
            Count of search results should be exactly 3:
            - src/auth/login.py: authenticate_user()
            - src/auth/session.py: validate_session()
            - src/auth/session.py: verify_token()
        </verification>
    </question>

    <!-- More questions... -->
</evaluation>
```

### Evaluation Question Categories

**Category 1: Basic Semantic Search (3 questions)**
- Simple queries requiring 1-2 tool calls
- Tests core embedding/similarity matching
- Examples:
  - "Find database migration functions"
  - "Locate API route handlers"
  - "Find error handling code"

**Category 2: Filtering & Precision (3 questions)**
- Tests repository_id, file_type, directory filters
- Requires precise result filtering
- Examples:
  - "Find authentication functions in Python files only"
  - "Search for database queries in the src/database/ directory"
  - "Find test fixtures in test files"

**Category 3: Multi-Step Workflows (2 questions)**
- Requires multiple search_code calls
- Tests workflow composition
- Examples:
  - "Find all API endpoints, then find their test coverage"
  - "Search for database models, then find their migration scripts"

**Category 4: Performance & Context (2 questions)**
- Tests latency targets and context extraction
- Validates quality of context_before/context_after
- Examples:
  - "Search across 100+ files in under 500ms"
  - "Find function definition with correct context showing imports"

### Helper Functions/Utilities

Create `evaluations/run_evaluations.py`:

```python
"""Evaluation suite runner for codebase-mcp server.

Executes XML evaluation files and validates results against expected answers.
"""

import asyncio
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.database.session import get_session
from src.mcp.tools.indexing import index_repository
from src.mcp.tools.search import search_code


@dataclass
class EvaluationResult:
    """Result of a single evaluation question."""
    question_id: str
    question_text: str
    expected_answer: str
    actual_answer: str
    passed: bool
    latency_ms: int
    error: str | None = None


async def run_evaluation(eval_file: Path) -> list[EvaluationResult]:
    """Run a single evaluation file.

    Args:
        eval_file: Path to XML evaluation file

    Returns:
        List of evaluation results for each question
    """
    tree = ET.parse(eval_file)
    root = tree.getroot()

    results: list[EvaluationResult] = []

    # Index test codebase first
    fixture_path = Path(__file__).parent / "fixtures" / "test-codebase"
    await index_repository(
        repo_path=str(fixture_path),
        project_id="evaluation-suite"
    )

    # Run each question
    for question in root.findall(".//question"):
        result = await execute_question(question)
        results.append(result)

    return results


async def execute_question(question: ET.Element) -> EvaluationResult:
    """Execute a single evaluation question.

    Args:
        question: XML element containing question data

    Returns:
        EvaluationResult with pass/fail status
    """
    question_id = question.get("id", "unknown")
    text = question.findtext("text", "")
    expected = question.findtext("expected_answer", "")
    answer_type = question.findtext("answer_type", "exact")

    # Execute search
    import time
    start = time.perf_counter()

    try:
        # Parse query and execute
        search_results = await search_code(
            query=text,
            project_id="evaluation-suite"
        )

        latency_ms = int((time.perf_counter() - start) * 1000)

        # Validate answer based on type
        if answer_type == "count":
            actual = str(search_results["total_count"])
        elif answer_type == "contains":
            actual = search_results["results"][0]["file_path"] if search_results["results"] else ""
        else:
            actual = str(search_results)

        passed = (actual == expected)

        return EvaluationResult(
            question_id=question_id,
            question_text=text,
            expected_answer=expected,
            actual_answer=actual,
            passed=passed,
            latency_ms=latency_ms
        )

    except Exception as e:
        return EvaluationResult(
            question_id=question_id,
            question_text=text,
            expected_answer=expected,
            actual_answer="",
            passed=False,
            latency_ms=0,
            error=str(e)
        )


async def run_all_evaluations() -> dict[str, list[EvaluationResult]]:
    """Run all evaluation files in evaluations/ directory.

    Returns:
        Dictionary mapping eval file name to results
    """
    eval_dir = Path(__file__).parent
    eval_files = list(eval_dir.glob("*.xml"))

    all_results: dict[str, list[EvaluationResult]] = {}

    for eval_file in eval_files:
        results = await run_evaluation(eval_file)
        all_results[eval_file.name] = results

    return all_results


def print_results(all_results: dict[str, list[EvaluationResult]]) -> None:
    """Print formatted evaluation results."""
    total_questions = 0
    total_passed = 0

    for eval_name, results in all_results.items():
        print(f"\n{'='*80}")
        print(f"Evaluation: {eval_name}")
        print(f"{'='*80}\n")

        for result in results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"{status} Q{result.question_id}: {result.question_text[:60]}...")
            print(f"  Expected: {result.expected_answer}")
            print(f"  Actual:   {result.actual_answer}")
            print(f"  Latency:  {result.latency_ms}ms")
            if result.error:
                print(f"  Error:    {result.error}")
            print()

            total_questions += 1
            if result.passed:
                total_passed += 1

    print(f"\n{'='*80}")
    print(f"Overall: {total_passed}/{total_questions} passed ({total_passed/total_questions*100:.1f}%)")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    results = asyncio.run(run_all_evaluations())
    print_results(results)
```

### Error Handling

**Evaluation Execution Errors**:
- **Invalid XML**: Log parsing error, skip evaluation file
- **Missing Fixture**: Fail fast with clear error message
- **Indexing Failure**: Report error, continue with next evaluation
- **Search Timeout**: Mark question as failed, record latency

**Answer Verification Errors**:
- **Type Mismatch**: Log warning, mark as failed
- **Missing Expected Answer**: Fail evaluation file validation
- **Ambiguous Results**: Log details for manual review

## Implementation Steps

### Step 1: Create Evaluation Directory Structure
- Create `evaluations/` directory
- Create `evaluations/fixtures/test-codebase/` directory
- Add README.md with evaluation suite documentation
- **Dependencies**: None
- **Testing**: Directory structure validation

### Step 2: Create Test Codebase Fixture
- Design test codebase with known patterns
- Create 10-15 Python files with authentication, database, API code
- Add comments and docstrings for semantic richness
- Ensure 100+ lines per file for realistic chunking
- **Dependencies**: Step 1
- **Testing**: Verify fixture can be indexed successfully

### Step 3: Write XML Evaluation Files
- Create 3 evaluation files (basic, filtering, multi-step)
- Write 10 total questions across files
- Define expected answers and verification logic
- **Dependencies**: Step 2
- **Testing**: XML validation against schema

### Step 4: Implement Evaluation Runner
- Create `run_evaluations.py` with helper functions
- Implement XML parsing logic
- Implement question execution logic
- Implement answer verification logic
- **Dependencies**: Step 3
- **Testing**: Unit tests for each helper function

### Step 5: Test Evaluation Suite
- Run all evaluations against test fixture
- Validate 100% pass rate
- Measure execution time (target: <30s for all 10 questions)
- **Dependencies**: Step 4
- **Testing**: Integration test running full suite

### Step 6: Document Evaluation Suite
- Add usage instructions to README.md
- Document how to add new evaluations
- Document XML schema requirements
- Add CI integration instructions
- **Dependencies**: Step 5
- **Testing**: Manual review of documentation

## Success Criteria

### Measurable Outcomes
1. **Completeness**: 10 complex evaluation questions across 3 categories
2. **Quality**: Each question requires 2+ tool calls or complex filtering
3. **Reliability**: 100% pass rate on initial run
4. **Performance**: Full suite execution in <30 seconds
5. **Maintainability**: Clear documentation for adding new evaluations

### How to Validate Completion
1. Run `python evaluations/run_evaluations.py`
2. Verify 10/10 questions pass
3. Verify total execution time <30s
4. Verify each question requires read-only operations
5. Verify each answer is verifiable and deterministic

### Quality Gates
- XML files validate against schema
- Test fixture indexes in <10 seconds
- Each question has clear verification criteria
- README.md provides complete usage instructions
- No false positives/negatives in answer verification

## Risks & Mitigations

### Risk 1: Flaky Evaluation Results
**Potential Issue**: Semantic search results may vary due to embedding model changes
**Mitigation**:
- Pin Ollama model version in evaluation environment
- Use exact match for critical fields (file paths, line numbers)
- Use range matching for similarity scores (e.g., score > 0.8)

### Risk 2: Test Fixture Maintenance Burden
**Potential Issue**: Fixture may become outdated or misaligned with real use cases
**Mitigation**:
- Keep fixture minimal (10-15 files)
- Document fixture design in README.md
- Review fixture quarterly for relevance

### Risk 3: XML Complexity
**Potential Issue**: XML format may be unfamiliar to developers
**Mitigation**:
- Provide XML template in README.md
- Include JSON-to-XML converter utility
- Add XML validation to pre-commit hooks

### Risk 4: Evaluation Suite Execution Time
**Potential Issue**: 10 questions may take too long to run in CI
**Mitigation**:
- Parallelize question execution where possible
- Cache indexed test fixture between runs
- Add fast/slow evaluation categories

## Alternative Approaches Considered

### Approach 1: JSON Format Instead of XML
**Considered**: Use JSON for evaluation files
**Why Rejected**: XML is the MCP standard format, ensures compatibility with MCP tooling

### Approach 2: 100 Simple Questions Instead of 10 Complex
**Considered**: Create many simple questions for broader coverage
**Why Rejected**: Complex questions better test real-world workflows; simple questions covered by unit tests

### Approach 3: Live Codebase Evaluations
**Considered**: Run evaluations against live open-source repositories
**Why Rejected**: Results would be unpredictable and flaky; dedicated fixture ensures determinism

### Approach 4: Manual Evaluation Only
**Considered**: Keep evaluations as manual test plans
**Why Rejected**: Automated evaluations enable regression detection and CI integration

## Constitutional Compliance Checklist

- ✅ **Principle I (Simplicity)**: Evaluation suite doesn't add feature complexity, only tests existing features
- ✅ **Principle II (Local-First)**: All evaluations run locally against local fixture
- ✅ **Principle III (Protocol Compliance)**: Evaluations follow MCP evaluation standards
- ✅ **Principle IV (Performance)**: Each question validates against <500ms search target
- ✅ **Principle V (Production Quality)**: Comprehensive error handling in evaluation runner
- ✅ **Principle VI (Specification-First)**: This plan created before implementation
- ✅ **Principle VII (TDD)**: Evaluation suite itself is a test artifact
- ✅ **Principle VIII (Type Safety)**: Evaluation runner uses Pydantic models and mypy --strict
- ✅ **Principle IX (Orchestration)**: N/A - documentation task, no subagent execution
- ✅ **Principle X (Git Micro-Commits)**: Implementation will follow micro-commit strategy
- ✅ **Principle XI (FastMCP)**: Evaluations test FastMCP tool implementations

## Next Steps After Completion

1. **CI Integration**: Add evaluation suite to GitHub Actions workflow
2. **Regression Tracking**: Track evaluation pass rate over time
3. **Expansion**: Add 5-10 more questions based on real user queries
4. **Benchmarking**: Use evaluation results to guide performance optimizations
5. **Documentation**: Reference evaluation suite in main README.md
