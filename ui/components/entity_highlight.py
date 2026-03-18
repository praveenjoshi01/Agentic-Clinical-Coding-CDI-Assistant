"""
NER entity annotation rendering with overlap resolution.

Converts a clinical narrative and entity list into color-coded
annotated text using the st-annotated-text library.
"""

from __future__ import annotations

from typing import Any

from annotated_text import annotated_text

from ui.components.theme import ENTITY_COLORS


def _resolve_overlaps(entities: list[Any]) -> list[Any]:
    """Remove overlapping entity spans, keeping the higher-confidence one.

    If confidences are equal, keeps the longer span.
    Entities must have start_char, end_char, and confidence attributes.
    """
    if not entities:
        return []

    # Sort by start_char, then by span length descending (longer first)
    sorted_ents = sorted(
        entities, key=lambda e: (e.start_char, -(e.end_char - e.start_char))
    )

    resolved: list[Any] = []
    for ent in sorted_ents:
        overlaps = False
        for kept in resolved:
            # Check overlap: two spans overlap if one starts before the other ends
            if ent.start_char < kept.end_char and ent.end_char > kept.start_char:
                # Overlap detected -- keep existing if higher confidence or longer
                if kept.confidence > ent.confidence:
                    overlaps = True
                    break
                elif kept.confidence == ent.confidence:
                    kept_len = kept.end_char - kept.start_char
                    ent_len = ent.end_char - ent.start_char
                    if kept_len >= ent_len:
                        overlaps = True
                        break
                    else:
                        # New entity is longer with equal confidence -- replace
                        resolved.remove(kept)
                        break
                else:
                    # New entity has higher confidence -- replace
                    resolved.remove(kept)
                    break

        if not overlaps:
            resolved.append(ent)

    # Re-sort by start position after resolution
    resolved.sort(key=lambda e: e.start_char)
    return resolved


def render_ner_highlights(narrative: str, entities: list[Any]) -> None:
    """Render clinical text with color-coded NER entity annotations.

    Sorts entities by position, resolves overlapping spans (keeping
    higher-confidence or longer entities), and renders using
    annotated_text from the st-annotated-text library.

    Args:
        narrative: The full clinical narrative text.
        entities: List of entity objects with start_char, end_char,
            entity_type, confidence, negated, and text attributes.
    """
    if not entities:
        annotated_text(narrative)
        return

    resolved = _resolve_overlaps(entities)
    parts: list[str | tuple[str, str, str]] = []
    last_end = 0

    for entity in resolved:
        # Add plain text before this entity
        if entity.start_char > last_end:
            parts.append(narrative[last_end : entity.start_char])

        # Build label with optional NEG prefix
        label = entity.entity_type.upper()
        if entity.negated:
            label = f"NEG {label}"

        color = ENTITY_COLORS.get(entity.entity_type, "#dddddd")
        parts.append((entity.text, label, color))
        last_end = entity.end_char

    # Add remaining text after last entity
    if last_end < len(narrative):
        parts.append(narrative[last_end:])

    annotated_text(*parts)
