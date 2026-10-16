import re
import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.integrations.servicenow import TicketingProvider, get_ticketing_provider
from app.models.chat import (
    ChatRequest,
    ChatResponse,
    ChatResponseType,
    IntentClassification,
    SupportIntent,
)
from app.models.conversation import Conversation
from app.models.knowledge import get_utc_now
from app.models.ticket import TicketCreateRequest
from app.repositories.conversation_repository import ConversationRepository
from app.services.classification_service import ClassificationService
from app.services.incident_service import IncidentService
from app.services.rag_service import RAGService

logger = get_logger("conversation_service")


def normalize(text: str) -> str:
    return re.sub(r"[^\w\s]", "", text.lower()).strip()


def is_decline(text: str) -> bool:
    refusals = {
        "no",
        "nope",
        "nah",
        "cancel",
        "stop",
        "never mind",
        "nevermind",
        "not now",
        "wait",
        "no wait",
        "cancel it",
        "cancel that",
        "cancel this",
        "dont",
        "do not",
        "no need",
    }
    # Preserve clause boundaries so a trailing "No." or "Cancel it." wins,
    # without treating symptoms such as "applications stop responding" as refusal.
    clauses = re.split(r"[.!?;,]+", text)
    text = normalize(text)
    if text in refusals or any(normalize(clause) in refusals for clause in clauses):
        return True
    return bool(
        re.search(
            r"\b(?:not now|no wait|no thanks|no thank you|no ticket|no incident|no need)\b"
            r"|\b(?:cancel (?:it|that|this)|never mind|nevermind)(?: please)?$"
            r"|\b(?:dont|do not|never)\b.*\b(?:create|open|raise|log|submit|escalate|send|file|proceed)\b",
            text,
        )
    )


def is_deferred_request(text: str) -> bool:
    # A future condition is not acceptance to dispatch now.
    return bool(
        re.search(
            r"\b(?:ticket|incident|escalate)\b.*\b(?:if|unless|when|once|after|until)\b",
            normalize(text),
        )
    )


def explicitly_requests_ticket(text: str) -> bool:
    # Require a direct instruction, not a mention of a ticket or a failed step.
    return not is_deferred_request(text) and bool(
        re.match(
            r"^(?:.*?[.!?]\s*)?(?:(?:please|can you|could you|would you)\s+)?(?:create|open|raise|log|submit)\s+(?:(?:an?|the|my)\s+)?(?:incident|ticket)\b",
            text,
            re.I,
        )
        or re.search(r"\bplease escalate(?:\s+this)?[.!?]*$", text, re.I)
        or normalize(text) in {"escalate", "escalate this"}
    )


class ConversationService:
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
        self.repository = ConversationRepository(session)

    async def process_message(self, request: ChatRequest) -> ChatResponse:
        if request.session_id:
            conversation = await self.repository.get(request.session_id)
            if conversation is None:
                raise LookupError("Conversation not found")
        else:
            conversation = Conversation(id=uuid.uuid4().hex, issue="")
            self.session.add(conversation)
        conversation_id = conversation.id
        text = normalize(request.message)
        declined = is_decline(request.message)
        deferred = is_deferred_request(request.message)
        accepted = (
            not declined
            and not deferred
            and (
                request.force_ticket
                or explicitly_requests_ticket(request.message)
                or (
                    bool(conversation.escalation_offered)
                    and text in {"yes", "yes please", "ok", "okay", "accept"}
                )
            )
        )
        greeting = text in {
            "hi",
            "hey",
            "hello",
            "good morning",
            "good afternoon",
            "good evening",
        }
        capabilities = text in {
            "help",
            "help me",
            "what can you do",
            "what can i ask",
            "what i can ask",
            "who are you",
            "what can you help me with",
            "what can you help with",
        }
        failed_steps = bool(
            re.search(
                r"\b(?:steps (?:failed|did not work)|didnt work|did not work|still (?:broken|not working))\b",
                text,
            )
        )

        if (
            not declined
            and not deferred
            and not greeting
            and not capabilities
            and not accepted
        ):
            if not conversation.issue:
                conversation.issue = request.message
            elif not failed_steps:
                conversation.issue = (conversation.issue + "\n" + request.message)[
                    -6000:
                ]
        if accepted and not conversation.issue:
            # Extract issue detail from a standalone explicit request, if present.
            detail = re.sub(
                r"^(?:(?:please|can you|could you|would you)\s+)?(?:create|open|raise|log|submit)\s+(?:(?:an?|the|my)\s+)?(?:ticket|incident)(?:\s+for)?\s*",
                "",
                request.message,
                flags=re.I,
            ).strip(" .:")
            if normalize(detail) not in {
                "",
                "this",
                "this issue",
                "me",
                "my issue",
                "escalate",
                "escalate this",
                "please escalate",
            }:
                conversation.issue = detail
        classification = self.classifier.classify(conversation.issue or request.message)
        conversation.classification = classification.model_dump(mode="json")
        conversation.updated_at = get_utc_now()
        self.repository.add_message(conversation.id, "user", request.message)
        self.repository.audit(
            conversation.id, "request_received", {"message": request.message}
        )
        self.repository.audit(
            conversation.id, "intent_classified", classification.model_dump(mode="json")
        )
        # Retain the issue even when retrieval or Gemini becomes unavailable.
        await self.session.commit()

        if declined:
            conversation.escalation_offered = 0
            self.repository.audit(conversation.id, "escalation_declined", {})
            return await self._reply(
                conversation,
                classification,
                ChatResponseType.CONVERSATIONAL,
                "Understood. I will not create an incident. Any incident already created remains unchanged.",
            )
        if deferred:
            if not conversation.issue:
                return await self._reply(
                    conversation,
                    classification,
                    ChatResponseType.CONVERSATIONAL,
                    "Please describe the issue first. I have not created an incident.",
                )
            return await self._offer(
                conversation,
                classification,
                "I have not created an incident. Please confirm explicitly when you want to proceed.",
            )
        if greeting or capabilities:
            return await self._reply(
                conversation,
                classification,
                ChatResponseType.CONVERSATIONAL,
                "I can help with password resets, VPN connectivity, software guidance, Outlook, Teams, SAP, and disk-space troubleshooting. Describe one issue to begin. Device tools in the sidebar use simulated telemetry.",
            )
        if accepted:
            if not conversation.issue:
                return await self._reply(
                    conversation,
                    classification,
                    ChatResponseType.CONVERSATIONAL,
                    "Please describe the issue before I create an incident.",
                )
            existing_attempt = await self.repository.find_attempt(conversation.id)
            if (
                classification.intent == SupportIntent.SOFTWARE_REQUEST
                and existing_attempt is None
            ):
                return await self._reply(
                    conversation,
                    classification,
                    ChatResponseType.SERVICE_REQUEST,
                    "Formal software service request submission is not available yet. Please use your ServiceNow service catalog for software or licensing requests; I have not created an incident.",
                )
            history = await self.repository.messages(conversation.id)
            transcript = "\n".join(f"{m.role}: {m.content}" for m in history)
            status, ticket = await IncidentService(
                self.session, self.ticketing_provider
            ).create_or_reconcile(
                TicketCreateRequest(
                    short_description=conversation.issue.splitlines()[0][:150],
                    description=(
                        f"Support issue: {conversation.issue}\n\nConversation:\n{transcript}"
                    )[:4000],
                    urgency=classification.urgency,
                    impact=classification.impact,
                    category=classification.category,
                    subcategory=classification.subcategory,
                    assignment_group=classification.assignment_group,
                    correlation_id=conversation.id,
                )
            )
            conversation = await self.repository.get(conversation_id)
            conversation.escalation_offered = 0
            if status == "created":
                return await self._reply(
                    conversation,
                    classification,
                    ChatResponseType.TICKET_CREATED,
                    f"Incident **{ticket.number}** is recorded with **{ticket.assignment_group}**, priority **{ticket.priority}**.",
                    ticket=ticket,
                )
            if status == "failed":
                return await self._reply(
                    conversation,
                    classification,
                    ChatResponseType.TICKET_FAILED,
                    "ServiceNow rejected the incident request. No incident was confirmed. Check the integration configuration before explicitly retrying.",
                )
            return await self._reply(
                conversation,
                classification,
                ChatResponseType.PENDING_VERIFICATION,
                "Incident creation is pending verification. The outcome is uncertain, so another creation attempt is blocked. Use Check incident status to look for the existing incident.",
            )
        if failed_steps:
            return await self._offer(
                conversation,
                classification,
                "The troubleshooting did not resolve your issue.",
            )
        conversation_id = conversation.id
        try:
            grounded = await self.rag_service.generate_grounded_answer(
                query=conversation.issue
            )
        except Exception:
            await self.session.rollback()
            # Rollback expires ORM attributes; reload after a retrieval DB failure.
            conversation = await self.repository.get(conversation_id)
            return await self._offer(
                conversation,
                classification,
                "Knowledge assistance is unavailable. Your issue details are saved.",
            )
        # Retrieval may roll back its failed transaction before returning fallback.
        # Reload expired ORM state before recording the result or offering escalation.
        conversation = await self.repository.get(conversation_id)
        self.repository.audit(
            conversation.id,
            "knowledge_retrieved",
            {
                "sources": grounded.sources,
                "chunks": [c.model_dump(mode="json") for c in grounded.matched_chunks],
                "confidence": grounded.confidence,
                "selected_chunk_ids": grounded.selected_chunk_ids,
                "fallback_reason": grounded.fallback_reason,
            },
        )
        if grounded.should_escalate:
            return await self._offer(
                conversation,
                classification,
                "I could not find sufficiently reliable knowledge for this issue.",
            )
        if classification.intent == SupportIntent.SOFTWARE_REQUEST:
            return await self._reply(
                conversation,
                classification,
                ChatResponseType.SERVICE_REQUEST,
                grounded.answer
                + "\n\nFormal software service request submission is not available yet. Use your ServiceNow service catalog if approval is required.",
                sources=grounded.sources,
            )
        self.repository.audit(
            conversation.id,
            "rag_answer_deflected",
            {"sources": grounded.sources, "confidence": grounded.confidence},
        )
        return await self._reply(
            conversation,
            classification,
            ChatResponseType.DEFLECTED_RAG,
            grounded.answer,
            sources=grounded.sources,
        )

    async def _offer(
        self,
        conversation: Conversation,
        classification: IntentClassification,
        reason: str,
    ) -> ChatResponse:
        if classification.intent == SupportIntent.SOFTWARE_REQUEST:
            return await self._reply(
                conversation,
                classification,
                ChatResponseType.SERVICE_REQUEST,
                reason
                + " Formal software service request submission is not available yet; use your ServiceNow service catalog.",
            )
        conversation.escalation_offered = 1
        self.repository.audit(conversation.id, "escalation_offered", {"reason": reason})
        return await self._reply(
            conversation,
            classification,
            ChatResponseType.ESCALATION_OFFERED,
            reason
            + f" Would you like an incident routed to {classification.assignment_group}? Reply 'Create a ticket' or choose the escalation option.",
        )

    async def _reply(
        self,
        conversation: Conversation,
        classification: IntentClassification,
        response_type: ChatResponseType,
        message: str,
        **kwargs,
    ) -> ChatResponse:
        response = ChatResponse(
            session_id=conversation.id,
            classification=classification,
            response_type=response_type,
            message=message,
            **kwargs,
        )
        self.repository.add_message(
            conversation.id, "assistant", message, response.model_dump(mode="json")
        )
        await self.session.commit()
        return response
