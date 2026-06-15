import os
import uuid
import time
import json
from datetime import datetime, timezone
from typing import Dict, Optional

from tools.db import get_connection, DatabaseIntegrityError
from agents.audit import AuditAgent
from agents.ingestion import IngestionAgent
from agents.classifier import ClassifierAgent
from agents.datastore import DatastoreAgent
from agents.archive import ArchiveAgent
from agents.escalation import EscalationAgent
from agents.judge import JudgeAgent


def iso_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class CeaseGuardWorkflow:
    def __init__(self, config: dict):
        self.config = config
        self.audit = AuditAgent(config)
        self.ingestion = IngestionAgent(config)
        self.classifier = ClassifierAgent(config)
        self.judge = JudgeAgent(config)
        self.datastore = DatastoreAgent(config)
        self.archive = ArchiveAgent(config)
        self.escalation = EscalationAgent(config)

    def run(self, state: dict) -> dict:
        """
        Runs the stateful workflow on the document ingestion state.
        The state dict template:
        {
            "document_id": str (optional),
            "pdf_path": str,
            "filename": str (optional),
            "human_decision": dict (optional),
            "current_stage": str,
            "trace": list
        }
        """
        # Ensure document ID is present
        if not state.get("document_id"):
            state["document_id"] = str(uuid.uuid4())
        
        if not state.get("filename"):
            state["filename"] = os.path.basename(state["pdf_path"])

        state.setdefault("trace", [])
        state.setdefault("current_stage", "INGEST")
        
        start_time = time.time()

        try:
            # 1. INGEST STATE
            if state["current_stage"] == "INGEST":
                ingest_res = self.ingestion.run({
                    "pdf_path": state["pdf_path"],
                    "filename": state["filename"]
                })
                state["text"] = ingest_res.get("text", "")
                state["language"] = ingest_res.get("language", {"language": "unknown", "confidence": 0.0})
                state["extraction_status"] = ingest_res.get("extraction_status", "failed")
                
                # Check for unreadable text
                if not state["text"].strip():
                    state["classification"] = {
                        "label": "UNCERTAIN",
                        "confidence": 0.0,
                        "citation": "",
                        "reasoning": "PDF text extraction returned empty string.",
                        "edge_case_flag": True,
                        "model": "heuristic",
                        "prompt_version": "v1.0.0"
                    }
                    state["current_stage"] = "ROUTE"
                else:
                    state["current_stage"] = "CLASSIFY"
                
                state["trace"].append("INGEST")
                
                # Log audit stage RECEIVED
                self.audit.log(self._build_received_audit(state, start_time))

            # 2. CLASSIFY STATE
            if state["current_stage"] == "CLASSIFY":
                class_res = self.classifier.run({
                    "text": state["text"],
                    "language": state["language"],
                    "filename": state["filename"]
                })
                state["classification"] = class_res
                state["trace"].append("CLASSIFY")
                state["current_stage"] = "JUDGE"

            # 3. JUDGE STATE
            if state["current_stage"] == "JUDGE":
                label = state["classification"]["label"]
                confidence = state["classification"]["confidence"]
                edge_case = state["classification"]["edge_case_flag"]
                
                judge_enabled = self.config.get("judge", {}).get("enabled", True)
                always_on_uncertain = self.config.get("judge", {}).get("always_on_uncertain", True)
                always_on_edge_cases = self.config.get("judge", {}).get("always_on_edge_cases", True)
                sample_rate = self.config.get("judge", {}).get("sample_rate", 0.10)
                
                should_judge = False
                if judge_enabled:
                    if label == "UNCERTAIN" and always_on_uncertain:
                        should_judge = True
                    elif edge_case and always_on_edge_cases:
                        should_judge = True
                    else:
                        # Random sample check
                        import random
                        should_judge = random.random() < sample_rate

                if should_judge:
                    judge_res = self.judge.run(state["classification"], state["text"])
                    state["judge_result"] = judge_res
                    state["trace"].append("JUDGE")
                    
                    # If judge disagrees or suggests correction, override classification label
                    if not judge_res.get("judge_agrees") and judge_res.get("correction"):
                        corr = judge_res["correction"]
                        state["classification"]["original_label"] = state["classification"]["label"]
                        state["classification"]["label"] = corr.get("new_label", "UNCERTAIN")
                        state["classification"]["reasoning"] = (
                            state["classification"]["reasoning"] + 
                            f" [Judge override: {corr.get('reason')}]"
                        )
                        state["classification"]["edge_case_flag"] = True

                state["current_stage"] = "ROUTE"

            # 4. ROUTE STATE
            if state["current_stage"] == "ROUTE":
                # Check if human decision is already provided
                human_decision = state.get("human_decision")
                
                label = state["classification"]["label"]
                confidence = state["classification"]["confidence"]
                edge_case = state["classification"]["edge_case_flag"]
                threshold = self.config.get("classifier", {}).get("confidence_threshold_uncertain", 0.75)
                
                needs_escalation = (
                    label == "UNCERTAIN" or 
                    confidence < threshold or 
                    edge_case
                )
                
                # If needs human escalation and no operator choice is supplied yet, pause
                if needs_escalation and not human_decision:
                    state["route_result"] = {
                        "status": "needs_review",
                        "review_state": "pending_human",
                        "processing_time_ms": int((time.time() - start_time) * 1000)
                    }
                    state["current_stage"] = "ESCALATED"
                    state["trace"].append("ESCALATED_PAUSED")
                    
                    # Log intermediate routing state to audit
                    self.audit.log(self._build_routed_audit(state, start_time))
                    return state

                # Determine final routing action based on decision
                action_label = human_decision["decision"] if human_decision else label
                state["agent_trace"] = list(state["trace"])
                
                if action_label == "DEFER":
                    # Deferred request logic
                    self.escalation._write_deferred(
                        {
                            "document_id": state["document_id"],
                            "filename": state["filename"],
                            "pdf_path": state["pdf_path"],
                            "classification": state["classification"],
                            "language": state["language"]
                        },
                        human_decision
                    )
                    state["route_result"] = {
                        "status": "deferred",
                        "deferred_at": human_decision.get("decided_at", iso_timestamp())
                    }
                    state["trace"].append("DEFERRED")
                elif action_label == "CEASE":
                    # Datastore routing logic
                    db_classification = dict(state["classification"])
                    db_classification["label"] = action_label
                    db_payload = {
                        "document_id": state["document_id"],
                        "filename": state["filename"],
                        "processing_start": state.get("processing_start", iso_timestamp()),
                        "processing_end": iso_timestamp(),
                        "classification": db_classification,
                        "language": state["language"],
                        "processing_time_ms": int((time.time() - start_time) * 1000),
                    }
                    if human_decision:
                        db_payload["human_decision"] = human_decision
                    db_res = self.datastore.run(db_payload)
                    
                    # Index document in vector store for similarity search
                    try:
                        from tools.rag_service import RAGService
                        RAGService(self.config).index_document(state["document_id"], state.get("text", "")[:4000])
                    except Exception:
                        pass
                        
                    state["route_result"] = db_res
                    state["trace"].append("DATASTORE")
                else: # IRRELEVANT
                    # Archive routing logic
                    archive_classification = dict(state["classification"])
                    archive_classification["label"] = action_label
                    archive_payload = {
                        "document_id": state["document_id"],
                        "filename": state["filename"],
                        "processing_start": state.get("processing_start", iso_timestamp()),
                        "processing_end": iso_timestamp(),
                        "classification": archive_classification,
                        "language": state["language"],
                        "processing_time_ms": int((time.time() - start_time) * 1000)
                    }
                    archive_res = self.archive.run(archive_payload)
                    state["route_result"] = archive_res
                    state["trace"].append("ARCHIVE")
                
                state["current_stage"] = "COMPLETED"
                state["trace"].append("COMPLETED")
                
                # Log final audit event
                self.audit.log(self._build_completed_audit(state, start_time))

        except Exception as exc:
            state["current_stage"] = "FAILED"
            state["error"] = str(exc)
            state["trace"].append("FAILED")
            logger.error(f"Workflow execution failed: {exc}", exc_info=True)
            self.audit.log(self._build_failed_audit(state, start_time, exc))

        state["processing_time_ms"] = int((time.time() - start_time) * 1000)
        return state

    # Audit Entry Builders
    def _build_received_audit(self, state: dict, start_time: float) -> dict:
        return {
            "entry_id": state["document_id"] + "-received",
            "document_id": state["document_id"],
            "filename": state["filename"],
            "timestamp": iso_timestamp(),
            "stage": "RECEIVED",
            "classification": state.get("classification", {}).get("label", "PENDING"),
            "confidence": state.get("classification", {}).get("confidence", 0.0),
            "citation": state.get("classification", {}).get("citation", ""),
            "language": state.get("language", {}).get("language", "unknown"),
            "edge_case_flag": state.get("classification", {}).get("edge_case_flag", False),
            "agent_trace": list(state["trace"]),
            "human_override": None,
            "routing_destination": None,
            "error": None,
            "processing_time_ms": int((time.time() - start_time) * 1000),
            "metadata": {"extraction_status": state.get("extraction_status", "unknown")},
        }

    def _build_routed_audit(self, state: dict, start_time: float) -> dict:
        return {
            "entry_id": state["document_id"] + "-route-pending",
            "document_id": state["document_id"],
            "filename": state["filename"],
            "timestamp": iso_timestamp(),
            "stage": "ROUTED",
            "classification": state["classification"]["label"],
            "confidence": state["classification"]["confidence"],
            "citation": state["classification"]["citation"],
            "language": state["language"]["language"],
            "edge_case_flag": state["classification"]["edge_case_flag"],
            "agent_trace": list(state["trace"]),
            "human_override": None,
            "routing_destination": "needs_review",
            "error": None,
            "processing_time_ms": int((time.time() - start_time) * 1000),
            "metadata": {
                "route_status": "needs_review",
                "review_state": "pending_human",
                "text": state.get("text", ""),
                "pdf_path": state.get("pdf_path", "")
            },
        }

    def _build_completed_audit(self, state: dict, start_time: float) -> dict:
        route = state.get("route_result", {})
        decision = state.get("human_decision", {})
        return {
            "entry_id": state["document_id"] + "-completed",
            "document_id": state["document_id"],
            "filename": state["filename"],
            "timestamp": iso_timestamp(),
            "stage": "COMPLETED",
            "classification": state["classification"]["label"],
            "confidence": state["classification"]["confidence"],
            "citation": state["classification"]["citation"],
            "language": state["language"]["language"],
            "edge_case_flag": state["classification"]["edge_case_flag"],
            "agent_trace": list(state["trace"]),
            "human_override": decision.get("decision"),
            "routing_destination": route.get("status"),
            "error": None,
            "processing_time_ms": int((time.time() - start_time) * 1000),
            "metadata": {
                "route_result": route,
                "human_note": decision.get("note"),
            },
        }

    def _build_failed_audit(self, state: dict, start_time: float, exc: Exception) -> dict:
        return {
            "entry_id": state["document_id"] + "-failed",
            "document_id": state["document_id"],
            "filename": state["filename"],
            "timestamp": iso_timestamp(),
            "stage": "FAILED",
            "classification": "ERROR",
            "confidence": 0.0,
            "citation": "",
            "language": "unknown",
            "edge_case_flag": True,
            "agent_trace": list(state["trace"]),
            "human_override": None,
            "routing_destination": None,
            "error": str(exc),
            "processing_time_ms": int((time.time() - start_time) * 1000),
            "metadata": {},
        }
