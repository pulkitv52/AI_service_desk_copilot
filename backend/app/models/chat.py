from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

from app.models.ticket import TicketResponse, TicketUrgency, TicketImpact


class SupportIntent(str, Enum):
    KNOWLEDGE_INQUIRY = "knowledge_inquiry"
    SOFTWARE_REQUEST = "software_request"
    APPLICATION_ISSUE = "application_issue"
    DIAGNOSTIC_REMEDIATION = "diagnostic_remediation"
    GENERAL_INCIDENT = "general_incident"


class TicketPriority(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"
    P5 = "P5"


class IntentClassification(BaseModel):
    """Structured representation of classified support request."""

    intent: SupportIntent
    category: str
    subcategory: Optional[str] = None
    application: Optional[str] = None
    urgency: TicketUrgency = TicketUrgency.LOW
    impact: TicketImpact = TicketImpact.LOW
    priority: TicketPriority = TicketPriority.P5
    assignment_group: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: Optional[str] = None


class ChatRequest(BaseModel):
    """User incoming chat message payload."""

    message: str = Field(..., min_length=2, max_length=2000)
    session_id: Optional[str] = Field(default=None, pattern=r"^[a-f0-9]{32}$")
    user_id: Optional[str] = None
    force_ticket: bool = False


class ChatResponseType(str, Enum):
    DEFLECTED_RAG = "deflected_rag"
    TICKET_CREATED = "ticket_created"
    SERVICE_REQUEST = "service_request"
    DIAGNOSTIC_ACTION = "diagnostic_action"
    ESCALATION_OFFERED = "escalation_offered"
    CONVERSATIONAL = "conversational"
    PENDING_VERIFICATION = "pending_verification"
    TICKET_FAILED = "ticket_failed"


class ChatResponse(BaseModel):
    """Unified conversational orchestrator response."""

    session_id: str
    response_type: ChatResponseType
    message: str
    classification: IntentClassification
    ticket: Optional[TicketResponse] = None
    sources: list[str] = Field(default_factory=list)
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
