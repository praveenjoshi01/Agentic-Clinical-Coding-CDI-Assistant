"""
Reusable Streamlit UI components for ClinIQ demo.

Provides themed entity highlighting, ICD-10 code cards, knowledge graph
embedding, metric displays, and pipeline progress wrappers.
"""

from ui.components.theme import inject_custom_css, ENTITY_COLORS, STATUS_COLORS
from ui.components.metric_cards import render_metric_row
from ui.components.entity_highlight import render_ner_highlights
from ui.components.code_display import render_code_cards, render_principal_diagnosis
from ui.components.graph_embed import render_kg_graph
from ui.components.pipeline_status import run_pipeline_with_status

__all__ = [
    "inject_custom_css",
    "ENTITY_COLORS",
    "STATUS_COLORS",
    "render_metric_row",
    "render_ner_highlights",
    "render_code_cards",
    "render_principal_diagnosis",
    "render_kg_graph",
    "run_pipeline_with_status",
]
