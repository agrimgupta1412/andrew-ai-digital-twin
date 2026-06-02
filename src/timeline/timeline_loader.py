"""Load and validate Andrew Ng timeline events."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.config import get_settings


REQUIRED_FIELDS = {"year", "event", "category", "source", "confidence"}


def _is_valid_event(event: dict[str, Any]) -> bool:
    if not REQUIRED_FIELDS.issubset(event):
        return False
    try:
        int(event["year"])
    except (TypeError, ValueError):
        return False
    return all(str(event.get(field, "")).strip() for field in REQUIRED_FIELDS - {"year"})


def load_timeline(path: Path | None = None) -> list[dict[str, Any]]:
    timeline_path = path or get_settings().timeline_file
    if not timeline_path.exists():
        return []
    try:
        data = json.loads(timeline_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []

    events: list[dict[str, Any]] = []
    for item in data:
        if isinstance(item, dict) and _is_valid_event(item):
            event = dict(item)
            event["year"] = int(event["year"])
            events.append(event)
    return sorted(events, key=lambda event: event["year"])
