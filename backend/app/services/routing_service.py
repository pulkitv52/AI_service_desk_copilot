from typing import Optional
from app.core.logging import get_logger
from app.models.chat import SupportIntent, TicketPriority
from app.models.ticket import TicketUrgency, TicketImpact

logger = get_logger("routing_service")


class RoutingService:
    """Deterministic routing and ServiceNow priority calculation engine."""

    # PDI Priority Data Lookup (dl_u_priority): (Impact, Urgency) -> Priority.
    PRIORITY_MATRIX: dict[tuple[str, str], TicketPriority] = {
        ("1", "1"): TicketPriority.P1,
        ("1", "2"): TicketPriority.P2,
        ("2", "1"): TicketPriority.P2,
        ("1", "3"): TicketPriority.P3,
        ("2", "2"): TicketPriority.P3,
        ("3", "1"): TicketPriority.P3,
        ("2", "3"): TicketPriority.P4,
        ("3", "2"): TicketPriority.P4,
        ("3", "3"): TicketPriority.P5,
    }

    ASSIGNMENT_RULES: list[tuple[set[str], str]] = [
        (
            {"sap", "purchase order", "fiori", "me28", "me29n", "su53"},
            "SAP Support",
        ),
        (
            {
                "password",
                "sspr",
                "active directory",
                "mfa",
                "authenticator",
                "locked out",
                "unlock",
            },
            "Identity & Access Support",
        ),
        (
            {
                "vpn",
                "globalprotect",
                "gateway",
                "wifi",
                "dns",
                "network",
                "firewall",
            },
            "Network Support",
        ),
        (
            {
                "outlook",
                "teams",
                "exchange",
                "mailbox",
                "calendar",
                "meeting",
                "ost",
            },
            "Collaboration Support",
        ),
        (
            {
                "install",
                "software",
                "company portal",
                "license",
                "disk",
                "storage",
                "laptop",
            },
            "End User Computing",
        ),
    ]

    DEFAULT_ASSIGNMENT_GROUP = "Service Desk L1"

    @classmethod
    def calculate_priority(
        cls, impact: TicketImpact, urgency: TicketUrgency
    ) -> TicketPriority:
        """Compute priority using the verified PDI impact/urgency matrix."""
        key = (impact.value, urgency.value)
        priority = cls.PRIORITY_MATRIX[key]
        logger.debug(
            "Priority computed impact=%s urgency=%s -> %s",
            impact.value,
            urgency.value,
            priority.value,
        )
        return priority

    @classmethod
    def determine_assignment_group(
        cls,
        text: str,
        intent: Optional[SupportIntent] = None,
        application: Optional[str] = None,
    ) -> str:
        """Determine ticket assignment group using deterministic precedence."""
        lowered = text.lower()

        # Check explicit application first
        if application:
            app_lower = application.lower()
            if "sap" in app_lower:
                return "SAP Support"
            elif any(k in app_lower for k in ["outlook", "teams"]):
                return "Collaboration Support"
            elif "globalprotect" in app_lower or "vpn" in app_lower:
                return "Network Support"

        # Check intent-specific shortcuts
        if intent == SupportIntent.SOFTWARE_REQUEST:
            return "End User Computing"

        # Check keyword rules with word boundary matching
        import re

        for keywords, group in cls.ASSIGNMENT_RULES:
            for k in keywords:
                pattern = rf"\b{re.escape(k)}\b"
                if re.search(pattern, lowered):
                    return group

        return cls.DEFAULT_ASSIGNMENT_GROUP
