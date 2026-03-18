"""
Evaluation schemas for gold standard cases and test results.

Defines the format for synthetic test data and evaluation metrics.
"""

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


class GoldStandardEntity(BaseModel):
    """Expected entity for a gold standard test case."""

    text: str
    entity_type: str
    start_char: int
    end_char: int
    negated: bool
    qualifiers: list[str] = Field(default_factory=list)


class GoldStandardCase(BaseModel):
    """
    A single gold standard test case with expected outputs.

    Used for evaluating NER, coding, negation, and CDI modules.
    """

    case_id: str
    source_type: Literal["fhir", "text", "image"]
    input_data: str  # File path or inline text
    expected_entities: list[GoldStandardEntity]
    expected_icd10_codes: list[str]
    expected_principal_dx: str
    expected_comorbidities: list[str] = Field(default_factory=list)
    expected_complications: list[str] = Field(default_factory=list)
    negation_test_cases: list[dict] = Field(default_factory=list)
    cdi_gap_annotations: Optional[list[dict]] = Field(default=None)
    kg_qualification_rules: Optional[list[dict]] = Field(default=None)
    notes: str = Field(default="")


class EvalResult(BaseModel):
    """
    Evaluation results for a module test run.

    Captures aggregate metrics and per-case results for analysis.
    """

    module_name: str
    timestamp: datetime
    n_cases: int
    metrics: dict[str, float]
    per_case_results: list[dict] = Field(default_factory=list)
    failures: list[dict] = Field(default_factory=list)
    passed: bool
