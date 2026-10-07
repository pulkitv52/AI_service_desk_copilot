from typing import Optional, Protocol, runtime_checkable
from app.models.device import DeviceHealthResponse, DeviceSimulationRequest


@runtime_checkable
class TelemetryProvider(Protocol):
    """Protocol for Digital Employee Experience (DEX) telemetry providers."""

    async def get_device_health(self, device_id: str) -> Optional[DeviceHealthResponse]:
        """Fetch endpoint telemetry metrics for a given device identifier."""
        ...

    async def update_device_telemetry(
        self, device_id: str, updates: DeviceSimulationRequest
    ) -> DeviceHealthResponse:
        """Simulate or update telemetry signals for testing."""
        ...
