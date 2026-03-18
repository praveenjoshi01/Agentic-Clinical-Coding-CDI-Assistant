"""
ClinIQ -- Clinical Documentation Integrity Demo UI.

Streamlit entry point with multipage navigation, session state init,
and custom theming. Run with: streamlit run ui/app.py
"""

import streamlit as st

# -- Page config MUST come before any other st.* call -----------------------
st.set_page_config(
    page_title="ClinIQ - Clinical Documentation Integrity",
    page_icon=":material/medical_services:",
    layout="wide",
)

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

# -- Group pages in sidebar navigation --------------------------------------
pg = st.navigation(
    {
        "Overview": [home],
        "Pipeline": [pipeline_runner, kg_viewer, audit_trail],
        "Analysis": [eval_dashboard, qa_bot],
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

# -- Sidebar footer ----------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.markdown("**ClinIQ v0.1.0**")
st.sidebar.caption("Powered by OSS Models")

# -- Run the selected page ---------------------------------------------------
pg.run()
