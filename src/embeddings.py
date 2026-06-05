"""Embedding client for Google text embeddings."""

from __future__ import annotations

import hashlib
import math
import queue
import threading

from .config import Settings
from .utils import clear_dead_proxy_env, simple_tokenize


class EmbeddingError(RuntimeError):
    """Raised when embeddings cannot be created."""


class GoogleEmbeddingClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.active_model = settings.embedding_model

    def _api_keys(self) -> list[str]:
        keys = list(getattr(self.settings, "google_api_keys", []) or [])
        if not keys and self.settings.google_api_key:
            keys = [self.settings.google_api_key]
        return keys

    def _configure(self, api_key: str) -> None:
        clear_dead_proxy_env()
        import google.generativeai as genai

        genai.configure(api_key=api_key)

    def embed_query(self, text: str) -> list[float]:
        return self._embed_single(text, task_type="retrieval_query")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_single(text, task_type="retrieval_document") for text in texts]

    def _embed_single(self, text: str, task_type: str) -> list[float]:
        if self.active_model == "__local_hash_fallback__":
            return self._local_hash_embedding(text)

        api_keys = self._api_keys()
        if not api_keys:
            raise EmbeddingError("Missing GOOGLE_API_KEY. Add it to .env before ingestion or retrieval.")

        import google.generativeai as genai

        model_names = [self.active_model]
        if "gemini-embedding-001" not in model_names:
            model_names.append("gemini-embedding-001")

        last_error: Exception | None = None
        for api_key in api_keys:
            self._configure(api_key)
            for model_name in model_names:
                try:
                    result_queue: queue.Queue = queue.Queue(maxsize=1)

                    def _request_embedding():
                        try:
                            result_queue.put(
                                genai.embed_content(
                                    model=model_name,
                                    content=text,
                                    task_type=task_type,
                                    request_options={"timeout": self.settings.request_timeout_seconds},
                                )
                            )
                        except Exception as exc:
                            result_queue.put(exc)

                    thread = threading.Thread(target=_request_embedding, daemon=True)
                    thread.start()
                    response = result_queue.get(timeout=self.settings.request_timeout_seconds)
                    if isinstance(response, Exception):
                        raise response
                    embedding = response.get("embedding") if isinstance(response, dict) else None
                    if embedding and isinstance(embedding[0], list):
                        self.active_model = model_name
                        return [float(value) for value in embedding[0]]
                    if embedding:
                        self.active_model = model_name
                        return [float(value) for value in embedding]
                except Exception as exc:
                    last_error = exc
                    error_text = str(exc).lower()
                    if isinstance(exc, queue.Empty):
                        error_text = "timeout"
                    if "quota" in error_text or "429" in error_text or "timeout" in error_text or "unavailable" in error_text:
                        break
                    if "not found" not in error_text and "not supported" not in error_text:
                        break
            else:
                continue

        if last_error:
            error_text = str(last_error).lower()
            if isinstance(last_error, queue.Empty):
                error_text = "timeout"
            if "quota" in error_text or "429" in error_text or "timeout" in error_text or "unavailable" in error_text:
                self.active_model = "__local_hash_fallback__"
                return self._local_hash_embedding(text)

        if last_error:
            raise EmbeddingError(f"Embedding request failed: {last_error}") from last_error
        raise EmbeddingError("Embedding response did not contain an embedding vector.")

    @staticmethod
    def _local_hash_embedding(text: str, dimensions: int = 384) -> list[float]:
        vector = [0.0] * dimensions
        tokens = simple_tokenize(text)
        if not tokens:
            vector[0] = 1.0
            return vector
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]
