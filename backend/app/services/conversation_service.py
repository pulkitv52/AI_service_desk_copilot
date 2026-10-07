import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.integrations.servicenow import TicketingProvider, get_ticketing_provider
from app.models.chat import (
    ChatRequest,
    ChatResponse,
    ChatResponseType,
    SupportIntent,
)
from app.models.knowledge import AuditLog
from app.models.ticket import (
    TicketCreateRequest,
    TicketUrgency,
    TicketImpact,
)
from app.services.classification_service import ClassificationService
from app.services.rag_service import RAGService

logger = get_logger("conversation_service")


class ConversationService:
    """Orchestrates end-to-end conversation flow, RAG deflection, and incident escalation."""

    def __init__(
        self,
        session: AsyncSession,
        ticketing_provider: Optional[TicketingProvider] = None,
        classification_service: Optional[ClassificationService] = None,
        rag_service: Optional[RAGService] = None,
    ) -> None:
        self.session = session
        self.ticketing_provider = ticketing_provider or get_ticketing_provider()
        self.classifier = classification_service or ClassificationService()
        self.rag_service = rag_service or RAGService(session)

    async def _log_audit_event(
        self, session_id: str, event_type: str, payload: dict
    ) -> None:
        """Record audit event in PostgreSQL database."""
        try:
            audit = AuditLog(
                session_id=session_id,
                event_type=event_type,
                payload=payload,
            )
            self.session.add(audit)
            await self.session.flush()
        except Exception as exc:
            logger.warning("Failed to record audit log: %s", exc)

    async def process_message(self, request: ChatRequest) -> ChatResponse:
        """Process incoming user message through classification, RAG deflection, or ticketing."""
        session_id = request.session_id or uuid.uuid4().hex

        await self._log_audit_event(
            session_id=session_id,
            event_type="request_received",
            payload={"message": request.message, "user_id": request.user_id},
        )

        classification = self.classifier.classify(request.message)

        await self._log_audit_event(
            session_id=session_id,
            event_type="intent_classified",
            payload=classification.model_dump(),
        )

        msg_lower = request.message.lower()

        # Case 0: Conversational Greetings (e.g. "hey", "hello", "hi")
        import re
        clean_text = re.sub(r"[^\w\s]", "", msg_lower).strip()
        greetings = {
            "hi",
            "hey",
            "hello",
            "good morning",
            "good afternoon",
            "good evening",
            "hey there",
            "hi there",
            "greetings",
            "howdy",
        }
        capabilities_phrases = {
            "what can i ask",
            "what can you do",
            "what do you do",
            "help",
            "capabilities",
            "options",
            "what questions can i ask",
            "how can you help",
            "how do you work",
        }
        if clean_text in greetings:
            return ChatResponse(
                session_id=session_id,
                response_type=ChatResponseType.DEFLECTED_RAG,
                message=(
                    "Hello! I am your AI Service Desk Copilot. How can I assist you today?\n\n"
                    "You can ask me about **password resets**, **VPN connectivity**, "
                    "**software requests**, **endpoint disk cleanup**, or report an **enterprise application issue**."
                ),
                classification=classification,
                sources=[],
            )

        if any(phrase in clean_text for phrase in capabilities_phrases):
            return ChatResponse(
                session_id=session_id,
                response_type=ChatResponseType.DEFLECTED_RAG,
                message=(
                    "### What You Can Ask Me:\n\n"
                    "1. **Identity & Passwords (KB-SEC-001)**\n"
                    "   * *'How do I reset my Windows domain password?'*\n"
                    "   * *'I am locked out of my corporate login.'*\n\n"
                    "2. **VPN & Remote Network (KB-NET-002)**\n"
                    "   * *'My GlobalProtect VPN keeps disconnecting.'*\n"
                    "   * *'How do I switch to an alternate VPN gateway?'*\n\n"
                    "3. **Storage & Disk Space (KB-EUC-003)**\n"
                    "   * *'My laptop says disk space is almost full.'*\n"
                    "   * *'How do I clean temporary caches on Windows?'*\n\n"
                    "4. **Approved Software Catalog (KB-EUC-004)**\n"
                    "   * *'I need Visual Studio Code installed on my machine.'*\n"
                    "   * *'How do I install Slack or Docker Desktop?'*\n\n"
                    "5. **Collaboration Tools (KB-COL-005, KB-COL-006)**\n"
                    "   * *'My Outlook search indexing is broken.'*\n"
                    "   * *'Microsoft Teams keeps crashing during video calls.'*\n\n"
                    "6. **Enterprise Applications (KB-APP-007)**\n"
                    "   * *'SAP is not allowing me to approve purchase orders in Fiori.'*\n"
                    "   * *'How do I check /nSU53 authorization errors?'*\n\n"
                    "7. **Automated Escalation & Ticketing**\n"
                    "   * *'Create a ticket for my issue'*\n"
                    "   * *'Troubleshooting steps failed, please escalate.'*"
                ),
                classification=classification,
                sources=[],
            )

        # Case 1: Explicit Ticket Request or Forced Escalation
        escalation_keywords = [
            "create a ticket",
            "create ticket",
            "open a ticket",
            "open ticket",
            "raise an incident",
            "raise a ticket",
            "log a ticket",
            "escalate",
            "please escalate",
            "escalate this",
            "steps failed",
            "steps did not work",
            "didn't work",
            "did not work",
        ]
        if request.force_ticket or any(phrase in msg_lower for phrase in escalation_keywords):
            ticket_req = TicketCreateRequest(
                short_description=request.message[:150],
                description=(
                    f"User Request: {request.message}\n"
                    f"Classified Intent: {classification.intent.value}\n"
                    f"Reported Application: {classification.application or 'N/A'}"
                ),
                urgency=classification.urgency,
                impact=classification.impact,
                category=classification.category,
                subcategory=classification.subcategory,
                assignment_group=classification.assignment_group,
                caller_id=request.user_id,
                correlation_id=session_id,
            )
            created_ticket = await self.ticketing_provider.create_incident(ticket_req)

            await self._log_audit_event(
                session_id=session_id,
                event_type="ticket_created",
                payload={
                    "ticket_number": created_ticket.number,
                    "sys_id": created_ticket.sys_id,
                },
            )

            return ChatResponse(
                session_id=session_id,
                response_type=ChatResponseType.TICKET_CREATED,
                message=(
                    f"I have created an incident ticket for you: **{created_ticket.number}**.\n"
                    f"It has been routed to the **{created_ticket.assignment_group}** team with priority **{created_ticket.priority}**.\n"
                    "An IT support engineer will follow up shortly."
                ),
                classification=classification,
                ticket=created_ticket,
            )

        # Case 2: Software Installation Request (UC-03)
        if classification.intent == SupportIntent.SOFTWARE_REQUEST:
            grounded = await self.rag_service.generate_grounded_answer(
                query=request.message
            )
            return ChatResponse(
                session_id=session_id,
                response_type=ChatResponseType.SERVICE_REQUEST,
                message=(
                    f"{grounded.answer}\n\n"
                    "If you require a licensed tool or manager approval, reply with "
                    "'Create a ticket' and I will submit a formal Service Request."
                ),
                classification=classification,
                sources=grounded.sources,
            )

        # Case 3: Diagnostic / Endpoint Storage Remediation (UC-04)
        if classification.intent == SupportIntent.DIAGNOSTIC_REMEDIATION:
            grounded = await self.rag_service.generate_grounded_answer(
                query=request.message
            )
            return ChatResponse(
                session_id=session_id,
                response_type=ChatResponseType.DIAGNOSTIC_ACTION,
                message=grounded.answer,
                classification=classification,
                sources=grounded.sources,
            )

        # Case 4: Knowledge Inquiries & General Inquiries (UC-01, UC-02, UC-05)
        grounded = await self.rag_service.generate_grounded_answer(
            query=request.message
        )

        if not grounded.should_escalate:
            # Deflection success!
            await self._log_audit_event(
                session_id=session_id,
                event_type="rag_answer_deflected",
                payload={
                    "sources": grounded.sources,
                    "confidence": grounded.confidence,
                },
            )
            return ChatResponse(
                session_id=session_id,
                response_type=ChatResponseType.DEFLECTED_RAG,
                message=grounded.answer,
                classification=classification,
                sources=grounded.sources,
            )

        # Case 5: Knowledge Deflection - Low Confidence (Offer Escalation per AGENTS.md Section 14)
        return ChatResponse(
            session_id=session_id,
            response_type=ChatResponseType.DEFLECTED_RAG,
            message=(
                "I was unable to find an authoritative self-service guide matching your request in the IT knowledge base.\n\n"
                f"Would you like me to open an incident ticket and route it to **{classification.assignment_group}**? "
                "Reply with **'Create a ticket'** or click the escalation option below."
            ),
            classification=classification,
            sources=[],
        )
