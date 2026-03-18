"""
Unit tests for RAG components: ICD-10 loader, retriever, reranker.
"""

import json
from pathlib import Path

import pytest

from cliniq.rag import (
    load_icd10_codes,
    get_code_by_id,
    get_codes_by_chapter,
    build_faiss_index,
    FAISSRetriever,
    CrossEncoderReranker,
)


def test_load_icd10_codes():
    """Test ICD-10 code loading returns expected structure."""
    codes = load_icd10_codes()

    # Should have at least 200 codes
    assert len(codes) >= 200, f"Expected at least 200 codes, got {len(codes)}"

    # Each code should have required keys
    required_keys = {"code", "description", "chapter"}
    for code_entry in codes:
        assert isinstance(code_entry, dict)
        assert required_keys.issubset(code_entry.keys())
        assert isinstance(code_entry["code"], str)
        assert isinstance(code_entry["description"], str)
        assert isinstance(code_entry["chapter"], str)


def test_get_code_by_id():
    """Test code lookup by ICD-10 code ID."""
    codes = load_icd10_codes()

    # Should find E11.9 (Type 2 diabetes without complications)
    result = get_code_by_id(codes, "E11.9")
    assert result is not None
    assert result["code"] == "E11.9"
    assert "diabetes" in result["description"].lower()
    assert result["chapter"] == "E00-E89"

    # Should return None for non-existent code
    result = get_code_by_id(codes, "NONEXISTENT")
    assert result is None


def test_get_codes_by_chapter():
    """Test filtering codes by chapter prefix."""
    codes = load_icd10_codes()

    # Test endocrine chapter (E)
    endocrine_codes = get_codes_by_chapter(codes, "E")
    assert len(endocrine_codes) > 0
    for code in endocrine_codes:
        assert code["chapter"].startswith("E")

    # Test circulatory chapter (I)
    circulatory_codes = get_codes_by_chapter(codes, "I")
    assert len(circulatory_codes) > 0
    for code in circulatory_codes:
        assert code["chapter"].startswith("I")

    # Test respiratory chapter (J)
    respiratory_codes = get_codes_by_chapter(codes, "J")
    assert len(respiratory_codes) > 0
    for code in respiratory_codes:
        assert code["chapter"].startswith("J")


@pytest.mark.slow
def test_build_faiss_index_subset(tmp_path):
    """Test FAISS index building with a small subset (requires model download)."""
    # Load full codes and take a small subset for fast testing
    all_codes = load_icd10_codes()
    subset = all_codes[:50]  # Use first 50 codes

    # Build index in temporary directory
    index, codes = build_faiss_index(codes=subset, output_dir=tmp_path)

    # Verify index was created
    assert index is not None
    assert index.ntotal == 50
    assert len(codes) == 50

    # Verify files were saved
    assert (tmp_path / "icd10.faiss").exists()
    assert (tmp_path / "icd10_metadata.json").exists()

    # Verify metadata file contains correct data
    with open(tmp_path / "icd10_metadata.json", "r") as f:
        saved_codes = json.load(f)
    assert len(saved_codes) == 50
    assert saved_codes[0]["code"] == subset[0]["code"]


@pytest.mark.slow
def test_faiss_retriever(tmp_path):
    """Test FAISS retriever interface (requires model download)."""
    # Build a small index for testing
    all_codes = load_icd10_codes()
    subset = all_codes[:50]
    build_faiss_index(codes=subset, output_dir=tmp_path)

    # Create retriever
    retriever = FAISSRetriever(index_dir=tmp_path)

    # Test retrieval
    query = "patient has type 2 diabetes without complications"
    results = retriever.retrieve(query, top_k=5)

    # Verify results structure
    assert len(results) == 5
    for result in results:
        assert "code" in result
        assert "description" in result
        assert "score" in result
        assert "rank" in result
        assert isinstance(result["code"], str)
        assert isinstance(result["description"], str)
        assert isinstance(result["score"], float)
        assert isinstance(result["rank"], int)

    # Verify ranks are sequential
    ranks = [r["rank"] for r in results]
    assert ranks == [1, 2, 3, 4, 5]

    # Verify scores are in descending order
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)


def test_cross_encoder_reranker_interface():
    """Test CrossEncoderReranker interface without model loading."""
    # Create mock candidates (no model needed for interface test)
    mock_candidates = [
        {"code": "E11.9", "description": "Type 2 diabetes mellitus without complications", "score": 0.85, "rank": 1},
        {"code": "E10.9", "description": "Type 1 diabetes mellitus without complications", "score": 0.75, "rank": 2},
        {"code": "E11.65", "description": "Type 2 diabetes mellitus with hyperglycemia", "score": 0.70, "rank": 3},
        {"code": "E11.21", "description": "Type 2 diabetes mellitus with diabetic nephropathy", "score": 0.65, "rank": 4},
        {"code": "E03.9", "description": "Hypothyroidism, unspecified", "score": 0.60, "rank": 5},
    ]

    reranker = CrossEncoderReranker()

    # Test that reranker can be instantiated
    assert reranker is not None
    assert reranker.cross_encoder is None  # Lazy loading, not loaded yet


@pytest.mark.slow
def test_cross_encoder_reranker_scoring(tmp_path):
    """Test CrossEncoderReranker scoring (requires model download)."""
    # Build a small index
    all_codes = load_icd10_codes()
    subset = all_codes[:50]
    build_faiss_index(codes=subset, output_dir=tmp_path)

    # Get initial candidates from retriever
    retriever = FAISSRetriever(index_dir=tmp_path)
    query = "patient has type 2 diabetes"
    candidates = retriever.retrieve(query, top_k=10)

    # Rerank candidates
    reranker = CrossEncoderReranker()
    reranked = reranker.rerank(query, candidates, top_k=5)

    # Verify reranking results
    assert len(reranked) == 5
    for result in reranked:
        assert "code" in result
        assert "description" in result
        assert "retrieval_score" in result  # Original score preserved
        assert "rerank_score" in result  # New score added
        assert "rank" in result

    # Verify ranks are updated
    ranks = [r["rank"] for r in reranked]
    assert ranks == [1, 2, 3, 4, 5]

    # Verify rerank scores are in descending order
    rerank_scores = [r["rerank_score"] for r in reranked]
    assert rerank_scores == sorted(rerank_scores, reverse=True)

    # Verify rerank_score differs from retrieval_score (reordering occurred)
    # At least one candidate should have changed position
    score_changes = sum(
        1 for r in reranked
        if abs(r["rerank_score"] - r["retrieval_score"]) > 0.01
    )
    assert score_changes > 0, "Reranker should produce different scores than retriever"
