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
# Helper: build disambiguation items from PipelineResult
# ---------------------------------------------------------------------------


def _build_disambiguation_items(pipeline_result) -> list:
    """Extract disambiguation items from a PipelineResult's CDI report."""
    from cliniq.models.ambient import DisambiguationItem

    items: list[DisambiguationItem] = []
    if pipeline_result.cdi_report is None:
        return items

    for gap in pipeline_result.cdi_report.documentation_gaps:
        desc = gap.physician_query
        if gap.evidence_text:
            desc += f"\n\n**Evidence:** _{gap.evidence_text}_"
        items.append(
            DisambiguationItem(
                item_id=uuid.uuid4().hex[:8],
                category="gap",
                title=f"Documentation Gap: {gap.code}",
                description=desc,
                suggested_action=f"Clarify {gap.missing_qualifier} for {gap.code}",
                source_code=gap.code,
                confidence=gap.confidence,
            )
        )
    for md in pipeline_result.cdi_report.missed_diagnoses:
        desc = md.description
        if md.evidence_text:
            desc += f"\n\n**Evidence:** _{md.evidence_text}_"
        if md.co_coded_with:
            desc += f"\n\n**Co-coded with:** `{md.co_coded_with}`"
        items.append(
            DisambiguationItem(
                item_id=uuid.uuid4().hex[:8],
                category="missed_diagnosis",
                title=f"Potential Missed Dx: {md.suggested_code}",
                description=desc,
                suggested_action=f"Consider documenting {md.suggested_code} ({md.description})",
                source_code=md.suggested_code,
                confidence=md.co_occurrence_weight,
            )
        )
    for cc in pipeline_result.cdi_report.code_conflicts:
        items.append(
            DisambiguationItem(
                item_id=uuid.uuid4().hex[:8],
                category="conflict",
                title=f"Code Conflict: {cc.code_a} vs {cc.code_b}",
                description=cc.conflict_reason,
                suggested_action=cc.recommendation,
                source_code=f"{cc.code_a},{cc.code_b}",
            )
        )
    return items


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
                    # Step 1: Transcript
                    st.write("**Step 1/4** — Loading transcript...")
                    time.sleep(0.3)
                    transcript_text = demo_data.get("transcript", "")
                    st.session_state["ambient_transcript"] = transcript_text
                    word_count = len(transcript_text.split()) if transcript_text else 0
                    st.success(f"Transcript loaded — {word_count} words")
                    with st.expander("Preview transcript", expanded=False):
                        preview = transcript_text[:500]
                        if len(transcript_text) > 500:
                            preview += "..."
                        st.text(preview)

                    # Step 2: Clinical note
                    st.write("**Step 2/4** — Parsing clinical note...")
                    time.sleep(0.3)
                    note_text = demo_data.get("generated_note", "")
                    st.session_state["ambient_note"] = note_text
                    st.success("Clinical note loaded")
                    with st.expander("Preview note", expanded=False):
                        st.markdown(note_text[:400] + ("..." if len(note_text) > 400 else ""))

                    # Step 3: Pipeline results
                    st.write("**Step 3/4** — Loading pipeline results...")
                    time.sleep(0.3)
                    pipeline_dict = demo_data.get("pipeline_result")
                    st.session_state["ambient_pipeline_result"] = pipeline_dict
                    if pipeline_dict:
                        nlu = pipeline_dict.get("nlu_result") or {}
                        entity_count = nlu.get("entity_count", 0)
                        coding = pipeline_dict.get("coding_result") or {}
                        code_count = (1 if coding.get("principal_diagnosis") else 0) + len(coding.get("secondary_codes", [])) + len(coding.get("complication_codes", []))
                        cdi = pipeline_dict.get("cdi_report") or {}
                        gap_count = cdi.get("gap_count", 0)
                        st.success(f"Pipeline loaded — {entity_count} entities, {code_count} codes, {gap_count} gaps")
                    else:
                        st.success("Pipeline results loaded")

                    # Step 4: Disambiguation
                    st.write("**Step 4/4** — Preparing disambiguation items...")

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

                    item_count = len(items_with_status)
                    if item_count > 0:
                        cats: dict[str, int] = {}
                        for it in items_with_status:
                            c = it.get("category", "unknown")
                            cats[c] = cats.get(c, 0) + 1
                        cat_summary = ", ".join(
                            f"{cnt} {cat.replace('_', ' ')}" for cat, cnt in cats.items()
                        )
                        st.success(f"Found {item_count} items for review: {cat_summary}")
                    else:
                        st.success("No disambiguation items — documentation looks complete!")

                    st.session_state["ambient_state"] = "results"
                    status.update(
                        label="Demo encounter loaded!",
                        state="complete",
                        expanded=False,
                    )
                    st.rerun()

            else:
                # LIVE PATH: transcribe -> note -> NER/RAG -> CDI -> disambiguation
                audio_bytes = st.session_state.get("ambient_audio_bytes")
                if audio_bytes is None:
                    st.error("No audio data captured. Please record audio first.")
                    st.session_state["ambient_state"] = "idle"
                    status.update(label="No audio data", state="error")
                else:
                    from ui.helpers.backend import get_ambient_module, get_pipeline_module

                    ambient_mod = get_ambient_module()
                    pipeline_mod = get_pipeline_module()

                    # ----------------------------------------------------------
                    # Step 1: Transcribe audio
                    # ----------------------------------------------------------
                    st.write("**Step 1/4** — Transcribing audio...")

                    t0 = time.time()
                    with tempfile.NamedTemporaryFile(
                        suffix=".wav", delete=False
                    ) as tmp:
                        tmp.write(audio_bytes)
                        tmp_path = tmp.name

                    transcript = ambient_mod.transcribe_audio(tmp_path)
                    st.session_state["ambient_transcript"] = transcript.raw_text
                    t1 = time.time()

                    word_count = len(transcript.raw_text.split())
                    st.success(f"Transcription complete — {word_count} words captured ({t1 - t0:.1f}s)")
                    with st.expander("Preview transcript", expanded=False):
                        preview = transcript.raw_text[:500]
                        if len(transcript.raw_text) > 500:
                            preview += "..."
                        st.text(preview)

                    # ----------------------------------------------------------
                    # Step 2: Generate SOAP note
                    # ----------------------------------------------------------
                    st.write("**Step 2/4** — Generating structured clinical note...")

                    t2 = time.time()
                    note = ambient_mod.generate_soap_note(transcript.raw_text)
                    st.session_state["ambient_note"] = note.full_text
                    t3 = time.time()

                    st.success(f"Clinical note generated ({t3 - t2:.1f}s)")
                    with st.expander("Preview note sections", expanded=False):
                        sections_found = []
                        if note.chief_complaint:
                            sections_found.append(f"**CC:** {note.chief_complaint[:120]}...")
                        if note.hpi:
                            sections_found.append(f"**HPI:** {note.hpi[:120]}...")
                        if note.assessment:
                            sections_found.append(f"**Assessment:** {note.assessment[:120]}...")
                        if note.plan:
                            sections_found.append(f"**Plan:** {note.plan[:120]}...")
                        if sections_found:
                            st.markdown("\n\n".join(sections_found))
                        else:
                            st.text(note.full_text[:300])

                    # ----------------------------------------------------------
                    # Step 3: Run NER + RAG coding + CDI pipeline
                    # ----------------------------------------------------------
                    st.write("**Step 3/4** — Running clinical NER, ICD-10 coding & CDI analysis...")

                    t4 = time.time()
                    pipeline_result = pipeline_mod.run_pipeline_audited(
                        note.full_text, use_llm_queries=False
                    )
                    t5 = time.time()

                    entity_count = (
                        pipeline_result.nlu_result.entity_count
                        if pipeline_result.nlu_result
                        else 0
                    )
                    code_count = 0
                    if pipeline_result.coding_result:
                        if pipeline_result.coding_result.principal_diagnosis:
                            code_count += 1
                        code_count += len(pipeline_result.coding_result.secondary_codes)
                        code_count += len(pipeline_result.coding_result.complication_codes)
                    gap_count = (
                        pipeline_result.cdi_report.gap_count
                        if pipeline_result.cdi_report
                        else 0
                    )

                    st.success(
                        f"Pipeline complete — {entity_count} entities, "
                        f"{code_count} ICD-10 codes, {gap_count} documentation gaps ({t5 - t4:.1f}s)"
                    )
                    with st.expander("Preview findings", expanded=False):
                        if pipeline_result.nlu_result and pipeline_result.nlu_result.entities:
                            top_ents = pipeline_result.nlu_result.entities[:5]
                            ent_text = ", ".join(
                                f"`{e.text}` ({e.entity_type})" for e in top_ents
                            )
                            st.markdown(f"**Top entities:** {ent_text}")
                        if pipeline_result.coding_result and pipeline_result.coding_result.principal_diagnosis:
                            pd = pipeline_result.coding_result.principal_diagnosis
                            st.markdown(
                                f"**Principal Dx:** `{pd.icd10_code}` — {pd.description}"
                            )

                    st.session_state["ambient_pipeline_result"] = json.loads(
                        pipeline_result.model_dump_json()
                    )

                    # ----------------------------------------------------------
                    # Step 4: Build disambiguation items
                    # ----------------------------------------------------------
                    st.write("**Step 4/4** — Building disambiguation & review items...")

                    t6 = time.time()
                    disambiguation_items = _build_disambiguation_items(pipeline_result)

                    st.session_state["ambient_disambiguation"] = [
                        json.loads(item.model_dump_json())
                        for item in disambiguation_items
                    ]

                    item_count = len(disambiguation_items)
                    if item_count > 0:
                        cats = {}
                        for it in disambiguation_items:
                            cats[it.category] = cats.get(it.category, 0) + 1
                        cat_summary = ", ".join(
                            f"{cnt} {cat.replace('_', ' ')}" for cat, cnt in cats.items()
                        )
                        st.success(f"Found {item_count} items for review: {cat_summary}")
                    else:
                        st.success("No disambiguation items — documentation looks complete!")
                    t7 = time.time()

                    total_time = t7 - t0
                    st.session_state["ambient_state"] = "results"
                    status.update(
                        label=f"Encounter processed! (Total: {total_time:.1f}s)",
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
