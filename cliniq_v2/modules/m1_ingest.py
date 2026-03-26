"""
Multi-modal ingestion module for clinical documents (ClinIQ v2).

Reuses FHIR and text parsers from cliniq v1 (model-agnostic).
Replaces local vision model with GPT-4o vision API for image parsing.
"""

import base64
from pathlib import Path
from typing import Union
from uuid import uuid4
from datetime import datetime

from cliniq.models.document import ClinicalDocument, DocumentMetadata
from cliniq.modules.m1_ingest import detect_modality, parse_fhir, parse_text

from cliniq_v2.api_client import OpenAIClient
from cliniq_v2.config import MODEL_REGISTRY


# MIME type mapping for common image formats
_MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".bmp": "image/bmp",
    ".tiff": "image/tiff",
}


def parse_image(image_path: str) -> ClinicalDocument:
    """
    Extract clinical text from an image using GPT-4o vision API.

    Args:
        image_path: Path to the image file.

    Returns:
        ClinicalDocument with extracted text, source_type="image".

    Raises:
        FileNotFoundError: If image file does not exist.
    """
    path = Path(image_path)

    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")
    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")

    # Read and base64-encode the image
    with open(path, "rb") as f:
        b64_image = base64.b64encode(f.read()).decode("utf-8")

    # Detect MIME type from file suffix
    mime_type = _MIME_TYPES.get(path.suffix.lower(), "image/png")

    # Call GPT-4o vision API
    client = OpenAIClient().client
    response = client.chat.completions.create(
        model=MODEL_REGISTRY["VISION"],
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{b64_image}",
                            "detail": "high",
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "Extract all clinical text from this medical document. "
                            "Include all diagnoses, procedures, medications, and "
                            "clinical findings exactly as written."
                        ),
                    },
                ],
            }
        ],
        max_tokens=1024,
        temperature=0.0,
    )

    extracted_text = response.choices[0].message.content or ""

    # Create metadata
    metadata = DocumentMetadata(
        patient_id=str(uuid4()),
        encounter_id=str(uuid4()),
        source_type="image",
        timestamp=datetime.now(),
    )

    return ClinicalDocument(
        metadata=metadata,
        raw_narrative=extracted_text.strip(),
        structured_facts=[],
        modality_confidence=0.90,
        extraction_trace=f"Extracted from image using GPT-4o vision (model: {MODEL_REGISTRY['VISION']})",
    )


def ingest(input_data: Union[str, Path, dict]) -> ClinicalDocument:
    """
    Main ingestion router.

    Detects input modality and dispatches to appropriate parser.
    FHIR and text parsing are delegated to cliniq v1 (model-agnostic).
    Image parsing uses GPT-4o vision.

    Args:
        input_data: FHIR dict, FHIR JSON string, plain text, or image path.

    Returns:
        Validated ClinicalDocument.

    Raises:
        ValueError: If modality detection or parsing fails.
    """
    modality = detect_modality(input_data)

    if modality == "fhir":
        return parse_fhir(input_data)
    elif modality == "text":
        return parse_text(str(input_data))
    elif modality == "image":
        return parse_image(str(input_data))
    else:
        raise ValueError(f"Unknown modality: {modality}")
