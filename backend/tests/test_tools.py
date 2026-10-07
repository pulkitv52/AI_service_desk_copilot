from app.tools.diagnostics import SystemDiagnosticTools
from app.tools.disk import DiskRemediationTools
from app.tools.network import NetworkRemediationTools


def test_disk_tools_dry_run_and_execution() -> None:
    dry = DiskRemediationTools.clean_temp_files(dry_run=True)
    assert dry["dry_run"] is True
    assert "Dry-run simulation" in dry["message"]

    real = DiskRemediationTools.clean_temp_files(dry_run=False)
    assert real["dry_run"] is False
    assert real["freed_gb"] > 0.0

    purge = DiskRemediationTools.purge_developer_caches(dry_run=False)
    assert purge["freed_gb"] > 0.0


def test_network_tools() -> None:
    net = NetworkRemediationTools.check_network()
    assert net["status"] == "healthy"
    assert net["ping_gateway_ms"] > 0.0

    vpn_restart = NetworkRemediationTools.restart_vpn_service(dry_run=False)
    assert vpn_restart["status"] == "restarted"


def test_diagnostic_tools() -> None:
    teams = SystemDiagnosticTools.clear_teams_cache(dry_run=False)
    assert teams["status"] == "cleared"
