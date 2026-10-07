from typing import Any, Optional
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.knowledge import (
    KnowledgeDocument,
    KnowledgeChunk,
    KnowledgeSearchResult,
    get_utc_now,
)

logger = get_logger("knowledge_repository")


class KnowledgeRepository:
    """Data access layer for knowledge documents and pgvector chunks."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_document_by_source_id(
        self, source_id: str
    ) -> Optional[KnowledgeDocument]:
        """Lookup document by source_id identifier."""
        stmt = select(KnowledgeDocument).where(KnowledgeDocument.source_id == source_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def upsert_document(
        self,
        source_id: str,
        title: str,
        category: str,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> KnowledgeDocument:
        """Create or update a knowledge document record."""
        existing = await self.get_document_by_source_id(source_id)
        if existing:
            existing.title = title
            existing.category = category
            existing.content = content
            existing.doc_metadata = metadata or {}
            existing.updated_at = get_utc_now()
            await self.session.flush()
            return existing

        doc = KnowledgeDocument(
            source_id=source_id,
            title=title,
            category=category,
            content=content,
            doc_metadata=metadata or {},
        )
        self.session.add(doc)
        await self.session.flush()
        return doc

    async def delete_chunks_for_document(self, document_id: str) -> None:
        """Remove all existing chunks associated with a document."""
        stmt = delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document_id)
        await self.session.execute(stmt)
        await self.session.flush()

    async def save_chunks(self, chunks: list[KnowledgeChunk]) -> None:
        """Persist a list of knowledge chunk records."""
        self.session.add_all(chunks)
        await self.session.flush()

    async def search_similar_chunks(
        self,
        query_vector: list[float],
        limit: int = 5,
        category: Optional[str] = None,
    ) -> list[KnowledgeSearchResult]:
        """Retrieve most similar chunks using pgvector cosine distance."""
        distance_col = KnowledgeChunk.embedding.cosine_distance(query_vector)

        stmt = (
            select(
                KnowledgeChunk,
                KnowledgeDocument,
                distance_col.label("distance"),
            )
            .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
            .order_by(distance_col.asc())
            .limit(limit)
        )

        if category:
            stmt = stmt.where(KnowledgeDocument.category == category)

        rows = await self.session.execute(stmt)
        results: list[KnowledgeSearchResult] = []

        for chunk, doc, distance in rows:
            dist_val = float(distance) if distance is not None else 1.0
            similarity = max(0.0, min(1.0, 1.0 - dist_val))
            results.append(
                KnowledgeSearchResult(
                    chunk_id=chunk.id,
                    document_id=doc.id,
                    source_id=doc.source_id,
                    title=doc.title,
                    category=doc.category,
                    content=chunk.content,
                    similarity=round(similarity, 4),
                )
            )

        return results
