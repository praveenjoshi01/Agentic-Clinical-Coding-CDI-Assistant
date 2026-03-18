"""
Home / Landing page for ClinIQ demo.

First page the interviewer sees. Communicates project value proposition,
shows architecture at a glance, model registry, and provides clear
navigation to all functional pages. Lightweight -- no ML imports.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Hero Section
# ---------------------------------------------------------------------------

st.markdown(
    "<h1 style='text-align:center; margin-bottom:0;'>ClinIQ</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align:center; font-size:1.25rem; color:#666; margin-top:0;'>"
    "Agentic Clinical Coding &amp; CDI Intelligence Platform</p>",
    unsafe_allow_html=True,
)

st.info(
    "A fully local, multi-modal pipeline that ingests clinical data, extracts "
    "entities, assigns ICD-10 codes, and detects documentation gaps -- all "
    "using OSS models. No API keys. No cloud dependencies."
)

# Value propositions
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("#### Multi-Modal Ingestion")
    st.caption("FHIR R4 bundles, free-text clinical notes, and scanned images via SmolVLM OCR.")

with col2:
    st.markdown("#### Explainable AI")
    st.caption(
        "Full audit trail with per-stage chain-of-thought traces, evidence attribution, "
        "and retrieval logs for every coding decision."
    )

with col3:
    st.markdown("#### 100% Local")
    st.caption(
        "Five specialised OSS models (total ~2.1 GB). Runs entirely on-device -- no API keys, "
        "no cloud calls, no data leaves the machine."
    )

st.divider()

# ---------------------------------------------------------------------------
# Architecture Overview
# ---------------------------------------------------------------------------

st.subheader("Architecture Overview")

st.markdown(
    """
```
Clinical Document
       |
       v
 [M1: Ingest]  --  FHIR R4 parse / text extract / SmolVLM OCR
       |
       v
 [M2: NER]     --  Biomedical NER with negation & qualifier detection
       |
       v
 [M3: RAG Coding] -- FAISS retrieval + cross-encoder reranking + Qwen reasoning
       |
       v
 [M4: CDI Agent]   -- Knowledge-graph gap detection, conflict alerts, physician queries
       |
       v
 [M5: Audit Trail] -- Per-stage chain-of-thought traces & evidence attribution
```
"""
)

with st.expander("Module Details", expanded=False):
    st.markdown(
        """
**M1 -- Ingestion:** Accepts FHIR R4 JSON bundles (parsed via fhir.resources),
plain-text clinical notes, and scanned images (OCR via SmolVLM). Outputs a
validated `ClinicalDocument` Pydantic model with normalized sections.

**M2 -- Named Entity Recognition:** Uses `d4data/biomedical-ner-all` (110M) for
biomedical NER with rule-based negation detection and qualifier capture. Extracts
diagnoses, procedures, medications, anatomical sites, lab values, and qualifiers
with confidence scores.

**M3 -- RAG-Based ICD-10 Coding:** Embeds entities with `bge-small-en-v1.5`,
retrieves candidate codes from a FAISS flat index of ~70k ICD-10-CM codes,
reranks with `ms-marco-MiniLM-L-6-v2`, and uses `Qwen2.5-1.5B-Instruct` for
final code selection with chain-of-thought rationale.

**M4 -- CDI Agent:** Builds a NetworkX knowledge graph from extracted entities
and assigned codes. Detects documentation gaps, code conflicts, and missed
diagnoses using curated clinical rules. Generates physician queries for
unresolved ambiguities.

**M5 -- Explainability & Audit Trail:** Captures per-stage timing, I/O
summaries, chain-of-thought reasoning, retrieval logs, and evidence spans.
Produces a complete audit trail for regulatory compliance and clinical review.
"""
    )

st.divider()

# ---------------------------------------------------------------------------
# Model Registry
# ---------------------------------------------------------------------------

st.subheader("OSS Model Registry")

model_data = {
    "Alias": [
        "CLINICAL_NER",
        "REASONING_LLM",
        "EMBEDDER",
        "MULTIMODAL",
        "RERANKER",
    ],
    "HuggingFace Model ID": [
        "d4data/biomedical-ner-all",
        "Qwen/Qwen2.5-1.5B-Instruct",
        "BAAI/bge-small-en-v1.5",
        "HuggingFaceTB/SmolVLM-Instruct",
        "cross-encoder/ms-marco-MiniLM-L-6-v2",
    ],
    "Size": ["110M", "1.5B", "33M", "256M", "22M"],
    "Purpose": [
        "Biomedical entity extraction",
        "CDI reasoning, query generation, CoT",
        "RAG embeddings (FAISS index)",
        "Image-to-text OCR ingestion",
        "RAG reranking (cross-encoder)",
    ],
}

st.dataframe(
    pd.DataFrame(model_data),
    use_container_width=True,
    hide_index=True,
)

st.divider()

# ---------------------------------------------------------------------------
# Quick Start Navigation
# ---------------------------------------------------------------------------

st.subheader("Quick Start")

nav_col1, nav_col2, nav_col3 = st.columns(3)

with nav_col1:
    with st.container(border=True):
        st.markdown("##### Run the Pipeline")
        st.caption(
            "Upload a clinical document or select a demo case. "
            "View NER annotations, ICD-10 codes, and CDI findings."
        )
        st.page_link("pages/pipeline_runner.py", label="Open Pipeline Runner", icon=":material/play_arrow:")

with nav_col2:
    with st.container(border=True):
        st.markdown("##### View Knowledge Graph")
        st.caption(
            "Explore the interactive PyVis graph with CDI-based "
            "color coding: green (ok), amber (gap), red (conflict)."
        )
        st.page_link("pages/kg_viewer.py", label="Open KG Viewer", icon=":material/hub:")

with nav_col3:
    with st.container(border=True):
        st.markdown("##### Ask Questions")
        st.caption(
            "Interview-ready Q&A bot with 8 pre-seeded questions "
            "covering the full ClinIQ system."
        )
        st.page_link("pages/qa_bot.py", label="Open QA Bot", icon=":material/chat:")

eval_col, _, _ = st.columns(3)
with eval_col:
    with st.container(border=True):
        st.markdown("##### Evaluation Metrics")
        st.caption(
            "Radar and bar charts comparing actual vs target metrics "
            "across all 5 pipeline modules."
        )
        st.page_link("pages/eval_dashboard.py", label="Open Eval Dashboard", icon=":material/assessment:")

st.divider()

# ---------------------------------------------------------------------------
# Technology Stack
# ---------------------------------------------------------------------------

with st.expander("Technology Stack", expanded=False):
    tech_cols = st.columns(3)
    with tech_cols[0]:
        st.markdown(
            """
**Core:**
- Python 3.11+
- PyTorch
- Transformers
- Sentence-Transformers
"""
        )
    with tech_cols[1]:
        st.markdown(
            """
**Data & Search:**
- FAISS (flat index)
- NetworkX
- Pydantic v2
- fhir.resources
"""
        )
    with tech_cols[2]:
        st.markdown(
            """
**UI & Viz:**
- Streamlit
- Plotly
- PyVis
- st-annotated-text
"""
        )
