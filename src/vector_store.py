"""ChromaDB vector store wrapper."""

from __future__ import annotations

import tempfile
from typing import Any
from pathlib import Path

from .config import Settings
from .utils import ensure_dir


COLLECTION_NAME_PREFIX = "andrew_ai_chunks"


class VectorStoreError(RuntimeError):
    """Raised when the vector store cannot be used."""


class ChromaVectorStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = None
        self._collections = {}
        self.active_dir = settings.chroma_db_dir

    @property
    def client(self):
        if self._client is None:
            last_error: Exception | None = None
            try:
                import chromadb
            except Exception as exc:
                raise VectorStoreError(f"Could not import ChromaDB: {exc}") from exc

            fallback_dir = Path(tempfile.gettempdir()) / "andrew-ai-digital-twin" / "vectorstore"
            for candidate_dir in [self.settings.chroma_db_dir, fallback_dir]:
                try:
                    ensure_dir(candidate_dir)
                    client = chromadb.PersistentClient(path=str(candidate_dir))
                    self._probe_client(client)
                    self._client = client
                    self.active_dir = candidate_dir
                    break
                except Exception as exc:
                    last_error = exc

            if self._client is None:
                raise VectorStoreError(f"Could not initialize ChromaDB: {last_error}") from last_error
        return self._client

    @staticmethod
    def collection_name_for_dimension(dimension: int) -> str:
        return f"{COLLECTION_NAME_PREFIX}_d{dimension}"

    def collection_for_dimension(self, dimension: int):
        if dimension <= 0:
            raise VectorStoreError("Embedding vector must have at least one dimension.")
        name = self.collection_name_for_dimension(dimension)
        if name not in self._collections:
            self._collections[name] = self.client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine", "embedding_dimension": dimension},
            )
        return self._collections[name]

    @staticmethod
    def _probe_client(client) -> None:
        probe_name = "andrew-ai-chroma-probe"
        try:
            try:
                client.delete_collection(probe_name)
            except Exception:
                pass
            probe = client.get_or_create_collection(probe_name)
            probe.upsert(
                ids=["probe"],
                documents=["probe"],
                metadatas=[{"kind": "probe"}],
                embeddings=[[0.1, 0.2, 0.3]],
            )
            if probe.count() != 1:
                raise VectorStoreError("ChromaDB health probe did not persist a test row.")
        finally:
            try:
                client.delete_collection(probe_name)
            except Exception:
                pass

    def add_chunks(
        self,
        ids: list[str],
        texts: list[str],
        metadatas: list[dict[str, Any]],
        embeddings: list[list[float]],
    ) -> None:
        if not ids:
            return
        dimension = len(embeddings[0]) if embeddings else 0
        self.collection_for_dimension(dimension).upsert(
            ids=ids,
            documents=texts,
            metadatas=metadatas,
            embeddings=embeddings,
        )

    def query(self, query_embedding: list[float], top_k: int) -> list[dict[str, Any]]:
        collection = self.collection_for_dimension(len(query_embedding))
        if collection.count() == 0:
            return []
        result = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        rows: list[dict[str, Any]] = []
        for text, metadata, distance in zip(documents, metadatas, distances):
            score = max(0.0, 1.0 - float(distance))
            rows.append(
                {
                    "text": text,
                    **(metadata or {}),
                    "score": score,
                    "vector_score": score,
                    "retrieval_method": "vector",
                }
            )
        return rows

    def count(self) -> int:
        try:
            total = 0
            for collection in self.client.list_collections():
                name = collection.name if hasattr(collection, "name") else str(collection)
                if name.startswith(f"{COLLECTION_NAME_PREFIX}_d"):
                    if hasattr(collection, "count"):
                        total += int(collection.count())
                    else:
                        total += int(self.client.get_collection(name).count())
            return total
        except Exception:
            return 0
