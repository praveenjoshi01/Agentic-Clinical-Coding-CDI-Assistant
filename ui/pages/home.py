"""
Home / Landing page for ClinIQ.

Communicates the platform's value proposition, shows architecture at a
glance, model registry, and provides clear navigation to all functional
pages. Lightweight -- no ML imports.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ui.helpers.backend import is_v2_backend

_V2 = is_v2_backend()

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

if _V2:
    st.info(
        "A multi-modal pipeline that ingests clinical data, extracts entities, "
        "assigns ICD-10 codes, and detects documentation gaps -- powered by "
        "OpenAI GPT-4o, text-embedding-3-small, and gpt-4o-mini-transcribe."
    )
else:
    st.info(
        "A fully local, multi-modal pipeline that ingests clinical data, extracts "
        "entities, assigns ICD-10 codes, and detects documentation gaps -- all "
        "using OSS models. No API keys. No cloud dependencies."
    )

# Value propositions
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("#### Multi-Modal Ingestion")
    if _V2:
        st.caption("FHIR R4 bundles, free-text clinical notes, and scanned images via GPT-4o vision.")
    else:
        st.caption("FHIR R4 bundles, free-text clinical notes, and scanned images via SmolVLM OCR.")

with col2:
    st.markdown("#### Explainable AI")
    st.caption(
        "Full audit trail with per-stage chain-of-thought traces, evidence attribution, "
        "and retrieval logs for every coding decision."
    )

with col3:
    if _V2:
        st.markdown("#### OpenAI-Powered")
        st.caption(
            "GPT-4o for reasoning & NER, text-embedding-3-small for RAG, "
            "gpt-4o-mini-transcribe for ambient transcription. All via OpenAI API."
        )
    else:
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

if _V2:
    st.markdown(
        """
```
Clinical Document
       |
       v
 [M1: Ingest]  --  FHIR R4 parse / text extract / GPT-4o vision
       |
       v
 [M2: NER]     --  GPT-4o biomedical NER with negation & qualifiers
       |
       v
 [M3: RAG Coding] -- text-embedding-3-small retrieval + GPT-4o reasoning
       |
       v
 [M4: CDI Agent]   -- Knowledge-graph gap detection, conflict alerts, GPT-4o queries
       |
       v
 [M5: Audit Trail] -- Per-stage chain-of-thought traces & evidence attribution
```
"""
    )
else:
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
    if _V2:
        st.markdown(
            """
**M1 -- Ingestion:** Accepts FHIR R4 JSON bundles (parsed via fhir.resources),
plain-text clinical notes, and scanned images (OCR via GPT-4o vision). Outputs a
validated `ClinicalDocument` Pydantic model with normalized sections.

**M2 -- Named Entity Recognition:** Uses GPT-4o for biomedical NER with
integrated negation detection and qualifier capture in a single API call.
Extracts diagnoses, procedures, medications, anatomical sites, lab values,
and qualifiers with confidence scores.

**M3 -- RAG-Based ICD-10 Coding:** Embeds entities with `text-embedding-3-small`,
retrieves candidate codes from a FAISS flat index of ~70k ICD-10-CM codes,
and uses GPT-4o for combined reranking, selection, and chain-of-thought rationale.

**M4 -- CDI Agent:** Builds a NetworkX knowledge graph from extracted entities
and assigned codes. Detects documentation gaps, code conflicts, and missed
diagnoses using curated clinical rules. Uses GPT-4o for physician query generation.

**M5 -- Explainability & Audit Trail:** Captures per-stage timing, I/O
summaries, chain-of-thought reasoning, retrieval logs, and evidence spans.
Produces a complete audit trail for regulatory compliance and clinical review.

**M6 -- Ambient Mode:** Records doctor-patient encounters, transcribes audio
via OpenAI gpt-4o-mini-transcribe, generates structured SOAP notes with GPT-4o, and runs
the full CDI pipeline for documentation gap detection and coding disambiguation.
"""
        )
    else:
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

if _V2:
    st.subheader("OpenAI Model Registry")

    model_data = {
        "Role": [
            "NER + Reasoning + CDI",
            "Embeddings",
            "Audio Transcription",
        ],
        "Model": [
            "GPT-4o",
            "text-embedding-3-small",
            "gpt-4o-mini-transcribe",
        ],
        "Dimensions / Notes": [
            "Handles NER, code selection, CDI queries, and note generation",
            "1536-d embeddings for FAISS index & RAG retrieval",
            "Audio-to-text for ambient mode transcription",
        ],
        "Replaces (v1)": [
            "d4data NER + Qwen 1.5B + cross-encoder",
            "bge-small-en-v1.5 (384-d)",
            "faster-whisper (local)",
        ],
    }
else:
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
            "Clinical Q&A assistant with pre-seeded questions "
            "covering the full ClinIQ system."
        )
        st.page_link("pages/qa_bot.py", label="Open QA Bot", icon=":material/chat:")

eval_col, ambient_col, _ = st.columns(3)
with eval_col:
    with st.container(border=True):
        st.markdown("##### Evaluation Metrics")
        st.caption(
            "Radar and bar charts comparing actual vs target metrics "
            "across all 5 pipeline modules."
        )
        st.page_link("pages/eval_dashboard.py", label="Open Eval Dashboard", icon=":material/assessment:")

with ambient_col:
    with st.container(border=True):
        st.markdown("##### Ambient Mode")
        st.caption(
            "Record doctor-patient encounters, auto-generate SOAP notes, "
            "and detect documentation gaps with coding disambiguation."
        )
        st.page_link("pages/ambient_mode.py", label="Open Ambient Mode", icon=":material/mic:")

st.divider()

# ---------------------------------------------------------------------------
# Technology Stack
# ---------------------------------------------------------------------------

with st.expander("Technology Stack", expanded=False):
    tech_cols = st.columns(3)
    with tech_cols[0]:
        if _V2:
            st.markdown(
                """
**Core:**
- Python 3.11+
- OpenAI API (GPT-4o)
- openai SDK
"""
            )
        else:
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
