from pathlib import Path
import pytest
from app.services.rag_service import RAGService


def test_parse_password_reset_doc() -> None:
    kb_path = (
        Path(__file__).resolve().parent.parent.parent
        / "knowledge-base"
        / "password-reset.md"
    )
    assert kb_path.exists(), f"File does not exist: {kb_path}"

    content = kb_path.read_text(encoding="utf-8")
    parsed = RAGService.parse_markdown_document(content, "password-reset.md")

    assert parsed["title"] == "Self-Service Password Reset Guide"
    assert parsed["source_id"] == "KB-SEC-001"
    assert parsed["category"] == "Identity and Access Management"
    assert len(parsed["sections"]) >= 4

    headings = [h for h, _ in parsed["sections"]]
    assert "Problem Description" in headings
    assert "Resolution Steps" in headings
    assert "Escalation Conditions" in headings


def test_parse_all_synthetic_docs() -> None:
    kb_dir = Path(__file__).resolve().parent.parent.parent / "knowledge-base"
    files = list(kb_dir.glob("*.md"))
    assert len(files) == 7

    for f in files:
        content = f.read_text(encoding="utf-8")
        parsed = RAGService.parse_markdown_document(content, f.name)
        assert parsed["title"]
        assert parsed["source_id"].startswith("KB-")
        assert parsed["category"]
        assert len(parsed["sections"]) >= 3
