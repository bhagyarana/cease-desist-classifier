# Extra Work — Post-MVP Ideas
> Use this file once the main functionality is complete.
> These items are intentionally outside the core build order in `features.md`.

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

1. PDF cleanup and fixture coverage.
2. Human review flow improvements.
3. Configurable thresholds and reporting.
4. Export and packaging work.
5. Concurrency, CI, and deployment hardening.