"""Text chunking with metadata preservation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .document_loader import DocumentPage, SourceDocument
from .utils import clean_text, stable_hash


DEFAULT_CHUNK_SIZE = 3500
DEFAULT_CHUNK_OVERLAP = 600
DEFAULT_MIN_CHUNK_SIZE = 500


@dataclass
class Chunk:
    text: str
    metadata: dict[str, Any]


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    min_chunk_size: int = DEFAULT_MIN_CHUNK_SIZE,
) -> list[str]:
    """Split text into overlapping character chunks."""
    cleaned = clean_text(text)
    if not cleaned:
        return []
    if len(cleaned) <= chunk_size:
        return [cleaned]

    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(start + chunk_size, len(cleaned))
        chunk = cleaned[start:end].strip()

        if end < len(cleaned):
            paragraph_break = chunk.rfind("\n\n")
            sentence_break = max(chunk.rfind(". "), chunk.rfind("? "), chunk.rfind("! "))
            break_at = paragraph_break if paragraph_break > min_chunk_size else sentence_break
            if break_at > min_chunk_size:
                end = start + break_at + 1
                chunk = cleaned[start:end].strip()

        if len(chunk) >= min_chunk_size or not chunks:
            chunks.append(chunk)
        elif chunks:
            chunks[-1] = f"{chunks[-1]}\n\n{chunk}".strip()

        if end >= len(cleaned):
            break
        start = max(0, end - chunk_overlap)

    return [item for item in chunks if item.strip()]


def chunk_pages(
    source: dict[str, Any],
    pages: Iterable[DocumentPage],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    min_chunk_size: int = DEFAULT_MIN_CHUNK_SIZE,
) -> list[Chunk]:
    source_id = str(source.get("id", "source"))
    chunks: list[Chunk] = []
    for page in pages:
        page_chunks = chunk_text(page.text, chunk_size, chunk_overlap, min_chunk_size)
        for index, text in enumerate(page_chunks):
            page_label = page.page if page.page is not None else "text"
            chunk_id = f"{source_id}-p{page_label}-{index}-{stable_hash([source_id, str(page_label), str(index), text])}"
            metadata = {
                "chunk_id": chunk_id,
                "source_id": source_id,
                "source_title": source.get("title", "Untitled source"),
                "source_type": source.get("type", "unknown"),
                "author": source.get("author", ""),
                "page": page.page,
                "url": source.get("url", ""),
                "domain": source.get("domain", ""),
                "text_preview": text[:200],
            }
            chunks.append(Chunk(text=text, metadata=metadata))
    return chunks


def chunk_document(document: SourceDocument) -> list[Chunk]:
    return chunk_pages(document.metadata, document.pages)

