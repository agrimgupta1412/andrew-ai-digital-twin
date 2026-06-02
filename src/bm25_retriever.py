"""BM25 keyword retrieval over processed chunk JSONL."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .utils import simple_tokenize


class BM25Retriever:
    def __init__(self, chunks_path: Path):
        self.chunks_path = chunks_path
        self._chunks: list[dict[str, Any]] | None = None
        self._bm25 = None

    def _load_chunks(self) -> list[dict[str, Any]]:
        if self._chunks is not None:
            return self._chunks
        chunks: list[dict[str, Any]] = []
        if self.chunks_path.exists():
            with self.chunks_path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if line.strip():
                        chunks.append(json.loads(line))
        self._chunks = chunks
        return chunks

    def _load_bm25(self):
        if self._bm25 is not None:
            return self._bm25
        chunks = self._load_chunks()
        if not chunks:
            return None
        try:
            from rank_bm25 import BM25Okapi
        except Exception:
            return None
        corpus = [simple_tokenize(chunk.get("text", "")) for chunk in chunks]
        self._bm25 = BM25Okapi(corpus)
        return self._bm25

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        chunks = self._load_chunks()
        bm25 = self._load_bm25()
        if not chunks or bm25 is None:
            return []
        scores = bm25.get_scores(simple_tokenize(query))
        max_score = max(scores) if len(scores) else 0
        ranked_indices = sorted(range(len(scores)), key=lambda index: scores[index], reverse=True)[:top_k]

        results: list[dict[str, Any]] = []
        for index in ranked_indices:
            raw_score = float(scores[index])
            if raw_score <= 0:
                continue
            normalized = raw_score / max_score if max_score else 0.0
            chunk = chunks[index]
            metadata = chunk.get("metadata", {})
            results.append(
                {
                    "text": chunk.get("text", ""),
                    **metadata,
                    "score": normalized,
                    "bm25_score": normalized,
                    "retrieval_method": "bm25",
                }
            )
        return results

    def count(self) -> int:
        return len(self._load_chunks())

