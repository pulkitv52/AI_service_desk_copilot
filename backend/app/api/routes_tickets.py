from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.logging import get_logger
from app.integrations.servicenow import (
    TicketingProvider,
    get_ticketing_provider,
    ServiceNowError,
)
from app.models.ticket import (
    TicketCreateRequest,
    TicketUpdateRequest,
    TicketResponse,
)

logger = get_logger("routes_tickets")
router = APIRouter(prefix="/api/tickets", tags=["Tickets"])


@router.post(
    "",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new ticket/incident",
)
async def create_ticket(
    ticket: TicketCreateRequest,
    provider: TicketingProvider = Depends(get_ticketing_provider),
) -> TicketResponse:
    """Create a new incident ticket in the configured ITSM provider."""
    try:
        return await provider.create_incident(ticket)
    except ServiceNowError as exc:
        raise HTTPException(
            status_code=exc.status_code or status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error creating ticket: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create ticket due to internal server error",
        ) from exc


@router.get(
    "/{ticket_id}",
    response_model=TicketResponse,
    summary="Get incident details by sys_id or ticket number",
)
async def get_ticket(
    ticket_id: str,
    provider: TicketingProvider = Depends(get_ticketing_provider),
) -> TicketResponse:
    """Retrieve ticket details by sys_id or incident number."""
    try:
        ticket = await provider.get_incident(ticket_id)
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticket '{ticket_id}' not found",
            )
        return ticket
    except HTTPException:
        raise
    except ServiceNowError as exc:
        raise HTTPException(
            status_code=exc.status_code or status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error fetching ticket %s: %s", ticket_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve ticket",
        ) from exc


@router.patch(
    "/{ticket_id}",
    response_model=TicketResponse,
    summary="Update an existing incident ticket",
)
async def update_ticket(
    ticket_id: str,
    update: TicketUpdateRequest,
    provider: TicketingProvider = Depends(get_ticketing_provider),
) -> TicketResponse:
    """Update fields on an existing incident."""
    try:
        updated = await provider.update_incident(ticket_id, update)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticket '{ticket_id}' not found for update",
            )
        return updated
    except HTTPException:
        raise
    except ServiceNowError as exc:
        raise HTTPException(
            status_code=exc.status_code or status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error updating ticket %s: %s", ticket_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update ticket",
        ) from exc


@router.get(
    "",
    response_model=list[TicketResponse],
    summary="Query incident tickets",
)
async def list_tickets(
    query: Optional[str] = Query(default="", description="Search query or filter"),
    limit: int = Query(
        default=10, ge=1, le=100, description="Maximum number of tickets to return"
    ),
    provider: TicketingProvider = Depends(get_ticketing_provider),
) -> list[TicketResponse]:
    """Query incident tickets."""
    try:
        return await provider.query_incidents(query=query or "", limit=limit)
    except ServiceNowError as exc:
        raise HTTPException(
            status_code=exc.status_code or status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error querying tickets: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to query tickets",
        ) from exc
