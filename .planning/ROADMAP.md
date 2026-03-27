# Roadmap: ClinIQ — Agentic Clinical Coding & CDI Intelligence Platform

## Overview

ClinIQ delivers a fully local, multi-modal clinical coding pipeline with explainable AI reasoning. Starting from Week 1's foundation (repo scaffold, model manager, FAISS index, NetworkX graph, test cases), we build the core NER-to-coding pipeline, add knowledge graph CDI intelligence, then complete evaluation and demo UI. Each phase delivers a complete, verifiable capability running on OSS models without API dependencies.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Core Pipeline & Test Data Foundation** - Multi-modal ingestion, clinical NER, RAG-based ICD-10 coding, plus comprehensive synthetic test data for all modules
- [x] **Phase 2: CDI Intelligence Layer** - Knowledge graph reasoning, gap detection, and explainability
- [ ] **Phase 3: Evaluation & Demo UI** - Quantitative validation suite and 5-page Streamlit demo
- [ ] **Phase 4: Demo UI for the Whole App** - Polished 7-page Streamlit demo with interactive KG, evaluation charts, and QA bot
- [x] **Phase 5: Ambient Listening Mode** - Real-time session recording with auto-generated clinical notes, documentation gap detection, and coding disambiguation
- [ ] **Phase 6: ClinIQ v2 — OpenAI Backend** - Create cliniq_v2 package mirroring all capabilities with OpenAI models replacing local OSS models, plus API key configuration at UI startup

## Phase Details

### Phase 1: Core Pipeline & Test Data Foundation
**Goal**: Clinical notes (FHIR/text/images) produce ICD-10 code assignments with confidence scores, and all synthetic test data for downstream modules is generated
**Depends on**: Nothing (foundation already built in Week 1)
**Requirements**: INGS-01, INGS-02, INGS-03, INGS-04, INGS-05, NLU-01, NLU-02, NLU-03, NLU-04, NLU-05, RAG-01, RAG-02, RAG-03, RAG-04, RAG-05, RAG-06, EVAL-08
**Success Criteria** (what must be TRUE):
  1. User submits FHIR R4 JSON and system extracts clinical entities with negation detection
  2. User submits plain text note and system assigns top-3 ICD-10 codes with structured rationale
  3. User submits scanned clinical image (PNG/JPG) and system extracts text via SmolVLM and codes it
  4. System sequences codes into principal diagnosis, comorbidities, and complications automatically
  5. All outputs include per-entity and per-code confidence scores above validation threshold (0.80)
  6. Complete gold standard test suite exists with 20 synthetic cases covering all modules: synthetic FHIR bundles, PIL-generated scanned note images, expert-assigned ICD-10 codes, entity labels with negation/qualifiers, CDI gap annotations, sample KG qualification rules, and expected outputs for evaluation fixtures
**Plans:** 7 plans

Plans:
- [x] 01-01-PLAN.md — Project scaffold, Pydantic schemas, config, and model manager
- [x] 01-02-PLAN.md — ICD-10 data loading, FAISS index builder, retriever, and reranker
- [x] 01-03-PLAN.md — Multi-modal ingestion module (FHIR, text, image parsers)
- [x] 01-04-PLAN.md — Clinical NER pipeline with negation detection and qualifier capture
- [x] 01-05-PLAN.md — RAG-based ICD-10 coding with retrieval, reranking, and LLM reasoning
- [x] 01-06-PLAN.md — Pipeline orchestrator, gold standard test data generation (20 cases)
- [x] 01-07-PLAN.md — Gap closure: gold standard completeness + Pydantic validation

### Phase 2: CDI Intelligence Layer
**Goal**: Knowledge graph identifies documentation gaps, suggests missed diagnoses, and produces audit trails
**Depends on**: Phase 1 (requires NER entities, RAG codes, and test data as input)
**Requirements**: CDI-01, CDI-02, CDI-03, CDI-04, CDI-05, CDI-06, EXPL-01, EXPL-02, EXPL-03, EXPL-04, EXPL-05
**Success Criteria** (what must be TRUE):
  1. User reviews case and sees natural language physician queries for every documentation gap
  2. System flags invalid code combinations via conflict detection with accuracy above 0.90
  3. System suggests potential missed diagnoses via COMMONLY_CO_CODED graph edges
  4. User clicks any suggested code and sees supporting text span from original clinical note
  5. Every reasoning step has captured chain-of-thought trace for audit compliance
**Plans:** 6 plans

Plans:
- [x] 02-01-PLAN.md — CDI/Audit Pydantic schemas, KG schema constants, KG builder with curated rules
- [x] 02-02-PLAN.md — KG querier functions (gap detection, conflict detection, co-occurrence) + unit tests
- [x] 02-03-PLAN.md — Explainability module (audit trail builder, CoT capture, evidence linking) + unit tests
- [x] 02-04-PLAN.md — CDI agent module (physician query generation, CDIReport assembly) + unit tests
- [x] 02-05-PLAN.md — Pipeline integration (CDI stage + audit trail instrumentation) + integration tests
- [x] 02-06-PLAN.md — LLM-as-judge evaluation (query relevance CDI-06, CoT coherence EXPL-05) + tests

### Phase 3: Evaluation & Demo UI
**Goal**: Polished 5-page Streamlit demo with quantitative metrics proving all pipeline stages meet targets
**Depends on**: Phases 1 & 2 (requires complete pipeline to evaluate and visualize)
**Requirements**: VIZ-01, VIZ-02, VIZ-03, VIZ-04, EVAL-01, EVAL-02, EVAL-03, EVAL-04, EVAL-05, EVAL-06, EVAL-07, UI-01, UI-02, UI-03, UI-04, UI-05, UI-06, UI-07
**Success Criteria** (what must be TRUE):
  1. User runs automated eval suite and sees metrics table showing all targets met (NER F1 >= 0.80, Top-3 >= 0.85, MRR >= 0.75)
  2. User navigates 5-page Streamlit app (Pipeline Runner, Eval Dashboard, KG Viewer, Audit Trail, QA Bot) with persistent session state
  3. User clicks node in interactive PyVis knowledge graph and sees code description, evidence text, and CDI query
  4. User asks QA Bot 5 standard clinical questions and receives correct answers via RAG over project docs
  5. All 20 synthetic test cases pass validation (100% schema compliance, FHIR parse accuracy >= 95%)
**Plans**: TBD (split across evaluation harness and UI pages)

Plans:
- [ ] 03-01: TBD during phase planning
- [ ] 03-02: TBD during phase planning
- [ ] 03-03: TBD during phase planning

### Phase 4: Demo UI for the Whole App
**Goal**: Production-ready 7-page Streamlit application showcasing the entire ClinIQ pipeline with interactive visualizations, pre-computed demo results, and a QA chatbot
**Depends on**: Phases 1 & 2 (requires complete pipeline backend; builds UI from scratch)
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05, UI-06, UI-07, VIZ-01, VIZ-02, VIZ-03, VIZ-04
**Success Criteria** (what must be TRUE):
  1. User opens Streamlit app and sees polished landing page with project overview and navigation
  2. User selects a demo case on Pipeline Runner and sees full pipeline results instantly (NER highlights, ICD-10 cards, CDI findings)
  3. User views interactive PyVis knowledge graph with green/amber/red nodes and click-to-see-details
  4. User expands audit trail stages and sees per-stage timing, CoT traces, and evidence spans
  5. User views evaluation radar chart and per-module bar charts with pass/fail badges
  6. User asks QA Bot pre-seeded clinical questions and gets correct, instant answers
  7. Session state persists across all page navigations
**Plans:** 5 plans

Plans:
- [ ] 04-01-PLAN.md — App shell, theme, reusable components, and pre-computed demo data
- [ ] 04-02-PLAN.md — Pipeline Runner page (upload, run, NER highlights, code cards, CDI display)
- [ ] 04-03-PLAN.md — KG Viewer page (PyVis graph) and Audit Trail page (expandable traces)
- [ ] 04-04-PLAN.md — Eval Dashboard page (Plotly charts) and QA Bot page (chat interface)
- [ ] 04-05-PLAN.md — Home/Landing page, integration polish, and visual verification

### Phase 5: Ambient Listening Mode
**Goal**: Enable passive real-time audio listening during physician-patient encounters, with automatic generation of structured clinical notes, documentation gap detection, missed diagnosis flagging, and coding disambiguation upon session completion
**Depends on**: Phase 4 (requires complete pipeline backend and UI framework)
**Requirements**: AMB-01, AMB-02, AMB-03, AMB-04, AMB-05, AMB-06
**Success Criteria** (what must be TRUE):
  1. User clicks "Start Ambient Mode" and system begins passively listening to doctor-patient conversation with visible session timer
  2. User clicks "End Session" and system automatically generates structured clinical notes from the encounter transcript
  3. System identifies documentation gaps — missing or incomplete clinical information required for accurate documentation
  4. System flags missed or potential diagnoses discussed or implied during the encounter but not formally captured
  5. System detects coding ambiguities (unclear clinical language for ICD/CPT assignment) and code conflicts (contradictory documentation)
  6. System presents disambiguation suggestions and recommended clarifications in a reviewable, actionable format before provider finalizes the note
**Plans:** 3 plans

Plans:
- [x] 05-01-PLAN.md — Ambient Pydantic schemas, backend module (transcription + note gen + pipeline), dependency setup
- [x] 05-02-PLAN.md — Pre-computed ambient demo encounters (2 scenarios) and regeneration script
- [x] 05-03-PLAN.md — Ambient Mode UI page (session lifecycle, dual-path, disambiguation) and app integration

### Phase 6: ClinIQ v2 — OpenAI Backend
**Goal**: Create cliniq_v2 package that mirrors all ClinIQ capabilities but replaces local OSS models (Qwen, bge-small, SmolVLM, d4data NER, cross-encoder, whisper) with OpenAI API calls (GPT-4o, text-embedding-3-small, Whisper API), plus UI-level API key configuration at startup
**Depends on**: Phase 5 (requires complete pipeline and UI as reference implementation)
**Requirements**: OAI-01, OAI-02, OAI-03, OAI-04, OAI-05, OAI-06
**Success Criteria** (what must be TRUE):
  1. cliniq_v2 folder exists with all pipeline modules (ingestion, NER, RAG coding, CDI, explainability, ambient) using OpenAI API instead of local models
  2. UI prompts for OpenAI API key on startup and validates it before allowing access to any page
  3. All existing UI pages work with cliniq_v2 backend (pipeline runner, KG viewer, audit trail, eval dashboard, QA bot, ambient mode)
  4. No local model downloads required — all inference via OpenAI API (GPT-4o for reasoning/NER/CDI, text-embedding-3-small for embeddings, Whisper API for audio)
  5. Original cliniq package remains unchanged and functional (backward compatible)
**Plans:** 6 plans

Plans:
- [x] 06-01-PLAN.md — cliniq_v2 package foundation (config, api_client) + m1_ingest + m2_nlu
- [x] 06-02-PLAN.md — RAG infrastructure (FAISS index builder, retriever) + m3_rag_coding
- [x] 06-03-PLAN.md — m4_cdi (GPT-4o queries) + m5_explainability (re-export) + m6_ambient (Whisper API)
- [x] 06-04-PLAN.md — Pipeline orchestrator + evaluation/llm_judge (GPT-4o judge)
- [x] 06-05-PLAN.md — UI API key gate + backend selector + page import updates + FAISS index check
- [x] 06-06-PLAN.md — v2 FAISS index build script

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Core Pipeline & Test Data Foundation | 7/7 | ✓ Complete | 2026-03-18 |
| 2. CDI Intelligence Layer | 6/6 | ✓ Complete | 2026-03-18 |
| 3. Evaluation & Demo UI | 0/TBD | Not started | - |
| 4. Demo UI for the Whole App | 0/5 | Planned | - |
| 5. Ambient Listening Mode | 3/3 | ✓ Complete | 2026-03-24 |
| 6. ClinIQ v2 — OpenAI Backend | 6/6 | ✓ Complete | 2026-03-27 |

### Phase 7: Optional Pinecone vector DB instead of FAISS when API key provided

**Goal:** Add optional Pinecone serverless vector DB as an alternative to local FAISS for ICD-10 code retrieval in the v2 (OpenAI) backend path, with transparent fallback to FAISS when no Pinecone key is provided
**Depends on:** Phase 6
**Plans:** 2 plans

Plans:
- [ ] 07-01-PLAN.md — Retriever abstraction (BaseRetriever Protocol), PineconeClient singleton, PineconeRetriever, factory, m3_rag_coding wiring
- [ ] 07-02-PLAN.md — Pinecone index population script, UI API key gate with optional Pinecone field, sidebar indicator

---
*Roadmap created: 2026-03-18*
*Roadmap revised: 2026-03-18 (moved EVAL-08 to Phase 1, added comprehensive test data generation)*
*Phase 1 planned: 2026-03-18 (6 plans across 5 waves)*
*Depth: quick (3 phases, 1-3 plans each)*
*Coverage: 45/45 v1 requirements mapped*
*Phase 1 complete: 2026-03-18 (7/7 plans, verification passed 6/6)*
*Phase 2 planned: 2026-03-18 (6 plans across 5 waves)*
*Phase 2 complete: 2026-03-18 (6/6 plans, verification passed 5/5)*
*Phase 4 planned: 2026-03-18 (5 plans across 3 waves)*
*Phase 5 planned: 2026-03-24 (3 plans across 2 waves)*
*Phase 5 complete: 2026-03-24 (3/3 plans, verification passed 6/6)*
*Phase 6 planned: 2026-03-27 (6 plans across 4 waves, plan 06-06 added for FAISS build script + backend-aware execution)*
*Phase 6 revised: 2026-03-27 (moved FAISS index check from 06-06 to 06-05, eliminated file overlap)*
*Phase 6 complete: 2026-03-27 (6/6 plans, verification passed 31/31)*
*Phase 7 planned: 2026-03-27 (2 plans across 2 waves)*
