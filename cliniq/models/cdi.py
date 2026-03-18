"""
CDI (Clinical Documentation Integrity) report schemas.

Defines the output format for CDI analysis, including documentation gaps,
missed diagnoses, and code conflicts identified by KG analysis.

Requirements: CDI-01 through CDI-05.
"""

from pydantic import BaseModel, Field, computed_field


class DocumentationGap(BaseModel):
    """
    A single documentation gap identified by KG analysis.

    Represents a missing qualifier or specificity issue that should be
    addressed via physician query (CDI-01, CDI-02).
    """

    code: str
    description: str
    missing_qualifier: str
    physician_query: str
    evidence_text: str
    confidence: float = Field(ge=0.0, le=1.0)
    cot_trace: str = Field(default="")


class MissedDiagnosis(BaseModel):
    """
    A potential missed diagnosis from co-occurrence analysis.

    Represents a diagnosis that is commonly co-coded with existing codes
    but was not documented (CDI-03).
    """

    suggested_code: str
    description: str
    co_coded_with: str
    co_occurrence_weight: float
    evidence_text: str


class CodeConflict(BaseModel):
    """
    An invalid code combination detected by KG conflict rules.

    Represents two codes that violate ICD-10 Excludes1 rules and cannot
    both appear on the same claim (CDI-04).
    """

    code_a: str
    code_b: str
    conflict_reason: str
    recommendation: str


class CDIReport(BaseModel):
    """
    Complete CDI analysis output for a clinical document.

    Aggregates documentation gaps, missed diagnoses, and code conflicts
    with an overall completeness score (CDI-05).
    """

    documentation_gaps: list[DocumentationGap] = Field(default_factory=list)
    missed_diagnoses: list[MissedDiagnosis] = Field(default_factory=list)
    code_conflicts: list[CodeConflict] = Field(default_factory=list)
    completeness_score: float = Field(ge=0.0, le=1.0)
    processing_time_ms: float = Field(default=0.0)

    @computed_field
    @property
    def gap_count(self) -> int:
        """Total number of documentation gaps identified."""
        return len(self.documentation_gaps)

    @computed_field
    @property
    def conflict_count(self) -> int:
        """Total number of code conflicts identified."""
        return len(self.code_conflicts)
