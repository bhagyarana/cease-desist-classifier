import argparse
import json
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path

import yaml

from agents.audit import AuditAgent
from agents.archive import ArchiveAgent
from agents.classifier import ClassifierAgent
from agents.datastore import DatastoreAgent
from agents.escalation import EscalationAgent
from agents.ingestion import IngestionAgent
from tools.db import initialize_sqlite


def load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def iso_timestamp() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def route_result(result: dict, config: dict, audit: AuditAgent) -> dict:
    label = result["classification"]["label"]
    if label == "CEASE":
        datastore = DatastoreAgent(config)
        route = datastore.run(result)
        audit.log({
            "entry_id": result["document_id"] + "-route",
            "document_id": result["document_id"],
            "filename": result["filename"],
            "timestamp": iso_timestamp(),
            "stage": "ROUTED",
            "classification": label,
            "confidence": result["classification"]["confidence"],
            "citation": result["classification"]["citation"],
            "language": result["language"]["language"],
            "edge_case_flag": result["classification"]["edge_case_flag"],
            "agent_trace": ["ingestion", "classifier", "datastore"],
            "human_override": None,
            "routing_destination": "datastore",
            "error": None if route.get("status") != "error" else route.get("error"),
            "processing_time_ms": int(route.get("processing_time_ms", 0)),
            "metadata": {"route_status": route.get("status"), "record_id": route.get("record_id")},
        })
        return route
    if label == "IRRELEVANT":
        archive = ArchiveAgent(config)
        route = archive.run(result)
        audit.log({
            "entry_id": result["document_id"] + "-route",
            "document_id": result["document_id"],
            "filename": result["filename"],
            "timestamp": iso_timestamp(),
            "stage": "ROUTED",
            "classification": label,
            "confidence": result["classification"]["confidence"],
            "citation": result["classification"]["citation"],
            "language": result["language"]["language"],
            "edge_case_flag": result["classification"]["edge_case_flag"],
            "agent_trace": ["ingestion", "classifier", "archive"],
            "human_override": None,
            "routing_destination": "archive",
            "error": None if route.get("status") != "error" else route.get("error"),
            "processing_time_ms": int(route.get("processing_time_ms", 0)),
            "metadata": {"route_status": route.get("status"), "filepath": route.get("filepath")},
        })
        return route
    escalation = EscalationAgent(config)
    human = escalation.run(result)
    decision = human["decision"]
    result["human_decision"] = human
    result["classification"]["human_override"] = decision
    if decision == "DEFER":
        audit.log({
            "entry_id": result["document_id"] + "-defer",
            "document_id": result["document_id"],
            "filename": result["filename"],
            "timestamp": iso_timestamp(),
            "stage": "ROUTED",
            "classification": label,
            "confidence": result["classification"]["confidence"],
            "citation": result["classification"]["citation"],
            "language": result["language"]["language"],
            "edge_case_flag": result["classification"]["edge_case_flag"],
            "agent_trace": ["ingestion", "classifier", "escalation"],
            "human_override": decision,
            "routing_destination": "deferred",
            "error": None,
            "processing_time_ms": 0,
            "metadata": {"deferred_at": human["decided_at"]},
        })
        return {"status": "deferred", "deferred_at": human["decided_at"]}
    if decision == "CEASE":
        datastore = DatastoreAgent(config)
        route = datastore.run(result)
        audit.log({
            "entry_id": result["document_id"] + "-route",
            "document_id": result["document_id"],
            "filename": result["filename"],
            "timestamp": iso_timestamp(),
            "stage": "ROUTED",
            "classification": decision,
            "confidence": result["classification"]["confidence"],
            "citation": result["classification"]["citation"],
            "language": result["language"]["language"],
            "edge_case_flag": result["classification"]["edge_case_flag"],
            "agent_trace": ["ingestion", "classifier", "escalation", "datastore"],
            "human_override": decision,
            "routing_destination": "datastore",
            "error": None if route.get("status") != "error" else route.get("error"),
            "processing_time_ms": int(route.get("processing_time_ms", 0)),
            "metadata": {"route_status": route.get("status"), "record_id": route.get("record_id")},
        })
        return route
    archive = ArchiveAgent(config)
    route = archive.run(result)
    audit.log({
        "entry_id": result["document_id"] + "-route",
        "document_id": result["document_id"],
        "filename": result["filename"],
        "timestamp": iso_timestamp(),
        "stage": "ROUTED",
        "classification": decision,
        "confidence": result["classification"]["confidence"],
        "citation": result["classification"]["citation"],
        "language": result["language"]["language"],
        "edge_case_flag": result["classification"]["edge_case_flag"],
        "agent_trace": ["ingestion", "classifier", "escalation", "archive"],
        "human_override": decision,
        "routing_destination": "archive",
        "error": None if route.get("status") != "error" else route.get("error"),
        "processing_time_ms": int(route.get("processing_time_ms", 0)),
        "metadata": {"route_status": route.get("status"), "filepath": route.get("filepath")},
    })
    return route


def process_pdf(pdf_path: str, config: dict, audit: AuditAgent) -> dict:
    ingestion = IngestionAgent(config)
    result = ingestion.run({"pdf_path": pdf_path})
    audit.log({
        "entry_id": result["document_id"] + "-received",
        "document_id": result["document_id"],
        "filename": result["filename"],
        "timestamp": iso_timestamp(),
        "stage": "RECEIVED",
        "classification": result["classification"]["label"],
        "confidence": result["classification"]["confidence"],
        "citation": result["classification"]["citation"],
        "language": result["language"]["language"],
        "edge_case_flag": result["classification"]["edge_case_flag"],
        "agent_trace": ["ingestion"],
        "human_override": None,
        "routing_destination": None,
        "error": None,
        "processing_time_ms": int(result.get("processing_time_ms", 0) or 0),
        "metadata": {"extraction_status": result["extraction_status"]},
    })
    route = route_result(result, config, audit)
    audit.log({
        "entry_id": result["document_id"] + "-completed",
        "document_id": result["document_id"],
        "filename": result["filename"],
        "timestamp": iso_timestamp(),
        "stage": "COMPLETED",
        "classification": result["classification"]["label"],
        "confidence": result["classification"]["confidence"],
        "citation": result["classification"]["citation"],
        "language": result["language"]["language"],
        "edge_case_flag": result["classification"]["edge_case_flag"],
        "agent_trace": result.get("agent_trace", ["ingestion"]),
        "human_override": result.get("human_decision", {}).get("decision"),
        "routing_destination": route.get("status"),
        "error": None,
        "processing_time_ms": int(result.get("processing_time_ms", 0) or 0),
        "metadata": {"route_result": route},
    })
    return result


def main():
    parser = argparse.ArgumentParser(description="CeaseGuard PDF processing pipeline")
    parser.add_argument("--pdf", type=str, help="Path to a PDF document to process")
    parser.add_argument("--process-deferred", action="store_true", help="Process deferred documents")
    args = parser.parse_args()

    config = load_config()
    audit = AuditAgent(config)
    if config.get("datastore", {}).get("type") == "sqlite":
        initialize_sqlite(config["datastore"]["sqlite_path"])

    if args.pdf:
        result = process_pdf(args.pdf, config, audit)
        print(json.dumps(result, indent=2))
        return
    if args.process_deferred:
        print("Deferred processing is not implemented in this MVP.")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
