import pytest
from httpx import AsyncClient
from app.integrations.telemetry import reset_telemetry_provider
from app.models.device import DeviceHealthStatus, RemediationTool


@pytest.fixture(autouse=True)
def reset_telemetry() -> None:
    reset_telemetry_provider()
    yield
    reset_telemetry_provider()


@pytest.mark.asyncio
async def test_get_device_health(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/devices/EMP-LT-104/health")
    assert response.status_code == 200
    data = response.json()
    assert data["device_id"] == "EMP-LT-104"
    assert data["disk_free_gb"] == 3.2
    assert data["health_status"] == DeviceHealthStatus.CRITICAL.value


@pytest.mark.asyncio
async def test_simulate_device_telemetry(async_client: AsyncClient) -> None:
    sim_payload = {
        "cpu_usage": 45.0,
        "disk_free_gb": 85.0,
        "network_latency_ms": 25.0,
    }
    response = await async_client.post(
        "/api/devices/EMP-LT-104/simulate", json=sim_payload
    )
    assert response.status_code == 200
    data = response.json()
    assert data["cpu_usage"] == 45.0
    assert data["disk_free_gb"] == 85.0
    assert data["network_latency_ms"] == 25.0
    assert data["health_status"] == DeviceHealthStatus.HEALTHY.value


@pytest.mark.asyncio
async def test_remediate_disk_dry_run(async_client: AsyncClient) -> None:
    payload = {
        "tool_name": RemediationTool.CLEAN_TEMP_FILES.value,
        "dry_run": True,
        "reason": "Test dry run remediation",
    }
    response = await async_client.post(
        "/api/devices/EMP-LT-104/remediate", json=payload
    )
    assert response.status_code == 200
    data = response.json()
    assert data["dry_run"] is True
    assert data["status"] == "dry_run"
    assert "Dry-run simulation" in data["output"]

    # Verify state was not actually changed
    health_resp = await async_client.get("/api/devices/EMP-LT-104/health")
    assert health_resp.json()["disk_free_gb"] == 3.2


@pytest.mark.asyncio
async def test_remediate_disk_real_execution(async_client: AsyncClient) -> None:
    # Set non-storage metrics to healthy baseline first
    await async_client.post(
        "/api/devices/EMP-LT-104/simulate",
        json={"cpu_usage": 32.0, "network_latency_ms": 24.0},
    )

    # Step 1: Clean temp files (adds 14.8 GB -> 18.0 GB)
    payload1 = {
        "tool_name": RemediationTool.CLEAN_TEMP_FILES.value,
        "dry_run": False,
        "reason": "Clean temporary storage",
    }
    resp1 = await async_client.post("/api/devices/EMP-LT-104/remediate", json=payload1)
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["before_state"]["disk_free_gb"] == 3.2
    assert data1["after_state"]["disk_free_gb"] == 18.0

    # Step 2: Purge developer caches (adds 9.2 GB -> 27.2 GB > 20 GB -> HEALTHY)
    payload2 = {
        "tool_name": RemediationTool.PURGE_DEVELOPER_CACHES.value,
        "dry_run": False,
        "reason": "Purge npm, pip, docker build caches",
    }
    resp2 = await async_client.post("/api/devices/EMP-LT-104/remediate", json=payload2)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["after_state"]["disk_free_gb"] == 27.2
    assert data2["resolved"] is True
    assert data2["after_state"]["health_status"] == DeviceHealthStatus.HEALTHY.value
