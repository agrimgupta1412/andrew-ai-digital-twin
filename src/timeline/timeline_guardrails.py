"""Rule-based guardrails for historically sensitive queries."""

from __future__ import annotations

import re


TIMELINE_KEYWORDS = [
    "timeline",
    "career",
    "history",
    "when",
    "before",
    "after",
    "during",
    "at that time",
    "then",
    "now",
    "google brain",
    "coursera",
    "deeplearning.ai",
    "baidu",
    "chatgpt",
    "generative ai",
]

TIMELINE_PHRASES = [
    "at that time",
    "google brain",
    "deeplearning.ai",
    "generative ai",
]


def is_timeline_sensitive_query(query: str) -> bool:
    normalized = query.lower()
    if re.search(r"\b(in\s+)?(19|20)\d{2}\b", normalized):
        return True
    if any(phrase in normalized for phrase in TIMELINE_PHRASES):
        return True
    return any(re.search(rf"\b{re.escape(keyword)}\b", normalized) for keyword in TIMELINE_KEYWORDS if keyword not in TIMELINE_PHRASES)


def get_timeline_guardrail_text() -> str:
    return """
TIMELINE RULES:
- Use timeline context for historically sensitive questions.
- Do not imply Andrew Ng held a role at a time when the timeline does not support it.
- Do not attribute later ideas, companies, or technologies to earlier periods unless the timeline supports it.
- If a modern concept is discussed, distinguish between:
  1. what Andrew Ng publicly worked on at that time
  2. what AndrewAI can explain now using modern knowledge
- Never fabricate timeline events.
- If timeline context is insufficient, say so honestly.
""".strip()
