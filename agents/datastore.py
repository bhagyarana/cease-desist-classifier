import json
import time
from datetime import datetime

from tools.db import get_connection, DatabaseIntegrityError


class DatastoreAgent:
    def __init__(self, config: dict):
        self.config = config
        self.retry_attempts = config.get("datastore", {}).get("retry_attempts", 3)
        self.backoff_base = config.get("datastore", {}).get("retry_backoff_base_seconds", 1)

    def run(self, ingestion_result: dict) -> dict:
        if ingestion_result["classification"]["label"] != "CEASE":
            return {"status": "error", "error": "invalid_label", "record_id": None}

        document_id = ingestion_result["document_id"]
        start_ts = time.time()
        attempt = 0
        while attempt < self.retry_attempts:
            try:
                conn = get_connection(self.config)
                with conn:
                    cursor = conn.execute(
                        "SELECT id FROM cease_requests WHERE id = ?",
                        (document_id,),
                    )
                    row = cursor.fetchone()
                    if row:
                        return {
                            "status": "duplicate",
                            "record_id": document_id,
                            "processing_time_ms": int((time.time() - start_ts) * 1000),
                        }
                    conn.execute(
                        "INSERT INTO cease_requests (id, filename, date_received, processed_at, classification_label, confidence, citation, reasoning, language, edge_case_flag, agent_trace, processing_time_ms, human_override) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            document_id,
                            ingestion_result["filename"],
                            ingestion_result["processing_start"],
                            ingestion_result["processing_end"],
                            ingestion_result["classification"]["label"],
                            ingestion_result["classification"]["confidence"],
                            ingestion_result["classification"]["citation"],
                            ingestion_result["classification"]["reasoning"],
                            ingestion_result["language"]["language"],
                            int(ingestion_result["classification"]["edge_case_flag"]),
                            json.dumps(["ingestion", "classifier", "datastore"]),
                            ingestion_result.get("processing_time_ms", 0),
                            ingestion_result.get("human_decision", {}).get("decision"),
                        ),
                    )
                return {
                    "status": "written",
                    "record_id": document_id,
                    "processing_time_ms": int((time.time() - start_ts) * 1000),
                }
            except DatabaseIntegrityError:
                return {
                    "status": "duplicate",
                    "record_id": document_id,
                    "processing_time_ms": int((time.time() - start_ts) * 1000),
                }
            except Exception as exc:
                attempt += 1
                if attempt >= self.retry_attempts:
                    return {
                        "status": "error",
                        "error": str(exc),
                        "record_id": None,
                        "processing_time_ms": int((time.time() - start_ts) * 1000),
                    }
                time.sleep(self.backoff_base * attempt)
