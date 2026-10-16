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


@pytest.mark.parametrize("task", ["RETRIEVAL_QUERY", "RETRIEVAL_DOCUMENT"])
async def test_gemini_embedding_tasks_dimensions_and_normalization(task):
    import json
    import httpx
    from app.integrations.gemini.embeddings import GeminiEmbeddingProvider

    def handler(request):
        body = json.loads(request.content)
        assert body["taskType"] == task
        assert body["outputDimensionality"] == 768
        assert request.headers["x-goog-api-key"] == "test-key"
        assert "key=" not in str(request.url)
        return httpx.Response(200, json={"embedding": {"values": [2.0] * 768}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = GeminiEmbeddingProvider("test-key", client=client)
        vector = await provider.embed_text("Synthetic test", task_type=task)
        assert len(vector) == 768
        assert sum(v * v for v in vector) == pytest.approx(1.0)


@pytest.mark.parametrize(
    "values", [[], [1.0], [0.0] * 768, [float("nan")] * 768, [float("inf")] * 768]
)
async def test_gemini_rejects_invalid_embeddings(values):
    import httpx
    from app.integrations.gemini.embeddings import GeminiEmbeddingProvider

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(
                200,
                content=__import__("json")
                .dumps({"embedding": {"values": values}})
                .encode(),
            )
        )
    ) as client:
        with pytest.raises(RuntimeError, match="Gemini embedding request failed"):
            await GeminiEmbeddingProvider("test-key", client=client).embed_text("test")


@pytest.mark.parametrize("status,expected_calls", [(401, 1), (429, 2), (503, 2)])
async def test_embedding_retry_is_bounded_and_only_transient(
    status, expected_calls, monkeypatch
):
    from unittest.mock import AsyncMock
    import httpx
    from app.integrations.gemini.embeddings import GeminiEmbeddingProvider

    monkeypatch.setattr("asyncio.sleep", AsyncMock())
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(status, text="secret-provider-error")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RuntimeError) as error:
            await GeminiEmbeddingProvider("test-key", client=client).embed_text("test")
    assert len(requests) == expected_calls
    assert "secret-provider-error" not in str(error.value)


async def test_embedding_document_batch_uses_document_task():
    import json
    import httpx
    from app.integrations.gemini.embeddings import GeminiEmbeddingProvider

    tasks = []

    def handler(request):
        tasks.append(json.loads(request.content)["taskType"])
        return httpx.Response(200, json={"embedding": {"values": [1.0] * 768}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        vectors = await GeminiEmbeddingProvider("test-key", client=client).embed_batch(
            ["doc one", "doc two"]
        )
    assert tasks == ["RETRIEVAL_DOCUMENT"] * 2
    assert len(vectors) == 2
