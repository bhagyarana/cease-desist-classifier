# CeaseGuard: AI Cohort Bootcamp Learnings

This document summarizes the engineering learnings and production patterns adopted from the **AI Bootcamp Modules** that have been integrated into the CeaseGuard platform.

---

## 1. Structured Output Enforcement (Gemini SDK Integration)
* **Problem**: Traditional prompt engineering suffers from formatting errors, hallucinations, and parsing crashes when mapping raw LLM responses to JSON.
* **Bootcamp Lesson**: Leveraging native **Structured Outputs** via model configurations is much more robust than post-facto regex parsing.
* **Implementation**: We refactored `ClassifierAgent` to use the official `google-genai` SDK and defined our output contract as a Pydantic `ClassificationResult` class:
  ```python
  from pydantic import BaseModel

  class ClassificationResult(BaseModel):
      label: str  # CEASE, UNCERTAIN, IRRELEVANT
      confidence: float
      citation: str
      reasoning: str
      edge_case_flag: bool
  ```
  By passing this schema directly to the Gemini API via the `response_schema` parameter of `client.models.generate_content`, we guarantee that every classification returns a valid JSON matching the schema, with 0% parsing failures.

---

## 2. Stateful Workflow Orchestration (LangGraph Patterns)
* **Problem**: Complex business logic involves multiple conditional routing stages, quality audits, and manual human escalations which quickly lead to spaghetti code if implemented linearly.
* **Bootcamp Lesson**: Treat the agent pipeline as a **state-chart state machine** that operates on a shared state dictionary.
* **Implementation**: We implemented the workflow manager in `agents/workflow.py` tracking stages like `INGEST`, `CLASSIFY`, `JUDGE`, and `ROUTE`.
* **Stateful Interrupts**: We solved the human-in-the-loop problem by pausing execution at the `ROUTE` stage if confidence is low, saving the text and intermediate parameters in the audit log metadata, and resuming the stateful run from the paused `ROUTE` stage when an operator submits a manual verdict over the Web console.

---

## 3. Database-Agnostic RAG & Vector Similarities
* **Problem**: Traditional vector databases (or PostgreSQL `pgvector`) are powerful but require dedicated server management or compiled native dependencies that are tricky to install or fail in Vercel's serverless runtime environments.
* **Bootcamp Lesson**: For moderately sized collections (e.g. historical C&D cases), running **local vector calculations** on top of a standard database is highly performant, portable, and completely database-agnostic.
* **Implementation**:
  * We generate document summary embeddings using Google's `text-embedding-004` model.
  * We store the resulting floats as a serialized JSON string in a standard text column in the `document_embeddings` table.
  * To search similar documents, we load the database records and compute the **Cosine Similarity** directly in Python. This works identically in both local SQLite files and production cloud PostgreSQL without needing compile-time pgvector plugins.

---

## 4. Model Context Protocol (MCP) Server
* **Problem**: Agents need access to internal tools and databases, but tightly coupling tools inside prompts limits reusability and scalability.
* **Bootcamp Lesson**: Model Context Protocol (MCP) defines a standardized JSON-RPC communication bridge between LLM clients and local tools.
* **Implementation**: In `tools/mcp_server.py`, we created an MCP server that exposes CeaseGuard tools (`classify_document`, `lookup_compliance_history`, `check_vector_similarity`). This enables AI assistants to directly interact with our pipeline databases and classification code.

---

## 5. Growth Design Psychology (User-Centered Production Patterns)
* **Problem**: AI processing pipelines can take several seconds to complete, causing users to feel the interface is frozen, leading to page-exits or double-submits.
* **Bootcamp Lesson**: Apply cognitive design principles to optimize operator experience.
* **Implementation**:
  * **Labor Illusion**: In the `Ingest Console`, we display a sequential check-off list of execution steps (parsing layout, detecting language, calling Gemini model functions, checking vector similarities). This shows the user that the AI is working hard, making the wait feel satisfying and productive.
  * **Zeigarnik Effect**: We placed a real-time pending review badge in the sidebar. This incomplete-task alert prompts operators to visit the review workstations and keep the queue clear.
  * **Aesthetic-Usability Effect**: An elite Swiss grotesque typography style (Inter) with a 12-column grid and a hotkeyable grid guide. Operators respect a layout that is visually premium, which improves perceived usability and trust in the AI verdicts.
