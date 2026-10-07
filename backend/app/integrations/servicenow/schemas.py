from typing import Any, Optional
from pydantic import BaseModel, Field


class ServiceNowIncidentPayload(BaseModel):
    """Raw payload structure sent to ServiceNow Table API incident endpoint."""

    short_description: str
    description: Optional[str] = None
    urgency: str = "3"
    impact: str = "3"
    category: Optional[str] = None
    subcategory: Optional[str] = None
    assignment_group: Optional[str] = None
    caller_id: Optional[str] = None
    correlation_id: Optional[str] = None
    comments: Optional[str] = None
    work_notes: Optional[str] = None


class ServiceNowIncidentResult(BaseModel):
    """Result object returned by ServiceNow Table API."""

    sys_id: str
    number: str
    short_description: Optional[str] = None
    description: Optional[str] = None
    state: Optional[str] = None
    urgency: Optional[str] = None
    impact: Optional[str] = None
    priority: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    assignment_group: Any = None
    caller_id: Any = None
    sys_created_on: Optional[str] = None
    sys_updated_on: Optional[str] = None


class ServiceNowApiResponse(BaseModel):
    """Standard ServiceNow REST API response wrapper."""

    result: Optional[Any] = None
    error: Optional[dict[str, Any]] = None
