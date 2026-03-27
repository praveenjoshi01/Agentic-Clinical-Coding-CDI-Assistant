"""
QA Bot page — interactive clinical Q&A for the ClinIQ system.

Three-tier answer strategy:
  1. **Pre-seeded** (default): keyword/Jaccard matching against demo_questions.json
     for instant, verified responses about the system.
  2. **Patient context**: template-based answers generated from the active
     PipelineResult in session state for patient/case-specific questions.
  3. **LLM fallback** (opt-in): uses Qwen via RAG for novel questions.  Not
     imported at page load to avoid model downloads on startup.
"""

from __future__ import annotations

import json
import pathlib
from typing import TYPE_CHECKING

import streamlit as st

if TYPE_CHECKING:
    from cliniq.pipeline import PipelineResult

# ---------------------------------------------------------------------------
# Constants / paths
# ---------------------------------------------------------------------------

_DEMO_QUESTIONS_PATH = pathlib.Path(__file__).resolve().parent.parent / "demo_data" / "demo_questions.json"

_WELCOME_MESSAGE = (
    "Welcome! I'm the ClinIQ QA Bot. I can answer questions about:\n\n"
    "- **System architecture** — pipeline, models, evaluation metrics\n"
    "- **Active patient case** — diagnoses, ICD-10 codes, CDI gaps, audit trail\n\n"
    "Run the pipeline on a demo case first, then ask me anything about the patient!"
)

_WELCOME_MESSAGE_NO_CASE = (
    "Welcome! I'm the ClinIQ QA Bot. Ask me about the pipeline architecture, "
    "models, or evaluation metrics.\n\n"
    "> **Tip:** Run the pipeline on a demo case first to unlock patient-specific Q&A."
)

# Patient-related quick questions shown when a pipeline result is loaded
_PATIENT_QUESTIONS = [
    "What are the patient's diagnoses?",
    "What ICD-10 codes were assigned?",
    "What is the principal diagnosis?",
    "What medications is the patient on?",
    "Are there any documentation gaps?",
    "Are there any missed diagnoses?",
    "What is the completeness score?",
    "Summarize the patient case",
]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

@st.cache_data
def _load_questions() -> list[dict[str, str]]:
    """Load pre-seeded Q&A pairs from demo_questions.json."""
    with open(_DEMO_QUESTIONS_PATH, encoding="utf-8") as fh:
        data: list[dict[str, str]] = json.load(fh)
    return data


# ---------------------------------------------------------------------------
# Matching logic
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> set[str]:
    """Lowercase split into word tokens, stripping punctuation and possessives."""
    tokens = set()
    for w in text.lower().split():
        w = w.strip(".,;:!?\"'()[]{}").replace("\u2019", "'")
        # Strip possessive 's
        if w.endswith("'s"):
            w = w[:-2]
        if len(w) > 1:
            tokens.add(w)
    return tokens


def _jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard similarity between two token sets."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _find_best_match(
    user_question: str,
    bank: list[dict[str, str]],
    threshold: float = 0.3,
) -> str | None:
    """Return the best pre-seeded answer or *None* if below threshold."""
    user_tokens = _tokenize(user_question)
    best_score = 0.0
    best_answer: str | None = None
    for item in bank:
        score = _jaccard(user_tokens, _tokenize(item["question"]))
        if score > best_score:
            best_score = score
            best_answer = item["answer"]
    if best_score >= threshold and best_answer is not None:
        return best_answer
    return None


# ---------------------------------------------------------------------------
# Patient-context answer generation
# ---------------------------------------------------------------------------

# Keyword stems that signal a patient/case-specific question.
# Uses prefix matching: token "diagnoses" starts with stem "diagnos".
_PATIENT_STEMS = [
    "patient", "diagnos", "icd", "code", "medication", "drug", "gap",
    "completeness", "conflict", "missed", "entit", "ner", "finding",
    "case", "principal", "secondary", "complication", "audit", "trail",
    "evidence", "score", "cdi", "query", "physician", "summar",
    "overview", "result", "narrative", "clinical", "negat", "qualifier",
]


def _is_patient_question(question: str) -> bool:
    """Check if the question is about the active patient/case (prefix matching)."""
    tokens = _tokenize(question)
    for token in tokens:
        for stem in _PATIENT_STEMS:
            if token.startswith(stem) or stem.startswith(token):
                return True
    return False


def _get_pipeline_result() -> PipelineResult | None:
    """Retrieve the active PipelineResult from session state."""
    return st.session_state.get("pipeline_result")


def _answer_from_pipeline(question: str, result: PipelineResult) -> str:
    """Generate a template-based answer from the PipelineResult."""
    q_lower = question.lower()

    # --- Summarize / overview ---
    if any(w in q_lower for w in ["summary", "summarize", "overview", "tell me about"]):
        return _build_summary(result)

    # --- Diagnoses / entities ---
    if any(w in q_lower for w in ["diagnos", "condition", "disease", "finding"]):
        return _build_diagnoses_answer(result)

    # --- Principal diagnosis ---
    if "principal" in q_lower:
        return _build_principal_answer(result)

    # --- ICD-10 codes ---
    if any(w in q_lower for w in ["icd", "code", "coding"]):
        return _build_codes_answer(result)

    # --- Medications ---
    if any(w in q_lower for w in ["medication", "drug", "medicine", "prescription", "rx"]):
        return _build_medications_answer(result)

    # --- Documentation gaps ---
    if "gap" in q_lower:
        return _build_gaps_answer(result)

    # --- Missed diagnoses ---
    if "missed" in q_lower:
        return _build_missed_answer(result)

    # --- Code conflicts ---
    if "conflict" in q_lower:
        return _build_conflicts_answer(result)

    # --- Completeness score ---
    if "completeness" in q_lower or "score" in q_lower:
        return _build_completeness_answer(result)

    # --- Audit trail ---
    if any(w in q_lower for w in ["audit", "trail", "trace", "timing", "stage"]):
        return _build_audit_answer(result)

    # --- Negation ---
    if "negat" in q_lower:
        return _build_negation_answer(result)

    # --- Entities (generic) ---
    if any(w in q_lower for w in ["entity", "entities", "ner", "extract"]):
        return _build_entities_answer(result)

    # --- Evidence ---
    if "evidence" in q_lower:
        return _build_evidence_answer(result)

    # --- Narrative ---
    if "narrative" in q_lower or "clinical note" in q_lower or "document" in q_lower:
        narrative = result.document.raw_narrative
        if len(narrative) > 500:
            narrative = narrative[:500] + "..."
        return f"**Clinical Narrative:**\n\n{narrative}"

    # --- Catch-all: generic patient summary ---
    return _build_summary(result)


def _build_summary(result: PipelineResult) -> str:
    """Build a full case summary."""
    doc = result.document
    nlu = result.nlu_result
    coding = result.coding_result
    cdi = result.cdi_report

    parts = [f"**Case Summary** (Source: {doc.metadata.source_type.upper()})"]
    parts.append(f"- **Patient ID:** {doc.metadata.patient_id}")
    parts.append(f"- **Processing Time:** {result.processing_time_ms:.0f}ms")
    parts.append(f"- **Entities Extracted:** {nlu.entity_count}")

    # Diagnoses
    dx_list = [e for e in nlu.entities if e.entity_type == "diagnosis" and not e.negated]
    if dx_list:
        dx_names = ", ".join(e.text for e in dx_list)
        parts.append(f"- **Active Diagnoses:** {dx_names}")

    # Codes
    if coding.principal_diagnosis:
        parts.append(f"- **Principal Dx:** {coding.principal_diagnosis.icd10_code} — {coding.principal_diagnosis.description}")
    if coding.secondary_codes:
        sec = ", ".join(f"{c.icd10_code}" for c in coding.secondary_codes)
        parts.append(f"- **Secondary Codes:** {sec}")

    # CDI
    if cdi:
        parts.append(f"- **Completeness Score:** {cdi.completeness_score:.0%}")
        parts.append(f"- **Documentation Gaps:** {cdi.gap_count}")
        parts.append(f"- **Missed Diagnoses:** {len(cdi.missed_diagnoses)}")
        parts.append(f"- **Code Conflicts:** {cdi.conflict_count}")

    if result.errors:
        parts.append(f"- **Errors:** {len(result.errors)}")

    return "\n".join(parts)


def _build_diagnoses_answer(result: PipelineResult) -> str:
    nlu = result.nlu_result
    dx_entities = [e for e in nlu.entities if e.entity_type == "diagnosis"]
    if not dx_entities:
        return "No diagnoses were extracted from this case."

    parts = [f"**Diagnoses Extracted** ({len(dx_entities)} total):\n"]
    for e in dx_entities:
        neg = " (NEGATED)" if e.negated else ""
        qual = f" [{', '.join(e.qualifiers)}]" if e.qualifiers else ""
        conf = f" — confidence: {e.confidence:.0%}"
        parts.append(f"- **{e.text}**{neg}{qual}{conf}")
    return "\n".join(parts)


def _build_principal_answer(result: PipelineResult) -> str:
    pd = result.coding_result.principal_diagnosis
    if not pd:
        return "No principal diagnosis was assigned for this case."
    return (
        f"**Principal Diagnosis:** {pd.icd10_code} — {pd.description}\n\n"
        f"- **Confidence:** {pd.confidence:.0%}\n"
        f"- **Evidence:** {pd.evidence_text}\n"
        f"- **Reasoning:** {pd.reasoning}"
    )


def _build_codes_answer(result: PipelineResult) -> str:
    coding = result.coding_result
    parts = ["**ICD-10 Codes Assigned:**\n"]

    if coding.principal_diagnosis:
        pd = coding.principal_diagnosis
        parts.append(f"**Principal:** {pd.icd10_code} — {pd.description} (confidence: {pd.confidence:.0%})")

    if coding.secondary_codes:
        parts.append("\n**Secondary Codes:**")
        for c in coding.secondary_codes:
            parts.append(f"- {c.icd10_code} — {c.description} (confidence: {c.confidence:.0%})")

    if coding.complication_codes:
        parts.append("\n**Complication Codes:**")
        for c in coding.complication_codes:
            parts.append(f"- {c.icd10_code} — {c.description} (confidence: {c.confidence:.0%})")

    if coding.sequencing_rationale:
        parts.append(f"\n**Sequencing Rationale:** {coding.sequencing_rationale}")

    if not coding.principal_diagnosis and not coding.secondary_codes:
        return "No ICD-10 codes were assigned for this case."

    return "\n".join(parts)


def _build_medications_answer(result: PipelineResult) -> str:
    nlu = result.nlu_result
    meds = [e for e in nlu.entities if e.entity_type == "medication"]
    if not meds:
        return "No medications were extracted from this case."

    parts = [f"**Medications Identified** ({len(meds)}):\n"]
    for m in meds:
        qual = f" — {', '.join(m.qualifiers)}" if m.qualifiers else ""
        parts.append(f"- **{m.text}**{qual} (confidence: {m.confidence:.0%})")
    return "\n".join(parts)


def _build_gaps_answer(result: PipelineResult) -> str:
    cdi = result.cdi_report
    if not cdi:
        return "CDI analysis was not run for this case."
    if not cdi.documentation_gaps:
        return "No documentation gaps were identified for this case."

    parts = [f"**Documentation Gaps** ({cdi.gap_count}):\n"]
    for i, gap in enumerate(cdi.documentation_gaps, 1):
        parts.append(
            f"**{i}. {gap.code} — {gap.description}**\n"
            f"   - Missing: {gap.missing_qualifier}\n"
            f"   - Physician Query: *{gap.physician_query}*\n"
            f"   - Evidence: {gap.evidence_text}\n"
            f"   - Confidence: {gap.confidence:.0%}"
        )
    return "\n\n".join(parts)


def _build_missed_answer(result: PipelineResult) -> str:
    cdi = result.cdi_report
    if not cdi:
        return "CDI analysis was not run for this case."
    if not cdi.missed_diagnoses:
        return "No missed diagnoses were identified for this case."

    parts = [f"**Potential Missed Diagnoses** ({len(cdi.missed_diagnoses)}):\n"]
    for i, m in enumerate(cdi.missed_diagnoses, 1):
        parts.append(
            f"**{i}. {m.suggested_code} — {m.description}**\n"
            f"   - Co-coded with: {m.co_coded_with}\n"
            f"   - Co-occurrence weight: {m.co_occurrence_weight:.0%}\n"
            f"   - Evidence: {m.evidence_text}"
        )
    return "\n\n".join(parts)


def _build_conflicts_answer(result: PipelineResult) -> str:
    cdi = result.cdi_report
    if not cdi:
        return "CDI analysis was not run for this case."
    if not cdi.code_conflicts:
        return "No code conflicts were detected for this case."

    parts = [f"**Code Conflicts** ({cdi.conflict_count}):\n"]
    for i, c in enumerate(cdi.code_conflicts, 1):
        parts.append(
            f"**{i}. {c.code_a} vs {c.code_b}**\n"
            f"   - Reason: {c.conflict_reason}\n"
            f"   - Recommendation: {c.recommendation}"
        )
    return "\n\n".join(parts)


def _build_completeness_answer(result: PipelineResult) -> str:
    cdi = result.cdi_report
    if not cdi:
        return "CDI analysis was not run for this case, so no completeness score is available."

    gap_penalty = cdi.gap_count * 0.10
    conflict_penalty = cdi.conflict_count * 0.15
    total_penalty = gap_penalty + conflict_penalty

    parts = [
        f"**Documentation Completeness Score:** {cdi.completeness_score:.0%}\n",
        f"- Documentation gaps: {cdi.gap_count} (-{gap_penalty:.0%} penalty)",
        f"- Code conflicts: {cdi.conflict_count} (-{conflict_penalty:.0%} penalty)",
        f"- Missed diagnoses: {len(cdi.missed_diagnoses)}",
    ]
    if total_penalty > 0:
        parts.append(f"\nTotal penalty applied: **-{total_penalty:.0%}**")
    return "\n".join(parts)


def _build_audit_answer(result: PipelineResult) -> str:
    audit = result.audit_trail
    if not audit:
        return "No audit trail is available for this case."

    parts = [f"**Audit Trail** (Case: {audit.case_id}):\n"]
    for s in audit.stages:
        parts.append(f"- **{s.stage.upper()}:** {s.processing_time_ms:.1f}ms — {s.output_summary}")
    total = sum(s.processing_time_ms for s in audit.stages)
    parts.append(f"\n**Total stage time:** {total:.1f}ms")

    if audit.evidence_spans:
        parts.append(f"\n**Evidence spans** linked for {len(audit.evidence_spans)} codes.")

    return "\n".join(parts)


def _build_negation_answer(result: PipelineResult) -> str:
    nlu = result.nlu_result
    negated = [e for e in nlu.entities if e.negated]
    if not negated:
        return "No negated entities were found in this case."

    parts = [f"**Negated Entities** ({len(negated)}):\n"]
    for e in negated:
        parts.append(f"- **{e.text}** ({e.entity_type}) — confidence: {e.confidence:.0%}")
    return "\n".join(parts)


def _build_entities_answer(result: PipelineResult) -> str:
    nlu = result.nlu_result
    if not nlu.entities:
        return "No entities were extracted from this case."

    # Group by type
    by_type: dict[str, list] = {}
    for e in nlu.entities:
        by_type.setdefault(e.entity_type, []).append(e)

    parts = [f"**Extracted Entities** ({nlu.entity_count} total):\n"]
    for etype, entities in by_type.items():
        parts.append(f"\n**{etype.replace('_', ' ').title()}** ({len(entities)}):")
        for e in entities:
            neg = " (NEGATED)" if e.negated else ""
            parts.append(f"- {e.text}{neg} — confidence: {e.confidence:.0%}")
    return "\n".join(parts)


def _build_evidence_answer(result: PipelineResult) -> str:
    audit = result.audit_trail
    if not audit or not audit.evidence_spans:
        return "No evidence spans are available for this case."

    parts = ["**Evidence Spans by Code:**\n"]
    for code, spans in audit.evidence_spans.items():
        parts.append(f"**{code}:**")
        for span in spans:
            parts.append(f"- \"{span}\"")
        parts.append("")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Answer generation (3-tier)
# ---------------------------------------------------------------------------

_FALLBACK_RESPONSE = (
    "I don't have specific information about that. Try one of the pre-seeded "
    "questions in the sidebar for verified answers about the ClinIQ system, "
    "or ask about the active patient case."
)


def _generate_answer(
    user_question: str,
    bank: list[dict[str, str]],
    use_llm: bool,
) -> tuple[str, str]:
    """Return (answer_text, source_badge).

    Tries: pre-seeded -> patient context -> LLM fallback.
    """
    # Tier 1: pre-seeded system answers
    match = _find_best_match(user_question, bank)
    if match is not None:
        return match, "Pre-seeded"

    # Tier 2: patient-context answers
    pipeline_result = _get_pipeline_result()
    if pipeline_result is not None and _is_patient_question(user_question):
        answer = _answer_from_pipeline(user_question, pipeline_result)
        return answer, "Patient Context"

    # Tier 3: LLM fallback (opt-in)
    if use_llm:
        try:
            return _FALLBACK_RESPONSE, "Generated"
        except Exception:
            return _FALLBACK_RESPONSE, "Generated"

    # No pipeline result but question seems patient-related
    if _is_patient_question(user_question):
        return (
            "No pipeline result is loaded. Please run the pipeline on a demo "
            "case first (via the **Pipeline Runner** page), then come back to "
            "ask patient-specific questions.",
            "No Data",
        )

    return _FALLBACK_RESPONSE, "Generated"


# ── Page UI ─────────────────────────────────────────────────────────────────

st.title("QA Bot")

pipeline_result = _get_pipeline_result()
case_id = st.session_state.get("active_case_id")

if pipeline_result is not None:
    st.markdown(f"*Ask about the ClinIQ system or the active patient case* &nbsp; `{case_id or 'loaded'}`")
else:
    st.markdown("*Ask questions about the ClinIQ system*")

# --- Load question bank ---
question_bank = _load_questions()

# --- Sidebar: Patient Questions (only when pipeline result loaded) ---
if pipeline_result is not None:
    st.sidebar.markdown("### Patient Questions")
    st.sidebar.caption("Ask about the active case results.")
    for idx, q in enumerate(_PATIENT_QUESTIONS):
        if st.sidebar.button(q, key=f"pq_{idx}"):
            st.session_state["pending_question"] = q
    st.sidebar.markdown("---")

# --- Sidebar: System Questions ---
st.sidebar.markdown("### System Questions")
st.sidebar.caption("Click a question for an instant, verified answer.")

for idx, item in enumerate(question_bank):
    if st.sidebar.button(item["question"], key=f"q_{idx}"):
        st.session_state["pending_question"] = item["question"]

# --- Sidebar: Settings ---
st.sidebar.markdown("---")
st.sidebar.markdown("### Settings")
use_llm = st.sidebar.toggle(
    "Use LLM for unknown questions",
    value=False,
    help=(
        "When enabled, uses Qwen2.5-1.5B to answer questions not in the "
        "pre-seeded list. Requires model download."
    ),
)

# --- Initialise chat history ---
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Show welcome message based on whether a pipeline result is loaded
if not st.session_state["messages"]:
    welcome = _WELCOME_MESSAGE if pipeline_result is not None else _WELCOME_MESSAGE_NO_CASE
    st.session_state["messages"] = [
        {"role": "assistant", "content": welcome, "badge": None},
    ]

# --- Display existing messages ---
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        badge = msg.get("badge")
        if badge:
            st.caption(f"[{badge}]")

# --- Handle pending question from sidebar button ---
pending = st.session_state.pop("pending_question", None)

# --- Accept new input ---
placeholder = (
    "Ask about the patient, diagnoses, codes, gaps..."
    if pipeline_result is not None
    else "Ask about the pipeline, models, evaluation..."
)
user_input = st.chat_input(placeholder)

# Sidebar button takes priority over chat input
question = pending or user_input

if question:
    # Show user message
    st.session_state["messages"].append(
        {"role": "user", "content": question, "badge": None},
    )
    with st.chat_message("user"):
        st.markdown(question)

    # Generate answer (3-tier)
    answer, badge = _generate_answer(question, question_bank, use_llm)

    st.session_state["messages"].append(
        {"role": "assistant", "content": answer, "badge": badge},
    )
    with st.chat_message("assistant"):
        st.markdown(answer)
        st.caption(f"[{badge}]")
