import pytest
from app.integrations.servicenow.mock import MockTicketingProvider
from app.models.ticket import (
    TicketCreateRequest,
    TicketUpdateRequest,
    TicketUrgency,
    TicketImpact,
    TicketState,
)


@pytest.mark.asyncio
async def test_mock_create_and_get_incident() -> None:
    provider = MockTicketingProvider()
    create_req = TicketCreateRequest(
        short_description="Unable to access VPN",
        description="GlobalProtect fails to connect after password reset",
        urgency=TicketUrgency.HIGH,
        impact=TicketImpact.MEDIUM,
        category="network",
        assignment_group="Network Support",
    )
    created = await provider.create_incident(create_req)

    assert created.sys_id is not None
    assert created.number.startswith("INC")
    assert created.short_description == "Unable to access VPN"
    assert created.urgency == TicketUrgency.HIGH.value
    assert created.impact == TicketImpact.MEDIUM.value
    assert created.assignment_group == "Network Support"
    assert created.provider == "mock"

    # Fetch by sys_id
    by_sys_id = await provider.get_incident(created.sys_id)
    assert by_sys_id is not None
    assert by_sys_id.number == created.number

    # Fetch by incident number
    by_number = await provider.get_incident(created.number)
    assert by_number is not None
    assert by_number.sys_id == created.sys_id


@pytest.mark.asyncio
async def test_mock_update_incident() -> None:
    provider = MockTicketingProvider()
    create_req = TicketCreateRequest(
        short_description="Printer offline",
        urgency=TicketUrgency.LOW,
        impact=TicketImpact.LOW,
    )
    created = await provider.create_incident(create_req)

    update_req = TicketUpdateRequest(
        state=TicketState.IN_PROGRESS,
        assignment_group="Hardware Support",
    )
    updated = await provider.update_incident(created.sys_id, update_req)

    assert updated is not None
    assert updated.state == TicketState.IN_PROGRESS.value
    assert updated.assignment_group == "Hardware Support"


@pytest.mark.asyncio
async def test_mock_query_incidents() -> None:
    provider = MockTicketingProvider()
    await provider.create_incident(
        TicketCreateRequest(short_description="SAP purchase order error")
    )
    await provider.create_incident(
        TicketCreateRequest(short_description="Outlook calendar sync issue")
    )

    results = await provider.query_incidents("SAP")
    assert len(results) == 1
    assert "SAP" in results[0].short_description


@pytest.mark.asyncio
async def test_priority_recalculated_when_impact_or_urgency_changes() -> None:
    provider = MockTicketingProvider()
    created = await provider.create_incident(
        TicketCreateRequest(short_description="VPN issue")
    )
    assert created.priority == "P5"
    updated = await provider.update_incident(
        created.sys_id, TicketUpdateRequest(urgency=TicketUrgency.HIGH)
    )
    assert updated.priority == "P3"
    updated = await provider.update_incident(
        created.sys_id, TicketUpdateRequest(impact=TicketImpact.HIGH)
    )
    assert updated.priority == "P1"
    updated = await provider.update_incident(
        created.sys_id, TicketUpdateRequest(state=TicketState.IN_PROGRESS)
    )
    assert updated.priority == "P1"
