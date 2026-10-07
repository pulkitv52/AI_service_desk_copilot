#!/usr/bin/env python3
import sys
from typing import Dict, Any


def clear_demo_cache(dry_run: bool = False) -> Dict[str, Any]:
    """Demonstration remediation tool: safe cleanup of simulated application cache."""
    freed_mb = 1250.0
    if dry_run:
        return {
            "action": "clear_demo_cache",
            "dry_run": True,
            "potential_freed_mb": freed_mb,
            "message": f"Simulation: {freed_mb} MB of application cache would be safely cleared.",
        }

    return {
        "action": "clear_demo_cache",
        "dry_run": False,
        "freed_mb": freed_mb,
        "message": f"Successfully purged {freed_mb} MB of temporary application cache.",
    }


if __name__ == "__main__":
    is_dry = "--dry-run" in sys.argv
    res = clear_demo_cache(dry_run=is_dry)
    print(res["message"])
