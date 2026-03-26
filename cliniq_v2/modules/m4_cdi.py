"""
CDI (Clinical Documentation Integrity) agent module for cliniq_v2.

Orchestrates KG queries and GPT-4o-based physician query generation to produce
CDIReports with documentation gaps, code conflicts, missed diagnoses,
and completeness scoring.

Replaces Qwen LLM with OpenAI GPT-4o for physician query generation.
All KG infrastructure, Pydantic models, and helper functions are reused
from cliniq (model-agnostic).

Requirements: CDI-01 through CDI-05.
"""

import json
import logging
import time
from typing import Optional

import networkx as nx

from cliniq.knowledge_graph.builder import build_cdi_knowledge_graph
from cliniq.knowledge_graph.querier import (
    find_code_conflicts,
    find_documentation_gaps,
    find_missed_diagnoses,
)
from cliniq.models.cdi import (
    CDIReport,
    CodeConflict,
    DocumentationGap,
    MissedDiagnosis,
)
from cliniq.models.coding import CodeSuggestion, CodingResult
from cliniq.models.entities import NLUResult
from cliniq.modules.m4_cdi import (
    _extract_entity_qualifiers,
    _find_evidence_for_code,
    calculate_completeness_score,
)
from cliniq_v2.modules.m5_explainability import capture_cot_and_json

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level KG caching: build once, reuse across calls.
# ---------------------------------------------------------------------------

_KG_CACHE: Optional[nx.DiGraph] = None


def _get_kg() -> nx.DiGraph:
    """Return the cached CDI knowledge graph, building on first call."""
    global _KG_CACHE
    if _KG_CACHE is None:
        logger.info("Building CDI knowledge graph (first call, will be cached)")
        _KG_CACHE = build_cdi_knowledge_graph()
        logger.info(
            "KG cached: %d nodes, %d edges",
            _KG_CACHE.number_of_nodes(),
            _KG_CACHE.number_of_edges(),
        )
    return _KG_CACHE


# ---------------------------------------------------------------------------
# Physician query generation (CDI-02) -- GPT-4o replaces Qwen
# ---------------------------------------------------------------------------


def generate_physician_query(
    gap: dict, clinical_context: str
) -> tuple[str, str]:
    """
    Generate a physician query for a documentation gap using GPT-4o.

    Builds a prompt with clinical context and few-shot examples, calls GPT-4o
    with JSON structured output, and captures the raw chain-of-thought trace.

    Falls back to a template-based query if GPT-4o JSON parsing fails.

    Args:
        gap: Dict with keys ``code``, ``missing_qualifier``, ``description``.
        clinical_context: The clinical note text (first 300 chars used).

    Returns:
        Tuple of (physician_query_text, raw_cot_trace).
    """
    from cliniq_v2.api_client import OpenAIClient

    code = gap.get("code", "")
    description = gap.get("description", "")
    missing_qualifier = gap.get("missing_qualifier", "")

    context_snippet = clinical_context[:300] if clinical_context else "None"

    prompt = f"""You are a clinical documentation integrity specialist. Generate a polite physician query asking for missing documentation.

ICD-10 Code: {code}
Code Description: {description}
Missing Qualifier: {missing_qualifier}
Clinical Context: {context_snippet}

Examples of good physician queries:
- Gap: E11.40 missing "laterality" -> "Dr. Smith, the documentation notes diabetic neuropathy. Could you please specify whether the neuropathy affects the right, left, or bilateral lower extremities?"
- Gap: I50.9 missing "type" -> "The assessment indicates heart failure. Could you clarify whether this is systolic (HFrEF), diastolic (HFpEF), or combined heart failure?"

Return a JSON object with a single field:
{{"query": "Your physician query here"}}

Return ONLY the JSON object, no other text."""

    try:
        client = OpenAIClient().client
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a clinical documentation integrity specialist.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        raw_response = response.choices[0].message.content

        # Capture CoT trace and extract JSON
        cot_trace, json_str = capture_cot_and_json(raw_response)

        if json_str:
            parsed = json.loads(json_str)
            query_text = parsed.get("query", "")
            if query_text:
                logger.debug(
                    "GPT-4o physician query generated for %s: %s",
                    code,
                    query_text[:80],
                )
                return (query_text, cot_trace)

        # JSON parsing failed or no query field - fall through to template
        logger.warning(
            "GPT-4o response did not contain valid query JSON for %s, "
            "using template fallback",
            code,
        )
    except Exception as e:
        logger.warning(
            "GPT-4o physician query generation failed for %s: %s, "
            "using template fallback",
            code,
            e,
        )
        cot_trace = ""

    # Template fallback
    query_text = (
        f"Can you please clarify the {missing_qualifier} for the documented "
        f"{description}? This information is needed to assign the most "
        f"specific ICD-10 code ({code})."
    )
    return (query_text, cot_trace)


# ---------------------------------------------------------------------------
# Main CDI orchestrator (CDI-05)
# ---------------------------------------------------------------------------


def run_cdi_analysis(
    nlu_result: NLUResult,
    coding_result: CodingResult,
    clinical_text: str,
    use_llm_queries: bool = True,
) -> CDIReport:
    """
    Run full CDI analysis producing a CDIReport.

    Orchestrates:
    1. KG construction/caching
    2. Code extraction from CodingResult
    3. Entity qualifier extraction
    4. Gap detection (CDI-01)
    5. Conflict detection (CDI-04)
    6. Missed diagnosis suggestions (CDI-03)
    7. Physician query generation via GPT-4o (CDI-02)
    8. Completeness scoring (CDI-05)

    Args:
        nlu_result: NLU output with extracted entities.
        coding_result: Coding output with code suggestions.
        clinical_text: Full clinical note text.
        use_llm_queries: If True, generate physician queries via GPT-4o.
            If False, use template fallback (for fast testing).

    Returns:
        CDIReport with gaps, conflicts, missed diagnoses, and completeness score.
    """
    start_time = time.time()

    # Step 1: Get cached KG
    G = _get_kg()

    # Step 2: Extract case codes from CodingResult
    case_codes: list[str] = []
    if coding_result.principal_diagnosis is not None:
        case_codes.append(coding_result.principal_diagnosis.icd10_code)
    case_codes.extend(s.icd10_code for s in coding_result.secondary_codes)
    case_codes.extend(s.icd10_code for s in coding_result.complication_codes)

    logger.info("CDI analysis: %d case codes extracted", len(case_codes))

    # Handle empty case
    if not case_codes:
        processing_time_ms = (time.time() - start_time) * 1000
        return CDIReport(
            documentation_gaps=[],
            missed_diagnoses=[],
            code_conflicts=[],
            completeness_score=1.0,
            processing_time_ms=processing_time_ms,
        )

    # Step 3: Extract entity qualifiers
    entity_qualifiers = _extract_entity_qualifiers(nlu_result, coding_result)
    logger.debug("Entity qualifiers: %s", entity_qualifiers)

    # Step 4: Find documentation gaps (CDI-01)
    raw_gaps = find_documentation_gaps(G, case_codes, entity_qualifiers)
    logger.info("Found %d documentation gaps", len(raw_gaps))

    # Step 5: Find code conflicts (CDI-04)
    raw_conflicts = find_code_conflicts(G, case_codes)
    logger.info("Found %d code conflicts", len(raw_conflicts))

    # Step 6: Find missed diagnoses (CDI-03)
    raw_missed = find_missed_diagnoses(G, case_codes)
    logger.info("Found %d missed diagnosis suggestions", len(raw_missed))

    # Step 7: Build DocumentationGap models with physician queries
    documentation_gaps: list[DocumentationGap] = []
    for gap in raw_gaps:
        if use_llm_queries:
            query_text, cot_trace = generate_physician_query(
                gap, clinical_text
            )
        else:
            # Template fallback for fast testing
            query_text = (
                f"Can you please clarify the {gap['missing_qualifier']} "
                f"for the documented {gap['description']}? This information "
                f"is needed to assign the most specific ICD-10 code "
                f"({gap['code']})."
            )
            cot_trace = ""

        evidence = _find_evidence_for_code(
            gap["code"], nlu_result, clinical_text
        )

        documentation_gaps.append(
            DocumentationGap(
                code=gap["code"],
                description=gap["description"],
                missing_qualifier=gap["missing_qualifier"],
                physician_query=query_text,
                evidence_text=evidence,
                confidence=0.8,  # Default confidence for KG-based gaps
                cot_trace=cot_trace,
            )
        )

    # Step 8: Build MissedDiagnosis models
    missed_diagnoses: list[MissedDiagnosis] = []
    for missed in raw_missed:
        evidence = _find_evidence_for_code(
            missed["suggested_code"], nlu_result, clinical_text
        )
        missed_diagnoses.append(
            MissedDiagnosis(
                suggested_code=missed["suggested_code"],
                description=missed["description"],
                co_coded_with=missed["co_coded_with"],
                co_occurrence_weight=missed["weight"],
                evidence_text=evidence,
            )
        )

    # Step 9: Build CodeConflict models
    code_conflicts: list[CodeConflict] = []
    for conflict in raw_conflicts:
        code_conflicts.append(
            CodeConflict(
                code_a=conflict["code_a"],
                code_b=conflict["code_b"],
                conflict_reason=conflict["reason"],
                recommendation=(
                    "Review documentation to determine which code "
                    "is clinically appropriate"
                ),
            )
        )

    # Step 10: Calculate completeness score
    completeness = calculate_completeness_score(
        documentation_gaps, code_conflicts, len(case_codes)
    )

    processing_time_ms = (time.time() - start_time) * 1000

    logger.info(
        "CDI analysis complete: %d gaps, %d conflicts, %d missed, "
        "completeness=%.2f, time=%.1fms",
        len(documentation_gaps),
        len(code_conflicts),
        len(missed_diagnoses),
        completeness,
        processing_time_ms,
    )

    return CDIReport(
        documentation_gaps=documentation_gaps,
        missed_diagnoses=missed_diagnoses,
        code_conflicts=code_conflicts,
        completeness_score=completeness,
        processing_time_ms=processing_time_ms,
    )
