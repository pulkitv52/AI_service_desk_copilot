from app.models.chat import SupportIntent, TicketPriority
from app.models.ticket import TicketImpact, TicketUrgency
from app.services.routing_service import RoutingService


def test_priority_matrix() -> None:
    # Critical P1
    assert (
        RoutingService.calculate_priority(TicketImpact.HIGH, TicketUrgency.HIGH)
        == TicketPriority.P1
    )
    # High P2
    assert (
        RoutingService.calculate_priority(TicketImpact.HIGH, TicketUrgency.MEDIUM)
        == TicketPriority.P2
    )
    assert (
        RoutingService.calculate_priority(TicketImpact.MEDIUM, TicketUrgency.HIGH)
        == TicketPriority.P2
    )
    # Medium P3
    assert (
        RoutingService.calculate_priority(TicketImpact.MEDIUM, TicketUrgency.MEDIUM)
        == TicketPriority.P3
    )
    assert (
        RoutingService.calculate_priority(TicketImpact.LOW, TicketUrgency.HIGH)
        == TicketPriority.P3
    )
    # Low P4
    assert (
        RoutingService.calculate_priority(TicketImpact.LOW, TicketUrgency.LOW)
        == TicketPriority.P4
    )


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
