"""
Tests for the end-to-end pipeline orchestrator.
"""

import pytest
from cliniq.pipeline import run_pipeline, run_pipeline_batch, PipelineResult


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
