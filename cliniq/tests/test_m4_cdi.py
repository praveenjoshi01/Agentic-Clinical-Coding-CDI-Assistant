"""
Unit tests for the CDI agent module (m4_cdi).

Covers:
- calculate_completeness_score: various gap/conflict combinations, clamping, zero codes
- _extract_entity_qualifiers: qualifier extraction from NLU + coding results
- run_cdi_analysis: empty coding, no-LLM mode with KG gap detection
- generate_physician_query (slow): LLM-based query generation
- run_cdi_analysis full (slow): end-to-end CDI analysis with LLM queries

Non-model tests run without model downloads.
Slow tests require Qwen model and are marked @pytest.mark.slow.
"""

import pytest

from cliniq.models.cdi import CDIReport, DocumentationGap
from cliniq.models.coding import CodeSuggestion, CodingResult
from cliniq.models.entities import ClinicalEntity, NLUResult
from cliniq.modules.m4_cdi import (
    _extract_entity_qualifiers,
    calculate_completeness_score,
    run_cdi_analysis,
)


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture
def sample_nlu_result() -> NLUResult:
    """NLUResult with 3 entities: diabetes, hypertension, neuropathy."""
    return NLUResult(
        entities=[
            ClinicalEntity(
                text="diabetes mellitus",
                entity_type="diagnosis",
                start_char=0,
                end_char=17,
                confidence=0.92,
                negated=False,
                qualifiers=["type 2"],
            ),
            ClinicalEntity(
                text="hypertension",
                entity_type="diagnosis",
                start_char=22,
                end_char=34,
                confidence=0.89,
                negated=False,
                qualifiers=["essential"],
            ),
            ClinicalEntity(
                text="neuropathy",
                entity_type="diagnosis",
                start_char=40,
                end_char=50,
                confidence=0.85,
                negated=False,
                qualifiers=["peripheral"],
            ),
        ],
        processing_time_ms=15.0,
    )


@pytest.fixture
def sample_coding_result() -> CodingResult:
    """CodingResult with E11.40 as principal, I10 as secondary."""
    return CodingResult(
        principal_diagnosis=CodeSuggestion(
            icd10_code="E11.40",
            description="Type 2 diabetes mellitus with diabetic neuropathy, unspecified",
            confidence=0.88,
            evidence_text="diabetes mellitus",
            reasoning="Patient has documented diabetes with neuropathy",
            needs_specificity=True,
            alternatives=[],
        ),
        secondary_codes=[
            CodeSuggestion(
                icd10_code="I10",
                description="Essential (primary) hypertension",
                confidence=0.82,
                evidence_text="hypertension",
                reasoning="Documented elevated blood pressure",
                needs_specificity=False,
                alternatives=[],
            ),
        ],
        complication_codes=[],
        sequencing_rationale="Diabetes principal by confidence",
        retrieval_stats={"total_entities_coded": 2},
    )


@pytest.fixture
def sample_clinical_text() -> str:
    """Short clinical note text for testing."""
    return (
        "Patient is a 62-year-old male with type 2 diabetes mellitus and "
        "peripheral neuropathy. Also has essential hypertension controlled "
        "on lisinopril. Presents with numbness in bilateral feet."
    )


# ------------------------------------------------------------------
# Non-model tests (no @pytest.mark.slow)
# ------------------------------------------------------------------


class TestCalculateCompletenessScore:
    """Tests for the calculate_completeness_score function."""

    def test_no_issues(self) -> None:
        """0 gaps, 0 conflicts, 5 codes -> score = 1.0."""
        score = calculate_completeness_score(gaps=[], conflicts=[], total_codes=5)
        assert score == 1.0

    def test_with_gaps(self) -> None:
        """2 gaps, 0 conflicts -> score = 0.8."""
        score = calculate_completeness_score(
            gaps=["g1", "g2"], conflicts=[], total_codes=5
        )
        assert score == pytest.approx(0.8)

    def test_with_conflicts(self) -> None:
        """0 gaps, 2 conflicts -> score = 0.7."""
        score = calculate_completeness_score(
            gaps=[], conflicts=["c1", "c2"], total_codes=5
        )
        assert score == pytest.approx(0.7)

    def test_clamped(self) -> None:
        """10 gaps, 5 conflicts -> score = 0.0 (clamped, not negative)."""
        score = calculate_completeness_score(
            gaps=list(range(10)),
            conflicts=list(range(5)),
            total_codes=5,
        )
        assert score == 0.0

    def test_zero_codes(self) -> None:
        """0 total codes -> score = 1.0."""
        score = calculate_completeness_score(
            gaps=["g1"], conflicts=["c1"], total_codes=0
        )
        assert score == 1.0


class TestExtractEntityQualifiers:
    """Tests for _extract_entity_qualifiers helper."""

    def test_extract_qualifiers(self) -> None:
        """Build NLUResult with 2 entities and matching CodingResult. Verify qualifier dict."""
        nlu = NLUResult(
            entities=[
                ClinicalEntity(
                    text="diabetes mellitus",
                    entity_type="diagnosis",
                    start_char=0,
                    end_char=17,
                    confidence=0.9,
                    qualifiers=["type 2"],
                ),
                ClinicalEntity(
                    text="hypertension",
                    entity_type="diagnosis",
                    start_char=20,
                    end_char=32,
                    confidence=0.85,
                    qualifiers=["essential"],
                ),
            ],
            processing_time_ms=10.0,
        )

        coding = CodingResult(
            principal_diagnosis=CodeSuggestion(
                icd10_code="E11.9",
                description="Type 2 diabetes without complications",
                confidence=0.88,
                evidence_text="diabetes mellitus",
                reasoning="Documented DM",
                needs_specificity=False,
                alternatives=[],
            ),
            secondary_codes=[
                CodeSuggestion(
                    icd10_code="I10",
                    description="Essential hypertension",
                    confidence=0.82,
                    evidence_text="hypertension",
                    reasoning="Documented HTN",
                    needs_specificity=False,
                    alternatives=[],
                ),
            ],
            complication_codes=[],
        )

        qualifiers = _extract_entity_qualifiers(nlu, coding)

        assert "E11.9" in qualifiers
        assert "I10" in qualifiers
        assert "type 2" in qualifiers["E11.9"]
        assert "essential" in qualifiers["I10"]


class TestRunCdiAnalysis:
    """Tests for run_cdi_analysis orchestrator."""

    def test_empty_coding(self) -> None:
        """Empty CodingResult (no codes) -> CDIReport with 0 gaps, 0 conflicts, completeness 1.0."""
        nlu = NLUResult(entities=[], processing_time_ms=5.0)
        coding = CodingResult(
            principal_diagnosis=None,
            secondary_codes=[],
            complication_codes=[],
        )

        report = run_cdi_analysis(nlu, coding, "", use_llm_queries=False)

        assert isinstance(report, CDIReport)
        assert report.gap_count == 0
        assert report.conflict_count == 0
        assert report.completeness_score == 1.0
        assert report.processing_time_ms >= 0

    def test_no_llm(
        self,
        sample_nlu_result: NLUResult,
        sample_coding_result: CodingResult,
        sample_clinical_text: str,
    ) -> None:
        """CDI analysis with use_llm_queries=False uses template fallback for physician queries."""
        report = run_cdi_analysis(
            sample_nlu_result,
            sample_coding_result,
            sample_clinical_text,
            use_llm_queries=False,
        )

        assert isinstance(report, CDIReport)
        assert 0.0 <= report.completeness_score <= 1.0
        assert report.processing_time_ms > 0

        # Any gaps should have template-style queries (not LLM generated)
        for gap in report.documentation_gaps:
            assert isinstance(gap, DocumentationGap)
            assert gap.physician_query  # Non-empty
            assert gap.code  # Has code
            assert gap.missing_qualifier  # Has qualifier
            # Template queries use "Can you please clarify" pattern
            assert "clarify" in gap.physician_query.lower()
            # No CoT trace for template fallback
            assert gap.cot_trace == ""


# ------------------------------------------------------------------
# Model-requiring tests (@pytest.mark.slow)
# ------------------------------------------------------------------


@pytest.mark.slow
class TestGeneratePhysicianQueryWithLLM:
    """Tests requiring Qwen model download."""

    def test_generate_physician_query_with_llm(self) -> None:
        """Generate physician query for E11.40 missing laterality."""
        from cliniq.modules.m4_cdi import generate_physician_query

        gap = {
            "code": "E11.40",
            "description": "Type 2 diabetes mellitus with diabetic neuropathy, unspecified",
            "missing_qualifier": "laterality",
        }
        clinical_context = (
            "Patient presents with type 2 diabetes and peripheral neuropathy "
            "affecting the lower extremities."
        )

        query_text, cot_trace = generate_physician_query(gap, clinical_context)

        assert isinstance(query_text, str)
        assert len(query_text) > 0
        assert isinstance(cot_trace, str)
        assert len(cot_trace) > 0  # CoT trace should be non-empty from LLM

    def test_run_cdi_analysis_full(
        self,
        sample_nlu_result: NLUResult,
        sample_coding_result: CodingResult,
        sample_clinical_text: str,
    ) -> None:
        """Full CDI analysis with LLM queries on synthetic data."""
        report = run_cdi_analysis(
            sample_nlu_result,
            sample_coding_result,
            sample_clinical_text,
            use_llm_queries=True,
        )

        assert isinstance(report, CDIReport)
        assert 0.0 <= report.completeness_score <= 1.0
        assert report.processing_time_ms > 0

        # Verify any gaps have physician queries
        for gap in report.documentation_gaps:
            assert gap.physician_query
            # LLM queries should have CoT trace
            assert isinstance(gap.cot_trace, str)
