"""
Base retriever protocol for ICD-10 code retrieval backends.

Defines the interface that both FAISSRetriever and PineconeRetriever implement,
enabling the factory pattern in cliniq_v2.rag.factory.
"""

from typing import Protocol


class BaseRetriever(Protocol):
    """Protocol for ICD-10 code retrieval backends."""

    def retrieve(self, query: str, top_k: int = 20) -> list[dict]:
        """Retrieve top-k ICD-10 codes for a clinical query.

        Returns list of dicts with keys: code, description, score, rank.
        """
        ...

    def ensure_index_built(self) -> None:
        """Ensure the underlying index/collection is populated."""
        ...
