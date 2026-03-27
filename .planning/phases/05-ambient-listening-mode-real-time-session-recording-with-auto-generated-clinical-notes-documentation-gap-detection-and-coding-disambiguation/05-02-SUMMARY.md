---
phase: 05-ambient-listening-mode
plan: 02
subsystem: demo-data
tags: [ambient, demo, json, precompute, clinical-notes, icd10, cdi, soap]

# Dependency graph
requires:
  - phase: 05-ambient-listening-mode
    plan: 01
    provides: "AmbientEncounterDemo schema, ambient pipeline functions"
  - phase: 02-cdi-explainability
    provides: "CDI pipeline (run_pipeline_audited, CDIReport, PipelineResult)"
provides:
  - "Pre-computed ambient encounter 001: Primary care CKD/HTN/DM2 follow-up"
  - "Pre-computed ambient encounter 002: Urgent care chest pain/SOB evaluation"
  - "Ambient demo data regeneration script (precompute_ambient.py)"
affects: [05-03-ambient-ui]

# Tech tracking
tech-stack:
  added: []
  patterns: [handcrafted-demo-data, pipeline-result-regeneration, disambiguation-item-generation]

key-files:
  created:
    - ui/demo_data/ambient/encounter_001.json
    - ui/demo_data/ambient/encounter_002.json
    - scripts/precompute_ambient.py
  modified: []

key-decisions:
  - "Handcrafted JSON over pipeline-generated: demo data is authored for clinical realism and clinical realism, not auto-generated from models"
  - "SOAP note as pipeline input for regeneration: precompute script feeds generated_note (not transcript) to run_pipeline_audited"
  - "9 disambiguation items total (5 + 4) covering gaps, missed diagnoses, ambiguities, and conflicts across both scenarios"

patterns-established:
  - "Ambient demo data pattern: encounter JSON with transcript + SOAP note + pipeline_result + disambiguation_items"
  - "Precompute script pattern: load existing JSON, feed note to pipeline, update result fields, write back"

# Metrics
duration: 5min
completed: 2026-03-24
---

# Phase 5 Plan 2: Pre-compute Ambient Demo Data Summary

**Two handcrafted ambient encounter JSONs (CKD/HTN/DM2 primary care + chest pain urgent care) with realistic transcripts, SOAP notes, pipeline results, CDI findings, and disambiguation items plus regeneration script**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-24T21:23:58Z
- **Completed:** 2026-03-24T21:29:21Z
- **Tasks:** 2
- **Files created:** 3

## Accomplishments
- Created encounter_001.json: Primary care follow-up with CKD stage 3, HTN, and DM2 -- 5899-char transcript, 3354-char SOAP note, 11 NLU entities, 5 ICD-10 codes, 2 documentation gaps, 1 missed diagnosis, 5 disambiguation items
- Created encounter_002.json: Urgent care chest pain with SOB -- 5585-char transcript, 3775-char SOAP note, 10 NLU entities, 5 ICD-10 codes, 1 documentation gap, 1 missed diagnosis, 1 code conflict, 4 disambiguation items
- Created precompute_ambient.py following precompute_demo.py pattern for pipeline result regeneration

## Task Commits

Each task was committed atomically:

1. **Task 1: Create pre-computed ambient encounter JSON files** - `fb1477e` (feat)
2. **Task 2: Create precompute_ambient.py regeneration script** - `c91e558` (feat)

## Files Created/Modified
- `ui/demo_data/ambient/encounter_001.json` - Primary care CKD/HTN/DM2 follow-up encounter with full pipeline output
- `ui/demo_data/ambient/encounter_002.json` - Urgent care chest pain/SOB encounter with full pipeline output
- `scripts/precompute_ambient.py` - Regeneration script feeding SOAP notes through live pipeline

## Decisions Made
- Handcrafted JSON over pipeline-generated: ensures clinically realistic, impressive clinical content without model dependency
- SOAP note (generated_note) is the pipeline input for regeneration, since that is what run_pipeline_audited processes
- 9 disambiguation items total covering all four categories (gap, missed_diagnosis, conflict, ambiguity)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Both ambient encounter JSON files are ready for Plan 03 (ambient UI page)
- UI can load encounters instantly via AmbientEncounterDemo.model_validate()
- precompute_ambient.py can refresh pipeline results when models are available
- No blockers or concerns

## Self-Check: PASSED

- FOUND: ui/demo_data/ambient/encounter_001.json
- FOUND: ui/demo_data/ambient/encounter_002.json
- FOUND: scripts/precompute_ambient.py
- FOUND: commit fb1477e
- FOUND: commit c91e558

---
*Phase: 05-ambient-listening-mode*
*Completed: 2026-03-24*
