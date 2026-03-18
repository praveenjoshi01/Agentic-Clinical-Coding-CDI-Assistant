"""
Audit trail schemas for pipeline explainability.

Defines the format for capturing per-stage processing details,
chain-of-thought traces, and retrieval logs for full transparency.

Requirements: EXPL-01 through EXPL-04.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class RetrievalLog(BaseModel):
    """
    Captures a single RAG retrieval chain for explainability.

    Records the query, raw top-k results, reranked results, and the
    final selected code with confidence (EXPL-04).
    """

    query: str
    top_k_results: list[dict] = Field(default_factory=list)
    reranked_results: list[dict] = Field(default_factory=list)
    selected_code: str
    selected_confidence: float


class StageTrace(BaseModel):
    """
    Trace for a single pipeline processing stage.

    Captures timing, input/output summaries, chain-of-thought traces,
    and retrieval logs for each stage (EXPL-03, EXPL-04).
    """

    stage: Literal["ingestion", "ner", "rag", "cdi", "audit"]
    processing_time_ms: float
    input_summary: str
    output_summary: str
    details: dict = Field(default_factory=dict)
    cot_traces: list[str] = Field(default_factory=list)
    retrieval_logs: list[RetrievalLog] = Field(default_factory=list)


class AuditTrail(BaseModel):
    """
    Complete audit trail for a clinical document processing run.

    Aggregates per-stage traces and evidence spans for full
    explainability (EXPL-01, EXPL-02).
    """

    case_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    stages: list[StageTrace] = Field(default_factory=list)
    evidence_spans: dict[str, list[str]] = Field(default_factory=dict)

    def add_stage(self, trace: StageTrace) -> None:
        """Append a stage trace to the audit trail."""
        self.stages.append(trace)

    def add_evidence(self, code: str, text_span: str) -> None:
        """Add an evidence text span for a specific code (EXPL-02)."""
        if code not in self.evidence_spans:
            self.evidence_spans[code] = []
        self.evidence_spans[code].append(text_span)
