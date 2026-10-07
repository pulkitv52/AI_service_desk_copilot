from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.logging import get_logger
from app.models.chat import ChatRequest, ChatResponse
from app.services.conversation_service import ConversationService

logger = get_logger("routes_chat")
router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post(
    "",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Process conversational support message",
)
async def chat_endpoint(
    request: ChatRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ChatResponse:
    """Conversational endpoint orchestrating intent classification, RAG deflection, and ServiceNow escalation."""
    try:
        service = ConversationService(session)
        return await service.process_message(request)
    except Exception as exc:
        logger.exception("Chat processing failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat processing failed: {exc}",
        ) from exc
