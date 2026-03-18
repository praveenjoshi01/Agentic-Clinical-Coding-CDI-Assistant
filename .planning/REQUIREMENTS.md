# Requirements: ClinIQ

**Defined:** 2026-03-18
**Core Value:** Every clinical note produces correctly sequenced ICD-10 codes with full explainability — from entity extraction through RAG retrieval through KG-based CDI gap detection — all running locally on OSS models.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Ingestion

- [ ] **INGS-01**: System parses FHIR R4 JSON (DocumentReference, Encounter, Condition, Procedure) into unified ClinicalDocument
- [ ] **INGS-02**: System accepts plain text clinical notes and produces ClinicalDocument
- [ ] **INGS-03**: System extracts clinical text from scanned images (PNG, JPG) via SmolVLM-Instruct
- [ ] **INGS-04**: System detects input modality (FHIR, text, image) and routes to correct parser
- [ ] **INGS-05**: All ingested data validated against Pydantic ClinicalDocument schema (100% pass rate on 20 synthetic cases)

### NLU/NER

- [ ] **NLU-01**: System extracts clinical entities (diagnoses, procedures, medications, anatomical sites) from narrative text using d4data/biomedical-ner-all
- [ ] **NLU-02**: System detects negated entities ("no signs of infection") with accuracy >= 0.85
- [ ] **NLU-03**: System captures severity/type/laterality qualifiers on entities with capture rate >= 0.75
- [ ] **NLU-04**: System produces NLUResult with per-entity confidence scores from model logits
- [ ] **NLU-05**: NER achieves F1 >= 0.80 on held-out synthetic gold standard cases

### RAG Coding

- [ ] **RAG-01**: System retrieves top-20 ICD-10 candidates from FAISS index using bge-small-en-v1.5 embeddings
- [ ] **RAG-02**: System reranks candidates using cross-encoder/ms-marco-MiniLM-L-6-v2 with measurable MRR lift > 0.05
- [ ] **RAG-03**: Qwen2.5-1.5B-Instruct selects most specific code with structured rationale and alternatives
- [ ] **RAG-04**: System sequences codes: principal diagnosis -> comorbidities -> complications
- [ ] **RAG-05**: System flags codes needing higher specificity for CDI agent
- [ ] **RAG-06**: Top-3 accuracy >= 0.85 and MRR >= 0.75 on gold standard cases

### CDI Intelligence

- [ ] **CDI-01**: NetworkX KG queries identify missing qualifiers for codes flagged as needing specificity
- [ ] **CDI-02**: Qwen generates natural language physician queries for each documentation gap
- [ ] **CDI-03**: KG agent suggests potential missed diagnoses via COMMONLY_CO_CODED edges
- [ ] **CDI-04**: KG agent flags invalid code combinations via CONFLICTS_WITH edges
- [ ] **CDI-05**: System produces CDIReport with documentation completeness score (0-1)
- [ ] **CDI-06**: Physician query relevance score >= 0.80 via LLM-as-judge evaluation

### Explainability

- [ ] **EXPL-01**: System produces per-case AuditTrail covering all pipeline stages (ingestion, NER, RAG, KG)
- [ ] **EXPL-02**: Every suggested code has >= 1 supporting text span from the clinical note
- [ ] **EXPL-03**: Raw chain-of-thought traces from Qwen captured for each reasoning step
- [ ] **EXPL-04**: Audit trail includes retrieval log (query -> top-k -> reranked -> selected)
- [ ] **EXPL-05**: CoT coherence score >= 0.82 via LLM-as-judge evaluation

### Visualization

- [ ] **VIZ-01**: PyVis generates interactive HTML knowledge graph for each patient case
- [ ] **VIZ-02**: Nodes colour-coded: green=well-documented, amber=needs CDI query, red=conflict
- [ ] **VIZ-03**: Node click shows code description, evidence text, and CDI query if applicable
- [ ] **VIZ-04**: Graph shows only case-relevant subgraph (not all 70k codes)

### Evaluation

- [ ] **EVAL-01**: Automated eval runner executes all 5 module evaluation suites
- [ ] **EVAL-02**: M1 eval: schema validation pass rate = 100%, FHIR parse accuracy >= 95%
- [ ] **EVAL-03**: M2 eval: NER precision >= 0.82, recall >= 0.80, F1 >= 0.81
- [ ] **EVAL-04**: M3 eval: Top-1 accuracy >= 0.70, Top-3 accuracy >= 0.85, MRR >= 0.75
- [ ] **EVAL-05**: M4 eval: query relevance >= 0.80, conflict detection accuracy >= 0.90
- [ ] **EVAL-06**: M5 eval: trace completeness = 100%, evidence attribution = 100%
- [ ] **EVAL-07**: LLM-as-judge scoring with calibrated rubric for M4 and M5
- [ ] **EVAL-08**: 20 synthetic gold standard cases with expert-assigned labels for ground truth

### UI & Demo

- [ ] **UI-01**: Streamlit Pipeline Runner page: upload FHIR/image/text, run full pipeline, see per-module results
- [ ] **UI-02**: Streamlit Eval Dashboard page: run eval suite, show metrics table + Plotly radar/bar charts
- [ ] **UI-03**: Streamlit KG Viewer page: embedded PyVis graph with case-specific subgraph
- [ ] **UI-04**: Streamlit Audit Trail page: expandable trace for every pipeline decision
- [ ] **UI-05**: Streamlit QA Bot page: Qwen answers questions about the system via RAG over project docs
- [ ] **UI-06**: QA Bot responds correctly to >= 5 standard interview questions (pre-seeded)
- [ ] **UI-07**: All 5 pages share session state correctly across navigation

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Stretch Goals

- **STRETCH-01**: Federated inference simulation (split NER and coding across "hospitals")
- **STRETCH-02**: Edge Veda integration note in README (NER on-device for mobile CDI)
- **STRETCH-03**: Confidence calibration plot (reliability diagram)
- **STRETCH-04**: SNOMED CT second KG layer linked to ICD-10 nodes

### Production Hardening

- **PROD-01**: Real de-identified clinical note validation (MIMIC-III)
- **PROD-02**: Docker containerization for reproducible deployment
- **PROD-03**: CI/CD pipeline with automated eval on commit
- **PROD-04**: Neo4j migration for production-scale KG

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real PHI / HIPAA infrastructure | Synthetic data only; demo POC not production |
| Model fine-tuning | Inference only; discuss fine-tuning strategy in interview |
| Live EHR / real FHIR server | Use synthetic FHIR bundles; show integration architecture |
| Inpatient DRG coding | Outpatient + professional fee only for MVP scope |
| Mobile app / cloud deployment | Desktop Streamlit sufficient for interview demo |
| CPT/HCPCS procedure coding | ICD-10 diagnosis coding demonstrates capability |
| User authentication / RBAC | Single-user demo; mention security in architecture discussion |
| Real-time processing at scale | Pre-computed results acceptable; discuss scaling strategy |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INGS-01 | Phase TBD | Pending |
| INGS-02 | Phase TBD | Pending |
| INGS-03 | Phase TBD | Pending |
| INGS-04 | Phase TBD | Pending |
| INGS-05 | Phase TBD | Pending |
| NLU-01 | Phase TBD | Pending |
| NLU-02 | Phase TBD | Pending |
| NLU-03 | Phase TBD | Pending |
| NLU-04 | Phase TBD | Pending |
| NLU-05 | Phase TBD | Pending |
| RAG-01 | Phase TBD | Pending |
| RAG-02 | Phase TBD | Pending |
| RAG-03 | Phase TBD | Pending |
| RAG-04 | Phase TBD | Pending |
| RAG-05 | Phase TBD | Pending |
| RAG-06 | Phase TBD | Pending |
| CDI-01 | Phase TBD | Pending |
| CDI-02 | Phase TBD | Pending |
| CDI-03 | Phase TBD | Pending |
| CDI-04 | Phase TBD | Pending |
| CDI-05 | Phase TBD | Pending |
| CDI-06 | Phase TBD | Pending |
| EXPL-01 | Phase TBD | Pending |
| EXPL-02 | Phase TBD | Pending |
| EXPL-03 | Phase TBD | Pending |
| EXPL-04 | Phase TBD | Pending |
| EXPL-05 | Phase TBD | Pending |
| VIZ-01 | Phase TBD | Pending |
| VIZ-02 | Phase TBD | Pending |
| VIZ-03 | Phase TBD | Pending |
| VIZ-04 | Phase TBD | Pending |
| EVAL-01 | Phase TBD | Pending |
| EVAL-02 | Phase TBD | Pending |
| EVAL-03 | Phase TBD | Pending |
| EVAL-04 | Phase TBD | Pending |
| EVAL-05 | Phase TBD | Pending |
| EVAL-06 | Phase TBD | Pending |
| EVAL-07 | Phase TBD | Pending |
| EVAL-08 | Phase TBD | Pending |
| UI-01 | Phase TBD | Pending |
| UI-02 | Phase TBD | Pending |
| UI-03 | Phase TBD | Pending |
| UI-04 | Phase TBD | Pending |
| UI-05 | Phase TBD | Pending |
| UI-06 | Phase TBD | Pending |
| UI-07 | Phase TBD | Pending |

**Coverage:**
- v1 requirements: 45 total
- Mapped to phases: 0
- Unmapped: 45 (pending roadmap)

---
*Requirements defined: 2026-03-18*
*Last updated: 2026-03-18 after initial definition*
