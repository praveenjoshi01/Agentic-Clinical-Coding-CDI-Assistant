---
phase: 06-cliniq-v2-openai-backend
plan: 03
subsystem: api
tags: [openai, gpt-4o, whisper, cdi, ambient, explainability, clinical-nlp]

# Dependency graph
requires:
  - phase: 06-cliniq-v2-openai-backend plan 01
    provides: cliniq_v2 package foundation (api_client, config, __init__)
provides:
  - m4_cdi.py with GPT-4o physician query generation
  - m5_explainability.py thin re-export of model-agnostic utilities
  - m6_ambient.py with Whisper API transcription and GPT-4o SOAP notes
affects: [06-04-pipeline, 06-05-ui-integration]

# Tech tracking
tech-stack:
  added: []
  patterns: [openai-chat-completions-json, whisper-api-transcription, module-reexport-pattern]

key-files:
  created:
    - cliniq_v2/modules/m4_cdi.py
    - cliniq_v2/modules/m5_explainability.py
    - cliniq_v2/modules/m6_ambient.py
  modified: []

key-decisions:
  - "Re-export m5_explainability from cliniq rather than duplicating (all functions model-agnostic)"
  - "Reuse _extract_entity_qualifiers, _find_evidence_for_code, calculate_completeness_score from cliniq.modules.m4_cdi directly"
  - "Reuse _parse_note_sections from cliniq.modules.m6_ambient (pure string parsing)"
  - "Set duration_seconds=0.0 for Whisper API transcription (API does not return duration)"

patterns-established:
  - "Module re-export: m5_explainability is a pure re-export, proving model-agnostic modules need no v2 rewrite"
  - "GPT-4o JSON structured output for physician queries with template fallback on failure"
  - "Lazy OpenAI client import inside function bodies (never at module level)"

# Metrics
duration: 5min
completed: 2026-03-26
---

# Phase 06 Plan 03: CDI, Explainability, and Ambient Modules Summary

**GPT-4o physician query generation for CDI, Whisper API transcription for ambient mode, and thin re-export of model-agnostic explainability utilities**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-26T23:06:28Z
- **Completed:** 2026-03-26T23:12:17Z
- **Tasks:** 2
- **Files created:** 3

## Accomplishments
- Created m4_cdi.py that uses GPT-4o for physician query generation with template fallback, reusing all KG infrastructure and helper functions from cliniq
- Created m5_explainability.py as a thin re-export of all model-agnostic utilities from cliniq (AuditTrailBuilder, capture_cot_and_json, link_evidence_spans, build_retrieval_log)
- Created m6_ambient.py with OpenAI Whisper API for transcription (no local model) and GPT-4o for SOAP note generation, with section parsing reused from cliniq

## Task Commits

Each task was committed atomically:

1. **Task 1: Create m4_cdi.py and m5_explainability.py** - `1f8020a` (feat)
2. **Task 2: Create m6_ambient.py** - `1a8719c` (feat)
3. **Docstring cleanup** - `632b784` (fix) - removed local model name references from docstrings

## Files Created/Modified
- `cliniq_v2/modules/m5_explainability.py` - Pure re-export of model-agnostic explainability utilities from cliniq
- `cliniq_v2/modules/m4_cdi.py` - CDI analysis with GPT-4o physician queries, KG infrastructure reused from cliniq
- `cliniq_v2/modules/m6_ambient.py` - Ambient pipeline with Whisper API transcription and GPT-4o SOAP notes

## Decisions Made
- Re-export m5_explainability directly from cliniq (zero new logic, all functions are model-agnostic)
- Import helper functions (_extract_entity_qualifiers, _find_evidence_for_code, calculate_completeness_score) from cliniq.modules.m4_cdi rather than re-implementing (pure data manipulation)
- Import _parse_note_sections from cliniq.modules.m6_ambient (pure string parsing, no model dependency)
- Set duration_seconds=0.0 for Whisper API transcription (API response does not include duration; field is informational only)
- Lazy import of cliniq_v2.pipeline in run_ambient_pipeline (pipeline module created in plan 04)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed local model name references from docstrings**
- **Found during:** Overall verification (post-Task 2)
- **Issue:** Module docstrings contained references to "Qwen" which triggered strict verification check for forbidden strings
- **Fix:** Replaced specific model name references with generic terms ("local models", "local LLM")
- **Files modified:** cliniq_v2/modules/m4_cdi.py, cliniq_v2/modules/m6_ambient.py
- **Verification:** grep for forbidden terms passes clean
- **Committed in:** `632b784`

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Cosmetic fix only. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required (API key configured at runtime via existing api_client.py).

## Next Phase Readiness
- All six pipeline modules (m1-m6) now exist in cliniq_v2/modules/
- Ready for plan 04 (pipeline orchestrator) to import from cliniq_v2.modules
- m6_ambient.py has lazy import of cliniq_v2.pipeline which will be satisfied when plan 04 executes

## Self-Check: PASSED

All 4 files verified present. All 3 commits verified in git log.

---
*Phase: 06-cliniq-v2-openai-backend*
*Completed: 2026-03-26*
