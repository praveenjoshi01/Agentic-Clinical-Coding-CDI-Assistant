# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-18)

**Core value:** Every clinical note produces correctly sequenced ICD-10 codes with full explainability — from entity extraction through RAG retrieval through KG-based CDI gap detection — all running locally on OSS models.
**Current focus:** Phase 7 in progress. Optional Pinecone vector DB integration.

## Current Position

Phase: 7 of 7 (Optional Pinecone Vector DB)
Plan: 1 of 2 in current phase
Status: Executing Phase 07 — plan 01 complete
Last activity: 2026-03-27 — Completed 07-01-PLAN.md (Pinecone Retriever and Factory Wiring)

Progress: [████████████████████████░] 96%

## Performance Metrics

**Velocity:**
- Total plans completed: 27
- Average duration: 3.2 min
- Total execution time: 1.46 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 7 | 28 min | 4 min |
| 02 | 6 | 14 min | 2.3 min |
| 04 | 4 | 15 min | 3.75 min |
| 05 | 3 | 11 min | 3.7 min |
| 06 | 6 | 19 min | 3.2 min |
| 07 | 1 | 2 min | 2 min |

**Recent Trend:**
- Last 5 plans: 5 min, 3 min, 2 min, 1 min, 2 min
- Trend: Consistently fast execution

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
| Phase 04 P01 | 6 | 2 tasks | 18 files |
| Phase 04 P02 | 3 | 1 tasks | 1 files |
| Phase 04 P03 | 3 | 2 tasks | 2 files |
| Phase 04 P04 | 3 | 2 tasks | 2 files |
| Phase 05 P01 | 3 | 2 tasks | 4 files |
| Phase 05 P02 | 5 | 2 tasks | 3 files |
| Phase 05 P03 | 3 | 2 tasks | 2 files |
| Phase 06 P01 | 4 | 2 tasks | 6 files |
| Phase 06 P02 | 4 | 2 tasks | 4 files |
| Phase 06 P03 | 5 | 2 tasks | 3 files |
| Phase 06 P04 | 3 | 2 tasks | 3 files |
| Phase 06 P05 | 2 | 2 tasks | 6 files |
| Phase 06 P06 | 1 | 1 tasks | 1 files |
| Phase 07 P01 | 2 | 2 tasks | 8 files |

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
- 04-01: Streamlit >=1.35.0 for broader compatibility (st.navigation introduced in 1.36)
- 04-01: TYPE_CHECKING guards for heavy imports in component modules (keep imports fast)
- 04-01: Entity overlap resolution by confidence then span length for NER highlighting
- 04-01: 1-hop neighbor expansion with size differentiation for KG subgraph visualization
- 04-01: 8 pre-seeded QA questions covering all ClinIQ system aspects
- 04-02: Placeholder clinical note text for text_area usability guidance
- 04-02: Fallthrough from pre-computed to live pipeline execution when JSON not found
- 04-02: Entity summary as st.dataframe for built-in sorting and search
- 04-02: Color legend as inline HTML spans matching ENTITY_COLORS palette
- 04-03: Two-column (3:1) layout for KG Viewer: graph main area + CDI summary sidebar
- 04-03: Inline HTML color circles for legend (cross-platform consistent rendering)
- 04-03: 300-char truncation for evidence spans to prevent layout overflow
- 04-03: Horizontal bar chart for stage timing breakdown visualization
- 04-04: Hardcoded demo metrics close to targets for instant display without model downloads
- 04-04: Jaccard threshold 0.3 for pre-seeded question matching (balances recall vs false positives)
- 04-04: Chat badges [Pre-seeded] vs [Generated] for answer source transparency
- 04-04: Primary metric per module for radar chart (Schema, F1, MRR, Query Rel, Trace Comp)
- 05-01: Lazy whisper model loading with module-level _whisper_model cache (same pattern as _KG_CACHE)
- 05-01: Simple string-based SOAP section parsing for LLM output robustness
- 05-01: Raw transcript fallback as note text when LLM generation fails
- 05-01: DisambiguationItem confidence sourced directly from CDI report item confidence values
- 05-02: Handcrafted JSON over pipeline-generated for demo data (clinical realism)
- 05-02: SOAP note (generated_note) as pipeline input for precompute regeneration script
- 05-02: 9 disambiguation items across 2 encounters covering gap, missed_diagnosis, conflict, and ambiguity categories
- 05-03: Session state stored as dicts (not Pydantic models) for Streamlit serialization safety
- 05-03: st.fragment(run_every=1.0) for live session timer (avoids full page rerun)
- 05-03: PipelineResult reconstructed from dict only when rendering Clinical Findings tab
- 05-03: Category badge colors: gap=amber, missed_diagnosis=blue, conflict=red, ambiguity=orange
- 06-01: Singleton OpenAIClient with runtime configure() + validate_key() pattern
- 06-01: Reuse cliniq.models Pydantic schemas directly (no duplication)
- 06-01: Post-hoc offset computation for NER entities (GPT-4o returns text only, offsets computed by string search)
- 06-01: GPT-4o handles negation and qualifiers in single NER call (no separate detect_negation)
- 06-01: Separate cache directory (~/.cache/cliniq_v2/) to avoid v1 conflicts
- 06-02: OpenAI embeddings API in batches of 2048 for FAISS index building (1536d)
- 06-02: All 20 FAISS candidates sent to GPT-4o for combined reranking + selection + reasoning (eliminates cross-encoder)
- 06-02: Direct GPT-4o confidence (no blending with reranker score)
- 06-02: sequence_codes reused from cliniq v1 via import (model-agnostic, pure rule-based)
- 06-02: response_format json_object for structured output (no retry logic needed)
- 06-03: Re-export m5_explainability from cliniq (all functions model-agnostic, zero new logic needed)
- 06-03: Reuse helper functions from cliniq.modules.m4_cdi directly (pure data manipulation, no model dependency)
- 06-03: Reuse _parse_note_sections from cliniq.modules.m6_ambient (pure string parsing)
- 06-03: Set duration_seconds=0.0 for Whisper API transcription (API does not return duration)
- 06-04: PipelineResult re-defined locally in cliniq_v2/pipeline.py for independent importability
- 06-04: GPT-4o judge with max_tokens=128 and temperature=0.1 for consistent evaluation scoring
- 06-04: Same prompt templates, rubrics, and aggregation logic as v1 (only model call changes)
- 06-04: Lazy import of OpenAIClient inside _generate_judge_response (not module-level)
- 06-05: Backend selection via session state key presence (not explicit toggle)
- 06-05: TYPE_CHECKING imports preserved for IDE support; only runtime imports made dynamic
- 06-05: FAISS index check returns None (not crash) when v2 index missing
- 06-05: _get_model_manager() retained for v1 fallback (lazy import inside cached function)
- 06-06: Enhanced error handling with specific messages for invalid API key, rate limits, and missing ICD-10 data
- 06-06: KeyboardInterrupt handler for graceful cancellation of long-running index builds
- 06-06: Help epilog with usage examples for CLI discoverability
- 07-01: BaseRetriever as Protocol (structural subtyping) so FAISSRetriever needs no modification
- 07-01: Factory catches RuntimeError and ImportError to fall back to FAISS transparently
- 07-01: PineconeRetriever uses lazy index connection matching FAISS lazy-load pattern
- 07-01: Pinecone import wrapped in try/except at module level for graceful missing-package handling

### Pending Todos

None yet.

### Roadmap Evolution

- Phase 4 added: demo UI for the whole app
- Phase 5 added: Ambient Listening Mode – real-time session recording with auto-generated clinical notes, documentation gap detection, and coding disambiguation
- Phase 6 added: ClinIQ v2 OpenAI backend – replace all local OSS models with OpenAI API calls
- Phase 7 added: Optional Pinecone vector DB instead of FAISS when API key provided

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-03-27
Stopped at: Completed 07-01-PLAN.md (Pinecone Retriever and Factory Wiring)
Resume file: None

---
*State initialized: 2026-03-18*
*Last updated: 2026-03-27 after completing 07-01*
*Next action: Execute 07-02-PLAN.md (tests and population script)*
