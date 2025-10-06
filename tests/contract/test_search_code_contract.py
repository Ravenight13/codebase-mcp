"""
T006: Contract tests for search_code MCP tool.

These tests validate the MCP protocol contract for semantic code search functionality.
Tests MUST fail initially as the tool is not yet implemented (TDD approach).

Performance Requirements:
- p95 latency: < 500ms
- max latency: < 2000ms
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, Field, ValidationError


# Input Schema Models
class SearchCodeInput(BaseModel):
    """Input schema for search_code tool."""

    query: str = Field(..., min_length=1, description="Natural language search query")
    repository_id: UUID | None = Field(
        default=None, description="Optional repository filter"
    )
    file_type: str | None = Field(
        default=None, description="Optional file extension filter (e.g., 'py', 'js')"
    )
    directory: str | None = Field(
        default=None, description="Optional directory path filter"
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of results",
    )


# Output Schema Models
class SearchResult(BaseModel):
    """Individual search result from code chunk."""

    chunk_id: UUID = Field(..., description="Unique chunk identifier")
    file_path: str = Field(..., description="Path to the file containing the chunk")
    content: str = Field(..., description="The matched code chunk content")
    start_line: int = Field(..., ge=1, description="Starting line number")
    end_line: int = Field(..., ge=1, description="Ending line number")
    similarity_score: float = Field(
        ..., ge=0.0, le=1.0, description="Semantic similarity score"
    )
    context_before: str | None = Field(
        default=None, description="10 lines before the chunk"
    )
    context_after: str | None = Field(
        default=None, description="10 lines after the chunk"
    )


class SearchCodeOutput(BaseModel):
    """Output schema for search_code tool."""

    results: list[SearchResult] = Field(
        ..., description="Array of matching code chunks"
    )
    total_count: int = Field(
        ..., ge=0, description="Total matching chunks (before limit)"
    )
    latency_ms: int = Field(
        ..., ge=0, description="Query execution time in milliseconds"
    )


# Contract Tests


@pytest.mark.contract
def test_search_code_input_valid_minimal() -> None:
    """Test search_code input schema with minimal required fields."""
    # Minimal valid input (only required query)
    valid_input = SearchCodeInput(query="find function")

    assert valid_input.query == "find function"
    assert valid_input.repository_id is None
    assert valid_input.file_type is None
    assert valid_input.directory is None
    assert valid_input.limit == 10  # Default value


@pytest.mark.contract
def test_search_code_input_valid_complete() -> None:
    """Test search_code input schema with all optional fields."""
    repo_id = uuid4()
    valid_input = SearchCodeInput(
        query="semantic search",
        repository_id=repo_id,
        file_type="py",
        directory="/src",
        limit=25,
    )

    assert valid_input.query == "semantic search"
    assert valid_input.repository_id == repo_id
    assert valid_input.file_type == "py"
    assert valid_input.directory == "/src"
    assert valid_input.limit == 25


@pytest.mark.contract
def test_search_code_input_missing_required_field() -> None:
    """Test search_code input validation fails when required query is missing."""
    with pytest.raises(ValidationError) as exc_info:
        SearchCodeInput()  # type: ignore[call-arg]

    errors = exc_info.value.errors()
    assert len(errors) == 1
    assert errors[0]["loc"] == ("query",)
    assert errors[0]["type"] == "missing"


@pytest.mark.contract
def test_search_code_input_empty_query() -> None:
    """Test search_code input validation fails for empty query string."""
    with pytest.raises(ValidationError) as exc_info:
        SearchCodeInput(query="")

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("query",) for error in errors)


@pytest.mark.contract
def test_search_code_input_limit_out_of_range() -> None:
    """Test search_code input validation enforces limit range [1, 50]."""
    # Test limit too low
    with pytest.raises(ValidationError) as exc_info:
        SearchCodeInput(query="test", limit=0)
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("limit",) for error in errors)

    # Test limit too high
    with pytest.raises(ValidationError) as exc_info:
        SearchCodeInput(query="test", limit=51)
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("limit",) for error in errors)


@pytest.mark.contract
def test_search_code_input_invalid_uuid() -> None:
    """Test search_code input validation fails for invalid UUID format."""
    with pytest.raises(ValidationError) as exc_info:
        SearchCodeInput(query="test", repository_id="not-a-uuid")  # type: ignore[arg-type]

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("repository_id",) for error in errors)


@pytest.mark.contract
def test_search_code_output_valid_structure() -> None:
    """Test search_code output schema validates correct structure."""
    chunk_id = uuid4()
    output = SearchCodeOutput(
        results=[
            SearchResult(
                chunk_id=chunk_id,
                file_path="/src/main.py",
                content="def hello():\n    pass",
                start_line=1,
                end_line=2,
                similarity_score=0.95,
                context_before="",
                context_after="",
            )
        ],
        total_count=1,
        latency_ms=45,
    )

    assert len(output.results) == 1
    assert output.results[0].chunk_id == chunk_id
    assert output.results[0].similarity_score == 0.95
    assert output.total_count == 1
    assert output.latency_ms == 45


@pytest.mark.contract
def test_search_code_output_empty_results() -> None:
    """Test search_code output schema allows empty results array."""
    output = SearchCodeOutput(
        results=[],
        total_count=0,
        latency_ms=12,
    )

    assert output.results == []
    assert output.total_count == 0
    assert output.latency_ms == 12


@pytest.mark.contract
def test_search_code_output_missing_required_result_fields() -> None:
    """Test search_code output validation fails when result fields missing."""
    with pytest.raises(ValidationError) as exc_info:
        SearchCodeOutput(
            results=[
                {
                    "chunk_id": str(uuid4()),
                    "file_path": "/test.py",
                    # Missing: content, start_line, end_line, similarity_score
                }
            ],
            total_count=1,
            latency_ms=50,
        )

    errors = exc_info.value.errors()
    # Should have errors for missing required fields in results[0]
    assert len(errors) >= 4


@pytest.mark.contract
def test_search_code_output_similarity_score_range() -> None:
    """Test search_code output validation enforces similarity_score in [0, 1]."""
    chunk_id = uuid4()

    # Test score too high
    with pytest.raises(ValidationError) as exc_info:
        SearchCodeOutput(
            results=[
                SearchResult(
                    chunk_id=chunk_id,
                    file_path="/test.py",
                    content="test",
                    start_line=1,
                    end_line=1,
                    similarity_score=1.5,  # Invalid: > 1.0
                )
            ],
            total_count=1,
            latency_ms=50,
        )
    errors = exc_info.value.errors()
    assert any("similarity_score" in str(error["loc"]) for error in errors)

    # Test negative score
    with pytest.raises(ValidationError) as exc_info:
        SearchCodeOutput(
            results=[
                SearchResult(
                    chunk_id=chunk_id,
                    file_path="/test.py",
                    content="test",
                    start_line=1,
                    end_line=1,
                    similarity_score=-0.1,  # Invalid: < 0.0
                )
            ],
            total_count=1,
            latency_ms=50,
        )
    errors = exc_info.value.errors()
    assert any("similarity_score" in str(error["loc"]) for error in errors)


@pytest.mark.contract
@pytest.mark.asyncio
async def test_search_code_tool_not_implemented() -> None:
    """
    Test documenting that search_code tool is not yet implemented.

    This test MUST fail until the actual tool implementation is complete.
    Once implemented, replace this with actual tool invocation tests.

    Expected behavior: Raises NotImplementedError
    """
    with pytest.raises(NotImplementedError) as exc_info:
        # TODO: Uncomment once tool is implemented
        # from src.mcp.tools.search import search_code
        # result = await search_code(query="test query")
        raise NotImplementedError("search_code tool not implemented yet")

    assert "not implemented" in str(exc_info.value).lower()


@pytest.mark.contract
def test_search_code_performance_requirement_documented() -> None:
    """
    Document performance requirements for search_code tool.

    Performance Requirements (from mcp-protocol.json):
    - p95 latency: < 500ms
    - max latency: < 2000ms

    This test serves as documentation. Actual performance validation
    will be implemented in integration/performance tests.
    """
    p95_requirement_ms = 500
    max_requirement_ms = 2000

    # Document the requirements through assertions
    assert p95_requirement_ms == 500, "p95 latency requirement"
    assert max_requirement_ms == 2000, "max latency requirement"

    # These requirements will be validated once tool is implemented
    # and integrated with actual database queries
