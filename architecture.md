# architecture.md — CeaseGuard Deep Architecture
> This file covers HOW the system works. README.md covers WHAT it does.
> Agents: Read this before implementing any orchestration or inter-agent communication.

---

## Agent Contracts

Every agent is a Python class with a strict interface. Agents communicate via plain Python dicts — no shared state, no global variables.

### Contract Template
```python
class AgentName:
    def __init__(self, config: dict): ...
    def run(self, input: dict) -> dict: ...
    # run() NEVER raises exceptions — always returns {"status": "error", ...} on failure
```

---

### Agent 1: Ingestion Agent
```
Role:     Pipeline entry point
Input:    {"pdf_path": str}
Output:   IngestionResult dict (see features.md F-05)
Calls:    PDFReader.extract(), LanguageDetector.detect(), ClassifierAgent.run()
Fails:    Returns status="failed" if PDF unreadable. status="partial" if extraction degraded.
Logs:     Calls audit_logger at start and after classification
```

### Agent 2: Classifier Agent
```
Role:     Core LLM classification
Input:    {"text": str, "language": str, "filename": str}
Output:   {"label": str, "confidence": float, "citation": str, "reasoning": str, "edge_case_flag": bool}
Calls:    Anthropic API (claude-sonnet-4-20250514)
Fails:    Returns label="UNCERTAIN", confidence=0.0, error="API failure"
Validates: citation must be substring of input text (post-call check)
Logs:     Nothing directly — Ingestion agent handles audit
```

### Agent 3: Datastore Agent
```
Role:     Write CEASE records to database
Input:    IngestionResult where label="CEASE"
Output:   {"status": "written" | "duplicate" | "error", "record_id": str}
Calls:    SQLite (dev) / PostgreSQL (prod)
Fails:    Returns status="error", retries 3x with backoff
Idempotent: Duplicate document_id → status="duplicate", not an error
```

### Agent 4: Archive Agent
```
Role:     Write IRRELEVANT records to flat file
Input:    IngestionResult where label="IRRELEVANT"
Output:   {"status": "archived", "filepath": str}
Calls:    File I/O (append to archive.jsonl)
Fails:    Returns status="error", logs to audit
Idempotent: Duplicate document_id → skip + log warning
```

### Agent 5: Human Escalation Agent
```
Role:     Present UNCERTAIN cases to human, collect decision
Input:    IngestionResult where label="UNCERTAIN"
Output:   {"human_decision": "CEASE"|"IRRELEVANT"|"DEFER", "decided_at": str}
Mode:     CLI prompt (MVP). Web UI (future).
DEFER:    Writes to data/deferred.jsonl for later reprocessing
```

### Agent 6: Audit Agent
```
Role:     Write-only event log. Never reads. Never fails silently.
Input:    AuditEntry dict (see data-schema.md)
Output:   None (side effect: appends to audit.jsonl)
Called by: Every other agent at every stage boundary
Fails:    Logs to stderr, continues pipeline (audit failure NEVER stops processing)
```

### Agent 7: Judge Agent (Optional)
```
Role:     Second-pass quality check on classifier output
Input:    {"classifier_output": dict, "original_text": str}
Output:   {"judge_agrees": bool, "judge_confidence": float, "correction": dict|None}
When:     Always on UNCERTAIN, 10% random on others, always on edge_case_flag=True
Prompt:   Adversarial — assume classifier is wrong, find contradiction
```

---

## Data Flow

### Happy Path — CEASE Document
```
PDF File
  ↓ pdf_reader.extract()
Raw Text
  ↓ language_detector.detect()
{text, language}
  ↓ audit_logger.log("RECEIVED")
  ↓ classifier.run()
{label="CEASE", confidence=0.91, citation="...", reasoning="..."}
  ↓ audit_logger.log("CLASSIFIED")
  ↓ [confidence >= 0.75, label=CEASE]
  ↓ datastore_agent.run()
{status="written", record_id="uuid-..."}
  ↓ audit_logger.log("ROUTED_TO_DATASTORE")
DONE
```

### Uncertain Path — Human in Loop
```
PDF File → [same ingestion steps] →
{label="UNCERTAIN", confidence=0.61}
  ↓ judge_agent.run()  [optional, but runs on UNCERTAIN]
{judge_agrees=True, correction=None}  [judge confirms uncertain]
  ↓ escalation_agent.run()
[CLI prompt shown to human]
Human enters: [1] CEASE
  ↓ {human_decision="CEASE"}
  ↓ datastore_agent.run()
  ↓ audit_logger.log("HUMAN_DECISION: CEASE")
DONE
```

### Failure Path — PDF Unreadable
```
PDF File → pdf_reader.extract() → "" (empty, status=failed)
  ↓ audit_logger.log("EXTRACTION_FAILED")
  ↓ [text length < 10 chars → abort classification]
  ↓ escalation_agent.run() with context: "PDF unreadable"
[Human sees: "Document could not be read. Manual review required."]
Human enters decision → route accordingly
  ↓ audit_logger.log("MANUAL_FALLBACK")
```

---

## Edge Cases Handled

| Scenario | Handling |
|----------|----------|
| Blank/empty PDF | status=failed → human escalation |
| Scanned image PDF (no text layer) | OCR fallback via pytesseract |
| Confidence 0.60–0.74 | Force UNCERTAIN regardless of label |
| Citation not in source text | Flag edge_case=True → judge agent |
| API timeout/error | classifier returns UNCERTAIN + error reason |
| Duplicate document_id | Datastore: return "duplicate". Archive: skip. Audit: always write. |
| DEFER from human | Write to deferred.jsonl, retry on next `--process-deferred` run |
| Very long document (>50 pages) | Chunk into 10-page sections, classify each, aggregate by majority |
| Mixed language document | Detect dominant language, note secondary in audit |
| Document mentions "cease" in non-C&D context ("cease operations", "cease trading") | Classifier prompt includes negative examples for this. Confidence should be low. |

---

## System Boundaries

**IN SCOPE:**
- Ingesting PDFs from a local folder (batch or single)
- Classifying into 3 categories
- Writing CEASE records to DB
- Writing IRRELEVANT records to flat file
- Human review CLI for UNCERTAIN
- Full audit log

**OUT OF SCOPE (Phase 2):**
- Email ingestion (receive PDF from email)
- Real-time API endpoint
- Web-based human review UI
- Integration with enterprise CRM/CMS
- Multi-user human review queue
- Authentication/authorization
- PDF generation of reports

---

## Configuration

All config in `config.yaml` (not hardcoded):
```yaml
classifier:
  model: "claude-sonnet-4-20250514"
  confidence_threshold_uncertain: 0.75
  confidence_threshold_edge_case: 0.60
  max_text_length: 50000     # chars before chunking
  
judge:
  enabled: true
  sample_rate: 0.10          # 10% of non-UNCERTAIN cases
  always_on_uncertain: true
  always_on_edge_cases: true

datastore:
  type: "sqlite"             # switch to "postgres" for prod
  path: "data/cease_records.db"
  retry_attempts: 3
  retry_backoff_seconds: 1

audit:
  path: "data/audit.jsonl"
  
archive:
  path: "data/archive.jsonl"

deferred:
  path: "data/deferred.jsonl"
```

---

## Performance Targets (NFR — see nfr.md for full detail)

| Metric | Target |
|--------|--------|
| Single document processing time | < 5 seconds (API latency included) |
| Batch (100 docs) | < 10 minutes sequential |
| Classifier accuracy (on labeled test set) | > 90% |
| False negative rate on CEASE | < 2% (missing a real C&D is the worst outcome) |
| Audit completeness | 100% — zero documents unlogged |

---

## Why This Architecture

**Q: Why not one big LLM call that does everything?**  
A: Single-agent has no audit trail, can't route to different systems, and fails catastrophically on PDF extraction errors. Multi-agent gives us testability and human-in-loop.

**Q: Why not LangChain or CrewAI?**  
A: Framework abstractions hide what's happening. For a compliance system that needs to explain itself (audit, citation, confidence), full transparency matters. Direct SDK calls = full control = full explainability.

**Q: Why SQLite for MVP?**  
A: Zero infrastructure. One file. Perfect for demo. Schema is identical to PostgreSQL — migration is a config change.

**Q: Why JSONL for audit/archive?**  
A: Append-only, one-record-per-line, grep-able, pandas-loadable, no schema migrations. Perfect for audit logs.

---

*Reference: Claude for Legal (ip-legal cease-desist skill) uses similar patterns: confidence scoring, citation extraction, approval routing. Our system adapts these patterns for mass-volume inbound processing rather than legal counsel one-off review.*
