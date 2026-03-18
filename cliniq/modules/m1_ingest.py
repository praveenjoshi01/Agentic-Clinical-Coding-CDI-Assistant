"""
Multi-modal ingestion module for clinical documents.

Handles FHIR R4 bundles, plain text, and image-based documents.
Routes input to appropriate parser and returns validated ClinicalDocument.
"""

import json
from pathlib import Path
from typing import Literal, Union
from uuid import uuid4
from datetime import datetime

from PIL import Image

from cliniq.models.document import ClinicalDocument, DocumentMetadata
from cliniq.model_manager import ModelManager


def detect_modality(input_data: Union[str, Path, dict]) -> Literal["fhir", "text", "image"]:
    """
    Detect the modality of input data.

    Args:
        input_data: Raw input (string, Path, or dict)

    Returns:
        Detected modality: "fhir", "text", or "image"

    Raises:
        ValueError: If input type is unrecognized
    """
    # Check if it's a file path (string or Path object)
    if isinstance(input_data, (str, Path)):
        path_str = str(input_data)
        # Check for image extensions
        if path_str.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
            return "image"

        # Try to parse as JSON
        try:
            parsed = json.loads(path_str)
            if isinstance(parsed, dict) and "resourceType" in parsed:
                return "fhir"
            else:
                # Valid JSON but not FHIR
                return "text"
        except (json.JSONDecodeError, ValueError):
            # Not valid JSON, treat as plain text
            return "text"

    # If it's already a dict, check for FHIR structure
    elif isinstance(input_data, dict):
        if "resourceType" in input_data:
            return "fhir"
        else:
            raise ValueError("Dictionary input must have 'resourceType' field for FHIR detection")

    else:
        raise ValueError(f"Unrecognized input type: {type(input_data)}")


def parse_fhir(fhir_data: Union[dict, str]) -> ClinicalDocument:
    """
    Parse FHIR R4 Bundle into ClinicalDocument.

    Args:
        fhir_data: FHIR Bundle as dict or JSON string

    Returns:
        ClinicalDocument with extracted narrative and structured facts

    Raises:
        ValueError: If FHIR validation fails
    """
    # Import FHIR R4B resources (not default R5)
    from fhir.resources.r4b.bundle import Bundle
    from fhir.resources.r4b.condition import Condition
    from fhir.resources.r4b.procedure import Procedure
    from fhir.resources.r4b.encounter import Encounter
    from fhir.resources.r4b.documentreference import DocumentReference
    from fhir.resources.r4b.patient import Patient

    # Parse string to dict if needed
    if isinstance(fhir_data, str):
        fhir_data = json.loads(fhir_data)

    try:
        # Validate FHIR Bundle
        bundle = Bundle.model_validate(fhir_data)
    except Exception as e:
        raise ValueError(f"FHIR validation failed: {e}")

    # Extract data from bundle entries
    narrative_parts = []
    structured_facts = []
    patient_id = None
    encounter_id = None

    if bundle.entry:
        for entry in bundle.entry:
            if not entry.resource:
                continue

            resource = entry.resource
            resource_type = resource.resource_type

            # Extract patient ID
            if resource_type == "Patient":
                patient_id = resource.id or str(uuid4())

            # Extract encounter ID
            elif resource_type == "Encounter":
                encounter_id = resource.id or str(uuid4())
                if resource.type:
                    for type_coding in resource.type:
                        if type_coding.text:
                            narrative_parts.append(f"Encounter: {type_coding.text}")
                            structured_facts.append({
                                "type": "encounter",
                                "text": type_coding.text,
                                "resource_type": "Encounter"
                            })

            # Extract conditions
            elif resource_type == "Condition":
                if resource.code and resource.code.text:
                    condition_text = resource.code.text
                    narrative_parts.append(f"Condition: {condition_text}")

                    fact = {
                        "type": "condition",
                        "text": condition_text,
                        "resource_type": "Condition"
                    }

                    # Add clinical status
                    if resource.clinicalStatus and resource.clinicalStatus.text:
                        fact["clinical_status"] = resource.clinicalStatus.text

                    # Add coding systems
                    if resource.code.coding:
                        codings = []
                        for coding in resource.code.coding:
                            if coding.system and coding.code:
                                codings.append({
                                    "system": coding.system,
                                    "code": coding.code,
                                    "display": coding.display
                                })
                        if codings:
                            fact["codings"] = codings

                    structured_facts.append(fact)

            # Extract procedures
            elif resource_type == "Procedure":
                if resource.code and resource.code.text:
                    procedure_text = resource.code.text
                    narrative_parts.append(f"Procedure: {procedure_text}")

                    fact = {
                        "type": "procedure",
                        "text": procedure_text,
                        "resource_type": "Procedure"
                    }

                    # Add status
                    if resource.status:
                        fact["status"] = resource.status

                    structured_facts.append(fact)

            # Extract document reference text
            elif resource_type == "DocumentReference":
                if resource.content:
                    for content in resource.content:
                        if content.attachment and content.attachment.data:
                            # Decode base64 attachment if needed
                            try:
                                import base64
                                decoded = base64.b64decode(content.attachment.data).decode('utf-8')
                                narrative_parts.append(decoded)
                            except Exception:
                                pass

    # Generate IDs if not found
    if not patient_id:
        patient_id = str(uuid4())
    if not encounter_id:
        encounter_id = str(uuid4())

    # Join narrative parts
    raw_narrative = "\n".join(narrative_parts) if narrative_parts else "No narrative extracted from FHIR bundle."

    # Create metadata
    metadata = DocumentMetadata(
        patient_id=patient_id,
        encounter_id=encounter_id,
        source_type="fhir",
        timestamp=datetime.now()
    )

    # Create and return ClinicalDocument
    return ClinicalDocument(
        metadata=metadata,
        raw_narrative=raw_narrative,
        structured_facts=structured_facts,
        modality_confidence=1.0,
        extraction_trace="Parsed from FHIR R4B Bundle"
    )


def parse_text(text: str) -> ClinicalDocument:
    """
    Wrap plain text into ClinicalDocument.

    Args:
        text: Plain clinical note text

    Returns:
        ClinicalDocument with text as raw_narrative
    """
    metadata = DocumentMetadata(
        patient_id=str(uuid4()),
        encounter_id=str(uuid4()),
        source_type="text",
        timestamp=datetime.now()
    )

    return ClinicalDocument(
        metadata=metadata,
        raw_narrative=text.strip(),
        structured_facts=[],
        modality_confidence=1.0,
        extraction_trace="Direct text input"
    )


def parse_image(image_path: Union[str, Path]) -> ClinicalDocument:
    """
    Extract text from clinical image using SmolVLM.

    Args:
        image_path: Path to image file

    Returns:
        ClinicalDocument with extracted text

    Raises:
        FileNotFoundError: If image file doesn't exist
        Exception: If model loading or inference fails
    """
    image_path = Path(image_path)

    # Validate file exists
    if not image_path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    if not image_path.is_file():
        raise ValueError(f"Path is not a file: {image_path}")

    try:
        # Load model and processor
        model, processor = ModelManager().get_multimodal()

        # Load image
        image = Image.open(image_path)

        # Build chat message
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image"},
                    {
                        "type": "text",
                        "text": "Extract all clinical text from this medical document. Include all diagnoses, procedures, medications, and clinical findings exactly as written."
                    }
                ]
            }
        ]

        # Apply chat template
        prompt = processor.apply_chat_template(messages, add_generation_prompt=True)

        # Process inputs
        inputs = processor(text=prompt, images=[image], return_tensors="pt")

        # Generate
        generated_ids = model.generate(**inputs, max_new_tokens=1024)

        # Decode
        generated_text = processor.batch_decode(
            generated_ids,
            skip_special_tokens=True
        )[0]

        # Clean extracted text - remove chat template artifacts
        # The output typically includes the prompt + assistant response
        # We want only the assistant's response
        if "Assistant:" in generated_text:
            extracted_text = generated_text.split("Assistant:")[-1].strip()
        elif "\n\n" in generated_text:
            # Sometimes the response starts after double newline
            extracted_text = generated_text.split("\n\n")[-1].strip()
        else:
            extracted_text = generated_text.strip()

        # Calculate confidence heuristic based on output length
        # Longer, more detailed extractions get higher confidence
        # Clamp between 0.4 and 0.85
        text_length = len(extracted_text)
        confidence = min(0.85, max(0.4, text_length / 500))

        # Create metadata
        metadata = DocumentMetadata(
            patient_id=str(uuid4()),
            encounter_id=str(uuid4()),
            source_type="image",
            timestamp=datetime.now()
        )

        # Create and return ClinicalDocument
        return ClinicalDocument(
            metadata=metadata,
            raw_narrative=extracted_text,
            structured_facts=[],
            modality_confidence=confidence,
            extraction_trace=f"Extracted from image using SmolVLM (confidence: {confidence:.2f})"
        )

    except FileNotFoundError:
        raise
    except Exception as e:
        # Log error and re-raise with context
        error_trace = f"Image parsing failed for {image_path}: {str(e)}"
        raise Exception(error_trace) from e


def ingest(input_data: Union[str, Path, dict]) -> ClinicalDocument:
    """
    Main ingestion router.

    Detects input modality and dispatches to appropriate parser.

    Args:
        input_data: FHIR dict, FHIR JSON string, plain text, or image path

    Returns:
        Validated ClinicalDocument

    Raises:
        ValueError: If modality detection or parsing fails
    """
    # Detect modality
    modality = detect_modality(input_data)

    # Route to appropriate parser
    if modality == "fhir":
        return parse_fhir(input_data)
    elif modality == "text":
        return parse_text(str(input_data))
    elif modality == "image":
        return parse_image(input_data)
    else:
        raise ValueError(f"Unknown modality: {modality}")
