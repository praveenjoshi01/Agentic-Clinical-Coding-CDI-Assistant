"""
Pipeline progress wrapper using st.status for real-time feedback.

Wraps run_pipeline_audited inside an expandable status container
that shows per-stage progress updates.
"""

from __future__ import annotations

import logging
from typing import Union
from pathlib import Path

import streamlit as st

logger = logging.getLogger(__name__)


@st.cache_resource
def _get_model_manager():
    """Cache the ModelManager singleton to prevent reloading models on every rerun."""
    from cliniq.modules.model_manager import ModelManager
    return ModelManager()


def run_pipeline_with_status(
    input_data: Union[str, dict, Path],
    use_llm_queries: bool = False,
    skip_cdi: bool = False,
):
    """Run the audited pipeline with real-time st.status progress updates.

    Wraps cliniq.pipeline.run_pipeline_audited inside an st.status container,
    showing per-stage progress messages. On completion, stores the result
    in st.session_state["pipeline_result"].

    Args:
        input_data: FHIR bundle (dict), plain text (str), or image path (str/Path).
        use_llm_queries: If True, generate physician queries via Qwen LLM.
        skip_cdi: If True, skip the CDI analysis stage.

    Returns:
        PipelineResult with all stage outputs, cdi_report, audit_trail.
    """
    from cliniq.pipeline import run_pipeline_audited, PipelineResult

    with st.status("Running ClinIQ Pipeline...", expanded=True) as status:
        st.write("Stage 1: Ingesting document...")
        st.write("Stage 2: Extracting clinical entities (NER)...")
        st.write("Stage 3: RAG-based ICD-10 coding...")
        if not skip_cdi:
            st.write("Stage 4: CDI analysis (KG-based gap detection)...")
        st.write("Stage 5: Generating audit trail...")

        # Run the full pipeline
        result = run_pipeline_audited(
            input_data,
            use_llm_queries=use_llm_queries,
            skip_cdi=skip_cdi,
        )

        if result.errors:
            status.update(
                label=f"Pipeline complete with {len(result.errors)} error(s)",
                state="error",
                expanded=True,
            )
            for err in result.errors:
                st.error(err)
        else:
            status.update(
                label=f"Pipeline complete! ({result.processing_time_ms:.0f}ms)",
                state="complete",
                expanded=False,
            )

    # Store result in session state for cross-page access
    st.session_state["pipeline_result"] = result

    return result
