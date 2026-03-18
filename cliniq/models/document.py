"""
Clinical document input schemas.

Defines the common format for documents entering the pipeline,
regardless of source modality (FHIR, image, plain text).
"""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    """Metadata for a clinical document."""

    patient_id: str
    encounter_id: str
    source_type: Literal["fhir", "image", "text"]
    timestamp: datetime = Field(default_factory=datetime.now)


class ClinicalDocument(BaseModel):
    """
    Unified representation of a clinical document.

    All input modalities (FHIR bundles, OCR'd images, plain text)
    are normalized to this schema before NER processing.
    """

    metadata: DocumentMetadata
    raw_narrative: str
    structured_facts: list[dict] = Field(default_factory=list)
    modality_confidence: float = Field(ge=0.0, le=1.0)
    extraction_trace: str = Field(default="")
