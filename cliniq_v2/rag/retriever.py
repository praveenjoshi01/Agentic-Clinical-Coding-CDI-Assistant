"""
FAISS-based retrieval for ICD-10 codes using OpenAI embeddings.

Wraps a pre-built FAISS index and provides query-time retrieval
using OpenAI text-embedding-3-small instead of BGE embeddings.
No BGE query prefix needed.
"""

from pathlib import Path
from typing import Optional

import numpy as np

from cliniq_v2.config import INDEX_DIR, RETRIEVAL_TOP_K, EMBEDDING_DIMENSIONS
from cliniq_v2.rag.build_index import load_faiss_index, build_faiss_index


class FAISSRetriever:
    """
    Retrieve ICD-10 codes from FAISS index using OpenAI embeddings.

    Uses text-embedding-3-small (1536d) for query encoding.
    No BGE query prefix needed -- OpenAI embeddings don't use prefixes.
    """

    def __init__(self, index_dir: Optional[Path] = None):
        """
        Initialize retriever.

        Args:
            index_dir: Directory containing index files. If None, uses cliniq_v2 INDEX_DIR.
        """
        self.index_dir = index_dir if index_dir is not None else INDEX_DIR
        self.index = None
        self.codes = None

    def _ensure_loaded(self):
        """Lazy load index and codes. Does NOT load any local embedder."""
        if self.index is None:
            try:
                self.index, self.codes = load_faiss_index(self.index_dir)
            except FileNotFoundError:
                print(f"Index not found at {self.index_dir}, building...")
                self.ensure_index_built()

    def ensure_index_built(self):
        """
        Check if index exists, build if missing.

        Called automatically on first retrieval if index is not found.
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

        Uses OpenAI text-embedding-3-small for query encoding.

        Args:
            query: Clinical text query (e.g., "patient has type 2 diabetes").
            top_k: Number of candidates to retrieve (default from config).

        Returns:
            List of dicts with keys: code, description, score, rank.
        """
        from cliniq_v2.api_client import OpenAIClient

        self._ensure_loaded()

        # Encode query via OpenAI Embeddings API
        client = OpenAIClient().client
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=query,
        )
        query_vec = np.array(
            response.data[0].embedding, dtype=np.float32
        ).reshape(1, EMBEDDING_DIMENSIONS)

        # Search FAISS index
        distances, indices = self.index.search(query_vec, top_k)

        # Build results with code metadata
        results = []
        for rank, (idx, score) in enumerate(
            zip(indices[0], distances[0]), start=1
        ):
            code_entry = self.codes[idx]
            results.append({
                "code": code_entry["code"],
                "description": code_entry["description"],
                "score": float(score),
                "rank": rank,
            })

        return results
