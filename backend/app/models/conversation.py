import uuid
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text

from app.core.database import Base
from app.models.knowledge import get_utc_now
from app.models.ticket import TicketResponse


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    issue = Column(Text, nullable=False, default="")
    classification = Column(JSON, nullable=True)
    escalation_offered = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=get_utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=get_utc_now)


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(
        String(36), ForeignKey("conversations.id"), nullable=False, index=True
    )
    role = Column(String(16), nullable=False)
    content = Column(Text, nullable=False)
    response = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=get_utc_now)


class IncidentAttempt(Base):
    __tablename__ = "incident_attempts"

    # Also the provider correlation ID. One durable creation state per issue.
    id = Column(String(128), primary_key=True)
    status = Column(String(24), nullable=False, default="ready")
    request = Column(JSON, nullable=False)
    ticket = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=get_utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=get_utc_now)


class ConversationSummary(BaseModel):
    id: str
    issue: str
    updated_at: str


class SavedMessage(BaseModel):
    id: int
    role: str
    content: str
    created_at: str
    response: dict[str, Any] | None = None


class ConversationDetail(ConversationSummary):
    incident_status: str | None = None
    ticket: TicketResponse | None = None
    messages: list[SavedMessage] = Field(default_factory=list)


class AuditEvent(BaseModel):
    id: str
    event_type: str
    payload: dict[str, Any]
    created_at: str
