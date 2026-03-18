"""
Unit tests for multi-modal ingestion module.

Tests FHIR parsing, text parsing, image parsing, modality detection, and routing.
"""

import json
import pytest
from uuid import UUID

from cliniq.modules.m1_ingest import (
    detect_modality,
    parse_fhir,
    parse_text,
    parse_image,
    ingest
)
from cliniq.models.document import ClinicalDocument


# Test fixtures
SAMPLE_FHIR_BUNDLE = {
    "resourceType": "Bundle",
    "type": "collection",
    "entry": [
        {
            "fullUrl": "urn:uuid:patient-001",
            "resource": {
                "resourceType": "Patient",
                "id": "patient-001",
                "name": [{"family": "Smith", "given": ["John"]}]
            }
        },
        {
            "fullUrl": "urn:uuid:condition-001",
            "resource": {
                "resourceType": "Condition",
                "id": "condition-001",
                "subject": {
                    "reference": "Patient/patient-001"
                },
                "code": {
                    "text": "Type 2 diabetes mellitus",
                    "coding": [
                        {
                            "system": "http://hl7.org/fhir/sid/icd-10-cm",
                            "code": "E11.9",
                            "display": "Type 2 diabetes mellitus without complications"
                        }
                    ]
                },
                "clinicalStatus": {
                    "text": "active"
                }
            }
        },
        {
            "fullUrl": "urn:uuid:procedure-001",
            "resource": {
                "resourceType": "Procedure",
                "id": "procedure-001",
                "subject": {
                    "reference": "Patient/patient-001"
                },
                "code": {
                    "text": "Hemoglobin A1c test"
                },
                "status": "completed"
            }
        }
    ]
}

SAMPLE_TEXT_NOTE = """Patient presents with uncontrolled type 2 diabetes mellitus. HbA1c is 9.2%.
Also reports chronic lower back pain. Currently on metformin 1000mg BID.
No signs of diabetic retinopathy. Blood pressure 145/92, consistent with hypertension."""


class TestDetectModality:
    """Test modality detection for different input types."""

    def test_detect_modality_text(self):
        """Plain string should be detected as text."""
        result = detect_modality("Some clinical text")
        assert result == "text"

    def test_detect_modality_fhir_dict(self):
        """Dict with resourceType should be detected as FHIR."""
        result = detect_modality({"resourceType": "Bundle", "type": "collection"})
        assert result == "fhir"

    def test_detect_modality_fhir_string(self):
        """JSON string with resourceType should be detected as FHIR."""
        fhir_json = json.dumps({"resourceType": "Bundle", "type": "collection"})
        result = detect_modality(fhir_json)
        assert result == "fhir"

    def test_detect_modality_image(self):
        """Path ending in image extension should be detected as image."""
        assert detect_modality("document.png") == "image"
        assert detect_modality("scan.jpg") == "image"
        assert detect_modality("xray.jpeg") == "image"
        assert detect_modality("report.bmp") == "image"
        assert detect_modality("file.tiff") == "image"

    def test_detect_modality_invalid_dict(self):
        """Dict without resourceType should raise ValueError."""
        with pytest.raises(ValueError, match="must have 'resourceType'"):
            detect_modality({"data": "value"})


class TestParseText:
    """Test plain text parsing."""

    def test_parse_text(self):
        """Text parsing should wrap input into ClinicalDocument."""
        doc = parse_text(SAMPLE_TEXT_NOTE)

        # Verify it's a ClinicalDocument
        assert isinstance(doc, ClinicalDocument)

        # Verify metadata
        assert doc.metadata.source_type == "text"
        assert doc.metadata.patient_id  # Should be a UUID
        assert doc.metadata.encounter_id  # Should be a UUID

        # Verify UUIDs are valid
        UUID(doc.metadata.patient_id)
        UUID(doc.metadata.encounter_id)

        # Verify content
        assert doc.raw_narrative == SAMPLE_TEXT_NOTE.strip()
        assert doc.modality_confidence == 1.0
        assert doc.extraction_trace == "Direct text input"
        assert doc.structured_facts == []


class TestParseFhir:
    """Test FHIR R4B parsing."""

    def test_parse_fhir(self):
        """FHIR parsing should extract narrative and structured facts."""
        doc = parse_fhir(SAMPLE_FHIR_BUNDLE)

        # Verify it's a ClinicalDocument
        assert isinstance(doc, ClinicalDocument)

        # Verify metadata
        assert doc.metadata.source_type == "fhir"
        assert doc.metadata.patient_id == "patient-001"

        # Verify narrative contains key terms
        assert "diabetes" in doc.raw_narrative.lower()

        # Verify structured facts extracted
        assert len(doc.structured_facts) > 0

        # Check for condition fact
        condition_facts = [f for f in doc.structured_facts if f.get("type") == "condition"]
        assert len(condition_facts) > 0
        assert condition_facts[0]["text"] == "Type 2 diabetes mellitus"

        # Check for procedure fact
        procedure_facts = [f for f in doc.structured_facts if f.get("type") == "procedure"]
        assert len(procedure_facts) > 0
        assert procedure_facts[0]["text"] == "Hemoglobin A1c test"

        # Verify confidence and trace
        assert doc.modality_confidence == 1.0
        assert "FHIR R4B" in doc.extraction_trace

    def test_parse_fhir_from_string(self):
        """FHIR parser should handle JSON string input."""
        fhir_json = json.dumps(SAMPLE_FHIR_BUNDLE)
        doc = parse_fhir(fhir_json)

        assert isinstance(doc, ClinicalDocument)
        assert doc.metadata.source_type == "fhir"
        assert "diabetes" in doc.raw_narrative.lower()


class TestIngestRouter:
    """Test the main ingest router function."""

    def test_ingest_routes_text(self):
        """Ingest should route plain text to text parser."""
        doc = ingest(SAMPLE_TEXT_NOTE)

        assert isinstance(doc, ClinicalDocument)
        assert doc.metadata.source_type == "text"
        assert doc.raw_narrative == SAMPLE_TEXT_NOTE.strip()

    def test_ingest_routes_fhir(self):
        """Ingest should route FHIR dict to FHIR parser."""
        doc = ingest(SAMPLE_FHIR_BUNDLE)

        assert isinstance(doc, ClinicalDocument)
        assert doc.metadata.source_type == "fhir"
        assert len(doc.structured_facts) > 0


class TestClinicalDocumentValidation:
    """Test Pydantic validation of ClinicalDocument."""

    def test_clinical_document_validation(self):
        """All ingested documents should pass Pydantic validation."""
        # Test with text
        text_doc = ingest(SAMPLE_TEXT_NOTE)
        assert text_doc.metadata.patient_id
        assert text_doc.metadata.encounter_id
        assert 0.0 <= text_doc.modality_confidence <= 1.0

        # Test with FHIR
        fhir_doc = ingest(SAMPLE_FHIR_BUNDLE)
        assert fhir_doc.metadata.patient_id
        assert fhir_doc.metadata.encounter_id
        assert 0.0 <= fhir_doc.modality_confidence <= 1.0

    def test_patient_and_encounter_ids_exist(self):
        """All documents should have patient_id and encounter_id."""
        doc = parse_text("Test note")

        # Verify IDs exist
        assert doc.metadata.patient_id
        assert doc.metadata.encounter_id

        # Verify they're valid UUIDs
        UUID(doc.metadata.patient_id)
        UUID(doc.metadata.encounter_id)


class TestImageParsing:
    """Test image parsing (requires SmolVLM model)."""

    @pytest.mark.slow
    def test_parse_image_missing_file(self):
        """parse_image should raise FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError, match="Image file not found"):
            parse_image("nonexistent.png")

    @pytest.mark.slow
    def test_parse_image_not_a_file(self):
        """parse_image should raise ValueError if path is not a file."""
        # Create a temporary directory path
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError, match="Path is not a file"):
                parse_image(tmpdir)
