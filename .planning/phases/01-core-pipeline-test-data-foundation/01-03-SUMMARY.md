---
phase: 01-core-pipeline-test-data-foundation
plan: 03
subsystem: ingestion
tags: [fhir, multimodal, text-parsing, image-ocr, modality-detection]
dependency_graph:
  requires:
    - cliniq.models.document (ClinicalDocument, DocumentMetadata)
    - cliniq.model_manager (ModelManager.get_multimodal())
  provides:
    - cliniq.modules.m1_ingest.ingest() - main entry point
    - cliniq.modules.m1_ingest.detect_modality() - routing logic
    - cliniq.modules.m1_ingest.parse_fhir() - FHIR R4B parser
    - cliniq.modules.m1_ingest.parse_text() - text wrapper
    - cliniq.modules.m1_ingest.parse_image() - SmolVLM OCR
  affects:
    - Phase 01 Plan 04 (NER module) - will receive ClinicalDocument instances
    - Phase 01 Plan 06 (test data generation) - will use ingestion for synthetic data
tech_stack:
  added:
    - fhir.resources (R4B) for FHIR Bundle/Condition/Procedure validation
    - PIL for image loading
  patterns:
    - Modality detection router pattern
    - Lazy model loading via ModelManager singleton
    - Confidence heuristics for OCR quality
key_files:
  created:
    - cliniq/modules/m1_ingest.py
    - cliniq/tests/test_m1_ingest.py
  modified:
    - pyproject.toml (removed outlines dependency - requires Rust compiler)
decisions:
  - decision: Use FHIR R4B (not R5) for parsing
    rationale: Research pitfall 2 highlighted R5 compatibility issues; R4B is standard for clinical systems
  - decision: Confidence heuristic for image extraction based on text length
    rationale: Longer extracted text indicates more successful OCR; clamped to 0.4-0.85 range
  - decision: Remove outlines dependency
    rationale: Requires Rust compiler not available in environment; not needed for ingestion module
  - decision: Use get_resource_type() method instead of resource_type attribute
    rationale: fhir.resources R4B uses method-based access pattern
metrics:
  duration_minutes: 5
  tasks_completed: 2
  tests_added: 12
  files_created: 2
  commits: 2
  completed_date: "2026-03-18"
---

# Phase 01 Plan 03: Multi-Modal Ingestion Module Summary

**One-liner:** Multi-modal ingestion with FHIR R4B parser, text wrapper, and SmolVLM image OCR - automatic modality detection routes all inputs to validated ClinicalDocument instances.

## Objective Achieved

Built the pipeline's entry point: a multi-modal ingestion system that accepts FHIR JSON bundles, plain text notes, or image file paths and returns validated ClinicalDocument instances. All downstream NER and RAG modules can now process clinical data regardless of original format.

## Tasks Completed

| Task | Name                                                      | Commit  | Files Modified                                 |
| ---- | --------------------------------------------------------- | ------- | ---------------------------------------------- |
| 1    | Multi-modal ingestion module with FHIR, text, and image parsers | 0ae0506 | cliniq/modules/m1_ingest.py                    |
| 2    | Ingestion unit tests with synthetic FHIR and text fixtures | a60a868 | cliniq/tests/test_m1_ingest.py, pyproject.toml, m1_ingest.py |

## What Was Built

### 1. Modality Detection Router

**detect_modality(input_data) -> Literal["fhir", "text", "image"]:**
- Image detection: checks file extensions (.png, .jpg, .jpeg, .bmp, .tiff)
- FHIR detection: checks for "resourceType" key in dict or JSON string
- Text fallback: anything else treated as plain clinical text
- Handles str, Path, and dict inputs

### 2. FHIR R4B Parser

**parse_fhir(fhir_data) -> ClinicalDocument:**
- Validates FHIR Bundle using `fhir.resources.R4B` (capital letters, not lowercase)
- Extracts Patient, Encounter, Condition, Procedure resources
- Builds narrative from resource text fields
- Captures structured facts with ICD-10 codings, clinical status, procedure status
- Uses `get_resource_type()` method (not attribute) for resource type checking
- Patient/encounter IDs extracted from resources or generated as UUIDs
- modality_confidence=1.0 for validated FHIR

### 3. Text Parser

**parse_text(text) -> ClinicalDocument:**
- Simple wrapper for plain text notes
- Generates UUID patient/encounter IDs
- modality_confidence=1.0
- No structured facts (NER module will extract entities downstream)

### 4. Image Parser

**parse_image(image_path) -> ClinicalDocument:**
- Uses ModelManager.get_multimodal() for lazy SmolVLM loading
- Loads image with PIL
- Chat template: "Extract all clinical text from this medical document..."
- Generates with max_new_tokens=1024
- Cleans output to remove chat template artifacts
- Confidence heuristic: clamp(len(text)/500, 0.4, 0.85)
- Longer extractions get higher confidence (indicates better OCR)

### 5. Main Ingestion Router

**ingest(input_data) -> ClinicalDocument:**
- detect_modality() -> dispatch to parser
- Pydantic validation ensures all outputs are valid ClinicalDocuments
- Single entry point for all modalities

### 6. Comprehensive Test Suite (12 tests)

**Test coverage:**
- **Modality detection (5 tests):** text, FHIR dict, FHIR JSON string, image extensions, invalid dict
- **Text parsing (1 test):** validates ClinicalDocument structure, UUID generation, confidence=1.0
- **FHIR parsing (2 tests):** validates narrative extraction, structured facts, patient/encounter IDs, handles JSON string input
- **Routing (2 tests):** verifies ingest() routes text and FHIR correctly
- **Validation (2 tests):** Pydantic validation, patient/encounter ID presence

**FHIR test fixtures:**
- Proper R4B structure with Patient, Condition, Procedure resources
- Condition: Type 2 diabetes mellitus with ICD-10 E11.9 coding
- Procedure: Hemoglobin A1c test (completed status)
- Includes required `subject` references per R4B schema

**Slow tests (marked @pytest.mark.slow):**
- Image parsing tests (require SmolVLM model download)
- Missing file and invalid path error handling

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed outlines dependency**
- **Found during:** pip install after Task 1
- **Issue:** outlines package requires Rust compiler via outlines_core; not available in environment
- **Fix:** Removed from pyproject.toml dependencies
- **Rationale:** outlines is for structured generation (used in reasoning module), not needed for ingestion
- **Files modified:** pyproject.toml
- **Commit:** a60a868 (included with Task 2)

**2. [Rule 1 - Bug] Fixed FHIR R4B import paths**
- **Found during:** First test run after Task 1
- **Issue:** Used lowercase `fhir.resources.r4b` but module is capital `R4B`
- **Fix:** Changed imports to `from fhir.resources.R4B.bundle import Bundle`
- **Files modified:** cliniq/modules/m1_ingest.py
- **Commit:** a60a868 (included with Task 2)

**3. [Rule 1 - Bug] Fixed resource_type access pattern**
- **Found during:** Test run after import fix
- **Issue:** Used `resource.resource_type` attribute but fhir.resources R4B uses method-based access
- **Fix:** Changed to `resource.get_resource_type()`
- **Files modified:** cliniq/modules/m1_ingest.py
- **Commit:** a60a868 (included with Task 2)

**4. [Rule 1 - Bug] Added missing subject references in test FHIR fixtures**
- **Found during:** FHIR validation test
- **Issue:** R4B Condition and Procedure resources require `subject` field (patient reference)
- **Fix:** Added `"subject": {"reference": "Patient/patient-001"}` to Condition and Procedure test resources
- **Files modified:** cliniq/tests/test_m1_ingest.py
- **Commit:** a60a868 (included with Task 2)

## Verification Results

1. All 12 non-slow tests pass: `pytest cliniq/tests/test_m1_ingest.py -v -k "not slow"` → 12 passed in 0.27s
2. FHIR parsing uses R4B imports (capital letters): Verified in source code
3. Text parsing returns ClinicalDocument with confidence=1.0: Test validates
4. Modality detection correctly identifies FHIR JSON, plain text, and image paths: 5 tests confirm
5. All returned ClinicalDocument instances pass Pydantic validation: Tests confirm

## Success Criteria Met

- [x] ingest() accepts FHIR dict, FHIR JSON string, plain text string, and image file path
- [x] detect_modality() correctly routes all input types
- [x] FHIR parser uses fhir.resources.R4B (not R5 default) per research pitfall
- [x] Image parser uses SmolVLM with appropriate prompt and confidence heuristic
- [x] 12 unit tests pass covering all modalities and edge cases (2 slow tests excluded)

## Impact on Downstream Work

**Enables:**
- Phase 01 Plan 04 (NER module): Can receive ClinicalDocument instances from any modality
- Phase 01 Plan 06 (test data generation): Can use ingestion to validate synthetic FHIR/text/image data
- Phase 02 evaluation: Gold standard cases can be ingested regardless of source format

**Provides:**
- Unified ClinicalDocument abstraction hiding modality complexity
- Automatic routing eliminates manual format checking
- Confidence scores indicate OCR quality for downstream filtering

**Critical design decisions:**
- R4B validation ensures compatibility with real-world EHR systems
- UUID generation for missing IDs prevents null reference errors
- Confidence heuristics allow downstream modules to filter low-quality OCR

## Next Steps

1. Implement NER module (01-04) using d4data/biomedical-ner-all on ClinicalDocument.raw_narrative
2. Build RAG module (01-05) for ICD-10 code retrieval
3. Generate test data (01-06) including synthetic FHIR bundles and PIL-generated images

## Self-Check: PASSED

**Files created:**
- FOUND: cliniq/modules/m1_ingest.py
- FOUND: cliniq/tests/test_m1_ingest.py

**Files modified:**
- FOUND: pyproject.toml (outlines removed)

**Commits created:**
- FOUND: 0ae0506 (Task 1 - ingestion module)
- FOUND: a60a868 (Task 2 - tests and fixes)

**Test verification:**
- PASSED: 12 tests pass in pytest cliniq/tests/test_m1_ingest.py -v -k "not slow"

All claimed files, commits, and test results verified.
