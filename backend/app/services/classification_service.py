import re
from typing import Optional
from app.core.logging import get_logger
from app.models.chat import IntentClassification, SupportIntent
from app.models.ticket import TicketUrgency, TicketImpact
from app.services.routing_service import RoutingService

logger = get_logger("classification_service")


class ClassificationService:
    """Classifies user support requests and extracts ITSM metadata."""

    def __init__(self) -> None:
        pass

    def classify(self, message: str) -> IntentClassification:
        """Classify message intent, category, application, urgency, impact, and assignment group."""
        text = message.strip()
        lowered = text.lower()

        intent = SupportIntent.KNOWLEDGE_INQUIRY
        category = "inquiry"
        subcategory: Optional[str] = None
        application: Optional[str] = None
        urgency = TicketUrgency.LOW
        impact = TicketImpact.LOW
        confidence = 0.85
        reasoning = "Standard IT support inquiry"

        # Urgency & Impact detection
        if any(
            w in lowered
            for w in [
                "urgent",
                "emergency",
                "immediately",
                "production down",
                "critical",
                "blocker",
            ]
        ):
            urgency = TicketUrgency.HIGH
            impact = TicketImpact.HIGH
            confidence = 0.95
        elif any(
            w in lowered for w in ["important", "asap", "can't work", "cannot work"]
        ):
            urgency = TicketUrgency.MEDIUM
            impact = TicketImpact.MEDIUM

        # Software Installation Requests (UC-03)
        if any(
            pattern in lowered
            for pattern in [
                "install",
                "installation",
                "need vs code",
                "download software",
                "request software",
                "license for",
            ]
        ):
            intent = SupportIntent.SOFTWARE_REQUEST
            category = "software"
            subcategory = "installation_request"
            confidence = 0.92
            reasoning = "Software install or package request detected"
            if "vs code" in lowered or "vscode" in lowered:
                application = "Visual Studio Code"
            elif "docker" in lowered:
                application = "Docker Desktop"

        # Enterprise Application Issues (UC-05: SAP, Fiori)
        elif any(
            kw in lowered
            for kw in [
                "sap",
                "fiori",
                "purchase order",
                "po approval",
                "me28",
                "me29n",
                "su53",
            ]
        ):
            intent = SupportIntent.APPLICATION_ISSUE
            category = "software"
            subcategory = "enterprise_application"
            application = "SAP"
            confidence = 0.94
            reasoning = "SAP enterprise application issue detected"

        # Diagnostic & Disk Remediation (UC-04)
        elif any(
            kw in lowered
            for kw in [
                "disk space",
                "low disk",
                "disk full",
                "storage full",
                "clean disk",
            ]
        ):
            intent = SupportIntent.DIAGNOSTIC_REMEDIATION
            category = "hardware"
            subcategory = "endpoint_storage"
            confidence = 0.93
            reasoning = "Endpoint storage diagnostic detected"

        # VPN & Network Connectivity (UC-02)
        elif any(
            kw in lowered
            for kw in ["vpn", "globalprotect", "cannot connect to network", "gateway"]
        ):
            intent = SupportIntent.KNOWLEDGE_INQUIRY
            category = "network"
            subcategory = "vpn"
            application = "GlobalProtect"
            confidence = 0.91
            reasoning = "VPN network connectivity issue detected"

        # Password Reset (UC-01)
        elif any(
            kw in lowered
            for kw in ["password", "forgot password", "reset password", "locked out"]
        ):
            intent = SupportIntent.KNOWLEDGE_INQUIRY
            category = "identity"
            subcategory = "authentication"
            application = "Active Directory"
            confidence = 0.95
            reasoning = "Authentication and password reset inquiry detected"

        # Collaboration (Outlook / Teams)
        elif any(kw in lowered for kw in ["outlook", "teams", "mailbox", "meeting"]):
            intent = SupportIntent.KNOWLEDGE_INQUIRY
            category = "collaboration"
            subcategory = "email" if "outlook" in lowered else "messaging"
            application = "Outlook" if "outlook" in lowered else "Teams"
            confidence = 0.90
            reasoning = "Collaboration application troubleshooting detected"

        # General Incident Fallback
        elif any(
            kw in lowered
            for kw in ["broken", "crash", "error", "failing", "not working", "ticket"]
        ):
            intent = SupportIntent.GENERAL_INCIDENT
            category = "incident"
            confidence = 0.75
            reasoning = "Generic technical incident detected"

        # Compute deterministic priority and assignment group
        priority = RoutingService.calculate_priority(impact=impact, urgency=urgency)
        assignment_group = RoutingService.determine_assignment_group(
            text=text,
            intent=intent,
            application=application,
        )

        logger.info(
            "Classified request intent=%s app=%s priority=%s group=%s",
            intent.value,
            application,
            priority.value,
            assignment_group,
        )

        return IntentClassification(
            intent=intent,
            category=category,
            subcategory=subcategory,
            application=application,
            urgency=urgency,
            impact=impact,
            priority=priority,
            assignment_group=assignment_group,
            confidence=confidence,
            reasoning=reasoning,
        )
