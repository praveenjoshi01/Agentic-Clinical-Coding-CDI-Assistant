# Phase 4: Demo UI for the Whole App - Research

**Researched:** 2026-03-18
**Domain:** Streamlit multipage application, demo UX, clinical pipeline visualization
**Confidence:** HIGH

## Summary

Phase 4 builds the complete Streamlit demo UI that showcases the entire ClinIQ pipeline end-to-end. Phase 3 was originally planned to include a 5-page Streamlit app (Pipeline Runner, Eval Dashboard, KG Viewer, Audit Trail, QA Bot) plus PyVis KG visualization and an automated evaluation suite. Since Phase 4 was added AFTER the original roadmap as "demo UI for the whole app," its purpose is to deliver the actual implementation of that full UI system -- the 5 core pages, the PyVis embedding, the QA Bot, plus a polished landing page and "interview-ready" demo experience with pre-computed results.

The existing codebase has all backend modules (M1-M5) implemented with Pydantic schemas, a pipeline orchestrator (`run_pipeline_audited`), KG builder/querier, LLM-as-judge evaluation, and a CLI demo script. There is NO `ui/` directory yet -- no Streamlit code exists. The entire UI needs to be built from scratch, but the backend API surface (PipelineResult, CDIReport, AuditTrail, NLUResult, CodingResult) is well-defined and stable.

Streamlit 1.55.0 (March 2026) provides all necessary features: `st.navigation` with `st.Page` for programmatic multipage apps, `st.status` for pipeline progress visualization, `st.chat_message`/`st.chat_input` for the QA Bot, `st.components.v1.html` for PyVis graph embedding, `st.plotly_chart` for evaluation dashboards, `st.dialog` for modal overlays, and comprehensive theming/CSS customization. The `st-annotated-text` library (v4.0.2) handles NER entity highlighting in clinical text.

**Primary recommendation:** Build a 7-page Streamlit app using `st.navigation` with grouped sections: a Landing/Home page as the entry point, the 5 functional pages (Pipeline Runner, Eval Dashboard, KG Viewer, Audit Trail, QA Bot), and a pre-computed "Demo Showcase" page with cached results for instant interview demos. Use `st.cache_resource` for ML model loading, `st.session_state` for cross-page pipeline results, and JSON-serialized pre-computed results for zero-startup-delay demos.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| streamlit | >=1.55.0 | Multipage demo UI framework | Already decided; latest stable has st.navigation, st.status, st.dialog |
| plotly | >=5.20.0 | Interactive evaluation charts (radar, bar, metric) | Spec requirement; native st.plotly_chart integration |
| pyvis | >=0.3.2 | Interactive KG HTML visualization | Spec requirement; generates standalone HTML for embedding |
| networkx | >=3.3 | Graph operations for KG subgraph extraction | Already in codebase; needed for case-specific subgraphs |
| st-annotated-text | >=4.0.2 | NER entity highlighting in clinical text | Best Streamlit component for inline entity annotation |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| streamlit-extras | latest | style_metric_cards() for polished metric display | Optional polish for evaluation dashboard cards |
| Pillow | >=10.0.0 | Image handling for uploaded scanned notes | Already in dependencies; needed for image upload preview |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| st-annotated-text | spacy-streamlit visualize_ner | spacy-streamlit has heavier deps and less customization; st-annotated-text is lighter and works with any NER output |
| pyvis embedded HTML | streamlit-visgraph component | visgraph is React-based with richer interaction, but pyvis is already in the spec and codebase |
| plotly radar chart | matplotlib radar | Plotly has native Streamlit integration, interactivity, and theming; matplotlib requires st.pyplot which is static |

**Installation:**
```bash
pip install "streamlit>=1.55.0" "plotly>=5.20.0" "pyvis>=0.3.2" "st-annotated-text>=4.0.2"
```

## Architecture Patterns

### Recommended Project Structure
```
ui/
    app.py                    # Streamlit entry point: st.navigation + common frame
    pages/
        home.py               # Landing page with project overview + quick-start links
        pipeline_runner.py    # Upload + run pipeline + show per-stage results (UI-01)
        eval_dashboard.py     # Run/view eval suite + Plotly charts (UI-02)
        kg_viewer.py          # Embedded PyVis graph with case subgraph (UI-03)
        audit_trail.py        # Expandable per-decision trace (UI-04)
        qa_bot.py             # Chat interface with Qwen RAG (UI-05)
    components/
        __init__.py
        metric_cards.py       # Reusable metric/KPI card displays
        entity_highlight.py   # NER entity annotation rendering
        code_display.py       # ICD-10 code result cards with evidence
        graph_embed.py        # PyVis HTML generation + embedding
        pipeline_status.py    # st.status wrapper for pipeline progress
        theme.py              # Custom CSS and theming constants
    demo_data/
        precomputed/          # JSON-serialized PipelineResult for demo cases
            case_004.json     # CKD + Hypertension demo
            case_010.json     # CHF + AFib demo
        demo_questions.json   # Pre-seeded QA bot questions and expected answers
```

### Pattern 1: Programmatic Navigation with st.navigation
**What:** Use `st.navigation` with `st.Page` to define pages from Python functions, enabling grouped sidebar navigation, custom icons, and a default landing page.
**When to use:** Always -- this is the modern Streamlit multipage pattern replacing the `pages/` directory convention.
**Example:**
```python
# Source: https://docs.streamlit.io/develop/concepts/multipage-apps/page-and-navigation
import streamlit as st

# Define pages
home = st.Page("pages/home.py", title="Home", icon=":material/home:", default=True)
pipeline = st.Page("pages/pipeline_runner.py", title="Pipeline Runner", icon=":material/play_arrow:")
evaluation = st.Page("pages/eval_dashboard.py", title="Evaluation", icon=":material/assessment:")
kg_viewer = st.Page("pages/kg_viewer.py", title="Knowledge Graph", icon=":material/hub:")
audit = st.Page("pages/audit_trail.py", title="Audit Trail", icon=":material/fact_check:")
qa_bot = st.Page("pages/qa_bot.py", title="QA Bot", icon=":material/chat:")

# Group pages in sidebar
pg = st.navigation({
    "Overview": [home],
    "Pipeline": [pipeline, kg_viewer, audit],
    "Analysis": [evaluation, qa_bot],
})

st.set_page_config(
    page_title="ClinIQ - Clinical Documentation Integrity",
    page_icon=":material/medical_services:",
    layout="wide",
)

# Common sidebar elements
st.sidebar.image("ui/assets/logo.png", width=200)  # or text-based logo
st.sidebar.markdown("---")

pg.run()
```

### Pattern 2: Pipeline Progress with st.status
**What:** Use `st.status` container to show real-time pipeline execution with expandable stage details, replacing simple progress bars.
**When to use:** On the Pipeline Runner page when user clicks "Run Pipeline."
**Example:**
```python
# Source: https://docs.streamlit.io/develop/api-reference/status
import streamlit as st

with st.status("Running ClinIQ Pipeline...", expanded=True) as status:
    st.write("Stage 1: Ingesting document...")
    document = ingest(input_data)
    st.write(f"Ingested {document.metadata.source_type} document ({len(document.raw_narrative)} chars)")

    st.write("Stage 2: Extracting clinical entities...")
    nlu_result = extract_entities(document.raw_narrative)
    st.write(f"Found {nlu_result.entity_count} entities ({len(nlu_result.diagnoses)} diagnoses)")

    st.write("Stage 3: RAG-based ICD-10 coding...")
    coding_result = code_entities(nlu_result, clinical_context=document.raw_narrative)
    st.write(f"Principal: {coding_result.principal_diagnosis.icd10_code}")

    st.write("Stage 4: CDI analysis...")
    # ... CDI stage

    status.update(label="Pipeline complete!", state="complete", expanded=False)
```

### Pattern 3: Pre-computed Demo Results for Instant Startup
**What:** Serialize PipelineResult objects to JSON files during a pre-computation step. On the demo page, load these instantly instead of running the full pipeline (which takes minutes on CPU).
**When to use:** For the "Demo Showcase" / landing page and for interview scenarios where startup latency is unacceptable.
**Example:**
```python
import json
import streamlit as st
from pathlib import Path
from cliniq.pipeline import PipelineResult

DEMO_DIR = Path("ui/demo_data/precomputed")

@st.cache_data
def load_demo_result(case_id: str) -> dict:
    """Load pre-computed pipeline result from JSON."""
    path = DEMO_DIR / f"{case_id}.json"
    return json.loads(path.read_text())

# In the UI:
demo_case = st.selectbox("Select demo case", ["case_004", "case_010"])
result_dict = load_demo_result(demo_case)
result = PipelineResult.model_validate(result_dict)
# Render result immediately -- no pipeline execution needed
```

### Pattern 4: Session State for Cross-Page Data Sharing
**What:** Store PipelineResult in `st.session_state` so all pages can access the same results without re-running the pipeline.
**When to use:** After pipeline execution on Pipeline Runner page; other pages (KG Viewer, Audit Trail) read from session state.
**Example:**
```python
# Source: https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state

# On Pipeline Runner page -- after pipeline completes:
st.session_state["pipeline_result"] = result
st.session_state["active_case_id"] = case_id

# On KG Viewer page -- read shared state:
if "pipeline_result" not in st.session_state:
    st.warning("Run the pipeline first on the Pipeline Runner page.")
    st.page_link("pages/pipeline_runner.py", label="Go to Pipeline Runner")
    st.stop()

result = st.session_state["pipeline_result"]
# Render KG for this result's codes
```

### Pattern 5: NER Entity Highlighting with st-annotated-text
**What:** Convert NLUResult entities into annotated text tuples for visual entity highlighting.
**When to use:** On Pipeline Runner page to show NER results overlaid on the clinical narrative.
**Example:**
```python
# Source: https://github.com/tvst/st-annotated-text
from annotated_text import annotated_text

ENTITY_COLORS = {
    "diagnosis": "#ff6b6b",
    "procedure": "#4ecdc4",
    "medication": "#45b7d1",
    "anatomical_site": "#96ceb4",
    "qualifier": "#ffd93d",
    "lab_value": "#c9b1ff",
}

def render_ner_highlights(narrative: str, entities: list) -> None:
    """Render clinical text with color-coded NER entity annotations."""
    # Sort entities by start position
    sorted_entities = sorted(entities, key=lambda e: e.start_char)
    parts = []
    last_end = 0

    for entity in sorted_entities:
        # Add plain text before this entity
        if entity.start_char > last_end:
            parts.append(narrative[last_end:entity.start_char])

        # Add annotated entity
        color = ENTITY_COLORS.get(entity.entity_type, "#ddd")
        label = entity.entity_type.upper()
        if entity.negated:
            label = f"NEG {label}"
        parts.append((entity.text, label, color))
        last_end = entity.end_char

    # Add remaining text
    if last_end < len(narrative):
        parts.append(narrative[last_end:])

    annotated_text(*parts)
```

### Pattern 6: PyVis Graph Embedding
**What:** Generate PyVis HTML for the case-specific KG subgraph and embed it using `st.components.v1.html`.
**When to use:** On the KG Viewer page.
**Example:**
```python
import streamlit.components.v1 as components
from pyvis.network import Network

def render_kg_graph(G, case_codes, cdi_report):
    """Generate and embed a PyVis graph for the case subgraph."""
    net = Network(height="600px", width="100%", bgcolor="#ffffff", font_color="#333")
    net.barnes_hut()

    # Color mapping based on CDI status
    gap_codes = {g.code for g in cdi_report.documentation_gaps}
    conflict_codes = set()
    for c in cdi_report.code_conflicts:
        conflict_codes.update([c.code_a, c.code_b])

    for code in case_codes:
        if code in conflict_codes:
            color = "#e74c3c"  # red = conflict
        elif code in gap_codes:
            color = "#f39c12"  # amber = needs CDI query
        else:
            color = "#2ecc71"  # green = well-documented

        desc = G.nodes.get(code, {}).get("description", code)
        net.add_node(code, label=code, title=desc, color=color)

    # Add edges between case-relevant nodes
    for u, v, data in G.edges(data=True):
        if u in case_codes and v in case_codes:
            net.add_edge(u, v, title=data.get("relation", ""))

    html = net.generate_html()
    components.html(html, height=620, scrolling=True)
```

### Pattern 7: Chat Interface for QA Bot
**What:** Use `st.chat_message` and `st.chat_input` with session state history for the interview QA bot.
**When to use:** On the QA Bot page.
**Example:**
```python
# Source: https://docs.streamlit.io/develop/tutorials/chat-and-llm-apps/build-conversational-apps
import streamlit as st

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Ask me anything about the ClinIQ system!"}
    ]

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Pre-seeded question buttons for demo reliability
st.sidebar.markdown("### Quick Questions")
for q in DEMO_QUESTIONS:
    if st.sidebar.button(q, key=f"q_{hash(q)}"):
        st.session_state.pending_question = q
        st.rerun()

# Accept user input
prompt = st.chat_input("Ask about the pipeline, architecture, or clinical coding...")
if prompt or st.session_state.get("pending_question"):
    question = prompt or st.session_state.pop("pending_question")
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    # Generate response via RAG over project docs
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = qa_generate_response(question)
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
```

### Anti-Patterns to Avoid
- **Running pipeline on every rerun:** NEVER call `run_pipeline_audited()` outside a button callback or cached function. Streamlit reruns the entire page on every interaction. Always guard pipeline execution behind `st.button` or load from session state.
- **Nested columns deeper than one level:** Streamlit explicitly warns against deep column nesting. Use flat layouts with `st.columns` at the top level only.
- **Loading ML models without caching:** NEVER load transformers/sentence-transformers models without `@st.cache_resource`. First-load takes minutes; subsequent loads should be instant.
- **Embedding PyVis via file path:** Do NOT write HTML to temp files and use `st.components.v1.iframe()` with file paths. Use `net.generate_html()` and pass the HTML string to `st.components.v1.html()` directly.
- **Blocking the main thread with long operations:** Pipeline execution (especially RAG coding with LLM) takes 10-20 minutes on CPU. Always show progress feedback and consider offering pre-computed results as the default.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| NER entity highlighting | Custom HTML spans with st.markdown(unsafe_allow_html) | st-annotated-text `annotated_text()` | Handles overlapping entities, proper escaping, consistent styling |
| Metric display cards | Custom CSS card components | `st.metric` with `border=True` + `st.columns` | Native Streamlit, responsive, delta arrows, consistent theme |
| Interactive KG graph | Custom D3.js or canvas rendering | PyVis `Network.generate_html()` + `st.components.v1.html()` | Physics simulation, drag/zoom/click built-in, color/shape API |
| Radar chart for eval metrics | matplotlib polar plot | `plotly.graph_objects.Scatterpolar` + `st.plotly_chart()` | Interactive, themed, hover tooltips, native Streamlit integration |
| Chat message history | Custom div-based chat UI | `st.chat_message` + `st.chat_input` + `st.session_state` | Native Streamlit chat elements, auto-scroll, avatar support |
| Page navigation | Manual sidebar links | `st.navigation` + `st.Page` | Programmatic page definition, grouping, icons, dynamic pages |
| Progress visualization | Custom HTML progress bars | `st.status` container with expandable details | Native, shows intermediate outputs, state management |

**Key insight:** Streamlit 1.55+ has native components for every major UI need in this project. Custom HTML/CSS should only be used for minor polish (entity colors, spacing), never for core interaction patterns.

## Common Pitfalls

### Pitfall 1: Session State Lost on Page Switch
**What goes wrong:** Pipeline results disappear when navigating between pages because data was stored in local variables instead of `st.session_state`.
**Why it happens:** Streamlit re-executes the entire page script on every navigation. Local variables are reset.
**How to avoid:** Store ALL cross-page data in `st.session_state`. Initialize with defaults at the top of `app.py` before `pg.run()`. Check for required state on dependent pages and show `st.page_link` redirects.
**Warning signs:** "Run the pipeline first" messages appearing after page navigation even though the pipeline was already run.

### Pitfall 2: Model Loading Blocks Every Page Rerun
**What goes wrong:** Transformers model loading (5-30 seconds) happens on every page rerun, making the UI unusable.
**Why it happens:** Models loaded in a function without `@st.cache_resource` are re-loaded on every Streamlit rerun cycle.
**How to avoid:** Use `@st.cache_resource` for ALL model loading. The existing `ModelManager` class should be wrapped with a cached factory function. Models are loaded once per server session, not per page rerun.
**Warning signs:** Multi-second delays on every click/interaction.

### Pitfall 3: Pipeline Execution Timeout / Unresponsive UI
**What goes wrong:** Running the full pipeline (especially RAG coding with Qwen reasoning on CPU) takes 10-20 minutes, during which the Streamlit UI appears frozen.
**Why it happens:** Streamlit is single-threaded. Long-running operations block the event loop.
**How to avoid:** (1) Use `st.status` with per-stage updates so users see progress. (2) Offer pre-computed demo results as the default path. (3) Add a `--quick` mode toggle that skips LLM reasoning (template-based CDI queries). (4) Cache results per case_id in session state so re-viewing doesn't re-run.
**Warning signs:** User seeing a blank page or spinner for minutes with no feedback.

### Pitfall 4: PyVis HTML Too Large for st.components.v1.html
**What goes wrong:** The full ICD-10 KG has ~70,000 nodes. Generating PyVis HTML for the full graph crashes the browser or exceeds Streamlit component size limits.
**Why it happens:** PyVis generates JavaScript that creates all nodes/edges in the DOM. 70k nodes means megabytes of HTML.
**How to avoid:** ALWAYS filter to case-relevant subgraph before rendering. The spec explicitly requires "only case-relevant subgraph (not all 70k codes)" (VIZ-04). Extract only codes in CodingResult + CDIReport + their 1-hop KG neighbors.
**Warning signs:** KG Viewer page takes >10 seconds to render or shows a blank iframe.

### Pitfall 5: annotated_text Fails with Overlapping Entities
**What goes wrong:** NER can produce overlapping entity spans (e.g., "acute renal failure" matched as both "acute" qualifier and "renal failure" diagnosis). Overlapping spans cause incorrect text rendering.
**Why it happens:** The entity sorting algorithm doesn't handle overlaps.
**How to avoid:** Pre-process entities to resolve overlaps before passing to `annotated_text()`. Strategy: prefer longer spans; if two entities overlap, keep the one with higher confidence; or merge overlapping spans into a single annotation with combined labels.
**Warning signs:** Garbled or duplicated text in the NER highlight display.

### Pitfall 6: QA Bot Generates Hallucinated Answers
**What goes wrong:** Qwen2.5-1.5B generates plausible-sounding but incorrect answers about the system, especially for edge-case questions.
**Why it happens:** Small LLMs hallucinate when they lack grounding context.
**How to avoid:** (1) Implement RAG over project docs (CLINIQ_SPEC.md, README.md, docstrings) so the QA bot has grounding context. (2) Pre-seed 7+ standard interview questions with verified answers that are injected as few-shot examples. (3) Add a confidence indicator and "I don't have enough information" fallback.
**Warning signs:** Bot gives technically incorrect answers about the architecture, model names, or evaluation metrics.

### Pitfall 7: Custom CSS Breaks on Streamlit Updates
**What goes wrong:** Injected CSS targeting internal Streamlit class names (e.g., `.stMarkdown`, `.css-1629p8f`) breaks when Streamlit updates its internal DOM structure.
**Why it happens:** Streamlit's internal CSS class names are auto-generated and not part of the public API.
**How to avoid:** Use Streamlit's official theming system (`.streamlit/config.toml` or `st.set_page_config`) for colors, fonts, and roundness. Only use custom CSS for minor adjustments (entity annotation colors, specific padding). Never target auto-generated class names.
**Warning signs:** UI looks broken after a pip upgrade of Streamlit.

## Code Examples

Verified patterns from official sources:

### Evaluation Radar Chart with Plotly
```python
# Source: https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart
import plotly.graph_objects as go
import streamlit as st

def render_eval_radar(metrics: dict[str, float], title: str = "Module Evaluation"):
    """Render a radar chart of evaluation metrics."""
    categories = list(metrics.keys())
    values = list(metrics.values())
    # Close the radar polygon
    categories.append(categories[0])
    values.append(values[0])

    fig = go.Figure(data=[go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        name='Score',
        line_color='#2ecc71',
    )])

    fig.add_trace(go.Scatterpolar(
        r=[0.80] * len(categories),
        theta=categories,
        fill='toself',
        name='Target',
        line_color='#e74c3c',
        opacity=0.3,
    ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        showlegend=True,
        title=title,
    )
    st.plotly_chart(fig, use_container_width=True)
```

### Pipeline Runner Page Layout
```python
import streamlit as st
from pathlib import Path

st.title("Pipeline Runner")
st.markdown("Upload a clinical document to run the full ClinIQ pipeline.")

# Input section
col1, col2 = st.columns([2, 1])
with col1:
    input_type = st.radio("Input type", ["Text Note", "FHIR Bundle (JSON)", "Scanned Image"], horizontal=True)

with col2:
    use_precomputed = st.toggle("Use pre-computed results", value=True,
                                 help="Load cached results instantly instead of running the pipeline")

if input_type == "Text Note":
    uploaded = st.text_area("Paste clinical note", height=200)
elif input_type == "FHIR Bundle (JSON)":
    uploaded = st.file_uploader("Upload FHIR JSON", type=["json"])
else:
    uploaded = st.file_uploader("Upload scanned note", type=["png", "jpg", "jpeg"])

# Demo case selector
st.markdown("**Or select a demo case:**")
demo_cases = {
    "Case 004: CKD + Hypertension (68M)": "case_004",
    "Case 010: CHF + AFib (75M)": "case_010",
}
selected_demo = st.selectbox("Demo cases", ["(none)"] + list(demo_cases.keys()))

if st.button("Run Pipeline", type="primary", use_container_width=True):
    # Execute pipeline or load precomputed
    pass
```

### Theming Configuration (.streamlit/config.toml)
```toml
# Source: https://docs.streamlit.io/develop/concepts/configuration/theming
[theme]
primaryColor = "#2ecc71"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#1a1a2e"
font = "sans serif"
```

### Audit Trail Expandable Display
```python
import streamlit as st
from cliniq.models.audit import AuditTrail

def render_audit_trail(trail: AuditTrail):
    """Render the audit trail as expandable stage cards."""
    st.subheader(f"Audit Trail: Case {trail.case_id}")
    st.caption(f"Timestamp: {trail.timestamp.isoformat()}")

    for trace in trail.stages:
        icon = {"ingestion": "1", "ner": "2", "rag": "3", "cdi": "4"}.get(trace.stage, "?")
        with st.expander(
            f"Stage {icon}: {trace.stage.upper()} ({trace.processing_time_ms:.1f}ms)",
            expanded=False
        ):
            col1, col2 = st.columns(2)
            col1.metric("Input", trace.input_summary)
            col2.metric("Output", trace.output_summary)

            if trace.cot_traces:
                st.markdown("**Chain-of-Thought:**")
                for cot in trace.cot_traces:
                    st.code(cot, language="text")

            if trace.retrieval_logs:
                st.markdown("**Retrieval Logs:**")
                for log in trace.retrieval_logs:
                    st.json({
                        "query": log.query,
                        "selected": log.selected_code,
                        "confidence": log.selected_confidence,
                    })

    # Evidence spans
    if trail.evidence_spans:
        with st.expander("Evidence Spans", expanded=False):
            for code, spans in trail.evidence_spans.items():
                st.markdown(f"**{code}:** {len(spans)} supporting span(s)")
                for span in spans:
                    st.markdown(f"> {span[:200]}...")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `pages/` directory convention | `st.navigation` + `st.Page` programmatic API | Streamlit 1.36 (2024) | Dynamic pages, grouping, icons, role-based access |
| `st.cache` (deprecated) | `st.cache_data` + `st.cache_resource` | Streamlit 1.18 (2023) | Separate data vs resource caching, clearer semantics |
| `st.experimental_rerun` | `st.rerun` | Streamlit 1.27 (2023) | Stable API for triggering reruns |
| Custom progress tracking | `st.status` container | Streamlit 1.29 (2023) | Built-in expandable progress with state management |
| Third-party chat components | `st.chat_message` + `st.chat_input` | Streamlit 1.26 (2023) | Native chat UI, avatar support, streaming |
| `unsafe_allow_html` for styling | `st.html` + official theming | Streamlit 1.33+ (2024) | Safer HTML injection, comprehensive theme config |
| Manual modal overlays | `@st.dialog` decorator | Streamlit 1.35 (2024) | Native modal with session state integration |

**Deprecated/outdated:**
- `st.cache`: Replaced by `st.cache_data` and `st.cache_resource`. Do not use.
- `pages/` directory auto-detection: Still works but superseded by `st.navigation` for programmatic control. `st.navigation` disables `pages/` directory once activated.
- `st.experimental_get_query_params` / `st.experimental_set_query_params`: Removed in Streamlit 1.54.0 (Feb 2026). Use `st.query_params` instead.

## Open Questions

1. **Pipeline execution time on demo hardware**
   - What we know: CPU inference with Qwen2.5-1.5B takes 10-20 minutes per case based on CLI demo script
   - What's unclear: Exact time on the target demo machine; whether GPU is available
   - Recommendation: Always provide pre-computed results as the default demo path. Support live execution as a secondary option with clear time estimates shown in the UI.

2. **QA Bot RAG index scope**
   - What we know: Spec says "RAG over project docs" for the QA Bot
   - What's unclear: Whether to index just CLINIQ_SPEC.md and README.md, or also docstrings from all modules, or the codebase itself
   - Recommendation: Index CLINIQ_SPEC.md + README.md + a curated FAQ document with the 7 pre-seeded questions and ideal answers. Keep the index small for fast retrieval with the small embedding model.

3. **How many pre-computed demo cases to include**
   - What we know: CLI demo uses 2 cases (case_004, case_010). Gold standard has 20 cases total across 3 modalities.
   - What's unclear: Whether to pre-compute all 20 or a representative subset
   - Recommendation: Pre-compute 3-5 representative cases covering all 3 input modalities (1 FHIR, 2 text notes, 1-2 images). This demonstrates breadth without excessive storage. Include the 2 existing CLI demo cases plus at least 1 FHIR and 1 image case.

4. **Whether to use streamlit-extras or stick to core Streamlit**
   - What we know: streamlit-extras provides `style_metric_cards()` and other polish features
   - What's unclear: Whether it's actively maintained and compatible with Streamlit 1.55.0
   - Recommendation: Start with core Streamlit only. Add streamlit-extras only if specific polish features (metric card styling) prove necessary and it's confirmed compatible. The core Streamlit API in 1.55.0 is comprehensive enough.

## Sources

### Primary (HIGH confidence)
- Streamlit 1.55.0 release notes (2026): https://docs.streamlit.io/develop/quick-reference/release-notes/2026
- Streamlit 2025 release notes: https://docs.streamlit.io/develop/quick-reference/release-notes/2025
- st.navigation API reference: https://docs.streamlit.io/develop/api-reference/navigation/st.navigation
- st.Page and st.navigation concepts: https://docs.streamlit.io/develop/concepts/multipage-apps/page-and-navigation
- st.plotly_chart API: https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart
- st.status API: https://docs.streamlit.io/develop/api-reference/status
- st.session_state API: https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state
- st.cache_resource API: https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_resource
- Streamlit theming configuration: https://docs.streamlit.io/develop/concepts/configuration/theming
- Streamlit chat elements: https://docs.streamlit.io/develop/api-reference/chat
- st.dialog API: https://docs.streamlit.io/develop/api-reference/execution-flow/st.dialog
- st-annotated-text v4.0.2: https://github.com/tvst/st-annotated-text
- PyVis-Streamlit integration: https://github.com/kennethleungty/Pyvis-Network-Graph-Streamlit

### Secondary (MEDIUM confidence)
- Streamlit layout best practices: https://medium.com/data-science-collective/wait-this-was-built-in-streamlit-10-best-streamlit-design-tips-for-dashboards-2b0f50067622
- Streamlit healthcare applications: https://discuss.streamlit.io/t/healthcare-applications-examples/5941
- Plotly radar charts: https://towardsdatascience.com/creating-interactive-radar-charts-with-python-2856d06535f6/

### Tertiary (LOW confidence)
- streamlit-extras metric cards: https://arnaudmiribel.github.io/streamlit-extras/extras/metric_cards/ (compatibility with 1.55.0 unverified)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries verified via official docs and release notes; versions confirmed
- Architecture: HIGH - Patterns drawn from official Streamlit documentation and verified API references
- Pitfalls: HIGH - Based on known Streamlit execution model (rerun-on-every-interaction), verified caching semantics, and actual codebase analysis showing long pipeline execution times
- Code examples: MEDIUM-HIGH - Patterns are from official docs but adapted to ClinIQ's specific data models; the actual integration may need minor adjustments

**Research date:** 2026-03-18
**Valid until:** 2026-04-18 (30 days; Streamlit is stable, minor releases only)
