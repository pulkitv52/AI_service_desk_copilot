import os
import re
from pathlib import Path
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.integrations.gemini import (
    EmbeddingProvider,
    get_embedding_provider,
    LLMProvider,
    get_llm_provider,
)
from app.models.knowledge import (
    GroundedAnswer,
    KnowledgeChunk,
    KnowledgeIngestResponse,
    KnowledgeSearchResult,
)
from app.repositories.knowledge_repository import KnowledgeRepository

logger = get_logger("rag_service")


class RAGService:
    """Orchestrates document parsing, chunking, embedding generation, and vector retrieval."""

    def __init__(
        self,
        session: AsyncSession,
        embedding_provider: Optional[EmbeddingProvider] = None,
        llm_provider: Optional[LLMProvider] = None,
    ) -> None:
        self.session = session
        self.repository = KnowledgeRepository(session)
        self.embedding_provider = embedding_provider or get_embedding_provider()
        self.llm_provider = llm_provider or get_llm_provider()

    @staticmethod
    def parse_markdown_document(content: str, filename: str) -> dict[str, Any]:
        """Extract title, metadata, and sections from IT support markdown document."""
        lines = content.splitlines()
        title = Path(filename).stem.replace("-", " ").title()
        source_id = f"KB-{Path(filename).stem.upper()}"
        category = "General IT"
        metadata: dict[str, Any] = {"filename": filename}

        # Parse H1 title
        for line in lines:
            if line.startswith("# "):
                title = line[2:].strip()
                break

        # Parse Metadata section if present
        meta_match = re.search(r"## Metadata\s*\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
        if meta_match:
            for m_line in meta_match.group(1).splitlines():
                if ":" in m_line:
                    k, v = m_line.lstrip("- *").split(":", 1)
                    k_clean = k.strip().lower().replace(" ", "_")
                    v_clean = v.strip()
                    metadata[k_clean] = v_clean
                    if k_clean == "source_identifier":
                        source_id = v_clean
                    elif k_clean == "category":
                        category = v_clean

        # Chunk by H2 headings
        sections: list[tuple[str, str]] = []
        current_heading = "Overview"
        current_lines: list[str] = []

        for line in lines:
            if line.startswith("## "):
                if current_lines:
                    text_block = "\n".join(current_lines).strip()
                    if text_block and current_heading.lower() != "metadata":
                        sections.append((current_heading, text_block))
                    current_lines = []
                current_heading = line[3:].strip()
            else:
                current_lines.append(line)

        if current_lines:
            text_block = "\n".join(current_lines).strip()
            if text_block and current_heading.lower() != "metadata":
                sections.append((current_heading, text_block))

        return {
            "title": title,
            "source_id": source_id,
            "category": category,
            "metadata": metadata,
            "sections": sections,
        }

    async def ingest_directory(
        self, directory_path: str | Path
    ) -> KnowledgeIngestResponse:
        """Ingest all markdown files from a knowledge base directory."""
        dir_path = Path(directory_path)
        if not dir_path.exists():
            raise FileNotFoundError(f"Knowledge directory not found: {directory_path}")

        md_files = list(dir_path.glob("*.md"))
        logger.info(
            "Found %d markdown files to ingest from %s", len(md_files), dir_path
        )

        total_chunks = 0
        documents_ingested = 0

        for file_path in md_files:
            content = file_path.read_text(encoding="utf-8")
            parsed = self.parse_markdown_document(content, file_path.name)

            doc = await self.repository.upsert_document(
                source_id=parsed["source_id"],
                title=parsed["title"],
                category=parsed["category"],
                content=content,
                metadata=parsed["metadata"],
            )

            # Clear old chunks for document
            await self.repository.delete_chunks_for_document(doc.id)

            # Prepare text blocks with title context
            chunks_to_create: list[KnowledgeChunk] = []
            texts_to_embed: list[str] = []

            for idx, (heading, sec_text) in enumerate(parsed["sections"]):
                chunk_text = (
                    f"Title: {parsed['title']}\nSection: {heading}\n\n{sec_text}"
                )
                texts_to_embed.append(chunk_text)
                chunk = KnowledgeChunk(
                    document_id=doc.id,
                    chunk_index=idx,
                    content=chunk_text,
                    chunk_metadata={
                        "heading": heading,
                        "source_id": parsed["source_id"],
                        "category": parsed["category"],
                    },
                )
                chunks_to_create.append(chunk)

            if texts_to_embed:
                embeddings = await self.embedding_provider.embed_batch(texts_to_embed)
                for chunk_obj, emb in zip(chunks_to_create, embeddings):
                    chunk_obj.embedding = emb

                await self.repository.save_chunks(chunks_to_create)
                total_chunks += len(chunks_to_create)

            documents_ingested += 1

        await self.session.commit()
        logger.info(
            "Ingestion complete: %d documents, %d chunks",
            documents_ingested,
            total_chunks,
        )
        return KnowledgeIngestResponse(
            documents_ingested=documents_ingested,
            chunks_created=total_chunks,
            message="Knowledge base ingested successfully",
        )

    async def search(
        self, query: str, limit: int = 5, category: Optional[str] = None
    ) -> list[KnowledgeSearchResult]:
        """Perform semantic vector search against stored knowledge chunks."""
        query_vector = await self.embedding_provider.embed_text(query)
        return await self.repository.search_similar_chunks(
            query_vector=query_vector,
            limit=limit,
            category=category,
        )

    async def generate_grounded_answer(
        self,
        query: str,
        similarity_threshold: Optional[float] = None,
        category: Optional[str] = None,
    ) -> GroundedAnswer:
        """Synthesize answer grounded in retrieved knowledge base context."""
        from app.integrations.gemini.embeddings import MockEmbeddingProvider

        if similarity_threshold is None:
            if isinstance(self.embedding_provider, MockEmbeddingProvider):
                threshold = 0.05
            else:
                threshold = 0.60
        else:
            threshold = similarity_threshold

        chunks = await self.search(query=query, limit=4, category=category)

        # Fallback if no chunks match or confidence is below threshold
        if not chunks or chunks[0].similarity < threshold:
            return GroundedAnswer(
                query=query,
                answer=(
                    "I could not locate an authoritative knowledge base article "
                    "matching your request. Would you like me to open an IT "
                    "support incident for this issue?"
                ),
                confidence=chunks[0].similarity if chunks else 0.0,
                sources=[],
                should_escalate=True,
                matched_chunks=chunks,
            )

        context_blocks = []
        sources = set()
        for c in chunks:
            sources.add(f"{c.source_id} - {c.title}")
            context_blocks.append(f"[{c.source_id}] ({c.category}):\n{c.content}")

        context_text = "\n\n---\n\n".join(context_blocks)
        system_instruction = (
            "You are an enterprise AI IT Service Desk Assistant. "
            "Answer the user request strictly using the provided knowledge base context. "
            "Provide direct, actionable resolution steps. "
            "Always include source citations in the format [KB-XXX-YYY]. "
            "If the context does not answer the question, state that escalation is required."
        )
        prompt = (
            f"Knowledge Base Context:\n{context_text}\n\n"
            f"Employee Request:\n{query}\n\n"
            f"Grounded Response:"
        )

        try:
            answer_text = await self.llm_provider.generate(
                prompt=prompt, system_instruction=system_instruction
            )
        except Exception as exc:
            logger.warning("LLM generation failed, falling back to top grounded chunk: %s", exc)
            top_chunk = chunks[0]
            answer_text = (
                f"Based on enterprise documentation ({top_chunk.source_id} - {top_chunk.title}):\n\n"
                f"{top_chunk.content}\n\n"
                f"Sources: [{top_chunk.source_id}]"
            )

        return GroundedAnswer(
            query=query,
            answer=answer_text,
            confidence=chunks[0].similarity,
            sources=sorted(list(sources)),
            should_escalate=False,
            matched_chunks=chunks,
        )
