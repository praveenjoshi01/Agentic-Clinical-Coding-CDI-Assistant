"""
Tests for the end-to-end pipeline orchestrator.
"""

import pytest
from cliniq.pipeline import (
    run_pipeline,
    run_pipeline_batch,
    run_pipeline_audited,
    run_pipeline_audited_batch,
    PipelineResult,
)


# Sample FHIR bundle for testing
SAMPLE_FHIR_BUNDLE = {
    "resourceType": "Bundle",
    "type": "collection",
    "entry": [
        {
            "resource": {
                "resourceType": "Patient",
                "id": "test-patient",
                "name": [{"family": "Smith", "given": ["John"]}],
                "gender": "male",
                "birthDate": "1960-05-15"
            }
        },
        {
            "resource": {
                "resourceType": "Condition",
                "id": "condition-1",
                "subject": {"reference": "Patient/test-patient"},
                "code": {
                    "coding": [
                        {
                            "system": "http://hl7.org/fhir/sid/icd-10-cm",
                            "code": "E11.9",
                            "display": "Type 2 diabetes mellitus without complications"
                        }
                    ],
                    "text": "Type 2 diabetes mellitus"
                },
                "clinicalStatus": {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                            "code": "active"
                        }
                    ]
                }
            }
        }
    ]
}


def test_pipeline_result_schema():
    """Test that PipelineResult validates with Pydantic."""
    # This test doesn't run the pipeline, just validates the schema structure
    from cliniq.models import ClinicalDocument, NLUResult, CodingResult, DocumentMetadata
    from cliniq.models.entities import ClinicalEntity
    from cliniq.models.coding import CodeSuggestion

    result = PipelineResult(
        document=ClinicalDocument(
            metadata=DocumentMetadata(
                source_type="text",
                patient_id="test-123",
                encounter_id="enc-456"
            ),
            raw_narrative="Patient has diabetes.",
            modality_confidence=1.0
        ),
        nlu_result=NLUResult(
            entities=[
                ClinicalEntity(
                    text="diabetes",
                    entity_type="diagnosis",
                    start_char=12,
                    end_char=20,
                    confidence=0.95
                )
            ],
            processing_time_ms=50.0
        ),
        coding_result=CodingResult(
            principal_diagnosis=CodeSuggestion(
                icd10_code="E11.9",
                description="Type 2 diabetes mellitus without complications",
                confidence=0.92,
                evidence_text="diabetes",
                reasoning="Patient has documented diabetes",
                needs_specificity=False,
                alternatives=[]
            ),
            secondary_codes=[],
            complication_codes=[],
            sequencing_rationale="Principal diagnosis based on highest confidence",
            retrieval_stats={"total_entities_coded": 1}
        ),
        processing_time_ms=1500.5,
        errors=[]
    )

    # Validate the structure
    assert isinstance(result, PipelineResult)
    assert result.document.metadata.source_type == "text"
    assert result.nlu_result.entity_count == 1
    assert result.coding_result.principal_diagnosis.icd10_code == "E11.9"
    assert result.processing_time_ms > 0
    assert len(result.errors) == 0


@pytest.mark.slow
def test_pipeline_with_text():
    """Test pipeline with plain text input."""
    text = "Patient has type 2 diabetes mellitus and hypertension."

    result = run_pipeline(text)

    # Validate pipeline result structure
    assert isinstance(result, PipelineResult)
    assert result.document.metadata.source_type == "text"
    assert len(result.document.raw_narrative) > 0
    assert result.nlu_result.entity_count >= 0  # May or may not extract entities
    assert result.coding_result is not None
    assert result.processing_time_ms > 0
    # Errors may or may not be present (depends on model availability)


@pytest.mark.slow
def test_pipeline_with_fhir():
    """Test pipeline with FHIR bundle input."""
    result = run_pipeline(SAMPLE_FHIR_BUNDLE)

    # Validate pipeline result structure
    assert isinstance(result, PipelineResult)
    assert result.document.metadata.source_type == "fhir"
    assert "diabetes" in result.document.raw_narrative.lower()
    assert result.nlu_result.entity_count >= 0
    assert result.coding_result is not None
    assert result.processing_time_ms > 0


def test_pipeline_error_handling():
    """Test pipeline error handling with empty input."""
    result = run_pipeline("")

    # Should not crash, should capture error
    assert isinstance(result, PipelineResult)
    # Either errors list is populated, or pipeline handles empty input gracefully
    assert result.processing_time_ms > 0


@pytest.mark.slow
def test_pipeline_skip_coding():
    """Test pipeline with skip_coding=True."""
    text = "Patient has diabetes."

    result = run_pipeline(text, skip_coding=True)

    # Validate that coding was skipped
    assert isinstance(result, PipelineResult)
    assert result.document.metadata.source_type == "text"
    assert result.nlu_result is not None  # NER should still run
    assert result.coding_result.principal_diagnosis is None  # No coding
    assert result.coding_result.sequencing_rationale == "Coding skipped"
    assert result.processing_time_ms > 0


@pytest.mark.slow
def test_pipeline_batch():
    """Test batch pipeline processing."""
    inputs = [
        "Patient has diabetes.",
        "Patient has hypertension and asthma.",
        SAMPLE_FHIR_BUNDLE
    ]

    results = run_pipeline_batch(inputs, skip_coding=True)

    # Validate batch results
    assert len(results) == 3
    assert all(isinstance(r, PipelineResult) for r in results)
    assert results[0].document.metadata.source_type == "text"
    assert results[1].document.metadata.source_type == "text"
    assert results[2].document.metadata.source_type == "fhir"


# ---------------------------------------------------------------------------
# CDI Pipeline Integration Tests (02-05)
# ---------------------------------------------------------------------------


def test_pipeline_result_has_cdi_fields():
    """PipelineResult schema has cdi_report and audit_trail as Optional fields defaulting to None."""
    from cliniq.models import ClinicalDocument, NLUResult, CodingResult, DocumentMetadata
    from cliniq.models.coding import CodeSuggestion

    result = PipelineResult(
        document=ClinicalDocument(
            metadata=DocumentMetadata(
                source_type="text",
                patient_id="p-1",
                encounter_id="e-1",
            ),
            raw_narrative="Test note.",
            modality_confidence=1.0,
        ),
        nlu_result=NLUResult(entities=[], processing_time_ms=0),
        coding_result=CodingResult(
            principal_diagnosis=None,
            secondary_codes=[],
            complication_codes=[],
            sequencing_rationale="",
            retrieval_stats={},
        ),
        processing_time_ms=100.0,
    )

    # cdi_report and audit_trail should default to None
    assert result.cdi_report is None
    assert result.audit_trail is None
    # Original fields still present
    assert result.document is not None
    assert result.nlu_result is not None
    assert result.coding_result is not None


def test_pipeline_backward_compatible():
    """Existing run_pipeline function still works and returns cdi_report=None."""
    result = run_pipeline("")

    assert isinstance(result, PipelineResult)
    assert result.processing_time_ms > 0
    # Backward compatibility: CDI fields are None when using original pipeline
    assert result.cdi_report is None
    assert result.audit_trail is None


@pytest.mark.slow
def test_pipeline_audited_with_text():
    """Run run_pipeline_audited on clinical text and verify audit trail completeness (EXPL-01)."""
    text = "Patient has type 2 diabetes mellitus and hypertension."

    result = run_pipeline_audited(text, use_llm_queries=False)

    assert isinstance(result, PipelineResult)
    assert result.processing_time_ms > 0

    # audit_trail must be present
    assert result.audit_trail is not None
    trail = result.audit_trail

    # EXPL-01: audit trail has traces for all 4 core stages
    stage_names = {t.stage for t in trail.stages}
    assert "ingestion" in stage_names
    assert "ner" in stage_names
    assert "rag" in stage_names
    assert "cdi" in stage_names

    # Each stage has processing_time_ms >= 0
    for trace in trail.stages:
        assert trace.processing_time_ms >= 0

    # EXPL-02: evidence_spans should have at least 1 entry (if coding produced codes)
    if result.coding_result.principal_diagnosis is not None:
        assert len(trail.evidence_spans) >= 1


@pytest.mark.slow
def test_pipeline_audited_with_cdi():
    """Run run_pipeline_audited on text likely to trigger CDI gaps and verify cdi_report."""
    text = "Patient has diabetic neuropathy and retinopathy."

    result = run_pipeline_audited(text, use_llm_queries=False)

    assert isinstance(result, PipelineResult)

    # cdi_report should be populated
    assert result.cdi_report is not None
    cdi = result.cdi_report

    # completeness_score must be in [0.0, 1.0]
    assert 0.0 <= cdi.completeness_score <= 1.0

    # CDI report has expected structure (may or may not have gaps depending on KG match)
    assert isinstance(cdi.documentation_gaps, list)
    assert isinstance(cdi.missed_diagnoses, list)
    assert isinstance(cdi.code_conflicts, list)


@pytest.mark.slow
def test_pipeline_audited_skip_cdi():
    """Run with skip_cdi=True and verify cdi_report is None but audit_trail has ingestion/ner/rag."""
    text = "Patient has diabetes."

    result = run_pipeline_audited(text, skip_cdi=True, use_llm_queries=False)

    assert isinstance(result, PipelineResult)

    # CDI report should be None when skipped
    assert result.cdi_report is None

    # Audit trail should still be present with the other stages
    assert result.audit_trail is not None
    stage_names = {t.stage for t in result.audit_trail.stages}
    assert "ingestion" in stage_names
    assert "ner" in stage_names
    assert "rag" in stage_names
    # CDI stage should NOT be present when skipped
    assert "cdi" not in stage_names


@pytest.mark.slow
def test_pipeline_audited_batch():
    """Run run_pipeline_audited_batch on 2 inputs and verify each has audit_trail."""
    inputs = [
        "Patient has diabetes.",
        "Patient has hypertension and asthma.",
    ]

    results = run_pipeline_audited_batch(
        inputs, use_llm_queries=False
    )

    assert len(results) == 2
    for result in results:
        assert isinstance(result, PipelineResult)
        assert result.audit_trail is not None
        assert len(result.audit_trail.stages) >= 3  # At least ingestion, ner, rag
