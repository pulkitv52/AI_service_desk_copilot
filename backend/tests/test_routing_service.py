import pytest

from app.models.chat import SupportIntent, TicketPriority
from app.models.ticket import TicketImpact, TicketUrgency
from app.services.routing_service import RoutingService


# Verified against all nine rows of the PDI Priority Data Lookup table.
@pytest.mark.parametrize(
    "impact,urgency,priority",
    [
        ("1", "1", "P1"),
        ("1", "2", "P2"),
        ("1", "3", "P3"),
        ("2", "1", "P2"),
        ("2", "2", "P3"),
        ("2", "3", "P4"),
        ("3", "1", "P3"),
        ("3", "2", "P4"),
        ("3", "3", "P5"),
    ],
)
def test_priority_matrix(impact: str, urgency: str, priority: str) -> None:
    assert RoutingService.calculate_priority(
        TicketImpact(impact), TicketUrgency(urgency)
    ) == TicketPriority(priority)


def test_assignment_groups() -> None:
    # SAP
    assert (
        RoutingService.determine_assignment_group("Cannot approve PO in SAP")
        == "SAP Support"
    )
    # Identity
    assert (
        RoutingService.determine_assignment_group("Forgot my domain password for SSPR")
        == "Identity & Access Support"
    )
    # Network
    assert (
        RoutingService.determine_assignment_group("GlobalProtect VPN tunnel dropped")
        == "Network Support"
    )
    # Collaboration
    assert (
        RoutingService.determine_assignment_group("Teams microphone not detecting")
        == "Collaboration Support"
    )
    # End User Computing
    assert (
        RoutingService.determine_assignment_group(
            "Need VS Code installed", intent=SupportIntent.SOFTWARE_REQUEST
        )
        == "End User Computing"
    )
    # Default fallback
    assert (
        RoutingService.determine_assignment_group("Something strange is happening")
        == "Service Desk L1"
    )
