"""Format retrieved sources outside the LLM."""

from __future__ import annotations


def unique_sources(chunks: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    sources: list[dict] = []
    for chunk in chunks:
        key = (chunk.get("source_id"), chunk.get("page"), chunk.get("url"))
        if key in seen:
            continue
        seen.add(key)
        sources.append(
            {
                "source_title": chunk.get("source_title", "Untitled source"),
                "source_id": chunk.get("source_id", "unknown"),
                "page": chunk.get("page"),
                "url": chunk.get("url", ""),
                "score": chunk.get("score", 0),
                "retrieval_method": chunk.get("retrieval_method", ""),
            }
        )
    return sources


def format_sources(chunks: list[dict]) -> str:
    sources = unique_sources(chunks)
    if not sources:
        return "Sources used: none retrieved."
    lines = ["Sources used:"]
    for index, source in enumerate(sources, start=1):
        page = source.get("page")
        page_text = f"page {page}" if page else "page N/A"
        url = source.get("url") or "no URL"
        lines.append(f"{index}. {source['source_title']} - {page_text} - {url}")
    return "\n".join(lines)

