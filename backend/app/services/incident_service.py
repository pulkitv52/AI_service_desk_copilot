from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.integrations.servicenow import ServiceNowError, TicketingProvider
from app.models.ticket import TicketCreateRequest, TicketResponse
from app.repositories.conversation_repository import ConversationRepository

logger = get_logger("incident_service")


class IncidentService:
    """Durable dispatch: uncertain outcomes are reconciled, never blindly retried."""

    def __init__(self, session: AsyncSession, provider: TicketingProvider) -> None:
        self.session = session
        self.provider = provider
        self.repository = ConversationRepository(session)

    async def create_or_reconcile(
        self, request: TicketCreateRequest
    ) -> tuple[str, TicketResponse | None]:
        correlation_id = request.correlation_id
        if not correlation_id:
            raise ValueError("Incident creation requires a correlation identifier")
        await self.repository.prepare_attempt(
            correlation_id, request.model_dump(mode="json")
        )
        claimed = await self.repository.claim_attempt(correlation_id)
        attempt = await self.repository.attempt(correlation_id)
        if claimed:
            self.repository.audit(
                correlation_id,
                "escalation_accepted",
                {"request": attempt.request},
            )
        await self.session.commit()
        attempt = await self.repository.attempt(correlation_id)
        if attempt.status == "created":
            return "created", TicketResponse.model_validate(attempt.ticket)
        if not claimed:
            return await self.reconcile(correlation_id)

        # Use the original, durably accepted payload even after a definite failure.
        accepted = TicketCreateRequest.model_validate(attempt.request)
        try:
            ticket = await self.provider.create_incident(accepted)
        except ServiceNowError as exc:
            # Only definite rejection can be retried. 5xx/transport/malformed replies
            # might happen after the server has committed the incident.
            status = (
                "failed"
                if exc.status_code in {400, 401, 403, 404, 422, 429}
                else "pending"
            )
            attempt.status = status
            self.repository.audit(
                correlation_id,
                (
                    "ticket_rejected"
                    if status == "failed"
                    else "ticket_pending_verification"
                ),
                {"status_code": exc.status_code},
            )
            await self.session.commit()
            return status, None
        except Exception:
            self.repository.audit(correlation_id, "ticket_pending_verification", {})
            await self.session.commit()
            return "pending", None
        return await self._record_result(correlation_id, ticket, "ticket_created")

    async def reconcile(self, correlation_id: str) -> tuple[str, TicketResponse | None]:
        """Provider lookup only, even if a concurrent dispatch changes state."""
        attempt = await self.repository.attempt(correlation_id)
        if attempt.status == "created":
            return "created", TicketResponse.model_validate(attempt.ticket)
        if attempt.status != "pending":
            return attempt.status, None
        try:
            ticket = await self.provider.find_incident_by_correlation(correlation_id)
        except ServiceNowError as exc:
            conflict = exc.status_code == 409
            self.repository.audit(
                correlation_id,
                "ticket_reconciliation_failed",
                {
                    "status_code": exc.status_code,
                    "manual_intervention_required": conflict,
                },
            )
            await self.session.commit()
            logger.warning(
                "Incident reconciliation failed correlation_id=%s status_code=%s manual_intervention_required=%s",
                correlation_id,
                exc.status_code,
                conflict,
            )
            if conflict:
                raise ServiceNowError(
                    "Multiple incidents match this conversation. Manual reconciliation in ServiceNow is required; another creation attempt remains blocked.",
                    409,
                ) from None
            return "pending", None
        except Exception as exc:
            self.repository.audit(
                correlation_id,
                "ticket_reconciliation_failed",
                {"error_type": type(exc).__name__},
            )
            await self.session.commit()
            logger.warning(
                "Incident reconciliation failed correlation_id=%s error_type=%s",
                correlation_id,
                type(exc).__name__,
            )
            return "pending", None
        if ticket is None:
            return "pending", None
        return await self._record_result(correlation_id, ticket, "ticket_reconciled")

    async def _record_result(
        self, correlation_id: str, ticket: TicketResponse, event: str
    ) -> tuple[str, TicketResponse | None]:
        try:
            attempt = await self.repository.attempt(correlation_id)
            attempt.status = "created"
            attempt.ticket = ticket.model_dump(mode="json")
            self.repository.audit(
                correlation_id,
                event,
                {
                    "ticket_number": ticket.number,
                    "sys_id": ticket.sys_id,
                    "assignment_group": ticket.assignment_group,
                },
            )
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            # The earlier pending record survives and is recoverable by correlation.
            return "pending", None
        return "created", ticket
