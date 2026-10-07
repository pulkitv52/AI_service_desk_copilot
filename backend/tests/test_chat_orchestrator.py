import pytest
from httpx import AsyncClient
from app.models.chat import ChatResponseType


@pytest.mark.asyncio
async def test_chat_password_reset_deflection(async_client: AsyncClient) -> None:
    response = await async_client.post(
        "/api/chat",
        json={"message": "I forgot my password. How can I reset it?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["response_type"] == ChatResponseType.DEFLECTED_RAG.value
    assert data["ticket"] is None
    assert "password" in data["message"].lower()
    assert len(data["sources"]) > 0


@pytest.mark.asyncio
async def test_chat_forced_ticket_creation(async_client: AsyncClient) -> None:
    response = await async_client.post(
        "/api/chat",
        json={
            "message": "I tried resetting password but steps did not work. Please open a ticket.",
            "force_ticket": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["response_type"] == ChatResponseType.TICKET_CREATED.value
    assert data["ticket"] is not None
    assert data["ticket"]["number"].startswith("INC")
    assert data["ticket"]["assignment_group"] == "Identity & Access Support"


@pytest.mark.asyncio
async def test_chat_software_request(async_client: AsyncClient) -> None:
    response = await async_client.post(
        "/api/chat",
        json={"message": "I need VS Code installed on my machine."},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["response_type"] == ChatResponseType.SERVICE_REQUEST.value
    assert "company portal" in data["message"].lower()


@pytest.mark.asyncio
async def test_chat_sap_issue_escalation(async_client: AsyncClient) -> None:
    response = await async_client.post(
        "/api/chat",
        json={
            "message": "SAP is failing and the steps didn't work. Please escalate this.",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["response_type"] == ChatResponseType.TICKET_CREATED.value
    assert data["ticket"] is not None
    assert data["ticket"]["assignment_group"] == "SAP Support"
