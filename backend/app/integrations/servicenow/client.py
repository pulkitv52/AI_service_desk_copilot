from typing import Any, Optional
import httpx

from app.core.logging import get_logger
from app.models.ticket import (
    TicketCreateRequest,
    TicketUpdateRequest,
    TicketResponse,
)

logger = get_logger("servicenow_client")


class ServiceNowError(Exception):
    """Base exception for ServiceNow API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ServiceNowProvider:
    """ServiceNow REST API integration provider."""

    def __init__(
        self,
        instance_url: str,
        username: str,
        password: str,
        timeout_seconds: float = 10.0,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.instance_url = instance_url.rstrip("/")
        self.username = username
        self.password = password
        self.timeout = timeout_seconds
        self._external_client = client

    def _get_client(self) -> httpx.AsyncClient:
        if self._external_client is not None:
            return self._external_client
        return httpx.AsyncClient(
            base_url=self.instance_url,
            auth=(self.username, self.password),
            timeout=self.timeout,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

    def _map_result_to_response(self, result: dict[str, Any]) -> TicketResponse:
        """Map ServiceNow incident JSON result to TicketResponse domain model."""
        sys_id = result.get("sys_id", "")
        number = result.get("number", "")
        short_desc = result.get("short_description", "")
        desc = result.get("description")
        state = result.get("state", "1")
        urgency = result.get("urgency", "3")
        impact = result.get("impact", "3")
        priority = result.get("priority", "3")
        category = result.get("category")
        subcategory = result.get("subcategory")

        # assignment_group can be a string or a display object {"link": "...", "value": "..."}
        raw_ag = result.get("assignment_group")
        assignment_group: Optional[str] = None
        if isinstance(raw_ag, dict):
            assignment_group = raw_ag.get("display_value") or raw_ag.get("value")
        elif isinstance(raw_ag, str):
            assignment_group = raw_ag

        # caller_id can be a string or a display object
        raw_caller = result.get("caller_id")
        caller_id: Optional[str] = None
        if isinstance(raw_caller, dict):
            caller_id = raw_caller.get("display_value") or raw_caller.get("value")
        elif isinstance(raw_caller, str):
            caller_id = raw_caller

        created_at = result.get("sys_created_on", "")
        updated_at = result.get("sys_updated_on")

        return TicketResponse(
            sys_id=sys_id,
            number=number,
            short_description=short_desc,
            description=desc,
            state=str(state),
            urgency=str(urgency),
            impact=str(impact),
            priority=f"P{priority}" if priority else None,
            category=category,
            subcategory=subcategory,
            assignment_group=assignment_group,
            caller_id=caller_id,
            provider="servicenow",
            created_at=created_at or "",
            updated_at=updated_at,
        )

    async def create_incident(self, ticket: TicketCreateRequest) -> TicketResponse:
        """Create a new ServiceNow incident record via Table API."""
        url = "/api/now/table/incident"
        payload: dict[str, Any] = {
            "short_description": ticket.short_description,
            "description": ticket.description,
            "urgency": ticket.urgency.value,
            "impact": ticket.impact.value,
        }
        if ticket.category:
            payload["category"] = ticket.category
        if ticket.subcategory:
            payload["subcategory"] = ticket.subcategory
        if ticket.assignment_group:
            payload["assignment_group"] = ticket.assignment_group
        if ticket.caller_id:
            payload["caller_id"] = ticket.caller_id
        if ticket.correlation_id:
            payload["correlation_id"] = ticket.correlation_id

        client = self._get_client()
        should_close = self._external_client is None
        try:
            logger.info(
                "Dispatching incident creation to ServiceNow short_description=%s",
                ticket.short_description,
            )
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            result = data.get("result", {})
            logger.info(
                "ServiceNow incident created successfully number=%s sys_id=%s",
                result.get("number"),
                result.get("sys_id"),
            )
            return self._map_result_to_response(result)
        except httpx.TimeoutException as exc:
            logger.error("ServiceNow API timeout during incident creation: %s", exc)
            raise ServiceNowError("ServiceNow API timed out", status_code=504) from exc
        except httpx.HTTPStatusError as exc:
            logger.error(
                "ServiceNow API returned HTTP error %s: %s",
                exc.response.status_code,
                exc.response.text,
            )
            raise ServiceNowError(
                f"ServiceNow API error: {exc.response.status_code}",
                status_code=exc.response.status_code,
            ) from exc
        except httpx.RequestError as exc:
            logger.error("ServiceNow connection failure: %s", exc)
            raise ServiceNowError(
                f"Failed to connect to ServiceNow: {exc}", status_code=502
            ) from exc
        finally:
            if should_close:
                await client.aclose()

    async def get_incident(self, sys_id: str) -> Optional[TicketResponse]:
        """Fetch incident by sys_id or incident number."""
        client = self._get_client()
        should_close = self._external_client is None
        try:
            # If sys_id starts with INC, query by number
            if sys_id.upper().startswith("INC"):
                url = f"/api/now/table/incident?sysparm_query=number={sys_id.upper()}&sysparm_limit=1"
                response = await client.get(url)
                response.raise_for_status()
                results = response.json().get("result", [])
                if not results:
                    return None
                return self._map_result_to_response(results[0])
            else:
                url = f"/api/now/table/incident/{sys_id}"
                response = await client.get(url)
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                result = response.json().get("result", {})
                return self._map_result_to_response(result)
        except httpx.TimeoutException as exc:
            logger.error("ServiceNow API timeout during incident retrieval: %s", exc)
            raise ServiceNowError("ServiceNow API timed out", status_code=504) from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            logger.error("ServiceNow API HTTP error: %s", exc.response.status_code)
            raise ServiceNowError(
                f"ServiceNow API error: {exc.response.status_code}",
                status_code=exc.response.status_code,
            ) from exc
        except httpx.RequestError as exc:
            logger.error("ServiceNow connection error: %s", exc)
            raise ServiceNowError(
                f"Failed to connect to ServiceNow: {exc}", status_code=502
            ) from exc
        finally:
            if should_close:
                await client.aclose()

    async def update_incident(
        self, sys_id: str, update: TicketUpdateRequest
    ) -> Optional[TicketResponse]:
        """Update an existing ServiceNow incident by sys_id."""
        url = f"/api/now/table/incident/{sys_id}"
        payload: dict[str, Any] = {}
        if update.comments:
            payload["comments"] = update.comments
        if update.work_notes:
            payload["work_notes"] = update.work_notes
        if update.state is not None:
            payload["state"] = update.state.value
        if update.urgency is not None:
            payload["urgency"] = update.urgency.value
        if update.impact is not None:
            payload["impact"] = update.impact.value
        if update.assignment_group is not None:
            payload["assignment_group"] = update.assignment_group

        client = self._get_client()
        should_close = self._external_client is None
        try:
            response = await client.patch(url, json=payload)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            result = response.json().get("result", {})
            return self._map_result_to_response(result)
        except httpx.TimeoutException as exc:
            logger.error("ServiceNow API timeout during incident update: %s", exc)
            raise ServiceNowError("ServiceNow API timed out", status_code=504) from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            logger.error("ServiceNow update HTTP error: %s", exc.response.status_code)
            raise ServiceNowError(
                f"ServiceNow API error: {exc.response.status_code}",
                status_code=exc.response.status_code,
            ) from exc
        except httpx.RequestError as exc:
            logger.error("ServiceNow update connection error: %s", exc)
            raise ServiceNowError(
                f"Failed to connect to ServiceNow: {exc}", status_code=502
            ) from exc
        finally:
            if should_close:
                await client.aclose()

    async def query_incidents(
        self, query: str = "", limit: int = 10
    ) -> list[TicketResponse]:
        """Query ServiceNow incidents using sysparm_query syntax."""
        url = f"/api/now/table/incident?sysparm_limit={limit}"
        if query:
            url += f"&sysparm_query={query}"

        client = self._get_client()
        should_close = self._external_client is None
        try:
            response = await client.get(url)
            response.raise_for_status()
            results = response.json().get("result", [])
            return [self._map_result_to_response(item) for item in results]
        except httpx.TimeoutException as exc:
            logger.error("ServiceNow API timeout during query: %s", exc)
            raise ServiceNowError("ServiceNow API timed out", status_code=504) from exc
        except httpx.HTTPStatusError as exc:
            logger.error("ServiceNow query HTTP error: %s", exc.response.status_code)
            raise ServiceNowError(
                f"ServiceNow API error: {exc.response.status_code}",
                status_code=exc.response.status_code,
            ) from exc
        except httpx.RequestError as exc:
            logger.error("ServiceNow query connection error: %s", exc)
            raise ServiceNowError(
                f"Failed to connect to ServiceNow: {exc}", status_code=502
            ) from exc
        finally:
            if should_close:
                await client.aclose()
