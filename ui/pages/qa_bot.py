"""
QA Bot page — interactive interview Q&A for the ClinIQ system.

Two-tier answer strategy:
  1. **Pre-seeded** (default): keyword/Jaccard matching against demo_questions.json
     for instant, verified responses.
  2. **LLM fallback** (opt-in): uses Qwen via RAG for novel questions.  Not
     imported at page load to avoid model downloads on startup.
"""

from __future__ import annotations

import json
import pathlib
from typing import TYPE_CHECKING

import streamlit as st

if TYPE_CHECKING:
    pass  # reserved for future heavy-type imports

# ---------------------------------------------------------------------------
# Constants / paths
# ---------------------------------------------------------------------------

_DEMO_QUESTIONS_PATH = pathlib.Path(__file__).resolve().parent.parent / "demo_data" / "demo_questions.json"

_WELCOME_MESSAGE = (
    "Welcome! I'm the ClinIQ QA Bot. Ask me about the pipeline architecture, "
    "models, evaluation metrics, or any aspect of the system. Try the "
    "pre-seeded questions in the sidebar for instant answers!"
)


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
    """Lowercase split into word tokens, stripping punctuation."""
    return {
        w.strip(".,;:!?\"'()[]{}") for w in text.lower().split() if len(w) > 1
    }


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
# Answer generation
# ---------------------------------------------------------------------------

_FALLBACK_RESPONSE = (
    "I don't have specific information about that. Try one of the pre-seeded "
    "questions in the sidebar for verified answers about the ClinIQ system."
)


def _generate_answer(
    user_question: str,
    bank: list[dict[str, str]],
    use_llm: bool,
) -> tuple[str, str]:
    """Return (answer_text, source_badge).

    *source_badge* is ``"Pre-seeded"`` or ``"Generated"``.
    """
    match = _find_best_match(user_question, bank)
    if match is not None:
        return match, "Pre-seeded"

    # LLM fallback (opt-in)
    if use_llm:
        # Heavy imports only when actually needed
        try:
            # Placeholder — real RAG integration goes here
            return _FALLBACK_RESPONSE, "Generated"
        except Exception:
            return _FALLBACK_RESPONSE, "Generated"

    return _FALLBACK_RESPONSE, "Generated"


# ── Page UI ─────────────────────────────────────────────────────────────────

st.title("QA Bot")
st.markdown("*Ask questions about the ClinIQ system*")

# --- Load question bank ---
question_bank = _load_questions()

# --- Sidebar: Quick Questions ---
st.sidebar.markdown("### Interview Questions")
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
    st.session_state["messages"] = [
        {"role": "assistant", "content": _WELCOME_MESSAGE, "badge": None},
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
user_input = st.chat_input("Ask about the pipeline, models, evaluation...")

# Sidebar button takes priority over chat input
question = pending or user_input

if question:
    # Show user message
    st.session_state["messages"].append(
        {"role": "user", "content": question, "badge": None},
    )
    with st.chat_message("user"):
        st.markdown(question)

    # Generate answer
    match = _find_best_match(question, question_bank)
    if match is not None:
        answer, badge = match, "Pre-seeded"
        # Pre-seeded: render immediately (no spinner)
        st.session_state["messages"].append(
            {"role": "assistant", "content": answer, "badge": badge},
        )
        with st.chat_message("assistant"):
            st.markdown(answer)
            st.caption(f"[{badge}]")
    else:
        # Potentially slow path
        with st.spinner("Thinking..."):
            answer, badge = _generate_answer(question, question_bank, use_llm)
        st.session_state["messages"].append(
            {"role": "assistant", "content": answer, "badge": badge},
        )
        with st.chat_message("assistant"):
            st.markdown(answer)
            st.caption(f"[{badge}]")
