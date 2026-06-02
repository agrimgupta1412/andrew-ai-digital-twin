from src.retriever import _dedupe_and_rerank, detect_confidence


def test_retriever_merge_returns_list_with_text_and_metadata():
    vector_results = [
        {
            "chunk_id": "a",
            "text": "Gradient descent reduces loss step by step.",
            "source_id": "source-a",
            "source_title": "Source A",
            "page": 1,
            "url": "https://example.com/a",
            "vector_score": 0.8,
        }
    ]
    results = _dedupe_and_rerank(vector_results, [], top_k=5)
    assert isinstance(results, list)
    assert results[0]["text"]
    assert results[0]["source_id"] == "source-a"
    assert results[0]["source_title"] == "Source A"


def test_duplicate_chunks_are_removed_and_scores_are_combined():
    vector_results = [
        {"chunk_id": "a", "text": "same", "source_id": "s", "source_title": "S", "vector_score": 0.7}
    ]
    bm25_results = [
        {"chunk_id": "a", "text": "same", "source_id": "s", "source_title": "S", "bm25_score": 1.0}
    ]
    results = _dedupe_and_rerank(vector_results, bm25_results, top_k=5)
    assert len(results) == 1
    assert results[0]["retrieval_method"] == "hybrid"
    assert results[0]["score"] == 0.7 * 0.7 + 0.3 * 1.0


def test_weak_retrieval_is_detected():
    assert detect_confidence([]) == "low"
    assert detect_confidence([{"score": 0.1}]) == "low"
    assert detect_confidence([{"score": 0.3}]) == "medium"
    assert detect_confidence([{"score": 0.7}]) == "high"

