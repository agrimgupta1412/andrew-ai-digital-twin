"""Gemini response generation wrapper."""

from __future__ import annotations

import queue
import threading
from collections.abc import Sequence
from typing import Any

from .config import Settings
from .utils import clear_dead_proxy_env


class LLMError(RuntimeError):
    """Raised when Gemini generation fails."""


class GeminiClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._key_index = 0
        self._key_lock = threading.Lock()

    def _api_keys(self) -> list[str]:
        keys = list(getattr(self.settings, "google_api_keys", []) or [])
        if not keys and self.settings.google_api_key:
            keys = [self.settings.google_api_key]
        return keys

    @staticmethod
    def _is_retryable_key_error(exc: Exception) -> bool:
        error_text = str(exc).lower()
        retryable_markers = [
            "429",
            "quota",
            "rate limit",
            "rate_limit",
            "resource_exhausted",
            "too many requests",
            "retry_delay",
            "timed out",
            "timeout",
            "unavailable",
            "503",
            "504",
        ]
        return any(marker in error_text for marker in retryable_markers)

    def _ordered_api_keys(self) -> list[str]:
        keys = self._api_keys()
        if not keys:
            raise LLMError("Missing GOOGLE_API_KEY. Create .env from .env.example and add your Google API key.")
        with self._key_lock:
            start_index = self._key_index % len(keys)
        return keys[start_index:] + keys[:start_index]

    def _remember_successful_key(self, api_key: str) -> None:
        keys = self._api_keys()
        if not keys:
            return
        try:
            successful_index = keys.index(api_key)
        except ValueError:
            return
        with self._key_lock:
            self._key_index = (successful_index + 1) % len(keys)

    def _request_with_key(self, api_key: str, parts: str | Sequence[Any]):
        def _request():
            clear_dead_proxy_env()
            import google.generativeai as genai

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(self.settings.gemini_model)
            return model.generate_content(
                parts,
                request_options={"timeout": self.settings.request_timeout_seconds},
            )

        result_queue: queue.Queue = queue.Queue(maxsize=1)

        def _run_request():
            try:
                result_queue.put(_request())
            except Exception as exc:
                result_queue.put(exc)

        thread = threading.Thread(target=_run_request, daemon=True)
        try:
            thread.start()
            response = result_queue.get(timeout=self.settings.request_timeout_seconds)
            if isinstance(response, Exception):
                raise response
        except queue.Empty as exc:
            raise LLMError(
                f"Gemini request timed out after {self.settings.request_timeout_seconds} seconds. "
                "Check the API key, model name, quota, and network access."
            ) from exc
        except Exception as exc:
            raise LLMError(
                f"Gemini request failed. Check the API key, model name, quota, and network access. Details: {exc}"
            ) from exc

        text = getattr(response, "text", None)
        if text:
            return text.strip()
        raise LLMError("Gemini returned an empty response.")

    def _generate_content(self, parts: str | Sequence[Any]) -> str:
        last_error: LLMError | None = None
        keys = self._ordered_api_keys()
        for index, api_key in enumerate(keys, start=1):
            try:
                response_text = self._request_with_key(api_key, parts)
                self._remember_successful_key(api_key)
                return response_text
            except LLMError as exc:
                last_error = exc
                if index == len(keys) or not self._is_retryable_key_error(exc):
                    break

        if len(keys) > 1 and last_error:
            raise LLMError(
                f"All configured Gemini API keys failed or hit quota/rate limits. Last error: {last_error}"
            ) from last_error
        if last_error:
            raise last_error
        raise LLMError("Gemini request failed before a response was created.")

    def generate(self, prompt: str) -> str:
        return self._generate_content(prompt)

    def transcribe_audio(self, audio_bytes: bytes, mime_type: str = "audio/wav") -> str:
        prompt = (
            "Transcribe this audio into the exact user question for an AI/ML tutoring chatbot. "
            "Return only the transcription text. Do not answer the question."
        )
        return self._generate_content(
            [
                prompt,
                {
                    "mime_type": mime_type or "audio/wav",
                    "data": audio_bytes,
                },
            ]
        )
