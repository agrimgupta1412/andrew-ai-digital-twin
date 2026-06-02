"""Print vector store and processed chunk status."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.bm25_retriever import BM25Retriever
from src.config import get_settings
from src.vector_store import ChromaVectorStore


def main() -> int:
    settings = get_settings()
    vector_store = ChromaVectorStore(settings)
    vector_count = vector_store.count()
    bm25_count = BM25Retriever(settings.processed_chunks_path).count()
    print(f"Configured ChromaDB directory: {settings.chroma_db_dir}")
    print(f"Active ChromaDB directory: {vector_store.active_dir}")
    print(f"Chroma indexed chunks: {vector_count}")
    print(f"Processed JSONL chunks: {bm25_count}")
    if vector_count == 0 and bm25_count == 0:
        print("No documents are indexed yet. Please add documents to data/raw/ and run python scripts/ingest_documents.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
