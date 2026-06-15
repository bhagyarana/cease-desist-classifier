import json
import os
from datetime import datetime, timezone
from pathlib import Path


class EscalationAgent:
    def __init__(self, config: dict):
        self.config = config
        self.path = config.get("files", {}).get("deferred_path", "data/deferred.jsonl")
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)

    def run(self, ingestion_result: dict) -> dict:
        print("\n=== HUMAN ESCALATION REQUIRED ===")
        print("Document:", ingestion_result["filename"])
        print("Detected language:", ingestion_result["language"]["language"])
        print("Classifier label:", ingestion_result["classification"]["label"])
        print("Confidence:", ingestion_result["classification"]["confidence"])
        print("Citation:", ingestion_result["classification"]["citation"])
        print("Reasoning:", ingestion_result["classification"]["reasoning"])
        print("\nChoose an action:")
        print("  1) CEASE")
        print("  2) IRRELEVANT")
        print("  3) DEFER for later review")

        while True:
            choice = input("Enter 1, 2, or 3: ").strip()
            if choice == "1":
                return self._build_result("CEASE")
            if choice == "2":
                return self._build_result("IRRELEVANT")
            if choice == "3":
                result = self._build_result("DEFER")
                self._write_deferred(ingestion_result, result)
                return result
            print("Invalid choice. Please select 1, 2, or 3.")

    def _build_result(self, decision: str) -> dict:
        return {
            "decision": decision,
            "decided_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "operator_id": "cli-user",
        }

    def _write_deferred(self, ingestion_result: dict, result: dict) -> None:
        postgres_url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or self.config.get("datastore", {}).get("postgres_url")
        db_type = self.config.get("datastore", {}).get("type", "sqlite")
        sqlite_path = self.config.get("datastore", {}).get("sqlite_path")

        # Always write to file
        try:
            self._write_deferred_file(ingestion_result, result)
        except Exception as exc:
            pass

        # Attempt to write to DB if database mode is configured
        if db_type == "postgres" or postgres_url or (db_type == "sqlite" and sqlite_path):
            try:
                self._write_deferred_db(ingestion_result, result)
            except Exception as exc:
                pass

    def _write_deferred_file(self, ingestion_result: dict, result: dict) -> None:
        deferred = {
            "document_id": ingestion_result["document_id"],
            "filename": ingestion_result["filename"],
            "pdf_path": ingestion_result["pdf_path"],
            "deferred_at": result["decided_at"],
            "retry_after": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "retry_count": 0,
            "max_retries": self.config.get("escalation", {}).get("max_defer_retries", 3),
            "deferred_reason": "Human elected to defer decision",
            "original_classification": {
                "label": ingestion_result["classification"]["label"],
                "confidence": ingestion_result["classification"]["confidence"],
            },
        }
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(deferred, ensure_ascii=False) + "\n")

    def _write_deferred_db(self, ingestion_result: dict, result: dict) -> None:
        from tools.db import get_connection, DatabaseIntegrityError
        conn = get_connection(self.config)
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO deferred_requests (
                        document_id, filename, deferred_at, operator_id, note, retries_count, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ingestion_result["document_id"],
                        ingestion_result["filename"],
                        result["decided_at"],
                        result.get("operator_id", "cli-user"),
                        result.get("note"),
                        0,
                        "deferred"
                    )
                )
        except DatabaseIntegrityError:
            # Duplicate entry, ignore
            pass
