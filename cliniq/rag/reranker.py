"""
Cross-encoder reranking for ICD-10 retrieval candidates.

Takes initial retrieval candidates and reorders them using a cross-encoder
model that scores query-document pairs directly.
"""

from cliniq.config import RERANK_TOP_K
from cliniq.model_manager import ModelManager


class CrossEncoderReranker:
    """
    Rerank ICD-10 candidates using a cross-encoder model.

    Cross-encoders jointly encode query + document pairs, providing
    more accurate relevance scores than bi-encoder retrieval alone.
    """

    def __init__(self):
        """Initialize reranker with lazy model loading."""
        self.cross_encoder = None

    def _ensure_loaded(self):
        """Lazy load cross-encoder model."""
        if self.cross_encoder is None:
            manager = ModelManager()
            self.cross_encoder = manager.get_cross_encoder()

    def rerank(
        self,
        query: str,
        candidates: list[dict],
        top_k: int = RERANK_TOP_K
    ) -> list[dict]:
        """
        Rerank candidates using cross-encoder scores.

        Args:
            query: Clinical text query
            candidates: List of candidate dicts from retriever with keys:
                        code, description, score, rank
            top_k: Number of top candidates to return after reranking

        Returns:
            List of reranked candidates with added "rerank_score" field.
            Original "score" preserved as "retrieval_score" for comparison.
            Sorted by rerank_score descending, limited to top_k.
        """
        self._ensure_loaded()

        if not candidates:
            return []

        # Create query-document pairs for cross-encoder
        pairs = [(query, candidate["description"]) for candidate in candidates]

        # Get cross-encoder scores
        rerank_scores = self.cross_encoder.predict(pairs)

        # Add rerank scores to candidates and preserve original scores
        for candidate, rerank_score in zip(candidates, rerank_scores):
            candidate["retrieval_score"] = candidate["score"]  # Preserve original
            candidate["rerank_score"] = float(rerank_score)

        # Sort by rerank_score descending
        reranked = sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)

        # Update rank field to reflect new ordering
        for rank, candidate in enumerate(reranked, start=1):
            candidate["rank"] = rank

        # Return top_k
        return reranked[:top_k]
