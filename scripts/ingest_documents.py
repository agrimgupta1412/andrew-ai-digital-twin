"""Ingest manifest-listed documents into processed JSONL and ChromaDB."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.chunking import chunk_document
from src.config import get_settings
from src.document_loader import load_manifest, load_source
from src.embeddings import EmbeddingError, GoogleEmbeddingClient
from src.utils import ensure_dir
from src.vector_store import ChromaVectorStore, VectorStoreError


def sanitize_metadata(metadata: dict) -> dict:
    sanitized = {}
    for key, value in metadata.items():
        sanitized[key] = "" if value is None else value
    return sanitized


def main() -> int:
    settings = get_settings()
    sources = [source for source in load_manifest(settings.sources_manifest) if source.get("include_in_index", True)]
    if not sources:
        print("No sources are listed for indexing in data/sources_manifest.json.")
        return 0

    all_chunks = []
    for source in sources:
        try:
            document = load_source(source)
            chunks = chunk_document(document)
            all_chunks.extend(chunks)
            print(f"Loaded {len(chunks)} chunks from {source.get('title', source.get('id'))}.")
        except Exception as exc:
            print(f"Skipping {source.get('id', 'unknown source')}: {exc}")

    if not all_chunks:
        print("No chunks were created. Check that your source files contain extractable text.")
        return 0

    ensure_dir(settings.processed_chunks_path.parent)
    with settings.processed_chunks_path.open("w", encoding="utf-8") as handle:
        for chunk in all_chunks:
            handle.write(json.dumps({"text": chunk.text, "metadata": chunk.metadata}, ensure_ascii=True) + "\n")
    print(f"Saved {len(all_chunks)} processed chunks to {settings.processed_chunks_path}.")

    try:
        embedding_client = GoogleEmbeddingClient(settings)
        vector_store = ChromaVectorStore(settings)
        batch_size = 16
        for start in range(0, len(all_chunks), batch_size):
            batch = all_chunks[start : start + batch_size]
            texts = [chunk.text for chunk in batch]
            embeddings = embedding_client.embed_documents(texts)
            vector_store.add_chunks(
                ids=[chunk.metadata["chunk_id"] for chunk in batch],
                texts=texts,
                metadatas=[sanitize_metadata(chunk.metadata) for chunk in batch],
                embeddings=embeddings,
            )
            print(f"Indexed chunks {start + 1}-{start + len(batch)}.")
    except (EmbeddingError, VectorStoreError) as exc:
        print(f"Processed chunks were saved, but vector indexing failed: {exc}")
        return 1

    print("Ingestion complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

