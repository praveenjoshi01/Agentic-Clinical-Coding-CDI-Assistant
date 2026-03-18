"""
Knowledge graph package for CDI intelligence.

Provides a static reference knowledge graph built from ICD-10 codes
and curated clinical rules for co-occurrence, conflict, and qualifier
analysis.
"""

from cliniq.knowledge_graph.builder import build_cdi_knowledge_graph

__all__ = ["build_cdi_knowledge_graph"]
