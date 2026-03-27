"""
Pipeline Runner page -- primary interactive page for running the ClinIQ pipeline.

Users upload clinical documents (text, FHIR JSON, scanned images), optionally
load pre-computed demo results, and view per-stage outputs with NER highlights,
ICD-10 code cards, and CDI findings across four result tabs.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import streamlit as st

from ui.components.entity_highlight import render_ner_highlights
from ui.components.code_display import render_code_cards, render_principal_diagnosis
from ui.components.pipeline_status import run_pipeline_with_status
from ui.components.metric_cards import render_metric_row
from ui.components.theme import ENTITY_COLORS


# ---------------------------------------------------------------------------
# Pre-computed result loader (cached)
# ---------------------------------------------------------------------------

@st.cache_data
def _load_precomputed(case_id: str) -> str | None:
    """Load pre-computed PipelineResult JSON for a demo case.

    Returns the raw JSON string, or None if the file does not exist.
    """
    path = Path(__file__).resolve().parent.parent / "demo_data" / "precomputed" / f"{case_id}.json"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


# ---------------------------------------------------------------------------
# Demo case options
# ---------------------------------------------------------------------------

DEMO_CASES: dict[str, str | None] = {
    "(none)": None,
    "Case 004: CKD + Hypertension (68M, text)": "case_004",
    "Case 010: CHF + AFib (75M, text)": "case_010",
    "Case 001: Diabetes + Neuropathy (FHIR)": "case_001",
}

PLACEHOLDER_NOTE = (
    "HISTORY OF PRESENT ILLNESS:\n"
    "The patient is a 68-year-old male with a history of chronic kidney disease "
    "stage 3, hypertension, and type 2 diabetes mellitus who presents with "
    "worsening peripheral edema and fatigue over the past two weeks.\n\n"
    "PHYSICAL EXAMINATION:\n"
    "Blood pressure 158/94 mmHg. Heart rate 82 bpm. 2+ pitting edema bilateral "
    "lower extremities. Lungs clear to auscultation.\n\n"
    "ASSESSMENT AND PLAN:\n"
    "1. Chronic kidney disease stage 3 - will check BMP, urinalysis\n"
    "2. Hypertension - poorly controlled, increase lisinopril to 20mg daily\n"
    "3. Type 2 diabetes - A1C pending, continue metformin"
)

# ---------------------------------------------------------------------------
# Page layout
# ---------------------------------------------------------------------------

st.title("Pipeline Runner")
st.caption(
    "Upload a clinical document or select a demo case to run the full "
    "ClinIQ pipeline: Ingestion -> NER -> ICD-10 Coding -> CDI Analysis."
)

# ---- INPUT SECTION --------------------------------------------------------

st.subheader("Input")

input_type = st.radio(
    "Document type",
    options=["Text Note", "FHIR Bundle (JSON)", "Scanned Image"],
    horizontal=True,
)

# Conditional input widgets
input_data = None
if input_type == "Text Note":
    text_input = st.text_area(
        "Paste clinical note",
        value="",
        placeholder=PLACEHOLDER_NOTE,
        height=200,
    )
    if text_input.strip():
        input_data = text_input.strip()

elif input_type == "FHIR Bundle (JSON)":
    uploaded_json = st.file_uploader(
        "Upload FHIR Bundle", type=["json"], key="fhir_upload"
    )
    if uploaded_json is not None:
        try:
            input_data = json.loads(uploaded_json.read().decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            st.error("Invalid JSON file. Please upload a valid FHIR Bundle.")

elif input_type == "Scanned Image":
    uploaded_img = st.file_uploader(
        "Upload scanned document image",
        type=["png", "jpg", "jpeg"],
        key="img_upload",
    )
    if uploaded_img is not None:
        input_data = uploaded_img  # Will be saved to temp file before pipeline call

col_precomputed, col_demo = st.columns(2)
with col_precomputed:
    use_precomputed = st.toggle(
        "Use pre-computed results",
        value=True,
        help="When enabled, loads instant pre-computed results for demo cases "
        "instead of running the live pipeline (which requires model downloads).",
    )
with col_demo:
    demo_label = st.selectbox("Demo case", options=list(DEMO_CASES.keys()))
    demo_case_id = DEMO_CASES[demo_label]

run_clicked = st.button("Run Pipeline", type="primary", use_container_width=True)

# ---- EXECUTION SECTION ----------------------------------------------------

if run_clicked:
    result = None

    # Path A: Pre-computed demo results
    if use_precomputed and demo_case_id:
        raw_json = _load_precomputed(demo_case_id)
        if raw_json is not None:
            from ui.helpers.backend import get_pipeline_module

            pipeline_mod = get_pipeline_module()
            PipelineResult = pipeline_mod.PipelineResult
            result = PipelineResult.model_validate_json(raw_json)
            st.success(f"Loaded pre-computed results for {demo_label}.")
        else:
            st.warning(
                "Pre-computed results not found. "
                "Run `python scripts/precompute_demo.py` first."
            )
            # Fall through to live execution if input_data available

    # Path B: Live pipeline execution
    if result is None:
        # Determine effective input
        effective_input = input_data

        # If no custom input but a demo case selected, use demo case text
        if effective_input is None and demo_case_id:
            # Try loading the demo case source from the gold standard data
            gold_std = Path(__file__).resolve().parent.parent.parent / "cliniq" / "data" / "gold_standard"
            demo_text_path = gold_std / "text_notes" / f"{demo_case_id}.txt"
            demo_fhir_path = gold_std / "fhir_bundles" / f"{demo_case_id}.json"
            if demo_text_path.exists():
                effective_input = demo_text_path.read_text(encoding="utf-8")
            elif demo_fhir_path.exists():
                effective_input = json.loads(demo_fhir_path.read_text(encoding="utf-8"))
            else:
                st.error(
                    "No input provided and demo case source text not found. "
                    "Please paste a clinical note or upload a file."
                )

        if effective_input is not None:
            # Handle image uploads: save to temp file
            if input_type == "Scanned Image" and hasattr(effective_input, "read"):
                with tempfile.NamedTemporaryFile(
                    suffix=".png", delete=False
                ) as tmp:
                    tmp.write(effective_input.read())
                    effective_input = tmp.name

            result = run_pipeline_with_status(
                effective_input, use_llm_queries=False
            )
        elif not (use_precomputed and demo_case_id):
            st.error(
                "No input provided. Paste a clinical note, upload a file, "
                "or select a demo case."
            )

    # Store result in session state
    if result is not None:
        st.session_state["pipeline_result"] = result
        st.session_state["active_case_id"] = demo_case_id

# ---- RESULTS SECTION ------------------------------------------------------

result = st.session_state.get("pipeline_result")

if result is not None:
    st.divider()
    st.subheader("Pipeline Results")

    tab_overview, tab_ner, tab_icd10, tab_cdi = st.tabs(
        ["Overview", "NER Entities", "ICD-10 Codes", "CDI Analysis"]
    )

    # -- Tab 1: Overview ----------------------------------------------------
    with tab_overview:
        # Metrics row
        entity_count = (
            result.nlu_result.entity_count
            if result.nlu_result
            else 0
        )
        code_count = 0
        if result.coding_result:
            if result.coding_result.principal_diagnosis:
                code_count += 1
            code_count += len(result.coding_result.secondary_codes)
            code_count += len(result.coding_result.complication_codes)

        completeness = "N/A"
        completeness_delta = None
        if result.cdi_report is not None:
            score = result.cdi_report.completeness_score
            completeness = f"{score:.0%}"
            # Show penalty as delta (gaps penalize -10% each, conflicts -15% each)
            gap_penalty = result.cdi_report.gap_count * 0.10
            conflict_penalty = result.cdi_report.conflict_count * 0.15
            total_penalty = gap_penalty + conflict_penalty
            if total_penalty > 0:
                completeness_delta = f"-{total_penalty:.0%} penalty"

        render_metric_row(
            {
                "Processing Time": (f"{result.processing_time_ms:.0f}ms", None),
                "Entity Count": (str(entity_count), None),
                "Code Count": (str(code_count), None),
                "Completeness": (completeness, completeness_delta),
            }
        )

        # Document metadata
        st.markdown("---")
        meta_col1, meta_col2, meta_col3 = st.columns(3)
        with meta_col1:
            source_type = result.document.metadata.source_type
            badge_colors = {"fhir": "blue", "text": "green", "image": "orange"}
            badge_color = badge_colors.get(source_type, "gray")
            st.markdown(f"**Source Type:** :{badge_color}[{source_type.upper()}]")
        with meta_col2:
            st.markdown(f"**Patient ID:** {result.document.metadata.patient_id}")
        with meta_col3:
            st.markdown(
                f"**Encounter ID:** {result.document.metadata.encounter_id}"
            )

        # Errors
        if result.errors:
            st.markdown("---")
            st.error(f"{len(result.errors)} error(s) occurred during pipeline execution:")
            for err in result.errors:
                st.markdown(f"- {err}")

    # -- Tab 2: NER Entities ------------------------------------------------
    with tab_ner:
        if result.nlu_result and result.nlu_result.entities:
            st.markdown("#### Annotated Clinical Narrative")
            render_ner_highlights(
                result.document.raw_narrative,
                result.nlu_result.entities,
            )

            st.markdown("---")
            st.markdown("#### Entity Summary")

            # Build entity table data
            entity_rows = []
            for ent in result.nlu_result.entities:
                entity_rows.append(
                    {
                        "Entity Text": ent.text,
                        "Type": ent.entity_type,
                        "Negated": "Yes" if ent.negated else "No",
                        "Confidence": f"{ent.confidence:.2f}",
                        "Qualifiers": ", ".join(ent.qualifiers) if ent.qualifiers else "--",
                    }
                )
            st.dataframe(entity_rows, use_container_width=True)

            # Color legend
            st.markdown("---")
            st.markdown("#### Entity Type Legend")
            legend_cols = st.columns(len(ENTITY_COLORS))
            for col, (etype, color) in zip(legend_cols, ENTITY_COLORS.items()):
                with col:
                    st.markdown(
                        f'<span style="background:{color};padding:2px 8px;'
                        f'border-radius:4px;font-size:0.85rem;">'
                        f"{etype}</span>",
                        unsafe_allow_html=True,
                    )
        else:
            st.info("No entities extracted from this document.")

    # -- Tab 3: ICD-10 Codes ------------------------------------------------
    with tab_icd10:
        if result.coding_result:
            render_principal_diagnosis(result.coding_result.principal_diagnosis)

            if result.coding_result.secondary_codes:
                st.markdown("---")
                render_code_cards(
                    result.coding_result.secondary_codes, "Secondary Codes"
                )

            if result.coding_result.complication_codes:
                st.markdown("---")
                render_code_cards(
                    result.coding_result.complication_codes, "Complications"
                )

            # Sequencing rationale
            if result.coding_result.sequencing_rationale:
                st.markdown("---")
                st.markdown("#### Sequencing Rationale")
                st.info(result.coding_result.sequencing_rationale)

            # Retrieval stats
            if result.coding_result.retrieval_stats:
                with st.expander("Retrieval Statistics"):
                    st.json(result.coding_result.retrieval_stats)
        else:
            st.info("No coding results available.")

    # -- Tab 4: CDI Analysis ------------------------------------------------
    with tab_cdi:
        if result.cdi_report is None:
            st.info("CDI analysis was not run for this case.")
        else:
            cdi = result.cdi_report

            # Completeness score gauge
            st.markdown("#### Completeness Score")
            gap_penalty = cdi.gap_count * 0.10
            conflict_penalty = cdi.conflict_count * 0.15
            total_penalty = gap_penalty + conflict_penalty
            delta_str = None
            if total_penalty > 0:
                delta_str = f"-{total_penalty:.0%} penalty"
            st.metric(
                label="Documentation Completeness",
                value=f"{cdi.completeness_score:.0%}",
                delta=delta_str,
                delta_color="inverse",
            )

            # Documentation Gaps
            st.markdown("---")
            st.markdown(f"#### Documentation Gaps ({cdi.gap_count})")
            if cdi.documentation_gaps:
                for i, gap in enumerate(cdi.documentation_gaps, 1):
                    with st.expander(
                        f"Gap {i}: {gap.code} -- {gap.description}"
                    ):
                        st.markdown(f"**Missing Qualifier:** {gap.missing_qualifier}")
                        st.markdown(f"**Physician Query:** {gap.physician_query}")
                        st.markdown(f"**Evidence:** {gap.evidence_text}")
                        st.caption(f"Confidence: {gap.confidence:.2f}")
            else:
                st.success("No documentation gaps identified.")

            # Missed Diagnoses
            st.markdown("---")
            st.markdown(
                f"#### Missed Diagnoses ({len(cdi.missed_diagnoses)})"
            )
            if cdi.missed_diagnoses:
                for i, missed in enumerate(cdi.missed_diagnoses, 1):
                    with st.expander(
                        f"Missed {i}: {missed.suggested_code} -- {missed.description}"
                    ):
                        st.markdown(
                            f"**Co-coded with:** {missed.co_coded_with}"
                        )
                        st.markdown(
                            f"**Co-occurrence Weight:** "
                            f"{missed.co_occurrence_weight:.2f}"
                        )
                        st.markdown(f"**Evidence:** {missed.evidence_text}")
            else:
                st.success("No missed diagnoses identified.")

            # Code Conflicts
            st.markdown("---")
            st.markdown(
                f"#### Code Conflicts ({cdi.conflict_count})"
            )
            if cdi.code_conflicts:
                for i, conflict in enumerate(cdi.code_conflicts, 1):
                    st.warning(
                        f"**Conflict {i}:** {conflict.code_a} vs "
                        f"{conflict.code_b}\n\n"
                        f"**Reason:** {conflict.conflict_reason}\n\n"
                        f"**Recommendation:** {conflict.recommendation}"
                    )
            else:
                st.success("No code conflicts detected.")

        # Navigation hints
        st.markdown("---")
        st.markdown("#### Continue Analysis")
        nav_col1, nav_col2 = st.columns(2)
        with nav_col1:
            st.page_link(
                "pages/kg_viewer.py",
                label="View Knowledge Graph",
                icon=":material/hub:",
            )
        with nav_col2:
            st.page_link(
                "pages/audit_trail.py",
                label="View Audit Trail",
                icon=":material/fact_check:",
            )
