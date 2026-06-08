# CHANGELOG.md — CeaseGuard Change History
> Every change must be documented here before merging.
> Format: date · change type · files affected · why · agent impact
> Agents: Read the last 5 entries before starting any session.

---

## How to Add an Entry

```markdown
## [vX.Y.Z] — YYYY-MM-DD

### Changed | Added | Fixed | Removed
- **File:** `path/to/file.py`
- **What:** One sentence describing the change
- **Why:** One sentence explaining the reason
- **Agent Impact:** Which agents are affected and how
- **Lesson ref:** L-XXX (if this change was triggered by a lesson)
```

---

## [v0.1.0] — 2025-06-08 (Project Kickoff)

### Added
- **File:** `README.md`
- **What:** Full project overview, architecture diagram, tech stack, quick start
- **Why:** Capstone project initialization. Project brief analyzed.
- **Agent Impact:** All agents — this is the source of truth for system intent

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
- **Agent Impact:** All agents — NFRs constrain implementation choices

### Added
- **File:** `docs/rationale.md`
- **What:** Why this solution over alternatives (LangChain, monolithic LLM, rules engine)
- **Why:** Required by brief. Presentation needs this.
- **Agent Impact:** Reference only — no code impact

---

## [Unreleased] — Template for future entries

```
## [v0.2.0] — YYYY-MM-DD

### Fixed
- **File:** `agents/classifier.py`
- **What:** Added citation validation against source text
- **Why:** L-003 — classifier was hallucinating citations
- **Agent Impact:** classifier.py now raises ValueError if citation not in text
- **Lesson ref:** L-003

### Added
- **File:** `agents/audit.py`
- **What:** Stage-based logging (received, classified, routed)
- **Why:** L-002 — single end-of-pipeline log lost data on crashes
- **Agent Impact:** ingestion.py now passes audit_logger instance through pipeline
- **Lesson ref:** L-002
```

---

*Rule: No code ships without a CHANGELOG entry. No exception.*
