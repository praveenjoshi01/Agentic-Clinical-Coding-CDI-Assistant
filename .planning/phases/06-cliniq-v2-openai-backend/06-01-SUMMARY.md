---
phase: 06-cliniq-v2-openai-backend
plan: 01
subsystem: api
tags: [openai, gpt-4o, singleton, vision, ner, structured-output]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: "Pydantic models (ClinicalDocument, ClinicalEntity, NLUResult), m1_ingest parsers, config constants"
provides:
  - "cliniq_v2 package with __init__.py, config.py, api_client.py"
  - "OpenAI singleton client with runtime key injection and validation"
  - "GPT-4o vision image ingestion (m1_ingest.py)"
  - "GPT-4o structured NER with post-hoc offsets (m2_nlu.py)"
affects: [06-02, 06-03, 06-04, 06-05]

# Tech tracking
tech-stack:
  added: [openai]
  patterns: [singleton-api-client, gpt4o-structured-output, post-hoc-offset-computation, reuse-cliniq-models]

key-files:
  created:
    - cliniq_v2/__init__.py
    - cliniq_v2/config.py
    - cliniq_v2/api_client.py
    - cliniq_v2/modules/__init__.py
    - cliniq_v2/modules/m1_ingest.py
    - cliniq_v2/modules/m2_nlu.py
  modified: []

key-decisions:
  - "Singleton OpenAIClient with runtime configure() + validate_key() pattern"
  - "Reuse cliniq.models Pydantic schemas directly (no duplication)"
  - "Post-hoc offset computation for NER entities (GPT-4o returns text only, offsets computed by string search)"
  - "GPT-4o handles negation and qualifiers in single NER call (no separate detect_negation)"
  - "Separate cache directory (~/.cache/cliniq_v2/) to avoid v1 conflicts"

patterns-established:
  - "Singleton API client: all modules access OpenAIClient().client inside function bodies only"
  - "Model registry in config.py maps aliases to OpenAI model IDs"
  - "Reuse v1 infrastructure: import Pydantic models from cliniq.models, parsers from cliniq.modules"

# Metrics
duration: 4min
completed: 2026-03-26
---

# Phase 6 Plan 01: Package Foundation + Ingestion/NLU Summary

**cliniq_v2 package with singleton OpenAI client, GPT-4o vision image ingestion, and GPT-4o structured NER replacing local models**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-26T23:05:53Z
- **Completed:** 2026-03-26T23:09:51Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Created cliniq_v2 package foundation with OpenAI model registry (gpt-4o, text-embedding-3-small, whisper-1)
- Implemented singleton OpenAIClient with runtime key injection, validation, and clear/reset capability
- Built GPT-4o vision image parser replacing local SmolVLM, reusing FHIR/text parsers from cliniq v1
- Built GPT-4o structured NER module with post-hoc offset computation and qualifier capture logic

## Task Commits

Each task was committed atomically:

1. **Task 1: Create cliniq_v2 package foundation** - `8f9d336` (feat)
2. **Task 2: Create m1_ingest.py and m2_nlu.py** - `accbe3d` (feat)

## Files Created/Modified
- `cliniq_v2/__init__.py` - Package marker with version 2.0.0
- `cliniq_v2/config.py` - OpenAI model registry, cache paths, re-exported cliniq v1 constants
- `cliniq_v2/api_client.py` - Singleton OpenAI client with configure/validate/clear
- `cliniq_v2/modules/__init__.py` - Modules subpackage marker
- `cliniq_v2/modules/m1_ingest.py` - Multi-modal ingestion with GPT-4o vision for images
- `cliniq_v2/modules/m2_nlu.py` - GPT-4o structured NER with negation, qualifiers, post-hoc offsets

## Decisions Made
- Singleton OpenAIClient with class-level _instance/_client and __new__ pattern (matches research recommendation)
- Post-hoc offset computation for NER: GPT-4o returns entity text only, start_char/end_char computed by string.find() with case-insensitive fallback
- GPT-4o handles negation detection in the NER prompt (no separate detect_negation function needed)
- Qualifier capture logic mirrors cliniq v1 pattern (50-char window, attach to nearest diagnosis/procedure)
- Separate cache directory (~/.cache/cliniq_v2/) to avoid FAISS index dimension conflicts with v1
- response_format={"type": "json_object"} for NER (compatible with openai v2.26.0)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed forbidden references from docstrings**
- **Found during:** Task 2 verification
- **Issue:** Docstrings in m1_ingest.py and m2_nlu.py referenced "SmolVLM" and "d4data" respectively, which the plan verification checks flag as forbidden
- **Fix:** Replaced with generic terms ("local vision model", "local NER model")
- **Files modified:** cliniq_v2/modules/m1_ingest.py, cliniq_v2/modules/m2_nlu.py
- **Verification:** String search confirms no forbidden references in any cliniq_v2 file
- **Committed in:** accbe3d (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor docstring cleanup. No scope creep.

## Issues Encountered
None

## User Setup Required

External services require configuration before API calls can be made:
- **OPENAI_API_KEY**: Required for GPT-4o and embedding calls. Obtain from OpenAI Dashboard -> API keys -> Create new secret key.
- The API key is injected at runtime via `OpenAIClient().configure(api_key)` -- never hardcoded.

## Next Phase Readiness
- cliniq_v2 package foundation established with all 6 files
- Singleton API client pattern ready for use by all subsequent modules (m3-m6)
- Config points to OpenAI models; cache paths separated from v1
- Ready for Plan 02: RAG coding module with OpenAI embeddings + GPT-4o reasoning

## Self-Check: PASSED

All 6 created files verified on disk. Both task commits (8f9d336, accbe3d) verified in git log.

---
*Phase: 06-cliniq-v2-openai-backend*
*Completed: 2026-03-26*
