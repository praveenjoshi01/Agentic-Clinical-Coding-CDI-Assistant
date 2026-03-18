---
phase: 02-cdi-intelligence-layer
plan: 04
subsystem: cdi-intelligence
tags: [cdi-agent, physician-query, qwen-llm, knowledge-graph, completeness-score, template-fallback]

# Dependency graph
requires:
  - phase: 02-02
    provides: "find_documentation_gaps, find_code_conflicts, find_missed_diagnoses KG query functions"
  - phase: 02-03
    provides: "capture_cot_and_json for CoT trace capture (EXPL-03)"
provides:
  - "run_cdi_analysis orchestrator producing CDIReport from NLUResult + CodingResult (CDI-05)"
  - "generate_physician_query with Qwen LLM + template fallback (CDI-02)"
  - "calculate_completeness_score with gap/conflict penalties (CDI-05)"
  - "Module-level KG caching via _get_kg() for single-build reuse"
affects: [02-05, 02-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Module-level KG caching with _KG_CACHE global and _get_kg() accessor"
    - "Template fallback for physician queries when LLM JSON parsing fails"
    - "Gap/conflict penalty scoring with clamped [0,1] output"

key-files:
  created:
    - "cliniq/modules/m4_cdi.py"
    - "cliniq/tests/test_m4_cdi.py"
  modified: []

key-decisions:
  - "Module-level KG caching via global _KG_CACHE to avoid rebuilding per call"
  - "Template fallback for physician queries ensures valid output when LLM fails"
  - "Gap penalty 10%, conflict penalty 15%, clamped to [0.0, 1.0] for completeness scoring"
  - "Default confidence 0.8 for KG-based documentation gaps"

patterns-established:
  - "CDI agent as pure orchestrator: queries KG, calls LLM, assembles CDIReport"
  - "use_llm_queries=False flag enables fast testing without model downloads"

# Metrics
duration: 2min
completed: 2026-03-18
---

# Phase 2 Plan 4: CDI Agent Module Summary

**CDI agent orchestrating KG-based gap/conflict/missed-diagnosis detection with Qwen physician query generation and template fallback**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-18T15:28:59Z
- **Completed:** 2026-03-18T15:31:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- run_cdi_analysis orchestrator consuming NLUResult + CodingResult, querying frozen KG for gaps/conflicts/missed diagnoses, and assembling CDIReport (CDI-01 through CDI-05)
- generate_physician_query using Qwen LLM with few-shot examples and template fallback when JSON parsing fails (CDI-02)
- calculate_completeness_score with 10% gap penalty, 15% conflict penalty, clamped to [0.0, 1.0] (CDI-05)
- Module-level KG caching (_KG_CACHE) to build once and reuse across calls
- Raw CoT trace captured for every LLM physician query generation via capture_cot_and_json (EXPL-03)
- 8 non-slow tests pass covering completeness scoring, qualifier extraction, empty input handling, and no-LLM CDI analysis; 2 slow tests defined for LLM testing

## Task Commits

Each task was committed atomically:

1. **Task 1: CDI agent module with physician query generation** - `bf838a8` (feat)
2. **Task 2: CDI agent unit tests** - `01f03d2` (test)

## Files Created/Modified

- `cliniq/modules/m4_cdi.py` - CDI agent with run_cdi_analysis, generate_physician_query, calculate_completeness_score, _extract_entity_qualifiers, _find_evidence_for_code, and KG caching
- `cliniq/tests/test_m4_cdi.py` - 10 unit tests (8 fast + 2 slow) covering all CDI agent functions

## Decisions Made

- **Module-level KG caching:** Global `_KG_CACHE` with `_get_kg()` accessor ensures the knowledge graph is built once and reused across CDI analysis calls, avoiding expensive rebuild per case
- **Template fallback for physician queries:** When LLM JSON parsing fails, a template-based query is generated using the gap's missing qualifier, description, and code - ensures valid output always
- **Gap/conflict penalty scoring:** 10% per gap, 15% per conflict, clamped to [0.0, 1.0] - simple, interpretable scoring that penalizes conflicts more heavily than missing qualifiers
- **Default confidence 0.8 for KG-based gaps:** All KG-detected documentation gaps get 0.8 confidence since they are rule-based (deterministic from graph structure)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- CDI agent ready for pipeline orchestrator integration (Plan 05)
- run_cdi_analysis accepts NLUResult + CodingResult from Phase 1 pipeline
- use_llm_queries=False flag available for fast testing without model downloads
- KG caching ensures efficient multi-case analysis

## Self-Check: PASSED

- FOUND: cliniq/modules/m4_cdi.py
- FOUND: cliniq/tests/test_m4_cdi.py
- FOUND: commit bf838a8
- FOUND: commit 01f03d2

---
*Phase: 02-cdi-intelligence-layer*
*Completed: 2026-03-18*
