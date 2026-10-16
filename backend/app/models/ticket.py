from datetime import datetime, timezone
from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, Field


class TicketUrgency(str, Enum):
    HIGH = "1"
    MEDIUM = "2"
    LOW = "3"


class TicketImpact(str, Enum):
    HIGH = "1"
    MEDIUM = "2"
    LOW = "3"


class TicketState(str, Enum):
    NEW = "1"
    IN_PROGRESS = "2"
    ON_HOLD = "3"
    RESOLVED = "6"
    CLOSED = "7"
    CANCELED = "8"


class TicketCreateRequest(BaseModel):
    """Schema for requesting a new ticket/incident creation."""

    short_description: str = Field(..., min_length=3, max_length=160)
    description: Optional[str] = Field(default=None, max_length=4000)
    urgency: TicketUrgency = TicketUrgency.LOW
    impact: TicketImpact = TicketImpact.LOW
    category: Optional[str] = Field(default="inquiry")
    subcategory: Optional[str] = None
    assignment_group: Optional[str] = None
    caller_id: Optional[str] = None
    correlation_id: Optional[str] = Field(
        default=None, pattern=r"^[a-zA-Z0-9_-]{1,128}$"
    )


class TicketUpdateRequest(BaseModel):
    """Schema for updating an existing ticket/incident."""

    comments: Optional[str] = None
    work_notes: Optional[str] = None
    state: Optional[TicketState] = None
    urgency: Optional[TicketUrgency] = None
    impact: Optional[TicketImpact] = None
    assignment_group: Optional[str] = None


class TicketResponse(BaseModel):
    """Standardized representation of a ticket."""

    sys_id: str
    number: str
    short_description: str
    description: Optional[str] = None
    state: str = TicketState.NEW.value
    urgency: str = TicketUrgency.LOW.value
    impact: str = TicketImpact.LOW.value
    priority: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    assignment_group: Optional[str] = None
    caller_id: Optional[str] = None
    provider: str = "mock"
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: Optional[str] = None


class IncidentStatusResponse(BaseModel):
    status: Literal["ready", "pending", "failed", "created"]
    ticket: TicketResponse | None = None
