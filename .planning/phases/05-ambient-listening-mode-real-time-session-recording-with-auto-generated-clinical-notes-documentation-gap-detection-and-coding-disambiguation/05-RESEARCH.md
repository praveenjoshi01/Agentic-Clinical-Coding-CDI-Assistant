# Phase 5: Ambient Listening Mode - Research

**Researched:** 2026-03-24
**Domain:** Real-time audio capture, speech-to-text, clinical note generation, Streamlit UI
**Confidence:** HIGH (standard libraries, well-documented patterns, interview-demo scope)

## Summary

Phase 5 adds an "Ambient Listening Mode" page to the existing Streamlit UI. The feature captures (or simulates) a physician-patient encounter, transcribes it, generates structured clinical notes (SOAP format), then feeds the transcript through the existing ClinIQ pipeline for documentation gap detection, missed diagnosis flagging, and coding disambiguation. This requires three new capabilities: (1) audio capture/transcription, (2) transcript-to-structured-note generation via LLM, and (3) a new Streamlit page with session lifecycle management.

**Critical design constraint:** This is an interview demo project, not production software. The project already uses a "pre-computed demo data" pattern extensively (Phase 4). The ambient listening mode MUST support both a live path (microphone -> Whisper -> LLM -> pipeline) and a pre-computed demo path (hardcoded transcript -> pre-computed results). The demo path is the primary interview experience; the live path demonstrates technical capability.

**Primary recommendation:** Use `st.audio_input` (native Streamlit, GA since v1.40.0) for audio capture, `faster-whisper` with the `small` model for local CPU transcription, Qwen2.5-1.5B-Instruct (already in stack) for SOAP note generation, and the existing `run_pipeline_audited` for downstream CDI analysis. Provide pre-computed demo encounters for instant, reliable interview demonstrations.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| streamlit | >=1.40.0 | `st.audio_input` for microphone recording, `@st.fragment` for timer | Native widget, no third-party component needed. Already >=1.35.0 in pyproject.toml; bump to >=1.40.0. |
| faster-whisper | >=1.1.0 | Local speech-to-text via CTranslate2-optimized Whisper | 4x faster than openai/whisper on CPU, int8 quantization, MIT license, ~150MB for `small` model |
| Qwen2.5-1.5B-Instruct | (already in stack) | SOAP note generation from transcript via prompted LLM | Already used for CDI reasoning; reuse for note generation avoids new model download |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic | >=2.0.0 (already in stack) | Schema for AmbientSession, EncounterTranscript, StructuredNote | All new data models follow project's Pydantic pattern |
| io / wave (stdlib) | N/A | Parse WAV bytes from st.audio_input | st.audio_input returns WAV UploadedFile; stdlib handles it |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| faster-whisper | openai-whisper (original) | 4x slower on CPU, higher memory; faster-whisper is strictly better for local inference |
| faster-whisper | streamlit-mic-recorder (built-in STT) | Third-party component, less control, depends on browser speech API |
| st.audio_input | streamlit-webrtc | Overkill for record-and-process; webrtc is for real-time streaming. st.audio_input is simpler and native |
| st.audio_input | streamlit-mic-recorder | Third-party custom component; st.audio_input is now native and stable |
| pyttsx3 (synthetic audio) | Pre-written transcript text | For demo mode, text transcript is simpler than generating fake audio files |

**Installation (new dependencies only):**
```bash
pip install faster-whisper>=1.1.0
```

**pyproject.toml update:**
```toml
dependencies = [
    # ... existing ...
    "streamlit>=1.40.0",  # bumped from >=1.35.0 for st.audio_input
    "faster-whisper>=1.1.0",
]
```

**Note on faster-whisper:** Requires `ctranslate2` (auto-installed). Works on Python 3.9-3.12. Does NOT require ffmpeg for WAV input (only for MP3/other formats). The `small` model (~461MB) auto-downloads from HuggingFace on first use, consistent with the project's lazy-download pattern.

## Architecture Patterns

### Recommended Project Structure
```
cliniq/
  models/
    ambient.py           # AmbientSession, EncounterTranscript, StructuredNote schemas
  modules/
    m6_ambient.py         # Transcription + note generation logic
ui/
  pages/
    ambient_mode.py       # New Streamlit page (AMB-01 through AMB-06)
  demo_data/
    ambient/
      encounter_001.json  # Pre-computed ambient demo (transcript + results)
      encounter_002.json  # Second pre-computed demo case
scripts/
  precompute_ambient.py   # Script to generate pre-computed ambient demo data
```

### Pattern 1: Session Lifecycle (AMB-01)
**What:** Manage ambient listening session state: idle -> recording -> processing -> results
**When to use:** The ambient mode page uses a state machine stored in `st.session_state`

```python
# Session states: "idle" | "recording" | "processing" | "results"
# Stored in st.session_state["ambient_state"]

# State transitions:
# idle -> recording: User clicks "Start Ambient Mode"
# recording -> processing: User clicks "End Session"
# processing -> results: Pipeline completes
# results -> idle: User clicks "New Session"
```

### Pattern 2: Timer Display with st.fragment (AMB-01)
**What:** Show a live elapsed-time counter during recording without blocking the UI
**When to use:** While session is in "recording" state, show HH:MM:SS timer

```python
import time
import streamlit as st
from datetime import datetime

@st.fragment(run_every=1.0)
def session_timer():
    """Auto-rerunning fragment that displays elapsed session time."""
    if st.session_state.get("ambient_state") != "recording":
        return
    start = st.session_state.get("recording_start_time")
    if start:
        elapsed = datetime.now() - start
        minutes, seconds = divmod(int(elapsed.total_seconds()), 60)
        hours, minutes = divmod(minutes, 60)
        st.metric("Session Duration", f"{hours:02d}:{minutes:02d}:{seconds:02d}")
```

**Requires:** Streamlit >=1.37.0 for `@st.fragment`. Already satisfied by >=1.40.0 requirement.

### Pattern 3: Dual-Path Architecture (Demo vs Live)
**What:** Support both pre-computed demo mode and live audio processing
**When to use:** Always -- demo mode is primary for interviews

```python
# Demo path (instant, reliable):
# 1. User selects a pre-computed encounter
# 2. System loads transcript + pre-computed pipeline results from JSON
# 3. Simulates "processing" with brief spinner
# 4. Displays results immediately

# Live path (shows technical capability):
# 1. User records audio via st.audio_input
# 2. faster-whisper transcribes WAV -> text
# 3. Qwen generates structured SOAP note from transcript
# 4. run_pipeline_audited processes the generated note
# 5. Results displayed with full CDI analysis
```

### Pattern 4: Transcript-to-Note Generation (AMB-02)
**What:** Use Qwen2.5-1.5B-Instruct to convert a conversation transcript into structured SOAP format
**When to use:** After transcription, before feeding to ClinIQ pipeline

```python
SOAP_GENERATION_PROMPT = """You are a medical scribe. Convert this doctor-patient conversation transcript into a structured clinical note in SOAP format.

Transcript:
{transcript}

Generate a clinical note with these sections:
- Chief Complaint (CC)
- History of Present Illness (HPI)
- Review of Systems (ROS) - only if discussed
- Physical Examination - only if discussed
- Assessment
- Plan

Return ONLY the clinical note text. Do not add commentary.
"""
```

### Pattern 5: Reuse Existing Pipeline for CDI (AMB-03, AMB-04, AMB-05)
**What:** Feed the generated SOAP note as plain text into `run_pipeline_audited`
**When to use:** After note generation -- leverages ALL existing CDI capabilities

```python
from cliniq.pipeline import run_pipeline_audited

# The generated SOAP note IS a clinical text note
# Feed it directly to the existing pipeline
result = run_pipeline_audited(
    input_data=generated_soap_note,  # plain text string
    use_llm_queries=False,  # template queries for speed
)
# result.cdi_report contains: documentation_gaps, missed_diagnoses, code_conflicts
```

This is the most important architectural decision: **do NOT rebuild CDI logic for ambient mode**. The existing pipeline already does NER, ICD-10 coding, gap detection, conflict detection, and missed diagnosis flagging. Ambient mode just needs to produce a clinical note (text string) and feed it through.

### Pattern 6: Disambiguation UI (AMB-06)
**What:** Present coding ambiguities, conflicts, and suggestions in a reviewable format
**When to use:** Results display after session processing

The existing CDI Analysis tab pattern in `pipeline_runner.py` already shows documentation gaps, missed diagnoses, and code conflicts in expandable sections. The ambient mode results page should reuse the same UI components (from `ui/components/`) but add an "Accept/Dismiss" interaction pattern for each suggestion.

### Anti-Patterns to Avoid
- **Real-time streaming transcription:** Do NOT attempt to transcribe audio in real-time during recording. The demo is record-then-process. Real-time streaming requires `streamlit-webrtc` and significantly more complexity for no demo benefit.
- **Generating fake audio files:** Do NOT use pyttsx3 or gTTS to synthesize audio for demo encounters. Pre-computed text transcripts are simpler, more reliable, and avoid audio generation dependencies.
- **Building a new CDI engine:** Do NOT create separate gap detection or coding logic for ambient mode. Reuse `run_pipeline_audited` entirely.
- **Blocking UI with timer loop:** Do NOT use `while True: time.sleep(1)` for the session timer. Use `@st.fragment(run_every=1.0)` for non-blocking updates.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Speech-to-text | Custom ASR pipeline | `faster-whisper` WhisperModel | Medical vocabulary, noise handling, punctuation -- all handled by Whisper |
| Audio recording in browser | Custom WebRTC/JS component | `st.audio_input` (native Streamlit) | Built-in, handles permissions, returns WAV bytes |
| SOAP note structure parsing | Custom regex parser | Qwen LLM prompted generation | LLM handles freeform transcript -> structured note naturally |
| CDI analysis on generated notes | Separate ambient CDI logic | Existing `run_pipeline_audited` | Already handles text input, NER, coding, CDI, audit trail |
| Session timer | while-loop with sleep | `@st.fragment(run_every=1.0)` | Non-blocking, Streamlit-native |
| WAV file handling | pydub/ffmpeg | Python stdlib `io.BytesIO` | st.audio_input returns WAV UploadedFile, compatible with faster-whisper directly |

**Key insight:** Phase 5 is primarily a UI/orchestration layer. The hard technical work (NER, coding, CDI, KG reasoning) is already built in Phases 1-2. The "ambient" aspect adds (1) audio capture, (2) transcription, and (3) note generation as a preprocessing step before the existing pipeline.

## Common Pitfalls

### Pitfall 1: st.audio_input Version Mismatch
**What goes wrong:** `st.audio_input` doesn't exist or is experimental
**Why it happens:** Project currently requires streamlit>=1.35.0 but st.audio_input GA is 1.40.0
**How to avoid:** Bump pyproject.toml to `streamlit>=1.40.0`
**Warning signs:** `AttributeError: module 'streamlit' has no attribute 'audio_input'`

### Pitfall 2: faster-whisper Model Download Size
**What goes wrong:** First-run experience takes minutes to download ~461MB model
**Why it happens:** Whisper `small` model auto-downloads from HuggingFace
**How to avoid:** Document in README. Use `small` model (not medium/large). In demo mode, transcription is skipped entirely (pre-computed).
**Warning signs:** Long pause on first "End Session" click

### Pitfall 3: Blocking UI During Transcription
**What goes wrong:** Streamlit freezes for 10-30 seconds during Whisper transcription
**Why it happens:** Whisper inference on CPU is synchronous and slow for long audio
**How to avoid:** Use `st.status` (like pipeline_status.py pattern) to show progress. Keep demo recordings short (1-2 minutes). Use `int8` quantization for faster inference.
**Warning signs:** Unresponsive UI after clicking "End Session"

### Pitfall 4: Audio Format Incompatibility
**What goes wrong:** faster-whisper can't read the audio bytes from st.audio_input
**Why it happens:** st.audio_input returns WAV in an UploadedFile wrapper (BytesIO subclass)
**How to avoid:** Save to a temporary file with `.wav` extension before passing to faster-whisper. Use `tempfile.NamedTemporaryFile(suffix=".wav")` pattern (already used in pipeline_runner.py for image uploads).
**Warning signs:** `RuntimeError` or `ValueError` from faster-whisper

### Pitfall 5: Qwen Generating Poor SOAP Notes
**What goes wrong:** 1.5B model produces incomplete or hallucinated clinical content
**Why it happens:** Small model, complex clinical task, no fine-tuning
**How to avoid:** Use explicit few-shot examples in the prompt. For demo mode, use pre-computed notes (bypass LLM entirely). For live mode, accept imperfect output -- the CDI layer catches gaps anyway, which is the demo's value proposition.
**Warning signs:** Missing SOAP sections, fabricated medications, nonsensical diagnoses

### Pitfall 6: Session State Reset on Page Navigation
**What goes wrong:** Recording state, timer, or results lost when navigating away
**Why it happens:** Streamlit re-runs full script on page change
**How to avoid:** Store all ambient session data in `st.session_state` (same pattern as `pipeline_result` in Phase 4). Key state variables: `ambient_state`, `recording_start_time`, `ambient_transcript`, `ambient_result`.
**Warning signs:** Timer resets, results disappear after viewing another page

### Pitfall 7: ctranslate2 Python Version Incompatibility
**What goes wrong:** `pip install faster-whisper` fails
**Why it happens:** ctranslate2 does not support Python 3.13+; no wheels available
**How to avoid:** Ensure Python 3.10-3.12 (project already specifies >=3.10). Verify during install.
**Warning signs:** `pip` build failure mentioning ctranslate2

## Code Examples

Verified patterns from official sources and project codebase:

### Audio Capture with st.audio_input (AMB-01)
```python
# Source: https://docs.streamlit.io/develop/api-reference/widgets/st.audio_input
# st.audio_input returns UploadedFile (BytesIO subclass) with WAV data at 16kHz
audio_bytes = st.audio_input(
    "Record encounter",
    key="ambient_audio",
    sample_rate=16000,  # default, optimal for speech recognition
)
if audio_bytes is not None:
    st.audio(audio_bytes)  # Playback
    # Save to temp file for Whisper
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes.getvalue())
        audio_path = tmp.name
```

### Transcription with faster-whisper (AMB-02 preprocessing)
```python
# Source: https://github.com/SYSTRAN/faster-whisper
from faster_whisper import WhisperModel

# Lazy-load model (follow ModelManager singleton pattern)
model = WhisperModel("small", device="cpu", compute_type="int8")

# Transcribe audio file
segments, info = model.transcribe(audio_path, beam_size=5)
transcript = " ".join(segment.text for segment in segments)
# Note: segments is a generator -- must iterate to trigger transcription
```

### SOAP Note Generation via Qwen (AMB-02)
```python
# Reuse existing ModelManager pattern from cliniq/model_manager.py
from cliniq.model_manager import ModelManager

model, tokenizer = ModelManager().get_reasoning_llm()

prompt = f"""You are a medical scribe. Convert this doctor-patient conversation into a structured clinical note.

Conversation:
{transcript}

Write a clinical note with:
- Chief Complaint
- History of Present Illness
- Assessment and Plan

Clinical Note:"""

inputs = tokenizer(prompt, return_tensors="pt")
outputs = model.generate(
    inputs.input_ids,
    max_new_tokens=512,
    temperature=0.3,
    do_sample=True,
    pad_token_id=tokenizer.eos_token_id,
)
generated_note = tokenizer.decode(outputs[0], skip_special_tokens=True)
# Extract only the generated portion (after prompt)
note_text = generated_note[len(prompt):].strip()
```

### Pre-computed Demo Data Structure
```python
# Schema for pre-computed ambient demo encounter
from pydantic import BaseModel, Field
from typing import Optional
from cliniq.pipeline import PipelineResult

class AmbientEncounterDemo(BaseModel):
    """Pre-computed ambient encounter for demo mode."""
    encounter_id: str
    encounter_label: str  # Display name for dropdown
    scenario_description: str  # Brief context shown in UI
    transcript: str  # Full conversation transcript
    generated_note: str  # Pre-generated SOAP note
    pipeline_result: dict  # Serialized PipelineResult JSON
    disambiguation_items: list[dict] = Field(default_factory=list)
    session_duration_seconds: int = 180  # Simulated duration
```

### Fragment-based Session Timer
```python
# Source: https://docs.streamlit.io/develop/tutorials/execution-flow/start-and-stop-fragment-auto-reruns
import streamlit as st
from datetime import datetime

@st.fragment(run_every=1.0 if st.session_state.get("ambient_state") == "recording" else None)
def session_timer_fragment():
    start = st.session_state.get("recording_start_time")
    if start and st.session_state.get("ambient_state") == "recording":
        elapsed = (datetime.now() - start).total_seconds()
        mins, secs = divmod(int(elapsed), 60)
        st.metric("Session Timer", f"{mins:02d}:{secs:02d}")
    elif st.session_state.get("ambient_state") == "idle":
        st.metric("Session Timer", "00:00")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| streamlit-mic-recorder (3rd party) | st.audio_input (native) | Streamlit 1.40.0, Nov 2024 | No 3rd-party dependency for audio recording |
| openai-whisper (original) | faster-whisper (CTranslate2) | 2023-present | 4x faster on CPU, int8 quantization, lower memory |
| st.experimental_audio_input | st.audio_input (GA) | Streamlit 1.40.0 | Stable API, no experimental prefix |
| while-loop timers | @st.fragment(run_every=N) | Streamlit 1.37.0, Aug 2024 | Non-blocking partial reruns |
| Custom audio components | Native widget | 2024 | Simplified dependency tree |

**Deprecated/outdated:**
- `st.experimental_audio_input`: Use `st.audio_input` instead (GA since 1.40.0)
- `openai-whisper` package: Still maintained but `faster-whisper` is strictly superior for local CPU inference

## Open Questions

1. **Maximum audio recording length in demo**
   - What we know: st.audio_input has no built-in max duration. Long recordings produce large WAV files (16kHz mono = ~1.9MB/min). Whisper `small` on CPU processes ~1 minute of audio in ~10-15 seconds.
   - What's unclear: At what duration does the UX degrade unacceptably?
   - Recommendation: Keep demo encounters at 1-3 minutes. Add a soft warning at 5 minutes. Pre-computed demos simulate 3-minute encounters.

2. **Number of pre-computed demo encounters**
   - What we know: Phase 4 uses 3 pre-computed pipeline results. Ambient mode needs conversations, not just notes.
   - What's unclear: How many varied scenarios are needed to impress in an interview?
   - Recommendation: 2 pre-computed encounters covering different specialties (e.g., primary care follow-up, urgent care visit). Each should demonstrate different CDI findings.

3. **Whisper model accuracy on medical terminology**
   - What we know: Whisper is general-purpose, not medical-domain-specific. The `small` model is 244M parameters.
   - What's unclear: How well does it handle clinical terms like medication names, ICD codes mentioned verbally?
   - Recommendation: For interview demo, pre-computed transcripts bypass this concern. For live demo, accept imperfect transcription -- the value story is the CDI layer, not perfect ASR.

4. **Qwen 1.5B quality for SOAP note generation**
   - What we know: 1.5B parameter model; previously used for CDI queries with template fallback.
   - What's unclear: Quality of structured note output from a small model.
   - Recommendation: Use aggressive few-shot prompting with 1-2 complete examples. For demo mode, use pre-computed notes. For live mode, accept imperfect output and let CDI analysis demonstrate gap detection on the imperfect note (this actually makes the demo MORE impressive).

## Sources

### Primary (HIGH confidence)
- [Streamlit st.audio_input official docs](https://docs.streamlit.io/develop/api-reference/widgets/st.audio_input) - API, parameters, return type, version 1.40.0 GA
- [Streamlit st.fragment official docs](https://docs.streamlit.io/develop/api-reference/execution-flow/st.fragment) - Fragment decorator, run_every parameter
- [Streamlit fragment auto-rerun tutorial](https://docs.streamlit.io/develop/tutorials/execution-flow/start-and-stop-fragment-auto-reruns) - Start/stop streaming pattern
- [SYSTRAN/faster-whisper GitHub](https://github.com/SYSTRAN/faster-whisper) - API, model sizes, CPU int8, installation
- [faster-whisper PyPI](https://pypi.org/project/faster-whisper/) - Version, dependencies, Python compatibility
- Existing codebase: `cliniq/pipeline.py` (run_pipeline_audited), `cliniq/model_manager.py` (ModelManager pattern), `ui/pages/pipeline_runner.py` (demo data loading pattern), `ui/components/pipeline_status.py` (st.status pattern)

### Secondary (MEDIUM confidence)
- [Streamlit 2025 release notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2025) - st.audio_input improvements
- [SOAP Notes StatPearls](https://www.ncbi.nlm.nih.gov/books/NBK482263/) - Clinical note structure reference
- [OpenAI Whisper GitHub](https://github.com/openai/whisper) - Model sizes, accuracy comparison

### Tertiary (LOW confidence)
- WebSearch findings on Whisper medical transcription accuracy -- no authoritative benchmark found for medical domain specifically with the `small` model
- WebSearch findings on Qwen SOAP note generation -- no published benchmarks for 1.5B model on clinical note tasks

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries are well-documented, actively maintained, and compatible with existing project. st.audio_input is native Streamlit. faster-whisper is the de facto local Whisper implementation.
- Architecture: HIGH - The dual-path (demo/live) pattern follows the established Phase 4 pattern exactly. Reusing `run_pipeline_audited` for CDI is the obvious correct approach.
- Pitfalls: HIGH - Identified from official docs (version requirements, audio format), project experience (session state, model download), and community reports (timer blocking, ctranslate2 compatibility).
- Whisper medical accuracy: LOW - No authoritative benchmarks found; mitigated by pre-computed demo path.
- Qwen SOAP quality: LOW - Not benchmarked for this task; mitigated by pre-computed demo path and template fallback.

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (30 days -- all libraries are stable)
