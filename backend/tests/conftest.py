from typing import AsyncGenerator
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.integrations.servicenow import reset_ticketing_provider
from app.main import app


@pytest.fixture(autouse=True)
def reset_provider_state() -> None:
    """Ensure singleton provider is reset between tests."""
    from app.integrations.gemini import reset_embedding_provider, reset_llm_provider

    reset_ticketing_provider()
    reset_llm_provider()
    reset_embedding_provider()
    yield
    reset_ticketing_provider()
    reset_llm_provider()
    reset_embedding_provider()


@pytest.fixture
def test_settings() -> Settings:
    """Return test settings with mock enabled."""
    return Settings(
        environment="test",
        use_mock_servicenow=True,
    )


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Async test client for FastAPI application."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
