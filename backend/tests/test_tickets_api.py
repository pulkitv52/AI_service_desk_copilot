import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_ticket_api_success(async_client: AsyncClient) -> None:
    payload = {
        "short_description": "Password reset needed for Active Directory",
        "description": "User locked out after 3 invalid attempts",
        "urgency": "2",
        "impact": "2",
        "category": "Identity",
        "assignment_group": "Identity & Access Support",
    }
    response = await async_client.post("/api/tickets", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["number"].startswith("INC")
    assert data["short_description"] == payload["short_description"]
    assert data["urgency"] == "2"
    assert data["impact"] == "2"
    assert data["assignment_group"] == "Identity & Access Support"


@pytest.mark.asyncio
async def test_create_ticket_api_validation_error(async_client: AsyncClient) -> None:
    # short_description is shorter than minimum length (3)
    payload = {
        "short_description": "hi",
    }
    response = await async_client.post("/api/tickets", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_ticket_api_and_update(async_client: AsyncClient) -> None:
    create_resp = await async_client.post(
        "/api/tickets",
        json={"short_description": "Outlook calendar not syncing with mobile device"},
    )
    assert create_resp.status_code == 201
    created = create_resp.json()
    sys_id = created["sys_id"]
    number = created["number"]

    # Retrieve by sys_id
    get_resp = await async_client.get(f"/api/tickets/{sys_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["number"] == number

    # Retrieve by number
    get_num_resp = await async_client.get(f"/api/tickets/{number}")
    assert get_num_resp.status_code == 200
    assert get_num_resp.json()["sys_id"] == sys_id

    # Update ticket
    update_resp = await async_client.patch(
        f"/api/tickets/{sys_id}",
        json={"state": "2", "assignment_group": "Collaboration Support"},
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["state"] == "2"
    assert updated["assignment_group"] == "Collaboration Support"


@pytest.mark.asyncio
async def test_get_ticket_not_found(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/tickets/non_existent_sys_id")
    assert response.status_code == 404
