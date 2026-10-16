from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, IncidentAttempt, Message
from app.models.knowledge import AuditLog, get_utc_now


class ConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, conversation_id: str) -> Conversation | None:
        return await self.session.get(Conversation, conversation_id)

    async def list_recent(self) -> list[Conversation]:
        result = await self.session.scalars(
            select(Conversation).order_by(Conversation.updated_at.desc()).limit(50)
        )
        return list(result)

    async def messages(self, conversation_id: str) -> list[Message]:
        result = await self.session.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.id)
        )
        return list(result)

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        response: dict | None = None,
    ) -> None:
        self.session.add(
            Message(
                conversation_id=conversation_id,
                role=role,
                content=content,
                response=response,
            )
        )

    def audit(self, session_id: str, event_type: str, payload: dict) -> None:
        self.session.add(
            AuditLog(session_id=session_id, event_type=event_type, payload=payload)
        )

    async def audit_events(self, session_id: str) -> list[AuditLog]:
        result = await self.session.scalars(
            select(AuditLog)
            .where(AuditLog.session_id == session_id)
            .order_by(AuditLog.created_at, AuditLog.id)
        )
        return list(result)

    async def prepare_attempt(self, correlation_id: str, payload: dict) -> None:
        # ON CONFLICT keeps concurrent requests from replacing an accepted payload.
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert

        insert = (
            sqlite_insert
            if self.session.get_bind().dialect.name == "sqlite"
            else pg_insert
        )
        stmt = (
            insert(IncidentAttempt)
            .values(id=correlation_id, status="ready", request=payload)
            .on_conflict_do_nothing(index_elements=["id"])
        )
        await self.session.execute(stmt)

    async def claim_attempt(self, correlation_id: str) -> bool:
        # The state transition and audit must commit before any external side effect.
        result = await self.session.execute(
            update(IncidentAttempt)
            .where(
                IncidentAttempt.id == correlation_id,
                IncidentAttempt.status.in_(["ready", "failed"]),
            )
            .values(status="pending", updated_at=get_utc_now())
            .returning(IncidentAttempt.id)
        )
        return result.scalar_one_or_none() is not None

    async def attempt(self, correlation_id: str) -> IncidentAttempt:
        result = await self.session.execute(
            select(IncidentAttempt)
            .where(IncidentAttempt.id == correlation_id)
            .execution_options(populate_existing=True)
        )
        return result.scalar_one()

    async def find_attempt(self, correlation_id: str) -> IncidentAttempt | None:
        return await self.session.get(
            IncidentAttempt, correlation_id, populate_existing=True
        )
