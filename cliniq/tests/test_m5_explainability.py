"""
Unit tests for the explainability module (m5_explainability).

Covers:
- AuditTrailBuilder: init, record_stage, add_evidence, has_all_stages, get_trail
- capture_cot_and_json: valid JSON, no JSON, nested JSON
- link_evidence_spans: normal coding result, empty coding result
- build_retrieval_log: populated and empty inputs

All tests are non-model (no downloads needed).
"""

import pytest

from cliniq.models.audit import AuditTrail, RetrievalLog
from cliniq.models.coding import CodeSuggestion, CodingResult
from cliniq.modules.m5_explainability import (
    AuditTrailBuilder,
    build_retrieval_log,
    capture_cot_and_json,
    link_evidence_spans,
)


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture
def sample_code_suggestion_a() -> CodeSuggestion:
    """A CodeSuggestion for diabetes mellitus."""
    return CodeSuggestion(
        icd10_code="E11.9",
        description="Type 2 diabetes mellitus without complications",
        confidence=0.85,
        evidence_text="diabetes mellitus",
        reasoning="Patient history of diabetes",
        needs_specificity=False,
        alternatives=[],
    )


@pytest.fixture
def sample_code_suggestion_b() -> CodeSuggestion:
    """A CodeSuggestion for hypertension."""
    return CodeSuggestion(
        icd10_code="I10",
        description="Essential (primary) hypertension",
        confidence=0.78,
        evidence_text="hypertension",
        reasoning="Elevated blood pressure readings",
        needs_specificity=False,
        alternatives=[],
    )


@pytest.fixture
def sample_coding_result(
    sample_code_suggestion_a: CodeSuggestion,
    sample_code_suggestion_b: CodeSuggestion,
) -> CodingResult:
    """A CodingResult with principal and one secondary code."""
    return CodingResult(
        principal_diagnosis=sample_code_suggestion_a,
        secondary_codes=[sample_code_suggestion_b],
        complication_codes=[],
        sequencing_rationale="Diabetes is principal",
        retrieval_stats={"total_entities_coded": 2},
    )


@pytest.fixture
def sample_clinical_text() -> str:
    """Clinical text containing relevant entity mentions."""
    return (
        "The patient is a 65-year-old male with a long history of diabetes mellitus "
        "and hypertension. He presents with fatigue and polyuria. Blood glucose is "
        "elevated at 250 mg/dL. Blood pressure is 160/95 mmHg."
    )


# ------------------------------------------------------------------
# AuditTrailBuilder tests
# ------------------------------------------------------------------


class TestAuditTrailBuilder:
    """Tests for the AuditTrailBuilder convenience wrapper."""

    def test_audit_trail_builder_init(self) -> None:
        """Creates builder with case_id, trail starts with 0 stages."""
        builder = AuditTrailBuilder("case-001")
        assert builder.stage_count == 0
        trail = builder.get_trail()
        assert trail.case_id == "case-001"

    def test_audit_trail_builder_record_stage(self) -> None:
        """Record 2 stages, verify stage_count and stage names."""
        builder = AuditTrailBuilder("case-002")
        builder.record_stage("ingestion", 10.5, "raw text", "parsed document")
        builder.record_stage("ner", 25.3, "narrative", "5 entities extracted")

        assert builder.stage_count == 2

        trail = builder.get_trail()
        assert trail.stages[0].stage == "ingestion"
        assert trail.stages[0].processing_time_ms == 10.5
        assert trail.stages[1].stage == "ner"
        assert trail.stages[1].processing_time_ms == 25.3

    def test_audit_trail_builder_add_evidence(self) -> None:
        """Add evidence for a code and verify evidence_spans dict."""
        builder = AuditTrailBuilder("case-003")
        builder.add_evidence("E11.9", "patient has diabetes mellitus type 2")

        trail = builder.get_trail()
        assert "E11.9" in trail.evidence_spans
        assert len(trail.evidence_spans["E11.9"]) == 1
        assert "diabetes mellitus" in trail.evidence_spans["E11.9"][0]

    def test_audit_trail_builder_has_all_stages(self) -> None:
        """has_all_stages is True only when all 4 core stages are recorded."""
        builder = AuditTrailBuilder("case-004")

        # Only 2 stages recorded — should be False
        builder.record_stage("ingestion", 10.0, "in", "out")
        builder.record_stage("ner", 15.0, "in", "out")
        assert builder.has_all_stages is False

        # Add the remaining 2 — should become True
        builder.record_stage("rag", 50.0, "in", "out")
        builder.record_stage("cdi", 30.0, "in", "out")
        assert builder.has_all_stages is True

    def test_audit_trail_builder_get_trail(self) -> None:
        """get_trail returns an AuditTrail Pydantic model with case_id and stages."""
        builder = AuditTrailBuilder("case-005")
        builder.record_stage("ingestion", 5.0, "text", "doc")

        trail = builder.get_trail()
        assert isinstance(trail, AuditTrail)
        assert trail.case_id == "case-005"
        assert len(trail.stages) == 1


# ------------------------------------------------------------------
# capture_cot_and_json tests
# ------------------------------------------------------------------


class TestCaptureCotAndJson:
    """Tests for the capture_cot_and_json utility."""

    def test_capture_cot_valid_json(self) -> None:
        """Input with embedded JSON returns full text as cot and extracted JSON."""
        raw = 'The patient has diabetes. {"code": "E11.9", "confidence": 0.9} end'
        cot, json_str = capture_cot_and_json(raw)

        assert cot == raw
        assert json_str == '{"code": "E11.9", "confidence": 0.9}'

    def test_capture_cot_no_json(self) -> None:
        """Input with no braces returns full text as cot and empty string."""
        raw = "The patient has diabetes with no structured output"
        cot, json_str = capture_cot_and_json(raw)

        assert cot == raw
        assert json_str == ""

    def test_capture_cot_nested_json(self) -> None:
        """Input with nested JSON braces extracts the outermost JSON object."""
        raw = 'reasoning {"outer": {"inner": "value"}, "key": 1} done'
        cot, json_str = capture_cot_and_json(raw)

        assert cot == raw
        assert json_str == '{"outer": {"inner": "value"}, "key": 1}'


# ------------------------------------------------------------------
# link_evidence_spans tests
# ------------------------------------------------------------------


class TestLinkEvidenceSpans:
    """Tests for the link_evidence_spans utility."""

    def test_link_evidence_spans_from_coding_result(
        self,
        sample_coding_result: CodingResult,
        sample_clinical_text: str,
    ) -> None:
        """Creates a dict mapping both codes to text spans."""
        evidence = link_evidence_spans(sample_coding_result, sample_clinical_text)

        assert "E11.9" in evidence
        assert "I10" in evidence

        # Each code should have at least 1 span (the primary evidence_text)
        assert len(evidence["E11.9"]) >= 1
        assert len(evidence["I10"]) >= 1

        # Primary span should be present
        assert "diabetes mellitus" in evidence["E11.9"][0]
        assert "hypertension" in evidence["I10"][0]

    def test_link_evidence_spans_empty_coding(self) -> None:
        """CodingResult with None principal returns empty dict."""
        coding_result = CodingResult(
            principal_diagnosis=None,
            secondary_codes=[],
            complication_codes=[],
        )
        evidence = link_evidence_spans(coding_result, "some clinical text here")
        assert evidence == {}


# ------------------------------------------------------------------
# build_retrieval_log tests
# ------------------------------------------------------------------


class TestBuildRetrievalLog:
    """Tests for the build_retrieval_log utility."""

    def test_build_retrieval_log(self) -> None:
        """Build a RetrievalLog from sample data, verify all fields populated."""
        top_k = [
            {"code": "E11.9", "description": "Type 2 DM", "score": 0.9},
            {"code": "E11.65", "description": "Type 2 DM with hyperglycemia", "score": 0.8},
        ]
        reranked = [
            {"code": "E11.9", "description": "Type 2 DM", "rerank_score": 0.95},
        ]

        log = build_retrieval_log(
            query="diabetes mellitus type 2",
            top_k_results=top_k,
            reranked_results=reranked,
            selected_code="E11.9",
            selected_confidence=0.95,
        )

        assert isinstance(log, RetrievalLog)
        assert log.query == "diabetes mellitus type 2"
        assert len(log.top_k_results) == 2
        assert len(log.reranked_results) == 1
        assert log.selected_code == "E11.9"
        assert log.selected_confidence == 0.95

    def test_build_retrieval_log_empty_results(self) -> None:
        """Empty top_k and reranked creates a RetrievalLog without error."""
        log = build_retrieval_log(
            query="some query",
            top_k_results=[],
            reranked_results=[],
            selected_code="Z00.00",
            selected_confidence=0.5,
        )

        assert isinstance(log, RetrievalLog)
        assert log.top_k_results == []
        assert log.reranked_results == []
        assert log.selected_code == "Z00.00"
