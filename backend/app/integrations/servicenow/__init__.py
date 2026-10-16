from app.core.config import get_settings
from app.core.logging import get_logger
from app.integrations.servicenow.client import ServiceNowProvider, ServiceNowError
from app.integrations.servicenow.mock import MockTicketingProvider
from app.integrations.servicenow.provider import TicketingProvider

logger = get_logger("ticketing_factory")

_singleton_provider: TicketingProvider | None = None


def get_ticketing_provider() -> TicketingProvider:
    """Return active TicketingProvider based on application settings."""
    global _singleton_provider
    if _singleton_provider is not None:
        return _singleton_provider

    cfg = get_settings()
    if cfg.is_servicenow_configured:
        logger.info(
            "Initializing real ServiceNowProvider for instance: %s",
            cfg.servicenow_instance_url,
        )
        _singleton_provider = ServiceNowProvider(
            instance_url=cfg.servicenow_instance_url or "",
            username=cfg.servicenow_username or "",
            password=cfg.servicenow_password or "",
            timeout_seconds=cfg.servicenow_timeout_seconds,
            caller_sys_id=cfg.servicenow_caller_sys_id,
            group_ids=cfg.servicenow_group_ids,
            fallback_group_sys_id=cfg.servicenow_fallback_group_sys_id,
        )
    else:
        logger.info(
            "ServiceNow not configured or mock requested; using MockTicketingProvider"
        )
        _singleton_provider = MockTicketingProvider()

    return _singleton_provider


def reset_ticketing_provider() -> None:
    """Reset singleton provider, useful in test fixtures."""
    global _singleton_provider
    _singleton_provider = None


__all__ = [
    "TicketingProvider",
    "ServiceNowProvider",
    "MockTicketingProvider",
    "ServiceNowError",
    "get_ticketing_provider",
    "reset_ticketing_provider",
]
