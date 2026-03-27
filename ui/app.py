"""
ClinIQ -- Clinical Documentation Integrity Platform UI.

Streamlit entry point with multipage navigation, session state init,
API key gate for ClinIQ v2 (OpenAI backend), and custom theming.
Run with: streamlit run ui/app.py
"""

import streamlit as st

# -- Page config MUST come before any other st.* call -----------------------
st.set_page_config(
    page_title="ClinIQ - Clinical Documentation Integrity",
    page_icon=":material/medical_services:",
    layout="wide",
)

# -- Initialize API key session state defaults early ------------------------
if "openai_api_key" not in st.session_state:
    st.session_state["openai_api_key"] = None
if "skip_api_key" not in st.session_state:
    st.session_state["skip_api_key"] = False

# -- API Key Gate -----------------------------------------------------------
# Block page rendering until the user provides an OpenAI API key or
# explicitly opts to continue with the v1 (local models) backend.

if not st.session_state.get("openai_api_key") and not st.session_state.get("skip_api_key"):
    st.title("ClinIQ v2 -- API Key Setup")
    st.markdown(
        "ClinIQ **v2** uses OpenAI models (GPT-4o, text-embedding-3-small) "
        "instead of local OSS models. Enter your OpenAI API key below to "
        "enable the v2 backend, or continue without one to use local models."
    )

    api_key_input = st.text_input(
        "OpenAI API Key",
        type="password",
        placeholder="sk-...",
    )

    col_connect, col_skip = st.columns(2)
    with col_connect:
        if st.button("Connect with OpenAI", type="primary", use_container_width=True):
            if api_key_input and api_key_input.strip():
                # Validate key via OpenAIClient
                try:
                    from cliniq_v2.api_client import OpenAIClient

                    client = OpenAIClient()
                    client.configure(api_key_input.strip())
                    if client.validate_key():
                        st.session_state["openai_api_key"] = api_key_input.strip()
                        st.rerun()
                    else:
                        st.error("Invalid API key. Please check your key and try again.")
                except Exception as exc:
                    st.error(f"Failed to validate API key: {exc}")
            else:
                st.warning("Please enter an API key first.")

    with col_skip:
        if st.button("Continue without API key", use_container_width=True):
            st.session_state["skip_api_key"] = True
            st.rerun()

    st.stop()

# -- If we have an API key, ensure OpenAIClient is configured ---------------
if st.session_state.get("openai_api_key"):
    try:
        from cliniq_v2.api_client import OpenAIClient

        client = OpenAIClient()
        # Only configure if not already configured (singleton)
        try:
            _ = client.client  # test if already configured
        except RuntimeError:
            client.configure(st.session_state["openai_api_key"])
    except ImportError:
        pass

# -- Define pages ------------------------------------------------------------
home = st.Page("pages/home.py", title="Home", icon=":material/home:", default=True)
pipeline_runner = st.Page(
    "pages/pipeline_runner.py",
    title="Pipeline Runner",
    icon=":material/play_arrow:",
)
eval_dashboard = st.Page(
    "pages/eval_dashboard.py",
    title="Evaluation",
    icon=":material/assessment:",
)
kg_viewer = st.Page(
    "pages/kg_viewer.py",
    title="Knowledge Graph",
    icon=":material/hub:",
)
audit_trail = st.Page(
    "pages/audit_trail.py",
    title="Audit Trail",
    icon=":material/fact_check:",
)
qa_bot = st.Page(
    "pages/qa_bot.py",
    title="QA Bot",
    icon=":material/chat:",
)
ambient_mode = st.Page(
    "pages/ambient_mode.py",
    title="Ambient Mode",
    icon=":material/mic:",
)

# -- Group pages in sidebar navigation --------------------------------------
pg = st.navigation(
    {
        "Overview": [home],
        "Pipeline": [pipeline_runner, kg_viewer, audit_trail],
        "Analysis": [eval_dashboard, qa_bot],
        "Ambient": [ambient_mode],
    }
)

# -- Initialize session state defaults --------------------------------------
if "pipeline_result" not in st.session_state:
    st.session_state["pipeline_result"] = None
if "active_case_id" not in st.session_state:
    st.session_state["active_case_id"] = None
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "eval_results" not in st.session_state:
    st.session_state["eval_results"] = None
if "ambient_state" not in st.session_state:
    st.session_state["ambient_state"] = "idle"
if "ambient_session_id" not in st.session_state:
    st.session_state["ambient_session_id"] = None
if "ambient_pipeline_result" not in st.session_state:
    st.session_state["ambient_pipeline_result"] = None
if "ambient_disambiguation" not in st.session_state:
    st.session_state["ambient_disambiguation"] = []

# -- Sidebar: Getting Started -----------------------------------------------
with st.sidebar.expander("Getting Started", expanded=False):
    st.markdown(
        """
1. **Start on Pipeline Runner** -- select a sample case and run the pipeline
2. **Explore KG Viewer and Audit Trail** -- drill into the knowledge graph and decision trace
3. **Check Eval Dashboard** for metrics, then ask the **QA Bot** questions
4. **Try Ambient Mode** -- select a sample encounter to see auto-generated notes with CDI analysis
"""
    )

# -- Sidebar: Session info --------------------------------------------------
st.sidebar.markdown("---")
case_id = st.session_state.get("active_case_id")
pipeline = st.session_state.get("pipeline_result")

if case_id:
    st.sidebar.markdown(f"**Active Case:** `{case_id}`")
if pipeline is not None:
    st.sidebar.success("Pipeline result loaded", icon=":material/check_circle:")
else:
    st.sidebar.caption("No pipeline result in session")

# Ambient session info
ambient_state = st.session_state.get("ambient_state", "idle")
ambient_session_id = st.session_state.get("ambient_session_id")
if ambient_state != "idle" and ambient_session_id:
    st.sidebar.markdown(f"**Ambient Session:** `{ambient_session_id}`")
    state_colors = {"recording": "red", "processing": "orange", "results": "green"}
    color = state_colors.get(ambient_state, "gray")
    st.sidebar.markdown(f"Status: :{color}[{ambient_state.upper()}]")

# -- Sidebar footer ----------------------------------------------------------
st.sidebar.markdown("---")
if st.session_state.get("openai_api_key"):
    st.sidebar.markdown("**ClinIQ v2.0.0 | OpenAI Backend**")
    st.sidebar.caption("Powered by GPT-4o")
else:
    st.sidebar.markdown("**ClinIQ v0.1.0 | Local Models**")
    st.sidebar.caption("Powered by OSS Models")

# -- Run the selected page ---------------------------------------------------
pg.run()
