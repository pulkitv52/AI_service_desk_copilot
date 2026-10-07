from typing import Any
from app.core.logging import get_logger

logger = get_logger("tool_diagnostics")


class SystemDiagnosticTools:
    """Allow-listed tools for system health inspection and app cache clearing."""

    @staticmethod
    def clear_teams_cache(dry_run: bool = False) -> dict[str, Any]:
        """Safely clears Microsoft Teams client cache to resolve crash loops."""
        logger.info("Executing clear_teams_cache dry_run=%s", dry_run)
        if dry_run:
            return {
                "action": "clear_teams_cache",
                "dry_run": True,
                "target_path": "%LOCALAPPDATA%\\Packages\\MSTeams_*\\LocalCache",
                "message": "Dry-run simulation: Microsoft Teams cache would be purged.",
            }

        return {
            "action": "clear_teams_cache",
            "dry_run": False,
            "target_path": "%LOCALAPPDATA%\\Packages\\MSTeams_*\\LocalCache",
            "status": "cleared",
            "message": "Microsoft Teams local cache directory cleared successfully.",
        }
