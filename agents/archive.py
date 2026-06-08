import json
import os
import time
from pathlib import Path


class ArchiveAgent:
    def __init__(self, config: dict):
        self.path = config.get("files", {}).get("archive_path", "data/archive.jsonl")
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)

    def run(self, ingestion_result: dict) -> dict:
        document_id = ingestion_result["document_id"]
        start_ts = time.time()
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

    def _document_exists(self, document_id: str) -> bool:
        if not os.path.exists(self.path):
            return False
        with open(self.path, "r", encoding="utf-8") as handle:
            for line in handle:
                if document_id in line:
                    return True
        return False
