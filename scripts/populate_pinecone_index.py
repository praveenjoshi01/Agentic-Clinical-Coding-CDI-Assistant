#!/usr/bin/env python3
"""Populate Pinecone serverless index with ICD-10 embeddings for ClinIQ v2.

Creates a Pinecone serverless index, embeds ICD-10 code descriptions using
OpenAI text-embedding-3-small, and upserts them with code metadata.
This is a one-time setup step for users who want cloud vector search
instead of the default local FAISS index.
"""

import sys
import os
import time
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cliniq_v2.config import (
    PINECONE_INDEX_NAME,
    PINECONE_NAMESPACE,
    EMBEDDING_DIMENSIONS,
)


def populate_index(openai_key: str, pinecone_key: str):
    """Create Pinecone index and upload ICD-10 embeddings.

    Parameters
    ----------
    openai_key : str
        OpenAI API key for generating embeddings.
    pinecone_key : str
        Pinecone API key for index management.
    """
    from cliniq_v2.api_client import OpenAIClient
    from cliniq_v2.pinecone_client import PineconeClient
    from pinecone import ServerlessSpec

    # Configure and validate both clients
    print("Configuring API clients...")
    OpenAIClient().configure(openai_key)
    PineconeClient().configure(pinecone_key)

    print("Validating OpenAI API key...")
    if not OpenAIClient().validate_key():
        print("ERROR: Invalid OpenAI API key.")
        sys.exit(1)
    print("  OpenAI key validated.")

    print("Validating Pinecone API key...")
    if not PineconeClient().validate_key():
        print("ERROR: Invalid Pinecone API key.")
        sys.exit(1)
    print("  Pinecone key validated.\n")

    # Load ICD-10 codes
    print("Loading ICD-10 codes...")
    from cliniq.rag.icd10_loader import load_icd10_codes

    codes = load_icd10_codes()
    print(f"  Loaded {len(codes)} ICD-10 codes.\n")

    # Create index if it doesn't exist
    pc = PineconeClient().client
    if not pc.has_index(name=PINECONE_INDEX_NAME):
        print(f"Creating Pinecone index '{PINECONE_INDEX_NAME}'...")
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=EMBEDDING_DIMENSIONS,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        # Wait for index to be ready
        while not pc.describe_index(PINECONE_INDEX_NAME).status["ready"]:
            time.sleep(1)
        print(f"  Index '{PINECONE_INDEX_NAME}' created and ready.\n")
    else:
        print(f"Index '{PINECONE_INDEX_NAME}' already exists.\n")

    # Generate embeddings with OpenAI
    print("Generating embeddings with text-embedding-3-small...")
    start = time.perf_counter()
    oai_client = OpenAIClient().client
    descriptions = [c["description"] for c in codes]

    # Embed in batches of 200 for safety
    embeddings = []
    for i in range(0, len(descriptions), 200):
        batch = descriptions[i : i + 200]
        response = oai_client.embeddings.create(
            model="text-embedding-3-small", input=batch
        )
        embeddings.extend([item.embedding for item in response.data])
        print(f"  Embedded batch {i // 200 + 1} ({len(embeddings)}/{len(descriptions)})")

    embed_time = time.perf_counter() - start
    print(f"  Embeddings complete in {embed_time:.1f}s.\n")

    # Prepare vectors for upsert
    print("Preparing vectors for upsert...")
    vectors = []
    for code_entry, embedding in zip(codes, embeddings):
        vectors.append(
            {
                "id": code_entry["code"],
                "values": embedding,
                "metadata": {
                    "code": code_entry["code"],
                    "description": code_entry["description"],
                    "chapter": code_entry.get("chapter", ""),
                },
            }
        )
    print(f"  Prepared {len(vectors)} vectors.\n")

    # Upsert to Pinecone in batches of 200
    print("Upserting vectors to Pinecone...")
    upsert_start = time.perf_counter()
    index = pc.Index(name=PINECONE_INDEX_NAME)
    for i in range(0, len(vectors), 200):
        batch = vectors[i : i + 200]
        index.upsert(vectors=batch, namespace=PINECONE_NAMESPACE)
        print(f"  Upserted batch {i // 200 + 1} ({min(i + 200, len(vectors))}/{len(vectors)})")

    upsert_time = time.perf_counter() - upsert_start
    print(f"  Upsert complete in {upsert_time:.1f}s.\n")

    # Verify
    time.sleep(2)  # Brief wait for index stats to update
    stats = index.describe_index_stats()
    total_time = time.perf_counter() - start

    print("=" * 50)
    print("Pinecone index population complete!")
    print(f"  Index:      {PINECONE_INDEX_NAME}")
    print(f"  Namespace:  {PINECONE_NAMESPACE}")
    print(f"  Vectors:    {stats.total_vector_count}")
    print(f"  Dimension:  {EMBEDDING_DIMENSIONS}")
    print(f"  Total time: {total_time:.1f}s")
    print("=" * 50)


def check_index(pinecone_key: str):
    """Check if the Pinecone index exists and print stats.

    Parameters
    ----------
    pinecone_key : str
        Pinecone API key.
    """
    from cliniq_v2.pinecone_client import PineconeClient

    PineconeClient().configure(pinecone_key)

    if not PineconeClient().validate_key():
        print("ERROR: Invalid Pinecone API key.")
        sys.exit(1)

    pc = PineconeClient().client
    if pc.has_index(name=PINECONE_INDEX_NAME):
        index = pc.Index(name=PINECONE_INDEX_NAME)
        stats = index.describe_index_stats()
        print(f"Index '{PINECONE_INDEX_NAME}' exists.")
        print(f"  Total vectors: {stats.total_vector_count}")
        if stats.namespaces:
            for ns_name, ns_stats in stats.namespaces.items():
                print(f"  Namespace '{ns_name}': {ns_stats.vector_count} vectors")
    else:
        print(f"Index '{PINECONE_INDEX_NAME}' does NOT exist.")
        print("Run: python scripts/populate_pinecone_index.py --openai-api-key KEY --pinecone-api-key KEY")
        sys.exit(1)


def delete_index(pinecone_key: str):
    """Delete the Pinecone index if it exists.

    Parameters
    ----------
    pinecone_key : str
        Pinecone API key.
    """
    from cliniq_v2.pinecone_client import PineconeClient

    PineconeClient().configure(pinecone_key)

    if not PineconeClient().validate_key():
        print("ERROR: Invalid Pinecone API key.")
        sys.exit(1)

    pc = PineconeClient().client
    if pc.has_index(name=PINECONE_INDEX_NAME):
        pc.delete_index(PINECONE_INDEX_NAME)
        print(f"Index '{PINECONE_INDEX_NAME}' deleted.")
    else:
        print(f"Index '{PINECONE_INDEX_NAME}' does not exist. Nothing to delete.")


def main():
    parser = argparse.ArgumentParser(
        description="Populate Pinecone serverless index with ICD-10 embeddings for ClinIQ v2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python scripts/populate_pinecone_index.py --openai-api-key sk-... --pinecone-api-key pcsk_...
  OPENAI_API_KEY=sk-... PINECONE_API_KEY=pcsk_... python scripts/populate_pinecone_index.py
  python scripts/populate_pinecone_index.py --pinecone-api-key pcsk_... --check
  python scripts/populate_pinecone_index.py --pinecone-api-key pcsk_... --delete
""",
    )
    parser.add_argument(
        "--openai-api-key",
        help="OpenAI API key (or set OPENAI_API_KEY env var)",
    )
    parser.add_argument(
        "--pinecone-api-key",
        help="Pinecone API key (or set PINECONE_API_KEY env var)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if index exists and print vector count",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete the Pinecone index",
    )
    args = parser.parse_args()

    pinecone_key = args.pinecone_api_key or os.environ.get("PINECONE_API_KEY")
    if not pinecone_key:
        print("ERROR: Provide --pinecone-api-key or set PINECONE_API_KEY environment variable")
        sys.exit(1)

    if args.check:
        check_index(pinecone_key)
        sys.exit(0)

    if args.delete:
        delete_index(pinecone_key)
        sys.exit(0)

    openai_key = args.openai_api_key or os.environ.get("OPENAI_API_KEY")
    if not openai_key:
        print("ERROR: Provide --openai-api-key or set OPENAI_API_KEY environment variable")
        sys.exit(1)

    try:
        populate_index(openai_key, pinecone_key)
    except FileNotFoundError as e:
        print(f"ERROR: Missing ICD-10 data file: {e}")
        print("Ensure the ICD-10 data directory is populated.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nPopulation interrupted by user.")
        sys.exit(130)
    except Exception as e:
        error_msg = str(e).lower()
        if "invalid api key" in error_msg or "authentication" in error_msg:
            print(f"ERROR: API authentication failed: {e}")
            print("Check that your API keys are valid.")
        elif "rate limit" in error_msg or "rate_limit" in error_msg:
            print(f"ERROR: Rate limit exceeded: {e}")
            print("Wait a moment and try again, or check your usage limits.")
        elif "index" in error_msg and "create" in error_msg:
            print(f"ERROR: Index creation failed: {e}")
            print("Check your Pinecone plan limits and try again.")
        else:
            print(f"ERROR: Failed to populate index: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
