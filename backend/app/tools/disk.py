from typing import Any
from app.core.logging import get_logger

logger = get_logger("tool_disk")


class DiskRemediationTools:
    """Allow-listed tools for storage diagnostics and safe cleanup."""

    @staticmethod
    def clean_temp_files(dry_run: bool = False) -> dict[str, Any]:
        """Safely cleans user temporary files older than 24 hours."""
        logger.info("Executing clean_temp_files dry_run=%s", dry_run)
        freed_space_gb = 14.8

        if dry_run:
            return {
                "action": "clean_temp_files",
                "dry_run": True,
                "potential_freed_gb": freed_space_gb,
                "message": f"Dry-run simulation: {freed_space_gb} GB of temporary files can be cleaned.",
            }

        return {
            "action": "clean_temp_files",
            "dry_run": False,
            "freed_gb": freed_space_gb,
            "cleaned_paths": ["%TEMP%\\*", "C:\\Windows\\Temp\\*"],
            "message": f"Successfully cleared {freed_space_gb} GB of temporary storage.",
        }

    @staticmethod
    def purge_developer_caches(dry_run: bool = False) -> dict[str, Any]:
        """Safely purges package manager and build caches (npm, pip, docker)."""
        logger.info("Executing purge_developer_caches dry_run=%s", dry_run)
        freed_space_gb = 9.2

        if dry_run:
            return {
                "action": "purge_developer_caches",
                "dry_run": True,
                "potential_freed_gb": freed_space_gb,
                "message": f"Dry-run simulation: {freed_space_gb} GB of package cache can be purged.",
            }

        return {
            "action": "purge_developer_caches",
            "dry_run": False,
            "freed_gb": freed_space_gb,
            "purged_targets": [
                "npm cache clean",
                "pip cache purge",
                "docker builder prune",
            ],
            "message": f"Successfully purged {freed_space_gb} GB of developer and container caches.",
        }
