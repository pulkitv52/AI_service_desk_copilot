from typing import Optional, Protocol, runtime_checkable
from app.models.ticket import TicketCreateRequest, TicketUpdateRequest, TicketResponse


@runtime_checkable
class TicketingProvider(Protocol):
    """Protocol for external IT Service Management ticketing providers."""

    async def create_incident(self, ticket: TicketCreateRequest) -> TicketResponse:
        """Create a new incident ticket."""
        ...

    async def get_incident(self, sys_id: str) -> Optional[TicketResponse]:
        """Fetch an incident by sys_id or ticket number."""
        ...

    async def update_incident(
        self, sys_id: str, update: TicketUpdateRequest
    ) -> Optional[TicketResponse]:
        """Update an existing incident ticket."""
        ...

    async def query_incidents(
        self, query: str = "", limit: int = 10
    ) -> list[TicketResponse]:
        """Query incidents using provider query syntax or filter."""
        ...
