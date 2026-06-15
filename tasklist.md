# CeaseGuard Enhancements Tasklist

This tasklist outlines the step-by-step roadmap to upgrade CeaseGuard into a production-grade multi-agent document intelligence platform with a world-class UI, deployed on Vercel.

---

## Phase 1: Backend & Agent Upgrades (AI Cohort Modules)
- [x] **Google Gemini API Integration**
  - [x] Update `requirements.txt` to include `google-genai` and remove `anthropic`.
  - [x] Update `agents/classifier.py` to import and use the official Google GenAI SDK (`client.models.generate_content`) targeting `gemini-2.5-pro` for classification.
  - [x] Implement a Pydantic schema for the output contract and pass it via `response_schema` to enforce guaranteed JSON format.
  - [x] Set up `gemini-2.5-flash` for helper translation queries.
- [x] **PostgreSQL Database Datastore**
  - [x] Implement Postgres connection and queries in `tools/db.py` fallback to SQLite if PostgreSQL is not configured.
  - [x] Create database tables for logs: `audit_logs`, `archive_logs`, and `deferred_requests` (removing file I/O dependencies for serverless contexts).
  - [x] Write DB table migration/initialization functions in python.
- [x] **Stateful Workflow (LangGraph Pattern)**
  - [x] Implement `agents/workflow.py` representing a stateful agent pipeline using LangGraph or a clean python state manager.
  - [x] Support pipeline execution states and pause-on-uncertain transitions for manual review.
- [x] **Similarity Search & RAG (Module 2)**
  - [x] Create `tools/rag_service.py` to index document summaries using Gemini `text-embedding-004` and run cosine similarity.
  - [x] Fetch similar historical C&D cases to assist operator decisions in real-time.
- [x] **Model Context Protocol (MCP) Integration (Module 4)**
  - [x] Create `tools/mcp_server.py` exposing compliance lookup, classification and historical case queries.

---

## Phase 2: Design System & Web App Scaffold
- [x] **Vite/Next.js Project Setup**
  - [x] Initialize the React project inside the current directory (Next.js App Router).
  - [x] Set up `vercel.json` configuration to handle frontend routing and map `/api/*` to python serverless handlers.
- [x] **Swiss Design System (Müller-Brockmann Grid)**
  - [x] Create `globals.css` with 12-column grid tokens, baseline height grid (8px increments), and margins.
  - [x] Import and load the Inter Google Webfont for grotesque sans typography.
  - [x] Define the Swiss compliance color palette (cream/light gray backgrounds, charcoal text, and deep teal accent).
- [x] **Grid Overlay & Optical Alignment**
  - [x] Build the interactive grid overlay component (`G` key toggles visibility showing columns and baseline guide lines).
  - [x] Add runtime optical alignment JS for display headings to adjust text ink positioning.

---

## Phase 3: Interactive Operator Console
- [x] **Dashboard Home (`/`)**
  - [x] Layout metric cards showing: total parsed, compliance rate, pending review count, and average confidence.
  - [x] Display historical volume charts and recent processing events list.
- [x] **Ingestion Console (`/ingest`)**
  - [x] Implement drag-and-drop document upload.
  - [x] Display step-by-step progress checklist (Labor Illusion) as agents run (Ingestion -> Language -> Classifier -> Judge -> Route).
- [x] **Review Workspace (`/review`)**
  - [x] Design the layout: Left Column shows document metadata, extracted text highlight context, and RAG similar recommendations. Right Column displays the decision panel (CEASE, IRRELEVANT, DEFER) and reviewer notes.
  - [x] Use Progressive Disclosure to keep the interface clean while allowing operators to expand deep raw json audit logs or OCR full-text.
- [x] **History & Audit Log (`/history`)**
  - [x] Search and filter console showing all processed events, confidence distributions, and human overrides.

---

## Phase 4: Verification & Deployment
- [x] **Automated Testing**
  - [x] Fix sys path resolving in python tests.
  - [x] Write tests for the Postgres database connections and workflow transitions.
- [x] **Vercel Cloud Deployment**
  - [x] Deploy a preview branch on Vercel.
  - [x] Link database environment variables (`DATABASE_URL`, `GEMINI_API_KEY`) and run live ingestion checks.
