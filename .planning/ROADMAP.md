# Roadmap: ClinIQ — Agentic Clinical Coding & CDI Intelligence Platform

## Overview

ClinIQ delivers a fully local, multi-modal clinical coding pipeline with explainable AI reasoning. Starting from Week 1's foundation (repo scaffold, model manager, FAISS index, NetworkX graph, test cases), we build the core NER-to-coding pipeline, add knowledge graph CDI intelligence, then complete evaluation and demo UI. Each phase delivers a complete, verifiable capability running on OSS models without API dependencies.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Core Pipeline & Test Data Foundation** - Multi-modal ingestion, clinical NER, RAG-based ICD-10 coding, plus comprehensive synthetic test data for all modules
- [ ] **Phase 2: CDI Intelligence Layer** - Knowledge graph reasoning, gap detection, and explainability
- [ ] **Phase 3: Evaluation & Demo UI** - Quantitative validation suite and 5-page Streamlit demo

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
- [ ] 02-01-PLAN.md — CDI/Audit Pydantic schemas, KG schema constants, KG builder with curated rules
- [ ] 02-02-PLAN.md — KG querier functions (gap detection, conflict detection, co-occurrence) + unit tests
- [ ] 02-03-PLAN.md — Explainability module (audit trail builder, CoT capture, evidence linking) + unit tests
- [ ] 02-04-PLAN.md — CDI agent module (physician query generation, CDIReport assembly) + unit tests
- [ ] 02-05-PLAN.md — Pipeline integration (CDI stage + audit trail instrumentation) + integration tests
- [ ] 02-06-PLAN.md — LLM-as-judge evaluation (query relevance CDI-06, CoT coherence EXPL-05) + tests

### Phase 3: Evaluation & Demo UI
**Goal**: Polished 5-page Streamlit demo with quantitative metrics proving all pipeline stages meet targets
**Depends on**: Phases 1 & 2 (requires complete pipeline to evaluate and visualize)
**Requirements**: VIZ-01, VIZ-02, VIZ-03, VIZ-04, EVAL-01, EVAL-02, EVAL-03, EVAL-04, EVAL-05, EVAL-06, EVAL-07, UI-01, UI-02, UI-03, UI-04, UI-05, UI-06, UI-07
**Success Criteria** (what must be TRUE):
  1. User runs automated eval suite and sees metrics table showing all targets met (NER F1 >= 0.80, Top-3 >= 0.85, MRR >= 0.75)
  2. User navigates 5-page Streamlit app (Pipeline Runner, Eval Dashboard, KG Viewer, Audit Trail, QA Bot) with persistent session state
  3. User clicks node in interactive PyVis knowledge graph and sees code description, evidence text, and CDI query
  4. User asks QA Bot 5 standard interview questions and receives correct answers via RAG over project docs
  5. All 20 synthetic test cases pass validation (100% schema compliance, FHIR parse accuracy >= 95%)
**Plans**: TBD (split across evaluation harness and UI pages)

Plans:
- [ ] 03-01: TBD during phase planning
- [ ] 03-02: TBD during phase planning
- [ ] 03-03: TBD during phase planning

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Core Pipeline & Test Data Foundation | 7/7 | ✓ Complete | 2026-03-18 |
| 2. CDI Intelligence Layer | 0/6 | Not started | - |
| 3. Evaluation & Demo UI | 0/TBD | Not started | - |

---
*Roadmap created: 2026-03-18*
*Roadmap revised: 2026-03-18 (moved EVAL-08 to Phase 1, added comprehensive test data generation)*
*Phase 1 planned: 2026-03-18 (6 plans across 5 waves)*
*Depth: quick (3 phases, 1-3 plans each)*
*Coverage: 45/45 v1 requirements mapped*
*Phase 1 complete: 2026-03-18 (7/7 plans, verification passed 6/6)*
