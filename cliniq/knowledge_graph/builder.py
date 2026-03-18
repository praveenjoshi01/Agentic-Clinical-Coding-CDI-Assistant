"""
Static CDI knowledge graph builder.

Builds a reference knowledge graph from ICD-10 codes and curated clinical
rules for co-occurrence, conflict, and qualifier analysis. The graph is
built once and queried per-case during CDI analysis.
"""

import json
import logging
from pathlib import Path

import networkx as nx

from cliniq.knowledge_graph.schema import (
    COMMONLY_CO_CODED,
    CONFLICTS_WITH,
    HAS_PARENT,
    REQUIRES_QUALIFIER,
    NODE_TYPE_ICD,
)

logger = logging.getLogger(__name__)

# Path to curated rules JSON
_RULES_PATH = Path(__file__).parent.parent / "data" / "kg_rules.json"


def _derive_parent_code(code: str) -> str | None:
    """
    Derive the parent ICD-10 code from a given code.

    E11.40  -> E11.4
    E11.4   -> E11
    E11     -> None

    Args:
        code: ICD-10 code string.

    Returns:
        Parent code string, or None if no parent exists.
    """
    if "." in code:
        # Has decimal: try removing last char after the dot
        base, suffix = code.split(".", 1)
        if len(suffix) > 1:
            # E11.40 -> E11.4, E11.311 -> E11.31
            return f"{base}.{suffix[:-1]}"
        else:
            # E11.4 -> E11
            return base
    # No decimal: top-level category, no parent
    return None


def build_cdi_knowledge_graph() -> nx.DiGraph:
    """
    Build the static CDI reference knowledge graph.

    The graph contains:
    - ICD-10 code nodes (loaded from icd10_loader)
    - HAS_PARENT edges (derived from code hierarchy)
    - COMMONLY_CO_CODED edges (from curated co-occurrence rules)
    - CONFLICTS_WITH edges (from curated Excludes1 rules)
    - REQUIRES_QUALIFIER edges (from curated qualifier requirements)

    Returns:
        A NetworkX DiGraph representing the CDI knowledge graph.
    """
    G = nx.DiGraph()

    # Step 1: Load ICD-10 codes and add as nodes
    try:
        from cliniq.rag.icd10_loader import load_icd10_codes

        icd10_codes = load_icd10_codes()
        for entry in icd10_codes:
            G.add_node(
                entry["code"],
                type=NODE_TYPE_ICD,
                description=entry.get("description", ""),
                chapter=entry.get("chapter", ""),
            )
        logger.info("Loaded %d ICD-10 codes as nodes", len(icd10_codes))
    except (FileNotFoundError, ImportError, ValueError) as e:
        logger.warning(
            "Could not load ICD-10 codes (%s). Building KG from rules only.", e
        )
        icd10_codes = []

    # Step 2: Add HAS_PARENT edges by deriving parent codes
    parent_edge_count = 0
    # Collect all node IDs for parent lookup
    all_nodes = set(G.nodes())
    for node in list(all_nodes):
        parent = _derive_parent_code(node)
        while parent is not None:
            # Ensure parent node exists (add if not present from ICD-10 load)
            if parent not in G:
                G.add_node(parent, type=NODE_TYPE_ICD, description="", chapter="")
            G.add_edge(node, parent, relation=HAS_PARENT)
            parent_edge_count += 1
            # Only link direct parent, not grandparent
            break
    logger.info("Added %d HAS_PARENT edges", parent_edge_count)

    # Step 3: Load curated rules
    if not _RULES_PATH.exists():
        logger.warning("Curated rules file not found at %s", _RULES_PATH)
        return nx.freeze(G)

    with open(_RULES_PATH, "r", encoding="utf-8") as f:
        rules = json.load(f)

    # Step 4: Add COMMONLY_CO_CODED edges (bidirectional)
    co_occ_count = 0
    for rule in rules.get("co_occurrences", []):
        code_a = rule["code_a"]
        code_b = rule["code_b"]
        weight = rule.get("weight", 0.5)
        evidence = rule.get("evidence", "")

        # Ensure both nodes exist
        for code in (code_a, code_b):
            if code not in G:
                G.add_node(code, type=NODE_TYPE_ICD, description="", chapter="")

        # Bidirectional edges
        G.add_edge(
            code_a,
            code_b,
            relation=COMMONLY_CO_CODED,
            weight=weight,
            evidence=evidence,
        )
        G.add_edge(
            code_b,
            code_a,
            relation=COMMONLY_CO_CODED,
            weight=weight,
            evidence=evidence,
        )
        co_occ_count += 1
    logger.info("Added %d COMMONLY_CO_CODED pairs (%d edges)", co_occ_count, co_occ_count * 2)

    # Step 5: Add CONFLICTS_WITH edges (bidirectional)
    conflict_count = 0
    for rule in rules.get("conflicts", []):
        code_a = rule["code_a"]
        code_b = rule["code_b"]
        reason = rule.get("reason", "")

        for code in (code_a, code_b):
            if code not in G:
                G.add_node(code, type=NODE_TYPE_ICD, description="", chapter="")

        G.add_edge(
            code_a, code_b, relation=CONFLICTS_WITH, reason=reason
        )
        G.add_edge(
            code_b, code_a, relation=CONFLICTS_WITH, reason=reason
        )
        conflict_count += 1
    logger.info("Added %d CONFLICTS_WITH pairs (%d edges)", conflict_count, conflict_count * 2)

    # Step 6: Add REQUIRES_QUALIFIER edges (code -> qualifier string node)
    qualifier_count = 0
    for rule in rules.get("qualifier_requirements", []):
        code = rule["code"]
        qualifiers = rule.get("qualifiers", [])
        rationale = rule.get("rationale", "")

        if code not in G:
            G.add_node(code, type=NODE_TYPE_ICD, description="", chapter="")

        for qualifier in qualifiers:
            qualifier_node = f"qualifier:{qualifier}"
            if qualifier_node not in G:
                G.add_node(qualifier_node, type="qualifier", description=qualifier)
            G.add_edge(
                code,
                qualifier_node,
                relation=REQUIRES_QUALIFIER,
                rationale=rationale,
            )
            qualifier_count += 1
    logger.info("Added %d REQUIRES_QUALIFIER edges", qualifier_count)

    # Step 7: Log KG statistics
    edge_counts = {}
    for _, _, data in G.edges(data=True):
        rel = data.get("relation", "UNKNOWN")
        edge_counts[rel] = edge_counts.get(rel, 0) + 1

    logger.info(
        "KG built: %d nodes, %d edges. Edge breakdown: %s",
        G.number_of_nodes(),
        G.number_of_edges(),
        edge_counts,
    )

    return nx.freeze(G)
