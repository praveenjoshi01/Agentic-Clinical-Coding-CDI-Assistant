"""
FAISS index construction for ICD-10 code retrieval using OpenAI embeddings.

Builds and saves a FAISS flat index from ICD-10 code descriptions
using text-embedding-3-small (1536 dimensions).
"""

import json
from pathlib import Path
from typing import Optional

import faiss
import numpy as np

from cliniq_v2.config import INDEX_DIR, EMBEDDING_DIMENSIONS
from cliniq.rag.icd10_loader import load_icd10_codes


def build_faiss_index(
    codes: Optional[list[dict]] = None,
    output_dir: Optional[Path] = None,
) -> tuple[faiss.Index, list[dict]]:
    """
    Build FAISS flat index from ICD-10 code descriptions using OpenAI embeddings.

    Process:
    1. Load ICD-10 codes (if not provided)
    2. Extract descriptions
    3. Encode with OpenAI text-embedding-3-small in batches of 2048
    4. Create FAISS IndexFlatIP (cosine similarity via normalized vectors)
    5. Save index and metadata to disk

    Args:
        codes: Optional pre-loaded code list. If None, loads from default location.
        output_dir: Directory to save index files. If None, uses cliniq_v2 INDEX_DIR.

    Returns:
        Tuple of (faiss.Index, list[dict] of codes).
    """
    from cliniq_v2.api_client import OpenAIClient

    # Load codes if not provided
    if codes is None:
        codes = load_icd10_codes()

    if output_dir is None:
        output_dir = INDEX_DIR
    else:
        output_dir = Path(output_dir)

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Extract descriptions for embedding
    descriptions = [code["description"] for code in codes]

    # Get OpenAI client
    client = OpenAIClient().client

    # Encode descriptions in batches of 2048 using OpenAI Embeddings API
    batch_size = 2048
    all_embeddings = []

    print(f"Encoding {len(descriptions)} ICD-10 descriptions with text-embedding-3-small...")
    for i in range(0, len(descriptions), batch_size):
        batch = descriptions[i : i + batch_size]
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=batch,
        )
        # Extract embeddings in order
        batch_embeddings = [item.embedding for item in response.data]
        all_embeddings.extend(batch_embeddings)
        print(f"  Batch {i // batch_size + 1}: encoded {len(batch)} descriptions")

    # Convert to numpy array (OpenAI embeddings are already normalized)
    embeddings = np.array(all_embeddings, dtype=np.float32)

    # Create FAISS index (IndexFlatIP = inner product, equivalent to cosine with normalized vectors)
    dimension = embeddings.shape[1]
    assert dimension == EMBEDDING_DIMENSIONS, (
        f"Expected {EMBEDDING_DIMENSIONS} dimensions, got {dimension}"
    )
    index = faiss.IndexFlatIP(dimension)

    # Add embeddings to index
    index.add(embeddings)

    # Save index to disk
    index_path = output_dir / "icd10.faiss"
    faiss.write_index(index, str(index_path))
    print(f"FAISS index saved to {index_path}")

    # Save metadata (codes) to disk
    metadata_path = output_dir / "icd10_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(codes, f, indent=2, ensure_ascii=False)
    print(f"Metadata saved to {metadata_path}")

    print(f"Index built successfully: {len(codes)} codes, {dimension} dimensions")

    return index, codes


def load_faiss_index(
    index_dir: Optional[Path] = None,
) -> tuple[faiss.Index, list[dict]]:
    """
    Load pre-built FAISS index and metadata from disk.

    Args:
        index_dir: Directory containing index files. If None, uses cliniq_v2 INDEX_DIR.

    Returns:
        Tuple of (faiss.Index, list[dict] of codes).

    Raises:
        FileNotFoundError: If index or metadata files don't exist.
    """
    if index_dir is None:
        index_dir = INDEX_DIR
    else:
        index_dir = Path(index_dir)

    index_path = index_dir / "icd10.faiss"
    metadata_path = index_dir / "icd10_metadata.json"

    if not index_path.exists():
        raise FileNotFoundError(
            f"FAISS index not found: {index_path}. "
            f"Run build_faiss_index() first to create the index."
        )

    if not metadata_path.exists():
        raise FileNotFoundError(
            f"Metadata file not found: {metadata_path}. "
            f"Index and metadata must be created together."
        )

    # Load index
    index = faiss.read_index(str(index_path))

    # Load metadata
    with open(metadata_path, "r", encoding="utf-8") as f:
        codes = json.load(f)

    print(f"Loaded index with {index.ntotal} codes from {index_path}")

    return index, codes
