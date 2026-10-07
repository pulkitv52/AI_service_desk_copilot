import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.integrations.telemetry import TelemetryProvider, get_telemetry_provider
from app.models.device import (
    DeviceHealthStatus,
    DeviceSimulationRequest,
    RemediationActionRequest,
    RemediationResultResponse,
    RemediationTool,
)
from app.models.knowledge import AuditLog
from app.tools.diagnostics import SystemDiagnosticTools
from app.tools.disk import DiskRemediationTools
from app.tools.network import NetworkRemediationTools

logger = get_logger("remediation_service")


class RemediationService:
    """Orchestrates allow-listed remediation tools, telemetry verification, and audit tracking."""

    def __init__(
        self,
        session: Optional[AsyncSession] = None,
        telemetry_provider: Optional[TelemetryProvider] = None,
    ) -> None:
        self.session = session
        self.telemetry = telemetry_provider or get_telemetry_provider()

    async def execute_remediation(
        self, device_id: str, request: RemediationActionRequest
    ) -> RemediationResultResponse:
        """Safely executes an allow-listed remediation tool against an endpoint device."""
        action_id = uuid.uuid4().hex
        before_health = await self.telemetry.get_device_health(device_id)
        if not before_health:
            raise ValueError(f"Device '{device_id}' not found")

        before_state = before_health.model_dump()
        tool = request.tool_name
        output_msg = ""
        freed_gb = 0.0

        logger.info(
            "Executing tool=%s for device=%s dry_run=%s reason='%s'",
            tool.value,
            device_id,
            request.dry_run,
            request.reason,
        )

        if tool == RemediationTool.CLEAN_TEMP_FILES:
            res = DiskRemediationTools.clean_temp_files(dry_run=request.dry_run)
            output_msg = res["message"]
            if not request.dry_run:
                freed_gb = res["freed_gb"]
                await self.telemetry.update_device_telemetry(
                    device_id,
                    DeviceSimulationRequest(
                        disk_free_gb=before_health.disk_free_gb + freed_gb
                    ),
                )

        elif tool == RemediationTool.PURGE_DEVELOPER_CACHES:
            res = DiskRemediationTools.purge_developer_caches(dry_run=request.dry_run)
            output_msg = res["message"]
            if not request.dry_run:
                freed_gb = res["freed_gb"]
                await self.telemetry.update_device_telemetry(
                    device_id,
                    DeviceSimulationRequest(
                        disk_free_gb=before_health.disk_free_gb + freed_gb
                    ),
                )

        elif tool == RemediationTool.RESTART_VPN_SERVICE:
            res = NetworkRemediationTools.restart_vpn_service(dry_run=request.dry_run)
            output_msg = res["message"]
            if not request.dry_run:
                await self.telemetry.update_device_telemetry(
                    device_id,
                    DeviceSimulationRequest(
                        vpn_connected=True,
                        network_latency_ms=18.0,
                    ),
                )

        elif tool == RemediationTool.CLEAR_TEAMS_CACHE:
            res = SystemDiagnosticTools.clear_teams_cache(dry_run=request.dry_run)
            output_msg = res["message"]
            if not request.dry_run:
                await self.telemetry.update_device_telemetry(
                    device_id,
                    DeviceSimulationRequest(teams_crashes_24h=0),
                )

        elif tool == RemediationTool.CHECK_NETWORK:
            res = NetworkRemediationTools.check_network()
            output_msg = res["message"]

        else:
            raise ValueError(f"Unknown remediation tool: {tool}")

        after_health = await self.telemetry.get_device_health(device_id)
        assert after_health is not None
        after_state = after_health.model_dump()

        resolved = after_health.health_status == DeviceHealthStatus.HEALTHY

        # Record audit log in database if session present
        if self.session is not None:
            try:
                audit = AuditLog(
                    session_id=device_id,
                    event_type="remediation_executed",
                    payload={
                        "action_id": action_id,
                        "tool_name": tool.value,
                        "dry_run": request.dry_run,
                        "before_status": before_health.health_status.value,
                        "after_status": after_health.health_status.value,
                        "resolved": resolved,
                    },
                )
                self.session.add(audit)
                await self.session.flush()
            except Exception as exc:
                logger.warning("Failed to record remediation audit log: %s", exc)

        return RemediationResultResponse(
            action_id=action_id,
            device_id=device_id,
            tool_name=tool.value,
            status="dry_run" if request.dry_run else "success",
            dry_run=request.dry_run,
            before_state=before_state,
            after_state=after_state,
            output=output_msg,
            resolved=resolved,
            executed_at=datetime.now(timezone.utc).isoformat(),
        )
