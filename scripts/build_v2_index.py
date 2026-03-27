#!/usr/bin/env python3
"""Build FAISS index for ClinIQ v2 using OpenAI text-embedding-3-small."""

import sys
import os
import time
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cliniq_v2.config import INDEX_DIR


def check_index():
    """Check if v2 FAISS index exists."""
    index_path = INDEX_DIR / "icd10.faiss"
    metadata_path = INDEX_DIR / "icd10_metadata.json"
    if index_path.exists() and metadata_path.exists():
        import faiss

        index = faiss.read_index(str(index_path))
        print(f"v2 FAISS index exists: {index.ntotal} vectors at {index_path}")
        return True
    print(f"v2 FAISS index NOT found at {INDEX_DIR}")
    print("Run: python scripts/build_v2_index.py --api-key YOUR_KEY")
    return False


def build_index(api_key: str):
    """Build the v2 FAISS index."""
    from cliniq_v2.api_client import OpenAIClient
    from cliniq_v2.rag.build_index import build_faiss_index

    client = OpenAIClient()
    client.configure(api_key)

    print("Validating OpenAI API key...")
    if not client.validate_key():
        print("ERROR: Invalid OpenAI API key.")
        sys.exit(1)
    print("API key validated successfully.\n")

    print("Building ClinIQ v2 FAISS index (text-embedding-3-small, 1536d)...")
    print("Estimated cost: ~$0.015 for ~70K ICD-10 descriptions")
    print(f"Output directory: {INDEX_DIR}")
    print()

    start = time.perf_counter()
    try:
        index, codes = build_faiss_index()
    except FileNotFoundError as e:
        print(f"ERROR: Missing ICD-10 data file: {e}")
        print("Ensure the ICD-10 data directory is populated.")
        sys.exit(1)
    except Exception as e:
        error_msg = str(e).lower()
        if "invalid api key" in error_msg or "authentication" in error_msg:
            print(f"ERROR: API authentication failed: {e}")
            print("Check that your OpenAI API key is valid and has billing enabled.")
        elif "rate limit" in error_msg or "rate_limit" in error_msg:
            print(f"ERROR: Rate limit exceeded: {e}")
            print("Wait a moment and try again, or check your OpenAI usage limits.")
        else:
            print(f"ERROR: Failed to build index: {e}")
        sys.exit(1)
    elapsed = time.perf_counter() - start

    print(f"\nIndex built successfully in {elapsed:.1f}s")
    print(f"  Vectors: {index.ntotal}")
    print(f"  Dimension: {index.d}")
    print(f"  Location: {INDEX_DIR}")


def main():
    parser = argparse.ArgumentParser(
        description="Build FAISS index for ClinIQ v2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python scripts/build_v2_index.py --api-key sk-...
  OPENAI_API_KEY=sk-... python scripts/build_v2_index.py
  python scripts/build_v2_index.py --check
""",
    )
    parser.add_argument(
        "--api-key",
        help="OpenAI API key (or set OPENAI_API_KEY env var)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if index exists (don't build)",
    )
    args = parser.parse_args()

    if args.check:
        sys.exit(0 if check_index() else 1)

    api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: Provide --api-key or set OPENAI_API_KEY environment variable")
        sys.exit(1)

    try:
        build_index(api_key)
    except KeyboardInterrupt:
        print("\n\nBuild interrupted by user.")
        sys.exit(130)


if __name__ == "__main__":
    main()
