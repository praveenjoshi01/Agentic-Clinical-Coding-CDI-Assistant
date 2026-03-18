"""
PyVis HTML generation and Streamlit component embedding for KG visualization.

Filters the full ICD-10 knowledge graph to a case-relevant subgraph,
colors nodes by CDI status, and embeds the interactive visualization.
CRITICAL: Never render the full KG (70k nodes). Always filter first.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import networkx as nx
import streamlit as st
import streamlit.components.v1 as components
from pyvis.network import Network

if TYPE_CHECKING:
    from cliniq.models.cdi import CDIReport


def render_kg_graph(
    G: nx.DiGraph,
    case_codes: list[str],
    cdi_report: "CDIReport | None" = None,
    height: int = 600,
) -> None:
    """Generate and embed a PyVis graph for the case-relevant KG subgraph.

    Filters to case codes + 1-hop neighbors, colors nodes by CDI status
    (red=conflict, amber=gap, green=ok), and embeds as interactive HTML.

    Args:
        G: The full ICD-10 knowledge graph (NetworkX DiGraph).
        case_codes: List of ICD-10 codes relevant to the current case.
        cdi_report: Optional CDI report for coloring gap/conflict nodes.
        height: Height in pixels for the embedded graph.
    """
    if not case_codes:
        st.info("No codes to visualize. Run the pipeline first.")
        return

    # Build set of case-relevant nodes: case codes + 1-hop neighbors
    relevant_nodes: set[str] = set(case_codes)
    for code in case_codes:
        if code in G:
            # Add predecessors and successors (1-hop neighbors)
            relevant_nodes.update(G.predecessors(code))
            relevant_nodes.update(G.successors(code))

    # Filter to only nodes that exist in the graph
    relevant_nodes = {n for n in relevant_nodes if n in G}

    if not relevant_nodes:
        st.warning("No matching nodes found in the knowledge graph.")
        return

    # Determine CDI status sets for coloring
    gap_codes: set[str] = set()
    conflict_codes: set[str] = set()
    gap_queries: dict[str, str] = {}

    if cdi_report is not None:
        gap_codes = {g.code for g in cdi_report.documentation_gaps}
        for g in cdi_report.documentation_gaps:
            gap_queries[g.code] = g.physician_query

        for c in cdi_report.code_conflicts:
            conflict_codes.add(c.code_a)
            conflict_codes.add(c.code_b)

    # Create PyVis network
    net = Network(
        height=f"{height}px",
        width="100%",
        bgcolor="#ffffff",
        font_color="#333333",
    )
    net.barnes_hut()

    # Add nodes with CDI-based coloring
    for node in relevant_nodes:
        if node in conflict_codes:
            color = "#e74c3c"  # Red = conflict
        elif node in gap_codes:
            color = "#f39c12"  # Amber = needs CDI query
        else:
            color = "#2ecc71"  # Green = well-documented

        # Node tooltip: description + optional physician query
        desc = G.nodes[node].get("description", node)
        title = f"{node}: {desc}"

        if node in gap_queries:
            title += f"\n\nPhysician Query: {gap_queries[node]}"

        # Larger nodes for case codes vs neighbors
        size = 25 if node in case_codes else 15

        net.add_node(node, label=node, title=title, color=color, size=size)

    # Add edges between case-relevant nodes
    for u, v, data in G.edges(data=True):
        if u in relevant_nodes and v in relevant_nodes:
            relation = data.get("relation", data.get("type", ""))
            net.add_edge(u, v, title=relation)

    # Generate and embed HTML
    html = net.generate_html()
    components.html(html, height=height + 20, scrolling=True)
