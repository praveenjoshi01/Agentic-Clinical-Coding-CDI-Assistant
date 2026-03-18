"""
Custom CSS injection and theming constants for ClinIQ UI.

Provides entity color palette, status colors, and minor CSS tweaks.
Does NOT target auto-generated Streamlit class names.
"""

import streamlit as st

# Entity type color palette for NER highlighting
ENTITY_COLORS: dict[str, str] = {
    "diagnosis": "#ff6b6b",
    "procedure": "#4ecdc4",
    "medication": "#45b7d1",
    "anatomical_site": "#96ceb4",
    "qualifier": "#ffd93d",
    "lab_value": "#c9b1ff",
}

# Status colors for CDI indicators
STATUS_COLORS: dict[str, str] = {
    "green": "#2ecc71",
    "amber": "#f39c12",
    "red": "#e74c3c",
}


def inject_custom_css() -> None:
    """Inject minor CSS tweaks for entity annotations and layout spacing.

    Only targets stable HTML patterns (annotated-text spans, data attributes).
    Never targets auto-generated Streamlit class names.
    """
    st.markdown(
        """
        <style>
        /* Entity annotation padding and border radius */
        span[data-testid="stAnnotatedTextContent"] {
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 500;
        }

        /* Slightly tighter spacing for expander sections */
        details[data-testid="stExpander"] summary {
            font-size: 0.95rem;
        }

        /* Code card styling */
        .code-card {
            padding: 0.75rem;
            border-radius: 8px;
            border: 1px solid #e0e0e0;
            margin-bottom: 0.5rem;
        }

        /* Confidence bar styling */
        .confidence-bar {
            height: 8px;
            border-radius: 4px;
            background: linear-gradient(90deg, #2ecc71, #f39c12, #e74c3c);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
