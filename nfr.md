# nfr.md — Non-Functional Requirements
> Required by the Wells Fargo brief. Also needed for the "additional rationale" section.
> Each NFR has a target, measurement method, and implementation approach.

---

## 1. Performance

| Requirement | Target | Measurement |
|-------------|--------|-------------|
| Single document end-to-end | < 5 seconds | `processing_time_ms` in audit log |
| Batch (100 docs) | < 10 minutes | Timer on `main.py --batch` |
| API call latency (Anthropic) | < 3 seconds p95 | Logged per call |
| DB write time | < 100ms | Logged per write |
| Audit log write | < 10ms | Never a bottleneck |

**Implementation:**
- Measure `processing_time_ms` at every stage, log to audit
- For batch: sequential by default (safe for SQLite), parallel with PostgreSQL
- Set Anthropic SDK timeout to 30 seconds, retry once on timeout

---

## 2. Reliability & Correctness

| Requirement | Target | Measurement |
|-------------|--------|-------------|
| Classifier accuracy on labeled test set | > 90% | Manual eval on 50 synthetic docs |
| False negative rate (miss a real CEASE) | < 2% | Manual eval on CEASE test set |
| False positive rate (wrong CEASE call) | < 5% | Manual eval on IRRELEVANT test set |
| Audit log completeness | 100% | Cross-check doc count vs audit entries |
| Data loss on agent crash | Zero | Retry + deferred queue |

**Implementation:**
- Confidence threshold at 0.75 catches borderline cases → human review
- Audit log written at RECEIVED stage (before any processing) guarantees completeness
- Retry logic in datastore agent (3 attempts, exponential backoff)
- DEFER queue for human decisions that need more info

---

## 3. Security

| Requirement | Implementation |
|-------------|---------------|
| API key not in code | Loaded from `.env` via `python-dotenv` |
| No PDF content logged to console | All text truncated in DEBUG logs at 100 chars |
| No PII in plain text logs | customer_info field is optional, flagged sensitive |
| Audit log is append-only | File opened in `"a"` mode. No delete function exposed. |
| SQLite access controlled by file permissions | Stored in `data/` dir with restricted permissions |

**Note:** For production deployment, replace SQLite with PostgreSQL behind enterprise auth. All audit logs should be routed to enterprise SIEM.

---

## 4. Scalability

**Current design (MVP):**
- Sequential processing
- SQLite single-file database
- Local file storage
- Handles ~500-1000 documents/day comfortably

**Scale path (Phase 2 — no code changes needed to agent logic):**
```
SQLite → PostgreSQL         (change config.yaml: datastore.type = "postgres")
Local files → S3/Blob       (add storage adapter in tools/storage.py)
Sequential → Queue-based    (add SQS/RabbitMQ adapter in main.py)
Single machine → K8s pods   (agents are stateless — scale horizontally)
```

**Why this design is scalable:**
- Each agent is stateless (no shared memory, no class-level state)
- All state is in the DB or JSONL files (swappable to cloud storage)
- Config-driven: no hardcoded environment assumptions
- Agent contracts are fixed — internals can be replaced without changing callers

---

## 5. Maintainability

| Practice | Implementation |
|----------|---------------|
| Every change documented | CHANGELOG.md required entry |
| Mistakes captured | lessons.md living document |
| Prompts versioned | agent-prompts.md with version history |
| Schema-first | data-schema.md before code |
| One agent per file | Clear ownership |
| Typed inputs/outputs | Python type hints throughout |
| Test coverage | pytest for all agents |

---

## 6. Observability (Audit = Compliance + Debugging)

The audit log (`data/audit.jsonl`) serves two purposes:

**Compliance purpose:**
- Every document is logged with the classification decision
- Citations show WHY the decision was made
- Human overrides are recorded with timestamp and operator
- This log is the answer to "how was this document classified?"

**Debugging purpose:**
- `stage` field shows exactly where in the pipeline a document failed
- `error` field captures exception messages
- `agent_trace` shows which agents ran
- `processing_time_ms` helps identify slow stages

**Querying the audit log:**
```bash
# Find all CEASE documents today
grep '"classification": "CEASE"' data/audit.jsonl | grep "2025-01-15"

# Find all failed documents
grep '"stage": "ERROR"' data/audit.jsonl

# Find all human overrides
grep '"human_override"' data/audit.jsonl | grep -v 'null'

# Count by classification
cat data/audit.jsonl | python -c "
import sys, json
from collections import Counter
c = Counter(json.loads(l)['classification'] for l in sys.stdin if 'COMPLETED' in l)
print(dict(c))
"
```

---

## 7. Explainability (Required by Brief)

Every classification must be explainable. The audit log provides:

1. **Citation** — verbatim text from document that drove the decision
2. **Reasoning** — one-sentence LLM explanation
3. **Confidence** — numeric score (0.0–1.0)
4. **Edge case flag** — whether the document had unusual patterns
5. **Judge review** — whether a second pass was done and what it found
6. **Human override** — if a human changed the AI's decision

This enables: "For document X, the AI classified it as CEASE with 92% confidence because the customer wrote: [citation]. A judge agent confirmed. No human override."

---

## 8. Multilingual Support

**Phase 1 (MVP):** Classify documents in any language using Claude's multilingual capability. Confidence may be lower for non-English documents. Language is logged in all records.

**Phase 2:** Add translation of key fields (citation, reasoning) to English for audit log readability while preserving original language citation in the primary record.

**Supported languages (via Claude):** English, Spanish, French, German, Portuguese, Mandarin, Hindi, Arabic, and others — Claude handles these natively without a translation step.

**Implementation note:** Language detection (F-02) uses `langdetect`, which is offline and fast. The classifier itself handles multilingual docs — no separate translation pipeline needed for classification.
