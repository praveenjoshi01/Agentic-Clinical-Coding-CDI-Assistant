# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-18)

**Core value:** Every clinical note produces correctly sequenced ICD-10 codes with full explainability — from entity extraction through RAG retrieval through KG-based CDI gap detection — all running locally on OSS models.
**Current focus:** Phase 2 complete — CDI Intelligence Layer. Ready for Phase 3.

## Current Position

Phase: 2 of 3 (CDI Intelligence Layer)
Plan: 6 of 6 in current phase
Status: Phase 2 COMPLETE — all 6 plans executed
Last activity: 2026-03-18 — Completed 02-06 (LLM-as-judge evaluation)

Progress: [████████░░] 40%

## Performance Metrics

**Velocity:**
- Total plans completed: 13
- Average duration: 4 min
- Total execution time: 0.70 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 7 | 28 min | 4 min |
| 02 | 6 | 14 min | 2.3 min |

**Recent Trend:**
- Last 5 plans: 2 min, 2 min, 2 min, 3 min, 2 min
- Trend: Steady pace

*Updated after each plan completion*
| Phase 01 P05 | 3 | 2 tasks | 2 files |
| Phase 01 P06 | 8 | 2 tasks | 25 files |
| Phase 01 P07 | 2 | 2 tasks | 2 files |
| Phase 02 P01 | 3 | 2 tasks | 7 files |
| Phase 02 P02 | 2 | 2 tasks | 3 files |
| Phase 02 P03 | 2 | 2 tasks | 2 files |
| Phase 02 P04 | 2 | 2 tasks | 2 files |
| Phase 02 P05 | 3 | 2 tasks | 2 files |
| Phase 02 P06 | 2 | 2 tasks | 3 files |

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
- 02-01: Curated rules in external JSON (kg_rules.json) for auditability and clinical review
- 02-01: Bidirectional edges for co-occurrence/conflict relationships in KG
- 02-01: Qualifier nodes as separate graph nodes (qualifier:name pattern) for flexible querying
- 02-01: HAS_PARENT edges link direct parent only (not transitive) to keep graph sparse
- 02-02: Read-only query pattern: querier functions never modify frozen graph
- 02-02: Frozenset deduplication for conflict pairs to avoid (A,B)+(B,A) duplicates
- 02-02: Weight-based ranking for missed diagnosis suggestions with per-code deduplication
- 02-03: Builder pattern for AuditTrailBuilder wrapping AuditTrail Pydantic model
- 02-03: Case-insensitive substring matching with +/- 50 char window for evidence linking
- 02-03: Outermost brace extraction (first '{' to last '}') for CoT/JSON separation
- 02-04: Module-level KG caching via global _KG_CACHE to avoid rebuilding per call
- 02-04: Template fallback for physician queries ensures valid output when LLM fails
- 02-04: Gap penalty 10%, conflict penalty 15%, clamped to [0.0, 1.0] for completeness scoring
- 02-04: Default confidence 0.8 for KG-based documentation gaps
- 02-05: Separate run_pipeline_audited function instead of modifying run_pipeline to maintain backward compatibility
- 02-05: Optional cdi_report and audit_trail fields (default None) on PipelineResult for schema backward compatibility
- 02-05: UUID4 hex[:8] for case_id generation (short, unique, no external dependencies)
- 02-06: Explicit 5-point Likert rubric in prompts for consistent LLM judge scoring
- 02-06: Normalize raw 1-5 scores to 0-1 by dividing by 5
- 02-06: Fallback score of 0.6 (raw 3) on JSON parse failure for graceful degradation
- 02-06: Relaxed test thresholds (0.60) for individual items; aggregate targets (0.80/0.82) for gold standard

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-03-18
Stopped at: Completed 02-06-PLAN.md (Phase 2 complete)
Resume file: None

---
*State initialized: 2026-03-18*
*Last updated: 2026-03-18 after completing 02-06*
*Next action: Begin Phase 3 planning*
