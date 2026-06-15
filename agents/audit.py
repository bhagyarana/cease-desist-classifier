import json
import os
import sys
import time
import uuid
from pathlib import Path

try:
    import fcntl
except ImportError:
    fcntl = None

try:
    import msvcrt
except ImportError:
    msvcrt = None


class AuditAgent:
    def __init__(self, config: dict):
        self.config = config
        self.path = config.get("files", {}).get("audit_path", "data/audit.jsonl")
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)

    def log(self, entry: dict) -> None:
        entry = self._normalize_entry(entry)
        # Always write to file for backup and test validation
        try:
            self._write_line(entry)
        except Exception as exc:
            print(f"[AUDIT] Failed to write audit log to file: {exc}", file=sys.stderr)

        # Attempt to write to database if configured
        try:
            postgres_url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or self.config.get("datastore", {}).get("postgres_url")
            db_type = self.config.get("datastore", {}).get("type", "sqlite")
            sqlite_path = self.config.get("datastore", {}).get("sqlite_path")
            if db_type == "postgres" or postgres_url or (db_type == "sqlite" and sqlite_path):
                self._write_to_db(entry)
        except Exception as exc:
            # Fallback silently or print error if db is uninitialized
            pass

    def _write_to_db(self, entry: dict) -> None:
        from tools.db import get_connection
        conn = get_connection(self.config)
        with conn:
            conn.execute(
                """
                INSERT INTO audit_logs (
                    entry_id, document_id, filename, timestamp, stage, classification,
                    confidence, citation, language, edge_case_flag, agent_trace,
                    human_override, routing_destination, error, processing_time_ms, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.get("entry_id"),
                    entry.get("document_id"),
                    entry.get("filename"),
                    entry.get("timestamp"),
                    entry.get("stage"),
                    entry.get("classification"),
                    entry.get("confidence"),
                    entry.get("citation"),
                    entry.get("language"),
                    int(entry.get("edge_case_flag", False)),
                    json.dumps(entry.get("agent_trace", [])),
                    entry.get("human_override"),
                    entry.get("routing_destination"),
                    entry.get("error"),
                    entry.get("processing_time_ms", 0),
                    json.dumps(entry.get("metadata", {})),
                )
            )

    def _normalize_entry(self, entry: dict) -> dict:
        normalized = dict(entry)
        normalized["entry_id"] = normalized.get("entry_id") or str(uuid.uuid4())
        normalized["timestamp"] = normalized.get("timestamp") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        return normalized

    def _write_line(self, entry: dict) -> None:
        data = json.dumps(entry, ensure_ascii=False)
        with open(self.path, "a", encoding="utf-8") as handle:
            self._lock_file(handle)
            handle.write(data + "\n")
            handle.flush()
            self._unlock_file(handle)

    def _lock_file(self, handle):
        if msvcrt:
            try:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            except OSError:
                pass
        elif fcntl:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            except OSError:
                pass

    def _unlock_file(self, handle):
        if msvcrt:
            try:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
        elif fcntl:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser(description="Test audit log writer")
    parser.add_argument("--test", action="store_true", help="Append a test entry")
    args = parser.parse_args()
    if args.test:
        AuditAgent({"files": {"audit_path": "data/audit.jsonl"}}).log({
            "document_id": "test-doc",
            "filename": "test.pdf",
            "stage": "TEST",
            "classification": "UNCERTAIN",
            "confidence": 0.0,
            "citation": "",
            "language": "en",
            "edge_case_flag": False,
            "agent_trace": ["audit"],
            "human_override": None,
            "routing_destination": None,
            "error": None,
            "processing_time_ms": 0,
            "metadata": {},
        })
