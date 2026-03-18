"""
Knowledge graph package for CDI intelligence.

Provides a static reference knowledge graph built from ICD-10 codes
and curated clinical rules for co-occurrence, conflict, and qualifier
analysis. Includes query functions for gap detection, conflict detection,
and co-occurrence suggestions.
"""

from cliniq.knowledge_graph.builder import build_cdi_knowledge_graph
from cliniq.knowledge_graph.querier import (
    find_code_conflicts,
    find_documentation_gaps,
    find_missed_diagnoses,
)

__all__ = [
    "build_cdi_knowledge_graph",
    "find_code_conflicts",
    "find_documentation_gaps",
    "find_missed_diagnoses",
]
