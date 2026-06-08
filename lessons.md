# lessons.md — CeaseGuard: Mistakes & Learnings Log
> This file is written AFTER things go wrong, not before.
> Every entry here is a real mistake that cost time. Read it before starting any new feature.
> Agents: read this file before every implementation session.

---

## Format

```
### L-[number] · [Short title]
**When:** Which feature/phase this happened
**What went wrong:** Plain description
**Root cause:** Why it happened
**Fix applied:** What we changed
**Rule going forward:** One-line rule to prevent recurrence
```

---

## Active Lessons

---

### L-001 · Empty string vs None from PDF extractor crashes classifier

**When:** F-01 → F-04 pipeline  
**What went wrong:** `pdf_reader.py` returned `None` on a corrupt PDF. The classifier tried to call `.lower()` on it and crashed. The audit log never fired because the error propagated all the way up.  
**Root cause:** F-01 spec said "return empty string" but the first implementation returned `None`.  
**Fix applied:** Added `assert isinstance(text, str)` at the top of `classifier.py`. Made `pdf_reader.py` return `""` in all failure paths.  
**Rule going forward:** Every tool/agent function must have a typed return — never `None` where `str` is expected. Use `Optional[str]` only if the caller handles `None` explicitly.

---

### L-002 · Audit log written AFTER routing — loses data on agent crash

**When:** F-03 + F-09 integration  
**What went wrong:** Initial design wrote one audit entry at the end. When the datastore agent crashed mid-write, no audit entry existed for that document. It was effectively lost.  
**Root cause:** Treated audit as a post-processing step rather than a persistent state machine.  
**Fix applied:** Audit now writes at 3 points: (1) document received, (2) classification complete, (3) routing complete. Each entry has a `stage` field.  
**Rule going forward:** Audit entries are written at every stage boundary, not just at completion. Think of audit as a checkpoint system, not a report.

---

### L-003 · Classifier hallucinated a citation not in the document

**When:** F-04 testing  
**What went wrong:** The LLM returned a citation: `"Customer explicitly requests cessation of all communications"` but that exact phrase wasn't in the document. The classifier was paraphrasing, not quoting.  
**Root cause:** The system prompt said "include a citation" but didn't specify it must be verbatim from the text.  
**Fix applied:** 
1. Updated system prompt: *"Citation must be an exact substring of the input text. Do not paraphrase."*
2. Added post-processing validation: `assert citation in document_text`
3. If validation fails → flag as `edge_case=True` and route to human.  
**Rule going forward:** Always validate LLM outputs against the source data. Never trust that "citation" means "verbatim quote" without enforcement.

---

### L-004 · Confidence score was always 0.95 — model was not calibrated

**When:** F-04 testing on varied documents  
**What went wrong:** The model returned 0.95 confidence on almost everything, including genuinely ambiguous documents. The 0.75 threshold for UNCERTAIN was useless because nothing went below 0.85.  
**Root cause:** The prompt didn't instruct the model to use the full 0.0–1.0 range. LLMs default to high confidence when not prompted otherwise.  
**Fix applied:** Added to system prompt: *"Calibrate confidence honestly. A truly ambiguous document should score 0.55-0.65. Reserve 0.90+ for documents with explicit, unambiguous cease language."* Added few-shot examples with varied confidence scores.  
**Rule going forward:** Confidence calibration must be explicitly instructed in the prompt. Add few-shot examples that demonstrate the full range of scores.

---

### L-005 · SQLite locked on concurrent batch processing

**When:** F-06 + F-09 batch mode  
**What went wrong:** Processing a folder of 20 PDFs simultaneously caused SQLite `database is locked` errors. 3 records were lost.  
**Root cause:** `tools/db.py` opened a connection per-call without connection pooling or retry logic.  
**Fix applied:** 
1. Added `timeout=30` to SQLite connection.
2. Added exponential backoff retry (3 attempts) in `datastore.py`.
3. For batch mode, switched to sequential processing with progress bar (concurrency is a Phase 2 optimization).  
**Rule going forward:** SQLite is single-writer. For MVP, process documents sequentially. Concurrency needs PostgreSQL or a queue system.

---

### L-006 · DEFER cases from human escalation were silently dropped

**When:** F-08 implementation  
**What went wrong:** When a human chose `[3] DEFER`, the code logged it to audit but didn't re-queue the document. It was never processed again.  
**Root cause:** DEFER path wasn't implemented — it was a TODO that got forgotten.  
**Fix applied:** DEFER now writes to `data/deferred.jsonl` with a `retry_after` timestamp. Added a `--process-deferred` flag to `main.py`.  
**Rule going forward:** Every output state must have an explicit handler. "TODO" in routing code = guaranteed data loss.

---

### L-007 · Language detection was run on PDF headers, not document body

**When:** F-02 + F-05 integration  
**What went wrong:** A Spanish document was detected as English because the PDF had English headers (`CONFIDENTIAL`, `Page 1 of 3`, `Internal Use Only`) that appeared before the body text.  
**Root cause:** `pdf_reader.py` returned ALL text including metadata and headers. Language detection ran on the first 500 chars which were headers.  
**Fix applied:**
1. `pdf_reader.py` now strips common header/footer patterns.
2. Language detection runs on the middle 60% of the text (skip first 20% and last 20%).  
**Rule going forward:** When detecting document properties (language, topic), skip boilerplate header/footer regions. Use middle body text.

---

### L-008 · Judge agent agreed with classifier 100% of the time (useless)

**When:** F-10 implementation  
**What went wrong:** The judge agent used the same base prompt as the classifier. Of course it agreed — it was essentially the same model being asked the same question.  
**Root cause:** Judge was a copy-paste of classifier with "review this" prepended.  
**Fix applied:** Judge agent now uses adversarial prompting: *"Assume the classifier is wrong. Find evidence that contradicts its classification. Only agree if you cannot find contradictory evidence."*  
**Rule going forward:** A judge agent must be adversarially prompted. Same prompt = rubber stamp = waste of tokens.

---

## Pending Lessons (Suspected but not yet confirmed)

These are patterns we suspect will be problems. Fill in the blanks when they materialize.

- **Suspected:** Very long documents (30+ pages) will blow the context window. Need chunking strategy.
- **Suspected:** Documents with handwriting (common in scanned requests) will confuse PyMuPDF. Need OCR fallback testing.
- **Suspected:** Multilingual documents (part English, part another language) will get wrong language detection.

---

## Patterns That Worked Well

These are things we did RIGHT. Keep doing them.

**P-001 · Test with edge cases first**  
Before testing the happy path, test blank PDFs, corrupt PDFs, and empty strings. This caught L-001 early.

**P-002 · Log everything to JSONL**  
JSONL is append-only, grep-able, and compatible with every analytics tool. Never regretted this choice.

**P-003 · One agent = one file = one responsibility**  
When something broke, we always knew exactly which file to open. No debugging across 500-line monoliths.

**P-004 · Schema first, code second**  
Writing `data-schema.md` before writing `datastore.py` saved at least one full rewrite.

---

*Agents: After fixing a bug, write a lesson here BEFORE closing the task. A lesson not written is a lesson that will repeat.*
