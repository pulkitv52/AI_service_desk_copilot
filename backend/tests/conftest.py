from typing import AsyncGenerator
from pathlib import Path

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.core.database import get_db_session
from app.integrations.servicenow import reset_ticketing_provider
from app.main import app
from app.models.conversation import Conversation, IncidentAttempt, Message
from app.models.knowledge import AuditLog, KnowledgeSearchResult


@pytest.fixture(autouse=True)
def isolate_integrations(monkeypatch):
    from app.integrations.gemini import reset_embedding_provider, reset_llm_provider

    settings = Settings(
        _env_file=None,
        environment="test",
        gemini_api_key=None,
        servicenow_instance_url=None,
        servicenow_username=None,
        servicenow_password=None,
        use_mock_servicenow=True,
        database_url="sqlite+aiosqlite:///:memory:",
    )
    for module in (
        "app.core.config",
        "app.integrations.gemini",
        "app.integrations.servicenow",
    ):
        monkeypatch.setattr(module + ".get_settings", lambda: settings)
    app.dependency_overrides[
        __import__("app.core.config", fromlist=["get_settings"]).get_settings
    ] = lambda: settings
    # FastAPI captured the original dependency before the monkeypatch.
    from app.api import routes_health

    app.dependency_overrides[routes_health.get_settings] = lambda: settings
    original_send = httpx.AsyncClient.send

    async def isolated_send(client, *args, **kwargs):
        if not isinstance(client._transport, (httpx.MockTransport, ASGITransport)):
            raise AssertionError("Tests must use an ASGI or mock HTTP transport")
        return await original_send(client, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "send", isolated_send)
    reset_ticketing_provider()
    reset_llm_provider()
    reset_embedding_provider()
    yield
    app.dependency_overrides.clear()
    reset_ticketing_provider()
    reset_llm_provider()
    reset_embedding_provider()


@pytest.fixture
async def database(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    tables = [
        Conversation.__table__,
        Message.__table__,
        IncidentAttempt.__table__,
        AuditLog.__table__,
    ]
    async with engine.begin() as connection:
        await connection.run_sync(
            lambda sync: Conversation.metadata.create_all(sync, tables=tables)
        )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest.fixture
async def async_client(database, monkeypatch) -> AsyncGenerator[AsyncClient, None]:
    async def db_session():
        async with database() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db_session] = db_session

    # HTTP workflow tests use fixture retrieval; repository retrieval has separate
    # tests. No ingestion, live database, or provider credentials are required.
    async def fixture_search(self, query, limit=5, category=None):
        name = (
            "password-reset.md"
            if "password" in query.lower()
            else (
                "software-installation.md"
                if "install" in query.lower()
                else "vpn-troubleshooting.md"
            )
        )
        content = (
            Path(__file__).resolve().parents[2] / "knowledge-base" / name
        ).read_text()
        parsed = self.parse_markdown_document(content, name)
        return [
            KnowledgeSearchResult(
                chunk_id="fixture-chunk",
                document_id="fixture-doc",
                source_id=parsed["source_id"],
                title=parsed["title"],
                category=parsed["category"],
                content=content,
                similarity=0.9,
            )
        ]

    monkeypatch.setattr("app.services.rag_service.RAGService.search", fixture_search)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
