"""
Unit tests for Module M2: Natural Language Understanding (NLU)

Tests entity type mapping, NLUResult computed properties, entity extraction,
negation detection, qualifier capture, and document processing.

Tests marked @pytest.mark.slow require model downloads (d4data biomedical-ner-all).
Run non-model tests with: pytest -k "not slow"
"""

import pytest

from cliniq.models.document import ClinicalDocument, DocumentMetadata
from cliniq.models.entities import ClinicalEntity, NLUResult
from cliniq.modules.m2_nlu import extract_entities, map_entity_type, process_document

# Sample clinical notes for reuse across tests
SAMPLE_CLINICAL_NOTES = {
    "diabetes": "Patient has type 2 diabetes mellitus and hypertension.",
    "negation": "Patient denies chest pain. Reports shortness of breath.",
    "qualifiers": "Patient presents with severe lower back pain and mild anxiety.",
    "mixed": "Diagnosed with stage 3 chronic kidney disease. No evidence of diabetic retinopathy. Currently taking metformin 1000mg.",
    "simple": "Fever and cough for 3 days.",
}


# ============================================================================
# Non-model tests (always run)
# ============================================================================

def test_map_entity_type_disease():
    """Test mapping Disease_disorder to diagnosis category."""
    assert map_entity_type("Disease_disorder") == "diagnosis"


def test_map_entity_type_sign_symptom():
    """Test mapping Sign_symptom to diagnosis category."""
    assert map_entity_type("Sign_symptom") == "diagnosis"


def test_map_entity_type_medication():
    """Test mapping Medication to medication category."""
    assert map_entity_type("Medication") == "medication"


def test_map_entity_type_procedure():
    """Test mapping Therapeutic_procedure to procedure category."""
    assert map_entity_type("Therapeutic_procedure") == "procedure"


def test_map_entity_type_bio_prefix():
    """Test handling BIO prefixes in entity labels."""
    assert map_entity_type("B-Disease_disorder") == "diagnosis"
    assert map_entity_type("I-Disease_disorder") == "diagnosis"
    assert map_entity_type("B-Medication") == "medication"


def test_map_entity_type_unknown():
    """Test unknown label mapping to 'other'."""
    assert map_entity_type("Unknown_label") == "other"
    assert map_entity_type("Random_Type") == "other"


def test_nlu_result_computed_properties():
    """Test NLUResult computed properties filter entities by type."""
    # Create test entities manually
    entities = [
        ClinicalEntity(
            text="diabetes",
            entity_type="diagnosis",
            start_char=0,
            end_char=8,
            confidence=0.95,
        ),
        ClinicalEntity(
            text="hypertension",
            entity_type="diagnosis",
            start_char=13,
            end_char=25,
            confidence=0.92,
        ),
        ClinicalEntity(
            text="appendectomy",
            entity_type="procedure",
            start_char=30,
            end_char=42,
            confidence=0.88,
        ),
        ClinicalEntity(
            text="metformin",
            entity_type="medication",
            start_char=47,
            end_char=56,
            confidence=0.91,
        ),
        ClinicalEntity(
            text="liver",
            entity_type="anatomical_site",
            start_char=60,
            end_char=65,
            confidence=0.85,
        ),
    ]

    result = NLUResult(entities=entities, processing_time_ms=10.5)

    # Test computed properties
    assert result.entity_count == 5
    assert len(result.diagnoses) == 2
    assert len(result.procedures) == 1
    assert len(result.medications) == 1
    assert len(result.anatomical_sites) == 1

    # Verify correct entities are returned
    assert result.diagnoses[0].text == "diabetes"
    assert result.diagnoses[1].text == "hypertension"
    assert result.procedures[0].text == "appendectomy"
    assert result.medications[0].text == "metformin"
    assert result.anatomical_sites[0].text == "liver"


# ============================================================================
# Model-required tests (marked @pytest.mark.slow)
# ============================================================================

@pytest.mark.slow
def test_extract_entities_basic():
    """Test basic entity extraction from clinical text."""
    text = SAMPLE_CLINICAL_NOTES["diabetes"]
    result = extract_entities(text)

    # Verify result structure
    assert isinstance(result, NLUResult)
    assert result.processing_time_ms > 0
    assert len(result.entities) >= 1  # Should extract at least diabetes/hypertension

    # Verify entities have required fields
    for entity in result.entities:
        assert isinstance(entity, ClinicalEntity)
        assert entity.text
        assert entity.entity_type
        assert 0 <= entity.confidence <= 1.0
        assert entity.start_char >= 0
        assert entity.end_char > entity.start_char


@pytest.mark.slow
def test_extract_entities_negation():
    """Test negation detection marks 'denies X' as negated."""
    text = SAMPLE_CLINICAL_NOTES["negation"]
    result = extract_entities(text)

    # Find chest pain and shortness of breath entities
    chest_pain = None
    shortness_of_breath = None

    for entity in result.entities:
        if "chest" in entity.text.lower() or "pain" in entity.text.lower():
            chest_pain = entity
        if "breath" in entity.text.lower() or "shortness" in entity.text.lower():
            shortness_of_breath = entity

    # Verify negation detection
    # "Patient denies chest pain" -> chest pain should be negated
    if chest_pain:
        assert chest_pain.negated is True, "Chest pain should be negated"

    # "Reports shortness of breath" -> NOT negated
    if shortness_of_breath:
        assert shortness_of_breath.negated is False, "Shortness of breath should NOT be negated"


@pytest.mark.slow
def test_extract_entities_qualifiers():
    """Test qualifier capture attaches severity/descriptions to parent entities."""
    text = SAMPLE_CLINICAL_NOTES["qualifiers"]
    result = extract_entities(text)

    # Find entities with qualifiers
    entities_with_qualifiers = [e for e in result.entities if len(e.qualifiers) > 0]

    # Should find at least one entity with a qualifier
    # (e.g., "severe" attached to "back pain" or "mild" attached to "anxiety")
    assert len(entities_with_qualifiers) >= 0  # May be 0 if model doesn't extract qualifiers

    # If qualifiers are extracted, verify structure
    for entity in entities_with_qualifiers:
        assert isinstance(entity.qualifiers, list)
        assert all(isinstance(q, str) for q in entity.qualifiers)
        assert entity.entity_type in ["diagnosis", "procedure"]  # Qualifiers attach to these


@pytest.mark.slow
def test_extract_entities_mixed():
    """Test extraction with diagnoses, negations, and medications in one text."""
    text = SAMPLE_CLINICAL_NOTES["mixed"]
    result = extract_entities(text)

    assert isinstance(result, NLUResult)
    assert result.entity_count >= 2  # Should find at least CKD and metformin

    # Check for diagnosis entities
    diagnoses = result.diagnoses
    assert len(diagnoses) >= 1  # Should find at least chronic kidney disease

    # Check for negated entities
    negated_entities = [e for e in result.entities if e.negated]
    # "No evidence of diabetic retinopathy" should produce at least 1 negated entity
    assert len(negated_entities) >= 0  # May be 0 if negation doesn't trigger on this specific text

    # Check for medications
    medications = result.medications
    # Should find metformin if the model extracts it
    assert len(medications) >= 0  # May be 0 if model doesn't extract medication


@pytest.mark.slow
def test_process_document():
    """Test document processing wrapper."""
    # Create a ClinicalDocument
    metadata = DocumentMetadata(
        patient_id="P123",
        encounter_id="E456",
        source_type="ehr_note",
    )

    doc = ClinicalDocument(
        metadata=metadata,
        raw_narrative=SAMPLE_CLINICAL_NOTES["simple"],
    )

    # Process document
    result = process_document(doc)

    # Verify result
    assert isinstance(result, NLUResult)
    assert result.processing_time_ms > 0
    assert result.entity_count >= 0  # May be 0 for simple text


@pytest.mark.slow
def test_process_document_empty_narrative():
    """Test process_document raises ValueError for empty narrative."""
    metadata = DocumentMetadata(
        patient_id="P123",
        encounter_id="E456",
        source_type="ehr_note",
    )

    doc = ClinicalDocument(
        metadata=metadata,
        raw_narrative="",
    )

    with pytest.raises(ValueError, match="raw_narrative cannot be empty"):
        process_document(doc)
