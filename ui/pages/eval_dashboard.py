"""
Evaluation Dashboard page — quantitative validation of all pipeline modules.

Displays hardcoded target and demo-actual metrics with interactive Plotly
radar and bar charts.  When a real evaluation run completes the results
are picked up from session state automatically.
"""

from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go

from ui.components.metric_cards import render_metric_row

# ---------------------------------------------------------------------------
# Reference target metrics (from project spec)
# ---------------------------------------------------------------------------
TARGETS: dict[str, dict[str, float]] = {
    "M1: Ingestion": {"Schema Validation": 1.00, "FHIR Parse Accuracy": 0.95},
    "M2: NER": {"Precision": 0.82, "Recall": 0.80, "F1": 0.81},
    "M3: RAG Coding": {"Top-1 Accuracy": 0.70, "Top-3 Accuracy": 0.85, "MRR": 0.75},
    "M4: CDI Agent": {"Query Relevance": 0.80, "Conflict Detection": 0.90},
    "M5: Explainability": {"Trace Completeness": 1.00, "Evidence Attribution": 1.00},
}

# ---------------------------------------------------------------------------
# Demo / placeholder actual metrics (close-to-target on 20 synthetic cases)
# ---------------------------------------------------------------------------
DEMO_ACTUALS: dict[str, dict[str, float]] = {
    "M1: Ingestion": {"Schema Validation": 1.00, "FHIR Parse Accuracy": 0.95},
    "M2: NER": {"Precision": 0.84, "Recall": 0.81, "F1": 0.82},
    "M3: RAG Coding": {"Top-1 Accuracy": 0.72, "Top-3 Accuracy": 0.86, "MRR": 0.77},
    "M4: CDI Agent": {"Query Relevance": 0.82, "Conflict Detection": 0.92},
    "M5: Explainability": {"Trace Completeness": 1.00, "Evidence Attribution": 1.00},
}

# Primary metric per module (used in radar chart)
PRIMARY_METRIC: dict[str, str] = {
    "M1: Ingestion": "Schema Validation",
    "M2: NER": "F1",
    "M3: RAG Coding": "MRR",
    "M4: CDI Agent": "Query Relevance",
    "M5: Explainability": "Trace Completeness",
}

# Short labels for radar categories
RADAR_LABELS: dict[str, str] = {
    "M1: Ingestion": "M1 Schema",
    "M2: NER": "M2 F1",
    "M3: RAG Coding": "M3 MRR",
    "M4: CDI Agent": "M4 Query Rel.",
    "M5: Explainability": "M5 Trace Comp.",
}

MODULE_DESCRIPTIONS: dict[str, str] = {
    "M1: Ingestion": (
        "Validates that all input documents (FHIR bundles, plain text, scanned images) "
        "are parsed into well-formed ClinicalDocument objects with correct schema."
    ),
    "M2: NER": (
        "Measures entity-level precision, recall, and F1 for clinical named entity "
        "recognition using the d4data biomedical NER model."
    ),
    "M3: RAG Coding": (
        "Evaluates the retrieve-rerank-reason pipeline for ICD-10 code assignment "
        "against a 20-case gold standard."
    ),
    "M4: CDI Agent": (
        "Assesses the quality of physician queries generated for documentation gaps "
        "and the accuracy of code conflict detection via the knowledge graph."
    ),
    "M5: Explainability": (
        "Verifies that every pipeline stage produces complete traces and every "
        "assigned code links back to supporting evidence in the clinical narrative."
    ),
}


# ── helpers ─────────────────────────────────────────────────────────────────

def _get_actuals() -> dict[str, dict[str, float]]:
    """Return actual metrics — prefer session-state eval results over demo."""
    if "eval_results" in st.session_state and st.session_state["eval_results"]:
        return st.session_state["eval_results"]
    return DEMO_ACTUALS


def _module_passes(module: str, actuals: dict[str, dict[str, float]]) -> bool:
    """True when every metric in *module* meets or exceeds its target."""
    for metric, target in TARGETS[module].items():
        if actuals.get(module, {}).get(metric, 0.0) < target:
            return False
    return True


def _build_radar(actuals: dict[str, dict[str, float]]) -> go.Figure:
    """Create a Plotly radar chart comparing actuals vs targets."""
    modules = list(TARGETS.keys())
    categories = [RADAR_LABELS[m] for m in modules]

    actual_vals = [
        actuals.get(m, {}).get(PRIMARY_METRIC[m], 0.0) for m in modules
    ]
    target_vals = [
        TARGETS[m][PRIMARY_METRIC[m]] for m in modules
    ]

    # Close the polygon
    categories_closed = categories + [categories[0]]
    actual_closed = actual_vals + [actual_vals[0]]
    target_closed = target_vals + [target_vals[0]]

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=target_closed,
        theta=categories_closed,
        name="Target",
        line=dict(color="red", dash="dash"),
        fill="toself",
        fillcolor="rgba(255, 0, 0, 0.08)",
        opacity=0.3,
    ))

    fig.add_trace(go.Scatterpolar(
        r=actual_closed,
        theta=categories_closed,
        name="Actual",
        line=dict(color="#2ecc71", width=2),
        fill="toself",
        fillcolor="rgba(46, 204, 113, 0.18)",
    ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        showlegend=True,
        margin=dict(l=60, r=60, t=40, b=40),
        height=420,
    )
    return fig


def _build_module_bar(module: str, actuals: dict[str, dict[str, float]]) -> go.Figure:
    """Grouped bar chart for one module (actual vs target per metric)."""
    metrics = list(TARGETS[module].keys())
    target_vals = [TARGETS[module][m] for m in metrics]
    actual_vals = [actuals.get(module, {}).get(m, 0.0) for m in metrics]

    bar_colors = [
        "#2ecc71" if a >= t else "#e74c3c"
        for a, t in zip(actual_vals, target_vals)
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=metrics,
        y=actual_vals,
        name="Actual",
        marker_color=bar_colors,
    ))
    fig.add_trace(go.Bar(
        x=metrics,
        y=target_vals,
        name="Target",
        marker_color="rgba(160, 160, 160, 0.6)",
    ))
    fig.update_layout(
        barmode="group",
        yaxis=dict(range=[0, 1.05]),
        height=320,
        margin=dict(l=40, r=20, t=30, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


# ── page ────────────────────────────────────────────────────────────────────

st.title("Evaluation Dashboard")
st.markdown("*Quantitative validation of all pipeline modules*")

actuals = _get_actuals()

# --- Overview section: radar + pass/fail cards ---
left, right = st.columns([3, 1])

with left:
    st.subheader("Module Performance Radar")
    st.plotly_chart(_build_radar(actuals), use_container_width=True)

with right:
    st.subheader("Pass / Fail")
    for module in TARGETS:
        passed = _module_passes(module, actuals)
        icon = "✅" if passed else "❌"
        short = module.split(":")[0].strip()
        st.markdown(f"**{short}** {icon}")

st.divider()

# --- Per-module detail tabs ---
tab_labels = list(TARGETS.keys())
tabs = st.tabs(tab_labels)

for tab, module in zip(tabs, tab_labels):
    with tab:
        st.markdown(f"**{module}**")
        st.caption(MODULE_DESCRIPTIONS[module])

        # Metric row
        metric_dict: dict[str, tuple[str, str | None]] = {}
        for metric_name, target_val in TARGETS[module].items():
            actual_val = actuals.get(module, {}).get(metric_name, 0.0)
            delta = actual_val - target_val
            delta_str = f"{delta:+.2f}" if delta != 0 else None
            metric_dict[metric_name] = (f"{actual_val:.2f}", delta_str)
        render_metric_row(metric_dict)

        # Bar chart
        st.plotly_chart(
            _build_module_bar(module, actuals),
            use_container_width=True,
        )

        # Pass / fail badge
        if _module_passes(module, actuals):
            st.success("All metrics meet or exceed targets.")
        else:
            st.error("One or more metrics below target.")

st.divider()

# --- Run Eval button (placeholder) ---
st.button(
    "Run Full Evaluation Suite",
    disabled=True,
    help="Requires ~30 min on CPU. Connect evaluation infrastructure to enable.",
)
st.caption("Demo metrics are displayed by default. Run the full evaluation suite to replace with live results.")
