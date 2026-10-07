from datetime import datetime, timezone
from typing import Optional
from app.core.logging import get_logger
from app.models.device import (
    DeviceHealthResponse,
    DeviceHealthStatus,
    DeviceSimulationRequest,
)

logger = get_logger("synthetic_dex")


class SyntheticDEXProvider:
    """Simulates endpoint signals provided by enterprise DEX platforms like Nexthink."""

    def __init__(self) -> None:
        self._devices: dict[str, DeviceHealthResponse] = {}
        self._init_default_devices()

    def _calculate_status(
        self, disk_free_gb: float, cpu_usage: float, latency: float, vpn: bool
    ) -> DeviceHealthStatus:
        if disk_free_gb < 10.0 or cpu_usage > 90.0 or latency > 250.0 or not vpn:
            return DeviceHealthStatus.CRITICAL
        elif disk_free_gb < 20.0 or cpu_usage > 75.0 or latency > 120.0:
            return DeviceHealthStatus.WARNING
        return DeviceHealthStatus.HEALTHY

    def _init_default_devices(self) -> None:
        now_str = datetime.now(timezone.utc).isoformat()
        # Primary test endpoint from AGENTS.md (UC-04: EMP-LT-104 with degraded disk)
        self._devices["EMP-LT-104"] = DeviceHealthResponse(
            device_id="EMP-LT-104",
            hostname="W11-CORP-104",
            os="Windows 11 Enterprise 23H2",
            cpu_usage=92.0,
            memory_usage=86.0,
            disk_free_gb=3.2,
            disk_total_gb=256.0,
            teams_crashes_24h=5,
            network_latency_ms=178.0,
            vpn_connected=True,
            health_status=DeviceHealthStatus.CRITICAL,
            last_seen=now_str,
        )

        self._devices["EMP-LT-200"] = DeviceHealthResponse(
            device_id="EMP-LT-200",
            hostname="MBP-CORP-200",
            os="macOS Sonoma 14.5",
            cpu_usage=24.0,
            memory_usage=45.0,
            disk_free_gb=110.0,
            disk_total_gb=512.0,
            teams_crashes_24h=0,
            network_latency_ms=18.0,
            vpn_connected=True,
            health_status=DeviceHealthStatus.HEALTHY,
            last_seen=now_str,
        )

    async def get_device_health(self, device_id: str) -> Optional[DeviceHealthResponse]:
        """Fetch endpoint telemetry metrics for device."""
        if device_id in self._devices:
            return self._devices[device_id]

        # Auto-create healthy device for unseen IDs
        now_str = datetime.now(timezone.utc).isoformat()
        dev = DeviceHealthResponse(
            device_id=device_id,
            hostname=f"HOST-{device_id}",
            os="Windows 11 Enterprise",
            cpu_usage=18.0,
            memory_usage=38.0,
            disk_free_gb=64.0,
            disk_total_gb=256.0,
            teams_crashes_24h=0,
            network_latency_ms=22.0,
            vpn_connected=True,
            health_status=DeviceHealthStatus.HEALTHY,
            last_seen=now_str,
        )
        self._devices[device_id] = dev
        return dev

    async def update_device_telemetry(
        self, device_id: str, updates: DeviceSimulationRequest
    ) -> DeviceHealthResponse:
        """Simulate change in telemetry signals."""
        current = await self.get_device_health(device_id)
        assert current is not None

        data = current.model_dump()
        if updates.cpu_usage is not None:
            data["cpu_usage"] = updates.cpu_usage
        if updates.memory_usage is not None:
            data["memory_usage"] = updates.memory_usage
        if updates.disk_free_gb is not None:
            data["disk_free_gb"] = updates.disk_free_gb
        if updates.teams_crashes_24h is not None:
            data["teams_crashes_24h"] = updates.teams_crashes_24h
        if updates.network_latency_ms is not None:
            data["network_latency_ms"] = updates.network_latency_ms
        if updates.vpn_connected is not None:
            data["vpn_connected"] = updates.vpn_connected

        # Recompute health status dynamically
        data["health_status"] = self._calculate_status(
            disk_free_gb=data["disk_free_gb"],
            cpu_usage=data["cpu_usage"],
            latency=data["network_latency_ms"],
            vpn=data["vpn_connected"],
        )
        data["last_seen"] = datetime.now(timezone.utc).isoformat()

        updated = DeviceHealthResponse(**data)
        self._devices[device_id] = updated
        logger.info(
            "Updated synthetic telemetry for device=%s status=%s",
            device_id,
            updated.health_status.value,
        )
        return updated
