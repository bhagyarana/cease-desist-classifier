# rationale.md — Why This Solution?
> Required by the brief: "Why was this solution chosen over others?"
> This document answers that question for each major design decision.

---

## Problem Framing (First Principles)

The problem is: **high-volume document triage with zero tolerance for missed CEASE requests**.

Before picking a solution, break it down:
1. Documents arrive as scanned PDFs (variable quality)
2. Each document needs to be read and classified (NLU task)
3. Classification has legal/compliance implications (can't be wrong on CEASE)
4. Different outcomes require different actions (routing)
5. Everything must be auditable (compliance + explainability)
6. Humans must stay in the loop for ambiguous cases (risk management)

This is a **classification + routing + auditing** problem, not a simple search or Q&A problem.

---

## Solution Comparison

### Option A: Rules-Based Keyword Matching (Rejected)

**What it is:** grep for keywords like "cease", "stop", "do not contact"

**Pros:**
- Fast, cheap, no API calls
- 100% deterministic
- Easy to audit

**Cons:**
- "Cease trading" = false positive
- "Please stop sending me catalogs" = false negative (word "cease" absent)
- Cannot handle multi-language without massive keyword lists
- Cannot handle context (same word, different meaning)
- Fails on scanned documents with OCR errors

**Why rejected:** High false positive/negative rate in testing. A customer writing "I've had it, no more emails from you ever" would be missed. Legal risk too high.

---

### Option B: Fine-Tuned Classification Model (Rejected for MVP)

**What it is:** Fine-tune a smaller model (BERT, DistilBERT) on labeled C&D documents

**Pros:**
- Very fast inference
- No ongoing API costs after training
- Can run on-premise

**Cons:**
- Requires labeled training data (we don't have it at MVP)
- Fine-tuning takes weeks + ML infrastructure
- Poor on out-of-distribution documents (new languages, new phrasings)
- No citation generation capability
- No reasoning transparency

**Why rejected:** No labeled dataset, no ML infrastructure, no time for MVP. This is a Phase 2 consideration once we have classification data from the LLM-based system.

---

### Option C: Single LLM Call — "Read this PDF and classify it" (Rejected)

**What it is:** One API call with the whole document, ask the model to classify + route + audit

**Pros:**
- Simple code
- One file

**Cons:**
- No separation of concerns — testing is impossible
- No retry logic per stage
- If routing fails, classification is lost
- No audit trail during processing (only after)
- Cannot add human-in-loop cleanly
- Cannot independently test/improve each stage
- LLM handling PDF parsing, classification, routing, and DB writes = chaos

**Why rejected:** Works for demos, fails in production. Any one step failing cascades to total failure.

---

### Option D: LangChain / LlamaIndex Agent Framework (Rejected)

**What it is:** Use LangChain's agents or LlamaIndex's pipeline abstractions

**Pros:**
- Pre-built patterns for multi-agent workflows
- Large community and docs
- Quick to prototype

**Cons:**
- Abstracts away too much — hard to debug what's happening
- Compliance systems need full transparency (audit, citation validation, confidence)
- LangChain's output parsing is fragile — JSON parsing fails silently
- Framework updates break agent behavior without warning
- For a capstone that needs to explain every decision: "the LangChain agent decided" is not an acceptable audit entry
- Context management is hidden, making it hard to reason about what the LLM sees

**Why rejected:** Compliance systems require explainability at every layer. Frameworks trade transparency for convenience. Wrong trade for this use case.

---

### ✅ Option E: Direct Anthropic SDK + Custom Multi-Agent (CHOSEN)

**What it is:** Python classes, one per agent, communicating via dicts, calling Anthropic API directly

**Why this wins:**

1. **Full transparency:** Every API call is visible. Every prompt is versioned. Every output is validated.

2. **Testability:** `classifier.py` can be unit tested in isolation with mock API responses. No framework magic to work around.

3. **Auditability:** We control exactly what goes into the audit log and when. No framework auto-logging that we can't customize.

4. **Human-in-loop:** Easy to inject a human decision at any point in the pipeline. Frameworks make this awkward.

5. **Citation validation:** We can assert the citation is in the source text. Frameworks don't do this.

6. **Confidence calibration:** We control the prompt and can enforce thresholds in code, not in configuration files we don't understand.

7. **Scalability path:** Each agent is stateless. Swap SQLite for PostgreSQL by changing one config value. Add a queue by wrapping `main.py`. Zero framework lock-in.

8. **Explainability for presentation:** We can explain every line of code. "The classifier agent calls claude-sonnet-4-20250514 with this exact prompt, validates the citation, checks confidence thresholds, and routes accordingly." Clean story.

---

## Why Claude (vs GPT-4, Gemini)?

1. **Classification quality:** Claude's structured JSON output is more reliable in testing. Fewer hallucinated fields.

2. **Citation accuracy:** Claude's "here is the exact text" capability is stronger than alternatives for verbatim extraction tasks.

3. **Multi-language handling:** Claude handles multilingual documents well without a separate translation step.

4. **Context length:** Handles 30+ page documents without chunking in most cases (200K context).

5. **Prompt adherence:** Claude follows structured output instructions reliably. "Return ONLY JSON" is respected consistently.

6. **Reference:** Claude for Legal's `ip-legal` plugin uses the same model for cease-and-desist triage. Production-validated pattern.

---

## Why SQLite First?

- Zero infrastructure for demo/capstone
- Schema is identical to PostgreSQL (migration = config change)
- 1-10 documents/minute throughput is more than sufficient for MVP
- No networking, no auth, no separate service to manage
- `data/cease_records.db` can be opened in DB Browser for visual inspection during demos

---

## Why JSONL for Audit/Archive?

- Append-only by nature (no accidental overwrites)
- One record per line = easy to grep, tail, and count
- Valid JSON = loadable by pandas, DuckDB, any analytics tool
- No schema migrations — add a field, old records just don't have it
- Human-readable in a text editor
- Compliance-friendly: immutable, simple, archivable

---

## Reference: Anthropic's IP Legal Cease-Desist Skill

Anthropic's own `claude-for-legal` repo includes a `cease-desist` skill in the `ip-legal` plugin. Key patterns we borrowed:

- **Enforcement posture → confidence thresholds:** Their "aggressive / measured / conservative" spectrum maps to our confidence threshold tuning
- **Approval routing → human escalation:** Their per-letter-type approval routing maps to our UNCERTAIN → human pipeline  
- **Citation in every output:** Their skill always includes "why this decision" — we adopted the same pattern
- **Practice profile (CLAUDE.md) → config.yaml:** Their enterprise-specific context document maps to our config system

Key difference: their skill is designed for legal counsel reviewing ~10 documents/week with full legal analysis. Our system is designed for compliance operations processing ~hundreds/day with routing automation. We optimize for throughput + audit completeness, they optimize for legal reasoning quality.
