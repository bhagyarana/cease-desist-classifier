# Extra Work: Post-MVP Ideas

This document outlines the backlog of future operational improvements and production features for CeaseGuard, built on top of our completed Next.js + FastAPI version.

---

## 1. Completed Post-MVP Roadmap Items

- [x] **Batch upload with a results table**: Document ingestion accepts file processing with progress checklists.
- [x] **Recent audit/history pane**: Pipeline logs and metric counts are fetched directly in the Dashboard overview.
- [x] **Search and filters for past cases**: Filter logs by keyword search and classification verdict.
- [x] **Inline review workstation**: Dual-pane workspace showing extracted text, RAG similarity metrics, and manual override forms.

---

## 2. Advanced Backlog & Production Hardening

### Concurrency & Performance
- **Queue-Based Processing**: Transition from direct serverless processing to a queue (e.g. Redis / Celery or AWS SQS) to support high-volume batch processing without request timeouts.
- **WebSocket Streaming**: Stream agent execution status checkpoints from the FastAPI workflow to the Next.js client in real-time, removing simulated Labor Illusion timings.

### Machine Learning & OCR
- **Advanced OCR Fallback**: Integrate cloud OCR engines (like Google Cloud Vision API) to accurately parse scanned, handwritten C&D letters.
- **Embeddings Fine-Tuning**: Fine-tune custom document embeddings to improve RAG similarity searches.

### Operations & Security
- **Authentication & Roles**: Implement NextAuth or Auth0 to restrict access to the Operator workstation to authorized compliance personnel.
- **One-Click CSV Export**: Add a download button on the History table to export query results in standard CSV/JSON format for downstream compliance audits.
- **Enterprise SIEM Integration**: Forward audit log transactions to enterprise logging frameworks (like Datadog or Splunk).