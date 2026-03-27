---
phase: 04-demo-ui
plan: 04
subsystem: ui
tags: [streamlit, plotly, scatterpolar, jaccard-matching, chat-interface, evaluation]

# Dependency graph
requires:
  - phase: 04-demo-ui
    plan: 01
    provides: "App shell, components (render_metric_row), demo_questions.json, session state init"
provides:
  - "Eval Dashboard page with Plotly radar and bar charts for 5 pipeline modules"
  - "QA Bot page with Jaccard-matched pre-seeded answers and chat persistence"
affects: [04-05-audit-qa]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Plotly Scatterpolar for multi-module radar comparison"
    - "Jaccard similarity for fuzzy question matching"
    - "Two-tier answer strategy: pre-seeded primary, LLM opt-in fallback"
    - "Session state chat persistence via st.session_state['messages']"

key-files:
  created: []
  modified:
    - "ui/pages/eval_dashboard.py"
    - "ui/pages/qa_bot.py"

key-decisions:
  - "Hardcoded demo metrics close to targets for instant display without model downloads"
  - "Primary metric per module for radar chart (Schema, F1, MRR, Query Rel, Trace Comp)"
  - "Jaccard threshold 0.3 for pre-seeded question matching (balances recall vs false positives)"
  - "Chat badges [Pre-seeded] vs [Generated] for answer source transparency"

patterns-established:
  - "Eval metrics pattern: TARGETS dict + DEMO_ACTUALS dict with session-state override"
  - "QA matching pattern: tokenize-Jaccard-threshold for lightweight fuzzy matching"

# Metrics
duration: 3min
completed: 2026-03-18
---

# Phase 4 Plan 04: Eval Dashboard and QA Bot Summary

**Plotly radar/bar evaluation dashboard with 5-module metrics and Jaccard-matched QA chat bot with 8 pre-seeded clinical questions**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-18T21:39:01Z
- **Completed:** 2026-03-18T21:42:10Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Eval Dashboard with Scatterpolar radar chart comparing actual vs target primary metrics across all 5 pipeline modules
- Per-module detail tabs with grouped bar charts, metric cards (via render_metric_row), and pass/fail badges
- QA Bot with Jaccard keyword matching against 8 pre-seeded Q&A pairs for instant verified responses
- Chat history persisted in st.session_state["messages"] with source badges and sidebar quick-question buttons

## Task Commits

Each task was committed atomically:

1. **Task 1: Eval Dashboard page with metrics and Plotly charts** - `3fc2b4f` (feat)
2. **Task 2: QA Bot page with chat interface and pre-seeded questions** - `5a93f6e` (feat)

## Files Created/Modified
- `ui/pages/eval_dashboard.py` - Full eval dashboard with radar chart, per-module bar charts, metric cards, pass/fail badges (240 lines)
- `ui/pages/qa_bot.py` - QA Bot with Jaccard matching, sidebar buttons, chat persistence, LLM toggle (198 lines)

## Decisions Made
- Hardcoded TARGETS and DEMO_ACTUALS dicts with session-state override for future live eval results
- Primary metric per module for radar chart: Schema Validation (M1), F1 (M2), MRR (M3), Query Relevance (M4), Trace Completeness (M5)
- Jaccard similarity threshold of 0.3 balances recall of valid questions against false positive matches
- Answer source badges ([Pre-seeded] / [Generated]) provide transparency about answer origin
- Pre-seeded answers render immediately without spinner; generated path shows st.spinner

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Both Analysis group pages fully functional and navigable from the app shell
- Eval Dashboard displays demo metrics by default; ready to accept live results via session_state["eval_results"]
- QA Bot matches all 8 pre-seeded questions; LLM fallback path stubbed for future RAG integration
- Ready for plan 04-05 (final polish/integration)

## Self-Check: PASSED

- ui/pages/eval_dashboard.py: FOUND (240 lines)
- ui/pages/qa_bot.py: FOUND (198 lines)
- Commit 3fc2b4f (Task 1): verified in git log
- Commit 5a93f6e (Task 2): verified in git log

---
*Phase: 04-demo-ui*
*Completed: 2026-03-18*
