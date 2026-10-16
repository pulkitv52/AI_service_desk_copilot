"""Consent must remain explicit even with mixed or conditional language."""

import pytest
from app.integrations.servicenow import get_ticketing_provider


@pytest.mark.parametrize(
    "message",
    [
        "Create a ticket, but do not send it.",
        "Create a ticket. Actually, don't.",
        "Create a ticket? No need.",
        "Create a ticket if the VPN fails again.",
        "Create a ticket when I confirm.",
        "Can you explain how to create a ticket?",
        "What does create a ticket mean?",
    ],
)
@pytest.mark.parametrize("force_ticket", [False, True])
async def test_ambiguous_or_withdrawn_consent_never_dispatches(
    async_client, message, force_ticket
):
    initial = (
        await async_client.post(
            "/api/chat", json={"message": "My VPN is not connecting"}
        )
    ).json()
    # A force flag is explicit acceptance only for unambiguous instructions.
    # Informational questions are not refusals, so exercise those without it.
    if message.startswith(("Can you explain", "What does")):
        force_ticket = False
    response = await async_client.post(
        "/api/chat",
        json={
            "session_id": initial["session_id"],
            "message": message,
            "force_ticket": force_ticket,
        },
    )
    assert response.status_code == 200
    assert response.json()["ticket"] is None
    assert await get_ticketing_provider().query_incidents() == []


async def test_deferred_request_without_issue_does_not_invent_issue(async_client):
    first = (
        await async_client.post(
            "/api/chat", json={"message": "Create a ticket when I confirm."}
        )
    ).json()
    saved = (await async_client.get(f"/api/conversations/{first['session_id']}")).json()
    assert saved["issue"] == ""
    assert first["ticket"] is None
    again = (
        await async_client.post(
            "/api/chat", json={"session_id": first["session_id"], "message": "yes"}
        )
    ).json()
    assert again["ticket"] is None
    assert not await get_ticketing_provider().query_incidents()


async def test_deferred_request_can_be_explicitly_accepted_later(async_client):
    first = (
        await async_client.post(
            "/api/chat", json={"message": "My VPN is not connecting"}
        )
    ).json()
    cid = first["session_id"]
    delayed = (
        await async_client.post(
            "/api/chat",
            json={"session_id": cid, "message": "Create a ticket when I confirm."},
        )
    ).json()
    assert delayed["ticket"] is None
    accepted = (
        await async_client.post("/api/chat", json={"session_id": cid, "message": "yes"})
    ).json()
    assert accepted["ticket"]["assignment_group"] == "Network Support"
    assert accepted["ticket"]["short_description"] == "My VPN is not connecting"
    assert len(await get_ticketing_provider().query_incidents()) == 1
