"""
Backend selector helpers for dynamic cliniq / cliniq_v2 module switching.

Uses Streamlit session state to determine which backend to use:
- If ``openai_api_key`` is set in session state -> cliniq_v2 (OpenAI backend)
- Otherwise -> cliniq (local OSS models)
"""

import streamlit as st


def is_v2_backend() -> bool:
    """Check if v2 backend is active (API key configured)."""
    return bool(st.session_state.get("openai_api_key"))


def is_pinecone_backend() -> bool:
    """Check if Pinecone vector DB is active (API key configured)."""
    return bool(st.session_state.get("pinecone_api_key"))


def get_pipeline_module():
    """Return the appropriate pipeline module (cliniq or cliniq_v2)."""
    if is_v2_backend():
        from cliniq_v2 import pipeline
        return pipeline
    from cliniq import pipeline
    return pipeline


def get_ambient_module():
    """Return the appropriate ambient module (cliniq or cliniq_v2)."""
    if is_v2_backend():
        from cliniq_v2.modules import m6_ambient
        return m6_ambient
    from cliniq.modules import m6_ambient
    return m6_ambient
