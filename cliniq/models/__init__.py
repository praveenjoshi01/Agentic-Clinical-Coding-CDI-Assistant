"""
Pydantic data models for clinical document processing pipeline.

These schemas define the contracts between pipeline modules:
- document.py: Input document schemas
- entities.py: NER output schemas
- coding.py: ICD-10 coding result schemas
- evaluation.py: Gold standard and evaluation schemas
- cdi.py: CDI report schemas (documentation gaps, missed diagnoses, conflicts)
- audit.py: Audit trail schemas (stage traces, retrieval logs)
"""

from cliniq.models.document import ClinicalDocument, DocumentMetadata
from cliniq.models.entities import ClinicalEntity, NLUResult, ENTITY_TYPE_MAP
from cliniq.models.coding import CodeSuggestion, CodingResult
from cliniq.models.evaluation import (
    GoldStandardCase,
    GoldStandardEntity,
    EvalResult,
)
from cliniq.models.cdi import (
    CDIReport,
    DocumentationGap,
    MissedDiagnosis,
    CodeConflict,
)
from cliniq.models.audit import AuditTrail, StageTrace, RetrievalLog

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
    "CDIReport",
    "DocumentationGap",
    "MissedDiagnosis",
    "CodeConflict",
    "AuditTrail",
    "StageTrace",
    "RetrievalLog",
]
