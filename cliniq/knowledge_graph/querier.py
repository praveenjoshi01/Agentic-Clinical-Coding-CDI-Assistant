"""
Knowledge graph query functions for CDI analysis.

Provides read-only query functions that interrogate the static CDI knowledge
graph to find documentation gaps, code conflicts, and missed diagnoses.
These functions NEVER modify the graph.
"""

from __future__ import annotations

import networkx as nx

from cliniq.knowledge_graph.schema import (
    COMMONLY_CO_CODED,
    CONFLICTS_WITH,
    REQUIRES_QUALIFIER,
)


def find_documentation_gaps(
    G: nx.DiGraph,
    case_codes: list[str],
    entity_qualifiers: dict[str, list[str]],
) -> list[dict]:
    """
    Find missing documentation qualifiers for case codes (CDI-01).

    For each code in case_codes, checks REQUIRES_QUALIFIER edges in the KG
    and compares required qualifiers against documented qualifiers from NER.

    Args:
        G: The frozen CDI knowledge graph.
        case_codes: List of ICD-10 codes assigned to the case.
        entity_qualifiers: Mapping of code -> list of documented qualifier names.

    Returns:
        List of gap dicts with keys: code, missing_qualifier, description.
    """
    gaps: list[dict] = []

    for code in case_codes:
        if not G.has_node(code):
            continue

        # Find all REQUIRES_QUALIFIER out-edges from this code
        documented = set(entity_qualifiers.get(code, []))

        for _, target, data in G.out_edges(code, data=True):
            if data.get("relation") != REQUIRES_QUALIFIER:
                continue

            # Target is "qualifier:name" -- extract the qualifier name
            qualifier_name = target.removeprefix("qualifier:")

            if qualifier_name not in documented:
                gaps.append(
                    {
                        "code": code,
                        "missing_qualifier": qualifier_name,
                        "description": G.nodes[code].get("description", ""),
                    }
                )

    return gaps


def find_code_conflicts(
    G: nx.DiGraph,
    case_codes: list[str],
) -> list[dict]:
    """
    Find conflicting code pairs (Excludes1 violations) in case codes (CDI-04).

    Checks all pairs of case_codes for CONFLICTS_WITH edges. Since conflicts
    are stored bidirectionally, only one direction is checked per pair to
    avoid duplicates.

    Args:
        G: The frozen CDI knowledge graph.
        case_codes: List of ICD-10 codes assigned to the case.

    Returns:
        List of conflict dicts with keys: code_a, code_b, reason.
    """
    conflicts: list[dict] = []
    seen: set[frozenset[str]] = set()

    for i, code_a in enumerate(case_codes):
        for code_b in case_codes[i + 1 :]:
            pair = frozenset((code_a, code_b))
            if pair in seen:
                continue

            # Check both directions for CONFLICTS_WITH edge
            for src, dst in [(code_a, code_b), (code_b, code_a)]:
                if G.has_edge(src, dst):
                    edge_data = G.edges[src, dst]
                    if edge_data.get("relation") == CONFLICTS_WITH:
                        conflicts.append(
                            {
                                "code_a": code_a,
                                "code_b": code_b,
                                "reason": edge_data.get(
                                    "reason", "Excludes1 conflict"
                                ),
                            }
                        )
                        seen.add(pair)
                        break

    return conflicts


def find_missed_diagnoses(
    G: nx.DiGraph,
    case_codes: list[str],
    max_suggestions: int = 5,
) -> list[dict]:
    """
    Suggest potentially missed diagnoses based on co-occurrence patterns (CDI-03).

    For each code in case_codes, finds COMMONLY_CO_CODED neighbors not already
    in case_codes. Results are sorted by weight (descending), deduplicated by
    suggested code (keeping highest weight), and limited to max_suggestions.

    Args:
        G: The frozen CDI knowledge graph.
        case_codes: List of ICD-10 codes assigned to the case.
        max_suggestions: Maximum number of suggestions to return.

    Returns:
        List of suggestion dicts with keys: suggested_code, description,
        co_coded_with, weight.
    """
    case_set = set(case_codes)
    # Track best suggestion per suggested_code (highest weight)
    best: dict[str, dict] = {}

    for code in case_codes:
        if not G.has_node(code):
            continue

        for _, neighbor, data in G.out_edges(code, data=True):
            if data.get("relation") != COMMONLY_CO_CODED:
                continue

            if neighbor in case_set:
                continue

            weight = data.get("weight", 0.0)

            # Keep the suggestion with the highest weight for each neighbor
            if neighbor not in best or weight > best[neighbor]["weight"]:
                best[neighbor] = {
                    "suggested_code": neighbor,
                    "description": G.nodes.get(neighbor, {}).get(
                        "description", ""
                    ),
                    "co_coded_with": code,
                    "weight": weight,
                }

    # Sort by weight descending, limit to max_suggestions
    suggestions = sorted(best.values(), key=lambda x: x["weight"], reverse=True)
    return suggestions[:max_suggestions]
