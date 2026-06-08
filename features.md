# features.md — CeaseGuard Feature Breakdown
> Build order is strict. Each feature is a self-contained, testable unit.
> Do NOT skip ahead. Each feature is a dependency for the next.

---

## How to Read This File

Each feature block has:
- **What** — plain English
- **Input / Output** — exact contract
- **Acceptance Test** — how you know it works
- **Files touched** — so the agent knows exactly what to create/edit
- **Do NOT** — common mistakes to avoid

---

## PHASE 1 — Foundation (Must work before anything else)

---

### F-01 · PDF Text Extraction

**What:** Given a PDF file path, extract all readable text. Handle both text-based PDFs and scanned image PDFs (OCR fallback).

**Input:** `str` — path to a `.pdf` file  
**Output:** `str` — extracted text content (may be messy, that's OK)

**Acceptance Test:**
```
python tools/pdf_reader.py --file tests/sample_docs/sample_cease.pdf
# Must print: non-empty text to stdout
# Must NOT crash on a blank/corrupt PDF — return empty string + log warning
```

**Files touched:**
- `tools/pdf_reader.py` (CREATE)
- `tests/test_ingestion.py` (CREATE — 3 test cases: text PDF, blank PDF, corrupt PDF)

**Implementation hints:**
- Use `PyMuPDF` (`import fitz`) as primary reader
- If text length < 50 chars, try pytesseract OCR as fallback
- Strip headers/footers (page numbers, watermarks) — they confuse the classifier

**Do NOT:**
- Do not crash the whole pipeline if one PDF fails
- Do not return `None` — always return `str` (empty string on failure)

---

### F-02 · Language Detection

**What:** Given extracted text, detect the language. Return ISO 639-1 code (`en`, `es`, `fr`, etc.)

**Input:** `str` — extracted text  
**Output:** `dict` — `{"language": "en", "confidence": 0.99}`

**Acceptance Test:**
```
python tools/language_detect.py --text "Please stop sending us marketing emails"
# Output: {"language": "en", "confidence": 0.99}
```

**Files touched:**
- `tools/language_detect.py` (CREATE)

**Implementation hints:**
- Use `langdetect` library (pip install langdetect)
- If confidence < 0.7 → return `{"language": "unknown", "confidence": 0.0}`
- `unknown` language → classifier still runs but prompt includes warning

**Do NOT:**
- Do not make an API call for language detection — keep it local/fast

---

### F-03 · Audit Logger (Build this THIRD — used by everything)

**What:** A write-only append logger. Every document processed MUST get an audit entry, even if classification fails.

**Input:** `dict` — structured audit record  
**Output:** Appends one JSON line to `data/audit.jsonl`

**Audit record schema:**
```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "document_id": "uuid-v4",
  "filename": "customer_request_001.pdf",
  "classification": "CEASE | UNCERTAIN | IRRELEVANT | ERROR",
  "confidence": 0.92,
  "citation": "Customer states: 'I request you immediately cease...'",
  "language": "en",
  "agent_trace": ["ingestion", "classifier", "datastore"],
  "human_override": null,
  "error": null,
  "processing_time_ms": 1243
}
```

**Acceptance Test:**
```
python agents/audit.py --test
# Must create data/audit.jsonl
# Must be valid JSON on each line
# Must handle concurrent writes without corruption (use file lock)
```

**Files touched:**
- `agents/audit.py` (CREATE)
- `data/audit.jsonl` (auto-created on first run)

**Do NOT:**
- Do not let audit logging failure stop document processing
- Do not write audit AFTER processing — write at each stage (start, classify, route, done)
- Do not delete or overwrite old entries

---

## PHASE 2 — Core Intelligence

---

### F-04 · Classifier Agent

**What:** The heart of the system. Takes document text → returns classification label + confidence + citation.

**Input:**
```python
{
  "text": str,           # extracted document text
  "language": str,       # ISO code from F-02
  "filename": str        # for context
}
```

**Output:**
```python
{
  "label": "CEASE" | "UNCERTAIN" | "IRRELEVANT",
  "confidence": float,   # 0.0 to 1.0
  "citation": str,       # exact excerpt that drove the decision (max 200 chars)
  "reasoning": str,      # one sentence explanation
  "edge_case_flag": bool # True if the doc has unusual patterns
}
```

**Acceptance Test:**
```
python agents/classifier.py --text "I formally request you cease all direct marketing communications"
# Must return label=CEASE, confidence > 0.85

python agents/classifier.py --text "Invoice attached for your records"  
# Must return label=IRRELEVANT, confidence > 0.80

python agents/classifier.py --text "Please review the attached and advise"
# Must return label=UNCERTAIN, confidence < 0.75
```

**Files touched:**
- `agents/classifier.py` (CREATE)
- `docs/agent-prompts.md` → CLASSIFIER_SYSTEM_PROMPT section (UPDATE)

**Classifier System Prompt (v1 — documented in agent-prompts.md):**
```
You are a compliance document classifier for a financial services enterprise.
Your job is to read customer documents and classify them into exactly one of:

CEASE — The customer is formally requesting the enterprise stop all direct communications.
Look for: explicit requests to stop, cease, desist, unsubscribe from all contact, DNC (Do Not Contact), opt-out.

IRRELEVANT — The document has nothing to do with communication opt-out requests.
Look for: invoices, complaints about products, general inquiries, legal disputes unrelated to communication consent.

UNCERTAIN — You cannot determine with confidence whether this is a CEASE request.
Use this when: the document is ambiguous, partially damaged/unreadable, or mixes cease and non-cease content.

RULES:
1. Return ONLY valid JSON. No prose.
2. Always include a citation — the exact phrase from the document that most influenced your decision.
3. Confidence must reflect genuine uncertainty — do not round to 1.0.
4. If the document is in a language other than English, still classify but note in reasoning.
5. If confidence would be below 0.60, always return UNCERTAIN regardless of leaning.
```

**Confidence thresholds:**
```
>= 0.85 → use as-is
0.75-0.84 → use label but flag for spot-check
0.60-0.74 → force UNCERTAIN
< 0.60 → force UNCERTAIN + flag as edge case
```

**Do NOT:**
- Do not hallucinate citations — the citation must be a substring of the input text
- Do not return CEASE on documents that only mention "cease" in a different context
- Do not skip the confidence calibration thresholds

---

### F-05 · Ingestion Agent (Orchestrates F-01 + F-02 + F-04)

**What:** The pipeline entry point. Takes a PDF path, runs extraction → language detection → classification → returns structured result.

**Input:** `str` — PDF file path  
**Output:**
```python
{
  "document_id": "uuid",
  "filename": "doc.pdf",
  "text": str,
  "language": {"language": "en", "confidence": 0.99},
  "classification": {
    "label": "CEASE",
    "confidence": 0.92,
    "citation": "...",
    "reasoning": "...",
    "edge_case_flag": False
  },
  "status": "success" | "partial" | "failed"
}
```

**Acceptance Test:**
```
python agents/ingestion.py --pdf tests/sample_docs/sample_cease.pdf
# Must return complete JSON with all fields populated
# Must set status=partial if PDF extraction partially failed
```

**Files touched:**
- `agents/ingestion.py` (CREATE)

**Do NOT:**
- Do not let one agent failure cascade — catch and set status=partial

---

## PHASE 3 — Routing Agents

---

### F-06 · Datastore Agent (CEASE cases)

**What:** When classification = CEASE, write a record to the database.

**Input:**
```python
{
  "document_id": str,
  "filename": str,
  "date_received": str,     # ISO 8601
  "classification": dict,   # full classifier output
  "language": str,
  "customer_info": str      # extracted name/address if present
}
```

**Output:** `{"status": "written", "record_id": str}`

**DB Table: `cease_requests`**
```sql
CREATE TABLE cease_requests (
  id TEXT PRIMARY KEY,          -- document_id (uuid)
  filename TEXT NOT NULL,
  date_received TEXT NOT NULL,
  classification_label TEXT NOT NULL,
  confidence REAL NOT NULL,
  citation TEXT,
  language TEXT,
  customer_info TEXT,
  agent_processed TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  human_reviewed INTEGER DEFAULT 0,
  human_override TEXT
);
```

**Acceptance Test:**
```
python agents/datastore.py --test
# Must create data/cease_records.db
# Must write a test record
# Must reject duplicate document_ids (idempotent)
```

**Files touched:**
- `agents/datastore.py` (CREATE)
- `tools/db.py` (CREATE)
- `docs/data-schema.md` (UPDATE — add SQL schema)

**Do NOT:**
- Do not store raw PDF binary in the DB
- Do not allow duplicate records for same document_id

---

### F-07 · Archive Agent (IRRELEVANT cases)

**What:** When classification = IRRELEVANT, write a record to a flat file (JSONL).

**Input:** Same as F-06  
**Output:** Appends one line to `data/archive.jsonl`

**Archive record schema:**
```json
{
  "document_id": "uuid",
  "filename": "doc.pdf",
  "date_received": "2025-01-15T10:30:00Z",
  "classification": "IRRELEVANT",
  "confidence": 0.91,
  "citation": "Invoice #4521 attached",
  "archived_at": "2025-01-15T10:30:05Z"
}
```

**Acceptance Test:**
```
python agents/archive.py --test
# Must create data/archive.jsonl
# Must append (not overwrite) on each run
```

**Files touched:**
- `agents/archive.py` (CREATE)

---

### F-08 · Human Escalation Agent (UNCERTAIN cases)

**What:** When classification = UNCERTAIN, present the document summary to a human agent via CLI. Wait for human decision. Record the decision.

**Input:** Classification result with `label=UNCERTAIN`  
**Human sees:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 HUMAN REVIEW REQUIRED
Document: customer_request_042.pdf
Language: English
Confidence: 0.61 (UNCERTAIN)
AI Reasoning: Document contains ambiguous opt-out language mixed with product complaint

Key excerpt:
  "...I want you to stop sending me these notices about my account
   but please continue the service..."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Your decision:
  [1] CEASE — Treat as cease request
  [2] IRRELEVANT — Not a cease request
  [3] DEFER — Need more information
Enter choice (1/2/3):
```

**Output:**
```python
{
  "human_decision": "CEASE" | "IRRELEVANT" | "DEFER",
  "agent_by": "human_operator_id",  # placeholder for now
  "decided_at": "ISO timestamp"
}
```

**Acceptance Test:**
```
python agents/escalation.py --test-mode
# In test mode, auto-responds with decision=CEASE
# Must log the decision to audit trail
```

**Files touched:**
- `agents/escalation.py` (CREATE)

**Do NOT:**
- Do not auto-decide for the human (even if you think you know the answer)
- DEFER cases must be re-queued, not dropped

---

## PHASE 4 — Orchestration

---

### F-09 · Main Orchestrator

**What:** The `main.py` entry point that wires all agents together.

**Flow:**
```
main.py --pdf doc.pdf
  → F-05 Ingestion Agent
  → F-03 Audit: log start
  → Route by label:
      CEASE      → F-06 Datastore Agent → F-03 Audit: log CEASE
      IRRELEVANT → F-07 Archive Agent   → F-03 Audit: log IRRELEVANT
      UNCERTAIN  → F-08 Escalation      → human decides → re-route → F-03 Audit: log final
  → Print summary to console
```

**CLI interface:**
```bash
python main.py --pdf path/to/doc.pdf
python main.py --batch path/to/folder/    # process all PDFs in folder
python main.py --audit                    # show last 10 audit entries
```

**Files touched:**
- `main.py` (CREATE)

---

## PHASE 5 — Optional / Judge Agent

---

### F-10 · Judge Agent (Quality Control)

**What:** A second-pass agent that reviews the classifier's output for a sample of documents (or all UNCERTAIN ones). Validates: is the citation actually in the text? Does the confidence match the reasoning?

**Input:** Classifier output + original text  
**Output:**
```python
{
  "judge_agrees": bool,
  "judge_confidence": float,
  "correction": None | {"new_label": str, "reason": str}
}
```

**When it runs:**
- Always on UNCERTAIN cases before human escalation
- On 10% random sample of CEASE/IRRELEVANT (configurable)
- On any case flagged as `edge_case_flag=True`

**Files touched:**
- `agents/judge.py` (CREATE)

---

### F-11 · Multi-language Support

**What:** When `language != "en"`, translate the key citation to English before logging. Full document does NOT need translation — just the citation and reasoning.

**Implementation:** Add translation step in classifier prompt when language != en.

**Files touched:**
- `agents/classifier.py` (UPDATE — add translation instruction)
- `docs/agent-prompts.md` (UPDATE — add multilingual prompt variant)

---

## Build Order Summary

```
F-01 PDF Extraction
F-02 Language Detection  
F-03 Audit Logger         ← Build early, use everywhere
F-04 Classifier Agent     ← Core intelligence
F-05 Ingestion Agent      ← Wires F-01+F-02+F-04
F-06 Datastore Agent      ← CEASE routing
F-07 Archive Agent        ← IRRELEVANT routing
F-08 Escalation Agent     ← UNCERTAIN routing
F-09 Main Orchestrator    ← Wire everything
F-10 Judge Agent          ← Optional: QC layer
F-11 Multi-language       ← Optional: translation
```

---

## Testing Checklist

Before submitting, verify all of these pass:

```bash
python -m pytest tests/ -v
# F-01: 3 PDF extraction tests (normal, blank, corrupt)
# F-02: 3 language tests (English, Spanish, unknown)
# F-03: Audit append test, concurrent write test
# F-04: 5 classifier tests (clear CEASE, clear IRRELEVANT, ambiguous, multi-language, edge case)
# F-06: DB write + duplicate rejection
# F-07: Archive append
# F-09: End-to-end with mock PDF
```

---

*Last updated: Capstone kickoff. Update this file when a feature changes.*
