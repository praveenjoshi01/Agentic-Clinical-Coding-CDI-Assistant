"""
Unit tests for the knowledge_graph package (builder + querier).

Tests cover KG construction, edge types, parent derivation, curated rule
loading, gap detection, conflict detection, co-occurrence suggestions,
and edge cases. No model downloads required — pure NetworkX + JSON.
"""

import networkx as nx
import pytest

from cliniq.knowledge_graph import (
    build_cdi_knowledge_graph,
    find_code_conflicts,
    find_documentation_gaps,
    find_missed_diagnoses,
)
from cliniq.knowledge_graph.builder import _derive_parent_code
from cliniq.knowledge_graph.schema import (
    COMMONLY_CO_CODED,
    CONFLICTS_WITH,
    HAS_PARENT,
    REQUIRES_QUALIFIER,
)


@pytest.fixture(scope="module")
def kg() -> nx.DiGraph:
    """Build the KG once for all tests in this module."""
    return build_cdi_knowledge_graph()


# ---------------------------------------------------------------------------
# Builder tests
# ---------------------------------------------------------------------------


class TestBuilder:
    """Tests for the KG builder (build_cdi_knowledge_graph)."""

    def test_build_kg_returns_digraph(self, kg: nx.DiGraph) -> None:
        """build_cdi_knowledge_graph() returns a DiGraph with nodes and edges."""
        assert isinstance(kg, nx.DiGraph)
        assert kg.number_of_nodes() > 0
        assert kg.number_of_edges() > 0

    def test_kg_has_all_edge_types(self, kg: nx.DiGraph) -> None:
        """Built KG has edges with all 4 relation types."""
        edge_types_found: set[str] = set()
        for _, _, data in kg.edges(data=True):
            rel = data.get("relation")
            if rel:
                edge_types_found.add(rel)

        for expected in [COMMONLY_CO_CODED, CONFLICTS_WITH, HAS_PARENT, REQUIRES_QUALIFIER]:
            assert expected in edge_types_found, f"Missing edge type: {expected}"

    def test_kg_has_parent_edges(self, kg: nx.DiGraph) -> None:
        """Verify HAS_PARENT edges exist in the KG."""
        parent_edges = [
            (u, v)
            for u, v, d in kg.edges(data=True)
            if d.get("relation") == HAS_PARENT
        ]
        assert len(parent_edges) > 0, "No HAS_PARENT edges found"

    def test_derive_parent_code(self) -> None:
        """Test _derive_parent_code with various inputs."""
        assert _derive_parent_code("E11.40") == "E11.4"
        assert _derive_parent_code("E11.4") == "E11"
        assert _derive_parent_code("E11") is None
        assert _derive_parent_code("I10") is None

    def test_kg_loads_curated_rules(self, kg: nx.DiGraph) -> None:
        """KG has COMMONLY_CO_CODED edges between known pairs from kg_rules.json."""
        # E11.9 <-> I10 is a curated co-occurrence pair
        assert kg.has_edge("E11.9", "I10"), "Missing E11.9 -> I10 co-occurrence edge"
        edge_data = kg.edges["E11.9", "I10"]
        assert edge_data.get("relation") == COMMONLY_CO_CODED


# ---------------------------------------------------------------------------
# Querier tests
# ---------------------------------------------------------------------------


class TestQuerier:
    """Tests for the KG query functions."""

    def test_find_documentation_gaps_with_missing_qualifiers(
        self, kg: nx.DiGraph
    ) -> None:
        """E11.40 with empty qualifiers should return at least 1 gap."""
        gaps = find_documentation_gaps(kg, ["E11.40"], {"E11.40": []})
        assert len(gaps) >= 1
        qualifier_names = [g["missing_qualifier"] for g in gaps]
        # E11.40 requires complication_type and laterality per kg_rules.json
        assert "complication_type" in qualifier_names or "laterality" in qualifier_names

    def test_find_documentation_gaps_with_all_qualifiers_present(
        self, kg: nx.DiGraph
    ) -> None:
        """E11.40 with all required qualifiers should return 0 gaps."""
        gaps = find_documentation_gaps(
            kg,
            ["E11.40"],
            {"E11.40": ["complication_type", "laterality"]},
        )
        assert len(gaps) == 0

    def test_find_documentation_gaps_unknown_code(self, kg: nx.DiGraph) -> None:
        """Unknown code Z99.999 returns empty list (no crash)."""
        gaps = find_documentation_gaps(kg, ["Z99.999"], {"Z99.999": []})
        assert gaps == []

    def test_find_code_conflicts_known_conflict(self, kg: nx.DiGraph) -> None:
        """E10.9 and E11.9 should produce at least 1 conflict."""
        conflicts = find_code_conflicts(kg, ["E10.9", "E11.9"])
        assert len(conflicts) >= 1
        # Verify conflict structure
        c = conflicts[0]
        assert "code_a" in c
        assert "code_b" in c
        assert "reason" in c

    def test_find_code_conflicts_no_conflicts(self, kg: nx.DiGraph) -> None:
        """I10 and E11.9 should have 0 conflicts (hypertension + diabetes don't conflict)."""
        conflicts = find_code_conflicts(kg, ["I10", "E11.9"])
        assert len(conflicts) == 0

    def test_find_missed_diagnoses_co_occurrence(self, kg: nx.DiGraph) -> None:
        """E11.9 alone should suggest I10 (commonly co-coded)."""
        suggestions = find_missed_diagnoses(kg, ["E11.9"])
        suggested_codes = [s["suggested_code"] for s in suggestions]
        assert "I10" in suggested_codes, (
            f"I10 not in suggestions: {suggested_codes}"
        )

    def test_find_missed_diagnoses_already_coded(self, kg: nx.DiGraph) -> None:
        """If both E11.9 and I10 are in case_codes, I10 should NOT appear in suggestions."""
        suggestions = find_missed_diagnoses(kg, ["E11.9", "I10"])
        suggested_codes = [s["suggested_code"] for s in suggestions]
        assert "I10" not in suggested_codes

    def test_find_missed_diagnoses_max_limit(self, kg: nx.DiGraph) -> None:
        """With max_suggestions=2, returned list has at most 2 entries."""
        suggestions = find_missed_diagnoses(kg, ["E11.9"], max_suggestions=2)
        assert len(suggestions) <= 2
