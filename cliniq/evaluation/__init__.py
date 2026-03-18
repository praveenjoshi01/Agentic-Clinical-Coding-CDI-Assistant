"""
Evaluation package for CDI quality assessment.

Provides LLM-as-judge scoring for physician query relevance (CDI-06)
and chain-of-thought coherence (EXPL-05).
"""

from cliniq.evaluation.llm_judge import (
    judge_query_relevance,
    judge_cot_coherence,
    evaluate_cdi_quality,
    evaluate_cot_quality,
)

__all__ = [
    "judge_query_relevance",
    "judge_cot_coherence",
    "evaluate_cdi_quality",
    "evaluate_cot_quality",
]
