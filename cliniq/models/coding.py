"""
ICD-10 coding result schemas.

Defines the output format from the RAG-based coding module,
including code suggestions with evidence and reasoning.
"""

from typing import Optional

from pydantic import BaseModel, Field


class CodeSuggestion(BaseModel):
    """
    A single ICD-10 code suggestion with explainability.

    Includes evidence text, reasoning, and specificity indicators
    for CDI review.
    """

    icd10_code: str
    description: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_text: str
    reasoning: str
    needs_specificity: bool = Field(default=False)
    alternatives: list[dict] = Field(default_factory=list)


class CodingResult(BaseModel):
    """
    Complete coding output for a clinical document.

    Includes principal diagnosis, secondary codes, complications,
    and sequencing rationale for transparency.
    """

    principal_diagnosis: Optional[CodeSuggestion] = None
    secondary_codes: list[CodeSuggestion] = Field(default_factory=list)
    complication_codes: list[CodeSuggestion] = Field(default_factory=list)
    sequencing_rationale: str = Field(default="")
    retrieval_stats: dict = Field(default_factory=dict)
