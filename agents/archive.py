import json
import os
import time
from pathlib import Path


class ArchiveAgent:
    def __init__(self, config: dict):
        self.config = config
        self.path = config.get("files", {}).get("archive_path", "data/archive.jsonl")
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)

    def run(self, ingestion_result: dict) -> dict:
        document_id = ingestion_result["document_id"]
        start_ts = time.time()
        postgres_url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or self.config.get("datastore", {}).get("postgres_url")
        db_type = self.config.get("datastore", {}).get("type", "sqlite")
        sqlite_path = self.config.get("datastore", {}).get("sqlite_path")

        # Always write to file
        file_res = self._run_file(ingestion_result, start_ts)

        # Attempt to write to DB if database mode is configured
        if db_type == "postgres" or postgres_url or (db_type == "sqlite" and sqlite_path):
            try:
                db_res = self._run_db(ingestion_result, start_ts)
                return db_res
            except Exception as exc:
                pass

        return file_res

    def _run_file(self, ingestion_result: dict, start_ts: float) -> dict:
        document_id = ingestion_result["document_id"]
        data = {
            "document_id": document_id,
            "filename": ingestion_result["filename"],
            "date_received": ingestion_result["processing_start"],
            "archived_at": ingestion_result["processing_end"],
            "classification": ingestion_result["classification"]["label"],
            "confidence": ingestion_result["classification"]["confidence"],
            "citation": ingestion_result["classification"]["citation"],
            "reasoning": ingestion_result["classification"]["reasoning"],
            "language": ingestion_result["language"]["language"],
            "processing_time_ms": ingestion_result.get("processing_time_ms", 0),
        }
        existing = self._document_exists(document_id)
        if existing:
            return {
                "status": "duplicate",
                "filepath": self.path,
                "processing_time_ms": int((time.time() - start_ts) * 1000),
            }

        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(data, ensure_ascii=False) + "\n")

        return {
            "status": "archived",
            "filepath": self.path,
            "processing_time_ms": int((time.time() - start_ts) * 1000),
        }

    def _run_db(self, ingestion_result: dict, start_ts: float) -> dict:
        from tools.db import get_connection, DatabaseIntegrityError
        document_id = ingestion_result["document_id"]
        conn = get_connection(self.config)
        try:
            with conn:
                cursor = conn.execute("SELECT document_id FROM archive_logs WHERE document_id = ?", (document_id,))
                row = cursor.fetchone()
                if row:
                    return {
                        "status": "duplicate",
                        "filepath": "database",
                        "processing_time_ms": int((time.time() - start_ts) * 1000),
                    }

                conn.execute(
                    """
                    INSERT INTO archive_logs (
                        document_id, filename, date_received, classification, confidence, citation, archived_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        document_id,
                        ingestion_result["filename"],
                        ingestion_result["processing_start"],
                        ingestion_result["classification"]["label"],
                        ingestion_result["classification"]["confidence"],
                        ingestion_result["classification"]["citation"],
                        ingestion_result["processing_end"]
                    )
                )
            return {
                "status": "archived",
                "filepath": "database",
                "processing_time_ms": int((time.time() - start_ts) * 1000),
            }
        except DatabaseIntegrityError:
            return {
                "status": "duplicate",
                "filepath": "database",
                "processing_time_ms": int((time.time() - start_ts) * 1000),
            }

    def _document_exists(self, document_id: str) -> bool:
        if not os.path.exists(self.path):
            return False
        with open(self.path, "r", encoding="utf-8") as handle:
            for line in handle:
                if document_id in line:
                    return True
        return False
