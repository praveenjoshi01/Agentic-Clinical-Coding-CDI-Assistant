"""
LLM-as-judge evaluation for CDI quality scoring.

Uses Qwen2.5-1.5B as a rubric-based judge to score:
- Physician query relevance (CDI-06): target >= 0.80 aggregate
- Chain-of-thought coherence (EXPL-05): target >= 0.82 aggregate

This is evaluation-time tooling, not inference-time. Results feed into
the Phase 3 evaluation dashboard.
"""

import json
import logging
from typing import Any

from cliniq.model_manager import ModelManager
from cliniq.models.cdi import CDIReport
from cliniq.models.audit import AuditTrail
from cliniq.modules.m5_explainability import capture_cot_and_json

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_QUERY_RELEVANCE_PROMPT = """\
Rate the relevance of this physician query for addressing the documentation gap.

Documentation Gap: {documentation_gap}
Clinical Context: {clinical_context}
Physician Query: {physician_query}

Scoring rubric:
1 = Completely irrelevant — query does not address the documentation gap at all
2 = Tangentially related — query mentions the condition but not the specific missing information
3 = Somewhat relevant — query addresses the gap but is too vague or broad to be actionable
4 = Relevant and specific — query clearly asks about the missing information with clinical precision
5 = Highly relevant, specific, and actionable — query references the specific clinical finding, asks about the exact missing qualifier, and uses appropriate medical language

Return ONLY a JSON: {{"score": N, "reasoning": "brief explanation"}}"""

_COT_COHERENCE_PROMPT = """\
Rate the coherence of this chain-of-thought reasoning trace.

Task: {task_description}
Chain-of-Thought: {cot_trace}

Scoring rubric:
1 = Incoherent — reasoning is garbled, contradictory, or unrelated to the task
2 = Partially coherent — some relevant reasoning but with logical gaps or non-sequiturs
3 = Coherent but shallow — reasoning follows a logical thread but lacks depth or clinical insight
4 = Coherent and substantive — reasoning demonstrates clear clinical logic with appropriate steps
5 = Highly coherent — reasoning is logically structured, clinically sound, and demonstrates expertise

Return ONLY a JSON: {{"score": N, "reasoning": "brief explanation"}}"""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _generate_judge_response(prompt: str) -> str:
    """Generate a judge response using the reasoning LLM."""
    mm = ModelManager()
    model, tokenizer = mm.get_reasoning_llm()

    messages = [{"role": "user", "content": prompt}]
    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = tokenizer(text, return_tensors="pt")
    outputs = model.generate(
        **inputs,
        max_new_tokens=128,
        temperature=0.1,
        do_sample=True,
    )
    # Decode only newly generated tokens
    generated = outputs[0][inputs["input_ids"].shape[1] :]
    return tokenizer.decode(generated, skip_special_tokens=True)


def _parse_judge_response(raw_response: str) -> dict[str, Any]:
    """
    Parse a judge response into score and reasoning.

    Returns dict with score (0-1), raw_score (1-5), reasoning, cot_trace.
    Falls back to default score of 0.6 (raw 3) on parse failure.
    """
    cot_trace, json_str = capture_cot_and_json(raw_response)

    if not json_str:
        logger.warning("No JSON found in judge response, using fallback score")
        return {
            "score": 0.6,
            "raw_score": 3,
            "reasoning": "Parse failure, default score",
            "cot_trace": raw_response,
        }

    try:
        parsed = json.loads(json_str)
        raw_score = int(parsed.get("score", 3))
        raw_score = max(1, min(5, raw_score))  # Clamp to 1-5
        reasoning = str(parsed.get("reasoning", ""))
        return {
            "score": raw_score / 5.0,
            "raw_score": raw_score,
            "reasoning": reasoning,
            "cot_trace": cot_trace,
        }
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning("Failed to parse judge JSON: %s", exc)
        return {
            "score": 0.6,
            "raw_score": 3,
            "reasoning": "Parse failure, default score",
            "cot_trace": raw_response,
        }


# ---------------------------------------------------------------------------
# Per-item scoring (CDI-06, EXPL-05)
# ---------------------------------------------------------------------------


def judge_query_relevance(
    physician_query: str,
    documentation_gap: str,
    clinical_context: str,
) -> dict[str, Any]:
    """
    Score physician query relevance on a 1-5 Likert scale (CDI-06).

    Uses an explicit rubric prompt so the LLM judge scores consistently.

    Args:
        physician_query: The generated physician query to evaluate.
        documentation_gap: Description of the documentation gap being addressed.
        clinical_context: Clinical note context (truncated to 300 chars).

    Returns:
        Dict with score (0-1 normalized), raw_score (1-5), reasoning, cot_trace.
    """
    prompt = _QUERY_RELEVANCE_PROMPT.format(
        physician_query=physician_query,
        documentation_gap=documentation_gap,
        clinical_context=clinical_context[:300],
    )
    raw_response = _generate_judge_response(prompt)
    return _parse_judge_response(raw_response)


def judge_cot_coherence(
    cot_trace: str,
    task_description: str,
) -> dict[str, Any]:
    """
    Score chain-of-thought coherence on a 1-5 Likert scale (EXPL-05).

    Uses an explicit rubric prompt for consistent coherence assessment.

    Args:
        cot_trace: The chain-of-thought reasoning trace to evaluate.
        task_description: Description of the task the CoT was generated for.

    Returns:
        Dict with score (0-1 normalized), raw_score (1-5), reasoning, cot_trace.
    """
    prompt = _COT_COHERENCE_PROMPT.format(
        cot_trace=cot_trace[:500],
        task_description=task_description,
    )
    raw_response = _generate_judge_response(prompt)
    return _parse_judge_response(raw_response)


# ---------------------------------------------------------------------------
# Aggregate evaluation (CDI-06, EXPL-05)
# ---------------------------------------------------------------------------


def evaluate_cdi_quality(
    cdi_reports: list[CDIReport],
    clinical_contexts: list[str],
) -> dict[str, Any]:
    """
    Evaluate physician query relevance across multiple CDI reports (CDI-06).

    Scores every DocumentationGap's physician_query via judge_query_relevance
    and returns aggregate metrics. Target: mean_relevance_score >= 0.80.

    Args:
        cdi_reports: List of CDIReport objects to evaluate.
        clinical_contexts: Corresponding clinical note contexts (one per report).

    Returns:
        Dict with aggregate metrics and per-query detail list.
    """
    per_query_details: list[dict] = []

    for i, report in enumerate(cdi_reports):
        context = clinical_contexts[i] if i < len(clinical_contexts) else ""
        for gap in report.documentation_gaps:
            result = judge_query_relevance(
                physician_query=gap.physician_query,
                documentation_gap=f"{gap.code} {gap.description} missing {gap.missing_qualifier}",
                clinical_context=context,
            )
            per_query_details.append({
                "code": gap.code,
                "physician_query": gap.physician_query,
                "documentation_gap": gap.description,
                **result,
            })

    scores = [d["score"] for d in per_query_details]
    n_scored = len(scores)

    if n_scored == 0:
        return {
            "mean_relevance_score": 0.0,
            "min_score": 0.0,
            "max_score": 0.0,
            "n_queries_scored": 0,
            "n_above_threshold": 0,
            "per_query_details": [],
        }

    return {
        "mean_relevance_score": sum(scores) / n_scored,
        "min_score": min(scores),
        "max_score": max(scores),
        "n_queries_scored": n_scored,
        "n_above_threshold": sum(1 for s in scores if s >= 0.80),
        "per_query_details": per_query_details,
    }


def evaluate_cot_quality(
    audit_trails: list[AuditTrail],
) -> dict[str, Any]:
    """
    Evaluate chain-of-thought coherence across audit trails (EXPL-05).

    Scores every cot_trace in every StageTrace via judge_cot_coherence
    and returns aggregate metrics. Target: mean_coherence_score >= 0.82.

    Args:
        audit_trails: List of AuditTrail objects to evaluate.

    Returns:
        Dict with aggregate metrics and per-trace detail list.
    """
    per_trace_details: list[dict] = []

    for trail in audit_trails:
        for stage_trace in trail.stages:
            for cot in stage_trace.cot_traces:
                result = judge_cot_coherence(
                    cot_trace=cot,
                    task_description=f"{stage_trace.stage} stage processing",
                )
                per_trace_details.append({
                    "case_id": trail.case_id,
                    "stage": stage_trace.stage,
                    **result,
                })

    scores = [d["score"] for d in per_trace_details]
    n_scored = len(scores)

    if n_scored == 0:
        return {
            "mean_coherence_score": 0.0,
            "min_score": 0.0,
            "max_score": 0.0,
            "n_traces_scored": 0,
            "n_above_threshold": 0,
            "per_trace_details": [],
        }

    return {
        "mean_coherence_score": sum(scores) / n_scored,
        "min_score": min(scores),
        "max_score": max(scores),
        "n_traces_scored": n_scored,
        "n_above_threshold": sum(1 for s in scores if s >= 0.82),
        "per_trace_details": per_trace_details,
    }
