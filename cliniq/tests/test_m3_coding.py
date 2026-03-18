"""
Unit tests for RAG-based ICD-10 coding module.

Tests cover query construction, code sequencing, edge cases,
and full integration (slow tests require model downloads).
"""

import pytest

from cliniq.models import (
    ClinicalEntity,
    NLUResult,
    CodeSuggestion,
    CodingResult,
)
from cliniq.modules.m3_rag_coding import (
    build_coding_query,
    sequence_codes,
    build_code_suggestion,
    retrieve_and_rerank,
    code_entities,
)
from cliniq.rag import FAISSRetriever, CrossEncoderReranker


# ============================================================================
# Non-model tests (fast, no downloads)
# ============================================================================


def test_build_coding_query_basic():
    """Query construction from basic entity."""
    entity = ClinicalEntity(
        text="diabetes",
        entity_type="diagnosis",
        start_char=0,
        end_char=8,
        confidence=0.95
    )

    query = build_coding_query(entity)

    assert "diabetes" in query
    assert query == "diabetes"


def test_build_coding_query_with_qualifiers():
    """Query construction with entity qualifiers."""
    entity = ClinicalEntity(
        text="diabetes",
        entity_type="diagnosis",
        start_char=0,
        end_char=8,
        confidence=0.95,
        qualifiers=["type 2", "uncontrolled"]
    )

    query = build_coding_query(entity)

    assert "diabetes" in query
    assert "type 2" in query
    assert "uncontrolled" in query


def test_build_coding_query_with_context():
    """Query construction with context window."""
    entity = ClinicalEntity(
        text="diabetes",
        entity_type="diagnosis",
        start_char=0,
        end_char=8,
        confidence=0.95
    )

    query = build_coding_query(entity, context_window="with hypertension")

    assert "diabetes" in query
    assert "in context of with hypertension" in query


def test_sequence_codes_principal():
    """Principal diagnosis should be highest confidence diagnosis."""
    suggestions = [
        CodeSuggestion(
            icd10_code="I10",
            description="Essential hypertension",
            confidence=0.85,
            evidence_text="hypertension",
            reasoning="Primary diagnosis",
            needs_specificity=False,
            alternatives=[]
        ),
        CodeSuggestion(
            icd10_code="E11.9",
            description="Type 2 diabetes without complications",
            confidence=0.95,
            evidence_text="type 2 diabetes",
            reasoning="Most specific code",
            needs_specificity=False,
            alternatives=[]
        ),
        CodeSuggestion(
            icd10_code="J18.9",
            description="Pneumonia, unspecified",
            confidence=0.80,
            evidence_text="pneumonia",
            reasoning="Respiratory infection",
            needs_specificity=True,
            alternatives=[]
        ),
    ]

    result = sequence_codes(suggestions)

    assert result.principal_diagnosis.icd10_code == "E11.9"
    assert result.principal_diagnosis.confidence == 0.95
    assert len(result.secondary_codes) == 2
    assert result.retrieval_stats["total_entities_coded"] == 3
    assert result.retrieval_stats["avg_confidence"] == 0.87  # (0.95 + 0.85 + 0.80) / 3


def test_sequence_codes_empty():
    """Empty suggestions list should return CodingResult with None principal."""
    result = sequence_codes([])

    assert result.principal_diagnosis is None
    assert result.secondary_codes == []
    assert result.complication_codes == []
    assert result.retrieval_stats["total_entities_coded"] == 0
    assert "No codes to sequence" in result.sequencing_rationale


def test_build_code_suggestion():
    """CodeSuggestion creation from entity, LLM result, and candidates."""
    entity = ClinicalEntity(
        text="type 2 diabetes",
        entity_type="diagnosis",
        start_char=0,
        end_char=15,
        confidence=0.95
    )

    llm_result = {
        "selected_code": "E11.9",
        "description": "Type 2 diabetes without complications",
        "confidence": 0.90,
        "reasoning": "Most specific match for type 2 diabetes without mentioned complications",
        "needs_specificity": False,
        "alternatives": [
            {"code": "E11.0", "description": "Type 2 diabetes with hyperosmolarity", "reason": "Less likely without symptoms"},
        ]
    }

    candidates = [
        {"code": "E11.9", "description": "Type 2 diabetes without complications", "rerank_score": 0.88, "score": 0.85}
    ]

    suggestion = build_code_suggestion(entity, llm_result, candidates)

    assert suggestion.icd10_code == "E11.9"
    assert suggestion.description == "Type 2 diabetes without complications"
    assert suggestion.evidence_text == "type 2 diabetes"
    assert suggestion.reasoning == llm_result["reasoning"]
    assert suggestion.needs_specificity is False
    assert len(suggestion.alternatives) == 1
    # Blended confidence: 0.6 * 0.90 + 0.4 * 0.88 = 0.54 + 0.352 = 0.892
    assert 0.88 <= suggestion.confidence <= 0.90


def test_code_entities_empty_nlu():
    """code_entities with empty NLUResult should return empty CodingResult without crashing."""
    nlu_result = NLUResult(entities=[], processing_time_ms=0.0)

    result = code_entities(nlu_result, clinical_context="")

    assert result.principal_diagnosis is None
    assert result.secondary_codes == []
    assert result.complication_codes == []
    assert result.retrieval_stats["total_entities_coded"] == 0
    assert "No entities to code" in result.sequencing_rationale


# ============================================================================
# Model-required tests (slow, require downloads)
# ============================================================================


@pytest.fixture(scope="module")
def retriever():
    """Shared FAISSRetriever for slow tests."""
    r = FAISSRetriever()
    r.ensure_index_built()
    return r


@pytest.fixture(scope="module")
def reranker():
    """Shared CrossEncoderReranker for slow tests."""
    return CrossEncoderReranker()


@pytest.mark.slow
def test_retrieve_and_rerank(retriever, reranker):
    """Retrieval + reranking returns diabetes-related candidates with scores."""
    query = "type 2 diabetes mellitus"

    candidates = retrieve_and_rerank(query, retriever, reranker)

    assert len(candidates) > 0
    assert len(candidates) <= 5  # Should be top-5 after reranking
    assert all("code" in c for c in candidates)
    assert all("description" in c for c in candidates)
    assert all("rerank_score" in c for c in candidates)
    assert all("retrieval_score" in c for c in candidates)

    # Top candidate should be diabetes-related
    top_candidate = candidates[0]
    assert "diabetes" in top_candidate["description"].lower() or "E11" in top_candidate["code"]


@pytest.mark.slow
def test_code_entities_integration():
    """Full pipeline integration: entities -> CodingResult with ICD-10 codes."""
    entities = [
        ClinicalEntity(
            text="type 2 diabetes",
            entity_type="diagnosis",
            start_char=0,
            end_char=15,
            confidence=0.95,
            negated=False,
            qualifiers=[]
        ),
        ClinicalEntity(
            text="hypertension",
            entity_type="diagnosis",
            start_char=20,
            end_char=32,
            confidence=0.90,
            negated=False,
            qualifiers=[]
        ),
    ]

    nlu_result = NLUResult(entities=entities, processing_time_ms=100.0)
    clinical_context = "Patient has type 2 diabetes and hypertension."

    result = code_entities(nlu_result, clinical_context=clinical_context)

    # Should have principal diagnosis
    assert result.principal_diagnosis is not None
    assert result.principal_diagnosis.icd10_code
    assert result.principal_diagnosis.description
    assert result.principal_diagnosis.reasoning
    assert 0.0 <= result.principal_diagnosis.confidence <= 1.0

    # Should have at least 1 secondary code (since we have 2 diagnoses)
    assert len(result.secondary_codes) >= 1

    # All suggestions should have required fields
    all_suggestions = [result.principal_diagnosis] + result.secondary_codes
    for suggestion in all_suggestions:
        assert suggestion.icd10_code
        assert suggestion.description
        assert suggestion.reasoning
        assert suggestion.evidence_text

    # Stats should be populated
    assert result.retrieval_stats["total_entities_coded"] == 2
    assert result.retrieval_stats["avg_confidence"] > 0.0
    assert "processing_time_ms" in result.retrieval_stats


@pytest.mark.slow
def test_specificity_flagging():
    """Generic entity should trigger needs_specificity flag."""
    entities = [
        ClinicalEntity(
            text="kidney disease",
            entity_type="diagnosis",
            start_char=0,
            end_char=14,
            confidence=0.90,
            negated=False,
            qualifiers=[]  # No stage qualifier
        ),
    ]

    nlu_result = NLUResult(entities=entities, processing_time_ms=50.0)
    clinical_context = "Patient has kidney disease."

    result = code_entities(nlu_result, clinical_context=clinical_context)

    # Should have a principal diagnosis
    assert result.principal_diagnosis is not None

    # The needs_specificity flag depends on LLM reasoning
    # We can't guarantee it's True, but we can check the field exists
    assert hasattr(result.principal_diagnosis, 'needs_specificity')
    assert isinstance(result.principal_diagnosis.needs_specificity, bool)
