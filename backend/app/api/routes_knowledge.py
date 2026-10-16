from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.logging import get_logger
from app.models.knowledge import (
    GroundedAnswer,
    GroundedAnswerRequest,
    KnowledgeIngestResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResult,
)
from app.services.rag_service import RAGService

logger = get_logger("routes_knowledge")
router = APIRouter(prefix="/api/knowledge", tags=["Knowledge"])


@router.post(
    "/ingest",
    response_model=KnowledgeIngestResponse,
    summary="Ingest knowledge base documents into pgvector",
)
async def ingest_knowledge(
    directory: Optional[str] = Query(
        default=None, description="Optional custom directory path to ingest"
    ),
    session: AsyncSession = Depends(get_db_session),
) -> KnowledgeIngestResponse:
    """Ingest markdown knowledge base documents and store embeddings."""
    try:
        service = RAGService(session)
        kb_path = (
            Path(directory)
            if directory
            else Path(__file__).resolve().parent.parent.parent.parent / "knowledge-base"
        )
        return await service.ingest_directory(kb_path)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from None
    except Exception as exc:
        logger.error("External workflow failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Knowledge ingestion failed",
        ) from None


@router.post(
    "/search",
    response_model=list[KnowledgeSearchResult],
    summary="Search knowledge base using semantic vector similarity",
)
async def search_knowledge(
    request: KnowledgeSearchRequest,
    session: AsyncSession = Depends(get_db_session),
) -> list[KnowledgeSearchResult]:
    """Search knowledge documents with vector embedding similarity."""
    try:
        service = RAGService(session)
        return await service.search(
            query=request.query,
            limit=request.limit,
            category=request.category,
        )
    except Exception as exc:
        logger.error("External workflow failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Knowledge search failed",
        ) from None


@router.post(
    "/answer",
    response_model=GroundedAnswer,
    summary="Generate grounded answer with RAG retrieval and citations",
)
async def answer_question(
    request: GroundedAnswerRequest,
    session: AsyncSession = Depends(get_db_session),
) -> GroundedAnswer:
    """Answer employee support question grounded in enterprise knowledge base."""
    try:
        service = RAGService(session)
        return await service.generate_grounded_answer(
            query=request.query,
            similarity_threshold=request.similarity_threshold,
            category=request.category,
        )
    except Exception as exc:
        logger.error("External workflow failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate answer",
        ) from None
