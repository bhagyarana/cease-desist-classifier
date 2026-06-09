# CeaseGuard — Cease & Desist Document Intelligence System
> Capstone Project | Multi-Agent AI Orchestration | Internal Project

---

## What This Is

An intelligent multi-agent system that automates the classification and routing of inbound **Cease & Desist** PDF documents. Human agents currently read every document manually to decide if it's a real C&D request or not. This system replaces that manual step with AI classification, automated routing, audit logging, and human escalation — while keeping humans in the loop for uncertain cases.

**Three outcomes for every document:**
- `CEASE` → Write to datastore, trigger compliance workflow
- `IRRELEVANT` → Archive to flat file
- `UNCERTAIN` → Route to human agent for review

---

## Problem Statement (verbatim from brief)

> Cease & Desist is a formal request from customers to stop all kinds of direct communication to them from the enterprise. The enterprise receives scanned PDF documents of customer requests. In current process, human agents must manually read the documents and figure out if that request is a "Cease" or "No Cease" request and then process it accordingly.

**Key requirements from brief:**
- Classify into 3 categories: `Cease`, `Uncertain – Manual Review`, `Irrelevant`
- Cease → write to datastore (date received, document name, etc.)
- Irrelevant → write to flat file (archive agent)
- Uncertain → present to human agent
- ALL cases → audit log with explanation
- Optional: multi-language support, dedicated review/judge agent

**Expected coverage:**
- Multiple agents
- Human in the loop
- Database interaction by agents
- Auditing

**Additional rationale required:**
- Citation behind how documents are categorized
- Confidence score behind categorization
- Edge case coverage
- Why this solution over others
- Solution scalability
- NFR implementation

---

## Architecture Overview

```
                    ┌─────────────────────────────┐
                    │      INGESTION AGENT         │
                    │  Reads PDF → extracts text   │
                    │  Detects language            │
                    └────────────┬────────────────┘
                                 │
                    ┌────────────▼────────────────┐
                    │    CLASSIFIER AGENT          │
                    │  CEASE / UNCERTAIN / IRREL.  │
                    │  Returns: label + confidence │
                    │  + citation excerpt          │
                    └────────────┬────────────────┘
                    ┌────────────┼─────────────────┐
                    │            │                  │
          ┌─────────▼──┐  ┌─────▼──────┐  ┌───────▼──────┐
          │  DATASTORE  │  │  HUMAN     │  │  ARCHIVE     │
          │  AGENT      │  │  ESCALATION│  │  AGENT       │
          │  (CEASE)    │  │  (UNCERTAIN│  │  (IRRELEVANT)│
          └─────────────┘  └─────┬──────┘  └──────────────┘
                                 │ Human decides
                    ┌────────────▼────────────────┐
                    │       AUDIT AGENT            │
                    │  Logs EVERY case with reason │
                    │  Confidence, agent trace     │
                    └─────────────────────────────┘
```

---

## Repository Structure

```
cease-desist-agent/
│
├── README.md               ← You are here
├── features.md             ← Feature list + build order
├── lessons.md              ← Mistakes & learnings log
├── CHANGELOG.md            ← Every change documented
│
├── docs/
│   ├── architecture.md     ← Deep architecture + agent contracts
│   ├── agent-prompts.md    ← All system prompts (versioned)
│   ├── data-schema.md      ← DB schema + flat file format
│   ├── nfr.md              ← Non-functional requirements
│   └── rationale.md        ← Why this approach vs others
│
├── agents/
│   ├── ingestion.py        ← PDF → text extraction
│   ├── classifier.py       ← Core classification logic
│   ├── datastore.py        ← DB write agent (CEASE cases)
│   ├── archive.py          ← Flat file agent (IRRELEVANT)
│   ├── escalation.py       ← Human-in-loop handler
│   ├── audit.py            ← Audit logger (ALL cases)
│   └── judge.py            ← Optional: review agent
│
├── tools/
│   ├── pdf_reader.py       ← PDF text extraction util
│   ├── language_detect.py  ← Language detection
│   └── db.py               ← SQLite/Postgres abstraction
│
├── tests/
│   ├── test_classifier.py
│   ├── test_ingestion.py
│   ├── test_audit.py
│   └── sample_docs/        ← Test PDFs (synthetic)
│
├── data/
│   ├── cease_records.db    ← SQLite datastore
│   ├── archive.jsonl       ← Flat file for irrelevant docs
│   └── audit.jsonl         ← Full audit log
│
└── main.py                 ← Entry point: process a PDF
```

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your API key
echo "ANTHROPIC_API_KEY=your_key" > .env

# 3. Launch the browser UI
streamlit run app.py

# 4. Or process a single document from the CLI
python main.py --pdf path/to/document.pdf

# 5. Watch the audit log
tail -f data/audit.jsonl
```

The browser UI is the easiest way to review documents: upload a PDF, see the classification summary, and make the human decision inline for UNCERTAIN cases.

---

## Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| LLM | Claude claude-sonnet-4-20250514 | Best classification + citation quality |
| PDF Parsing | PyMuPDF (fitz) | Fast, handles scanned docs |
| Language Detection | langdetect | Lightweight, offline |
| Datastore | SQLite → PostgreSQL path | Simple start, scales |
| Audit Log | JSONL flat file | Append-only, grep-able |
| Orchestration | Python + Anthropic SDK | Direct control, no framework lock-in |
| Human UI | Streamlit review console + CLI fallback | Simple, user-friendly operator flow |

---

## Key Design Decisions

1. **No LangChain/LlamaIndex** — Direct SDK calls. Full transparency, no magic.
2. **Each agent = one Python class** — Easy to test, swap, or mock individually.
3. **Confidence threshold = 0.75** — Below this → UNCERTAIN regardless of label.
4. **Audit log is sacred** — Every document gets logged even on agent failure.
5. **Human always wins** — If human overrides classifier, that label sticks and feeds lessons.md.

---

## Reference: Claude for Legal — IP Legal Cease-Desist Skill

Anthropic's `ip-legal` plugin includes a `cease-desist` skill that handles **outbound** C&D letter drafting and **inbound** C&D triage. Key patterns borrowed:

- **Enforcement posture config** → maps to our confidence threshold tuning
- **Approval routing** → maps to our human escalation agent
- **Citation in every output** → maps to our `citation` field in classifier output
- **Practice profile (CLAUDE.md)** → maps to our `config.yaml` with enterprise-specific context
- **Matter workspace isolation** → maps to our per-document audit trail

Our use case differs: we handle **mass inbound volume** (not legal counsel reviewing one-offs), so we optimize for throughput + audit completeness over legal drafting quality.

---

## Documents in this Repo

| File | Purpose |
|------|---------|
| `README.md` | Project overview, architecture, quickstart |
| `features.md` | Feature list, build order, acceptance criteria |
| `lessons.md` | Mistakes made, patterns learned, do-nots |
| `CHANGELOG.md` | Every change with date, reason, agent impact |
| `docs/architecture.md` | Agent contracts, data flow, edge cases |
| `docs/agent-prompts.md` | All system prompts (versioned) |
| `docs/data-schema.md` | All data structures |
| `docs/nfr.md` | Non-functional requirements |
| `docs/rationale.md` | Why this solution |

---

*Built for capstone project | Do not share code/data/artifacts to restricted networks.*
