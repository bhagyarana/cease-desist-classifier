import json
from pathlib import Path

from agents.audit import AuditAgent


def test_audit_writes_valid_jsonl(tmp_path):
    audit_path = tmp_path / "audit.jsonl"
    config = {"files": {"audit_path": str(audit_path)}}
    audit = AuditAgent(config)
    audit.log({
        "document_id": "abc-123",
        "filename": "test.pdf",
        "stage": "RECEIVED",
        "classification": "UNCERTAIN",
        "confidence": 0.0,
        "citation": "",
        "language": "en",
        "edge_case_flag": False,
        "agent_trace": ["ingestion"],
        "human_override": None,
        "routing_destination": None,
        "error": None,
        "processing_time_ms": 0,
        "metadata": {},
    })

    assert audit_path.exists()
    lines = audit_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["document_id"] == "abc-123"
    assert entry["stage"] == "RECEIVED"
    assert entry["classification"] == "UNCERTAIN"
