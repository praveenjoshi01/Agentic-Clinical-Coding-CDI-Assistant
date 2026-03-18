"""
ICD-10 code result card rendering.

Provides a prominent principal diagnosis card and a grid of
code cards for secondary/complication codes with evidence expanders.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import streamlit as st

if TYPE_CHECKING:
    from cliniq.models.coding import CodeSuggestion


def render_principal_diagnosis(code: "CodeSuggestion | None") -> None:
    """Render a prominent card for the principal diagnosis.

    Shows code, description, confidence bar, reasoning text,
    and a needs_specificity badge when applicable.

    Args:
        code: The principal CodeSuggestion, or None if not available.
    """
    if code is None:
        st.warning("No principal diagnosis identified.")
        return

    st.subheader(f"Principal Diagnosis: {code.icd10_code}")
    st.markdown(f"**{code.description}**")

    # Confidence bar
    confidence_pct = int(code.confidence * 100)
    if code.confidence >= 0.8:
        bar_color = "#2ecc71"
    elif code.confidence >= 0.5:
        bar_color = "#f39c12"
    else:
        bar_color = "#e74c3c"

    st.markdown(
        f"""
        <div style="background:#e0e0e0; border-radius:4px; height:12px; width:100%; margin:4px 0;">
            <div style="background:{bar_color}; width:{confidence_pct}%; height:12px; border-radius:4px;"></div>
        </div>
        <span style="font-size:0.85rem;">Confidence: {code.confidence:.2f}</span>
        """,
        unsafe_allow_html=True,
    )

    # Reasoning
    if code.reasoning:
        st.markdown(f"**Reasoning:** {code.reasoning}")

    # Needs specificity badge
    if code.needs_specificity:
        st.warning("Needs more specificity -- consider a more specific code.")


def render_code_cards(codes: list["CodeSuggestion"], title: str = "Codes") -> None:
    """Render a grid of ICD-10 code cards with evidence in expanders.

    Displays 2-3 cards per row with code, description, confidence,
    and expandable evidence text.

    Args:
        codes: List of CodeSuggestion objects.
        title: Section title to display above the cards.
    """
    if not codes:
        st.info(f"No {title.lower()} identified.")
        return

    st.subheader(title)

    # Display in rows of 3
    for row_start in range(0, len(codes), 3):
        row_codes = codes[row_start : row_start + 3]
        cols = st.columns(len(row_codes))

        for col, code in zip(cols, row_codes):
            with col:
                # Code header
                st.markdown(f"**{code.icd10_code}**")
                st.caption(code.description)

                # Confidence indicator
                confidence_pct = int(code.confidence * 100)
                st.progress(code.confidence, text=f"{confidence_pct}%")

                # Needs specificity badge
                if code.needs_specificity:
                    st.caption(":warning: Needs specificity")

                # Evidence in expander
                with st.expander("Evidence & Reasoning"):
                    if code.evidence_text:
                        st.markdown(f"> {code.evidence_text}")
                    if code.reasoning:
                        st.markdown(f"**Reasoning:** {code.reasoning}")
