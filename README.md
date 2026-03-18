# ClinIQ — Clinical Documentation Integrity Pipeline

An end-to-end clinical NLP pipeline that ingests clinical notes, extracts medical entities with negation detection, suggests ICD-10 codes via RAG (retrieval-augmented generation), runs a CDI (Clinical Documentation Integrity) agent to flag documentation gaps and missed diagnoses, and produces a full explainability audit trail. Each of the five stages is independently testable.

## Features

- **Multi-modal ingestion** — accepts plain text, FHIR bundles, and OCR'd clinical images
- **Biomedical NER** — entity extraction with `d4data/biomedical-ner-all`, plus spaCy negation detection
- **RAG-based ICD-10 coding** — FAISS retrieval → cross-encoder reranking → Qwen LLM reasoning
- **CDI analysis** — knowledge-graph-driven gap detection, co-occurrence missed diagnoses, Excludes1 conflict checks, and physician query generation
- **Explainability** — per-stage audit trail with timing, chain-of-thought traces, evidence span linkage, and retrieval logs
- **Gold standard evaluation** — 10 synthetic clinical cases with LLM-as-judge scoring

## Architecture

```
Clinical Note (text / FHIR / image)
          │
          ▼
┌─────────────────────┐
│  M1  INGESTION      │  Detect modality, normalize to ClinicalDocument
└─────────┬───────────┘
          │  raw_narrative
          ▼
┌─────────────────────┐
│  M2  NER            │  d4data biomedical-ner-all + negation (negspacy)
└─────────┬───────────┘
          │  NLUResult (entities with types, negation, qualifiers)
          ▼
┌─────────────────────┐
│  M3  RAG CODING     │  FAISS (BGE) → Cross-encoder → Qwen 2.5 reasoning
└─────────┬───────────┘
          │  CodingResult (principal dx, secondary, complications)
          ▼
┌─────────────────────┐
│  M4  CDI ANALYSIS   │  KG gap detection, co-occurrence, conflict rules
└─────────┬───────────┘
          │  CDIReport (gaps, missed dx, conflicts, completeness score)
          ▼
┌─────────────────────┐
│  M5  EXPLAINABILITY │  Audit trail, evidence spans, CoT traces
└─────────────────────┘
          │  AuditTrail (per-stage timing, retrieval logs, evidence)
          ▼
      PipelineResult
```

## Demo

The demo script runs two gold-standard clinical notes through the full 5-stage pipeline. It uses template-based physician queries (`use_llm_queries=False`) for faster execution.

```bash
# Quick mode — skips LLM coding, runs in ~10 seconds
python scripts/demo.py --quick

# Full pipeline — includes RAG coding with Qwen LLM (~20 min/scenario on CPU)
python scripts/demo.py
```

### Scenario 1: CKD + Hypertension (68M, case_004)

**Input:** A 68-year-old male with stage 3 CKD (eGFR 45) and hypertension, good BP control, compliant with medications. Denies chest pain and shortness of breath.

**Stage 2 — NER** extracts 19 entities including diagnoses (chronic kidney disease, hypertension), medications (lisinopril, amlodipine), and correctly flags negated findings (chest pain, edema):

```
  Entity Text                         Type               Neg?    Conf  Qualifiers
  ----------------------------------- ------------------ ------ -----  --------------------
  chronic kidney disease              diagnosis                  0.99  stage 3
  blood pressure control              procedure                  0.85
  amlodipine                          medication         YES     0.92
  chest                               anatomical_site    YES     1.00
  short                               diagnosis          YES     1.00
  edema                               diagnosis          YES     0.97  low
  hypertension                        diagnosis                  0.97
```

**Stage 3 — RAG Coding** (full mode) retrieves and ranks ICD-10 candidates via FAISS + cross-encoder, then Qwen selects the most specific codes:

```
  Principal Dx  : I13.0 -- Hypertensive heart and CKD with heart failure and stage 1-4 CKD
                  Confidence: 0.92
  Secondary     : 2 additional codes
  Sequencing    : Principal diagnosis: I13.0 (confidence 0.92); 2 secondary code(s)
```

**Stage 5 — Audit Trail** captures per-stage timing and evidence spans:

```
    ingestion         0.2 ms  in=str  out=text, confidence=1.00
    ner            7975.4 ms  in=681 chars  out=19 entities
    rag               0.0 ms  in=skipped  out=Coding skipped
    cdi               3.9 ms  in=0 codes  out=0 gaps, 0 conflicts, 0 missed dx
```

### Scenario 2: CHF + Atrial Fibrillation (75M, case_010)

**Input:** A 75-year-old male with CHF (LVEF 30%), chronic atrial fibrillation, compensated on diuretics and carvedilol. Mild dyspnea on exertion, trace bilateral edema.

**Stage 2 — NER** extracts 34 entities including multiple diagnoses and medications:

```
  heart failure                       diagnosis                  1.00
  atrial fibrillation                 diagnosis                  1.00  chronic
  pain                                diagnosis          YES     1.00
  furosemide                          medication         YES     1.00
  carvedilol                          medication         YES     1.00
  apixaban                            medication                 0.91
  atrial fibrillation                 diagnosis                  1.00  chronic systolic, chronic, continue
```

This scenario demonstrates:
- Multiple entity extraction (heart failure, atrial fibrillation, dyspnea, edema)
- Negation detection on physical exam findings
- ICD-10 code sequencing (principal vs. secondary) in full mode
- CDI gap/conflict/co-occurrence analysis via knowledge graph

### Full demo output

See [`docs/demo_output.txt`](docs/demo_output.txt) for complete terminal output from both scenarios.

## Quick Start

### Prerequisites

- Python 3.10+
- ~4 GB disk for model downloads (first run)

### Install

```bash
# Clone the repository
git clone <repo-url>
cd "Clinical Documentation Integrity"

# Install in editable mode
pip install -e ".[dev]"

# Download spaCy model for negation detection
python -m spacy download en_core_web_sm
```

### Run the demo

```bash
# Quick demo (~10 seconds, skips LLM coding stage)
python scripts/demo.py --quick

# Full demo (~20 min/scenario on CPU, includes Qwen LLM reasoning)
python scripts/demo.py
```

### Run tests

```bash
pytest cliniq/tests/ -v
```

## Tech Stack

| Component | Model | Size | Purpose |
|-----------|-------|------|---------|
| NER | `d4data/biomedical-ner-all` | 440M | Clinical entity extraction |
| Embedder | `BAAI/bge-small-en-v1.5` | 130M | ICD-10 code retrieval (FAISS) |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` | 80M | Candidate reranking |
| Reasoning LLM | `Qwen/Qwen2.5-1.5B-Instruct` | 3B | Code selection + physician queries |
| OCR/Vision | `HuggingFaceTB/SmolVLM-256M-Instruct` | 500M | Image-based note ingestion |
| Knowledge Graph | NetworkX DiGraph | — | CDI gap/conflict/co-occurrence rules |

## Project Structure

```
cliniq/
├── config.py                 # Model registry, paths, hyperparameters
├── model_manager.py          # Lazy model loading singleton
├── pipeline.py               # End-to-end orchestrator (run_pipeline, run_pipeline_audited)
├── modules/
│   ├── m1_ingest.py          # Multi-modal ingestion (text, FHIR, image)
│   ├── m2_nlu.py             # NER + negation detection
│   ├── m3_rag_coding.py      # FAISS retrieval → rerank → LLM reasoning
│   ├── m4_cdi.py             # CDI agent (KG queries + physician queries)
│   └── m5_explainability.py  # Audit trail builder, evidence linking
├── models/
│   ├── document.py           # ClinicalDocument, DocumentMetadata
│   ├── entities.py           # ClinicalEntity, NLUResult
│   ├── coding.py             # CodeSuggestion, CodingResult
│   ├── cdi.py                # CDIReport, DocumentationGap, MissedDiagnosis
│   ├── audit.py              # AuditTrail, StageTrace, RetrievalLog
│   └── evaluation.py         # GoldStandardCase, EvalResult
├── rag/
│   ├── retriever.py          # FAISSRetriever (BGE embeddings)
│   ├── reranker.py           # CrossEncoderReranker
│   ├── build_index.py        # FAISS index builder
│   └── icd10_loader.py       # ICD-10 code catalog loader
├── knowledge_graph/
│   ├── schema.py             # KG node/edge types
│   ├── builder.py            # Build CDI knowledge graph
│   └── querier.py            # Gap, conflict, co-occurrence queries
├── evaluation/
│   └── llm_judge.py          # LLM-as-judge evaluation
├── data/
│   ├── icd10/                # ICD-10 code catalog
│   └── gold_standard/        # 10 synthetic test cases (text + FHIR + images)
├── tests/                    # pytest test suite
scripts/
├── demo.py                   # Demo script (2 scenarios)
├── generate_test_data.py     # Gold standard data generator
└── generate_test_images.py   # Test image generator
```

## Pipeline Stages

### M1 — Ingestion
Detects input modality (plain text, FHIR bundle, or clinical image), extracts the narrative, and normalizes into a `ClinicalDocument` with metadata and confidence score. FHIR parsing uses `fhir.resources`; image OCR uses SmolVLM.

### M2 — NER
Runs `d4data/biomedical-ner-all` (token classification) to extract clinical entities, maps raw labels to semantic categories (diagnosis, procedure, medication, anatomical site, lab value), and applies `negspacy` for negation detection (e.g., "denies chest pain" → negated).

### M3 — RAG Coding
For each non-negated diagnosis/procedure entity: (1) FAISS retrieves top-20 ICD-10 candidates using BGE embeddings, (2) cross-encoder reranks to top-5, (3) Qwen 2.5 selects the best code with structured JSON reasoning. Codes are sequenced into principal/secondary/complications.

### M4 — CDI Analysis
Builds a NetworkX knowledge graph with ICD-10 hierarchy, co-occurrence weights, Excludes1 conflict rules, and required qualifiers. Queries the KG to find: documentation gaps (missing qualifiers like laterality or acuity), code conflicts (mutually exclusive codes), and missed diagnoses (commonly co-coded conditions not documented). Generates physician queries for each gap.

### M5 — Explainability
Wraps each pipeline stage with timing and trace capture. Links ICD-10 codes to supporting text spans in the clinical note. Captures chain-of-thought traces from LLM responses. Produces a complete `AuditTrail` with per-stage `StageTrace` objects and `RetrievalLog` entries.

## Running Tests

```bash
# All tests
pytest cliniq/tests/ -v

# Individual modules
pytest cliniq/tests/test_m1_ingest.py -v
pytest cliniq/tests/test_m2_nlu.py -v
pytest cliniq/tests/test_m3_coding.py -v
pytest cliniq/tests/test_m4_cdi.py -v
pytest cliniq/tests/test_m5_explainability.py -v
pytest cliniq/tests/test_pipeline.py -v

# With coverage
pytest cliniq/tests/ --cov=cliniq --cov-report=term-missing
```
