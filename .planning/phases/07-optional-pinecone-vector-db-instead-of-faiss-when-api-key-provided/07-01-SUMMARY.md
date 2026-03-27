---
phase: 07-optional-pinecone-vector-db-instead-of-faiss-when-api-key-provided
plan: 01
subsystem: rag
tags: [pinecone, vector-db, faiss, retriever, factory-pattern, protocol]

# Dependency graph
requires:
  - phase: 06-cliniq-v2-openai-backend
    provides: "FAISSRetriever, OpenAIClient singleton, cliniq_v2 config, m3_rag_coding module"
provides:
  - "PineconeClient singleton with configure()/validate_key()/client"
  - "BaseRetriever Protocol for retriever abstraction"
  - "PineconeRetriever implementing BaseRetriever via Pinecone SDK"
  - "get_retriever() factory for transparent backend selection"
  - "m3_rag_coding wired through factory (no hardcoded FAISSRetriever)"
affects: [07-02, pinecone-index-population, deployment-config]

# Tech tracking
tech-stack:
  added: ["pinecone>=8.0.0 (optional)"]
  patterns: ["Retriever Protocol abstraction", "Factory pattern for backend selection", "Graceful optional dependency handling"]

key-files:
  created:
    - cliniq_v2/pinecone_client.py
    - cliniq_v2/rag/base.py
    - cliniq_v2/rag/pinecone_retriever.py
    - cliniq_v2/rag/factory.py
  modified:
    - cliniq_v2/config.py
    - cliniq_v2/rag/__init__.py
    - cliniq_v2/modules/m3_rag_coding.py
    - pyproject.toml

key-decisions:
  - "BaseRetriever as Protocol (structural subtyping) not ABC -- FAISSRetriever needs no modification"
  - "Factory catches RuntimeError and ImportError to fall back to FAISS transparently"
  - "PineconeRetriever uses lazy index connection (_ensure_connected) matching FAISS lazy-load pattern"
  - "Pinecone import wrapped in try/except at module level for graceful missing-package handling"

patterns-established:
  - "Protocol-based retriever abstraction: BaseRetriever defines retrieve() + ensure_index_built()"
  - "Factory pattern: get_retriever() returns correct backend based on runtime configuration"
  - "Graceful optional dependency: module importable even without pinecone package installed"

# Metrics
duration: 2min
completed: 2026-03-27
---

# Phase 7 Plan 1: Pinecone Retriever and Factory Wiring Summary

**PineconeClient singleton, BaseRetriever Protocol, PineconeRetriever with OpenAI embeddings, and get_retriever() factory replacing hardcoded FAISSRetriever in m3_rag_coding**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-27T23:02:42Z
- **Completed:** 2026-03-27T23:05:08Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- PineconeClient singleton mirroring OpenAIClient pattern, importable even without pinecone SDK
- BaseRetriever Protocol defining the retriever interface for both FAISS and Pinecone backends
- PineconeRetriever with lazy Pinecone index connection and OpenAI embedding query encoding
- get_retriever() factory transparently selecting backend based on PineconeClient configuration
- m3_rag_coding decoupled from FAISSRetriever, now using factory pattern

## Task Commits

Each task was committed atomically:

1. **Task 1: Create PineconeClient singleton, BaseRetriever Protocol, config constants, and pyproject.toml dependency** - `5b88544` (feat)
2. **Task 2: Create PineconeRetriever, retriever factory, update rag/__init__.py, and wire m3_rag_coding** - `85e7198` (feat)

## Files Created/Modified
- `cliniq_v2/pinecone_client.py` - Singleton Pinecone client with graceful missing-package handling
- `cliniq_v2/rag/base.py` - BaseRetriever Protocol defining retrieve() and ensure_index_built()
- `cliniq_v2/rag/pinecone_retriever.py` - Pinecone-based retriever using OpenAI embeddings
- `cliniq_v2/rag/factory.py` - get_retriever() factory for transparent backend selection
- `cliniq_v2/config.py` - Added PINECONE_INDEX_NAME and PINECONE_NAMESPACE constants
- `cliniq_v2/rag/__init__.py` - Updated exports with BaseRetriever, get_retriever, PineconeRetriever
- `cliniq_v2/modules/m3_rag_coding.py` - Replaced FAISSRetriever import with get_retriever factory
- `pyproject.toml` - Added pinecone optional dependency group

## Decisions Made
- BaseRetriever as Protocol (structural subtyping) so FAISSRetriever needs zero modifications to conform
- Factory catches both RuntimeError (not configured) and ImportError (package missing) for FAISS fallback
- PineconeRetriever uses lazy index connection pattern matching FAISS lazy-load approach
- Pinecone SDK import wrapped in try/except ImportError at module level for graceful degradation

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required. Pinecone is an optional dependency that activates only when configured with an API key.

## Next Phase Readiness
- Retriever abstraction and factory complete, ready for tests and population script in plan 07-02
- PineconeClient.configure() must be called with valid API key before PineconeRetriever activates
- Pinecone index must exist and be populated before PineconeRetriever.ensure_index_built() succeeds

## Self-Check: PASSED

- All 8 files verified present on disk
- Commit `5b88544` verified in git log
- Commit `85e7198` verified in git log
- All 6 overall verification commands passed

---
*Phase: 07-optional-pinecone-vector-db-instead-of-faiss-when-api-key-provided*
*Completed: 2026-03-27*
