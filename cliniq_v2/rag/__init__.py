"""
RAG components for ICD-10 code retrieval using OpenAI embeddings.

Reuses ICD-10 code loading from cliniq.rag.icd10_loader.
Replaces BGE embedder + cross-encoder with OpenAI text-embedding-3-small + GPT-4o.
Supports Pinecone as optional cloud vector DB alternative to FAISS.
"""

from cliniq.rag.icd10_loader import load_icd10_codes, get_code_by_id, get_codes_by_chapter
from cliniq_v2.rag.build_index import build_faiss_index, load_faiss_index
from cliniq_v2.rag.retriever import FAISSRetriever
from cliniq_v2.rag.base import BaseRetriever
from cliniq_v2.rag.factory import get_retriever

try:
    from cliniq_v2.rag.pinecone_retriever import PineconeRetriever
except ImportError:
    PineconeRetriever = None

__all__ = [
    "build_faiss_index",
    "load_faiss_index",
    "load_icd10_codes",
    "get_code_by_id",
    "get_codes_by_chapter",
    "FAISSRetriever",
    "BaseRetriever",
    "get_retriever",
    "PineconeRetriever",
]
