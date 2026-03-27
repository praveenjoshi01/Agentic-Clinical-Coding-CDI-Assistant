# Project Research Summary

**Project:** ClinIQ - Clinical Documentation Integrity Intelligence
**Domain:** Local multi-modal agentic clinical coding and CDI pipeline
**Researched:** 2026-03-18
**Confidence:** HIGH

## Executive Summary

ClinIQ is a clinical documentation integrity platform that combines NLP, RAG-based ICD-10 coding, and knowledge graph reasoning into a multi-agent architecture. The 2026-standard approach uses local-first OSS tools: HuggingFace transformers for clinical NER (biomedical-ner-all), FAISS with two-stage retrieval (BGE embeddings + cross-encoder reranking), NetworkX for knowledge graph prototyping, and Streamlit for interactive UI. This architecture demonstrates cutting-edge capabilities (agentic AI, multi-modal ingestion with SmolVLM, explainability-first design) while remaining fully local and CPU-viable.

The recommended approach is a modular multi-agent pipeline where specialized agents (Ingest, NER, RAG Coding, CDI KG, Audit) process clinical documents sequentially with paired evaluators at each stage. Core differentiation comes from: (1) RAG-based ICD-10 coding showing 17-26% accuracy improvement over baseline, (2) knowledge graph CDI agent for documentation gap detection, (3) full audit trail for regulatory compliance, and (4) multi-modal support for scanned documents. All models run locally on CPU with quantized small models (1.5-2B parameters), achieving <2 second latency per document for demo purposes.

Key risks center on multi-agent error cascade (17x error amplification in naive implementations), external validation failure (73% of clinical NLP projects lack it), and retrieval noise degrading RAG quality. Mitigation strategies include: structured topology with validation gates between agents, testing on multiple EHR systems before claiming accuracy, and hybrid RAG with knowledge graph grounding to reduce hallucinations by ~60%. The architecture prioritizes explainability and auditability—critical for clinical production systems—through provenance tracking and interactive KG visualization.

## Key Findings

### Recommended Stack

The 2026 standard stack for local clinical NLP + RAG + KG centers on PyTorch 2.10+ for CPU inference, HuggingFace transformers ecosystem (5.3.0+) for model loading, and sentence-transformers for embedding generation. Two-stage retrieval (FAISS + cross-encoder reranking) is RAG best practice, providing +33% accuracy improvement. NetworkX serves for rapid KG prototyping with migration path to Neo4j for production scale.

**Core technologies:**
- **PyTorch 2.10.0 + transformers 5.3.0** — ML framework with CPU-optimized inference, native support for Qwen2.5 and SmolVLM models
- **FAISS-cpu 1.13.2 + BGE embeddings** — Fast vector similarity search for ICD-10 coding; bge-small-en-v1.5 (33M params) + bge-reranker-v2-m3 for two-stage retrieval
- **d4data/biomedical-ner-all** — Clinical NER with 107 biomedical entities (distilbert-base, 66M params, ~250MB)
- **Qwen2.5-1.5B-Instruct** — Small language model for reasoning and orchestration; CPU-viable at ~3GB quantized
- **SmolVLM-2B** — Vision-language model for scanned document understanding (Apache 2.0, ~4GB)
- **NetworkX 3.6.1** — Pure Python graph library for KG prototyping; PyVis 0.3.2 for interactive visualization
- **Pydantic 2.12.5 + fhir.resources 8.2.0** — Type-safe data validation with FHIR R4B/R5 support
- **Streamlit 1.55.0** — Multi-page web UI with native multi-modal chat components
- **PyMuPDF 1.27.2** — High-performance PDF processing (5s for 1310 pages) with OCR support

**Python version:** 3.10 or 3.11 recommended (3.11 safest; full compatibility matrix verified)

**Critical notes:**
- All components run 100% local, no API dependencies
- FAISS indices not portable across architectures—rebuild per deployment platform
- fhir.resources 8.x supports R4B/R5 but NOT strict R4 (use 6.x if R4 compliance critical)
- Total model download: ~2.1GB; inference on CPU: 5-10 tokens/sec for LLM, ~100 sentences/sec for embeddings

### Expected Features

Clinical coding and CDI platforms operate at the intersection of healthcare documentation, revenue cycle management, and regulatory compliance. Research identifies table stakes, differentiators, and anti-features for the platform.

**Must have (table stakes):**
- **ICD-10-CM code extraction** — Core requirement; 95%+ accuracy expected with multi-code assignments per encounter
- **Clinical NER with negation detection** — Foundation for all downstream tasks; ~80% of EHR data is unstructured
- **FHIR R4 data ingestion** — Real-world systems must integrate with EHRs; FHIR is 2026 industry standard
- **Documentation gap detection** — Core CDI function; CDI specialists spend 60%+ time identifying gaps
- **Compliance validation** — Audit risk reduction is top-3 buyer concern; must show guideline references
- **Audit trail and explainability** — Regulatory requirement (CMS Program Integrity, False Claims Act 60-day rule); full traceability mandatory
- **Confidence scoring** — Users expect probabilistic output; codes below 0.85-0.90 threshold flagged for review

**Should have (competitive differentiators):**
- **Agentic AI architecture** — SOTA 2026 approach; autonomous agents demonstrate architectural thinking beyond simple ML
- **Multi-modal ingestion** — Text + FHIR + scanned images (SmolVLM); very few platforms support true multi-modal
- **RAG-based ICD-10 coding** — 17-26% exact match improvement; studies show RAG outperforms human coders in ED diagnostic accuracy
- **Knowledge graph CDI agent** — Rare in commercial products; demonstrates research-level capability and explainability
- **Physician query generation** — High-value CDI feature reducing CDI specialist workload by 40%+; must follow ACDIS/AHIMA guidelines
- **Interactive KG visualization (PyVis)** — Makes complex AI reasoning tangible for non-technical stakeholders
- **Cross-encoder reranking** — Two-stage retrieval demonstrates deep technical knowledge
- **Quantitative eval suite** — Module-level evaluation with explicit targets (NER F1 > 0.85, coding accuracy > 0.90)

**Defer (v2+):**
- **CPT/HCPCS procedure coding** — Diagnosis coding sufficient to demonstrate capability
- **Real-time EHR integration** — Show architecture diagram; use synthetic FHIR data for demo
- **Production-scale performance** — Acknowledge in discussion; optimize for demo throughput not scale
- **User authentication/RBAC** — Single-user Streamlit app appropriate for technical demo
- **Billing/RCM features** — Outside AI/ML scope; mention in architecture but don't build

**MVP recommendation:** 5-page Streamlit app (Demo/Data Entry/Results/KG Viz/QA Bot) with multi-modal FHIR ingestion, clinical NER, RAG-based coding, KG CDI agent, explainability layer, and quantitative eval suite. SmolVLM image ingestion optional based on time constraints.

### Architecture Approach

Standard architecture is a multi-agent sequential pipeline with specialized agents processing data in sequence, connected via typed Pydantic models. Each agent has focused responsibility (Ingest → NER → RAG Coding → CDI KG → Audit) with paired evaluators running in parallel to compute metrics, detect drift, and flag low-confidence outputs. All inter-agent communication uses immutable Pydantic models ensuring type safety and automatic validation. Centralized ModelManager handles lazy loading and caching of HuggingFace models.

**Major components:**
1. **Pipeline Orchestrator** — Coordinates multi-agent workflow with Chain of Responsibility pattern; manages data flow and error propagation
2. **Agent Processing Layer** — Five specialized agents (Ingest, NER, RAG Coding, CDI KG, Audit) with clear input/output contracts; each paired with evaluator for real-time quality monitoring
3. **Data & Retrieval Layer** — FAISS vector index (~70k ICD-10 codes), NetworkX knowledge graph (codes + documentation requirements), HuggingFace model cache
4. **Presentation Layer** — Streamlit multi-page UI (Dashboard, KG Visualization, QA Bot) with session state management for workflow persistence
5. **Evaluation Framework** — Module-level metrics (NER F1, coding precision/recall, CDI gap detection accuracy) with continuous drift monitoring

**Key patterns:**
- **Two-stage retrieval (RAG best practice):** Bi-encoder retrieves top-100 candidates (~50ms), cross-encoder reranks to top-10 (+120ms, +33% accuracy)
- **Hybrid RAG with KG grounding:** Combine FAISS semantic similarity with NetworkX graph traversal for ontology constraints; reduces hallucinations by ~60%
- **Explainability-first audit trail:** Every processing step logs provenance (model version, input features, evidence spans) for FDA/HIPAA compliance
- **Paired agent-evaluator architecture:** Each agent has evaluation module computing metrics in real-time, enabling early detection of drift
- **Centralized model management:** Singleton ModelManager with lazy loading prevents redundant model loads (5-10s overhead) and memory bloat

**Build order:** Phase 1 (Core data models + utilities) → Phase 2 (Individual agents in parallel) → Phase 3 (Pipeline orchestration) → Phase 4 (UI) → Phase 5 (Production hardening)

### Critical Pitfalls

1. **Error cascade in multi-agent pipelines (17x amplification)** — Errors compound through pipeline; missed NER entity → failed RAG retrieval → hallucinated KG relationship → incorrect DRG. Avoid with: structured topology with validation gates between agents, confidence thresholds for early stopping, self-correction loops where agents flag low-confidence outputs. Address in Phase 1 (architecture design).

2. **External validation blindness (73% of clinical NLP projects)** — Model works on test set, fails on real notes from different EHR systems. 73% of studies rely only on internal validation. Avoid with: test on multiple EHR systems (Epic, Cerner, Meditech), adversarial test sets with abbreviations/negations, continuous validation on production samples. Address in Phase 2 (NER module) and Phase 6 (production hardening).

3. **Retrieval noise drowning signal (RAG failure mode)** — FAISS retrieves technically similar but semantically wrong ICD codes; generic embeddings don't capture clinical similarity. Avoid with: clinical-specific embeddings (BioBERT), multi-stage retrieval with metadata filtering, hybrid search combining vector + keyword/BM25, tune cross-encoder on ICD-10 task not generic MS-MARCO. Address in Phase 3 (RAG retrieval) and Phase 4 (coding agent).

4. **Context and negation misinterpretation** — NER extracts "pneumonia" but misses "no evidence of pneumonia" or "rule out pneumonia." Pretrained models focus on entities not contextual qualifiers. Avoid with: add negation detection layer (NegEx, ConText), tag entities with assertion attributes (PRESENT/ABSENT/POSSIBLE/HISTORICAL), test on negation benchmark (>95% accuracy target). Address in Phase 2 (NER module).

5. **Small model structured output unreliability** — Qwen2.5-1.5B generates inconsistent JSON; one missing comma breaks pipeline. Avoid with: aggressive output validation with retry logic, JSON mode if available, chain-of-thought prompting (reason first, format second), test on range of input lengths to find failure threshold. Address in Phase 4 (coding agent) and Phase 5 (integration).

**Additional warnings:**
- **LLM-as-judge bias:** Using Qwen to evaluate Qwen introduces 40% position bias, 15% verbosity bias, 5-7% self-enhancement; use different larger model for evaluation or human expert validation
- **Synthetic data fidelity gap:** LLM-generated notes too clean; model learns synthetic patterns not real clinical documentation; mix with real de-identified notes (MIMIC-III, i2b2)
- **KG coverage vs scalability:** Manual rules don't scale beyond top-50 DRGs; NetworkX degrades at >5k nodes; design for graceful degradation with LLM fallback for long-tail
- **Vision OCR noise propagation:** SmolVLM (256M) produces noisy OCR with character errors that cascade through pipeline; validate against dedicated OCR engines (Tesseract, AWS Textract)
- **Streamlit state management:** Session state corruption across multi-page navigation; initialize all keys in main app.py before page loads

## Implications for Roadmap

Based on research, the roadmap should follow a 6-phase structure prioritizing foundational infrastructure before advanced features, with explicit validation gates to address critical pitfalls.

### Phase 1: Foundation and Data Infrastructure
**Rationale:** Core data models and FAISS indexing must exist before any agents can function. Pydantic schemas define inter-agent contracts. Building FAISS index upfront (offline) prevents latency during demo. Architectural decisions here (validation gates, error handling) prevent 17x error cascade pitfall.

**Delivers:** Pydantic models (ClinicalDocument, NEREntity, CodingResult, CDIReport, AuditTrail), ModelManager singleton with lazy loading, FAISS index builder (70k ICD-10 codes), NetworkX KG schema and builder (codes + documentation requirements), evaluation framework skeleton.

**Addresses:** Architecture anti-patterns (monolithic pipeline, repeated model loading), structured data contracts, model management.

**Avoids:** Pitfall #1 (error cascade) by designing validation gates; Pitfall #7 (synthetic data fidelity) by planning real data access upfront.

### Phase 2: NER and Entity Extraction
**Rationale:** NER is foundation for all downstream tasks (coding, CDI, KG). Must be built first with high quality since errors compound. Negation detection must be built into NER layer, not added later. External validation critical before proceeding to avoid Pitfall #2.

**Delivers:** NER agent (d4data/biomedical-ner-all model wrapper), negation detection layer (NegEx/ConText integration), entity normalization, assertion classification (PRESENT/ABSENT/POSSIBLE/HISTORICAL), NER evaluator with F1/precision/recall metrics, external validation suite (test on 3+ EHR note types).

**Addresses:** Clinical NER (table stakes), negation detection (competitive differentiator), external validation blindness (Pitfall #2), context misinterpretation (Pitfall #4).

**Uses:** PyTorch 2.10, transformers 5.3.0, d4data/biomedical-ner-all, seqeval for metrics.

**Research flag:** Test negation detection performance separately; may need custom assertion classifier if NegEx insufficient for clinical domain.

### Phase 3: RAG Retrieval Infrastructure
**Rationale:** Retrieval quality determines downstream coding accuracy. Two-stage retrieval (bi-encoder + cross-encoder) is 2026 best practice. Must validate retrieval precision independently before adding generation layer to avoid Pitfall #3 (retrieval noise).

**Delivers:** FAISS retriever with metadata filtering, embedder wrapper (bge-small-en-v1.5), cross-encoder reranker (bge-reranker-v2-m3), retrieval evaluator (top-10/top-20 precision), hybrid search combining vector + keyword for medical terms, tuning interface for top-k and confidence thresholds.

**Addresses:** RAG-based ICD-10 coding (differentiator), retrieval noise (Pitfall #3), two-stage retrieval pattern.

**Uses:** FAISS-cpu 1.13.2, sentence-transformers 5.3.0, BGE models.

**Research flag:** May need to fine-tune embeddings on ICD-10 coding task if retrieval precision <80% on validation set.

### Phase 4: Coding and CDI Agents
**Rationale:** Core business logic combining retrieval with reasoning. RAG coding agent generates ICD-10 assignments, KG CDI agent identifies documentation gaps. Structured output validation critical here to avoid Pitfall #5. KG coverage must be scoped realistically (top-50 DRGs) with graceful degradation for long-tail.

**Delivers:** RAG coding agent (FAISS retrieval → Qwen reasoning → structured output), confidence scoring and thresholding (>0.85), KG CDI agent (NetworkX graph traversal for gap detection), hybrid RAG with KG grounding, structured output validation with retry logic, coding evaluator (accuracy, precision, recall against ground truth), CDI evaluator (gap detection sensitivity/specificity).

**Addresses:** ICD-10 code extraction (table stakes), documentation gap detection (table stakes), KG CDI agent (differentiator), small model output reliability (Pitfall #5), KG coverage vs scalability (Pitfall #8).

**Uses:** Qwen2.5-1.5B-Instruct, NetworkX 3.6.1, PyVis 0.3.2 for visualization.

**Research flag:** Validate Qwen2.5-1.5B structured output reliability on medical schemas; may need to upgrade to larger model (3B) or use constrained decoding if parse error rate >10%.

### Phase 5: UI and Integration
**Rationale:** All processing logic complete; now build user-facing interface. Multi-page Streamlit structure requires careful session state management to avoid Pitfall #10. Explainability and audit trail cross-cut all agents, assembled here. Quantitative eval suite demonstrates engineering rigor.

**Delivers:** Streamlit 5-page app (Home/Demo, Data Entry, Results, KG Visualization, QA Bot), session state management (initialize all keys in main app.py), audit trail builder (aggregate provenance from all agents), evidence linker (map codes to text spans), interactive KG visualization (PyVis), quantitative eval dashboard (per-agent metrics), end-to-end integration tests.

**Addresses:** Compliance validation (table stakes), audit trail (table stakes), interactive KG visualization (differentiator), quantitative eval suite (differentiator), Streamlit state management (Pitfall #10).

**Uses:** Streamlit 1.55.0, Plotly 6.6.0, PyVis 0.3.2.

**Research flag:** Test multi-page navigation flows (forward, back, refresh, direct URL) to ensure state persistence; may need to refactor state management if KeyError issues arise.

### Phase 6: Multi-Modal and Production Hardening
**Rationale:** SmolVLM multi-modal ingestion is differentiator but not critical path; can be added after core workflow proven. Production hardening (external validation, continuous monitoring, LLM-as-judge bias mitigation) separates POC from production-ready demo.

**Delivers:** SmolVLM image-to-text module (scanned document OCR), multi-modal FHIR ingestion (text + structured + images), OCR quality validation (character error rate <3%), external validation on real clinical notes (MIMIC-III or i2b2 datasets), human expert validation pipeline (compare LLM-as-judge to SME agreement), continuous monitoring dashboard (drift detection, error rate tracking), deployment packaging (Docker, requirements.txt).

**Addresses:** Multi-modal ingestion (differentiator), vision OCR noise (Pitfall #9), external validation blindness (Pitfall #2), LLM-as-judge bias (Pitfall #6), synthetic data fidelity gap (Pitfall #7).

**Uses:** SmolVLM-2B, PyMuPDF 1.27.2, fhir.resources 8.2.0.

**Research flag:** Validate SmolVLM OCR quality on medical documents before committing; may need to fall back to dedicated OCR engine (Tesseract, AWS Textract) if character error rate too high.

### Phase Ordering Rationale

- **Foundation first (Phase 1):** Data models and indexing infrastructure required by all other phases; architectural decisions here prevent downstream error cascade
- **NER before coding (Phase 2 → 3 → 4):** NER extracts entities that feed RAG retrieval; retrieval provides candidates for coding agent; linear dependency chain
- **Retrieval isolation (Phase 3):** Validate retrieval quality independently before adding generation layer; prevents chasing generation bugs when root cause is retrieval noise
- **UI after logic (Phase 5):** All processing agents must be complete and tested before building interface; prevents UI changes breaking business logic
- **Multi-modal last (Phase 6):** Text-only pipeline demonstrates core capability; images are enhancement not requirement; adding vision model increases complexity significantly

**Validation gates between phases:**
- Phase 1 → 2: FAISS index built, KG schema validated, Pydantic models define contracts
- Phase 2 → 3: NER F1 score >0.85 on external validation, negation detection >95% accuracy
- Phase 3 → 4: Retrieval precision >80% (correct code in top-10), cross-encoder provides >20% lift over bi-encoder alone
- Phase 4 → 5: Coding accuracy >90% on held-out test set, structured output parse success rate >98%
- Phase 5 → 6: All integration tests pass, multi-page navigation validated, eval dashboard functional

### Research Flags

Phases likely needing deeper research during planning:

- **Phase 2 (NER Module):** Negation detection accuracy may require custom assertion classifier beyond off-the-shelf NegEx; research state-of-art clinical assertion detection models
- **Phase 3 (RAG Retrieval):** If generic BGE embeddings underperform, may need to fine-tune on ICD-10 coding task; research clinical embedding fine-tuning datasets and methods
- **Phase 4 (Coding Agent):** Qwen2.5-1.5B structured output reliability unknown for complex medical schemas; may need constrained decoding or model upgrade
- **Phase 6 (Multi-Modal):** SmolVLM OCR performance on medical documents uncertain; validate early and plan fallback to Tesseract/commercial OCR if needed

Phases with standard patterns (skip research-phase):

- **Phase 1 (Foundation):** Pydantic, FAISS, NetworkX are well-documented with extensive examples; standard patterns apply
- **Phase 5 (UI):** Streamlit multi-page apps have established patterns; session state management documented but needs careful implementation

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified from PyPI/HuggingFace official sources (Mar 2026); Python compatibility matrix validated; no experimental/alpha packages |
| Features | MEDIUM | Based on market analysis of commercial products (3M CodeFinder, Nuance, Dolbey) and 2026 technical literature; competitive positioning validated but feature prioritization involves subjective judgment |
| Architecture | MEDIUM-HIGH | Multi-agent patterns verified across multiple 2025-2026 sources; clinical NLP pipelines well-documented; specific implementation details require validation during build |
| Pitfalls | HIGH | 25+ authoritative sources cross-validated; error cascade (17x) and external validation (73%) statistics from peer-reviewed studies; RAG/LLM biases extensively documented in 2026 research |

**Overall confidence:** HIGH

Research draws on official documentation (PyPI, HuggingFace), peer-reviewed studies (PMC, arxiv), and 2026 industry benchmarks. Technology stack fully verified with current versions. Feature landscape validated against commercial products. Architecture patterns confirmed across multiple clinical NLP implementations. Pitfall statistics sourced from academic research and industry case studies.

### Gaps to Address

- **Real clinical data access:** Research assumes availability of de-identified clinical notes for external validation. If MIMIC-III/i2b2 datasets not accessible, will need to create adversarial test sets with synthetic data augmented with realistic noise patterns. Address during Phase 2 planning.

- **Qwen2.5-1.5B clinical reasoning capacity:** Limited benchmarks exist for Qwen2.5-1.5B on medical coding tasks specifically. May discover during Phase 4 that 1.5B parameter model insufficient for complex reasoning over ICD-10 guidelines. Mitigation: have upgrade path to 3B model or hybrid approach (small model + rule-based fallback). Validate early in Phase 4.

- **NetworkX performance at realistic KG scale:** Research suggests NetworkX degrades at >5k nodes, but specific performance profile for medical ontology queries unknown. Address during Phase 4 by profiling graph queries on realistic data and planning migration to Neo4j if latency >500ms.

- **SmolVLM medical document OCR quality:** SmolVLM OCR performance validated on generic documents, but medical documents (handwriting, tables, low-contrast scans) may have higher error rates. Validate early in Phase 6 and plan fallback to Tesseract or commercial OCR if character error rate >5%.

- **Cross-encoder reranker domain adaptation:** bge-reranker-v2-m3 trained on generic MS-MARCO dataset; may need fine-tuning for ICD-10 coding task to achieve +33% accuracy lift claimed in research. Address during Phase 3 by measuring retrieval lift and fine-tuning if necessary.

- **Evaluation ground truth:** Quantitative evaluation requires labeled test data (clinical notes with gold-standard ICD-10 codes). If not available, will need clinical expert to label sample (50-100 notes) during Phase 2-4 development. Plan for SME time allocation.

## Sources

### Stack (HIGH confidence)
- PyPI official releases (PyTorch 2.10.0, transformers 5.3.0, sentence-transformers 5.3.0, faiss-cpu 1.13.2, networkx 3.6.1, pydantic 2.12.5, streamlit 1.55.0) — all verified as current Jan-Mar 2026
- HuggingFace model hub (d4data/biomedical-ner-all, Qwen2.5-1.5B-Instruct, SmolVLM-2B, BGE models) — official model cards with license verification
- [GraphRAG in 2026: A Practitioner's Guide](https://medium.com/graph-praxis/graph-rag-in-2026-a-practitioners-guide-to-what-actually-works-dca4962e7517) — Two-stage retrieval best practice
- [Build BGE Reranker: Cross-Encoder Reranking for Better RAG 2026](https://markaicode.com/bge-reranker-cross-encoder-reranking-rag/) — +33% accuracy improvement validation

### Features (MEDIUM-HIGH confidence)
- Gartner Peer Insights 2026 Autonomous Clinical Coding Reviews — market analysis
- [Top 5 Clinical Documentation Improvement Software in 2026](https://www.mbwrcm.com/the-revenue-cycle-blog/clinical-documentation-improvement-software-hospitals) — commercial product features
- [Assessing Retrieval-Augmented LLM Performance in ED ICD-10-CM Coding (PMC11527068)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11527068/) — 17-26% accuracy improvement statistic
- [Guidelines For Achieving Compliant Physician Queries - AGS Health](https://www.agshealth.com/blog/guidelines-for-achieving-compliant-physician-queries/) — CDI specialist workload (60%+ on gap detection)
- [Transparent AI for Medical Coding: Why Black Box Tools Fail](https://blog.nym.health/transparent-ai-for-medical-coding) — audit trail regulatory requirements

### Architecture (MEDIUM-HIGH confidence)
- [Google's Eight Essential Multi-Agent Design Patterns](https://www.infoq.com/news/2026/01/multi-agent-design-patterns/) — multi-agent patterns
- [Code Like Humans: A Multi-Agent Solution for Medical Coding (arxiv 2509.05378)](https://arxiv.org/pdf/2509.05378) — clinical coding agent architecture
- [From Clinical Text to Knowledge Graphs with John Snow Labs Healthcare NLP](https://www.johnsnowlabs.com/from-clinical-text-to-knowledge-graphs-with-john-snow-labs-healthcare-nlp/) — NetworkX prototyping pattern
- [A survey on retrieval-augmentation generation (RAG) models for healthcare applications](https://link.springer.com/article/10.1007/s00521-025-11666-9) — healthcare RAG architecture
- [Ontology-grounded knowledge graphs for mitigating hallucinations in LLMs (PMC)](https://pubmed.ncbi.nlm.nih.gov/41610815/) — KG grounding reduces hallucinations ~60%

### Pitfalls (HIGH confidence)
- [Why Your Multi-Agent System is Failing: Escaping the 17x Error Trap](https://towardsdatascience.com/why-your-multi-agent-system-is-failing-escaping-the-17x-error-trap-of-the-bag-of-agents/) — 17x error amplification statistic
- [Using NLP to extract information from clinical text in EHRs: a systematic review (JAMIA)](https://academic.oup.com/jamia/article/33/2/484/8287208) — 73% lack external validation
- [Self-Preference Bias in LLM-as-a-Judge (arxiv 2410.21819)](https://arxiv.org/html/2410.21819v2) — 40% position bias, 15% verbosity bias, 5-7% self-enhancement bias
- [Evaluating Structured Output Robustness of Small LMs for Clinical Notes (arxiv 2507.01810)](https://arxiv.org/html/2507.01810v1) — small model JSON unreliability
- [OCR-Mediated Modality Dominance in VLMs (medrxiv)](https://www.medrxiv.org/content/10.64898/2026.02.22.26346828v1.full.pdf) — accuracy drops 0.56 to 0.43 under OCR adversarial attacks
- [Beyond the Hype: Why Synthetic Data Falls Short in Healthcare](https://www.rgnmed.com/post/beyond-the-hype-why-synthetic-data-falls-short-in-healthcare-and-how-regenmed-circles-closes-the-gap) — synthetic data fidelity gap
- [Streamlit Session State Issues (GitHub #5689)](https://github.com/streamlit/streamlit/issues/5689) — multi-page state management

---
*Research completed: 2026-03-18*
*Ready for roadmap: yes*
