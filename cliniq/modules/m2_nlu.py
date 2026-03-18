"""
Module M2: Natural Language Understanding (NLU)

Extracts clinical entities from narrative text using d4data/biomedical-ner-all NER model,
maps entity labels to pipeline categories, detects negation using pattern matching,
and captures qualifiers (severity, descriptions) to enrich entity annotations.

Key functions:
- extract_entities(text: str) -> NLUResult: Main entry point for entity extraction
- process_document(doc: ClinicalDocument) -> NLUResult: Convenience wrapper for documents
"""

import logging
import re
import time
from typing import Any

from cliniq.config import CONFIDENCE_THRESHOLD
from cliniq.model_manager import ModelManager
from cliniq.models.document import ClinicalDocument
from cliniq.models.entities import ENTITY_TYPE_MAP, ClinicalEntity, NLUResult

logger = logging.getLogger(__name__)

# Negation trigger patterns
NEGATION_TRIGGERS = [
    "no", "not", "without", "denies", "denied", "deny",
    "no evidence of", "ruled out", "negative for", "absence of",
    "free of", "no sign of", "no signs of"
]

# Termination terms that stop negation scope
TERMINATION_TERMS = ["but", "however", "although", "except", "though", "yet"]


def map_entity_type(model_label: str) -> str:
    """
    Map d4data biomedical-ner-all labels to pipeline entity categories.

    Handles both bare labels ("Disease_disorder") and BIO-prefixed labels
    ("B-Disease_disorder", "I-Disease_disorder") by stripping the prefix.

    Args:
        model_label: Raw label from NER model (may have B- or I- prefix)

    Returns:
        Mapped category ("diagnosis", "procedure", "medication", etc.) or "other"
    """
    # Strip BIO prefix if present
    clean_label = model_label
    if model_label.startswith("B-") or model_label.startswith("I-"):
        clean_label = model_label[2:]

    # Map to pipeline category
    return ENTITY_TYPE_MAP.get(clean_label, "other")


def extract_raw_entities(text: str) -> list[dict[str, Any]]:
    """
    Extract raw entities using the d4data biomedical NER pipeline.

    Args:
        text: Clinical narrative text

    Returns:
        List of raw entity dicts with keys: entity_group, score, word, start, end
    """
    ner_pipe = ModelManager().get_ner_pipeline()

    # Pipeline with aggregation_strategy="simple" already merges subword tokens
    results = ner_pipe(text)

    logger.debug(f"Extracted {len(results)} raw entities from text of length {len(text)}")
    return results


def detect_negation(text: str, entities: list[ClinicalEntity]) -> list[ClinicalEntity]:
    """
    Detect negation for clinical entities using pattern-based approach.

    Looks backward from each entity for negation triggers within a 6-token window.
    Stops if a termination term is found between trigger and entity.

    Args:
        text: Original clinical text
        entities: List of ClinicalEntity instances

    Returns:
        Updated entity list with negated flags set
    """
    # Tokenize text simply by splitting on whitespace and punctuation
    # This is a simple approach that works well for clinical text
    tokens = re.findall(r'\b\w+\b', text.lower())

    for entity in entities:
        # Get the entity position in the text
        entity_start = entity.start_char

        # Extract text before entity (up to 100 characters back for 6-token window)
        lookback_start = max(0, entity_start - 100)
        lookback_text = text[lookback_start:entity_start].lower()

        # Check for negation triggers
        negation_found = False
        termination_found = False

        # Look for triggers in reverse order (closest to entity first)
        for trigger in NEGATION_TRIGGERS:
            if trigger in lookback_text:
                # Check if there's a termination term between trigger and entity
                trigger_pos = lookback_text.rfind(trigger)
                text_after_trigger = lookback_text[trigger_pos + len(trigger):]

                # Check for termination terms
                for term in TERMINATION_TERMS:
                    if term in text_after_trigger:
                        termination_found = True
                        break

                if not termination_found:
                    negation_found = True
                    break

        if negation_found:
            entity.negated = True
            logger.debug(f"Marked entity '{entity.text}' as negated")

    return entities


def capture_qualifiers(text: str, entities: list[ClinicalEntity]) -> list[ClinicalEntity]:
    """
    Capture qualifiers and attach them to parent entities.

    Finds qualifier entities (severity, detailed_description, etc.) and attaches
    them to the nearest diagnosis/procedure entity within a 50-character window.
    Removes standalone qualifier entities from the main list.

    Args:
        text: Original clinical text
        entities: List of ClinicalEntity instances

    Returns:
        Updated entity list with qualifiers attached to parent entities
    """
    # Separate qualifiers from other entities
    qualifiers = [e for e in entities if e.entity_type == "qualifier"]
    non_qualifiers = [e for e in entities if e.entity_type != "qualifier"]

    # For each qualifier, find the nearest diagnosis or procedure
    for qualifier in qualifiers:
        best_match = None
        best_distance = float('inf')

        for entity in non_qualifiers:
            if entity.entity_type in ["diagnosis", "procedure"]:
                # Calculate distance between qualifier and entity
                distance = min(
                    abs(qualifier.start_char - entity.end_char),
                    abs(entity.start_char - qualifier.end_char)
                )

                # Must be within 50 characters
                if distance < best_distance and distance <= 50:
                    best_distance = distance
                    best_match = entity

        # Attach qualifier to best match
        if best_match is not None:
            best_match.qualifiers.append(qualifier.text)
            logger.debug(f"Attached qualifier '{qualifier.text}' to entity '{best_match.text}'")

    return non_qualifiers


def extract_entities(text: str) -> NLUResult:
    """
    Extract clinical entities from narrative text with negation and qualifiers.

    Main orchestrator function that:
    1. Extracts raw entities using d4data NER model
    2. Maps entity labels to pipeline categories
    3. Filters by confidence threshold (0.80)
    4. Detects negation
    5. Captures and attaches qualifiers

    Args:
        text: Clinical narrative text

    Returns:
        NLUResult with typed entities, processing time, and computed properties
    """
    start_time = time.time()

    # Extract raw entities
    raw_entities = extract_raw_entities(text)

    # Map to ClinicalEntity with type mapping
    entities = []
    for raw in raw_entities:
        entity_type = map_entity_type(raw["entity_group"])

        # Create ClinicalEntity
        entity = ClinicalEntity(
            text=raw["word"],
            entity_type=entity_type,
            start_char=raw["start"],
            end_char=raw["end"],
            confidence=raw["score"]
        )

        entities.append(entity)

    # Filter by confidence threshold (but keep qualifiers regardless)
    filtered_entities = [
        e for e in entities
        if e.confidence >= CONFIDENCE_THRESHOLD or e.entity_type == "qualifier"
    ]

    logger.debug(f"Filtered {len(entities)} entities to {len(filtered_entities)} "
                f"(threshold={CONFIDENCE_THRESHOLD})")

    # Detect negation
    filtered_entities = detect_negation(text, filtered_entities)

    # Capture qualifiers
    filtered_entities = capture_qualifiers(text, filtered_entities)

    # Calculate processing time
    end_time = time.time()
    processing_time_ms = (end_time - start_time) * 1000

    logger.info(f"Extracted {len(filtered_entities)} entities in {processing_time_ms:.2f}ms")

    return NLUResult(
        entities=filtered_entities,
        processing_time_ms=processing_time_ms
    )


def process_document(doc: ClinicalDocument) -> NLUResult:
    """
    Extract entities from a ClinicalDocument.

    Convenience wrapper that validates the document has narrative text
    and calls extract_entities().

    Args:
        doc: ClinicalDocument with raw_narrative field

    Returns:
        NLUResult with extracted entities

    Raises:
        ValueError: If doc.raw_narrative is empty or None
    """
    if not doc.raw_narrative or not doc.raw_narrative.strip():
        raise ValueError("ClinicalDocument.raw_narrative cannot be empty")

    return extract_entities(doc.raw_narrative)
