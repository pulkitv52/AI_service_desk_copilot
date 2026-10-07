from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.logging import get_logger
from app.integrations.telemetry import TelemetryProvider, get_telemetry_provider
from app.models.device import (
    DeviceHealthResponse,
    DeviceSimulationRequest,
    RemediationActionRequest,
    RemediationResultResponse,
)
from app.services.remediation_service import RemediationService

logger = get_logger("routes_devices")
router = APIRouter(prefix="/api/devices", tags=["Devices & DEX"])


@router.get(
    "/{device_id}/health",
    response_model=DeviceHealthResponse,
    summary="Get endpoint experience signals (DEX telemetry)",
)
async def get_device_health(
    device_id: str,
    telemetry: TelemetryProvider = Depends(get_telemetry_provider),
) -> DeviceHealthResponse:
    """Retrieve simulated endpoint DEX telemetry for a specific employee device."""
    device = await telemetry.get_device_health(device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device '{device_id}' not found",
        )
    return device


@router.post(
    "/{device_id}/simulate",
    response_model=DeviceHealthResponse,
    summary="Simulate or alter device telemetry signals",
)
async def simulate_device_health(
    device_id: str,
    request: DeviceSimulationRequest,
    telemetry: TelemetryProvider = Depends(get_telemetry_provider),
) -> DeviceHealthResponse:
    """Simulate changes in device metrics such as degraded disk space or VPN failure."""
    return await telemetry.update_device_telemetry(device_id, request)


@router.post(
    "/{device_id}/remediate",
    response_model=RemediationResultResponse,
    summary="Execute an approved self-healing remediation tool",
)
async def remediate_device(
    device_id: str,
    request: RemediationActionRequest,
    session: AsyncSession = Depends(get_db_session),
    telemetry: TelemetryProvider = Depends(get_telemetry_provider),
) -> RemediationResultResponse:
    """Safely execute an allow-listed remediation tool with before/after verification."""
    try:
        service = RemediationService(session=session, telemetry_provider=telemetry)
        return await service.execute_remediation(device_id, request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Remediation execution failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Remediation action failed: {exc}",
        ) from exc
