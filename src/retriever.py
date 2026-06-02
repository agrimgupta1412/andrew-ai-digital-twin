"""Hybrid retrieval: vector search plus BM25 plus simple reranking."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .bm25_retriever import BM25Retriever
from .config import Settings, get_settings
from .embeddings import EmbeddingError, GoogleEmbeddingClient
from .vector_store import ChromaVectorStore, VectorStoreError


@dataclass
class RetrievalResult:
    chunks: list[dict[str, Any]]
    context_confidence: str
    status_message: str = ""


def clean_query(query: str) -> str:
    return re.sub(r"\s+", " ", query).strip()


def _dedupe_and_rerank(vector_results: list[dict[str, Any]], bm25_results: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}

    for result in vector_results:
        key = result.get("chunk_id") or result.get("text", "")[:120]
        row = merged.setdefault(key, dict(result))
        row["vector_score"] = max(float(row.get("vector_score", 0)), float(result.get("vector_score", result.get("score", 0))))

    for result in bm25_results:
        key = result.get("chunk_id") or result.get("text", "")[:120]
        row = merged.setdefault(key, dict(result))
        row["bm25_score"] = max(float(row.get("bm25_score", 0)), float(result.get("bm25_score", result.get("score", 0))))
        if "text" not in row:
            row["text"] = result.get("text", "")

    ranked: list[dict[str, Any]] = []
    for row in merged.values():
        vector_score = float(row.get("vector_score", 0))
        bm25_score = float(row.get("bm25_score", 0))
        if vector_score and bm25_score:
            final_score = 0.7 * vector_score + 0.3 * bm25_score
            method = "hybrid"
        elif vector_score:
            final_score = vector_score
            method = "vector"
        else:
            final_score = bm25_score
            method = "bm25"
        row["score"] = final_score
        row["retrieval_method"] = method
        ranked.append(row)

    ranked.sort(key=lambda item: item.get("score", 0), reverse=True)
    return ranked[:top_k]


def detect_confidence(chunks: list[dict[str, Any]]) -> str:
    if not chunks:
        return "low"
    best = max(float(chunk.get("score", 0)) for chunk in chunks)
    if best >= 0.55:
        return "high"
    if best >= 0.25:
        return "medium"
    return "low"


class HybridRetriever:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.vector_store = ChromaVectorStore(self.settings)
        self.embedding_client = GoogleEmbeddingClient(self.settings)
        self.bm25 = BM25Retriever(self.settings.processed_chunks_path)

    def retrieve_context(self, query: str, top_k: int | None = None) -> RetrievalResult:
        query = clean_query(query)
        top_k = top_k or self.settings.top_k
        if not query:
            return RetrievalResult([], "low", "Empty query.")

        vector_results: list[dict[str, Any]] = []
        bm25_results: list[dict[str, Any]] = []
        messages: list[str] = []

        try:
            if self.vector_store.count() > 0:
                query_embedding = self.embedding_client.embed_query(query)
                vector_results = self.vector_store.query(query_embedding, top_k=top_k * 2)
            else:
                messages.append("No documents are indexed in ChromaDB yet.")
        except (EmbeddingError, VectorStoreError, Exception) as exc:
            messages.append(f"Vector retrieval unavailable: {exc}")

        if self.settings.use_bm25:
            try:
                bm25_results = self.bm25.search(query, top_k=top_k * 2)
            except Exception as exc:
                messages.append(f"BM25 retrieval unavailable: {exc}")

        chunks = _dedupe_and_rerank(vector_results, bm25_results, top_k)
        confidence = detect_confidence(chunks)
        return RetrievalResult(chunks, confidence, " ".join(messages))

    def indexed_count(self) -> int:
        vector_count = self.vector_store.count()
        return vector_count or self.bm25.count()


def retrieve_context(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Convenience function matching the assignment API."""
    return HybridRetriever().retrieve_context(query, top_k).chunks

