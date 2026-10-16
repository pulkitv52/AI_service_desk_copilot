import httpx
import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.integrations import gemini
from app.integrations.gemini.catalog import verify_models


def test_settings_match_existing_vector_schema():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, gemini_embedding_dimension=3072)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, rag_similarity_threshold=0.05)


def test_configured_models_reach_providers(monkeypatch):
    settings = Settings(_env_file=None, gemini_api_key="test-key")
    monkeypatch.setattr(gemini, "get_settings", lambda: settings)
    assert gemini.get_llm_provider().model == "gemini-3.5-flash-lite"
    assert (
        gemini.get_embedding_provider().profile
        == "gemini:gemini-embedding-001:768:retrieval-v1"
    )


async def test_read_only_model_capability_check(monkeypatch):
    requested = []

    def handler(request):
        requested.append(request)
        method = (
            "embedContent" if "embedding" in request.url.path else "generateContent"
        )
        return httpx.Response(200, json={"supportedGenerationMethods": [method]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(
        "app.integrations.gemini.catalog.httpx.AsyncClient", lambda **kwargs: client
    )
    result = await verify_models(
        "test-key", "gemini-3.5-flash-lite", "gemini-embedding-001"
    )
    assert result["generation_model"] == "gemini-3.5-flash-lite"
    assert len(requested) == 2
    assert all(
        r.method == "GET" and r.headers["x-goog-api-key"] == "test-key"
        for r in requested
    )
