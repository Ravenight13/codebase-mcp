"""Unit tests for chunker.py error paths and edge cases.

This test suite targets uncovered lines in src/services/chunker.py to improve
coverage from 72.15% to 90%+.

Test Coverage Areas:
- ParserCache singleton initialization
- Language grammar initialization errors
- Empty content validation
- Unsupported language fallback
- Parser not available fallback
- AST extraction with no chunks (fallback)
- Parse error fallback
- Batch file chunking with exceptions
- Small file handling (< MIN_CHUNK_LINES)
- Large file line-based chunking
- Parser cache clearing

Constitutional Compliance:
- Principle VII: Test-driven development with comprehensive error coverage
- Principle VIII: Type-safe test patterns with mypy --strict
- Principle V: Production quality with edge case validation
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch
from uuid import UUID, uuid4

import pytest
from tree_sitter import Language, Parser

from src.models import CodeChunkCreate
from src.services.chunker import (
    FALLBACK_CHUNK_LINES,
    MIN_CHUNK_LINES,
    ParserCache,
    _normalize_chunk_type,
    chunk_file,
    chunk_files_batch,
    detect_language,
    extract_chunks_from_ast,
    fallback_line_chunking,
)


# ==============================================================================
# Test Fixtures
# ==============================================================================


@pytest.fixture
def sample_python_content() -> str:
    """Create sample Python code for testing."""
    return """def hello():
    return "world"

class MyClass:
    def __init__(self):
        self.value = 42
"""


@pytest.fixture
def sample_javascript_content() -> str:
    """Create sample JavaScript code for testing."""
    return """function hello() {
    return "world";
}

class MyClass {
    constructor() {
        this.value = 42;
    }
}
"""


@pytest.fixture
def small_file_content() -> str:
    """Create content smaller than MIN_CHUNK_LINES."""
    return "def small(): pass\n"


@pytest.fixture
def large_file_content() -> str:
    """Create content larger than FALLBACK_CHUNK_LINES."""
    return "\n".join([f"line{i} = {i}" for i in range(600)])


@pytest.fixture
def test_file_id() -> UUID:
    """Create a test file UUID."""
    return uuid4()


# ==============================================================================
# ParserCache Singleton Tests
# ==============================================================================


def test_parser_cache_singleton() -> None:
    """Test ParserCache singleton pattern.

    Covers: Lines 78-85 (singleton __new__ method)
    """
    cache1 = ParserCache()
    cache2 = ParserCache()

    assert cache1 is cache2
    assert ParserCache._instance is cache1


def test_parser_cache_get_parser_cached() -> None:
    """Test parser caching returns same instance.

    Covers: Lines 122-123 (cached parser return)
    """
    cache = ParserCache()

    parser1 = cache.get_parser("python")
    parser2 = cache.get_parser("python")

    assert parser1 is parser2


def test_parser_cache_get_parser_unsupported_language() -> None:
    """Test get_parser returns None for unsupported language.

    Covers: Lines 126-127 (unsupported language check)
    """
    cache = ParserCache()

    parser = cache.get_parser("unsupported_language")

    assert parser is None


def test_parser_cache_clear() -> None:
    """Test parser cache clearing.

    Covers: Lines 136-138 (cache clear method)
    """
    cache = ParserCache()

    # Get a parser to populate cache
    _ = cache.get_parser("python")
    assert len(cache._parsers) > 0

    # Clear cache
    cache.clear()
    assert len(cache._parsers) == 0


def test_parser_cache_initialization_error() -> None:
    """Test parser cache handles grammar initialization errors.

    Covers: Lines 105-110 (grammar initialization error handling)
    """
    # Reset singleton to force re-initialization
    ParserCache._instance = None

    with patch("src.services.chunker.Language", side_effect=Exception("Grammar load failed")):
        with pytest.raises(Exception, match="Grammar load failed"):
            ParserCache()

    # Reset for other tests
    ParserCache._instance = None
    ParserCache()


# ==============================================================================
# Language Detection Tests
# ==============================================================================


def test_detect_language_python() -> None:
    """Test Python language detection."""
    assert detect_language(Path("script.py")) == "python"


def test_detect_language_javascript() -> None:
    """Test JavaScript language detection."""
    assert detect_language(Path("app.js")) == "javascript"
    assert detect_language(Path("component.jsx")) == "javascript"


def test_detect_language_unsupported() -> None:
    """Test unsupported language returns None."""
    assert detect_language(Path("README.md")) is None
    assert detect_language(Path("config.yaml")) is None
    assert detect_language(Path("data.json")) is None


def test_detect_language_case_insensitive() -> None:
    """Test language detection is case-insensitive."""
    assert detect_language(Path("Script.PY")) == "python"
    assert detect_language(Path("App.JS")) == "javascript"


# ==============================================================================
# Chunk Type Normalization Tests
# ==============================================================================


def test_normalize_chunk_type_function() -> None:
    """Test normalization of function node types."""
    assert _normalize_chunk_type("function_definition") == "function"
    assert _normalize_chunk_type("function_declaration") == "function"
    assert _normalize_chunk_type("method_definition") == "function"


def test_normalize_chunk_type_class() -> None:
    """Test normalization of class node types."""
    assert _normalize_chunk_type("class_definition") == "class"
    assert _normalize_chunk_type("class_declaration") == "class"


def test_normalize_chunk_type_block() -> None:
    """Test normalization of other node types to block."""
    assert _normalize_chunk_type("if_statement") == "block"
    assert _normalize_chunk_type("for_statement") == "block"
    assert _normalize_chunk_type("while_statement") == "block"


# ==============================================================================
# Empty Content Validation Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_chunk_file_empty_content(test_file_id: UUID) -> None:
    """Test ValueError raised for empty content.

    Covers: Lines 327-328 (empty content validation)
    """
    with pytest.raises(ValueError, match="Empty content for file"):
        await chunk_file(Path("test.py"), "", test_file_id)


# ==============================================================================
# Unsupported Language Fallback Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_chunk_file_unsupported_language(test_file_id: UUID) -> None:
    """Test fallback for unsupported language.

    Covers: Lines 333-339 (unsupported language fallback)
    """
    content = "# Some Ruby code\ndef hello\n  puts 'world'\nend\n"

    chunks = await chunk_file(Path("script.rb"), content, test_file_id)

    # Should fall back to line-based chunking
    assert len(chunks) > 0
    assert all(chunk.chunk_type == "block" for chunk in chunks)


# ==============================================================================
# Parser Not Available Fallback Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_chunk_file_parser_not_available(test_file_id: UUID, sample_python_content: str) -> None:
    """Test fallback when parser is not available.

    Covers: Lines 345-351 (parser not available fallback)
    """
    with patch.object(ParserCache, "get_parser", return_value=None):
        chunks = await chunk_file(Path("test.py"), sample_python_content, test_file_id)

    # Should fall back to line-based chunking
    assert len(chunks) > 0
    assert all(chunk.chunk_type == "block" for chunk in chunks)


# ==============================================================================
# AST Extraction with No Chunks Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_chunk_file_no_chunks_from_ast(test_file_id: UUID) -> None:
    """Test fallback when AST extraction produces no chunks.

    Covers: Lines 361-368 (no chunks extracted fallback)
    """
    # Python file with only comments (no functions/classes)
    content = "# Just a comment file\n# No functions or classes\n"

    chunks = await chunk_file(Path("comments.py"), content, test_file_id)

    # Should fall back to line-based chunking
    assert len(chunks) > 0
    assert all(chunk.chunk_type == "block" for chunk in chunks)


@pytest.mark.asyncio
async def test_chunk_file_unsupported_chunk_types(test_file_id: UUID) -> None:
    """Test extract_chunks_from_ast with no chunk types defined.

    Covers: Lines 191-196 (no chunk types warning)
    """
    # Mock a parsed tree
    mock_tree = Mock()
    mock_tree.root_node = Mock()
    mock_tree.root_node.children = []

    # Language with no chunk types defined
    chunks = extract_chunks_from_ast(mock_tree, "unsupported_lang", "test", test_file_id)

    assert len(chunks) == 0


# ==============================================================================
# Parse Error Fallback Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_chunk_file_parse_error_fallback(
    test_file_id: UUID, sample_python_content: str
) -> None:
    """Test fallback when Tree-sitter parsing fails.

    Covers: Lines 383-395 (parse error fallback)
    """
    with patch.object(Parser, "parse", side_effect=Exception("Parse failed")):
        chunks = await chunk_file(Path("test.py"), sample_python_content, test_file_id)

    # Should fall back to line-based chunking
    assert len(chunks) > 0
    assert all(chunk.chunk_type == "block" for chunk in chunks)


# ==============================================================================
# Fallback Line Chunking Tests
# ==============================================================================


def test_fallback_line_chunking_small_file(test_file_id: UUID, small_file_content: str) -> None:
    """Test small file creates single chunk.

    Covers: Lines 273-284 (small file single chunk)
    """
    chunks = fallback_line_chunking(small_file_content, test_file_id)

    assert len(chunks) == 1
    assert chunks[0].start_line == 1
    assert chunks[0].end_line == len(small_file_content.splitlines())
    assert chunks[0].chunk_type == "block"


def test_fallback_line_chunking_large_file(test_file_id: UUID, large_file_content: str) -> None:
    """Test large file splits into multiple chunks.

    Covers: Lines 286-300 (fixed-size chunk splitting)
    """
    chunks = fallback_line_chunking(large_file_content, test_file_id, chunk_lines=100)

    assert len(chunks) > 1
    # First chunk should be 100 lines
    assert chunks[0].start_line == 1
    assert chunks[0].end_line == 100
    # Check all chunks are block type
    assert all(chunk.chunk_type == "block" for chunk in chunks)


def test_fallback_line_chunking_custom_chunk_size(test_file_id: UUID) -> None:
    """Test custom chunk size parameter."""
    content = "\n".join([f"line{i}" for i in range(50)])

    chunks = fallback_line_chunking(content, test_file_id, chunk_lines=20)

    # 50 lines with chunk_lines=20 should produce 3 chunks
    assert len(chunks) == 3
    assert chunks[0].end_line == 20
    assert chunks[1].start_line == 21
    assert chunks[1].end_line == 40
    assert chunks[2].start_line == 41
    assert chunks[2].end_line == 50


def test_fallback_line_chunking_exact_multiple(test_file_id: UUID) -> None:
    """Test exact multiple of chunk_lines."""
    content = "\n".join([f"line{i}" for i in range(100)])

    chunks = fallback_line_chunking(content, test_file_id, chunk_lines=50)

    # 100 lines with chunk_lines=50 should produce exactly 2 chunks
    assert len(chunks) == 2
    assert chunks[0].end_line == 50
    assert chunks[1].start_line == 51
    assert chunks[1].end_line == 100


# ==============================================================================
# Batch File Chunking Error Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_chunk_files_batch_success(
    test_file_id: UUID, sample_python_content: str, sample_javascript_content: str
) -> None:
    """Test successful batch chunking.

    Covers: Lines 398-429 (batch chunking logic)
    """
    files = [
        (Path("test.py"), sample_python_content, test_file_id),
        (Path("test.js"), sample_javascript_content, uuid4()),
    ]

    results = await chunk_files_batch(files)

    assert len(results) == 2
    assert all(isinstance(result, list) for result in results)
    assert all(len(result) > 0 for result in results)


@pytest.mark.asyncio
async def test_chunk_files_batch_with_exception(test_file_id: UUID) -> None:
    """Test batch chunking handles exceptions gracefully.

    Covers: Lines 417-427 (exception handling in batch)
    """
    files = [
        (Path("good.py"), "def test(): pass", test_file_id),
        (Path("bad.py"), "", uuid4()),  # Empty content will raise ValueError
        (Path("good2.py"), "def test2(): pass", uuid4()),
    ]

    results = await chunk_files_batch(files)

    assert len(results) == 3
    assert len(results[0]) > 0  # First file succeeds
    assert len(results[1]) == 0  # Second file fails (empty list)
    assert len(results[2]) > 0  # Third file succeeds


@pytest.mark.asyncio
async def test_chunk_files_batch_all_fail(test_file_id: UUID) -> None:
    """Test batch chunking when all files fail."""
    files = [
        (Path("bad1.py"), "", test_file_id),
        (Path("bad2.py"), "", uuid4()),
    ]

    results = await chunk_files_batch(files)

    assert len(results) == 2
    assert all(len(result) == 0 for result in results)


# ==============================================================================
# AST Extraction Edge Cases
# ==============================================================================


@pytest.mark.asyncio
async def test_chunk_file_nested_functions(test_file_id: UUID) -> None:
    """Test chunking file with nested functions."""
    content = """def outer():
    def inner():
        return 42
    return inner

class MyClass:
    def method1(self):
        def nested():
            pass
        return nested
"""

    chunks = await chunk_file(Path("nested.py"), content, test_file_id)

    # Should extract outer function and class (nested functions are part of parent)
    assert len(chunks) >= 2
    assert any(chunk.chunk_type == "function" for chunk in chunks)
    assert any(chunk.chunk_type == "class" for chunk in chunks)


@pytest.mark.asyncio
async def test_chunk_file_javascript_classes(
    test_file_id: UUID, sample_javascript_content: str
) -> None:
    """Test JavaScript class extraction."""
    chunks = await chunk_file(Path("test.js"), sample_javascript_content, test_file_id)

    assert len(chunks) >= 2
    # Should have both function and class chunks
    chunk_types = {chunk.chunk_type for chunk in chunks}
    assert "function" in chunk_types
    assert "class" in chunk_types


@pytest.mark.asyncio
async def test_chunk_file_empty_lines_preserved(test_file_id: UUID) -> None:
    """Test that empty lines are preserved in chunks."""
    content = """def test():

    return True


class Empty:
    pass
"""

    chunks = await chunk_file(Path("test.py"), content, test_file_id)

    # Check that chunks preserve empty lines
    for chunk in chunks:
        assert chunk.content is not None
        # Empty lines should be in the content
        if "def test():" in chunk.content:
            assert "\n\n" in chunk.content


@pytest.mark.asyncio
async def test_chunk_file_unicode_content(test_file_id: UUID) -> None:
    """Test chunking file with Unicode characters."""
    content = """def hello():
    return "Hello, 世界! 🌍"

class Grüße:
    def salut(self):
        return "Bonjour"
"""

    chunks = await chunk_file(Path("unicode.py"), content, test_file_id)

    assert len(chunks) >= 2
    # Verify Unicode is preserved
    assert any("世界" in chunk.content for chunk in chunks)
    assert any("Grüße" in chunk.content or "salut" in chunk.content for chunk in chunks)


# ==============================================================================
# Edge Case: Single Line Files
# ==============================================================================


@pytest.mark.asyncio
async def test_chunk_file_single_line(test_file_id: UUID) -> None:
    """Test chunking single line file."""
    content = "x = 42"

    chunks = await chunk_file(Path("single.py"), content, test_file_id)

    # Single line should create one chunk
    assert len(chunks) == 1
    assert chunks[0].start_line == 1
    assert chunks[0].end_line == 1
    assert chunks[0].content == content


# ==============================================================================
# Edge Case: File with Only Whitespace
# ==============================================================================


@pytest.mark.asyncio
async def test_chunk_file_whitespace_only(test_file_id: UUID) -> None:
    """Test chunking file with only whitespace."""
    content = "   \n\n   \n"

    chunks = await chunk_file(Path("whitespace.py"), content, test_file_id)

    # Should create a single block chunk
    assert len(chunks) == 1
    assert chunks[0].chunk_type == "block"


# ==============================================================================
# Edge Case: Very Long Lines
# ==============================================================================


@pytest.mark.asyncio
async def test_chunk_file_very_long_lines(test_file_id: UUID) -> None:
    """Test chunking file with very long lines."""
    long_line = "x = " + "a" * 10000
    content = f"{long_line}\ndef test(): pass"

    chunks = await chunk_file(Path("long.py"), content, test_file_id)

    # Should handle long lines without error
    assert len(chunks) > 0
    assert any(len(chunk.content) > 10000 for chunk in chunks)
