# ClinIQ — Agentic Clinical Coding & CDI Intelligence Platform
## GSD Project Specification v1.0
**Owner:** Praveen | **Status:** Production-Ready Platform
**Target:** Fully local, OSS-only clinical documentation intelligence

---

## 0. ONE-LINE MISSION

> A fully local, multi-modal, agentic pipeline that ingests clinical data (text + images), extracts medical entities via NLU, retrieves ICD-10 codes via RAG, detects documentation gaps via a knowledge graph CDI agent, evaluates every step with AI-grade metrics, and visualises the entire reasoning chain in a polished Streamlit demo — using only small, specialised OSS HuggingFace models.

---

## 1. PROBLEM STATEMENT

Healthcare revenue cycle teams face three compounding problems:
1. **Incomplete documentation** — physicians write ambiguous notes; CDI teams manually query them
2. **Coding errors** — human coders misassign or under-specify ICD-10/CPT codes, causing claim denials
3. **No explainability** — black-box CAC systems cannot justify their suggestions, creating compliance risk

ClinIQ solves all three in a single agentic pipeline, running entirely on local OSS models.

---

## 2. GOALS

| # | Goal | Success Signal |
|---|------|---------------|
| G1 | Ingest FHIR R4 resources AND image inputs (scanned notes, lab reports) | Both modalities produce structured clinical facts |
| G2 | Extract clinical entities (diagnoses, procedures, qualifiers) with NLU | F1 ≥ 0.80 on held-out synthetic cases |
| G3 | Suggest ICD-10-CM + CPT codes via RAG | Top-3 accuracy ≥ 0.85, MRR ≥ 0.75 |
| G4 | Detect documentation gaps and generate physician queries via KG CDI agent | Query relevance score ≥ 0.80 |
| G5 | Evaluate each module with automated AI-grade metrics | Every module has a scored eval report |
| G6 | Visualise knowledge graph interactively | PyVis graph loads in browser, nodes clickable |
| G7 | Run entirely on local OSS models, downloaded + cached on first run | No API keys required for core pipeline |
| G8 | Streamlit demo answers questions about any pipeline step | QA bot responds correctly to ≥ 5 standard clinical questions |

## 3. NON-GOALS

- Not a production system — no real PHI, no HIPAA infrastructure
- Not fine-tuning models during the demo (inference only)
- Not connecting to a live EHR or real FHIR server
- Not supporting inpatient DRG coding (outpatient + professional fee only for MVP)

---

## 4. ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLINIQ PIPELINE                          │
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │ MODULE 1 │───▶│ MODULE 2 │───▶│ MODULE 3 │───▶│ MODULE 4 │  │
│  │  INGEST  │    │   NLU    │    │ RAG CODE │    │  CDI KG  │  │
│  │FHIR+IMG  │    │EXTRACTION│    │  SUGGEST │    │  AGENT   │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│       │               │               │               │         │
│       ▼               ▼               ▼               ▼         │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │  EVAL 1  │    │  EVAL 2  │    │  EVAL 3  │    │  EVAL 4  │  │
│  │ Schema   │    │ F1/NER   │    │ MRR/Top-k│    │ Query    │  │
│  │Validation│    │  Score   │    │ Accuracy │    │Relevance │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              MODULE 5 — EXPLAINABILITY LAYER             │   │
│  │         Chain-of-thought trace + Audit report            │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │      MODULE 6 — KG VISUALISATION (PyVis in browser)      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │         MODULE 7 — STREAMLIT DEMO UI + QA BOT            │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. OSS MODEL REGISTRY

All models are downloaded via `huggingface_hub` on first run and cached to `~/.cache/cliniq/models/`.

| Alias | HuggingFace Model ID | Size | Purpose |
|-------|---------------------|------|---------|
| `CLINICAL_NER` | `d4data/biomedical-ner-all` | 110M | Clinical entity extraction (diagnoses, procedures, drugs) |
| `REASONING_LLM` | `Qwen/Qwen2.5-1.5B-Instruct` | 1.5B | CDI reasoning, query generation, chain-of-thought |
| `EMBEDDER` | `BAAI/bge-small-en-v1.5` | 33M | RAG embeddings for ICD-10 vector store |
| `MULTIMODAL` | `HuggingFaceTB/SmolVLM-Instruct` | 256M | Image → clinical text extraction (scanned notes, lab images) |
| `QA_MODEL` | `Qwen/Qwen2.5-1.5B-Instruct` | shared | Demo QA bot (same model, different system prompt) |
| `RERANKER` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | 22M | RAG reranking of retrieved ICD-10 candidates |

**Total download size: ~2.1GB. All MIT/Apache-2.0 licensed.**

---

## 6. MODULE SPECIFICATIONS

---

### MODULE 1 — Multi-modal Ingestion

**Input types:**
- FHIR R4 JSON (`DocumentReference`, `Encounter`, `Condition`, `Procedure`)
- Plain text clinical note (`.txt`)
- Scanned document image (`.png`, `.jpg`, `.pdf` page)
- Lab report image

**Processing logic:**
```
if input is image/pdf:
    → SmolVLM-Instruct: "Extract all clinical information from this document as structured text"
    → output: normalized clinical narrative string

if input is FHIR JSON:
    → fhir.resources parser → extract narrative from DocumentReference.content
    → extract structured facts from Condition/Procedure resources
    → merge into unified ClinicalDocument object

if input is plain text:
    → pass through directly as ClinicalDocument
```

**Output schema (Pydantic):**
```python
class ClinicalDocument(BaseModel):
    patient_id: str
    encounter_id: str
    source_type: Literal["fhir", "image", "text"]
    raw_narrative: str
    structured_facts: list[dict]  # from FHIR resources if available
    modality_confidence: float    # 1.0 for text, OCR confidence for images
    extraction_trace: str         # what the multimodal model said
```

**Evaluation (EVAL-1):**
| Metric | Method | Target |
|--------|--------|--------|
| Schema validation pass rate | Pydantic validation on 20 synthetic cases | 100% |
| FHIR parse accuracy | Compare extracted facts vs ground truth resource fields | ≥ 95% |
| OCR entity recall | Compare SmolVLM output vs known entities in test images | ≥ 0.80 |
| Modality routing accuracy | Correct type detected for each of 20 test inputs | 100% |

**Synthetic test data:** Generated via [Synthea](https://github.com/synthetichealth/synthea) (FHIR) + 5 hand-crafted scanned note images using PIL.

---

### MODULE 2 — Clinical NLU Entity Extraction

**Model:** `d4data/biomedical-ner-all` (fine-tuned on BC5CDR, NCBI Disease, JNLPBA)

**Input:** `ClinicalDocument.raw_narrative`

**Processing logic:**
```
1. Tokenize narrative → NER model → raw entity spans
2. Post-process: merge subword tokens, resolve overlapping spans
3. Classify entities into schema types:
   - DIAGNOSIS (map to ICD-10 chapter hint)
   - PROCEDURE (map to CPT category hint)
   - MEDICATION
   - SEVERITY_QUALIFIER (e.g. "stage 3", "acute", "chronic")
   - ANATOMICAL_SITE
   - NEGATION (e.g. "no signs of infection")
4. Confidence score per entity from model logits
```

**Output schema:**
```python
class ClinicalEntity(BaseModel):
    text: str
    entity_type: str
    start_char: int
    end_char: int
    confidence: float
    negated: bool
    qualifiers: list[str]

class NLUResult(BaseModel):
    entities: list[ClinicalEntity]
    diagnoses: list[ClinicalEntity]      # filtered view
    procedures: list[ClinicalEntity]     # filtered view
    entity_count: int
    processing_time_ms: float
```

**Evaluation (EVAL-2):**
| Metric | Method | Target |
|--------|--------|--------|
| Precision | TP / (TP + FP) vs gold labels | ≥ 0.82 |
| Recall | TP / (TP + FN) vs gold labels | ≥ 0.80 |
| F1 Score | Harmonic mean of P/R | ≥ 0.81 |
| Negation accuracy | Correctly identified negated entities | ≥ 0.85 |
| Qualifier capture rate | Severity/type qualifiers found / total present | ≥ 0.75 |

**Gold standard:** 15 manually annotated synthetic notes with entity labels. Evaluated using `seqeval`.

---

### MODULE 3 — RAG-based ICD-10 Coding Agent

**Architecture:** Classic RAG with reranking

```
Query Construction
    → Entity text + qualifiers + context window
    
Retrieval (FAISS vector store)
    → BAAI/bge-small-en-v1.5 embeds query
    → Top-20 ICD-10 code descriptions retrieved
    
Reranking
    → cross-encoder/ms-marco-MiniLM-L-6-v2 scores each candidate
    → Top-5 reranked codes returned
    
Reasoning
    → Qwen2.5-1.5B-Instruct: "Given the clinical context and these candidate codes,
      select the most specific appropriate code and explain why"
    → Structured output: selected code + rationale + alternatives
    
Code Sequencing
    → Rule-based: principal diagnosis → comorbidities → complications
    → Flag codes needing higher specificity
```

**Knowledge base construction (one-time, run at startup):**
- Source: CMS ICD-10-CM FY2025 tabular data (public domain)
- Index: FAISS flat index over `bge-small` embeddings of all ~70,000 code descriptions
- Stored at: `~/.cache/cliniq/icd10_index/`

**Output schema:**
```python
class CodeSuggestion(BaseModel):
    icd10_code: str          # e.g. "N18.3"
    description: str         # e.g. "Chronic kidney disease, stage 3"
    confidence: float
    evidence_text: str       # clinical note excerpt that supports this code
    reasoning: str           # LLM chain-of-thought
    needs_specificity: bool  # flag for CDI agent
    alternatives: list[dict] # top-2 alternatives with scores

class CodingResult(BaseModel):
    principal_diagnosis_code: CodeSuggestion
    secondary_codes: list[CodeSuggestion]
    procedure_codes: list[CodeSuggestion]
    sequencing_rationale: str
    retrieval_stats: dict    # for eval: num retrieved, reranker scores
```

**Evaluation (EVAL-3):**
| Metric | Method | Target |
|--------|--------|--------|
| Top-1 Accuracy | Exact code match vs ground truth | ≥ 0.70 |
| Top-3 Accuracy | GT code in top-3 suggestions | ≥ 0.85 |
| MRR (Mean Reciprocal Rank) | 1/rank of correct code averaged | ≥ 0.75 |
| Specificity flag recall | Correctly flags under-specified codes | ≥ 0.80 |
| Retrieval recall@20 | GT code description in top-20 FAISS results | ≥ 0.92 |
| Reranker lift | Improvement in MRR vs pre-rerank | > 0.05 |

**Ground truth:** 20 synthetic cases with expert-assigned ICD-10 codes.

---

### MODULE 4 — CDI Knowledge Graph Agent

**This module is the most novel — it combines symbolic KG reasoning with LLM generation.**

**Knowledge graph construction:**
```
Nodes:
  - ICD10Code (code, description, chapter, requires_qualifier: bool)
  - ClinicalConcept (name, synonyms)
  - Qualifier (type: stage/severity/type/laterality, values: list)
  - DocumentationRequirement (what must be present for code specificity)

Edges:
  - MAPS_TO (ClinicalConcept → ICD10Code)
  - REQUIRES (ICD10Code → Qualifier)
  - PARENT_OF (ICD10Code → ICD10Code, ICD-10 hierarchy)
  - CONFLICTS_WITH (ICD10Code → ICD10Code)
  - COMMONLY_CO_CODED (ICD10Code → ICD10Code, from freq data)
```

**Graph source:** ICD-10 hierarchy from CMS tabular data + manually authored qualification rules for top-50 common DRGs.

**CDI Agent logic:**
```
For each CodeSuggestion where needs_specificity=True:
    1. Query KG: what qualifiers does this code require?
    2. Check NLUResult: are those qualifiers present in extracted entities?
    3. If missing → generate physician query via Qwen2.5-1.5B-Instruct
    4. Check KG for COMMONLY_CO_CODED → suggest potential missed diagnoses
    5. Check CONFLICTS_WITH → flag invalid code combinations

Output: CDIReport with queries, missed diagnoses, conflict alerts
```

**Output schema:**
```python
class PhysicianQuery(BaseModel):
    target_code: str
    missing_qualifier_type: str
    query_text: str          # natural language query to physician
    query_options: list[str] # multiple choice options if applicable
    clinical_impact: str     # why this matters for reimbursement

class CDIReport(BaseModel):
    queries: list[PhysicianQuery]
    missed_diagnoses: list[str]   # KG-suggested co-coded diagnoses
    code_conflicts: list[dict]
    documentation_completeness_score: float  # 0-1
    kg_reasoning_trace: list[str]
```

**Evaluation (EVAL-4):**
| Metric | Method | Target |
|--------|--------|--------|
| Query relevance score | LLM-as-judge: is query addressing correct gap? | ≥ 0.80 |
| Query actionability | Human eval on 10 cases: is query answerable? | ≥ 0.85 |
| Missed diagnosis recall | KG suggestions vs known co-coded diagnoses | ≥ 0.70 |
| Conflict detection accuracy | Known invalid combinations flagged | ≥ 0.90 |
| Completeness score correlation | Pearson r vs expert completeness rating | ≥ 0.75 |

---

### MODULE 5 — Explainability & Audit Layer

**Purpose:** Produce a per-case audit trail that a compliance officer or auditor can interrogate.

**What it generates:**
```python
class AuditTrail(BaseModel):
    case_id: str
    pipeline_version: str
    timestamp: str
    
    # Per-module traces
    ingestion_trace: str       # how document was parsed
    ner_evidence: dict         # entity → supporting text span
    rag_retrieval_log: dict    # query → top-k → reranked → selected
    kg_traversal_log: list     # graph path taken for each CDI finding
    llm_cot_traces: list       # raw chain-of-thought from Qwen
    
    # Summary
    confidence_breakdown: dict # per-code confidence with evidence
    regulatory_flags: list     # HIPAA-relevant decisions made
    human_review_required: bool
    estimated_reimbursement_delta: str  # narrative, not exact $
```

**Evaluation (EVAL-5):**
| Metric | Method | Target |
|--------|--------|--------|
| Trace completeness | All pipeline steps represented in audit | 100% |
| Evidence attribution | Every code has ≥1 supporting text span | 100% |
| CoT coherence score | LLM-as-judge: is reasoning logically sound? | ≥ 0.82 |

---

### MODULE 6 — Knowledge Graph Visualisation

**Library:** PyVis (interactive HTML) + NetworkX (graph ops)

**What's shown:**
- Full ICD-10 concept graph for the current patient case
- Colour coding: green=well-documented, amber=needs CDI query, red=conflict
- Node click → shows: code description, evidence text, CDI query if applicable
- Edge labels: relationship type (REQUIRES, MAPS_TO, CONFLICTS_WITH)
- Subgraph: only nodes relevant to the current case (not all 70k codes)

**Export:** Saves interactive `knowledge_graph.html` to `outputs/` — can be opened standalone.

---

### MODULE 7 — Streamlit Demo UI + QA Bot

**Pages:**
1. **Pipeline Runner** — upload FHIR JSON or image, run full pipeline, see results per module
2. **Evaluation Dashboard** — run eval suite, show metrics table + charts per module
3. **Knowledge Graph Viewer** — embedded PyVis graph with case-specific subgraph
4. **Audit Trail** — expandable trace for every pipeline decision
5. **Clinical QA Bot** — type any question about the system, Qwen answers using RAG over the codebase docs

**QA Bot pre-loaded Q&A seeds (for demo reliability):**
- "How does the RAG pipeline work?"
- "What model is used for entity extraction?"
- "How does the CDI agent detect documentation gaps?"
- "How would you handle HIPAA compliance in production?"
- "How does the knowledge graph improve over pure LLM coding?"
- "What is the difference between CAC and autonomous coding?"
- "How would you scale this to inpatient DRG coding?"

---

## 7. REPOSITORY STRUCTURE

```
cliniq/
│
├── README.md                    # Quick start + architecture diagram
├── requirements.txt             # All dependencies pinned
├── setup.py                     # Package definition
│
├── cliniq/
│   ├── __init__.py
│   ├── config.py                # Model registry, paths, constants
│   ├── model_manager.py         # HuggingFace download + cache manager
│   │
│   ├── modules/
│   │   ├── m1_ingest.py         # FHIR + image ingestion
│   │   ├── m2_nlu.py            # Clinical NER
│   │   ├── m3_rag_coding.py     # RAG + reranking + code suggestion
│   │   ├── m4_cdi_agent.py      # KG CDI agent
│   │   ├── m5_explainability.py # Audit trail builder
│   │   └── m6_kg_viz.py         # PyVis knowledge graph
│   │
│   ├── knowledge_graph/
│   │   ├── build_icd10_graph.py # One-time KG construction
│   │   ├── graph_queries.py     # NetworkX query helpers
│   │   └── qualification_rules.py  # Handcrafted CDI rules
│   │
│   ├── rag/
│   │   ├── build_index.py       # One-time FAISS index builder
│   │   ├── retriever.py         # FAISS search
│   │   └── reranker.py          # Cross-encoder reranking
│   │
│   ├── evaluation/
│   │   ├── eval_runner.py       # Runs all 5 eval suites
│   │   ├── eval_m1_ingest.py
│   │   ├── eval_m2_nlu.py
│   │   ├── eval_m3_coding.py
│   │   ├── eval_m4_cdi.py
│   │   ├── eval_m5_explainability.py
│   │   └── gold_standard/       # Hand-labelled test cases (JSON)
│   │       ├── cases_fhir/      # 10 FHIR synthetic cases
│   │       ├── cases_images/    # 5 synthetic scanned note images
│   │       └── ground_truth.json
│   │
│   └── pipeline.py              # End-to-end orchestrator
│
├── ui/
│   ├── app.py                   # Streamlit entry point
│   ├── pages/
│   │   ├── 1_pipeline.py
│   │   ├── 2_evaluation.py
│   │   ├── 3_knowledge_graph.py
│   │   ├── 4_audit_trail.py
│   │   └── 5_qa_bot.py
│   └── components/
│       ├── metric_cards.py
│       ├── code_display.py
│       └── graph_embed.py
│
├── data/
│   ├── icd10/                   # CMS ICD-10-CM FY2025 tabular files
│   ├── synthea_samples/         # Pre-generated FHIR bundles
│   └── sample_images/           # PIL-generated test note images
│
├── outputs/                     # Generated: eval reports, KG HTML, audit trails
│
└── scripts/
    ├── bootstrap.py             # First-run: download models + build indexes
    ├── generate_test_images.py  # Creates synthetic scanned note PNGs
    └── demo.py                  # CLI end-to-end demo runner
```

---

## 8. TECHNOLOGY STACK

| Layer | Technology | Version | Rationale |
|-------|-----------|---------|-----------|
| Core ML | `transformers` | ≥4.45 | HuggingFace model loading |
| LLM Inference | `transformers` pipeline + `torch` | latest | Local inference, no API |
| Model Download | `huggingface_hub` | ≥0.25 | Cached downloads |
| Vector Store | `faiss-cpu` | ≥1.8 | Fast ICD-10 retrieval |
| Embeddings | `sentence-transformers` | ≥3.0 | BAAI/bge-small wrapper |
| Knowledge Graph | `networkx` | ≥3.3 | Graph construction + queries |
| KG Visualisation | `pyvis` | ≥0.3 | Interactive HTML graph |
| FHIR Parsing | `fhir.resources` | ≥7.0 | FHIR R4 Python models |
| Multi-modal | `transformers` (SmolVLM) | ≥4.45 | Image → text |
| NER Evaluation | `seqeval` | ≥1.2 | Standard NER metrics |
| UI | `streamlit` | ≥1.38 | Demo interface |
| Data Validation | `pydantic` | v2 | Schema enforcement |
| Synthetic Data | `synthea` (external) / `faker` | — | Test case generation |
| PDF Handling | `pymupdf` | ≥1.24 | PDF page → image for multimodal |
| Charts | `plotly` | ≥5.20 | Eval metric charts in Streamlit |
| Reranker | `sentence-transformers` | ≥3.0 | Cross-encoder reranking |

---

## 9. FIRST-RUN BOOTSTRAP SEQUENCE

```python
# scripts/bootstrap.py — run once before demo

def bootstrap():
    # 1. Download all models → ~/.cache/cliniq/models/
    download_model("d4data/biomedical-ner-all")
    download_model("Qwen/Qwen2.5-1.5B-Instruct")
    download_model("BAAI/bge-small-en-v1.5")
    download_model("HuggingFaceTB/SmolVLM-Instruct")
    download_model("cross-encoder/ms-marco-MiniLM-L-6-v2")

    # 2. Download ICD-10 CM FY2025 tabular data from CMS (public domain)
    download_icd10_tabular()

    # 3. Build FAISS index over ICD-10 descriptions
    build_icd10_faiss_index()          # → ~/.cache/cliniq/icd10_index/

    # 4. Build ICD-10 knowledge graph
    build_icd10_networkx_graph()       # → ~/.cache/cliniq/icd10_graph.pkl

    # 5. Validate all modules load correctly
    run_smoke_tests()

    print("✅ ClinIQ bootstrap complete. Run: streamlit run ui/app.py")
```

**Estimated bootstrap time:** 8–15 min on first run (model downloads), <30 seconds on subsequent runs.

---

## 10. EVALUATION FRAMEWORK DESIGN

### Automated Eval Runner

```python
# evaluation/eval_runner.py

class EvalRunner:
    def run_all(self) -> EvalReport:
        results = {}
        results["m1_ingest"]  = EvalM1Ingest().run()
        results["m2_nlu"]     = EvalM2NLU().run()
        results["m3_coding"]  = EvalM3Coding().run()
        results["m4_cdi"]     = EvalM4CDI().run()
        results["m5_explain"] = EvalM5Explainability().run()
        return EvalReport(results=results, timestamp=now())
```

### LLM-as-Judge Pattern (used for M4 + M5)

Where ground truth is subjective (query quality, CoT coherence), we use the `Qwen2.5-1.5B-Instruct` model itself as evaluator with a calibrated rubric prompt:

```python
JUDGE_PROMPT = """
You are a clinical documentation expert evaluating an AI system's output.

[ORIGINAL CLINICAL NOTE]
{note}

[CDI QUERY GENERATED]
{query}

[EVALUATION RUBRIC]
Score 1-5 on each dimension:
- Relevance: Does the query address a real documentation gap?
- Specificity: Is the query specific enough to be actionable?
- Clinical accuracy: Is the medical reasoning correct?
- Clarity: Would a physician understand this without training?

Return JSON only: {"relevance": N, "specificity": N, "clinical_accuracy": N, "clarity": N, "overall": N}
"""
```

### Eval Output Format

Each module eval produces:
```json
{
  "module": "m3_coding",
  "timestamp": "2025-03-18T10:00:00",
  "n_cases": 20,
  "metrics": {
    "top1_accuracy": 0.72,
    "top3_accuracy": 0.87,
    "mrr": 0.78,
    "specificity_flag_recall": 0.83,
    "retrieval_recall_at_20": 0.94,
    "reranker_lift": 0.08
  },
  "per_case_results": [...],
  "failures": [...],
  "pass": true
}
```

---

## 11. USAGE GUIDE

**Step 1 — Launch**
```bash
streamlit run ui/app.py
```

**Step 2 — Upload a case**
- Drop in a synthetic FHIR JSON or a PIL-generated "scanned note" image
- Show both modalities work (text path vs image path through SmolVLM)

**Step 3 — Run pipeline**
- Watch each module execute with a progress bar
- Show the NER highlighting on the clinical note
- Show top-5 ICD-10 suggestions with RAG retrieval stats

**Step 4 — CDI findings**
- Show the knowledge graph with flagged nodes
- Click a node to see the physician query generated
- Show the missing qualifier detection

**Step 5 — Evaluation**
- Switch to Eval Dashboard
- Run eval suite live (or show pre-computed results)
- Show metrics table + Plotly radar chart

**Step 6 — QA Bot**
- Answer: "How would you make this HIPAA compliant in production?"
- Answer: "What's the difference between this and commercial CAC platforms?"
- Answer: "How would your split learning background help here?"

---

## 12. KEY TECHNICAL CAPABILITIES

| Capability Area | ClinIQ Demonstrates |
|----------------|---------------------|
| Agentic AI design | CDI Agent with KG tool use + multi-step reasoning |
| NLU for clinical text | Module 2 with biomedical NER + qualifier extraction |
| LLM fine-tuning awareness | Discuss how Qwen could be fine-tuned on ICD-10 coding pairs |
| FHIR / HL7 pipelines | Module 1 FHIR R4 ingestion with `fhir.resources` |
| RAG systems | Module 3 with FAISS + cross-encoder reranking |
| Multi-modal AI | Module 1 SmolVLM for scanned notes + lab images |
| Knowledge graph + symbolic reasoning | Module 4 ICD-10 KG with NetworkX |
| Explainability | Module 5 full audit trail with evidence attribution |
| Model evaluation frameworks | Module eval suite with automated + LLM-as-judge scoring |
| AWS / cloud | Architecture supports cloud deployment on AWS; same design applies |
| HIPAA / HITRUST | Discuss: local inference = no PHI leaves device; differential privacy angle from PhD |
| Research to production | Each module has a production-readiness note in README |

---

## 13. TASK BREAKDOWN (BUILD ORDER)

```
Week 1 — Foundation
  [x] T01: Repo scaffold + requirements.txt
  [x] T02: model_manager.py — download + cache all 5 models
  [x] T03: Build ICD-10 FAISS index (build_index.py)
  [x] T04: Build ICD-10 NetworkX graph (build_icd10_graph.py)
  [x] T05: Generate synthetic test cases + gold_standard.json

Week 2 — Core Modules
  [ ] T06: Module 1 — FHIR ingestion
  [ ] T07: Module 1 — SmolVLM image ingestion
  [ ] T08: Module 2 — Clinical NER pipeline
  [ ] T09: Module 3 — RAG retriever + reranker
  [ ] T10: Module 3 — Qwen reasoning layer + structured output

Week 3 — Intelligence Layer
  [ ] T11: Module 4 — KG CDI agent (graph queries + gap detection)
  [ ] T12: Module 4 — Physician query generation (Qwen)
  [ ] T13: Module 5 — Audit trail builder
  [ ] T14: Module 6 — PyVis KG visualisation

Week 4 — Eval + UI
  [ ] T15: All 5 eval modules
  [ ] T16: Streamlit UI — all 5 pages
  [ ] T17: QA Bot with RAG over project docs
  [ ] T18: End-to-end integration test
  [ ] T19: Demo script rehearsal + README polish
```

---

## 14. STRETCH GOALS (if time permits)

- **Federated inference simulation** — Run NER on "hospital A" and coding on "hospital B" using split model inference (direct callback to PhD work)
- **Edge Veda integration note** — Add a README section explaining how the NER module could run on-device using Edge Veda for HIPAA-sensitive mobile CDI
- **Confidence calibration plot** — Show that model confidence scores are well-calibrated (reliability diagram)
- **SNOMED CT layer** — Add a second KG layer with SNOMED concepts linked to ICD-10 nodes

---

*End of ClinIQ GSD Spec v1.0*
