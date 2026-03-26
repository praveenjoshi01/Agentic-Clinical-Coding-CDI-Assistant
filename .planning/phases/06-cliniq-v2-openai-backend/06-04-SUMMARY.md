---
phase: 06-cliniq-v2-openai-backend
plan: 04
subsystem: pipeline
tags: [openai, gpt-4o, pipeline-orchestrator, llm-judge, evaluation, pydantic]

# Dependency graph
requires:
  - phase: 06-01
    provides: "cliniq_v2 package foundation (api_client, config, __init__)"
  - phase: 06-02
    provides: "RAG infrastructure (build_index, retriever) and m3_rag_coding"
  - phase: 06-03
    provides: "m4_cdi, m5_explainability, m6_ambient modules"
provides:
  - "cliniq_v2/pipeline.py orchestrator with run_pipeline, run_pipeline_audited, batch variants"
  - "cliniq_v2/evaluation/ package with GPT-4o LLM judge for CDI scoring"
  - "PipelineResult Pydantic model identical to cliniq v1"
affects: [06-05-ui-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pipeline orchestrator identical to v1 except module import paths"
    - "GPT-4o judge replaces local Qwen for evaluation scoring"
    - "Lazy import of OpenAIClient inside _generate_judge_response"

key-files:
  created:
    - cliniq_v2/pipeline.py
    - cliniq_v2/evaluation/__init__.py
    - cliniq_v2/evaluation/llm_judge.py
  modified: []

key-decisions:
  - "Re-define PipelineResult locally in cliniq_v2/pipeline.py for independent importability"
  - "GPT-4o judge with max_tokens=128 and temperature=0.1 for consistent evaluation scoring"
  - "Same prompt templates, rubrics, and aggregation logic as v1 (only model call changes)"
  - "Lazy import of OpenAIClient inside _generate_judge_response (not module-level)"

patterns-established:
  - "Pipeline API surface preservation: cliniq_v2 pipeline is a drop-in replacement for cliniq v1"
  - "Evaluation module mirrors v1 structure: identical __init__.py re-exports and function signatures"

# Metrics
duration: 3min
completed: 2026-03-26
---

# Phase 06 Plan 04: Pipeline Orchestrator + Evaluation Summary

**cliniq_v2 pipeline orchestrator wiring all 5 OpenAI-backed modules with identical API surface to v1, plus GPT-4o LLM judge for CDI quality evaluation**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-26T23:15:13Z
- **Completed:** 2026-03-26T23:18:21Z
- **Tasks:** 2
- **Files created:** 3

## Accomplishments
- Created cliniq_v2/pipeline.py orchestrator importing from cliniq_v2.modules (m1-m5) with identical function signatures and PipelineResult schema to cliniq v1
- Created cliniq_v2/evaluation/ package with GPT-4o LLM judge replacing local Qwen, retaining identical prompt templates, scoring rubrics, and aggregation logic
- All 6 verifications passed: pipeline imports, evaluation imports, module tracing, OpenAIClient usage, field compatibility, v1 unchanged

## Task Commits

Each task was committed atomically:

1. **Task 1: Create cliniq_v2/pipeline.py (orchestrator with v2 module imports)** - `e5d6cb9` (feat)
2. **Task 2: Create cliniq_v2/evaluation/ package with GPT-4o judge** - `c9f5cf0` (feat)

## Files Created/Modified
- `cliniq_v2/pipeline.py` - Pipeline orchestrator with run_pipeline, run_pipeline_audited, batch variants
- `cliniq_v2/evaluation/__init__.py` - Re-exports judge_query_relevance, judge_cot_coherence, evaluate_cdi_quality, evaluate_cot_quality
- `cliniq_v2/evaluation/llm_judge.py` - GPT-4o LLM judge with same prompts/rubrics as v1, simplified _generate_judge_response

## Decisions Made
- Re-defined PipelineResult in cliniq_v2/pipeline.py locally (allows `from cliniq_v2.pipeline import PipelineResult` without v1 dependency)
- GPT-4o judge uses max_tokens=128, temperature=0.1 for deterministic scoring (matching v1 generation constraints)
- Prompt templates and scoring rubrics kept verbatim from v1 (1-5 Likert scale, normalize to 0-1)
- Lazy import of OpenAIClient inside function body only (consistent with all cliniq_v2 module patterns)
- capture_cot_and_json imported from cliniq_v2.modules.m5_explainability (follows re-export chain)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required (API key configured at runtime via existing api_client.py).

## Next Phase Readiness
- Pipeline orchestrator ready for UI integration (plan 06-05)
- `from cliniq_v2.pipeline import run_pipeline, run_pipeline_audited` works as drop-in replacement
- Evaluation package ready for scoring with `from cliniq_v2.evaluation import evaluate_cdi_quality`
- m6_ambient.py lazy import of cliniq_v2.pipeline now satisfied (pipeline.py exists)

## Self-Check: PASSED

All 3 created files verified on disk. Both task commits (e5d6cb9, c9f5cf0) verified in git log.

---
*Phase: 06-cliniq-v2-openai-backend*
*Completed: 2026-03-26*
