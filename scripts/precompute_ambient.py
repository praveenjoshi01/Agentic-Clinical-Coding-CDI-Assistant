#!/usr/bin/env python3
"""
Pre-compute ambient encounter demo data for the Streamlit UI.

Runs the ambient pipeline on hardcoded transcripts and serializes results
to ui/demo_data/ambient/encounter_NNN.json for instant loading in the
ambient mode page.

Usage:
    python scripts/precompute_ambient.py           # Full pipeline
    python scripts/precompute_ambient.py --quick    # Skip RAG coding (faster)

Note: The handcrafted JSON files in ui/demo_data/ambient/ are the primary
demo artifacts. This script regenerates the pipeline_result portions.
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s  %(name)s  %(message)s",
    stream=sys.stderr,
)
for noisy in ("transformers", "sentence_transformers", "faiss", "huggingface_hub"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

# Directories
AMBIENT_DIR = PROJECT_ROOT / "ui" / "demo_data" / "ambient"

# Encounter definitions: (encounter_id, json_filename)
# The SOAP note (generated_note) from each JSON is fed to the pipeline.
ENCOUNTERS = [
    ("encounter_001", "encounter_001.json"),
    ("encounter_002", "encounter_002.json"),
]


def load_encounter(filename: str) -> dict:
    """Load an existing ambient encounter JSON file."""
    filepath = AMBIENT_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Encounter file not found: {filepath}")
    return json.loads(filepath.read_text(encoding="utf-8"))


def regenerate_encounter(
    encounter_id: str,
    filename: str,
    quick: bool = False,
) -> bool:
    """
    Regenerate pipeline_result and disambiguation_items for a single encounter.

    Loads the existing JSON, feeds the generated_note through the pipeline,
    and updates the pipeline_result and disambiguation_items fields.

    Returns True on success, False on failure.
    """
    print(f"\n{'='*60}")
    print(f"  Processing: {encounter_id}")
    print(f"  File: {filename}")
    print(f"  Mode: {'quick (skip RAG coding)' if quick else 'full pipeline'}")
    print(f"{'='*60}")

    try:
        data = load_encounter(filename)
    except FileNotFoundError as e:
        print(f"  WARNING: {e}")
        print(f"  Skipping {encounter_id}.")
        return False

    # Extract the SOAP note to feed through the pipeline
    soap_note = data.get("generated_note", "")
    if not soap_note:
        print(f"  WARNING: No generated_note in {filename}")
        print(f"  Skipping {encounter_id}.")
        return False

    try:
        from cliniq.pipeline import run_pipeline_audited

        start = time.perf_counter()
        result = run_pipeline_audited(
            soap_note,
            use_llm_queries=False,  # Template-based queries for speed
            skip_coding=quick,
        )
        elapsed = time.perf_counter() - start

        # Serialize pipeline result to dict
        pipeline_dict = json.loads(result.model_dump_json())

        # Build disambiguation items from CDI report
        disambiguation_items = []
        if result.cdi_report is not None:
            from uuid import uuid4

            for gap in result.cdi_report.documentation_gaps:
                disambiguation_items.append({
                    "item_id": uuid4().hex[:8],
                    "category": "gap",
                    "title": f"Documentation Gap: {gap.code}",
                    "description": gap.physician_query,
                    "suggested_action": f"Clarify {gap.missing_qualifier} for {gap.code}",
                    "source_code": gap.code,
                    "confidence": gap.confidence,
                    "status": "pending",
                })

            for md in result.cdi_report.missed_diagnoses:
                disambiguation_items.append({
                    "item_id": uuid4().hex[:8],
                    "category": "missed_diagnosis",
                    "title": f"Potential Missed Dx: {md.suggested_code}",
                    "description": md.description,
                    "suggested_action": f"Consider documenting {md.suggested_code} ({md.description})",
                    "source_code": md.suggested_code,
                    "confidence": md.co_occurrence_weight,
                    "status": "pending",
                })

            for cc in result.cdi_report.code_conflicts:
                disambiguation_items.append({
                    "item_id": uuid4().hex[:8],
                    "category": "conflict",
                    "title": f"Code Conflict: {cc.code_a} vs {cc.code_b}",
                    "description": cc.conflict_reason,
                    "suggested_action": cc.recommendation,
                    "source_code": f"{cc.code_a},{cc.code_b}",
                    "confidence": 0.8,
                    "status": "pending",
                })

        # Update the JSON data with live pipeline results
        data["pipeline_result"] = pipeline_dict
        data["disambiguation_items"] = disambiguation_items

        # Write updated JSON back
        output_path = AMBIENT_DIR / filename
        output_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # Print summary
        entity_count = result.nlu_result.entity_count
        gap_count = result.cdi_report.gap_count if result.cdi_report else 0

        print(f"\n  Results for {encounter_id}:")
        print(f"    Entities        : {entity_count}")
        print(f"    CDI gaps        : {gap_count}")
        print(f"    Disambiguation  : {len(disambiguation_items)} items")
        print(f"    Processing time : {elapsed:.1f}s ({result.processing_time_ms:.0f}ms)")
        print(f"    Saved to        : {output_path}")

        return True

    except ImportError as e:
        print(f"\n  Could not import pipeline modules: {e}")
        print("  This usually means models are not downloaded yet.")
        print("  The handcrafted demo JSON files in ui/demo_data/ambient/")
        print("  already contain complete pipeline results and can be used as-is.")
        return False

    except Exception as e:
        print(f"\n  ERROR processing {encounter_id}: {e}")
        print("  The existing demo JSON file was not modified.")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Pre-compute ambient encounter demo data"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Skip RAG coding (NER + CDI only) for faster generation",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  ClinIQ -- Pre-compute Ambient Demo Data")
    print(f"  Mode: {'quick (skip RAG coding)' if args.quick else 'full pipeline'}")
    print(f"  Output: {AMBIENT_DIR}")
    print("=" * 60)

    if not AMBIENT_DIR.exists():
        print(f"\n  ERROR: Ambient demo directory not found: {AMBIENT_DIR}")
        print("  Run plan 05-02 Task 1 first to create the encounter JSON files.")
        sys.exit(1)

    successes = 0
    for encounter_id, filename in ENCOUNTERS:
        if regenerate_encounter(encounter_id, filename, quick=args.quick):
            successes += 1

    print(f"\n{'='*60}")
    print(f"  Pre-computation complete: {successes}/{len(ENCOUNTERS)} encounters processed")
    print(f"  Output directory: {AMBIENT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
