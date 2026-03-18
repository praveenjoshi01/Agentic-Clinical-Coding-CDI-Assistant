# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-18)

**Core value:** Every clinical note produces correctly sequenced ICD-10 codes with full explainability — from entity extraction through RAG retrieval through KG-based CDI gap detection — all running locally on OSS models.
**Current focus:** Phase 1 complete. Ready for Phase 2 planning.

## Current Position

Phase: 1 of 3 (Core Pipeline & Test Data Foundation) — COMPLETE ✓
Plan: 7 of 7 in current phase
Status: Phase complete — verification passed (6/6)
Last activity: 2026-03-18 — Phase 1 execution complete, verification passed

Progress: [██████████] 100%

## Performance Metrics

**Velocity:**
- Total plans completed: 7
- Average duration: 4 min
- Total execution time: 0.47 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 7 | 28 min | 4 min |

**Recent Trend:**
- Last 5 plans: 5 min, 2 min, 3 min, 8 min, 2 min
- Trend: Steady pace

*Updated after each plan completion*
| Phase 01 P05 | 3 | 2 tasks | 2 files |
| Phase 01 P06 | 8 | 2 tasks | 25 files |
| Phase 01 P07 | 2 | 2 tasks | 2 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Week 1 foundation: Qwen2.5-1.5B-Instruct selected for reasoning (small enough to run locally)
- Week 1 foundation: FAISS flat index over approximate (exact retrieval for 70k codes)
- Week 1 foundation: NetworkX over Neo4j for KG (no external DB dependency)
- Week 1 foundation: SmolVLM for image ingestion (smallest viable multimodal model)
- Phase 1 now includes comprehensive test data generation (EVAL-08): synthetic FHIR bundles, PIL-generated images, gold standard labels for all modules
- 01-01: Pydantic v2 for all data schemas (runtime validation, computed properties, JSON serialization)
- 01-01: Singleton pattern for ModelManager (prevents multiple model loads, reduces memory)
- 01-01: Lazy loading for all models (downloaded/loaded only when first accessed)
- 01-03: FHIR R4B (not R5) for parsing - R4B is standard for clinical systems, avoids R5 compatibility issues
- 01-03: Confidence heuristic for image OCR based on text length (longer = better quality, clamped 0.4-0.85)
- 01-03: Removed outlines dependency - requires Rust compiler, not needed for ingestion
- [Phase 01]: Pattern-based negation detection over spaCy/negspacy for Python 3.14 compatibility
- [Phase 01]: Keep qualifiers regardless of confidence threshold for clinical context preservation
- [Phase 01]: 50-character window for qualifier attachment (balances precision/recall)
- 01-05: JSON parsing with retry instead of outlines library (avoid Rust compiler dependency)
- 01-05: Blended confidence scoring: 60% LLM + 40% reranker (balances semantic understanding with relevance)
- 01-05: Simplified code sequencing by confidence for POC (full medical coding rules deferred to production)
- 01-05: Made CodingResult.principal_diagnosis Optional for graceful edge case handling
- [Phase 01-06]: Sequential batch processing over parallel for simpler error handling
- [Phase 01-06]: 20 synthetic test cases over real clinical data (HIPAA compliance, full control over ground truth)
- [Phase 01-06]: PIL-rendered images over scanned documents (reproducible, no dependencies)
- 01-07: Pydantic model_validate() gate on test data generation to prevent schema drift

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-03-18
Stopped at: Phase 1 execution complete — all 7 plans done, verification passed 6/6
Resume file: None

---
*State initialized: 2026-03-18*
*Last updated: 2026-03-18 after completing 01-07*
*Next action: Phase 01 verified and complete. Proceed to `/gsd:plan-phase 2`.*
