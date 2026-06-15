# CHANGELOG.md - CeaseGuard Change History
> Every change must be documented here before merging.
> Format: date · change type · files affected · why · agent impact
> Agents: Read the last 5 entries before starting any session.

---

## How to Add an Entry

```markdown
## [vX.Y.Z] - YYYY-MM-DD

### Changed | Added | Fixed | Removed
- **File:** `path/to/file.py`
- **What:** One sentence describing the change
- **Why:** One sentence explaining the reason
- **Agent Impact:** Which agents are affected and how
- **Lesson ref:** L-XXX (if this change was triggered by a lesson)
```

---

## [v0.1.0] - 2025-06-08 (Project Kickoff)

### Added
- **File:** `README.md`
- **What:** Full project overview, architecture diagram, tech stack, quick start
- **Why:** Capstone project initialization. Project brief analyzed.
- **Agent Impact:** All agents - this is the source of truth for system intent

### Added
- **File:** `features.md`
- **What:** 11 features (F-01 to F-11) with input/output contracts, acceptance tests, file references
- **Why:** Need a step-by-step build plan that any agent can follow without ambiguity
- **Agent Impact:** All agents use this as the build specification

### Added
- **File:** `lessons.md`
- **What:** 8 pre-seeded lessons (L-001 to L-008) from anticipated/common mistakes, plus patterns that work
- **Why:** Document institutional knowledge before it's lost. Prevent known failure modes.
- **Agent Impact:** All agents must read lessons.md before implementing any feature

### Added
- **File:** `CHANGELOG.md`
- **What:** This file. Change tracking initialized.
- **Why:** Every change must be traceable. Agents must know what changed and why.
- **Agent Impact:** All agents must write an entry here after every change

### Added
- **File:** `docs/architecture.md`
- **What:** Deep agent contracts, data flow, edge cases, system boundaries
- **Why:** README covers the what. architecture.md covers the how.
- **Agent Impact:** Primary reference for orchestration logic

### Added
- **File:** `docs/agent-prompts.md`
- **What:** All system prompts, versioned, with rationale for each instruction
- **Why:** Prompts are code. They must be versioned, documented, tested.
- **Agent Impact:** classifier.py, judge.py read prompts from here

### Added
- **File:** `docs/data-schema.md`
- **What:** Full SQL schema, JSONL schemas, field definitions
- **Why:** Schema-first design prevents costly DB migrations later
- **Agent Impact:** datastore.py, archive.py, audit.py all reference this

### Added
- **File:** `docs/nfr.md`
- **What:** Non-functional requirements (performance, security, reliability, scalability)
- **Why:** Required by brief. Also needed to pass the "additional rationale" section of presentation.
- **Agent Impact:** All agents - NFRs constrain implementation choices

### Added
- **File:** `docs/rationale.md`
- **What:** Why this solution over alternatives (LangChain, monolithic LLM, rules engine)
- **Why:** Required by brief. Presentation needs this.
- **Agent Impact:** Reference only - no code impact

---

## [v0.1.1] - 2026-06-10

### Added
- **File:** `docs/extra-work.md`
- **What:** Post-MVP backlog for optional enhancements after the main functionality is complete
- **Why:** Keep non-core improvements separated from the build order so implementation stays focused
- **Agent Impact:** Planning reference only - no runtime impact

## [v0.1.2] - 2026-06-10

### Added
- **File:** `agents/classifier.py`
- **What:** Added multilingual heuristic support and English citation translation for non-English documents
- **Why:** Implement the F-11 post-MVP enhancement and keep audit output usable for multilingual cases
- **Agent Impact:** Classifier now handles basic Spanish and French phrase translation in offline mode, and uses the translation prompt when Anthropic is available

### Added
- **File:** `agents/prompts.py`
- **What:** Exposed the multilingual translation prompt constant used by the classifier
- **Why:** Keep prompt definitions centralized and versioned with the code that consumes them
- **Agent Impact:** Classifier prompt flow now supports citation translation as a first-class step

### Fixed
- **File:** `agents/ingestion.py`, `main.py`, `agents/escalation.py`
- **What:** Replaced deprecated `datetime.utcnow()` usage with timezone-aware UTC timestamps
- **Why:** Remove Python deprecation warnings and keep timestamp formatting consistent across the pipeline
- **Agent Impact:** Ingestion, routing, and escalation logs now emit timezone-aware UTC timestamps

## [v0.1.3] - 2026-06-10

### Changed
- **File:** `docs/extra-work.md`
- **What:** Removed completed post-MVP items and rewrote the remaining backlog as narrower, more actionable work
- **Why:** Keep deferred work aligned with the current codebase state and easier to prioritize after MVP
- **Agent Impact:** Planning/reference only; no runtime impact

## [v0.1.4] - 2026-06-10

### Added
- **File:** `app.py`
- **What:** Added a Streamlit review console for uploading PDFs, seeing classification results, and making inline human decisions for UNCERTAIN cases
- **Why:** Provide a more intuitive operator experience than the CLI prompt while reusing the same routing and audit pipeline
- **Agent Impact:** Human escalation now has a browser-based path; CLI behavior remains available for automation

### Changed
- **File:** `main.py`
- **What:** Shared audit-entry helpers were extracted and routing now accepts an optional human decision from the UI
- **Why:** Keep CLI and UI flows aligned without duplicating routing logic
- **Agent Impact:** Orchestration supports both CLI escalation and browser-based review

### Changed
- **File:** `README.md`, `requirements.txt`
- **What:** Documented the browser UI startup flow and added the Streamlit dependency
- **Why:** Make the project easier to run locally and clarify the primary user-facing entry point
- **Agent Impact:** Setup instructions now include the browser UI

## [v0.1.5] - 2026-06-10

### Added
- **File:** `app.py`
- **What:** Added a batch upload tab with a results table, summary metrics, and non-blocking handling for UNCERTAIN documents
- **Why:** Support the highest-impact workflow for operators who process multiple PDFs at once
- **Agent Impact:** Streamlit now supports single-document review and batch processing in the same interface

### Changed
- **File:** `main.py`
- **What:** Routing can now skip human escalation for batch runs and mark UNCERTAIN documents as `needs_review`
- **Why:** Keep batch processing non-blocking while preserving the shared audit trail
- **Agent Impact:** Orchestration now supports both interactive review and queue-style batch classification

## [v0.1.6] - 2026-06-10

### Added
- **File:** `app.py`
- **What:** Added a recent history tab that reads the append-only audit log and shows the latest entries in a structured table
- **Why:** Give operators a quick in-app view of what the system just processed without opening raw log files
- **Agent Impact:** Streamlit now includes a history surface alongside single review and batch review

## [v0.1.7] - 2026-06-10

### Added
- **File:** `app.py`
- **What:** Upgraded the history pane into a searchable and filterable case browser with date, confidence, route, label, stage, and language controls
- **Why:** Make it easy to find the right case quickly and turn the audit log into an operational tool
- **Agent Impact:** Operators can now search, filter, sort, and inspect past cases in the UI

## [v0.1.8] - 2026-06-10

### Added
- **File:** `app.py`
- **What:** Added a guided UNCERTAIN review workspace with highlighted source text, a decision panel, and optional reviewer notes
- **Why:** Give operators the evidence, context, and action controls they need in one place for faster, higher-confidence reviews
- **Agent Impact:** Streamlit now routes UNCERTAIN cases through a browser-native review flow instead of the CLI prompt

---

## [v2.1.0-GEMINI] - 2026-06-15

### Added
- **File:** `app/layout.tsx`, `app/page.tsx`, `app/ingest/page.tsx`, `app/review/page.tsx`, `app/history/page.tsx`
- **What:** Replaced the Streamlit console with a high-performance Next.js React frontend styled with a 12-column Swiss design grid and grocery baseline.
- **Why:** Provide a world-class operator experience, incorporating Labor Illusion, Zeigarnik queues, and optical ink adjustments.
- **Agent Impact:** Interactive workstation for operators replaces Streamlit; handles batch uploads, context-rich reviews, and RAG logs.

### Added
- **File:** `api/index.py`
- **What:** Created a FastAPI backend router mapping Next.js frontend HTTP calls to python agent workflow executions.
- **Why:** Connect Next.js React client with our Python agents securely in serverless Vercel hostings.
- **Agent Impact:** Connects agents to browser traffic.

### Changed
- **File:** `agents/classifier.py`
- **What:** Upgraded LLM engine to Google Gemini `gemini-2.5-pro` (and `gemini-2.5-flash` for translations) using official `google-genai` SDK and Pydantic structured output response schemas.
- **Why:** Guarantees 100% JSON parsing safety and provides structured extraction context.
- **Agent Impact:** Eliminates regex output parsing crashes.

### Added
- **File:** `tools/db.py`, `agents/audit.py`, `agents/archive.py`, `agents/escalation.py`
- **What:** Migrated file-based storage logs (audit.jsonl, archive.jsonl, deferred.jsonl) to relational tables. Created `DBConnectionProxy` to swap SQLite parameters (`?`) with PostgreSQL parameters (`%s`) dynamically at runtime.
- **Why:** Enable persistent database writes in ephemeral serverless cloud platforms.
- **Agent Impact:** All agents now support SQLite/PostgreSQL write transactions.

### Added
- **File:** `tools/rag_service.py`
- **What:** Created vector index matching service using `text-embedding-004` and local Python cosine calculations.
- **Why:** Provide context-rich similarity suggestions in the Operator Review workstation.
- **Agent Impact:** Offers similar case lookup during reviews.

### Added
- **File:** `tools/mcp_server.py`
- **What:** Implemented Model Context Protocol (MCP) server exposing tools over JSON-RPC.
- **Why:** Standardize agent integrations with external tools.
- **Agent Impact:** Exposes pipeline commands to MCP clients.

---

## [Unreleased] - Template for future entries

```
## [v2.2.0] - YYYY-MM-DD

### Added
- **File:** `path/to/file.py`
- **What:** One sentence describing the change
- **Why:** One sentence explaining the reason
- **Agent Impact:** Which agents are affected and how
```

---

*Rule: No code ships without a CHANGELOG entry. No exception.*
