"""
Entity extraction schemas.

Defines the output format from NER and the mapping from d4data labels
to pipeline entity categories.
"""

from pydantic import BaseModel, Field, computed_field

# Mapping from d4data biomedical-ner-all labels to pipeline entity categories
ENTITY_TYPE_MAP = {
    # Clinical conditions
    "Disease_disorder": "diagnosis",
    "Sign_symptom": "diagnosis",
    # Procedures
    "Therapeutic_procedure": "procedure",
    "Diagnostic_procedure": "procedure",
    # Medications
    "Medication": "medication",
    # Anatomy
    "Biological_structure": "anatomical_site",
    # Qualifiers and descriptors
    "Severity": "qualifier",
    "Detailed_description": "qualifier",
    "Qualitative_concept": "qualifier",
    "Quantitative_concept": "qualifier",
    # Lab values
    "Lab_value": "lab_value",
}


class ClinicalEntity(BaseModel):
    """A single clinical entity extracted from text."""

    text: str
    entity_type: str
    start_char: int
    end_char: int
    confidence: float = Field(ge=0.0, le=1.0)
    negated: bool = Field(default=False)
    qualifiers: list[str] = Field(default_factory=list)


class NLUResult(BaseModel):
    """
    Complete NER output for a document.

    Provides computed properties to filter entities by semantic category.
    """

    entities: list[ClinicalEntity]
    processing_time_ms: float

    @computed_field
    @property
    def entity_count(self) -> int:
        """Total number of entities extracted."""
        return len(self.entities)

    @computed_field
    @property
    def diagnoses(self) -> list[ClinicalEntity]:
        """All diagnosis entities (diseases and symptoms)."""
        return [e for e in self.entities if e.entity_type == "diagnosis"]

    @computed_field
    @property
    def procedures(self) -> list[ClinicalEntity]:
        """All procedure entities."""
        return [e for e in self.entities if e.entity_type == "procedure"]

    @computed_field
    @property
    def medications(self) -> list[ClinicalEntity]:
        """All medication entities."""
        return [e for e in self.entities if e.entity_type == "medication"]

    @computed_field
    @property
    def anatomical_sites(self) -> list[ClinicalEntity]:
        """All anatomical structure entities."""
        return [e for e in self.entities if e.entity_type == "anatomical_site"]
