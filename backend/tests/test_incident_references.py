import httpx
import pytest

from app.integrations.servicenow.client import ServiceNowError, ServiceNowProvider
from app.models.ticket import TicketCreateRequest


async def test_mapped_references_and_fallback_are_sys_ids():
    sent = []

    def handler(request):
        import json

        payload = json.loads(request.content)
        sent.append(payload)
        return httpx.Response(
            201, json={"result": {"sys_id": "d" * 32, "number": "INC001", **payload}}
        )

    async with httpx.AsyncClient(
        base_url="https://pdi.test", transport=httpx.MockTransport(handler)
    ) as client:
        provider = ServiceNowProvider(
            "https://pdi.test",
            "demo",
            "not-a-real-password",
            client=client,
            caller_sys_id="a" * 32,
            group_ids={"Network Support": "b" * 32},
            fallback_group_sys_id="c" * 32,
        )
        network = await provider.create_incident(
            TicketCreateRequest(
                short_description="VPN down",
                assignment_group="Network Support",
                caller_id="untrusted-caller",
            )
        )
        fallback = await provider.create_incident(
            TicketCreateRequest(
                short_description="SAP fails", assignment_group="SAP Support"
            )
        )
    assert sent[0]["caller_id"] == "a" * 32
    assert sent[0]["assignment_group"] == "b" * 32
    assert sent[1]["assignment_group"] == "c" * 32
    assert network.assignment_group == "Network Support"
    assert fallback.assignment_group == "Service Desk L1"


async def test_missing_reference_configuration_prevents_post():
    calls = []
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: calls.append(r))
    ) as client:
        provider = ServiceNowProvider(
            "https://pdi.test", "demo", "not-real", client=client
        )
        with pytest.raises(ServiceNowError, match="caller"):
            await provider.create_incident(
                TicketCreateRequest(short_description="VPN down")
            )
    assert not calls


async def test_credential_error_body_is_not_propagated():
    async with httpx.AsyncClient(
        base_url="https://pdi.test",
        transport=httpx.MockTransport(
            lambda r: httpx.Response(401, text="private-password-and-token")
        ),
    ) as client:
        provider = ServiceNowProvider(
            "https://pdi.test", "demo", "not-real", client=client
        )
        with pytest.raises(ServiceNowError) as error:
            await provider.query_incidents()
    assert str(error.value) == "ServiceNow returned HTTP 401"


async def test_gemini_key_is_only_in_header():
    from app.integrations.gemini.llm import GeminiLLMProvider
    from app.integrations.gemini.embeddings import GeminiEmbeddingProvider

    seen = []

    def handler(request):
        seen.append(request)
        if ":embedContent" in request.url.path:
            return httpx.Response(200, json={"embedding": {"values": [1.0] * 768}})
        return httpx.Response(
            200, json={"candidates": [{"content": {"parts": [{"text": "grounded"}]}}]}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        await GeminiLLMProvider("private-api-key", client=client).generate("test")
        await GeminiEmbeddingProvider("private-api-key", client=client).embed_text(
            "test"
        )
    assert all("private-api-key" not in str(r.url) for r in seen)
    assert all(r.headers["x-goog-api-key"] == "private-api-key" for r in seen)


@pytest.mark.parametrize(
    "raw,expected", [("5", "P5"), ("P5", "P5"), ("", None), (None, None)]
)
def test_servicenow_priority_preserved_without_invented_default(raw, expected):
    provider = ServiceNowProvider("https://pdi.test", "demo", "not-real")
    result = {"sys_id": "d" * 32, "number": "INC001"}
    if raw is not None:
        result["priority"] = raw
    assert provider._map_result_to_response(result).priority == expected
