---
phase: 04-demo-ui
plan: 01
subsystem: ui
tags: [streamlit, pyvis, annotated-text, plotly, networkx, theme, components]

# Dependency graph
requires:
  - phase: 02-cdi-intelligence
    provides: "PipelineResult, CDIReport, AuditTrail, run_pipeline_audited"
provides:
  - "Streamlit app shell with st.navigation and 6 grouped page stubs"
  - "7 reusable UI components (theme, metric_cards, entity_highlight, code_display, graph_embed, pipeline_status)"
  - "Custom green theme configuration (.streamlit/config.toml)"
  - "Pre-compute demo data script (scripts/precompute_demo.py)"
  - "QA bot question bank (ui/demo_data/demo_questions.json with 8 Q&A pairs)"
  - "Session state initialization pattern for cross-page data sharing"
affects: [04-02-pipeline-runner, 04-03-eval-dashboard, 04-04-kg-viewer, 04-05-audit-qa]

# Tech tracking
tech-stack:
  added: [streamlit, plotly, pyvis, st-annotated-text, networkx]
  patterns:
    - "st.navigation with st.Page for programmatic multipage routing"
    - "Session state defaults initialized before pg.run() in app.py"
    - "TYPE_CHECKING imports for heavy model types in component modules"
    - "Overlap resolution algorithm for NER entity annotation rendering"
    - "@st.cache_resource for ModelManager singleton caching"

key-files:
  created:
    - "ui/app.py"
    - "ui/pages/home.py"
    - "ui/pages/pipeline_runner.py"
    - "ui/pages/eval_dashboard.py"
    - "ui/pages/kg_viewer.py"
    - "ui/pages/audit_trail.py"
    - "ui/pages/qa_bot.py"
    - "ui/components/__init__.py"
    - "ui/components/theme.py"
    - "ui/components/metric_cards.py"
    - "ui/components/entity_highlight.py"
    - "ui/components/code_display.py"
    - "ui/components/graph_embed.py"
    - "ui/components/pipeline_status.py"
    - ".streamlit/config.toml"
    - "scripts/precompute_demo.py"
    - "ui/demo_data/demo_questions.json"
  modified:
    - "pyproject.toml"

key-decisions:
  - "Streamlit >=1.35.0 rather than >=1.55.0 for broader compatibility with st.navigation"
  - "TYPE_CHECKING guards for heavy imports (CodeSuggestion, CDIReport) to keep component module imports fast"
  - "Overlap resolution: prefer higher confidence then longer span for NER entity deduplication"
  - "1-hop neighbor expansion for KG subgraph visualization with size differentiation (case codes larger)"
  - "8 pre-seeded QA questions covering all system aspects (models, pipeline, CDI, RAG, eval, data formats, KG, audit)"

patterns-established:
  - "UI component pattern: each component in ui/components/ exports one or two render_* functions"
  - "Session state pattern: defaults in app.py, checked on dependent pages"
  - "Demo data pattern: precompute_demo.py serializes PipelineResult.model_dump_json to ui/demo_data/precomputed/"

# Metrics
duration: 6min
completed: 2026-03-18
---

# Phase 4 Plan 01: App Shell and Components Summary

**Streamlit multipage app shell with 6 navigable pages, 7 reusable components (entity highlighting, KG embedding, code cards), green theme, and pre-computed demo data infrastructure**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-18T21:29:38Z
- **Completed:** 2026-03-18T21:35:25Z
- **Tasks:** 2
- **Files modified:** 18

## Accomplishments
- Working Streamlit app shell with st.navigation routing 6 pages in 3 sidebar groups (Overview, Pipeline, Analysis)
- 7 reusable components: theme with entity/status color palettes, metric row cards, NER entity annotation with overlap resolution, ICD-10 code cards with confidence bars, PyVis KG graph embedding with CDI-based coloring, and pipeline status wrapper
- Pre-compute script for generating demo PipelineResult JSON files from 3 demo cases (2 text notes + 1 FHIR bundle)
- 8 factually accurate QA bot questions covering all ClinIQ system aspects

## Task Commits

Each task was committed atomically:

1. **Task 1: App shell, theme, navigation, and reusable components** - `c86134a` (feat)
2. **Task 2: Pre-computed demo data and QA bot question bank** - `f78e723` (feat)

## Files Created/Modified
- `ui/app.py` - Streamlit entry point with st.navigation, page config, session state init
- `ui/pages/home.py` - Landing page stub
- `ui/pages/pipeline_runner.py` - Pipeline runner page stub
- `ui/pages/eval_dashboard.py` - Eval dashboard page stub
- `ui/pages/kg_viewer.py` - KG viewer page stub
- `ui/pages/audit_trail.py` - Audit trail page stub
- `ui/pages/qa_bot.py` - QA bot page stub
- `ui/components/__init__.py` - Component barrel export
- `ui/components/theme.py` - Entity/status colors and CSS injection
- `ui/components/metric_cards.py` - Responsive metric row using st.metric
- `ui/components/entity_highlight.py` - NER annotation with overlap resolution
- `ui/components/code_display.py` - ICD-10 code cards and principal diagnosis rendering
- `ui/components/graph_embed.py` - PyVis KG subgraph generation and embedding
- `ui/components/pipeline_status.py` - Pipeline execution with st.status progress
- `.streamlit/config.toml` - Green theme (primaryColor=#2ecc71)
- `scripts/precompute_demo.py` - Demo result pre-computation script
- `ui/demo_data/demo_questions.json` - 8 pre-seeded QA bot questions with answers
- `pyproject.toml` - Added streamlit, plotly, pyvis, st-annotated-text, networkx deps

## Decisions Made
- Used streamlit>=1.35.0 minimum version instead of >=1.55.0 for broader compatibility (st.navigation was introduced in 1.36)
- TYPE_CHECKING guards used for heavy imports (CodeSuggestion, CDIReport) in component modules to keep import times fast
- Entity overlap resolution: higher confidence wins, then longer span if equal
- KG graph uses 1-hop neighbor expansion with size differentiation (case codes 25px, neighbors 15px)
- Pre-seeded 8 QA questions (exceeds 7+ requirement) covering models, pipeline, CDI, RAG, eval, formats, KG, and audit trail

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- App shell is running and navigable between all 6 pages
- All components importable and ready for use by plans 04-02 through 04-05
- Demo data infrastructure ready; run `python scripts/precompute_demo.py` when ML models are downloaded
- Session state initialized with pipeline_result, active_case_id, messages, eval_results

## Self-Check: PASSED

- All 18 files verified present on disk
- Commit c86134a (Task 1) verified in git log
- Commit f78e723 (Task 2) verified in git log

---
*Phase: 04-demo-ui*
*Completed: 2026-03-18*
