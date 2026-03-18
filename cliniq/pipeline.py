"""
End-to-end pipeline orchestrator.

Chains ingestion -> NER -> RAG coding with error handling and performance tracking.
"""

import time
import logging
from typing import Union
from pathlib import Path

from pydantic import BaseModel, Field

from cliniq.models import ClinicalDocument, NLUResult, CodingResult
from cliniq.modules.m1_ingest import ingest
from cliniq.modules.m2_nlu import extract_entities
from cliniq.modules.m3_rag_coding import code_entities

logger = logging.getLogger(__name__)


class PipelineResult(BaseModel):
    """Complete pipeline output with all stage results and timing."""

    document: ClinicalDocument
    nlu_result: NLUResult
    coding_result: CodingResult
    processing_time_ms: float
    errors: list[str] = Field(default_factory=list)


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
