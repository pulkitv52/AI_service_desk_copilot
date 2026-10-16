import httpx
import pytest
from app.integrations.servicenow.client import ServiceNowProvider
from app.models.ticket import TicketCreateRequest
from app.services.incident_service import IncidentService


@pytest.mark.parametrize("broken_reply", ["html", "missing-number"])
async def test_unusable_post_reply_reconciles_by_lookup_without_second_post(
    database, broken_reply
):
    methods = []
    payload = {
        "sys_id": "d" * 32,
        "number": "INC0010001",
        "priority": "5",
        "assignment_group": {"value": "c" * 32},
    }

    def handler(request):
        methods.append(request.method)
        if request.method == "POST":
            return (
                httpx.Response(201, text="<html>proxy error</html>")
                if broken_reply == "html"
                else httpx.Response(201, json={"result": {"sys_id": "d" * 32}})
            )
        assert request.url.params["sysparm_query"] == "correlation_id=recovery-case"
        return httpx.Response(200, json={"result": [payload]})

    async with httpx.AsyncClient(
        base_url="https://pdi.test", transport=httpx.MockTransport(handler)
    ) as client:
        provider = ServiceNowProvider(
            "https://pdi.test",
            "test-user",
            "test-password",
            client=client,
            caller_sys_id="a" * 32,
            fallback_group_sys_id="c" * 32,
        )
        request = TicketCreateRequest(
            short_description="Synthetic VPN failure", correlation_id="recovery-case"
        )
        async with database() as session:
            assert (
                await IncidentService(session, provider).create_or_reconcile(request)
            )[0] == "pending"
        async with database() as session:
            status, recovered = await IncidentService(
                session, provider
            ).create_or_reconcile(request)
            assert status == "created"
            assert recovered.number == "INC0010001"
            assert recovered.priority == "P5"
    assert methods == ["POST", "GET"]
