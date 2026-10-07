from unittest.mock import AsyncMock
import pytest
from app.integrations.gemini.embeddings import MockEmbeddingProvider
from app.integrations.gemini.llm import MockLLMProvider
from app.models.knowledge import KnowledgeSearchResult
from app.services.rag_service import RAGService


@pytest.mark.asyncio
async def test_rag_service_search_integration() -> None:
    mock_session = AsyncMock()
    embedding_provider = MockEmbeddingProvider()

    service = RAGService(session=mock_session, embedding_provider=embedding_provider)

    expected_results = [
        KnowledgeSearchResult(
            chunk_id="chunk-1",
            document_id="doc-1",
            source_id="KB-SEC-001",
            title="Self-Service Password Reset Guide",
            category="Identity and Access Management",
            content="Navigate to the corporate SSPR portal to reset your password.",
            similarity=0.92,
        )
    ]
    service.repository.search_similar_chunks = AsyncMock(return_value=expected_results)

    results = await service.search("How do I reset my password?", limit=3)

    assert len(results) == 1
    assert results[0].source_id == "KB-SEC-001"
    assert results[0].similarity == 0.92
    service.repository.search_similar_chunks.assert_called_once()


@pytest.mark.asyncio
async def test_rag_service_grounded_answer_success() -> None:
    mock_session = AsyncMock()
    service = RAGService(
        session=mock_session,
        embedding_provider=MockEmbeddingProvider(),
        llm_provider=MockLLMProvider(),
    )

    expected_results = [
        KnowledgeSearchResult(
            chunk_id="chunk-1",
            document_id="doc-1",
            source_id="KB-SEC-001",
            title="Self-Service Password Reset Guide",
            category="Identity and Access Management",
            content="Step 1: Go to SSPR portal at passwordreset.corp.internal",
            similarity=0.88,
        )
    ]
    service.repository.search_similar_chunks = AsyncMock(return_value=expected_results)

    answer = await service.generate_grounded_answer(
        query="How do I reset my password?",
        similarity_threshold=0.60,
    )

    assert answer.should_escalate is False
    assert answer.confidence == 0.88
    assert len(answer.sources) == 1
    assert "KB-SEC-001" in answer.sources[0]
    assert "password" in answer.answer.lower()


@pytest.mark.asyncio
async def test_rag_service_grounded_answer_fallback_low_confidence() -> None:
    mock_session = AsyncMock()
    service = RAGService(
        session=mock_session,
        embedding_provider=MockEmbeddingProvider(),
        llm_provider=MockLLMProvider(),
    )

    low_similarity_results = [
        KnowledgeSearchResult(
            chunk_id="chunk-9",
            document_id="doc-9",
            source_id="KB-MISC-999",
            title="Irrelevant Topic",
            category="Miscellaneous",
            content="Unrelated information",
            similarity=0.42,
        )
    ]
    service.repository.search_similar_chunks = AsyncMock(
        return_value=low_similarity_results
    )

    answer = await service.generate_grounded_answer(
        query="Obscure proprietary mainframe error 9999",
        similarity_threshold=0.60,
    )

    assert answer.should_escalate is True
    assert answer.confidence == 0.42
    assert "open an it support incident" in answer.answer.lower()
