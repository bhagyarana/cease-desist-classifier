import os
import pytest

from agents.ingestion import IngestionAgent


def test_ingestion_returns_failed_for_missing_pdf(tmp_path):
    config = {"classifier": {"model": "mock"}}
    agent = IngestionAgent(config)
    missing_path = tmp_path / "missing.pdf"
    result = agent.run({"pdf_path": str(missing_path)})

    assert result["status"] == "partial"
    assert result["extraction_status"] == "failed"
    assert result["classification"]["label"] == "UNCERTAIN"


@pytest.mark.skipif(
    not os.getenv("CI") and not os.getenv("FITZ_AVAILABLE"),
    reason="Optional PDF extraction dependencies are not installed",
)
def test_ingestion_reads_simple_pdf(tmp_path):
    try:
        import fitz
    except ImportError:
        pytest.skip("PyMuPDF not installed")

    pdf_path = tmp_path / "simple.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "I hereby request you cease all communications immediately.")
    doc.save(str(pdf_path))
    doc.close()

    config = {"classifier": {"model": "mock"}}
    agent = IngestionAgent(config)
    result = agent.run({"pdf_path": str(pdf_path)})

    assert result["status"] == "success"
    assert result["extraction_status"] == "success"
    assert "cease" in result["text"].lower()
    assert result["classification"]["label"] in {"CEASE", "UNCERTAIN"}
