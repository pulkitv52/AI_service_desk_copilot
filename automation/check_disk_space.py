#!/usr/bin/env python3
import shutil
import sys
from typing import Dict, Any


def check_disk_space(path: str = "/") -> Dict[str, Any]:
    """Inspect disk space capacity for specified filesystem mount path."""
    total, used, free = shutil.disk_usage(path)
    total_gb = total / (1024**3)
    free_gb = free / (1024**3)
    percent_free = (free / total) * 100

    status = "healthy"
    if free_gb < 10.0 or percent_free < 10.0:
        status = "critical"
    elif free_gb < 20.0 or percent_free < 20.0:
        status = "warning"

    return {
        "path": path,
        "total_gb": round(total_gb, 2),
        "free_gb": round(free_gb, 2),
        "percent_free": round(percent_free, 2),
        "status": status,
    }


if __name__ == "__main__":
    result = check_disk_space()
    print(f"Disk check: {result['free_gb']} GB free ({result['percent_free']}%) - Status: {result['status']}")
    sys.exit(0 if result["status"] == "healthy" else 1)
