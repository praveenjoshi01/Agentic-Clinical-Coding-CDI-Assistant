---
phase: 06-cliniq-v2-openai-backend
plan: 05
subsystem: ui
tags: [streamlit, openai, api-key, backend-selector, faiss, dynamic-import]

# Dependency graph
requires:
  - phase: 06-04
    provides: "cliniq_v2 pipeline orchestrator with run_pipeline_audited and PipelineResult"
provides:
  - "API key gate in app.py blocking pages until key provided or v1 fallback chosen"
  - "Backend selector helper (ui/helpers/backend.py) for dynamic cliniq/cliniq_v2 imports"
  - "FAISS index existence check in pipeline_status.py preventing v2 crashes"
  - "All UI pages dynamically import from correct backend based on session state"
affects: [06-06, ui-pages, pipeline-runner, ambient-mode]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dynamic module import via get_pipeline_module() / get_ambient_module()"
    - "Session-state-based backend selection (openai_api_key presence)"
    - "FAISS index gate before v2 pipeline execution"

key-files:
  created:
    - ui/helpers/__init__.py
    - ui/helpers/backend.py
  modified:
    - ui/app.py
    - ui/pages/pipeline_runner.py
    - ui/pages/ambient_mode.py
    - ui/components/pipeline_status.py

key-decisions:
  - "Backend selection via session state key presence (not explicit toggle)"
  - "TYPE_CHECKING imports preserved for IDE support; only runtime imports made dynamic"
  - "qa_bot.py unchanged -- only TYPE_CHECKING import, no runtime cliniq imports to replace"
  - "FAISS index check returns None (not crash) when v2 index missing"
  - "_get_model_manager() retained for v1 fallback (lazy import inside cached function)"

patterns-established:
  - "Dynamic backend import: always call get_pipeline_module() at runtime, never import cliniq.pipeline directly"
  - "FAISS index gate: check INDEX_DIR / 'icd10.faiss' before v2 pipeline execution"

# Metrics
duration: 2min
completed: 2026-03-27
---

# Phase 6 Plan 5: UI Integration Summary

**API key gate with OpenAI validation, dynamic backend selector for cliniq/cliniq_v2, and FAISS index existence check across all UI pages**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-27T20:45:48Z
- **Completed:** 2026-03-27T20:48:06Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- API key gate in app.py blocks page rendering until OpenAI key is provided or user opts for v1 fallback
- Backend selector helper provides get_pipeline_module() and get_ambient_module() for session-state-based dynamic imports
- All 3 UI files with runtime cliniq imports updated to use backend selector (pipeline_runner, ambient_mode, pipeline_status)
- FAISS index existence check prevents v2 pipeline crashes with actionable error message
- Sidebar footer shows correct backend version (v2.0.0 OpenAI or v0.1.0 Local)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add API key gate to app.py and create backend selector helper** - `a92c73e` (feat)
2. **Task 2: Update UI page imports to use backend selector with FAISS index check** - `f1d6def` (feat)

## Files Created/Modified
- `ui/helpers/__init__.py` - Package marker for helpers module
- `ui/helpers/backend.py` - Backend selector with is_v2_backend(), get_pipeline_module(), get_ambient_module()
- `ui/app.py` - API key gate, OpenAI validation, session state defaults, sidebar version footer
- `ui/pages/pipeline_runner.py` - Dynamic PipelineResult import via get_pipeline_module()
- `ui/pages/ambient_mode.py` - Dynamic ambient module and pipeline module imports
- `ui/components/pipeline_status.py` - FAISS index check, dynamic pipeline import, v2 status labels

## Decisions Made
- Backend selection via session state key presence (not explicit toggle) -- simplest approach, automatic switching
- TYPE_CHECKING imports preserved for IDE support; only runtime imports made dynamic
- qa_bot.py unchanged -- only has TYPE_CHECKING import, no runtime cliniq imports to replace
- FAISS index check returns None (not crash) when v2 index missing, with actionable guidance
- _get_model_manager() retained for v1 fallback (lazy import inside cached function)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. API key is entered through the UI gate at runtime.

## Next Phase Readiness
- All UI pages are now connected to both cliniq and cliniq_v2 backends
- Ready for plan 06-06 (v2 FAISS index build script and backend-aware pipeline execution)
- Original cliniq package remains completely untouched

## Self-Check: PASSED

All 6 files verified present. Both task commits (a92c73e, f1d6def) confirmed in git log.

---
*Phase: 06-cliniq-v2-openai-backend*
*Completed: 2026-03-27*
