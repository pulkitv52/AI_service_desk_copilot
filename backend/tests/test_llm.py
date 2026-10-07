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
