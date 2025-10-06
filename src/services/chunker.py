"""Tree-sitter code chunker service with multi-language support.

Parses code files using Tree-sitter AST to extract semantic chunks (functions,
classes, blocks) for embedding generation and similarity search.

Constitutional Compliance:
- Principle IV: Performance (cached parsers, fallback chunking, async operations)
- Principle V: Production quality (graceful degradation, language detection)
- Principle VIII: Type safety (full mypy --strict compliance)

Key Features:
- AST-based semantic chunking for supported languages
- Dynamic language grammar loading based on file extension
- Fallback to line-based chunking for unsupported languages
- Parser caching for performance
- Target chunk size: 100-500 lines
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import Final

from tree_sitter import Language, Node, Parser, Tree
import tree_sitter_python
import tree_sitter_javascript

from src.mcp.mcp_logging import get_logger
from src.models import CodeChunkCreate

# ==============================================================================
# Constants
# ==============================================================================

logger = get_logger(__name__)

# Language configurations
# Note: TypeScript support can be added later with tree-sitter-typescript
LANGUAGE_EXTENSIONS: Final[dict[str, str]] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    # ".ts": "typescript",  # TODO: Add when tree-sitter-typescript is available
    # ".tsx": "tsx",        # TODO: Add when tree-sitter-typescript is available
}

# Node types to extract as chunks (by language)
CHUNK_NODE_TYPES: Final[dict[str, set[str]]] = {
    "python": {"function_definition", "class_definition"},
    "javascript": {"function_declaration", "class_declaration", "method_definition"},
    # "typescript": {"function_declaration", "class_declaration", "method_definition"},  # TODO
    # "tsx": {"function_declaration", "class_declaration", "method_definition"},  # TODO
}

# Fallback chunking parameters
FALLBACK_CHUNK_LINES: Final[int] = 500
MIN_CHUNK_LINES: Final[int] = 10
MAX_CHUNK_LINES: Final[int] = 1000


# ==============================================================================
# Parser Cache
# ==============================================================================


class ParserCache:
    """Caches Tree-sitter parsers for performance.

    Singleton pattern to avoid re-creating parsers for each file.
    """

    _instance: ParserCache | None = None
    _parsers: dict[str, Parser]
    _languages: dict[str, Language]

    def __new__(cls) -> ParserCache:
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._parsers = {}
            cls._instance._languages = {}
            cls._instance._initialize_languages()
        return cls._instance

    def _initialize_languages(self) -> None:
        """Initialize language grammars."""
        try:
            # Load Python grammar
            self._languages["python"] = Language(tree_sitter_python.language())
            logger.debug("Loaded Python grammar")

            # Load JavaScript grammar
            self._languages["javascript"] = Language(tree_sitter_javascript.language())
            logger.debug("Loaded JavaScript grammar")

            # TODO: Add TypeScript support when tree-sitter-typescript is available
            # self._languages["typescript"] = Language(
            #     tree_sitter_typescript.language_typescript()
            # )
            # self._languages["tsx"] = Language(tree_sitter_typescript.language_tsx())
            # logger.debug("Loaded TypeScript and TSX grammars")

        except Exception as e:
            logger.error(
                "Failed to initialize language grammars",
                extra={"context": {"error": str(e)}},
            )
            raise

    def get_parser(self, language: str) -> Parser | None:
        """Get parser for language.

        Args:
            language: Language name (e.g., "python", "javascript")

        Returns:
            Parser instance or None if language not supported
        """
        # Return cached parser if available
        if language in self._parsers:
            return self._parsers[language]

        # Create new parser if language is supported
        if language not in self._languages:
            return None

        parser = Parser()
        parser.language = self._languages[language]
        self._parsers[language] = parser

        logger.debug(f"Created parser for {language}")
        return parser

    def clear(self) -> None:
        """Clear parser cache (useful for testing)."""
        self._parsers.clear()


# ==============================================================================
# Language Detection
# ==============================================================================


def detect_language(file_path: Path) -> str | None:
    """Detect programming language from file extension.

    Args:
        file_path: Path to source file

    Returns:
        Language name or None if unsupported

    Examples:
        >>> detect_language(Path("script.py"))
        'python'
        >>> detect_language(Path("app.tsx"))
        'tsx'
        >>> detect_language(Path("README.md"))
        None
    """
    suffix = file_path.suffix.lower()
    return LANGUAGE_EXTENSIONS.get(suffix)


# ==============================================================================
# AST-Based Chunking
# ==============================================================================


def extract_chunks_from_ast(
    tree: Tree, language: str, content: str, file_id: uuid.UUID
) -> list[CodeChunkCreate]:
    """Extract semantic chunks from Tree-sitter AST.

    Args:
        tree: Parsed Tree-sitter AST
        language: Language name
        content: File content as string
        file_id: UUID of file in database

    Returns:
        List of CodeChunkCreate objects
    """
    chunks: list[CodeChunkCreate] = []
    content_bytes = content.encode("utf-8")

    # Get chunk node types for this language
    chunk_types = CHUNK_NODE_TYPES.get(language, set())
    if not chunk_types:
        logger.warning(
            f"No chunk types defined for language: {language}",
            extra={"context": {"language": language}},
        )
        return chunks

    # Traverse AST and extract chunks
    def visit_node(node: Node) -> None:
        """Recursively visit AST nodes."""
        if node.type in chunk_types:
            # Extract chunk content
            start_byte = node.start_byte
            end_byte = node.end_byte
            chunk_content = content_bytes[start_byte:end_byte].decode("utf-8")

            # Get line numbers (1-indexed)
            start_line = node.start_point[0] + 1
            end_line = node.end_point[0] + 1

            # Determine chunk type (normalize to function/class/block)
            chunk_type = _normalize_chunk_type(node.type)

            # Create chunk
            chunk = CodeChunkCreate(
                code_file_id=file_id,
                content=chunk_content,
                start_line=start_line,
                end_line=end_line,
                chunk_type=chunk_type,
            )
            chunks.append(chunk)

        # Visit children
        for child in node.children:
            visit_node(child)

    # Start traversal from root
    visit_node(tree.root_node)

    return chunks


def _normalize_chunk_type(node_type: str) -> str:
    """Normalize AST node type to standard chunk type.

    Args:
        node_type: Tree-sitter node type

    Returns:
        Normalized chunk type: "function", "class", or "block"
    """
    if "function" in node_type or "method" in node_type:
        return "function"
    elif "class" in node_type:
        return "class"
    else:
        return "block"


# ==============================================================================
# Fallback Line-Based Chunking
# ==============================================================================


def fallback_line_chunking(
    content: str, file_id: uuid.UUID, chunk_lines: int = FALLBACK_CHUNK_LINES
) -> list[CodeChunkCreate]:
    """Fallback to line-based chunking for unsupported languages.

    Args:
        content: File content
        file_id: UUID of file in database
        chunk_lines: Lines per chunk (default: 500)

    Returns:
        List of CodeChunkCreate objects
    """
    chunks: list[CodeChunkCreate] = []
    lines = content.splitlines(keepends=True)
    total_lines = len(lines)

    if total_lines < MIN_CHUNK_LINES:
        # File too small, create single chunk
        chunks.append(
            CodeChunkCreate(
                code_file_id=file_id,
                content=content,
                start_line=1,
                end_line=total_lines,
                chunk_type="block",
            )
        )
        return chunks

    # Split into fixed-size chunks
    for start_idx in range(0, total_lines, chunk_lines):
        end_idx = min(start_idx + chunk_lines, total_lines)
        chunk_content = "".join(lines[start_idx:end_idx])

        chunks.append(
            CodeChunkCreate(
                code_file_id=file_id,
                content=chunk_content,
                start_line=start_idx + 1,  # 1-indexed
                end_line=end_idx,  # 1-indexed
                chunk_type="block",
            )
        )

    return chunks


# ==============================================================================
# Public API
# ==============================================================================


async def chunk_file(file_path: Path, content: str, file_id: uuid.UUID) -> list[CodeChunkCreate]:
    """Parse file and extract semantic chunks.

    Args:
        file_path: Path to source file
        content: File content as string
        file_id: UUID of file in database

    Returns:
        List of CodeChunkCreate objects

    Raises:
        ValueError: If content is empty

    Performance:
        Uses cached parsers for performance
        Falls back to line-based chunking for unsupported languages
    """
    if not content:
        raise ValueError(f"Empty content for file: {file_path}")

    # Detect language
    language = detect_language(file_path)

    if language is None:
        # Unsupported language, use fallback
        logger.debug(
            f"Unsupported language for {file_path}, using fallback chunking",
            extra={"context": {"file_path": str(file_path)}},
        )
        return fallback_line_chunking(content, file_id)

    # Get parser for language
    cache = ParserCache()
    parser = cache.get_parser(language)

    if parser is None:
        # Parser not available, use fallback
        logger.warning(
            f"Parser not available for {language}, using fallback chunking",
            extra={"context": {"language": language, "file_path": str(file_path)}},
        )
        return fallback_line_chunking(content, file_id)

    # Parse with Tree-sitter
    try:
        content_bytes = content.encode("utf-8")
        tree = parser.parse(content_bytes)

        # Extract chunks from AST
        chunks = extract_chunks_from_ast(tree, language, content, file_id)

        if not chunks:
            # No chunks extracted (e.g., file with no functions/classes)
            # Fall back to line-based chunking
            logger.debug(
                f"No chunks extracted from AST for {file_path}, using fallback",
                extra={"context": {"file_path": str(file_path), "language": language}},
            )
            return fallback_line_chunking(content, file_id)

        logger.debug(
            f"Extracted {len(chunks)} chunks from {file_path}",
            extra={
                "context": {
                    "file_path": str(file_path),
                    "language": language,
                    "chunk_count": len(chunks),
                }
            },
        )

        return chunks

    except Exception as e:
        # Parse error, fall back to line-based chunking
        logger.warning(
            f"Failed to parse {file_path} with Tree-sitter, using fallback",
            extra={
                "context": {
                    "file_path": str(file_path),
                    "language": language,
                    "error": str(e),
                }
            },
        )
        return fallback_line_chunking(content, file_id)


async def chunk_files_batch(
    files: list[tuple[Path, str, uuid.UUID]]
) -> list[list[CodeChunkCreate]]:
    """Chunk multiple files in parallel.

    Args:
        files: List of (file_path, content, file_id) tuples

    Returns:
        List of chunk lists (one per file)

    Performance:
        Uses asyncio.gather for parallel processing
    """
    tasks = [chunk_file(path, content, file_id) for path, content, file_id in files]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Handle exceptions
    chunk_lists: list[list[CodeChunkCreate]] = []
    for i, result in enumerate(results):
        if isinstance(result, BaseException):
            file_path = files[i][0]
            logger.error(
                f"Failed to chunk file: {file_path}",
                extra={"context": {"file_path": str(file_path), "error": str(result)}},
            )
            chunk_lists.append([])  # Empty chunk list for failed file
        else:
            # result is list[CodeChunkCreate]
            chunk_lists.append(result)

    return chunk_lists


# ==============================================================================
# Module Exports
# ==============================================================================

__all__ = [
    "chunk_file",
    "chunk_files_batch",
    "detect_language",
]
