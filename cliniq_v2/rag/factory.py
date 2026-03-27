"""
Retriever factory for ICD-10 code retrieval.

Returns PineconeRetriever when Pinecone is configured, otherwise
falls back to FAISSRetriever. Transparent to callers -- both implement
the BaseRetriever protocol.
"""

from cliniq_v2.rag.base import BaseRetriever

def get_retriever() -> BaseRetriever:
    """Return the Pinecone retriever for ICD-10 code retrieval."""
    from cliniq_v2.rag.pinecone_retriever import PineconeRetriever
    return PineconeRetriever()
