import httpx
import pytest
from app.integrations.gemini import get_llm_provider, reset_llm_provider
from app.integrations.gemini.llm import MockLLMProvider, GeminiLLMProvider


@pytest.mark.asyncio
async def test_mock_llm_provider_generation() -> None:
    provider = MockLLMProvider()

    password_ans = await provider.generate("How can I reset my password?")
    assert "SSPR" in password_ans
    assert "KB-SEC-001" in password_ans

    vpn_ans = await provider.generate("VPN not connecting")
    assert "GlobalProtect" in vpn_ans
    assert "KB-NET-002" in vpn_ans


@pytest.mark.asyncio
async def test_gemini_llm_provider_mock_transport() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": "Here are the troubleshooting steps from KB-NET-002."
                                }
                            ]
                        }
                    }
                ]
            },
        )

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = GeminiLLMProvider(
        api_key="dummy-key",
        client=mock_client,
    )

    result = await provider.generate("How to fix VPN?")
    assert "KB-NET-002" in result


def test_get_llm_provider_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    mock_settings = config.Settings(gemini_api_key=None)
    monkeypatch.setattr("app.integrations.gemini.get_settings", lambda: mock_settings)
    reset_llm_provider()
    provider = get_llm_provider()
    assert isinstance(provider, MockLLMProvider)
    reset_llm_provider()


async def test_rag_generation_uses_json_mode_and_agreed_model():
    import json

    def handler(request):
        assert request.url.path.endswith(
            "/models/gemini-3.5-flash-lite:generateContent"
        )
        body = json.loads(request.content)
        assert body["generationConfig"]["responseMimeType"] == "application/json"
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": '{"answerable":false,"answer":"","source_ids":[]}'
                                }
                            ]
                        }
                    }
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await GeminiLLMProvider("test-key", client=client).generate(
            "test", "RAG_RESPONSE_JSON"
        )
        assert json.loads(result)["answerable"] is False


@pytest.mark.parametrize("status,expected_calls", [(401, 1), (429, 2), (503, 2)])
async def test_provider_failures_do_not_return_success_or_silently_change_models(
    status, expected_calls, monkeypatch
):
    from unittest.mock import AsyncMock

    monkeypatch.setattr("asyncio.sleep", AsyncMock())
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(
            status, json={"error": {"message": "secret-provider-detail"}}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RuntimeError, match="Gemini generation unavailable"):
            await GeminiLLMProvider("test-key", client=client).generate("test")
    assert (
        calls
        == ["/v1beta/models/gemini-3.5-flash-lite:generateContent"] * expected_calls
    )
