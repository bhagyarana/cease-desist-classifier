# features.md: CeaseGuard Feature Breakdown

---

## Implementation Status

- [x] F-01 · PDF Text Extraction
- [x] F-02 · Language Detection
- [x] F-03 · Audit Logger
- [x] F-04 · Classifier Agent
- [x] F-05 · Ingestion Agent
- [x] F-06 · Datastore Agent
- [x] F-07 · Archive Agent
- [x] F-08 · Human Escalation Agent
- [x] F-09 · Main Orchestrator
- [x] F-10 · Judge Agent
- [x] F-11 · Multi-language Support
- [x] F-12 · Web Dashboard Home
- [x] F-13 · Ingestion Console (Labor Illusion)
- [x] F-14 · Operator Workstation (RAG Recommendation)
- [x] F-15 · History Search Console

---

## PHASE 1: Foundation

### F-01 · PDF Text Extraction
* **What**: Given a PDF file path, extract all readable text. Handles both text-based PDFs and scanned image PDFs (OCR fallback).
* **Touchpoints**: `tools/pdf_reader.py`, `tests/test_ingestion.py`

### F-02 · Language Detection
* **What**: Given extracted text, detect the dominant language.
* **Touchpoints**: `tools/language_detect.py`

### F-03 · Audit Logger
* **What**: A transaction write logger. Appends stage events dynamically to the database and logs backups to `data/audit.jsonl`.
* **Touchpoints**: `agents/audit.py`, `tools/db.py`

---

## PHASE 2: Core Intelligence

### F-04 · Classifier Agent
* **What**: Uses Google Gemini `gemini-2.5-pro` with structured outputs via Pydantic model response schemas to extract classification, confidence, citation, and edge case flags.
* **Touchpoints**: `agents/classifier.py`

### F-05 · Ingestion Agent
* **What**: Entry controller orchestrating text extraction, language translation, and LLM classification.
* **Touchpoints**: `agents/ingestion.py`

---

## PHASE 3: Routing Agents

### F-06 · Datastore Agent
* **What**: Writes classified cease-and-desist metadata to database records (`cease_requests` table).
* **Touchpoints**: `agents/datastore.py`, `tools/db.py`

### F-07 · Archive Agent
* **What**: Archives irrelevant legal documents to flat JSONL files and writes logs to `archive_logs` database tables.
* **Touchpoints**: `agents/archive.py`

### F-08 · Human Escalation Agent
* **What**: Logs escalated cases requiring operator overrides to the database queue (`deferred_requests` table).
* **Touchpoints**: `agents/escalation.py`

---

## PHASE 4: Orchestration & Web Features

### F-09 · Main Orchestrator
* **What**: Orchestrates the stateful pipeline (`agents/workflow.py`) execution flow and resolves final routing stages.
* **Touchpoints**: `agents/workflow.py`, `main.py`

### F-10 · Judge Agent
* **What**: Runs second-pass adversarial check-offs on high-risk classifications and uncertain cases.
* **Touchpoints**: `agents/judge.py`

### F-11 · Multi-language Support
* **What**: Automatically translates non-English citations and reasoning back into English using Gemini model functions.
* **Touchpoints**: `agents/classifier.py`

### F-12 · Web Dashboard Home
* **What**: Displays real-time metrics (Total Ingested, Cease count, Archived count, Pending Reviews) and lists the recent pipeline activity logs.
* **Touchpoints**: `app/page.tsx`

### F-13 · Ingestion Console (Labor Illusion)
* **What**: Uploads legal documents and displays step-by-step progress checklist logs as the backend pipeline runs.
* **Touchpoints**: `app/ingest/page.tsx`, `api/index.py`

### F-14 · Operator Workstation (RAG Recommendation)
* **What**: Dual-pane interface to review escalated documents, run real-time RAG similarity checks, and submit overrides with reasoning justification.
* **Touchpoints**: `app/review/page.tsx`, `tools/rag_service.py`

### F-15 · History Search Console
* **What**: Database search and filter interface to audit transaction histories.
* **Touchpoints**: `app/history/page.tsx`
