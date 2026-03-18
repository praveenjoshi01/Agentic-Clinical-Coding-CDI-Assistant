#!/usr/bin/env python3
"""
Pre-compute demo PipelineResult JSON files for the Streamlit UI.

Runs the audited pipeline on 3 demo cases covering all modalities and
serializes results to ui/demo_data/precomputed/{case_id}.json for instant
loading in the demo UI.

Usage:
    python scripts/precompute_demo.py           # Full pipeline (slow, ~20 min/case)
    python scripts/precompute_demo.py --quick    # NER + CDI only (faster, skip RAG)
"""

import sys
import json
import time
import logging
import argparse
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cliniq.pipeline import run_pipeline_audited

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s  %(name)s  %(message)s",
    stream=sys.stderr,
)
for noisy in ("transformers", "sentence_transformers", "faiss", "huggingface_hub"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

# Output directory for pre-computed results
OUTPUT_DIR = PROJECT_ROOT / "ui" / "demo_data" / "precomputed"

# Demo case definitions: (case_id, source_type, file_path)
DEMO_CASES = [
    (
        "case_004",
        "text",
        PROJECT_ROOT / "cliniq" / "data" / "gold_standard" / "text_notes" / "case_004.txt",
    ),
    (
        "case_010",
        "text",
        PROJECT_ROOT / "cliniq" / "data" / "gold_standard" / "text_notes" / "case_010.txt",
    ),
    (
        "case_001",
        "fhir",
        PROJECT_ROOT / "cliniq" / "data" / "gold_standard" / "fhir_bundles" / "case_001.json",
    ),
]


def read_input(case_id: str, source_type: str, filepath: Path):
    """Read input data from file, handling encoding and format."""
    if source_type == "fhir":
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        # Text note -- handle encoding issues
        try:
            return filepath.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return filepath.read_text(encoding="latin-1")


def precompute_case(case_id: str, source_type: str, filepath: Path, quick: bool = False):
    """Run pipeline on a single case and save the result as JSON."""
    print(f"\n{'='*60}")
    print(f"  Processing: {case_id} ({source_type})")
    print(f"  File: {filepath.name}")
    print(f"  Mode: {'quick (NER + CDI only)' if quick else 'full pipeline'}")
    print(f"{'='*60}")

    if not filepath.exists():
        print(f"  WARNING: File not found: {filepath}")
        print(f"  Skipping {case_id}.")
        return None

    input_data = read_input(case_id, source_type, filepath)

    start = time.perf_counter()
    result = run_pipeline_audited(
        input_data,
        use_llm_queries=False,  # Template-based queries for speed
        skip_coding=quick,
    )
    elapsed = time.perf_counter() - start

    # Serialize to JSON
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{case_id}.json"
    output_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")

    # Print summary
    entity_count = result.nlu_result.entity_count
    code_count = 0
    if result.coding_result.principal_diagnosis:
        code_count += 1
    code_count += len(result.coding_result.secondary_codes)
    code_count += len(result.coding_result.complication_codes)

    gap_count = result.cdi_report.gap_count if result.cdi_report else 0

    print(f"\n  Results for {case_id}:")
    print(f"    Source type    : {source_type}")
    print(f"    Entities       : {entity_count}")
    print(f"    Codes          : {code_count}")
    print(f"    CDI gaps       : {gap_count}")
    print(f"    Processing time: {elapsed:.1f}s ({result.processing_time_ms:.0f}ms)")
    print(f"    Saved to       : {output_path}")

    return result


def main():
    parser = argparse.ArgumentParser(description="Pre-compute demo PipelineResult files")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Skip RAG coding (NER + CDI only) for faster generation",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  ClinIQ -- Pre-compute Demo Results")
    print(f"  Mode: {'quick (skip RAG coding)' if args.quick else 'full pipeline'}")
    print(f"  Output: {OUTPUT_DIR}")
    print("=" * 60)

    results = []
    for case_id, source_type, filepath in DEMO_CASES:
        result = precompute_case(case_id, source_type, filepath, quick=args.quick)
        if result:
            results.append((case_id, result))

    print(f"\n{'='*60}")
    print(f"  Pre-computation complete: {len(results)}/{len(DEMO_CASES)} cases processed")
    print(f"  Output directory: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
