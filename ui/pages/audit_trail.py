"""
Audit Trail page.

Renders a complete pipeline decision trace with expandable per-stage traces
showing timing, input/output summaries, chain-of-thought reasoning, retrieval
logs, and evidence attribution spans. Read-only -- no session state mutations.
"""

from __future__ import annotations

import streamlit as st


# ---------------------------------------------------------------------------
# Session state guard
# ---------------------------------------------------------------------------
if "pipeline_result" not in st.session_state or st.session_state["pipeline_result"] is None:
    st.warning("No pipeline result available. Run the pipeline first.")
    st.page_link("pages/pipeline_runner.py", label="Go to Pipeline Runner", icon=":material/play_arrow:")
    st.stop()

result = st.session_state["pipeline_result"]

if result.audit_trail is None:
    st.title("Audit Trail")
    st.info(
        "No audit trail available for this pipeline run. "
        "The pipeline may have been run without auditing."
    )
    st.stop()

audit = result.audit_trail

# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------
st.title("Audit Trail")
st.caption("Complete pipeline decision trace with per-stage timing, reasoning, and evidence.")

# Header metrics row
header_cols = st.columns(4)
with header_cols[0]:
    st.metric("Case ID", audit.case_id)
with header_cols[1]:
    st.metric("Timestamp", audit.timestamp.strftime("%Y-%m-%d %H:%M"))
with header_cols[2]:
    st.metric("Total Stages", len(audit.stages))
with header_cols[3]:
    total_time_ms = sum(s.processing_time_ms for s in audit.stages)
    if total_time_ms >= 1000:
        st.metric("Total Processing", f"{total_time_ms / 1000:.1f}s")
    else:
        st.metric("Total Processing", f"{total_time_ms:.0f}ms")

st.divider()

# ---------------------------------------------------------------------------
# Stage icon mapping
# ---------------------------------------------------------------------------
STAGE_ICONS = {
    "ingestion": "1",
    "ner": "2",
    "rag": "3",
    "cdi": "4",
    "audit": "5",
}

STAGE_LABELS = {
    "ingestion": "Document Ingestion",
    "ner": "Named Entity Recognition",
    "rag": "RAG-Based ICD-10 Coding",
    "cdi": "CDI Analysis",
    "audit": "Audit Trail Generation",
}

# ---------------------------------------------------------------------------
# Stage traces
# ---------------------------------------------------------------------------
st.subheader("Pipeline Stages")

for trace in audit.stages:
    stage_num = STAGE_ICONS.get(trace.stage, "?")
    stage_label = STAGE_LABELS.get(trace.stage, trace.stage.title())
    time_display = f"{trace.processing_time_ms:.1f}ms"

    with st.expander(f"Stage {stage_num}: {stage_label} ({time_display})", expanded=False):
        # Input / Output summary columns
        io_cols = st.columns(2)
        with io_cols[0]:
            st.metric("Input", trace.input_summary)
        with io_cols[1]:
            st.metric("Output", trace.output_summary)

        # Details (if present)
        if trace.details:
            st.markdown("**Stage Details:**")
            st.json(trace.details)

        # Chain-of-Thought traces
        if trace.cot_traces:
            st.markdown("**Chain-of-Thought Reasoning:**")
            for i, cot in enumerate(trace.cot_traces, 1):
                st.markdown(f"*Trace {i}:*")
                # Truncate very long CoT traces for display
                display_cot = cot if len(cot) <= 2000 else cot[:2000] + "\n... [truncated]"
                st.code(display_cot, language="text")

        # Retrieval logs
        if trace.retrieval_logs:
            st.markdown("**Retrieval Logs:**")
            for j, log in enumerate(trace.retrieval_logs, 1):
                with st.expander(
                    f"Retrieval {j}: {log.selected_code} "
                    f"(confidence: {log.selected_confidence:.2f})",
                    expanded=False,
                ):
                    st.markdown(f"**Query:** {log.query}")
                    st.markdown(f"**Selected Code:** {log.selected_code}")
                    st.markdown(f"**Confidence:** {log.selected_confidence:.2%}")

                    if log.top_k_results:
                        st.markdown("**Top-K Results:**")
                        st.json(log.top_k_results[:5])  # Show at most 5

                    if log.reranked_results:
                        st.markdown("**Reranked Results:**")
                        st.json(log.reranked_results[:5])

        # Fallback if stage has no extra data
        if not trace.details and not trace.cot_traces and not trace.retrieval_logs:
            st.caption("No additional details recorded for this stage.")

# ---------------------------------------------------------------------------
# Evidence attribution
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Evidence Attribution")

if not audit.evidence_spans:
    st.info("No evidence spans recorded for this pipeline run.")
else:
    st.caption(
        f"{len(audit.evidence_spans)} code(s) with supporting evidence from the clinical text."
    )

    for code, spans in audit.evidence_spans.items():
        with st.expander(f"{code} ({len(spans)} span{'s' if len(spans) != 1 else ''})"):
            for span in spans:
                # Truncate very long spans
                display_span = span if len(span) <= 300 else span[:300] + "..."
                st.markdown(f"> {display_span}")

# ---------------------------------------------------------------------------
# Timeline visualization -- per-stage processing time breakdown
# ---------------------------------------------------------------------------
if len(audit.stages) > 1:
    st.divider()
    st.subheader("Processing Time Breakdown")

    chart_data = {
        STAGE_LABELS.get(s.stage, s.stage.title()): s.processing_time_ms
        for s in audit.stages
    }

    st.bar_chart(chart_data, horizontal=True)

    # Show percentage breakdown
    if total_time_ms > 0:
        st.caption("Stage time as percentage of total:")
        pct_cols = st.columns(len(audit.stages))
        for idx, trace in enumerate(audit.stages):
            with pct_cols[idx]:
                pct = (trace.processing_time_ms / total_time_ms) * 100
                label = STAGE_LABELS.get(trace.stage, trace.stage.title())
                # Shorten long labels
                short = label if len(label) <= 15 else label[:12] + "..."
                st.metric(short, f"{pct:.0f}%")
