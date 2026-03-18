# ClinIQ — Agentic Clinical Coding & CDI Intelligence Platform

## What This Is

A fully local, multi-modal, agentic pipeline that ingests clinical data (text, FHIR R4, scanned images), extracts medical entities via NLU, retrieves ICD-10 codes via RAG, detects documentation gaps via a knowledge graph CDI agent, evaluates every step with AI-grade metrics, and visualises the entire reasoning chain in a polished Streamlit demo. Built using only small, specialised OSS HuggingFace models — no API keys required. This is a Principal AI Scientist interview POC for Solventum HIS.

## Core Value

Every clinical note produces correctly sequenced ICD-10 codes with full explainability — from entity extraction through RAG retrieval through KG-based CDI gap detection — all running locally on OSS models, demonstrating agentic clinical AI end-to-end.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Multi-modal ingestion: FHIR R4 JSON, plain text, scanned images (SmolVLM)
- [ ] Clinical NER extraction with negation detection and qualifier capture (d4data/biomedical-ner-all)
- [ ] RAG-based ICD-10 coding with FAISS retrieval + cross-encoder reranking + Qwen reasoning
- [ ] KG CDI agent: NetworkX graph with gap detection, physician query generation, conflict alerts
- [ ] Explainability layer: per-case audit trail with chain-of-thought traces and evidence attribution
- [ ] PyVis interactive knowledge graph visualisation (colour-coded by documentation status)
- [ ] Streamlit demo UI with 5 pages: Pipeline Runner, Eval Dashboard, KG Viewer, Audit Trail, QA Bot
- [ ] QA Bot using Qwen + RAG over project docs for interview Q&A
- [ ] Automated eval suite: 5 module evals with quantitative targets (F1 >= 0.80, Top-3 >= 0.85, MRR >= 0.75, Query relevance >= 0.80)
- [ ] All models downloaded + cached on first run via bootstrap script (~2.1GB total)

### Out of Scope

- Real PHI or HIPAA infrastructure — synthetic data only
- Model fine-tuning during demo — inference only
- Live EHR or real FHIR server connectivity
- Inpatient DRG coding — outpatient + professional fee only for MVP
- Mobile app or cloud deployment

## Context

**Interview target:** Principal AI Scientist role at Solventum HIS. The project directly maps to JD requirements: agentic AI, clinical NLU, FHIR pipelines, RAG, multi-modal AI, knowledge graphs, explainability, and model evaluation frameworks.

**Week 1 foundation already built:** Repo scaffold, model_manager.py (download + cache 5 models), FAISS index builder, NetworkX graph builder, synthetic test cases + gold_standard.json.

**OSS Model Registry:**

| Alias | Model | Size | Purpose |
|-------|-------|------|---------|
| CLINICAL_NER | d4data/biomedical-ner-all | 110M | Entity extraction |
| REASONING_LLM | Qwen/Qwen2.5-1.5B-Instruct | 1.5B | CDI reasoning, query gen, CoT |
| EMBEDDER | BAAI/bge-small-en-v1.5 | 33M | RAG embeddings |
| MULTIMODAL | HuggingFaceTB/SmolVLM-Instruct | 256M | Image-to-text |
| RERANKER | cross-encoder/ms-marco-MiniLM-L-6-v2 | 22M | RAG reranking |

**Repo structure:** `cliniq/` package with `modules/`, `knowledge_graph/`, `rag/`, `evaluation/` subdirs. `ui/` for Streamlit. `data/` for ICD-10 tabular files, Synthea samples, test images. `scripts/` for bootstrap, test image gen, CLI demo.

**Tech stack:** Python, transformers, torch, faiss-cpu, sentence-transformers, networkx, pyvis, fhir.resources, pydantic v2, streamlit, plotly, seqeval, pymupdf, huggingface_hub.

**Evaluation approach:** Each module has quantitative eval with ground truth. Modules 4 and 5 additionally use LLM-as-judge pattern (Qwen evaluating query quality and CoT coherence).

## Constraints

- **All local:** No cloud APIs, no API keys for core pipeline — everything runs on local OSS models
- **Model size:** Total ~2.1GB download; must run on a machine with sufficient RAM for Qwen 1.5B
- **Synthetic data only:** All test cases are synthetic (Synthea FHIR + PIL-generated images + hand-annotated notes)
- **Demo-ready:** Must be polished enough for a live interview walkthrough with progressive disclosure
- **Timeline:** ~3 weeks remaining (Weeks 2-4); Week 1 foundation is complete

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Qwen2.5-1.5B-Instruct for reasoning | Small enough to run locally, instruction-tuned, good structured output | — Pending |
| FAISS flat index over approximate | Only ~70k ICD-10 codes; flat is exact and fast enough | — Pending |
| NetworkX over Neo4j for KG | No external DB dependency; graph fits in memory; simpler demo | — Pending |
| SmolVLM for image ingestion | Smallest viable multimodal model; avoids large VLM downloads | — Pending |
| LLM-as-judge for subjective evals | No human raters available; Qwen with calibrated rubric is pragmatic | — Pending |
| Streamlit over Gradio | Better multi-page support; more professional look for interview demo | — Pending |

---
*Last updated: 2026-03-18 after initialization*
