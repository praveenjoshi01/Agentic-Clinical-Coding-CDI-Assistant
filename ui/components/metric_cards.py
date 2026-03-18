"""
Reusable metric display using st.metric in a responsive column row.

Handles 2-6 metrics per row with optional delta indicators.
"""

from typing import Optional

import streamlit as st


def render_metric_row(
    metrics: dict[str, tuple[str, Optional[str]]],
) -> None:
    """Render a row of st.metric cards in evenly spaced columns.

    Args:
        metrics: Mapping of label -> (value, delta).
            delta can be None for no delta indicator.

    Example::

        render_metric_row({
            "Entities": ("42", "+5"),
            "Confidence": ("0.87", None),
            "Gaps": ("3", "-1"),
        })
    """
    labels = list(metrics.keys())
    n = len(labels)
    if n == 0:
        return

    cols = st.columns(min(n, 6))
    for i, label in enumerate(labels):
        value, delta = metrics[label]
        with cols[i % len(cols)]:
            st.metric(label=label, value=value, delta=delta)
