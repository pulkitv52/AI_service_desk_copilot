from app.models.chat import SupportIntent, TicketPriority
from app.models.ticket import TicketUrgency, TicketImpact
from app.services.classification_service import ClassificationService


def test_classify_password_reset() -> None:
    classifier = ClassificationService()
    result = classifier.classify("I forgot my password. How can I reset it?")

    assert result.intent == SupportIntent.KNOWLEDGE_INQUIRY
    assert result.category == "identity"
    assert result.assignment_group == "Identity & Access Support"
    assert result.confidence >= 0.90


def test_classify_vpn_issue() -> None:
    classifier = ClassificationService()
    result = classifier.classify("My VPN is not connecting.")

    assert result.intent == SupportIntent.KNOWLEDGE_INQUIRY
    assert result.category == "network"
    assert result.application == "GlobalProtect"
    assert result.assignment_group == "Network Support"


def test_classify_software_installation() -> None:
    classifier = ClassificationService()
    result = classifier.classify("I need VS Code installed.")

    assert result.intent == SupportIntent.SOFTWARE_REQUEST
    assert result.category == "software"
    assert result.assignment_group == "End User Computing"


def test_classify_disk_space() -> None:
    classifier = ClassificationService()
    result = classifier.classify("My laptop says disk space is almost full.")

    assert result.intent == SupportIntent.DIAGNOSTIC_REMEDIATION
    assert result.category == "hardware"
    assert result.assignment_group == "End User Computing"


def test_classify_sap_urgent() -> None:
    classifier = ClassificationService()
    result = classifier.classify(
        "Urgent! SAP is not allowing me to approve purchase orders. Production down!"
    )

    assert result.intent == SupportIntent.APPLICATION_ISSUE
    assert result.application == "SAP"
    assert result.assignment_group == "SAP Support"
    assert result.urgency == TicketUrgency.HIGH
    assert result.impact == TicketImpact.HIGH
    assert result.priority == TicketPriority.P1
