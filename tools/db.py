import json
import os
import sqlite3
from pathlib import Path

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS cease_requests (
  id TEXT PRIMARY KEY,
  filename TEXT NOT NULL,
  date_received TEXT NOT NULL,
  processed_at TEXT NOT NULL,
  created_at TEXT DEFAULT (datetime('now')),
  classification_label TEXT NOT NULL CHECK(classification_label = 'CEASE'),
  confidence REAL NOT NULL CHECK(confidence BETWEEN 0 AND 1),
  citation TEXT,
  reasoning TEXT,
  language TEXT DEFAULT 'en',
  edge_case_flag INTEGER DEFAULT 0,
  customer_name TEXT,
  customer_address TEXT,
  customer_contact TEXT,
  agent_trace TEXT,
  processing_time_ms INTEGER,
  human_reviewed INTEGER DEFAULT 0,
  human_override TEXT,
  human_reviewed_by TEXT,
  human_reviewed_at TEXT,
  judge_reviewed INTEGER DEFAULT 0,
  judge_agrees INTEGER,
  judge_correction TEXT
);
CREATE INDEX IF NOT EXISTS idx_date_received ON cease_requests(date_received);
CREATE INDEX IF NOT EXISTS idx_language ON cease_requests(language);
CREATE INDEX IF NOT EXISTS idx_confidence ON cease_requests(confidence);
CREATE INDEX IF NOT EXISTS idx_human_reviewed ON cease_requests(human_reviewed);
"""


def get_sqlite_connection(path: str) -> sqlite3.Connection:
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path_obj), timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_sqlite(path: str) -> None:
    conn = get_sqlite_connection(path)
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()


def get_connection(config: dict):
    if config.get("datastore", {}).get("type") == "sqlite":
        return get_sqlite_connection(config["datastore"]["sqlite_path"])
    raise ValueError("Unsupported datastore type")
