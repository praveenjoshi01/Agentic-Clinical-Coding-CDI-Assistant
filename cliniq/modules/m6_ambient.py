"""
Ambient listening module for encounter transcription, note generation, and CDI integration.

Provides three main functions:
1. transcribe_audio: WAV file -> EncounterTranscript (via faster-whisper)
2. generate_soap_note: transcript text -> StructuredNote (via Qwen LLM)
3. run_ambient_pipeline: transcript text -> (StructuredNote, PipelineResult, disambiguation items)

All heavy dependencies (faster-whisper, transformers) use lazy imports to avoid
loading models at import time.
"""

import logging
from typing import Optional
from uuid import uuid4

from cliniq.models.ambient import (
    DisambiguationItem,
    EncounterTranscript,
    StructuredNote,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level model cache (same pattern as _KG_CACHE in m4_cdi.py)
# ---------------------------------------------------------------------------

_whisper_model: Optional[object] = None


# ---------------------------------------------------------------------------
# Function 1: Audio transcription
# ---------------------------------------------------------------------------


def transcribe_audio(audio_path: str) -> EncounterTranscript:
    """
    Transcribe a WAV audio file to an EncounterTranscript.

    Uses faster-whisper with the 'small' model on CPU with int8 quantisation.
    The model is loaded lazily on first call and cached for reuse.

    Args:
        audio_path: Path to the WAV audio file.

    Returns:
        EncounterTranscript with raw_text and duration_seconds populated.
    """
    global _whisper_model

    # Lazy import and model loading
    if _whisper_model is None:
        from faster_whisper import WhisperModel

        logger.info("Loading faster-whisper 'small' model (first call, will be cached)")
        _whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
        logger.info("Whisper model loaded successfully")

    segments, info = _whisper_model.transcribe(audio_path, beam_size=5)

    # segments is a generator -- iterate to collect all text
    segment_texts = []
    for segment in segments:
        segment_texts.append(segment.text.strip())

    transcript_text = " ".join(segment_texts)
    duration = info.duration

    logger.info(
        "Transcription complete: %d words, %.1f seconds duration",
        len(transcript_text.split()),
        duration,
    )

    return EncounterTranscript(
        raw_text=transcript_text,
        duration_seconds=duration,
    )


# ---------------------------------------------------------------------------
# Function 2: SOAP note generation
# ---------------------------------------------------------------------------


def generate_soap_note(transcript_text: str) -> StructuredNote:
    """
    Generate a structured SOAP note from a conversation transcript using Qwen LLM.

    Parses the LLM output into individual sections (CC, HPI, Assessment, Plan).
    Falls back to using the raw transcript as the note if generation fails.

    Args:
        transcript_text: Full doctor-patient conversation transcript.

    Returns:
        StructuredNote with parsed sections and full_text.
    """
    from cliniq.model_manager import ModelManager

    prompt = (
        "You are a medical scribe. Convert this doctor-patient conversation "
        "transcript into a structured clinical note.\n\n"
        f"Transcript:\n{transcript_text}\n\n"
        "Write the clinical note with these sections:\n"
        "- Chief Complaint (CC)\n"
        "- History of Present Illness (HPI)\n"
        "- Assessment\n"
        "- Plan\n\n"
        "Return ONLY the clinical note. Do not add commentary.\n\n"
        "Clinical Note:"
    )

    try:
        model, tokenizer = ModelManager().get_reasoning_llm()

        inputs = tokenizer(prompt, return_tensors="pt")
        outputs = model.generate(
            inputs.input_ids,
            max_new_tokens=512,
            temperature=0.3,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
        )

        full_response = tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Extract generated text after the prompt
        # Find the end of the prompt marker in the decoded output
        marker = "Clinical Note:"
        marker_idx = full_response.rfind(marker)
        if marker_idx != -1:
            generated_text = full_response[marker_idx + len(marker) :].strip()
        else:
            # Fallback: take everything after the transcript
            generated_text = full_response[len(prompt) :].strip()

        if not generated_text:
            logger.warning("LLM generated empty note, falling back to raw transcript")
            return StructuredNote(full_text=transcript_text)

        # Parse sections from the generated text
        note = _parse_note_sections(generated_text)

        logger.info(
            "SOAP note generated: %d chars, sections parsed",
            len(generated_text),
        )
        return note

    except Exception as e:
        logger.warning(
            "SOAP note generation failed: %s, falling back to raw transcript", e
        )
        return StructuredNote(full_text=transcript_text)


def _parse_note_sections(text: str) -> StructuredNote:
    """
    Parse a generated clinical note into StructuredNote sections.

    Looks for section headers (Chief Complaint/CC, HPI/History, Assessment, Plan)
    using simple string splitting. Unrecognised sections are left empty.

    Args:
        text: The full generated clinical note text.

    Returns:
        StructuredNote with parsed sections and full_text set to the input.
    """
    text_lower = text.lower()

    # Define section markers (order matters -- later markers end earlier sections)
    section_markers = [
        ("chief_complaint", ["chief complaint", "cc:"]),
        ("hpi", ["history of present illness", "hpi:", "history:"]),
        ("assessment", ["assessment:", "assessment\n"]),
        ("plan", ["plan:", "plan\n"]),
    ]

    sections: dict[str, str] = {}

    for field_name, markers in section_markers:
        best_idx = -1
        best_marker_len = 0
        for marker in markers:
            idx = text_lower.find(marker)
            if idx != -1 and (best_idx == -1 or idx < best_idx):
                best_idx = idx
                best_marker_len = len(marker)

        if best_idx != -1:
            sections[field_name] = (best_idx, best_marker_len)

    # Sort sections by position to extract text between them
    sorted_sections = sorted(sections.items(), key=lambda x: x[1][0])

    parsed: dict[str, str] = {}
    for i, (field_name, (start_idx, marker_len)) in enumerate(sorted_sections):
        content_start = start_idx + marker_len
        if i + 1 < len(sorted_sections):
            content_end = sorted_sections[i + 1][1][0]
        else:
            content_end = len(text)
        parsed[field_name] = text[content_start:content_end].strip()

    return StructuredNote(
        chief_complaint=parsed.get("chief_complaint", ""),
        hpi=parsed.get("hpi", ""),
        assessment=parsed.get("assessment", ""),
        plan=parsed.get("plan", ""),
        full_text=text,
    )


# ---------------------------------------------------------------------------
# Function 3: Full ambient pipeline
# ---------------------------------------------------------------------------


def run_ambient_pipeline(
    transcript_text: str,
    use_llm_queries: bool = False,
) -> tuple[StructuredNote, "PipelineResult", list[DisambiguationItem]]:
    """
    Run the full ambient pipeline: note generation -> CDI analysis -> disambiguation.

    Generates a SOAP note from the transcript, runs the audited pipeline on it,
    and converts CDI findings into disambiguation items for provider review.

    Args:
        transcript_text: Full doctor-patient conversation transcript.
        use_llm_queries: Whether to use LLM for physician query generation
            in the CDI stage. Defaults to False for faster processing.

    Returns:
        Tuple of (StructuredNote, PipelineResult, list[DisambiguationItem]).
    """
    from cliniq.pipeline import PipelineResult, run_pipeline_audited

    # Step 1: Generate structured note from transcript
    note = generate_soap_note(transcript_text)
    logger.info("Ambient pipeline: note generated (%d chars)", len(note.full_text))

    # Step 2: Run audited pipeline on the generated note
    result: PipelineResult = run_pipeline_audited(
        note.full_text, use_llm_queries=use_llm_queries
    )
    logger.info(
        "Ambient pipeline: pipeline complete (%.1f ms, %d errors)",
        result.processing_time_ms,
        len(result.errors),
    )

    # Step 3: Build disambiguation items from CDI report
    disambiguation_items: list[DisambiguationItem] = []

    if result.cdi_report is not None:
        # Documentation gaps
        for gap in result.cdi_report.documentation_gaps:
            disambiguation_items.append(
                DisambiguationItem(
                    item_id=uuid4().hex[:8],
                    category="gap",
                    title=f"Documentation Gap: {gap.code}",
                    description=gap.physician_query,
                    suggested_action=f"Clarify {gap.missing_qualifier} for {gap.code}",
                    source_code=gap.code,
                    confidence=gap.confidence,
                )
            )

        # Missed diagnoses
        for md in result.cdi_report.missed_diagnoses:
            disambiguation_items.append(
                DisambiguationItem(
                    item_id=uuid4().hex[:8],
                    category="missed_diagnosis",
                    title=f"Potential Missed Dx: {md.suggested_code}",
                    description=md.description,
                    suggested_action=(
                        f"Consider documenting {md.suggested_code} ({md.description})"
                    ),
                    source_code=md.suggested_code,
                    confidence=md.co_occurrence_weight,
                )
            )

        # Code conflicts
        for cc in result.cdi_report.code_conflicts:
            disambiguation_items.append(
                DisambiguationItem(
                    item_id=uuid4().hex[:8],
                    category="conflict",
                    title=f"Code Conflict: {cc.code_a} vs {cc.code_b}",
                    description=cc.conflict_reason,
                    suggested_action=cc.recommendation,
                    source_code=f"{cc.code_a},{cc.code_b}",
                )
            )

    logger.info(
        "Ambient pipeline: %d disambiguation items generated",
        len(disambiguation_items),
    )

    return (note, result, disambiguation_items)
