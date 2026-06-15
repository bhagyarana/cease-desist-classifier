# architecture.md: CeaseGuard Deep Architecture
> This file covers HOW the system works. README.md covers WHAT it does.

---

## Technical Stack Overview

CeaseGuard has transitioned from a local command-line prototype to a production-grade web application deployed on Vercel:

```
┌────────────────────────────────────────────────────────┐
│                   NEXT.JS FRONTEND                     │
│         (React / Swiss Müller-Brockmann CSS)           │
└──────────────────────────┬─────────────────────────────┘
                           │ HTTP JSON Requests
┌──────────────────────────▼─────────────────────────────┐
│                 FASTAPI BACKEND ROUTER                 │
│                 (api/index.py on Uvicorn)              │
└──────────────────────────┬─────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────┐
│               STATEFUL AGENT WORKFLOW                  │
│             (agents/workflow.py Run State)             │
└──────┬───────────────────┬───────────────────┬─────────┘
       │                   │                   │
┌──────▼──────┐     ┌──────▼──────┐     ┌──────▼──────┐
│  INGESTION  │     │ CLASSIFIER  │     │    JUDGE    │
│    AGENT    │     │    AGENT    │     │    AGENT    │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └─────────┬─────────┴───────────────────┘
                 │
      ┌──────────▼──────────┐
      │  ROUTING DECISIONS  │
      └──────┬───────────┬──┘
             │           │
   ┌─────────▼──┐     ┌──▼─────────┐
   │  DATASTORE │     │   ARCHIVE  │
   │  (CEASE)   │     │(IRRELEVANT)│
   └────────────┘     └────────────┘
```

* **Frontend Layer**: Built with **Next.js (App Router)** and styled using Vanilla CSS following the 12-column Swiss grid system (Müller-Brockmann).
* **Backend Layer**: A Python **FastAPI** application running on Uvicorn, structured to compile directly into serverless lambda functions on Vercel.
* **LLM Engine**: Upgraded to **Google Gemini** using the official `google-genai` SDK. We utilize `gemini-2.5-pro` for core classification/reasoning and `gemini-2.5-flash` for translations.
* **Vector Store & RAG**: Real-time context searches powered by Gemini `text-embedding-004` and local Cosine Similarity calculations for cross-database portability.
* **Model Context Protocol (MCP)**: Exposes tool RPC interfaces for external compliance agents.

---

## Agent Contracts

Every agent is a Python class with a strict interface. Agents communicate via plain Python dicts - no shared state, no global variables.

### Contract Template
```python
class AgentName:
    def __init__(self, config: dict): ...
    def run(self, input: dict) -> dict: ...
    # run() NEVER raises exceptions: always returns error payloads on failure
```

### Agent 1: Ingestion Agent
```
Role:     Pipeline entry point
Input:    {"pdf_path": str, "filename": str}
Output:   {"text": str, "language": dict, "extraction_status": str}
Calls:    PyMuPDF (fitz) text extractor, langdetect
Fails:    Returns extraction_status="failed" if PDF unreadable.
```

### Agent 2: Classifier Agent
```
Role:     Core LLM classification using Gemini Structured Outputs
Input:    {"text": str, "language": dict, "filename": str}
Output:   {"label": str, "confidence": float, "citation": str, "reasoning": str, "edge_case_flag": bool}
Calls:    Google GenAI SDK (gemini-2.5-pro with Pydantic response_schema)
Fails:    Returns label="UNCERTAIN", confidence=0.0, reasoning="Model fallback"
Validates: Enforces strict JSON structure and verbatim citation check
```

### Agent 3: Datastore Agent
```
Role:     Write CEASE records to database
Input:    Ingestion payload where label="CEASE"
Output:   {"status": "written" | "duplicate" | "error", "record_id": str}
Calls:    tools/db.py connection pool (PostgreSQL or SQLite)
Fails:    Returns status="error", retries 3x with backoff
```

### Agent 4: Archive Agent
```
Role:     Write IRRELEVANT records to archive log
Input:    Ingestion payload where label="IRRELEVANT"
Output:   {"status": "archived" | "duplicate" | "error", "filepath": str}
Calls:    Dual writes: appends to JSONL archive and writes to archive_logs table
```

### Agent 5: Human Escalation Agent
```
Role:     Stores deferred queue reviews
Input:    Ingestion payload where label is escalated (UNCERTAIN or low confidence)
Output:   {"decision": "CEASE"|"IRRELEVANT"|"DEFER", "decided_at": str}
Calls:    Dual writes: logs to deferred.jsonl and deferred_requests table
```

### Agent 6: Audit Agent
```
Role:     Write-only pipeline event audit
Input:    AuditEntry dict (received, routed, completed logs)
Output:   None (side effect: appends to audit.jsonl and audit_logs database table)
```

### Agent 7: Judge Agent
```
Role:     Adversarial quality verification audit on high-risk classifications
Input:    {"classifier_output": dict, "original_text": str}
Output:   {"judge_agrees": bool, "correction": dict|None}
Prompt:   Adversarial prompt instructing the LLM to inspect classifications for errors
```

---

## Stateful Workflow Execution (`agents/workflow.py`)

Rather than executing linear scripts, CeaseGuard implements a **Stateful Workflow** pattern:
1. **INGEST**: Extracts PDF text, determines language. Logs a `RECEIVED` event in the audit log database.
2. **CLASSIFY**: Executes Gemini structured output classification model.
3. **JUDGE**: Runs adversarial validation if label is `UNCERTAIN`, has high risk (`edge_case_flag=True`), or based on random sample checks.
4. **ROUTE**: 
   * If the confidence score is below the threshold (`0.75`), or the label is `UNCERTAIN`, it saves the current state (including extracted text) in the audit log metadata, flags the stage as `ESCALATED`, and pauses execution.
   * If a human decision override is provided, the stage resumes from the `ROUTE` stage and writes the record to the appropriate database tables (`cease_requests` or `archive_logs`).
   * Logs a final `COMPLETED` entry in the audit database.

---

## Edge Cases Handled

| Scenario | Handling |
|----------|----------|
| Blank/empty PDF | stage = INGEST → classification label = UNCERTAIN → Escalates to Review Queue |
| Scanned image PDF (no text layer) | OCR fallback via PyMuPDF layout parsing |
| Confidence 0.60–0.74 | Force UNCERTAIN regardless of model classification label |
| Citation not in source text | Post-processing validation check → flags edge_case = True → Judge override audit |
| Database uniqueness constraint | Database Connection Proxy translates SQLite `?` to Postgres `%s` and handles `DatabaseIntegrityError` idempotently |
| Serverless file ephemerality | Audit, archive, and defer log writes are written directly to database tables (PostgreSQL / SQLite) |

---

## Configuration (`config.yaml`)

Configuration is managed in a single central file:
```yaml
classifier:
  model: "gemini-2.5-pro"
  confidence_threshold_uncertain: 0.75
  confidence_threshold_edge_case: 0.60
  max_text_chars: 50000

judge:
  enabled: true
  sample_rate: 0.10
  always_on_uncertain: true
  always_on_edge_cases: true

datastore:
  type: "sqlite"             # Set "postgres" for Vercel production
  sqlite_path: "data/cease_records.db"
  postgres_url: null         # Read from POSTGRES_URL environment variable

files:
  audit_path: "data/audit.jsonl"
  archive_path: "data/archive.jsonl"
  deferred_path: "data/deferred.jsonl"
```
