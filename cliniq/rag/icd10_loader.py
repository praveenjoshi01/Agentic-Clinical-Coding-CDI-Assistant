"""
ICD-10 code data loading and management.

Provides functions for loading, querying, and filtering ICD-10-CM codes
from the curated JSON dataset.
"""

import json
from pathlib import Path
from typing import Optional

from cliniq.config import ICD10_DIR


def load_icd10_codes(filepath: Optional[str | Path] = None) -> list[dict]:
    """
    Load ICD-10 codes from JSON file.

    Args:
        filepath: Path to ICD-10 codes JSON file. If None, uses default
                  from config.ICD10_DIR / "icd10_codes.json"

    Returns:
        List of dicts with keys: code, description, chapter

    Raises:
        FileNotFoundError: If the ICD-10 codes file does not exist
        ValueError: If file contains fewer than 100 codes
    """
    if filepath is None:
        filepath = ICD10_DIR / "icd10_codes.json"
    else:
        filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(
            f"ICD-10 codes file not found: {filepath}. "
            f"Expected location: {ICD10_DIR / 'icd10_codes.json'}"
        )

    with open(filepath, "r", encoding="utf-8") as f:
        codes = json.load(f)

    if not isinstance(codes, list):
        raise ValueError(
            f"ICD-10 codes file must contain a JSON array, got {type(codes).__name__}"
        )

    if len(codes) < 100:
        raise ValueError(
            f"ICD-10 codes file must contain at least 100 codes, found {len(codes)}"
        )

    # Validate structure of each code entry
    required_keys = {"code", "description", "chapter"}
    for i, code_entry in enumerate(codes):
        if not isinstance(code_entry, dict):
            raise ValueError(
                f"Code entry {i} must be a dict, got {type(code_entry).__name__}"
            )
        missing_keys = required_keys - set(code_entry.keys())
        if missing_keys:
            raise ValueError(
                f"Code entry {i} missing required keys: {missing_keys}"
            )

    return codes


def get_code_by_id(codes: list[dict], code_id: str) -> Optional[dict]:
    """
    Find a code by its ICD-10 code identifier.

    Args:
        codes: List of code dicts from load_icd10_codes()
        code_id: ICD-10 code string (e.g., "E11.9")

    Returns:
        Code dict if found, None otherwise
    """
    for code in codes:
        if code["code"] == code_id:
            return code
    return None


def get_codes_by_chapter(codes: list[dict], chapter_prefix: str) -> list[dict]:
    """
    Filter codes by chapter range prefix.

    Args:
        codes: List of code dicts from load_icd10_codes()
        chapter_prefix: Chapter prefix to match (e.g., "E" matches "E00-E89",
                        "I" matches "I00-I99")

    Returns:
        List of codes in the specified chapter
    """
    matching_codes = []
    for code in codes:
        chapter = code["chapter"]
        # Match if chapter starts with the prefix (e.g., "E00-E89" starts with "E")
        if chapter.startswith(chapter_prefix):
            matching_codes.append(code)
    return matching_codes
