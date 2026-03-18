"""
FAISS-based retrieval for ICD-10 codes.

Wraps a pre-built FAISS index and provides query-time retrieval
with BGE query prefix handling.
"""

from pathlib import Path
from typing import Optional

import numpy as np

from cliniq.config import INDEX_DIR, RETRIEVAL_TOP_K, BGE_QUERY_PREFIX
from cliniq.model_manager import ModelManager
from cliniq.rag.build_index import load_faiss_index, build_faiss_index


class FAISSRetriever:
    """
    Retrieve ICD-10 codes from FAISS index using BGE embeddings.

    Applies the BGE query prefix ("Represent this sentence: ") to queries
    but NOT to indexed documents. The index must be pre-built with documents
    encoded without the prefix.
    """

    def __init__(self, index_dir: Optional[Path] = None):
        """
        Initialize retriever with pre-built FAISS index.

        Args:
            index_dir: Directory containing index files. If None, uses config.INDEX_DIR
        """
        self.index_dir = index_dir if index_dir is not None else INDEX_DIR
        self.index = None
        self.codes = None
        self.embedder = None

    def _ensure_loaded(self):
        """Lazy load index, codes, and embedder."""
        if self.index is None:
            # Try to load existing index
            try:
                self.index, self.codes = load_faiss_index(self.index_dir)
            except FileNotFoundError:
                # Index doesn't exist, build it
                print(f"Index not found at {self.index_dir}, building...")
                self.ensure_index_built()

        if self.embedder is None:
            manager = ModelManager()
            self.embedder = manager.get_embedder()

    def ensure_index_built(self):
        """
        Check if index exists, build if missing.

        This is called automatically on first retrieval if index is not found.
        Can also be called explicitly to force index building.
        """
        index_path = self.index_dir / "icd10.faiss"
        if not index_path.exists():
            print(f"Building FAISS index at {self.index_dir}...")
            self.index, self.codes = build_faiss_index(output_dir=self.index_dir)
        else:
            self.index, self.codes = load_faiss_index(self.index_dir)

    def retrieve(self, query: str, top_k: int = RETRIEVAL_TOP_K) -> list[dict]:
        """
        Retrieve top-k ICD-10 codes for a clinical query.

        Args:
            query: Clinical text query (e.g., "patient has type 2 diabetes")
            top_k: Number of candidates to retrieve (default from config)

        Returns:
            List of dicts with keys:
                - code: ICD-10 code string
                - description: Code description
                - score: Retrieval score (cosine similarity)
                - rank: 1-indexed rank position
        """
        self._ensure_loaded()

        # Prepend BGE query prefix (NOT applied to documents in index)
        prefixed_query = BGE_QUERY_PREFIX + query

        # Encode query with embedder
        query_vec = self.embedder.encode(
            prefixed_query,
            normalize_embeddings=True,
            show_progress_bar=False
        )

        # Ensure query_vec is 2D for FAISS search
        query_vec = np.array(query_vec, dtype=np.float32).reshape(1, -1)

        # Search FAISS index
        distances, indices = self.index.search(query_vec, top_k)

        # Build results with code metadata
        results = []
        for rank, (idx, score) in enumerate(zip(indices[0], distances[0]), start=1):
            code_entry = self.codes[idx]
            results.append({
                "code": code_entry["code"],
                "description": code_entry["description"],
                "score": float(score),
                "rank": rank
            })

        return results
