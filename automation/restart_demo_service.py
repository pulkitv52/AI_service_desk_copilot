#!/usr/bin/env python3
import sys
from typing import Dict, Any


def restart_demo_service(service_name: str = "demo-print-spooler", dry_run: bool = False) -> Dict[str, Any]:
    """Demonstration remediation tool: safe restart of simulated background service."""
    if dry_run:
        return {
            "action": "restart_demo_service",
            "service": service_name,
            "dry_run": True,
            "message": f"Simulation: Service '{service_name}' would be restarted.",
        }

    return {
        "action": "restart_demo_service",
        "service": service_name,
        "dry_run": False,
        "status": "restarted",
        "message": f"Service '{service_name}' successfully stopped and restarted.",
    }


if __name__ == "__main__":
    is_dry = "--dry-run" in sys.argv
    res = restart_demo_service(dry_run=is_dry)
    print(res["message"])
