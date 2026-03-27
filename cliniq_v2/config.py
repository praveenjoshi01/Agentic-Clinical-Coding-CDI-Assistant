"""
Configuration constants for the ClinIQ v2 pipeline.

Provides OpenAI model registry, cache paths, and shared settings.
Reuses data paths and thresholds from cliniq v1 where model-agnostic.
"""

from pathlib import Path

from cliniq.config import (
    CONFIDENCE_THRESHOLD,
    DATA_DIR,
    GOLD_STANDARD_DIR,
    ICD10_DIR,
    RETRIEVAL_TOP_K,
)

# OpenAI model registry mapping aliases to OpenAI model IDs
MODEL_REGISTRY = {
    "REASONING_LLM": "gpt-4o",
    "EMBEDDER": "text-embedding-3-small",
    "TRANSCRIPTION": "gpt-4o-mini-transcribe",
    "VISION": "gpt-4o",
}

# Directory paths (separate from cliniq v1 cache)
CACHE_DIR = Path.home() / ".cache" / "cliniq_v2"
INDEX_DIR = CACHE_DIR / "icd10_index"

# text-embedding-3-small default dimension
EMBEDDING_DIMENSIONS = 1536

# Pinecone configuration (used when Pinecone API key is provided)
PINECONE_INDEX_NAME = "cliniq-icd10"
PINECONE_NAMESPACE = "icd10"

# Re-exported for convenience (imported from cliniq.config above)
__all__ = [
    "MODEL_REGISTRY",
    "CACHE_DIR",
    "INDEX_DIR",
    "EMBEDDING_DIMENSIONS",
    "PINECONE_INDEX_NAME",
    "PINECONE_NAMESPACE",
    "CONFIDENCE_THRESHOLD",
    "RETRIEVAL_TOP_K",
    "DATA_DIR",
    "ICD10_DIR",
    "GOLD_STANDARD_DIR",
]
