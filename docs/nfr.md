# nfr.md — Non-Functional Requirements

---

## 1. Performance

| Requirement | Target | Measurement |
|-------------|--------|-------------|
| Single document end-to-end | < 5 seconds | `processing_time_ms` in audit logs |
| API call latency (Gemini) | < 2.5 seconds p95 | Logged per call |
| DB write time | < 50ms | Logged per write |
| UI Page Load Latency | < 300ms | Next.js serverless metric |

**Implementation**:
* Measure latency at every stage of the stateful workflow and log in the database.
* Use `gemini-2.5-flash` for translations and speed-intensive helpers; reserve `gemini-2.5-pro` for core classification logic.

---

## 2. Reliability & Correctness

| Requirement | Target | Measurement |
|-------------|--------|-------------|
| Classifier accuracy on test set | > 92% | Automated testing validation |
| False negative rate (miss real C&D) | < 1% | Verified CEASE test subset |
| Audit log completeness | 100% | Cross-reference uploaded docs vs log rows |
| Data loss on agent crash | Zero | Stateful transaction logs + dual writes |

**Implementation**:
* Confidence thresholds catch ambiguous items (score `< 0.75`) and auto-escalate them to the Operator Review workstation.
* Every stage boundary logs audit checkpoints. If a crash occurs at any point, the document state is saved in the database.
* SQLite connection pooling is configured with timeouts (`timeout=30`), and retry decorators handle PostgreSQL transaction conflicts.

---

## 3. Security

| Requirement | Implementation |
|-------------|---------------|
| API key confidentiality | Environment variables (`GEMINI_API_KEY`, `DATABASE_URL`) loaded at startup. |
| Zero plain text logging of PII | Text logs truncate PII. Excerpts are isolated in database columns. |
| SQL injection protection | Parameterized SQL query placeholders handled dynamically by `DBConnectionProxy`. |
| Audit trail immutability | Append-only database constraints. No edit or delete routes are exposed on the API. |

---

## 4. Scalability

### Architectural Portability
CeaseGuard can transition between local execution and high-scale cloud production by editing `config.yaml`:
```
[SQLite Local Dev]  ──►  [PostgreSQL Serverless Prod]
   - config: type="sqlite"  - config: type="postgres"
   - SQLite db file         - Neon/Supabase cloud DB
   - Local JSONL files      - Automated DB persistence
```

### Why this design scales:
1. **Stateless Agents**: Agents do not maintain in-memory states between runs. All state is passed via the FastAPI request payload.
2. **Serverless Portability**: Running on Vercel Python runtime allows scale-to-zero when idle and immediate auto-scaling during high-traffic bursts.
3. **Database Connection Proxy**: Simplifies database queries and abstracts SQLite/PostgreSQL parameters dynamically, eliminating engine-specific SQL dependencies.

---

## 5. Observability (SQL-Powered Compliance Logs)

Audit logging has been upgraded from raw file parsing to SQL query endpoints. Since all audit records are written to the `audit_logs` table, operators can run compliance and debugging audits directly using SQL:

```sql
-- Find all CEASE request filings processed today
SELECT * FROM audit_logs 
WHERE stage = 'COMPLETED' AND classification = 'CEASE' 
  AND created_at >= CURRENT_DATE;

-- Find all failed pipeline stages
SELECT document_id, filename, error FROM audit_logs 
WHERE stage = 'FAILED';

-- List all human decision overrides
SELECT document_id, human_override, metadata FROM audit_logs 
WHERE human_override IS NOT NULL;
```

---

## 6. Explainability

Every classification is fully explainable. The audit logs preserve:
1. **Citation**: Verbatim string excerpt from the PDF.
2. **Reasoning**: One-sentence LLM output.
3. **Confidence**: Calibrated numeric score.
4. **Judge Review**: Results from the adversarial QC check.
5. **Operator Note**: Override rationale if a human made the final call.
