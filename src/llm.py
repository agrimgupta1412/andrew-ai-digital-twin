"""Gemini response generation wrapper."""

from __future__ import annotations

import queue
import threading

from .config import Settings
from .utils import clear_dead_proxy_env


class LLMError(RuntimeError):
    """Raised when Gemini generation fails."""


class GeminiClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def generate(self, prompt: str) -> str:
        if not self.settings.google_api_key:
            raise LLMError("Missing GOOGLE_API_KEY. Create .env from .env.example and add your Google API key.")

        def _request():
            clear_dead_proxy_env()
            import google.generativeai as genai

            genai.configure(api_key=self.settings.google_api_key)
            model = genai.GenerativeModel(self.settings.gemini_model)
            return model.generate_content(
                prompt,
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
