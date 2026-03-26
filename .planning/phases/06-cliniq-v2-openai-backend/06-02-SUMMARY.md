---
phase: 06-cliniq-v2-openai-backend
plan: 02
subsystem: rag
tags: [openai, faiss, text-embedding-3-small, gpt-4o, icd10, rag]

requires:
  - phase: 06-01
    provides: "cliniq_v2 package foundation (config, api_client, __init__)"
provides:
  - "FAISS index builder using OpenAI text-embedding-3-small (1536d)"
  - "FAISSRetriever with OpenAI embedding at query time"
  - "m3_rag_coding with GPT-4o reasoning (no cross-encoder reranker)"
  - "cliniq_v2/rag/ package with build_index.py, retriever.py, __init__.py"
affects: [06-04-pipeline, 06-05-ui]

tech-stack:
  added: []
  patterns:
    - "OpenAI embeddings API in batches of 2048 for index building"
    - "Lazy import of OpenAIClient inside function bodies (not module level)"
    - "Direct GPT-4o confidence (no reranker score blending)"
    - "Reuse of cliniq v1 model-agnostic functions (sequence_codes, load_icd10_codes)"

key-files:
  created:
    - cliniq_v2/rag/__init__.py
    - cliniq_v2/rag/build_index.py
    - cliniq_v2/rag/retriever.py
    - cliniq_v2/modules/m3_rag_coding.py
  modified: []

key-decisions:
  - "OpenAI embeddings API in batches of 2048 for FAISS index building (1536d)"
  - "All 20 FAISS candidates sent to GPT-4o for combined reranking + selection + reasoning"
  - "Direct GPT-4o confidence (no blending with reranker score since reranker eliminated)"
  - "sequence_codes reused from cliniq v1 via import (model-agnostic)"
  - "ICD-10 loader reused from cliniq.rag.icd10_loader (no duplication)"

patterns-established:
  - "Single GPT-4o call replaces cross-encoder reranking + Qwen reasoning"
  - "response_format json_object for structured output (no retry logic needed)"
  - "Separate FAISS index at ~/.cache/cliniq_v2/icd10_index/ (not shared with v1)"

duration: 4min
completed: 2026-03-26
---

# Phase 06 Plan 02: RAG Infrastructure + Coding Module Summary

**FAISS index builder with OpenAI text-embedding-3-small (1536d) and m3_rag_coding using GPT-4o for combined retrieval-ranking-reasoning without cross-encoder**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-26T23:06:21Z
- **Completed:** 2026-03-26T23:10:46Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- FAISS index builder uses OpenAI text-embedding-3-small with batch size 2048 for 1536d embeddings
- FAISSRetriever uses OpenAI embeddings for query encoding (no BGE prefix, no local embedder)
- m3_rag_coding eliminates cross-encoder, sends all 20 candidates to GPT-4o for combined reranking + selection + reasoning
- GPT-4o structured output (response_format json_object) for code selection eliminates retry logic
- All Pydantic models (CodeSuggestion, CodingResult) reused from cliniq.models
- sequence_codes reused from cliniq v1 (model-agnostic, pure rule-based)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create cliniq_v2 RAG infrastructure (build_index + retriever)** - `68ac88b` (feat)
2. **Task 2: Create m3_rag_coding.py with GPT-4o reasoning (no cross-encoder)** - `1f8020a` (feat)

## Files Created/Modified
- `cliniq_v2/rag/__init__.py` - Re-exports FAISSRetriever and ICD-10 loader from cliniq
- `cliniq_v2/rag/build_index.py` - FAISS index builder using OpenAI embeddings API
- `cliniq_v2/rag/retriever.py` - FAISSRetriever with OpenAI embedding at query time
- `cliniq_v2/modules/m3_rag_coding.py` - RAG coding with GPT-4o reasoning (no cross-encoder)

## Decisions Made
- OpenAI embeddings API called in batches of 2048 for index building (balances API call count vs batch size)
- All 20 FAISS candidates sent to GPT-4o in a single call for combined reranking + selection + reasoning (eliminates cross-encoder dependency entirely)
- Direct GPT-4o confidence used (no blending with reranker score since there is no reranker)
- sequence_codes imported directly from cliniq.modules.m3_rag_coding (pure rule-based, no model dependency)
- ICD-10 loader imported from cliniq.rag.icd10_loader (not duplicated in cliniq_v2)
- FAISS index stored at ~/.cache/cliniq_v2/icd10_index/ (separate from cliniq v1)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. API key configuration handled by cliniq_v2/api_client.py (set at runtime via UI or environment).

## Next Phase Readiness
- RAG infrastructure ready for pipeline integration (plan 06-04)
- FAISSRetriever importable from cliniq_v2.rag
- m3_rag_coding.code_entities() returns CodingResult matching cliniq v1 schema
- No blockers for subsequent plans

## Self-Check: PASSED

- [x] cliniq_v2/rag/__init__.py exists
- [x] cliniq_v2/rag/build_index.py exists
- [x] cliniq_v2/rag/retriever.py exists
- [x] cliniq_v2/modules/m3_rag_coding.py exists
- [x] Commit 68ac88b found (Task 1)
- [x] Commit 1f8020a found (Task 2)

---
*Phase: 06-cliniq-v2-openai-backend*
*Completed: 2026-03-26*
