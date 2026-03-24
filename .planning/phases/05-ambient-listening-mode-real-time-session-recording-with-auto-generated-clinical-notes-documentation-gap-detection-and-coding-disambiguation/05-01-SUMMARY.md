---
phase: 05-ambient-listening-mode
plan: 01
subsystem: backend
tags: [pydantic, faster-whisper, whisper, soap-note, ambient, transcription, llm]

# Dependency graph
requires:
  - phase: 02-cdi-explainability
    provides: "CDI pipeline (run_pipeline_audited, CDIReport, PipelineResult)"
  - phase: 01-foundation
    provides: "ModelManager singleton, Pydantic model patterns, NLU/coding pipeline"
provides:
  - "Ambient Pydantic schemas (AmbientSession, EncounterTranscript, StructuredNote, DisambiguationItem, AmbientEncounterDemo)"
  - "Audio transcription function (transcribe_audio) via faster-whisper"
  - "SOAP note generation function (generate_soap_note) via Qwen LLM"
  - "Full ambient pipeline orchestrator (run_ambient_pipeline) integrating CDI"
affects: [05-02-precompute-demo, 05-03-ambient-ui]

# Tech tracking
tech-stack:
  added: [faster-whisper>=1.1.0, streamlit>=1.40.0]
  patterns: [lazy-whisper-loading, soap-section-parsing, disambiguation-item-extraction]

key-files:
  created:
    - cliniq/models/ambient.py
    - cliniq/modules/m6_ambient.py
  modified:
    - cliniq/models/__init__.py
    - pyproject.toml

key-decisions:
  - "Lazy whisper model loading with module-level _whisper_model cache (same pattern as _KG_CACHE in m4_cdi.py)"
  - "Simple string-based section parsing for SOAP note extraction (CC, HPI, Assessment, Plan markers)"
  - "Fallback to raw transcript as note text when LLM generation fails"
  - "DisambiguationItem confidence sourced directly from CDI report item confidence values"

patterns-established:
  - "Ambient session state machine: idle -> recording -> processing -> results"
  - "AmbientEncounterDemo as pre-computed data contract for demo mode"

# Metrics
duration: 3min
completed: 2026-03-24
---

# Phase 5 Plan 1: Ambient Schemas and Backend Module Summary

**Pydantic v2 schemas for ambient sessions plus m6_ambient.py with faster-whisper transcription, Qwen SOAP note generation, and CDI-integrated disambiguation pipeline**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-24T21:17:49Z
- **Completed:** 2026-03-24T21:20:26Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Created 5 Pydantic v2 models covering the full ambient session lifecycle (transcript, note, disambiguation, session state, demo data)
- Built m6_ambient.py with 3 public functions: transcribe_audio, generate_soap_note, run_ambient_pipeline
- All heavy dependencies use lazy imports -- module is importable without triggering model downloads
- Updated pyproject.toml with faster-whisper>=1.1.0 and streamlit>=1.40.0

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ambient Pydantic schemas and update dependencies** - `446fdd6` (feat)
2. **Task 2: Create ambient backend module with transcription, note generation, and pipeline integration** - `93903a6` (feat)

## Files Created/Modified
- `cliniq/models/ambient.py` - 5 Pydantic v2 schemas: EncounterTranscript, StructuredNote, DisambiguationItem, AmbientSession, AmbientEncounterDemo
- `cliniq/modules/m6_ambient.py` - Backend module: transcribe_audio, generate_soap_note, run_ambient_pipeline with lazy model loading
- `cliniq/models/__init__.py` - Updated exports to include all 5 ambient models
- `pyproject.toml` - Added faster-whisper>=1.1.0, bumped streamlit to >=1.40.0

## Decisions Made
- Lazy whisper model loading with module-level `_whisper_model` cache (consistent with `_KG_CACHE` pattern in m4_cdi.py)
- Simple string-based SOAP section parsing using marker detection (Chief Complaint, HPI, Assessment, Plan) -- robust for LLM output without requiring structured JSON
- Raw transcript fallback as note text when LLM generation fails, ensuring pipeline always has input
- DisambiguationItem confidence values sourced directly from CDI report item confidence (gap.confidence, md.co_occurrence_weight)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All ambient schemas and backend functions are ready for Plan 02 (pre-compute demo data script)
- Plan 03 (ambient UI page) can import schemas and call run_ambient_pipeline directly
- No blockers or concerns

## Self-Check: PASSED

- FOUND: cliniq/models/ambient.py
- FOUND: cliniq/modules/m6_ambient.py
- FOUND: commit 446fdd6
- FOUND: commit 93903a6

---
*Phase: 05-ambient-listening-mode*
*Completed: 2026-03-24*
