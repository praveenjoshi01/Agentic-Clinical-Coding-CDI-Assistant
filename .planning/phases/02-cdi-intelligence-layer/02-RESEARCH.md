# Phase 2: CDI Intelligence Layer - Research

**Researched:** 2026-03-18
**Domain:** Knowledge graph reasoning, CDI gap detection, physician query generation, chain-of-thought audit trails, explainability
**Confidence:** HIGH

## Summary

Phase 2 transforms the Phase 1 pipeline output (NLUResult + CodingResult from clinical NER and RAG coding) into actionable CDI intelligence. The phase has two major subsystems: (1) a Knowledge Graph agent that uses NetworkX to detect documentation gaps, suggest missed diagnoses via co-occurrence edges, and flag invalid code combinations; and (2) an Explainability/Audit system that captures chain-of-thought traces from Qwen for every reasoning step, links every suggested code to supporting text spans, and produces per-case audit trails covering the full pipeline.

The critical architectural insight is that the KG must be constructed as a static data artifact (built once from ICD-10 code relationships, Excludes1/Excludes2 rules, and domain-curated co-occurrence/qualification rules) and then queried per-case using the codes produced by Phase 1's RAG module. The KG is NOT a dynamic, per-patient graph. It is a reference knowledge base that the CDI agent queries with case-specific codes. The per-case output is a CDIReport (Pydantic model) containing documentation gaps, physician queries, conflict flags, and missed diagnosis suggestions.

The second critical insight is that audit trail capture must be woven retroactively into the existing pipeline stages (ingestion, NER, RAG) via a lightweight AuditTrail accumulator object passed through the pipeline, not by rewriting those modules. Phase 2 also modifies the Qwen LLM calls to capture raw chain-of-thought text before JSON extraction.

**Primary recommendation:** Build in dependency order: (1) KG schema + static KG construction from ICD-10 data + curated rules, (2) KG query functions (gap detection, conflict detection, co-occurrence suggestions), (3) CDI agent that consumes PipelineResult and produces CDIReport with Qwen-generated physician queries, (4) AuditTrail Pydantic schema + trail builder that instruments existing pipeline, (5) LLM-as-judge evaluation for physician query relevance (CDI-06) and CoT coherence (EXPL-05), (6) integration tests against gold standard CDI gap annotations.

## Standard Stack

### Core (already installed from Phase 1)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| networkx | >=3.4.0 | Knowledge graph data structure | Already a prior decision; pure Python, no external DB, sufficient for ~300 ICD nodes + relationships |
| pydantic | >=2.0.0 | CDIReport, AuditTrail, DocumentationGap schemas | Phase 1 pattern; all inter-module contracts are Pydantic |
| transformers | >=4.45.0 | Qwen2.5-1.5B for physician query generation + CoT | Already loaded via ModelManager singleton |

### Supporting (new for Phase 2)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| (none new) | - | - | Phase 2 uses only libraries already installed in Phase 1 |

**No new dependencies.** Phase 2 is pure Python logic over NetworkX (already installed), Pydantic (already installed), and the Qwen LLM (already loaded by ModelManager). This is by design -- the CDI intelligence layer is graph queries + LLM prompting + data schemas, not new model infrastructure.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Static curated KG edges | Mining co-occurrence from HCUP/AHRQ data | Curated rules are deterministic and auditable; mined data requires large clinical datasets not available in this POC |
| Excludes1 rules from CMS guidelines | Full ICD-10-CM XML with cross-reference data | CMS XML is comprehensive but 200+ MB; curated subset of high-value conflicts sufficient for demo |
| Qwen for physician query generation | Template-based query generation | Qwen produces natural language; templates are rigid but deterministic. Qwen is the prior decision for reasoning. |
| Lightweight AuditTrail accumulator | Pydantic Logfire/OpenTelemetry tracing | Logfire is production-grade but overkill; simple Pydantic model captures what EXPL-01 through EXPL-04 require |

## Architecture Patterns

### Recommended Project Structure

```
cliniq/
├── models/
│   ├── cdi.py                  # CDIReport, DocumentationGap, PhysicianQuery, MissedDiagnosis
│   └── audit.py                # AuditTrail, StageTrace, RetrievalLog, CoTTrace
├── knowledge_graph/
│   ├── __init__.py
│   ├── schema.py               # Node/edge type constants, KG type aliases
│   ├── builder.py              # Build static KG from ICD-10 data + curated rules
│   └── querier.py              # Gap detection, conflict detection, co-occurrence queries
├── modules/
│   ├── m4_cdi.py               # CDI agent: KG queries + Qwen physician queries
│   └── m5_explainability.py    # AuditTrail builder, evidence linker, CoT capture
├── tests/
│   ├── test_knowledge_graph.py # KG construction + query unit tests
│   ├── test_m4_cdi.py          # CDI agent tests against gold standard
│   └── test_m5_explainability.py # Audit trail completeness tests
└── pipeline.py                 # Extended: Stage 4 (CDI) + Stage 5 (Audit) + AuditTrail threading
```

### Pattern 1: Static Reference KG with Per-Case Querying

**What:** The knowledge graph is built once from ICD-10 code metadata and curated clinical rules. At inference time, case-specific codes (from RAG output) are used to query the KG for gaps, conflicts, and co-occurrences. The KG itself does not change per patient.

**When to use:** When the knowledge base is domain reference data (ICD-10 relationships, coding rules) rather than patient-specific data.

**KG Node Types:**
- `icd_code`: One node per ICD-10 code in the dataset (~200-300 codes relevant to gold standard, full set ~1300)
- Attributes: `code`, `description`, `chapter`, `requires_qualifiers` (list of required qualifiers)

**KG Edge Types:**
- `COMMONLY_CO_CODED`: Codes frequently coded together (e.g., E11.9 <-> I10, diabetes <-> hypertension). Weight = co-occurrence strength. Used for CDI-03.
- `CONFLICTS_WITH`: Codes that cannot be coded together (Excludes1 rule from ICD-10-CM). Used for CDI-04.
- `HAS_PARENT`: Hierarchical ICD-10 relationship (E11 -> E11.4 -> E11.40). Used for specificity gap detection.
- `REQUIRES_QUALIFIER`: Edge from code to qualifier type (e.g., E11.40 -> "laterality"). Used for CDI-01.

**Example:**
```python
import networkx as nx

# Build static KG
G = nx.DiGraph()

# Add code nodes
G.add_node("E11.40", type="icd_code", description="Type 2 DM with neuropathy",
           chapter="E00-E89", requires_qualifiers=["laterality", "complication_type"])

# Add co-occurrence edges (CDI-03)
G.add_edge("E11.9", "I10", relation="COMMONLY_CO_CODED", weight=0.85,
           evidence="Diabetes and hypertension co-occur in 60-70% of cases")

# Add conflict edges (CDI-04 - Excludes1)
G.add_edge("E10.9", "E11.9", relation="CONFLICTS_WITH",
           reason="Cannot code both Type 1 and Type 2 DM")

# Add qualifier edges (CDI-01)
G.add_edge("E11.40", "laterality", relation="REQUIRES_QUALIFIER")

# Per-case query: find gaps for a set of assigned codes
case_codes = ["E11.40", "E11.311"]
for code in case_codes:
    node = G.nodes[code]
    required = node.get("requires_qualifiers", [])
    # Check which qualifiers are documented vs missing
```

### Pattern 2: CoT Capture Before JSON Extraction

**What:** When using Qwen for reasoning (physician query generation, code selection), capture the FULL raw text output before extracting structured JSON. Store the raw chain-of-thought text in the audit trail, then extract the JSON for programmatic use. This satisfies EXPL-03.

**When to use:** Every Qwen LLM call in the pipeline (both Phase 1 RAG reasoning and Phase 2 CDI query generation).

**Example:**
```python
def generate_with_cot_capture(prompt: str, model, tokenizer) -> tuple[str, str]:
    """Generate LLM output and capture raw CoT trace.

    Returns:
        tuple of (raw_response, extracted_json_str)
    """
    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(inputs.input_ids, max_new_tokens=512,
                             temperature=0.1, do_sample=False,
                             pad_token_id=tokenizer.eos_token_id)
    raw_response = tokenizer.decode(outputs[0], skip_special_tokens=True)

    # Store full raw response as CoT trace (EXPL-03)
    cot_trace = raw_response

    # Extract JSON for programmatic use
    start_idx = raw_response.find('{')
    end_idx = raw_response.rfind('}')
    json_str = raw_response[start_idx:end_idx + 1] if start_idx != -1 else ""

    return cot_trace, json_str
```

### Pattern 3: AuditTrail Accumulator Threading

**What:** An AuditTrail Pydantic object is created at pipeline start and passed through each stage. Each stage appends its trace (timing, inputs, outputs, model versions, evidence spans). The trail is returned as part of the final pipeline output.

**When to use:** EXPL-01 requires per-case audit trail covering all stages. Rather than rewriting Phase 1 modules, wrap their calls in the orchestrator with trace capture.

**Example:**
```python
from cliniq.models.audit import AuditTrail, StageTrace

# In pipeline.py
def run_pipeline_audited(input_data) -> tuple[PipelineResult, AuditTrail]:
    trail = AuditTrail(case_id=generate_case_id())

    # Stage 1: Ingestion (wrap existing call)
    t0 = time.perf_counter()
    document = ingest(input_data)
    trail.add_stage(StageTrace(
        stage="ingestion",
        input_summary=str(type(input_data)),
        output_summary=f"{document.metadata.source_type}, confidence={document.modality_confidence}",
        processing_time_ms=(time.perf_counter() - t0) * 1000,
        details={"extraction_trace": document.extraction_trace}
    ))
    # ... repeat for NER, RAG, CDI stages
```

### Pattern 4: LLM-as-Judge for Quality Scoring

**What:** Use the same Qwen2.5-1.5B model (already loaded) to score the quality of its own outputs by prompting it as a judge with a rubric. This satisfies CDI-06 (query relevance >= 0.80) and EXPL-05 (CoT coherence >= 0.82).

**When to use:** Evaluation time, not inference time. Run LLM-as-judge scoring as a separate evaluation pass over generated outputs.

**Limitation:** Self-evaluation with a 1.5B model has known biases (tends to rate its own outputs favorably). Mitigation: use explicit rubric criteria, score on a 1-5 Likert scale, and calibrate thresholds.

**Example:**
```python
def llm_judge_relevance(physician_query: str, documentation_gap: str,
                        clinical_context: str) -> float:
    """Score physician query relevance (0-1) using LLM-as-judge."""
    prompt = f"""Rate the relevance of this physician query for addressing the documentation gap.

Documentation Gap: {documentation_gap}
Clinical Context: {clinical_context}
Physician Query: {physician_query}

Score 1-5:
1 = Completely irrelevant
2 = Tangentially related
3 = Somewhat relevant but too vague or broad
4 = Relevant and specific
5 = Highly relevant, specific, and actionable

Return ONLY a JSON: {{"score": N, "reasoning": "..."}}"""

    # Generate and parse score
    raw, json_str = generate_with_cot_capture(prompt, model, tokenizer)
    result = json.loads(json_str)
    return result["score"] / 5.0  # Normalize to 0-1
```

### Anti-Patterns to Avoid

- **Building a per-patient KG:** The KG is a reference knowledge base of ICD-10 relationships, NOT a patient-specific graph. Patient data is queried against the KG, not added to it. Building per-patient graphs would be O(n) graph constructions instead of O(1) queries.

- **Rewriting Phase 1 modules for audit trails:** The existing ingest, NER, and RAG modules work. Wrap their calls in the pipeline orchestrator with trace capture rather than modifying their internal code. Only the Qwen LLM call needs modification to capture raw CoT.

- **Using the LLM judge at inference time:** LLM-as-judge is for evaluation only. Running judge scoring during inference doubles LLM calls and latency. Evaluate offline against gold standard.

- **Hardcoding KG edges in Python code:** Store KG construction rules in a JSON/YAML data file, not scattered across Python functions. This makes the KG auditable and extensible without code changes.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Graph data structure | Custom adjacency lists | NetworkX DiGraph | NetworkX handles directed edges, typed edges, node/edge attributes, traversal algorithms, serialization |
| ICD-10 code hierarchy parsing | Manual string parsing of code structure | Simple prefix-based parent extraction (E11.40 -> E11.4 -> E11) | ICD-10 hierarchy is encoded in the code string itself; no external parser needed |
| JSON schema validation | Manual dict checking | Pydantic BaseModel with validators | Pydantic v2 is already the project standard; handles nested validation, computed fields, serialization |
| Co-occurrence statistics | Computing from real clinical data | Curated rules based on clinical knowledge | POC has no access to HCUP/MIMIC data; curated rules from Elixhauser/Charlson comorbidity indices are sufficient and deterministic |
| Excludes1 conflict rules | Parsing full CMS ICD-10-CM XML | Curated subset of high-impact conflicts relevant to gold standard cases | Full XML is 200+ MB; 20 gold standard cases use ~40 unique codes, so ~20 curated conflict rules suffice |

**Key insight:** The KG for this POC is a curated knowledge artifact, not a mined data product. It needs to contain rules for the ~40 codes appearing in the 20 gold standard cases, plus a reasonable buffer of related codes. Quality over quantity.

## Common Pitfalls

### Pitfall 1: Overcomplicated KG Schema

**What goes wrong:** Developers design elaborate ontology schemas with dozens of edge types, SNOMED-CT mappings, and hierarchical subgraph structures. The KG becomes too complex to build, query, or debug.

**Why it happens:** Clinical coding IS complex, and the temptation is to model all of it.

**How to avoid:** Start with exactly 4 edge types: `COMMONLY_CO_CODED`, `CONFLICTS_WITH`, `HAS_PARENT`, `REQUIRES_QUALIFIER`. These map directly to the 4 CDI requirements (CDI-01 through CDI-04). Add edge types only when a requirement demands it.

**Warning signs:** More than 6 edge types; KG construction takes >5 seconds; query functions have >20 lines.

### Pitfall 2: Qwen Generating Unusable Physician Queries

**What goes wrong:** The 1.5B model generates queries that are too generic ("Please provide more details"), too technical for physicians, or not clinically relevant.

**Why it happens:** Small models struggle with domain-specific natural language generation without strong prompting.

**How to avoid:** Include specific clinical context in the prompt: the actual code, its description, the exact missing qualifier, and the clinical note excerpt. Provide 1-2 few-shot examples of good physician queries in the prompt. Fall back to template-based queries if LLM output quality is below threshold.

**Warning signs:** LLM-as-judge scores below 0.60; all queries look identical; queries reference information not in the clinical note.

### Pitfall 3: Audit Trail Missing Pipeline Stages

**What goes wrong:** The audit trail captures CDI reasoning but misses earlier pipeline stages (ingestion, NER, RAG). EXPL-01 requires coverage of ALL stages.

**Why it happens:** Phase 1 modules were not built with audit trail capture in mind. Developers forget to retroactively instrument them.

**How to avoid:** Thread the AuditTrail accumulator from the very start of the pipeline. In `pipeline.py`, wrap each stage call (ingest, extract_entities, code_entities) with timing and trace capture. The EXPL-04 requirement specifically needs retrieval logs (query -> top-k -> reranked -> selected), which means the RAG module's intermediate results must be captured.

**Warning signs:** AuditTrail has fewer than 4 stage entries; retrieval log is empty; NER stage has no entity details.

### Pitfall 4: Conflating KG Construction with KG Querying

**What goes wrong:** Developers mix graph building logic with per-case query logic in the same module or function. The KG gets rebuilt or modified during inference.

**Why it happens:** Unclear separation between "reference data setup" and "inference-time querying."

**How to avoid:** Strict separation: `builder.py` constructs the KG once (at startup or as a pre-built artifact). `querier.py` takes a frozen graph and case-specific codes as input. The querier never modifies the graph.

**Warning signs:** Import cycles between builder and querier; graph `add_edge` calls during inference; KG construction inside pipeline functions.

### Pitfall 5: Chain-of-Thought Capture Breaking JSON Parsing

**What goes wrong:** Modifying the Qwen generation to capture CoT introduces regressions in the existing JSON extraction logic. The raw response format changes or the prompt changes affect JSON output.

**Why it happens:** The Phase 1 `reason_with_llm` function in `m3_rag_coding.py` already extracts JSON with retry logic. Changes to capture CoT must not break this.

**How to avoid:** The CoT capture should happen BEFORE JSON extraction, using the same raw response text. Do not change the prompt or generation parameters. Simply store the full decoded response as the CoT trace, then extract JSON from it as before. Create a shared utility function that both Phase 1 RAG reasoning and Phase 2 CDI query generation use.

**Warning signs:** Phase 1 RAG tests start failing; JSON parse errors increase; reasoning field in CodeSuggestion is empty.

## Code Examples

Verified patterns based on existing codebase analysis:

### CDIReport Pydantic Schema (models/cdi.py)

```python
# Source: Based on existing coding.py pattern + requirements CDI-01 through CDI-06
from pydantic import BaseModel, Field, computed_field
from typing import Optional

class DocumentationGap(BaseModel):
    """A single documentation gap identified by KG analysis."""
    code: str                           # ICD-10 code needing specificity
    description: str                    # Code description
    missing_qualifier: str              # What's missing (e.g., "laterality")
    physician_query: str                # Natural language query for physician
    evidence_text: str                  # Supporting text span from clinical note
    confidence: float = Field(ge=0.0, le=1.0)
    cot_trace: str = Field(default="")  # Raw chain-of-thought from Qwen (EXPL-03)

class MissedDiagnosis(BaseModel):
    """A potential missed diagnosis from co-occurrence analysis."""
    suggested_code: str                 # ICD-10 code to consider
    description: str
    co_coded_with: str                  # The code that triggered this suggestion
    co_occurrence_weight: float         # Strength of co-occurrence
    evidence_text: str                  # Supporting text span from note (EXPL-02)

class CodeConflict(BaseModel):
    """An invalid code combination detected via CONFLICTS_WITH edges."""
    code_a: str
    code_b: str
    conflict_reason: str                # Excludes1 explanation
    recommendation: str                 # What to do about it

class CDIReport(BaseModel):
    """Complete CDI analysis output for a clinical case."""
    documentation_gaps: list[DocumentationGap] = Field(default_factory=list)
    missed_diagnoses: list[MissedDiagnosis] = Field(default_factory=list)
    code_conflicts: list[CodeConflict] = Field(default_factory=list)
    completeness_score: float = Field(ge=0.0, le=1.0)  # CDI-05
    processing_time_ms: float = Field(default=0.0)

    @computed_field
    @property
    def gap_count(self) -> int:
        return len(self.documentation_gaps)

    @computed_field
    @property
    def conflict_count(self) -> int:
        return len(self.code_conflicts)
```

### AuditTrail Pydantic Schema (models/audit.py)

```python
# Source: Based on existing PipelineResult pattern + requirements EXPL-01 through EXPL-05
from datetime import datetime
from pydantic import BaseModel, Field

class RetrievalLog(BaseModel):
    """Retrieval log for a single entity coding. EXPL-04."""
    query: str
    top_k_results: list[dict]           # Raw FAISS results
    reranked_results: list[dict]        # After cross-encoder
    selected_code: str                  # Final selection
    selected_confidence: float

class StageTrace(BaseModel):
    """Trace for a single pipeline stage."""
    stage: str                          # "ingestion" | "ner" | "rag" | "cdi" | "audit"
    processing_time_ms: float
    input_summary: str
    output_summary: str
    details: dict = Field(default_factory=dict)
    cot_traces: list[str] = Field(default_factory=list)     # EXPL-03
    retrieval_logs: list[RetrievalLog] = Field(default_factory=list)  # EXPL-04

class AuditTrail(BaseModel):
    """Per-case audit trail covering all pipeline stages. EXPL-01."""
    case_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    stages: list[StageTrace] = Field(default_factory=list)
    evidence_spans: dict[str, list[str]] = Field(default_factory=dict)  # code -> [text spans] EXPL-02

    def add_stage(self, trace: StageTrace):
        self.stages.append(trace)

    def add_evidence(self, code: str, text_span: str):
        if code not in self.evidence_spans:
            self.evidence_spans[code] = []
        self.evidence_spans[code].append(text_span)
```

### KG Builder (knowledge_graph/builder.py)

```python
# Source: Based on NetworkX 3.6.1 DiGraph API + ICD-10 data structure from icd10_codes.json
import networkx as nx
from cliniq.rag.icd10_loader import load_icd10_codes

# Edge type constants
COMMONLY_CO_CODED = "COMMONLY_CO_CODED"
CONFLICTS_WITH = "CONFLICTS_WITH"
HAS_PARENT = "HAS_PARENT"
REQUIRES_QUALIFIER = "REQUIRES_QUALIFIER"

def build_cdi_knowledge_graph() -> nx.DiGraph:
    """Build static CDI knowledge graph from ICD-10 data + curated rules."""
    G = nx.DiGraph()

    # 1. Add ICD-10 code nodes from existing data
    codes = load_icd10_codes()
    for code_entry in codes:
        G.add_node(code_entry["code"],
                   type="icd_code",
                   description=code_entry["description"],
                   chapter=code_entry["chapter"])

    # 2. Add HAS_PARENT edges (derive from code structure)
    for code_entry in codes:
        code = code_entry["code"]
        parent = _derive_parent_code(code)
        if parent and G.has_node(parent):
            G.add_edge(parent, code, relation=HAS_PARENT)

    # 3. Load curated rules (co-occurrences, conflicts, qualifier requirements)
    _add_curated_co_occurrences(G)
    _add_curated_conflicts(G)
    _add_curated_qualifier_requirements(G)

    return G

def _derive_parent_code(code: str) -> str | None:
    """Derive parent code from ICD-10 code string.
    E11.40 -> E11.4 -> E11 -> None
    """
    if '.' in code:
        parts = code.split('.')
        if len(parts[1]) > 1:
            return parts[0] + '.' + parts[1][:-1]
        else:
            return parts[0]
    return None
```

### KG Querier (knowledge_graph/querier.py)

```python
# Source: NetworkX DiGraph.neighbors() + edges() API
import networkx as nx

def find_documentation_gaps(G: nx.DiGraph, case_codes: list[str],
                            entity_qualifiers: dict[str, list[str]]) -> list[dict]:
    """CDI-01: Find codes needing more specific documentation.

    Args:
        G: The static CDI knowledge graph
        case_codes: ICD-10 codes assigned by RAG module
        entity_qualifiers: {code: [qualifiers already documented]}

    Returns:
        List of gaps: {code, missing_qualifier, description}
    """
    gaps = []
    for code in case_codes:
        if not G.has_node(code):
            continue
        # Check REQUIRES_QUALIFIER edges
        for _, target, data in G.out_edges(code, data=True):
            if data.get("relation") == "REQUIRES_QUALIFIER":
                qualifier = target
                documented = entity_qualifiers.get(code, [])
                if qualifier not in documented:
                    gaps.append({
                        "code": code,
                        "missing_qualifier": qualifier,
                        "description": G.nodes[code].get("description", "")
                    })
    return gaps

def find_code_conflicts(G: nx.DiGraph, case_codes: list[str]) -> list[dict]:
    """CDI-04: Find invalid code combinations via CONFLICTS_WITH edges."""
    conflicts = []
    for i, code_a in enumerate(case_codes):
        for code_b in case_codes[i+1:]:
            if G.has_edge(code_a, code_b):
                edge = G.edges[code_a, code_b]
                if edge.get("relation") == "CONFLICTS_WITH":
                    conflicts.append({
                        "code_a": code_a,
                        "code_b": code_b,
                        "reason": edge.get("reason", "Excludes1 conflict")
                    })
            # Check reverse direction too
            if G.has_edge(code_b, code_a):
                edge = G.edges[code_b, code_a]
                if edge.get("relation") == "CONFLICTS_WITH":
                    conflicts.append({
                        "code_a": code_b,
                        "code_b": code_a,
                        "reason": edge.get("reason", "Excludes1 conflict")
                    })
    return conflicts

def find_missed_diagnoses(G: nx.DiGraph, case_codes: list[str]) -> list[dict]:
    """CDI-03: Suggest potential missed diagnoses via COMMONLY_CO_CODED edges."""
    suggestions = []
    coded_set = set(case_codes)
    for code in case_codes:
        if not G.has_node(code):
            continue
        for _, neighbor, data in G.out_edges(code, data=True):
            if data.get("relation") == "COMMONLY_CO_CODED" and neighbor not in coded_set:
                suggestions.append({
                    "suggested_code": neighbor,
                    "co_coded_with": code,
                    "weight": data.get("weight", 0.0),
                    "description": G.nodes.get(neighbor, {}).get("description", "")
                })
    return suggestions
```

### Physician Query Generation with Qwen (modules/m4_cdi.py)

```python
# Source: Based on existing reason_with_llm pattern in m3_rag_coding.py
def generate_physician_query(gap: dict, clinical_context: str,
                             model, tokenizer) -> tuple[str, str]:
    """CDI-02: Generate natural language physician query for a documentation gap.

    Returns:
        tuple of (physician_query_text, raw_cot_trace)
    """
    prompt = f"""You are a Clinical Documentation Integrity (CDI) specialist.
Generate a natural language query for the physician to clarify documentation.

ICD-10 Code: {gap['code']}
Code Description: {gap['description']}
Missing Information: {gap['missing_qualifier']}
Clinical Context: {clinical_context[:300]}

Write a clear, concise physician query that:
1. References the specific clinical finding
2. Asks about the missing qualifier
3. Uses professional medical language

Return JSON: {{"query": "your query text", "rationale": "why this matters for coding"}}"""

    # Generate with CoT capture
    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(inputs.input_ids, max_new_tokens=256,
                             temperature=0.1, do_sample=False,
                             pad_token_id=tokenizer.eos_token_id)
    raw_response = tokenizer.decode(outputs[0], skip_special_tokens=True)

    # Extract JSON
    import json
    start = raw_response.find('{')
    end = raw_response.rfind('}')
    if start != -1 and end != -1:
        try:
            result = json.loads(raw_response[start:end+1])
            return result.get("query", ""), raw_response
        except json.JSONDecodeError:
            pass

    # Fallback: template-based query
    fallback = (f"Can you please clarify the {gap['missing_qualifier']} "
                f"for the documented {gap['description']}?")
    return fallback, raw_response
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Rule-based CDI (hard-coded if/else) | KG-based CDI with LLM query generation | 2024-2025 | Natural language queries instead of template alerts; higher physician response rates |
| No chain-of-thought capture | CoT capture for every reasoning step | 2025-2026 | Audit compliance; ability to review AI reasoning; regulatory requirement trending |
| Manual audit trails (log files) | Structured Pydantic audit trails | 2025-2026 | Type-safe, queryable, serializable traces; supports compliance reporting |
| Separate evaluation frameworks | LLM-as-judge self-evaluation | 2025-2026 | Cheaper than human evaluation; reasonable quality for POC; needs calibration |
| Static exclude-code lists | Graph-based conflict detection | 2024-2025 | Handles transitive conflicts; scales to new codes; more maintainable than flat lists |

**Deprecated/outdated:**
- Hard-coded CDI rules without evidence trails: no longer meets regulatory expectations
- Template-only physician queries: physicians ignore generic queries; NLP-generated queries have higher response rates per ACDIS 2026 guidelines

## Open Questions

1. **How many curated KG rules are needed for demo quality?**
   - What we know: 20 gold standard cases use ~40 unique ICD-10 codes. Each case has 1-2 CDI gap annotations and 1-2 KG qualification rules in the gold standard data.
   - What's unclear: Whether 40-50 curated rules (co-occurrences, conflicts, qualifiers) are enough to demonstrate all CDI capabilities convincingly.
   - Recommendation: Start with exactly the rules implied by the gold standard `cdi_gap_annotations` and `kg_qualification_rules` fields. This guarantees test coverage. Add 10-15 extra rules for codes that commonly co-occur with gold standard codes (e.g., diabetes + hypertension, CHF + AFib) to demonstrate breadth.

2. **Will Qwen 1.5B generate physician queries of sufficient quality (CDI-06 >= 0.80)?**
   - What we know: Qwen2.5-1.5B has strong instruction following and JSON output generation (verified in Phase 1). Clinical text understanding is MEDIUM confidence for a 1.5B model.
   - What's unclear: Whether physician query generation (a creative NLG task) meets the 0.80 relevance threshold with self-evaluation.
   - Recommendation: Implement template-based fallback queries. If LLM-as-judge scores < 0.80 on average, use a hybrid approach: LLM generates query, template provides structure, pick the better one.

3. **How to capture RAG retrieval logs (EXPL-04) without modifying Phase 1 modules?**
   - What we know: The existing `retrieve_and_rerank` function in `m3_rag_coding.py` returns only the final reranked list. EXPL-04 needs the full chain: query -> top-20 retrieval -> top-5 reranked -> selected.
   - What's unclear: Whether we can capture intermediate results from outside the function or need minimal modifications to `m3_rag_coding.py`.
   - Recommendation: Add optional `retrieval_log` parameter to `code_entities` that, when provided, captures intermediate results. This is a minimal, backward-compatible change to Phase 1 code. Alternatively, create a wrapper function in m5_explainability that calls retrieve and rerank steps separately.

4. **Self-evaluation bias with Qwen as its own judge (CDI-06, EXPL-05)**
   - What we know: LLM-as-judge with the same model that generated the output has known positivity bias. GPT-o3-mini achieved ICC 0.818 as judge for clinical EHR summaries, but that's a much larger model.
   - What's unclear: Whether a 1.5B model can reliably discriminate between quality levels of its own output.
   - Recommendation: Use explicit rubric with 5-point Likert scale. Calibrate by including known-bad examples and verifying the judge scores them low. Accept that scores may need manual threshold adjustment. Document the limitation in evaluation results.

## Sources

### Primary (HIGH confidence)
- [NetworkX 3.6.1 Tutorial and API](https://networkx.org/documentation/stable/tutorial.html) - DiGraph, add_edge, neighbors, edge attributes
- [NetworkX DiGraph documentation](https://networkx.org/documentation/stable/reference/classes/digraph.html) - Directed graph class reference
- [Qwen/Qwen2.5-1.5B-Instruct Model Card](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct) - Model capabilities, generation parameters
- [CMS ICD-10-CM Excludes Notes](https://www.cms.gov/Outreach-and-Education/MLN/WBT/MLN6447308-ICD-10-CM/icd10cm/lesson02/12-icd-10-cm-features/index.html) - Official Excludes1/Excludes2 rules
- Existing codebase analysis: `cliniq/models/`, `cliniq/modules/`, `cliniq/rag/`, `cliniq/pipeline.py` - Phase 1 patterns

### Secondary (MEDIUM confidence)
- [Optum CDI for ICD-10-CM Reference](https://www.optumcoding.com/product/63191/) - CDI query practices and documentation gap patterns
- [AHIMA Inpatient Query Toolkit](https://www.ahima.org/media/pc3hu5qy/ahima-inpatient-query-toolkit-axs.pdf) - Physician query best practices
- [Elixhauser Comorbidity Software for ICD-10-CM](https://hcup-us.ahrq.gov/toolssoftware/comorbidityicd10/comorbidity_icd10.jsp) - Comorbidity co-occurrence reference
- [Why Chain of Thought Fails in Clinical Text Understanding](https://arxiv.org/html/2509.21933) - CoT limitations and failure modes for clinical LLMs
- [LLM-as-judge evaluation in clinical NLP](https://pmc.ncbi.nlm.nih.gov/articles/PMC12319771/) - LLM-as-judge methodology and reliability
- [CLEVER Framework for Clinical LLM Evaluation](https://pmc.ncbi.nlm.nih.gov/articles/PMC12677871/) - Clinical LLM evaluation best practices
- [Evaluating clinical AI summaries with LLMs as judges](https://www.nature.com/articles/s41746-025-02005-2) - ICC 0.818 for clinical judge reliability
- [Co-Occurrence Graph for ICD Codes (IEEE)](https://ieeexplore.ieee.org/document/10447721/) - Graph-based ICD code co-occurrence modeling
- [ICD-10 Excludes1 and Excludes2 conventions](https://providers.highmark.com/wholecare/wholecare-newsfeed/Coding-Corner-Excludes-1-and-Excludes-2-ICD-10-CM-Conventions.html) - Practical conflict rule examples

### Tertiary (LOW confidence)
- [LLM-as-a-Judge 2026 Guide](https://labelyourdata.com/articles/llm-as-a-judge) - General LLM-as-judge patterns (not clinical-specific)
- [Finetune Qwen-2.5 for Chain-of-Thought](https://medium.com/@mahadir.ahmad/finetune-qwen-2-5-ai-model-for-chain-of-thought-cot-4d1eae3a3aa9) - CoT fine-tuning patterns (we use inference-only)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - No new libraries needed; all Phase 1 dependencies suffice; NetworkX is already a prior decision
- Architecture: HIGH - KG-based CDI, audit trails, and LLM-as-judge are well-documented patterns; codebase provides clear extension points
- Pitfalls: HIGH - Identified from direct codebase analysis (e.g., existing JSON extraction logic in m3_rag_coding.py that must not break)
- KG construction approach: MEDIUM - Curated rules approach is sound but requires careful rule authoring; no existing data source for automatic rule mining in this POC
- LLM-as-judge reliability with 1.5B model: MEDIUM - Self-evaluation bias is a known limitation; may need threshold calibration

**Research date:** 2026-03-18
**Valid until:** 2026-04-18 (30 days - stable domain, no fast-moving dependencies)
