# Phase 7: Optional Pinecone Vector DB Instead of FAISS When API Key Provided - Research

**Researched:** 2026-03-27
**Domain:** Vector database integration, retriever abstraction, Pinecone serverless
**Confidence:** HIGH

## Summary

This phase adds an optional Pinecone serverless vector store as an alternative to the local FAISS index for ICD-10 code retrieval in the cliniq_v2 (OpenAI) backend path. When the user provides a Pinecone API key at startup (alongside the OpenAI API key), the system should use Pinecone for vector similarity search instead of FAISS. When no Pinecone key is provided, behavior falls back to the existing FAISS path transparently.

The current codebase has a clean architecture for this: `FAISSRetriever` in `cliniq_v2/rag/retriever.py` has a simple `retrieve(query, top_k) -> list[dict]` interface that returns `[{code, description, score, rank}]`. The same interface can be implemented by a `PineconeRetriever` class. The key architectural task is introducing a retriever abstraction (Protocol or ABC) and a factory function that chooses between them based on session state. The ICD-10 dataset is only 265 codes, making Pinecone indexing trivial and well within the free tier (2 GB / ~300k records).

**Primary recommendation:** Use `pinecone` SDK v8+ with ServerlessSpec (AWS us-east-1, cosine metric, 1536 dimensions). Introduce a `BaseRetriever` Protocol, implement `PineconeRetriever` alongside the existing `FAISSRetriever`, and add a factory function `get_retriever()` that checks `st.session_state.get("pinecone_api_key")` to decide which retriever to instantiate.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pinecone` | >=8.0.0 | Pinecone serverless vector DB client | Official Pinecone Python SDK; v8 is latest stable on PyPI, requires Python >=3.10 (matches project), uses API version 2025-10 |
| `openai` | (existing) | Embeddings for query encoding | Already used by cliniq_v2 for text-embedding-3-small |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pinecone[grpc]` | >=8.0.0 | gRPC transport for faster upsert/query | Optional performance optimization; not needed for 265 codes |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Pinecone serverless | Pinecone pod-based | Serverless is simpler, auto-scales, free tier sufficient for 265 codes |
| Pinecone `upsert_records` (integrated embedding) | `upsert` with pre-computed vectors | Pre-computed vectors match existing OpenAI embedding workflow and are more controllable |
| LangChain PineconeVectorStore | Direct Pinecone SDK | Direct SDK avoids unnecessary abstraction layer and LangChain dependency |

**Installation:**
```bash
pip install "pinecone>=8.0.0"
```

Add to `pyproject.toml` as optional dependency:
```toml
[project.optional-dependencies]
pinecone = ["pinecone>=8.0.0"]
```

## Architecture Patterns

### Recommended Project Structure
```
cliniq_v2/
├── rag/
│   ├── __init__.py          # Updated exports
│   ├── base.py              # NEW: BaseRetriever Protocol
│   ├── retriever.py         # Existing FAISSRetriever (unchanged)
│   ├── pinecone_retriever.py # NEW: PineconeRetriever
│   ├── factory.py           # NEW: get_retriever() factory
│   └── build_index.py       # Existing FAISS build (unchanged)
├── pinecone_client.py       # NEW: Singleton PineconeClient (mirrors api_client.py)
├── config.py                # Updated with Pinecone constants
└── ...
scripts/
└── populate_pinecone_index.py  # NEW: CLI to populate Pinecone from ICD-10 codes
ui/
└── app.py                   # Updated: Pinecone API key input field
```

### Pattern 1: Retriever Protocol (Abstraction)
**What:** A `typing.Protocol` class defining the contract for all retrievers.
**When to use:** When multiple implementations share the same interface.
**Example:**
```python
# cliniq_v2/rag/base.py
from typing import Protocol

class BaseRetriever(Protocol):
    """Protocol for ICD-10 code retrieval backends."""

    def retrieve(self, query: str, top_k: int = 20) -> list[dict]:
        """Retrieve top-k ICD-10 codes for a clinical query.

        Returns:
            List of dicts with keys: code, description, score, rank.
        """
        ...

    def ensure_index_built(self) -> None:
        """Ensure the underlying index/collection is populated."""
        ...
```

### Pattern 2: PineconeClient Singleton (Mirrors OpenAIClient)
**What:** A singleton client for the Pinecone connection, matching the existing OpenAIClient pattern.
**When to use:** When the Pinecone API key is provided at runtime.
**Example:**
```python
# cliniq_v2/pinecone_client.py
from typing import Optional
from pinecone import Pinecone

class PineconeClient:
    """Singleton Pinecone client with runtime API key injection."""

    _instance: Optional["PineconeClient"] = None
    _client: Optional[Pinecone] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def configure(self, api_key: str) -> None:
        """Set API key and initialize client."""
        self._client = Pinecone(api_key=api_key)

    @property
    def client(self) -> Pinecone:
        if self._client is None:
            raise RuntimeError(
                "Pinecone client not configured. Call configure(api_key) first."
            )
        return self._client

    def validate_key(self) -> bool:
        """Test API key by listing indexes."""
        try:
            self.client.list_indexes()
            return True
        except Exception:
            return False

    @classmethod
    def clear(cls) -> None:
        cls._instance = None
        cls._client = None
```

### Pattern 3: PineconeRetriever
**What:** Drop-in replacement for FAISSRetriever using Pinecone for vector search.
**When to use:** When Pinecone API key is configured.
**Example:**
```python
# cliniq_v2/rag/pinecone_retriever.py
import numpy as np
from cliniq_v2.config import PINECONE_INDEX_NAME, PINECONE_NAMESPACE, RETRIEVAL_TOP_K, EMBEDDING_DIMENSIONS

class PineconeRetriever:
    """Retrieve ICD-10 codes from Pinecone serverless index."""

    def __init__(self):
        self._index = None

    def _ensure_connected(self):
        if self._index is None:
            from cliniq_v2.pinecone_client import PineconeClient
            pc = PineconeClient().client
            self._index = pc.Index(name=PINECONE_INDEX_NAME)

    def ensure_index_built(self) -> None:
        """Check Pinecone index exists and has vectors."""
        from cliniq_v2.pinecone_client import PineconeClient
        pc = PineconeClient().client
        if not pc.has_index(name=PINECONE_INDEX_NAME):
            raise RuntimeError(
                f"Pinecone index '{PINECONE_INDEX_NAME}' not found. "
                f"Run scripts/populate_pinecone_index.py first."
            )
        self._ensure_connected()
        stats = self._index.describe_index_stats()
        if stats.total_vector_count == 0:
            raise RuntimeError(
                f"Pinecone index '{PINECONE_INDEX_NAME}' is empty. "
                f"Run scripts/populate_pinecone_index.py to populate."
            )

    def retrieve(self, query: str, top_k: int = RETRIEVAL_TOP_K) -> list[dict]:
        from cliniq_v2.api_client import OpenAIClient

        self._ensure_connected()

        # Encode query with OpenAI (same embedding model as FAISS path)
        client = OpenAIClient().client
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=query,
        )
        query_vec = response.data[0].embedding

        # Query Pinecone
        results = self._index.query(
            vector=query_vec,
            top_k=top_k,
            include_metadata=True,
            namespace=PINECONE_NAMESPACE,
        )

        # Convert to standard format
        candidates = []
        for rank, match in enumerate(results["matches"], start=1):
            candidates.append({
                "code": match["metadata"]["code"],
                "description": match["metadata"]["description"],
                "score": float(match["score"]),
                "rank": rank,
            })
        return candidates
```

### Pattern 4: Retriever Factory
**What:** Factory function that returns the correct retriever based on session state.
**When to use:** At retriever instantiation points in the pipeline.
**Example:**
```python
# cliniq_v2/rag/factory.py
from cliniq_v2.rag.base import BaseRetriever
from cliniq_v2.rag.retriever import FAISSRetriever

def get_retriever() -> BaseRetriever:
    """Return appropriate retriever based on configured backends."""
    try:
        from cliniq_v2.pinecone_client import PineconeClient
        pc = PineconeClient()
        _ = pc.client  # Test if configured
        from cliniq_v2.rag.pinecone_retriever import PineconeRetriever
        return PineconeRetriever()
    except (RuntimeError, ImportError):
        return FAISSRetriever()
```

### Pattern 5: Index Population Script
**What:** CLI script to upload ICD-10 code embeddings to Pinecone (one-time setup).
**When to use:** Run once before using Pinecone retriever.
**Example:**
```python
# scripts/populate_pinecone_index.py
# Key steps:
# 1. Accept Pinecone API key + OpenAI API key as args/env vars
# 2. Create serverless index if not exists (1536d, cosine, aws/us-east-1)
# 3. Wait for index ready
# 4. Load ICD-10 codes from cliniq/data/icd10/icd10_codes.json
# 5. Embed descriptions with OpenAI text-embedding-3-small in batches
# 6. Upsert vectors with metadata {code, description, chapter} in batches of 200
# 7. Verify vector count matches code count
```

### Pattern 6: UI API Key Gate Extension
**What:** Add Pinecone API key input alongside the OpenAI API key gate.
**When to use:** At startup in ui/app.py.
**Example:**
```python
# In the API key gate section of ui/app.py, AFTER the OpenAI key input:
pinecone_key_input = st.text_input(
    "Pinecone API Key (optional)",
    type="password",
    placeholder="pcsk_...",
    help="Optional: enables cloud-hosted vector search instead of local FAISS index",
)
# Store in session_state["pinecone_api_key"] after validation
```

### Anti-Patterns to Avoid
- **Hardcoding the retriever type in m3_rag_coding.py:** The module currently does `retriever = FAISSRetriever()`. Change this to use the factory, not a conditional import inside the module.
- **Creating the Pinecone index at query time:** Index creation (with ServerlessSpec) can take 10-60 seconds. Always use a pre-created index via the population script. The PineconeRetriever should fail fast if the index doesn't exist.
- **Storing embeddings redundantly:** The Pinecone index stores the vectors -- do not also maintain a local FAISS copy when using Pinecone.
- **Skipping the cosine metric:** The existing FAISS index uses IndexFlatIP with normalized vectors (equivalent to cosine). Pinecone index MUST use `metric="cosine"` to produce comparable results.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Vector similarity search | Custom similarity computation | Pinecone `index.query()` | Pinecone handles ANN, scaling, and optimization |
| Batch upsert with retries | Custom retry logic | Pinecone SDK batch upsert (200 vectors/batch) | SDK handles serialization and 2MB limit |
| Index readiness polling | Custom polling loop | `pc.describe_index(name).status["ready"]` | SDK provides status field directly |
| API key validation | Custom HTTP calls | `pc.list_indexes()` (catches auth errors) | SDK raises clear exceptions on invalid keys |

**Key insight:** The Pinecone Python SDK handles all the infrastructure complexity (connection pooling, retries, serialization). The only custom code needed is the retriever adapter mapping Pinecone response format to the existing `{code, description, score, rank}` dict format.

## Common Pitfalls

### Pitfall 1: Index Not Ready After create_index
**What goes wrong:** Calling `upsert()` immediately after `create_index()` returns 404 or 403.
**Why it happens:** `create_index()` is asynchronous -- it submits the job but returns before provisioning completes.
**How to avoid:** Poll with `while not pc.describe_index(name).status["ready"]: time.sleep(1)`.
**Warning signs:** 404 errors on upsert immediately after index creation.

### Pitfall 2: Namespace Mismatch Between Upsert and Query
**What goes wrong:** Queries return 0 results despite successful upsert.
**Why it happens:** Vectors were upserted to namespace "X" but query targets default namespace or "Y".
**How to avoid:** Use a constant `PINECONE_NAMESPACE = "icd10"` in config, referenced by both populate script and retriever.
**Warning signs:** `describe_index_stats()` shows vectors in one namespace but queries target another.

### Pitfall 3: Score Interpretation Differs Between FAISS and Pinecone
**What goes wrong:** Confidence thresholds or comparisons break when switching retrievers.
**Why it happens:** FAISS IndexFlatIP returns raw inner product scores. Pinecone cosine returns 0.0-1.0 similarity. The numerical ranges differ.
**How to avoid:** Both use cosine similarity (FAISS via normalized vectors + IP), so scores should be comparable. However, document that score semantics may vary slightly and avoid hard-coded thresholds on retrieval scores (the current code passes all 20 candidates to GPT-4o without threshold filtering, which is the right approach).
**Warning signs:** GPT-4o receives candidates with unexpected score distributions.

### Pitfall 4: Pinecone Free Tier Inactivity Pause
**What goes wrong:** Index becomes unavailable after 3 weeks of no queries.
**Why it happens:** Pinecone Starter plan pauses inactive indexes to save resources.
**How to avoid:** Document this limitation. The populate script should check for paused indexes and provide clear error messages. Consider adding a "resume" step in ensure_index_built().
**Warning signs:** Queries suddenly fail after a period of no use.

### Pitfall 5: Import Errors When Pinecone Not Installed
**What goes wrong:** Application crashes on startup if `pinecone` package isn't installed.
**Why it happens:** Pinecone is an optional dependency.
**How to avoid:** Guard all Pinecone imports with try/except ImportError. The factory function should gracefully fall back to FAISS when pinecone isn't installed.
**Warning signs:** ImportError on `from pinecone import Pinecone`.

### Pitfall 6: Vector ID Format
**What goes wrong:** Upsert fails or deduplication breaks with poor ID choices.
**Why it happens:** Pinecone IDs must be strings <= 512 characters.
**How to avoid:** Use the ICD-10 code itself as the vector ID (e.g., "E11.9"). Codes are unique, short, and human-readable.
**Warning signs:** Duplicate vectors in the index, or confusing opaque UUIDs.

## Code Examples

Verified patterns from official Pinecone documentation:

### Creating a Serverless Index
```python
# Source: https://docs.pinecone.io/guides/index-data/create-an-index
from pinecone import Pinecone, ServerlessSpec
import time

pc = Pinecone(api_key="YOUR_API_KEY")

if not pc.has_index(name="cliniq-icd10"):
    pc.create_index(
        name="cliniq-icd10",
        dimension=1536,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )
    # Wait for ready
    while not pc.describe_index("cliniq-icd10").status["ready"]:
        time.sleep(1)
```

### Upserting Vectors with Metadata
```python
# Source: https://docs.pinecone.io/guides/index-data/upsert-data
index = pc.Index(name="cliniq-icd10")

# Batch upsert (265 codes fits in a single batch of 200 + remainder)
vectors = []
for code_entry, embedding in zip(codes, embeddings):
    vectors.append({
        "id": code_entry["code"],      # e.g., "E11.9"
        "values": embedding,             # 1536d float list
        "metadata": {
            "code": code_entry["code"],
            "description": code_entry["description"],
            "chapter": code_entry["chapter"],
        },
    })

# Batch in chunks of 200
for i in range(0, len(vectors), 200):
    batch = vectors[i : i + 200]
    index.upsert(vectors=batch, namespace="icd10")
```

### Querying with Vector
```python
# Source: https://docs.pinecone.io/guides/search/semantic-search
results = index.query(
    vector=query_embedding,  # 1536d list from OpenAI
    top_k=20,
    include_metadata=True,
    namespace="icd10",
)

# Response shape:
# {
#     "matches": [
#         {"id": "E11.9", "score": 0.92, "metadata": {"code": "E11.9", "description": "...", "chapter": "..."}},
#         ...
#     ],
#     "namespace": "icd10",
#     "usage": {"read_units": N}
# }

for match in results["matches"]:
    print(f"{match['id']}: {match['score']:.3f} - {match['metadata']['description']}")
```

### Index Stats Check
```python
# Verify population succeeded
stats = index.describe_index_stats()
print(f"Total vectors: {stats.total_vector_count}")
print(f"Namespaces: {stats.namespaces}")
# Expected: {'icd10': {'vector_count': 265}}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `pinecone-client` package name | `pinecone` package name | SDK v5.1.0 (2024) | Must use `pip install pinecone`, NOT `pinecone-client` |
| `pinecone.init(api_key=...)` | `Pinecone(api_key=...)` class | SDK v3+ (2023) | Object-oriented client, no global init |
| Pod-based indexes | Serverless indexes | 2024 | Free tier uses serverless, simpler pricing, auto-scales |
| `Environment` parameter | `ServerlessSpec(cloud, region)` | SDK v5+ | No environment string needed; specify cloud+region directly |
| Python 3.8/3.9 support | Python 3.10+ required | SDK v8.0.0 (2025) | Matches this project's `requires-python = ">=3.10"` |

**Deprecated/outdated:**
- `pinecone-client` package: Replaced by `pinecone` package since v5.1.0. Must uninstall `pinecone-client` if present.
- `pinecone.init()` global function: Replaced by `Pinecone(api_key=...)` class constructor.
- `pinecone.GRPCIndex`: Now `from pinecone.grpc import PineconeGRPC`.
- `pinecone-plugin-inference` / `pinecone-plugin-records`: Merged into core `pinecone` package in v6.0.0.

## Codebase Integration Points

### Current Flow (FAISS)
```
ui/app.py (OpenAI key gate)
    -> st.session_state["openai_api_key"]
    -> OpenAIClient.configure(key)

m3_rag_coding.py::code_entities()
    -> retriever = FAISSRetriever()
    -> retriever.ensure_index_built()
    -> retriever.retrieve(query, top_k=20)
    -> reason_with_gpt4o(entity, candidates, clinical_context)
```

### Target Flow (with Pinecone option)
```
ui/app.py (OpenAI key gate + optional Pinecone key)
    -> st.session_state["openai_api_key"]
    -> st.session_state["pinecone_api_key"]  # NEW
    -> OpenAIClient.configure(key)
    -> PineconeClient.configure(key)         # NEW (if key provided)

m3_rag_coding.py::code_entities()
    -> retriever = get_retriever()             # CHANGED: factory instead of direct FAISSRetriever()
    -> retriever.ensure_index_built()          # Same interface, different implementation
    -> retriever.retrieve(query, top_k=20)     # Same interface, queries Pinecone or FAISS
    -> reason_with_gpt4o(entity, candidates, clinical_context)  # UNCHANGED
```

### Files That Change
| File | Change Type | What Changes |
|------|-------------|--------------|
| `cliniq_v2/rag/base.py` | NEW | BaseRetriever Protocol |
| `cliniq_v2/pinecone_client.py` | NEW | PineconeClient singleton |
| `cliniq_v2/rag/pinecone_retriever.py` | NEW | PineconeRetriever class |
| `cliniq_v2/rag/factory.py` | NEW | get_retriever() factory |
| `scripts/populate_pinecone_index.py` | NEW | CLI to populate Pinecone index |
| `cliniq_v2/rag/__init__.py` | MODIFY | Export new classes |
| `cliniq_v2/config.py` | MODIFY | Add PINECONE_INDEX_NAME, PINECONE_NAMESPACE constants |
| `cliniq_v2/modules/m3_rag_coding.py` | MODIFY | Use get_retriever() instead of FAISSRetriever() |
| `ui/app.py` | MODIFY | Add optional Pinecone API key input + validation |
| `ui/helpers/backend.py` | MODIFY (optional) | Add is_pinecone_backend() helper |
| `pyproject.toml` | MODIFY | Add pinecone as optional dependency |

### Files That Do NOT Change
| File | Why Unchanged |
|------|---------------|
| `cliniq_v2/rag/retriever.py` | FAISSRetriever stays exactly as-is |
| `cliniq_v2/rag/build_index.py` | FAISS build logic stays exactly as-is |
| `cliniq_v2/api_client.py` | OpenAIClient stays exactly as-is |
| `cliniq_v2/pipeline.py` | Calls m3_rag_coding which handles retriever internally |
| All `cliniq/` (v1) files | v1 backend is unaffected |

## Pinecone Free Tier Viability

| Metric | Free Tier Limit | This Project's Usage | Verdict |
|--------|-----------------|---------------------|---------|
| Storage | 2 GB | 265 vectors x 1536d x 4 bytes = ~1.6 MB | Well within limits |
| Indexes | 5 | 1 (cliniq-icd10) | Well within limits |
| Namespaces | 100 per index | 1 (icd10) | Well within limits |
| Write units | 2M/month | 265 vectors (one-time) | Negligible |
| Read units | 1M/month | ~20 per pipeline run | Well within limits |
| Region | AWS us-east-1 only | AWS us-east-1 | Compatible |
| Max dimensions | 20,000 | 1,536 | Compatible |

**Conclusion:** The free Starter plan is more than sufficient. The 265-code ICD-10 dataset is trivially small for Pinecone.

## Open Questions

1. **Index name convention**
   - What we know: Pinecone index names must be lowercase alphanumeric with hyphens. A good candidate is `cliniq-icd10`.
   - What's unclear: Should the index name be configurable or hardcoded?
   - Recommendation: Use a config constant `PINECONE_INDEX_NAME = "cliniq-icd10"` in `cliniq_v2/config.py`. This is sufficient for now; a user who needs a different name can modify the config.

2. **Auto-populate vs. manual script**
   - What we know: The existing FAISS index has `ensure_index_built()` which auto-builds if missing. Pinecone index creation takes time and costs API calls (OpenAI embeddings).
   - What's unclear: Should PineconeRetriever auto-populate, or require a separate script run?
   - Recommendation: Require separate script (`scripts/populate_pinecone_index.py`). Auto-creating a cloud index silently is surprising behavior. The retriever should fail fast with a helpful error message if the index is empty or missing.

3. **Sidebar indicator for Pinecone**
   - What we know: The sidebar currently shows "OpenAI Backend" or "Local Models". Adding Pinecone context would be informative.
   - What's unclear: Exact UI treatment.
   - Recommendation: Add a small indicator like "Vector DB: Pinecone" or "Vector DB: FAISS (local)" in the sidebar footer, beneath the backend version line.

## Sources

### Primary (HIGH confidence)
- [Pinecone Python SDK reference](https://docs.pinecone.io/reference/python-sdk) - SDK versions, import paths, API patterns
- [Pinecone PyPI page](https://pypi.org/project/pinecone/) - v8.1.0 latest, Python >=3.10 requirement
- [Pinecone database limits](https://docs.pinecone.io/reference/api/database-limits) - Max dimensions, batch sizes, plan limits
- [Pinecone SDK managing indexes](https://sdk.pinecone.io/python/db_control/shared-index-actions.html) - has_index(), create_index(), describe_index() patterns
- [Pinecone upsert docs](https://docs.pinecone.io/guides/index-data/upsert-data) - Batch upsert pattern, vector format
- [Pinecone semantic search](https://docs.pinecone.io/guides/search/semantic-search) - Query API, response format

### Secondary (MEDIUM confidence)
- [Pinecone pricing page](https://www.pinecone.io/pricing/) - Free tier limits (2 GB, 5 indexes)
- [Pinecone serverless free announcement](https://www.pinecone.io/blog/serverless-free/) - 3x capacity, 300k records at 1536d
- [Pinecone GitHub releases](https://github.com/pinecone-io/pinecone-python-client/releases) - v6, v7, v8 changelog
- [Pinecone SDK upgrading guide](https://sdk.pinecone.io/python/upgrading.html) - Breaking changes between SDK versions
- [Pinecone wait for index creation](https://docs.pinecone.io/troubleshooting/wait-for-index-creation) - describe_index polling pattern

### Tertiary (LOW confidence)
- None. All findings verified with official documentation.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Verified with PyPI and official docs. SDK v8.1.0 confirmed, Python >=3.10 matches project.
- Architecture: HIGH - Based on direct analysis of existing codebase (retriever.py, api_client.py patterns) and official Pinecone SDK patterns. The retriever abstraction pattern is straightforward.
- Pitfalls: HIGH - Documented from official Pinecone troubleshooting guides and community-reported issues.

**Research date:** 2026-03-27
**Valid until:** 2026-04-27 (30 days - Pinecone SDK is stable, no fast-moving changes expected)
