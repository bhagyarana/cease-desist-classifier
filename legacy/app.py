import json
import tempfile
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

import streamlit as st

from agents.audit import AuditAgent
from agents.ingestion import IngestionAgent
from main import build_completed_audit_entry, build_received_audit_entry, iso_timestamp, load_config, route_result
from tools.db import initialize_sqlite


st.set_page_config(
    page_title="CeaseGuard Review Console",
    page_icon="CG",
    layout="wide",
    initial_sidebar_state="expanded",
)


APP_CSS = """
<style>
    :root {
        --bg: #f4efe6;
        --panel: #fffaf3;
        --panel-strong: #ffffff;
        --text: #1f2937;
        --muted: #5b6472;
        --border: #e7ded0;
        --accent: #0f766e;
        --accent-2: #c2410c;
        --success: #166534;
        --warning: #b45309;
        --danger: #b91c1c;
    }

    .stApp {
        background:
            radial-gradient(circle at top left, rgba(15, 118, 110, 0.14), transparent 30%),
            radial-gradient(circle at top right, rgba(194, 65, 12, 0.11), transparent 24%),
            linear-gradient(180deg, #f8f3ea 0%, #f3efe7 100%);
        color: var(--text);
    }

    .hero {
        background: linear-gradient(135deg, rgba(255,255,255,0.94), rgba(255,250,243,0.9));
        border: 1px solid var(--border);
        border-radius: 24px;
        padding: 1.5rem 1.6rem;
        box-shadow: 0 18px 45px rgba(31, 41, 55, 0.08);
        margin-bottom: 1rem;
    }

    .hero h1 {
        margin: 0 0 0.35rem 0;
        font-size: 2.2rem;
        letter-spacing: -0.03em;
    }

    .hero p {
        margin: 0;
        color: var(--muted);
        font-size: 1rem;
        line-height: 1.55;
    }

    .panel {
        background: rgba(255,255,255,0.92);
        border: 1px solid var(--border);
        border-radius: 20px;
        padding: 1rem 1.1rem;
        box-shadow: 0 12px 30px rgba(31, 41, 55, 0.05);
    }

    .label-pill {
        display: inline-block;
        padding: 0.25rem 0.6rem;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        margin-right: 0.35rem;
    }

    .label-cease { background: rgba(22, 101, 52, 0.12); color: var(--success); }
    .label-irrelevant { background: rgba(194, 65, 12, 0.12); color: var(--accent-2); }
    .label-uncertain { background: rgba(180, 83, 9, 0.14); color: var(--warning); }

    .small-note {
        color: var(--muted);
        font-size: 0.92rem;
        line-height: 1.5;
    }

    div[data-testid="stMetric"] {
        background: rgba(255,255,255,0.92);
        border: 1px solid var(--border);
        padding: 0.8rem 0.9rem;
        border-radius: 18px;
        box-shadow: 0 10px 20px rgba(31, 41, 55, 0.04);
    }
</style>
"""


def get_runtime() -> tuple[dict, AuditAgent]:
    if "runtime" not in st.session_state:
        config = load_config()
        if config.get("datastore", {}).get("type") == "sqlite":
            initialize_sqlite(config["datastore"]["sqlite_path"])
        st.session_state["runtime"] = (config, AuditAgent(config))
    return st.session_state["runtime"]


def save_upload(uploaded_file) -> str:
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    temp_file.write(uploaded_file.getbuffer())
    temp_file.flush()
    temp_file.close()
    return temp_file.name


def badge_for_label(label: str) -> str:
    if label == "CEASE":
        return '<span class="label-pill label-cease">Cease</span>'
    if label == "IRRELEVANT":
        return '<span class="label-pill label-irrelevant">Irrelevant</span>'
    return '<span class="label-pill label-uncertain">Uncertain</span>'


def citation_context_excerpt(text: str, citation: str, context_chars: int = 120) -> str:
    if not text:
        return "No text extracted from this PDF."
    if not citation:
        return text[: context_chars * 2].strip()

    lowered_text = text.lower()
    lowered_citation = citation.lower()
    position = lowered_text.find(lowered_citation)
    if position == -1:
        return text[: context_chars * 2].strip()

    start = max(0, position - context_chars)
    end = min(len(text), position + len(citation) + context_chars)
    excerpt = text[start:end].strip()
    if start > 0:
        excerpt = "…" + excerpt
    if end < len(text):
        excerpt = excerpt + "…"
    return excerpt


def highlight_citation(text: str, citation: str) -> str:
    if not text:
        return "No text extracted from this PDF."
    if not citation:
        return text

    lowered_text = text.lower()
    lowered_citation = citation.lower()
    position = lowered_text.find(lowered_citation)
    if position == -1:
        return text

    before = text[:position]
    match_text = text[position:position + len(citation)]
    after = text[position + len(citation):]
    return f"{before}<mark style='background: rgba(251, 191, 36, 0.35); padding: 0 0.12rem; border-radius: 0.2rem;'>{match_text}</mark>{after}"

    def build_uncertain_signals(result: dict) -> list[dict]:
        classification = result["classification"]
        text = result.get("text", "") or ""
        citation = classification.get("citation", "") or ""
        language = result.get("language", {}).get("language", "unknown")
        confidence = float(classification.get("confidence", 0.0) or 0.0)
        signals = []

        if confidence < 0.65:
            signals.append({"title": "Very low confidence", "detail": "The model is still below the comfort threshold.", "level": "high"})
        elif confidence < 0.75:
            signals.append({"title": "Below decision threshold", "detail": "This case was auto-routed into review because confidence is not strong enough.", "level": "medium"})

        if classification.get("edge_case_flag"):
            signals.append({"title": "Edge case flagged", "detail": "The classifier saw unusual or mixed cues.", "level": "high"})

        if language != "en":
            signals.append({"title": f"Non-English content ({language.upper()})", "detail": "Review the translated citation and the surrounding text carefully.", "level": "medium"})

        if citation and citation.lower() not in text.lower():
            signals.append({"title": "Citation not matched in source", "detail": "The cited phrase was not found exactly in the extracted text.", "level": "high"})

        if not citation:
            signals.append({"title": "No citation captured", "detail": "The model did not return an evidence snippet.", "level": "high"})

        if not signals:
            signals.append({"title": "Manual confirmation needed", "detail": "The document still sits near the boundary between cease and non-cease intent.", "level": "medium"})

        return signals

    def render_signal_panel(result: dict) -> None:
        signals = build_uncertain_signals(result)
        risk_level = "high" if any(signal["level"] == "high" for signal in signals) else "medium"
        accent_class = "label-cease" if risk_level == "high" else "label-irrelevant"

        st.markdown(
            f"""
            <div class="panel">
                <span class="label-pill {accent_class}">{'High risk' if risk_level == 'high' else 'Moderate risk'}</span>
                <h3 style="margin:0.55rem 0 0.25rem 0;">Why this is uncertain</h3>
                <div class="small-note">The signals below explain what should get your attention first.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        for signal in signals:
            if signal["level"] == "high":
                st.error(f"{signal['title']}: {signal['detail']}")
            else:
                st.warning(f"{signal['title']}: {signal['detail']}")


def render_result(result: dict) -> None:
    classification = result["classification"]
    route = st.session_state.get("route")
    route_status = route.get("status") if isinstance(route, dict) else None

    st.markdown(
        f"""
        <div class="panel">
            {badge_for_label(classification['label'])}
            <h3 style="margin:0.5rem 0 0.35rem 0;">{result['filename']}</h3>
            <div class="small-note">{classification['reasoning']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Confidence", f"{classification['confidence']:.0%}")
    col2.metric("Language", result["language"]["language"].upper())
    col3.metric("Edge case", "Yes" if classification["edge_case_flag"] else "No")
    col4.metric("Route", route_status or "Pending")

    if classification["citation"]:
        st.markdown("**Citation**")
        st.code(classification["citation"], language="text")

    st.progress(min(max(classification["confidence"], 0.0), 1.0))

    with st.expander("Show extracted text"):
        st.text(result.get("text", "") or "No text extracted from this PDF.")

    with st.expander("Processing details"):
        st.json(
            {
                "document_id": result.get("document_id"),
                "processing_time_ms": result.get("processing_time_ms"),
                "status": result.get("status"),
                "extraction_status": result.get("extraction_status"),
                "processing_start": result.get("processing_start"),
                "processing_end": result.get("processing_end"),
                "human_decision": result.get("human_decision"),
            }
        )


def render_uncertain_review_workspace(result: dict) -> None:
    classification = result["classification"]
    citation = classification.get("citation", "")
    text = result.get("text", "") or ""
    confidence = float(classification.get("confidence", 0.0) or 0.0)
    reason = classification.get("reasoning", "")
    language = result.get("language", {}).get("language", "unknown")
    note_default = st.session_state.get("uncertain_review_note", "")

    st.markdown("### Human review workspace")
    st.caption("This workspace is optimized for quick review: the clue, the excerpt, and the decision controls stay on screen together.")

    left, right = st.columns([1.35, 0.95], gap="large")

    with left:
        st.markdown(
            f"""
            <div class="panel">
                <span class="label-pill label-uncertain">Uncertain</span>
                <span class="label-pill">Language: {language.upper()}</span>
                <span class="label-pill">Confidence: {confidence:.0%}</span>
                <h3 style="margin:0.6rem 0 0.25rem 0;">Why the model paused</h3>
                <div class="small-note">{reason}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("**Key excerpt**")
        excerpt = citation_context_excerpt(text, citation)
        st.code(excerpt, language="text")

        with st.expander("Show highlighted source text", expanded=True):
            st.markdown(highlight_citation(text, citation), unsafe_allow_html=True)

        with st.expander("Operator guidance"):
            st.markdown(
                """
                - Read the highlighted excerpt first.
                - Decide whether the document is truly asking to stop contact.
                - Use defer only when the intent is still not clear after review.
                """
            )

    with right:
        st.markdown(
            """
            <div class="panel">
                <h3 style="margin:0 0 0.35rem 0;">Decision panel</h3>
                <div class="small-note">Pick the outcome that best matches the customer’s intent. Your note will be recorded in the audit trail.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        note = st.text_area(
            "Optional reviewer note",
            value=note_default,
            key="uncertain_review_note",
            placeholder="Add a short rationale for future traceability...",
            height=140,
        )

        note_preview = note.strip() or "No reviewer note entered."
        st.info(note_preview)

        st.markdown("**Decision shortcuts**")
        button_row_one = st.columns(2)
        button_row_two = st.columns(1)
        if button_row_one[0].button("Treat as CEASE", use_container_width=True):
            route_with_decision("CEASE")
            st.rerun()
        if button_row_one[1].button("Treat as IRRELEVANT", use_container_width=True):
            route_with_decision("IRRELEVANT")
            st.rerun()
        if button_row_two[0].button("Defer review", use_container_width=True):
            route_with_decision("DEFER")
            st.rerun()

        st.markdown("**Decision framing**")
        st.write("CEASE means the customer is asking to stop direct communication.")
        st.write("IRRELEVANT means the document is about something else entirely.")
        st.write("DEFER means the document still needs more human context.")


def render_batch_summary(batch_results: list[dict]) -> None:
    if not batch_results:
        return

    counts = Counter(item["final_status"] for item in batch_results)
    total = len(batch_results)
    avg_confidence = sum(item["confidence"] for item in batch_results) / total if total else 0.0

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Documents", total)
    col2.metric("Cease", counts.get("CEASE", 0))
    col3.metric("Irrelevant", counts.get("IRRELEVANT", 0))
    col4.metric("Needs review", counts.get("needs_review", 0))
    col5.metric("Avg confidence", f"{avg_confidence:.0%}")


def render_batch_table(batch_results: list[dict]) -> None:
    if not batch_results:
        return

    st.markdown("### Batch results")
    st.dataframe(
        [
            {
                "filename": item["filename"],
                "label": item["label"],
                "confidence": f"{item['confidence']:.0%}",
                "route": item["final_status"],
                "language": item["language"],
                "citation": item["citation"],
                "processing_ms": item["processing_time_ms"],
            }
            for item in batch_results
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.caption("UNCERTAIN documents are marked as needs_review in batch mode so the queue stays non-blocking.")


def load_recent_audit_entries(audit_path: str, limit: int = 12) -> list[dict]:
    return load_audit_entries(audit_path, limit=limit)


def load_audit_entries(audit_path: str, limit: int | None = None) -> list[dict]:
    path = Path(audit_path)
    if not path.exists():
        return []

    entries: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries[-limit:] if limit is not None else entries


def parse_audit_timestamp(entry: dict) -> datetime | None:
    raw_timestamp = entry.get("timestamp")
    if not raw_timestamp:
        return None
    try:
        return datetime.fromisoformat(str(raw_timestamp).replace("Z", "+00:00"))
    except ValueError:
        return None


def audit_search_text(entry: dict) -> str:
    parts = [
        str(entry.get("timestamp", "")),
        str(entry.get("stage", "")),
        str(entry.get("filename", "")),
        str(entry.get("document_id", "")),
        str(entry.get("classification", "")),
        str(entry.get("routing_destination", "")),
        str(entry.get("human_override", "")),
        str(entry.get("language", "")),
        str(entry.get("citation", "")),
        str(entry.get("error", "")),
        str(entry.get("entry_id", "")),
    ]
    return " ".join(parts).lower()


def audit_confidence_value(entry: dict) -> float | None:
    value = entry.get("confidence")
    if isinstance(value, (int, float)):
        return float(value)
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def format_confidence(entry: dict) -> str:
    value = audit_confidence_value(entry)
    return f"{value:.0%}" if value is not None else "—"


def audit_sort_timestamp(entry: dict) -> datetime:
    parsed_timestamp = entry.get("parsed_timestamp")
    return parsed_timestamp or datetime.min.replace(tzinfo=timezone.utc)


def normalize_audit_entry(entry: dict) -> dict:
    normalized = dict(entry)
    normalized["confidence_value"] = audit_confidence_value(entry)
    normalized["search_blob"] = audit_search_text(entry)
    parsed_ts = parse_audit_timestamp(entry)
    normalized["parsed_timestamp"] = parsed_ts
    normalized["timestamp_display"] = parsed_ts.strftime("%Y-%m-%d %H:%M UTC") if parsed_ts else str(entry.get("timestamp", "—"))
    normalized["date_value"] = parsed_ts.date() if parsed_ts else None
    normalized["route_display"] = entry.get("routing_destination") or entry.get("route") or "unknown"
    normalized["classification_display"] = entry.get("classification") or "unknown"
    normalized["language_display"] = str(entry.get("language") or "unknown").upper()
    return normalized


def build_audit_filters(entries: list[dict]) -> dict:
    dates = [entry["date_value"] for entry in entries if entry.get("date_value")]
    confidences = [entry["confidence_value"] for entry in entries if entry.get("confidence_value") is not None]
    labels = sorted({str(entry.get("classification_display", "unknown")) for entry in entries})
    stages = sorted({str(entry.get("stage") or "unknown") for entry in entries})
    routes = sorted({str(entry.get("route_display") or "unknown") for entry in entries})
    languages = sorted({str(entry.get("language") or "unknown") for entry in entries})

    return {
        "min_date": min(dates) if dates else date.today(),
        "max_date": max(dates) if dates else date.today(),
        "min_confidence": min(confidences) if confidences else 0.0,
        "max_confidence": max(confidences) if confidences else 1.0,
        "labels": labels,
        "stages": stages,
        "routes": routes,
        "languages": languages,
    }


def initialize_audit_filter_state(filters: dict) -> None:
    defaults = {
        "audit_search_query": "",
        "audit_selected_labels": filters["labels"],
        "audit_selected_stages": filters["stages"],
        "audit_selected_routes": filters["routes"],
        "audit_selected_languages": filters["languages"],
        "audit_date_range": (filters["min_date"], filters["max_date"]),
        "audit_confidence_range": (filters["min_confidence"], filters["max_confidence"]),
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def filter_audit_entries(
    entries: list[dict],
    query_text: str,
    selected_labels: list[str],
    selected_stages: list[str],
    selected_routes: list[str],
    selected_languages: list[str],
    date_range: tuple[date, date],
    confidence_range: tuple[float, float],
) -> list[dict]:
    start_date, end_date = date_range
    min_confidence, max_confidence = confidence_range
    normalized_query = query_text.strip().lower()

    filtered_entries = []
    for entry in entries:
        if normalized_query and normalized_query not in entry["search_blob"]:
            continue
        if selected_labels and str(entry.get("classification_display", "unknown")) not in selected_labels:
            continue
        if selected_stages and str(entry.get("stage") or "unknown") not in selected_stages:
            continue
        if selected_routes and str(entry.get("route_display") or "unknown") not in selected_routes:
            continue
        if selected_languages and str(entry.get("language") or "unknown") not in selected_languages:
            continue

        entry_date = entry.get("date_value")
        if entry_date and (entry_date < start_date or entry_date > end_date):
            continue

        confidence_value = entry.get("confidence_value")
        if confidence_value is not None and not (min_confidence <= confidence_value <= max_confidence):
            continue

        filtered_entries.append(entry)

    return filtered_entries


def render_recent_audit_pane(config: dict) -> None:
    audit_path = config["files"]["audit_path"]
    recent_entries = [normalize_audit_entry(entry) for entry in load_recent_audit_entries(audit_path)]

    st.markdown("### Search and filters")
    st.caption("Search the case log using text, labels, routing outcomes, dates, and confidence to find exactly what you need.")

    if not recent_entries:
        st.info("No audit entries found yet. Process a document to populate the history pane.")
        return

    filters = build_audit_filters(recent_entries)

    initialize_audit_filter_state(filters)

    reset_requested = st.button("Clear filters", use_container_width=False)
    if reset_requested:
        st.session_state["audit_search_query"] = ""
        st.session_state["audit_selected_labels"] = filters["labels"]
        st.session_state["audit_selected_stages"] = filters["stages"]
        st.session_state["audit_selected_routes"] = filters["routes"]
        st.session_state["audit_selected_languages"] = filters["languages"]
        st.session_state["audit_date_range"] = (filters["min_date"], filters["max_date"])
        st.session_state["audit_confidence_range"] = (filters["min_confidence"], filters["max_confidence"])
        st.rerun()

    query_text = st.text_input(
        "Search cases",
        placeholder="Try a filename, document ID, citation fragment, label, route, or human decision...",
        key="audit_search_query",
    )

    col1, col2 = st.columns(2)
    with col1:
        selected_labels = st.multiselect("Labels", filters["labels"], key="audit_selected_labels")
        selected_routes = st.multiselect("Routes", filters["routes"], key="audit_selected_routes")
    with col2:
        selected_stages = st.multiselect("Stages", filters["stages"], key="audit_selected_stages")
        selected_languages = st.multiselect("Languages", filters["languages"], key="audit_selected_languages")

    date_range = st.date_input(
        "Date range",
        min_value=filters["min_date"],
        max_value=filters["max_date"],
        key="audit_date_range",
    )
    if isinstance(date_range, tuple):
        selected_date_range = date_range
    else:
        selected_date_range = (filters["min_date"], filters["max_date"])

    confidence_range = st.slider(
        "Confidence range",
        min_value=0.0,
        max_value=1.0,
        step=0.01,
        key="audit_confidence_range",
    )

    sort_mode = st.selectbox(
        "Sort by",
        ["Newest first", "Oldest first", "Highest confidence", "Lowest confidence"],
        index=0,
    )

    filtered_entries = filter_audit_entries(
        recent_entries,
        query_text=query_text,
        selected_labels=selected_labels,
        selected_stages=selected_stages,
        selected_routes=selected_routes,
        selected_languages=selected_languages,
        date_range=selected_date_range,
        confidence_range=confidence_range,
    )

    if sort_mode == "Newest first":
        filtered_entries = sorted(filtered_entries, key=audit_sort_timestamp, reverse=True)
    elif sort_mode == "Oldest first":
        filtered_entries = sorted(filtered_entries, key=audit_sort_timestamp)
    elif sort_mode == "Highest confidence":
        filtered_entries = sorted(filtered_entries, key=lambda entry: entry["confidence_value"] if entry["confidence_value"] is not None else -1.0, reverse=True)
    elif sort_mode == "Lowest confidence":
        filtered_entries = sorted(filtered_entries, key=lambda entry: entry["confidence_value"] if entry["confidence_value"] is not None else 2.0)

    st.divider()

    row_count = len(filtered_entries)
    unique_docs = len({entry.get("document_id") for entry in filtered_entries})
    error_count = sum(1 for entry in filtered_entries if entry.get("error"))
    route_values = Counter(entry.get("route_display") or "unknown" for entry in filtered_entries)
    cease_count = sum(1 for entry in filtered_entries if entry.get("classification_display") == "CEASE")
    uncertain_count = sum(1 for entry in filtered_entries if entry.get("classification_display") == "UNCERTAIN")

    metric_col1, metric_col2, metric_col3, metric_col4, metric_col5, metric_col6 = st.columns(6)
    metric_col1.metric("Matches", row_count)
    metric_col2.metric("Documents", unique_docs)
    metric_col3.metric("Cease", cease_count)
    metric_col4.metric("Uncertain", uncertain_count)
    metric_col5.metric("Errors", error_count)
    metric_col6.metric("Top route", route_values.most_common(1)[0][0] if route_values else "unknown")

    if not filtered_entries:
        st.warning("No cases match the current filters. Try widening the date range or clearing the label filters.")
        return

    st.dataframe(
        [
            {
                "timestamp": entry["timestamp_display"],
                "stage": entry.get("stage"),
                "filename": entry.get("filename"),
                "classification": entry["classification_display"],
                "confidence": format_confidence(entry),
                "route": entry["route_display"],
                "language": entry["language_display"],
                "human_override": entry.get("human_override"),
                "confidence_value": entry.get("confidence_value"),
            }
            for entry in filtered_entries
        ],
        use_container_width=True,
        hide_index=True,
    )

    with st.expander("Latest matching entry"):
        st.json(filtered_entries[-1])

    with st.expander("Search tips"):
        st.markdown(
            """
            - Search by filename, document ID, citation fragment, route, label, language, or human decision.
            - Narrow confidence to isolate ambiguous cases.
            - Use date filters to find recent operator activity quickly.
            """
        )


def process_uploaded_document(uploaded_file, prompt_human: bool = True) -> tuple[dict, dict]:
    config, audit = get_runtime()
    temp_path = save_upload(uploaded_file)
    st.session_state["temp_path"] = temp_path

    ingestion = IngestionAgent(config)
    with st.spinner("Reading and classifying the document..."):
        result = ingestion.run({"pdf_path": temp_path, "filename": uploaded_file.name})
        audit.log(build_received_audit_entry(result))
        route = route_result(result, config, audit, prompt_human=prompt_human)
        audit.log(build_completed_audit_entry(result, route))
        return result, route


def build_batch_row(result: dict, route: dict) -> dict:
    classification = result["classification"]
    return {
        "document_id": result["document_id"],
        "filename": result["filename"],
        "label": classification["label"],
        "confidence": classification["confidence"],
        "citation": classification["citation"],
        "language": result["language"]["language"],
        "final_status": route.get("status", "unknown"),
        "processing_time_ms": int(result.get("processing_time_ms", 0) or 0),
        "edge_case_flag": classification["edge_case_flag"],
    }


def process_batch_documents(uploaded_files) -> list[dict]:
    if not uploaded_files:
        return []

    batch_results = []
    progress = st.progress(0)
    status = st.empty()

    for index, uploaded_file in enumerate(uploaded_files, start=1):
        status.write(f"Processing {uploaded_file.name} ({index}/{len(uploaded_files)})")
        result, route = process_uploaded_document(uploaded_file, prompt_human=False)
        batch_results.append(build_batch_row(result, route))
        progress.progress(index / len(uploaded_files))

    st.session_state["batch_results"] = batch_results
    return batch_results


def route_with_decision(decision: str, note: str | None = None) -> None:
    config, audit = get_runtime()
    result = st.session_state.get("result")
    if not result:
        return

    note_value = note if note is not None else st.session_state.get("uncertain_review_note", "")
    note_value = note_value.strip() or None

    human_decision = {
        "decision": decision,
        "decided_at": iso_timestamp(),
        "operator_id": "streamlit-user",
        "note": note_value,
    }
    with st.spinner("Routing document based on your decision..."):
        route = route_result(result, config, audit, human_decision=human_decision)
        st.session_state["route"] = route
        audit.log(build_completed_audit_entry(result, route))


st.markdown(APP_CSS, unsafe_allow_html=True)

st.markdown(
    """
    <div class="hero">
        <h1>CeaseGuard Review Console</h1>
        <p>Upload a PDF, review the AI summary, and resolve uncertain cases inline without leaving the browser.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

config, _audit = get_runtime()

with st.sidebar:
    st.subheader("Workflow")
    st.write("1. Upload a PDF")
    st.write("2. Review the classification")
    st.write("3. Make a human decision if needed")

    st.subheader("Routing rules")
    st.write(f"Confidence below {config['classifier']['confidence_threshold_uncertain']:.2f} is forced to UNCERTAIN.")
    st.write(f"Edge cases below {config['classifier']['confidence_threshold_edge_case']:.2f} are flagged.")

    st.subheader("Storage")
    st.write(f"Audit log: {config['files']['audit_path']}")
    st.write(f"Archive file: {config['files']['archive_path']}")
    st.write(f"Datastore: {config['datastore']['sqlite_path']}")

single_tab, batch_tab, history_tab = st.tabs(["Single review", "Batch review", "Recent history"])

with single_tab:
    uploaded_file = st.file_uploader(
        "Choose a PDF",
        type=["pdf"],
        help="Local files only. Nothing leaves your machine unless you have enabled external model calls.",
        key="single_uploader",
    )

    button_disabled = uploaded_file is None
    if st.button("Analyze document", type="primary", disabled=button_disabled, key="single_analyze_button"):
        result, route = process_uploaded_document(uploaded_file, prompt_human=False)
        st.session_state["result"] = result
        st.session_state["route"] = route

    result = st.session_state.get("result")
    if result:
        st.divider()
        render_result(result)

        route = st.session_state.get("route")
        if result["classification"]["label"] == "UNCERTAIN" and (not isinstance(route, dict) or route.get("status") == "needs_review"):
            render_uncertain_review_workspace(result)
        elif isinstance(route, dict):
            st.success(f"Final status: {route.get('status')}")
            st.json(route)

with batch_tab:
    batch_files = st.file_uploader(
        "Choose one or more PDFs",
        type=["pdf"],
        accept_multiple_files=True,
        help="Upload a queue of documents and review the full results table after processing.",
        key="batch_uploader",
    )

    batch_disabled = not batch_files
    if st.button("Analyze batch", type="primary", disabled=batch_disabled, key="batch_analyze_button"):
        batch_results = process_batch_documents(batch_files)
        st.session_state["batch_results"] = batch_results

    batch_results = st.session_state.get("batch_results") or []
    if batch_results:
        st.divider()
        render_batch_summary(batch_results)
        render_batch_table(batch_results)

with history_tab:
    render_recent_audit_pane(config)
