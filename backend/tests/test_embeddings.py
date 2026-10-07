import math
import pytest
from app.integrations.gemini.embeddings import (
    MockEmbeddingProvider,
    EMBEDDING_DIMENSION,
)


@pytest.mark.asyncio
async def test_mock_embedding_provider_dimension_and_norm() -> None:
    provider = MockEmbeddingProvider()
    vec = await provider.embed_text("How do I reset my Windows password?")

    assert len(vec) == EMBEDDING_DIMENSION
    # Check unit norm: sqrt(sum(x^2)) ~= 1.0
    norm = math.sqrt(sum(x * x for x in vec))
    assert abs(norm - 1.0) < 1e-4


@pytest.mark.asyncio
async def test_mock_embedding_provider_deterministic() -> None:
    provider = MockEmbeddingProvider()
    vec1 = await provider.embed_text("GlobalProtect VPN connection failed")
    vec2 = await provider.embed_text("GlobalProtect VPN connection failed")
    assert vec1 == vec2


@pytest.mark.asyncio
async def test_mock_embedding_provider_batch() -> None:
    provider = MockEmbeddingProvider()
    texts = [
        "First document text",
        "Second document text",
        "Third document text",
    ]
    vectors = await provider.embed_batch(texts)
    assert len(vectors) == 3
    for v in vectors:
        assert len(v) == EMBEDDING_DIMENSION
