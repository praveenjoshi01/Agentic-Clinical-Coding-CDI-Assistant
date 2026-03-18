#!/usr/bin/env python3
"""
ClinIQ Demo — run two clinical scenarios through the full 5-stage pipeline.

Scenarios:
  1. case_004.txt — CKD + Hypertension (68M)
  2. case_010.txt — CHF + AFib (75M)

Uses template-based physician queries (use_llm_queries=False) so no Qwen
LLM is needed for the CDI query generation step.
"""

import sys
import logging
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cliniq.pipeline import run_pipeline_audited

# Configure logging — send to stderr so formatted output stays clean on stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s  %(name)s  %(message)s",
    stream=sys.stderr,
)
# Quiet noisy libraries
for noisy in ("transformers", "sentence_transformers", "faiss", "huggingface_hub"):
    logging.getLogger(noisy).setLevel(logging.WARNING)


def _print(*args, **kwargs) -> None:
    """Print with immediate flush for piped/tee output."""
    print(*args, **kwargs)
    sys.stdout.flush()


# -- Pretty-print helpers ------------------------------------------------

SEPARATOR = "=" * 72
THIN_SEP = "-" * 72


def print_header(title: str) -> None:
    _print(f"\n{SEPARATOR}")
    _print(f"  {title}")
    _print(SEPARATOR)


def print_section(title: str) -> None:
    _print(f"\n{THIN_SEP}")
    _print(f"  {title}")
    _print(THIN_SEP)


def print_ingestion(result) -> None:
    """Print Stage 1 -- Ingestion metadata."""
    print_section("STAGE 1: INGESTION")
    doc = result.document
    meta = doc.metadata
    _print(f"  Source type   : {meta.source_type}")
    _print(f"  Patient ID    : {meta.patient_id}")
    _print(f"  Encounter ID  : {meta.encounter_id}")
    _print(f"  Confidence    : {doc.modality_confidence:.2f}")
    _print(f"  Narrative len : {len(doc.raw_narrative)} chars")


def print_ner(result) -> None:
    """Print Stage 2 -- NER entity table."""
    print_section("STAGE 2: NER (Named Entity Recognition)")
    nlu = result.nlu_result
    _print(f"  Total entities: {nlu.entity_count}")
    _print(f"  Diagnoses     : {len(nlu.diagnoses)}")
    _print(f"  Procedures    : {len(nlu.procedures)}")
    _print(f"  Medications   : {len(nlu.medications)}")
    _print()
    # Entity table
    _print(f"  {'Entity Text':<35} {'Type':<18} {'Neg?':<6} {'Conf':>5}  Qualifiers")
    _print(f"  {'-'*35} {'-'*18} {'-'*6} {'-'*5}  {'-'*20}")
    for e in nlu.entities:
        neg = "YES" if e.negated else ""
        quals = ", ".join(e.qualifiers) if e.qualifiers else ""
        _print(f"  {e.text:<35} {e.entity_type:<18} {neg:<6} {e.confidence:5.2f}  {quals}")


def print_coding(result) -> None:
    """Print Stage 3 -- ICD-10 coding results."""
    print_section("STAGE 3: RAG-BASED ICD-10 CODING")
    cr = result.coding_result

    if cr.principal_diagnosis:
        p = cr.principal_diagnosis
        _print(f"  Principal Dx  : {p.icd10_code} -- {p.description}")
        _print(f"                  Confidence: {p.confidence:.2f}")
        _print(f"                  Reasoning : {p.reasoning}")
        if p.needs_specificity:
            _print(f"                  ** Needs more specificity **")
    else:
        _print("  Principal Dx  : (none)")

    if cr.secondary_codes:
        _print()
        _print("  Secondary codes:")
        for s in cr.secondary_codes:
            spec = " [needs specificity]" if s.needs_specificity else ""
            _print(f"    {s.icd10_code} -- {s.description}  (conf {s.confidence:.2f}){spec}")
            _print(f"      Reasoning: {s.reasoning}")
    else:
        _print("  Secondary     : (none)")

    if cr.complication_codes:
        _print()
        _print("  Complication codes:")
        for c in cr.complication_codes:
            _print(f"    {c.icd10_code} -- {c.description}  (conf {c.confidence:.2f})")

    _print()
    _print(f"  Sequencing    : {cr.sequencing_rationale}")
    stats = cr.retrieval_stats
    if stats:
        _print(f"  Stats         : {stats.get('total_entities_coded', 0)} entities coded, "
               f"avg conf {stats.get('avg_confidence', 0):.2f}, "
               f"{stats.get('codes_needing_specificity', 0)} need specificity")


def print_cdi(result) -> None:
    """Print Stage 4 -- CDI analysis."""
    print_section("STAGE 4: CDI ANALYSIS")
    cdi = result.cdi_report
    if cdi is None:
        _print("  CDI analysis was skipped.")
        return

    _print(f"  Completeness score: {cdi.completeness_score:.2f}")
    _print(f"  Gaps: {cdi.gap_count}  |  Conflicts: {cdi.conflict_count}  |  "
           f"Missed Dx: {len(cdi.missed_diagnoses)}")

    if cdi.documentation_gaps:
        _print()
        _print("  Documentation Gaps:")
        for i, gap in enumerate(cdi.documentation_gaps, 1):
            _print(f"    [{i}] {gap.code} -- {gap.description}")
            _print(f"        Missing : {gap.missing_qualifier}")
            _print(f"        Query   : {gap.physician_query}")

    if cdi.missed_diagnoses:
        _print()
        _print("  Missed Diagnosis Suggestions:")
        for i, md in enumerate(cdi.missed_diagnoses, 1):
            _print(f"    [{i}] {md.suggested_code} -- {md.description}")
            _print(f"        Co-coded with: {md.co_coded_with}  "
                   f"(weight {md.co_occurrence_weight:.2f})")

    if cdi.code_conflicts:
        _print()
        _print("  Code Conflicts:")
        for i, cc in enumerate(cdi.code_conflicts, 1):
            _print(f"    [{i}] {cc.code_a} vs {cc.code_b}")
            _print(f"        Reason: {cc.conflict_reason}")
            _print(f"        Action: {cc.recommendation}")


def print_audit(result) -> None:
    """Print Stage 5 -- Audit trail summary."""
    print_section("STAGE 5: AUDIT TRAIL (Explainability)")
    trail = result.audit_trail
    if trail is None:
        _print("  No audit trail available.")
        return

    _print(f"  Case ID       : {trail.case_id}")
    _print(f"  Stages traced : {len(trail.stages)}")
    _print()
    for st in trail.stages:
        _print(f"    {st.stage:<12} {st.processing_time_ms:>8.1f} ms  "
               f"in={st.input_summary}  out={st.output_summary}")

    if trail.evidence_spans:
        _print()
        _print("  Evidence spans:")
        for code, spans in trail.evidence_spans.items():
            _print(f"    {code}: {len(spans)} span(s)")
            for span in spans[:2]:
                snippet = span[:80].replace("\n", " ")
                _print(f"      \"{snippet}...\"")


def run_scenario(name: str, filepath: Path, quick: bool = False) -> None:
    """Run one clinical note through the audited pipeline and print results."""
    print_header(f"SCENARIO: {name}")
    _print(f"  File: {filepath.name}")

    # Read the clinical note (some gold-standard files use latin-1)
    try:
        text = filepath.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = filepath.read_text(encoding="latin-1")
    _print(f"  Input preview: {text[:120].strip()}...")
    _print()

    # Run pipeline (template queries -- fast, no Qwen for query gen)
    result = run_pipeline_audited(
        text,
        use_llm_queries=False,
        skip_coding=quick,
    )

    # Print each stage
    print_ingestion(result)
    print_ner(result)
    if not quick:
        print_coding(result)
    else:
        print_section("STAGE 3: RAG-BASED ICD-10 CODING")
        _print("  (skipped in --quick mode; full run requires ~20 min/scenario on CPU)")
    print_cdi(result)
    print_audit(result)

    _print(f"\n  Total pipeline time: {result.processing_time_ms:.1f} ms")
    if result.errors:
        _print(f"  Errors: {result.errors}")
    _print()


# -- Main -----------------------------------------------------------------

def main() -> None:
    quick = "--quick" in sys.argv
    data_dir = PROJECT_ROOT / "cliniq" / "data" / "gold_standard" / "text_notes"

    mode_label = " (quick mode -- skipping LLM coding)" if quick else ""
    _print(SEPARATOR)
    _print(f"  ClinIQ -- Clinical Documentation Integrity Pipeline Demo{mode_label}")
    _print("  5-stage pipeline: Ingest -> NER -> RAG Coding -> CDI -> Audit")
    _print(SEPARATOR)

    # Scenario 1: CKD + Hypertension
    run_scenario(
        "CKD + Hypertension (68M, case_004)",
        data_dir / "case_004.txt",
        quick=quick,
    )

    # Scenario 2: CHF + AFib
    run_scenario(
        "CHF + Atrial Fibrillation (75M, case_010)",
        data_dir / "case_010.txt",
        quick=quick,
    )

    _print(SEPARATOR)
    _print("  Demo complete.")
    _print(SEPARATOR)


if __name__ == "__main__":
    main()
