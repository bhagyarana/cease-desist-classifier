import os
import pytest
from tools.db import get_connection, initialize_sqlite, DatabaseIntegrityError


def test_sqlite_schema_initialization(tmp_path):
    db_path = tmp_path / "test_init.db"
    config = {"datastore": {"type": "sqlite", "sqlite_path": str(db_path)}}
    
    # Initialize SQLite database
    initialize_sqlite(str(db_path))
    
    # Verify tables can be queried
    conn = get_connection(config)
    with conn:
        # Check tables existence
        tables = [
            "cease_requests",
            "audit_logs",
            "archive_logs",
            "deferred_requests",
            "document_embeddings"
        ]
        for table in tables:
            cursor = conn.execute(f"SELECT count(*) FROM {table}")
            assert cursor is not None
            assert cursor.fetchone() is not None


def test_database_integrity_error_wrapping(tmp_path):
    db_path = tmp_path / "test_integrity.db"
    config = {"datastore": {"type": "sqlite", "sqlite_path": str(db_path)}}
    initialize_sqlite(str(db_path))
    
    conn = get_connection(config)
    with conn:
        # Insert initial cease_request
        conn.execute(
            "INSERT INTO cease_requests (id, filename, date_received, processed_at, classification_label, confidence) VALUES (?, ?, ?, ?, ?, ?)",
            ("doc-abc-123", "cease.pdf", "2025-01-15T10:30:00Z", "2025-01-15T10:30:01Z", "CEASE", 0.95)
        )
    
    # Verify duplicate insertion triggers DatabaseIntegrityError
    conn2 = get_connection(config)
    with pytest.raises(DatabaseIntegrityError):
        with conn2:
            conn2.execute(
                "INSERT INTO cease_requests (id, filename, date_received, processed_at, classification_label, confidence) VALUES (?, ?, ?, ?, ?, ?)",
                ("doc-abc-123", "cease.pdf", "2025-01-15T10:30:00Z", "2025-01-15T10:30:01Z", "CEASE", 0.95)
            )
