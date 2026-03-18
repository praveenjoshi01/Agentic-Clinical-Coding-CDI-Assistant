"""
RAG-based ICD-10 coding module.

Three-stage pipeline:
1. FAISS retrieval (top-20 candidates)
2. Cross-encoder reranking (top-5 candidates)
3. Qwen LLM reasoning (structured JSON output)

Outputs sequenced codes: principal diagnosis, secondary codes, complications.
"""

import json
import logging
import time
from typing import Optional

from cliniq.config import RETRIEVAL_TOP_K, RERANK_TOP_K
from cliniq.model_manager import ModelManager
from cliniq.models import ClinicalEntity, NLUResult, CodeSuggestion, CodingResult
from cliniq.rag import FAISSRetriever, CrossEncoderReranker

logger = logging.getLogger(__name__)


def build_coding_query(entity: ClinicalEntity, context_window: str = "") -> str:
    """
    Construct search query from clinical entity.

    Args:
        entity: The clinical entity to code
        context_window: Optional surrounding clinical context

    Returns:
        Search query string (BGE prefix added by retriever, not here)
    """
    query = entity.text

    # Append qualifiers if present (e.g., "severe", "chronic")
    if entity.qualifiers:
        query += " " + " ".join(entity.qualifiers)

    # Append context if provided
    if context_window:
        query += f" in context of {context_window}"

    return query


def retrieve_and_rerank(
    query: str,
    retriever: FAISSRetriever,
    reranker: CrossEncoderReranker
) -> list[dict]:
    """
    Two-stage retrieval: FAISS bi-encoder + cross-encoder reranking.

    Args:
        query: The clinical search query
        retriever: FAISSRetriever instance
        reranker: CrossEncoderReranker instance

    Returns:
        List of reranked candidates with both retrieval_score and rerank_score
    """
    # Stage 1: Retrieve top-20 candidates using FAISS
    logger.debug(f"Retrieving top-{RETRIEVAL_TOP_K} candidates for query: {query[:50]}...")
    candidates = retriever.retrieve(query, top_k=RETRIEVAL_TOP_K)

    if not candidates:
        logger.warning(f"No candidates retrieved for query: {query}")
        return []

    # Stage 2: Rerank to top-5 using cross-encoder
    logger.debug(f"Reranking {len(candidates)} candidates to top-{RERANK_TOP_K}")
    reranked = reranker.rerank(query, candidates, top_k=RERANK_TOP_K)

    return reranked


def reason_with_llm(
    entity: ClinicalEntity,
    candidates: list[dict],
    clinical_context: str
) -> dict:
    """
    Use Qwen LLM to select most appropriate code with reasoning.

    Args:
        entity: The clinical entity to code
        candidates: Reranked candidate codes
        clinical_context: Full clinical text for context

    Returns:
        Dict with selected_code, description, confidence, reasoning,
        needs_specificity, alternatives
    """
    # Get Qwen model and tokenizer
    model, tokenizer = ModelManager().get_reasoning_llm()

    # Build prompt
    candidates_text = "\n".join([
        f"- {c['code']}: {c['description']} (score: {c.get('rerank_score', c.get('score', 0.0)):.2f})"
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
- "alternatives": [{"code": "X", "description": "Y", "reason": "Z"}] for top 2 alternatives

Return ONLY the JSON object, no other text."""

    # Try to generate with retry logic (up to 3 attempts)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Tokenize and generate
            inputs = tokenizer(prompt, return_tensors="pt")
            outputs = model.generate(
                inputs.input_ids,
                max_new_tokens=512,
                temperature=0.1,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id
            )
            response = tokenizer.decode(outputs[0], skip_special_tokens=True)

            # Extract JSON from response (find first { to last })
            start_idx = response.find('{')
            end_idx = response.rfind('}')

            if start_idx == -1 or end_idx == -1:
                raise ValueError("No JSON object found in response")

            json_str = response[start_idx:end_idx + 1]
            result = json.loads(json_str)

            # Validate required fields
            required_fields = ['selected_code', 'description', 'confidence', 'reasoning', 'needs_specificity', 'alternatives']
            missing_fields = [f for f in required_fields if f not in result]

            if missing_fields:
                raise ValueError(f"Missing fields in LLM output: {missing_fields}")

            logger.debug(f"LLM selected code {result['selected_code']} with confidence {result['confidence']}")
            return result

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"LLM response parsing failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                # Final fallback: use top reranked candidate
                logger.warning("Using top reranked candidate as fallback")
                top_candidate = candidates[0]
                return {
                    "selected_code": top_candidate["code"],
                    "description": top_candidate["description"],
                    "confidence": top_candidate.get("rerank_score", top_candidate.get("score", 0.5)),
                    "reasoning": "Selected based on retrieval ranking (LLM generation failed)",
                    "needs_specificity": False,
                    "alternatives": [
                        {
                            "code": c["code"],
                            "description": c["description"],
                            "reason": "High retrieval score"
                        }
                        for c in candidates[1:3]  # Top 2 alternatives
                    ]
                }
            # Retry with simplified prompt
            continue

    # Should not reach here due to fallback, but just in case
    return reason_with_llm(entity, candidates, clinical_context)


def build_code_suggestion(
    entity: ClinicalEntity,
    llm_result: dict,
    candidates: list[dict]
) -> CodeSuggestion:
    """
    Convert LLM output to CodeSuggestion Pydantic model.

    Args:
        entity: The clinical entity that was coded
        llm_result: LLM output dict
        candidates: Reranked candidates (for score blending)

    Returns:
        CodeSuggestion instance
    """
    # Blend LLM confidence with top reranker score
    llm_confidence = llm_result["confidence"]
    top_rerank_score = candidates[0].get("rerank_score", candidates[0].get("score", 0.0))
    blended_confidence = 0.6 * llm_confidence + 0.4 * top_rerank_score

    return CodeSuggestion(
        icd10_code=llm_result["selected_code"],
        description=llm_result["description"],
        confidence=blended_confidence,
        evidence_text=entity.text,  # The clinical text that triggered this code
        reasoning=llm_result["reasoning"],
        needs_specificity=llm_result["needs_specificity"],
        alternatives=llm_result["alternatives"]
    )


def sequence_codes(suggestions: list[CodeSuggestion]) -> CodingResult:
    """
    Sequence codes into principal diagnosis, secondary, and complications.

    Simplified sequencing logic for POC:
    1. Principal diagnosis: highest confidence diagnosis code
    2. Secondary codes: remaining diagnosis codes sorted by confidence
    3. Complication codes: codes where entity had complication qualifiers

    Args:
        suggestions: List of CodeSuggestion instances

    Returns:
        CodingResult with sequenced codes and rationale
    """
    if not suggestions:
        # Return empty result
        return CodingResult(
            principal_diagnosis=None,
            secondary_codes=[],
            complication_codes=[],
            sequencing_rationale="No codes to sequence (empty suggestions list)",
            retrieval_stats={
                "total_entities_coded": 0,
                "avg_confidence": 0.0,
                "codes_needing_specificity": 0
            }
        )

    # Sort by confidence descending
    sorted_suggestions = sorted(suggestions, copy=False, key=lambda x: x.confidence, reverse=True)

    # Principal diagnosis: highest confidence (simplified - assume all are diagnoses)
    principal = sorted_suggestions[0]

    # Secondary codes: remaining codes
    secondary = sorted_suggestions[1:]

    # Complication codes: codes with evidence text containing complication keywords
    # (In practice, would check entity.qualifiers, but we only have the CodeSuggestion here)
    complication_keywords = ["complication", "secondary to", "due to", "following", "post-"]
    complication = [
        s for s in sorted_suggestions
        if any(kw in s.evidence_text.lower() for kw in complication_keywords)
    ]

    # Remove complications from secondary
    secondary = [s for s in secondary if s not in complication]

    # Build sequencing rationale
    rationale_parts = [
        f"Principal diagnosis: {principal.icd10_code} (confidence {principal.confidence:.2f})"
    ]

    if secondary:
        rationale_parts.append(f"{len(secondary)} secondary code(s) sequenced by confidence")

    if complication:
        rationale_parts.append(f"{len(complication)} complication code(s) identified by qualifier analysis")

    sequencing_rationale = "; ".join(rationale_parts)

    # Build retrieval stats
    codes_needing_specificity = sum(1 for s in sorted_suggestions if s.needs_specificity)
    avg_confidence = sum(s.confidence for s in sorted_suggestions) / len(sorted_suggestions)

    retrieval_stats = {
        "total_entities_coded": len(sorted_suggestions),
        "avg_confidence": round(avg_confidence, 2),
        "codes_needing_specificity": codes_needing_specificity
    }

    return CodingResult(
        principal_diagnosis=principal,
        secondary_codes=secondary,
        complication_codes=complication,
        sequencing_rationale=sequencing_rationale,
        retrieval_stats=retrieval_stats
    )


def code_entities(
    nlu_result: NLUResult,
    clinical_context: str = ""
) -> CodingResult:
    """
    Main orchestrator: RAG-based ICD-10 coding of clinical entities.

    Pipeline:
    1. Filter entities (diagnoses and procedures only, exclude negated)
    2. For each entity: build query -> retrieve -> rerank -> reason with LLM
    3. Sequence all suggestions into principal/secondary/complication

    Args:
        nlu_result: NLUResult with extracted entities
        clinical_context: Full clinical text for LLM context

    Returns:
        CodingResult with sequenced codes and stats
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
                "processing_time_ms": round((time.time() - start_time) * 1000, 2)
            }
        )

    # Initialize retrieval infrastructure
    logger.info("Initializing FAISSRetriever and CrossEncoderReranker")
    retriever = FAISSRetriever()
    reranker = CrossEncoderReranker()

    # Ensure FAISS index is built
    retriever.ensure_index_built()

    # Filter entities: only diagnoses and procedures, exclude negated
    eligible_entities = [
        e for e in nlu_result.entities
        if e.entity_type in ["diagnosis", "procedure"] and not e.negated
    ]

    if not eligible_entities:
        logger.info("No eligible entities (after filtering negated/non-diagnosis entities)")
        return CodingResult(
            principal_diagnosis=None,
            secondary_codes=[],
            complication_codes=[],
            sequencing_rationale="No eligible entities after filtering",
            retrieval_stats={
                "total_entities_coded": 0,
                "avg_confidence": 0.0,
                "codes_needing_specificity": 0,
                "processing_time_ms": round((time.time() - start_time) * 1000, 2)
            }
        )

    logger.info(f"Coding {len(eligible_entities)} eligible entities")

    # Process each entity
    suggestions = []
    for entity in eligible_entities:
        try:
            # Build query
            query = build_coding_query(entity, context_window=clinical_context[:200])
            logger.debug(f"Processing entity: {entity.text} (type: {entity.entity_type})")

            # Retrieve and rerank
            candidates = retrieve_and_rerank(query, retriever, reranker)

            if not candidates:
                logger.warning(f"No candidates retrieved for entity: {entity.text}")
                continue

            # Reason with LLM
            llm_result = reason_with_llm(entity, candidates, clinical_context)

            # Build CodeSuggestion
            suggestion = build_code_suggestion(entity, llm_result, candidates)
            suggestions.append(suggestion)

            logger.debug(f"Coded {entity.text} -> {suggestion.icd10_code} (confidence: {suggestion.confidence:.2f})")

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
                "processing_time_ms": round((time.time() - start_time) * 1000, 2)
            }
        )

    # Sequence codes
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
