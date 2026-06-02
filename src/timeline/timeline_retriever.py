"""Simple reliable retrieval over timeline events."""

from __future__ import annotations

import re
from typing import Any

from src.timeline.timeline_guardrails import is_timeline_sensitive_query
from src.timeline.timeline_loader import load_timeline
from src.utils import simple_tokenize


ORG_KEYWORDS = {
    "google brain": ["google brain"],
    "coursera": ["coursera"],
    "deeplearning.ai": ["deeplearning.ai", "deeplearning ai"],
    "baidu": ["baidu"],
}


def _years_in_query(query: str) -> list[int]:
    return [int(match) for match in re.findall(r"\b(19\d{2}|20\d{2})\b", query)]


def get_relevant_timeline_events(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    events = load_timeline()
    if not events:
        return []

    normalized = query.lower()
    query_tokens = set(simple_tokenize(query))
    years = _years_in_query(query)
    scored: list[tuple[float, dict[str, Any]]] = []

    for event in events:
        score = 0.0
        event_text = f"{event['event']} {event['category']}".lower()
        event_tokens = set(simple_tokenize(event_text))

        for year in years:
            distance = abs(event["year"] - year)
            if distance == 0:
                score += 5.0
            elif distance <= 2:
                score += 2.0

        for aliases in ORG_KEYWORDS.values():
            if any(alias in normalized for alias in aliases) and any(alias in event_text for alias in aliases):
                score += 4.0

        if event["category"].lower() in normalized:
            score += 2.0

        score += len(query_tokens & event_tokens) * 0.5
        if score > 0:
            scored.append((score, event))

    if not scored and is_timeline_sensitive_query(query):
        return events[:top_k]

    scored.sort(key=lambda item: (item[0], item[1]["year"]), reverse=True)
    return [event for _, event in scored[:top_k]]
