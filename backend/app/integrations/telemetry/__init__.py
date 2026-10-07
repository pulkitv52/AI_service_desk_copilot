from app.integrations.telemetry.base import TelemetryProvider
from app.integrations.telemetry.synthetic import SyntheticDEXProvider

_singleton_telemetry_provider: TelemetryProvider | None = None


def get_telemetry_provider() -> TelemetryProvider:
    """Return active TelemetryProvider instance."""
    global _singleton_telemetry_provider
    if _singleton_telemetry_provider is None:
        _singleton_telemetry_provider = SyntheticDEXProvider()
    return _singleton_telemetry_provider


def reset_telemetry_provider() -> None:
    """Reset singleton telemetry provider for tests."""
    global _singleton_telemetry_provider
    _singleton_telemetry_provider = None


__all__ = [
    "TelemetryProvider",
    "SyntheticDEXProvider",
    "get_telemetry_provider",
    "reset_telemetry_provider",
]
