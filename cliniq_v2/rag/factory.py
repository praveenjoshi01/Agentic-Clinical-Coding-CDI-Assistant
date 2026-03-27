"""
Retriever factory for ICD-10 code retrieval.

Returns PineconeRetriever when Pinecone is configured, otherwise
falls back to FAISSRetriever. Transparent to callers -- both implement
the BaseRetriever protocol.
"""

from cliniq_v2.rag.base import BaseRetriever
from cliniq_v2.rag.retriever import FAISSRetriever


def get_retriever() -> BaseRetriever:
    """Return the appropriate retriever based on configured backends.

    Returns PineconeRetriever if PineconeClient is configured,
    otherwise falls back to FAISSRetriever.
    """
    try:
        from cliniq_v2.pinecone_client import PineconeClient

        pc = PineconeClient()
        _ = pc.client  # Test if configured (raises RuntimeError if not)
        from cliniq_v2.rag.pinecone_retriever import PineconeRetriever

        return PineconeRetriever()
    except (RuntimeError, ImportError):
        return FAISSRetriever()
