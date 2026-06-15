# data-schema.md: CeaseGuard Data Structures
> All storage schemas defined here. Write code against these specs, not the other way around.

---

## 1. Relational Database Tables (SQLite & PostgreSQL)

CeaseGuard maintains identical relational tables in SQLite (local development) and PostgreSQL (production). Table creation statements are managed dynamically in `tools/db.py`.

### Table 1: `cease_requests`
Stores successfully classified and human-approved Cease & Desist orders.
```sql
CREATE TABLE cease_requests (
  id                  TEXT PRIMARY KEY,      -- UUID v4 (from document_id)
  filename            TEXT NOT NULL,          -- Original PDF filename
  date_received       TEXT NOT NULL,          -- ISO 8601, when PDF was ingested
  processed_at        TEXT NOT NULL,          -- ISO 8601, when classification completed
  created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  classification_label TEXT NOT NULL CHECK(classification_label = 'CEASE'),
  confidence           REAL NOT NULL CHECK(confidence BETWEEN 0 AND 1),
  citation             TEXT,                  -- Verbatim citation excerpt
  reasoning            TEXT,                  -- Classification reasoning summary
  language             TEXT DEFAULT 'en',     -- ISO 639-1 code
  edge_case_flag       INTEGER DEFAULT 0,     -- 0 = normal, 1 = flagged
  customer_name        TEXT,
  customer_address     TEXT,
  customer_contact     TEXT,
  agent_trace          TEXT,                  -- JSON stringified array of stage trace
  processing_time_ms   INTEGER,
  human_reviewed       INTEGER DEFAULT 0,     -- 0 = false, 1 = true
  human_override       TEXT,                  -- "CEASE" | "IRRELEVANT"
  human_reviewed_by    TEXT,                  -- Operator user ID
  human_reviewed_at    TEXT,                  -- ISO timestamp
  judge_reviewed       INTEGER DEFAULT 0,
  judge_agrees         INTEGER,
  judge_correction     TEXT                   -- Correction notes if judge disagreed
);
```

### Table 2: `audit_logs`
Immutable compliance transaction logs capturing stages (`RECEIVED`, `ROUTED`, `COMPLETED`, `FAILED`).
```sql
CREATE TABLE audit_logs (
  id                  SERIAL PRIMARY KEY,    -- Auto-increment key (INTEGER in SQLite)
  entry_id            TEXT NOT NULL,         -- Unique log transaction ID
  document_id         TEXT NOT NULL,         -- Associated PDF document UUID
  filename            TEXT NOT NULL,         -- PDF filename
  timestamp           TEXT NOT NULL,         -- Log creation timestamp
  stage               TEXT NOT NULL,         -- INGEST / CLASSIFY / JUDGE / ROUTED / COMPLETED / FAILED
  classification      TEXT,                  -- CEASE / IRRELEVANT / UNCERTAIN
  confidence          REAL,
  citation            TEXT,
  language            TEXT,
  edge_case_flag      INTEGER DEFAULT 0,
  agent_trace         TEXT,                  -- Stringified JSON array of stage trace
  human_override      TEXT,                  -- Override label if human review was executed
  routing_destination TEXT,                  -- datastore / archive / needs_review / deferred
  error               TEXT,                  -- Error detail message if stage failed
  processing_time_ms  INTEGER,
  metadata            TEXT,                  -- Stringified JSON (contains raw text and pdf_path for needs_review)
  created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Table 3: `archive_logs`
Index of archived, non-compliance related documents.
```sql
CREATE TABLE archive_logs (
  document_id         TEXT PRIMARY KEY,
  filename            TEXT NOT NULL,
  date_received       TEXT NOT NULL,
  classification      TEXT DEFAULT 'IRRELEVANT',
  confidence          REAL,
  citation            TEXT,
  archived_at         TEXT NOT NULL
);
```

### Table 4: `deferred_requests`
List of review items deferred by operators for subsequent processing.
```sql
CREATE TABLE deferred_requests (
  document_id         TEXT PRIMARY KEY,
  filename            TEXT NOT NULL,
  deferred_at         TEXT NOT NULL,
  operator_id         TEXT,
  note                TEXT,
  retries_count       INTEGER DEFAULT 0,
  status              TEXT DEFAULT 'deferred'
);
```

### Table 5: `document_embeddings`
Stores embedded document vectors to power context search recommendations.
```sql
CREATE TABLE document_embeddings (
  document_id         TEXT PRIMARY KEY,      -- Associated document UUID
  summary             TEXT NOT NULL,         -- First 4000 characters of document body
  embedding           TEXT NOT NULL          -- JSON-serialized float array (768 dimensions)
);
```

---

## 2. Flat File Formats (Backup Logs)

CeaseGuard maintains append-only JSONL files at local paths defined in `config.yaml` to ensure backwards compatibility with file-based unit tests.

### Ingest Audit File (`data/audit.jsonl`)
Appends one JSON object line per stage transition:
```json
{
  "entry_id": "550e8400-e29b-41d4-a716-446655440001",
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "customer_opt_out.pdf",
  "timestamp": "2026-06-15T12:00:00Z",
  "stage": "ROUTED",
  "classification": "UNCERTAIN",
  "confidence": 0.62,
  "citation": "Please stop sending notifications",
  "language": "en",
  "edge_case_flag": true,
  "agent_trace": ["INGEST", "CLASSIFY", "JUDGE"],
  "human_override": null,
  "routing_destination": "needs_review",
  "error": null,
  "processing_time_ms": 1400,
  "metadata": {
    "route_status": "needs_review",
    "review_state": "pending_human",
    "text": "Extracted PDF contents...",
    "pdf_path": "data/uploads/customer_opt_out.pdf"
  }
}
```

---

## 3. In-Memory Workflow State

The central state dictionary flowing through the stateful agent workflow (`agents/workflow.py`):

```python
state = {
    "document_id": str,                  # UUID v4
    "filename": str,                     # PDF name
    "pdf_path": str,                     # Absolute filepath
    "text": str,                         # Extracted text content
    "language": {
        "language": str,                 # ISO language code
        "confidence": float
    },
    "extraction_status": str,            # "success" | "failed"
    "classification": {
        "label": str,                    # "CEASE" | "IRRELEVANT" | "UNCERTAIN"
        "confidence": float,
        "citation": str,
        "reasoning": str,
        "edge_case_flag": bool
    },
    "current_stage": str,                # "INGEST" | "CLASSIFY" | "JUDGE" | "ROUTE" | "ESCALATED" | "COMPLETED"
    "trace": list[str],                  # Active trace logs (e.g. ["INGEST", "CLASSIFY"])
    "human_decision": None | {           # Present if operator overrides
        "decision": str,                 # "CEASE" | "IRRELEVANT" | "DEFER"
        "decided_at": str,
        "operator_id": str,
        "note": str
    },
    "route_result": dict,                # Outcome from datastore/archive agents
    "processing_time_ms": int
}
```
