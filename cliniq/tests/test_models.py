"""
Tests for Pydantic data models and configuration.

Validates schema creation, validation, computed properties, and ENTITY_TYPE_MAP.
"""

import pytest
from datetime import datetime
from cliniq.models import (
    ClinicalDocument,
    DocumentMetadata,
    ClinicalEntity,
    NLUResult,
    CodeSuggestion,
    CodingResult,
    GoldStandardCase,
    GoldStandardEntity,
    EvalResult,
    ENTITY_TYPE_MAP,
)


def test_document_metadata_creation():
    """Test DocumentMetadata creates with all fields."""
    metadata = DocumentMetadata(
        patient_id="P001",
        encounter_id="E001",
        source_type="fhir",
    )
    assert metadata.patient_id == "P001"
    assert metadata.encounter_id == "E001"
    assert metadata.source_type == "fhir"
    assert isinstance(metadata.timestamp, datetime)


def test_clinical_document_valid():
    """Test ClinicalDocument creates with valid data."""
    metadata = DocumentMetadata(
        patient_id="P001",
        encounter_id="E001",
        source_type="text",
    )
    doc = ClinicalDocument(
        metadata=metadata,
        raw_narrative="Patient presents with acute chest pain.",
        modality_confidence=0.95,
    )
    assert doc.metadata.patient_id == "P001"
    assert doc.raw_narrative == "Patient presents with acute chest pain."
    assert doc.modality_confidence == 0.95
    assert doc.structured_facts == []
    assert doc.extraction_trace == ""


def test_clinical_document_invalid_confidence():
    """Test ClinicalDocument rejects invalid modality_confidence."""
    metadata = DocumentMetadata(
        patient_id="P001",
        encounter_id="E001",
        source_type="text",
    )
    with pytest.raises(Exception):  # Pydantic ValidationError
        ClinicalDocument(
            metadata=metadata,
            raw_narrative="Test",
            modality_confidence=1.5,  # Invalid: > 1.0
        )


def test_clinical_entity_creation():
    """Test ClinicalEntity creates with all fields."""
    entity = ClinicalEntity(
        text="acute myocardial infarction",
        entity_type="diagnosis",
        start_char=10,
        end_char=37,
        confidence=0.92,
        negated=False,
        qualifiers=["acute"],
    )
    assert entity.text == "acute myocardial infarction"
    assert entity.entity_type == "diagnosis"
    assert entity.confidence == 0.92
    assert entity.negated is False
    assert entity.qualifiers == ["acute"]


def test_nlu_result_computed_properties():
    """Test NLUResult computed properties filter entities by type."""
    entities = [
        ClinicalEntity(
            text="diabetes",
            entity_type="diagnosis",
            start_char=0,
            end_char=8,
            confidence=0.95,
        ),
        ClinicalEntity(
            text="appendectomy",
            entity_type="procedure",
            start_char=10,
            end_char=22,
            confidence=0.90,
        ),
        ClinicalEntity(
            text="metformin",
            entity_type="medication",
            start_char=25,
            end_char=34,
            confidence=0.88,
        ),
    ]
    nlu_result = NLUResult(entities=entities, processing_time_ms=150.5)

    assert nlu_result.entity_count == 3
    assert len(nlu_result.diagnoses) == 1
    assert nlu_result.diagnoses[0].text == "diabetes"
    assert len(nlu_result.procedures) == 1
    assert nlu_result.procedures[0].text == "appendectomy"
    assert len(nlu_result.medications) == 1
    assert nlu_result.medications[0].text == "metformin"
    assert len(nlu_result.anatomical_sites) == 0


def test_code_suggestion_creation():
    """Test CodeSuggestion creates with all fields."""
    code = CodeSuggestion(
        icd10_code="I21.09",
        description="ST elevation myocardial infarction",
        confidence=0.89,
        evidence_text="Patient presents with chest pain and elevated troponin",
        reasoning="Elevated troponin indicates myocardial damage",
        needs_specificity=True,
        alternatives=[{"code": "I21.3", "confidence": 0.65}],
    )
    assert code.icd10_code == "I21.09"
    assert code.confidence == 0.89
    assert code.needs_specificity is True


def test_coding_result_creation():
    """Test CodingResult creates with principal and secondary codes."""
    principal = CodeSuggestion(
        icd10_code="E11.9",
        description="Type 2 diabetes mellitus",
        confidence=0.92,
        evidence_text="Patient has diabetes",
        reasoning="Chronic condition",
    )
    coding_result = CodingResult(
        principal_diagnosis=principal,
        sequencing_rationale="Type 2 diabetes is the primary condition",
    )
    assert coding_result.principal_diagnosis.icd10_code == "E11.9"
    assert coding_result.secondary_codes == []
    assert coding_result.complication_codes == []


def test_gold_standard_case_creation():
    """Test GoldStandardCase creates with all fields."""
    gold_entity = GoldStandardEntity(
        text="hypertension",
        entity_type="diagnosis",
        start_char=0,
        end_char=12,
        negated=False,
    )
    case = GoldStandardCase(
        case_id="CASE001",
        source_type="text",
        input_data="Patient has hypertension.",
        expected_entities=[gold_entity],
        expected_icd10_codes=["I10"],
        expected_principal_dx="I10",
        notes="Simple hypertension case",
    )
    assert case.case_id == "CASE001"
    assert len(case.expected_entities) == 1
    assert case.expected_principal_dx == "I10"


def test_eval_result_creation():
    """Test EvalResult creates with metrics."""
    result = EvalResult(
        module_name="NER",
        timestamp=datetime.now(),
        n_cases=10,
        metrics={"precision": 0.92, "recall": 0.88, "f1": 0.90},
        passed=True,
    )
    assert result.module_name == "NER"
    assert result.n_cases == 10
    assert result.metrics["f1"] == 0.90
    assert result.passed is True


def test_entity_type_map():
    """Test ENTITY_TYPE_MAP maps d4data labels to pipeline categories."""
    assert ENTITY_TYPE_MAP["Disease_disorder"] == "diagnosis"
    assert ENTITY_TYPE_MAP["Sign_symptom"] == "diagnosis"
    assert ENTITY_TYPE_MAP["Medication"] == "medication"
    assert ENTITY_TYPE_MAP["Therapeutic_procedure"] == "procedure"
    assert ENTITY_TYPE_MAP["Diagnostic_procedure"] == "procedure"
    assert ENTITY_TYPE_MAP["Biological_structure"] == "anatomical_site"
    assert ENTITY_TYPE_MAP["Severity"] == "qualifier"
    assert ENTITY_TYPE_MAP["Lab_value"] == "lab_value"
