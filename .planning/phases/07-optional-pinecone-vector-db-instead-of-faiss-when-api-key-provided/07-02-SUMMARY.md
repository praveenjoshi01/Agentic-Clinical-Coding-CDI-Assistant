---
phase: 07-optional-pinecone-vector-db-instead-of-faiss-when-api-key-provided
plan: 02
subsystem: ui
tags: [pinecone, vector-db, faiss, cli, streamlit, api-key-gate, sidebar]

# Dependency graph
requires:
  - phase: 07-optional-pinecone-vector-db-instead-of-faiss-when-api-key-provided
    plan: 01
    provides: "PineconeClient singleton, BaseRetriever Protocol, PineconeRetriever, get_retriever factory"
provides:
  - "populate_pinecone_index.py CLI for one-time index creation and ICD-10 embedding upload"
  - "Optional Pinecone API key input on UI startup page"
  - "is_pinecone_backend() helper for runtime backend detection"
  - "Sidebar vector DB indicator (Pinecone vs FAISS)"
affects: [deployment-config, user-documentation]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Optional API key gate with graceful fallback", "Sidebar status indicator for active backend"]

key-files:
  created:
    - scripts/populate_pinecone_index.py
  modified:
    - ui/app.py
    - ui/helpers/backend.py

key-decisions:
  - "Batch size 200 for embedding and upsert (manageable for 265 ICD-10 codes)"
  - "Pinecone key validation in Connect button handler before st.rerun() to show warning on same page"
  - "Post-gate PineconeClient configuration mirrors OpenAIClient pattern (singleton, idempotent)"
  - "Sidebar caption extended (not replaced) to show vector DB backend alongside model info"

patterns-established:
  - "Optional service key: input field with placeholder + help text + graceful fallback on invalid/missing"
  - "Post-gate singleton configuration: check if already configured before calling configure()"

# Metrics
duration: 2min
completed: 2026-03-27
---

# Phase 7 Plan 2: Pinecone Population Script and UI Integration Summary

**Pinecone index population CLI with --check/--delete flags, optional Pinecone API key on startup page with FAISS fallback, and sidebar vector DB indicator**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-27T23:07:27Z
- **Completed:** 2026-03-27T23:09:44Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Population CLI script that creates Pinecone serverless index, embeds ICD-10 codes with OpenAI, and upserts with code/description/chapter metadata
- Optional Pinecone API key input field on UI startup page with validation and graceful FAISS fallback
- Sidebar footer shows "Vector DB: Pinecone" when Pinecone is active, "Vector DB: FAISS (local)" otherwise
- is_pinecone_backend() helper for downstream backend detection

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Pinecone index population CLI script** - `7fa8724` (feat)
2. **Task 2: Add optional Pinecone API key to UI startup gate and sidebar indicator** - `6faa06e` (feat)

## Files Created/Modified
- `scripts/populate_pinecone_index.py` - CLI to create/populate/check/delete Pinecone serverless index with ICD-10 embeddings
- `ui/app.py` - Optional Pinecone key input, validation, post-gate configuration, sidebar vector DB indicator
- `ui/helpers/backend.py` - Added is_pinecone_backend() helper function

## Decisions Made
- Batch size 200 for both embedding API calls and Pinecone upserts (safe for ~265 ICD-10 codes)
- Pinecone key validation happens before st.rerun() so warnings display on the same page load
- Post-gate PineconeClient configuration mirrors the OpenAIClient pattern (test if configured, configure if not)
- Sidebar caption extended to show vector DB backend info alongside model name

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

**Pinecone is fully optional.** Users who want cloud vector search need:
1. Create a free Pinecone account at https://app.pinecone.io
2. Copy their API key
3. Enter it in the UI startup page alongside the OpenAI key
4. Run `python scripts/populate_pinecone_index.py --openai-api-key KEY --pinecone-api-key KEY` once to populate the index

Users without a Pinecone key see no changes -- FAISS remains the default.

## Next Phase Readiness
- Phase 7 (Optional Pinecone Vector DB) is now complete
- Full flow: PineconeClient singleton, BaseRetriever Protocol, PineconeRetriever, factory wiring, population CLI, UI integration
- All existing functionality preserved when Pinecone key is not provided

## Self-Check: PASSED

- All 3 files verified present on disk
- Commit `7fa8724` verified in git log
- Commit `6faa06e` verified in git log
- All 7 overall verification commands passed

---
*Phase: 07-optional-pinecone-vector-db-instead-of-faiss-when-api-key-provided*
*Completed: 2026-03-27*
