"""
Ambient listening session schemas.

Defines the data contracts for ambient encounter processing:
- EncounterTranscript: audio transcription output
- StructuredNote: generated SOAP note sections
- DisambiguationItem: CDI-derived items needing provider attention
- AmbientSession: full session state container
- AmbientEncounterDemo: pre-computed demo encounter data
"""

from pydantic import BaseModel, Field, computed_field


class EncounterTranscript(BaseModel):
    """
    Transcription output from an audio encounter.

    Holds the full conversation text and optional speaker-labeled segments
    for future diarization support.
    """

    raw_text: str
    speaker_segments: list[dict] = Field(default_factory=list)
    duration_seconds: float = 0.0

    @computed_field
    @property
    def word_count(self) -> int:
        """Total word count of the transcript."""
        return len(self.raw_text.split())


class StructuredNote(BaseModel):
    """
    Structured clinical note parsed into SOAP sections.

    The full_text field contains the complete note and is the primary
    input for run_pipeline_audited.
    """

    chief_complaint: str = ""
    hpi: str = ""
    ros: str = ""
    physical_exam: str = ""
    assessment: str = ""
    plan: str = ""
    full_text: str


class DisambiguationItem(BaseModel):
    """
    A single item requiring provider disambiguation.

    Derived from CDI analysis results (documentation gaps, missed diagnoses,
    code conflicts) and presented to the provider for resolution.
    """

    item_id: str
    category: str  # "gap", "missed_diagnosis", "conflict", "ambiguity"
    title: str
    description: str
    suggested_action: str
    source_code: str = ""
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    status: str = Field(default="pending")  # "pending", "accepted", "dismissed"


class AmbientSession(BaseModel):
    """
    Full ambient listening session state container.

    Tracks the lifecycle of a single encounter from recording through
    processing to results display.
    """

    session_id: str
    state: str = Field(default="idle")  # "idle", "recording", "processing", "results"
    transcript: EncounterTranscript | None = None
    generated_note: StructuredNote | None = None
    pipeline_result_json: dict | None = None
    disambiguation_items: list[DisambiguationItem] = Field(default_factory=list)
    session_duration_seconds: float = 0.0
    is_demo: bool = False


class AmbientEncounterDemo(BaseModel):
    """
    Pre-computed demo encounter for the ambient listening UI.

    Contains all pipeline outputs pre-computed so the demo can run
    without model downloads or GPU requirements.
    """

    encounter_id: str
    encounter_label: str
    scenario_description: str
    specialty: str = ""
    transcript: str
    generated_note: str
    pipeline_result: dict
    disambiguation_items: list[dict] = Field(default_factory=list)
    session_duration_seconds: int = 180
