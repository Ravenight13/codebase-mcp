"""
Integration tests for repository indexing with ignore patterns (Scenario 1).

Tests verify (from quickstart.md):
- Repository indexing workflow (FR-001 to FR-006)
- .gitignore pattern exclusion
- .mcpignore pattern exclusion
- Database record creation (Repository, CodeFile, CodeChunk)
- Embedding generation
- Performance target: <60 seconds for indexing

TDD Compliance: These tests MUST FAIL initially since services are not implemented yet.
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from src.models.code_chunk import CodeChunk
    from src.models.code_file import CodeFile
    from src.models.repository import Repository


@pytest.fixture
async def test_repository(tmp_path: Path) -> Path:
    """
    Create a temporary test repository with sample code.

    Structure:
    - src/calculator.py (Python, should be indexed)
    - src/utils.py (Python, should be indexed)
    - __pycache__/test.pyc (should be ignored via .gitignore)
    - .gitignore (defines ignore patterns)
    - .mcpignore (defines additional ignore patterns)
    """
    repo_path = tmp_path / "test-repo"
    repo_path.mkdir()

    # Create src directory
    src_dir = repo_path / "src"
    src_dir.mkdir()

    # Create calculator.py with functions and class
    (src_dir / "calculator.py").write_text('''def add(a: int, b: int) -> int:
    """Add two numbers and return the result."""
    return a + b

def multiply(a: int, b: int) -> int:
    """Multiply two numbers and return the result."""
    return a * b

class Calculator:
    """A simple calculator class."""

    def __init__(self) -> None:
        self.history: list[tuple[str, int, int, int]] = []

    def calculate(self, operation: str, a: int, b: int) -> int:
        """Perform calculation and store in history."""
        if operation == "add":
            result = add(a, b)
        elif operation == "multiply":
            result = multiply(a, b)
        else:
            raise ValueError(f"Unknown operation: {operation}")

        self.history.append((operation, a, b, result))
        return result
''')

    # Create utils.py with utility functions
    (src_dir / "utils.py").write_text('''def format_result(value: int, decimals: int = 2) -> str:
    """Format a numeric result as a string."""
    return f"{value:.{decimals}f}"

def log_message(message: str, level: str = "INFO") -> None:
    """Log a message to console."""
    print(f"[{level}] {message}")
''')

    # Create .gitignore
    (repo_path / ".gitignore").write_text('''__pycache__/
*.pyc
.env
*.log
''')

    # Create .mcpignore for MCP-specific exclusions
    (repo_path / ".mcpignore").write_text('''node_modules/
.git/
.venv/
dist/
build/
''')

    # Create files that should be ignored
    pycache_dir = repo_path / "__pycache__"
    pycache_dir.mkdir()
    (pycache_dir / "test.pyc").write_text("binary content")
    (repo_path / ".env").write_text("SECRET_KEY=test")

    return repo_path


@pytest.fixture
async def db_session() -> AsyncSession:
    """
    Create async database session for tests.

    Note: This fixture will need proper implementation once database setup is complete.
    For now, this is a placeholder that will cause tests to fail appropriately.
    """
    pytest.skip("Database session fixture not implemented yet (requires T019-T027)")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_basic_repository_indexing_not_implemented(
    test_repository: Path,
    db_session: AsyncSession,
) -> None:
    """
    Test basic repository indexing workflow - NOT YET IMPLEMENTED.

    Expected workflow:
    1. Call index_repository service
    2. Verify response contains files_indexed, chunks_created, duration
    3. Query database to verify Repository record created
    4. Verify CodeFile records created for .py files
    5. Verify CodeChunk records created for functions/classes
    6. Verify embeddings generated

    This test MUST FAIL until T031 (indexer service) is implemented.
    """
    pytest.skip("Repository indexing service not implemented yet (T031)")

    # Future implementation:
    # from src.services.indexer import index_repository
    #
    # start_time = time.perf_counter()
    # result = await index_repository(
    #     path=test_repository,
    #     name="Test Repository",
    #     force_reindex=False,
    # )
    # duration = time.perf_counter() - start_time
    #
    # # Verify response
    # assert result.status == "success"
    # assert result.files_indexed == 2  # calculator.py, utils.py
    # assert result.chunks_created >= 5  # add, multiply, calculate, Calculator class, format_result, log_message
    # assert result.duration_seconds < 60  # Performance target
    # assert duration < 60  # Verify actual time
    #
    # # Verify Repository record created
    # stmt = select(Repository).where(Repository.path == str(test_repository))
    # repo = await db_session.scalar(stmt)
    # assert repo is not None
    # assert repo.name == "Test Repository"
    # assert repo.is_active is True
    # assert repo.last_indexed_at is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_gitignore_patterns_respected(
    test_repository: Path,
    db_session: AsyncSession,
) -> None:
    """
    Test that .gitignore patterns are respected during indexing.

    Expected behavior:
    - __pycache__/test.pyc should NOT be indexed
    - .env should NOT be indexed
    - Only .py files in src/ should be indexed

    This test MUST FAIL until T028 (scanner service) and T031 (indexer) are implemented.
    """
    pytest.skip("Scanner and indexer not implemented yet (T028, T031)")

    # Future implementation:
    # from src.services.indexer import index_repository
    # from src.models.code_file import CodeFile
    #
    # await index_repository(
    #     path=test_repository,
    #     name="Test Repository",
    #     force_reindex=False,
    # )
    #
    # # Query all indexed files
    # stmt = select(CodeFile)
    # result = await db_session.execute(stmt)
    # code_files = result.scalars().all()
    #
    # relative_paths = [f.relative_path for f in code_files]
    #
    # # Verify ignored files are NOT indexed
    # assert "__pycache__/test.pyc" not in relative_paths
    # assert ".env" not in relative_paths
    #
    # # Verify valid files ARE indexed
    # assert "src/calculator.py" in relative_paths
    # assert "src/utils.py" in relative_paths
    # assert len(relative_paths) == 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mcpignore_patterns_respected(
    test_repository: Path,
    db_session: AsyncSession,
) -> None:
    """
    Test that .mcpignore patterns are respected during indexing.

    Expected behavior:
    - Create node_modules/ directory (should be ignored)
    - Verify it's not indexed

    This test MUST FAIL until T028 (scanner service) is implemented.
    """
    pytest.skip("Scanner service not implemented yet (T028)")

    # Create directory that should be ignored
    node_modules = test_repository / "node_modules"
    node_modules.mkdir()
    (node_modules / "package.js").write_text("module.exports = {};")

    # Future implementation:
    # from src.services.indexer import index_repository
    # from src.models.code_file import CodeFile
    #
    # await index_repository(
    #     path=test_repository,
    #     name="Test Repository",
    #     force_reindex=False,
    # )
    #
    # # Query all indexed files
    # stmt = select(CodeFile)
    # result = await db_session.execute(stmt)
    # code_files = result.scalars().all()
    #
    # relative_paths = [f.relative_path for f in code_files]
    #
    # # Verify node_modules is ignored
    # assert not any("node_modules" in path for path in relative_paths)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_code_chunks_created_for_functions_and_classes(
    test_repository: Path,
    db_session: AsyncSession,
) -> None:
    """
    Test that code chunks are created for functions and classes.

    Expected chunks from calculator.py:
    - add() function
    - multiply() function
    - Calculator class
    - calculate() method (within class)

    This test MUST FAIL until T029 (chunker service) is implemented.
    """
    pytest.skip("Chunker service not implemented yet (T029)")

    # Future implementation:
    # from src.services.indexer import index_repository
    # from src.models.code_chunk import CodeChunk
    # from src.models.code_file import CodeFile
    #
    # await index_repository(
    #     path=test_repository,
    #     name="Test Repository",
    #     force_reindex=False,
    # )
    #
    # # Get calculator.py file
    # stmt = select(CodeFile).where(CodeFile.relative_path == "src/calculator.py")
    # code_file = await db_session.scalar(stmt)
    # assert code_file is not None
    #
    # # Get chunks for this file
    # stmt = select(CodeChunk).where(CodeChunk.code_file_id == code_file.id)
    # result = await db_session.execute(stmt)
    # chunks = result.scalars().all()
    #
    # # Verify chunks exist
    # assert len(chunks) >= 4  # add, multiply, Calculator class, calculate method
    #
    # # Verify chunk types
    # chunk_types = {chunk.chunk_type for chunk in chunks}
    # assert "function" in chunk_types
    # assert "class" in chunk_types
    #
    # # Verify chunk content
    # chunk_contents = [chunk.content for chunk in chunks]
    # assert any("def add" in content for content in chunk_contents)
    # assert any("def multiply" in content for content in chunk_contents)
    # assert any("class Calculator" in content for content in chunk_contents)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_embeddings_generated_for_all_chunks(
    test_repository: Path,
    db_session: AsyncSession,
) -> None:
    """
    Test that embeddings are generated for all code chunks.

    Expected behavior:
    - All chunks should have non-null embeddings
    - Embeddings should be 768-dimensional vectors (nomic-embed-text)

    This test MUST FAIL until T030 (embedder service) is implemented.
    """
    pytest.skip("Embedder service not implemented yet (T030)")

    # Future implementation:
    # from src.services.indexer import index_repository
    # from src.models.code_chunk import CodeChunk
    #
    # await index_repository(
    #     path=test_repository,
    #     name="Test Repository",
    #     force_reindex=False,
    # )
    #
    # # Get all chunks
    # stmt = select(CodeChunk)
    # result = await db_session.execute(stmt)
    # chunks = result.scalars().all()
    #
    # # Verify all chunks have embeddings
    # assert len(chunks) > 0
    # for chunk in chunks:
    #     assert chunk.embedding is not None, f"Chunk {chunk.id} missing embedding"
    #     # pgvector stores as array, verify dimensions
    #     assert len(chunk.embedding) == 768, f"Chunk {chunk.id} has wrong embedding dimension"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_state_after_indexing(
    test_repository: Path,
    db_session: AsyncSession,
) -> None:
    """
    Test complete database state after indexing.

    Verifies:
    1. Repository record exists
    2. CodeFile records exist (2 files)
    3. CodeChunk records exist (>=5 chunks)
    4. All relationships are properly linked
    5. is_deleted=False for all files

    This test MUST FAIL until T019-T027 (models and migrations) are implemented.
    """
    pytest.skip("Database models and indexer not implemented yet (T019-T031)")

    # Future implementation:
    # from src.services.indexer import index_repository
    # from src.models.repository import Repository
    # from src.models.code_file import CodeFile
    # from src.models.code_chunk import CodeChunk
    #
    # result = await index_repository(
    #     path=test_repository,
    #     name="Test Repository",
    #     force_reindex=False,
    # )
    #
    # # Verify Repository
    # stmt = select(Repository).where(Repository.path == str(test_repository))
    # repo = await db_session.scalar(stmt)
    # assert repo is not None
    # assert repo.name == "Test Repository"
    # assert repo.is_active is True
    #
    # # Verify CodeFiles
    # stmt = select(CodeFile).where(CodeFile.repository_id == repo.id)
    # result_files = await db_session.execute(stmt)
    # files = result_files.scalars().all()
    # assert len(files) == 2
    #
    # for file in files:
    #     assert file.is_deleted is False
    #     assert file.deleted_at is None
    #     assert file.language == "py"
    #     assert file.content_hash is not None
    #     assert len(file.content_hash) == 64  # SHA-256
    #
    # # Verify CodeChunks
    # file_ids = [f.id for f in files]
    # stmt = select(CodeChunk).where(CodeChunk.code_file_id.in_(file_ids))
    # result_chunks = await db_session.execute(stmt)
    # chunks = result_chunks.scalars().all()
    # assert len(chunks) >= 5
    #
    # # Verify relationships
    # for chunk in chunks:
    #     assert chunk.code_file_id in file_ids
    #     assert chunk.start_line >= 1
    #     assert chunk.end_line >= chunk.start_line


@pytest.mark.integration
@pytest.mark.asyncio
async def test_indexing_performance_target(
    test_repository: Path,
    db_session: AsyncSession,
) -> None:
    """
    Test that indexing meets <60 second performance target.

    Performance requirement from spec:
    - Repository indexing should complete in <60 seconds

    This test MUST FAIL until T031 (indexer optimization) is implemented.
    """
    pytest.skip("Indexer service not implemented yet (T031)")

    # Future implementation:
    # from src.services.indexer import index_repository
    #
    # start_time = time.perf_counter()
    #
    # result = await index_repository(
    #     path=test_repository,
    #     name="Test Repository",
    #     force_reindex=False,
    # )
    #
    # duration = time.perf_counter() - start_time
    #
    # # Verify performance target
    # assert duration < 60, f"Indexing took {duration:.2f}s, exceeds 60s target"
    # assert result.duration_seconds < 60
    #
    # # For small repos like test, should be much faster
    # assert duration < 10, f"Small repo took {duration:.2f}s, should be <10s"
