from typing import Any
from fastapi import APIRouter, Depends
from app.core.config import Settings, get_settings

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check(settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    """Health check endpoint to verify backend operational status."""
    return {
        "status": "ok",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "servicenow_configured": settings.is_servicenow_configured,
    }
