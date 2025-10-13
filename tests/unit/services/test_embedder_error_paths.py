"""Unit tests for embedder.py error paths and edge cases.

This test suite targets uncovered lines in src/services/embedder.py to improve
coverage from 56.98% to 90%+.

Test Coverage Areas:
- OllamaEmbedder singleton initialization
- HTTP timeout handling with retry logic
- HTTP connection errors (Ollama not running)
- HTTP status errors (404, 500, etc.)
- Response validation errors (invalid JSON, wrong dimensions)
- Exponential backoff retry logic
- Empty text validation
- Batch embedding error handling
- Model validation failures
- Connection pooling edge cases

Constitutional Compliance:
- Principle VII: Test-driven development with comprehensive error coverage
- Principle VIII: Type-safe test patterns with mypy --strict
- Principle V: Production quality with edge case validation
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from src.services.embedder import (
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


# ==============================================================================
# Test Fixtures
# ==============================================================================


@pytest.fixture
def mock_embedding_response() -> dict[str, Any]:
    """Create a valid embedding response with 768 dimensions."""
    return {"embedding": [0.1] * 768}


@pytest.fixture
def mock_models_response() -> dict[str, Any]:
    """Create a valid models list response."""
    return {
        "models": [
            {"name": "nomic-embed-text", "modified_at": "2024-01-01T00:00:00Z", "size": 1000000}
        ]
    }


@pytest.fixture
def embedder() -> OllamaEmbedder:
    """Create a fresh OllamaEmbedder instance for testing."""
    # Reset singleton instance
    OllamaEmbedder._instance = None
    OllamaEmbedder._client = None
    return OllamaEmbedder()


# ==============================================================================
# OllamaEmbedder Initialization Tests
# ==============================================================================


def test_ollama_embedder_singleton() -> None:
    """Test OllamaEmbedder singleton pattern.

    Covers: Lines 168-172 (singleton __new__ method)
    """
    # Reset singleton
    OllamaEmbedder._instance = None
    OllamaEmbedder._client = None

    embedder1 = OllamaEmbedder()
    embedder2 = OllamaEmbedder()

    assert embedder1 is embedder2
    assert OllamaEmbedder._instance is embedder1


def test_ollama_embedder_initialization_idempotent(embedder: OllamaEmbedder) -> None:
    """Test OllamaEmbedder initialization is idempotent.

    Covers: Lines 176-177 (early return if already initialized)
    """
    client_before = embedder._client

    # Call __init__ again
    embedder.__init__()

    # Client should be the same instance
    assert embedder._client is client_before


@pytest.mark.asyncio
async def test_ollama_embedder_close(embedder: OllamaEmbedder) -> None:
    """Test OllamaEmbedder close method.

    Covers: Lines 202-207 (close method)
    """
    with patch.object(embedder._client, "aclose", new_callable=AsyncMock) as mock_close:
        await embedder.close()

    mock_close.assert_awaited_once()
    assert embedder._client is None


@pytest.mark.asyncio
async def test_ollama_embedder_close_when_already_closed() -> None:
    """Test closing embedder when already closed is safe.

    Covers: Lines 204-207 (None check in close)
    """
    embedder = OllamaEmbedder()
    await embedder.close()

    # Close again should be safe
    await embedder.close()


# ==============================================================================
# HTTP Timeout Error Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_request_with_retry_timeout_max_retries(embedder: OllamaEmbedder) -> None:
    """Test timeout error after max retries.

    Covers: Lines 237-245 (timeout handling with max retries)
    """
    from src.services.embedder import EmbeddingRequest

    request = EmbeddingRequest(model="nomic-embed-text", prompt="test")

    with patch.object(
        embedder._client, "post", side_effect=httpx.TimeoutException("Timeout")
    ):
        with pytest.raises(OllamaTimeoutError, match="timed out after 3 attempts"):
            await embedder._request_with_retry(request)


@pytest.mark.asyncio
async def test_request_with_retry_timeout_retry_logic(embedder: OllamaEmbedder) -> None:
    """Test exponential backoff retry logic for timeouts.

    Covers: Lines 237-296 (retry logic with backoff)
    """
    from src.services.embedder import EmbeddingRequest

    request = EmbeddingRequest(model="nomic-embed-text", prompt="test")

    call_count = 0

    async def mock_post(*args: Any, **kwargs: Any) -> Mock:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise httpx.TimeoutException("Timeout")
        # Third attempt succeeds
        response = Mock()
        response.json.return_value = {"embedding": [0.1] * 768}
        response.raise_for_status = Mock()
        return response

    with patch.object(embedder._client, "post", side_effect=mock_post):
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await embedder._request_with_retry(request)

    assert len(result) == 768
    assert call_count == 3
    # Should have slept twice (after 1st and 2nd attempt)
    assert mock_sleep.await_count == 2


# ==============================================================================
# HTTP Connection Error Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_request_with_retry_connection_error(embedder: OllamaEmbedder) -> None:
    """Test connection error when Ollama is not running.

    Covers: Lines 261-269 (connection error handling)
    """
    from src.services.embedder import EmbeddingRequest

    request = EmbeddingRequest(model="nomic-embed-text", prompt="test")

    with patch.object(embedder._client, "post", side_effect=httpx.ConnectError("Connection refused")):
        with pytest.raises(OllamaConnectionError, match="Unable to connect to Ollama"):
            await embedder._request_with_retry(request)


@pytest.mark.asyncio
async def test_request_with_retry_connection_error_with_retries(embedder: OllamaEmbedder) -> None:
    """Test connection error retries before giving up.

    Covers: Lines 261-269 (connection error retry logic)
    """
    from src.services.embedder import EmbeddingRequest

    request = EmbeddingRequest(model="nomic-embed-text", prompt="test")

    call_count = 0

    async def mock_post(*args: Any, **kwargs: Any) -> Mock:
        nonlocal call_count
        call_count += 1
        raise httpx.ConnectError("Connection refused")

    with patch.object(embedder._client, "post", side_effect=mock_post):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(OllamaConnectionError):
                await embedder._request_with_retry(request)

    assert call_count == 3  # Should retry 3 times


# ==============================================================================
# HTTP Status Error Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_request_with_retry_http_404_error(embedder: OllamaEmbedder) -> None:
    """Test 404 error (model not found) fails immediately without retry.

    Covers: Lines 247-259 (HTTP status error with 404 special case)
    """
    from src.services.embedder import EmbeddingRequest

    request = EmbeddingRequest(model="nonexistent-model", prompt="test")

    mock_response = Mock()
    mock_response.status_code = 404

    with patch.object(
        embedder._client,
        "post",
        side_effect=httpx.HTTPStatusError("Not found", request=Mock(), response=mock_response),
    ):
        with pytest.raises(OllamaError, match="HTTP error"):
            await embedder._request_with_retry(request, attempt=1)


@pytest.mark.asyncio
async def test_request_with_retry_http_500_error_with_retries(embedder: OllamaEmbedder) -> None:
    """Test 500 error retries before giving up.

    Covers: Lines 247-259 (HTTP status error retry logic)
    """
    from src.services.embedder import EmbeddingRequest

    request = EmbeddingRequest(model="nomic-embed-text", prompt="test")

    mock_response = Mock()
    mock_response.status_code = 500

    call_count = 0

    async def mock_post(*args: Any, **kwargs: Any) -> Mock:
        nonlocal call_count
        call_count += 1
        raise httpx.HTTPStatusError("Server error", request=Mock(), response=mock_response)

    with patch.object(embedder._client, "post", side_effect=mock_post):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(OllamaError, match="HTTP error"):
                await embedder._request_with_retry(request)

    assert call_count == 3


# ==============================================================================
# Response Validation Error Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_request_with_retry_invalid_response_format(embedder: OllamaEmbedder) -> None:
    """Test invalid response format raises ValidationError.

    Covers: Lines 271-277 (ValueError/Pydantic validation error handling)
    """
    from src.services.embedder import EmbeddingRequest

    request = EmbeddingRequest(model="nomic-embed-text", prompt="test")

    mock_response = Mock()
    mock_response.json.return_value = {"wrong_key": "wrong_value"}
    mock_response.raise_for_status = Mock()

    with patch.object(embedder._client, "post", return_value=mock_response):
        with pytest.raises(OllamaValidationError, match="Invalid response format"):
            await embedder._request_with_retry(request)


@pytest.mark.asyncio
async def test_request_with_retry_wrong_embedding_dimensions(embedder: OllamaEmbedder) -> None:
    """Test wrong embedding dimensions raises ValidationError.

    Covers: Lines 82-85 (embedding dimension validation)
    """
    from src.services.embedder import EmbeddingRequest

    request = EmbeddingRequest(model="nomic-embed-text", prompt="test")

    mock_response = Mock()
    mock_response.json.return_value = {"embedding": [0.1] * 512}  # Wrong dimension
    mock_response.raise_for_status = Mock()

    with patch.object(embedder._client, "post", return_value=mock_response):
        with pytest.raises(OllamaValidationError, match="Invalid response format"):
            await embedder._request_with_retry(request)


# ==============================================================================
# Unexpected Error Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_request_with_retry_unexpected_error(embedder: OllamaEmbedder) -> None:
    """Test unexpected error handling with retries.

    Covers: Lines 279-285 (generic Exception handling)
    """
    from src.services.embedder import EmbeddingRequest

    request = EmbeddingRequest(model="nomic-embed-text", prompt="test")

    call_count = 0

    async def mock_post(*args: Any, **kwargs: Any) -> Mock:
        nonlocal call_count
        call_count += 1
        raise RuntimeError("Unexpected error")

    with patch.object(embedder._client, "post", side_effect=mock_post):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(OllamaError, match="Unexpected error"):
                await embedder._request_with_retry(request)

    assert call_count == 3


# ==============================================================================
# Client Not Initialized Error Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_request_with_retry_client_not_initialized() -> None:
    """Test error when client is not initialized.

    Covers: Lines 224-225 (client None check)
    """
    from src.services.embedder import EmbeddingRequest

    embedder = OllamaEmbedder()
    await embedder.close()  # Set _client to None

    request = EmbeddingRequest(model="nomic-embed-text", prompt="test")

    with pytest.raises(OllamaError, match="Client not initialized"):
        await embedder._request_with_retry(request)


# ==============================================================================
# Empty Text Validation Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_generate_embedding_empty_text(embedder: OllamaEmbedder) -> None:
    """Test empty text raises ValueError.

    Covers: Lines 311-312 (empty text validation)
    """
    with pytest.raises(ValueError, match="Text cannot be empty"):
        await embedder.generate_embedding("")


@pytest.mark.asyncio
async def test_generate_embeddings_empty_list(embedder: OllamaEmbedder) -> None:
    """Test empty text list raises ValueError.

    Covers: Lines 334-335 (empty texts validation)
    """
    with pytest.raises(ValueError, match="Texts cannot be empty"):
        await embedder.generate_embeddings([])


@pytest.mark.asyncio
async def test_generate_embeddings_contains_empty_string(embedder: OllamaEmbedder) -> None:
    """Test text list with empty string raises ValueError.

    Covers: Lines 337-338 (non-empty texts validation)
    """
    with pytest.raises(ValueError, match="All texts must be non-empty"):
        await embedder.generate_embeddings(["valid text", "", "another text"])


# ==============================================================================
# Batch Embedding Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_generate_embeddings_success(embedder: OllamaEmbedder) -> None:
    """Test successful batch embedding generation.

    Covers: Lines 317-368 (batch embedding logic)
    """
    texts = ["text 1", "text 2", "text 3"]

    mock_response = Mock()
    mock_response.json.return_value = {"embedding": [0.1] * 768}
    mock_response.raise_for_status = Mock()

    with patch.object(embedder._client, "post", return_value=mock_response):
        result = await embedder.generate_embeddings(texts)

    assert len(result) == 3
    assert all(len(emb) == 768 for emb in result)


@pytest.mark.asyncio
async def test_generate_embeddings_partial_failure() -> None:
    """Test partial failure in batch embedding generation.

    Some embeddings succeed, others fail - should raise error.
    """
    embedder = OllamaEmbedder()
    texts = ["text 1", "text 2", "text 3"]

    call_count = 0

    async def mock_post(*args: Any, **kwargs: Any) -> Mock:
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise httpx.TimeoutException("Timeout")
        mock_response = Mock()
        mock_response.json.return_value = {"embedding": [0.1] * 768}
        mock_response.raise_for_status = Mock()
        return mock_response

    with patch.object(embedder._client, "post", side_effect=mock_post):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(OllamaTimeoutError):
                await embedder.generate_embeddings(texts)


# ==============================================================================
# Model Validation Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_validate_ollama_connection_success(mock_models_response: dict[str, Any]) -> None:
    """Test successful Ollama connection validation.

    Covers: Lines 376-434 (validate_ollama_connection success path)
    """
    mock_response = Mock()
    mock_response.json.return_value = mock_models_response
    mock_response.raise_for_status = Mock()

    async def mock_get(*args: Any, **kwargs: Any) -> Mock:
        return mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = Mock()
        mock_client.get = mock_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.return_value = mock_client

        result = await validate_ollama_connection()

    assert result is True


@pytest.mark.asyncio
async def test_validate_ollama_connection_model_not_found(mock_models_response: dict[str, Any]) -> None:
    """Test model not found error in validation.

    Covers: Lines 407-422 (model not found error path)
    """
    # Mock response with different model
    models_response = {
        "models": [
            {"name": "different-model", "modified_at": "2024-01-01T00:00:00Z", "size": 1000000}
        ]
    }

    mock_response = Mock()
    mock_response.json.return_value = models_response
    mock_response.raise_for_status = Mock()

    async def mock_get(*args: Any, **kwargs: Any) -> Mock:
        return mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = Mock()
        mock_client.get = mock_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.return_value = mock_client

        with pytest.raises(OllamaModelNotFoundError, match="not found in Ollama"):
            await validate_ollama_connection()


@pytest.mark.asyncio
async def test_validate_ollama_connection_connect_error() -> None:
    """Test connection error in validation (Ollama not running).

    Covers: Lines 436-445 (connection error in validation)
    """
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = Mock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.return_value = mock_client

        with pytest.raises(OllamaConnectionError, match="Unable to connect to Ollama"):
            await validate_ollama_connection()


@pytest.mark.asyncio
async def test_validate_ollama_connection_http_error() -> None:
    """Test HTTP error in validation.

    Covers: Lines 447-457 (HTTP status error in validation)
    """
    mock_response = Mock()
    mock_response.status_code = 500

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = Mock()
        mock_client.get = AsyncMock(
            side_effect=httpx.HTTPStatusError("Server error", request=Mock(), response=mock_response)
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.return_value = mock_client

        with pytest.raises(OllamaError, match="HTTP error"):
            await validate_ollama_connection()


# ==============================================================================
# Public API Convenience Function Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_generate_embedding_convenience_function() -> None:
    """Test convenience function uses singleton embedder.

    Covers: Lines 460-476 (generate_embedding convenience function)
    """
    mock_response = Mock()
    mock_response.json.return_value = {"embedding": [0.1] * 768}
    mock_response.raise_for_status = Mock()

    with patch("src.services.embedder.OllamaEmbedder") as mock_embedder_class:
        mock_embedder = Mock()
        mock_embedder.generate_embedding = AsyncMock(return_value=[0.1] * 768)
        mock_embedder_class.return_value = mock_embedder

        result = await generate_embedding("test text")

    assert len(result) == 768
    mock_embedder.generate_embedding.assert_awaited_once_with("test text")


@pytest.mark.asyncio
async def test_generate_embeddings_convenience_function() -> None:
    """Test convenience function for batch embeddings.

    Covers: Lines 479-495 (generate_embeddings convenience function)
    """
    with patch("src.services.embedder.OllamaEmbedder") as mock_embedder_class:
        mock_embedder = Mock()
        mock_embedder.generate_embeddings = AsyncMock(return_value=[[0.1] * 768, [0.2] * 768])
        mock_embedder_class.return_value = mock_embedder

        result = await generate_embeddings(["text 1", "text 2"])

    assert len(result) == 2
    mock_embedder.generate_embeddings.assert_awaited_once()
