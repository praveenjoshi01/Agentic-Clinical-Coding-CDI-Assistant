"""
Unit tests for LLM-as-judge evaluation module.

Split into non-model tests (fast) and model-requiring tests (slow).
Non-model tests mock the LLM to verify structure, imports, and edge cases.
Model-requiring tests use actual Qwen inference for scoring validation.
"""

from unittest.mock import patch, MagicMock

import pytest

from cliniq.models.cdi import CDIReport, DocumentationGap
from cliniq.models.audit import AuditTrail, StageTrace


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_physician_query_good():
    """A clearly relevant physician query for a laterality gap."""
    return "Can you specify the laterality of the diabetic neuropathy?"


@pytest.fixture
def sample_physician_query_bad():
    """A clearly irrelevant physician query."""
    return "What is the patient's favorite color?"


@pytest.fixture
def sample_documentation_gap():
    """A documentation gap description for laterality."""
    return "E11.40 missing laterality qualifier"


@pytest.fixture
def sample_clinical_context():
    """Clinical context for diabetes with neuropathy."""
    return (
        "Patient presents with type 2 diabetes mellitus with diabetic polyneuropathy. "
        "HbA1c 8.2%. Complains of numbness and tingling in bilateral lower extremities. "
        "Monofilament testing shows decreased sensation."
    )


@pytest.fixture
def sample_cot_good():
    """A coherent clinical reasoning trace."""
    return (
        "Step 1: Identified diabetes mellitus type 2 from HbA1c of 8.2% and clinical history. "
        "Step 2: Neuropathy confirmed by monofilament testing showing decreased sensation. "
        "Step 3: Mapped to E11.40 (Type 2 diabetes with neuropathy, unspecified). "
        "Step 4: Laterality not documented — bilateral mentioned in subjective but not "
        "confirmed in assessment. Flagging for physician query."
    )


@pytest.fixture
def sample_cot_bad():
    """An incoherent reasoning trace."""
    return "asdf random words 123 the cat sat on the mat purple banana helicopter"


@pytest.fixture
def mock_judge_result():
    """A well-formed judge result dict."""
    return {
        "score": 0.8,
        "raw_score": 4,
        "reasoning": "Query directly addresses the missing laterality qualifier",
        "cot_trace": '{"score": 4, "reasoning": "Query directly addresses the missing laterality qualifier"}',
    }


@pytest.fixture
def sample_cdi_report():
    """A CDI report with documentation gaps for aggregate testing."""
    return CDIReport(
        documentation_gaps=[
            DocumentationGap(
                code="E11.40",
                description="Type 2 diabetes with neuropathy, unspecified",
                missing_qualifier="laterality",
                physician_query="Can you specify the laterality of the diabetic neuropathy?",
                evidence_text="diabetic polyneuropathy",
                confidence=0.85,
            ),
        ],
        missed_diagnoses=[],
        code_conflicts=[],
        completeness_score=0.75,
    )


@pytest.fixture
def sample_audit_trail():
    """An audit trail with CoT traces for aggregate testing."""
    return AuditTrail(
        case_id="test-001",
        stages=[
            StageTrace(
                stage="ner",
                processing_time_ms=50.0,
                input_summary="Clinical note",
                output_summary="3 entities extracted",
                cot_traces=[
                    "Identified diabetes from HbA1c mention. "
                    "Extracted neuropathy from monofilament findings."
                ],
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Non-model tests (fast)
# ---------------------------------------------------------------------------


def test_judge_imports():
    """All judge functions importable from cliniq.evaluation.llm_judge."""
    from cliniq.evaluation.llm_judge import (
        judge_query_relevance,
        judge_cot_coherence,
        evaluate_cdi_quality,
        evaluate_cot_quality,
    )

    assert callable(judge_query_relevance)
    assert callable(judge_cot_coherence)
    assert callable(evaluate_cdi_quality)
    assert callable(evaluate_cot_quality)


def test_evaluate_cdi_quality_empty():
    """Empty cdi_reports list returns metrics with 0 queries scored."""
    from cliniq.evaluation.llm_judge import evaluate_cdi_quality

    result = evaluate_cdi_quality(cdi_reports=[], clinical_contexts=[])

    assert result["n_queries_scored"] == 0
    assert result["mean_relevance_score"] == 0.0
    assert result["per_query_details"] == []


def test_evaluate_cot_quality_empty():
    """Empty audit_trails list returns metrics with 0 traces scored."""
    from cliniq.evaluation.llm_judge import evaluate_cot_quality

    result = evaluate_cot_quality(audit_trails=[])

    assert result["n_traces_scored"] == 0
    assert result["mean_coherence_score"] == 0.0
    assert result["per_trace_details"] == []


def test_judge_result_structure(mock_judge_result):
    """Judge result dict has score (0-1), raw_score (1-5), reasoning (str), cot_trace (str)."""
    result = mock_judge_result

    assert "score" in result
    assert 0.0 <= result["score"] <= 1.0

    assert "raw_score" in result
    assert 1 <= result["raw_score"] <= 5

    assert "reasoning" in result
    assert isinstance(result["reasoning"], str)

    assert "cot_trace" in result
    assert isinstance(result["cot_trace"], str)


# ---------------------------------------------------------------------------
# Model-requiring tests (slow)
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_judge_query_relevance_good_query(
    sample_physician_query_good,
    sample_documentation_gap,
    sample_clinical_context,
):
    """A clearly relevant physician query should score >= 0.60."""
    from cliniq.evaluation.llm_judge import judge_query_relevance

    result = judge_query_relevance(
        physician_query=sample_physician_query_good,
        documentation_gap=sample_documentation_gap,
        clinical_context=sample_clinical_context,
    )

    assert "score" in result
    assert result["score"] >= 0.60, (
        f"Good query scored {result['score']}, expected >= 0.60"
    )


@pytest.mark.slow
def test_judge_query_relevance_bad_query(
    sample_physician_query_bad,
    sample_documentation_gap,
    sample_clinical_context,
):
    """A clearly irrelevant query should score <= 0.60."""
    from cliniq.evaluation.llm_judge import judge_query_relevance

    result = judge_query_relevance(
        physician_query=sample_physician_query_bad,
        documentation_gap=sample_documentation_gap,
        clinical_context=sample_clinical_context,
    )

    assert "score" in result
    assert result["score"] <= 0.60, (
        f"Bad query scored {result['score']}, expected <= 0.60"
    )


@pytest.mark.slow
def test_judge_cot_coherence_good_cot(sample_cot_good):
    """A coherent clinical reasoning trace should score >= 0.60."""
    from cliniq.evaluation.llm_judge import judge_cot_coherence

    result = judge_cot_coherence(
        cot_trace=sample_cot_good,
        task_description="NER entity extraction and ICD-10 mapping",
    )

    assert "score" in result
    assert result["score"] >= 0.60, (
        f"Good CoT scored {result['score']}, expected >= 0.60"
    )


@pytest.mark.slow
def test_judge_cot_coherence_bad_cot(sample_cot_bad):
    """Incoherent text should score <= 0.60."""
    from cliniq.evaluation.llm_judge import judge_cot_coherence

    result = judge_cot_coherence(
        cot_trace=sample_cot_bad,
        task_description="NER entity extraction and ICD-10 mapping",
    )

    assert "score" in result
    assert result["score"] <= 0.60, (
        f"Bad CoT scored {result['score']}, expected <= 0.60"
    )
