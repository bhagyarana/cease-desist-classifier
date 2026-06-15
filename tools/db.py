import os
import json
import sqlite3
from pathlib import Path

# Exception to unify database integrity errors (e.g. duplicate keys)
class DatabaseIntegrityError(Exception):
    pass

# Unified Schemas
# SQLite dialect schemas
SQLITE_SCHEMAS = [
    """
    CREATE TABLE IF NOT EXISTS cease_requests (
      id TEXT PRIMARY KEY,
      filename TEXT NOT NULL,
      date_received TEXT NOT NULL,
      processed_at TEXT NOT NULL,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP,
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
    """,
    "CREATE INDEX IF NOT EXISTS idx_cease_date_received ON cease_requests(date_received);",
    "CREATE INDEX IF NOT EXISTS idx_cease_language ON cease_requests(language);",
    "CREATE INDEX IF NOT EXISTS idx_cease_confidence ON cease_requests(confidence);",
    "CREATE INDEX IF NOT EXISTS idx_cease_human_reviewed ON cease_requests(human_reviewed);",
    """
    CREATE TABLE IF NOT EXISTS audit_logs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      entry_id TEXT NOT NULL,
      document_id TEXT NOT NULL,
      filename TEXT NOT NULL,
      timestamp TEXT NOT NULL,
      stage TEXT NOT NULL,
      classification TEXT,
      confidence REAL,
      citation TEXT,
      language TEXT,
      edge_case_flag INTEGER DEFAULT 0,
      agent_trace TEXT,
      human_override TEXT,
      routing_destination TEXT,
      error TEXT,
      processing_time_ms INTEGER,
      metadata TEXT,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_audit_document_id ON audit_logs(document_id);",
    "CREATE INDEX IF NOT EXISTS idx_audit_stage ON audit_logs(stage);",
    """
    CREATE TABLE IF NOT EXISTS archive_logs (
      document_id TEXT PRIMARY KEY,
      filename TEXT NOT NULL,
      date_received TEXT NOT NULL,
      classification TEXT DEFAULT 'IRRELEVANT',
      confidence REAL,
      citation TEXT,
      archived_at TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS deferred_requests (
      document_id TEXT PRIMARY KEY,
      filename TEXT NOT NULL,
      deferred_at TEXT NOT NULL,
      operator_id TEXT,
      note TEXT,
      retries_count INTEGER DEFAULT 0,
      status TEXT DEFAULT 'deferred'
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS document_embeddings (
      document_id TEXT PRIMARY KEY,
      summary TEXT NOT NULL,
      embedding TEXT NOT NULL
    );
    """
]

# PostgreSQL dialect schemas
POSTGRES_SCHEMAS = [
    """
    CREATE TABLE IF NOT EXISTS cease_requests (
      id TEXT PRIMARY KEY,
      filename TEXT NOT NULL,
      date_received TEXT NOT NULL,
      processed_at TEXT NOT NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
    """,
    "CREATE INDEX IF NOT EXISTS idx_cease_date_received ON cease_requests(date_received);",
    "CREATE INDEX IF NOT EXISTS idx_cease_language ON cease_requests(language);",
    "CREATE INDEX IF NOT EXISTS idx_cease_confidence ON cease_requests(confidence);",
    "CREATE INDEX IF NOT EXISTS idx_cease_human_reviewed ON cease_requests(human_reviewed);",
    """
    CREATE TABLE IF NOT EXISTS audit_logs (
      id SERIAL PRIMARY KEY,
      entry_id TEXT NOT NULL,
      document_id TEXT NOT NULL,
      filename TEXT NOT NULL,
      timestamp TEXT NOT NULL,
      stage TEXT NOT NULL,
      classification TEXT,
      confidence REAL,
      citation TEXT,
      language TEXT,
      edge_case_flag INTEGER DEFAULT 0,
      agent_trace TEXT,
      human_override TEXT,
      routing_destination TEXT,
      error TEXT,
      processing_time_ms INTEGER,
      metadata TEXT,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_audit_document_id ON audit_logs(document_id);",
    "CREATE INDEX IF NOT EXISTS idx_audit_stage ON audit_logs(stage);",
    """
    CREATE TABLE IF NOT EXISTS archive_logs (
      document_id TEXT PRIMARY KEY,
      filename TEXT NOT NULL,
      date_received TEXT NOT NULL,
      classification TEXT DEFAULT 'IRRELEVANT',
      confidence REAL,
      citation TEXT,
      archived_at TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS deferred_requests (
      document_id TEXT PRIMARY KEY,
      filename TEXT NOT NULL,
      deferred_at TEXT NOT NULL,
      operator_id TEXT,
      note TEXT,
      retries_count INTEGER DEFAULT 0,
      status TEXT DEFAULT 'deferred'
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS document_embeddings (
      document_id TEXT PRIMARY KEY,
      summary TEXT NOT NULL,
      embedding TEXT NOT NULL
    );
    """
]


class DBConnectionProxy:
    def __init__(self, raw_conn, is_pg: bool):
        self._conn = raw_conn
        self._is_pg = is_pg

    def execute(self, query: str, params: tuple = ()):
        if self._is_pg:
            # Translate placeholder '?' to PostgreSQL '%s'
            query = query.replace("?", "%s")
        
        cursor = self._conn.cursor()
        try:
            cursor.execute(query, params)
            return cursor
        except Exception as exc:
            exc_name = type(exc).__name__
            # Catch database integrity / unique key constraints
            if "IntegrityError" in exc_name or "UniqueViolation" in exc_name or "unique" in str(exc).lower():
                raise DatabaseIntegrityError(str(exc)) from exc
            raise exc

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()


def get_sqlite_connection(path: str) -> sqlite3.Connection:
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path_obj), timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def get_postgres_connection(connection_url: str):
    import psycopg2
    import psycopg2.extras
    # Connect and use DictCursor to mimic sqlite3.Row's dict-like results
    conn = psycopg2.connect(connection_url)
    # Ensure dictionary-like cursor access
    conn.cursor_factory = psycopg2.extras.DictCursor
    return conn


def initialize_sqlite(path: str) -> None:
    conn = get_sqlite_connection(path)
    try:
        for statement in SQLITE_SCHEMAS:
            if statement.strip():
                conn.execute(statement)
        conn.commit()
    finally:
        conn.close()


def initialize_postgres(connection_url: str) -> None:
    conn = get_postgres_connection(connection_url)
    try:
        with conn.cursor() as cursor:
            for statement in POSTGRES_SCHEMAS:
                if statement.strip():
                    cursor.execute(statement)
        conn.commit()
    finally:
        conn.close()


def get_connection(config: dict) -> DBConnectionProxy:
    db_type = config.get("datastore", {}).get("type", "sqlite")
    postgres_url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or config.get("datastore", {}).get("postgres_url")

    # If Postgres configuration is present in config or environment variables, prioritize it
    if db_type == "postgres" or postgres_url:
        if not postgres_url:
            raise ValueError("PostgreSQL selected but DATABASE_URL/POSTGRES_URL environment variable is missing.")
        raw_conn = get_postgres_connection(postgres_url)
        return DBConnectionProxy(raw_conn, is_pg=True)
    
    # SQLite fallback
    sqlite_path = config.get("datastore", {}).get("sqlite_path", "data/cease_records.db")
    raw_conn = get_sqlite_connection(sqlite_path)
    return DBConnectionProxy(raw_conn, is_pg=False)
