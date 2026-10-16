import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.chat import ChatRequest, ChatResponse
from app.models.conversation import (
    Conversation,
    IncidentAttempt,
    AuditEvent,
    ConversationDetail,
    ConversationSummary,
    SavedMessage,
)
from app.models.ticket import IncidentStatusResponse
from app.integrations.servicenow import ServiceNowError, get_ticketing_provider
from app.repositories.conversation_repository import ConversationRepository
from app.services.conversation_service import ConversationService
from app.services.incident_service import IncidentService

router = APIRouter(tags=["Chat"])


def reconciliation_error(exc: ServiceNowError) -> HTTPException:
    if exc.status_code == 409:
        return HTTPException(
            409,
            {
                "code": "manual_reconciliation_required",
                "message": "Multiple incidents match this conversation. Manual reconciliation in ServiceNow is required; another creation attempt remains blocked.",
            },
        )
    return HTTPException(503, "Incident verification unavailable")


@router.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest, session: AsyncSession = Depends(get_db_session)
) -> ChatResponse:
    try:
        return await ConversationService(session).process_message(request)
    except ServiceNowError as exc:
        raise reconciliation_error(exc) from None
    except LookupError:
        raise HTTPException(404, "Conversation not found") from None
    except Exception:
        raise HTTPException(
            503,
            "Support workflow unavailable. Retry using the same conversation; pending incidents will be verified before another creation.",
        ) from None


@router.post("/api/conversations", response_model=ConversationSummary, status_code=201)
async def start_conversation(
    session: AsyncSession = Depends(get_db_session),
) -> ConversationSummary:
    conversation = Conversation(id=uuid.uuid4().hex, issue="")
    session.add(conversation)
    await session.commit()
    return ConversationSummary(
        id=conversation.id, issue="", updated_at=conversation.updated_at.isoformat()
    )


@router.get("/api/conversations", response_model=list[ConversationSummary])
async def list_conversations(
    session: AsyncSession = Depends(get_db_session),
) -> list[ConversationSummary]:
    conversations = await ConversationRepository(session).list_recent()
    return [
        ConversationSummary(id=c.id, issue=c.issue, updated_at=c.updated_at.isoformat())
        for c in conversations
    ]


@router.get("/api/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str, session: AsyncSession = Depends(get_db_session)
) -> ConversationDetail:
    repository = ConversationRepository(session)
    conversation = await repository.get(conversation_id)
    if conversation is None:
        raise HTTPException(404, "Conversation not found")
    messages = await repository.messages(conversation_id)
    attempt = await session.get(IncidentAttempt, conversation_id)
    return ConversationDetail(
        id=conversation.id,
        issue=conversation.issue,
        updated_at=conversation.updated_at.isoformat(),
        incident_status=attempt.status if attempt else None,
        ticket=attempt.ticket if attempt else None,
        messages=[
            SavedMessage(
                id=m.id,
                role=m.role,
                content=m.content,
                created_at=m.created_at.isoformat(),
                response=m.response,
            )
            for m in messages
        ],
    )


@router.post(
    "/api/conversations/{conversation_id}/reconcile",
    response_model=IncidentStatusResponse,
)
async def reconcile_incident(
    conversation_id: str, session: AsyncSession = Depends(get_db_session)
) -> IncidentStatusResponse:
    repository = ConversationRepository(session)
    if await repository.get(conversation_id) is None:
        raise HTTPException(404, "Conversation not found")
    attempt = await session.get(IncidentAttempt, conversation_id)
    if attempt is None:
        raise HTTPException(404, "No accepted incident creation for this conversation")
    # Reconciliation is read-only at the provider: never claim a new dispatch here.
    if attempt.status not in {"pending", "created"}:
        return IncidentStatusResponse(status=attempt.status)
    try:
        status, ticket = await IncidentService(
            session, get_ticketing_provider()
        ).reconcile(conversation_id)
    except ServiceNowError as exc:
        raise reconciliation_error(exc) from None
    return IncidentStatusResponse(status=status, ticket=ticket)


@router.get("/api/audit/{session_id}", response_model=list[AuditEvent])
async def get_audit(
    session_id: str, session: AsyncSession = Depends(get_db_session)
) -> list[AuditEvent]:
    events = await ConversationRepository(session).audit_events(session_id)
    return [
        AuditEvent(
            id=e.id,
            event_type=e.event_type,
            payload=e.payload,
            created_at=e.created_at.isoformat(),
        )
        for e in events
    ]
