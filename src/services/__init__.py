"""Service layer for Codebase MCP Server.

This module exports all service implementations for repository indexing,
code chunking, and embedding generation.

Service Organization:
- scanner: File scanning with ignore pattern support
- chunker: Tree-sitter AST-based code chunking
- embedder: Ollama embedding generation with retry logic

Constitutional Compliance:
- Principle IV: Performance (async operations, caching, batching)
- Principle V: Production quality (error handling, retry logic, validation)
- Principle VIII: Type safety (full mypy --strict compliance)
"""

# Scanner service
from .scanner import (
    ChangeSet,
    compute_file_hash,
    detect_changes,
    is_ignored,
    scan_repository,
)

# Chunker service
from .chunker import chunk_file, chunk_files_batch, detect_language

# Embedder service
from .embedder import (
    OllamaConnectionError,
    OllamaEmbedder,
    OllamaError,
    OllamaModelNotFoundError,
    OllamaTimeoutError,
    OllamaValidationError,
    generate_embedding,
    generate_embeddings,
    validate_ollama_connection,
)

__all__ = [
    # Scanner
    "ChangeSet",
    "scan_repository",
    "detect_changes",
    "is_ignored",
    "compute_file_hash",
    # Chunker
    "chunk_file",
    "chunk_files_batch",
    "detect_language",
    # Embedder
    "OllamaEmbedder",
    "OllamaError",
    "OllamaConnectionError",
    "OllamaModelNotFoundError",
    "OllamaTimeoutError",
    "OllamaValidationError",
    "validate_ollama_connection",
    "generate_embedding",
    "generate_embeddings",
]
