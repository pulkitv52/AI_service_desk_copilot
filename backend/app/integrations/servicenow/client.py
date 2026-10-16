import re
from typing import Any

import httpx

from app.core.logging import get_logger
from app.models.ticket import TicketCreateRequest, TicketResponse, TicketUpdateRequest

logger = get_logger("servicenow_client")
SYS_ID = re.compile(r"^[a-f0-9]{32}$")


class ServiceNowError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ServiceNowProvider:
    def __init__(
        self,
        instance_url: str,
        username: str,
        password: str,
        timeout_seconds: float = 10.0,
        client: httpx.AsyncClient | None = None,
        caller_sys_id: str | None = None,
        group_ids: dict[str, str] | None = None,
        fallback_group_sys_id: str | None = None,
    ) -> None:
        self.instance_url = instance_url.rstrip("/")
        self.username = username
        self.password = password
        self.timeout = timeout_seconds
        self._external_client = client
        self.caller_sys_id = caller_sys_id
        self.group_ids = group_ids or {}
        self.fallback_group_sys_id = fallback_group_sys_id

    def _get_client(self) -> httpx.AsyncClient:
        return self._external_client or httpx.AsyncClient(
            base_url=self.instance_url,
            auth=(self.username, self.password),
            timeout=self.timeout,
            headers={"Accept": "application/json"},
        )

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        client = self._get_client()
        try:
            response = await client.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json()["result"]
        except httpx.TimeoutException:
            raise ServiceNowError("ServiceNow request timed out", 504) from None
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            logger.warning("ServiceNow request rejected status=%s", status)
            raise ServiceNowError(
                f"ServiceNow returned HTTP {status}", status
            ) from None
        except httpx.RequestError:
            raise ServiceNowError("ServiceNow connection unavailable", 502) from None
        except (ValueError, KeyError, TypeError):
            raise ServiceNowError(
                "ServiceNow returned an invalid response", 502
            ) from None
        finally:
            if self._external_client is None:
                await client.aclose()

    @staticmethod
    def _reference(value: Any) -> str | None:
        if isinstance(value, dict):
            return value.get("value") or value.get("display_value")
        return value or None

    def _map_result_to_response(self, result: dict[str, Any]) -> TicketResponse:
        if (
            not isinstance(result, dict)
            or not result.get("sys_id")
            or not result.get("number")
        ):
            raise ServiceNowError("ServiceNow returned an invalid incident", 502)
        group_id = self._reference(result.get("assignment_group"))
        group = next(
            (name for name, value in self.group_ids.items() if value == group_id), None
        )
        if group is None:
            group = (
                "Service Desk L1"
                if group_id and group_id == self.fallback_group_sys_id
                else group_id
            )
        raw_priority = result.get("priority")
        priority = str(raw_priority) if raw_priority else None
        return TicketResponse(
            sys_id=result["sys_id"],
            number=result["number"],
            short_description=result.get("short_description", ""),
            description=result.get("description"),
            state=str(result.get("state", "1")),
            urgency=str(result.get("urgency", "3")),
            impact=str(result.get("impact", "3")),
            priority=(
                (priority if priority.startswith("P") else f"P{priority}")
                if priority
                else None
            ),
            category=result.get("category"),
            subcategory=result.get("subcategory"),
            assignment_group=group,
            caller_id=self._reference(result.get("caller_id")),
            provider="servicenow",
            created_at=result.get("sys_created_on", ""),
            updated_at=result.get("sys_updated_on"),
        )

    def _group_id(self, name: str | None) -> str:
        value = self.group_ids.get(name or "") or self.fallback_group_sys_id
        if not value or not SYS_ID.fullmatch(value):
            raise ServiceNowError(
                "Configure a valid ServiceNow assignment group and fallback sys_id", 422
            )
        return value

    async def create_incident(self, ticket: TicketCreateRequest) -> TicketResponse:
        if not self.caller_sys_id or not SYS_ID.fullmatch(self.caller_sys_id):
            raise ServiceNowError(
                "Configure a valid ServiceNow demo caller sys_id", 422
            )
        payload = ticket.model_dump(mode="json", exclude_none=True)
        payload["caller_id"] = self.caller_sys_id
        payload["assignment_group"] = self._group_id(ticket.assignment_group)
        result = await self._request("POST", "/api/now/table/incident", json=payload)
        return self._map_result_to_response(result)

    async def get_incident(self, sys_id: str) -> TicketResponse | None:
        if sys_id.upper().startswith("INC"):
            if not re.fullmatch(r"INC\d+", sys_id, re.I):
                return None
            tickets = await self.query_incidents(f"number={sys_id.upper()}", 1)
            return tickets[0] if tickets else None
        if not SYS_ID.fullmatch(sys_id):
            return None
        try:
            return self._map_result_to_response(
                await self._request("GET", f"/api/now/table/incident/{sys_id}")
            )
        except ServiceNowError as exc:
            if exc.status_code == 404:
                return None
            raise

    async def update_incident(
        self, sys_id: str, update: TicketUpdateRequest
    ) -> TicketResponse | None:
        if not SYS_ID.fullmatch(sys_id):
            existing = await self.get_incident(sys_id)
            if existing is None:
                return None
            sys_id = existing.sys_id
        payload = update.model_dump(mode="json", exclude_none=True)
        if update.assignment_group:
            payload["assignment_group"] = self._group_id(update.assignment_group)
        try:
            return self._map_result_to_response(
                await self._request(
                    "PATCH", f"/api/now/table/incident/{sys_id}", json=payload
                )
            )
        except ServiceNowError as exc:
            if exc.status_code == 404:
                return None
            raise

    async def query_incidents(
        self, query: str = "", limit: int = 10
    ) -> list[TicketResponse]:
        result = await self._request(
            "GET",
            "/api/now/table/incident",
            params={"sysparm_query": query, "sysparm_limit": limit},
        )
        if not isinstance(result, list):
            raise ServiceNowError("ServiceNow returned an invalid incident list", 502)
        return [self._map_result_to_response(item) for item in result]

    async def find_incident_by_correlation(
        self, correlation_id: str
    ) -> TicketResponse | None:
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,128}", correlation_id):
            raise ServiceNowError("Invalid incident correlation identifier", 422)
        tickets = await self.query_incidents(f"correlation_id={correlation_id}", 2)
        if len(tickets) > 1:
            raise ServiceNowError(
                "Multiple incidents require manual reconciliation", 409
            )
        return tickets[0] if tickets else None

    async def validate_references(self) -> None:
        """Explicit live preflight for the demo; verify IDs without creating records."""
        self._group_id(None)
        if not self.caller_sys_id or not SYS_ID.fullmatch(self.caller_sys_id):
            raise ServiceNowError("Configure a valid demo caller sys_id", 422)
        for table, ids in (
            ("sys_user", [self.caller_sys_id]),
            (
                "sys_user_group",
                set([self.fallback_group_sys_id, *self.group_ids.values()]),
            ),
        ):
            for sys_id in ids:
                if not sys_id or not SYS_ID.fullmatch(sys_id):
                    raise ServiceNowError("Invalid configured reference sys_id", 422)
                result = await self._request(
                    "GET",
                    f"/api/now/table/{table}/{sys_id}",
                    params={"sysparm_fields": "sys_id,active"},
                )
                if (
                    result.get("sys_id") != sys_id
                    or str(result.get("active", "true")).lower() == "false"
                ):
                    raise ServiceNowError(
                        "Configured caller or assignment group is unavailable", 422
                    )
