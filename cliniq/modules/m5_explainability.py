"""
Explainability module for pipeline instrumentation.

Provides utilities that the pipeline orchestrator wraps around existing
stage outputs to capture audit trails, chain-of-thought traces,
evidence linkage, and retrieval logs.

This module does NOT modify Phase 1 modules — it wraps their outputs.

Requirements: EXPL-01 through EXPL-04.
"""

import re
from typing import Optional

from cliniq.models.audit import AuditTrail, StageTrace, RetrievalLog
from cliniq.models.coding import CodingResult, CodeSuggestion


class AuditTrailBuilder:
    """
    Convenience wrapper around AuditTrail for stage-recording.

    Provides methods to accumulate stage traces, evidence spans,
    and query the completeness of the audit trail (EXPL-01).
    """

    _CORE_STAGES = {"ingestion", "ner", "rag", "cdi"}

    def __init__(self, case_id: str) -> None:
        self._trail = AuditTrail(case_id=case_id)

    # ------------------------------------------------------------------
    # Recording helpers
    # ------------------------------------------------------------------

    def record_stage(
        self,
        stage: str,
        processing_time_ms: float,
        input_summary: str,
        output_summary: str,
        details: Optional[dict] = None,
        cot_traces: Optional[list[str]] = None,
        retrieval_logs: Optional[list[RetrievalLog]] = None,
    ) -> None:
        """
        Create a StageTrace and append it to the trail.

        Handles ``None`` defaults so callers can omit optional fields.
        """
        trace = StageTrace(
            stage=stage,
            processing_time_ms=processing_time_ms,
            input_summary=input_summary,
            output_summary=output_summary,
            details=details if details is not None else {},
            cot_traces=cot_traces if cot_traces is not None else [],
            retrieval_logs=retrieval_logs if retrieval_logs is not None else [],
        )
        self._trail.add_stage(trace)

    def add_evidence(self, code: str, text_span: str) -> None:
        """Delegate to AuditTrail.add_evidence() for EXPL-02."""
        self._trail.add_evidence(code, text_span)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get_trail(self) -> AuditTrail:
        """Return the accumulated audit trail."""
        return self._trail

    @property
    def stage_count(self) -> int:
        """Number of stages recorded so far."""
        return len(self._trail.stages)

    @property
    def has_all_stages(self) -> bool:
        """True when at least one trace exists for each core stage."""
        recorded = {t.stage for t in self._trail.stages}
        return self._CORE_STAGES.issubset(recorded)


# ----------------------------------------------------------------------
# Utility functions
# ----------------------------------------------------------------------


def capture_cot_and_json(raw_llm_response: str) -> tuple[str, str]:
    """
    Extract chain-of-thought trace and JSON payload from an LLM response.

    For EXPL-03.  Stores the full *raw_llm_response* as the CoT trace,
    then locates the outermost JSON object (first ``{`` to last ``}``)
    and returns it as a separate string.

    Returns:
        (cot_trace, json_str) — *json_str* is empty when no JSON found.
    """
    cot_trace = raw_llm_response

    first_brace = raw_llm_response.find("{")
    last_brace = raw_llm_response.rfind("}")

    if first_brace == -1 or last_brace == -1 or last_brace <= first_brace:
        return (cot_trace, "")

    json_str = raw_llm_response[first_brace : last_brace + 1]
    return (cot_trace, json_str)


def link_evidence_spans(
    coding_result: CodingResult,
    clinical_text: str,
) -> dict[str, list[str]]:
    """
    Map each code in *coding_result* to supporting text spans (EXPL-02).

    For every :class:`CodeSuggestion`:
    1. Use ``evidence_text`` as the primary span.
    2. Search *clinical_text* for the entity text (case-insensitive) and
       capture a window of +/- 50 characters around each match.
    3. Return ``{icd10_code: [deduplicated spans]}``.
    """
    evidence_map: dict[str, list[str]] = {}

    # Collect all suggestions from all categories
    suggestions: list[CodeSuggestion] = []
    if coding_result.principal_diagnosis is not None:
        suggestions.append(coding_result.principal_diagnosis)
    suggestions.extend(coding_result.secondary_codes)
    suggestions.extend(coding_result.complication_codes)

    clinical_lower = clinical_text.lower()

    for suggestion in suggestions:
        spans: list[str] = []

        # Primary span: evidence_text from the suggestion
        if suggestion.evidence_text:
            spans.append(suggestion.evidence_text)

        # Contextual spans: search for entity text in the clinical note
        entity_text_lower = suggestion.evidence_text.lower()
        if entity_text_lower:
            start = 0
            while True:
                idx = clinical_lower.find(entity_text_lower, start)
                if idx == -1:
                    break
                window_start = max(0, idx - 50)
                window_end = min(len(clinical_text), idx + len(entity_text_lower) + 50)
                context_span = clinical_text[window_start:window_end]
                spans.append(context_span)
                start = idx + 1

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_spans: list[str] = []
        for span in spans:
            if span not in seen:
                seen.add(span)
                unique_spans.append(span)

        if unique_spans:
            evidence_map[suggestion.icd10_code] = unique_spans

    return evidence_map


def build_retrieval_log(
    query: str,
    top_k_results: list[dict],
    reranked_results: list[dict],
    selected_code: str,
    selected_confidence: float,
) -> RetrievalLog:
    """
    Create a :class:`RetrievalLog` from retrieval pipeline intermediates (EXPL-04).

    Used by the pipeline wrapper to capture the full retrieval chain:
    query -> top-k -> reranked -> selected.
    """
    return RetrievalLog(
        query=query,
        top_k_results=top_k_results,
        reranked_results=reranked_results,
        selected_code=selected_code,
        selected_confidence=selected_confidence,
    )
