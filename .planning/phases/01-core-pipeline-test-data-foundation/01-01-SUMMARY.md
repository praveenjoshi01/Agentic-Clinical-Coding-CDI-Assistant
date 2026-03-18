---
phase: 01-core-pipeline-test-data-foundation
plan: 01
subsystem: foundation
tags: [schemas, config, model-manager, pydantic]
dependency_graph:
  requires: []
  provides:
    - cliniq.models (7 Pydantic schemas)
    - cliniq.config (MODEL_REGISTRY, paths, thresholds)
    - cliniq.model_manager (ModelManager singleton)
  affects:
    - All downstream modules depend on these data contracts
tech_stack:
  added:
    - Pydantic v2 for data validation
    - transformers for NER pipeline
    - sentence-transformers for embeddings and reranking
    - faiss-cpu for vector search
    - fhir.resources for FHIR parsing
    - Pillow for image processing
    - negspacy for negation detection
    - outlines for structured generation
  patterns:
    - Singleton pattern for model caching
    - Lazy loading for memory efficiency
    - Computed properties for derived entity filters
key_files:
  created:
    - pyproject.toml
    - cliniq/__init__.py
    - cliniq/config.py
    - cliniq/model_manager.py
    - cliniq/models/__init__.py
    - cliniq/models/document.py
    - cliniq/models/entities.py
    - cliniq/models/coding.py
    - cliniq/models/evaluation.py
    - cliniq/tests/test_models.py
    - .gitignore
  modified: []
decisions:
  - decision: Use Pydantic v2 for all data schemas
    rationale: Provides runtime validation, computed properties, and JSON serialization
  - decision: Singleton pattern for ModelManager
    rationale: Prevents multiple model loads, reduces memory footprint
  - decision: Lazy loading for all models
    rationale: Models only downloaded/loaded when first accessed, not at import time
  - decision: ENTITY_TYPE_MAP as module-level constant
    rationale: Centralized mapping from d4data labels to pipeline categories
metrics:
  duration_minutes: 3
  tasks_completed: 3
  tests_added: 10
  files_created: 15
  commits: 3
  completed_date: "2026-03-18"
---

# Phase 01 Plan 01: Project Structure and Data Schemas Summary

**One-liner:** Installable Python package with 7 Pydantic v2 schemas, singleton model manager with lazy loading, and 14 declared dependencies for the clinical NLU pipeline.

## Objective Achieved

Set up the foundational project structure with all Pydantic data schemas, configuration, and model manager. Every downstream module now has access to shared data contracts (ClinicalDocument, ClinicalEntity, NLUResult, CodingResult) and the lazy-loading model infrastructure.

## Tasks Completed

| Task | Name                                           | Commit  | Files Modified                                                                                     |
| ---- | ---------------------------------------------- | ------- | -------------------------------------------------------------------------------------------------- |
| 1    | Project scaffold and dependency configuration  | 0a6e873 | pyproject.toml, cliniq/__init__.py, cliniq/modules/, cliniq/rag/, cliniq/tests/, cliniq/data/, .gitignore |
| 2    | Pydantic data models for all pipeline schemas  | c43309a | cliniq/models/__init__.py, document.py, entities.py, coding.py, evaluation.py                      |
| 3    | Config, model manager, and schema validation tests | a245d85 | cliniq/config.py, cliniq/model_manager.py, cliniq/tests/test_models.py                            |

## What Was Built

### 1. Project Structure
- **pyproject.toml:** Package definition with 14 core dependencies (torch, transformers, sentence-transformers, faiss-cpu, pydantic, fhir.resources, etc.)
- **Package hierarchy:** cliniq/ with subpackages for modules/, rag/, tests/, data/
- **.gitignore:** Python defaults plus project-specific exclusions (*.faiss, *.pkl, data/icd10/*.txt)

### 2. Pydantic Data Schemas (7 models across 4 files)

**cliniq/models/document.py:**
- `DocumentMetadata`: patient_id, encounter_id, source_type, timestamp
- `ClinicalDocument`: Unified document representation with metadata, raw_narrative, structured_facts, modality_confidence, extraction_trace

**cliniq/models/entities.py:**
- `ENTITY_TYPE_MAP`: Maps d4data biomedical-ner-all labels to pipeline categories (Disease_disorder -> diagnosis, Medication -> medication, etc.)
- `ClinicalEntity`: Single entity with text, entity_type, span, confidence, negation, qualifiers
- `NLUResult`: Entity list with computed properties (.diagnoses, .procedures, .medications, .anatomical_sites, .entity_count)

**cliniq/models/coding.py:**
- `CodeSuggestion`: ICD-10 code with confidence, evidence_text, reasoning, needs_specificity flag, alternatives
- `CodingResult`: Principal diagnosis + secondary/complication codes + sequencing_rationale + retrieval_stats

**cliniq/models/evaluation.py:**
- `GoldStandardEntity`: Expected entity for test cases
- `GoldStandardCase`: Complete test case with input, expected entities/codes, negation tests, CDI annotations
- `EvalResult`: Module test results with metrics, per-case results, failures

### 3. Configuration and Model Management

**cliniq/config.py:**
- `MODEL_REGISTRY`: Maps aliases (CLINICAL_NER, REASONING_LLM, EMBEDDER, MULTIMODAL, RERANKER) to HuggingFace model IDs
- Path constants: DATA_DIR, ICD10_DIR, GOLD_STANDARD_DIR, CACHE_DIR, INDEX_DIR
- Hyperparameters: CONFIDENCE_THRESHOLD (0.80), RETRIEVAL_TOP_K (20), RERANK_TOP_K (5), BGE_QUERY_PREFIX

**cliniq/model_manager.py:**
- Singleton `ModelManager` class with lazy-loading methods:
  - `get_ner_pipeline()`: d4data biomedical NER with aggregation_strategy="simple"
  - `get_embedder()`: BAAI/bge-small-en-v1.5 sentence transformer
  - `get_cross_encoder()`: cross-encoder/ms-marco-MiniLM-L-6-v2 reranker
  - `get_reasoning_llm()`: Qwen2.5-1.5B-Instruct (model, tokenizer) tuple
  - `get_multimodal()`: SmolVLM-256M-Instruct (model, processor) tuple
- Models only loaded on first access, cached for reuse
- `clear()` method to release all cached models

### 4. Test Suite

**cliniq/tests/test_models.py:** 10 tests validating:
- DocumentMetadata and ClinicalDocument creation
- Invalid confidence rejection (> 1.0)
- ClinicalEntity creation with all fields
- NLUResult computed properties filtering entities by type
- CodeSuggestion and CodingResult creation
- GoldStandardCase creation
- EvalResult creation
- ENTITY_TYPE_MAP mapping from d4data labels to pipeline categories

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

1. Package imports successfully: `python -c "import cliniq; print(cliniq.__version__)"` → "0.1.0"
2. All models import: `from cliniq.models import *` → Success
3. Config and ModelManager import without downloading models → Success
4. All 10 tests pass: `pytest cliniq/tests/test_models.py -v` → 10 passed in 0.04s

## Success Criteria Met

- [x] Installable package with all 14 dependencies declared
- [x] 7 Pydantic model classes across 4 schema files, all importable
- [x] ENTITY_TYPE_MAP correctly maps all d4data label categories
- [x] NLUResult computed properties filter entities by type
- [x] Config exports MODEL_REGISTRY, paths, and thresholds
- [x] ModelManager singleton with 5 lazy-loading methods
- [x] 10 passing schema validation tests

## Impact on Downstream Work

**Enables:**
- Phase 01 Plan 02 (ICD-10 data pipeline): Can use DATA_DIR and ICD10_DIR from config
- Phase 01 Plan 03 (NER module): Can use ClinicalEntity and NLUResult schemas
- Phase 01 Plan 04 (RAG module): Can use ModelManager.get_embedder() and CodeSuggestion schema
- All evaluation modules: Can use GoldStandardCase and EvalResult schemas

**Provides:**
- Single source of truth for inter-module data contracts
- Centralized model loading infrastructure
- Type-safe data validation throughout pipeline

## Next Steps

1. Implement ICD-10 data pipeline (01-02) to download and process ICD-10-CM codes
2. Build NER module (01-03) using d4data/biomedical-ner-all and ClinicalEntity schema
3. Implement RAG module (01-04) using BGE embeddings and FAISS index

## Self-Check: PASSED

**Files created:**
- FOUND: pyproject.toml
- FOUND: cliniq/__init__.py
- FOUND: cliniq/config.py
- FOUND: cliniq/model_manager.py
- FOUND: cliniq/models/__init__.py
- FOUND: cliniq/models/document.py
- FOUND: cliniq/models/entities.py
- FOUND: cliniq/models/coding.py
- FOUND: cliniq/models/evaluation.py
- FOUND: cliniq/tests/test_models.py
- FOUND: .gitignore

**Commits created:**
- FOUND: 0a6e873 (Task 1)
- FOUND: c43309a (Task 2)
- FOUND: a245d85 (Task 3)

All claimed files and commits verified.
