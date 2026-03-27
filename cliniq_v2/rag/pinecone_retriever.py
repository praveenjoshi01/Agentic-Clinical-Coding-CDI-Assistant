"""
Pinecone-based retrieval for ICD-10 codes using OpenAI embeddings.

Queries a pre-populated Pinecone index with OpenAI text-embedding-3-small
vectors, returning results in the same format as FAISSRetriever.
"""

from cliniq_v2.config import RETRIEVAL_TOP_K, PINECONE_INDEX_NAME, PINECONE_NAMESPACE


class PineconeRetriever:
    """
    Retrieve ICD-10 codes from Pinecone index using OpenAI embeddings.

    Uses text-embedding-3-small (1536d) for query encoding.
    Requires PineconeClient to be configured before use.
    """

    def __init__(self):
        """Initialize retriever with lazy index connection."""
        self._index = None

    def _ensure_connected(self):
        """Lazy-connect to Pinecone index on first use."""
        if self._index is None:
            from cliniq_v2.pinecone_client import PineconeClient

            pc = PineconeClient().client
            self._index = pc.Index(name=PINECONE_INDEX_NAME)

    def ensure_index_built(self) -> None:
        """
        Verify that the Pinecone index exists and is populated.

        Raises:
            RuntimeError: If the index does not exist or is empty.
        """
        from cliniq_v2.pinecone_client import PineconeClient

        pc = PineconeClient().client

        if not pc.has_index(name=PINECONE_INDEX_NAME):
            raise RuntimeError(
                f"Pinecone index '{PINECONE_INDEX_NAME}' does not exist. "
                f"Create it in the Pinecone console or run "
                f"scripts/populate_pinecone_index.py to set it up."
            )

        self._ensure_connected()

        stats = self._index.describe_index_stats()
        if stats.total_vector_count == 0:
            raise RuntimeError(
                f"Pinecone index '{PINECONE_INDEX_NAME}' is empty. "
                f"Run scripts/populate_pinecone_index.py to populate it."
            )

    def retrieve(self, query: str, top_k: int = RETRIEVAL_TOP_K) -> list[dict]:
        """
        Retrieve top-k ICD-10 codes for a clinical query.

        Uses OpenAI text-embedding-3-small for query encoding,
        then queries the Pinecone index.

        Args:
            query: Clinical text query (e.g., "patient has type 2 diabetes").
            top_k: Number of candidates to retrieve (default from config).

        Returns:
            List of dicts with keys: code, description, score, rank.
        """
        from cliniq_v2.api_client import OpenAIClient

        self._ensure_connected()

        # Encode query via OpenAI Embeddings API
        client = OpenAIClient().client
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=query,
        )
        query_vec = response.data[0].embedding

        # Query Pinecone index
        results = self._index.query(
            vector=query_vec,
            top_k=top_k,
            include_metadata=True,
            namespace=PINECONE_NAMESPACE,
        )

        # Convert to standard result format
        return [
            {
                "code": match["metadata"]["code"],
                "description": match["metadata"]["description"],
                "score": float(match["score"]),
                "rank": rank,
            }
            for rank, match in enumerate(results["matches"], start=1)
        ]
