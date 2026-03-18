# Feature Landscape

**Domain:** Clinical Coding and CDI Intelligence Platform (Interview POC Demo)
**Researched:** 2026-03-18
**Confidence:** MEDIUM

Clinical coding and CDI intelligence platforms operate at the intersection of healthcare documentation, revenue cycle management, and regulatory compliance. This research identifies features for an interview POC demo targeting a Principal AI Scientist role at Solventum HIS.

## Table Stakes

Features users expect in any clinical coding/CDI platform. Missing these makes the demo feel incomplete or non-credible.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **ICD-10-CM Code Extraction** | Core requirement for any coding platform; 95%+ accuracy expected | Medium | MUST demonstrate on real discharge summaries; users expect multi-code assignments per encounter |
| **Clinical NER (Named Entity Recognition)** | Foundation for all downstream tasks; extracts diseases, symptoms, medications, procedures from unstructured text | Medium | ~80% of EHR data is unstructured; NER is the first step in every clinical NLP pipeline |
| **EHR/FHIR Data Ingestion** | Real-world systems MUST integrate with EHRs; FHIR R4 is industry standard as of 2026 | Medium | Demo credibility requires showing FHIR resource parsing (Condition, Procedure, Observation, DocumentReference) |
| **Documentation Gap Detection** | Core CDI function; identifies missing/incomplete documentation that affects reimbursement or quality measures | High | CDI specialists spend 60%+ time identifying gaps; AI automation is the primary value proposition |
| **Compliance Validation** | Built-in validation against coding guidelines (ICD-10 specificity, NCCI edits, payer rules) | High | Audit risk reduction is a top-3 buyer concern; demo must show guideline references |
| **Audit Trail / Explainability** | Regulatory requirement (CMS Program Integrity, False Claims Act 60-day rule); must show "how code was assigned" | High | 2026 regulatory environment demands full traceability: source documentation links, guideline references, decision logic |
| **Confidence Scoring** | Users expect probabilistic output with thresholds for human review | Low | Codes below confidence threshold (typically 0.85-0.90) are flagged for manual review |

## Differentiators

Features that set the demo apart and align with interview talking points (agentic AI, multi-modal, RAG, KG, explainability).

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Agentic AI Architecture** | Demonstrates SOTA 2026 approach; autonomous agents that take actions (not just suggestions) | High | Aligns with Solventum HIS Principal Scientist role; shows architectural thinking beyond simple ML models |
| **Multi-Modal Ingestion** | Handles text, FHIR structured data, AND scanned images (SmolVLM); differentiates from text-only competitors | High | Very few platforms support true multi-modal clinical AI; demonstrates advanced capability |
| **RAG-Based ICD-10 Coding** | Uses retrieval-augmented generation with reranking; research shows 17-26% exact match improvement with RAG | High | Cutting-edge approach; studies show RAG outperforms human coders in ED diagnostic accuracy |
| **Knowledge Graph CDI Agent** | Graph-based reasoning for documentation integrity; visualizes clinical relationships and missing links | Very High | Rare in commercial products; demonstrates research-level capability and explainability |
| **Negation Detection in NER** | Distinguishes positive findings from negative findings (e.g., "no fever" vs "fever present") | Medium | Critical for accuracy; most systems treat as separate pipeline; joint end-to-end models are SOTA |
| **Physician Query Generation** | Automated, compliant query generation with clinical evidence and multiple-choice options | High | High-value CDI feature; reduces CDI specialist workload by 40%+; must follow ACDIS/AHIMA guidelines |
| **Interactive KG Visualization (PyVis)** | Real-time, explorable knowledge graph of clinical relationships | Medium | Strong demo visual; makes complex AI reasoning tangible for non-technical stakeholders |
| **Cross-Encoder Reranking** | Two-stage retrieval (FAISS + cross-encoder) for higher precision ICD-10 coding | Medium | Demonstrates deep technical knowledge; significant accuracy improvement over single-stage retrieval |
| **Quantitative Eval Suite** | Module-level evaluation with explicit targets (e.g., NER F1 > 0.85, coding accuracy > 0.90) | Medium | Rare in demos; shows engineering rigor and understanding of ML operations |

## Anti-Features

Features to explicitly NOT build for an interview POC demo.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Full EHR Integration** | Production EHR integration takes months; unnecessary for demo credibility | Use FHIR R4 synthetic data with realistic structure; show integration architecture diagram |
| **Real-Time Processing at Scale** | Performance optimization is time-consuming; demo is proof-of-concept not production | Process sample encounters; use pre-computed results for complex queries; acknowledge scaling requirements |
| **Comprehensive ICD-10 Coverage** | ICD-10-CM has 72,000+ codes; full coverage requires massive training data | Focus on high-volume diagnosis categories (10-15 common conditions cover 60%+ encounters) |
| **CPT/HCPCS Procedure Coding** | Adds scope without demonstrating new capabilities; ICD-10 diagnosis coding is sufficient | Mention as "future work"; keep demo focused on diagnosis coding and CDI |
| **Billing/RCM Features** | Outside core AI/NLP scope; dilutes technical demonstration | Show how outputs feed downstream RCM (architecture diagram); don't build billing logic |
| **User Authentication/RBAC** | Security features are table stakes for production but irrelevant for technical demo | Single-user Streamlit app is sufficient; mention HIPAA/security in architecture discussion |
| **Mobile Responsiveness** | CDI specialists and coders work on desktop workstations | Desktop-optimized Streamlit UI is appropriate for demo |

## Feature Dependencies

```
FHIR Ingestion
    └──requires──> Clinical NER
                       └──requires──> ICD-10 Code Extraction
                       └──requires──> Documentation Gap Detection
                                          └──requires──> Physician Query Generation

RAG-Based Coding
    └──requires──> FAISS Vector Index
    └──requires──> Embedding Model (bge-small)
    └──requires──> Cross-Encoder Reranker

Knowledge Graph CDI Agent
    └──requires──> Clinical NER
    └──requires──> Entity Relationship Extraction
    └──enhances──> Documentation Gap Detection
    └──enables──> Interactive Visualization

Explainability Layer
    └──requires──> Audit Trail (all modules)
    └──enhances──> Confidence Scoring
    └──enables──> Regulatory Compliance

Multi-Modal Ingestion
    └──requires──> SmolVLM for scanned documents
    └──optional──> Can skip images for text-only demo
```

### Dependency Notes

- **Clinical NER is the foundation**: All downstream tasks (coding, gap detection, KG construction) depend on accurate entity extraction
- **RAG and KG are parallel capabilities**: Either can be removed without breaking core workflow, but both demonstrate advanced AI expertise
- **Explainability is cross-cutting**: Every module should contribute to audit trail, not a separate feature
- **Multi-modal ingestion is a differentiator**: Can be scoped out if time-constrained; text + FHIR still demonstrates strong capability

## MVP Recommendation for Interview Demo

### Launch With (v1 Demo - 5 pages minimum)

Prioritize features that demonstrate AI/ML depth and align with interview talking points.

- [x] **Multi-modal FHIR R4 ingestion** - Shows interoperability understanding; handles Condition, Procedure, Observation resources
- [x] **Clinical NER with negation detection** - Core NLP capability; use biomedical-ner-all model
- [x] **RAG-based ICD-10 coding** - SOTA approach; FAISS + bge-small + cross-encoder + Qwen reasoning
- [x] **Knowledge Graph CDI agent** - Unique differentiator; NetworkX graph with gap detection
- [x] **Explainability layer** - Regulatory compliance; full audit trails with source evidence
- [x] **Interactive KG visualization** - Makes AI reasoning tangible; PyVis is straightforward
- [x] **Streamlit 5-page UI** - Demo/Data Entry/Results/KG Visualization/QA Bot
- [x] **Quantitative eval suite** - Shows engineering rigor; module-level metrics

### Defer for Time Constraints (v1.1)

Features that add value but aren't critical for technical interview.

- [ ] **SmolVLM image ingestion** - Multi-modal is impressive but text+FHIR sufficient; add if time permits
- [ ] **Physician query generation** - High-value CDI feature but adds scope; gap detection is sufficient to show concept
- [ ] **Advanced compliance validation** - Basic guideline references sufficient; full NCCI/LCD/NCD rules are production concern
- [ ] **Batch processing interface** - Single-encounter demo is sufficient; mention batch capability in architecture
- [ ] **Export/reporting features** - Not needed for technical demo; focus on AI capabilities

### Explicitly Out of Scope (v2+)

Features to mention in "future work" but not build for interview.

- [ ] **CPT/HCPCS procedure coding** - Diagnosis coding demonstrates capability
- [ ] **Real-time EHR integration** - Show architecture, use synthetic data
- [ ] **Production-scale performance** - Acknowledge in discussion, don't optimize for demo
- [ ] **User management/RBAC** - Single-user demo appropriate
- [ ] **Billing/claims submission** - Outside AI/ML scope

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Interview Impact | Priority |
|---------|------------|---------------------|------------------|----------|
| ICD-10 Code Extraction (RAG) | HIGH | MEDIUM | HIGH | P0 |
| Clinical NER + Negation | HIGH | MEDIUM | HIGH | P0 |
| FHIR R4 Ingestion | HIGH | LOW | MEDIUM | P0 |
| Knowledge Graph CDI Agent | HIGH | HIGH | VERY HIGH | P0 |
| Explainability/Audit Trail | HIGH | MEDIUM | HIGH | P0 |
| Interactive KG Visualization | MEDIUM | LOW | HIGH | P1 |
| Agentic Architecture | LOW | MEDIUM | VERY HIGH | P1 |
| Physician Query Generation | HIGH | MEDIUM | MEDIUM | P2 |
| SmolVLM Multi-Modal | LOW | HIGH | HIGH | P2 |
| Quantitative Eval Suite | MEDIUM | MEDIUM | HIGH | P1 |
| Compliance Validation | HIGH | MEDIUM | MEDIUM | P2 |
| Confidence Scoring | HIGH | LOW | MEDIUM | P1 |

**Priority key:**
- P0: Must have for credible demo; build first
- P1: Should have; strong interview impact; build if time permits
- P2: Nice to have; mention in architecture or future work

## Competitive Feature Analysis

Based on market leaders (3M CodeFinder, Nuance Clintegrity, Dolbey Fusion CAC):

| Feature | 3M CodeFinder | Nuance Clintegrity | Dolbey Fusion CAC | ClinIQ POC Approach |
|---------|---------------|-------------------|-------------------|---------------------|
| **NLP-based NER** | Rule-based + terminology mapping | AI-driven NLP + CAC | AI/ML with CDI Alerts | Transformer-based biomedical-ner-all + negation |
| **ICD-10 Automation** | Logic-based encoder | AI-powered with HCC support | ML-based code suggestions | RAG with FAISS + cross-encoder reranking |
| **CDI Capabilities** | Basic gap detection | Integrated CDI module | CDI Alerts with prioritization | Knowledge graph-based gap detection |
| **Explainability** | Guideline references | Audit management module | Evidence markers | Full audit trail + KG visualization |
| **EHR Integration** | Epic, Cerner, broad HIS | Major EHR systems | Flexible EHR integration | FHIR R4 synthetic data (demo) |
| **Query Generation** | Manual workflow | Integrated query tools | Evidence-driven queries | Automated with clinical evidence (KG-based) |
| **Multi-Modal** | Text only | Text only | Text only | **Text + FHIR + images (SmolVLM)** |
| **Architecture** | Traditional CAC | AI-enhanced workflows | AI/ML-based | **Agentic AI with autonomous agents** |
| **Visualization** | Reports/dashboards | Standard reporting | Performance dashboards | **Interactive knowledge graph (PyVis)** |
| **RAG/Retrieval** | N/A | N/A | N/A | **FAISS + bge-small + cross-encoder** |

**ClinIQ's competitive positioning for interview:**
- **Research-level capabilities**: RAG, KG, agentic AI, multi-modal - features rarely seen in commercial products
- **Explainability-first**: Full audit trails and interactive KG visualization address 2026 regulatory demands
- **Modern AI stack**: Transformers, FAISS, cross-encoders vs rule-based/legacy ML in competitors
- **Architecture thinking**: Demonstrates system design skills beyond model selection

## Sources

### Clinical Coding Software Features
- [Best Autonomous Clinical Coding Reviews 2026 | Gartner Peer Insights](https://www.gartner.com/reviews/market/autonomous-clinical-coding)
- [10 Essential Medical Coding Software for 2026 Efficiency - Neutech](https://neutech.co/blog/10-essential-medical-coding-software-for-2026-efficiency/)
- [Best 10 AI Medical Coders in 2026 | Accuracy & ROI](https://www.sully.ai/blog/best-10-ai-medical-coders-in-2025)

### CDI Platform Capabilities
- [Top 5 Clinical Documentation Improvement Software in 2026](https://www.mbwrcm.com/the-revenue-cycle-blog/clinical-documentation-improvement-software-hospitals)
- [Cleo Health Debuts Acute Care OS at HIMSS 2026](https://www.lelezard.com/en/news-22142042.html)
- [Clinical Documentation Improvement (CDI) Software - AGS Health](https://www.agshealth.com/ai-platform/computer-assisted-cdi/)

### ICD-10 Coding Automation AI
- [Medical Coding Automation for ICD-10 & CPT (2026 Guide) | Ventus AI](https://www.ventus.ai/blog/medical-coding-automation-icd10-cpt-2026-guide/)
- [AI Scribe ICD-10 Coding: Complete Diagnosis Code Automation Guide 2026](https://s10.ai/blog/ai-scribe-icd-10-coding)
- [Why Human-Centered AI Matters in Modern ICD-10 Coding | Netsmart](https://www.ntst.com/blog/2026/why-human-centered-ai-matters-in-modern-icd-10-coding)

### Competitive Products
- [3M Codefinder Reviews 2026: Details, Pricing, & Features | G2](https://www.g2.com/products/3m-codefinder/reviews)
- [Clintegrity Facility Coding - Best Encoder Solution | Nuance](https://www.nuance.com/healthcare/provider-solutions/coding-compliance/facility-coding.html)
- [Fusion CDI | Dolbey Systems](https://www.dolbey.com/solutions/coding/fusion-cdi/)

### Explainability and Audit Requirements
- [Transparent AI for Medical Coding | Why Black Box Tools Fail](https://blog.nym.health/transparent-ai-for-medical-coding)
- [AI in Medical Auditing: Managing Compliance Risk in 2026](https://namas.co/ai-compliance-risk-medical-auditing-2026/)
- [How AI Powers Explainable and Auditable Medical Coding](https://blog.nym.health/explainable-ai-in-healthcare)

### Knowledge Graphs in Clinical Coding
- [The Role of Knowledge Graphs in Healthcare | Medium](https://medium.com/@adnanmasood/the-role-of-knowledge-graphs-in-healthcare-7109a8c33122)
- [Explainable Prediction of Medical Codes With Knowledge Graphs - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC7456905/)
- [Clinical Knowledge Graph Documentation](https://ckg.readthedocs.io/en/latest/INTRO.html)

### RAG and Multi-Modal AI
- [Assessing Retrieval-Augmented LLM Performance in ED ICD-10-CM Coding - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC11527068/)
- [Large Language Models are good medical coders](https://arxiv.org/pdf/2407.12849)
- [Multi-modal AI in precision medicine - Frontiers](https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2025.1743921/full)

### Agentic AI in Clinical Coding
- [AI Medical Coding Automation with Agentic AI (2026)](https://caliberfocus.com/ai-medical-coding-automation)
- [Agentic AI in Healthcare: Autonomous Patient Journey Management](https://www.webkorps.com/blog/agentic-ai-in-healthcare/)
- [GitHub - Awesome-AI-Agents-for-Healthcare](https://github.com/AgenticHealthAI/Awesome-AI-Agents-for-Healthcare)

### Clinical NER and Negation Detection
- [Named Entity Recognition in EHRs: A Methodological Review - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC10651400/)
- [End-to-End Joint Entity Extraction and Negation Detection](https://link.springer.com/chapter/10.1007/978-3-030-24409-5_13)
- [Clinical Named Entity Recognition Using Deep Learning - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC5977567/)

### Physician Query Best Practices
- [Guidelines For Achieving Compliant Physician Queries - AGS Health](https://www.agshealth.com/blog/guidelines-for-achieving-compliant-physician-queries/)
- [Five Steps To An Effective Physician Query Process - AGS Health](https://www.agshealth.com/blog/five-steps-to-an-effective-physician-query-process/)

---
*Feature research for: Clinical Coding and CDI Intelligence Platform (Interview POC)*
*Researched: 2026-03-18*
*Confidence: MEDIUM - Based on market analysis and 2026 technical literature; validated across multiple commercial products and research papers*
