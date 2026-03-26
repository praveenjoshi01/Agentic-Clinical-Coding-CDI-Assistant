# Phase 6: ClinIQ v2 -- OpenAI Backend - Research

**Researched:** 2026-03-26
**Domain:** OpenAI API integration, Python package architecture, model replacement strategy
**Confidence:** HIGH

## Summary

Phase 6 creates a `cliniq_v2` package that mirrors the entire `cliniq` pipeline but replaces all six local OSS models with OpenAI API calls. The existing codebase uses a clean module architecture (m1-m6) with a singleton `ModelManager` and Pydantic v2 data contracts. The replacement strategy is straightforward: every model touchpoint in the codebase is localized to well-defined functions, and OpenAI's Python SDK (v2.30+) provides direct equivalents for each capability (GPT-4o for reasoning/NER/CDI/vision, text-embedding-3-small for embeddings, Whisper API for audio). The critical architectural decision is whether to copy-and-modify vs. inherit-and-override -- given that the Pydantic models, KG infrastructure, RAG infrastructure (FAISS index, ICD-10 loader), and all data schemas remain identical, the cleanest approach is to reuse `cliniq.models`, `cliniq.rag`, and `cliniq.knowledge_graph` from the original package and only create new versions of `config.py`, `model_manager.py`, and the six pipeline modules (`m1`-`m6`), plus a new `pipeline.py` that imports from `cliniq_v2.modules` instead of `cliniq.modules`.

**Primary recommendation:** Create `cliniq_v2/` as a thin package that imports shared infrastructure (models, RAG, KG) from `cliniq` and only overrides the six modules + config + model_manager + pipeline. Use the OpenAI Python SDK v2.30+ with Pydantic-native structured outputs for all LLM calls. Rebuild the FAISS index with text-embedding-3-small embeddings (1536 dimensions, matching the current BGE small dimension). Add API key gate as a Streamlit session_state check in `app.py` before page navigation.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `openai` | >=2.30.0 | OpenAI API client for GPT-4o, embeddings, Whisper | Official Python SDK; type-safe, async-capable, Pydantic-native structured outputs |
| `pydantic` | v2 (existing) | Data validation schemas | Already used throughout `cliniq`; OpenAI SDK supports Pydantic models for structured outputs |
| `faiss-cpu` | >=1.8 (existing) | ICD-10 vector retrieval | FAISS index remains the same; only the embedder changes |
| `networkx` | >=3.3 (existing) | Knowledge graph | KG is model-agnostic; reused from `cliniq` verbatim |
| `streamlit` | >=1.38 (existing) | UI framework | Existing UI; add API key gate only |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `httpx` | (transitive via openai) | HTTP transport for API calls | Used internally by openai SDK |
| `numpy` | (existing) | Embedding array operations | FAISS query vectors |
| `pillow` | (existing) | Image loading for vision API | Image ingestion path only |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Direct openai SDK | LangChain/LiteLLM wrappers | Adds dependency; openai SDK is sufficient and simpler for single-provider use |
| text-embedding-3-small (1536d) | text-embedding-3-large (3072d) | Large is ~5x more expensive; small is sufficient for ICD-10 retrieval and matches existing BGE dimension |
| GPT-4o for NER | Fine-tuned GPT-4o-mini | Cheaper but requires fine-tuning data; GPT-4o zero-shot NER is sufficient for this POC |
| Whisper API (whisper-1) | gpt-4o-transcribe | Newer model but whisper-1 is cheaper and proven; either works |

**Installation:**
```bash
pip install openai>=2.30.0
```
No other new dependencies required -- all existing deps remain.

## Architecture Patterns

### Recommended Project Structure
```
cliniq_v2/
    __init__.py              # Version, package docstring
    config.py                # OpenAI model registry (replaces HF model IDs)
    api_client.py            # Singleton OpenAI client with API key management
    modules/
        __init__.py
        m1_ingest.py         # FHIR/text unchanged, image uses GPT-4o vision
        m2_nlu.py            # GPT-4o structured output for NER
        m3_rag_coding.py     # text-embedding-3-small + GPT-4o reasoning (no cross-encoder)
        m4_cdi.py            # GPT-4o for physician query generation
        m5_explainability.py # Thin wrapper (mostly model-agnostic already)
        m6_ambient.py        # Whisper API + GPT-4o for SOAP notes
    rag/
        __init__.py          # Re-exports from cliniq.rag + new embedder
        build_index.py       # Rebuild FAISS with text-embedding-3-small
        retriever.py         # OpenAI embedding at query time
    evaluation/
        __init__.py          # Re-exports from cliniq.evaluation
        llm_judge.py         # GPT-4o as judge (replaces Qwen)
    pipeline.py              # Orchestrator importing from cliniq_v2.modules
```

### Pattern 1: Singleton API Client with Key Injection
**What:** A singleton `OpenAIClient` class that holds the `openai.OpenAI` instance, initialized with the API key provided at runtime (via UI or environment variable).
**When to use:** Every module that makes API calls accesses the client through this singleton.
**Example:**
```python
# cliniq_v2/api_client.py
from openai import OpenAI
from typing import Optional

class OpenAIClient:
    """Singleton OpenAI client with runtime API key injection."""
    _instance: Optional["OpenAIClient"] = None
    _client: Optional[OpenAI] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def configure(self, api_key: str):
        """Set API key and initialize client. Called once at startup."""
        self._client = OpenAI(api_key=api_key)

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            raise RuntimeError("OpenAI client not configured. Call configure(api_key) first.")
        return self._client

    def validate_key(self) -> bool:
        """Test API key validity with a lightweight models.list() call."""
        try:
            self.client.models.list()
            return True
        except Exception:
            return False

    @classmethod
    def clear(cls):
        cls._instance = None
        cls._client = None
```

### Pattern 2: GPT-4o Structured Output for NER
**What:** Use `response_format` with a Pydantic schema to get guaranteed-valid JSON from GPT-4o for entity extraction.
**When to use:** Replaces d4data NER model -- GPT-4o extracts entities, types, negation, and qualifiers in one call.
**Example:**
```python
# cliniq_v2/modules/m2_nlu.py
from pydantic import BaseModel, Field
from cliniq.models.entities import ClinicalEntity, NLUResult

class NEROutput(BaseModel):
    """Schema for GPT-4o NER structured output."""
    entities: list[dict] = Field(description="List of extracted clinical entities")

def extract_entities(text: str) -> NLUResult:
    client = OpenAIClient().client
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": NER_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        response_format={"type": "json_object"},
        temperature=0.0,
    )
    # Parse JSON response into ClinicalEntity list
    ...
```

### Pattern 3: Embedding Replacement with FAISS Index Rebuild
**What:** Replace BGE embeddings with text-embedding-3-small for both index building and query-time encoding.
**When to use:** RAG pipeline initialization and per-query retrieval.
**Key detail:** text-embedding-3-small produces 1536-dimensional embeddings by default, which is the same as BGE-small-en-v1.5 (384d) -- wait, BGE-small is 384d, NOT 1536d. This means the FAISS index MUST be rebuilt with the new dimension (1536 vs 384). The existing FAISS index is incompatible.
**Example:**
```python
# cliniq_v2/rag/retriever.py
def embed_query(self, query: str) -> np.ndarray:
    client = OpenAIClient().client
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=query,
    )
    return np.array(response.data[0].embedding, dtype=np.float32)
```

### Pattern 4: UI API Key Gate
**What:** Before rendering any page, check `st.session_state["openai_api_key"]`. If missing, show an API key input screen and validate before proceeding.
**When to use:** In `app.py` before `pg.run()`.
**Example:**
```python
# In ui/app.py (v2 variant)
if "openai_api_key" not in st.session_state or not st.session_state["openai_api_key"]:
    st.title("ClinIQ v2 -- API Key Required")
    api_key = st.text_input("Enter your OpenAI API key", type="password")
    if st.button("Connect"):
        from cliniq_v2.api_client import OpenAIClient
        client = OpenAIClient()
        client.configure(api_key)
        if client.validate_key():
            st.session_state["openai_api_key"] = api_key
            st.rerun()
        else:
            st.error("Invalid API key.")
    st.stop()
```

### Pattern 5: Vision API for Image Ingestion
**What:** Replace SmolVLM with GPT-4o vision for extracting text from scanned clinical documents.
**When to use:** Image modality path in m1_ingest.py.
**Example:**
```python
import base64
from cliniq_v2.api_client import OpenAIClient

def parse_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    client = OpenAIClient().client
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                {"type": "text", "text": "Extract all clinical text from this medical document..."}
            ]
        }],
        max_tokens=1024,
    )
    return response.choices[0].message.content
```

### Pattern 6: Whisper API for Audio Transcription
**What:** Replace faster-whisper local model with OpenAI Whisper API.
**When to use:** Ambient mode audio transcription (m6_ambient.py).
**Example:**
```python
from cliniq_v2.api_client import OpenAIClient

def transcribe_audio(audio_path: str) -> str:
    client = OpenAIClient().client
    with open(audio_path, "rb") as f:
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="en",
        )
    return transcription.text
```

### Anti-Patterns to Avoid
- **Duplicating Pydantic models:** The `cliniq.models` package is model-agnostic. Import directly from `cliniq.models` instead of copying schemas into `cliniq_v2`.
- **Duplicating KG infrastructure:** `cliniq.knowledge_graph` uses NetworkX and curated rules -- zero model dependencies. Import directly.
- **Duplicating ICD-10 data loading:** `cliniq.rag.icd10_loader` is pure file I/O. Import directly.
- **Modifying `cliniq` package:** Requirement OAI-05 specifies backward compatibility. Never edit files in `cliniq/`.
- **Hardcoding API key:** Use session state or environment variable, never commit keys.
- **Using cross-encoder reranker:** With GPT-4o, the reranking step can be folded into the LLM reasoning prompt (send all 20 FAISS candidates to GPT-4o and let it select). This eliminates the cross-encoder dependency entirely.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON parsing from LLM output | Manual regex/string extraction | OpenAI structured outputs (`response_format: json_object`) | 100% valid JSON guaranteed; no retry logic needed |
| Embedding normalization | Custom L2 normalization | OpenAI API returns normalized embeddings; FAISS IndexFlatIP handles similarity | Embeddings from OpenAI API are already normalized |
| API key validation | Custom HTTP health check | `client.models.list()` -- lightest authenticated endpoint | Standard pattern; catches invalid keys, expired keys, rate limits |
| Audio format conversion | Custom ffmpeg wrapper | Whisper API accepts wav/mp3/m4a directly (up to 25MB) | Built-in format support |
| Retry logic for API calls | Custom exponential backoff | openai SDK has built-in retry with `max_retries` parameter | SDK handles 429/500/503 automatically |

**Key insight:** The OpenAI Python SDK v2.x handles most infrastructure concerns (retries, timeouts, streaming, type safety) that would otherwise require custom code. Lean on the SDK rather than wrapping it.

## Common Pitfalls

### Pitfall 1: FAISS Dimension Mismatch
**What goes wrong:** The existing FAISS index was built with BGE-small (384 dimensions). text-embedding-3-small produces 1536 dimensions by default. If you query the old index with new embeddings, FAISS will crash with a dimension mismatch error.
**Why it happens:** Developers assume "just swap the embedder" without considering the index.
**How to avoid:** Build a separate FAISS index for cliniq_v2 stored in a different cache directory (e.g., `~/.cache/cliniq_v2/icd10_index/`). Alternatively, use `dimensions=384` parameter in the OpenAI embedding call to match the existing BGE dimension, but this sacrifices embedding quality. Better to rebuild at 1536d.
**Warning signs:** `RuntimeError: ndarray shape mismatch` or `AssertionError` from FAISS.

### Pitfall 2: API Key Not Available at Import Time
**What goes wrong:** If modules import the OpenAI client at module level (top of file), the API key may not be set yet when Streamlit loads the page modules.
**Why it happens:** Streamlit evaluates page module files eagerly during navigation setup.
**How to avoid:** All OpenAI client access must be lazy -- only call `OpenAIClient().client` inside function bodies, never at module level. Use `TYPE_CHECKING` guards for type annotations.
**Warning signs:** `RuntimeError: OpenAI client not configured` on app startup.

### Pitfall 3: Exceeding Token Limits in NER Prompt
**What goes wrong:** Long clinical notes (>3000 words) may exceed GPT-4o's optimal context window when combined with NER system prompt and output schema.
**Why it happens:** Clinical notes can be very long; the NER prompt includes detailed instructions and examples.
**How to avoid:** Chunk long narratives into segments of ~2000 tokens, run NER on each chunk, then merge entities with deduplication. GPT-4o supports 128K context but costs scale linearly.
**Warning signs:** High API costs, slow response times, or truncated entity lists.

### Pitfall 4: Whisper API 25MB File Size Limit
**What goes wrong:** Audio files from long encounters (>30 minutes at high quality) can exceed the 25MB upload limit.
**Why it happens:** WAV files are uncompressed; a 30-minute mono 16kHz WAV is ~55MB.
**How to avoid:** Convert to MP3 or M4A before upload (lossy but much smaller). Or chunk audio into segments. For the demo, pre-computed encounters are short enough.
**Warning signs:** `openai.BadRequestError: File too large`.

### Pitfall 5: Structured Output Schema Constraints
**What goes wrong:** OpenAI structured outputs require strict JSON Schema compliance. Some Pydantic v2 features (computed fields, complex validators, Union types) may not convert cleanly to JSON Schema.
**Why it happens:** OpenAI's schema enforcement is stricter than Pydantic's runtime validation.
**How to avoid:** Use simple Pydantic models for the `response_format` -- flat fields with basic types (str, int, float, bool, list, Optional). Complex types like ClinicalEntity can be represented as plain dicts in the API response schema, then validated into Pydantic models after parsing.
**Warning signs:** `openai.BadRequestError: Invalid schema`.

### Pitfall 6: Forgetting to Update UI Imports
**What goes wrong:** The UI currently imports from `cliniq.pipeline` and `cliniq.modules`. If you switch to `cliniq_v2` without updating the UI, the v1 pipeline runs instead.
**Why it happens:** Multiple import points across 7 UI page files.
**How to avoid:** Use a backend selector pattern: the UI checks which backend to use (v1 or v2) based on session state, then dynamically imports from the correct package. This also enables backward compatibility.
**Warning signs:** Pipeline runs without API calls (using local models instead).

## Code Examples

### Example 1: GPT-4o NER with Structured Output
```python
# Source: OpenAI Structured Outputs docs + existing m2_nlu.py pattern
import json
import time
from cliniq_v2.api_client import OpenAIClient
from cliniq.models.entities import ClinicalEntity, NLUResult

NER_SYSTEM_PROMPT = """You are a clinical NER system. Extract all clinical entities from the text.

For each entity, provide:
- text: the exact text span
- entity_type: one of "diagnosis", "procedure", "medication", "anatomical_site", "lab_value", "qualifier"
- start_char: character offset start in the original text
- end_char: character offset end in the original text
- confidence: your confidence 0.0-1.0
- negated: true if the entity is negated (e.g., "no fever", "denies pain")
- qualifiers: list of qualifying terms (e.g., ["stage 3", "chronic", "bilateral"])

Return a JSON object: {"entities": [...]}"""

def extract_entities(text: str) -> NLUResult:
    start_time = time.time()
    client = OpenAIClient().client

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": NER_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        response_format={"type": "json_object"},
        temperature=0.0,
    )

    raw = json.loads(response.choices[0].message.content)
    entities = [ClinicalEntity(**e) for e in raw.get("entities", [])]
    processing_time_ms = (time.time() - start_time) * 1000

    return NLUResult(entities=entities, processing_time_ms=processing_time_ms)
```

### Example 2: RAG Coding with GPT-4o (Eliminates Cross-Encoder)
```python
# Source: existing m3_rag_coding.py pattern + OpenAI embeddings API
import json
from cliniq_v2.api_client import OpenAIClient
from cliniq.models import ClinicalEntity, CodeSuggestion

def retrieve_candidates(query: str, retriever) -> list[dict]:
    """FAISS retrieval using text-embedding-3-small embeddings."""
    client = OpenAIClient().client
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=query,
    )
    query_vec = np.array(response.data[0].embedding, dtype=np.float32).reshape(1, -1)
    distances, indices = retriever.index.search(query_vec, 20)
    return [{"code": retriever.codes[i]["code"],
             "description": retriever.codes[i]["description"],
             "score": float(d)} for i, d in zip(indices[0], distances[0])]

def reason_with_gpt4o(entity: ClinicalEntity, candidates: list[dict], context: str) -> dict:
    """GPT-4o selects best code and provides reasoning (replaces Qwen + cross-encoder)."""
    client = OpenAIClient().client
    # Send all 20 candidates -- GPT-4o handles reranking internally
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a clinical coding expert..."},
            {"role": "user", "content": f"Entity: {entity.text}\nCandidates:\n{candidates}\nContext: {context[:500]}"},
        ],
        response_format={"type": "json_object"},
        temperature=0.0,
    )
    return json.loads(response.choices[0].message.content)
```

### Example 3: API Key Validation in Streamlit
```python
# Source: OpenAI API key validation pattern + Streamlit session state docs
import streamlit as st

def require_api_key():
    """Gate function: blocks page rendering until valid API key is provided."""
    if st.session_state.get("openai_api_key"):
        return  # Already validated

    st.title("ClinIQ v2 -- OpenAI API Key Required")
    st.markdown("Enter your OpenAI API key to use the ClinIQ v2 backend.")
    st.caption("Your key is stored in session memory only and never saved to disk.")

    key = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")

    if st.button("Connect", type="primary"):
        if not key.startswith("sk-"):
            st.error("Invalid key format. OpenAI keys start with 'sk-'.")
            st.stop()

        from cliniq_v2.api_client import OpenAIClient
        oc = OpenAIClient()
        oc.configure(key)
        if oc.validate_key():
            st.session_state["openai_api_key"] = key
            st.success("Connected successfully!")
            st.rerun()
        else:
            st.error("API key validation failed. Check your key and try again.")

    st.stop()
```

### Example 4: GPT-4o Vision for Image Ingestion
```python
# Source: OpenAI Images and Vision docs
import base64
from pathlib import Path
from cliniq_v2.api_client import OpenAIClient

def parse_image_with_gpt4o(image_path: str) -> str:
    """Extract clinical text from scanned document using GPT-4o vision."""
    path = Path(image_path)
    with open(path, "rb") as f:
        b64_image = base64.b64encode(f.read()).decode("utf-8")

    # Determine MIME type
    suffix = path.suffix.lower()
    mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
    mime = mime_map.get(suffix, "image/png")

    client = OpenAIClient().client
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64_image}", "detail": "high"}},
                {"type": "text", "text": (
                    "Extract all clinical text from this medical document. "
                    "Include all diagnoses, procedures, medications, and "
                    "clinical findings exactly as written."
                )},
            ],
        }],
        max_tokens=1024,
    )
    return response.choices[0].message.content
```

## Model Replacement Map

This is the complete mapping of every model touchpoint in the codebase and its OpenAI replacement:

| Original Model | HuggingFace ID | Used In | Replaced By | OpenAI Model |
|---------------|----------------|---------|-------------|--------------|
| CLINICAL_NER | d4data/biomedical-ner-all | m2_nlu.py (extract_raw_entities) | GPT-4o structured output NER | gpt-4o |
| REASONING_LLM | Qwen/Qwen2.5-1.5B-Instruct | m3_rag_coding.py (reason_with_llm), m4_cdi.py (generate_physician_query), m6_ambient.py (generate_soap_note), evaluation/llm_judge.py | GPT-4o chat completions | gpt-4o |
| EMBEDDER | BAAI/bge-small-en-v1.5 | rag/retriever.py (query encoding), rag/build_index.py (index building) | OpenAI Embeddings API | text-embedding-3-small |
| RERANKER | cross-encoder/ms-marco-MiniLM-L-6-v2 | rag/reranker.py | Eliminated -- GPT-4o handles selection from candidates | N/A (folded into GPT-4o reasoning) |
| MULTIMODAL | HuggingFaceTB/SmolVLM-256M-Instruct | m1_ingest.py (parse_image) | GPT-4o vision | gpt-4o |
| WHISPER | faster-whisper small model | m6_ambient.py (transcribe_audio) | OpenAI Whisper API | whisper-1 |

## Module-by-Module Change Analysis

### m1_ingest.py
- **parse_fhir():** No changes needed -- pure FHIR parsing, no model dependency.
- **parse_text():** No changes needed -- pass-through, no model dependency.
- **parse_image():** Replace SmolVLM with GPT-4o vision API. Load image as base64, send to chat completions with image_url content type. Remove `ModelManager().get_multimodal()` call.
- **detect_modality():** No changes needed.
- **ingest():** No changes needed -- router function.

### m2_nlu.py
- **extract_raw_entities():** Complete replacement. Instead of d4data NER pipeline, send full text to GPT-4o with structured output requesting entity extraction. GPT-4o handles entity typing, negation detection, and qualifier capture in a single call.
- **detect_negation():** Can be eliminated or kept as validation layer. GPT-4o's NER prompt should handle negation directly.
- **capture_qualifiers():** Can be eliminated. GPT-4o extracts qualifiers as part of entity output.
- **map_entity_type():** Not needed -- GPT-4o outputs pipeline entity types directly.
- **extract_entities():** Simplified orchestrator -- one API call replaces the multi-step pipeline.

### m3_rag_coding.py
- **build_coding_query():** No changes needed -- string construction.
- **retrieve_and_rerank():** Replace retriever's BGE encoding with text-embedding-3-small. Eliminate cross-encoder reranking entirely -- send all 20 FAISS candidates directly to GPT-4o.
- **reason_with_llm():** Replace Qwen tokenizer+generate with GPT-4o chat completion. Use `response_format: json_object` for reliable JSON output (eliminates retry logic).
- **build_code_suggestion():** Minor changes to confidence blending (no reranker score).
- **sequence_codes():** No changes needed -- rule-based logic.
- **code_entities():** Update to use new retriever and remove reranker dependency.

### m4_cdi.py
- **_get_kg():** No changes -- KG is model-agnostic.
- **generate_physician_query():** Replace Qwen with GPT-4o chat completion. Same prompt structure, just different API call.
- **_extract_entity_qualifiers():** No changes -- pure data manipulation.
- **_find_evidence_for_code():** No changes -- pure text search.
- **calculate_completeness_score():** No changes -- pure math.
- **run_cdi_analysis():** No changes to orchestration logic, just uses updated generate_physician_query.

### m5_explainability.py
- **AuditTrailBuilder:** No changes -- model-agnostic instrumentation.
- **capture_cot_and_json():** No changes -- string parsing utility.
- **link_evidence_spans():** No changes -- string matching.
- **build_retrieval_log():** No changes.
- This module is almost entirely model-agnostic. Can be imported directly from `cliniq.modules.m5_explainability`.

### m6_ambient.py
- **transcribe_audio():** Replace faster-whisper with OpenAI Whisper API. Much simpler -- just open file and call API.
- **generate_soap_note():** Replace Qwen with GPT-4o chat completion. Same prompt, different API.
- **_parse_note_sections():** No changes -- string parsing.
- **run_ambient_pipeline():** Update to call cliniq_v2.pipeline instead of cliniq.pipeline.

### evaluation/llm_judge.py
- **_generate_judge_response():** Replace Qwen with GPT-4o. Same prompt templates, different API.
- **_parse_judge_response():** No changes -- JSON parsing.
- All aggregate functions unchanged.

### pipeline.py
- **run_pipeline():** Import from `cliniq_v2.modules` instead of `cliniq.modules`.
- **run_pipeline_audited():** Same -- update imports only.
- Core orchestration logic unchanged.

## Shared vs. New Code Analysis

### Reuse from `cliniq` (import directly):
- `cliniq/models/` -- ALL Pydantic schemas (document, entities, coding, cdi, audit, ambient, evaluation)
- `cliniq/rag/icd10_loader.py` -- ICD-10 code loading (pure file I/O)
- `cliniq/knowledge_graph/` -- KG builder, querier, schema (NetworkX, no ML)
- `cliniq/data/` -- All data files (ICD-10 codes, kg_rules, gold standard)

### New code in `cliniq_v2`:
- `cliniq_v2/config.py` -- OpenAI model names, API settings
- `cliniq_v2/api_client.py` -- Singleton OpenAI client
- `cliniq_v2/modules/m1_ingest.py` -- Only parse_image changes
- `cliniq_v2/modules/m2_nlu.py` -- Full rewrite (GPT-4o NER)
- `cliniq_v2/modules/m3_rag_coding.py` -- Modified (OpenAI embeddings + GPT-4o reasoning, no reranker)
- `cliniq_v2/modules/m4_cdi.py` -- Modified (GPT-4o physician queries)
- `cliniq_v2/modules/m5_explainability.py` -- Thin re-export (almost no changes)
- `cliniq_v2/modules/m6_ambient.py` -- Modified (Whisper API + GPT-4o SOAP)
- `cliniq_v2/rag/build_index.py` -- Rebuild with text-embedding-3-small
- `cliniq_v2/rag/retriever.py` -- OpenAI embedding at query time
- `cliniq_v2/evaluation/llm_judge.py` -- Modified (GPT-4o as judge)
- `cliniq_v2/pipeline.py` -- Updated imports

### UI changes:
- `ui/app.py` -- Add API key gate + backend selector (v1/v2)
- Import changes in pages that reference pipeline/modules (conditional imports based on backend)

## FAISS Index Strategy

**Current state:** BGE-small produces 384-dimensional embeddings. The FAISS index at `~/.cache/cliniq/icd10_index/` uses IndexFlatIP with 384-d vectors.

**text-embedding-3-small:** Produces 1536-dimensional embeddings by default. Can be reduced to 384 using the `dimensions` parameter, but this sacrifices quality.

**Recommended approach:**
1. Build a separate FAISS index for cliniq_v2 at `~/.cache/cliniq_v2/icd10_index/`
2. Use full 1536 dimensions for best retrieval quality
3. The `cliniq_v2/rag/build_index.py` calls OpenAI Embeddings API to embed all ~70,000 ICD-10 descriptions
4. This is a one-time operation (save index to disk)
5. Cost estimate: ~70K descriptions * ~10 tokens each = ~700K tokens = ~$0.014 at $0.02/M tokens

**Alternative:** Use `dimensions=384` to match BGE-small and potentially reuse the same FAISS index structure. But index content would still differ (different embeddings), so a rebuild is required regardless. Better to use 1536d.

## UI Architecture for Backend Selection

The UI needs to support both `cliniq` (v1, local models) and `cliniq_v2` (OpenAI API) backends:

**Option A: Separate app.py files** -- `ui/app.py` (v1) and `ui/app_v2.py` (v2). Simple but duplicates navigation/layout code.

**Option B: Backend selector in app.py** -- A toggle or session state flag selects which package to import. Pages use a helper function to get the correct pipeline module.

**Recommended: Option B** with a conditional import helper:
```python
# ui/helpers/backend.py
def get_pipeline_module():
    if st.session_state.get("openai_api_key"):
        from cliniq_v2 import pipeline
        return pipeline
    from cliniq import pipeline
    return pipeline
```

This keeps a single UI codebase and lets users switch between backends. The API key gate naturally determines which backend is active.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `response_format: {"type": "json_object"}` | `response_format` with JSON Schema / Pydantic | Aug 2024 (structured outputs) | Guarantees valid JSON matching exact schema; eliminates retry logic |
| `client.chat.completions.create()` | `client.chat.completions.parse()` for Pydantic | Aug 2024 | Returns parsed Pydantic model directly |
| whisper-1 only | gpt-4o-transcribe, whisper-1 both available | Dec 2025 | Newer transcription model available; whisper-1 still supported and cheaper |
| Manual retry on 429 | openai SDK built-in `max_retries` | SDK v1.0+ (Nov 2023) | No custom retry wrapper needed |

**Deprecated/outdated:**
- `openai.ChatCompletion.create()` (pre-v1.0 API): Replaced by `client.chat.completions.create()`
- `gpt-4-vision-preview`: Replaced by `gpt-4o` with native vision support

## Open Questions

1. **FAISS Index Rebuild Cost and Time**
   - What we know: ~70K ICD-10 descriptions need re-embedding. At $0.02/M tokens, cost is ~$0.014. Time depends on API rate limits.
   - What's unclear: Exact batch size for OpenAI Embeddings API (it accepts lists). Whether all 70K can be sent in reasonable number of batches.
   - Recommendation: Use batch size of 2048 (max supported), which means ~35 API calls. Should complete in under 2 minutes.

2. **GPT-4o NER Quality vs. d4data Specialized Model**
   - What we know: GPT-4o is a general-purpose model; d4data/biomedical-ner-all is fine-tuned for biomedical NER. Character offsets from GPT-4o may be less accurate than token-level NER.
   - What's unclear: Whether GPT-4o will produce accurate character offsets (`start_char`, `end_char`).
   - Recommendation: Ask GPT-4o for entity text + type + negation + qualifiers but NOT character offsets. Compute offsets post-hoc by searching for the entity text in the original narrative. This is more reliable.

3. **Cost Per Pipeline Run**
   - What we know: Each pipeline run involves ~4-6 GPT-4o calls (NER, coding per entity, CDI queries, SOAP note) + 1 embedding call. GPT-4o input ~$2.50/M tokens, output ~$10/M tokens.
   - What's unclear: Exact token usage varies by note length and entity count.
   - Recommendation: Add token usage tracking to the audit trail for cost transparency. Estimate ~$0.02-0.10 per pipeline run.

4. **Whether to Support Both Backends Simultaneously in the UI**
   - What we know: The spec requires original cliniq package to remain "unchanged and functional."
   - What's unclear: Whether the UI should offer a toggle between v1 and v2, or just run v2 when an API key is present.
   - Recommendation: Automatic selection -- if API key is configured, use v2; otherwise fall back to v1. No explicit toggle needed.

## Sources

### Primary (HIGH confidence)
- OpenAI Python SDK v2.30.0 (PyPI) -- https://pypi.org/project/openai/ -- version, API patterns
- OpenAI Structured Outputs docs -- https://platform.openai.com/docs/guides/structured-outputs -- Pydantic integration, response_format
- OpenAI Embeddings docs -- https://developers.openai.com/api/docs/guides/embeddings -- text-embedding-3-small dimensions, API usage
- OpenAI Speech to Text docs -- https://platform.openai.com/docs/guides/speech-to-text -- Whisper API, file limits, models
- OpenAI Images and Vision docs -- https://platform.openai.com/docs/guides/images-vision -- GPT-4o vision, base64 encoding

### Secondary (MEDIUM confidence)
- OpenAI API Changelog -- https://developers.openai.com/api/docs/changelog -- latest model updates
- Streamlit Session State docs -- https://docs.streamlit.io/develop/concepts/architecture/session-state -- API key management pattern
- OpenAI Python SDK GitHub -- https://github.com/openai/openai-python -- release history, features

### Tertiary (LOW confidence)
- Community patterns for API key validation -- https://gist.github.com/Wind010/f8cc1920246d4b6d903911350d0879ea -- models.list() approach (needs validation)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- OpenAI SDK is well-documented; all API patterns verified against official docs
- Architecture: HIGH -- Existing codebase thoroughly analyzed; module boundaries are clear and clean
- Pitfalls: HIGH -- FAISS dimension mismatch is well-known; API key lifecycle is well-understood
- Model replacement map: HIGH -- Every model touchpoint identified and mapped by reading all source files

**Research date:** 2026-03-26
**Valid until:** 2026-04-26 (stable -- OpenAI API is backward-compatible)
