"""
RAG-based ICD-10 coding module using OpenAI API.

Two-stage pipeline (cross-encoder eliminated):
1. FAISS retrieval (top-20 candidates via OpenAI embeddings)
2. GPT-4o reasoning (combined reranking + selection + reasoning in one call)

Outputs sequenced codes: principal diagnosis, secondary codes, complications.
"""

import json
import logging
import time
from typing import Optional

from cliniq_v2.config import RETRIEVAL_TOP_K
from cliniq.models import ClinicalEntity, NLUResult, CodeSuggestion, CodingResult
from cliniq_v2.rag import get_retriever

# Reuse sequence_codes from cliniq v1 (model-agnostic, pure rule-based)
from cliniq.modules.m3_rag_coding import sequence_codes

logger = logging.getLogger(__name__)


def build_coding_query(entity: ClinicalEntity, context_window: str = "") -> str:
    """
    Construct search query from clinical entity.

    Identical to cliniq v1 (pure string construction, no model dependency).

    Args:
        entity: The clinical entity to code.
        context_window: Optional surrounding clinical context.

    Returns:
        Search query string.
    """
    query = entity.text

    # Append qualifiers if present (e.g., "severe", "chronic")
    if entity.qualifiers:
        query += " " + " ".join(entity.qualifiers)

    # Append context if provided
    if context_window:
        query += f" in context of {context_window}"

    return query


def retrieve_candidates(
    query: str, retriever
) -> list[dict]:
    """
    Single-stage retrieval via configured retriever (no reranking).

    All 20 candidates go directly to GPT-4o for selection.

    Args:
        query: The clinical search query.
        retriever: Retriever instance (FAISSRetriever or PineconeRetriever).

    Returns:
        List of candidate dicts with code, description, score, rank.
    """
    logger.debug(
        f"Retrieving top-{RETRIEVAL_TOP_K} candidates for query: {query[:50]}..."
    )
    candidates = retriever.retrieve(query, top_k=RETRIEVAL_TOP_K)

    if not candidates:
        logger.warning(f"No candidates retrieved for query: {query}")
        return []

    return candidates


def reason_with_gpt4o(
    entity: ClinicalEntity,
    candidates: list[dict],
    clinical_context: str,
) -> dict:
    """
    Use GPT-4o to select most appropriate code with reasoning.

    Replaces both cross-encoder reranking and Qwen LLM reasoning --
    GPT-4o handles reranking, selection, and reasoning in one call.

    Args:
        entity: The clinical entity to code.
        candidates: All 20 retrieval candidates (not reranked).
        clinical_context: Full clinical text for context.

    Returns:
        Dict with selected_code, description, confidence, reasoning,
        needs_specificity, alternatives.
    """
    from cliniq_v2.api_client import OpenAIClient

    # Build prompt with all candidates
    candidates_text = "\n".join([
        f"- {c['code']}: {c['description']} (retrieval score: {c.get('score', 0.0):.2f})"
        for c in candidates
    ])

    context_snippet = clinical_context[:500] if clinical_context else "None provided"
    qualifiers_text = ", ".join(entity.qualifiers) if entity.qualifiers else "None"

    prompt = f"""You are a clinical coding expert. Given a clinical finding and candidate ICD-10 codes, select the most specific appropriate code.

Clinical finding: {entity.text}
Qualifiers: {qualifiers_text}
Clinical context: {context_snippet}

Candidate ICD-10 codes:
{candidates_text}

Return a JSON object with these exact fields:
- "selected_code": the ICD-10 code string
- "description": the code description
- "confidence": your confidence 0.0-1.0
- "reasoning": one sentence explaining why this code is most appropriate
- "needs_specificity": true if a more specific code might exist but documentation is insufficient
- "alternatives": [{{"code": "X", "description": "Y", "reason": "Z"}}] for top 2 alternatives

Return ONLY the JSON object, no other text."""

    try:
        client = OpenAIClient().client
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a clinical coding expert."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )

        result = json.loads(response.choices[0].message.content)

        # Validate required fields
        required_fields = [
            "selected_code", "description", "confidence",
            "reasoning", "needs_specificity", "alternatives",
        ]
        missing_fields = [f for f in required_fields if f not in result]

        if missing_fields:
            raise ValueError(f"Missing fields in GPT-4o output: {missing_fields}")

        logger.debug(
            f"GPT-4o selected code {result['selected_code']} "
            f"with confidence {result['confidence']}"
        )
        return result

    except Exception as e:
        # Fallback: use top retrieval candidate
        logger.warning(f"GPT-4o reasoning failed: {e}. Using top retrieval candidate.")
        top_candidate = candidates[0]
        return {
            "selected_code": top_candidate["code"],
            "description": top_candidate["description"],
            "confidence": top_candidate.get("score", 0.5),
            "reasoning": "Selected based on retrieval ranking (GPT-4o reasoning failed)",
            "needs_specificity": False,
            "alternatives": [
                {
                    "code": c["code"],
                    "description": c["description"],
                    "reason": "High retrieval score",
                }
                for c in candidates[1:3]
            ],
        }


def build_code_suggestion(
    entity: ClinicalEntity,
    llm_result: dict,
    candidates: list[dict],
) -> CodeSuggestion:
    """
    Convert GPT-4o output to CodeSuggestion Pydantic model.

    Modified from v1: confidence comes directly from GPT-4o (no blending
    with reranker score since there is no reranker). Clamped to [0.0, 1.0].

    Args:
        entity: The clinical entity that was coded.
        llm_result: GPT-4o output dict.
        candidates: Retrieval candidates (not used for score blending).

    Returns:
        CodeSuggestion instance.
    """
    # Direct confidence from GPT-4o (no reranker score blending)
    confidence = max(0.0, min(1.0, float(llm_result["confidence"])))

    return CodeSuggestion(
        icd10_code=llm_result["selected_code"],
        description=llm_result["description"],
        confidence=confidence,
        evidence_text=entity.text,
        reasoning=llm_result["reasoning"],
        needs_specificity=llm_result["needs_specificity"],
        alternatives=llm_result["alternatives"],
    )


def code_entities(
    nlu_result: NLUResult,
    clinical_context: str = "",
) -> CodingResult:
    """
    Main orchestrator: RAG-based ICD-10 coding of clinical entities.

    Pipeline:
    1. Filter entities (diagnoses and procedures only, exclude negated)
    2. For each entity: build query -> retrieve (FAISS) -> reason with GPT-4o
    3. Sequence all suggestions into principal/secondary/complication

    Args:
        nlu_result: NLUResult with extracted entities.
        clinical_context: Full clinical text for GPT-4o context.

    Returns:
        CodingResult with sequenced codes and stats.
    """
    start_time = time.time()

    # Handle empty NLU result
    if not nlu_result.entities:
        logger.info("Empty NLU result, returning empty CodingResult")
        return CodingResult(
            principal_diagnosis=None,
            secondary_codes=[],
            complication_codes=[],
            sequencing_rationale="No entities to code",
            retrieval_stats={
                "total_entities_coded": 0,
                "avg_confidence": 0.0,
                "codes_needing_specificity": 0,
                "processing_time_ms": round((time.time() - start_time) * 1000, 2),
            },
        )

    # Initialize retrieval infrastructure via factory (Pinecone if configured, else FAISS)
    logger.info("Initializing retriever")
    retriever = get_retriever()

    # Ensure FAISS index is built
    retriever.ensure_index_built()

    # Filter entities: only diagnoses and procedures, exclude negated
    eligible_entities = [
        e for e in nlu_result.entities
        if e.entity_type in ["diagnosis", "procedure"] and not e.negated
    ]

    if not eligible_entities:
        logger.info(
            "No eligible entities (after filtering negated/non-diagnosis entities)"
        )
        return CodingResult(
            principal_diagnosis=None,
            secondary_codes=[],
            complication_codes=[],
            sequencing_rationale="No eligible entities after filtering",
            retrieval_stats={
                "total_entities_coded": 0,
                "avg_confidence": 0.0,
                "codes_needing_specificity": 0,
                "processing_time_ms": round((time.time() - start_time) * 1000, 2),
            },
        )

    logger.info(f"Coding {len(eligible_entities)} eligible entities")

    # Process each entity
    suggestions = []
    for entity in eligible_entities:
        try:
            # Build query
            query = build_coding_query(entity, context_window=clinical_context[:200])
            logger.debug(
                f"Processing entity: {entity.text} (type: {entity.entity_type})"
            )

            # Retrieve candidates (no reranking)
            candidates = retrieve_candidates(query, retriever)

            if not candidates:
                logger.warning(f"No candidates retrieved for entity: {entity.text}")
                continue

            # Reason with GPT-4o (replaces Qwen + cross-encoder)
            llm_result = reason_with_gpt4o(entity, candidates, clinical_context)

            # Build CodeSuggestion (no reranker score blending)
            suggestion = build_code_suggestion(entity, llm_result, candidates)
            suggestions.append(suggestion)

            logger.debug(
                f"Coded {entity.text} -> {suggestion.icd10_code} "
                f"(confidence: {suggestion.confidence:.2f})"
            )

        except Exception as e:
            logger.error(f"Error coding entity {entity.text}: {e}", exc_info=True)
            continue

    if not suggestions:
        logger.warning("No code suggestions generated")
        return CodingResult(
            principal_diagnosis=None,
            secondary_codes=[],
            complication_codes=[],
            sequencing_rationale="All entities failed to generate suggestions",
            retrieval_stats={
                "total_entities_coded": 0,
                "avg_confidence": 0.0,
                "codes_needing_specificity": 0,
                "processing_time_ms": round((time.time() - start_time) * 1000, 2),
            },
        )

    # Sequence codes (reused from cliniq v1 -- model-agnostic)
    result = sequence_codes(suggestions)

    # Add processing time to stats
    processing_time = round((time.time() - start_time) * 1000, 2)
    result.retrieval_stats["processing_time_ms"] = processing_time

    logger.info(
        f"Coding complete: {result.retrieval_stats['total_entities_coded']} entities coded, "
        f"avg confidence {result.retrieval_stats['avg_confidence']}, "
        f"time {processing_time}ms"
    )

    return result
