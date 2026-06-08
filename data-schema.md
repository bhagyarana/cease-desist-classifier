# data-schema.md — CeaseGuard Data Structures
> All storage schemas defined here. Write code against these specs, not the other way around.
> If you need to change a schema, update this file first, then update the code.

---

## 1. Database: `cease_records` (SQLite → PostgreSQL)

**File:** `data/cease_records.db`  
**Created by:** `tools/db.py` on first run  
**Written by:** `agents/datastore.py`  
**Read by:** Future reporting/dashboard

```sql
CREATE TABLE IF NOT EXISTS cease_requests (
  -- Identity
  id                  TEXT PRIMARY KEY,      -- UUID v4, from document_id
  filename            TEXT NOT NULL,          -- Original PDF filename
  
  -- Timing
  date_received       TEXT NOT NULL,          -- ISO 8601, when PDF was ingested
  processed_at        TEXT NOT NULL,          -- ISO 8601, when classification completed
  created_at          TEXT DEFAULT (datetime('now')),
  
  -- Classification
  classification_label TEXT NOT NULL          -- "CEASE" (always CEASE in this table)
                       CHECK(classification_label = 'CEASE'),
  confidence           REAL NOT NULL          -- 0.0 to 1.0
                       CHECK(confidence BETWEEN 0 AND 1),
  citation             TEXT,                  -- Verbatim excerpt from document
  reasoning            TEXT,                  -- One-line LLM reasoning
  language             TEXT DEFAULT 'en',     -- ISO 639-1 code
  edge_case_flag       INTEGER DEFAULT 0,     -- 0 or 1
  
  -- Customer info (extracted if available)
  customer_name        TEXT,
  customer_address     TEXT,
  customer_contact     TEXT,                  -- Phone/email if present in doc
  
  -- Processing metadata
  agent_trace          TEXT,                  -- JSON array: ["ingestion", "classifier", "datastore"]
  processing_time_ms   INTEGER,
  
  -- Human review
  human_reviewed       INTEGER DEFAULT 0,     -- 0 = not reviewed, 1 = reviewed
  human_override       TEXT,                  -- "CEASE" | "IRRELEVANT" | null
  human_reviewed_by    TEXT,                  -- Agent/user ID
  human_reviewed_at    TEXT,                  -- ISO 8601
  
  -- Judge agent
  judge_reviewed       INTEGER DEFAULT 0,
  judge_agrees         INTEGER,               -- 0 or 1
  judge_correction     TEXT                   -- JSON if correction was made
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_date_received ON cease_requests(date_received);
CREATE INDEX IF NOT EXISTS idx_language ON cease_requests(language);
CREATE INDEX IF NOT EXISTS idx_confidence ON cease_requests(confidence);
CREATE INDEX IF NOT EXISTS idx_human_reviewed ON cease_requests(human_reviewed);
```

---

## 2. Flat File: `archive.jsonl` (IRRELEVANT cases)

**File:** `data/archive.jsonl`  
**Format:** One JSON object per line, newline-delimited  
**Written by:** `agents/archive.py` (append-only)  
**Never overwritten — only appended**

```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "customer_doc_2025_001.pdf",
  "date_received": "2025-01-15T10:30:00Z",
  "archived_at": "2025-01-15T10:30:05Z",
  "classification": "IRRELEVANT",
  "confidence": 0.91,
  "citation": "Invoice #4521 attached for your records",
  "reasoning": "Document is a billing invoice, no communication opt-out language present",
  "language": "en",
  "processing_time_ms": 987
}
```

---

## 3. Audit Log: `audit.jsonl` (ALL cases)

**File:** `data/audit.jsonl`  
**Format:** One JSON object per line, newline-delimited  
**Written by:** `agents/audit.py` (append-only)  
**Multiple entries per document** (one per processing stage)  
**NEVER modify or delete entries — this is the compliance record**

```json
{
  "entry_id": "uuid-v4-unique-per-log-entry",
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "customer_doc_2025_001.pdf",
  "timestamp": "2025-01-15T10:30:00.123Z",
  "stage": "RECEIVED | CLASSIFIED | ROUTED | HUMAN_DECISION | COMPLETED | ERROR",
  "classification": "CEASE | UNCERTAIN | IRRELEVANT | PENDING | ERROR",
  "confidence": 0.92,
  "citation": "I hereby request you cease all direct communications",
  "language": "en",
  "edge_case_flag": false,
  "agent_trace": ["ingestion_agent"],
  "human_override": null,
  "routing_destination": "datastore | archive | escalation | deferred | null",
  "error": null,
  "processing_time_ms": 1243,
  "metadata": {}
}
```

**Stage sequence for successful processing:**
```
RECEIVED → CLASSIFIED → ROUTED → COMPLETED
```

**Stage sequence with human review:**
```
RECEIVED → CLASSIFIED → ROUTED (to escalation) → HUMAN_DECISION → ROUTED (to datastore/archive) → COMPLETED
```

**Stage sequence on failure:**
```
RECEIVED → ERROR
or
RECEIVED → CLASSIFIED → ERROR
```

---

## 4. Deferred Queue: `deferred.jsonl`

**File:** `data/deferred.jsonl`  
**Written by:** `agents/escalation.py` when human chooses DEFER  
**Read by:** `main.py --process-deferred`  
**Format:** One JSON per line

```json
{
  "document_id": "uuid",
  "filename": "doc.pdf",
  "pdf_path": "/path/to/original.pdf",
  "deferred_at": "2025-01-15T10:30:00Z",
  "retry_after": "2025-01-16T10:30:00Z",
  "retry_count": 0,
  "max_retries": 3,
  "deferred_reason": "human requested more info",
  "original_classification": {
    "label": "UNCERTAIN",
    "confidence": 0.61
  }
}
```

---

## 5. IngestionResult (In-Memory, not persisted)

This is the in-memory dict that flows between agents. Not stored to disk.

```python
IngestionResult = {
  "document_id": str,          # UUID v4
  "filename": str,
  "pdf_path": str,
  "text": str,                 # Full extracted text
  "text_length": int,
  "extraction_status": "success" | "partial" | "failed",
  "language": {
    "language": str,           # ISO 639-1
    "confidence": float
  },
  "classification": {
    "label": str,              # CEASE | UNCERTAIN | IRRELEVANT
    "confidence": float,
    "citation": str,
    "reasoning": str,
    "edge_case_flag": bool,
    "model": str,              # Which model was used
    "prompt_version": str      # v1.0.0
  },
  "judge_review": None | {
    "judge_agrees": bool,
    "judge_confidence": float,
    "correction": None | dict
  },
  "routing": {
    "destination": str,        # datastore | archive | escalation
    "status": str,             # pending | complete | error
    "record_id": str | None
  },
  "human_decision": None | {
    "decision": str,
    "decided_at": str,
    "operator_id": str
  },
  "processing_start": str,     # ISO 8601
  "processing_end": str | None,
  "processing_time_ms": int | None,
  "errors": []                 # List of non-fatal errors
}
```

---

## 6. Config Schema: `config.yaml`

```yaml
# config.yaml — All tunable parameters. Edit here, not in code.

classifier:
  model: "claude-sonnet-4-20250514"
  prompt_version: "v1.0.0"
  confidence_threshold_uncertain: 0.75    # Below this → force UNCERTAIN
  confidence_threshold_edge_case: 0.60    # Below this → force UNCERTAIN + flag
  max_text_chars: 50000                   # Chunk if longer
  chunk_size_chars: 10000
  chunk_overlap_chars: 500

judge:
  enabled: true
  sample_rate: 0.10
  always_on_uncertain: true
  always_on_edge_cases: true

datastore:
  type: "sqlite"                          # "sqlite" | "postgres"
  sqlite_path: "data/cease_records.db"
  postgres_url: null                      # Set for production
  retry_attempts: 3
  retry_backoff_base_seconds: 1

files:
  audit_path: "data/audit.jsonl"
  archive_path: "data/archive.jsonl"
  deferred_path: "data/deferred.jsonl"

escalation:
  mode: "cli"                             # "cli" | "webhook" (future)
  defer_retry_hours: 24
  max_defer_retries: 3

logging:
  level: "INFO"                           # DEBUG | INFO | WARNING | ERROR
  format: "json"                          # "json" | "text"
```

---

## Schema Change Protocol

1. Update this file first
2. Write a migration script if DB schema changes (even for SQLite)
3. Add a CHANGELOG entry
4. Update any agent that reads/writes the changed schema
5. Run full test suite

**Never** change a schema in code without updating this file.
