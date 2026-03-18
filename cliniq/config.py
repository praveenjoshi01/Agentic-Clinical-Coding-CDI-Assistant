"""
Configuration constants for the ClinIQ pipeline.

Provides model registry, data paths, and hyperparameters used across modules.
"""

from pathlib import Path

# Model registry mapping aliases to HuggingFace model IDs
MODEL_REGISTRY = {
    "CLINICAL_NER": "d4data/biomedical-ner-all",
    "REASONING_LLM": "Qwen/Qwen2.5-1.5B-Instruct",
    "EMBEDDER": "BAAI/bge-small-en-v1.5",
    "MULTIMODAL": "HuggingFaceTB/SmolVLM-256M-Instruct",
    "RERANKER": "cross-encoder/ms-marco-MiniLM-L-6-v2",
}

# Directory paths
DATA_DIR = Path("cliniq/data")
ICD10_DIR = DATA_DIR / "icd10"
GOLD_STANDARD_DIR = DATA_DIR / "gold_standard"
CACHE_DIR = Path.home() / ".cache" / "cliniq"
INDEX_DIR = CACHE_DIR / "icd10_index"

# Confidence thresholds
CONFIDENCE_THRESHOLD = 0.80

# RAG hyperparameters
RETRIEVAL_TOP_K = 20
RERANK_TOP_K = 5

# BGE embedder query prefix
BGE_QUERY_PREFIX = "Represent this sentence: "
