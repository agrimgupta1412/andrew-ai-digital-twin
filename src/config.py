"""Configuration helpers for the digital twin."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    google_api_key: str
    google_api_keys: list[str]
    gemini_model: str
    embedding_model: str
    request_timeout_seconds: int
    chroma_db_dir: Path
    sqlite_memory_db: Path
    top_k: int
    use_bm25: bool
    response_depth: str
    enable_timeline: bool
    timeline_file: Path
    enable_memory_dashboard: bool
    sources_manifest: Path
    processed_chunks_path: Path


def _as_bool(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _load_google_api_keys() -> list[str]:
    """Load one or more Google API keys while keeping the old single-key setting working."""
    keys: list[str] = []
    numbered_keys = [os.getenv(f"GOOGLE_API_KEY_{index}", "").strip() for index in range(1, 5)]
    keys.extend(key for key in numbered_keys if key)

    combined_keys = os.getenv("GOOGLE_API_KEYS", "")
    if combined_keys.strip():
        keys.extend(key.strip() for key in combined_keys.split(",") if key.strip())

    legacy_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if legacy_key:
        keys.append(legacy_key)

    unique_keys: list[str] = []
    seen: set[str] = set()
    for key in keys:
        if key not in seen:
            unique_keys.append(key)
            seen.add(key)
    return unique_keys


def get_settings() -> Settings:
    """Load settings from .env and environment variables."""
    load_dotenv(PROJECT_ROOT / ".env")
    top_k_raw = os.getenv("TOP_K", "5")
    try:
        top_k = max(1, int(top_k_raw))
    except ValueError:
        top_k = 5
    timeout_raw = os.getenv("REQUEST_TIMEOUT_SECONDS", "15")
    try:
        request_timeout_seconds = max(1, int(timeout_raw))
    except ValueError:
        request_timeout_seconds = 15

    chroma_dir = PROJECT_ROOT / os.getenv("CHROMA_DB_DIR", "vectorstore")
    memory_db = PROJECT_ROOT / os.getenv("SQLITE_MEMORY_DB", "memory/memory.db")
    google_api_keys = _load_google_api_keys()

    return Settings(
        google_api_key=google_api_keys[0] if google_api_keys else "",
        google_api_keys=google_api_keys,
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip(),
        embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-004").strip(),
        request_timeout_seconds=request_timeout_seconds,
        chroma_db_dir=chroma_dir,
        sqlite_memory_db=memory_db,
        top_k=top_k,
        use_bm25=_as_bool(os.getenv("USE_BM25"), True),
        response_depth=os.getenv("RESPONSE_DEPTH", "standard").strip().lower(),
        enable_timeline=_as_bool(os.getenv("ENABLE_TIMELINE"), True),
        timeline_file=PROJECT_ROOT / os.getenv("TIMELINE_FILE", "data/timeline/andrew_ng_timeline.json"),
        enable_memory_dashboard=_as_bool(os.getenv("ENABLE_MEMORY_DASHBOARD"), True),
        sources_manifest=PROJECT_ROOT / "data/sources_manifest.json",
        processed_chunks_path=PROJECT_ROOT / "data/processed/chunks.jsonl",
    )
