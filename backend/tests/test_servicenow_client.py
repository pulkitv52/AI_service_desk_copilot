import httpx
import pytest
from app.integrations.servicenow.client import ServiceNowProvider, ServiceNowError
from app.models.ticket import (
    TicketCreateRequest,
    TicketUpdateRequest,
    TicketUrgency,
    TicketImpact,
    TicketState,
)


@pytest.fixture
def mock_servicenow_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        # Create incident
        if (
            request.method == "POST"
            and url_str == "https://dev12345.service-now.com/api/now/table/incident"
        ):
            return httpx.Response(
                201,
                json={
                    "result": {
                        "sys_id": "abc123sysid",
                        "number": "INC0010001",
                        "short_description": "Cannot connect to VPN",
                        "description": "Details here",
                        "state": "1",
                        "urgency": "2",
                        "impact": "2",
                        "priority": "3",
                        "category": "network",
                        "assignment_group": {"display_value": "Network Support"},
                        "sys_created_on": "2026-10-07 10:00:00",
                    }
                },
            )
        # Get incident by sys_id
        if (
            request.method == "GET"
            and url_str
            == "https://dev12345.service-now.com/api/now/table/incident/abc123sysid"
        ):
            return httpx.Response(
                200,
                json={
                    "result": {
                        "sys_id": "abc123sysid",
                        "number": "INC0010001",
                        "short_description": "Cannot connect to VPN",
                        "state": "1",
                        "urgency": "2",
                        "impact": "2",
                        "priority": "3",
                    }
                },
            )
        # 404 for missing sys_id
        if request.method == "GET" and "incident/nonexistent" in url_str:
            return httpx.Response(404, json={"error": {"message": "Not Found"}})
        # Update incident
        if (
            request.method == "PATCH"
            and url_str
            == "https://dev12345.service-now.com/api/now/table/incident/abc123sysid"
        ):
            return httpx.Response(
                200,
                json={
                    "result": {
                        "sys_id": "abc123sysid",
                        "number": "INC0010001",
                        "short_description": "Cannot connect to VPN",
                        "state": "2",
                        "urgency": "2",
                        "impact": "2",
                        "priority": "3",
                    }
                },
            )
        return httpx.Response(404)

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_servicenow_provider_create_incident(
    mock_servicenow_transport: httpx.MockTransport,
) -> None:
    client = httpx.AsyncClient(
        transport=mock_servicenow_transport, base_url="https://dev12345.service-now.com"
    )
    provider = ServiceNowProvider(
        instance_url="https://dev12345.service-now.com",
        username="admin",
        password="secretpassword",
        client=client,
    )

    ticket_req = TicketCreateRequest(
        short_description="Cannot connect to VPN",
        description="Details here",
        urgency=TicketUrgency.MEDIUM,
        impact=TicketImpact.MEDIUM,
        category="network",
    )
    response = await provider.create_incident(ticket_req)

    assert response.sys_id == "abc123sysid"
    assert response.number == "INC0010001"
    assert response.short_description == "Cannot connect to VPN"
    assert response.assignment_group == "Network Support"
    assert response.provider == "servicenow"


@pytest.mark.asyncio
async def test_servicenow_provider_get_incident(
    mock_servicenow_transport: httpx.MockTransport,
) -> None:
    client = httpx.AsyncClient(
        transport=mock_servicenow_transport, base_url="https://dev12345.service-now.com"
    )
    provider = ServiceNowProvider(
        instance_url="https://dev12345.service-now.com",
        username="admin",
        password="secretpassword",
        client=client,
    )

    incident = await provider.get_incident("abc123sysid")
    assert incident is not None
    assert incident.number == "INC0010001"

    missing = await provider.get_incident("nonexistent")
    assert missing is None


@pytest.mark.asyncio
async def test_servicenow_provider_update_incident(
    mock_servicenow_transport: httpx.MockTransport,
) -> None:
    client = httpx.AsyncClient(
        transport=mock_servicenow_transport, base_url="https://dev12345.service-now.com"
    )
    provider = ServiceNowProvider(
        instance_url="https://dev12345.service-now.com",
        username="admin",
        password="secretpassword",
        client=client,
    )

    updated = await provider.update_incident(
        "abc123sysid", TicketUpdateRequest(state=TicketState.IN_PROGRESS)
    )
    assert updated is not None
    assert updated.state == "2"
