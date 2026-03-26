"""
Ambient listening module for cliniq_v2.

Provides encounter transcription via OpenAI Whisper API, SOAP note generation
via GPT-4o, and full ambient pipeline integration with cliniq_v2 CDI analysis.

Replaces:
- faster-whisper local model with OpenAI Whisper API (whisper-1)
- Qwen LLM with GPT-4o for SOAP note generation
- cliniq.pipeline with cliniq_v2.pipeline for CDI analysis

Reuses:
- Pydantic models from cliniq.models.ambient
- Section parsing from cliniq.modules.m6_ambient._parse_note_sections
"""

import logging
from uuid import uuid4

from cliniq.models.ambient import (
    DisambiguationItem,
    EncounterTranscript,
    StructuredNote,
)
from cliniq.modules.m6_ambient import _parse_note_sections

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Function 1: Audio transcription via OpenAI Whisper API
# ---------------------------------------------------------------------------


def transcribe_audio(audio_path: str) -> EncounterTranscript:
    """
    Transcribe an audio file to an EncounterTranscript using OpenAI Whisper API.

    Uses the whisper-1 model. No local model loading or caching needed
    (API is stateless).

    Args:
        audio_path: Path to the audio file (WAV, MP3, M4A supported).

    Returns:
        EncounterTranscript with raw_text populated and duration_seconds=0.0
        (Whisper API does not return duration).
    """
    from cliniq_v2.api_client import OpenAIClient

    client = OpenAIClient().client

    with open(audio_path, "rb") as f:
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="en",
        )

    transcript_text = transcription.text

    logger.info(
        "Transcription complete: %d words (via Whisper API)",
        len(transcript_text.split()),
    )

    return EncounterTranscript(
        raw_text=transcript_text,
        duration_seconds=0.0,
    )


# ---------------------------------------------------------------------------
# Function 2: SOAP note generation via GPT-4o
# ---------------------------------------------------------------------------


def generate_soap_note(transcript_text: str) -> StructuredNote:
    """
    Generate a structured SOAP note from a conversation transcript using GPT-4o.

    Parses the GPT-4o output into individual sections (CC, HPI, Assessment, Plan).
    Falls back to using the raw transcript as the note if generation fails.

    Args:
        transcript_text: Full doctor-patient conversation transcript.

    Returns:
        StructuredNote with parsed sections and full_text.
    """
    from cliniq_v2.api_client import OpenAIClient

    try:
        client = OpenAIClient().client
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a medical scribe. Convert doctor-patient "
                        "conversation transcripts into structured clinical notes."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Convert this transcript into a structured clinical note "
                        "with these sections:\n"
                        "- Chief Complaint (CC)\n"
                        "- History of Present Illness (HPI)\n"
                        "- Assessment\n"
                        "- Plan\n\n"
                        "Return ONLY the clinical note. Do not add commentary.\n\n"
                        f"Transcript:\n{transcript_text}"
                    ),
                },
            ],
            max_tokens=1024,
            temperature=0.3,
        )
        generated_text = response.choices[0].message.content

        if not generated_text:
            logger.warning("GPT-4o generated empty note, falling back to raw transcript")
            return StructuredNote(full_text=transcript_text)

        # Parse sections using reused parser from cliniq
        note = _parse_note_sections(generated_text)

        logger.info(
            "SOAP note generated: %d chars, sections parsed (via GPT-4o)",
            len(generated_text),
        )
        return note

    except Exception as e:
        logger.warning(
            "SOAP note generation failed: %s, falling back to raw transcript", e
        )
        return StructuredNote(full_text=transcript_text)


# ---------------------------------------------------------------------------
# Function 3: Full ambient pipeline
# ---------------------------------------------------------------------------


def run_ambient_pipeline(
    transcript_text: str,
    use_llm_queries: bool = False,
) -> tuple[StructuredNote, "PipelineResult", list[DisambiguationItem]]:
    """
    Run the full ambient pipeline: note generation -> CDI analysis -> disambiguation.

    Generates a SOAP note from the transcript, runs the audited pipeline on it
    (via cliniq_v2.pipeline), and converts CDI findings into disambiguation items
    for provider review.

    Args:
        transcript_text: Full doctor-patient conversation transcript.
        use_llm_queries: Whether to use LLM for physician query generation
            in the CDI stage. Defaults to False for faster processing.

    Returns:
        Tuple of (StructuredNote, PipelineResult, list[DisambiguationItem]).
    """
    from cliniq_v2.pipeline import PipelineResult, run_pipeline_audited

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
