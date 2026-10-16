"""Opt-in PostgreSQL tests. Run through scripts/verify_postgres.py, never on app data."""

import asyncio
import os
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.integrations.gemini.embeddings import MockEmbeddingProvider
from app.integrations.gemini.llm import MockLLMProvider
from app.integrations.servicenow.mock import MockTicketingProvider
from app.models.conversation import Conversation, IncidentAttempt, Message
from app.models.knowledge import AuditLog, KnowledgeChunk, KnowledgeDocument
from app.models.ticket import TicketCreateRequest
from app.repositories.knowledge_repository import KnowledgeRepository
from app.services.incident_service import IncidentService
from app.services.rag_service import RAGService

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_POSTGRES_URL"),
    reason="Run scripts/verify_postgres.py for disposable PostgreSQL verification",
)


@pytest.fixture
async def pg_sessions():
    url = os.environ["TEST_POSTGRES_URL"]
    assert make_url(url).database.startswith(
        "service_desk_test_"
    ), "Refusing non-test database"
    engine = create_async_engine(url)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "TRUNCATE messages, conversations, incident_attempts, audit_logs, knowledge_chunks, knowledge_documents RESTART IDENTITY CASCADE"
            )
        )
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def test_pgvector_installed_and_migrations_at_head(pg_sessions):
    async with pg_sessions() as session:
        assert (
            await session.execute(
                text("SELECT extversion FROM pg_extension WHERE extname='vector'")
            )
        ).scalar()
        assert (
            await session.execute(text("SELECT version_num FROM alembic_version"))
        ).scalar_one() == "002_conversations"


async def test_real_vector_ranking_category_and_embedding_profile(pg_sessions):
    query = [1.0] + [0.0] * 767
    orthogonal = [0.0, 1.0] + [0.0] * 766
    async with pg_sessions() as session:
        repo = KnowledgeRepository(session)
        for source, category, profile, vector in [
            ("KB-MATCH", "Network", "profile-a", query),
            ("KB-OTHER", "Network", "profile-a", orthogonal),
            ("KB-WRONG-PROFILE", "Network", "profile-b", query),
            ("KB-WRONG-CATEGORY", "Identity", "profile-a", query),
            ("KB-LEGACY", "Network", None, query),
        ]:
            doc = await repo.upsert_document(
                source,
                source,
                category,
                "synthetic",
                {"embedding_profile": profile} if profile else {},
            )
            await repo.save_chunks(
                [
                    KnowledgeChunk(
                        document_id=doc.id,
                        chunk_index=0,
                        content="synthetic",
                        embedding=vector,
                    )
                ]
            )
        await session.commit()
        result = await repo.search_similar_chunks(
            query, limit=10, category="Network", embedding_profile="profile-a"
        )
        assert [c.source_id for c in result] == ["KB-MATCH", "KB-OTHER"]
        assert result[0].similarity == 1.0
        assert result[1].similarity == 0.0
        limited = await repo.search_similar_chunks(
            query, limit=1, category="Network", embedding_profile="profile-a"
        )
        assert [c.source_id for c in limited] == ["KB-MATCH"]


async def test_ingestion_replacement_and_rollback_preserve_previous_chunks(
    pg_sessions, tmp_path
):
    kb = tmp_path / "test.md"
    kb.write_text(
        "# Synthetic KB\n\n## Metadata\n- Source Identifier: KB-TEST\n\n## Resolution Steps\nOriginal steps.\n"
    )
    async with pg_sessions() as session:
        service = RAGService(session, MockEmbeddingProvider(), MockLLMProvider())
        first = await service.ingest_directory(tmp_path)
        assert first.documents_ingested == 1
        before = (await session.scalars(select(KnowledgeChunk.content))).all()
        kb.write_text(kb.read_text().replace("Original steps", "Replacement steps"))
        service.embedding_provider.embed_batch = AsyncMock(
            side_effect=RuntimeError("embedding unavailable")
        )
        with pytest.raises(RuntimeError):
            await service.ingest_directory(tmp_path)
        await session.rollback()
        assert (await session.scalars(select(KnowledgeChunk.content))).all() == before
    async with pg_sessions() as session:
        service = RAGService(session, MockEmbeddingProvider(), MockLLMProvider())
        await service.ingest_directory(tmp_path)
        await service.ingest_directory(tmp_path)
        assert (
            await session.scalar(select(func.count()).select_from(KnowledgeDocument))
        ) == 1
        contents = (await session.scalars(select(KnowledgeChunk.content))).all()
        assert len(contents) == len(before)
        assert any("Replacement steps" in c for c in contents)
        assert not any("Original steps" in c for c in contents)


async def test_batch_cardinality_failure_does_not_replace_old_knowledge(
    pg_sessions, tmp_path
):
    (tmp_path / "kb.md").write_text(
        "# Synthetic KB\n\n## Resolution Steps\nUse SSPR.\n"
    )
    async with pg_sessions() as session:
        service = RAGService(session, MockEmbeddingProvider(), MockLLMProvider())
        await service.ingest_directory(tmp_path)
        count = await session.scalar(select(func.count()).select_from(KnowledgeChunk))
        service.embedding_provider.embed_batch = AsyncMock(return_value=[])
        with pytest.raises(ValueError, match="batch size"):
            await service.ingest_directory(tmp_path)
        await session.rollback()
        assert (
            await session.scalar(select(func.count()).select_from(KnowledgeChunk))
            == count
        )


async def test_postgres_burst_acceptance_dispatches_once(pg_sessions):
    provider = MockTicketingProvider()
    real_create = provider.create_incident

    async def delayed(request):
        await asyncio.sleep(0.1)
        return await real_create(request)

    provider.create_incident = AsyncMock(side_effect=delayed)
    request = TicketCreateRequest(
        short_description="Synthetic VPN failure", correlation_id="pg-concurrency"
    )

    async def accept():
        async with pg_sessions() as session:
            return await IncidentService(session, provider).create_or_reconcile(request)

    outcomes = await asyncio.gather(*(accept() for _ in range(16)))
    assert provider.create_incident.await_count == 1
    assert any(status == "created" for status, _ in outcomes)
    async with pg_sessions() as session:
        status, ticket = await IncidentService(session, provider).reconcile(
            "pg-concurrency"
        )
        assert status == "created"
        assert len(await provider.query_incidents()) == 1
        assert (
            await session.scalar(select(func.count()).select_from(IncidentAttempt))
        ) == 1
        audit = (await session.scalars(select(AuditLog))).all()
        assert len([e for e in audit if e.event_type == "escalation_accepted"]) == 1
        assert ticket.number


async def test_postgres_pending_survives_process_session_loss(pg_sessions):
    provider = MockTicketingProvider()
    request = TicketCreateRequest(
        short_description="Synthetic timeout", correlation_id="pg-timeout"
    )
    async with pg_sessions() as session:
        service = IncidentService(session, provider)
        await service.repository.prepare_attempt(
            request.correlation_id, request.model_dump(mode="json")
        )
        assert await service.repository.claim_attempt(request.correlation_id)
        await session.commit()
    # Simulate ServiceNow committing, followed by worker death before result save.
    created = await provider.create_incident(request)
    provider.create_incident = AsyncMock(
        side_effect=AssertionError("Must never redispatch")
    )
    async with pg_sessions() as session:
        status, recovered = await IncidentService(
            session, provider
        ).create_or_reconcile(request)
        assert status == "created"
        assert recovered.sys_id == created.sys_id
        provider.create_incident.assert_not_awaited()


async def test_postgres_reopens_conversation_and_audit_in_new_session(pg_sessions):
    async with pg_sessions() as session:
        session.add(Conversation(id="a" * 32, issue="Synthetic VPN issue"))
        await session.flush()
        session.add(
            Message(conversation_id="a" * 32, role="user", content="VPN failed")
        )
        session.add(
            AuditLog(
                session_id="a" * 32,
                event_type="request_received",
                payload={"message": "VPN failed"},
            )
        )
        await session.commit()
    async with pg_sessions() as session:
        assert (
            await session.get(Conversation, "a" * 32)
        ).issue == "Synthetic VPN issue"
        assert (await session.scalars(select(Message))).one().content == "VPN failed"
        assert (await session.scalars(select(AuditLog))).one().session_id == "a" * 32
