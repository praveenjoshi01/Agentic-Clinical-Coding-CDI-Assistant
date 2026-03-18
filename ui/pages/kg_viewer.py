"""
Knowledge Graph Viewer page.

Renders an interactive PyVis graph of the case-relevant KG subgraph with
CDI-based node coloring (green=ok, amber=gap, red=conflict). Shows node
tooltips with code description and physician queries. Sidebar displays
CDI summary with documentation gaps, conflicts, and missed diagnoses.
"""

from __future__ import annotations

import streamlit as st

from cliniq.knowledge_graph import build_cdi_knowledge_graph
from ui.components.graph_embed import render_kg_graph


# ---------------------------------------------------------------------------
# Session state guard
# ---------------------------------------------------------------------------
if "pipeline_result" not in st.session_state or st.session_state["pipeline_result"] is None:
    st.warning("No pipeline result available. Run the pipeline first.")
    st.page_link("pages/pipeline_runner.py", label="Go to Pipeline Runner", icon=":material/play_arrow:")
    st.stop()

result = st.session_state["pipeline_result"]

# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------
st.title("Knowledge Graph Viewer")
st.caption(
    "Interactive visualization of the case-relevant ICD-10 knowledge subgraph. "
    "Node colors reflect CDI analysis status."
)

# Color legend
legend_cols = st.columns(3)
with legend_cols[0]:
    st.markdown(
        '<span style="display:inline-block;width:14px;height:14px;border-radius:50%;'
        'background:#2ecc71;vertical-align:middle;margin-right:6px;"></span>'
        "**Well Documented**",
        unsafe_allow_html=True,
    )
with legend_cols[1]:
    st.markdown(
        '<span style="display:inline-block;width:14px;height:14px;border-radius:50%;'
        'background:#f39c12;vertical-align:middle;margin-right:6px;"></span>'
        "**Needs CDI Query**",
        unsafe_allow_html=True,
    )
with legend_cols[2]:
    st.markdown(
        '<span style="display:inline-block;width:14px;height:14px;border-radius:50%;'
        'background:#e74c3c;vertical-align:middle;margin-right:6px;"></span>'
        "**Conflict Detected**",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Extract case codes from pipeline result
# ---------------------------------------------------------------------------
coding = result.coding_result
case_codes: list[str] = []

if coding.principal_diagnosis is not None:
    case_codes.append(coding.principal_diagnosis.icd10_code)

case_codes.extend(c.icd10_code for c in coding.secondary_codes)
case_codes.extend(c.icd10_code for c in coding.complication_codes)

if not case_codes:
    st.info(
        "No ICD-10 codes available for visualization. "
        "The pipeline may have been run with skip_coding enabled or produced no codes."
    )
    st.stop()

# ---------------------------------------------------------------------------
# Build / cache knowledge graph
# ---------------------------------------------------------------------------


@st.cache_resource(show_spinner="Building knowledge graph...")
def _get_kg():
    """Cache the CDI knowledge graph so it is built only once per session."""
    return build_cdi_knowledge_graph()


G = _get_kg()

# ---------------------------------------------------------------------------
# Graph rendering (main area) + CDI summary (sidebar)
# ---------------------------------------------------------------------------
main_col, sidebar_col = st.columns([3, 1])

with main_col:
    st.subheader("Case Subgraph")
    render_kg_graph(G, case_codes, cdi_report=result.cdi_report, height=600)

    # Graph details expander
    with st.expander("Graph Details"):
        # Calculate subgraph stats
        relevant_nodes: set[str] = set(case_codes)
        for code in case_codes:
            if code in G:
                relevant_nodes.update(G.predecessors(code))
                relevant_nodes.update(G.successors(code))
        relevant_nodes = {n for n in relevant_nodes if n in G}

        edge_count = sum(
            1
            for u, v in G.edges()
            if u in relevant_nodes and v in relevant_nodes
        )

        st.metric("Nodes in subgraph", len(relevant_nodes))
        st.metric("Edges in subgraph", edge_count)

        st.markdown("**Case Codes and CDI Status:**")

        # Determine CDI status per code
        gap_codes: set[str] = set()
        conflict_codes: set[str] = set()
        if result.cdi_report is not None:
            gap_codes = {g.code for g in result.cdi_report.documentation_gaps}
            for c in result.cdi_report.code_conflicts:
                conflict_codes.add(c.code_a)
                conflict_codes.add(c.code_b)

        for code in case_codes:
            if code in conflict_codes:
                status = "Conflict"
                icon = "🔴"
            elif code in gap_codes:
                status = "Gap"
                icon = "🟠"
            else:
                status = "OK"
                icon = "🟢"
            desc = G.nodes[code].get("description", "") if code in G else ""
            st.markdown(f"{icon} **{code}** ({status}) — {desc}")

with sidebar_col:
    st.subheader("CDI Summary")

    cdi = result.cdi_report
    if cdi is None:
        st.info("CDI analysis was not performed for this run.")
    else:
        # Metric counts
        st.metric("Documentation Gaps", cdi.gap_count)
        st.metric("Code Conflicts", cdi.conflict_count)
        st.metric("Missed Diagnoses", len(cdi.missed_diagnoses))
        st.metric("Completeness", f"{cdi.completeness_score:.0%}")

        st.divider()

        # Documentation gaps detail
        if cdi.documentation_gaps:
            st.markdown("**Documentation Gaps**")
            for gap in cdi.documentation_gaps:
                with st.expander(f"{gap.code} — {gap.missing_qualifier}"):
                    st.markdown(f"**Code:** {gap.code}")
                    st.markdown(f"**Description:** {gap.description}")
                    st.markdown(f"**Missing qualifier:** {gap.missing_qualifier}")
                    st.markdown(f"**Confidence:** {gap.confidence:.0%}")
                    st.markdown("---")
                    st.markdown("**Physician Query:**")
                    st.info(gap.physician_query)
                    if gap.evidence_text:
                        st.markdown("**Evidence:**")
                        st.markdown(f"> {gap.evidence_text[:300]}")

        # Code conflicts detail
        if cdi.code_conflicts:
            st.markdown("**Code Conflicts**")
            for conflict in cdi.code_conflicts:
                with st.expander(f"{conflict.code_a} vs {conflict.code_b}"):
                    st.markdown(f"**Codes:** {conflict.code_a} vs {conflict.code_b}")
                    st.markdown(f"**Reason:** {conflict.conflict_reason}")
                    st.markdown(f"**Recommendation:** {conflict.recommendation}")

        # Missed diagnoses detail
        if cdi.missed_diagnoses:
            st.markdown("**Missed Diagnoses**")
            for md in cdi.missed_diagnoses:
                with st.expander(f"{md.suggested_code} — {md.description}"):
                    st.markdown(f"**Suggested code:** {md.suggested_code}")
                    st.markdown(f"**Description:** {md.description}")
                    st.markdown(f"**Co-coded with:** {md.co_coded_with}")
                    st.markdown(f"**Weight:** {md.co_occurrence_weight:.2f}")
                    if md.evidence_text:
                        st.markdown(f"> {md.evidence_text[:300]}")
