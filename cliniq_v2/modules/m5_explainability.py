"""
Explainability module re-export for cliniq_v2.

All explainability utilities (audit trail builder, CoT capture, evidence linking,
retrieval logging) are model-agnostic and work identically with any LLM backend.
This module re-exports them from cliniq for use within the cliniq_v2 pipeline.
"""

from cliniq.modules.m5_explainability import (
    AuditTrailBuilder,
    build_retrieval_log,
    capture_cot_and_json,
    link_evidence_spans,
)

__all__ = [
    "AuditTrailBuilder",
    "capture_cot_and_json",
    "link_evidence_spans",
    "build_retrieval_log",
]
