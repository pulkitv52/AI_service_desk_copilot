import uuid
from datetime import datetime, timezone
from typing import Optional
from app.core.logging import get_logger
from app.models.ticket import (
    TicketCreateRequest,
    TicketUpdateRequest,
    TicketResponse,
    TicketState,
)

logger = get_logger("mock_ticketing_provider")


class MockTicketingProvider:
    """In-memory mock ticketing provider for testing and offline development."""

    def __init__(self) -> None:
        self._tickets: dict[str, TicketResponse] = {}
        self._next_inc_num: int = 10001

    async def create_incident(self, ticket: TicketCreateRequest) -> TicketResponse:
        """Create a mock incident."""
        sys_id = uuid.uuid4().hex
        number = f"INC{self._next_inc_num}"
        self._next_inc_num += 1

        now_str = datetime.now(timezone.utc).isoformat()
        response = TicketResponse(
            sys_id=sys_id,
            number=number,
            short_description=ticket.short_description,
            description=ticket.description,
            state=TicketState.NEW.value,
            urgency=ticket.urgency.value,
            impact=ticket.impact.value,
            priority="P3",
            category=ticket.category,
            subcategory=ticket.subcategory,
            assignment_group=ticket.assignment_group,
            caller_id=ticket.caller_id,
            provider="mock",
            created_at=now_str,
            updated_at=now_str,
        )
        self._tickets[sys_id] = response
        logger.info(
            "Created mock incident number=%s sys_id=%s short_description=%s",
            number,
            sys_id,
            ticket.short_description,
        )
        return response

    async def get_incident(self, sys_id: str) -> Optional[TicketResponse]:
        """Retrieve a mock incident by sys_id or ticket number."""
        if sys_id in self._tickets:
            return self._tickets[sys_id]

        for ticket in self._tickets.values():
            if ticket.number.lower() == sys_id.lower():
                return ticket
        return None

    async def update_incident(
        self, sys_id: str, update: TicketUpdateRequest
    ) -> Optional[TicketResponse]:
        """Update fields on an existing mock incident."""
        existing = await self.get_incident(sys_id)
        if not existing:
            return None

        update_data = existing.model_dump()
        if update.state is not None:
            update_data["state"] = update.state.value
        if update.urgency is not None:
            update_data["urgency"] = update.urgency.value
        if update.impact is not None:
            update_data["impact"] = update.impact.value
        if update.assignment_group is not None:
            update_data["assignment_group"] = update.assignment_group

        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        updated_ticket = TicketResponse(**update_data)
        self._tickets[existing.sys_id] = updated_ticket
        logger.info("Updated mock incident sys_id=%s", existing.sys_id)
        return updated_ticket

    async def query_incidents(
        self, query: str = "", limit: int = 10
    ) -> list[TicketResponse]:
        """Query mock tickets."""
        results: list[TicketResponse] = []
        for ticket in self._tickets.values():
            if query:
                if (
                    query.lower() in ticket.short_description.lower()
                    or query.lower() in (ticket.description or "").lower()
                    or query.lower() in ticket.number.lower()
                ):
                    results.append(ticket)
            else:
                results.append(ticket)
            if len(results) >= limit:
                break
        return results
