import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from pgvector.sqlalchemy import Vector
from pydantic import BaseModel, Field
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import relationship

from app.core.database import Base

EMBEDDING_DIMENSION = 768


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class KnowledgeDocument(Base):
    """SQLAlchemy model for parent knowledge documents."""

    __tablename__ = "knowledge_documents"

    id = Column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    source_id = Column(String(64), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    content = Column(Text, nullable=False)
    doc_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    updated_at = Column(
        DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now
    )

    chunks = relationship(
        "KnowledgeChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="KnowledgeChunk.chunk_index",
    )


class KnowledgeChunk(Base):
    """SQLAlchemy model for chunked text embeddings."""

    __tablename__ = "knowledge_chunks"

    id = Column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    document_id = Column(
        String(36),
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(EMBEDDING_DIMENSION), nullable=True)
    chunk_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)

    document = relationship("KnowledgeDocument", back_populates="chunks")


class AuditLog(Base):
    """SQLAlchemy model for platform audit trail."""

    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    session_id = Column(String(128), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    payload = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)


# Pydantic Schemas
class KnowledgeSearchRequest(BaseModel):
    """Request payload for semantic knowledge search."""

    query: str = Field(..., min_length=2, max_length=500)
    limit: int = Field(default=5, ge=1, le=20)
    category: Optional[str] = None


class KnowledgeSearchResult(BaseModel):
    """Individual retrieved knowledge chunk with similarity score."""

    chunk_id: str
    document_id: str
    source_id: str
    title: str
    category: str
    content: str
    similarity: float


class KnowledgeIngestResponse(BaseModel):
    """Ingestion summary response."""

    documents_ingested: int
    chunks_created: int
    message: str


class GroundedAnswerRequest(BaseModel):
    """Request payload for RAG-grounded answer generation."""

    query: str = Field(..., min_length=2, max_length=1000)
    category: Optional[str] = None
    similarity_threshold: float = Field(default=0.60, ge=0.0, le=1.0)


class GroundedAnswer(BaseModel):
    """Synthesized answer grounded in retrieved knowledge base chunks."""

    query: str
    answer: str
    confidence: float
    sources: list[str] = Field(default_factory=list)
    should_escalate: bool = False
    matched_chunks: list[KnowledgeSearchResult] = Field(default_factory=list)
