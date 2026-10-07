from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class DeviceHealthStatus(str, Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


class RemediationTool(str, Enum):
    CLEAN_TEMP_FILES = "clean_temp_files"
    PURGE_DEVELOPER_CACHES = "purge_developer_caches"
    RESTART_VPN_SERVICE = "restart_vpn_service"
    CLEAR_TEAMS_CACHE = "clear_teams_cache"
    CHECK_DISK_SPACE = "check_disk_space"
    CHECK_NETWORK = "check_network"


class DeviceHealthResponse(BaseModel):
    """Synthetic Digital Employee Experience (DEX) device telemetry."""

    device_id: str
    hostname: str
    os: str
    cpu_usage: float = Field(ge=0.0, le=100.0)
    memory_usage: float = Field(ge=0.0, le=100.0)
    disk_free_gb: float = Field(ge=0.0)
    disk_total_gb: float = Field(default=256.0)
    teams_crashes_24h: int = Field(ge=0)
    network_latency_ms: float = Field(ge=0.0)
    vpn_connected: bool = True
    health_status: DeviceHealthStatus = DeviceHealthStatus.HEALTHY
    last_seen: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class DeviceSimulationRequest(BaseModel):
    """Payload to simulate or override device telemetry signals."""

    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    disk_free_gb: Optional[float] = None
    teams_crashes_24h: Optional[int] = None
    network_latency_ms: Optional[float] = None
    vpn_connected: Optional[bool] = None


class RemediationActionRequest(BaseModel):
    """Request to invoke an approved allow-listed diagnostic or remediation tool."""

    tool_name: RemediationTool
    dry_run: bool = False
    reason: str = Field(..., min_length=5, max_length=200)


class RemediationResultResponse(BaseModel):
    """Structured result of an executed remediation action."""

    action_id: str
    device_id: str
    tool_name: str
    status: str
    dry_run: bool
    before_state: dict[str, Any]
    after_state: dict[str, Any]
    output: str
    resolved: bool
    executed_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
