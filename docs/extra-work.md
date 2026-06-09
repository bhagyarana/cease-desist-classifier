# Extra Work — Post-MVP Ideas
> Use this file once the main functionality is complete.
> These items are intentionally outside the core build order in `features.md`.

---

## High Impact First Roadmap

These are the customer-facing improvements most likely to increase adoption, reduce manual work, and make the product feel polished.

1. Batch upload with a results table.
   - Upload multiple PDFs at once.
   - Show per-document status, label, confidence, citation, and route.
   - Add a clear success/failure summary at the top of the page.

2. Recent audit/history pane.
   - Show the latest processed documents inside the UI.
   - Let users inspect the audit trail without leaving the app.
   - Include timestamp, filename, classification, confidence, and final routing decision.

3. Search and filters for past cases.
   - Filter by date, label, confidence range, filename, and reviewer action.
   - Make it easy to answer operational questions quickly.

4. Inline review experience for UNCERTAIN cases.
   - Keep the citation and extracted text visible beside the decision controls.
   - Make the human choice obvious and fast.

5. One-click export.
   - Export filtered results to CSV or JSON for compliance and reporting.
   - Preserve the audit trail format so downstream systems can ingest it easily.

---

## Remaining Quality Work

- Expand fixture coverage for damaged PDFs, mixed-language documents, and ambiguous opt-out language.
- Make PDF cleanup more deterministic by stripping repeated headers, footers, page numbers, and watermarks before classification.
- Add stronger audit assertions so each pipeline stage can be traced from ingestion to final route.

## Remaining Product Work

- Build a more polished human review flow for uncertain cases, including clearer summaries and better operator prompts.
- Add batch run summaries with counts for CEASE, IRRELEVANT, UNCERTAIN, and failed documents.
- Add a lightweight review dashboard or CLI summary for recent processing outcomes.

## Remaining Operational Work

- Make routing thresholds and behavior configurable without editing code.
- Add throughput, error-rate, and confidence-distribution reporting.
- Add structured export paths for downstream compliance or case-management systems.
- Package the project for simpler local setup and repeatable execution.

## Remaining Hardening Work

- Add stronger duplicate handling and idempotency checks across routing agents.
- Expand concurrency coverage for audit and datastore writes.
- Add CI checks that run the acceptance tests automatically.
- Add deployment notes for a production-style environment if the project grows beyond a capstone demo.

---

## Suggested Order After MVP

1. Batch upload with results table.
2. Recent audit/history pane.
3. Search and filters for past cases.
4. Export and reporting improvements.
5. PDF cleanup and fixture coverage.
6. Human review flow refinements.
7. Configurable thresholds and operational hardening.