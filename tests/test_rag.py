import pytest
from tools.db import initialize_sqlite
from tools.rag_service import RAGService


def test_rag_index_and_search(tmp_path):
    # Initialize test database
    db_path = tmp_path / "test_rag.db"
    initialize_sqlite(str(db_path))
    
    config = {
        "datastore": {
            "type": "sqlite",
            "sqlite_path": str(db_path)
        }
    }
    
    rag = RAGService(config)
    
    # Index test cases
    assert rag.index_document("doc-1", "This is an opt-out request from John Doe regarding all communication channels.")
    assert rag.index_document("doc-2", "Invoice number 5493 for account services.")
    assert rag.index_document("doc-3", "Complaint about delayed delivery of products.")
    
    # Query for similar items
    matches = rag.find_similar("John Doe wants to opt out of contact", limit=2)
    
    assert len(matches) == 2
    # The first document (doc-1) contains opt-out language and John Doe, so it should be the most similar
    assert matches[0]["document_id"] == "doc-1"
    
    # Search for billing
    billing_matches = rag.find_similar("account invoice", limit=1)
    assert len(billing_matches) == 1
    assert billing_matches[0]["document_id"] == "doc-2"
