"""
Ambient Listening Mode page -- passive encounter recording with auto-generated
clinical notes, CDI gap detection, missed diagnosis flagging, and coding
disambiguation.

Supports dual-path architecture:
- Demo mode: Pre-computed encounters for instant, reliable results
- Live mode: Microphone recording -> Whisper transcription -> SOAP note generation -> CDI pipeline
"""

from __future__ import annotations

import json
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import streamlit as st

if TYPE_CHECKING:
    from cliniq.pipeline import PipelineResult

# ---------------------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------------------

_AMBIENT_DEFAULTS: dict = {
    "ambient_state": "idle",
    "ambient_session_id": None,
    "recording_start_time": None,
    "ambient_transcript": None,
    "ambient_note": None,
    "ambient_pipeline_result": None,
    "ambient_disambiguation": [],
    "ambient_is_demo": False,
    "ambient_audio_bytes": None,
}

for _key, _default in _AMBIENT_DEFAULTS.items():
    if _key not in st.session_state:
        st.session_state[_key] = _default


# ---------------------------------------------------------------------------
# Pre-computed demo loader (cached)
# ---------------------------------------------------------------------------


@st.cache_data
def _load_demo_encounter(encounter_id: str) -> dict | None:
    """Load a pre-computed ambient demo encounter by ID."""
    path = (
        Path(__file__).resolve().parent.parent
        / "demo_data"
        / "ambient"
        / f"{encounter_id}.json"
    )
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def _get_demo_options() -> dict[str, str | None]:
    """Return mapping of display labels to encounter IDs."""
    ambient_dir = (
        Path(__file__).resolve().parent.parent / "demo_data" / "ambient"
    )
    options: dict[str, str | None] = {"(none -- use live recording)": None}
    if ambient_dir.exists():
        for f in sorted(ambient_dir.glob("encounter_*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                options[data.get("encounter_label", f.stem)] = data.get(
                    "encounter_id", f.stem
                )
            except (json.JSONDecodeError, KeyError):
                continue
    return options


# ---------------------------------------------------------------------------
# Session timer fragment (AMB-01)
# ---------------------------------------------------------------------------


@st.fragment(run_every=1.0)
def _session_timer():
    """Display a live session timer that counts up during recording."""
    if st.session_state.get("ambient_state") != "recording":
        st.metric("Session Timer", "00:00")
        return
    start = st.session_state.get("recording_start_time")
    if start:
        elapsed = (datetime.now() - start).total_seconds()
        mins, secs = divmod(int(elapsed), 60)
        st.metric("Session Timer", f"{mins:02d}:{secs:02d}")
    else:
        st.metric("Session Timer", "00:00")


# ---------------------------------------------------------------------------
# Helper: reset session to idle
# ---------------------------------------------------------------------------


def _reset_session():
    """Reset all ambient session state to defaults."""
    for key, default in _AMBIENT_DEFAULTS.items():
        st.session_state[key] = (
            default if not isinstance(default, list) else []
        )


# ---------------------------------------------------------------------------
# Helper: category badge color
# ---------------------------------------------------------------------------

_CATEGORY_COLORS: dict[str, str] = {
    "gap": "#f39c12",
    "missed_diagnosis": "#3498db",
    "conflict": "#e74c3c",
    "ambiguity": "#e67e22",
}


def _category_badge(category: str) -> str:
    """Return an HTML badge span for a disambiguation category."""
    color = _CATEGORY_COLORS.get(category, "#95a5a6")
    label = category.replace("_", " ").title()
    return (
        f'<span style="background:{color};color:#fff;padding:2px 10px;'
        f'border-radius:12px;font-size:0.8rem;font-weight:600;">'
        f"{label}</span>"
    )


# ---------------------------------------------------------------------------
# Page layout
# ---------------------------------------------------------------------------

st.title("Ambient Listening Mode")
st.caption(
    "Passively record a physician-patient encounter, then automatically generate "
    "structured clinical notes with documentation gap detection, missed diagnosis "
    "flagging, and coding disambiguation."
)

# ---- MODE SELECTION -------------------------------------------------------

mode_radio = st.radio(
    "Mode",
    ["Demo Encounter", "Live Recording"],
    horizontal=True,
    key="ambient_mode_radio",
)

is_demo_mode = mode_radio == "Demo Encounter"

demo_encounter_id: str | None = None
audio_data = None

if is_demo_mode:
    demo_options = _get_demo_options()
    if len(demo_options) <= 1:
        st.warning(
            "No demo encounters found. Run `python scripts/precompute_ambient.py` "
            "to generate demo data, or switch to Live Recording mode."
        )
    demo_label = st.selectbox(
        "Select demo encounter",
        options=list(demo_options.keys()),
        key="ambient_demo_select",
    )
    demo_encounter_id = demo_options[demo_label]

# ---- SESSION CONTROLS (state machine) ------------------------------------

ambient_state = st.session_state["ambient_state"]

# --- IDLE STATE ---
if ambient_state == "idle":
    _session_timer()

    if is_demo_mode:
        start_disabled = demo_encounter_id is None
        if st.button(
            "Start Demo Session",
            type="primary",
            disabled=start_disabled,
            use_container_width=True,
        ):
            st.session_state["ambient_session_id"] = uuid.uuid4().hex[:8]
            st.session_state["ambient_is_demo"] = True
            st.session_state["ambient_state"] = "processing"
            st.session_state["_demo_encounter_id"] = demo_encounter_id
            st.rerun()
    else:
        st.markdown("##### Step 1: Record Encounter")
        st.caption(
            "Click the **microphone icon** below to start recording. "
            "Click it again to stop. The captured audio will appear as a playback bar."
        )
        live_audio = st.audio_input(
            "Record encounter audio",
            key="ambient_audio_recorder",
        )

        st.markdown("##### Step 2: Process Recording")
        has_audio = live_audio is not None
        if has_audio:
            st.success("Audio captured! Click below to process.")
        if st.button(
            "Process Recording",
            type="primary",
            disabled=not has_audio,
            use_container_width=True,
        ):
            st.session_state["ambient_session_id"] = uuid.uuid4().hex[:8]
            st.session_state["ambient_is_demo"] = False
            st.session_state["ambient_audio_bytes"] = live_audio.read()
            st.session_state["ambient_state"] = "processing"
            st.rerun()
        if not has_audio:
            st.caption("Record audio above first, then click Process.")

# --- PROCESSING STATE ---
elif ambient_state == "processing":
    with st.status("Processing encounter...", expanded=True) as status:
        try:
            if st.session_state.get("ambient_is_demo"):
                # DEMO PATH: load pre-computed results
                enc_id = st.session_state.get("_demo_encounter_id")
                st.write("Loading demo encounter data...")
                demo_data = _load_demo_encounter(enc_id) if enc_id else None

                if demo_data is None:
                    st.error(
                        f"Demo encounter '{enc_id}' not found. "
                        "Run `python scripts/precompute_ambient.py` to generate data."
                    )
                    st.session_state["ambient_state"] = "idle"
                    status.update(label="Failed to load demo", state="error")
                else:
                    st.write("Parsing transcript...")
                    time.sleep(0.5)
                    st.write("Generating clinical note...")
                    time.sleep(0.5)
                    st.write("Running CDI analysis...")
                    time.sleep(0.5)

                    st.session_state["ambient_transcript"] = demo_data.get(
                        "transcript", ""
                    )
                    st.session_state["ambient_note"] = demo_data.get(
                        "generated_note", ""
                    )
                    st.session_state["ambient_pipeline_result"] = demo_data.get(
                        "pipeline_result"
                    )

                    # Load disambiguation items with pending status
                    raw_items = demo_data.get("disambiguation_items", [])
                    items_with_status = []
                    for item in raw_items:
                        if "status" not in item:
                            item["status"] = "pending"
                        if "item_id" not in item:
                            item["item_id"] = uuid.uuid4().hex[:8]
                        items_with_status.append(item)
                    st.session_state["ambient_disambiguation"] = items_with_status

                    st.session_state["ambient_state"] = "results"
                    status.update(
                        label="Demo encounter loaded!",
                        state="complete",
                        expanded=False,
                    )
                    st.rerun()

            else:
                # LIVE PATH: transcribe -> note -> CDI pipeline
                audio_bytes = st.session_state.get("ambient_audio_bytes")
                if audio_bytes is None:
                    st.error("No audio data captured. Please record audio first.")
                    st.session_state["ambient_state"] = "idle"
                    status.update(label="No audio data", state="error")
                else:
                    st.write("Step 1: Transcribing audio...")

                    from ui.helpers.backend import get_ambient_module

                    ambient_mod = get_ambient_module()
                    run_ambient_pipeline = ambient_mod.run_ambient_pipeline
                    transcribe_audio = ambient_mod.transcribe_audio

                    # Save audio to temporary WAV file
                    with tempfile.NamedTemporaryFile(
                        suffix=".wav", delete=False
                    ) as tmp:
                        tmp.write(audio_bytes)
                        tmp_path = tmp.name

                    transcript = transcribe_audio(tmp_path)
                    st.session_state["ambient_transcript"] = transcript.raw_text

                    st.write("Step 2: Generating clinical note and running CDI pipeline...")

                    note, pipeline_result, disambiguation_items = (
                        run_ambient_pipeline(transcript.raw_text)
                    )

                    st.session_state["ambient_note"] = note.full_text
                    st.session_state["ambient_pipeline_result"] = json.loads(
                        pipeline_result.model_dump_json()
                    )
                    st.session_state["ambient_disambiguation"] = [
                        json.loads(item.model_dump_json())
                        for item in disambiguation_items
                    ]

                    st.write("Step 3: Processing complete!")
                    st.session_state["ambient_state"] = "results"
                    status.update(
                        label="Encounter processed!",
                        state="complete",
                        expanded=False,
                    )
                    st.rerun()

        except Exception as exc:
            st.error(f"Processing failed: {exc}")
            st.session_state["ambient_state"] = "idle"
            status.update(label="Processing failed", state="error")

# --- RESULTS STATE ---
elif ambient_state == "results":
    # New Session button
    if st.button("New Session", type="primary", use_container_width=True):
        _reset_session()
        st.rerun()

    session_id = st.session_state.get("ambient_session_id", "N/A")
    is_demo = st.session_state.get("ambient_is_demo", False)
    mode_badge = ":blue[DEMO]" if is_demo else ":green[LIVE]"

    st.markdown(f"**Session:** `{session_id}` {mode_badge}")

    # ---- RESULT TABS -------------------------------------------------------
    tab_transcript, tab_note, tab_findings, tab_disambiguation = st.tabs(
        ["Transcript", "Generated Note", "Clinical Findings", "Disambiguation & Review"]
    )

    # -- Tab 1: Transcript --------------------------------------------------
    with tab_transcript:
        transcript_text = st.session_state.get("ambient_transcript", "")
        word_count = len(transcript_text.split()) if transcript_text else 0

        from ui.components.metric_cards import render_metric_row

        render_metric_row(
            {
                "Session ID": (session_id, None),
                "Mode": ("Demo" if is_demo else "Live", None),
                "Word Count": (str(word_count), None),
            }
        )

        st.markdown("#### Full Transcript")
        st.text_area(
            "Transcript",
            value=transcript_text or "(No transcript available)",
            height=300,
            disabled=True,
            label_visibility="collapsed",
        )

    # -- Tab 2: Generated Note (AMB-02) ------------------------------------
    with tab_note:
        note_text = st.session_state.get("ambient_note", "")
        if note_text:
            st.markdown("#### Generated Clinical Note")
            st.markdown(note_text)
        else:
            st.info("No clinical note generated for this session.")

    # -- Tab 3: Clinical Findings -------------------------------------------
    with tab_findings:
        pipeline_dict = st.session_state.get("ambient_pipeline_result")

        if pipeline_dict is None:
            st.info("No pipeline results available for this session.")
        else:
            from ui.helpers.backend import get_pipeline_module

            pipeline_mod = get_pipeline_module()
            PipelineResult = pipeline_mod.PipelineResult
            from ui.components.code_display import (
                render_code_cards,
                render_principal_diagnosis,
            )
            from ui.components.metric_cards import (
                render_metric_row as render_metrics,
            )

            try:
                result: PipelineResult = PipelineResult.model_validate(
                    pipeline_dict
                )
            except Exception as e:
                st.error(f"Failed to parse pipeline results: {e}")
                result = None

            if result is not None:
                # Metrics row
                entity_count = (
                    result.nlu_result.entity_count
                    if result.nlu_result
                    else 0
                )
                code_count = 0
                if result.coding_result:
                    if result.coding_result.principal_diagnosis:
                        code_count += 1
                    code_count += len(result.coding_result.secondary_codes)
                    code_count += len(result.coding_result.complication_codes)

                completeness = "N/A"
                completeness_delta = None
                if result.cdi_report is not None:
                    score = result.cdi_report.completeness_score
                    completeness = f"{score:.0%}"
                    gap_penalty = result.cdi_report.gap_count * 0.10
                    conflict_penalty = (
                        result.cdi_report.conflict_count * 0.15
                    )
                    total_penalty = gap_penalty + conflict_penalty
                    if total_penalty > 0:
                        completeness_delta = f"-{total_penalty:.0%} penalty"

                render_metrics(
                    {
                        "Processing Time": (
                            f"{result.processing_time_ms:.0f}ms",
                            None,
                        ),
                        "Entity Count": (str(entity_count), None),
                        "Code Count": (str(code_count), None),
                        "Completeness": (completeness, completeness_delta),
                    }
                )

                # NER entity summary
                if result.nlu_result and result.nlu_result.entities:
                    st.markdown("---")
                    st.markdown(
                        f"#### NER Entities ({result.nlu_result.entity_count})"
                    )
                    entity_rows = []
                    for ent in result.nlu_result.entities:
                        entity_rows.append(
                            {
                                "Entity Text": ent.text,
                                "Type": ent.entity_type,
                                "Negated": "Yes" if ent.negated else "No",
                                "Confidence": f"{ent.confidence:.2f}",
                            }
                        )
                    st.dataframe(entity_rows, use_container_width=True)

                # ICD-10 codes
                if result.coding_result:
                    st.markdown("---")
                    st.markdown("#### ICD-10 Codes")
                    render_principal_diagnosis(
                        result.coding_result.principal_diagnosis
                    )
                    if result.coding_result.secondary_codes:
                        render_code_cards(
                            result.coding_result.secondary_codes,
                            "Secondary Codes",
                        )
                    if result.coding_result.complication_codes:
                        render_code_cards(
                            result.coding_result.complication_codes,
                            "Complications",
                        )

                # CDI findings
                if result.cdi_report is not None:
                    cdi = result.cdi_report
                    st.markdown("---")
                    st.markdown(
                        f"#### Documentation Gaps ({cdi.gap_count})"
                    )
                    if cdi.documentation_gaps:
                        for i, gap in enumerate(cdi.documentation_gaps, 1):
                            with st.expander(
                                f"Gap {i}: {gap.code} -- {gap.description}"
                            ):
                                st.markdown(
                                    f"**Missing Qualifier:** {gap.missing_qualifier}"
                                )
                                st.markdown(
                                    f"**Physician Query:** {gap.physician_query}"
                                )
                                st.caption(
                                    f"Confidence: {gap.confidence:.2f}"
                                )
                    else:
                        st.success("No documentation gaps identified.")

                    st.markdown(
                        f"#### Missed Diagnoses ({len(cdi.missed_diagnoses)})"
                    )
                    if cdi.missed_diagnoses:
                        for i, missed in enumerate(
                            cdi.missed_diagnoses, 1
                        ):
                            with st.expander(
                                f"Missed {i}: {missed.suggested_code} -- {missed.description}"
                            ):
                                st.markdown(
                                    f"**Co-coded with:** {missed.co_coded_with}"
                                )
                                st.markdown(
                                    f"**Weight:** {missed.co_occurrence_weight:.2f}"
                                )
                    else:
                        st.success("No missed diagnoses identified.")

                    st.markdown(
                        f"#### Code Conflicts ({cdi.conflict_count})"
                    )
                    if cdi.code_conflicts:
                        for i, conflict in enumerate(
                            cdi.code_conflicts, 1
                        ):
                            st.warning(
                                f"**Conflict {i}:** {conflict.code_a} vs "
                                f"{conflict.code_b}\n\n"
                                f"**Reason:** {conflict.conflict_reason}\n\n"
                                f"**Recommendation:** {conflict.recommendation}"
                            )
                    else:
                        st.success("No code conflicts detected.")

    # -- Tab 4: Disambiguation & Review (AMB-05, AMB-06) --------------------
    with tab_disambiguation:
        st.markdown(
            "#### Review and resolve coding disambiguation items before "
            "finalizing the note"
        )

        items = st.session_state.get("ambient_disambiguation", [])

        if not items:
            st.info(
                "No disambiguation items found for this session. "
                "The clinical documentation appears complete."
            )
        else:
            reviewed = sum(
                1 for it in items if it.get("status") in ("accepted", "dismissed")
            )
            total = len(items)
            st.progress(
                reviewed / total if total > 0 else 0,
                text=f"{reviewed} of {total} items reviewed",
            )

            for idx, item in enumerate(items):
                with st.container(border=True):
                    # Category badge
                    category = item.get("category", "unknown")
                    st.markdown(
                        _category_badge(category),
                        unsafe_allow_html=True,
                    )

                    # Title and description
                    st.markdown(f"**{item.get('title', 'Untitled')}**")
                    st.markdown(item.get("description", ""))

                    # Suggested action
                    if item.get("suggested_action"):
                        st.info(
                            f"**Suggested action:** {item['suggested_action']}"
                        )

                    # Source code and confidence
                    meta_cols = st.columns(2)
                    with meta_cols[0]:
                        if item.get("source_code"):
                            st.caption(
                                f"Source code: `{item['source_code']}`"
                            )
                    with meta_cols[1]:
                        confidence = item.get("confidence", 0.0)
                        st.caption(f"Confidence: {confidence:.2f}")

                    # Action buttons or status badge
                    item_status = item.get("status", "pending")

                    if item_status == "pending":
                        btn_cols = st.columns(2)
                        with btn_cols[0]:
                            if st.button(
                                "Accept",
                                key=f"accept_{idx}",
                                type="primary",
                                use_container_width=True,
                            ):
                                st.session_state["ambient_disambiguation"][
                                    idx
                                ]["status"] = "accepted"
                                st.toast(
                                    f"Accepted: {item.get('title', '')}",
                                    icon=":material/check_circle:",
                                )
                                st.rerun()
                        with btn_cols[1]:
                            if st.button(
                                "Dismiss",
                                key=f"dismiss_{idx}",
                                type="secondary",
                                use_container_width=True,
                            ):
                                st.session_state["ambient_disambiguation"][
                                    idx
                                ]["status"] = "dismissed"
                                st.toast(
                                    f"Dismissed: {item.get('title', '')}",
                                    icon=":material/info:",
                                )
                                st.rerun()
                    elif item_status == "accepted":
                        st.markdown(
                            ":green[Accepted]  :material/check_circle:"
                        )
                    elif item_status == "dismissed":
                        st.markdown(
                            ":gray[Dismissed]  :material/close:"
                        )

            # Summary at bottom
            st.markdown("---")
            reviewed_final = sum(
                1
                for it in st.session_state.get("ambient_disambiguation", [])
                if it.get("status") in ("accepted", "dismissed")
            )
            st.markdown(
                f"**{reviewed_final} of {total} items reviewed**"
            )

    # ---- SIDEBAR INTEGRATION -----------------------------------------------
    with st.sidebar:
        st.markdown(f"**Ambient Session:** `{session_id}`")
        st.markdown(f"Type: {mode_badge}")
