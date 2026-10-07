#!/usr/bin/env python3
import socket
import time
from typing import Dict, Any


def check_network(host: str = "8.8.8.8", port: int = 53, timeout: float = 3.0) -> Dict[str, Any]:
    """Test network socket reachability and measure connection latency."""
    start = time.perf_counter()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.close()
        latency_ms = (time.perf_counter() - start) * 1000.0
        return {
            "target": f"{host}:{port}",
            "reachable": True,
            "latency_ms": round(latency_ms, 2),
            "status": "healthy" if latency_ms < 150.0 else "degraded",
        }
    except Exception as exc:
        return {
            "target": f"{host}:{port}",
            "reachable": False,
            "error": str(exc),
            "status": "critical",
        }


if __name__ == "__main__":
    result = check_network()
    print(f"Network check: {result['status']} (Latency: {result.get('latency_ms', 'N/A')} ms)")
