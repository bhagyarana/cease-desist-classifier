# rationale.md — Why This Solution?
> Required by the brief: "Why was this solution chosen over others?"
> This document answers that question for each major design decision.

---

## Technical Stack Selection

### 1. Why Google Gemini (vs Anthropic / OpenAI)?
We transitioned from Anthropic to **Google Gemini** using the official `google-genai` SDK:
* **Native Structured Outputs**: Gemini supports passing a Pydantic class schema directly to the model configuration (`response_schema` parameter). The API forces the model to conform strictly to the schema structure, achieving a 100% success rate on JSON parsing.
* **Dual Model Efficiencies**: We split tasks based on complexity. `gemini-2.5-pro` handles the complex reasoning, semantic citations, and adversarial auditing. `gemini-2.5-flash` handles the quick translation requests, minimizing latency and API token costs.
* **Context Scaling**: Google Gemini supports an industry-leading context window, allowing us to ingest extremely long documents (e.g. 50+ pages) without performance degradation.

---

### 2. Why Next.js (React) + FastAPI (Python)?
Rather than utilizing basic frameworks like Streamlit, we built a hybrid **Next.js + FastAPI** application:
* **Production-Grade Frontends**: Streamlit is excellent for simple data scripts but lacks layout flexibility and custom CSS styling. Next.js gives us absolute control over the visual presentation, allowing us to implement a strict 12-column Swiss design grid (Müller-Brockmann system) and custom typographic scaling.
* **Growth Psychology Adaptations**: Next.js client state lets us easily design interactive micro-animations:
  * **Labor Illusion**: Sequential checklists showing active agent operations in real-time.
  * **Zeigarnik Effect**: Direct sidebar notification badges showing pending reviews to encourage completion.
  * **Aesthetic-Usability**: Clean margins, baseline rhythms, and a toggleable grid overlay (`G` key).
* **Python Agent Compatibility**: Our classification and ingestion logic requires Python libraries (PyMuPDF, langdetect). FastAPI acts as a high-performance, async routing layer to run these agents and easily maps to Next.js routes using Vercel rewrites.

---

### 3. Why PostgreSQL + SQLite Connection Proxy?
* **SQLite for Local Dev**: Zero setup, single-file DB. Perfect for developer speed.
* **PostgreSQL for Production**: Necessary for Vercel serverless functions. Vercel runs in ephemeral environments, meaning write actions to local files (like SQLite DB or JSONL files) are lost on function restart. PostgreSQL provides a persistent cloud data layer.
* **The DB Connection Proxy Solution**: We wrote a custom proxy wrapper `DBConnectionProxy` in `tools/db.py`. It dynamically translates SQL placeholder syntax between SQLite (`?`) and PostgreSQL (`%s`) at runtime. This allows us to use identical agent database code in both local development and production cloud deploys.

---

### 4. Why Local Cosine Similarity (RAG)?
* **Portability**: Storing embeddings as serialized JSON strings and running cosine similarity in Python allows us to run RAG vector matching on ANY database engine without compile-time plugins (like `pgvector`). This ensures our system is 100% serverless-portable and easy to test offline.

---

## Reference: Anthropic's IP Legal Cease-Desist Skill

Anthropic's `claude-for-legal` repository includes a `cease-desist` skill in the `ip-legal` plugin. Key patterns we adapted:
* **Confidence thresholds**: Threshold mapping (forces manual review on uncertainty) ensures high compliance safety.
* **Citation in every output**: Prompts instruct the model to return a verbatim citation, which is validated in code.
* **Approval routing**: Resuming workflows from intermediate stages to keep humans in the loop.

*Key difference*: Their system is built for legal counsel reviewing small volumes with manual drafting. CeaseGuard is optimized for compliance operations, handling hundreds of inbound files daily with automated classification, routing, and SQL audit trail logging.
