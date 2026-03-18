"""
End-to-end pipeline orchestrator.

Chains ingestion -> NER -> RAG coding with error handling and performance tracking.
Optionally extends with CDI analysis (Stage 4) and full audit trail instrumentation.
"""

import time
import logging
import uuid
from typing import Optional, Union
from pathlib import Path

from pydantic import BaseModel, Field

from cliniq.models import ClinicalDocument, NLUResult, CodingResult
from cliniq.models.cdi import CDIReport
from cliniq.models.audit import AuditTrail
from cliniq.modules.m1_ingest import ingest
from cliniq.modules.m2_nlu import extract_entities
from cliniq.modules.m3_rag_coding import code_entities
from cliniq.modules.m4_cdi import run_cdi_analysis
from cliniq.modules.m5_explainability import AuditTrailBuilder, link_evidence_spans

logger = logging.getLogger(__name__)


class PipelineResult(BaseModel):
    """Complete pipeline output with all stage results and timing."""

    document: ClinicalDocument
    nlu_result: NLUResult
    coding_result: CodingResult
    processing_time_ms: float
    errors: list[str] = Field(default_factory=list)
    cdi_report: Optional[CDIReport] = None
    audit_trail: Optional[AuditTrail] = None


def run_pipeline(
    input_data: Union[str, dict, Path],
    skip_coding: bool = False
) -> PipelineResult:
    """
    Run the end-to-end clinical documentation pipeline.

    Args:
        input_data: FHIR bundle (dict), plain text (str), or image path (str/Path)
        skip_coding: If True, skip the RAG coding stage

    Returns:
        PipelineResult with all stage outputs, timing, and errors
    """
    start_time = time.perf_counter()
    errors = []

    # Stage 1: Ingestion
    try:
        logger.info("Stage 1: Ingesting document...")
        document = ingest(input_data)
        logger.info(f"Ingestion complete: {document.metadata.source_type} modality, "
                   f"confidence={document.modality_confidence:.2f}")
    except Exception as e:
        error_msg = f"Ingestion failed: {str(e)}"
        logger.error(error_msg)
        errors.append(error_msg)
        # Return early with empty results
        end_time = time.perf_counter()
        return PipelineResult(
            document=ClinicalDocument(
                metadata={"source_type": "unknown"},
                raw_narrative="",
                modality_confidence=0.0
            ),
            nlu_result=NLUResult(entities=[]),
            coding_result=CodingResult(
                principal_diagnosis=None,
                secondary_codes=[],
                complication_codes=[],
                sequencing_rationale="",
                retrieval_stats={}
            ),
            processing_time_ms=(end_time - start_time) * 1000,
            errors=errors
        )

    # Stage 2: NER
    try:
        logger.info("Stage 2: Extracting clinical entities...")
        nlu_result = extract_entities(document.raw_narrative)
        logger.info(f"NER complete: {nlu_result.entity_count} entities extracted "
                   f"({len(nlu_result.diagnoses)} diagnoses, "
                   f"{len(nlu_result.procedures)} procedures)")

        if nlu_result.entity_count == 0:
            warning_msg = "NER extracted 0 entities from narrative"
            logger.warning(warning_msg)
            # Continue with empty NLU result
    except Exception as e:
        error_msg = f"NER failed: {str(e)}"
        logger.error(error_msg)
        errors.append(error_msg)
        # Continue with empty NLU result
        nlu_result = NLUResult(entities=[])

    # Stage 3: RAG Coding (unless skipped)
    coding_result = None
    if skip_coding:
        logger.info("Stage 3: Skipped (skip_coding=True)")
        coding_result = CodingResult(
            principal_diagnosis=None,
            secondary_codes=[],
            complication_codes=[],
            sequencing_rationale="Coding skipped",
            retrieval_stats={}
        )
    else:
        try:
            logger.info("Stage 3: RAG-based ICD-10 coding...")
            coding_result = code_entities(nlu_result, clinical_context=document.raw_narrative)
            principal_code = coding_result.principal_diagnosis.icd10_code if coding_result.principal_diagnosis else None
            logger.info(f"Coding complete: Principal={principal_code}, "
                       f"Secondary={len(coding_result.secondary_codes)}, "
                       f"Complications={len(coding_result.complication_codes)}")
        except Exception as e:
            error_msg = f"RAG coding failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
            # Return partial result with empty coding
            coding_result = CodingResult(
                principal_diagnosis=None,
                secondary_codes=[],
                complication_codes=[],
                sequencing_rationale="",
                retrieval_stats={}
            )

    # Calculate total time
    end_time = time.perf_counter()
    processing_time_ms = (end_time - start_time) * 1000

    logger.info(f"Pipeline complete: {processing_time_ms:.1f}ms total, {len(errors)} errors")

    return PipelineResult(
        document=document,
        nlu_result=nlu_result,
        coding_result=coding_result,
        processing_time_ms=processing_time_ms,
        errors=errors
    )


def run_pipeline_audited(
    input_data: Union[str, dict, Path],
    skip_coding: bool = False,
    skip_cdi: bool = False,
    use_llm_queries: bool = True,
) -> PipelineResult:
    """
    Run the end-to-end pipeline with full audit trail instrumentation and CDI analysis.

    Wraps each pipeline stage with timing and trace capture, adds CDI analysis
    as Stage 4, and produces a PipelineResult with cdi_report and audit_trail.

    Args:
        input_data: FHIR bundle (dict), plain text (str), or image path (str/Path)
        skip_coding: If True, skip the RAG coding stage
        skip_cdi: If True, skip the CDI analysis stage
        use_llm_queries: If True, generate physician queries via Qwen LLM.
            If False, use template fallback (faster for testing).

    Returns:
        PipelineResult with all stage outputs, cdi_report, audit_trail, timing, and errors
    """
    start_time = time.perf_counter()
    errors = []

    # Create audit trail builder with auto-generated case_id
    case_id = uuid.uuid4().hex[:8]
    audit = AuditTrailBuilder(case_id=case_id)

    # Stage 1: Ingestion (instrumented)
    stage1_start = time.perf_counter()
    try:
        logger.info("[Audited] Stage 1: Ingesting document...")
        document = ingest(input_data)
        stage1_ms = (time.perf_counter() - stage1_start) * 1000

        audit.record_stage(
            stage="ingestion",
            processing_time_ms=stage1_ms,
            input_summary=str(type(input_data).__name__),
            output_summary=f"{document.metadata.source_type}, confidence={document.modality_confidence:.2f}",
        )

        logger.info(f"Ingestion complete: {document.metadata.source_type} modality, "
                   f"confidence={document.modality_confidence:.2f}")
    except Exception as e:
        stage1_ms = (time.perf_counter() - stage1_start) * 1000
        error_msg = f"Ingestion failed: {str(e)}"
        logger.error(error_msg)
        errors.append(error_msg)

        audit.record_stage(
            stage="ingestion",
            processing_time_ms=stage1_ms,
            input_summary=str(type(input_data).__name__),
            output_summary=f"FAILED: {str(e)[:100]}",
        )

        # Return early with empty results
        end_time = time.perf_counter()
        return PipelineResult(
            document=ClinicalDocument(
                metadata={"source_type": "unknown"},
                raw_narrative="",
                modality_confidence=0.0
            ),
            nlu_result=NLUResult(entities=[]),
            coding_result=CodingResult(
                principal_diagnosis=None,
                secondary_codes=[],
                complication_codes=[],
                sequencing_rationale="",
                retrieval_stats={}
            ),
            processing_time_ms=(end_time - start_time) * 1000,
            errors=errors,
            audit_trail=audit.get_trail(),
        )

    # Stage 2: NER (instrumented)
    stage2_start = time.perf_counter()
    try:
        logger.info("[Audited] Stage 2: Extracting clinical entities...")
        nlu_result = extract_entities(document.raw_narrative)
        stage2_ms = (time.perf_counter() - stage2_start) * 1000

        entity_details = {
            "diagnoses": len(nlu_result.diagnoses),
            "procedures": len(nlu_result.procedures),
            "total_entities": nlu_result.entity_count,
        }

        audit.record_stage(
            stage="ner",
            processing_time_ms=stage2_ms,
            input_summary=f"{len(document.raw_narrative)} chars",
            output_summary=f"{nlu_result.entity_count} entities",
            details=entity_details,
        )

        logger.info(f"NER complete: {nlu_result.entity_count} entities extracted "
                   f"({len(nlu_result.diagnoses)} diagnoses, "
                   f"{len(nlu_result.procedures)} procedures)")

        if nlu_result.entity_count == 0:
            warning_msg = "NER extracted 0 entities from narrative"
            logger.warning(warning_msg)
    except Exception as e:
        stage2_ms = (time.perf_counter() - stage2_start) * 1000
        error_msg = f"NER failed: {str(e)}"
        logger.error(error_msg)
        errors.append(error_msg)
        nlu_result = NLUResult(entities=[])

        audit.record_stage(
            stage="ner",
            processing_time_ms=stage2_ms,
            input_summary=f"{len(document.raw_narrative)} chars",
            output_summary=f"FAILED: {str(e)[:100]}",
        )

    # Stage 3: RAG Coding (instrumented, unless skipped)
    coding_result = None
    if skip_coding:
        logger.info("[Audited] Stage 3: Skipped (skip_coding=True)")
        coding_result = CodingResult(
            principal_diagnosis=None,
            secondary_codes=[],
            complication_codes=[],
            sequencing_rationale="Coding skipped",
            retrieval_stats={}
        )
        audit.record_stage(
            stage="rag",
            processing_time_ms=0.0,
            input_summary="skipped",
            output_summary="Coding skipped",
        )
    else:
        stage3_start = time.perf_counter()
        try:
            logger.info("[Audited] Stage 3: RAG-based ICD-10 coding...")
            coding_result = code_entities(nlu_result, clinical_context=document.raw_narrative)
            stage3_ms = (time.perf_counter() - stage3_start) * 1000

            principal_code = coding_result.principal_diagnosis.icd10_code if coding_result.principal_diagnosis else None
            n_secondary = len(coding_result.secondary_codes)

            # Link evidence spans (EXPL-02)
            evidence_spans = link_evidence_spans(coding_result, document.raw_narrative)
            for code, spans in evidence_spans.items():
                for span in spans:
                    audit.add_evidence(code, span)

            # Extract retrieval timing from retrieval_stats if available
            rag_time = coding_result.retrieval_stats.get("total_retrieval_time_ms", stage3_ms)

            audit.record_stage(
                stage="rag",
                processing_time_ms=rag_time,
                input_summary=f"{nlu_result.entity_count} entities",
                output_summary=f"principal={principal_code}, {n_secondary} secondary",
            )

            logger.info(f"Coding complete: Principal={principal_code}, "
                       f"Secondary={n_secondary}, "
                       f"Complications={len(coding_result.complication_codes)}")
        except Exception as e:
            stage3_ms = (time.perf_counter() - stage3_start) * 1000
            error_msg = f"RAG coding failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
            coding_result = CodingResult(
                principal_diagnosis=None,
                secondary_codes=[],
                complication_codes=[],
                sequencing_rationale="",
                retrieval_stats={}
            )
            audit.record_stage(
                stage="rag",
                processing_time_ms=stage3_ms,
                input_summary=f"{nlu_result.entity_count} entities",
                output_summary=f"FAILED: {str(e)[:100]}",
            )

    # Stage 4: CDI Analysis (instrumented, unless skip_cdi=True)
    cdi_report = None
    if skip_cdi:
        logger.info("[Audited] Stage 4: Skipped (skip_cdi=True)")
    else:
        stage4_start = time.perf_counter()
        try:
            logger.info("[Audited] Stage 4: CDI analysis...")
            clinical_text = document.raw_narrative

            cdi_report = run_cdi_analysis(
                nlu_result, coding_result, clinical_text, use_llm_queries
            )
            stage4_ms = (time.perf_counter() - stage4_start) * 1000

            # Count total codes for input summary
            n_codes = 0
            if coding_result.principal_diagnosis:
                n_codes += 1
            n_codes += len(coding_result.secondary_codes)
            n_codes += len(coding_result.complication_codes)

            # Collect CoT traces from CDI gaps
            cot_traces = [
                gap.cot_trace for gap in cdi_report.documentation_gaps
                if gap.cot_trace
            ]

            audit.record_stage(
                stage="cdi",
                processing_time_ms=stage4_ms,
                input_summary=f"{n_codes} codes",
                output_summary=(
                    f"{cdi_report.gap_count} gaps, "
                    f"{cdi_report.conflict_count} conflicts, "
                    f"{len(cdi_report.missed_diagnoses)} missed dx"
                ),
                cot_traces=cot_traces,
            )

            logger.info(
                f"CDI complete: {cdi_report.gap_count} gaps, "
                f"{cdi_report.conflict_count} conflicts, "
                f"{len(cdi_report.missed_diagnoses)} missed dx, "
                f"completeness={cdi_report.completeness_score:.2f}"
            )
        except Exception as e:
            stage4_ms = (time.perf_counter() - stage4_start) * 1000
            error_msg = f"CDI analysis failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

            audit.record_stage(
                stage="cdi",
                processing_time_ms=stage4_ms,
                input_summary="N/A",
                output_summary=f"FAILED: {str(e)[:100]}",
            )

    # Calculate total time
    end_time = time.perf_counter()
    processing_time_ms = (end_time - start_time) * 1000

    logger.info(f"Audited pipeline complete: {processing_time_ms:.1f}ms total, {len(errors)} errors")

    return PipelineResult(
        document=document,
        nlu_result=nlu_result,
        coding_result=coding_result,
        processing_time_ms=processing_time_ms,
        errors=errors,
        cdi_report=cdi_report,
        audit_trail=audit.get_trail(),
    )


def run_pipeline_batch(
    inputs: list[Union[str, dict, Path]],
    skip_coding: bool = False
) -> list[PipelineResult]:
    """
    Process multiple inputs sequentially through the pipeline.

    Args:
        inputs: List of FHIR bundles, text notes, or image paths
        skip_coding: If True, skip the RAG coding stage for all inputs

    Returns:
        List of PipelineResult, one per input
    """
    logger.info(f"Starting batch pipeline: {len(inputs)} inputs")
    results = []

    for i, input_data in enumerate(inputs, 1):
        logger.info(f"Processing input {i}/{len(inputs)}...")
        result = run_pipeline(input_data, skip_coding=skip_coding)
        results.append(result)

    logger.info(f"Batch pipeline complete: {len(results)} results")
    return results


def run_pipeline_audited_batch(
    inputs: list[Union[str, dict, Path]],
    skip_coding: bool = False,
    skip_cdi: bool = False,
    use_llm_queries: bool = True,
) -> list[PipelineResult]:
    """
    Process multiple inputs sequentially through the audited pipeline.

    Args:
        inputs: List of FHIR bundles, text notes, or image paths
        skip_coding: If True, skip the RAG coding stage for all inputs
        skip_cdi: If True, skip the CDI analysis stage for all inputs
        use_llm_queries: If True, generate physician queries via Qwen LLM

    Returns:
        List of PipelineResult with cdi_report and audit_trail, one per input
    """
    logger.info(f"Starting audited batch pipeline: {len(inputs)} inputs")
    results = []

    for i, input_data in enumerate(inputs, 1):
        logger.info(f"Processing input {i}/{len(inputs)} (audited)...")
        result = run_pipeline_audited(
            input_data,
            skip_coding=skip_coding,
            skip_cdi=skip_cdi,
            use_llm_queries=use_llm_queries,
        )
        results.append(result)

    logger.info(f"Audited batch pipeline complete: {len(results)} results")
    return results
