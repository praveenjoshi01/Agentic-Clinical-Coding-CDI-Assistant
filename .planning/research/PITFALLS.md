# Domain Pitfalls: Clinical NLP + RAG + Knowledge Graph Multi-Agent Pipeline

**Domain:** Clinical Documentation Integrity (CDI) Intelligence Platform
**Researched:** 2026-03-18
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Error Cascade in Multi-Agent Pipelines (17x Error Amplification)

**What goes wrong:**
Errors from upstream agents (NER → RAG → KG) compound and amplify through the pipeline. Unstructured multi-agent networks amplify errors up to 17.2 times compared to single-agent baselines. By the time output reaches the final CDI agent, you have confidently-written, grammatically-flawless recommendations that are subtly or substantially wrong.

**Why it happens:**
Each agent trusts its inputs, produces an output, and passes it downstream. Errors don't announce themselves—they compound. A missed entity in NER becomes a failed RAG retrieval, which becomes a hallucinated KG relationship, which becomes an incorrect DRG recommendation. Naive agentic pipelines are optimistic by design.

**How to avoid:**
- Implement structured topology with explicit validation checkpoints between agents
- Add confidence scores at each stage and threshold-based early stopping
- Build error detection before handoff (e.g., NER entity count sanity check, RAG retrieval score validation)
- Include self-correction loops where agents can request clarification or flag low-confidence outputs
- Log and monitor error propagation metrics per stage

**Warning signs:**
- End-to-end accuracy degrades faster than individual module accuracy
- Errors show patterns (e.g., always fails on certain note types)
- Downstream agents receive invalid/malformed inputs but don't fail gracefully
- Debugging requires tracing back through 3+ layers to find root cause

**Phase to address:**
Phase 1 (Architecture) — Design structured topology with validation gates, not naive sequential chaining

---

### Pitfall 2: External Validation Blindness (73% of Clinical NLP Projects)

**What goes wrong:**
Model works perfectly on held-out test set, fails catastrophically on real clinical notes from different hospitals/EHR systems. 73% of clinical NLP studies rely only on left-out test sets for internal validation with no external validation.

**Why it happens:**
Training data comes from one source (e.g., d4data/biomedical-ner-all pretrained on specific corpora). Real clinical notes have different documentation styles, abbreviations, templates, EHR formatting. No two providers document conditions the same way. Dataset bias gets exploited rather than generalizable patterns learned.

**How to avoid:**
- Test on notes from multiple EHR systems (Epic, Cerner, Meditech) and different hospital types
- Create adversarial test sets with known difficult cases (abbreviations, negations, uncertain language)
- Validate against gold-standard clinical datasets (i2b2, MIMIC-III notes if accessible)
- Include edge cases in synthetic test data (measurement errors, contradictory information)
- Set up continuous validation pipeline with real production samples

**Warning signs:**
- Accuracy drops >15% when tested on different hospital system
- Fails on common abbreviations not in training data
- Entity recognition works on typed notes, fails on handwritten-then-scanned notes
- Performance varies significantly across note types (H&P vs progress notes vs discharge summaries)

**Phase to address:**
Phase 2 (NER Module) — Build external validation BEFORE claiming accuracy metrics
Phase 6 (Production Hardening) — Continuous validation against live data

---

### Pitfall 3: Retrieval Noise Drowning Signal (RAG Failure Mode)

**What goes wrong:**
FAISS flat index retrieves 70k ICD-10 codes, but top-k results contain irrelevant codes that confuse downstream reasoning. RAG retrieves technically similar vectors but semantically wrong codes. LLM generates responses over-relying on retrieval noise instead of actual clinical relevance.

**Why it happens:**
Embedding quality determines retrieval quality. Generic sentence-transformers may not capture clinical semantic similarity (e.g., "chest pain" maps to cardiac AND pulmonary AND musculoskeletal codes). FAISS flat index has no domain-aware filtering. Cross-encoder reranker helps but adds latency and may introduce own biases.

**How to avoid:**
- Use clinical-specific embeddings (e.g., BioBERT, Clinical-Longformer, domain-finetuned models)
- Implement multi-stage retrieval: coarse filter (category/body system) → fine-grained embedding search
- Add metadata filtering BEFORE vector search (note type, patient demographics, clinical context)
- Test retrieval quality independently: measure whether correct code is in top-10/top-20 retrieval
- Consider hybrid search: combine vector similarity with keyword/BM25 for specific medical terms
- Tune cross-encoder reranker on ICD-10 coding task, not generic MS-MARCO

**Warning signs:**
- Top-10 retrieved codes span completely unrelated body systems
- Retrieval precision degrades with longer/more complex clinical notes
- Same symptoms retrieve different codes depending on surrounding text
- Reranker significantly changes result distribution (indicates poor initial retrieval)

**Phase to address:**
Phase 3 (RAG Retrieval) — Validate retrieval quality BEFORE building generation layer
Phase 4 (Coding Agent) — Add domain-aware filters and hybrid retrieval

---

### Pitfall 4: Context and Negation Misinterpretation

**What goes wrong:**
NER extracts "pneumonia" but misses "no evidence of pneumonia" or "rule out pneumonia." Coding agent assigns pneumonia code when clinician explicitly documented absence or uncertainty. In clinical text, negated or uncertain statements significantly impact interpretation.

**Why it happens:**
Pretrained NER models (d4data/biomedical-ner-all) focus on entity extraction, not contextual qualifiers. Small LLMs (Qwen2.5-1.5B) may lack capacity to consistently track negation scope across long contexts. Clinical notes embed context non-linearly ("patient denies chest pain but reports dyspnea" — both symptoms in same sentence, different statuses).

**How to avoid:**
- Add negation detection layer (NegEx, ConText algorithm, or dedicated negation classifier)
- Tag entities with assertion attributes: PRESENT, ABSENT, POSSIBLE, HYPOTHETICAL, HISTORICAL
- Include context window around entities (±5 sentences) for downstream agents
- Test specifically on negation/uncertainty cases (create benchmark with affirmed vs negated conditions)
- Use assertion-aware prompting for LLMs: explicitly ask "Is this condition present, absent, or uncertain?"

**Warning signs:**
- Coding accuracy degrades on notes with extensive differential diagnosis lists
- False positives on "rule out X" or "no evidence of X" patterns
- Historical conditions (e.g., "history of MI") coded as current acute conditions
- Hypothetical scenarios ("if patient develops fever, consider...") treated as actual findings

**Phase to address:**
Phase 2 (NER Module) — Add assertion classification alongside entity extraction
Phase 4 (Coding Agent) — Validate context understanding before finalizing codes

---

### Pitfall 5: Small Model Structured Output Unreliability

**What goes wrong:**
Qwen2.5-1.5B-Instruct generates inconsistent JSON output. Sometimes valid, sometimes malformed, sometimes missing required fields. Downstream modules crash on parse errors or silently skip invalid outputs. Structural robustness declines for longer documents.

**Why it happens:**
Small models (1.5B parameters) have limited capacity for consistent formatting while simultaneously reasoning about content. JSON parsing is brittle — one missing comma breaks entire pipeline. Training on structured output may not generalize to complex medical schemas. Longer contexts increase probability of formatting errors.

**How to avoid:**
- Use JSON mode/structured output features if available in model API
- Add aggressive output validation: parse JSON, check schema, retry on failure
- Implement fallback strategies: regex repair common formatting issues, request regeneration with simplified schema
- Consider chain-of-thought prompting: reason first, then format (two-stage generation)
- Test on range of input lengths (100 words, 500 words, 1500 words) to find failure threshold
- Choose model known for structured output (some SLMs designed specifically for function calling/JSON)

**Warning signs:**
- Parse errors on >10% of outputs
- Success rate degrades with note length
- Certain JSON fields frequently missing or malformed
- Model includes explanatory text outside JSON structure
- Inconsistent field naming (sometimes "icd_code", sometimes "icd-code", sometimes "code")

**Phase to address:**
Phase 4 (Coding Agent) — Validate structured output reliability early
Phase 5 (Integration) — Add robust error handling and retry logic

---

### Pitfall 6: LLM-as-Judge Self-Evaluation Bias

**What goes wrong:**
Using Qwen to evaluate Qwen-generated outputs introduces multiple systematic biases. GPT-4 exhibits ~40% position bias, ~15% verbosity bias, 5-7% self-enhancement bias. Evaluation metrics look good in POC but don't reflect actual clinical accuracy. Agreement rates between LLM judges and clinical subject matter experts range only 60-68%.

**Why it happens:**
LLMs prefer texts more familiar to them (self-preference bias). Models assign higher scores to outputs with lower perplexity relative to their training distribution. In specialized clinical domains, LLM judgment aligns more with lay user preferences than SME standards due to RLHF training on general internet text, not medical guidelines.

**How to avoid:**
- Use different, larger model for evaluation (e.g., GPT-4 to judge Qwen outputs)
- Implement human-in-the-loop validation: have clinical coders review sample of outputs
- Create rubric-based evaluation with specific medical accuracy criteria, not just fluency
- Test for known biases: shuffle output order, vary verbosity, check if model prefers own outputs
- Track agreement with SME judgments as ground truth, not just LLM scores
- Consider domain-specific evaluation models finetuned on clinical coding quality

**Warning signs:**
- Evaluation scores consistently higher than human expert agreement
- Model rates verbose/confident-sounding wrong answers highly
- Scores correlate more with text length than actual accuracy
- Positional bias: first response in pairwise comparison wins more often
- Evaluation doesn't catch clinically critical errors (wrong DRG assignment despite high scores)

**Phase to address:**
Phase 5 (Evaluation) — Build human validation pipeline alongside automated metrics
Phase 6 (Production Hardening) — Continuous monitoring with clinical expert review

---

### Pitfall 7: Synthetic Data Fidelity Gap

**What goes wrong:**
Model trained/tested on synthetic clinical notes performs well in demo, fails on real EHR notes. Synthetic notes too clean, lack real-world messiness (abbreviations, typos, inconsistent grammar, template artifacts). Model learns "synthetic clinical style" rather than real documentation patterns.

**Why it happens:**
LLM-generated synthetic data inherits LLM training distribution — cleaner and more structured than actual clinical documentation. Real notes have irregular phrasing, domain-specific shorthand, copy-paste artifacts, measurement unit inconsistencies. Synthetic data tends to over-generate frequent ICD-10 codes (assuming frequency means importance), distorting natural distribution. Complex clinical correlations and rare events not captured by generative models.

**How to avoid:**
- Mix synthetic data with real de-identified clinical notes (MIMIC-III, i2b2 datasets)
- Augment synthetic data with realistic noise: inject typos, abbreviations, template repetitions
- Validate synthetic data distribution matches real clinical data distribution (code frequency, note length, entity density)
- Test model performance separately on synthetic vs real data to measure gap
- Use synthetic data for scaffolding/initial development only — validate on real data before production claims
- Consider hybrid approach: synthetic for privacy-safe development, real for final validation

**Warning signs:**
- Performance gap >20% between synthetic and real note testing
- Model confused by common clinical abbreviations present in real notes
- Fails on copy-paste patterns common in EHR documentation
- Doesn't handle incomplete or unstructured sections of real notes
- Rare condition codes never appear in synthetic data despite clinical relevance

**Phase to address:**
Phase 1 (Data Strategy) — Plan for real data access, don't rely solely on synthetic
Phase 6 (Production Validation) — Test on real clinical notes before deployment claims

---

### Pitfall 8: Knowledge Graph Coverage vs Scalability Tradeoff

**What goes wrong:**
NetworkX KG with manually authored rules covers only top-50 DRGs. Works beautifully on common cases in demo (CHF, pneumonia, sepsis), completely fails on less common conditions. Manually scaling to 700+ DRGs is infeasible. NetworkX performance degrades significantly beyond thousands of nodes/edges.

**Why it happens:**
Manual rule authoring doesn't scale. Clinical knowledge space is enormous (70k ICD-10 codes, 700+ MS-DRGs, complex qualification logic). NetworkX is pure Python, becomes computationally expensive at scale. Graph queries that work on 50-node graph timeout on 5000-node graph. Demo focuses on common cases, real production sees long-tail distribution.

**How to avoid:**
- Start with rule coverage analysis: what % of actual clinical cases do top-50 DRGs represent?
- Design for graceful degradation: flag cases outside KG coverage rather than failing silently
- Consider hybrid approach: rules for top-N common cases, LLM reasoning for long-tail
- If scaling NetworkX: use GPU acceleration (nx-cugraph, RAPIDS cuGraph), or migrate to graph database (Neo4j, ArangoDB) for production
- Evaluate semi-automated rule extraction from clinical coding guidelines
- Build coverage dashboard: track % of cases handled by KG vs fallback to LLM-only reasoning

**Warning signs:**
- Demo success rate >80%, but only tested on top-10 conditions
- KG queries take >500ms on graph with >1000 nodes
- No plan for how to add nodes 51-700
- Qualification rules hard-coded rather than data-driven
- Error rate spikes for conditions outside top-50 DRG coverage

**Phase to address:**
Phase 4 (KG CDI Agent) — Design scalable architecture, not demo-only solution
Phase 6 (Production Hardening) — Profile performance at realistic scale, plan migration if needed

---

### Pitfall 9: Vision Model OCR Noise Propagation

**What goes wrong:**
SmolVLM (256M) processes scanned clinical documents but produces noisy OCR output with character-level errors, missed sections, or hallucinated text. Errors propagate through entire pipeline since all downstream agents trust OCR output as ground truth. OCR-capable models become vulnerable to adversarial manipulation through text overlays.

**Why it happens:**
Small vision models (256M parameters) have limited capacity for accurate OCR, especially on complex clinical documents with tables, handwriting, poor scan quality. Models occasionally produce malformed tags or repetitive tokens due to autoregressive nature or model size limitations. Medical documents often have challenging layouts (multi-column, mixed print/handwriting, low contrast). 2026 research shows OCR-readable overlays can manipulate diagnostic workflows with median accuracy dropping from 0.56 to 0.43 under stealth injection.

**How to avoid:**
- Compare SmolVLM OCR against dedicated OCR engines (Tesseract, AWS Textract, Azure Form Recognizer) on medical documents
- Implement OCR confidence scoring and flag low-confidence extractions for human review
- Add character-level and word-level validation: medical term spell-checking, expected section detection
- Test on realistic document types: handwritten notes, faxed documents, photocopies, mobile phone photos
- Consider hybrid: dedicated OCR for text extraction, VLM for understanding/reasoning over extracted text
- Treat OCR output as untrusted input: validate structure, check for adversarial patterns

**Warning signs:**
- Character error rate >5% on clinical documents
- Misses entire sections or tables
- Hallucinates plausible-sounding medical terms not in original document
- Inconsistent performance across scan quality levels
- Entity extraction accuracy much lower on vision-extracted text vs typed text

**Phase to address:**
Phase 2 (Image-to-Text Module) — Validate OCR quality before chaining to NER
Phase 6 (Production Hardening) — Test on real-world document quality distribution

---

### Pitfall 10: Streamlit State Management in Multi-Page Pipeline

**What goes wrong:**
User navigates through 5-page Streamlit app (Upload → NER → RAG → KG → Results). Session state gets lost, corrupted, or inconsistently updated between pages. User uploads document on page 1, results disappear when viewing page 3. Pipeline must re-run from scratch on each page navigation, breaking demo flow.

**Why it happens:**
Streamlit reruns entire script on every interaction, including page navigation. Session state persistence across pages requires careful initialization and management. Widget states don't always sync correctly in multi-page apps. Sidebar navigation triggers page reloads that can reset state. Keys not properly initialized lead to KeyError on page switches.

**How to avoid:**
- Initialize ALL session state keys in main app.py before any page loads
- Use consistent key naming and access patterns across all pages
- Avoid storing large objects (entire documents, model outputs) in session state — use caching or disk storage
- Implement state validation at page entry: check required keys exist before rendering
- Use st.cache_data for expensive computations that shouldn't re-run on navigation
- Test full navigation flow: page 1 → 2 → 3 → back to 2 → refresh → 4 → back to 1

**Warning signs:**
- KeyError: 'variable_name' on page navigation
- User inputs reset to default when returning to previous page
- Intermediate results disappear after visiting different page
- Pipeline re-runs from beginning instead of resuming from current stage
- Different behavior on first visit vs returning to page

**Phase to address:**
Phase 5 (UI Integration) — Design state management architecture before building all pages
Phase 6 (Testing) — Test complete multi-page navigation flows, not just individual pages

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip external validation, test only on held-out internal data | Faster development, can claim high accuracy metrics | Model fails in production on real clinical notes from different sources | Never acceptable for clinical AI |
| Use flat FAISS index without metadata filtering | Simple implementation, fast initial setup | Poor retrieval quality, high noise, doesn't scale beyond 70k vectors | Only for initial POC, must upgrade for production |
| Manual rule authoring for KG | Full control, interpretable logic | Doesn't scale beyond top-50 cases, infeasible to maintain | Acceptable for narrowly scoped demo, not general CDI tool |
| Single model for generation and evaluation | Simpler pipeline, lower cost | Self-preference bias, inflated accuracy metrics | Never — always use independent evaluation |
| Synthetic data only, no real clinical notes | Privacy-safe, unlimited generation | Fidelity gap, model learns synthetic patterns not real clinical documentation | Acceptable for initial development, must validate on real data |
| NetworkX for knowledge graph | Python-native, easy development | Performance degrades at scale, limited query optimization | Acceptable for <5k nodes, migrate to graph DB for production |
| Naive sequential agent chaining | Simple to implement, easy to understand | 17x error amplification, brittle failure modes | Never — always add validation gates between agents |
| No assertion classification (negation/uncertainty) | Simpler NER pipeline | High false positive rate on negated/uncertain findings | Never for production clinical coding |
| Small model (1.5B) for structured output | Low latency, cheap inference | Inconsistent formatting, parse errors on long inputs | Only if output validation and retry logic are robust |

---

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| FAISS Index Loading | Loading 70k vectors on every request | Load once at startup, keep in memory with caching |
| Cross-Encoder Reranker | Calling on CPU for all retrievals, adding 300-400ms latency | Use GPU if available (80ms), or use lightweight model (ms-marco-MiniLM-L12, 2-5ms per pair) |
| Hugging Face Model Loading | Re-downloading model weights on each execution | Cache models locally, load at initialization |
| ICD-10 Code Database | Querying external API for each code lookup | Embed code database locally (70k codes = ~50MB uncompressed) |
| EHR Integration | Assuming clean, structured data feed | Build robust parsing for HL7/FHIR variations, handle missing fields gracefully |
| Clinical Terminology Mapping | Direct string matching SNOMED/LOINC/ICD | Use UMLS MetaMap or similar for concept mapping |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Linear scan of all 70k ICD codes | Fast for demo with 5 test cases | Use indexed search (FAISS) or hierarchical filtering | >100 coding requests/day |
| Storing full clinical notes in session state | Works for single-page demo | Use disk caching or database, store only references in session | Notes >50KB or >10 concurrent users |
| Synchronous multi-agent pipeline | Simple to debug, works for demo | Parallelize independent stages (NER + metadata extraction), use async where possible | End-to-end latency >10 seconds |
| NetworkX in-memory graph queries | Easy development, works for 50 nodes | Use graph database (Neo4j) with indexed queries | >5k nodes or >10k edges |
| Single-threaded Streamlit | Default behavior, fine for demo | Deploy with multi-worker config for production | >5 concurrent users |
| CPU-only inference | No GPU setup required | Use GPU for vision models and cross-encoder | Inference time >2 seconds per request |
| Flat file storage for results | Simple, no database needed | Use database with indexing for search/analytics | >1000 processed documents |

---

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| OCR adversarial vulnerability | OCR-readable text overlays can manipulate model outputs (accuracy drops to 0.43) | Treat OCR output as untrusted input, validate against expected document structure, implement immune prompting |
| Storing PHI in Streamlit session state | HIPAA violation if session data logged or leaked | Never store identifiable patient information, use de-identification pipeline |
| Logging full clinical notes | Audit logs contain PHI | Log only metadata (document ID, length, processing time), not content |
| Embedding model memorization | Model may memorize and regurgitate training data PHI | Use differential privacy during embedding training, test for memorization |
| KG relationship inference exposing patient links | Graph queries might reveal patient connections not intended for disclosure | Implement role-based access control on graph queries |
| Model artifacts containing training data | Saved model files may leak training data snippets | Test models for training data extraction attacks before deployment |
| Insufficient access controls on DRG recommendations | Unauthorized users viewing billing-relevant information | Implement authentication and audit trail for all coding recommendations |

---

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No confidence scores on outputs | Users don't know which results to trust | Display confidence for each entity, code, and recommendation |
| Black-box recommendations | "System recommends DRG 291" with no explanation | Show reasoning chain: entities found → codes considered → qualification logic applied |
| No manual override capability | Demo works 90%, users can't fix the 10% errors | Allow users to edit entities, adjust codes, override DRG assignments |
| Overwhelming detail dump | Show all 50 retrieved codes and entire KG reasoning | Progressive disclosure: summary first, details on demand |
| No error recovery flow | Pipeline fails at stage 3, user must restart from beginning | Allow restart from failed stage, save intermediate results |
| Silent failures | Agent fails but UI shows empty results without explanation | Explicit error messages: "NER found no diagnoses — note may need manual review" |
| No way to compare system vs human coder | Users can't validate system accuracy | Side-by-side comparison: system recommendation vs human coding with diff highlighting |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **NER module:** Often missing negation/assertion classification — verify negative and uncertain findings are handled correctly
- [ ] **RAG retrieval:** Often missing metadata filtering — verify retrieval uses clinical context, not just text similarity
- [ ] **Cross-encoder reranker:** Often not tuned for medical domain — verify it's trained/tested on ICD-10 coding task, not generic MS-MARCO
- [ ] **KG qualification rules:** Often cover only happy path — verify edge cases (conflicting codes, missing data, atypical presentations)
- [ ] **Evaluation pipeline:** Often tests only on clean data — verify testing includes noisy OCR, abbreviations, negations, complex cases
- [ ] **Error handling:** Often assumes all upstream outputs valid — verify graceful handling of malformed JSON, missing entities, failed retrievals
- [ ] **Structured output parsing:** Often assumes perfect JSON — verify retry logic and repair strategies for malformed outputs
- [ ] **Multi-page navigation:** Often tested only forward flow — verify back button, refresh, direct URL navigation don't break state
- [ ] **Latency optimization:** Often measured on single request — verify performance under load (10+ concurrent requests)
- [ ] **External validation:** Often tested only on internal data — verify testing on different EHR systems, document types, scan quality
- [ ] **PHI handling:** Often logs full text during development — verify no PHI in logs, session state, cached artifacts before deployment
- [ ] **Scale testing:** Often tested on 10 documents — verify performance on 1000+ documents, full ICD-10 code space, realistic KG size

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Error cascade detected in production | HIGH | 1. Add logging at each agent boundary 2. Implement validation gates 3. Add confidence thresholds for early stopping 4. May require architecture redesign |
| External validation failure (works on internal data, fails on real notes) | HIGH | 1. Collect real failure cases 2. Augment training/test data 3. Retrain or finetune models 4. May require different model architecture |
| Retrieval noise degrading results | MEDIUM | 1. Add metadata filtering layer 2. Tune retrieval parameters (top-k, threshold) 3. Switch to clinical embeddings 4. Add hybrid search |
| Negation/context errors causing false positives | MEDIUM | 1. Add NegEx or ConText algorithm 2. Retag training data with assertions 3. Update prompts to request assertion status 4. Create negation benchmark |
| Small model structured output failures | LOW | 1. Add aggressive output validation 2. Implement retry with simplified schema 3. Consider model upgrade or structured output API |
| LLM-as-judge bias inflating metrics | LOW-MEDIUM | 1. Get human expert validation on sample 2. Switch to different/larger judge model 3. Build clinical accuracy rubric |
| Synthetic data fidelity gap | HIGH | 1. Obtain real de-identified clinical notes 2. Augment synthetic data with realistic noise 3. Retrain on mixed data 4. Rebuild validation pipeline |
| KG coverage insufficient for long-tail cases | MEDIUM-HIGH | 1. Add graceful degradation (LLM fallback) 2. Prioritize expanding coverage based on actual case frequency 3. Consider semi-automated rule extraction |
| Vision OCR noise propagating errors | MEDIUM | 1. Switch to dedicated OCR engine 2. Add confidence scoring and human review flag 3. Implement OCR output validation |
| Streamlit state management breaks | LOW | 1. Refactor state initialization 2. Add state validation at page entry 3. Use caching for expensive operations |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Error cascade (17x amplification) | Phase 1: Architecture Design | Measure end-to-end accuracy vs individual module accuracy; should be >90% of product |
| External validation blindness | Phase 2: NER Module | Test on 3+ different EHR systems/note types before claiming accuracy |
| Retrieval noise | Phase 3: RAG Retrieval | Measure retrieval precision: is correct code in top-10? Should be >80% |
| Context/negation misinterpretation | Phase 2: NER Module | Test on negation benchmark (affirmed vs negated conditions); should be >95% accurate |
| Small model structured output | Phase 4: Coding Agent | Track parse error rate; should be <2% with retry logic |
| LLM-as-judge bias | Phase 5: Evaluation | Compare LLM scores to human expert judgment; correlation should be >0.8 |
| Synthetic data fidelity gap | Phase 1: Data Strategy | Measure performance gap between synthetic and real notes; should be <10% |
| KG coverage vs scalability | Phase 4: KG CDI Agent | Track % cases covered by KG rules; plan for scaling or fallback |
| Vision OCR noise | Phase 2: Image-to-Text | Character error rate <3% on representative document set |
| Streamlit state management | Phase 5: UI Integration | Test all navigation paths (forward, back, refresh, direct URL); zero state loss |

---

## Sources

### Multi-Agent Pipeline Errors
- [Why Your Multi-Agent System is Failing: Escaping the 17x Error Trap](https://towardsdatascience.com/why-your-multi-agent-system-is-failing-escaping-the-17x-error-trap-of-the-bag-of-agents/)
- [Multi-agent workflows often fail. Here's how to engineer ones that don't](https://github.blog/ai-and-ml/generative-ai/multi-agent-workflows-often-fail-heres-how-to-engineer-ones-that-dont/)
- [Prompt-to-Pill: Multi-Agent Drug Discovery and Clinical Simulation Pipeline](https://pmc.ncbi.nlm.nih.gov/articles/PMC12800774/)

### Clinical NLP Pitfalls
- [What Health Tech Gets Wrong About Clinical NLP](https://www.imohealth.com/resources/what-health-tech-gets-wrong-about-clinical-nlp-and-how-to-get-it-right/)
- [Using NLP to extract information from clinical text in EHRs: a systematic review](https://academic.oup.com/jamia/article/33/2/484/8287208)
- [Natural Language Processing in clinical documentation](https://www.imohealth.com/resources/natural-language-processing-101-a-guide-to-nlp-in-clinical-documentation/)

### RAG Retrieval Challenges
- [Retrieval-Augmented Generation (RAG) in Healthcare: A Comprehensive Review](https://www.mdpi.com/2673-2688/6/9/226)
- [Enhancing medical AI with retrieval-augmented generation](https://pmc.ncbi.nlm.nih.gov/articles/PMC12059965/)
- [Retrieval augmented generation for LLMs in healthcare: A systematic review](https://journals.plos.org/digitalhealth/article?id=10.1371/journal.pdig.0000877)

### Biomedical NER Issues
- [Biomedical Flat and Nested Named Entity Recognition: Methods, Challenges, and Advances](https://www.mdpi.com/2076-3417/14/20/9302)
- [How Do Your Biomedical NER Models Generalize to Novel Entities?](https://pmc.ncbi.nlm.nih.gov/articles/PMC9014470/)

### ICD-10 Coding Errors
- [Avoid 8 Common ICD-10 Coding Errors](https://www.codeemr.com/avoid-common-icd-10-coding-errors-claim-denials/)
- [AI-based ICD coding and classification approaches](https://www.sciencedirect.com/science/article/abs/pii/S0957417422020152)
- [Adapting to Evolving ICD-10-CM Guidelines in the Era of AI](https://icd10monitor.medlearn.com/adapting-to-evolving-icd-10-cm-guidelines-in-the-era-of-artificial-intelligence/)

### AI POC Failures
- [Why 70% of AI Projects Fail to Move Beyond Proof of Concept](https://www.ayadata.ai/why-70-of-ai-projects-fail-to-move-beyond-proof-of-concept/)
- [Why Healthcare AI PoCs Fail the Production Test](https://www.boston-technology.com/blog/why-healthcare-ai-pocs-fail-the-production-test)
- [Why your AI Proof of Concept failed (and how to fix it)](https://clarasys.com/insights/thinking/why-your-ai-proof-of-concept-failed-and-how-to-fix-it)

### FAISS and Vector Search
- [Vector Search with FAISS: Approximate Nearest Neighbor Explained](https://pyimagesearch.com/2026/02/16/vector-search-with-faiss-approximate-nearest-neighbor-ann-explained/)
- [The Faiss Library](https://arxiv.org/html/2401.08281v3)

### Small Language Models and Structured Output
- [Evaluating Structured Output Robustness of Small LMs for Clinical Notes](https://arxiv.org/html/2507.01810v1)
- [LLMStructBench: Benchmarking LLM Structured Data Extraction](https://www.researchgate.net/publication/400855630_LLMStructBench_Benchmarking_Large_Language_Model_Structured_Data_Extraction)

### LLM-as-Judge Bias
- [LLM as a Judge: A 2026 Guide](https://labelyourdata.com/articles/llm-as-a-judge)
- [Self-Preference Bias in LLM-as-a-Judge](https://arxiv.org/html/2410.21819v2)
- [Justice or Prejudice? Quantifying Biases in LLM-as-a-Judge](https://llm-judge-bias.github.io/)

### Synthetic vs Real Clinical Data
- [Synthetic data in health care: A narrative review](https://pmc.ncbi.nlm.nih.gov/articles/PMC9931305/)
- [Beyond the Hype: Why Synthetic Data Falls Short in Healthcare](https://www.rgnmed.com/post/beyond-the-hype-why-synthetic-data-falls-short-in-healthcare-and-how-regenmed-circles-closes-the-gap)
- [Evaluation of synthetic EHRs: A systematic review](https://www.sciencedirect.com/science/article/pii/S0925231224010245)

### Cross-Encoder Reranker Performance
- [Best Reranker Models for RAG: Open-Source vs API Comparison](https://docs.bswen.com/blog/2026-02-25-best-reranker-models/)
- [Does Adding a Reranker to RAG Increase Latency?](https://docs.bswen.com/blog/2026-02-25-reranker-latency-impact/)

### Vision-Language Models and OCR
- [OCR-Mediated Modality Dominance in VLMs: Implications for clinical workflows](https://www.medrxiv.org/content/10.64898/2026.02.22.26346828v1.full.pdf)
- [SmolVLM - small yet mighty Vision Language Model](https://huggingface.co/blog/smolvlm)
- [Vision-Language Models for Medical Report Generation: a review](https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2024.1430984/full)

### Streamlit State Management
- [Add statefulness to apps - Streamlit Docs](https://docs.streamlit.io/develop/concepts/architecture/session-state)
- [Session state in multipage app - Streamlit Issues](https://github.com/streamlit/streamlit/issues/5689)
- [Help with session state - multi-page app](https://discuss.streamlit.io/t/help-with-session-state-multi-page-app/43471)

### NetworkX Scalability
- [Data Persistency, Large-Scale Analytics - Biggest NetworkX Challenges](https://memgraph.com/blog/data-persistency-large-scale-data-analytics-and-visualizations-biggest-networkx-challenges)
- [Accelerating NetworkX on NVIDIA GPUs](https://developer.nvidia.com/blog/accelerating-networkx-on-nvidia-gpus-for-high-performance-graph-analytics/)
- [Scaling Biomedical Knowledge Graph Retrieval](https://www.medrxiv.org/content/10.64898/2026.01.12.26343957v1.full.pdf)

---

*Pitfalls research for: Clinical NLP + RAG + Knowledge Graph Multi-Agent CDI Platform*
*Researched: 2026-03-18*
*Confidence: HIGH (25+ authoritative sources, cross-validated across multiple search queries)*
