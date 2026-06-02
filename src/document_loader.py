"""Load source documents listed in the manifest."""

from __future__ import annotations

import json
from html.parser import HTMLParser
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT
from .utils import clean_text


@dataclass
class DocumentPage:
    text: str
    page: int | None


@dataclass
class SourceDocument:
    metadata: dict[str, Any]
    pages: list[DocumentPage]


def load_manifest(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, dict):
        return data.get("sources", [])
    return data if isinstance(data, list) else []


def _extract_pdf(path: Path) -> list[DocumentPage]:
    try:
        import fitz  # PyMuPDF

        pages: list[DocumentPage] = []
        with fitz.open(path) as doc:
            for index, page in enumerate(doc, start=1):
                pages.append(DocumentPage(clean_text(page.get_text("text")), index))
        return pages
    except Exception:
        try:
            import pdfplumber

            pages = []
            with pdfplumber.open(path) as pdf:
                for index, page in enumerate(pdf.pages, start=1):
                    pages.append(DocumentPage(clean_text(page.extract_text() or ""), index))
            return pages
        except Exception as exc:
            raise RuntimeError(f"Could not extract PDF text from {path}: {exc}") from exc


def _extract_text(path: Path) -> list[DocumentPage]:
    return [DocumentPage(clean_text(path.read_text(encoding="utf-8", errors="ignore")), None)]


class _HTMLTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self.skip_depth += 1
        if tag in {"p", "div", "section", "article", "li", "h1", "h2", "h3", "br"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self.skip_depth:
            self.skip_depth -= 1
        if tag in {"p", "div", "section", "article", "li", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            text = data.strip()
            if text:
                self.parts.append(text)


def _extract_html(path: Path) -> list[DocumentPage]:
    parser = _HTMLTextParser()
    parser.feed(path.read_text(encoding="utf-8", errors="ignore"))
    return [DocumentPage(clean_text(" ".join(parser.parts)), None)]


def resolve_source_path(source: dict[str, Any]) -> Path:
    raw_path = Path(str(source.get("path", "")))
    if raw_path.is_absolute():
        return raw_path
    return PROJECT_ROOT / raw_path


def load_source(source: dict[str, Any]) -> SourceDocument:
    path = resolve_source_path(source)
    if not path.exists():
        raise FileNotFoundError(f"Source file not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        pages = _extract_pdf(path)
    elif suffix in {".txt", ".md"}:
        pages = _extract_text(path)
    elif suffix in {".html", ".htm"}:
        pages = _extract_html(path)
    else:
        raise ValueError(f"Unsupported source file type: {suffix}")

    pages = [page for page in pages if page.text.strip()]
    return SourceDocument(metadata=source, pages=pages)


def load_included_sources(manifest_path: Path) -> list[SourceDocument]:
    documents: list[SourceDocument] = []
    for source in load_manifest(manifest_path):
        if source.get("include_in_index", True):
            documents.append(load_source(source))
    return documents
