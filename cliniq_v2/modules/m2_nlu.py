"""
Module M2: Natural Language Understanding (NLU) -- ClinIQ v2

Extracts clinical entities from narrative text using GPT-4o structured output.
GPT-4o handles entity typing, negation detection, and qualifier extraction
in a single API call, replacing the local NER model + pattern-based pipeline.

Key functions:
- extract_entities(text: str) -> NLUResult: Main entry point for entity extraction
- process_document(doc: ClinicalDocument) -> NLUResult: Convenience wrapper for documents
"""

import json
import logging
import time

from cliniq.models.document import ClinicalDocument
from cliniq.models.entities import ClinicalEntity, NLUResult

from cliniq_v2.api_client import OpenAIClient
from cliniq_v2.config import CONFIDENCE_THRESHOLD, MODEL_REGISTRY

logger = logging.getLogger(__name__)

# System prompt instructing GPT-4o to perform clinical NER
NER_SYSTEM_PROMPT = """You are a clinical NER system. Extract all clinical entities from the text.

For each entity, provide:
- text: the exact text span as it appears in the original text
- entity_type: one of "diagnosis", "procedure", "medication", "anatomical_site", "lab_value", "qualifier"
- confidence: your confidence score between 0.0 and 1.0
- negated: true if the entity is negated (e.g., "no fever", "denies pain", "ruled out pneumonia")
- qualifiers: list of qualifying terms associated with this entity (e.g., ["stage 3", "chronic", "bilateral"])

Do NOT include character offsets -- they will be computed post-hoc.

Return a JSON object with the following structure:
{"entities": [{"text": "...", "entity_type": "...", "confidence": 0.95, "negated": false, "qualifiers": ["..."]}]}

If no entities are found, return: {"entities": []}"""


def _compute_offsets(entity_text: str, source_text: str) -> tuple[int, int]:
    """Compute start_char and end_char by finding entity text in the source.

    Args:
        entity_text: The entity text to locate.
        source_text: The full source text.

    Returns:
        Tuple of (start_char, end_char).
    """
    idx = source_text.find(entity_text)
    if idx >= 0:
        return idx, idx + len(entity_text)
    # Fallback: case-insensitive search
    idx_lower = source_text.lower().find(entity_text.lower())
    if idx_lower >= 0:
        return idx_lower, idx_lower + len(entity_text)
    # Final fallback if not found
    return 0, len(entity_text)


def _capture_qualifiers(
    entities: list[ClinicalEntity],
) -> list[ClinicalEntity]:
    """Separate qualifiers and attach them to nearest diagnosis/procedure within 50 chars.

    Mirrors the qualifier capture logic from cliniq.modules.m2_nlu.capture_qualifiers.

    Args:
        entities: List of ClinicalEntity instances (some may be qualifiers).

    Returns:
        Non-qualifier entities with qualifiers attached.
    """
    qualifiers = [e for e in entities if e.entity_type == "qualifier"]
    non_qualifiers = [e for e in entities if e.entity_type != "qualifier"]

    for qualifier in qualifiers:
        best_match = None
        best_distance = float("inf")

        for entity in non_qualifiers:
            if entity.entity_type in ("diagnosis", "procedure"):
                distance = min(
                    abs(qualifier.start_char - entity.end_char),
                    abs(entity.start_char - qualifier.end_char),
                )
                if distance < best_distance and distance <= 50:
                    best_distance = distance
                    best_match = entity

        if best_match is not None:
            best_match.qualifiers.append(qualifier.text)
            logger.debug(
                "Attached qualifier '%s' to entity '%s'",
                qualifier.text,
                best_match.text,
            )

    return non_qualifiers


def extract_entities(text: str) -> NLUResult:
    """
    Extract clinical entities from narrative text using GPT-4o structured output.

    Orchestrates:
    1. Sends text to GPT-4o with NER system prompt
    2. Parses JSON response into entity dicts
    3. Computes character offsets post-hoc
    4. Creates ClinicalEntity instances filtered by confidence threshold
    5. Runs qualifier capture logic
    6. Returns NLUResult with entities and processing time

    Args:
        text: Clinical narrative text.

    Returns:
        NLUResult with typed entities and processing time.
    """
    start_time = time.time()

    # Call GPT-4o for NER
    client = OpenAIClient().client
    response = client.chat.completions.create(
        model=MODEL_REGISTRY["REASONING_LLM"],
        messages=[
            {"role": "system", "content": NER_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        response_format={"type": "json_object"},
        temperature=0.0,
    )

    # Parse JSON response
    raw_content = response.choices[0].message.content or '{"entities": []}'
    raw = json.loads(raw_content)
    raw_entities = raw.get("entities", [])

    logger.debug("GPT-4o returned %d raw entities", len(raw_entities))

    # Convert to ClinicalEntity instances
    entities: list[ClinicalEntity] = []
    for item in raw_entities:
        entity_text = item.get("text", "")
        entity_type = item.get("entity_type", "other")
        confidence = item.get("confidence", 0.0)
        negated = item.get("negated", False)
        qualifiers = item.get("qualifiers", [])

        # Compute offsets post-hoc
        start_char, end_char = _compute_offsets(entity_text, text)

        entity = ClinicalEntity(
            text=entity_text,
            entity_type=entity_type,
            start_char=start_char,
            end_char=end_char,
            confidence=confidence,
            negated=negated,
            qualifiers=qualifiers,
        )
        entities.append(entity)

    # Filter by confidence threshold (keep qualifiers regardless)
    filtered = [
        e
        for e in entities
        if e.confidence >= CONFIDENCE_THRESHOLD or e.entity_type == "qualifier"
    ]

    logger.debug(
        "Filtered %d entities to %d (threshold=%s)",
        len(entities),
        len(filtered),
        CONFIDENCE_THRESHOLD,
    )

    # Capture qualifiers and attach to nearest diagnosis/procedure
    filtered = _capture_qualifiers(filtered)

    # Calculate processing time
    processing_time_ms = (time.time() - start_time) * 1000

    logger.info(
        "Extracted %d entities in %.2fms", len(filtered), processing_time_ms
    )

    return NLUResult(
        entities=filtered,
        processing_time_ms=processing_time_ms,
    )


def process_document(doc: ClinicalDocument) -> NLUResult:
    """
    Extract entities from a ClinicalDocument.

    Convenience wrapper that validates the document has narrative text
    and calls extract_entities().

    Args:
        doc: ClinicalDocument with raw_narrative field.

    Returns:
        NLUResult with extracted entities.

    Raises:
        ValueError: If doc.raw_narrative is empty or None.
    """
    if not doc.raw_narrative or not doc.raw_narrative.strip():
        raise ValueError("ClinicalDocument.raw_narrative cannot be empty")

    return extract_entities(doc.raw_narrative)
