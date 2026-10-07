#!/usr/bin/env python3
import platform
import shutil
import sys
from typing import Dict, Any


def collect_system_health() -> Dict[str, Any]:
    """Collect basic endpoint operating system and filesystem diagnostics."""
    total, used, free = shutil.disk_usage("/")
    return {
        "os": platform.platform(),
        "python_version": platform.python_version(),
        "machine": platform.machine(),
        "disk_free_gb": round(free / (1024**3), 2),
        "disk_total_gb": round(total / (1024**3), 2),
    }


if __name__ == "__main__":
    health = collect_system_health()
    for k, v in health.items():
        print(f"{k}: {v}")
