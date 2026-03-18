# Architecture Research

**Domain:** Clinical NLP + RAG + Knowledge Graph Intelligence Platform
**Researched:** 2026-03-18
**Confidence:** MEDIUM-HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Presentation Layer                                │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │  Streamlit   │  │  KG Viz      │  │   QA Bot     │                  │
│  │  Dashboard   │  │  Interface   │  │  Interface   │                  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                  │
│         │                  │                  │                          │
├─────────┴──────────────────┴──────────────────┴──────────────────────────┤
│                     Orchestration Layer                                  │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                   Pipeline Orchestrator                         │    │
│  │         (Multi-Agent Coordinator + Model Manager)               │    │
│  └──────────────┬──────────────┬──────────────┬───────────────────┘    │
│                 │              │              │                          │
├─────────────────┴──────────────┴──────────────┴──────────────────────────┤
│                     Agent Processing Layer                               │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐      │
│  │ Ingest  │→ │  NER    │→ │   RAG   │→ │   CDI   │→ │ Audit   │      │
│  │ Agent   │  │ Agent   │  │ Coding  │  │   KG    │  │ Agent   │      │
│  │         │  │         │  │ Agent   │  │ Agent   │  │         │      │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘      │
│       │            │            │            │            │              │
│  ┌────┴────┐  ┌───┴─────┐  ┌───┴─────┐  ┌───┴─────┐  ┌──┴──────┐      │
│  │  Eval   │  │  Eval   │  │  Eval   │  │  Eval   │  │ Explain │      │
│  │ Module  │  │ Module  │  │ Module  │  │ Module  │  │ Module  │      │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘      │
├─────────────────────────────────────────────────────────────────────────┤
│                      Data & Retrieval Layer                              │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │    FAISS     │  │   NetworkX   │  │  HuggingFace │                  │
│  │ Vector Index │  │  Knowledge   │  │ Model Cache  │                  │
│  │  (~70k ICD)  │  │    Graph     │  │              │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
└─────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **Pipeline Orchestrator** | Coordinates multi-agent workflow; manages data flow between agents; handles error propagation | Python class with async support; implements Chain of Responsibility pattern |
| **Model Manager** | Centralized model loading/caching; version management; resource optimization | Singleton pattern with lazy loading; HuggingFace transformers cache integration |
| **Ingest Agent** | Parse raw clinical documents; normalize formats; validate structure | Document parser with format detection; Pydantic models for validation |
| **NER Agent** | Extract clinical entities (diagnoses, procedures, qualifiers); entity normalization | Fine-tuned BioBERT/ClinicalBERT; hybrid rule-based + transformer approach |
| **RAG Coding Agent** | Retrieve candidate ICD-10 codes; rank by semantic similarity; generate initial code assignments | FAISS similarity search + Sentence-BERT embeddings + generative refinement |
| **CDI KG Agent** | Query documentation requirements; identify gaps; suggest evidence improvements | Graph traversal algorithms (NetworkX); ontology-based reasoning |
| **Audit/Explainability Agent** | Generate evidence chains; create audit trails; map codes to clinical text spans | Attention visualization; provenance tracking; compliance reporting |
| **Evaluation Modules** | Compute metrics per agent; detect drift; flag confidence thresholds | Precision/Recall/F1; custom domain metrics; statistical monitoring |

## Recommended Project Structure

```
cliniq/                          # Core package
├── models/                      # Pydantic data schemas
│   ├── document.py              # ClinicalDocument, DocumentMetadata
│   ├── entities.py              # NEREntity, ClinicalConcept, Qualifier
│   ├── coding.py                # CodingResult, ICDCode, CodingEvidence
│   ├── cdi.py                   # CDIReport, DocumentationGap, Recommendation
│   └── audit.py                 # AuditTrail, ProvenanceChain, Explanation
├── modules/                     # Agent implementations
│   ├── ingest/
│   │   ├── parser.py            # Document ingestion logic
│   │   └── validator.py         # Format validation
│   ├── nlu/
│   │   ├── ner_engine.py        # Named entity recognition
│   │   ├── normalizer.py        # Entity normalization
│   │   └── embeddings.py        # Clinical embedding generation
│   ├── coding/
│   │   ├── rag_retriever.py     # FAISS-based code retrieval
│   │   ├── ranker.py            # Code re-ranking logic
│   │   └── generator.py         # Generative refinement
│   ├── cdi/
│   │   ├── kg_agent.py          # Knowledge graph reasoning
│   │   ├── gap_detector.py      # Documentation gap analysis
│   │   └── recommendation.py    # CDI suggestion engine
│   └── explainability/
│       ├── evidence_linker.py   # Map codes to text spans
│       ├── audit_builder.py     # Build audit trails
│       └── visualizer.py        # Attention visualization
├── evaluation/                  # Evaluation framework
│   ├── metrics/
│   │   ├── ner_metrics.py       # NER-specific metrics
│   │   ├── coding_metrics.py    # Coding accuracy metrics
│   │   └── cdi_metrics.py       # CDI quality metrics
│   ├── eval_runner.py           # Evaluation orchestration
│   └── benchmarks/              # Reference datasets
├── knowledge_graph/             # KG management
│   ├── schema.py                # Node/edge type definitions
│   ├── builder.py               # KG construction from ICD data
│   ├── querier.py               # Graph traversal queries
│   └── ontology.py              # Ontology mapping (SNOMED, LOINC)
├── rag/                         # RAG infrastructure
│   ├── index_builder.py         # FAISS index creation
│   ├── embedder.py              # Embedding model wrapper
│   └── retriever.py             # Retrieval interface
├── pipeline.py                  # Main orchestrator
└── model_manager.py             # Centralized model loading

ui/                              # User interface
├── app.py                       # Main Streamlit app
├── pages/
│   ├── dashboard.py             # Main analytics dashboard
│   ├── kg_viz.py                # Knowledge graph visualization
│   ├── qa_bot.py                # Interactive QA interface
│   └── audit_view.py            # Audit trail explorer
└── components/
    ├── charts.py                # Reusable chart components
    └── widgets.py               # Custom UI widgets

data/                            # Data assets
├── cms_icd10/                   # CMS ICD-10-CM FY2025 tabular
├── faiss_indices/               # Pre-built FAISS indices
└── kg_export/                   # Knowledge graph serialization

tests/                           # Test suite
├── unit/
│   ├── test_ner.py
│   ├── test_coding.py
│   └── test_cdi.py
├── integration/
│   └── test_pipeline.py
└── fixtures/                    # Test data
```

### Structure Rationale

- **models/**: Centralized Pydantic schemas enforce data contracts between agents, enabling type-safe inter-agent communication and automatic validation. This follows the "Parse, don't validate" principle common in modern Python architectures.

- **modules/**: Each agent is a self-contained module with clear input/output contracts (Pydantic models). This separation of concerns allows independent development, testing, and replacement of agents without affecting the pipeline.

- **evaluation/**: Co-located evaluation modules mirror the agent structure, making it easy to run per-agent metrics during development and detect performance drift in production.

- **knowledge_graph/**: Isolated KG infrastructure allows switching between NetworkX (development), Neo4j (production), or other graph databases without touching agent code.

- **rag/**: Encapsulates retrieval infrastructure, abstracting FAISS implementation details from coding agents. Enables swapping vector databases (Pinecone, Weaviate) or embedding models.

- **ui/**: Complete separation of presentation from business logic. Streamlit's multi-page architecture maps naturally to different stakeholder views (clinicians, coders, auditors).

## Architectural Patterns

### Pattern 1: Multi-Agent Sequential Pipeline

**What:** Specialized agents process data in sequence, each with a focused responsibility. Output of one agent becomes input to the next, connected via typed Pydantic models.

**When to use:** When tasks have clear dependencies (e.g., NER must precede coding, coding must precede CDI analysis) and each stage requires different domain expertise or models.

**Trade-offs:**
- **Pros:** Clear separation of concerns; easy to debug per-stage; allows independent optimization; straightforward error isolation
- **Cons:** Latency accumulates across stages; errors propagate; challenging to parallelize

**Example:**
```python
from cliniq.models.document import ClinicalDocument
from cliniq.models.entities import NLUResult
from cliniq.models.coding import CodingResult
from cliniq.models.cdi import CDIReport

class PipelineOrchestrator:
    def __init__(self, ingest, nlu, coding, cdi):
        self.ingest = ingest
        self.nlu = nlu
        self.coding = coding
        self.cdi = cdi

    def process(self, raw_text: str) -> CDIReport:
        # Stage 1: Ingest
        doc: ClinicalDocument = self.ingest.parse(raw_text)

        # Stage 2: NLU/NER
        nlu_result: NLUResult = self.nlu.extract_entities(doc)

        # Stage 3: RAG Coding
        coding_result: CodingResult = self.coding.assign_codes(nlu_result)

        # Stage 4: CDI Analysis
        cdi_report: CDIReport = self.cdi.analyze(coding_result)

        return cdi_report
```

### Pattern 2: Paired Agent-Evaluator Architecture

**What:** Each processing agent has a paired evaluation module that computes metrics, detects anomalies, and flags low-confidence outputs in real-time.

**When to use:** When you need continuous quality monitoring, explainability, or want to catch model drift during inference. Essential for clinical applications requiring auditability.

**Trade-offs:**
- **Pros:** Built-in quality gates; early error detection; continuous performance monitoring; supports active learning
- **Cons:** Increased compute overhead (~20-30%); requires ground truth or heuristic baselines; evaluation logic complexity

**Example:**
```python
from cliniq.evaluation.metrics import NERMetrics
from cliniq.models.entities import NLUResult

class NERAgent:
    def __init__(self, model, evaluator):
        self.model = model
        self.evaluator = evaluator

    def extract_entities(self, doc: ClinicalDocument) -> NLUResult:
        # Process with NER model
        result = self.model.predict(doc.text)

        # Evaluate quality in real-time
        eval_metrics = self.evaluator.compute(result)

        # Attach confidence and flag if below threshold
        result.quality_score = eval_metrics.f1
        result.needs_review = eval_metrics.f1 < 0.85

        return result
```

### Pattern 3: Hybrid RAG with Knowledge Graph Grounding

**What:** Combines dense vector retrieval (FAISS) for semantic similarity with structured graph traversal (NetworkX) for ontology-based reasoning. Retrieval results are re-ranked using graph relationships.

**When to use:** When semantic similarity alone produces false positives or you need to enforce medical ontology constraints (e.g., "diabetes codes must have documentation requirements from SNOMED CT diabetes concepts").

**Trade-offs:**
- **Pros:** Reduces hallucinations by ~60% (per research); enforces domain constraints; improves interpretability via graph paths
- **Cons:** More complex architecture; requires ontology maintenance; graph queries add latency (~50-100ms)

**Example:**
```python
from cliniq.rag.retriever import FAISSRetriever
from cliniq.knowledge_graph.querier import KGQuerier

class HybridCodingAgent:
    def __init__(self, faiss_retriever: FAISSRetriever, kg_querier: KGQuerier):
        self.retriever = faiss_retriever
        self.kg = kg_querier

    def assign_codes(self, nlu_result: NLUResult) -> CodingResult:
        # Stage 1: Dense retrieval
        candidate_codes = self.retriever.search(
            query=nlu_result.primary_diagnosis,
            top_k=50
        )

        # Stage 2: KG-based re-ranking
        for code in candidate_codes:
            # Check if code is semantically valid given extracted entities
            graph_evidence = self.kg.find_paths(
                source=code.icd_code,
                targets=nlu_result.clinical_concepts
            )
            code.graph_score = graph_evidence.path_strength

        # Combine scores: 0.6 * semantic + 0.4 * graph
        final_codes = self._hybrid_rank(candidate_codes)

        return CodingResult(codes=final_codes[:10])
```

### Pattern 4: Centralized Model Management with Lazy Loading

**What:** Single ModelManager class handles all model loading, caching, and version control. Models are loaded lazily (on first use) and cached in memory with HuggingFace's native caching.

**When to use:** Always. Prevents redundant model loading, manages GPU memory efficiently, and provides a single point for model versioning and A/B testing.

**Trade-offs:**
- **Pros:** Reduces memory footprint; faster cold starts; easy model swapping; centralized configuration
- **Cons:** Adds abstraction layer; first inference has loading latency; singleton pattern can complicate testing

**Example:**
```python
from functools import lru_cache
from transformers import AutoModel, AutoTokenizer

class ModelManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._models = {}
        return cls._instance

    @lru_cache(maxsize=5)
    def get_ner_model(self, model_name: str = "emilyalsentzer/Bio_ClinicalBERT"):
        if model_name not in self._models:
            self._models[model_name] = {
                'model': AutoModel.from_pretrained(model_name),
                'tokenizer': AutoTokenizer.from_pretrained(model_name)
            }
        return self._models[model_name]

    def clear_cache(self):
        """Clear all loaded models (e.g., for memory management)"""
        self._models.clear()
```

### Pattern 5: Explainability-First Audit Trail

**What:** Every processing step logs provenance information (which model, which code version, which input features influenced the decision) to an audit trail that can be reconstructed later for compliance or debugging.

**When to use:** Required for clinical production systems. Essential for FDA compliance, HIPAA audits, and appeals processes for denied claims.

**Trade-offs:**
- **Pros:** Full traceability; supports appeals; enables retrospective analysis; meets regulatory requirements
- **Cons:** Storage overhead (~20% more data); logging latency; audit trail management complexity

**Example:**
```python
from cliniq.models.audit import AuditTrail, ProvenanceEntry
from datetime import datetime

class AuditableAgent:
    def __init__(self, agent_id: str, version: str):
        self.agent_id = agent_id
        self.version = version

    def process_with_audit(self, input_data, audit_trail: AuditTrail):
        start_time = datetime.now()

        # Perform processing
        result = self._process(input_data)

        # Log provenance
        audit_trail.add_entry(ProvenanceEntry(
            agent_id=self.agent_id,
            agent_version=self.version,
            input_hash=hash(str(input_data)),
            output_hash=hash(str(result)),
            processing_time=(datetime.now() - start_time).total_seconds(),
            model_config=self._get_model_config(),
            evidence_spans=self._extract_evidence_spans(input_data, result)
        ))

        return result, audit_trail
```

## Data Flow

### Request Flow

```
Raw Clinical Note (text)
    ↓
[Ingest Module] → ClinicalDocument (Pydantic)
    ↓
[NLU/NER Module] → NLUResult (entities, concepts, qualifiers)
    ↓
[Embedder] → Vector representation
    ↓
[FAISS Index] → Top-K candidate ICD codes (semantic)
    ↓
[KG Querier] → Ontology constraints + graph paths
    ↓
[Hybrid Ranker] → CodingResult (final codes + evidence)
    ↓
[CDI KG Agent] → Documentation gap analysis
    ↓
[CDI Generator] → CDIReport (gaps, recommendations, evidence)
    ↓
[Audit Builder] → AuditTrail (provenance chain)
    ↓
[Streamlit UI] → Visual presentation
```

### Agent Communication Pattern

```
Agent A                          Agent B
   |                                |
   |-- ClinicalDocument (Pydantic)--|
   |                                |
   |                             [Process]
   |                                |
   |-- NLUResult (Pydantic) --------|
   |                                |
```

**Key Properties:**
- **Type-safe:** Pydantic validates all inter-agent data
- **Immutable:** Output models are frozen (Pydantic `frozen=True`)
- **Serializable:** All models support `.dict()`, `.json()` for logging/storage
- **Versioned:** Models include schema version for backward compatibility

### Evaluation Flow

```
Processing Agent --> Output --> Evaluation Module --> Metrics
                       |                                  |
                       |                                  v
                       +------> Audit Trail <------- Quality Flags
```

**Evaluation runs in parallel with normal processing:**
1. Agent produces output
2. Output is logged to audit trail
3. Evaluator computes metrics (precision, recall, confidence scores)
4. Quality flags attached to output
5. Low-confidence outputs marked for human review

### Key Data Flows

1. **Cold Start Flow (First Run):**
   - Load ICD-10-CM tabular data (CMS FY2025)
   - Build FAISS index from code descriptions (~70k codes)
   - Construct NetworkX knowledge graph (codes + documentation requirements)
   - Download/cache HuggingFace models (NER, embeddings, LLM)
   - **Optimization:** Pre-build indices offline; store in `data/faiss_indices/`

2. **Inference Flow (Production):**
   - Parse incoming clinical note
   - Extract entities (NER) in ~200-500ms
   - Retrieve candidate codes (FAISS) in ~50-100ms
   - Re-rank with KG (NetworkX) in ~100-200ms
   - Generate CDI report in ~300-500ms
   - **Total latency target:** < 2 seconds per document

3. **Evaluation Flow (Continuous):**
   - Each agent outputs metrics to evaluation store
   - Dashboard polls metrics every 60 seconds
   - Drift detection alerts when F1 drops >5% from baseline
   - Human reviewers examine flagged cases

## Scaling Considerations

| Concern | At 100 docs/day | At 10K docs/day | At 1M docs/day |
|---------|-----------------|-----------------|----------------|
| **Inference** | Single Python process; local FAISS index; NetworkX in-memory | Multi-worker with queue (Celery/RQ); Redis for shared state; persist FAISS to disk | Kubernetes cluster; FAISS sharding across pods; migrate to Neo4j or TigerGraph; distributed queue |
| **Model Loading** | Load once at startup; HuggingFace cache on local disk | Pre-warmed model cache; shared model server (Triton/TorchServe) | Model serving infrastructure with auto-scaling; quantization (INT8) for faster inference |
| **Knowledge Graph** | NetworkX in-memory (1-2GB RAM for ~70k codes) | Persist to disk; lazy load subgraphs | Neo4j or TigerGraph with indexing; graph partitioning by specialty |
| **Storage** | Local SQLite for audit trails | PostgreSQL with jsonb columns | Distributed database (PostgreSQL shards or Cassandra); object storage (S3) for document blobs |
| **Evaluation** | Real-time per-document evaluation | Sample-based evaluation (10% of traffic); async metrics computation | Offline batch evaluation; streaming metrics pipeline (Kafka + Flink) |

### Scaling Priorities

1. **First bottleneck:** Model inference latency. Each document requires multiple transformer forward passes (NER, embeddings, optional LLM refinement).
   - **Solution:** Batch inference; quantization (8-bit models); distillation to smaller models; GPU inference for high throughput

2. **Second bottleneck:** FAISS index size grows linearly with code count. At scale (millions of custom codes or multi-language), memory becomes limiting.
   - **Solution:** Index sharding by medical specialty; Product Quantization (PQ) for compression; migrate to distributed vector DB (Pinecone, Weaviate)

3. **Third bottleneck:** Knowledge graph query latency. Complex graph traversals (e.g., "find all documentation requirements for all codes in this note") become slow as graph size increases.
   - **Solution:** Pre-compute common paths; cache graph queries; migrate to dedicated graph database with query optimization

## Anti-Patterns

### Anti-Pattern 1: Monolithic Pipeline Class

**What people do:** Build a single `Pipeline` class with all logic (parsing, NER, coding, CDI) in one file with tightly coupled methods.

**Why it's wrong:** Impossible to test individual stages; can't swap models without rewriting the entire pipeline; error in one stage crashes everything; no clear boundaries for evaluation.

**Do this instead:** Separate agents with clear interfaces (Pydantic input/output). Use composition in the orchestrator:
```python
# Bad: Monolithic
class Pipeline:
    def process(self, text):
        parsed = self._parse(text)  # 500 lines
        entities = self._ner(parsed)  # 800 lines
        codes = self._code(entities)  # 600 lines
        cdi = self._analyze(codes)  # 400 lines
        return cdi

# Good: Modular
class PipelineOrchestrator:
    def __init__(self, ingest_agent, ner_agent, coding_agent, cdi_agent):
        self.ingest = ingest_agent
        self.ner = ner_agent
        self.coding = coding_agent
        self.cdi = cdi_agent

    def process(self, text: str) -> CDIReport:
        doc = self.ingest.parse(text)
        nlu = self.ner.extract(doc)
        coding = self.coding.assign(nlu)
        return self.cdi.analyze(coding)
```

### Anti-Pattern 2: Embedding Everything in the FAISS Index

**What people do:** Embed ICD code descriptions, clinical notes, documentation requirements, and historical cases all into the same FAISS index without structure.

**Why it's wrong:** Retrieval mixes semantically similar but structurally different content (code descriptions vs. documentation requirements); no way to enforce ontology constraints; results are noisy and hard to explain.

**Do this instead:** Use multiple indices with clear purposes + knowledge graph for structure:
```python
# Bad: Single mixed index
faiss_index = FAISS.from_texts([
    "ICD-10: E11.9 Type 2 diabetes",
    "Documentation requires: HbA1c value",
    "Similar case: Patient with diabetes and hypertension"
])

# Good: Separate indices + graph
icd_index = FAISS.from_texts(icd_descriptions)  # Code retrieval
doc_req_index = FAISS.from_texts(doc_requirements)  # CDI gaps
knowledge_graph = build_graph(icd_codes, snomed_concepts)  # Structure
```

### Anti-Pattern 3: No Confidence Thresholding

**What people do:** Return all predictions without confidence scores or quality flags; assume all outputs are production-ready.

**Why it's wrong:** Clinical systems must know when they're uncertain; low-confidence predictions cause downstream errors; no mechanism for human-in-the-loop review; auditors can't distinguish high vs. low confidence codes.

**Do this instead:** Every agent output includes confidence scores and quality flags:
```python
from cliniq.models.coding import CodingResult, ICDCode

class CodingAgent:
    CONFIDENCE_THRESHOLD = 0.75

    def assign_codes(self, nlu_result: NLUResult) -> CodingResult:
        codes = self._retrieve_and_rank(nlu_result)

        # Attach confidence and flag low-confidence codes
        flagged_codes = []
        for code in codes:
            code.needs_review = code.confidence < self.CONFIDENCE_THRESHOLD
            if code.needs_review:
                flagged_codes.append(code)

        return CodingResult(
            codes=codes,
            overall_confidence=sum(c.confidence for c in codes) / len(codes),
            needs_human_review=len(flagged_codes) > 0,
            review_reason="Low confidence codes detected"
        )
```

### Anti-Pattern 4: Skipping Evaluation During Development

**What people do:** Build the entire pipeline first, then add evaluation as an afterthought; test only on a handful of examples manually.

**Why it's wrong:** No way to detect regressions during development; can't objectively compare model changes; unclear which agent is the bottleneck; production issues are discovered too late.

**Do this instead:** Paired agent-evaluator architecture from day one:
```python
# Every agent has a paired evaluator
ner_agent = NERAgent(model=ner_model)
ner_eval = NEREvaluator(metrics=["precision", "recall", "f1"])

# Run evaluation during development
result = ner_agent.extract(doc)
metrics = ner_eval.compute(result, ground_truth)

# Log metrics for tracking
mlflow.log_metrics({"ner_f1": metrics.f1})
```

### Anti-Pattern 5: Loading Models Repeatedly

**What people do:** Load transformer models inside agent methods; reload on every request; multiple agents independently load the same model.

**Why it's wrong:** Massive latency overhead (5-10 seconds per load); memory bloat (multiple copies of same model); OOM errors on GPU; cold start problems.

**Do this instead:** Centralized model management with caching:
```python
# Bad: Load on every request
class NERAgent:
    def extract(self, doc):
        model = AutoModel.from_pretrained("Bio_ClinicalBERT")  # 10s latency
        return model.predict(doc.text)

# Good: Centralized with caching
model_manager = ModelManager()  # Singleton

class NERAgent:
    def __init__(self, model_manager):
        self.model_manager = model_manager

    def extract(self, doc):
        model = self.model_manager.get_ner_model()  # Cached after first load
        return model.predict(doc.text)
```

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| **CMS ICD-10-CM Updates** | Annual batch import; download FY2025 tabular data; rebuild FAISS index; versioned indices (e.g., `icd_fy2025_v1.faiss`) | Check cms.gov/medicare/coordination-benefits-recovery-overview/icd-code-lists quarterly for updates |
| **SNOMED CT / LOINC** | Ontology mapping layer; maintain bidirectional mappings (ICD ↔ SNOMED); use UMLS API or local database | Consider using NLM's UMLS API or download local terminology files |
| **HuggingFace Hub** | Model download during setup; transformers library handles caching automatically; specify `cache_dir` for custom location | Set `TRANSFORMERS_CACHE` environment variable for shared cache |
| **Clinical Data Sources (EHR)** | HL7 FHIR API or direct HL7v2 parsing; validate against FHIR profiles; handle various note formats (HL7 MDM, CDA) | Use `fhir.resources` library for FHIR parsing; `hl7apy` for HL7v2 |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| **Orchestrator ↔ Agents** | Direct method calls with Pydantic models; synchronous by default; async for I/O-bound operations | Consider async/await for parallel agent execution in future versions |
| **Agents ↔ Evaluators** | Agents call evaluators after processing; evaluators return metrics; metrics logged to audit trail | Evaluators are stateless; can be parallelized |
| **Agents ↔ Model Manager** | Lazy model retrieval; agents request models by name; model manager handles loading/caching | Model manager uses singleton pattern; thread-safe caching |
| **Pipeline ↔ FAISS Index** | Read-only access during inference; index loaded at startup; in-memory for speed | For large indices (>10GB), consider memory-mapped FAISS |
| **Pipeline ↔ Knowledge Graph** | Read-only graph queries via NetworkX API; complex queries may be slow (>100ms) | Pre-compute common paths; cache query results; consider Neo4j for production scale |
| **UI ↔ Pipeline** | Streamlit calls pipeline via direct Python import; session state for caching; async execution for long-running operations | Use `st.cache_resource` for pipeline singleton; `st.cache_data` for results |

## Build Order and Dependencies

### Phase 1: Core Data Models and Utilities (No dependencies)
Build these first; all other components depend on them.
1. Pydantic models (`cliniq/models/`)
2. Model manager (`cliniq/model_manager.py`)
3. FAISS index builder (`cliniq/rag/index_builder.py`)
4. Knowledge graph schema and builder (`cliniq/knowledge_graph/`)

### Phase 2: Individual Agents (Depends on Phase 1)
Can be built in parallel; each has independent evaluation.
1. Ingest module (`cliniq/modules/ingest/`)
2. NER/NLU module (`cliniq/modules/nlu/`)
3. RAG coding module (`cliniq/modules/coding/`)
4. CDI KG agent (`cliniq/modules/cdi/`)
5. Explainability module (`cliniq/modules/explainability/`)

### Phase 3: Pipeline Orchestration (Depends on Phases 1-2)
Integrates all agents into end-to-end workflow.
1. Pipeline orchestrator (`cliniq/pipeline.py`)
2. Integration tests (`tests/integration/`)

### Phase 4: User Interface (Depends on Phases 1-3)
Can iterate independently once pipeline API is stable.
1. Streamlit dashboard (`ui/app.py`, `ui/pages/`)
2. Visualization components (`ui/components/`)

### Phase 5: Production Hardening (Depends on all previous phases)
Add monitoring, logging, and deployment infrastructure.
1. Production logging
2. Monitoring and alerting
3. Containerization (Docker)
4. CI/CD pipelines

## Sources

**Clinical NLP + RAG + KG Architecture:**
- [A survey on retrieval-augmentation generation (RAG) models for healthcare applications](https://link.springer.com/article/10.1007/s00521-025-11666-9)
- [Scaling Biomedical Knowledge Graph Retrieval for Interpretable](https://www.medrxiv.org/content/10.64898/2026.01.12.26343957v1.full.pdf)
- [From Clinical Text to Knowledge Graphs with John Snow Labs Healthcare NLP](https://www.johnsnowlabs.com/from-clinical-text-to-knowledge-graphs-with-john-snow-labs-healthcare-nlp/)
- [Research on the construction and application of RAG model based on knowledge graph](https://www.nature.com/articles/s41598-025-21222-z)
- [Real-time clinical analytics at scale: a platform built on LLM-powered knowledge graphs](https://pmc.ncbi.nlm.nih.gov/articles/PMC12772639/)

**Multi-Agent Systems & Medical Coding:**
- [Google's Eight Essential Multi-Agent Design Patterns](https://www.infoq.com/news/2026/01/multi-agent-design-patterns/)
- [Code Like Humans: A Multi-Agent Solution for Medical Coding](https://arxiv.org/pdf/2509.05378)
- [MedDCR: Learning to Design Agentic Workflows for Medical Coding](https://arxiv.org/pdf/2511.13361)
- [Multi-Agent Architecture Guide (March 2026)](https://www.openlayer.com/blog/post/multi-agent-system-architecture-guide)
- [White Paper: Agentic Multi-Agent Orchestration (2026)](https://medium.com/@dynamicsfrontier/white-paper-agentic-multi-agent-orchestration-2026-f86401afb6dc)

**Healthcare Data Pipelines:**
- [Why we need to transform our healthcare data architecture](https://www.weforum.org/stories/2026/01/ai-healthcare-data-architecture/)
- [A scalable and transparent data pipeline for AI-enabled health data ecosystems](https://pmc.ncbi.nlm.nih.gov/articles/PMC11321077/)
- [Task-Based Clinical NLP: Unlocking Insights with One-Liner Pipelines](https://www.johnsnowlabs.com/task-based-clinical-nlp-unlocking-insights-with-one-liner-pipelines/)

**Clinical NER Best Practices:**
- [Named Entity Recognition: Master Enterprise-Scale Deep Learning for NLP in 2026](https://muralimarimekala.com/2026/02/09/named-entity-recognition-deep-learning-nlp-enterprise/)
- [Exploring Named Entity Recognition Potential for Radiology, Pathology, and Progress Notes](https://ai.jmir.org/2025/1/e59251/)
- [Enhancing Clinical NER via Fine-Tuned BERT and Dictionary-Infused RAG](https://www.mdpi.com/2079-9292/14/18/3676)

**FAISS & Vector Retrieval for ICD-10:**
- [Retrieval-Augmented Generation for ICD-10 Coding in German Clinical Texts](https://ebooks.iospress.nl/doi/10.3233/SHTI251397)
- [MedCodER: A Generative AI Assistant for Medical Coding](https://arxiv.org/html/2409.15368v1)
- [ICD-10 Code Representation in Embedding Vector Spaces](https://intuitionlabs.ai/articles/icd-10-code-embedding-vector-spaces)

**Model Orchestration & Evaluation:**
- [Task-Based Clinical NLP: One-Liner Pipelines](https://www.johnsnowlabs.com/task-based-clinical-nlp-unlocking-insights-with-one-liner-pipelines/)
- [A roadmap to implementing machine learning in healthcare](https://pmc.ncbi.nlm.nih.gov/articles/PMC11788154/)

**Knowledge Graphs in Healthcare:**
- [A Review on Knowledge Graphs for Healthcare: Resources, Applications, and Promises](https://arxiv.org/html/2306.04802v4)
- [Patient-centric knowledge graphs: methods, challenges, and applications](https://pmc.ncbi.nlm.nih.gov/articles/PMC11558794/)
- [Ontology-grounded knowledge graphs for mitigating hallucinations in LLMs](https://pubmed.ncbi.nlm.nih.gov/41610815/)
- [Clinical Knowledge Graph Construction via Retrieval-Augmented Generation](https://arxiv.org/html/2601.01844v1)

**Pydantic for Clinical Data:**
- [Validating Healthcare Data: Pydantic Models vs. LLMs](https://www.linkedin.com/pulse/validating-healthcare-data-pydantic-models-vs-large-llms-planchart-lcc0c)
- [Fhircraft: FHIR-to-Pydantic Transformation](https://pypi.org/project/fhircraft/)

**Explainability & Audit Trails:**
- [Transparent AI for Medical Coding: Why Black Box Tools Fail](https://blog.nym.health/transparent-ai-for-medical-coding)
- [How AI Powers Explainable and Auditable Medical Coding](https://blog.nym.health/explainable-ai-in-healthcare)
- [AI and LLM Data Provenance and Audit Trails for Healthcare Technology](https://www.onhealthcare.tech/p/ai-and-llm-data-provenance-and-audit)
- [Transparency of AI in Healthcare as a Multilayered System of Accountabilities](https://pmc.ncbi.nlm.nih.gov/articles/PMC9189302/)

**Streamlit for Healthcare:**
- [Improving healthcare management with Streamlit](https://blog.streamlit.io/improving-healthcare-management-with-streamlit/)
- [Medical reports analysis dashboard using Amazon Bedrock, LangChain, and Streamlit](https://aws.amazon.com/blogs/machine-learning/medical-reports-analysis-dashboard-using-amazon-bedrock-langchain-and-streamlit/)

**ML Pipeline Architecture:**
- [What Is an ML Pipeline? Stages, Architecture & Best Practices](https://www.clarifai.com/blog/ml-pipeline)
- [How to Build ML Pipeline Architecture](https://oneuptime.com/blog/post/2026-01-30-ml-pipeline-architecture/view)
- [Enhance ML development with modular architecture using Amazon SageMaker](https://aws.amazon.com/blogs/machine-learning/enhance-your-machine-learning-development-by-using-a-modular-architecture-with-amazon-sagemaker-projects/)

---
*Architecture research for: Clinical NLP + RAG + Knowledge Graph CDI Intelligence Platform*
*Researched: 2026-03-18*
*Confidence: MEDIUM-HIGH (web search + official documentation; clinical domain patterns verified across multiple 2025-2026 sources)*
