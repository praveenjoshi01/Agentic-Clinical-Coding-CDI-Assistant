"""
Pydantic data models for clinical document processing pipeline.

These schemas define the contracts between pipeline modules:
- document.py: Input document schemas
- entities.py: NER output schemas
- coding.py: ICD-10 coding result schemas
- evaluation.py: Gold standard and evaluation schemas
"""

from cliniq.models.document import ClinicalDocument, DocumentMetadata
from cliniq.models.entities import ClinicalEntity, NLUResult, ENTITY_TYPE_MAP
from cliniq.models.coding import CodeSuggestion, CodingResult
from cliniq.models.evaluation import (
    GoldStandardCase,
    GoldStandardEntity,
    EvalResult,
)

__all__ = [
    "ClinicalDocument",
    "DocumentMetadata",
    "ClinicalEntity",
    "NLUResult",
    "ENTITY_TYPE_MAP",
    "CodeSuggestion",
    "CodingResult",
    "GoldStandardCase",
    "GoldStandardEntity",
    "EvalResult",
]
