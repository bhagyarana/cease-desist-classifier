import os
import pytest
import fitz
from agents.workflow import CeaseGuardWorkflow
from tools.db import initialize_sqlite


def test_workflow_cease_happy_path(tmp_path):
    # Setup mock databases and config
    db_path = tmp_path / "test_workflow_happy.db"
    initialize_sqlite(str(db_path))
    
    config = {
        "classifier": {
            "model": "mock",
            "confidence_threshold_uncertain": 0.75,
            "confidence_threshold_edge_case": 0.60
        },
        "judge": {
            "enabled": False
        },
        "datastore": {
            "type": "sqlite",
            "sqlite_path": str(db_path)
        },
        "files": {
            "audit_path": str(tmp_path / "audit.jsonl"),
            "archive_path": str(tmp_path / "archive.jsonl"),
            "deferred_path": str(tmp_path / "deferred.jsonl")
        }
    }
    
    # Create valid simple PDF containing cease language
    pdf_path = str(tmp_path / "happy_cease.pdf")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "I hereby request you cease all communications immediately.")
    doc.save(pdf_path)
    doc.close()

    workflow = CeaseGuardWorkflow(config)
    
    state = {
        "pdf_path": pdf_path,
        "filename": "happy_cease.pdf",
    }
        
    final_state = workflow.run(state)
    
    assert final_state["current_stage"] == "COMPLETED"
    assert "DATASTORE" in final_state["trace"]
    assert final_state["classification"]["label"] == "CEASE"
    assert final_state["route_result"]["status"] == "written"


def test_workflow_escalates_and_resumes(tmp_path):
    db_path = tmp_path / "test_workflow_escalate.db"
    initialize_sqlite(str(db_path))
    
    config = {
        "classifier": {
            "model": "mock",
            "confidence_threshold_uncertain": 0.75,
            "confidence_threshold_edge_case": 0.60
        },
        "judge": {
            "enabled": False
        },
        "datastore": {
            "type": "sqlite",
            "sqlite_path": str(db_path)
        },
        "files": {
            "audit_path": str(tmp_path / "audit.jsonl"),
            "archive_path": str(tmp_path / "archive.jsonl"),
            "deferred_path": str(tmp_path / "deferred.jsonl")
        }
    }
    
    # Create valid simple PDF containing ambiguous language
    pdf_path = str(tmp_path / "ambiguous.pdf")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Please review this request and advise what to do next.")
    doc.save(pdf_path)
    doc.close()
        
    workflow = CeaseGuardWorkflow(config)
    
    # 1. First run: should escalate and pause
    state = {
        "pdf_path": pdf_path,
        "filename": "ambiguous.pdf"
    }
    
    paused_state = workflow.run(state)
    
    assert paused_state["current_stage"] == "ESCALATED"
    assert "ESCALATED_PAUSED" in paused_state["trace"]
    assert paused_state["classification"]["label"] == "UNCERTAIN"
    assert paused_state["route_result"]["status"] == "needs_review"
    
    # 2. Second run: simulate operator decision CEASE
    paused_state["human_decision"] = {
        "decision": "CEASE",
        "decided_at": "2025-01-15T12:00:00Z",
        "operator_id": "test-admin"
    }
    paused_state["current_stage"] = "ROUTE"  # Resume at routing node
    
    resumed_state = workflow.run(paused_state)
    
    assert resumed_state["current_stage"] == "COMPLETED"
    assert "DATASTORE" in resumed_state["trace"]
    assert resumed_state["route_result"]["status"] == "written"
